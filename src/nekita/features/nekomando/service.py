"""Nekomandos: frase → respuesta fija (spec 4.5, 7.5, Apéndice B)."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from nekita.core.db import Database
from nekita.core.texts import normalize

log = logging.getLogger(__name__)

DEFAULT_PATH = Path(__file__).parent / "data" / "nekomandos.json"
_HORA_TOKEN = re.compile(r"\{hora:([A-Za-z0-9_+\-/]+)\}")


class NekomandoConfigError(ValueError):
    """El fichero de datos por defecto es inválido: aborta el arranque."""


@dataclass(frozen=True)
class Entry:
    response: str
    group: str | None = None
    label: str | None = None


def load_defaults(path: Path | None = None) -> dict[str, Entry]:
    ruta = path or DEFAULT_PATH
    try:
        raw = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise NekomandoConfigError(f"No se pudo leer {ruta.name}: {exc}") from exc
    if not isinstance(raw, dict):
        raise NekomandoConfigError(f"{ruta.name}: debe ser un objeto frase → datos")
    out: dict[str, Entry] = {}
    for frase, datos in raw.items():
        clave = normalize(str(frase))
        resp = datos.get("respuesta") if isinstance(datos, dict) else None
        if not clave or not isinstance(resp, str) or not resp.strip():
            raise NekomandoConfigError(f"{ruta.name}: entrada no válida {frase!r}")
        if clave in out:
            raise NekomandoConfigError(f"{ruta.name}: la frase {frase!r} está repetida")
        out[clave] = Entry(resp, datos.get("grupo"), datos.get("etiqueta"))
    return out


class Nekomandos:
    def __init__(self, defaults: dict[str, Entry]) -> None:
        self._entries = dict(defaults)
        self._defaults = dict(defaults)

    def __len__(self) -> int:
        return len(self._entries)

    def apply_overrides(self, overrides: dict[str, object]) -> list[str]:
        """Aplica overrides; devuelve las claves rechazadas (vacías o no-texto), sin romper."""
        rechazadas: list[str] = []
        for frase, valor in overrides.items():
            clave = normalize(str(frase))
            if not clave or not isinstance(valor, str) or not valor.strip():
                rechazadas.append(str(frase))
                continue
            previa = self._defaults.get(clave)
            self._entries[clave] = Entry(
                valor, previa.group if previa else None, previa.label if previa else None
            )
        return rechazadas

    def reply(self, text: str, now: datetime) -> str | None:
        entry = self._entries.get(normalize(text))
        return None if entry is None else render(entry.response, now)

    def help_lines(self) -> list[str]:
        """Pie de /help: etiquetas agrupadas, en el orden del fichero de datos."""
        grupos: dict[str, list[str]] = {}
        for entry in self._defaults.values():
            if entry.group and entry.label:
                grupos.setdefault(entry.group, []).append(entry.label)
        return [", ".join(etiquetas) for etiquetas in grupos.values()]


def render(response: str, now: datetime) -> str:
    """Sustituye `{hora:<zona>}` por HH:MM; una zona inválida deja el token y avisa."""

    def sustituir(m: re.Match[str]) -> str:
        try:
            zona = ZoneInfo(m.group(1))
        except (ZoneInfoNotFoundError, ValueError, OSError):
            log.warning("Zona horaria desconocida en un nekomando: %s", m.group(1))
            return m.group(0)
        return now.astimezone(zona).strftime("%H:%M")

    return _HORA_TOKEN.sub(sustituir, response)


async def load_db_overrides(db: Database) -> dict[str, object]:
    rows = await db.fetchall("SELECT phrase, response FROM nekomando_overrides")
    return {str(r[0]): r[1] for r in rows}


async def import_legacy_file(db: Database, data_dir: Path) -> None:
    """Una sola vez: `nekomandos.json` de Node → tabla de overrides; el fichero se renombra."""
    fichero = data_dir / "nekomandos.json"
    if not fichero.is_file():
        return
    try:
        raw = json.loads(fichero.read_text(encoding="utf-8"))
        overrides = raw.get("overrides", {}) if isinstance(raw, dict) else {}
        if not isinstance(overrides, dict):
            raise ValueError("`overrides` debe ser un objeto")
    except (OSError, ValueError) as exc:
        log.warning("No se pudo leer %s: %s", fichero, exc)
        fichero.rename(fichero.with_suffix(".json.corrupto"))
        return
    validos = {
        normalize(str(k)): v
        for k, v in overrides.items()
        if normalize(str(k)) and isinstance(v, str) and v.strip()
    }
    if len(validos) < len(overrides):
        log.warning("Overrides rechazados en %s (clave o valor vacío o no es texto)", fichero)
    async with db.transaction() as conn:
        await conn.executemany(
            "INSERT INTO nekomando_overrides(phrase, response) VALUES(?, ?) "
            "ON CONFLICT(phrase) DO NOTHING",
            list(validos.items()),
        )
    fichero.rename(fichero.with_suffix(".json.importado"))
    log.info("Importados %d overrides de nekomandos", len(validos))
