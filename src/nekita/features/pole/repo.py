"""SQL de las poles (spec 7.3): la restricción de la BD es la garantía, no el código."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime

from nekita.core import timeutil
from nekita.core.db import Database, utc_now_iso
from nekita.features.pole.games import Game

TOP_N = 10


class _NoWin(Exception):
    """El puesto no corresponde (otro se adelantó o aún no toca): deshace la transacción."""


@dataclass(frozen=True)
class Row:
    user_id: int
    name: str
    points: int


def day_key(game: Game, when: datetime) -> str | None:
    """Fecha local (en la zona de la pole) o None si está fuera de su franja."""
    local = timeutil.local(when, game.tz)
    if game.window is not None and not game.window.contains(local.time()):
        return None
    return local.date().isoformat()


async def try_win(
    db: Database,
    game: Game,
    position: int,
    *,
    chat_id: int,
    user_id: int,
    display: str,
    when: datetime,
) -> bool:
    """Intenta ganar el puesto `position` (0 = primero). True solo si se concede."""
    key = day_key(game, when)
    if key is None:
        return False
    puntos = game.positions[position].points
    won_at = when.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        async with db.transaction() as conn:
            cur = await conn.execute(
                "SELECT COUNT(*) FROM pole_wins WHERE chat_id = ? AND game_id = ? AND day_key = ?",
                (chat_id, game.id, key),
            )
            fila = await cur.fetchone()
            if fila is None or int(fila[0]) != position:
                raise _NoWin
            await conn.execute(
                "INSERT INTO users(user_id, display, updated_at) VALUES(?, ?, ?) "
                "ON CONFLICT(user_id) DO UPDATE SET display = excluded.display, "
                "updated_at = excluded.updated_at",
                (user_id, display, utc_now_iso()),
            )
            await conn.execute(
                "INSERT INTO pole_wins(chat_id, game_id, day_key, position, user_id, points, "
                "won_at) VALUES(?, ?, ?, ?, ?, ?, ?)",
                (chat_id, game.id, key, position, user_id, puntos, won_at),
            )
            await _claim_legacy(conn, chat_id, game.id, user_id, display)
    except (_NoWin, sqlite3.IntegrityError):
        return False  # ya ganó hoy, otro se adelantó o no toca este puesto
    return True


async def _claim_legacy(conn: object, chat_id: int, game_id: str, user_id: int, name: str) -> None:
    """Si había puntos de Node v1 guardados con su nombre, pasan a su usuario."""
    cur = await conn.execute(  # type: ignore[attr-defined]
        "SELECT points FROM pole_legacy WHERE chat_id = ? AND game_id = ? "
        "AND name = ? COLLATE NOCASE",
        (chat_id, game_id, name),
    )
    fila = await cur.fetchone()
    if fila is None:
        return
    await conn.execute(  # type: ignore[attr-defined]
        "INSERT INTO pole_adjust(chat_id, game_id, user_id, points) VALUES(?, ?, ?, ?) "
        "ON CONFLICT(chat_id, game_id, user_id) DO UPDATE SET points = points + excluded.points",
        (chat_id, game_id, user_id, int(fila[0])),
    )
    await conn.execute(  # type: ignore[attr-defined]
        "DELETE FROM pole_legacy WHERE chat_id = ? AND game_id = ? AND name = ? COLLATE NOCASE",
        (chat_id, game_id, name),
    )


async def top(db: Database, game_id: str, chat_id: int, limit: int = TOP_N) -> list[Row]:
    """Ranking: puntos desc, nombre alfabético sin mayúsculas/acentos de más, id estable."""
    rows = await db.fetchall(
        "SELECT u.user_id, u.display, SUM(t.pts) FROM ("
        " SELECT user_id, SUM(points) AS pts FROM pole_wins"
        "  WHERE chat_id = ? AND game_id = ? GROUP BY user_id"
        " UNION ALL"
        " SELECT user_id, points FROM pole_adjust WHERE chat_id = ? AND game_id = ?"
        ") t JOIN users u ON u.user_id = t.user_id GROUP BY u.user_id, u.display",
        (chat_id, game_id, chat_id, game_id),
    )
    legado = await db.fetchall(
        "SELECT name, points FROM pole_legacy WHERE chat_id = ? AND game_id = ?",
        (chat_id, game_id),
    )
    todos = [Row(int(r[0]), str(r[1]), int(r[2])) for r in rows]
    todos += [Row(0, str(r[0]), int(r[1])) for r in legado]  # sin reclamar: sin usuario
    todos = [r for r in todos if r.points > 0]
    todos.sort(key=lambda r: (-r.points, r.name.casefold(), r.user_id))
    return todos[:limit]


async def total_wins(db: Database) -> int:
    """Poles concedidas en total (fuente de `/stats`): no puede desfasarse de los puntos."""
    fila = await db.fetchone("SELECT COUNT(*) FROM pole_wins")
    return int(fila[0]) if fila else 0
