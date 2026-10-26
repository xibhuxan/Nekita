"""Orquestación de arranque y parada (asyncio puro, sin servidor HTTP)."""

from __future__ import annotations

import asyncio
import logging
import signal

from nekita import __version__
from nekita.config import Settings

log = logging.getLogger(__name__)


def install_signal_handlers(stop: asyncio.Event) -> None:
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)


async def run(settings: Settings, stop: asyncio.Event | None = None) -> int:
    """Arranca el bot y espera la señal de parada. Devuelve el código de salida.

    Fase 0: aún no hay bot ni BD; los pasos del ciclo de vida (spec 5.2)
    se irán añadiendo aquí, en orden, y se cerrarán en orden inverso.
    """
    stop_event = stop if stop is not None else asyncio.Event()
    if stop is None:
        install_signal_handlers(stop_event)

    log.info("Nekita v%s lista (zona %s)", __version__, settings.tz)
    try:
        await stop_event.wait()
    finally:
        log.info("Parando Nekita...")
    return 0
