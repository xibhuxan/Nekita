"""Proveedores de imágenes y filtro de dominios (sin red)."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from nekita.features.images import providers


def client(handler: Any) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=False)


@pytest.mark.parametrize(
    ("url", "ok"),
    [
        ("https://cdn2.thecatapi.com/images/a.jpg", True),
        ("https://thecatapi.com/a.jpg", True),
        ("http://cdn2.thecatapi.com/a.jpg", False),
        ("https://evilthecatapi.com/a.jpg", False),
        ("https://thecatapi.com.evil.com/a.jpg", False),
        ("https://user:pw@thecatapi.com/a.jpg", False),
        ("https://thecatapi.com:8443/a.jpg", False),
        ("https://127.0.0.1/a.jpg", False),
        ("https://[::1]/a.jpg", False),
        ("https://localhost/a.jpg", False),
        ("ftp://thecatapi.com/a.jpg", False),
        ("no es una url", False),
    ],
)
def test_is_allowed(url: str, ok: bool) -> None:
    assert providers.is_allowed(url, ("thecatapi.com",)) is ok


async def test_cat_pide_lote_de_10_y_filtra_dominios() -> None:
    vistos: list[httpx.Request] = []

    def handler(req: httpx.Request) -> httpx.Response:
        vistos.append(req)
        return httpx.Response(
            200,
            json=[
                {"url": "https://cdn2.thecatapi.com/images/1.jpg"},
                {"url": "https://malo.example.com/2.jpg"},
                {"sin_url": 1},
            ],
        )

    async with client(handler) as c:
        urls = await providers.fetch_urls(providers.CAT, c)
    assert urls == ["https://cdn2.thecatapi.com/images/1.jpg"]
    assert vistos[0].url.params["limit"] == "10"


async def test_dog_descarta_videos_y_duplicados() -> None:
    respuestas = iter(
        ["https://random.dog/a.jpg", "https://random.dog/a.jpg", "https://random.dog/b.mp4"]
    )

    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"url": next(respuestas, "https://random.dog/c.png")})

    async with client(handler) as c:
        urls = await providers.fetch_urls(providers.DOG, c)
    assert len(urls) == len(set(urls))
    assert not any(u.endswith(".mp4") for u in urls)
    assert "https://random.dog/a.jpg" in urls


async def test_dog_reintenta_si_falla_la_peticion() -> None:
    intentos = 0

    def handler(req: httpx.Request) -> httpx.Response:
        nonlocal intentos
        intentos += 1
        if intentos == 1:
            return httpx.Response(500)
        return httpx.Response(200, json={"url": "https://random.dog/x.jpg"})

    async with client(handler) as c:
        assert await providers._one_dog(c) == "https://random.dog/x.jpg"


async def test_cangrejo_son_19_urls_sin_red() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        raise AssertionError("no debe haber red")

    async with client(handler) as c:
        urls = await providers.fetch_urls(providers.CRAB, c)
    assert len(urls) == 19
    assert urls[0].endswith("Random-Crab-image-1.jpg")
    assert urls[-1].endswith("Random-Crab-image-19.jpg")


async def test_moneda_solo_jpeg_y_png_con_miniatura() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        assert req.url.params["iiurlwidth"] == "800"
        pages = [
            {
                "imageinfo": [
                    {"thumburl": "https://upload.wikimedia.org/a.jpg", "mime": "image/jpeg"}
                ]
            },
            {"imageinfo": [{"url": "https://upload.wikimedia.org/b.svg", "mime": "image/svg+xml"}]},
            {"imageinfo": [{"url": "https://upload.wikimedia.org/c.png", "mime": "image/png"}]},
            {},
        ]
        return httpx.Response(200, json={"query": {"pages": pages}})

    async with client(handler) as c:
        urls = await providers.fetch_urls(providers.COIN, c)
    assert urls == ["https://upload.wikimedia.org/a.jpg", "https://upload.wikimedia.org/c.png"]


@pytest.mark.parametrize("respuesta", [httpx.Response(500), httpx.Response(200, text="no json")])
async def test_fallo_de_proveedor_da_lote_vacio(respuesta: httpx.Response) -> None:
    async with client(lambda req: respuesta) as c:
        assert await providers.fetch_urls(providers.CAT, c) == []


async def test_error_de_red_da_lote_vacio() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("sin red")

    async with client(handler) as c:
        assert await providers.fetch_urls(providers.COIN, c) == []
