import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from nekita.core.backup import make_backup, select_to_keep
from nekita.core.db import Database
from nekita.core.scheduler import seconds_until
from nekita.core.stats import Stats


async def test_backup_es_consistente_y_legible(db: Database, tmp_path: Path) -> None:
    await db.execute("INSERT INTO stats(key, count) VALUES('cmd:neko', 3)")
    destino = await make_backup(db, tmp_path / "bk")
    with closing(sqlite3.connect(destino)) as conn:
        assert conn.execute("SELECT count FROM stats").fetchall() == [(3,)]


async def test_backup_ejecuta_copia_externa(db: Database, tmp_path: Path) -> None:
    fuera = tmp_path / "fuera"
    fuera.mkdir()
    await make_backup(db, tmp_path / "bk", external_cmd=f"cp {{file}} {fuera}")
    assert len(list(fuera.glob("nekita_*.db"))) == 1


def test_retencion_7_diarias_y_semanales(tmp_path: Path) -> None:
    files = [tmp_path / f"nekita_2026-01-{d:02d}T04-00-00.db" for d in range(1, 29)]
    keep = select_to_keep(files)
    assert all(f in keep for f in files[-7:])  # las 7 más recientes
    assert files[0] not in keep and len(keep) < len(files)
    assert len(keep) <= 7 + 5


async def test_stats_acumula_y_vuelca(db: Database) -> None:
    s = Stats()
    s.command("neko")
    s.command("neko")
    s.command("hora")
    assert await s.top_commands(db) == [("neko", 2), ("hora", 1)]
    await s.flush(db)
    assert s.pending == 0
    s.command("neko")
    assert await s.top_commands(db) == [("neko", 3), ("hora", 1)]


async def test_stats_conserva_si_falla_el_volcado(db: Database) -> None:
    s = Stats()
    s.command("neko")
    await db.execute("DROP TABLE stats")
    with pytest.raises(sqlite3.OperationalError):
        await s.flush(db)
    assert s.pending == 1


def test_seconds_until_hoy_y_manana() -> None:
    tz = ZoneInfo("Europe/Madrid")
    ahora = datetime(2026, 1, 10, 2, 0, tzinfo=UTC)  # 03:00 en Madrid
    assert seconds_until(ahora, "04:00", tz) == 3600
    assert seconds_until(ahora, "03:00", tz) == 24 * 3600  # ya es la hora: mañana


def test_seconds_until_cambio_de_hora() -> None:
    tz = ZoneInfo("Europe/Madrid")
    ahora = datetime(2026, 3, 28, 3, 0, tzinfo=UTC)  # 04:00 Madrid, el día antes del cambio
    # el 29/03 son 23 horas reales entre las 04:00 de ambos días
    assert seconds_until(ahora, "04:00", tz) == 23 * 3600
