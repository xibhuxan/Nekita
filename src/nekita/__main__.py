"""Punto de entrada: `python -m nekita`."""

from __future__ import annotations

import asyncio
import sys

from nekita.app import run
from nekita.config import ConfigError, load_settings
from nekita.logging_setup import setup_logging


def main() -> int:
    try:
        settings = load_settings()
    except ConfigError as exc:
        print(exc, file=sys.stderr)
        return 1
    setup_logging(settings.log_level)
    return asyncio.run(run(settings))


if __name__ == "__main__":
    sys.exit(main())
