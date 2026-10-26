"""Servicios compartidos que los handlers reciben por inyección (`ctx: AppContext`)."""

from __future__ import annotations

from dataclasses import dataclass

from nekita.config import Settings
from nekita.core.db import Database
from nekita.core.registry import Registry
from nekita.core.stats import Stats


@dataclass
class AppContext:
    settings: Settings
    db: Database
    stats: Stats
    registry: Registry
