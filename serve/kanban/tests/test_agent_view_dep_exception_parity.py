"""Durable drift guard — dep-lookup exception tuple parity (#1530).

Asserts that ``show_task()`` and ``start_work()`` in ``AgentView`` both
catch the same set of exception types
``{FileNotFoundError, CorruptionError, ValueError, KeyError}``
in their dep-iteration loops.

``CorruptionError`` presence in the handler tuple discriminates dep-iteration
``except`` clauses from other ``try/except`` blocks in the same methods
(``show_task()`` has a separate ``FileNotFoundError``-only handler at its
outermost try that must not be counted).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

_PKG_DIR = Path(__file__).parent.parent / "src" / "owlbear_kanban"
_EXPECTED_EXCEPTIONS: frozenset[str] = frozenset({"FileNotFoundError", "CorruptionError", "ValueError", "KeyError"})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _agent_view_source() -> str:
    return (_PKG_DIR / "agent_view.py").read_text(encoding="utf-8")


def _find_method(tree: ast.AST, classname: str, methodname: str) -> ast.FunctionDef | None:
    """Return the FunctionDef for *classname*.*methodname*, or None."""
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == classname:
            for item in ast.iter_child_nodes(node):
                if isinstance(item, ast.FunctionDef) and item.name == methodname:
                    return item
    return None


def _dep_iteration_exception_sets(method_node: ast.FunctionDef) -> list[frozenset[str]]:
    """Return exception-name sets for ExceptHandlers that contain CorruptionError.

    The CorruptionError discriminator isolates dep-iteration handlers from
    unrelated try/except blocks in the same method.
    """
    result: list[frozenset[str]] = []
    for node in ast.walk(method_node):
        if not isinstance(node, ast.ExceptHandler):
            continue
        if node.type is None:
            continue
        if isinstance(node.type, ast.Tuple):
            names: frozenset[str] = frozenset(elt.id for elt in node.type.elts if isinstance(elt, ast.Name))
        elif isinstance(node.type, ast.Name):
            names = frozenset({node.type.id})
        else:
            names = frozenset()
        if "CorruptionError" in names:
            result.append(names)
    return result


# ---------------------------------------------------------------------------
# TestDepLookupExceptionParity — AC5 drift guard
# ---------------------------------------------------------------------------


class TestDepLookupExceptionParity:
    """AC5: dep-iteration ExceptHandlers in show_task() and start_work() stay in sync."""

    # -- handler presence ----------------------------------------------------

    def test_show_task_has_exactly_one_dep_iteration_handler(self) -> None:
        """show_task() must have exactly one ExceptHandler containing CorruptionError."""
        src = _agent_view_source()
        tree = ast.parse(src)
        method = _find_method(tree, "AgentView", "show_task")
        assert method is not None, "AgentView.show_task not found in agent_view.py"
        sets = _dep_iteration_exception_sets(method)
        assert len(sets) == 1, (
            f"Expected exactly 1 dep-iteration ExceptHandler in show_task(), found {len(sets)}: {sets}"
        )

    def test_start_work_has_exactly_one_dep_iteration_handler(self) -> None:
        """start_work() must have exactly one ExceptHandler containing CorruptionError."""
        src = _agent_view_source()
        tree = ast.parse(src)
        method = _find_method(tree, "AgentView", "start_work")
        assert method is not None, "AgentView.start_work not found in agent_view.py"
        sets = _dep_iteration_exception_sets(method)
        assert len(sets) == 1, (
            f"Expected exactly 1 dep-iteration ExceptHandler in start_work(), found {len(sets)}: {sets}"
        )

    # -- exact exception types -----------------------------------------------

    def test_show_task_dep_handler_catches_exact_exception_set(self) -> None:
        """show_task() dep-iteration handler must catch exactly the 4 required types."""
        src = _agent_view_source()
        tree = ast.parse(src)
        method = _find_method(tree, "AgentView", "show_task")
        assert method is not None
        sets = _dep_iteration_exception_sets(method)
        assert sets, "No dep-iteration ExceptHandler found in show_task()"
        actual = sets[0]
        assert actual == _EXPECTED_EXCEPTIONS, (
            f"show_task() dep handler mismatch — expected {set(_EXPECTED_EXCEPTIONS)}, got {set(actual)}"
        )

    def test_start_work_dep_handler_catches_exact_exception_set(self) -> None:
        """start_work() dep-iteration handler must catch exactly the 4 required types."""
        src = _agent_view_source()
        tree = ast.parse(src)
        method = _find_method(tree, "AgentView", "start_work")
        assert method is not None
        sets = _dep_iteration_exception_sets(method)
        assert sets, "No dep-iteration ExceptHandler found in start_work()"
        actual = sets[0]
        assert actual == _EXPECTED_EXCEPTIONS, (
            f"start_work() dep handler mismatch — expected {set(_EXPECTED_EXCEPTIONS)}, got {set(actual)}"
        )

    # -- cross-method parity (the core drift guard) --------------------------

    def test_dep_handlers_are_identical_across_methods(self) -> None:
        """The dep-iteration exception sets in show_task() and start_work() must be equal."""
        src = _agent_view_source()
        tree = ast.parse(src)
        show_method = _find_method(tree, "AgentView", "show_task")
        start_method = _find_method(tree, "AgentView", "start_work")
        assert show_method is not None, "AgentView.show_task not found"
        assert start_method is not None, "AgentView.start_work not found"
        show_sets = _dep_iteration_exception_sets(show_method)
        start_sets = _dep_iteration_exception_sets(start_method)
        assert show_sets, "No dep-iteration ExceptHandler in show_task()"
        assert start_sets, "No dep-iteration ExceptHandler in start_work()"
        assert show_sets[0] == start_sets[0], (
            f"Exception tuple drift detected — show_task()={set(show_sets[0])}, start_work()={set(start_sets[0])}"
        )

    # -- no bare except ------------------------------------------------------

    def test_show_task_dep_handler_is_not_bare_except(self) -> None:
        """The dep-iteration handler in show_task() must not be a bare except clause."""
        src = _agent_view_source()
        tree = ast.parse(src)
        method = _find_method(tree, "AgentView", "show_task")
        assert method is not None
        for node in ast.walk(method):
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                pytest.fail("show_task() contains a bare 'except:' clause")

    def test_start_work_dep_handler_is_not_bare_except(self) -> None:
        """The dep-iteration handler in start_work() must not be a bare except clause."""
        src = _agent_view_source()
        tree = ast.parse(src)
        method = _find_method(tree, "AgentView", "start_work")
        assert method is not None
        for node in ast.walk(method):
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                pytest.fail("start_work() contains a bare 'except:' clause")
