"""Lógica de anuncios sin Telegram: destinatarios, anuncios pendientes y registro."""

from __future__ import annotations

import secrets
import time
from collections.abc import Callable
from dataclasses import dataclass

from nekita.core.broadcast import Payload, Report
from nekita.core.chats import ChatRow
from nekita.core.db import Database, utc_now_iso

PENDING_TTL = 300.0  # segundos para confirmar
MAX_TEXT = 3500  # holgura bajo el límite de 4096 de Telegram
PREVIEW_CHARS = 200


class AnnouncementError(Exception):
    """Entrada no válida; el mensaje se muestra tal cual al admin."""


@dataclass(frozen=True)
class Pending:
    admin_id: int
    chat_ids: tuple[int, ...]
    payload: Payload
    scope: str  # 'all' | 'some'
    preview: str
    expires: float


class PendingStore:
    """Anuncios esperando confirmación. En memoria: si el bot reinicia, se pierden (a propósito)."""

    def __init__(self, clock: Callable[[], float] = time.monotonic, max_items: int = 50) -> None:
        self._clock = clock
        self._max = max_items
        self._items: dict[str, Pending] = {}

    def add(self, admin_id: int, chat_ids: list[int], payload: Payload, scope: str) -> str:
        self._purge()
        if len(self._items) >= self._max:
            raise AnnouncementError("Hay demasiados anuncios sin confirmar; cancela alguno.")
        token = secrets.token_hex(4)
        texto = payload.text if payload.text is not None else "(mensaje copiado)"
        self._items[token] = Pending(
            admin_id,
            tuple(chat_ids),
            payload,
            scope,
            texto[:PREVIEW_CHARS],
            self._clock() + PENDING_TTL,
        )
        return token

    def take(self, token: str, admin_id: int) -> Pending | None:
        """Lo saca (un solo uso). None si no existe, caducó o es de otro admin."""
        item = self._items.get(token)
        if item is None or item.admin_id != admin_id:
            return None
        del self._items[token]
        return item if item.expires > self._clock() else None

    def _purge(self) -> None:
        ahora = self._clock()
        self._items = {k: v for k, v in self._items.items() if v.expires > ahora}

    def __len__(self) -> int:
        return len(self._items)


def check_text(text: str) -> str:
    texto = text.strip()
    if not texto:
        raise AnnouncementError("El anuncio está vacío.")
    if len(texto) > MAX_TEXT:
        raise AnnouncementError(f"El texto es demasiado largo ({len(texto)} > {MAX_TEXT}).")
    return texto


def parse_targets(args: str, groups: list[ChatRow]) -> tuple[list[int], str]:
    """`"1 3 -1001234 texto..."` → ([ids], "texto...").

    Número positivo = posición en /grupos. Negativo = id de chat. Hay que indicar al menos uno.
    """
    por_id = {g.chat_id for g in groups}
    destinos: list[int] = []
    resto = args.strip()
    while resto:
        primero, _, cola = resto.partition(" ")
        try:
            n = int(primero)
        except ValueError:
            break
        if n > 0:
            if n > len(groups):
                raise AnnouncementError(f"No existe el grupo nº {n}: usa /grupos.")
            destinos.append(groups[n - 1].chat_id)
        else:
            if n not in por_id:
                raise AnnouncementError(f"No conozco ningún grupo activo con id {n}.")
            destinos.append(n)
        resto = cola.strip()
    if not destinos:
        raise AnnouncementError("Indica al menos un grupo: /anuncio_a <nº o id> [...] <texto>")
    return list(dict.fromkeys(destinos)), resto


def render_groups(groups: list[ChatRow]) -> str:
    if not groups:
        return "Todavía no conozco ningún grupo."
    lineas = [f"{i}. {g.label} ({g.chat_id})" for i, g in enumerate(groups, start=1)]
    return "Grupos activos:\n" + "\n".join(lineas)


def render_report(report: Report, names: dict[int, str]) -> str:
    texto = f"Anuncio enviado a {report.ok} de {report.total} grupos."
    if report.failed:
        fallos = [f"• {names.get(c, c)}: {motivo}" for c, motivo in report.failed[:15]]
        extra = len(report.failed) - len(fallos)
        texto += "\nFallidos:\n" + "\n".join(fallos)
        if extra > 0:
            texto += f"\n… y {extra} más."
    return texto


async def record(db: Database, admin_id: int, scope: str, report: Report, preview: str) -> None:
    await db.execute(
        "INSERT INTO announcements(admin_id, created_at, scope, total, ok, failed, preview) "
        "VALUES(?,?,?,?,?,?,?)",
        (admin_id, utc_now_iso(), scope, report.total, report.ok, len(report.failed), preview),
    )
