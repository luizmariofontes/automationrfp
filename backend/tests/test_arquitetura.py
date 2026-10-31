"""Regras de fronteira entre módulos (complementa o import-linter).

Um módulo só pode importar de outro módulo:
- o pacote raiz (`app.modules.x`), ou
- a interface pública: `app.modules.x.service`.

Nunca `domain`, `repository`, `models`, `api` ou qualquer outro arquivo interno.
"""

import ast
import sys
from pathlib import Path

import pytest

from app.modules import MODULES

MODULES_DIR = Path(__file__).resolve().parents[1] / "app" / "modules"
PUBLIC = {"", "service"}


def _imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            # `from app.modules.x.repository import Repo` → confere "app.modules.x.repository"
            # `from app.modules.x import repository` → confere "app.modules.x.repository"
            if len(node.module.split(".")) > 3:
                found.append(node.module)
            else:
                found.extend(f"{node.module}.{alias.name}" for alias in node.names)
    return found


def _violations() -> list[str]:
    problems: list[str] = []
    for own in MODULES:
        for path in (MODULES_DIR / own).rglob("*.py"):
            for imported in _imports(path):
                parts = imported.split(".")
                if parts[:2] != ["app", "modules"] or len(parts) < 3:
                    continue
                other = parts[2]
                if other == own or other not in MODULES:
                    continue
                rest = parts[3] if len(parts) > 3 else ""
                if rest not in PUBLIC:
                    rel = path.relative_to(MODULES_DIR)
                    problems.append(f"{rel}: importa {imported}")
    return problems


def test_todos_os_modulos_existem():
    for name in MODULES:
        assert (MODULES_DIR / name / "service.py").exists(), name
        assert (MODULES_DIR / name / "api.py").exists(), name


def test_modulos_so_usam_interface_publica_uns_dos_outros():
    problems = _violations()
    if problems:
        pytest.fail("Imports entre módulos fora da interface pública:\n" + "\n".join(problems))


def test_detector_pega_violacao(tmp_path, monkeypatch):
    """Garante que a própria regra funciona."""
    fake = tmp_path / "modules"
    (fake / "cadastros").mkdir(parents=True)
    (fake / "requisicoes").mkdir()
    (fake / "requisicoes" / "x.py").write_text(
        "from app.modules.cadastros.repository import Repo\n"
    )
    (fake / "requisicoes" / "y.py").write_text("from app.modules.cadastros import service\n")
    this = sys.modules[__name__]
    monkeypatch.setattr(this, "MODULES_DIR", fake)
    monkeypatch.setattr(this, "MODULES", ("cadastros", "requisicoes"))
    problems = _violations()
    assert len(problems) == 1
    assert "repository" in problems[0]
