import json
from pathlib import Path

from nekita.core.db import Database
from nekita.core.importer import FILE_NAME, import_node_data


async def _abrir(tmp_path: Path) -> Database:
    return await Database.open(tmp_path / "data" / "nekita.db")


def _escribir(tmp_path: Path, contenido: str) -> Path:
    d = tmp_path / "data"
    d.mkdir(parents=True, exist_ok=True)
    (d / FILE_NAME).write_text(contenido, encoding="utf-8")
    return d


async def test_sin_fichero_no_hace_nada(tmp_path: Path) -> None:
    db = await _abrir(tmp_path)
    try:
        assert await import_node_data(db, tmp_path / "data", tmp_path / "bk") is None
    finally:
        await db.close()


async def test_fichero_vacio_se_renombra(tmp_path: Path) -> None:
    d = _escribir(tmp_path, '{"chats": {}, "stats": {}}')
    db = await _abrir(tmp_path)
    try:
        res = await import_node_data(db, d, tmp_path / "bk")
        assert res is not None and res.chats == 0
        assert (d / (FILE_NAME + ".importado")).exists() and not (d / FILE_NAME).exists()
        assert (tmp_path / "bk" / (FILE_NAME + ".original")).exists()
    finally:
        await db.close()


async def test_v1_v2_y_stats(tmp_path: Path) -> None:
    datos = {
        "chats": {
            "-100": {  # v1: scores por nombre
                "winners": [1],
                "scores": {"ana": 4, "malo": "x"},
                "nextPosition": 1,
            },
            "-200": {
                "schemaVersion": 2,
                "scores": {"123": 7, "abc": 1},
                "names": {"123": "fulano"},
                "legacyScores": {"mengano": 2},
            },
            "no_numerico": {},
        },
        "stats": {"neko": 12, "pole:oro": 3, "hora": 1},
    }
    d = _escribir(tmp_path, json.dumps(datos))
    db = await _abrir(tmp_path)
    try:
        res = await import_node_data(db, d, tmp_path / "bk")
        assert res is not None
        assert (res.chats, res.adjusts, res.legacy, res.stats) == (2, 1, 2, 2)
        assert await db.fetchall("SELECT name, points FROM pole_legacy ORDER BY name") == [
            ("ana", 4),
            ("mengano", 2),
        ]
        assert await db.fetchall("SELECT user_id, points FROM pole_adjust") == [(123, 7)]
        assert await db.fetchall("SELECT display FROM users") == [("fulano",)]
        assert await db.fetchall("SELECT key, count FROM stats ORDER BY key") == [
            ("cmd:hora", 1),
            ("cmd:neko", 12),
        ]
    finally:
        await db.close()


async def test_fichero_corrupto_no_tumba_el_arranque(tmp_path: Path) -> None:
    d = _escribir(tmp_path, "{esto no es json")
    db = await _abrir(tmp_path)
    try:
        assert await import_node_data(db, d, tmp_path / "bk") is None
        assert (d / (FILE_NAME + ".corrupto")).exists()
    finally:
        await db.close()


async def test_no_importa_si_la_bd_ya_existia(tmp_path: Path) -> None:
    await (await _abrir(tmp_path)).close()
    d = _escribir(tmp_path, '{"chats": {}, "stats": {"neko": 1}}')
    db = await _abrir(tmp_path)
    try:
        assert await import_node_data(db, d, tmp_path / "bk") is None
        assert (d / FILE_NAME).exists()
    finally:
        await db.close()
