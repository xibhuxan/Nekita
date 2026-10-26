"""Feature `meta`: salud del bot y estadísticas (solo admin)."""

from nekita.core.feature import CommandInfo, Feature
from nekita.features.meta.router import build_router


def build() -> Feature:
    """Cada llamada crea un Router nuevo (aiogram no admite reutilizarlo)."""
    return Feature(
        name="meta",
        router=build_router(),
        commands=[
            CommandInfo("health", "Comprueba que el bot está vivo", category="meta"),
            CommandInfo(
                "stats", "Estadísticas del bot (solo admin)", category="meta", admin_only=True
            ),
        ],
    )
