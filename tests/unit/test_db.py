import asyncio
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from nekita.core.db import Database, DatabaseError
from nekita.core.migrations import Migration, load_migrations

M1 = Migration(1, "uno", "CREATE TABLE a(x INTEGER) STRICT;")
M2 = Migration(2, "dos", "CREATE TABLE b(y INTEGER) STRICT;")


def consulta(path: Path, sql: str) -> list[tuple[object, ...]]:
    with closing(sqlite3.connect(path)) as conn:
        return conn.execute(sql).fetchall()


async def test_bd_nueva_aplica_esquema_y_pragmas(tmp_path: Path) -> None:
    db = await Database.open(tmp_path / "n.db")
    try:
        assert db.is_new
        assert await db.user_version() == len(load_migrations())
        assert (await db.fetchone("PRAGMA journal_mode"))[0] == "wal"  # type: ignore[index]
        assert (await db.fetchone("PRAGMA foreign_keys"))[0] == 1  # type: ignore[index]
        tablas = {r[0] for r in await db.fetchall("SELECT name FROM sqlite_master")}
        assert {"chats", "users", "pole_wins", "stats"} <= tablas
    finally:
        await db.close()


async def test_reabrir_no_repite_migraciones(tmp_path: Path) -> None:
    primera = await Database.open(tmp_path / "n.db", migrations=[M1])
    assert primera.is_new
    await primera.close()
    db = await Database.open(tmp_path / "n.db", migrations=[M1])
    try:
        assert not db.is_new
    finally:
        await db.close()


async def test_migracion_hace_copia_previa(tmp_path: Path) -> None:
    db = await Database.open(tmp_path / "n.db", migrations=[M1])
    await db.execute("INSERT INTO a VALUES (7)")
    await db.close()
    backups = tmp_path / "bk"
    db = await Database.open(tmp_path / "n.db", backups_dir=backups, migrations=[M1, M2])
    try:
        assert await db.user_version() == 2
        copias = list(backups.glob("premigracion_v1_*.db"))
        assert len(copias) == 1
        assert consulta(copias[0], "SELECT x FROM a") == [(7,)]
    finally:
        await db.close()


async def test_migracion_fallida_no_deja_rastro(tmp_path: Path) -> None:
    mala = Migration(1, "mala", "CREATE TABLE ok(x INTEGER); SELECT * FROM no_existe;")
    with pytest.raises(DatabaseError, match="0001_mala"):
        await Database.open(tmp_path / "n.db", migrations=[mala])
    assert consulta(tmp_path / "n.db", "PRAGMA user_version") == [(0,)]
    assert consulta(tmp_path / "n.db", "SELECT name FROM sqlite_master WHERE name='ok'") == []


async def test_bd_mas_nueva_que_el_programa_se_rechaza(tmp_path: Path) -> None:
    await (await Database.open(tmp_path / "n.db", migrations=[M1, M2])).close()
    with pytest.raises(DatabaseError, match="más nueva"):
        await Database.open(tmp_path / "n.db", migrations=[M1])


async def test_transaccion_hace_rollback(tmp_path: Path) -> None:
    db = await Database.open(tmp_path / "n.db", migrations=[M1])
    try:
        with pytest.raises(RuntimeError):
            async with db.transaction() as conn:
                await conn.execute("INSERT INTO a VALUES (1)")
                raise RuntimeError("boom")
        assert await db.fetchall("SELECT * FROM a") == []
    finally:
        await db.close()


async def test_escrituras_concurrentes_se_serializan(tmp_path: Path) -> None:
    db = await Database.open(tmp_path / "n.db", migrations=[M1])
    try:
        await asyncio.gather(*(db.execute("INSERT INTO a VALUES (?)", (i,)) for i in range(50)))
        assert (await db.fetchone("SELECT COUNT(*) FROM a"))[0] == 50  # type: ignore[index]
    finally:
        await db.close()


def test_migraciones_con_hueco_o_nombre_malo(tmp_path: Path) -> None:
    (tmp_path / "0002_x.sql").write_text("SELECT 1;")
    with pytest.raises(DatabaseError, match="0001"):
        load_migrations(tmp_path)
    (tmp_path / "malo.sql").write_text("SELECT 1;")
    with pytest.raises(DatabaseError, match="no válido"):
        load_migrations(tmp_path)
