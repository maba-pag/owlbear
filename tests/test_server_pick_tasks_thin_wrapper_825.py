"""Tests for task #825: server pick_tasks thin wrapper (TDD RED).

AC coverage:
  - AC1: server pick_tasks delegates to pick_dispatchable() from engine   [4 RED]
  - AC2: no inline gating logic (_check_pick_gates, _PICK_* constants) in server.py  [3 RED]
  - AC3: pick_tasks response format unchanged (dispatch wrapper with task details)  [4 PASS]
  - AC4: existing pick_tasks MCP contract preserved  [3 PASS]

AC1 and AC2 tests FAIL RED:
  - AC1: patch("owlbear_mcp_kanban.server.pick_dispatchable") raises AttributeError —
    server.py has no pick_dispatchable import yet.
  - AC2: hasattr assertions fail — _check_pick_gates and _PICK_* constants still present.
AC3 and AC4 tests PASS as regression guards for current behavior.
"""

from __future__ import annotations

import owlbear_mcp_kanban.server as server_mod
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban.models import Task
from owlbear_mcp_kanban.server import AppContext, mcp, pick_tasks

# ---------------------------------------------------------------------------
# Helpers (duplicated from test_kanban_mcp_migration.py for self-containment)
# ---------------------------------------------------------------------------

_MINIMAL_TASK_RECORD = Task(
    id=1,
    title="Minimal Task",
    status="todo",
    priority="important",
    created="2026-01-01T00:00:00+00:00",
    updated="2026-01-01T00:00:00+00:00",
    body="## AC\n- [ ] Something important",
)

_TASK_NO_AC = Task(
    id=2,
    title="No AC Task",
    status="todo",
    priority="critical",
    created="2026-01-01T00:00:00+00:00",
    updated="2026-01-01T00:00:00+00:00",
    body="just a description with no action items",
)


def _make_mock_engine(**attr_overrides: object) -> MagicMock:
    """Return a MagicMock with KanbanEngine spec."""
    mock = MagicMock(spec=KanbanEngine)
    for name, value in attr_overrides.items():
        getattr(mock, name).return_value = value
    return mock


def _make_engine_app_ctx(
    kanban_dir: Path = Path("/fake/kanban"),
    **engine_return_values: object,
) -> AppContext:
    """Build AppContext with a mock engine."""
    mock_engine = _make_mock_engine(**engine_return_values)
    return AppContext(engine=mock_engine, kanban_dir=kanban_dir)  # type: ignore[call-arg]


def _make_mcp_ctx(app_ctx: AppContext) -> MagicMock:
    """Return a MagicMock mimicking an MCP Context with lifespan_context."""
    ctx = MagicMock()
    ctx.request_context.lifespan_context = app_ctx
    return ctx


def _get_tool_annotations(tool_name: str) -> object | None:
    """Return the ToolAnnotations object for a named tool, or None."""
    if hasattr(mcp, "_tool_manager"):
        for t in mcp._tool_manager.list_tools():  # noqa: SLF001
            if getattr(t, "name", None) == tool_name:
                return getattr(t, "annotations", None)
    return None


# ===========================================================================
# TestFromAC_PickTasksDelegation — AC1
# RED: server.py has no pick_dispatchable import; patch raises AttributeError
# ===========================================================================


