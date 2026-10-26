"""Arranque real en un subproceso (spec 11, nivel 'Arranque')."""

import json
import os
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import IO, Any

import pytest

TOKEN = "123456:" + "A" * 35


class _FakeBotApi(BaseHTTPRequestHandler):
    """Mini servidor Bot API: responde a getMe/getUpdates/setMyCommands."""

    def do_POST(self) -> None:
        metodo = self.path.rsplit("/", 1)[-1]
        self.rfile.read(int(self.headers.get("Content-Length", 0)))
        if metodo == "getMe":
            result: Any = {
                "id": 123456,
                "is_bot": True,
                "first_name": "Nekita",
                "username": "nekita_test_bot",
                "can_read_all_group_messages": True,
            }
        elif metodo == "getUpdates":
            time.sleep(0.2)
            result = []
        else:
            result = True
        cuerpo = json.dumps({"ok": True, "result": result}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def log_message(self, format: str, *args: Any) -> None:
        return None


@pytest.fixture
def api_url() -> Iterator[str]:
    server = HTTPServer(("127.0.0.1", 0), _FakeBotApi)
    hilo = threading.Thread(target=server.serve_forever, daemon=True)
    hilo.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    server.server_close()


def _esperar_lista(stdout: IO[str]) -> str:
    """Lee el log hasta la línea "lista"; devuelve todo lo leído."""
    leido = ""
    while True:
        linea = stdout.readline()
        if not linea:
            raise AssertionError(f"El proceso terminó sin quedar lista:\n{leido}")
        leido += linea
        if "lista" in linea:
            return leido


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


def test_con_token_arranca_y_sigterm_cierra_limpio(tmp_path: Path, api_url: str) -> None:
    p = subprocess.Popen(
        [sys.executable, "-m", "nekita"],
        cwd=tmp_path,
        env=_env(NEKITA_TOKEN=TOKEN, NEKITA_API_URL=api_url),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        assert p.stdout is not None
        linea = _esperar_lista(p.stdout)
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
def test_sigint_tambien_cierra(tmp_path: Path, sig: int, api_url: str) -> None:
    p = subprocess.Popen(
        [sys.executable, "-m", "nekita"],
        cwd=tmp_path,
        env=_env(NEKITA_TOKEN=TOKEN, NEKITA_API_URL=api_url),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        assert p.stdout is not None
        _esperar_lista(p.stdout)
        p.send_signal(sig)
        assert p.wait(timeout=5) == 0
    finally:
        if p.poll() is None:
            p.kill()
        if p.stdout:
            p.stdout.close()
