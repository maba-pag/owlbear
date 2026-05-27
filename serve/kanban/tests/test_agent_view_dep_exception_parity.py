"""Durable drift guard — dep-lookup exception tuple parity (#1530).

Asserts that the engine's single-task dependency-status context helper and
``AgentView.start_work()`` both catch the same set of exception types
``{FileNotFoundError, CorruptionError, ValueError, KeyError}``
in their dep-iteration loops.

``CorruptionError`` presence in the handler tuple discriminates dep-iteration
``except`` clauses from other ``try/except`` blocks in the same methods.
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


def _module_source(module_name: str) -> str:
    return (_PKG_DIR / module_name).read_text(encoding="utf-8")


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
    """AC5: dep-iteration ExceptHandlers stay in sync across projection paths."""

    # -- handler presence ----------------------------------------------------

    def test_engine_projection_context_has_exactly_one_dep_iteration_handler(self) -> None:
        """_dep_status_context_for_task() must have exactly one CorruptionError handler."""
        src = _module_source("engine.py")
        tree = ast.parse(src)
        method = _find_method(tree, "KanbanEngine", "_dep_status_context_for_task")
        assert method is not None, "KanbanEngine._dep_status_context_for_task not found in engine.py"
        sets = _dep_iteration_exception_sets(method)
        assert len(sets) == 1, (
            "Expected exactly 1 dep-iteration ExceptHandler in _dep_status_context_for_task(), "
            f"found {len(sets)}: {sets}"
        )

    def test_start_work_has_exactly_one_dep_iteration_handler(self) -> None:
        """start_work() must have exactly one ExceptHandler containing CorruptionError."""
        src = _module_source("agent_view.py")
        tree = ast.parse(src)
        method = _find_method(tree, "AgentView", "start_work")
        assert method is not None, "AgentView.start_work not found in agent_view.py"
        sets = _dep_iteration_exception_sets(method)
        assert len(sets) == 1, (
            f"Expected exactly 1 dep-iteration ExceptHandler in start_work(), found {len(sets)}: {sets}"
        )

    # -- exact exception types -----------------------------------------------

    def test_engine_projection_context_handler_catches_exact_exception_set(self) -> None:
        """_dep_status_context_for_task() must catch exactly the 4 required types."""
        src = _module_source("engine.py")
        tree = ast.parse(src)
        method = _find_method(tree, "KanbanEngine", "_dep_status_context_for_task")
        assert method is not None
        sets = _dep_iteration_exception_sets(method)
        assert sets, "No dep-iteration ExceptHandler found in _dep_status_context_for_task()"
        actual = sets[0]
        assert actual == _EXPECTED_EXCEPTIONS, (
            "_dep_status_context_for_task() dep handler mismatch — "
            f"expected {set(_EXPECTED_EXCEPTIONS)}, got {set(actual)}"
        )

    def test_start_work_dep_handler_catches_exact_exception_set(self) -> None:
        """start_work() dep-iteration handler must catch exactly the 4 required types."""
        src = _module_source("agent_view.py")
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
        """The engine projection helper and start_work() exception sets must be equal."""
        engine_tree = ast.parse(_module_source("engine.py"))
        agent_tree = ast.parse(_module_source("agent_view.py"))
        show_method = _find_method(engine_tree, "KanbanEngine", "_dep_status_context_for_task")
        start_method = _find_method(agent_tree, "AgentView", "start_work")
        assert show_method is not None, "KanbanEngine._dep_status_context_for_task not found"
        assert start_method is not None, "AgentView.start_work not found"
        show_sets = _dep_iteration_exception_sets(show_method)
        start_sets = _dep_iteration_exception_sets(start_method)
        assert show_sets, "No dep-iteration ExceptHandler in _dep_status_context_for_task()"
        assert start_sets, "No dep-iteration ExceptHandler in start_work()"
        assert show_sets[0] == start_sets[0], (
            "Exception tuple drift detected — "
            f"_dep_status_context_for_task()={set(show_sets[0])}, start_work()={set(start_sets[0])}"
        )

    # -- no bare except ------------------------------------------------------

    def test_engine_projection_context_handler_is_not_bare_except(self) -> None:
        """The dep-iteration handler in _dep_status_context_for_task() must not be bare."""
        src = _module_source("engine.py")
        tree = ast.parse(src)
        method = _find_method(tree, "KanbanEngine", "_dep_status_context_for_task")
        assert method is not None
        for node in ast.walk(method):
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                pytest.fail("_dep_status_context_for_task() contains a bare 'except:' clause")

    def test_start_work_dep_handler_is_not_bare_except(self) -> None:
        """The dep-iteration handler in start_work() must not be a bare except clause."""
        src = _module_source("agent_view.py")
        tree = ast.parse(src)
        method = _find_method(tree, "AgentView", "start_work")
        assert method is not None
        for node in ast.walk(method):
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                pytest.fail("start_work() contains a bare 'except:' clause")
