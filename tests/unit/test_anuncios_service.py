"""Lógica de anuncios sin Telegram: destinatarios, pendientes e informe."""

from __future__ import annotations

import pytest

from nekita.core.broadcast import Payload, Report
from nekita.core.chats import ChatRow
from nekita.features.anuncios import service
from nekita.features.anuncios.service import AnnouncementError, PendingStore

GRUPOS = [ChatRow(-1, "Alfa", "supergroup"), ChatRow(-2, "Beta", "group"), ChatRow(-3, None, None)]


def test_destinos_por_numero_e_id() -> None:
    destinos, texto = service.parse_targets("1 -3 hola a todos", GRUPOS)
    assert destinos == [-1, -3]
    assert texto == "hola a todos"


def test_destinos_sin_repetidos() -> None:
    destinos, _ = service.parse_targets("2 2 -2 hola", GRUPOS)
    assert destinos == [-2]


@pytest.mark.parametrize("args", ["hola", "", "   "])
def test_sin_destino_falla(args: str) -> None:
    with pytest.raises(AnnouncementError):
        service.parse_targets(args, GRUPOS)


def test_destino_inexistente() -> None:
    with pytest.raises(AnnouncementError, match="nº 9"):
        service.parse_targets("9 hola", GRUPOS)
    with pytest.raises(AnnouncementError, match="-99"):
        service.parse_targets("-99 hola", GRUPOS)


def test_texto_vacio_o_enorme() -> None:
    with pytest.raises(AnnouncementError):
        service.check_text("   ")
    with pytest.raises(AnnouncementError):
        service.check_text("x" * (service.MAX_TEXT + 1))
    assert service.check_text("  hola ") == "hola"


def test_pendiente_un_solo_uso_y_solo_su_admin() -> None:
    store = PendingStore()
    token = store.add(7, [-1], Payload(text="hola"), "all")
    assert store.take(token, 99) is None  # otro usuario no lo roba
    assert store.take(token, 7) is not None
    assert store.take(token, 7) is None  # ya consumido


def test_pendiente_caduca() -> None:
    ahora = [0.0]
    store = PendingStore(clock=lambda: ahora[0])
    token = store.add(7, [-1], Payload(text="hola"), "all")
    ahora[0] = service.PENDING_TTL + 1
    assert store.take(token, 7) is None


def test_pendientes_con_tope() -> None:
    store = PendingStore(max_items=2)
    store.add(7, [-1], Payload(text="a"), "all")
    store.add(7, [-1], Payload(text="b"), "all")
    with pytest.raises(AnnouncementError):
        store.add(7, [-1], Payload(text="c"), "all")


def test_listado_e_informe() -> None:
    assert "1. Alfa (-1)" in service.render_groups(GRUPOS)
    assert "(sin título) -3" in service.render_groups(GRUPOS)
    assert "Todavía no" in service.render_groups([])
    informe = Report(ok=2, failed=[(-2, "sin permiso")])
    texto = service.render_report(informe, {-2: "Beta"})
    assert "2 de 3" in texto
    assert "Beta: sin permiso" in texto


def test_payload_exige_texto_o_mensaje() -> None:
    with pytest.raises(ValueError):
        Payload()
    with pytest.raises(ValueError):
        Payload(text="a", message_id=1, from_chat_id=1)
    with pytest.raises(ValueError):
        Payload(message_id=1)
