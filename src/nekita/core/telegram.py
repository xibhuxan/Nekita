"""Vigilancia de la sesión de Telegram: reintento por 429, latido y fallos fatales.

aiogram reintenta `getUpdates` eternamente aunque el token esté revocado o haya
otra instancia (409). Aquí se detecta para terminar con código ≠ 0 (spec 4.6).
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING

from aiogram.client.session.middlewares.base import BaseRequestMiddleware, NextRequestMiddlewareType
from aiogram.exceptions import (
    TelegramConflictError,
    TelegramRetryAfter,
    TelegramUnauthorizedError,
)
from aiogram.methods import GetUpdates

if TYPE_CHECKING:
    from aiogram.client.bot import Bot
    from aiogram.methods import Response, TelegramMethod
    from aiogram.methods.base import TelegramType

log = logging.getLogger(__name__)

MAX_RETRY_WAIT = 60.0
CONFLICTS_BEFORE_FATAL = 3


class PollingHealth:
    """Estado del polling: latido en memoria y señal de fallo irrecuperable."""

    def __init__(self) -> None:
        self.last_ok: float | None = None  # time.monotonic() del último getUpdates correcto
        self.fatal = asyncio.Event()
        self.fatal_reason = ""
        self._conflicts = 0

    def beat(self) -> None:
        self.last_ok = time.monotonic()
        self._conflicts = 0

    def seconds_since_beat(self) -> float | None:
        return None if self.last_ok is None else time.monotonic() - self.last_ok

    def set_fatal(self, reason: str) -> None:
        if not self.fatal.is_set():
            self.fatal_reason = reason
            self.fatal.set()

    def conflict(self) -> None:
        self._conflicts += 1
        if self._conflicts >= CONFLICTS_BEFORE_FATAL:
            self.set_fatal(
                "Telegram devuelve 409: hay otra instancia con este token "
                "(¿sigue en marcha la versión Node?)"
            )


class TelegramGuard(BaseRequestMiddleware):
    def __init__(self, health: PollingHealth, *, max_wait: float = MAX_RETRY_WAIT) -> None:
        self._health = health
        self._max_wait = max_wait

    async def __call__(
        self,
        make_request: NextRequestMiddlewareType[TelegramType],
        bot: Bot,
        method: TelegramMethod[TelegramType],
    ) -> Response[TelegramType]:
        es_polling = isinstance(method, GetUpdates)
        try:
            try:
                respuesta = await make_request(bot, method)
            except TelegramRetryAfter as exc:  # 429: esperar lo indicado y reintentar UNA vez
                espera = min(float(exc.retry_after), self._max_wait)
                log.warning("Telegram pide esperar %.0f s (%s)", espera, type(method).__name__)
                await asyncio.sleep(espera)
                respuesta = await make_request(bot, method)
        except TelegramUnauthorizedError:
            if es_polling:
                self._health.set_fatal("Telegram ha rechazado el token (¿revocado?)")
            raise
        except TelegramConflictError:
            if es_polling:
                self._health.conflict()
            raise
        if es_polling:
            self._health.beat()
        return respuesta
