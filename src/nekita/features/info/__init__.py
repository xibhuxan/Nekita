"""Feature `info`: hora, fecha e id del chat."""

from nekita.core.feature import CommandInfo, Feature
from nekita.features.info.router import build_router


def build() -> Feature:
    return Feature(
        name="info",
        router=build_router(),
        commands=[
            CommandInfo("hora", "Hora actual en España", category="info"),
            CommandInfo("dia", "Fecha actual", category="info"),
            CommandInfo("id", "ID del chat actual", category="info"),
        ],
    )
