import asyncio

import pytest

from nekita import __version__
from nekita.app import run
from nekita.config import Settings
from tests.support.fake_telegram import FakeTelegram


async def test_run_termina_con_0_al_parar(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEKITA_TOKEN", "123456:" + "A" * 35)
    stop = asyncio.Event()
    tarea = asyncio.create_task(run(Settings(), stop, session=FakeTelegram()))
    await asyncio.sleep(0.3)
    assert not tarea.done()
    stop.set()
    assert await asyncio.wait_for(tarea, 15) == 0


def test_version_viene_de_metadatos() -> None:
    assert __version__ != ""
