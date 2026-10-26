"""Flujo completo del bot contra una Telegram falsa (sin red)."""

from __future__ import annotations

import asyncio
import time

import pytest
from aiogram.exceptions import TelegramConflictError, TelegramUnauthorizedError
from aiogram.methods import GetMe, GetUpdates, SetMyCommands

from nekita import app
from nekita.config import Settings
from nekita.core.bot import BotRuntime, BotStartupError
from nekita.core.context import AppContext
from nekita.core.db import Database
from nekita.core.registry import Registry
from nekita.core.stats import Stats
from tests.integration.conftest import ADMIN, Entorno, make_features
from tests.support.fake_telegram import BOT_USERNAME, FakeTelegram


async def test_responde_y_publica_menu(entorno: Entorno) -> None:
    rt, fake, _ = entorno
    fake.feed_text("/eco")
    assert await fake.wait_for_sent(1) == ["eco"]
    menus = [c for c in fake.calls if isinstance(c, SetMyCommands)]
    publicados = {c.command for c in menus[0].commands}
    assert publicados == {"eco", "lento", "rapido", "roto", "viejo", "health", "help"}
    assert "secreto" not in publicados
    assert rt.ctx.stats.pending == 1  # contado tras el éxito


async def test_comando_de_otro_bot_se_ignora(entorno: Entorno) -> None:
    _, fake, log = entorno
    fake.feed_text("/eco@otro_bot")
    fake.feed_text(f"/eco@{BOT_USERNAME}")
    assert await fake.wait_for_sent(1) == ["eco"]
    assert log == ["eco"]


async def test_error_responde_con_referencia_y_no_cuenta(entorno: Entorno) -> None:
    rt, fake, _ = entorno
    fake.feed_text("/roto")
    (texto,) = await fake.wait_for_sent(1)
    assert texto.startswith("Algo ha fallado-nya (ref. ")
    assert rt.ctx.stats.pending == 0


async def test_admin(entorno: Entorno) -> None:
    _, fake, _ = entorno
    fake.feed_text("/secreto", user_id=99)
    fake.feed_text("/secreto", user_id=ADMIN)
    assert await fake.wait_for_sent(2) == [
        "Este comando es solo para el administrador-nya.",
        "secreto",
    ]


async def test_updates_viejos_solo_se_descartan_si_procede(entorno: Entorno) -> None:
    _, fake, _ = entorno
    antiguo = time.time() - 300
    fake.feed_text("/viejo", date=antiguo)  # drop_if_stale
    fake.feed_text("/eco", date=antiguo)  # no caduca
    assert await fake.wait_for_sent(1) == ["eco"]
    await asyncio.sleep(0.1)
    assert fake.sent_texts() == ["eco"]


async def test_orden_por_chat_y_paralelo_entre_chats(entorno: Entorno) -> None:
    _, fake, log = entorno
    fake.feed_text("/lento", chat_id=-1)
    fake.feed_text("/rapido", chat_id=-1)  # mismo chat: espera a /lento
    fake.feed_text("/rapido", chat_id=-2)  # otro chat: pasa de largo
    await fake.wait_for_sent(3)
    assert log.index("rapido") < log.index("lento-out")  # el de otro chat no esperó
    assert log[-1] == "rapido"  # el del mismo chat fue después de /lento


async def test_token_rechazado_en_arranque(db: Database, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEKITA_TOKEN", "123456:" + "A" * 35)
    feats = make_features([])
    fake = FakeTelegram()
    fake.errors[GetMe] = [TelegramUnauthorizedError(GetMe(), "Unauthorized")]
    rt = BotRuntime(AppContext(Settings(), db, Stats(), Registry(feats)), feats, session=fake)
    with pytest.raises(BotStartupError, match="rechazado el token"):
        await rt.start()


async def test_conflicto_409_repetido_es_fatal(entorno: Entorno) -> None:
    rt, fake, _ = entorno
    fake.errors[GetUpdates] = [TelegramConflictError(GetUpdates(), "Conflict") for _ in range(5)]
    assert await asyncio.wait_for(rt.wait(asyncio.Event()), 15) == 1
    assert "409" in rt.health.fatal_reason


async def test_run_completo_sale_con_0(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEKITA_TOKEN", "123456:" + "A" * 35)
    stop = asyncio.Event()
    fake = FakeTelegram()
    tarea = asyncio.create_task(app.run(Settings(), stop, session=fake))
    fake.feed_text("/health")
    (texto,) = await fake.wait_for_sent(1)
    assert "Nekita está viva" in texto
    stop.set()
    assert await asyncio.wait_for(tarea, 15) == 0


async def test_help_se_genera_del_registro(entorno: Entorno) -> None:
    _, fake, _ = entorno
    fake.feed_text("/help", user_id=99)
    fake.feed_text("/help", user_id=ADMIN)
    normal, admin = await fake.wait_for_sent(2)
    assert "/eco — Eco" in normal
    assert "/secreto" not in normal
    assert "/secreto" in admin
