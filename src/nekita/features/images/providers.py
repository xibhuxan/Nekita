"""Fuentes de imágenes (spec 4.4). Cada una devuelve un LOTE de URLs."""

from __future__ import annotations

import asyncio
import logging
import random
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

import httpx

log = logging.getLogger(__name__)

USER_AGENT = "NekitaBot/1.0 (+https://github.com/Xibhu/Nekita)"
VIDEO_EXT = (".mp4", ".webm")
CRAB_URL = "https://generatorfun.com/code/uploads/Random-Crab-image-{n}.jpg"
COIN_CATEGORIES = ("Euro_coins", "Gold_coins", "Silver_coins", "Coins_of_Spain")
COIN_MIMES = {"image/jpeg", "image/png"}

Fetcher = Callable[[httpx.AsyncClient], Awaitable[list[str]]]


@dataclass(frozen=True)
class Provider:
    key: str
    domains: tuple[str, ...]  # solo se aceptan URLs https de estos dominios
    fetch: Fetcher


def is_allowed(url: str, domains: tuple[str, ...]) -> bool:
    """https + dominio permitido. Rechaza IPs, credenciales en la URL y puertos raros."""
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError:
        return False
    host = (parts.hostname or "").lower()
    if parts.scheme != "https" or not host or parts.username or parts.password:
        return False
    if port not in (None, 443):
        return False
    if ":" in host or host.replace(".", "").isdigit():  # IPv6 / IPv4
        return False
    return any(host == d or host.endswith(f".{d}") for d in domains)


async def _get_json(client: httpx.AsyncClient, url: str, params: dict[str, Any]) -> Any:
    resp = await client.get(url, params=params)
    resp.raise_for_status()
    return resp.json()


async def fetch_cat(client: httpx.AsyncClient) -> list[str]:
    data = await _get_json(client, "https://api.thecatapi.com/v1/images/search", {"limit": 10})
    if not isinstance(data, list):
        return []
    return [i["url"] for i in data if isinstance(i, dict) and isinstance(i.get("url"), str)]


async def _one_dog(client: httpx.AsyncClient) -> str | None:
    for _ in range(3):  # reintentos por petición
        try:
            data = await _get_json(client, "https://random.dog/woof.json", {"filter": "mp4,webm"})
        except (httpx.HTTPError, ValueError):
            continue
        url = data.get("url") if isinstance(data, dict) else None
        if isinstance(url, str) and not urlsplit(url).path.lower().endswith(VIDEO_EXT):
            return url
    return None


async def fetch_dog(client: httpx.AsyncClient) -> list[str]:
    resultados = await asyncio.gather(*(_one_dog(client) for _ in range(5)))
    return list(dict.fromkeys(u for u in resultados if u))  # sin duplicados, en orden


async def fetch_crab(client: httpx.AsyncClient) -> list[str]:
    return [CRAB_URL.format(n=n) for n in range(1, 20)]  # lista fija, sin red


async def fetch_coin(client: httpx.AsyncClient) -> list[str]:
    data = await _get_json(
        client,
        "https://commons.wikimedia.org/w/api.php",
        {
            "action": "query",
            "generator": "categorymembers",
            "gcmtitle": f"Category:{random.choice(COIN_CATEGORIES)}",  # noqa: S311
            "gcmtype": "file",
            "gcmlimit": 50,
            "prop": "imageinfo",
            "iiprop": "url|mime",
            "iiurlwidth": 800,  # miniatura: el límite de foto por URL es pequeño
            "format": "json",
            "formatversion": 2,
        },
    )
    urls: list[str] = []
    for page in (data.get("query") or {}).get("pages") or []:
        info = (page.get("imageinfo") or [{}])[0]
        url = info.get("thumburl") or info.get("url")
        if isinstance(url, str) and info.get("mime") in COIN_MIMES:
            urls.append(url)
    return urls


CAT = Provider("cat", ("thecatapi.com",), fetch_cat)
DOG = Provider("dog", ("random.dog",), fetch_dog)
CRAB = Provider("crab", ("generatorfun.com",), fetch_crab)
COIN = Provider("coin", ("wikimedia.org",), fetch_coin)


async def fetch_urls(provider: Provider, client: httpx.AsyncClient) -> list[str]:
    """Lote de URLs válidas; un fallo de red o de formato da lote vacío, nunca excepción."""
    try:
        crudas = await provider.fetch(client)
    except (httpx.HTTPError, ValueError, KeyError, TypeError, AttributeError) as exc:
        log.warning("Fallo obteniendo imágenes de %s: %s", provider.key, exc)
        return []
    validas = [u for u in crudas if is_allowed(u, provider.domains)]
    if len(validas) < len(crudas):
        log.warning("%s: %d URLs descartadas por dominio", provider.key, len(crudas) - len(validas))
    return validas
