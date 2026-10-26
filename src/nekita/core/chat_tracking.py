"""Alta y baja de grupos cuando añaden o expulsan al bot (`my_chat_member`)."""

from __future__ import annotations

import logging

from aiogram import Router
from aiogram.types import ChatMemberUpdated

from nekita.core.chats import GROUP_TYPES, set_active, upsert_chat
from nekita.core.context import AppContext

log = logging.getLogger(__name__)


def build_router() -> Router:
    router = Router(name="chat_tracking")

    @router.my_chat_member()
    async def on_member_change(event: ChatMemberUpdated, ctx: AppContext) -> None:
        if event.chat.type not in GROUP_TYPES:
            return  # en privado, un bloqueo del usuario no nos interesa
        if event.new_chat_member.status in ("left", "kicked"):
            await set_active(ctx.db, event.chat.id, False)
            log.info("El bot ya no está en %s (%s)", event.chat.title, event.chat.id)
        else:
            await upsert_chat(ctx.db, event.chat.id, event.chat.title, event.chat.type)
            log.info("El bot está en %s (%s)", event.chat.title, event.chat.id)

    return router
