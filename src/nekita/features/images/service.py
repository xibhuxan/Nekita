"""Servicio de imágenes: caché + proveedores + descarga, con su cliente HTTP."""

from __future__ import annotations

import logging

import httpx

from nekita.features.images.cache import ImageCache
from nekita.features.images.download import Downloader
from nekita.features.images.providers import USER_AGENT, Provider, fetch_urls

log = logging.getLogger(__name__)


class ImageService:
    def __init__(self, ttl: float, client: httpx.AsyncClient | None = None) -> None:
        # follow_redirects=False: una redirección a otro dominio no se sigue (anti-SSRF)
        self.client = client or httpx.AsyncClient(
            timeout=10.0,
            headers={"User-Agent": USER_AGENT},
            follow_redirects=False,
            limits=httpx.Limits(max_connections=5),
        )
        self.cache = ImageCache(ttl)
        self.downloader = Downloader(self.client)

    async def next_url(self, provider: Provider) -> str | None:
        return await self.cache.take(provider.key, lambda: fetch_urls(provider, self.client))

    async def close(self) -> None:
        await self.client.aclose()
