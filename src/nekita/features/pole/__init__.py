"""Feature `pole`: juegos definidos por datos en `games.toml`."""

from pathlib import Path

from nekita.core.feature import CommandInfo, Feature
from nekita.features.pole.games import GameIndex
from nekita.features.pole.loader import load_games
from nekita.features.pole.router import build_router


def build(games_path: Path | None = None) -> Feature:
    """Lee y valida `games.toml`; si es inválido lanza `GamesConfigError` y el bot no arranca."""
    index = GameIndex(load_games(games_path))
    return Feature(
        name="pole",
        router=build_router(index),
        commands=[
            CommandInfo(g.command, f"Ranking de {g.title}", category="poles") for g in index.games
        ],
    )
