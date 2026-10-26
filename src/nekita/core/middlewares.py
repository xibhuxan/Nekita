"""Tubería común de mensajes (spec 4.6, 9.1).

Un solo middleware externo, en orden explícito y fácil de leer:
filtro @OtroBot → descarte de updates viejos → admin → límite de uso →
lock por chat → handler → estadísticas (solo éxito) / error con referencia.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from nekita.core.chats import GROUP_TYPES, upsert_chat
from nekita.core.context import AppContext
from nekita.core.errors import report_failure
from nekita.core.feature import CommandInfo
from nekita.core.limits import Cooldown, KeyedLock
from nekita.core.texts import NO_PERMISO

log = logging.getLogger(__name__)

STALE_SECONDS = 60
_COMMAND_RE = re.compile(r"^/([A-Za-z0-9_]{1,64})(?:@([A-Za-z0-9_]{1,64}))?(?=\s|$)")

Handler = Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]]


def parse_command(text: str | None) -> tuple[str, str | None] | None:
    """`/Neko@MiBot args` → ('neko', 'MiBot'); `hola` → None."""
    if not text:
        return None
    m = _COMMAND_RE.match(text)
    if not m:
        return None
    return m.group(1).lower(), m.group(2)


class ContextMiddleware(BaseMiddleware):
    """Inyecta `ctx` en TODOS los eventos (botones, altas/bajas del bot...), no solo mensajes."""

    def __init__(self, ctx: AppContext) -> None:
        self._ctx = ctx

    async def __call__(self, handler: Handler, event: TelegramObject, data: dict[str, Any]) -> Any:
        data["ctx"] = self._ctx
        return await handler(event, data)


class MessagePipeline(BaseMiddleware):
    def __init__(
        self,
        ctx: AppContext,
        *,
        clock: Callable[[], float] = time.time,
        cooldown: Cooldown | None = None,
    ) -> None:
        self._ctx = ctx
        self._clock = clock
        self._locks = KeyedLock()
        self._cooldown = cooldown or Cooldown()
        self._inflight: set[asyncio.Task[Any]] = set()
        self._known_chats: dict[int, str | None] = {}  # chat_id -> título ya guardado

    async def drain(self, timeout: float) -> int:  # noqa: ASYNC109
        """Espera a los handlers en curso; devuelve cuántos quedaron sin terminar."""
        pendientes = {t for t in self._inflight if not t.done()}
        if pendientes:
            _, resto = await asyncio.wait(pendientes, timeout=timeout)
            return len(resto)
        return 0

    async def __call__(self, handler: Handler, event: TelegramObject, data: dict[str, Any]) -> Any:
        if not isinstance(event, Message):
            return await handler(event, data)

        parsed = parse_command(event.text)
        info: CommandInfo | None = None
        if parsed is not None:
            name, target = parsed
            if target is not None and not await self._is_for_me(target, data):
                return None  # /comando@OtroBot: no es para este bot
            info = self._ctx.registry.get(name)

        await self._track_chat(event)
        user = event.from_user
        is_admin = user is not None and user.id == self._ctx.settings.admin_id
        data["ctx"] = self._ctx
        data["is_admin"] = is_admin
        data["command_info"] = info

        if info is not None:
            if info.drop_if_stale and self._age(event) > STALE_SECONDS:
                log.info("Descartado /%s antiguo (%.0f s)", info.name, self._age(event))
                return None
            if info.admin_only and not is_admin:
                await event.answer(NO_PERMISO)
                return None
            uid = user.id if user else 0
            if info.cooldown and not self._cooldown.allow((event.chat.id, uid), info.cooldown):
                return None  # límite de uso: se ignora en silencio

        task = asyncio.current_task()
        if task is not None:
            self._inflight.add(task)
        try:
            async with self._locks.hold(event.chat.id):
                try:
                    result = await handler(event, data)
                except Exception as exc:
                    await report_failure(event, exc, command=info.name if info else None)
                    return None
            if info is not None:
                self._ctx.stats.command(info.name)  # solo si terminó sin excepción
            return result
        finally:
            if task is not None:
                self._inflight.discard(task)

    async def _track_chat(self, message: Message) -> None:
        """Apunta el grupo la primera vez que se le ve (y si cambia de título)."""
        chat = message.chat
        if chat.type not in GROUP_TYPES or self._known_chats.get(chat.id, "") == chat.title:
            return
        try:
            await upsert_chat(self._ctx.db, chat.id, chat.title, chat.type)
            self._known_chats[chat.id] = chat.title
        except Exception:
            log.exception("No se pudo registrar el grupo %s", chat.id)

    async def _is_for_me(self, target: str, data: dict[str, Any]) -> bool:
        me = await data["bot"].me()
        return bool(me.username) and target.lower() == str(me.username).lower()

    def _age(self, message: Message) -> float:
        fecha = message.date
        if fecha.tzinfo is None:
            fecha = fecha.replace(tzinfo=UTC)
        return self._clock() - datetime.timestamp(fecha)
