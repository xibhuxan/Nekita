"""Comandos y botones de anuncios. Solo admin y solo por privado."""

from __future__ import annotations

import asyncio
import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message

from nekita.core.broadcast import broadcast
from nekita.core.chats import list_active
from nekita.core.context import AppContext
from nekita.features.anuncios import service
from nekita.features.anuncios.prepare import CADUCADO, SOLO_PRIVADO, payload_from, prepare
from nekita.features.anuncios.service import AnnouncementError, PendingStore

log = logging.getLogger(__name__)


async def _run_broadcast(query: CallbackQuery, ctx: AppContext, item: service.Pending) -> None:
    if query.bot is None:
        return
    nombres = {g.chat_id: g.label for g in await list_active(ctx.db)}
    try:
        informe = await broadcast(query.bot, ctx.db, list(item.chat_ids), item.payload)
        await service.record(ctx.db, item.admin_id, item.scope, informe, item.preview)
        texto = service.render_report(informe, nombres)
    except Exception:
        log.exception("Fallo enviando un anuncio")
        texto = "El anuncio se interrumpió por un error (mira el log)."
    try:
        await query.bot.send_message(item.admin_id, texto)
    except TelegramAPIError:
        log.warning("No se pudo enviar el informe del anuncio")


def build_router() -> tuple[Router, set[asyncio.Task[None]]]:
    router = Router(name="anuncios")
    pending = PendingStore()
    tasks: set[asyncio.Task[None]] = set()

    @router.message(Command("grupos"))
    async def grupos(message: Message, ctx: AppContext) -> None:
        if message.chat.type != "private":
            await message.answer(SOLO_PRIVADO)
            return
        await message.answer(service.render_groups(await list_active(ctx.db)))

    @router.message(Command("anuncio"))
    async def anuncio(message: Message, command: CommandObject, ctx: AppContext) -> None:
        if message.chat.type != "private":
            await message.answer(SOLO_PRIVADO)
            return
        try:
            payload = payload_from(message, command.args or "")
            await prepare(
                message,
                pending,
                [g.chat_id for g in await list_active(ctx.db)],
                payload,
                "all",
            )
        except AnnouncementError as exc:
            await message.answer(f"{exc}\nUso: /anuncio <texto>  (o responde a un mensaje)")

    @router.message(Command("anuncio_a"))
    async def anuncio_a(message: Message, command: CommandObject, ctx: AppContext) -> None:
        if message.chat.type != "private":
            await message.answer(SOLO_PRIVADO)
            return
        try:
            destinos, texto = service.parse_targets(command.args or "", await list_active(ctx.db))
            payload = payload_from(message, texto)
            await prepare(message, pending, destinos, payload, "some")
        except AnnouncementError as exc:
            await message.answer(f"{exc}\nUso: /anuncio_a <nº o id> [<nº o id>...] <texto>")

    @router.callback_query(F.data.startswith("ann:"))
    async def confirmar(query: CallbackQuery, ctx: AppContext) -> None:
        if query.from_user.id != ctx.settings.admin_id or query.bot is None:
            await query.answer("Solo el administrador.", show_alert=True)
            return
        _, accion, token = (query.data or "ann::").split(":", 2)
        item = pending.take(token, query.from_user.id)
        if item is None:
            await query.answer(CADUCADO, show_alert=True)
            return
        await query.answer()
        if isinstance(query.message, Message):
            await query.message.edit_reply_markup(reply_markup=None)  # evita doble clic
        if accion != "ok":
            await query.bot.send_message(item.admin_id, "Anuncio cancelado.")
            return
        await query.bot.send_message(item.admin_id, f"Enviando a {len(item.chat_ids)} grupos…")
        tarea = asyncio.create_task(_run_broadcast(query, ctx, item), name="anuncio")
        tasks.add(tarea)
        tarea.add_done_callback(tasks.discard)

    return router, tasks
