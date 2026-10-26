"""Nekita: bot de Telegram."""

from importlib.metadata import PackageNotFoundError, version


def get_version() -> str:
    """Versión única, tomada de los metadatos del paquete."""
    try:
        return version("nekita")
    except PackageNotFoundError:  # pragma: no cover - solo sin instalar
        return "0.0.0"


__version__ = get_version()
