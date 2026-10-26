"""Registro de comandos: /help, menú de Telegram y búsqueda por nombre (spec 5.1)."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

from aiogram.types import BotCommand

from nekita.core.feature import CommandInfo, Feature

HELP_HEADER = "Mis comandos son los siguientes-nya:"
HELP_FOOTER = "¡Y muchos otros comandos más directamente escritos! Como por ejemplo:"
MAX_MENU = 100  # límite de Telegram


class Registry:
    def __init__(self, features: Sequence[Feature]) -> None:
        nombres = Counter(f.name for f in features)
        repetidas = sorted(n for n, c in nombres.items() if c > 1)
        if repetidas:
            raise ValueError(f"Features repetidas: {', '.join(repetidas)}")
        self._commands: dict[str, CommandInfo] = {}
        for feature in features:
            for cmd in feature.commands:
                if cmd.name in self._commands:
                    raise ValueError(f"El comando /{cmd.name} está definido dos veces")
                self._commands[cmd.name] = cmd
        self._help_lines = [line for f in features for line in f.help_lines]

    @property
    def commands(self) -> list[CommandInfo]:
        return list(self._commands.values())

    def get(self, name: str) -> CommandInfo | None:
        return self._commands.get(name.lower())

    def menu(self) -> list[BotCommand]:
        """Comandos para `setMyCommands`: los `admin_only` nunca se publican."""
        publicos = [c for c in self._commands.values() if not c.admin_only]
        if len(publicos) > MAX_MENU:
            raise ValueError(f"Telegram admite {MAX_MENU} comandos en el menú, hay {len(publicos)}")
        return [BotCommand(command=c.name, description=c.description) for c in publicos]

    def render_help(self, *, is_admin: bool) -> str:
        """Texto de /help por categoría y orden alfabético; oculta lo admin a quien no lo es."""
        visibles = [c for c in self._commands.values() if is_admin or not c.admin_only]
        por_categoria: dict[str, list[CommandInfo]] = {}
        for cmd in visibles:
            por_categoria.setdefault(cmd.category, []).append(cmd)
        lineas = [HELP_HEADER, ""]
        for categoria in sorted(por_categoria):
            lineas.append(f"📋 {categoria}:")
            lineas.extend(
                f"  /{c.name} — {c.description}"
                for c in sorted(por_categoria[categoria], key=lambda c: c.name)
            )
            lineas.append("")
        if self._help_lines:
            lineas.append(HELP_FOOTER)
            lineas.extend(self._help_lines)
        return "\n".join(lineas).rstrip()
