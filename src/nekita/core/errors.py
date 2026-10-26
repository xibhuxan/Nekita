"""Errores en handlers: código de referencia corto y respuesta segura (spec 4.6, 9)."""

from __future__ import annotations

import logging
import secrets

from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError
from aiogram.types import Message

from nekita.core.texts import ERROR_COMANDO

log = logging.getLogger(__name__)


def new_ref() -> str:
    return secrets.token_hex(3)  # 6 hex


async def report_failure(message: Message, exc: Exception, *, command: str | None) -> str:
    """Registra el fallo con referencia y, si era un comando, avisa al usuario.

    Nunca propaga: si ni siquiera se puede responder, solo queda el log.
    """
    ref = new_ref()
    donde = f"/{command}" if command else "texto libre"
    log.error(
        "Fallo en %s (chat %s, ref. %s)",
        donde,
        message.chat.id,
        ref,
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    if command:
        try:
            await message.answer(ERROR_COMANDO.format(ref=ref))
        except TelegramForbiddenError:
            log.info("No se pudo avisar del error: el bot ya no puede escribir en el chat")
        except (TelegramAPIError, OSError):
            log.warning("No se pudo enviar el aviso de error (ref. %s)", ref)
    return ref
