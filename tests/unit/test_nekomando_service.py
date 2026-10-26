"""Servicio de nekomandos: datos, overrides, tokens de hora e importación de Node."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

import pytest

from nekita.core.db import Database
from nekita.features.nekomando import service
from nekita.features.nekomando.service import Entry, NekomandoConfigError, Nekomandos

# 12:30 UTC en enero: Madrid 13:30, Canarias 12:30, Shanghái 20:30, Moscú 15:30.
AHORA = datetime(2026, 1, 15, 12, 30, tzinfo=UTC)
# 12:30 UTC en julio: Madrid 14:30 (verano), Canarias 13:30.
VERANO = datetime(2026, 7, 15, 12, 30, tzinfo=UTC)


def test_horas_correctas_de_cada_sitio() -> None:
    n = Nekomandos(service.load_defaults())
    assert n.reply("hora china", AHORA) == "En China son las: 20:30"
    assert n.reply("Hora", AHORA) == "En España (península) son las: 13:30"
    assert n.reply("HORA CANARIA", AHORA) == "En Canarias son las: 12:30"
    assert n.reply("hora rusa", AHORA) == "En Rusia (Moscú) son las: 15:30"
    assert n.reply("hora", VERANO) == "En España (península) son las: 14:30"


def test_normalizacion_y_frase_desconocida() -> None:
    n = Nekomandos(service.load_defaults())
    assert n.reply("  BUENOS   DÍAS ", AHORA) == "Buenos días para ti también."
    assert n.reply("no existe", AHORA) is None


def test_zona_invalida_deja_el_token_y_avisa(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        out = service.render("Son las {hora:Mordor/Orodruin}", AHORA)
    assert out == "Son las {hora:Mordor/Orodruin}"
    assert "Mordor/Orodruin" in caplog.text


def test_overrides_validos_e_invalidos_no_rompen() -> None:
    n = Nekomandos({"hola": Entry("Hola", "saludos", "Hola")})
    rechazadas = n.apply_overrides({"HOLA": "Buenas-nya", "": "x", "vacio": "  ", "num": 5})
    assert sorted(rechazadas) == ["", "num", "vacio"]
    assert n.reply("hola", AHORA) == "Buenas-nya"
    assert n.help_lines() == ["Hola"]  # el pie de /help sigue saliendo de los defaults


def test_help_lines_agrupa_por_grupo() -> None:
    n = Nekomandos(
        {
            "a": Entry("1", "g1", "A"),
            "b": Entry("2", "g1", "B"),
            "c": Entry("3", "g2", "C"),
            "d": Entry("4"),  # sin grupo: no aparece
        }
    )
    assert n.help_lines() == ["A, B", "C"]


def test_defaults_invalidos(tmp_path: Path) -> None:
    casos = ['{"a": {"respuesta": ""}}', "[]", '{"a": {"respuesta": "x"}, "A": {"respuesta": "y"}}']
    for contenido in casos:
        ruta = tmp_path / "n.json"
        ruta.write_text(contenido, encoding="utf-8")
        with pytest.raises(NekomandoConfigError):
            service.load_defaults(ruta)
    with pytest.raises(NekomandoConfigError):
        service.load_defaults(tmp_path / "no_existe.json")


async def test_overrides_de_la_bd(db: Database) -> None:
    await db.execute("INSERT INTO nekomando_overrides(phrase, response) VALUES('hola', 'Ey')")
    assert await service.load_db_overrides(db) == {"hola": "Ey"}


async def test_importacion_de_node_una_sola_vez(db: Database, tmp_path: Path) -> None:
    fichero = tmp_path / "nekomandos.json"
    fichero.write_text(
        json.dumps({"overrides": {"Adiós": "Chao-nya", "": "x", "malo": 3}}), encoding="utf-8"
    )
    await service.import_legacy_file(db, tmp_path)
    assert await service.load_db_overrides(db) == {"adios": "Chao-nya"}
    assert not fichero.exists()
    assert (tmp_path / "nekomandos.json.importado").exists()
    await service.import_legacy_file(db, tmp_path)  # sin fichero: no hace nada


async def test_importacion_corrupta_no_tumba_el_arranque(db: Database, tmp_path: Path) -> None:
    (tmp_path / "nekomandos.json").write_text("{no es json", encoding="utf-8")
    await service.import_legacy_file(db, tmp_path)
    assert (tmp_path / "nekomandos.json.corrupto").exists()
    assert await service.load_db_overrides(db) == {}
