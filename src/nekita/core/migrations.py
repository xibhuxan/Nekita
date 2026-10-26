"""Carga de migraciones `NNNN_nombre.sql` (spec 3, decisión 5)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_MIGRATION_RE = re.compile(r"^(\d{4})_([A-Za-z0-9_]+)\.sql$")


class DatabaseError(Exception):
    """Error de base de datos con mensaje legible; aborta el arranque."""


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    sql: str


def default_migrations_dir() -> Path:
    # Dentro del paquete: un clone + `uv sync` ya las incluye.
    return Path(__file__).resolve().parent.parent / "migrations"


def load_migrations(directory: Path | None = None) -> list[Migration]:
    """Lee `NNNN_nombre.sql`; exige numeración 1..N sin huecos."""
    directory = directory or default_migrations_dir()
    found: list[Migration] = []
    for f in sorted(directory.glob("*.sql")):
        m = _MIGRATION_RE.match(f.name)
        if not m:
            raise DatabaseError(f"Nombre de migración no válido: {f.name} (usa NNNN_nombre.sql)")
        found.append(Migration(int(m.group(1)), m.group(2), f.read_text(encoding="utf-8")))
    for esperado, mig in enumerate(found, start=1):
        if mig.version != esperado:
            raise DatabaseError(f"Migraciones no consecutivas: falta la {esperado:04d}")
    return found
