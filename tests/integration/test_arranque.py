"""Arranque real en un subproceso (spec 11, nivel 'Arranque')."""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

TOKEN = "123456:" + "A" * 35


def _env(**extra: str) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("NEKITA_")}
    env.update(extra)
    return env


def test_sin_token_sale_con_1_y_mensaje_claro(tmp_path: Path) -> None:
    r = subprocess.run(
        [sys.executable, "-m", "nekita"],
        cwd=tmp_path,
        env=_env(),
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert r.returncode == 1
    assert "NEKITA_TOKEN" in r.stderr
    assert "Traceback" not in r.stderr


def test_con_token_arranca_y_sigterm_cierra_limpio(tmp_path: Path) -> None:
    p = subprocess.Popen(
        [sys.executable, "-m", "nekita"],
        cwd=tmp_path,
        env=_env(NEKITA_TOKEN=TOKEN),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        assert p.stdout is not None
        linea = p.stdout.readline()  # bloquea hasta "lista"
        assert "lista" in linea
        t0 = time.monotonic()
        p.send_signal(signal.SIGTERM)
        assert p.wait(timeout=5) == 0
        assert time.monotonic() - t0 < 5
        assert TOKEN not in (linea + p.stdout.read())
    finally:
        if p.poll() is None:
            p.kill()
        if p.stdout:
            p.stdout.close()


@pytest.mark.parametrize("sig", [signal.SIGINT])
def test_sigint_tambien_cierra(tmp_path: Path, sig: int) -> None:
    p = subprocess.Popen(
        [sys.executable, "-m", "nekita"],
        cwd=tmp_path,
        env=_env(NEKITA_TOKEN=TOKEN),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        assert p.stdout is not None
        p.stdout.readline()
        p.send_signal(sig)
        assert p.wait(timeout=5) == 0
    finally:
        if p.poll() is None:
            p.kill()
        if p.stdout:
            p.stdout.close()
