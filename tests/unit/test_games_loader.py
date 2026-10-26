"""Validación de games.toml: errores legibles en el arranque (spec 4.3.1)."""

from __future__ import annotations

from pathlib import Path

import pytest

from nekita.features.pole.games import GameIndex
from nekita.features.pole.loader import GamesConfigError, load_games

BASE = """
[[game]]
id = "{id}"
title = "{id}"
command = "{cmd}"
tz = "{tz}"
{extra}
  [[game.position]]
  prize = "x"
  points = 1
  words = {words}
"""


def toml(tmp_path: Path, *bloques: str) -> Path:
    p = tmp_path / "games.toml"
    p.write_text("\n".join(bloques), encoding="utf-8")
    return p


def bloque(
    id: str = "a",
    cmd: str = "a",
    tz: str = "Europe/Madrid",
    words: str = '["a"]',
    extra: str = "",
) -> str:
    return BASE.format(id=id, cmd=cmd, tz=tz, words=words, extra=extra)


def test_games_toml_incluido_es_valido_y_tiene_todas_las_poles() -> None:
    games = load_games()
    ids = {g.id for g in games}
    assert {"pole", "canaria", "andaluza", "palitos", "patitos", "cuack"} <= ids
    peninsular = next(g for g in games if g.id == "pole")
    assert [p.points for p in peninsular.positions] == [4, 3, 2, 1]
    index = GameIndex(games)
    assert index.lookup("  ORO ") is not None
    assert index.lookup("Aluminio") is not None


def test_palabra_repetida_entre_poles(tmp_path: Path) -> None:
    ruta = toml(tmp_path, bloque("a", "a", words='["x"]'), bloque("b", "b", words='["X"]'))
    with pytest.raises(GamesConfigError, match="ya la usa"):
        GameIndex(load_games(ruta))


def test_zona_invalida(tmp_path: Path) -> None:
    with pytest.raises(GamesConfigError, match="zona"):
        load_games(toml(tmp_path, bloque(tz="Mordor/Orodruin")))


def test_comando_repetido(tmp_path: Path) -> None:
    ruta = toml(tmp_path, bloque("a", "z", words='["a"]'), bloque("b", "z", words='["b"]'))
    with pytest.raises(GamesConfigError, match="z"):
        load_games(ruta)


def test_franja_invalida(tmp_path: Path) -> None:
    extra = 'window = { from = "25:00", to = "26:00" }'
    with pytest.raises(GamesConfigError):
        load_games(toml(tmp_path, bloque(extra=extra)))


def test_fichero_inexistente_o_roto(tmp_path: Path) -> None:
    with pytest.raises(GamesConfigError):
        load_games(tmp_path / "no_existe.toml")
    (tmp_path / "roto.toml").write_text("[[game", encoding="utf-8")
    with pytest.raises(GamesConfigError):
        load_games(tmp_path / "roto.toml")
