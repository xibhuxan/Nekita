from pathlib import Path

import pytest

from nekita.config import ConfigError, Settings, load_settings

TOKEN = "123456:" + "A" * 35


@pytest.fixture(autouse=True)
def _entorno_limpio(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    for k in list(__import__("os").environ):
        if k.startswith("NEKITA_"):
            monkeypatch.delenv(k)
    monkeypatch.chdir(tmp_path)  # sin .env


def test_falta_token_da_mensaje_legible() -> None:
    with pytest.raises(ConfigError) as exc:
        load_settings()
    assert "NEKITA_TOKEN" in str(exc.value)
    assert ".env.example" in str(exc.value)


def test_token_vacio_se_rechaza(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEKITA_TOKEN", "   ")
    with pytest.raises(ConfigError):
        load_settings()


def test_valores_por_defecto(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEKITA_TOKEN", TOKEN)
    s = load_settings()
    assert s.tz == "Europe/Madrid"
    assert s.cache_segundos == 300
    assert s.max_handlers == 20
    assert s.log_level == "INFO"
    assert s.admin_id is None
    assert s.data_path.is_absolute()


def test_token_no_aparece_en_repr(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEKITA_TOKEN", TOKEN)
    assert TOKEN not in repr(load_settings())


def test_master_id_numerico_y_no_numerico(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEKITA_TOKEN", TOKEN)
    monkeypatch.setenv("NEKITA_MASTER_ID", "42")
    assert load_settings().admin_id == 42
    monkeypatch.setenv("NEKITA_MASTER_ID", "your_telegram_user_id")
    assert load_settings().admin_id is None  # se ignora, no impide arrancar


@pytest.mark.parametrize(
    ("var", "valor"),
    [("NEKITA_TZ", "Mars/Olympus"), ("NEKITA_BACKUP_HORA", "25:00"), ("NEKITA_LOG_LEVEL", "LOUD")],
)
def test_valores_invalidos(monkeypatch: pytest.MonkeyPatch, var: str, valor: str) -> None:
    monkeypatch.setenv("NEKITA_TOKEN", TOKEN)
    monkeypatch.setenv(var, valor)
    with pytest.raises(ConfigError) as exc:
        load_settings()
    assert var in str(exc.value)


def test_log_level_acepta_minusculas(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEKITA_TOKEN", TOKEN)
    monkeypatch.setenv("NEKITA_LOG_LEVEL", "debug")
    assert load_settings().log_level == "DEBUG"


def test_variables_antiguas_se_ignoran(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEKITA_TOKEN", TOKEN)
    monkeypatch.setenv("NEKITA_HORA_GUARDADO", "20")
    assert isinstance(load_settings(), Settings)
