"""Comandos /neko, /perro, /cangrejo y /moneda."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from nekita.features.images.providers import CAT, COIN, CRAB, DOG, Provider
from nekita.features.images.sender import send_image
from nekita.features.images.service import ImageService

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class ImageCommand:
    name: str
    description: str
    provider: Provider
    sin_imagen: str  # Apéndice A
    error: str  # Apéndice A


COMMANDS = (
    ImageCommand(
        "neko",
        "Imagen aleatoria de un gato",
        CAT,
        "Todos los nekos están escondidos-nya",
        "Error obteniendo imagen de gato-nya",
    ),
    ImageCommand(
        "perro",
        "Imagen aleatoria de un perro",
        DOG,
        "Ahora mismo no veo ningún perrito-nya",
        "Error obteniendo imagen de perro-nya",
    ),
    ImageCommand(
        "cangrejo",
        "Imagen aleatoria de un cangrejo",
        CRAB,
        "Ahora mismo no veo ningún cangrejito-nya",
        "Error obteniendo imagen de cangrejo-nya",
    ),
    ImageCommand(
        "moneda",
        "Imagen aleatoria de una moneda",
        COIN,
        "Ahora mismo no veo ninguna monedita-nya",
        "Error obteniendo imagen de moneda-nya",
    ),
)


class ServiceHolder:
    """El servicio necesita la configuración (TTL), que solo existe al arrancar."""

    def __init__(self) -> None:
        self.service: ImageService | None = None


def build_router(holder: ServiceHolder) -> Router:
    router = Router(name="images")

    def register(cmd: ImageCommand) -> None:
        @router.message(Command(cmd.name))
        async def handler(message: Message) -> None:
            service = holder.service
            if service is None:  # no debería ocurrir: on_startup lo crea antes del polling
                await message.answer(cmd.error)
                return
            try:
                url = await service.next_url(cmd.provider)
                if url is None:
                    await message.answer(cmd.sin_imagen)
                    return
                await send_image(message, url, service.downloader, cmd.provider.domains)
            except Exception:
                log.exception("Error enviando imagen de /%s", cmd.name)
                await message.answer(cmd.error)

    for cmd in COMMANDS:
        register(cmd)
    return router
