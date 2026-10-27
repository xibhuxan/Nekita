"""Caché de lotes: cada petición consume una URL distinta (spec 4.4)."""

from __future__ import annotations

import asyncio
import random
import time
from collections.abc import Awaitable, Callable


class ImageCache:
    def __init__(self, ttl: float, clock: Callable[[], float] = time.monotonic) -> None:
        self._ttl = ttl
        self._clock = clock
        self._batches: dict[str, tuple[list[str], float]] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    def _pop(self, key: str) -> str | None:
        entry = self._batches.get(key)
        if entry is None:
            return None
        urls, created = entry
        if not urls or self._clock() - created > self._ttl:
            del self._batches[key]  # agotado o caducado
            return None
        return urls.pop(random.randrange(len(urls)))  # noqa: S311 (azar no criptográfico)

    async def take(self, key: str, fill: Callable[[], Awaitable[list[str]]]) -> str | None:
        """Una URL del lote; si no hay, UNA sola petición de relleno por clave a la vez."""
        url = self._pop(key)
        if url is not None:
            return url
        async with self._locks.setdefault(key, asyncio.Lock()):
            url = self._pop(key)  # otro peticionario pudo rellenar mientras esperábamos
            if url is not None:
                return url
            urls = list(dict.fromkeys(await fill()))
            if not urls:
                return None
            if self._ttl <= 0:  # caché desactivada
                return random.choice(urls)  # noqa: S311
            self._batches[key] = (urls, self._clock())
            return self._pop(key)
