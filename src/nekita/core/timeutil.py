"""Hora y fecha en una zona IANA (spec 4.1). Todo parte de un instante UTC."""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo


def utcnow() -> datetime:
    """Instante actual en UTC. Único punto de lectura del reloj: se sustituye en tests."""
    return datetime.now(UTC)


def local(now: datetime, tz: str) -> datetime:
    """Convierte un instante a la zona `tz`; un `datetime` sin zona se toma como UTC."""
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    return now.astimezone(ZoneInfo(tz))


def format_time(now: datetime, tz: str) -> str:
    """`HH:MM:SS` en `tz`."""
    return local(now, tz).strftime("%H:%M:%S")


def format_date(now: datetime, tz: str) -> str:
    """`DD-MM-YYYY` en `tz` (la fecha cambia a las 00:00 locales, no UTC)."""
    return local(now, tz).strftime("%d-%m-%Y")
