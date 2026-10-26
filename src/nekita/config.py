"""Configuración: variables NEKITA_*, validadas una sola vez al arrancar."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, SecretStr, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

log = logging.getLogger(__name__)


class ConfigError(Exception):
    """Configuración inválida; el mensaje es legible para el usuario."""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="NEKITA_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # el .env antiguo trae variables retiradas
    )

    token: SecretStr
    master_id: str = ""
    tz: str = "Europe/Madrid"
    cache_segundos: int = Field(default=300, ge=0)
    data_dir: Path = Path("~/.nekita/data")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_messages: bool = False
    backup_hora: str = "04:00"
    max_handlers: int = Field(default=20, ge=1)
    backup_copia_cmd: str = ""
    ai_url: str = ""
    ai_model: str = ""
    ai_key: SecretStr = SecretStr("")
    ai_timeout: int = Field(default=20, ge=1)

    @field_validator("token")
    @classmethod
    def _token_no_vacio(cls, v: SecretStr) -> SecretStr:
        if not v.get_secret_value().strip():
            raise ValueError("el token no puede estar vacío")
        return SecretStr(v.get_secret_value().strip())

    @field_validator("log_level", mode="before")
    @classmethod
    def _log_level_mayusculas(cls, v: object) -> object:
        return v.upper() if isinstance(v, str) else v

    @field_validator("tz")
    @classmethod
    def _tz_valida(cls, v: str) -> str:
        try:
            ZoneInfo(v)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(f"zona horaria IANA desconocida: {v!r}") from exc
        return v

    @field_validator("backup_hora")
    @classmethod
    def _hora_valida(cls, v: str) -> str:
        try:
            hh, mm = v.split(":")
            ok = 0 <= int(hh) <= 23 and 0 <= int(mm) <= 59
        except ValueError:
            ok = False
        if not ok:
            raise ValueError(f"se esperaba HH:MM, recibido {v!r}")
        return v

    @property
    def admin_id(self) -> int | None:
        """Id numérico del admin; un valor no numérico se ignora con aviso."""
        raw = self.master_id.strip()
        if not raw:
            return None
        try:
            return int(raw)
        except ValueError:
            log.warning("NEKITA_MASTER_ID no es numérico: admin deshabilitado")
            return None

    @property
    def data_path(self) -> Path:
        return self.data_dir.expanduser()


def _describir(exc: ValidationError) -> str:
    lineas = ["Configuración inválida:"]
    for err in exc.errors():
        nombre = "NEKITA_" + ".".join(str(p) for p in err["loc"]).upper()
        if err["type"] == "missing":
            lineas.append(f"  - {nombre}: falta (obligatoria; token de @BotFather)")
        else:
            lineas.append(f"  - {nombre}: {err['msg']}")
    lineas.append("Revisa tu .env (hay un ejemplo en .env.example).")
    return "\n".join(lineas)


def load_settings() -> Settings:
    """Carga y valida la configuración; lanza ConfigError con mensaje legible."""
    try:
        return Settings()
    except ValidationError as exc:
        raise ConfigError(_describir(exc)) from None
