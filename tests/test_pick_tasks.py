"""Tests for pick_tasks MCP tool: gate logic, output format, null-body safety, and tag passthrough.

Consolidated from tasks #620, #621, #628.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp.server.fastmcp.exceptions import ToolError

# ---------------------------------------------------------------------------
# Import target -- will raise ImportError until builder implements #621 (RED)
# ---------------------------------------------------------------------------
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
    """Build a minimal task dict as returned by `kanban-md list --json`."""
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
    """Return a mock _run_kanban return value with the given task list."""
    return (json.dumps(list(tasks)), "", 0)


# ---------------------------------------------------------------------------
# TestFromAC_PickTasksBasicPick
# ---------------------------------------------------------------------------


class TestFromAC_PickTasksBasicPick:
    """Basic pick: tasks returned with task_id and status in dispatch format."""

    @pytest.mark.asyncio
    async def test_returns_dispatch_key(self) -> None:
        """Return value is a dict with a 'dispatch' key."""
        mcp_ctx = _make_mcp_ctx()
        t = _task(id=42, status="todo")
        with patch("owlbear_mcp_kanban.server._run_kanban", AsyncMock(return_value=_board(t))):
            result = await pick_tasks(mcp_ctx)
        assert isinstance(result, dict)
        assert "dispatch" in result

    @pytest.mark.asyncio
    async def test_dispatch_entries_have_task_id_and_status(self) -> None:
        """Each dispatch entry has task_id (int) and status (str) fields."""
        mcp_ctx = _make_mcp_ctx()
        t = _task(id=42, status="todo")
        with patch("owlbear_mcp_kanban.server._run_kanban", AsyncMock(return_value=_board(t))):
            result = await pick_tasks(mcp_ctx)
        assert len(result["dispatch"]) == 1
        entry = result["dispatch"][0]
        assert entry["task_id"] == 42
        assert entry["status"] == "todo"

    @pytest.mark.asyncio
    async def test_task_id_is_integer(self) -> None:
        """task_id in each dispatch entry is an int, not a string."""
        mcp_ctx = _make_mcp_ctx()
        t = _task(id=7)
        with patch("owlbear_mcp_kanban.server._run_kanban", AsyncMock(return_value=_board(t))):
            result = await pick_tasks(mcp_ctx)
        assert isinstance(result["dispatch"][0]["task_id"], int)

    @pytest.mark.asyncio
    async def test_multiple_statuses_all_returned(self) -> None:
        """Tasks in different statuses all appear in dispatch with correct status."""
        mcp_ctx = _make_mcp_ctx()
        t1 = _task(id=1, status="todo")
        t2 = _task(
            id=2,
            status="in-progress",
            body="## AC\n- do stuff\n## Test-Writer Notes\n- tests written",
        )
        t3 = _task(id=3, status="review")
        with patch(
            "owlbear_mcp_kanban.server._run_kanban",
            AsyncMock(return_value=_board(t1, t2, t3)),
        ):
            result = await pick_tasks(mcp_ctx)
        ids = {e["task_id"] for e in result["dispatch"]}
        assert ids == {1, 2, 3}

    @pytest.mark.asyncio
    async def test_dispatch_entry_has_only_task_id_and_status(self) -> None:
        """Dispatch entries have exactly task_id and status -- no extra fields."""
        mcp_ctx = _make_mcp_ctx()
        t = _task(id=10)
        with patch("owlbear_mcp_kanban.server._run_kanban", AsyncMock(return_value=_board(t))):
            result = await pick_tasks(mcp_ctx)
        entry = result["dispatch"][0]
        assert set(entry.keys()) == {"task_id", "status"}


# ---------------------------------------------------------------------------
# TestFromAC_PickTasksGateFiltering
# ---------------------------------------------------------------------------


class TestFromAC_PickTasksGateFiltering:
    """Gate filtering: tasks failing atomicity/TDD/clarity gates are excluded."""

    @pytest.mark.asyncio
    async def test_atomicity_gate_excludes_and_in_title(self) -> None:
        """Task with word-boundary 'and' in title fails atomicity gate, excluded."""
        mcp_ctx = _make_mcp_ctx()
        t = _task(id=1, title="Fix auth and caching")
        with patch("owlbear_mcp_kanban.server._run_kanban", AsyncMock(return_value=_board(t))):
            result = await pick_tasks(mcp_ctx)
        ids = [e["task_id"] for e in result["dispatch"]]
        assert 1 not in ids

    @pytest.mark.asyncio
    async def test_atomicity_gate_passes_word_boundary_false_positive(self) -> None:
        """'sandwich' has 'and' inside a word -- passes atomicity (word-boundary check)."""
        mcp_ctx = _make_mcp_ctx()
        t = _task(id=2, title="Implement sandwich caching")
        with patch("owlbear_mcp_kanban.server._run_kanban", AsyncMock(return_value=_board(t))):
            result = await pick_tasks(mcp_ctx)
        ids = [e["task_id"] for e in result["dispatch"]]
        assert 2 in ids

    @pytest.mark.asyncio
    async def test_tdd_gate_excludes_in_progress_without_test_writer_notes(self) -> None:
        """in-progress task without '## Test-Writer Notes' in body is excluded."""
        mcp_ctx = _make_mcp_ctx()
        t = _task(id=3, status="in-progress", body="## AC\n- do something\n")
        with patch("owlbear_mcp_kanban.server._run_kanban", AsyncMock(return_value=_board(t))):
            result = await pick_tasks(mcp_ctx)
        ids = [e["task_id"] for e in result["dispatch"]]
        assert 3 not in ids

    @pytest.mark.asyncio
    async def test_tdd_gate_passes_in_progress_with_test_writer_notes(self) -> None:
        """in-progress task with '## Test-Writer Notes' in body is included."""
        mcp_ctx = _make_mcp_ctx()
        t = _task(
            id=4,
            status="in-progress",
            body="## AC\n- do something\n## Test-Writer Notes\n- N tests, all FAIL",
        )
        with patch("owlbear_mcp_kanban.server._run_kanban", AsyncMock(return_value=_board(t))):
            result = await pick_tasks(mcp_ctx)
        ids = [e["task_id"] for e in result["dispatch"]]
        assert 4 in ids

    @pytest.mark.asyncio
    async def test_clarity_gate_excludes_todo_without_bullet_ac(self) -> None:
        """todo task with prose-only body (no bullets/numbers) fails clarity gate."""
        mcp_ctx = _make_mcp_ctx()
        t = _task(id=5, status="todo", body="This task does something important but no bullets")
        with patch("owlbear_mcp_kanban.server._run_kanban", AsyncMock(return_value=_board(t))):
            result = await pick_tasks(mcp_ctx)
        ids = [e["task_id"] for e in result["dispatch"]]
        assert 5 not in ids

    @pytest.mark.asyncio
    async def test_clarity_gate_passes_todo_with_bullet_ac(self) -> None:
        """todo task with bullet AC passes clarity gate and is included."""
        mcp_ctx = _make_mcp_ctx()
        t = _task(id=6, status="todo", body="## AC\n- must do this\n- must do that")
        with patch("owlbear_mcp_kanban.server._run_kanban", AsyncMock(return_value=_board(t))):
            result = await pick_tasks(mcp_ctx)
        ids = [e["task_id"] for e in result["dispatch"]]
        assert 6 in ids

    @pytest.mark.asyncio
    async def test_clarity_gate_exempt_for_research(self) -> None:
        """research task without bullet AC still passes (pre-pipeline status exempt)."""
        mcp_ctx = _make_mcp_ctx()
        t = _task(id=7, status="research", body="Just a raw idea, no AC yet")
        with patch("owlbear_mcp_kanban.server._run_kanban", AsyncMock(return_value=_board(t))):
            result = await pick_tasks(mcp_ctx)
        ids = [e["task_id"] for e in result["dispatch"]]
        assert 7 in ids

    @pytest.mark.asyncio
    async def test_clarity_gate_passes_numbered_ac(self) -> None:
        """todo task with numbered-list AC passes clarity gate."""
        mcp_ctx = _make_mcp_ctx()
        t = _task(id=8, status="todo", body="1. step one\n2. step two\n")
        with patch("owlbear_mcp_kanban.server._run_kanban", AsyncMock(return_value=_board(t))):
            result = await pick_tasks(mcp_ctx)
        ids = [e["task_id"] for e in result["dispatch"]]
        assert 8 in ids


# ---------------------------------------------------------------------------
# TestFromAC_PickTasksLimit
# ---------------------------------------------------------------------------


class TestFromAC_PickTasksLimit:
    """Limit: limit=5 caps output at 5; default limit is 25."""

    @pytest.mark.asyncio
    async def test_limit_5_returns_at_most_5(self) -> None:
        """limit=5 with 10 passing tasks yields at most 5 dispatch entries."""
        mcp_ctx = _make_mcp_ctx()
        tasks = [_task(id=i, title=f"Task {i}") for i in range(1, 11)]
        with patch(
            "owlbear_mcp_kanban.server._run_kanban",
            AsyncMock(return_value=_board(*tasks)),
        ):
            result = await pick_tasks(mcp_ctx, limit=5)
        assert len(result["dispatch"]) <= 5

    @pytest.mark.asyncio
    async def test_limit_5_returns_exactly_5_when_available(self) -> None:
        """limit=5 with 10 passing tasks yields exactly 5 dispatch entries."""
        mcp_ctx = _make_mcp_ctx()
        tasks = [_task(id=i, title=f"Task {i}") for i in range(1, 11)]
        with patch(
            "owlbear_mcp_kanban.server._run_kanban",
            AsyncMock(return_value=_board(*tasks)),
        ):
            result = await pick_tasks(mcp_ctx, limit=5)
        assert len(result["dispatch"]) == 5

    @pytest.mark.asyncio
    async def test_default_limit_caps_at_25(self) -> None:
        """With 30 passing tasks and no limit arg, exactly 25 are returned."""
        mcp_ctx = _make_mcp_ctx()
        tasks = [_task(id=i, title=f"Task {i}") for i in range(1, 31)]
        with patch(
            "owlbear_mcp_kanban.server._run_kanban",
            AsyncMock(return_value=_board(*tasks)),
        ):
            result = await pick_tasks(mcp_ctx)
        assert len(result["dispatch"]) == 25

    @pytest.mark.asyncio
    async def test_default_limit_not_exceeded(self) -> None:
        """With 30 passing tasks and no limit arg, at most 25 are returned."""
        mcp_ctx = _make_mcp_ctx()
        tasks = [_task(id=i, title=f"Task {i}") for i in range(1, 31)]
        with patch(
            "owlbear_mcp_kanban.server._run_kanban",
            AsyncMock(return_value=_board(*tasks)),
        ):
            result = await pick_tasks(mcp_ctx)
        assert len(result["dispatch"]) <= 25


# ---------------------------------------------------------------------------
# TestFromAC_PickTasksSortOrder
# ---------------------------------------------------------------------------


class TestFromAC_PickTasksSortOrder:
    """Sort order: critical+done-adjacent tasks before someday+research."""

    @pytest.mark.asyncio
    async def test_critical_before_someday(self) -> None:
        """critical priority task appears before someday priority in dispatch."""
        mcp_ctx = _make_mcp_ctx()
        t_someday = _task(id=1, priority="someday", title="A someday task")
        t_critical = _task(id=2, priority="critical", title="A critical task")
        with patch(
            "owlbear_mcp_kanban.server._run_kanban",
            AsyncMock(return_value=_board(t_someday, t_critical)),
        ):
            result = await pick_tasks(mcp_ctx)
        ids = [e["task_id"] for e in result["dispatch"]]
        assert ids.index(2) < ids.index(1)

    @pytest.mark.asyncio
    async def test_review_before_research(self) -> None:
        """review status (done-adjacent) appears before research in dispatch."""
        mcp_ctx = _make_mcp_ctx()
        t_research = _task(id=1, status="research", title="A research task", body="raw idea")
        t_review = _task(id=2, status="review", title="A review task")
        with patch(
            "owlbear_mcp_kanban.server._run_kanban",
            AsyncMock(return_value=_board(t_research, t_review)),
        ):
            result = await pick_tasks(mcp_ctx)
        ids = [e["task_id"] for e in result["dispatch"]]
        assert ids.index(2) < ids.index(1)

    @pytest.mark.asyncio
    async def test_sort_by_priority_rank_then_status_rank(self) -> None:
        """Sort key (PRIORITY_RANK, STATUS_RANK) asc -- critical/done before needed/todo."""
        mcp_ctx = _make_mcp_ctx()
        t_needed_todo = _task(id=1, priority="needed", status="todo")
        t_critical_done = _task(id=2, priority="critical", status="done")
        with patch(
            "owlbear_mcp_kanban.server._run_kanban",
            AsyncMock(return_value=_board(t_needed_todo, t_critical_done)),
        ):
            result = await pick_tasks(mcp_ctx)
        ids = [e["task_id"] for e in result["dispatch"]]
        assert ids.index(2) < ids.index(1)


# ---------------------------------------------------------------------------
# TestFromAC_PickTasksEdgeCases
# ---------------------------------------------------------------------------


class TestFromAC_PickTasksEdgeCases:
    """Edge cases: empty board, all-gates-fail, error handling."""

    @pytest.mark.asyncio
    async def test_empty_board_returns_empty_dispatch(self) -> None:
        """Empty board yields {'dispatch': []}."""
        mcp_ctx = _make_mcp_ctx()
        with patch(
            "owlbear_mcp_kanban.server._run_kanban",
            AsyncMock(return_value=("[]", "", 0)),
        ):
            result = await pick_tasks(mcp_ctx)
        assert result == {"dispatch": []}

    @pytest.mark.asyncio
    async def test_all_gates_fail_returns_empty_dispatch(self) -> None:
        """When all tasks fail gates, dispatch list is empty."""
        mcp_ctx = _make_mcp_ctx()
        t = _task(id=1, title="Fix login and register flow")  # atomicity fail
        with patch("owlbear_mcp_kanban.server._run_kanban", AsyncMock(return_value=_board(t))):
            result = await pick_tasks(mcp_ctx)
        assert result == {"dispatch": []}

    @pytest.mark.asyncio
    async def test_nonzero_rc_raises_tool_error(self) -> None:
        """When _run_kanban returns rc!=0, pick_tasks raises ToolError."""
        mcp_ctx = _make_mcp_ctx()
        with patch(
            "owlbear_mcp_kanban.server._run_kanban",
            AsyncMock(return_value=("", "kanban-md: board not found", 1)),
        ), pytest.raises(ToolError):
            await pick_tasks(mcp_ctx)

    @pytest.mark.asyncio
    async def test_malformed_json_raises_tool_error(self) -> None:
        """When _run_kanban returns invalid JSON, pick_tasks raises ToolError."""
        mcp_ctx = _make_mcp_ctx()
        with patch(
            "owlbear_mcp_kanban.server._run_kanban",
            AsyncMock(return_value=("{not-valid-json", "", 0)),
        ), pytest.raises(ToolError):
            await pick_tasks(mcp_ctx)


# ---------------------------------------------------------------------------
# TestFromAC_PickTasksBoardFlags
# ---------------------------------------------------------------------------


class TestFromAC_PickTasksBoardFlags:
    """Board flags: _run_kanban called with correct exclusion flags."""

    @pytest.mark.asyncio
    async def test_calls_run_kanban_exactly_once(self) -> None:
        """pick_tasks calls _run_kanban exactly once for the board read."""
        mcp_ctx = _make_mcp_ctx()
        mock_run = AsyncMock(return_value=("[]", "", 0))
        with patch("owlbear_mcp_kanban.server._run_kanban", mock_run):
            await pick_tasks(mcp_ctx)
        assert mock_run.call_count == 1

    @pytest.mark.asyncio
    async def test_passes_unblocked_flag(self) -> None:
        """pick_tasks passes --unblocked to _run_kanban."""
        mcp_ctx = _make_mcp_ctx()
        mock_run = AsyncMock(return_value=("[]", "", 0))
        with patch("owlbear_mcp_kanban.server._run_kanban", mock_run):
            await pick_tasks(mcp_ctx)
        call_positional = mock_run.call_args[0]
        assert "--unblocked" in call_positional

    @pytest.mark.asyncio
    async def test_passes_not_blocked_flag(self) -> None:
        """pick_tasks passes --not-blocked to _run_kanban."""
        mcp_ctx = _make_mcp_ctx()
        mock_run = AsyncMock(return_value=("[]", "", 0))
        with patch("owlbear_mcp_kanban.server._run_kanban", mock_run):
            await pick_tasks(mcp_ctx)
        call_positional = mock_run.call_args[0]
        assert "--not-blocked" in call_positional

    @pytest.mark.asyncio
    async def test_passes_unclaimed_flag(self) -> None:
        """pick_tasks passes --unclaimed to _run_kanban."""
        mcp_ctx = _make_mcp_ctx()
        mock_run = AsyncMock(return_value=("[]", "", 0))
        with patch("owlbear_mcp_kanban.server._run_kanban", mock_run):
            await pick_tasks(mcp_ctx)
        call_positional = mock_run.call_args[0]
        assert "--unclaimed" in call_positional

    @pytest.mark.asyncio
    async def test_does_not_pass_archived_flag(self) -> None:
        """pick_tasks does NOT pass --archived (archived excluded by default)."""
        mcp_ctx = _make_mcp_ctx()
        mock_run = AsyncMock(return_value=("[]", "", 0))
        with patch("owlbear_mcp_kanban.server._run_kanban", mock_run):
            await pick_tasks(mcp_ctx)
        call_positional = mock_run.call_args[0]
        assert "--archived" not in call_positional

    @pytest.mark.asyncio
    async def test_passes_json_flag(self) -> None:
        """pick_tasks passes --json to _run_kanban for structured output."""
        mcp_ctx = _make_mcp_ctx()
        mock_run = AsyncMock(return_value=("[]", "", 0))
        with patch("owlbear_mcp_kanban.server._run_kanban", mock_run):
            await pick_tasks(mcp_ctx)
        call_positional = mock_run.call_args[0]
        assert "--json" in call_positional


# ---------------------------------------------------------------------------
# Null-body safety (from #621)
# ---------------------------------------------------------------------------


class TestPickTasksNullBodySafety:
    """pick_tasks handles body=None in raw JSON without raising TypeError."""

    @pytest.mark.asyncio
    async def test_todo_null_body_does_not_raise(self) -> None:
        mcp_ctx = _make_mcp_ctx()
        t = _task(id=1, status="todo", body=None)
        with patch("owlbear_mcp_kanban.server._run_kanban", AsyncMock(return_value=_board(t))):
            result = await pick_tasks(mcp_ctx)
        assert "dispatch" in result

    @pytest.mark.asyncio
    async def test_in_progress_null_body_does_not_raise(self) -> None:
        mcp_ctx = _make_mcp_ctx()
        t = _task(id=2, status="in-progress", body=None)
        with patch("owlbear_mcp_kanban.server._run_kanban", AsyncMock(return_value=_board(t))):
            result = await pick_tasks(mcp_ctx)
        assert "dispatch" in result

    @pytest.mark.asyncio
    async def test_in_progress_null_body_fails_tdd_gate(self) -> None:
        mcp_ctx = _make_mcp_ctx()
        t = _task(id=3, status="in-progress", body=None)
        with patch("owlbear_mcp_kanban.server._run_kanban", AsyncMock(return_value=_board(t))):
            result = await pick_tasks(mcp_ctx)
        ids = [e["task_id"] for e in result["dispatch"]]
        assert 3 not in ids

    @pytest.mark.asyncio
    async def test_todo_null_body_fails_clarity_gate(self) -> None:
        mcp_ctx = _make_mcp_ctx()
        t = _task(id=4, status="todo", body=None)
        with patch("owlbear_mcp_kanban.server._run_kanban", AsyncMock(return_value=_board(t))):
            result = await pick_tasks(mcp_ctx)
        ids = [e["task_id"] for e in result["dispatch"]]
        assert 4 not in ids


# ---------------------------------------------------------------------------
# Tag passthrough (from #628)
# ---------------------------------------------------------------------------


class TestPickTasksTagPassthrough:
    """When tag is non-empty, --tag {value} is appended to _run_kanban args."""

    @pytest.mark.asyncio
    async def test_tag_flag_passed_when_tag_provided(self) -> None:
        mcp_ctx = _make_mcp_ctx()
        mock_run = AsyncMock(return_value=_board())
        with patch("owlbear_mcp_kanban.server._run_kanban", mock_run):
            await pick_tasks(mcp_ctx, tag="phase-2")
        positional_args = mock_run.call_args[0]
        assert "--tag" in positional_args

    @pytest.mark.asyncio
    async def test_tag_value_passed_after_flag(self) -> None:
        mcp_ctx = _make_mcp_ctx()
        mock_run = AsyncMock(return_value=_board())
        with patch("owlbear_mcp_kanban.server._run_kanban", mock_run):
            await pick_tasks(mcp_ctx, tag="phase-2")
        positional_args = list(mock_run.call_args[0])
        tag_index = positional_args.index("--tag")
        assert positional_args[tag_index + 1] == "phase-2"

    @pytest.mark.asyncio
    async def test_tag_with_colon_passed_literally(self) -> None:
        mcp_ctx = _make_mcp_ctx()
        mock_run = AsyncMock(return_value=_board())
        with patch("owlbear_mcp_kanban.server._run_kanban", mock_run):
            await pick_tasks(mcp_ctx, tag="scope:mcp")
        positional_args = list(mock_run.call_args[0])
        assert "scope:mcp" in positional_args

    @pytest.mark.asyncio
    async def test_empty_tag_omits_flag(self) -> None:
        mcp_ctx = _make_mcp_ctx()
        mock_run = AsyncMock(return_value=_board())
        with patch("owlbear_mcp_kanban.server._run_kanban", mock_run):
            await pick_tasks(mcp_ctx, tag="")
        positional_args = mock_run.call_args[0]
        assert "--tag" not in positional_args
