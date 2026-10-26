"""Entorno del bot contra una Telegram falsa."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import pytest
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from nekita.config import Settings
from nekita.core.bot import BotRuntime
from nekita.core.context import AppContext
from nekita.core.db import Database
from nekita.core.feature import CommandInfo, Feature
from nekita.core.registry import Registry
from nekita.core.stats import Stats
from nekita.features import meta
from tests.support.fake_telegram import FakeTelegram

ADMIN = 7
Entorno = tuple[BotRuntime, FakeTelegram, list[str]]


def make_features(log: list[str]) -> list[Feature]:
    router = Router(name="t")

    @router.message(Command("eco"))
    async def eco(message: Message) -> None:
        log.append("eco")
        await message.answer("eco")

    @router.message(Command("lento"))
    async def lento(message: Message) -> None:
        log.append("lento-in")
        await asyncio.sleep(0.2)
        log.append("lento-out")
        await message.answer("lento")

    @router.message(Command("rapido"))
    async def rapido(message: Message) -> None:
        log.append("rapido")
        await message.answer("rapido")

    @router.message(Command("roto"))
    async def roto(message: Message) -> None:
        raise RuntimeError("boom")

    @router.message(Command("secreto"))
    async def secreto(message: Message) -> None:
        await message.answer("secreto")

    @router.message(Command("viejo"))
    async def viejo(message: Message) -> None:
        await message.answer("viejo")

    comandos = [
        CommandInfo("eco", "Eco"),
        CommandInfo("lento", "Lento"),
        CommandInfo("rapido", "Rápido"),
        CommandInfo("roto", "Falla"),
        CommandInfo("secreto", "Admin", admin_only=True),
        CommandInfo("viejo", "Caduca", drop_if_stale=True),
    ]
    return [Feature(name="t", router=router, commands=comandos), meta.build()]


@pytest.fixture
async def entorno(db: Database, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[Entorno]:
    monkeypatch.setenv("NEKITA_TOKEN", "123456:" + "A" * 35)
    monkeypatch.setenv("NEKITA_MASTER_ID", str(ADMIN))
    log: list[str] = []
    feats = make_features(log)
    ctx = AppContext(Settings(), db, Stats(), Registry(feats))
    fake = FakeTelegram()
    rt = BotRuntime(ctx, feats, session=fake, retry_delay=0)
    await rt.start()
    yield rt, fake, log
    await rt.shutdown()
