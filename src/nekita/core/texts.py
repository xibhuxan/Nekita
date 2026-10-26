"""Textos literales del contrato (Apéndice A) y normalización de texto (spec 4.5)."""

from __future__ import annotations

import re
import unicodedata

NO_PERMISO = "Este comando es solo para el administrador-nya."
ERROR_COMANDO = "Algo ha fallado-nya (ref. {ref})"

_SPACES = re.compile(r"\s+")


def normalize(text: str) -> str:
    """NFD, sin diacríticos, minúsculas y espacios colapsados: clave única de frases."""
    sin_acentos = "".join(
        c for c in unicodedata.normalize("NFD", text) if not unicodedata.combining(c)
    )
    return _SPACES.sub(" ", sin_acentos.casefold()).strip()
