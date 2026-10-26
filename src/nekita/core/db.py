"""SQLite: una conexión, PRAGMAs, transacciones y migraciones (spec 7.1-7.2)."""

from __future__ import annotations

import asyncio
import logging
import sqlite3
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager, suppress
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import aiosqlite

from nekita.core.migrations import DatabaseError, Migration, load_migrations

log = logging.getLogger(__name__)

MIN_SQLITE = (3, 37, 0)  # tablas STRICT
__all__ = ["Database", "DatabaseError", "utc_now_iso"]


def utc_now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


class Database:
    """Conexión única (escritor único). Todo acceso pasa por un lock asyncio."""

    def __init__(self, conn: aiosqlite.Connection, path: str, *, is_new: bool) -> None:
        self._conn = conn
        self._lock = asyncio.Lock()
        self.path = path
        self.is_new = is_new  # True si la BD se creó en este arranque

    @classmethod
    async def open(
        cls,
        path: Path | str,
        *,
        backups_dir: Path | None = None,
        migrations: Sequence[Migration] | None = None,
    ) -> Database:
        if sqlite3.sqlite_version_info < MIN_SQLITE:
            raise DatabaseError(
                f"SQLite {sqlite3.sqlite_version} es demasiado antiguo "
                f"(se necesita >= {'.'.join(map(str, MIN_SQLITE))} para tablas STRICT)"
            )
        en_memoria = str(path) == ":memory:"
        if not en_memoria:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        todas = list(migrations) if migrations is not None else load_migrations()
        ultima = todas[-1].version if todas else 0

        try:
            conn = await aiosqlite.connect(str(path), isolation_level=None)
        except sqlite3.Error as exc:
            raise DatabaseError(f"No se pudo abrir la base de datos {path}: {exc}") from exc
        try:
            cur = await conn.execute("PRAGMA user_version")
            fila = await cur.fetchone()
            actual = int(fila[0]) if fila else 0
            if actual > ultima:  # antes de tocar nada más
                raise DatabaseError(
                    f"La base de datos es de una versión más nueva (v{actual}) que este "
                    f"programa (v{ultima}). No se modifica: actualiza Nekita."
                )
            db = cls(conn, str(path), is_new=actual == 0)
            await db._apply_pragmas()
            await db._migrate(todas, actual, None if en_memoria else backups_dir)
            return db
        except BaseException:
            await conn.close()
            raise

    async def _apply_pragmas(self) -> None:
        for pragma in (
            "journal_mode=WAL",
            "synchronous=NORMAL",
            "foreign_keys=ON",
            "busy_timeout=5000",
            "cache_size=-2000",  # ~2 MB
            "temp_store=MEMORY",
        ):
            await self._conn.execute(f"PRAGMA {pragma}")

    async def _migrate(self, todas: list[Migration], actual: int, backups_dir: Path | None) -> None:
        pendientes = [m for m in todas if m.version > actual]
        if not pendientes:
            return
        if actual > 0 and backups_dir is not None:  # ya hay datos: copia antes de migrar
            backups_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%S")
            destino = backups_dir / f"premigracion_v{actual}_{ts}.db"
            await self.vacuum_into(destino)
            log.info("Copia previa a la migración: %s", destino)
        for mig in pendientes:
            log.info("Aplicando migración %04d_%s", mig.version, mig.name)
            script = (
                f"BEGIN IMMEDIATE;\n{mig.sql}\nPRAGMA user_version = {int(mig.version)};\nCOMMIT;"
            )
            try:
                await self._conn.executescript(script)
            except sqlite3.Error as exc:
                with suppress(sqlite3.Error):
                    await self._conn.execute("ROLLBACK")
                raise DatabaseError(
                    f"Falló la migración {mig.version:04d}_{mig.name}: {exc}"
                ) from exc

    # --- acceso ---

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[aiosqlite.Connection]:
        """`BEGIN IMMEDIATE` ... `COMMIT`; cualquier excepción hace `ROLLBACK`."""
        async with self._lock:
            await self._conn.execute("BEGIN IMMEDIATE")
            try:
                yield self._conn
            except BaseException:
                await self._conn.execute("ROLLBACK")
                raise
            else:
                await self._conn.execute("COMMIT")

    async def execute(self, sql: str, params: Sequence[Any] = ()) -> None:
        async with self.transaction() as conn:
            await conn.execute(sql, params)

    async def fetchall(self, sql: str, params: Sequence[Any] = ()) -> list[tuple[Any, ...]]:
        async with self._lock:
            cur = await self._conn.execute(sql, params)
            return [tuple(r) for r in await cur.fetchall()]

    async def fetchone(self, sql: str, params: Sequence[Any] = ()) -> tuple[Any, ...] | None:
        rows = await self.fetchall(sql, params)
        return rows[0] if rows else None

    async def user_version(self) -> int:
        fila = await self.fetchone("PRAGMA user_version")
        return int(fila[0]) if fila else 0

    async def integrity_check(self) -> str:
        fila = await self.fetchone("PRAGMA integrity_check")
        return str(fila[0]) if fila else "sin respuesta"

    async def vacuum_into(self, destino: Path) -> None:
        """Copia consistente con WAL activo (nunca `cp`). `destino` no debe existir."""
        async with self._lock:
            await self._conn.execute("VACUUM INTO ?", (str(destino),))

    async def close(self) -> None:
        async with self._lock:
            with suppress(sqlite3.Error):
                await self._conn.execute("PRAGMA optimize")
            await self._conn.close()
