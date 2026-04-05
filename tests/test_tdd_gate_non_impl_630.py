"""Failing tests for task #630: TDD gate non-impl pass-through tag exemption.

Covers AC lines 4 and 5:
  - check_tdd() returns True for in-progress tasks tagged with a non-impl
    pass-through tag (research, docs, type:config, type:docs, test, type:test,
    agent, quality) even without '## Test-Writer Notes' in the body.
  - _check_pick_gates() / pick_tasks: in-progress tasks with a non-impl tag and
    no '## Test-Writer Notes' are NOT excluded from the dispatch list.

All tests FAIL in RED phase -- neither gates.py nor server.py implement the
_NON_IMPL_TAGS intersection check yet.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlbear.planner.gates import check_tdd  # type: ignore[import]
from owlbear.planner.models import Task  # type: ignore[import]
from owlbear_mcp_kanban.server import AppContext, pick_tasks  # type: ignore[import]

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_BASE_TASK: dict[str, Any] = {
    "id": 1,
    "title": "Implement feature",
    "status": "todo",
    "priority": "important",
    "created": "2026-01-01T00:00:00+00:00",
    "updated": "2026-01-01T00:00:00+00:00",
    "tags": [],
    "depends_on": [],
    "class": "standard",
    "body": "## Acceptance Criteria\n- [ ] item",
    "file": "/kanban/tasks/1-task.md",
}


def _task(**overrides: Any) -> Task:
    return Task.model_validate({**_BASE_TASK, **overrides})


_BASE_DICT: dict[str, Any] = {
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
# TestFromAC_CheckTDD_NonImplTagExemption
# ---------------------------------------------------------------------------


class TestFromAC_CheckTDD_NonImplTagExemption:
    """Contract tests for check_tdd() non-impl tag exemption (AC #630 line 4).

    An in-progress task whose tags intersect {research, docs, type:config,
    type:docs, test, type:test, agent, quality} must return True from
    check_tdd() even when '## Test-Writer Notes' is absent from the body.
    """

    def test_quality_tag_in_progress_no_tdd_notes_passes(self) -> None:
        """in-progress task tagged 'quality' without TW notes returns True."""
        task = _task(status="in-progress", tags=["quality"], body="## AC\n- do something")
        assert check_tdd(task) is True

    def test_research_tag_in_progress_no_tdd_notes_passes(self) -> None:
        """in-progress task tagged 'research' without TW notes returns True."""
        task = _task(status="in-progress", tags=["research"], body="## AC\n- do something")
        assert check_tdd(task) is True

    def test_docs_tag_in_progress_no_tdd_notes_passes(self) -> None:
        """in-progress task tagged 'docs' without TW notes returns True."""
        task = _task(status="in-progress", tags=["docs"], body="## AC\n- do something")
        assert check_tdd(task) is True

    def test_agent_tag_in_progress_no_tdd_notes_passes(self) -> None:
        """in-progress task tagged 'agent' without TW notes returns True."""
        task = _task(status="in-progress", tags=["agent"], body="## AC\n- do something")
        assert check_tdd(task) is True

    def test_type_test_tag_in_progress_no_tdd_notes_passes(self) -> None:
        """in-progress task tagged 'type:test' without TW notes returns True."""
        task = _task(status="in-progress", tags=["type:test"], body="## AC\n- do something")
        assert check_tdd(task) is True

    def test_type_config_tag_in_progress_no_tdd_notes_passes(self) -> None:
        """in-progress task tagged 'type:config' without TW notes returns True."""
        task = _task(status="in-progress", tags=["type:config"], body="## AC\n- do something")
        assert check_tdd(task) is True

    def test_type_docs_tag_in_progress_no_tdd_notes_passes(self) -> None:
        """in-progress task tagged 'type:docs' without TW notes returns True."""
        task = _task(status="in-progress", tags=["type:docs"], body="## AC\n- do something")
        assert check_tdd(task) is True

    def test_test_tag_in_progress_no_tdd_notes_passes(self) -> None:
        """in-progress task tagged 'test' without TW notes returns True."""
        task = _task(status="in-progress", tags=["test"], body="## AC\n- do something")
        assert check_tdd(task) is True

    def test_mixed_tags_one_non_impl_in_progress_no_tdd_notes_passes(self) -> None:
        """in-progress + tags [quality, scope:mcp, phase-2] -- intersection non-empty, passes."""
        task = _task(
            status="in-progress",
            tags=["quality", "scope:mcp", "phase-2"],
            body="## AC\n- do something",
        )
        assert check_tdd(task) is True


# ---------------------------------------------------------------------------
# TestFromAC_PickTasksNonImplTDDExemption
# ---------------------------------------------------------------------------


class TestFromAC_PickTasksNonImplTDDExemption:
    """Gate filtering: non-impl-tagged in-progress tasks are NOT excluded (AC #630 line 5).

    in-progress tasks with a non-impl pass-through tag (quality, research, docs,
    type:config, type:docs, test, type:test, agent) must pass _check_pick_gates()
    even without '## Test-Writer Notes' in the body, and appear in the dispatch list.
    """

    @pytest.mark.asyncio
    async def test_quality_tag_in_progress_no_tdd_notes_not_excluded(self) -> None:
        """in-progress task tagged 'quality' without TW notes is included in dispatch."""
        mcp_ctx = _make_mcp_ctx()
        t = _task_dict(id=901, status="in-progress", tags=["quality"], body="## AC\n- do something")
        with patch("owlbear_mcp_kanban.server._run_kanban", AsyncMock(return_value=_board(t))):
            result = await pick_tasks(mcp_ctx)
        ids = [e["task_id"] for e in result["dispatch"]]
        assert 901 in ids

    @pytest.mark.asyncio
    async def test_research_tag_in_progress_no_tdd_notes_not_excluded(self) -> None:
        """in-progress task tagged 'research' without TW notes is included in dispatch."""
        mcp_ctx = _make_mcp_ctx()
        t = _task_dict(id=902, status="in-progress", tags=["research"], body="## AC\n- do something")
        with patch("owlbear_mcp_kanban.server._run_kanban", AsyncMock(return_value=_board(t))):
            result = await pick_tasks(mcp_ctx)
        ids = [e["task_id"] for e in result["dispatch"]]
        assert 902 in ids

    @pytest.mark.asyncio
    async def test_agent_tag_in_progress_no_tdd_notes_not_excluded(self) -> None:
        """in-progress task tagged 'agent' without TW notes is included in dispatch."""
        mcp_ctx = _make_mcp_ctx()
        t = _task_dict(id=903, status="in-progress", tags=["agent"], body="## AC\n- do something")
        with patch("owlbear_mcp_kanban.server._run_kanban", AsyncMock(return_value=_board(t))):
            result = await pick_tasks(mcp_ctx)
        ids = [e["task_id"] for e in result["dispatch"]]
        assert 903 in ids

    @pytest.mark.asyncio
    async def test_type_test_tag_in_progress_no_tdd_notes_not_excluded(self) -> None:
        """in-progress task tagged 'type:test' without TW notes is included in dispatch."""
        mcp_ctx = _make_mcp_ctx()
        t = _task_dict(id=904, status="in-progress", tags=["type:test"], body="## AC\n- do something")
        with patch("owlbear_mcp_kanban.server._run_kanban", AsyncMock(return_value=_board(t))):
            result = await pick_tasks(mcp_ctx)
        ids = [e["task_id"] for e in result["dispatch"]]
        assert 904 in ids

    @pytest.mark.asyncio
    async def test_docs_tag_in_progress_no_tdd_notes_not_excluded(self) -> None:
        """in-progress task tagged 'docs' without TW notes is included in dispatch."""
        mcp_ctx = _make_mcp_ctx()
        t = _task_dict(id=905, status="in-progress", tags=["docs"], body="## AC\n- do something")
        with patch("owlbear_mcp_kanban.server._run_kanban", AsyncMock(return_value=_board(t))):
            result = await pick_tasks(mcp_ctx)
        ids = [e["task_id"] for e in result["dispatch"]]
        assert 905 in ids

    @pytest.mark.asyncio
    async def test_mixed_tags_one_non_impl_in_progress_no_tdd_notes_not_excluded(self) -> None:
        """in-progress + tags [quality, scope:mcp, phase-2] is included -- tag intersection."""
        mcp_ctx = _make_mcp_ctx()
        t = _task_dict(
            id=906,
            status="in-progress",
            tags=["quality", "scope:mcp", "phase-2"],
            body="## AC\n- do something",
        )
        with patch("owlbear_mcp_kanban.server._run_kanban", AsyncMock(return_value=_board(t))):
            result = await pick_tasks(mcp_ctx)
        ids = [e["task_id"] for e in result["dispatch"]]
        assert 906 in ids
