"""Feature `anuncios`: mensajes globales o a grupos concretos (solo admin, solo privado)."""

import asyncio

from nekita.core.context import AppContext
from nekita.core.feature import CommandInfo, Feature
from nekita.features.anuncios.router import build_router

CATEGORIA = "admin"


def build() -> Feature:
    router, tasks = build_router()

    async def esperar_envios(ctx: AppContext) -> None:
        """Al parar, deja terminar los anuncios en curso (con tope)."""
        if tasks:
            await asyncio.wait(set(tasks), timeout=10)

    return Feature(
        name="anuncios",
        router=router,
        commands=[
            CommandInfo("grupos", "Lista los grupos activos", CATEGORIA, admin_only=True),
            CommandInfo("anuncio", "Anuncio a todos los grupos", CATEGORIA, admin_only=True),
            CommandInfo("anuncio_a", "Anuncio a grupos concretos", CATEGORIA, admin_only=True),
        ],
        on_shutdown=esperar_envios,
    )
