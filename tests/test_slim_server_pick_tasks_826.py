"""Tests for task #826: slim server pick_tasks to thin wrapper (TDD RED).

AC coverage:
  - AC1 (gap): pick_tasks calls pick_dispatchable with engine as first positional arg  [1 RED]
  - AC2 (gap): _PICK_MAX_PRIORITY_RANK and _PICK_MAX_STATUS_RANK removed from server.py  [2 RED]
  - AC4: boundary conversion — Task objects from pick_dispatchable formatted to dispatch dict  [4 RED]

Gap rationale:
  - #825 covers AC1 base (delegation, limit, tag kwarg) and AC2 base (_check_pick_gates,
    _PICK_PRIORITY_RANK, _PICK_STATUS_RANK, _PICK_AC_PATTERN, _PICK_CLARITY_STATUSES,
    _PICK_NON_IMPL_TAGS). Two symbols omitted by #825: _PICK_MAX_PRIORITY_RANK and
    _PICK_MAX_STATUS_RANK — covered here.
  - #825 AC3/AC4 tests verify format via engine.list_tasks mock (current code path).
    After refactoring those tests need pick_dispatchable mock — covered here as the
    canonical post-refactor regression guards (AC4 boundary conversion).

RED failure modes:
  - AC1/AC4 tests: AttributeError — owlbear_mcp_kanban.server has no pick_dispatchable attr.
  - AC2 tests: AssertionError — _PICK_MAX_* symbols still present in server.py.
"""

from __future__ import annotations

import owlbear_mcp_kanban.server as server_mod
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban.models import Task
from owlbear_mcp_kanban.server import AppContext, pick_tasks

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

_MINIMAL_TASK = Task(
    id=10,
    title="Test Task",
    status="todo",
    priority="important",
    created="2026-01-01T00:00:00+00:00",
    updated="2026-01-01T00:00:00+00:00",
    body="## AC\n- Do something important\n",
)


def _make_mock_engine() -> MagicMock:
    """Return a MagicMock with KanbanEngine spec."""
    return MagicMock(spec=KanbanEngine)


def _make_app_ctx(engine: MagicMock | None = None) -> AppContext:
    """Build AppContext with a mock engine (or a fresh one if not provided)."""
    if engine is None:
        engine = _make_mock_engine()
    return AppContext(engine=engine, kanban_dir=Path("/fake/kanban"))  # type: ignore[call-arg]


def _make_mcp_ctx(app_ctx: AppContext) -> MagicMock:
    """Return a MagicMock mimicking an MCP Context with lifespan_context."""
    ctx = MagicMock()
    ctx.request_context.lifespan_context = app_ctx
    return ctx


# ===========================================================================
# TestFromAC_DelegationEngine — AC1 gap
# RED: AttributeError — server has no pick_dispatchable import yet
# ===========================================================================


class TestFromAC_DelegationEngine:
    """AC1 gap: server passes the AppContext engine as first positional arg to pick_dispatchable."""

    @pytest.mark.asyncio
    async def test_pick_tasks_passes_engine_as_first_positional_arg(self) -> None:
        """pick_tasks must call pick_dispatchable(engine, ...) — engine from AppContext.

        RED: AttributeError — owlbear_mcp_kanban.server has no pick_dispatchable attribute.
        """
        mock_engine = _make_mock_engine()
        app_ctx = _make_app_ctx(engine=mock_engine)
        mcp_ctx = _make_mcp_ctx(app_ctx)
        with patch("owlbear_mcp_kanban.server.pick_dispatchable") as mock_pd:
            mock_pd.return_value = []
            await pick_tasks(mcp_ctx)
            args, _ = mock_pd.call_args
            assert len(args) >= 1, (
                "pick_dispatchable must receive engine as first positional argument"
            )
            assert args[0] is mock_engine, (
                f"Expected engine from AppContext as first arg, got: {args[0]!r}"
            )


# ===========================================================================
# TestFromAC_NoInlineGatingComplete — AC2 gap
# RED: AssertionError — _PICK_MAX_* symbols still present in server.py
# ===========================================================================


class TestFromAC_NoInlineGatingComplete:
    """AC2 gap: _PICK_MAX_PRIORITY_RANK and _PICK_MAX_STATUS_RANK removed from server.py.

    The 8 _PICK_* symbols targeted for removal include these two derived constants
    not covered by #825 tests.
    """

    def test_no_pick_max_priority_rank_in_server(self) -> None:
        """server module must not expose _PICK_MAX_PRIORITY_RANK after thin-wrapper refactor.

        RED: AssertionError — _PICK_MAX_PRIORITY_RANK is still defined in server.py.
        """
        assert not hasattr(server_mod, "_PICK_MAX_PRIORITY_RANK"), (
            "_PICK_MAX_PRIORITY_RANK must be removed from server.py (moved to dispatch.py)"
        )

    def test_no_pick_max_status_rank_in_server(self) -> None:
        """server module must not expose _PICK_MAX_STATUS_RANK after thin-wrapper refactor.

        RED: AssertionError — _PICK_MAX_STATUS_RANK is still defined in server.py.
        """
        assert not hasattr(server_mod, "_PICK_MAX_STATUS_RANK"), (
            "_PICK_MAX_STATUS_RANK must be removed from server.py (moved to dispatch.py)"
        )


