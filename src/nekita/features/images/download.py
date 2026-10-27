"""Descarga segura para el plan B (spec 4.4 y 9): streaming, tope, dominios y concurrencia."""

from __future__ import annotations

import asyncio

import httpx

from nekita.features.images.providers import is_allowed

MAX_BYTES = 10 * 1024 * 1024
TIMEOUT = 15.0
CONCURRENCY = 2


class DownloadError(Exception):
    """La descarga no es posible o no es segura."""


class Downloader:
    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        max_bytes: int = MAX_BYTES,
        timeout: float = TIMEOUT,
        concurrency: int = CONCURRENCY,
    ) -> None:
        self._client = client
        self._max = max_bytes
        self._timeout = timeout
        self._sem = asyncio.Semaphore(concurrency)

    async def fetch(self, url: str, domains: tuple[str, ...]) -> bytes:
        if not is_allowed(url, domains):
            raise DownloadError("URL no permitida")
        async with self._sem:
            try:
                async with asyncio.timeout(self._timeout):
                    return await self._read(url)
            except TimeoutError as exc:
                raise DownloadError("tiempo de descarga agotado") from exc
            except httpx.HTTPError as exc:  # incluye redirecciones (no se siguen)
                raise DownloadError(f"fallo de red: {exc}") from exc

    async def _read(self, url: str) -> bytes:
        async with self._client.stream("GET", url) as resp:
            resp.raise_for_status()
            declarado = resp.headers.get("content-length", "")
            if declarado.isdigit() and int(declarado) > self._max:
                raise DownloadError("el fichero supera el tamaño máximo")
            buf = bytearray()
            async for chunk in resp.aiter_bytes():
                buf += chunk
                if len(buf) > self._max:  # se corta: no se lee el resto
                    raise DownloadError("el fichero supera el tamaño máximo")
            return bytes(buf)
