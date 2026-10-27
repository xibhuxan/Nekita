"""Feature `images`: imágenes aleatorias con caché, plan B y límite de uso."""

from nekita.core.context import AppContext
from nekita.core.feature import CommandInfo, Feature
from nekita.features.images.router import COMMANDS, ServiceHolder, build_router
from nekita.features.images.service import ImageService

COOLDOWN = 3.0  # segundos por usuario y chat (spec 9)


def build(service: ImageService | None = None) -> Feature:
    """`service` solo se inyecta en las pruebas; en producción se crea al arrancar."""
    holder = ServiceHolder()
    holder.service = service

    async def on_startup(ctx: AppContext) -> None:
        if holder.service is None:
            holder.service = ImageService(ctx.settings.cache_segundos)

    async def on_shutdown(ctx: AppContext) -> None:
        if holder.service is not None:
            await holder.service.close()

    return Feature(
        name="images",
        router=build_router(holder),
        commands=[
            CommandInfo(
                c.name, c.description, category="images", cooldown=COOLDOWN, drop_if_stale=True
            )
            for c in COMMANDS
        ],
        on_startup=on_startup,
        on_shutdown=on_shutdown,
    )
