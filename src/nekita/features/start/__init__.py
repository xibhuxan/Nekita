"""Feature `start`: bienvenida, saludo y ayuda generada desde el registro."""

from nekita.core.feature import CommandInfo, Feature
from nekita.features.start.router import build_router


def build() -> Feature:
    """Cada llamada crea un Router nuevo (aiogram no admite reutilizarlo)."""
    return Feature(
        name="start",
        router=build_router(),
        commands=[
            CommandInfo("start", "Mensaje de bienvenida", category="start"),
            CommandInfo("hola", "Saluda al usuario", category="start"),
            CommandInfo("help", "Lista de comandos disponibles", category="start"),
        ],
    )
