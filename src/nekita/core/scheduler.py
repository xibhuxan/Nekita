"""Tareas periódicas mínimas sobre asyncio + zoneinfo (spec 3, decisión 8)."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

log = logging.getLogger(__name__)

Job = Callable[[], Awaitable[None]]


def seconds_until(now: datetime, hhmm: str, tz: ZoneInfo) -> float:
    """Segundos hasta la próxima ocurrencia de `HH:MM` local (siempre > 0).

    Seguro con cambios de hora: se compara en UTC, no en hora de pared.
    """
    hh, mm = (int(x) for x in hhmm.split(":"))
    local = now.astimezone(tz)
    objetivo = datetime(local.year, local.month, local.day, hh, mm, tzinfo=tz)
    if objetivo.astimezone(UTC) <= now.astimezone(UTC):
        manana = local.date() + timedelta(days=1)
        objetivo = datetime(manana.year, manana.month, manana.day, hh, mm, tzinfo=tz)
    return (objetivo.astimezone(UTC) - now.astimezone(UTC)).total_seconds()


async def _run_safely(name: str, job: Job) -> None:
    try:
        await job()
    except Exception:
        log.exception("Fallo en la tarea %s", name)


async def every(seconds: float, job: Job, *, name: str) -> None:
    """Ejecuta `job` cada `seconds`. Un fallo se registra y no detiene el bucle."""
    while True:
        await asyncio.sleep(seconds)
        await _run_safely(name, job)


async def daily_at(hhmm: str, tz: ZoneInfo, job: Job, *, name: str) -> None:
    """Ejecuta `job` cada día a `HH:MM` en `tz`."""
    while True:
        await asyncio.sleep(seconds_until(datetime.now(UTC), hhmm, tz))
        await _run_safely(name, job)
        await asyncio.sleep(1)  # evita repetir dentro del mismo minuto
