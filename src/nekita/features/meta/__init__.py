"""Feature `meta`: salud del bot (y, en la Fase 3, `/stats`)."""

from nekita.core.feature import CommandInfo, Feature
from nekita.features.meta.router import build_router


def build() -> Feature:
    """Cada llamada crea un Router nuevo (aiogram no admite reutilizarlo)."""
    return Feature(
        name="meta",
        router=build_router(),
        commands=[
            CommandInfo("help", "Muestra esta ayuda", category="meta"),
            CommandInfo("health", "Comprueba que el bot está vivo", category="meta"),
        ],
    )
