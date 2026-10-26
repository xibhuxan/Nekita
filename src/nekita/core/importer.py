"""Importación única desde la versión Node, `grupos_pole.json` (spec 7.6)."""

from __future__ import annotations

import json
import logging
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from nekita.core.db import Database, utc_now_iso

log = logging.getLogger(__name__)

FILE_NAME = "grupos_pole.json"
GAME_ID = "pole"  # todo lo de Node era una sola pole


@dataclass
class ImportResult:
    chats: int = 0
    adjusts: int = 0
    legacy: int = 0
    stats: int = 0


def _int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None


def _points(value: object) -> int | None:
    n = _int(value)
    return n if n is not None and n >= 0 else None


async def _import_chat(db: Database, conn: Any, chat_id: int, raw: dict[str, Any]) -> ImportResult:
    res = ImportResult(chats=1)
    now = utc_now_iso()
    await conn.execute(
        "INSERT OR IGNORE INTO chats(chat_id, title, first_seen, last_seen) VALUES(?,?,?,?)",
        (chat_id, None, now, now),
    )
    es_v2 = raw.get("schemaVersion") == 2
    legacy_src = raw.get("legacyScores") if es_v2 else raw.get("scores")
    raw_names = raw.get("names")
    names: dict[str, Any] = raw_names if es_v2 and isinstance(raw_names, dict) else {}

    if es_v2 and isinstance(raw.get("scores"), dict):
        for uid_raw, pts_raw in raw["scores"].items():
            uid, pts = _int(uid_raw), _points(pts_raw)
            if uid is None or pts is None:
                continue
            display = names.get(str(uid_raw))
            display = display if isinstance(display, str) and display else str(uid)
            await conn.execute(
                "INSERT INTO users(user_id, display, updated_at) VALUES(?,?,?) "
                "ON CONFLICT(user_id) DO UPDATE SET display=excluded.display",
                (uid, display, now),
            )
            await conn.execute(
                "INSERT OR REPLACE INTO pole_adjust(chat_id, game_id, user_id, points) "
                "VALUES(?,?,?,?)",
                (chat_id, GAME_ID, uid, pts),
            )
            res.adjusts += 1
    if isinstance(legacy_src, dict):
        for name, pts_raw in legacy_src.items():
            pts = _points(pts_raw)
            if not isinstance(name, str) or not name or pts is None:
                continue
            await conn.execute(
                "INSERT OR REPLACE INTO pole_legacy(chat_id, game_id, name, points) "
                "VALUES(?,?,?,?)",
                (chat_id, GAME_ID, name, pts),
            )
            res.legacy += 1
    return res


async def _import_data(db: Database, data: dict[str, Any]) -> ImportResult:
    total = ImportResult()
    async with db.transaction() as conn:
        chats = data.get("chats")
        for chat_raw, raw in (chats if isinstance(chats, dict) else {}).items():
            chat_id = _int(chat_raw)
            if chat_id is None or not isinstance(raw, dict):
                log.warning("Chat ignorado en la importación: %r", chat_raw)
                continue
            r = await _import_chat(db, conn, chat_id, raw)
            total.chats += r.chats
            total.adjusts += r.adjusts
            total.legacy += r.legacy
        stats = data.get("stats")
        for key, val in (stats if isinstance(stats, dict) else {}).items():
            n = _points(val)
            if not isinstance(key, str) or key.startswith("pole:") or n is None:
                continue  # las poles ahora salen de pole_wins
            await conn.execute(
                "INSERT INTO stats(key, count) VALUES(?,?) "
                "ON CONFLICT(key) DO UPDATE SET count = count + excluded.count",
                (f"cmd:{key}", n),
            )
            total.stats += 1
    return total


async def import_node_data(db: Database, data_dir: Path, backups_dir: Path) -> ImportResult | None:
    """Importa `grupos_pole.json` solo si la BD es nueva y el fichero existe."""
    origen = data_dir / FILE_NAME
    if not db.is_new or not origen.is_file():
        return None
    backups_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(origen, backups_dir / f"{FILE_NAME}.original")
    try:
        data = json.loads(origen.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("la raíz no es un objeto")
    except (OSError, ValueError) as exc:
        destino = origen.with_name(FILE_NAME + ".corrupto")
        origen.replace(destino)
        log.warning(
            "%s es ilegible (%s); apartado como %s. Se empieza vacío.", FILE_NAME, exc, destino.name
        )
        return None
    res = await _import_data(db, data)
    origen.replace(origen.with_name(FILE_NAME + ".importado"))
    log.info(
        "Importado de Node: %d chats, %d ajustes, %d legados, %d contadores",
        res.chats,
        res.adjusts,
        res.legacy,
        res.stats,
    )
    return res
