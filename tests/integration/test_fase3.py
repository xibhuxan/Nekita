"""Comandos sencillos de la Fase 3 contra la Telegram falsa."""

from __future__ import annotations

import re

from nekita.features.start.router import BIENVENIDA
from tests.integration.conftest import ADMIN, Entorno


async def test_start_y_hola(entorno: Entorno) -> None:
    _, fake, _ = entorno
    fake.feed_text("/start")
    fake.feed_text("/hola", username="ana")
    fake.feed_text("/hola", username=None, first_name="Luis", user_id=43)
    assert await fake.wait_for_sent(3) == [BIENVENIDA, "Hola, @ana-nya.", "Hola, Luis-nya."]


async def test_hora_dia_e_id(entorno: Entorno) -> None:
    _, fake, _ = entorno
    fake.feed_text("/hora", chat_id=-555)
    fake.feed_text("/dia", chat_id=-555)
    fake.feed_text("/id", chat_id=-555)
    hora, dia, ident = await fake.wait_for_sent(3)
    assert re.fullmatch(r"Son las: \d\d:\d\d:\d\d", hora)
    assert re.fullmatch(r"Hoy es: \d\d-\d\d-\d{4}", dia)
    assert ident == "El ID de este grupo es: -555"


async def test_stats_solo_admin_y_separa_comandos_de_poles(entorno: Entorno) -> None:
    rt, fake, _ = entorno
    fake.feed_text("/eco")
    await fake.wait_for_sent(1)
    fake.feed_text("/stats", user_id=99)
    fake.feed_text("/stats", user_id=ADMIN)
    _, no_admin, stats = await fake.wait_for_sent(3)
    assert no_admin == "Este comando es solo para el administrador-nya."
    assert "Comandos usados:" in stats
    assert "Poles concedidas: 0" in stats
    assert "eco: 1" in stats
    assert rt.ctx.settings.admin_id == ADMIN


async def test_stats_no_se_publica_en_el_menu_pero_help_si_la_muestra_al_admin(
    entorno: Entorno,
) -> None:
    _, fake, _ = entorno
    fake.feed_text("/help", user_id=99)
    fake.feed_text("/help", user_id=ADMIN)
    normal, admin = await fake.wait_for_sent(2)
    assert "/stats" not in normal
    assert "/stats" in admin
