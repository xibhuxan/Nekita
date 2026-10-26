"""Poles y nekomandos de punta a punta contra la Telegram falsa."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from nekita.config import Settings
from nekita.core.bot import BotRuntime
from nekita.core.context import AppContext
from nekita.core.db import Database
from nekita.core.registry import Registry
from nekita.core.stats import Stats
from nekita.features import info, meta, nekomando, pole, start
from tests.support.fake_telegram import FakeTelegram

MADRID = ZoneInfo("Europe/Madrid")
CANARIAS = ZoneInfo("Atlantic/Canary")
Entorno = tuple[BotRuntime, FakeTelegram]


def ts(y: int, mo: int, d: int, h: int, mi: int, tz: ZoneInfo = MADRID) -> float:
    return datetime(y, mo, d, h, mi, tzinfo=tz).timestamp()


@pytest.fixture
async def entorno(db: Database, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[Entorno]:
    monkeypatch.setenv("NEKITA_TOKEN", "123456:" + "A" * 35)
    feats = [start.build(), info.build(), meta.build(), pole.build(), nekomando.build()]
    ctx = AppContext(Settings(), db, Stats(), Registry(feats))
    fake = FakeTelegram()
    rt = BotRuntime(ctx, feats, session=fake, retry_delay=0)
    await rt.start()
    yield rt, fake
    await rt.shutdown()


async def test_pole_peninsular_cuatro_puestos_en_orden(entorno: Entorno) -> None:
    _, fake = entorno
    t = ts(2026, 1, 15, 10, 0)
    for i, palabra in enumerate(["oro", "plata", "bronce", "aluminio"]):
        fake.feed_text(palabra, user_id=100 + i, username=f"u{i}", date=t + i)
    textos = await fake.wait_for_sent(4)
    assert textos == [
        "¡Enhorabuena u0! Has ganado la pole-nya",
        "¡Enhorabuena u1! Has ganado la plata-nya",
        "¡Enhorabuena u2! Has ganado el bronce-nya",
        "¡Enhorabuena u3! Has ganado el aluminio-nya",
    ]
    fake.feed_text("/pole")
    ranking = (await fake.wait_for_sent(5))[-1]
    assert ranking.index("u0: 4 pts") < ranking.index("u1: 3 pts") < ranking.index("u3: 1 pts")


async def test_plata_sin_oro_no_puntua_y_mismo_usuario_no_repite(entorno: Entorno) -> None:
    _, fake = entorno
    t = ts(2026, 1, 15, 10, 0)
    fake.feed_text("plata", user_id=1, date=t)  # aún no hay oro
    fake.feed_text("oro", user_id=1, date=t + 1)
    fake.feed_text("plata", user_id=1, date=t + 2)  # ya ganó hoy
    fake.feed_text("plata", user_id=2, date=t + 3)
    textos = await fake.wait_for_sent(2)
    await asyncio.sleep(0.1)
    assert fake.sent_texts() == textos
    assert "la pole-nya" in textos[0] and "la plata-nya" in textos[1]


async def test_pole_de_un_puesto_respeta_su_franja_y_cae_a_la_frase(entorno: Entorno) -> None:
    _, fake = entorno
    fake.feed_text("pole patitos", user_id=1, date=ts(2026, 1, 15, 22, 21))  # antes de la franja
    fake.feed_text("pole patitos", user_id=1, date=ts(2026, 1, 15, 22, 22))
    fake.feed_text("pole patitos", user_id=2, date=ts(2026, 1, 15, 22, 22) + 1)  # llega tarde
    textos = await fake.wait_for_sent(3)
    assert textos[0] == "A las 22:22, tú puedes-nya!"  # nekomando, no concede
    assert textos[1].startswith("¡Enhorabuena ana! Has ganado la pole patitos")
    assert textos[2] == "A las 22:22, tú puedes-nya!"


async def test_el_dia_de_cada_pole_usa_su_zona(entorno: Entorno) -> None:
    _, fake = entorno
    # 00:30 en Canarias = 01:30 en Madrid: para `canaria` ya es otro día que a las 23:30.
    fake.feed_text("pole canaria", user_id=1, date=ts(2026, 1, 15, 23, 30, CANARIAS))
    fake.feed_text("pole canaria", user_id=2, date=ts(2026, 1, 16, 0, 30, CANARIAS))
    assert len(await fake.wait_for_sent(2)) == 2


async def test_polas_solo_en_grupos(entorno: Entorno) -> None:
    _, fake = entorno
    fake.feed_text("oro", chat_type="private", chat_id=5, date=ts(2026, 1, 15, 10, 0))
    await asyncio.sleep(0.2)
    assert fake.sent_texts() == []


async def test_concurrencia_50_oros_dan_un_solo_ganador(entorno: Entorno) -> None:
    _, fake = entorno
    t = ts(2026, 1, 15, 10, 0)
    for uid in range(1, 51):
        fake.feed_text("oro", user_id=uid, username=f"u{uid}", date=t)
    await fake.wait_for_sent(1)
    await asyncio.sleep(0.3)
    assert len(fake.sent_texts()) == 1


async def test_ranking_vacio_y_grupos_independientes(entorno: Entorno) -> None:
    _, fake = entorno
    fake.feed_text("oro", chat_id=-1, date=ts(2026, 1, 15, 10, 0))
    fake.feed_text("oro", chat_id=-2, user_id=9, username="otro", date=ts(2026, 1, 15, 10, 0))
    fake.feed_text("/pole_canaria", chat_id=-1)
    textos = await fake.wait_for_sent(3)
    assert sum("Enhorabuena" in t for t in textos) == 2
    assert "No hay puntuaciones de pole canaria" in textos[-1]


async def test_stats_cuenta_poles_desde_la_bd(entorno: Entorno) -> None:
    rt, fake = entorno
    fake.feed_text("oro", date=ts(2026, 1, 15, 10, 0))
    await fake.wait_for_sent(1)
    fila = await rt.ctx.db.fetchone("SELECT COUNT(*) FROM pole_wins")
    assert fila == (1,)


async def test_nekomandos_horas_y_normalizacion(entorno: Entorno) -> None:
    _, fake = entorno
    fake.feed_text("  HORA   China ")
    fake.feed_text("Buenos DÍAS")
    fake.feed_text("algo que no existe")
    textos = await fake.wait_for_sent(2)
    assert textos[0].startswith("En China son las: ")
    assert textos[0][-5:-3].isdigit() and textos[0][-3] == ":"
    assert textos[1] == "Buenos días para ti también."
    await asyncio.sleep(0.1)
    assert len(fake.sent_texts()) == 2


async def test_help_lista_poles_y_frases(entorno: Entorno) -> None:
    _, fake = entorno
    fake.feed_text("/help")
    texto = (await fake.wait_for_sent(1))[0]
    assert "/pole_patitos_canarias" in texto
    assert "poles" in texto
