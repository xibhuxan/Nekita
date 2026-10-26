from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from nekita.core import timeutil
from nekita.core.context import AppContext


def build_router() -> Router:
    router = Router(name="info")

    @router.message(Command("hora"))
    async def hora(message: Message, ctx: AppContext) -> None:
        await message.answer(f"Son las: {timeutil.format_time(timeutil.utcnow(), ctx.settings.tz)}")

    @router.message(Command("dia"))
    async def dia(message: Message, ctx: AppContext) -> None:
        await message.answer(f"Hoy es: {timeutil.format_date(timeutil.utcnow(), ctx.settings.tz)}")

    @router.message(Command("id"))
    async def id_(message: Message) -> None:
        await message.answer(f"El ID de este grupo es: {message.chat.id}")

    return router
