import pytest
from aiogram import Router

from nekita.core.feature import CommandInfo, Feature
from nekita.core.limits import Cooldown, KeyedLock
from nekita.core.middlewares import parse_command
from nekita.core.registry import Registry
from nekita.core.texts import normalize


def _f(name: str, *cmds: CommandInfo) -> Feature:
    return Feature(name=name, router=Router(name=name), commands=cmds)


def test_help_y_menu_salen_del_registro() -> None:
    reg = Registry(
        [
            _f("a", CommandInfo("neko", "Imagen de neko", category="imágenes")),
            _f("b", CommandInfo("stats", "Estadísticas", category="meta", admin_only=True)),
        ]
    )
    assert [c.command for c in reg.menu()] == ["neko"]  # admin_only no se publica
    assert "/neko — Imagen de neko" in reg.render_help(is_admin=False)
    assert "/stats" not in reg.render_help(is_admin=False)
    assert "/stats" in reg.render_help(is_admin=True)


def test_comando_repetido_falla() -> None:
    with pytest.raises(ValueError, match="dos veces"):
        Registry([_f("a", CommandInfo("x", "uno")), _f("b", CommandInfo("x", "dos"))])


def test_feature_repetida_falla() -> None:
    with pytest.raises(ValueError, match="repetidas"):
        Registry([_f("a"), _f("a")])


@pytest.mark.parametrize("nombre", ["Neko", "con-guion", "", "x" * 33])
def test_comando_invalido(nombre: str) -> None:
    with pytest.raises(ValueError):
        CommandInfo(nombre, "desc")


def test_parse_command() -> None:
    assert parse_command("/Neko@MiBot hola") == ("neko", "MiBot")
    assert parse_command("/neko") == ("neko", None)
    assert parse_command("neko") is None
    assert parse_command("/neko_x") == ("neko_x", None)
    assert parse_command(None) is None


def test_normalize() -> None:
    assert normalize("  BUENOS   DÍAS ") == "buenos dias"


async def test_keyed_lock_libera_memoria() -> None:
    locks = KeyedLock()
    async with locks.hold(1):
        assert len(locks) == 1
    assert len(locks) == 0


def test_cooldown() -> None:
    t = [0.0]
    cd = Cooldown(clock=lambda: t[0])
    assert cd.allow((1, 1), 3)
    assert not cd.allow((1, 1), 3)
    assert cd.allow((1, 2), 3)  # otro usuario
    t[0] = 3.1
    assert cd.allow((1, 1), 3)