class TestFromAC_PickTasksDelegation:
    """AC1: server pick_tasks delegates to pick_dispatchable() imported from owlbear_kanban.dispatch."""

    @pytest.mark.asyncio
    async def test_pick_tasks_delegates_to_pick_dispatchable(self) -> None:
        """pick_tasks calls pick_dispatchable exactly once per invocation.

        RED: AttributeError — owlbear_mcp_kanban.server has no pick_dispatchable attribute.
        """
        app_ctx = _make_engine_app_ctx(list_tasks=[])
        mcp_ctx = _make_mcp_ctx(app_ctx)
        with patch("owlbear_mcp_kanban.server.pick_dispatchable") as mock_pd:
            mock_pd.return_value = []
            await pick_tasks(mcp_ctx)
            mock_pd.assert_called_once()

    @pytest.mark.asyncio
    async def test_pick_tasks_passes_default_limit_to_pick_dispatchable(self) -> None:
        """pick_tasks passes limit=25 to pick_dispatchable when called without limit arg.

        RED: AttributeError — owlbear_mcp_kanban.server has no pick_dispatchable attribute.
        """
        app_ctx = _make_engine_app_ctx(list_tasks=[])
        mcp_ctx = _make_mcp_ctx(app_ctx)
        with patch("owlbear_mcp_kanban.server.pick_dispatchable") as mock_pd:
            mock_pd.return_value = []
            await pick_tasks(mcp_ctx)
            call_kwargs = mock_pd.call_args[1]
            assert call_kwargs.get("limit") == 25

    @pytest.mark.asyncio
    async def test_pick_tasks_passes_custom_limit_to_pick_dispatchable(self) -> None:
        """pick_tasks passes caller-supplied limit to pick_dispatchable.

        RED: AttributeError — owlbear_mcp_kanban.server has no pick_dispatchable attribute.
        """
        app_ctx = _make_engine_app_ctx(list_tasks=[])
        mcp_ctx = _make_mcp_ctx(app_ctx)
        with patch("owlbear_mcp_kanban.server.pick_dispatchable") as mock_pd:
            mock_pd.return_value = []
            await pick_tasks(mcp_ctx, limit=5)
            call_kwargs = mock_pd.call_args[1]
            assert call_kwargs.get("limit") == 5

    @pytest.mark.asyncio
    async def test_pick_tasks_passes_tag_to_pick_dispatchable(self) -> None:
        """pick_tasks passes tag kwarg to pick_dispatchable when provided.

        RED: AttributeError — owlbear_mcp_kanban.server has no pick_dispatchable attribute.
        """
        app_ctx = _make_engine_app_ctx(list_tasks=[])
        mcp_ctx = _make_mcp_ctx(app_ctx)
        with patch("owlbear_mcp_kanban.server.pick_dispatchable") as mock_pd:
            mock_pd.return_value = []
            await pick_tasks(mcp_ctx, tag="phase-3")
            call_kwargs = mock_pd.call_args[1]
            assert call_kwargs.get("tag") == "phase-3"


# ===========================================================================
# TestFromAC_NoInlineGating — AC2
# RED: _check_pick_gates and _PICK_* constants still present in server.py
# ===========================================================================


class TestFromAC_NoInlineGating:
    """AC2: no inline gating logic remains in server.py after thin-wrapper refactor."""

    def test_no_check_pick_gates_in_server(self) -> None:
        """server module must not define _check_pick_gates after thin-wrapper refactor.

        RED: AssertionError — _check_pick_gates is still defined in server.py.
        """
        assert not hasattr(server_mod, "_check_pick_gates"), (
            "_check_pick_gates must be removed from server.py (moved to dispatch.py)"
        )

    def test_no_pick_rank_maps_in_server(self) -> None:
        """server module must not define _PICK_PRIORITY_RANK or _PICK_STATUS_RANK.

        RED: AssertionError — rank map constants still present in server.py.
        """
        assert not hasattr(server_mod, "_PICK_PRIORITY_RANK"), (
            "_PICK_PRIORITY_RANK must be removed from server.py (moved to dispatch.py)"
        )
        assert not hasattr(server_mod, "_PICK_STATUS_RANK"), (
            "_PICK_STATUS_RANK must be removed from server.py (moved to dispatch.py)"
        )

    def test_no_pick_gate_constants_in_server(self) -> None:
        """server module must not define _PICK_AC_PATTERN, _PICK_CLARITY_STATUSES, or _PICK_NON_IMPL_TAGS.

        RED: AssertionError — gate constants still present in server.py.
        """
        assert not hasattr(server_mod, "_PICK_AC_PATTERN"), (
            "_PICK_AC_PATTERN must be removed from server.py (moved to dispatch.py)"
        )
        assert not hasattr(server_mod, "_PICK_CLARITY_STATUSES"), (
            "_PICK_CLARITY_STATUSES must be removed from server.py (moved to dispatch.py)"
        )
        assert not hasattr(server_mod, "_PICK_NON_IMPL_TAGS"), (
            "_PICK_NON_IMPL_TAGS must be removed from server.py (moved to dispatch.py)"
        )


# ===========================================================================
# TestFromAC_PickTasksResponseFormat — AC3
# PASS: regression guards for current pick_tasks response format
# ===========================================================================


