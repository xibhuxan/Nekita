"""Regla de dependencias (spec 5): core no importa features; una feature no importa otra."""

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src" / "nekita"


def _imports(path: Path) -> set[str]:
    out: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            out.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            out.add(node.module)
    return out


def test_core_no_importa_features() -> None:
    for f in (SRC / "core").rglob("*.py"):
        malos = [m for m in _imports(f) if m.startswith("nekita.features")]
        assert not malos, f"{f} importa {malos}"


def test_una_feature_no_importa_otra() -> None:
    for d in (SRC / "features").iterdir():
        if not d.is_dir() or d.name.startswith("__"):
            continue
        for f in d.rglob("*.py"):
            for m in _imports(f):
                if m.startswith("nekita.features."):
                    assert m.split(".")[2] == d.name, f"{f} importa {m}"
