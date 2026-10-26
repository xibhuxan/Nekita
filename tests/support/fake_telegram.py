"""Sesión falsa de Telegram: prueba el flujo completo del bot sin red (spec 11)."""

from __future__ import annotations

import asyncio
import itertools
import time
from collections.abc import AsyncGenerator
from typing import Any

from aiogram import Bot
from aiogram.client.session.base import BaseSession
from aiogram.methods import GetMe, GetUpdates, SendMessage, SetMyCommands, TelegramMethod
from aiogram.methods.base import TelegramType
from aiogram.types import Chat, Message, Update, User
from aiogram.types import Message as TgMessage

BOT_ID = 123456
BOT_USERNAME = "nekita_test_bot"


class FakeTelegram(BaseSession):
    """Cola de updates de entrada y registro de todo lo que el bot envía."""

    def __init__(self, *, can_read_all_group_messages: bool = True) -> None:
        super().__init__()
        self.updates: asyncio.Queue[Update] = asyncio.Queue()
        self.calls: list[TelegramMethod[Any]] = []
        self.errors: dict[type[TelegramMethod[Any]], list[Exception]] = {}
        self.can_read_all = can_read_all_group_messages
        self._ids = itertools.count(1)
        self._msg_ids = itertools.count(1000)

    # --- entrada ---

    def feed_text(
        self,
        text: str,
        *,
        chat_id: int = -100,
        user_id: int = 42,
        chat_type: str = "supergroup",
        date: float | None = None,
        username: str | None = "ana",
        first_name: str = "Ana",
    ) -> None:
        fecha = int(date if date is not None else time.time())
        update = Update.model_validate(
            {
                "update_id": next(self._ids),
                "message": {
                    "message_id": next(self._msg_ids),
                    "date": fecha,
                    "chat": {"id": chat_id, "type": chat_type, "title": "Grupo"},
                    "from": {
                        "id": user_id,
                        "is_bot": False,
                        "first_name": first_name,
                        "username": username,
                    },
                    "text": text,
                    "entities": (
                        [{"type": "bot_command", "offset": 0, "length": len(text.split()[0])}]
                        if text.startswith("/")
                        else []
                    ),
                },
            }
        )
        self.updates.put_nowait(update)

    # --- salida ---

    def sent_texts(self) -> list[str]:
        return [c.text for c in self.calls if isinstance(c, SendMessage)]

    async def wait_for_sent(self, n: int, timeout: float = 3.0) -> list[str]:
        """Espera hasta que el bot haya enviado `n` mensajes."""
        async with asyncio.timeout(timeout):
            while len(self.sent_texts()) < n:
                await asyncio.sleep(0.01)
        return self.sent_texts()

    # --- BaseSession ---

    async def close(self) -> None:
        return None

    async def make_request(
        self,
        bot: Bot,
        method: TelegramMethod[TelegramType],
        timeout: int | None = None,
    ) -> TelegramType:
        pendientes = self.errors.get(type(method))
        if pendientes:
            raise pendientes.pop(0)
        if isinstance(method, GetUpdates):
            try:
                update = await asyncio.wait_for(self.updates.get(), timeout=0.05)
            except TimeoutError:
                return []  # type: ignore[return-value]
            return [update]  # type: ignore[return-value]
        self.calls.append(method)
        if isinstance(method, GetMe):
            return User(  # type: ignore[return-value]
                id=BOT_ID,
                is_bot=True,
                first_name="Nekita",
                username=BOT_USERNAME,
                can_read_all_group_messages=self.can_read_all,
            )
        if isinstance(method, SendMessage):
            return TgMessage(  # type: ignore[return-value]
                message_id=next(self._msg_ids),
                date=int(time.time()),  # type: ignore[arg-type]
                chat=Chat(id=int(method.chat_id), type="supergroup"),
                text=method.text,
            )
        if isinstance(method, SetMyCommands):
            return True  # type: ignore[return-value]
        return True  # type: ignore[return-value]

    async def stream_content(
        self,
        url: str,
        headers: dict[str, Any] | None = None,
        timeout: int = 30,
        chunk_size: int = 65536,
        raise_for_status: bool = True,
    ) -> AsyncGenerator[bytes]:
        yield b""


__all__ = ["BOT_ID", "BOT_USERNAME", "FakeTelegram", "Message"]
