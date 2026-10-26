"""Modelo de las poles y su índice de palabras (spec 4.3)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import time

from nekita.core.texts import normalize


@dataclass(frozen=True)
class Window:
    start: time
    end: time  # exclusivo: [start, end)

    def contains(self, t: time) -> bool:
        return self.start <= t < self.end


@dataclass(frozen=True)
class Position:
    prize: str
    points: int
    words: tuple[str, ...]  # tal como se escribieron


@dataclass(frozen=True)
class Game:
    id: str
    title: str
    command: str
    tz: str
    positions: tuple[Position, ...]
    window: Window | None = None


class GameIndex:
    """Palabra normalizada → (pole, índice de puesto). Se construye una vez al arrancar."""

    def __init__(self, games: list[Game]) -> None:
        self.games = games
        self._words: dict[str, tuple[Game, int]] = {}
        for game in games:
            for i, pos in enumerate(game.positions):
                for word in pos.words:
                    self._words[normalize(word)] = (game, i)

    def lookup(self, text: str) -> tuple[Game, int] | None:
        return self._words.get(normalize(text))