# ===========================================================================
# TestFromAC_BoundaryConversion — AC4
# RED: AttributeError — server has no pick_dispatchable import yet
# ===========================================================================


class TestFromAC_BoundaryConversion:
    """AC4: server formats Task objects returned by pick_dispatchable into dispatch dict entries.

    After refactoring, pick_dispatchable returns list[Task] (Pydantic model instances).
    Server accesses task.id and task.status (attribute access), not dict keys.
    """

    @pytest.mark.asyncio
    async def test_task_object_id_becomes_task_id_int_in_dispatch(self) -> None:
        """Task.id from pick_dispatchable must appear as task_id int in each dispatch entry.

        RED: AttributeError — owlbear_mcp_kanban.server has no pick_dispatchable attribute.
        """
        app_ctx = _make_app_ctx()
        mcp_ctx = _make_mcp_ctx(app_ctx)
        with patch("owlbear_mcp_kanban.server.pick_dispatchable") as mock_pd:
            mock_pd.return_value = [_MINIMAL_TASK]
            result = await pick_tasks(mcp_ctx)
        entry = result["dispatch"][0]
        assert entry["task_id"] == 10, f"Expected task_id=10, got {entry['task_id']!r}"
        assert isinstance(entry["task_id"], int), (
            f"task_id must be int, got {type(entry['task_id'])}"
        )

    @pytest.mark.asyncio
    async def test_task_object_status_becomes_status_str_in_dispatch(self) -> None:
        """Task.status from pick_dispatchable must appear as status str in each dispatch entry.

        RED: AttributeError — owlbear_mcp_kanban.server has no pick_dispatchable attribute.
        """
        app_ctx = _make_app_ctx()
        mcp_ctx = _make_mcp_ctx(app_ctx)
        with patch("owlbear_mcp_kanban.server.pick_dispatchable") as mock_pd:
            mock_pd.return_value = [_MINIMAL_TASK]
            result = await pick_tasks(mcp_ctx)
        entry = result["dispatch"][0]
        assert entry["status"] == "todo", f"Expected status='todo', got {entry['status']!r}"
        assert isinstance(entry["status"], str), (
            f"status must be str, got {type(entry['status'])}"
        )

    @pytest.mark.asyncio
    async def test_multiple_task_objects_all_appear_in_dispatch_order(self) -> None:
        """All Task objects returned by pick_dispatchable are converted in order.

        RED: AttributeError — owlbear_mcp_kanban.server has no pick_dispatchable attribute.
        """
        task_a = Task(
            id=1,
            title="A",
            status="todo",
            priority="critical",
            created="2026-01-01T00:00:00+00:00",
            updated="2026-01-01T00:00:00+00:00",
            body="## AC\n- x\n",
        )
        task_b = Task(
            id=2,
            title="B",
            status="in-progress",
            priority="needed",
            created="2026-01-01T00:00:00+00:00",
            updated="2026-01-01T00:00:00+00:00",
            body="## Test-Writer Notes\n- y\n",
        )
        app_ctx = _make_app_ctx()
        mcp_ctx = _make_mcp_ctx(app_ctx)
        with patch("owlbear_mcp_kanban.server.pick_dispatchable") as mock_pd:
            mock_pd.return_value = [task_a, task_b]
            result = await pick_tasks(mcp_ctx)
        dispatch = result["dispatch"]
        assert len(dispatch) == 2, f"Expected 2 entries, got {len(dispatch)}"
        assert dispatch[0] == {"task_id": 1, "status": "todo"}
        assert dispatch[1] == {"task_id": 2, "status": "in-progress"}

    @pytest.mark.asyncio
    async def test_empty_task_list_from_pick_dispatchable_yields_empty_dispatch(self) -> None:
        """When pick_dispatchable returns [], server returns {'dispatch': []}.

        RED: AttributeError — owlbear_mcp_kanban.server has no pick_dispatchable attribute.
        """
        app_ctx = _make_app_ctx()
        mcp_ctx = _make_mcp_ctx(app_ctx)
        with patch("owlbear_mcp_kanban.server.pick_dispatchable") as mock_pd:
            mock_pd.return_value = []
            result = await pick_tasks(mcp_ctx)
        assert result == {"dispatch": []}, f"Expected {{'dispatch': []}}, got {result!r}"
