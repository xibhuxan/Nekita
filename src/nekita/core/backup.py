"""Copias de seguridad con `VACUUM INTO` y retención (spec 7.7)."""

from __future__ import annotations

import asyncio
import logging
import re
import shlex
import sqlite3
from datetime import UTC, date, datetime
from pathlib import Path

from nekita.core.db import Database

log = logging.getLogger(__name__)

_NAME_RE = re.compile(r"^nekita_(\d{4}-\d{2}-\d{2})T(\d{2}-\d{2}-\d{2})\.db$")
KEEP_DAILY = 7
KEEP_WEEKLY = 4


def _fecha(p: Path) -> date | None:
    m = _NAME_RE.match(p.name)
    return date.fromisoformat(m.group(1)) if m else None


def select_to_keep(files: list[Path]) -> set[Path]:
    """7 diarias (las más recientes) + la más reciente de cada una de las 4 semanas previas."""
    datadas = sorted(((f, d) for f in files if (d := _fecha(f))), key=lambda x: x[0].name)
    keep = {f for f, _ in datadas[-KEEP_DAILY:]}
    por_semana: dict[tuple[int, int], Path] = {}
    for f, d in datadas:
        iso = d.isocalendar()
        por_semana[(iso.year, iso.week)] = f  # la última (más reciente) de la semana
    for clave in sorted(por_semana)[-(KEEP_WEEKLY + 1) :]:
        keep.add(por_semana[clave])
    return keep


def prune(backups_dir: Path) -> list[Path]:
    """Borra las copias que ya no hay que conservar. Solo toca ficheros `nekita_*.db`."""
    files = [p for p in backups_dir.glob("nekita_*.db") if _NAME_RE.match(p.name)]
    keep = select_to_keep(files)
    borradas = [f for f in files if f not in keep]
    for f in borradas:
        f.unlink(missing_ok=True)
    return borradas


def _integrity(path: Path) -> str:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        return str(conn.execute("PRAGMA integrity_check").fetchone()[0])
    finally:
        conn.close()


async def run_external_copy(cmd: str, destino: Path) -> None:
    """Ejecuta el comando de copia externa (sin shell); `{file}` se sustituye por la copia."""
    if not cmd.strip():
        return
    args = [a.replace("{file}", str(destino)) for a in shlex.split(cmd)]
    if "{file}" not in cmd:
        args.append(str(destino))
    proc = await asyncio.create_subprocess_exec(
        *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
    )
    try:
        salida, _ = await asyncio.wait_for(proc.communicate(), timeout=300)
    except TimeoutError:
        proc.kill()
        log.error("La copia externa excedió el tiempo límite")
        return
    if proc.returncode != 0:
        log.error("La copia externa falló (%s): %s", proc.returncode, salida.decode()[-300:])


async def make_backup(db: Database, backups_dir: Path, *, external_cmd: str = "") -> Path:
    """Crea una copia consistente, verifica su integridad, aplica retención y copia fuera."""
    backups_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%S")
    destino = backups_dir / f"nekita_{ts}.db"
    await db.vacuum_into(destino)
    estado = await asyncio.to_thread(_integrity, destino)
    if estado != "ok":
        destino.unlink(missing_ok=True)
        raise RuntimeError(f"La copia no pasa integrity_check: {estado}")
    for borrada in prune(backups_dir):
        log.info("Copia antigua eliminada: %s", borrada.name)
    log.info("Copia de seguridad creada: %s", destino)
    await run_external_copy(external_cmd, destino)
    return destino
