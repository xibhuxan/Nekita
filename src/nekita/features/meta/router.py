from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from nekita import __version__
from nekita.core.context import AppContext


def build_router() -> Router:
    router = Router(name="meta")

    @router.message(Command("health"))
    async def health(message: Message) -> None:
        await message.answer(f"🐱 Nekita está viva! v{__version__}")

    @router.message(Command("help"))
    async def help_(message: Message, ctx: AppContext, is_admin: bool) -> None:
        """El texto sale del registro: no hay que mantenerlo a mano."""
        await message.answer(ctx.registry.render_help(is_admin=is_admin))

    return router
