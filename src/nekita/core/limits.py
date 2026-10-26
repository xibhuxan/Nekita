"""Colas y límites simples en memoria (spec 9.1)."""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager


class KeyedLock:
    """Un `asyncio.Lock` por clave (FIFO). Se libera la memoria al quedar sin usuarios."""

    def __init__(self) -> None:
        self._locks: dict[int, asyncio.Lock] = {}
        self._users: dict[int, int] = {}

    @asynccontextmanager
    async def hold(self, key: int) -> AsyncIterator[None]:
        lock = self._locks.setdefault(key, asyncio.Lock())
        self._users[key] = self._users.get(key, 0) + 1
        try:
            async with lock:
                yield
        finally:
            self._users[key] -= 1
            if self._users[key] == 0:
                del self._users[key]
                del self._locks[key]

    def __len__(self) -> int:
        return len(self._locks)


class Cooldown:
    """Limitador por clave: como máximo 1 uso cada `seconds`."""

    def __init__(
        self, clock: Callable[[], float] = time.monotonic, max_entries: int = 10_000
    ) -> None:
        self._clock = clock
        self._max = max_entries
        self._until: dict[tuple[int, int], float] = {}

    def allow(self, key: tuple[int, int], seconds: float) -> bool:
        """True y arranca el enfriamiento; False si todavía no ha pasado el tiempo."""
        now = self._clock()
        if self._until.get(key, 0.0) > now:
            return False
        if len(self._until) >= self._max:
            self._until = {k: t for k, t in self._until.items() if t > now}
        self._until[key] = now + seconds
        return True

    def __len__(self) -> int:
        return len(self._until)
