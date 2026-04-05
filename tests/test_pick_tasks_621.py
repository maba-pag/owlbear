"""Failing tests for task #621: pick_tasks null-body safety gap.

Covers AC items from #621 not tested in #620:
  - Null body safety: task with body=None in raw JSON does not crash pick_tasks
  - Applies to in-progress TDD gate (body in check)
  - Applies to active-status clarity gate (regex.search on body)
  - Key Findings for #621 specified: use task.get("body") or "" not task.get("body", "")
  - Current implementation uses task.get("body", "") which returns None when the key
    exists with a null value -- crashing both the TDD gate and the clarity gate.

All tests FAIL in RED phase -- _check_pick_gates crashes on body=None.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlbear_mcp_kanban.server import (  # type: ignore[import]
    AppContext,
    pick_tasks,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_app_ctx() -> AppContext:
    return AppContext(kanban_bin=Path("/fake/kanban-md"), kanban_dir=Path("/fake/kanban"))


def _make_mcp_ctx(app_ctx: AppContext | None = None) -> MagicMock:
    ctx = MagicMock()
    ctx.request_context.lifespan_context = app_ctx or _make_app_ctx()
    return ctx


def _task(**overrides: object) -> dict:
    """Build a minimal task dict matching kanban-md list --json output."""
    base: dict = {
        "id": 1,
        "title": "Implement feature",
        "status": "todo",
        "priority": "important",
        "created": "2026-01-01T00:00:00+00:00",
        "updated": "2026-01-01T00:00:00+00:00",
        "tags": [],
        "depends_on": [],
        "class": "standard",
        "body": "## AC\n- do something\n",
        "file": "/kanban/tasks/1-impl.md",
        "blocked": False,
        "block_reason": None,
        "claimed_by": None,
    }
    return {**base, **overrides}


def _board(*tasks: dict) -> tuple[str, str, int]:
    return (json.dumps(list(tasks)), "", 0)


# ---------------------------------------------------------------------------
# TestFromAC_PickTasksNullBodySafety
# ---------------------------------------------------------------------------


class TestFromAC_PickTasksNullBodySafety:
    """pick_tasks handles body=None in raw JSON without raising TypeError.

    KanbanTask.body is str|None (see models.py). kanban-md list --json emits
    "body": null for tasks with no body text. The Key Findings for #621 stated:
      'use task.get("body") or "" in gates'
    The current implementation uses task.get("body", "") which returns None when
    the key is present with a null value -- crashing both the TDD gate (via
    "'## Test-Writer Notes' not in None") and the clarity gate (via
    "regex.search(None)") with TypeError.
    """

    @pytest.mark.asyncio
    async def test_todo_null_body_does_not_raise(self) -> None:
        """todo task with body=None in JSON does not crash pick_tasks."""
        mcp_ctx = _make_mcp_ctx()
        t = _task(id=1, status="todo", body=None)
        with patch("owlbear_mcp_kanban.server._run_kanban", AsyncMock(return_value=_board(t))):
            # Must not raise TypeError from clarity gate on None body
            result = await pick_tasks(mcp_ctx)
        assert "dispatch" in result

    @pytest.mark.asyncio
    async def test_in_progress_null_body_does_not_raise(self) -> None:
        """in-progress task with body=None does not crash pick_tasks on TDD gate."""
        mcp_ctx = _make_mcp_ctx()
        t = _task(id=2, status="in-progress", body=None)
        with patch("owlbear_mcp_kanban.server._run_kanban", AsyncMock(return_value=_board(t))):
            # Must not raise TypeError from '## Test-Writer Notes' not in None
            result = await pick_tasks(mcp_ctx)
        assert "dispatch" in result

    @pytest.mark.asyncio
    async def test_in_progress_null_body_fails_tdd_gate(self) -> None:
        """in-progress task with body=None fails TDD gate (no Test-Writer Notes)."""
        mcp_ctx = _make_mcp_ctx()
        t = _task(id=3, status="in-progress", body=None)
        with patch("owlbear_mcp_kanban.server._run_kanban", AsyncMock(return_value=_board(t))):
            result = await pick_tasks(mcp_ctx)
        ids = [e["task_id"] for e in result["dispatch"]]
        assert 3 not in ids

    @pytest.mark.asyncio
    async def test_todo_null_body_fails_clarity_gate(self) -> None:
        """todo task with body=None fails clarity gate (no bullet AC found)."""
        mcp_ctx = _make_mcp_ctx()
        t = _task(id=4, status="todo", body=None)
        with patch("owlbear_mcp_kanban.server._run_kanban", AsyncMock(return_value=_board(t))):
            result = await pick_tasks(mcp_ctx)
        ids = [e["task_id"] for e in result["dispatch"]]
        assert 4 not in ids

    @pytest.mark.asyncio
    async def test_review_null_body_does_not_raise(self) -> None:
        """review task with body=None does not crash pick_tasks on clarity gate."""
        mcp_ctx = _make_mcp_ctx()
        t = _task(id=5, status="review", body=None)
        with patch("owlbear_mcp_kanban.server._run_kanban", AsyncMock(return_value=_board(t))):
            result = await pick_tasks(mcp_ctx)
        assert "dispatch" in result

    @pytest.mark.asyncio
    async def test_mixed_board_null_body_excluded_valid_passes(self) -> None:
        """Board with null-body todo and valid todo: null-body excluded, valid passes."""
        mcp_ctx = _make_mcp_ctx()
        t_null = _task(id=10, status="todo", body=None)
        t_valid = _task(id=11, status="todo", body="## AC\n- item\n")
        with patch(
            "owlbear_mcp_kanban.server._run_kanban",
            AsyncMock(return_value=_board(t_null, t_valid)),
        ):
            result = await pick_tasks(mcp_ctx)
        ids = [e["task_id"] for e in result["dispatch"]]
        assert 10 not in ids
        assert 11 in ids
