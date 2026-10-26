"""Contrato de una feature (spec 6.1-6.2)."""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from aiogram import Router

if TYPE_CHECKING:
    from nekita.core.context import AppContext

COMMAND_RE = re.compile(r"^[a-z0-9_]{1,32}$")  # límite de Telegram para el menú

Hook = Callable[["AppContext"], Awaitable[None]]


@dataclass(frozen=True)
class CommandInfo:
    """Metadatos de un comando: con ellos funcionan /help, el menú, admin y stats."""

    name: str
    description: str
    category: str = "otros"
    admin_only: bool = False  # no se publica en el menú y exige NEKITA_MASTER_ID
    cooldown: float = 0.0  # segundos entre usos por usuario y chat (0 = sin límite)
    drop_if_stale: bool = False  # ignorar si el update llega con > 60 s de retraso

    def __post_init__(self) -> None:
        if not COMMAND_RE.match(self.name):
            raise ValueError(f"Comando no válido {self.name!r}: usa [a-z0-9_], máx. 32")
        if not 1 <= len(self.description) <= 256:
            raise ValueError(f"/{self.name}: la descripción debe tener 1-256 caracteres")
        if not self.category.strip():
            raise ValueError(f"/{self.name}: la categoría no puede estar vacía")
        if self.cooldown < 0:
            raise ValueError(f"/{self.name}: el cooldown no puede ser negativo")


@dataclass(frozen=True)
class Job:
    """Tarea periódica de una feature."""

    name: str
    every: float  # segundos
    run: Hook


@dataclass(frozen=True)
class Feature:
    name: str
    router: Router
    commands: Sequence[CommandInfo] = ()
    help_lines: Sequence[str] = ()  # pie de /help: frases libres de ejemplo
    on_startup: Hook | None = None
    on_shutdown: Hook | None = None
    jobs: Sequence[Job] = ()
