"""Structural guardrails for managed Change worktree creation."""

from __future__ import annotations

import ast
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
_SOURCE_ROOTS = tuple(sorted(path for path in (_REPO_ROOT / "serve").glob("*/src") if path.is_dir()))
_RETIRED_PRODUCER_SYMBOLS = frozenset(
    {
        ("TargetMCPAdapter", "list_integration_ready_changes"),
        ("TargetMCPAdapter", "integrate_ready_change"),
        ("TargetMCPAdapter", "prepare_external_completion"),
        ("DeliveryRuntime", "completion_capture_bytes"),
        ("DeliveryRuntime", "publish_integration_completion"),
        ("DeliveryRuntime", "publish_integration_attention"),
        ("PortfolioCoordinator", "publish_finding"),
        ("ChangeWorkspaceManager", "integrate"),
        ("ChangeWorkspaceManager", "_publish_integration_finding"),
    }
)


def _source_files() -> tuple[Path, ...]:
    return tuple(sorted(path for root in _SOURCE_ROOTS for path in root.rglob("*.py")))


def _literal_string(node: ast.AST) -> str | None:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def _sequence_contains_worktree_add(node: ast.AST) -> bool:
    if isinstance(node, ast.Starred):
        return _sequence_contains_worktree_add(node.value)
    if not isinstance(node, (ast.List, ast.Tuple)):
        return False
    return any(
        _literal_string(left) == "worktree" and _literal_string(right) == "add"
        for left, right in zip(node.elts, node.elts[1:], strict=False)
    ) or any(_sequence_contains_worktree_add(item) for item in node.elts)


def _call_contains_worktree_add(node: ast.Call) -> bool:
    return any(
        _literal_string(left) == "worktree" and _literal_string(right) == "add"
        for left, right in zip(node.args, node.args[1:], strict=False)
    ) or any(_sequence_contains_worktree_add(argument) for argument in node.args)


class _WorktreeAddVisitor(ast.NodeVisitor):
    def __init__(self, path: Path) -> None:
        self.path = path
        self.classes: list[str] = []
        self.functions: list[str] = []
        self.matches: list[tuple[int, tuple[str, ...], tuple[str, ...], str]] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.classes.append(node.name)
        self.generic_visit(node)
        self.classes.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.functions.append(node.name)
        self.generic_visit(node)
        self.functions.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.functions.append(node.name)
        self.generic_visit(node)
        self.functions.pop()

    def visit_Call(self, node: ast.Call) -> None:
        if _call_contains_worktree_add(node):
            source = ast.get_source_segment(self._source, node) or "<call>"
            self.matches.append((node.lineno, tuple(self.classes), tuple(self.functions), source))
        self.generic_visit(node)

    def scan(self) -> None:
        self._source = self.path.read_text(encoding="utf-8")
        self.visit(ast.parse(self._source, filename=str(self.path)))


def _worktree_add_matches() -> list[tuple[Path, int, tuple[str, ...], tuple[str, ...], str]]:
    matches: list[tuple[Path, int, tuple[str, ...], tuple[str, ...], str]] = []
    for path in _source_files():
        visitor = _WorktreeAddVisitor(path)
        visitor.scan()
        matches.extend(
            (path, lineno, classes, functions, source) for lineno, classes, functions, source in visitor.matches
        )
    return matches


class _RetiredProducerVisitor(ast.NodeVisitor):
    def __init__(self, path: Path) -> None:
        self.path = path
        self.classes: list[str] = []
        self.functions: list[str] = []
        self.matches: list[tuple[int, str, tuple[str, ...], tuple[str, ...]]] = []

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        if self.classes and (self.classes[-1], node.name) in _RETIRED_PRODUCER_SYMBOLS:
            self.matches.append((node.lineno, node.name, tuple(self.classes), tuple(self.functions)))
        self.functions.append(node.name)
        self.generic_visit(node)
        self.functions.pop()

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.classes.append(node.name)
        self.generic_visit(node)
        self.classes.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node)

    def scan(self) -> None:
        self.visit(ast.parse(self.path.read_text(encoding="utf-8"), filename=str(self.path)))


def _retired_producer_definitions() -> list[tuple[Path, int, str, tuple[str, ...], tuple[str, ...]]]:
    matches: list[tuple[Path, int, str, tuple[str, ...], tuple[str, ...]]] = []
    for path in _source_files():
        visitor = _RetiredProducerVisitor(path)
        visitor.scan()
        matches.extend((path, lineno, name, classes, functions) for lineno, name, classes, functions in visitor.matches)
    return matches


def test_delivery_source_has_one_managed_worktree_add_implementation() -> None:
    matches = _worktree_add_matches()

    assert len(matches) == 1, "Expected exactly one source-level worktree-add implementation:\n" + "\n".join(
        f"{path.relative_to(_REPO_ROOT)}:{lineno}" for path, lineno, _classes, _functions, _source in matches
    )
    path, _lineno, classes, functions, source = matches[0]
    assert path == _REPO_ROOT / "serve/delivery/src/owlbear_delivery/change_workspace.py"
    assert classes == ("ChangeWorkspaceManager",)
    assert functions == ("_register_worktree",)
    assert "--detach" not in source


def test_delivery_source_has_no_retired_local_integration_producers() -> None:
    matches = _retired_producer_definitions()

    assert not matches, "Retired local Integration producers were reintroduced:\n" + "\n".join(
        f"{path.relative_to(_REPO_ROOT)}:{lineno} {name}" for path, lineno, name, _classes, _functions in matches
    )
