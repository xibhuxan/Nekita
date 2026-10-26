"""Lectura y validación de `games.toml` (spec 4.3.1): error legible y el bot no arranca."""

from __future__ import annotations

import re
import tomllib
from datetime import time
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from nekita.core.feature import COMMAND_RE, FeatureConfigError
from nekita.core.texts import normalize
from nekita.features.pole.games import Game, Position, Window

DEFAULT_PATH = Path(__file__).with_name("games.toml")
_ID_RE = re.compile(r"^[a-z0-9_]{1,32}$")
_HHMM_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")
_GAME_KEYS = {"id", "title", "command", "tz", "window", "position"}
_POS_KEYS = {"prize", "points", "words"}


class GamesConfigError(FeatureConfigError):
    """`games.toml` inválido."""


def _hhmm(value: object, where: str) -> time:
    m = _HHMM_RE.match(value) if isinstance(value, str) else None
    if not m:
        raise GamesConfigError(f"{where}: hora no válida {value!r} (usa HH:MM, p. ej. 22:22)")
    return time(int(m.group(1)), int(m.group(2)))


def _position(raw: Any, where: str, seen: dict[str, str]) -> Position:
    if not isinstance(raw, dict):
        raise GamesConfigError(f"{where}: el puesto debe ser una tabla")
    if extra := set(raw) - _POS_KEYS:
        raise GamesConfigError(f"{where}: claves desconocidas {sorted(extra)}")
    prize, points, words = raw.get("prize"), raw.get("points"), raw.get("words")
    if not isinstance(prize, str) or not prize.strip():
        raise GamesConfigError(f"{where}: falta `prize` (texto del premio)")
    if isinstance(points, bool) or not isinstance(points, int) or points < 0:
        raise GamesConfigError(f"{where}: `points` debe ser un entero ≥ 0 (es {points!r})")
    if not isinstance(words, list) or not words:
        raise GamesConfigError(f"{where}: `words` debe ser una lista no vacía")
    for w in words:
        if not isinstance(w, str) or not normalize(w):
            raise GamesConfigError(f"{where}: palabra vacía o no válida {w!r}")
        clave = normalize(w)
        if clave in seen:
            raise GamesConfigError(f"{where}: la palabra {w!r} ya la usa {seen[clave]}")
        seen[clave] = where
    return Position(prize.strip(), points, tuple(words))


def _window(raw: Any, where: str) -> Window:
    if not isinstance(raw, dict) or set(raw) != {"from", "to"}:
        raise GamesConfigError(f'{where}: `window` debe ser {{ from = "HH:MM", to = "HH:MM" }}')
    start, end = _hhmm(raw["from"], where), _hhmm(raw["to"], where)
    if not start < end:
        raise GamesConfigError(f"{where}: `from` debe ser anterior a `to` (no cruza medianoche)")
    return Window(start, end)


def _game(raw: Any, n: int, seen: dict[str, str]) -> Game:
    if not isinstance(raw, dict):
        raise GamesConfigError(f"[[game]] nº {n}: debe ser una tabla")
    gid = raw.get("id")
    where = f"pole {gid!r}" if isinstance(gid, str) else f"[[game]] nº {n}"
    if extra := set(raw) - _GAME_KEYS:
        raise GamesConfigError(f"{where}: claves desconocidas {sorted(extra)}")
    if not isinstance(gid, str) or not _ID_RE.match(gid):
        raise GamesConfigError(f"{where}: `id` obligatorio, solo [a-z0-9_]")
    title, command, tz = raw.get("title"), raw.get("command"), raw.get("tz")
    if not isinstance(title, str) or not title.strip():
        raise GamesConfigError(f"{where}: falta `title`")
    if not isinstance(command, str) or not COMMAND_RE.match(command):
        raise GamesConfigError(f"{where}: `command` no válido {command!r} (solo [a-z0-9_], ≤ 32)")
    try:
        ZoneInfo(str(tz))
    except Exception as exc:
        raise GamesConfigError(f"{where}: zona horaria no válida {tz!r}") from exc
    window = _window(raw["window"], where) if "window" in raw else None
    puestos = raw.get("position")
    if not isinstance(puestos, list) or not puestos:
        raise GamesConfigError(f"{where}: necesita al menos un [[game.position]]")
    posiciones = tuple(
        _position(p, f"{where}, puesto {i + 1}", seen) for i, p in enumerate(puestos)
    )
    return Game(gid, title.strip(), command, str(tz), posiciones, window)


def parse_games(text: str) -> list[Game]:
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise GamesConfigError(f"no es TOML válido: {exc}") from exc
    raw_games = data.get("game")
    if not isinstance(raw_games, list) or not raw_games:
        raise GamesConfigError("no define ninguna pole ([[game]])")
    seen: dict[str, str] = {}
    games = [_game(g, i + 1, seen) for i, g in enumerate(raw_games)]
    for campo in ("id", "command"):
        valores = [getattr(g, campo) for g in games]
        for v in valores:
            if valores.count(v) > 1:
                raise GamesConfigError(f"`{campo}` repetido entre poles: {v!r}")
    return games


def load_games(path: Path | None = None) -> list[Game]:
    ruta = path or DEFAULT_PATH
    try:
        texto = ruta.read_text(encoding="utf-8")
    except OSError as exc:
        raise GamesConfigError(f"No se pudo leer {ruta}: {exc}") from exc
    try:
        return parse_games(texto)
    except GamesConfigError as exc:
        raise GamesConfigError(f"{ruta.name}: {exc}") from exc
