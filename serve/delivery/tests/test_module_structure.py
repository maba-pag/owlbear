"""Structural guards for the split Delivery facade modules."""

from __future__ import annotations

import ast
import importlib
import inspect
import json
import subprocess
import sys
from pathlib import Path

import pytest

import owlbear_delivery

_PACKAGE = "owlbear_delivery"
_PACKAGE_ROOT = Path(owlbear_delivery.__file__).resolve().parent
_SURFACE = json.loads((Path(__file__).with_name("fixtures") / "module_surface.json").read_text())
_FACADES = (
    ("portfolio_application", "PortfolioApplication"),
    ("change_workspace", "ChangeWorkspaceManager"),
    ("delivery_runtime", "DeliveryRuntime"),
)
_CLASS_DUNDERS = frozenset(
    {"__module__", "__qualname__", "__doc__", "__dict__", "__weakref__", "__firstlineno__", "__static_attributes__"}
)


def _runtime_imports(body: list[ast.stmt], package: str) -> set[str]:
    found: set[str] = set()
    for node in body:
        if isinstance(node, ast.If) and "TYPE_CHECKING" in ast.unparse(node.test):
            found |= _runtime_imports(node.orelse, package)
        elif isinstance(node, ast.ImportFrom) and node.level == 1:
            found.update([node.module.split(".")[0]] if node.module else (alias.name for alias in node.names))
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.module == package:
                found.update(alias.name for alias in node.names)
            elif node.module.startswith(f"{package}."):
                found.add(node.module.split(".")[1])
        elif isinstance(node, ast.Import):
            found.update(alias.name.split(".")[1] for alias in node.names if alias.name.startswith(f"{package}."))
        elif isinstance(node, (ast.If, ast.Try)):
            found |= _runtime_imports(node.body, package)
            found |= _runtime_imports(node.orelse, package)
            for handler in getattr(node, "handlers", ()):
                found |= _runtime_imports(handler.body, package)
    return found


def _import_graph(root: Path, package: str) -> dict[str, set[str]]:
    modules = {path.stem: path for path in root.glob("*.py") if path.stem != "__init__"}
    return {
        name: _runtime_imports(ast.parse(path.read_text()).body, package) & set(modules) - {name}
        for name, path in modules.items()
    }


def _find_cycle(graph: dict[str, set[str]]) -> list[str] | None:
    state: dict[str, int] = {}
    path: list[str] = []

    def visit(module: str) -> list[str] | None:
        state[module] = 1
        path.append(module)
        for target in sorted(graph[module]):
            if state.get(target) == 1:
                return [*path[path.index(target) :], target]
            if target not in state and (cycle := visit(target)):
                return cycle
        state[module] = 2
        path.pop()
        return None

    for module in sorted(graph):
        if module not in state and (cycle := visit(module)):
            return cycle
    return None


def test_runtime_import_graph_is_acyclic() -> None:
    assert _find_cycle(_import_graph(_PACKAGE_ROOT, _PACKAGE)) is None


def test_cycle_detector_rejects_a_two_module_cycle(tmp_path: Path) -> None:
    (tmp_path / "first.py").write_text(f"from {_PACKAGE}.second import value\n")
    (tmp_path / "second.py").write_text(f"from {_PACKAGE} import first\n")

    assert _find_cycle(_import_graph(tmp_path, _PACKAGE)) == ["first", "second", "first"]


@pytest.mark.parametrize(
    "module",
    sorted(_PACKAGE if path.stem == "__init__" else f"{_PACKAGE}.{path.stem}" for path in _PACKAGE_ROOT.glob("*.py")),
)
def test_module_imports_in_a_fresh_interpreter(module: str) -> None:
    result = subprocess.run(  # noqa: S603
        (sys.executable, "-c", f"import {module}"),
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr


def test_package_exports_match_the_fixture() -> None:
    assert sorted(owlbear_delivery.__all__) == _SURFACE["package_all"]


@pytest.mark.parametrize("module", sorted(_SURFACE["surfaces"]))
def test_consumer_import_surface_resolves(module: str) -> None:
    imported = importlib.import_module(f"{_PACKAGE}.{module}")

    assert [name for name in _SURFACE["surfaces"][module] if not hasattr(imported, name)] == []


@pytest.mark.parametrize(("module", "facade"), _FACADES)
def test_facade_bases_are_pure_disjoint_mixins(module: str, facade: str) -> None:
    cls = getattr(importlib.import_module(f"{_PACKAGE}.{module}"), facade)
    bases = [base for base in cls.__mro__[1:] if base is not object]
    impure = [
        f"{base.__name__}.{name}"
        for base in bases
        for name, value in vars(base).items()
        if name == "__init__"
        or (
            name not in _CLASS_DUNDERS
            and not (inspect.isfunction(value) or isinstance(value, (staticmethod, classmethod, property)))
        )
    ]
    owners: dict[str, list[str]] = {}
    for owner in (cls, *bases):
        for name in vars(owner):
            if name not in _CLASS_DUNDERS:
                owners.setdefault(name, []).append(owner.__name__)

    assert impure == []
    assert {name: found for name, found in owners.items() if len(found) > 1} == {}
