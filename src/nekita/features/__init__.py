"""Lista explícita de features (spec 6.1). Añadir una función = una línea aquí."""

from __future__ import annotations

from nekita.core.feature import Feature
from nekita.features import anuncios, meta


def load_features() -> list[Feature]:
    return [
        meta.build(),
        anuncios.build(),
    ]
