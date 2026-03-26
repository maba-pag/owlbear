"""RED tests for task #939: cli_board_fixtures implementation and test_cli_board.py migration.

Tests verify the implementation contract the builder must satisfy:

- AC2: ``tests/test_cli_board.py`` is updated so that ``TestFromAC_BoardRendering``,
  ``TestFromAC_AssigneeDisplay``, and ``TestFromAC_AgeInStatus`` use helpers from
  ``cli_board_fixtures``; subprocess routing (``_subproc``) stays local.
- AC4: helper functions are pure — no subprocess, no live binary call needed at any
  point during invocation.

AC1/AC5: fully covered by the #936 test file ``tests/test_cli_board_fixtures.py``.
AC3: scope constraint (no conftest/src changes) is verified by git diff; no failing
test state is possible for a "do NOT touch" constraint.
"""

from __future__ import annotations

import ast
import pathlib

HERE = pathlib.Path(__file__).parent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _board_src() -> tuple[str, ast.Module]:
    source = (HERE / "test_cli_board.py").read_text(encoding="utf-8")
    return source, ast.parse(source)


def _find_class(tree: ast.Module, name: str) -> ast.ClassDef | None:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == name:
            return node
    return None


# ---------------------------------------------------------------------------
# AC #2 — Happy-path migration: TestFromAC_BoardRendering and
#          TestFromAC_AssigneeDisplay use cli_board_fixtures helpers
# ---------------------------------------------------------------------------


class TestFromAC_HappyPathMigration:
    """AC2: Happy-path test classes use helpers from cli_board_fixtures."""

    def test_test_cli_board_imports_from_cli_board_fixtures(self) -> None:
        """test_cli_board.py must contain a reference to cli_board_fixtures after migration."""
        source, _ = _board_src()
        assert "cli_board_fixtures" in source, (
            "test_cli_board.py must import from cli_board_fixtures after AC2 migration"
        )

    def test_board_rendering_class_body_uses_board_task(self) -> None:
        """TestFromAC_BoardRendering test methods must call board_task (not only local _task)."""
        _, tree = _board_src()
        cls = _find_class(tree, "TestFromAC_BoardRendering")
        assert cls is not None, "TestFromAC_BoardRendering class not found in test_cli_board.py"
        body_text = ast.unparse(cls)
        assert "board_task" in body_text, (
            "TestFromAC_BoardRendering must use board_task from cli_board_fixtures"
        )

    def test_assignee_display_class_body_uses_board_task(self) -> None:
        """TestFromAC_AssigneeDisplay test methods must call board_task."""
        _, tree = _board_src()
        cls = _find_class(tree, "TestFromAC_AssigneeDisplay")
        assert cls is not None, "TestFromAC_AssigneeDisplay class not found in test_cli_board.py"
        body_text = ast.unparse(cls)
        assert "board_task" in body_text, (
            "TestFromAC_AssigneeDisplay must use board_task from cli_board_fixtures"
        )

    def test_both_happy_path_classes_use_board_task_from_same_module(self) -> None:
        """Both TestFromAC_BoardRendering and TestFromAC_AssigneeDisplay use board_task."""
        _, tree = _board_src()
        rendering = _find_class(tree, "TestFromAC_BoardRendering")
        assignee = _find_class(tree, "TestFromAC_AssigneeDisplay")
        assert rendering is not None, "TestFromAC_BoardRendering not found"
        assert assignee is not None, "TestFromAC_AssigneeDisplay not found"
        assert "board_task" in ast.unparse(rendering), (
            "TestFromAC_BoardRendering must use board_task"
        )
        assert "board_task" in ast.unparse(assignee), (
            "TestFromAC_AssigneeDisplay must use board_task"
        )


# ---------------------------------------------------------------------------
# AC #2 — Age-in-status migration: TestFromAC_AgeInStatus uses
#          board_task and board_move from cli_board_fixtures
# ---------------------------------------------------------------------------


class TestFromAC_AgeInStatusMigration:
    """AC2: TestFromAC_AgeInStatus uses board_task and board_move from cli_board_fixtures."""

    def test_age_in_status_class_body_uses_board_task(self) -> None:
        """TestFromAC_AgeInStatus test methods must call board_task."""
        _, tree = _board_src()
        cls = _find_class(tree, "TestFromAC_AgeInStatus")
        assert cls is not None, "TestFromAC_AgeInStatus class not found in test_cli_board.py"
        body_text = ast.unparse(cls)
        assert "board_task" in body_text, (
            "TestFromAC_AgeInStatus must use board_task from cli_board_fixtures"
        )

    def test_age_in_status_class_body_uses_board_move(self) -> None:
        """TestFromAC_AgeInStatus test methods must call board_move."""
        _, tree = _board_src()
        cls = _find_class(tree, "TestFromAC_AgeInStatus")
        assert cls is not None, "TestFromAC_AgeInStatus class not found in test_cli_board.py"
        body_text = ast.unparse(cls)
        assert "board_move" in body_text, (
            "TestFromAC_AgeInStatus must use board_move from cli_board_fixtures"
        )

    def test_age_in_status_uses_both_board_task_and_board_move(self) -> None:
        """TestFromAC_AgeInStatus requires both board_task and board_move to describe scenarios."""
        _, tree = _board_src()
        cls = _find_class(tree, "TestFromAC_AgeInStatus")
        assert cls is not None
        body_text = ast.unparse(cls)
        assert "board_task" in body_text, (
            "TestFromAC_AgeInStatus must use board_task from cli_board_fixtures"
        )
        assert "board_move" in body_text, (
            "TestFromAC_AgeInStatus must use board_move from cli_board_fixtures"
        )


