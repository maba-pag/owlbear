"""Failing tests for task #661: type:user-action NON_IMPL_TAGS gate exemption.

Covers:
  - "type:user-action" must be present in _NON_IMPL_TAGS (gates.py) so that
    check_tdd() exempts tagged tasks from the Test-Writer Notes requirement.
  - "type:user-action" must be present in _PICK_NON_IMPL_TAGS (server.py) so
    that _check_pick_gates() / pick_tasks does not exclude them.
  - The orchestrator therefore recognises the type:user-action convention and
    does not block dispatch of those tasks solely due to absent TDD notes.

All tests FAIL in the RED phase -- neither gates.py nor server.py contain
"type:user-action" in their respective frozensets yet.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlbear.planner.gates import _NON_IMPL_TAGS, check_tdd  # type: ignore[import]
from owlbear.planner.models import Task  # type: ignore[import]
from owlbear_mcp_kanban.server import (  # type: ignore[import]
    AppContext,
    _PICK_NON_IMPL_TAGS,
    pick_tasks,
)

# ---------------------------------------------------------------------------
# Shared helpers (mirrored from test_tdd_gate_non_impl_630.py conventions)
# ---------------------------------------------------------------------------

_BASE_TASK: dict[str, Any] = {
    "id": 1,
    "title": "Verify teams GUI change",
    "status": "todo",
    "priority": "important",
    "created": "2026-01-01T00:00:00+00:00",
    "updated": "2026-01-01T00:00:00+00:00",
    "tags": [],
    "depends_on": [],
    "class": "standard",
    "body": "## Acceptance Criteria\n- [ ] manually verify X in Teams GUI",
    "file": "/kanban/tasks/1-task.md",
}


def _task(**overrides: Any) -> Task:
    return Task.model_validate({**_BASE_TASK, **overrides})


_BASE_DICT: dict[str, Any] = {
    "id": 1,
    "title": "Verify teams GUI change",
    "status": "todo",
    "priority": "important",
    "created": "2026-01-01T00:00:00+00:00",
    "updated": "2026-01-01T00:00:00+00:00",
    "tags": [],
    "depends_on": [],
    "class": "standard",
    "body": "## AC\n- manually verify\n",
    "file": "/kanban/tasks/1-user-action.md",
    "blocked": False,
    "block_reason": None,
    "claimed_by": None,
}


def _task_dict(**overrides: Any) -> dict:
    return {**_BASE_DICT, **overrides}


def _board(*tasks: dict) -> tuple[str, str, int]:
    return (json.dumps(list(tasks)), "", 0)


def _make_app_ctx() -> AppContext:
    return AppContext(kanban_bin=Path("/fake/kanban-md"), kanban_dir=Path("/fake/kanban"))


def _make_mcp_ctx(app_ctx: AppContext | None = None) -> MagicMock:
    ctx = MagicMock()
    ctx.request_context.lifespan_context = app_ctx or _make_app_ctx()
    return ctx


# ---------------------------------------------------------------------------
# TestFromAC_UserActionNonImplFrozensets
# ---------------------------------------------------------------------------


class TestFromAC_UserActionNonImplFrozensets:
    """Direct membership: 'type:user-action' must exist in both frozensets.

    Tests verify the convention is registered at the data level -- the tag
    string is present in the authoritative gate sets.  Both fail until
    gates.py and server.py are updated.
    """

    def test_type_user_action_in_non_impl_tags_gates(self) -> None:
        """'type:user-action' is a member of _NON_IMPL_TAGS in gates.py."""
        assert "type:user-action" in _NON_IMPL_TAGS

    def test_type_user_action_in_pick_non_impl_tags_server(self) -> None:
        """'type:user-action' is a member of _PICK_NON_IMPL_TAGS in server.py."""
        assert "type:user-action" in _PICK_NON_IMPL_TAGS


# ---------------------------------------------------------------------------
# TestFromAC_CheckTDD_UserActionExemption
# ---------------------------------------------------------------------------


class TestFromAC_CheckTDD_UserActionExemption:
    """check_tdd() must return True for in-progress type:user-action tasks.

    The TDD gate must not require '## Test-Writer Notes' for tasks tagged
    type:user-action -- these are user-action-required tasks with no testable
    Python interface.  All tests target status=in-progress (the only status
    where TDD gate applies) and omit TW notes to isolate new tag behaviour.
    """

    def test_user_action_tag_in_progress_no_tdd_notes_passes(self) -> None:
        """in-progress task tagged 'type:user-action' without TW notes returns True."""
        task = _task(
            status="in-progress",
            tags=["type:user-action"],
            body="## AC\n- manually verify X in GUI",
        )
        assert check_tdd(task) is True

    def test_user_action_combined_with_scope_tag_passes(self) -> None:
        """in-progress + ['type:user-action', 'scope:teams', 'phase-3'] returns True."""
        task = _task(
            status="in-progress",
            tags=["type:user-action", "scope:teams", "phase-3"],
            body="## AC\n- manually verify",
        )
        assert check_tdd(task) is True

    def test_user_action_only_tag_empty_body_in_progress_passes(self) -> None:
        """Boundary: in-progress type:user-action with minimal body (no AC) still exempted."""
        task = _task(
            status="in-progress",
            tags=["type:user-action"],
            body="no structured content here",
        )
        assert check_tdd(task) is True


# ---------------------------------------------------------------------------
# TestFromAC_PickTasksUserActionExemption
# ---------------------------------------------------------------------------


class TestFromAC_PickTasksUserActionExemption:
    """pick_tasks dispatch: in-progress type:user-action tasks must not be excluded.

    _check_pick_gates() must exempt 'type:user-action' tagged tasks from the
    TDD gate so they appear in the pick_tasks dispatch list even without
    '## Test-Writer Notes'.
    """

    @pytest.mark.asyncio
    async def test_user_action_in_progress_no_tdd_notes_included_in_dispatch(self) -> None:
        """in-progress task tagged 'type:user-action' without TW notes appears in dispatch."""
        mcp_ctx = _make_mcp_ctx()
        t = _task_dict(
            id=910,
            status="in-progress",
            tags=["type:user-action"],
            body="## AC\n- manually verify",
        )
        with patch("owlbear_mcp_kanban.server._run_kanban", AsyncMock(return_value=_board(t))):
            result = await pick_tasks(mcp_ctx)
        ids = [e["task_id"] for e in result["dispatch"]]
        assert 910 in ids

    @pytest.mark.asyncio
    async def test_user_action_combined_with_scope_tag_included_in_dispatch(self) -> None:
        """in-progress + ['type:user-action', 'scope:teams', 'phase-3'] without TW notes included."""
        mcp_ctx = _make_mcp_ctx()
        t = _task_dict(
            id=911,
            status="in-progress",
            tags=["type:user-action", "scope:teams", "phase-3"],
            body="## AC\n- manually verify",
        )
        with patch("owlbear_mcp_kanban.server._run_kanban", AsyncMock(return_value=_board(t))):
            result = await pick_tasks(mcp_ctx)
        ids = [e["task_id"] for e in result["dispatch"]]
        assert 911 in ids
