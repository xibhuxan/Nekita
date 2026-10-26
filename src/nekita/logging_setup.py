"""Logging a stdout con enmascarado de tokens de Telegram."""

from __future__ import annotations

import logging
import re
import sys

TOKEN_RE = re.compile(r"\d{6,}:[A-Za-z0-9_-]{30,}")
MASK = "***TOKEN***"


def mask(text: str) -> str:
    return TOKEN_RE.sub(MASK, text)


class MaskingFormatter(logging.Formatter):
    """Enmascara el token en el texto final (mensaje y tracebacks)."""

    def format(self, record: logging.LogRecord) -> str:
        return mask(super().format(record))


def setup_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(MaskingFormatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level)
    # httpx imprime URLs con parámetros: solo en DEBUG
    logging.getLogger("httpx").setLevel("DEBUG" if level == "DEBUG" else "WARNING")
    logging.getLogger("aiogram").setLevel(level)