class TestFromAC_PickTasksResponseFormat:
    """AC3: pick_tasks response format — dispatch wrapper with task_id/status entries — unchanged."""

    @pytest.mark.asyncio
    async def test_response_is_dispatch_dict(self) -> None:
        """pick_tasks returns a dict with a 'dispatch' key containing a list."""
        app_ctx = _make_engine_app_ctx()
        mcp_ctx = _make_mcp_ctx(app_ctx)
        with patch("owlbear_mcp_kanban.server.pick_dispatchable") as mock_pd:
            mock_pd.return_value = []
            result = await pick_tasks(mcp_ctx)
        assert isinstance(result, dict), "pick_tasks must return a dict"
        assert "dispatch" in result, "result must have 'dispatch' key"
        assert isinstance(result["dispatch"], list), "'dispatch' value must be a list"

    @pytest.mark.asyncio
    async def test_dispatch_entries_have_task_id_and_status(self) -> None:
        """Each dispatch entry contains exactly 'task_id' and 'status' keys."""
        app_ctx = _make_engine_app_ctx()
        mcp_ctx = _make_mcp_ctx(app_ctx)
        with patch("owlbear_mcp_kanban.server.pick_dispatchable") as mock_pd:
            mock_pd.return_value = [_MINIMAL_TASK_RECORD]
            result = await pick_tasks(mcp_ctx)
        dispatch = result["dispatch"]
        assert len(dispatch) == 1, "task with valid AC body should appear in dispatch"
        entry = dispatch[0]
        assert set(entry.keys()) == {"task_id", "status"}, (
            f"dispatch entry must have exactly {{task_id, status}}, got {set(entry.keys())}"
        )

    @pytest.mark.asyncio
    async def test_task_id_is_integer(self) -> None:
        """task_id in each dispatch entry must be an int, not str."""
        app_ctx = _make_engine_app_ctx()
        mcp_ctx = _make_mcp_ctx(app_ctx)
        with patch("owlbear_mcp_kanban.server.pick_dispatchable") as mock_pd:
            mock_pd.return_value = [_MINIMAL_TASK_RECORD]
            result = await pick_tasks(mcp_ctx)
        dispatch = result["dispatch"]
        assert len(dispatch) == 1
        assert isinstance(dispatch[0]["task_id"], int), f"task_id must be int, got {type(dispatch[0]['task_id'])}"

    @pytest.mark.asyncio
    async def test_empty_board_returns_empty_dispatch(self) -> None:
        """pick_tasks with no tasks returns {'dispatch': []}."""
        app_ctx = _make_engine_app_ctx()
        mcp_ctx = _make_mcp_ctx(app_ctx)
        with patch("owlbear_mcp_kanban.server.pick_dispatchable") as mock_pd:
            mock_pd.return_value = []
            result = await pick_tasks(mcp_ctx)
        assert result == {"dispatch": []}, f"Expected {{'dispatch': []}}, got {result!r}"


# ===========================================================================
# TestFromAC_PickTasksMCPContract — AC4
# PASS: regression guards for existing pick_tasks MCP tool registration
# ===========================================================================


class TestFromAC_PickTasksMCPContract:
    """AC4: existing pick_tasks MCP contract (registration, annotations) preserved."""

    def test_pick_tasks_registered_in_mcp(self) -> None:
        """'pick_tasks' tool must be registered in the FastMCP server."""
        registered_names = [
            getattr(t, "name", None)
            for t in mcp._tool_manager.list_tools()  # noqa: SLF001
        ]
        assert "pick_tasks" in registered_names, f"pick_tasks not found in registered tools: {registered_names}"

    def test_pick_tasks_has_read_only_hint(self) -> None:
        """pick_tasks MCP annotation must set readOnlyHint=True."""
        ann = _get_tool_annotations("pick_tasks")
        assert ann is not None, "pick_tasks must have ToolAnnotations"
        assert getattr(ann, "readOnlyHint", None) is True, (
            f"Expected readOnlyHint=True, got: {getattr(ann, 'readOnlyHint', None)!r}"
        )

    def test_pick_tasks_has_idempotent_hint(self) -> None:
        """pick_tasks MCP annotation must set idempotentHint=True."""
        ann = _get_tool_annotations("pick_tasks")
        assert ann is not None, "pick_tasks must have ToolAnnotations"
        assert getattr(ann, "idempotentHint", None) is True, (
            f"Expected idempotentHint=True, got: {getattr(ann, 'idempotentHint', None)!r}"
        )
