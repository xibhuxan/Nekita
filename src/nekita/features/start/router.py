from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, User

from nekita.core.context import AppContext

BIENVENIDA = (
    "Puedo hacer muchas cosas por tu grupo. Soy una sustituta definitiva para que podáis "
    "hacer poles, enviar nekos a tu amigo favorito y mucho más. "
    "Pregúntame qué puedo hacer con /help"
)


def display_name(user: User | None) -> str:
    """`@username` o, si no hay, el nombre de pila (como en la versión Node)."""
    if user is None:
        return "desconocido"
    return f"@{user.username}" if user.username else user.first_name


def build_router() -> Router:
    router = Router(name="start")

    @router.message(Command("start"))
    async def start(message: Message) -> None:
        await message.answer(BIENVENIDA)

    @router.message(Command("hola"))
    async def hola(message: Message) -> None:
        await message.answer(f"Hola, {display_name(message.from_user)}-nya.")

    @router.message(Command("help"))
    async def help_(message: Message, ctx: AppContext, is_admin: bool) -> None:
        """El texto sale del registro: no hay que mantenerlo a mano."""
        await message.answer(ctx.registry.render_help(is_admin=is_admin))

    return router