# ---------------------------------------------------------------------------
# AC #4 — Helpers are pure functions (no subprocess, no live binary)
# ---------------------------------------------------------------------------


class TestFromAC_HelpersArePure:
    """AC4: helper functions work without mocking subprocess — they are pure Python."""

    def test_board_task_callable_without_subprocess_mock(self) -> None:
        """board_task() must complete without any subprocess or live binary call."""
        from cli_board_fixtures import board_task  # type: ignore[import-not-found]

        result = board_task()
        assert isinstance(result, dict)

    def test_board_move_callable_without_subprocess_mock(self) -> None:
        """board_move() must complete without any subprocess or live binary call."""
        from cli_board_fixtures import board_move  # type: ignore[import-not-found]

        result = board_move(task_id=1, from_status="todo", to_status="in-progress")
        assert isinstance(result, dict)

    def test_board_payloads_callable_without_subprocess_mock(self) -> None:
        """board_payloads() must complete without any subprocess or live binary call."""
        from cli_board_fixtures import (  # type: ignore[import-not-found]
            board_move,
            board_payloads,
            board_task,
        )

        task = board_task(task_id=1, status="in-progress")
        move = board_move(task_id=1, from_status="todo", to_status="in-progress")
        list_json, log_json = board_payloads(tasks=[task], moves=[move])
        assert isinstance(list_json, str)
        assert isinstance(log_json, str)


# ---------------------------------------------------------------------------
# AC #2 (strict) — Local helpers _task/_move must NOT appear in migrated classes
#
# Reviewer cycle: prior tests only verified PRESENCE of board_task/board_move
# but a partial migration would still pass. These tests enforce FULL migration
# by asserting no direct call to the local _task/_move Name nodes exist in the
# migrated class bodies.  Uses AST Call node inspection so that board_task(...)
# (a different ast.Name id) is never confused with _task(...).
# Green on arrival (builder completed migration), but provide regression
# protection if migration is ever reverted.
# ---------------------------------------------------------------------------


def _local_name_calls(cls: ast.ClassDef, func_name: str) -> list[ast.Call]:
    """Return all ast.Call nodes inside *cls* whose function is a bare Name == func_name.

    This is exact-match: board_task has id='board_task', _task has id='_task'.
    They are distinct ast.Name nodes and this helper will NOT confuse them.
    """
    return [
        node
        for node in ast.walk(cls)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == func_name
    ]


class TestFromAC_NoLocalHelpersInMigratedClasses:
    """AC2 (strict): migrated classes must NOT call local _task or _move helpers."""

    def test_board_rendering_does_not_call_local_task(self) -> None:
        """TestFromAC_BoardRendering must have zero direct _task() AST calls after migration."""
        _, tree = _board_src()
        cls = _find_class(tree, "TestFromAC_BoardRendering")
        assert cls is not None, "TestFromAC_BoardRendering not found"
        calls = _local_name_calls(cls, "_task")
        assert len(calls) == 0, (
            f"TestFromAC_BoardRendering still has {len(calls)} local _task() call(s) "
            "— migration incomplete"
        )

    def test_assignee_display_does_not_call_local_task(self) -> None:
        """TestFromAC_AssigneeDisplay must have zero direct _task() AST calls after migration."""
        _, tree = _board_src()
        cls = _find_class(tree, "TestFromAC_AssigneeDisplay")
        assert cls is not None, "TestFromAC_AssigneeDisplay not found"
        calls = _local_name_calls(cls, "_task")
        assert len(calls) == 0, (
            f"TestFromAC_AssigneeDisplay still has {len(calls)} local _task() call(s) "
            "— migration incomplete"
        )

    def test_age_in_status_does_not_call_local_task(self) -> None:
        """TestFromAC_AgeInStatus must have zero direct _task() AST calls after migration."""
        _, tree = _board_src()
        cls = _find_class(tree, "TestFromAC_AgeInStatus")
        assert cls is not None, "TestFromAC_AgeInStatus not found"
        calls = _local_name_calls(cls, "_task")
        assert len(calls) == 0, (
            f"TestFromAC_AgeInStatus still has {len(calls)} local _task() call(s) "
            "— migration incomplete"
        )

    def test_age_in_status_does_not_call_local_move(self) -> None:
        """TestFromAC_AgeInStatus must have zero direct _move() AST calls after migration."""
        _, tree = _board_src()
        cls = _find_class(tree, "TestFromAC_AgeInStatus")
        assert cls is not None, "TestFromAC_AgeInStatus not found"
        calls = _local_name_calls(cls, "_move")
        assert len(calls) == 0, (
            f"TestFromAC_AgeInStatus still has {len(calls)} local _move() call(s) "
            "— migration incomplete"
        )
