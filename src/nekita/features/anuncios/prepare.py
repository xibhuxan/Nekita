"""Preparación de un anuncio: vista previa y botones de confirmación."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from nekita.core.broadcast import Payload
from nekita.features.anuncios import service
from nekita.features.anuncios.service import PendingStore

SOLO_PRIVADO = "Los anuncios solo se preparan por privado conmigo, para no enviarlos por error."
CADUCADO = "Ese anuncio ya no existe (caducó o ya se resolvió)."


def keyboard(token: str, n: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=f"✅ Enviar a {n}", callback_data=f"ann:ok:{token}"),
                InlineKeyboardButton(text="❌ Cancelar", callback_data=f"ann:no:{token}"),
            ]
        ]
    )


def payload_from(message: Message, texto: str) -> Payload:
    """Si respondes a un mensaje se copia tal cual (foto, formato, enlaces...)."""
    respondido = message.reply_to_message
    if respondido is not None:
        return Payload(from_chat_id=message.chat.id, message_id=respondido.message_id)
    return Payload(text=service.check_text(texto))


async def prepare(
    message: Message, pending: PendingStore, chat_ids: list[int], payload: Payload, scope: str
) -> None:
    user = message.from_user
    if user is None:
        return
    if not chat_ids:
        await message.answer("No hay grupos activos a los que enviar.")
        return
    if payload.message_id is not None and payload.from_chat_id is not None:
        await message.answer("Vista previa:")
        await message.bot.copy_message(  # type: ignore[union-attr]
            message.chat.id, payload.from_chat_id, payload.message_id
        )
    token = pending.add(user.id, chat_ids, payload, scope)
    cuantos = f"{len(chat_ids)} grupo{'s' if len(chat_ids) != 1 else ''}"
    cuerpo = payload.text if payload.text is not None else "(el mensaje de arriba)"
    await message.answer(
        f"Anuncio para {cuantos}:\n\n{cuerpo}\n\nConfirma en 5 minutos o se descarta.",
        reply_markup=keyboard(token, len(chat_ids)),
    )
