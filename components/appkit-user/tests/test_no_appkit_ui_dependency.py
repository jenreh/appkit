"""appkit-user must not depend on appkit-ui (code or package metadata)."""

import ast
import tomllib
from pathlib import Path

import pytest

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
SOURCES = sorted((PACKAGE_ROOT / "src" / "appkit_user").rglob("*.py"))


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def test_sources_found() -> None:
    assert SOURCES


@pytest.mark.parametrize("path", SOURCES, ids=lambda p: p.name)
def test_module_does_not_import_appkit_ui(path: Path) -> None:
    offending = {
        name
        for name in _imported_modules(path)
        if name == "appkit_ui" or name.startswith("appkit_ui.")
    }

    assert not offending, f"{path} imports {sorted(offending)}"


def test_pyproject_does_not_declare_appkit_ui() -> None:
    project = tomllib.loads((PACKAGE_ROOT / "pyproject.toml").read_text("utf-8"))
    dependencies = project["project"]["dependencies"]
    sources = project.get("tool", {}).get("uv", {}).get("sources", {})

    assert not [d for d in dependencies if d.startswith("appkit-ui")]
    assert "appkit-ui" not in sources
