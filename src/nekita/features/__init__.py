"""Lista explícita de features (spec 6.1). Añadir una función = una línea aquí."""

from __future__ import annotations

from nekita.core.feature import Feature
from nekita.features import anuncios, images, info, meta, nekomando, pole, start


def load_features() -> list[Feature]:
    return [
        start.build(),
        info.build(),
        meta.build(),
        images.build(),
        anuncios.build(),
        pole.build(),  # antes que nekomando: una pole fallida cae a su frase
        nekomando.build(),
    ]
