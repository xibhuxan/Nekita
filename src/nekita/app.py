"""Orquestación de arranque y parada (asyncio puro, sin servidor HTTP)."""

from __future__ import annotations

import asyncio
import logging
import signal
from zoneinfo import ZoneInfo

from aiogram.client.session.base import BaseSession

from nekita import __version__
from nekita.config import Settings
from nekita.core import scheduler
from nekita.core.backup import make_backup
from nekita.core.bot import BotRuntime, BotStartupError
from nekita.core.context import AppContext
from nekita.core.db import Database
from nekita.core.importer import import_node_data
from nekita.core.registry import Registry
from nekita.core.stats import Stats
from nekita.features import load_features

log = logging.getLogger(__name__)


def install_signal_handlers(stop: asyncio.Event) -> None:
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)


async def run(
    settings: Settings,
    stop: asyncio.Event | None = None,
    *,
    session: BaseSession | None = None,
) -> int:
    """Arranca el bot y espera la parada o un fallo. Devuelve el código de salida.

    Orden (spec 5.2): BD → importación → tareas → bot. Se cierra en orden inverso.
    `session` permite inyectar una sesión falsa de Telegram en las pruebas.
    """
    stop_event = stop if stop is not None else asyncio.Event()
    if stop is None:
        install_signal_handlers(stop_event)

    data_dir = settings.data_path
    backups_dir = data_dir / "backups"
    db = await Database.open(data_dir / "nekita.db", backups_dir=backups_dir)
    stats = Stats()
    tasks: list[asyncio.Task[None]] = []
    runtime: BotRuntime | None = None
    codigo = 0
    try:
        await import_node_data(db, data_dir, backups_dir)

        async def volcar() -> None:
            await stats.flush(db)

        async def copia() -> None:
            await make_backup(db, backups_dir, external_cmd=settings.backup_copia_cmd)

        tasks.append(asyncio.create_task(scheduler.every(30, volcar, name="stats")))
        tasks.append(
            asyncio.create_task(
                scheduler.daily_at(
                    settings.backup_hora, ZoneInfo(settings.tz), copia, name="backup"
                )
            )
        )
        features = load_features()
        ctx = AppContext(settings, db, stats, Registry(features))
        runtime = BotRuntime(ctx, features, session=session)
        await runtime.start()
        log.info("Nekita v%s lista (zona %s)", __version__, settings.tz)
        codigo = await runtime.wait(stop_event)
    except BotStartupError as exc:
        log.critical("%s", exc)
        codigo = 1
    finally:
        log.info("Parando Nekita...")
        if runtime is not None:
            await runtime.shutdown()
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        try:
            await stats.flush(db)
        except Exception:
            log.exception("No se pudieron volcar los contadores al parar")
        await db.close()
    return codigo
