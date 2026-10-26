"""Flujo de anuncios contra una Telegram falsa: preparar → confirmar → enviar."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import pytest
from aiogram.exceptions import TelegramForbiddenError
from aiogram.methods import SendMessage

from nekita.config import Settings
from nekita.core.bot import BotRuntime
from nekita.core.chats import list_active, upsert_chat
from nekita.core.context import AppContext
from nekita.core.db import Database
from nekita.core.registry import Registry
from nekita.core.stats import Stats
from nekita.features import anuncios
from tests.support.fake_telegram import FakeTelegram

ADMIN = 7
Entorno = tuple[BotRuntime, FakeTelegram]


@pytest.fixture
async def entorno(db: Database, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[Entorno]:
    monkeypatch.setenv("NEKITA_TOKEN", "123456:" + "A" * 35)
    monkeypatch.setenv("NEKITA_MASTER_ID", str(ADMIN))
    await upsert_chat(db, -1, "Alfa", "supergroup")
    await upsert_chat(db, -2, "Beta", "supergroup")
    feats = [anuncios.build()]
    ctx = AppContext(Settings(), db, Stats(), Registry(feats))
    fake = FakeTelegram()
    rt = BotRuntime(ctx, feats, session=fake, retry_delay=0)
    await rt.start()
    yield rt, fake
    await rt.shutdown()


async def esperar(condicion: object, timeout: float = 3.0) -> None:
    async with asyncio.timeout(timeout):
        while not condicion():  # type: ignore[operator]
            await asyncio.sleep(0.01)


async def test_anuncio_global_con_confirmacion(entorno: Entorno) -> None:
    rt, fake = entorno
    fake.feed_text(
        "/anuncio Mantenimiento mañana", chat_id=ADMIN, user_id=ADMIN, chat_type="private"
    )
    await esperar(lambda: fake.button_data())
    assert fake.sent_to(-1) == [] and fake.sent_to(-2) == []  # aún nada enviado
    ok, _ = fake.button_data()
    fake.feed_callback(ok, user_id=ADMIN)
    await esperar(lambda: fake.sent_to(-1) and fake.sent_to(-2))
    assert fake.sent_to(-1) == ["Mantenimiento mañana"]
    await esperar(lambda: any("enviado a 2 de 2" in t for t in fake.sent_to(ADMIN)))
    fila = await rt.ctx.db.fetchone("SELECT scope, total, ok FROM announcements")
    assert fila == ("all", 2, 2)


async def test_anuncio_a_un_grupo(entorno: Entorno) -> None:
    _, fake = entorno
    fake.feed_text("/anuncio_a 2 Solo Beta", chat_id=ADMIN, user_id=ADMIN, chat_type="private")
    await esperar(lambda: fake.button_data())
    fake.feed_callback(fake.button_data()[0], user_id=ADMIN)
    await esperar(lambda: fake.sent_to(-2))
    assert fake.sent_to(-2) == ["Solo Beta"]
    assert fake.sent_to(-1) == []


async def test_cancelar_no_envia(entorno: Entorno) -> None:
    _, fake = entorno
    fake.feed_text("/anuncio Hola", chat_id=ADMIN, user_id=ADMIN, chat_type="private")
    await esperar(lambda: fake.button_data())
    fake.feed_callback(fake.button_data()[1], user_id=ADMIN)
    await esperar(lambda: "Anuncio cancelado." in fake.sent_to(ADMIN))
    assert fake.sent_to(-1) == []


async def test_no_admin_no_puede(entorno: Entorno) -> None:
    _, fake = entorno
    fake.feed_text("/anuncio Hola", chat_id=5, user_id=5, chat_type="private")
    assert await fake.wait_for_sent(1) == ["Este comando es solo para el administrador-nya."]
    assert fake.button_data() == []


async def test_no_se_prepara_en_grupo(entorno: Entorno) -> None:
    _, fake = entorno
    fake.feed_text("/anuncio Hola", chat_id=-1, user_id=ADMIN)
    (texto,) = await fake.wait_for_sent(1)
    assert "por privado" in texto


async def test_boton_de_otro_usuario_se_rechaza(entorno: Entorno) -> None:
    _, fake = entorno
    fake.feed_text("/anuncio Hola", chat_id=ADMIN, user_id=ADMIN, chat_type="private")
    await esperar(lambda: fake.button_data())
    fake.feed_callback(fake.button_data()[0], user_id=999)
    await asyncio.sleep(0.3)
    assert fake.sent_to(-1) == []


async def test_boton_no_se_puede_usar_dos_veces(entorno: Entorno) -> None:
    _, fake = entorno
    fake.feed_text("/anuncio Hola", chat_id=ADMIN, user_id=ADMIN, chat_type="private")
    await esperar(lambda: fake.button_data())
    ok = fake.button_data()[0]
    fake.feed_callback(ok, user_id=ADMIN)
    fake.feed_callback(ok, user_id=ADMIN)
    await esperar(lambda: fake.sent_to(-1))
    await asyncio.sleep(0.3)
    assert fake.sent_to(-1) == ["Hola"]


async def test_grupo_que_expulso_al_bot_se_desactiva_y_el_resto_recibe(entorno: Entorno) -> None:
    rt, fake = entorno
    fake.chat_errors[-1] = TelegramForbiddenError(
        SendMessage(chat_id=-1, text="x"), "Forbidden: bot was kicked"
    )
    fake.feed_text("/anuncio Hola", chat_id=ADMIN, user_id=ADMIN, chat_type="private")
    await esperar(lambda: fake.button_data())
    fake.feed_callback(fake.button_data()[0], user_id=ADMIN)
    await esperar(lambda: any("enviado a" in t for t in fake.sent_to(ADMIN)))
    assert fake.sent_to(-2) == ["Hola"]
    assert {g.chat_id for g in await list_active(rt.ctx.db)} == {-2}
    assert any("1 de 2" in t for t in fake.sent_to(ADMIN))
