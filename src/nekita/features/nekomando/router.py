from aiogram import F, Router
from aiogram.types import Message

from nekita.core import timeutil
from nekita.features.nekomando.service import Nekomandos


def build_router(nekomandos: Nekomandos) -> Router:
    router = Router(name="nekomando")

    @router.message(F.text)
    async def on_text(message: Message) -> None:
        # Los comandos (/x) no son frases: los atienden sus propios handlers.
        if not message.text or message.text.startswith("/"):
            return
        respuesta = nekomandos.reply(message.text, timeutil.utcnow())
        if respuesta is not None:
            await message.answer(respuesta)

    return router
