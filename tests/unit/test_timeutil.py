from __future__ import annotations

from datetime import UTC, datetime

from nekita.core import timeutil


def test_hora_respeta_horario_de_verano() -> None:
    invierno = datetime(2026, 1, 15, 12, 0, 5, tzinfo=UTC)
    verano = datetime(2026, 7, 15, 12, 0, 5, tzinfo=UTC)
    assert timeutil.format_time(invierno, "Europe/Madrid") == "13:00:05"
    assert timeutil.format_time(verano, "Europe/Madrid") == "14:00:05"


def test_fecha_cambia_a_las_00_locales_no_utc() -> None:
    # 23:30 UTC del 31-dic ya es 1 de enero en Madrid, pero aún 31-dic en Canarias.
    instante = datetime(2026, 12, 31, 23, 30, tzinfo=UTC)
    assert timeutil.format_date(instante, "Europe/Madrid") == "01-01-2027"
    assert timeutil.format_date(instante, "Atlantic/Canary") == "31-12-2026"


def test_datetime_sin_zona_se_toma_como_utc() -> None:
    ingenuo = datetime(2026, 1, 15, 12, 0, 0)
    assert timeutil.format_time(ingenuo, "UTC") == "12:00:00"
