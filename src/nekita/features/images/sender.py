"""Envío de una imagen con plan B (descargar y subir) y plan C (documento)."""

from __future__ import annotations

import logging
import posixpath
from typing import Literal
from urllib.parse import urlsplit

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import BufferedInputFile, Message

from nekita.features.images.download import Downloader

log = logging.getLogger(__name__)

Kind = Literal["animation", "video", "photo"]


def media_kind(url: str) -> Kind:
    path = urlsplit(url).path.lower()
    if path.endswith(".gif"):
        return "animation"
    if path.endswith((".mp4", ".webm")):
        return "video"
    return "photo"


async def _send(message: Message, kind: Kind, media: str | BufferedInputFile) -> None:
    if kind == "animation":
        await message.answer_animation(media)
    elif kind == "video":
        await message.answer_video(media)
    else:
        await message.answer_photo(media)


async def send_image(
    message: Message, url: str, downloader: Downloader, domains: tuple[str, ...]
) -> None:
    kind = media_kind(url)
    try:
        await _send(message, kind, url)
        return
    except TelegramBadRequest as exc:  # Telegram no pudo bajar la URL
        log.info("Telegram rechazó la URL (%s); plan B: descargar y subir", exc.message)
    datos = await downloader.fetch(url, domains)
    nombre = posixpath.basename(urlsplit(url).path) or "imagen.jpg"
    fichero = BufferedInputFile(datos, filename=nombre)
    try:
        await _send(message, kind, fichero)
    except TelegramBadRequest:
        if kind != "photo":  # animaciones y vídeos no tienen plan C
            raise
        log.info("Foto rechazada al subirla; se envía como documento")
        await message.answer_document(fichero)
