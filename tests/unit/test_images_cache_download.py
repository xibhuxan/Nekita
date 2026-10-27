"""Caché de lotes y descarga segura (sin red)."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
import pytest

from nekita.features.images.cache import ImageCache
from nekita.features.images.download import Downloader, DownloadError

DOM = ("random.dog",)


def client(handler: Any) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=False)


async def test_cinco_neko_seguidos_no_repiten_con_una_llamada() -> None:
    llamadas = 0

    async def fill() -> list[str]:
        nonlocal llamadas
        llamadas += 1
        return [f"u{i}" for i in range(10)]

    cache = ImageCache(ttl=300)
    sacadas = [await cache.take("cat", fill) for _ in range(5)]
    assert len(set(sacadas)) == 5
    assert llamadas == 1


async def test_veinte_peticiones_simultaneas_hacen_una_sola_llamada() -> None:
    llamadas = 0

    async def fill() -> list[str]:
        nonlocal llamadas
        llamadas += 1
        await asyncio.sleep(0.05)
        return [f"u{i}" for i in range(30)]

    cache = ImageCache(ttl=300)
    res = await asyncio.gather(*(cache.take("cat", fill) for _ in range(20)))
    assert llamadas == 1
    assert len(set(res)) == 20


async def test_lote_agotado_o_caducado_se_vuelve_a_pedir() -> None:
    ahora = [0.0]
    llamadas = 0

    async def fill() -> list[str]:
        nonlocal llamadas
        llamadas += 1
        return ["a", "b"]

    cache = ImageCache(ttl=10, clock=lambda: ahora[0])
    await cache.take("k", fill)
    await cache.take("k", fill)
    assert llamadas == 1
    await cache.take("k", fill)  # agotado
    assert llamadas == 2
    ahora[0] = 11.0  # caducado
    await cache.take("k", fill)
    assert llamadas == 3


async def test_sin_imagenes_devuelve_none_y_no_cachea() -> None:
    llamadas = 0

    async def fill() -> list[str]:
        nonlocal llamadas
        llamadas += 1
        return []

    cache = ImageCache(ttl=300)
    assert await cache.take("k", fill) is None
    assert await cache.take("k", fill) is None
    assert llamadas == 2


async def test_ttl_cero_desactiva_la_cache() -> None:
    llamadas = 0

    async def fill() -> list[str]:
        nonlocal llamadas
        llamadas += 1
        return ["a", "b"]

    cache = ImageCache(ttl=0)
    await cache.take("k", fill)
    await cache.take("k", fill)
    assert llamadas == 2


async def test_descarga_normal() -> None:
    async with client(lambda r: httpx.Response(200, content=b"abc")) as c:
        assert await Downloader(c).fetch("https://random.dog/a.jpg", DOM) == b"abc"


async def test_descarga_de_20mb_se_corta_en_10mb() -> None:
    leidos = 0

    async def cuerpo() -> Any:
        nonlocal leidos
        for _ in range(20):
            leidos += 1
            yield b"x" * (1024 * 1024)

    async with client(lambda r: httpx.Response(200, content=cuerpo())) as c:
        with pytest.raises(DownloadError, match="tamaño"):
            await Downloader(c).fetch("https://random.dog/a.jpg", DOM)
    assert leidos <= 11  # no se lee el resto


async def test_content_length_enorme_se_rechaza() -> None:
    cabecera = {"content-length": str(50 * 1024 * 1024)}
    async with client(lambda r: httpx.Response(200, headers=cabecera)) as c:
        with pytest.raises(DownloadError, match="tamaño"):
            await Downloader(c).fetch("https://random.dog/a.jpg", DOM)


@pytest.mark.parametrize(
    "url", ["http://random.dog/a.jpg", "https://otro.com/a.jpg", "https://127.0.0.1/a.jpg"]
)
async def test_descarga_rechaza_urls_no_permitidas(url: str) -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        raise AssertionError("no debe salir a la red")

    async with client(handler) as c:
        with pytest.raises(DownloadError, match="no permitida"):
            await Downloader(c).fetch(url, DOM)


async def test_redireccion_no_se_sigue() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "http://127.0.0.1/secreto"})

    async with client(handler) as c:
        with pytest.raises(DownloadError):
            await Downloader(c).fetch("https://random.dog/a.jpg", DOM)


async def test_descarga_con_timeout() -> None:
    async def handler(req: httpx.Request) -> httpx.Response:
        await asyncio.sleep(1)
        return httpx.Response(200, content=b"x")

    async with client(handler) as c:
        with pytest.raises(DownloadError, match="tiempo"):
            await Downloader(c, timeout=0.05).fetch("https://random.dog/a.jpg", DOM)


async def test_maximo_dos_descargas_simultaneas() -> None:
    activas = 0
    pico = 0

    async def handler(req: httpx.Request) -> httpx.Response:
        nonlocal activas, pico
        activas += 1
        pico = max(pico, activas)
        await asyncio.sleep(0.02)
        activas -= 1
        return httpx.Response(200, content=b"x")

    async with client(handler) as c:
        d = Downloader(c)
        await asyncio.gather(*(d.fetch("https://random.dog/a.jpg", DOM) for _ in range(6)))
    assert pico <= 2
