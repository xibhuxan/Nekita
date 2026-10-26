from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from nekita import __version__
from nekita.core.chats import list_active
from nekita.core.context import AppContext

TOP = 10


async def render_stats(ctx: AppContext) -> str:
    """Comandos usados y poles concedidas van separados; las poles salen de `pole_wins`."""
    comandos = await ctx.stats.all_commands(ctx.db)
    fila = await ctx.db.fetchone("SELECT COUNT(*) FROM pole_wins")
    poles = int(fila[0]) if fila else 0
    lineas = [
        f"📊 Estadísticas de Nekita v{__version__}-nya!",
        "",
        f"Grupos activos: {len(await list_active(ctx.db))}",
        f"Comandos usados: {sum(n for _, n in comandos)}",
        f"Poles concedidas: {poles}",
    ]
    if comandos:
        lineas += ["", "Comandos más usados:"]
        lineas += [f"  • {nombre}: {n}" for nombre, n in comandos[:TOP]]
    return "\n".join(lineas)


def build_router() -> Router:
    router = Router(name="meta")

    @router.message(Command("health"))
    async def health(message: Message) -> None:
        await message.answer(f"🐱 Nekita está viva! v{__version__}")

    @router.message(Command("stats"))
    async def stats(message: Message, ctx: AppContext) -> None:
        """El middleware ya ha comprobado que es el admin."""
        await message.answer(await render_stats(ctx))

    return router
