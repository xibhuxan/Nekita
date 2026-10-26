"""Envío a muchos chats con ritmo, sin saturar a Telegram (spec 9.1: cola de salida)."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence
from dataclasses import dataclass, field

from aiogram import Bot
from aiogram.exceptions import (
    TelegramAPIError,
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramMigrateToChat,
    TelegramNetworkError,
    TelegramRetryAfter,
)

from nekita.core.chats import set_active, upsert_chat
from nekita.core.db import Database

log = logging.getLogger(__name__)

DEFAULT_RATE = 15.0  # mensajes/segundo, por debajo del tope global de Telegram (~30/s)
_GONE = ("chat not found", "bot was kicked", "bot is not a member", "have no rights to send")


@dataclass(frozen=True)
class Payload:
    """Qué se envía: un texto, o la copia de un mensaje existente (conserva foto y formato)."""

    text: str | None = None
    from_chat_id: int | None = None
    message_id: int | None = None

    def __post_init__(self) -> None:
        if (self.text is None) == (self.message_id is None):
            raise ValueError("Payload: indica `text` o `message_id`, no ambos ni ninguno")
        if self.message_id is not None and self.from_chat_id is None:
            raise ValueError("Payload: falta `from_chat_id`")


@dataclass
class Report:
    ok: int = 0
    failed: list[tuple[int, str]] = field(default_factory=list)  # (chat_id, motivo)

    @property
    def total(self) -> int:
        return self.ok + len(self.failed)


async def send_one(bot: Bot, chat_id: int, payload: Payload) -> None:
    if payload.text is not None:
        await bot.send_message(chat_id, payload.text)
    else:
        assert payload.from_chat_id is not None and payload.message_id is not None  # noqa: S101
        await bot.copy_message(chat_id, payload.from_chat_id, payload.message_id)


async def broadcast(
    bot: Bot,
    db: Database,
    chat_ids: Sequence[int],
    payload: Payload,
    *,
    rate: float = DEFAULT_RATE,
) -> Report:
    """Envía a cada chat, uno tras otro y con ritmo. Un fallo no detiene al resto.

    - Grupo del que expulsaron al bot → se marca inactivo.
    - Grupo migrado a supergrupo → se actualiza al nuevo id y se reenvía allí.
    """
    informe = Report()
    pausa = 1.0 / rate if rate > 0 else 0.0
    for i, chat_id in enumerate(dict.fromkeys(chat_ids)):  # sin repetidos, en orden
        if i and pausa:
            await asyncio.sleep(pausa)
        motivo = await _try_send(bot, db, chat_id, payload)
        if motivo is None:
            informe.ok += 1
        else:
            informe.failed.append((chat_id, motivo))
    return informe


async def _try_send(bot: Bot, db: Database, chat_id: int, payload: Payload) -> str | None:
    """None si se envió; si no, el motivo (corto, para el informe)."""
    try:
        await send_one(bot, chat_id, payload)
        return None
    except TelegramMigrateToChat as exc:
        nuevo = exc.migrate_to_chat_id
        await set_active(db, chat_id, False)
        await upsert_chat(db, nuevo, None, "supergroup")
        try:
            await send_one(bot, nuevo, payload)
            return None
        except TelegramAPIError as exc2:
            return f"migrado a {nuevo}, pero falló: {_short(exc2)}"
    except TelegramRetryAfter as exc:  # el guard ya reintentó una vez
        return f"límite de Telegram ({exc.retry_after} s)"
    except (TelegramForbiddenError, TelegramBadRequest) as exc:
        texto = str(exc).lower()
        if isinstance(exc, TelegramForbiddenError) or any(g in texto for g in _GONE):
            await set_active(db, chat_id, False)
            return "el bot ya no puede escribir ahí (desactivado)"
        return _short(exc)
    except (TelegramNetworkError, TelegramAPIError, OSError) as exc:
        return _short(exc)


def _short(exc: BaseException) -> str:
    return str(exc).splitlines()[0][:120] if str(exc) else type(exc).__name__
