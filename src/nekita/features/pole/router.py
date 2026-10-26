"""Poles: palabras de texto libre y un comando de ranking por pole (spec 4.3)."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.filters import Command
from aiogram.types import Message, User

from nekita.core.chats import GROUP_TYPES
from nekita.core.context import AppContext
from nekita.features.pole import repo
from nekita.features.pole.games import Game, GameIndex

MEDALLAS = ("🥇", "🥈", "🥉")


def display_name(user: User) -> str:
    """`username` sin @ o, si no hay, el nombre de pila."""
    return user.username or user.first_name


def render_ranking(game: Game, rows: list[repo.Row]) -> str:
    if not rows:
        return f"No hay puntuaciones de {game.title} aún-nya. ¡Sé el primero!"
    lineas = [f"Puntuaciones de {game.title}-nya!", ""]
    for i, r in enumerate(rows):
        marca = MEDALLAS[i] if i < len(MEDALLAS) else f"#{i + 1}"
        lineas.append(f"{marca} {r.name}: {r.points} pts")
    return "\n".join(lineas)


def build_router(index: GameIndex) -> Router:
    router = Router(name="pole")

    @router.message(F.text)
    async def on_text(message: Message, ctx: AppContext) -> None:
        user = message.from_user
        hit = index.lookup(message.text or "")
        if hit is None or user is None or user.is_bot or message.chat.type not in GROUP_TYPES:
            raise SkipHandler  # sigue hacia los nekomandos
        game, position = hit
        ganada = await repo.try_win(
            ctx.db,
            game,
            position,
            chat_id=message.chat.id,
            user_id=user.id,
            display=display_name(user),
            when=message.date,
        )
        if not ganada:
            raise SkipHandler  # p. ej. "pole patitos" fuera de hora: responde el nekomando
        premio = game.positions[position].prize
        await message.answer(f"¡Enhorabuena {display_name(user)}! Has ganado {premio}-nya")

    for game in index.games:
        _add_ranking(router, game)
    return router


def _add_ranking(router: Router, game: Game) -> None:
    @router.message(Command(game.command))
    async def ranking(message: Message, ctx: AppContext) -> None:
        rows = await repo.top(ctx.db, game.id, message.chat.id)
        await message.answer(render_ranking(game, rows))
