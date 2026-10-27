"""Envío de imágenes: método según extensión, plan B y plan C."""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import SendPhoto

from nekita.features.images.download import Downloader, DownloadError
from nekita.features.images.sender import media_kind, send_image


class FakeMessage:
    """Registra qué método de envío se usó y simula rechazos de Telegram."""

    def __init__(self, rechaza: set[str] | None = None) -> None:
        self.rechaza = rechaza or set()
        self.enviado: list[tuple[str, Any]] = []

    async def _do(self, metodo: str, media: Any) -> None:
        clave = f"{metodo}:{'url' if isinstance(media, str) else 'subida'}"
        if clave in self.rechaza:
            raise TelegramBadRequest(method=SendPhoto(chat_id=1, photo="x"), message="rechazada")
        self.enviado.append((metodo, media))

    async def answer_photo(self, media: Any) -> None:
        await self._do("photo", media)

    async def answer_animation(self, media: Any) -> None:
        await self._do("animation", media)

    async def answer_video(self, media: Any) -> None:
        await self._do("video", media)

    async def answer_document(self, media: Any) -> None:
        await self._do("document", media)


async def enviar(url: str, msg: FakeMessage) -> None:
    transporte = httpx.MockTransport(lambda r: httpx.Response(200, content=b"datos"))
    async with httpx.AsyncClient(transport=transporte) as c:
        await send_image(msg, url, Downloader(c), ("random.dog",))  # type: ignore[arg-type]


def test_media_kind() -> None:
    assert media_kind("https://x.com/a.GIF?v=1") == "animation"
    assert media_kind("https://x.com/a.mp4") == "video"
    assert media_kind("https://x.com/a.webm") == "video"
    assert media_kind("https://x.com/a.jpg") == "photo"
    assert media_kind("https://x.com/sin_extension") == "photo"


@pytest.mark.parametrize(
    ("url", "metodo"),
    [
        ("https://random.dog/a.jpg", "photo"),
        ("https://random.dog/a.gif", "animation"),
        ("https://random.dog/a.mp4", "video"),
    ],
)
async def test_envio_usa_el_metodo_segun_extension(url: str, metodo: str) -> None:
    msg = FakeMessage()
    await enviar(url, msg)
    assert msg.enviado == [(metodo, url)]


async def test_plan_b_descarga_y_sube() -> None:
    msg = FakeMessage(rechaza={"photo:url"})
    await enviar("https://random.dog/a.jpg", msg)
    assert [m for m, _ in msg.enviado] == ["photo"]
    assert not isinstance(msg.enviado[0][1], str)  # se subió el fichero


async def test_foto_rechazada_tambien_al_subir_va_como_documento() -> None:
    msg = FakeMessage(rechaza={"photo:url", "photo:subida"})
    await enviar("https://random.dog/a.jpg", msg)
    assert [m for m, _ in msg.enviado] == ["document"]


@pytest.mark.parametrize("ext", ["gif", "mp4"])
async def test_animacion_y_video_sin_plan_c(ext: str) -> None:
    metodo = "animation" if ext == "gif" else "video"
    msg = FakeMessage(rechaza={f"{metodo}:url", f"{metodo}:subida"})
    with pytest.raises(TelegramBadRequest):
        await enviar(f"https://random.dog/a.{ext}", msg)
    assert msg.enviado == []


async def test_plan_b_con_url_no_permitida_falla() -> None:
    msg = FakeMessage(rechaza={"photo:url"})
    with pytest.raises(DownloadError):
        await enviar("https://otro.com/a.jpg", msg)
