"""Aislamiento: ningún test toca el ~/.nekita real ni el .env del desarrollador."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest

from nekita.core.db import Database


@pytest.fixture(autouse=True)
def _aislar_datos(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEKITA_DATA_DIR", str(tmp_path / "data"))


@pytest.fixture
async def db(tmp_path: Path) -> AsyncIterator[Database]:
    base = await Database.open(tmp_path / "t.db", backups_dir=tmp_path / "backups")
    yield base
    await base.close()
