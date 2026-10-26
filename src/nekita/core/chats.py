"""Grupos conocidos por el bot (Telegram no permite preguntar en cuáles está)."""

from __future__ import annotations

from dataclasses import dataclass

from nekita.core.db import Database, utc_now_iso

GROUP_TYPES = frozenset({"group", "supergroup"})


@dataclass(frozen=True)
class ChatRow:
    chat_id: int
    title: str | None
    kind: str | None

    @property
    def label(self) -> str:
        return self.title or f"(sin título) {self.chat_id}"


async def upsert_chat(db: Database, chat_id: int, title: str | None, kind: str | None) -> None:
    """Alta o actualización de un grupo; siempre lo deja activo."""
    now = utc_now_iso()
    await db.execute(
        "INSERT INTO chats(chat_id, title, kind, active, first_seen, last_seen) "
        "VALUES(?, ?, ?, 1, ?, ?) "
        "ON CONFLICT(chat_id) DO UPDATE SET "
        "title = COALESCE(excluded.title, title), kind = COALESCE(excluded.kind, kind), "
        "active = 1, last_seen = excluded.last_seen",
        (chat_id, title, kind, now, now),
    )


async def set_active(db: Database, chat_id: int, active: bool) -> None:
    await db.execute("UPDATE chats SET active = ? WHERE chat_id = ?", (int(active), chat_id))


async def list_active(db: Database) -> list[ChatRow]:
    """Grupos activos, orden estable: título (sin distinguir mayúsculas) y luego id."""
    rows = await db.fetchall(
        "SELECT chat_id, title, kind FROM chats WHERE active = 1 "
        "ORDER BY lower(COALESCE(title, '')), chat_id"
    )
    return [ChatRow(int(r[0]), r[1], r[2]) for r in rows]
