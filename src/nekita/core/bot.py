"""Bot + Dispatcher: registro de features, arranque y vigilancia del polling (spec 5.2)."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence
from contextlib import suppress

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.session.base import BaseSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.exceptions import TelegramAPIError, TelegramNetworkError, TelegramUnauthorizedError
from aiogram.types import User

from nekita.core import chat_tracking
from nekita.core.context import AppContext
from nekita.core.feature import Feature
from nekita.core.middlewares import ContextMiddleware, MessagePipeline
from nekita.core.telegram import PollingHealth, TelegramGuard

log = logging.getLogger(__name__)

DRAIN_SECONDS = 10.0
GETME_ATTEMPTS = 5


class BotStartupError(Exception):
    """El bot no puede arrancar; el mensaje es legible para el usuario."""


class BotRuntime:
    """Todo lo que vive mientras el bot está conectado."""

    def __init__(
        self,
        ctx: AppContext,
        features: Sequence[Feature],
        *,
        session: BaseSession | None = None,
        retry_delay: float = 2.0,
    ) -> None:
        self.ctx = ctx
        self.features = list(features)
        self.health = PollingHealth()
        self._retry_delay = retry_delay
        if session is None and ctx.settings.api_url:
            session = AiohttpSession(api=TelegramAPIServer.from_base(ctx.settings.api_url))
        self.bot = Bot(token=ctx.settings.token.get_secret_value(), session=session)
        self.bot.session.middleware.register(TelegramGuard(self.health))
        self.dispatcher = Dispatcher()
        self.pipeline = MessagePipeline(ctx)
        self.dispatcher.update.outer_middleware(ContextMiddleware(ctx))
        self.dispatcher.message.outer_middleware(self.pipeline)
        self.dispatcher.include_router(chat_tracking.build_router())
        for feature in self.features:
            self.dispatcher.include_router(feature.router)
        self._polling: asyncio.Task[None] | None = None
        self.me: User | None = None

    async def start(self) -> None:
        """getMe (con reintentos de red), aviso de Group Privacy, menú y hooks."""
        self.me = await self._get_me()
        log.info("Conectado como @%s", self.me.username)
        if not self.me.can_read_all_group_messages:
            log.warning(
                "El bot no lee todos los mensajes de grupo (Group Privacy activado): "
                "las poles y nekomandos no funcionarán. Desactívalo en @BotFather "
                "(Bot Settings → Group Privacy → Turn off) o hazlo administrador."
            )
        try:  # best-effort: un fallo aquí no impide arrancar
            await self.bot.set_my_commands(self.ctx.registry.menu())
        except TelegramAPIError as exc:
            log.warning("No se pudo publicar el menú de comandos: %s", exc)
        for feature in self.features:
            if feature.on_startup:
                await feature.on_startup(self.ctx)
        self._polling = asyncio.create_task(self._poll(), name="polling")

    async def _get_me(self) -> User:
        for intento in range(1, GETME_ATTEMPTS + 1):
            try:
                return await self.bot.me()
            except TelegramUnauthorizedError as exc:
                raise BotStartupError(
                    "Telegram ha rechazado el token (NEKITA_TOKEN). Revísalo en @BotFather."
                ) from exc
            except TelegramNetworkError as exc:
                if intento == GETME_ATTEMPTS:
                    raise BotStartupError(f"No se pudo contactar con Telegram: {exc}") from exc
                log.warning("Sin conexión con Telegram (%d/%d), reintentando", intento, 5)
                await asyncio.sleep(self._retry_delay * intento)
        raise AssertionError("inalcanzable")  # pragma: no cover

    async def _poll(self) -> None:
        await self.dispatcher.start_polling(
            self.bot,
            handle_signals=False,  # las señales las gestiona app.py
            close_bot_session=False,
            polling_timeout=30,
            tasks_concurrency_limit=self.ctx.settings.max_handlers,
            allowed_updates=self.dispatcher.resolve_used_update_types(),
        )

    async def wait(self, stop: asyncio.Event) -> int:
        """Espera a la parada o a un fallo. Devuelve el código de salida (0 = limpio)."""
        if self._polling is None:
            raise RuntimeError("wait() antes de start()")
        stop_task = asyncio.create_task(stop.wait())
        fatal_task = asyncio.create_task(self.health.fatal.wait())
        try:
            await asyncio.wait(
                {self._polling, stop_task, fatal_task}, return_when=asyncio.FIRST_COMPLETED
            )
        finally:
            stop_task.cancel()
            fatal_task.cancel()
        if self.health.fatal.is_set():
            log.critical("Fallo irrecuperable: %s", self.health.fatal_reason)
            return 1
        if self._polling.done() and not stop.is_set():
            exc = self._polling.exception()
            log.critical("El polling terminó inesperadamente: %r", exc)
            return 1
        return 0

    async def shutdown(self) -> None:
        """Parar polling → esperar handlers (tope) → hooks → cerrar sesión."""
        if self._polling is not None and not self._polling.done():
            with suppress(RuntimeError):
                await asyncio.wait_for(self.dispatcher.stop_polling(), timeout=DRAIN_SECONDS)
        if self._polling is not None:
            self._polling.cancel()
            await asyncio.gather(self._polling, return_exceptions=True)
        sin_terminar = await self.pipeline.drain(DRAIN_SECONDS)
        if sin_terminar:
            log.warning("%d handlers no terminaron a tiempo", sin_terminar)
        for feature in reversed(self.features):
            if feature.on_shutdown:
                try:
                    await feature.on_shutdown(self.ctx)
                except Exception:
                    log.exception("Fallo en on_shutdown de %s", feature.name)
        await self.bot.session.close()
