"""Failing tests for #1447: resolve_drs MCP tool adapter.

AC coverage:
  ac1-registered    — resolve_drs registered in MCP tool registry (td:1)
  ac1-idempotent    — resolve_drs has idempotentHint=True
  ac1-destructive   — resolve_drs has destructiveHint=False
  ac1-parameterless — resolve_drs accepts only ctx (no business params)
  ac1-return-shape  — resolve_drs returns {"moved": [...], "count": N}
  ac2-happy         — approved DR: resolved and returned as relative path (td:2 happy)
  ac2-edge          — rejected DR: resolved and returned as relative path (td:2 edge)
  ac2-error         — empty pending: returns {"moved": [], "count": 0} (td:2 error)
  ac2-boundary      — multiple DRs: count matches len(moved) (td:2 boundary)
  ac3               — needs-info DR: resolved and returned as relative path (td:1)
  ac4               — repeat call for already-resolved DR returns empty result (td:1)
  ac5-mcp           — MCP pick_tasks has no resolve_drs/resolve_pending_drs path (td:1)
  ac5-agent-view    — AgentView.pick_tasks has no resolve call path (td:1)

All tests FAIL (RED phase) — resolve_drs MCP tool not yet registered in server.py.
"""

from __future__ import annotations

import inspect
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_mcp_kanban.server import AppContext, mcp

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CONFIG_YAML = """\
version: 10
board:
  name: TestBoard
tasks_dir: tasks
statuses:
- name: research
- name: backlog
- name: todo
- name: in-progress
- name: review
- name: docs
- name: done
priorities:
- someday
- nice-to-have
- important
- needed
- critical
defaults:
  status: research
  priority: important
claim_timeout: 1h
next_id: 1
archive_dir: archive
activity_log: false
agent_map:
  research: researcher
  backlog: architect
  todo: test-writer
  in-progress: builder
  review: reviewer
  docs: doc-writer
  done: auditor
agent_types: {}
agent_compatibility: {}
non_impl_tags: []
archival_reasons: [completed, deprecated, dropped, duplicate, wontfix]
status_predicates: {}
"""


def _make_board(base_dir: Path) -> Path:
    """Create a minimal valid kanban board and return its path."""
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    (kanban_dir / "decisions" / "pending").mkdir(parents=True, exist_ok=True)
    (kanban_dir / "decisions" / "resolved").mkdir(parents=True, exist_ok=True)
    return kanban_dir


def _make_mcp_ctx(app_ctx: AppContext) -> MagicMock:
    """Return a minimal MCP Context mock backed by the given AppContext."""
    ctx = MagicMock()
    ctx.request_context.lifespan_context = app_ctx
    return ctx


def _get_tool_annotations(tool_name: str) -> object | None:
    """Return ToolAnnotations for a named tool, or None if not found."""
    if hasattr(mcp, "_tool_manager"):
        for t in mcp._tool_manager.list_tools():  # noqa: SLF001
            if getattr(t, "name", None) == tool_name:
                return getattr(t, "annotations", None)
    return None


@pytest.fixture
def app_ctx(tmp_path: Path) -> AppContext:
    """Provide an AppContext backed by an isolated temp board."""
    kanban_dir = _make_board(tmp_path)
    engine = KanbanEngine(kanban_dir)
    return AppContext(engine=engine, kanban_dir=kanban_dir)


# ---------------------------------------------------------------------------
# AC-1: resolve_drs registration, annotations, signature, return shape
# ---------------------------------------------------------------------------


class TestFromAC_ResolveDrsRegistration:
    """AC-1: resolve_drs registered with correct annotations and no business params."""

    def test_resolve_drs_is_registered_in_mcp_registry(self) -> None:
        """AC-1: resolve_drs must be a registered MCP tool in the server registry."""
        registered_names = [
            t.name
            for t in mcp._tool_manager._tools.values()  # noqa: SLF001
        ]
        assert "resolve_drs" in registered_names, (
            f"resolve_drs must be registered via @mcp.tool(); "
            f"current tools: {registered_names!r}"
        )

    def test_resolve_drs_has_idempotent_hint_true(self) -> None:
        """AC-1: resolve_drs must have idempotentHint=True in its ToolAnnotations."""
        ann = _get_tool_annotations("resolve_drs")
        assert ann is not None, (
            "resolve_drs must have ToolAnnotations; got None — "
            "add annotations=ToolAnnotations(...) to the @mcp.tool() decorator"
        )
        assert getattr(ann, "idempotentHint", None) is True, (
            f"resolve_drs must have idempotentHint=True; got: {getattr(ann, 'idempotentHint', 'MISSING')!r}"
        )

    def test_resolve_drs_has_destructive_hint_false(self) -> None:
        """AC-1: resolve_drs must have destructiveHint=False in its ToolAnnotations."""
        ann = _get_tool_annotations("resolve_drs")
        assert ann is not None, "resolve_drs must have ToolAnnotations; got None"
        assert getattr(ann, "destructiveHint", None) is False, (
            f"resolve_drs must have destructiveHint=False; "
            f"got: {getattr(ann, 'destructiveHint', 'MISSING')!r}"
        )

    def test_resolve_drs_is_parameterless(self) -> None:
        """AC-1: resolve_drs must accept only ctx — no business parameters."""
        import owlbear_mcp_kanban.server as server_mod  # noqa: PLC0415

        fn = getattr(server_mod, "resolve_drs", None)
        assert fn is not None, (
            "owlbear_mcp_kanban.server.resolve_drs must exist as a callable"
        )
        params = inspect.signature(fn).parameters
        non_ctx_params = [p for p in params if p != "ctx"]
        assert len(non_ctx_params) == 0, (
            f"resolve_drs must be parameterless (only ctx); "
            f"found extra params: {non_ctx_params!r}"
        )

    @pytest.mark.asyncio
    async def test_resolve_drs_returns_moved_list_and_count(
        self, app_ctx: AppContext
    ) -> None:
        """AC-1: resolve_drs result must include 'moved' list and 'count' int."""
        import owlbear_mcp_kanban.server as server_mod  # noqa: PLC0415

        fn = getattr(server_mod, "resolve_drs", None)
        assert fn is not None, "owlbear_mcp_kanban.server.resolve_drs must exist"

        ctx = _make_mcp_ctx(app_ctx)
        with patch(
            "owlbear_mcp_kanban.server.decisions.resolve_pending_drs",
            return_value=[],
        ):
            result = await fn(ctx)

        assert isinstance(result, dict), (
            f"resolve_drs must return a dict; got {type(result)!r}"
        )
        assert "moved" in result, (
            f"resolve_drs result must include 'moved' key; got keys: {list(result.keys())!r}"
        )
        assert "count" in result, (
            f"resolve_drs result must include 'count' key; got keys: {list(result.keys())!r}"
        )
        assert isinstance(result["moved"], list), (
            f"'moved' must be a list; got {type(result['moved'])!r}"
        )
        assert isinstance(result["count"], int), (
            f"'count' must be an int; got {type(result['count'])!r}"
        )


# ---------------------------------------------------------------------------
# AC-2: approved and rejected DR handling (td:2 — happy, edge, error, boundary)
# ---------------------------------------------------------------------------


class TestFromAC_ResolveDrsResolution:
    """AC-2: resolve_drs handles approved and rejected responses correctly."""

    @pytest.mark.asyncio
    async def test_happy_approved_dr_returned_as_relative_path(
        self, app_ctx: AppContext
    ) -> None:
        """AC-2 happy: approved DR resolved path returned as workspace-relative posix string."""
        import owlbear_mcp_kanban.server as server_mod  # noqa: PLC0415

        fn = getattr(server_mod, "resolve_drs", None)
        assert fn is not None, "owlbear_mcp_kanban.server.resolve_drs must exist"

        resolved_abs = app_ctx.kanban_dir / "decisions" / "resolved" / "42-decision.md"
        ctx = _make_mcp_ctx(app_ctx)
        with patch(
            "owlbear_mcp_kanban.server.decisions.resolve_pending_drs",
            return_value=[resolved_abs],
        ):
            result = await fn(ctx)

        assert result["count"] == 1, (
            f"AC-2 happy: expected count=1 for one approved DR; got {result['count']!r}"
        )
        assert len(result["moved"]) == 1, (
            f"AC-2 happy: expected 1 item in 'moved'; got {result['moved']!r}"
        )
        moved_path = result["moved"][0]
        assert not Path(moved_path).is_absolute(), (
            f"AC-2 happy: 'moved' paths must be relative; got absolute: {moved_path!r}"
        )
        assert moved_path == "decisions/resolved/42-decision.md", (
            f"AC-2 happy: expected relative path 'decisions/resolved/42-decision.md'; "
            f"got {moved_path!r}"
        )

    @pytest.mark.asyncio
    async def test_edge_rejected_dr_returned_as_relative_path(
        self, app_ctx: AppContext
    ) -> None:
        """AC-2 edge: rejected DR resolved path returned as workspace-relative posix string."""
        import owlbear_mcp_kanban.server as server_mod  # noqa: PLC0415

        fn = getattr(server_mod, "resolve_drs", None)
        assert fn is not None, "owlbear_mcp_kanban.server.resolve_drs must exist"

        resolved_abs = app_ctx.kanban_dir / "decisions" / "resolved" / "7-action.md"
        ctx = _make_mcp_ctx(app_ctx)
        with patch(
            "owlbear_mcp_kanban.server.decisions.resolve_pending_drs",
            return_value=[resolved_abs],
        ):
            result = await fn(ctx)

        assert result["count"] == 1, (
            f"AC-2 edge: expected count=1 for one rejected DR; got {result['count']!r}"
        )
        assert result["moved"] == ["decisions/resolved/7-action.md"], (
            f"AC-2 edge: unexpected 'moved' paths: {result['moved']!r}"
        )

    @pytest.mark.asyncio
    async def test_error_empty_pending_returns_empty_result(
        self, app_ctx: AppContext
    ) -> None:
        """AC-2 error: no pending DRs → {"moved": [], "count": 0}."""
        import owlbear_mcp_kanban.server as server_mod  # noqa: PLC0415

        fn = getattr(server_mod, "resolve_drs", None)
        assert fn is not None, "owlbear_mcp_kanban.server.resolve_drs must exist"

        ctx = _make_mcp_ctx(app_ctx)
        with patch(
            "owlbear_mcp_kanban.server.decisions.resolve_pending_drs",
            return_value=[],
        ):
            result = await fn(ctx)

        assert result["moved"] == [], (
            f"AC-2 error: empty pending must yield moved=[], got {result['moved']!r}"
        )
        assert result["count"] == 0, (
            f"AC-2 error: empty pending must yield count=0, got {result['count']!r}"
        )

    @pytest.mark.asyncio
    async def test_boundary_multiple_drs_count_matches_moved_length(
        self, app_ctx: AppContext
    ) -> None:
        """AC-2 boundary: multiple resolved DRs → count == len(moved), all paths relative."""
        import owlbear_mcp_kanban.server as server_mod  # noqa: PLC0415

        fn = getattr(server_mod, "resolve_drs", None)
        assert fn is not None, "owlbear_mcp_kanban.server.resolve_drs must exist"

        resolved_dir = app_ctx.kanban_dir / "decisions" / "resolved"
        abs_paths = [
            resolved_dir / "1-decision.md",
            resolved_dir / "2-action.md",
            resolved_dir / "3-decision-2.md",
        ]
        ctx = _make_mcp_ctx(app_ctx)
        with patch(
            "owlbear_mcp_kanban.server.decisions.resolve_pending_drs",
            return_value=abs_paths,
        ):
            result = await fn(ctx)

        assert result["count"] == 3, (
            f"AC-2 boundary: expected count=3, got {result['count']!r}"
        )
        assert len(result["moved"]) == 3, (
            f"AC-2 boundary: expected 3 items in 'moved', got {result['moved']!r}"
        )
        assert result["count"] == len(result["moved"]), (
            "AC-2 boundary: count must equal len(moved)"
        )
        for path_str in result["moved"]:
            assert not Path(path_str).is_absolute(), (
                f"AC-2 boundary: all 'moved' paths must be relative; found absolute: {path_str!r}"
            )


# ---------------------------------------------------------------------------
# AC-3: needs-info handling (td:1)
# ---------------------------------------------------------------------------


class TestFromAC_ResolveDrsNeedsInfo:
    """AC-3: resolve_drs handles needs-info responses correctly."""

    @pytest.mark.asyncio
    async def test_needs_info_dr_returned_as_relative_path(
        self, app_ctx: AppContext
    ) -> None:
        """AC-3: needs-info DR moved to resolved/ and returned as relative path."""
        import owlbear_mcp_kanban.server as server_mod  # noqa: PLC0415

        fn = getattr(server_mod, "resolve_drs", None)
        assert fn is not None, "owlbear_mcp_kanban.server.resolve_drs must exist"

        resolved_abs = app_ctx.kanban_dir / "decisions" / "resolved" / "55-clarify.md"
        ctx = _make_mcp_ctx(app_ctx)
        with patch(
            "owlbear_mcp_kanban.server.decisions.resolve_pending_drs",
            return_value=[resolved_abs],
        ):
            result = await fn(ctx)

        assert result["count"] == 1, (
            f"AC-3: needs-info DR must be counted; got count={result['count']!r}"
        )
        assert result["moved"] == ["decisions/resolved/55-clarify.md"], (
            f"AC-3: expected needs-info path in 'moved'; got {result['moved']!r}"
        )


# ---------------------------------------------------------------------------
# AC-4: idempotency — repeat call returns empty result (td:1)
# ---------------------------------------------------------------------------


class TestFromAC_ResolveDrsIdempotency:
    """AC-4: repeated resolve_drs call for already-resolved DRs returns empty result."""

    @pytest.mark.asyncio
    async def test_repeat_call_returns_empty_when_dr_already_resolved(
        self, app_ctx: AppContext
    ) -> None:
        """AC-4: second call finds nothing in pending/ → {"moved": [], "count": 0}.

        resolve_drs scans only decisions/pending/ — files already in resolved/
        are invisible to the scan. A second call must return empty, not duplicate-resolve.
        """
        import owlbear_mcp_kanban.server as server_mod  # noqa: PLC0415

        fn = getattr(server_mod, "resolve_drs", None)
        assert fn is not None, "owlbear_mcp_kanban.server.resolve_drs must exist"

        ctx = _make_mcp_ctx(app_ctx)
        resolved_abs = app_ctx.kanban_dir / "decisions" / "resolved" / "10-decision.md"

        # First call: DR was in pending/, resolve_pending_drs moved it.
        with patch(
            "owlbear_mcp_kanban.server.decisions.resolve_pending_drs",
            return_value=[resolved_abs],
        ):
            first_result = await fn(ctx)

        assert first_result["count"] == 1, (
            f"AC-4: first call must resolve 1 DR; got {first_result!r}"
        )

        # Second call: pending/ is now empty (DR is in resolved/).
        with patch(
            "owlbear_mcp_kanban.server.decisions.resolve_pending_drs",
            return_value=[],
        ) as mock_resolve:
            second_result = await fn(ctx)

        assert second_result["moved"] == [], (
            f"AC-4: second call must return empty 'moved'; got {second_result['moved']!r}"
        )
        assert second_result["count"] == 0, (
            f"AC-4: second call must return count=0; got {second_result['count']!r}"
        )
        # Verify resolve_pending_drs was called (not short-circuited by the tool)
        (
            mock_resolve.assert_called_once(),
            (
                "AC-4: resolve_pending_drs must be called on each invocation — "
                "the tool must not maintain its own state"
            ),
        )


# ---------------------------------------------------------------------------
# AC-5: pick_tasks has no call path to resolve functions (td:1)
# ---------------------------------------------------------------------------


class TestFromAC_PickTasksNoResolve:
    """AC-5: AgentView.pick_tasks and MCP pick_tasks have no resolve_drs call path."""

    def test_mcp_pick_tasks_has_no_resolve_calls(self) -> None:
        """AC-5: MCP pick_tasks source must not call resolve_drs or resolve_pending_drs.

        Conditioned on resolve_drs being registered so this test fails in RED phase
        (when resolve_drs doesn't exist yet) and guards against accidental wiring in GREEN.
        """
        import owlbear_mcp_kanban.server as server_mod  # noqa: PLC0415

        # Precondition: resolve_drs must be registered — fails in RED phase.
        resolve_drs_fn = getattr(server_mod, "resolve_drs", None)
        assert resolve_drs_fn is not None, (
            "AC-5 precondition: resolve_drs must exist in server_mod "
            "(this test fails in RED — it will pass once resolve_drs is implemented)"
        )

        src = inspect.getsource(server_mod.pick_tasks)
        assert "resolve_drs" not in src, (
            "AC-5: MCP pick_tasks must NOT call resolve_drs; "
            f"found 'resolve_drs' in pick_tasks source"
        )
        assert "resolve_pending_drs" not in src, (
            "AC-5: MCP pick_tasks must NOT call resolve_pending_drs; "
            f"found 'resolve_pending_drs' in pick_tasks source"
        )

    def test_agent_view_pick_tasks_has_no_resolve_calls(self) -> None:
        """AC-5: AgentView.pick_tasks source must not call resolve_drs or resolve_pending_drs.

        Conditioned on resolve_drs being registered so this test fails in RED phase
        and acts as a regression guard after GREEN.
        """
        import owlbear_mcp_kanban.server as server_mod  # noqa: PLC0415
        from owlbear_kanban.agent_view import AgentView  # noqa: PLC0415

        # Precondition: resolve_drs must be registered — fails in RED phase.
        resolve_drs_fn = getattr(server_mod, "resolve_drs", None)
        assert resolve_drs_fn is not None, (
            "AC-5 precondition: resolve_drs must exist in server_mod "
            "(this test fails in RED — it will pass once resolve_drs is implemented)"
        )

        src = inspect.getsource(AgentView.pick_tasks)
        assert "resolve_drs" not in src, (
            "AC-5: AgentView.pick_tasks must NOT call resolve_drs"
        )
        assert "resolve_pending_drs" not in src, (
            "AC-5: AgentView.pick_tasks must NOT call resolve_pending_drs"
        )


# ---------------------------------------------------------------------------
# Coverage uplift: server utility paths not reached by AC test classes
# ---------------------------------------------------------------------------


class TestCoverageUplift_ServerUtils:
    """Coverage uplift tests for server.py utility paths (builder Required Follow-up).

    These tests exercise code paths that are not covered by the AC test classes above
    and bring owlbear_mcp_kanban.server module coverage from 86% to >=90%.  All tests
    should PASS since the implementation already exists.
    """

    def test_coerce_to_str_converts_int_to_string(self) -> None:
        """_coerce_to_str must convert int input to str (line 48)."""
        from owlbear_mcp_kanban.server import _coerce_to_str  # noqa: PLC0415

        assert _coerce_to_str(42) == "42"
        assert isinstance(_coerce_to_str(0), str)

    def test_map_kanban_error_raises_tool_error_with_json_payload(self) -> None:
        """_map_kanban_error must raise ToolError carrying JSON code+message (lines 137-140)."""
        import json  # noqa: PLC0415

        from mcp.server.fastmcp.exceptions import ToolError  # noqa: PLC0415
        from owlbear_kanban.errors import KanbanError  # noqa: PLC0415
        from owlbear_mcp_kanban.server import _map_kanban_error  # noqa: PLC0415

        exc = KanbanError("ERR_NOT_FOUND", "Task not found")
        with pytest.raises(ToolError) as exc_info:
            _map_kanban_error(exc)
        payload = json.loads(str(exc_info.value))
        assert payload["code"] == "ERR_NOT_FOUND"
        assert payload["message"] == "Task not found"

    def test_app_ctx_contains_always_returns_false(self, app_ctx: AppContext) -> None:
        """AppContext.__contains__ must always return False (lines 143-146)."""
        assert "anything" not in app_ctx
        assert 42 not in app_ctx
        assert None not in app_ctx

    def test_apply_tool_exclusions_exception_swallowed(self) -> None:
        """_apply_tool_exclusions must swallow remove_tool failures (lines 160-161)."""
        from owlbear_mcp_kanban.server import _apply_tool_exclusions  # noqa: PLC0415

        mock_server = MagicMock()
        mock_server.remove_tool.side_effect = RuntimeError("tool not found")

        with patch.dict("os.environ", {"KANBAN_TOOLS_EXCLUDE": "nonexistent_tool"}):
            result = _apply_tool_exclusions(mock_server)

        assert result == set(), (
            f"Failed removal must not add tool to excluded set; got {result!r}"
        )

    def test_to_single_task_response_accepts_kanban_task_input(self) -> None:
        """_to_single_task_response must handle KanbanTask input (line ~258)."""
        from owlbear_mcp_kanban.models import KanbanTask  # noqa: PLC0415
        from owlbear_mcp_kanban.server import _to_single_task_response  # noqa: PLC0415

        task = KanbanTask(
            id=1,
            title="Coverage task",
            status="todo",
            priority="important",
            created="2026-01-01T00:00:00+00:00",
            updated="2026-01-01T00:00:00+00:00",
        )
        result = _to_single_task_response(task)
        assert result.id == 1
        assert result.title == "Coverage task"

    def test_to_single_task_response_accepts_dict_input(self) -> None:
        """_to_single_task_response must handle dict input (line ~262)."""
        from owlbear_mcp_kanban.server import _to_single_task_response  # noqa: PLC0415

        record = {
            "id": 7,
            "title": "Dict input task",
            "status": "research",
            "priority": "important",
            "created": "2026-01-01T00:00:00+00:00",
            "updated": "2026-01-01T00:00:00+00:00",
            "tags": [],
            "depends_on": [],
            "blocked": False,
            "block_reason": None,
            "body": None,
            "parent": None,
            "guidance": [],
        }
        result = _to_single_task_response(record)
        assert result.id == 7
        assert result.title == "Dict input task"

    @pytest.mark.asyncio
    async def test_show_validated_file_not_found_raises_tool_error(
        self, app_ctx: AppContext
    ) -> None:
        """_show_validated must convert FileNotFoundError to ToolError (lines 268-270)."""
        from mcp.server.fastmcp.exceptions import ToolError  # noqa: PLC0415
        from owlbear_mcp_kanban.server import _show_validated  # noqa: PLC0415

        with (
            patch.object(
                app_ctx.engine,
                "show_task",
                side_effect=FileNotFoundError("task 999 not found"),
            ),
            pytest.raises(ToolError),
        ):
            await _show_validated(app_ctx, 999)

    @pytest.mark.asyncio
    async def test_resolve_drs_kanban_error_raises_tool_error(
        self, app_ctx: AppContext
    ) -> None:
        """resolve_drs must convert KanbanError to ToolError (lines 380-381)."""
        import owlbear_mcp_kanban.server as server_mod  # noqa: PLC0415

        from mcp.server.fastmcp.exceptions import ToolError  # noqa: PLC0415
        from owlbear_kanban.errors import KanbanError  # noqa: PLC0415

        fn = getattr(server_mod, "resolve_drs", None)
        assert fn is not None, "resolve_drs must be registered"

        ctx = _make_mcp_ctx(app_ctx)
        with (
            patch(
                "owlbear_mcp_kanban.server.decisions.resolve_pending_drs",
                side_effect=KanbanError("ERR_NOT_FOUND", "Decisions dir missing"),
            ),
            pytest.raises(ToolError),
        ):
            await fn(ctx)

    @pytest.mark.asyncio
    async def test_edit_task_kanban_error_raises_tool_error(
        self, app_ctx: AppContext
    ) -> None:
        """edit_task must convert KanbanError to ToolError (lines 479-480)."""
        import owlbear_mcp_kanban.server as server_mod  # noqa: PLC0415

        from mcp.server.fastmcp.exceptions import ToolError  # noqa: PLC0415
        from owlbear_kanban.errors import KanbanError  # noqa: PLC0415

        ctx = _make_mcp_ctx(app_ctx)
        mock_av = MagicMock()
        mock_av.edit_task.side_effect = KanbanError(
            "ERR_INVALID_TITLE", "title cannot be empty"
        )

        with (
            patch.object(app_ctx.engine, "agent_view", return_value=mock_av),
            pytest.raises(ToolError),
        ):
            await server_mod.edit_task(ctx, id="1", title="x")

    @pytest.mark.asyncio
    async def test_start_work_value_error_raises_tool_error(
        self, app_ctx: AppContext
    ) -> None:
        """start_work must convert ValueError to ToolError (lines 516-517)."""
        import owlbear_mcp_kanban.server as server_mod  # noqa: PLC0415

        from mcp.server.fastmcp.exceptions import ToolError  # noqa: PLC0415

        ctx = _make_mcp_ctx(app_ctx)
        mock_av = MagicMock()
        mock_av.start_work.side_effect = ValueError("already claimed by another")

        with (
            patch.object(app_ctx.engine, "agent_view", return_value=mock_av),
            pytest.raises(ToolError),
        ):
            await server_mod.start_work(ctx, id="1")

    @pytest.mark.asyncio
    async def test_end_work_value_error_raises_tool_error(
        self, app_ctx: AppContext
    ) -> None:
        """end_work must convert ValueError to ToolError (lines 558-559)."""
        import owlbear_mcp_kanban.server as server_mod  # noqa: PLC0415

        from mcp.server.fastmcp.exceptions import ToolError  # noqa: PLC0415

        ctx = _make_mcp_ctx(app_ctx)
        mock_av = MagicMock()
        mock_av.end_work.side_effect = ValueError("outcome mismatch")

        with (
            patch.object(app_ctx.engine, "agent_view", return_value=mock_av),
            pytest.raises(ToolError),
        ):
            await server_mod.end_work(ctx, id="1", note="done", outcome="success")


# ---------------------------------------------------------------------------
# AC-2/AC-3/AC-4: MCP seam tests — real filesystem, spy verification
# (Reviewer retry Required Follow-up: review cycle 2)
# ---------------------------------------------------------------------------


class TestFromAC_ResolveDrsMcpSeam:
    """Real-filesystem seam tests: argument correctness, canonical summary count, idempotency.

    Reviewer Required Follow-up items (review cycle 2):
    1. Spy: verify resolve_drs calls decisions.resolve_pending_drs with the correct
       decisions dir and engine — wrong arguments cause the assertion to fail.
    2. Summary count (AC-2, AC-3): prove exactly one canonical summary is appended
       for approved and needs-info responses at the MCP call path.
    3. AC-4 real filesystem: prove a second resolve_drs call adds no duplicate summary.

    All tests invoke the real decisions.resolve_pending_drs (no full mock).
    """

    @pytest.mark.asyncio
    async def test_seam_passes_correct_decisions_dir_and_engine(
        self, app_ctx: AppContext
    ) -> None:
        """MCP seam: resolve_drs must invoke decisions.resolve_pending_drs with
        (kanban_dir / 'decisions', engine) — wrong path or wrong engine would fail.

        Uses wraps= spy so the real resolver still runs (returning [] for empty
        pending/) while call arguments are recorded and asserted.
        """
        import owlbear_kanban.decisions as kanban_decisions  # noqa: PLC0415
        import owlbear_mcp_kanban.server as server_mod  # noqa: PLC0415

        fn = getattr(server_mod, "resolve_drs", None)
        assert fn is not None, "resolve_drs must be registered"

        ctx = _make_mcp_ctx(app_ctx)
        with patch(
            "owlbear_mcp_kanban.server.decisions.resolve_pending_drs",
            wraps=kanban_decisions.resolve_pending_drs,
        ) as spy:
            await fn(ctx)

        spy.assert_called_once_with(
            app_ctx.kanban_dir / "decisions",
            app_ctx.engine,
        )

    @pytest.mark.asyncio
    async def test_approved_dr_appends_exactly_one_canonical_summary(
        self, app_ctx: AppContext
    ) -> None:
        """AC-2 real filesystem: resolve_drs with an approved DR appends exactly one
        '## Decision Request' canonical summary to the linked task body.

        Uses real files and the real resolver.  Proves the MCP adapter does not add
        extra writes beyond the single resolver-level append.
        """
        import owlbear_mcp_kanban.server as server_mod  # noqa: PLC0415

        fn = getattr(server_mod, "resolve_drs", None)
        assert fn is not None, "resolve_drs must be registered"

        view = app_ctx.engine.agent_view()
        task_resp = view.create_task(title="Task for approved DR seam test")
        task_id = task_resp.id
        app_ctx.engine.edit_task(str(task_id), blocked=True, block_reason="DR pending")

        pending_dir = app_ctx.kanban_dir / "decisions" / "pending"
        (pending_dir / f"{task_id}-decision.md").write_text(
            f"---\ntask_id: {task_id}\nagent: test-writer\n"
            "request_type: decision\ncreated: '2026-05-11'\n"
            "response: approved\n---\n\n## Question\nApprove this change.\n",
            encoding="utf-8",
        )

        ctx = _make_mcp_ctx(app_ctx)
        result = await fn(ctx)

        assert result["count"] == 1, (
            f"AC-2 seam: one approved DR must yield count=1; got {result['count']!r}"
        )
        task_after = app_ctx.engine.show_task(str(task_id))
        body = task_after.body if isinstance(task_after.body, str) else ""
        summary_count = body.count("## Decision Request")
        assert summary_count == 1, (
            f"AC-2 seam: exactly one '## Decision Request' summary must appear; "
            f"found {summary_count}. Body:\n{body!r}"
        )

    @pytest.mark.asyncio
    async def test_needs_info_dr_appends_exactly_one_canonical_summary(
        self, app_ctx: AppContext
    ) -> None:
        """AC-3 real filesystem: resolve_drs with a needs-info DR appends exactly one
        '## Decision Request' canonical summary and keeps the task blocked.

        Uses real files and the real resolver.
        """
        import owlbear_mcp_kanban.server as server_mod  # noqa: PLC0415

        fn = getattr(server_mod, "resolve_drs", None)
        assert fn is not None, "resolve_drs must be registered"

        view = app_ctx.engine.agent_view()
        task_resp = view.create_task(title="Task for needs-info DR seam test")
        task_id = task_resp.id
        app_ctx.engine.edit_task(str(task_id), blocked=True, block_reason="DR pending")

        pending_dir = app_ctx.kanban_dir / "decisions" / "pending"
        (pending_dir / f"{task_id}-clarify.md").write_text(
            f"---\ntask_id: {task_id}\nagent: test-writer\n"
            "request_type: decision\ncreated: '2026-05-11'\n"
            "response: needs-info\n---\n\n## Question\nNeed more info.\n",
            encoding="utf-8",
        )

        ctx = _make_mcp_ctx(app_ctx)
        result = await fn(ctx)

        assert result["count"] == 1, (
            f"AC-3 seam: needs-info DR must be counted as resolved; got count={result['count']!r}"
        )
        task_after = app_ctx.engine.show_task(str(task_id))
        body = task_after.body if isinstance(task_after.body, str) else ""
        summary_count = body.count("## Decision Request")
        assert summary_count == 1, (
            f"AC-3 seam: exactly one '## Decision Request' summary must appear; "
            f"found {summary_count}. Body:\n{body!r}"
        )
        assert task_after.blocked is True, (
            "AC-3 seam: needs-info must keep the task blocked; "
            f"got blocked={task_after.blocked!r}"
        )

    @pytest.mark.asyncio
    async def test_ac4_real_filesystem_second_call_no_duplicate_summary(
        self, app_ctx: AppContext
    ) -> None:
        """AC-4 real filesystem: a second resolve_drs call must neither re-resolve the DR
        nor append a duplicate canonical summary to the linked task body.

        First call moves the approved DR from pending/ to resolved/ and appends one
        summary.  Second call must find pending/ empty, return moved=[]/count=0, and
        leave the task body with exactly one summary — not two.

        This is the real-filesystem proof that the existing mocked AC-4 test cannot
        provide: the mocked test passes even if a duplicate summary were appended.
        """
        import owlbear_mcp_kanban.server as server_mod  # noqa: PLC0415

        fn = getattr(server_mod, "resolve_drs", None)
        assert fn is not None, "resolve_drs must be registered"

        view = app_ctx.engine.agent_view()
        task_resp = view.create_task(title="Task for idempotency real filesystem test")
        task_id = task_resp.id
        app_ctx.engine.edit_task(str(task_id), blocked=True, block_reason="DR pending")

        pending_dir = app_ctx.kanban_dir / "decisions" / "pending"
        (pending_dir / f"{task_id}-decision.md").write_text(
            f"---\ntask_id: {task_id}\nagent: test-writer\n"
            "request_type: decision\ncreated: '2026-05-11'\n"
            "response: approved\n---\n\n## Question\nApprove for idempotency test.\n",
            encoding="utf-8",
        )

        ctx = _make_mcp_ctx(app_ctx)

        # First call: processes the pending DR, appends summary, moves file
        first_result = await fn(ctx)
        assert first_result["count"] == 1, (
            f"AC-4 real: first call must resolve 1 DR; got {first_result!r}"
        )
        task_mid = app_ctx.engine.show_task(str(task_id))
        body_mid = task_mid.body if isinstance(task_mid.body, str) else ""
        assert body_mid.count("## Decision Request") == 1, (
            "AC-4 real: first call must produce exactly 1 summary in task body"
        )

        # Second call: pending/ is empty (DR already moved to resolved/)
        second_result = await fn(ctx)
        assert second_result["moved"] == [], (
            f"AC-4 real: second call must return moved=[]; got {second_result['moved']!r}"
        )
        assert second_result["count"] == 0, (
            f"AC-4 real: second call must return count=0; got {second_result['count']!r}"
        )

        # Critical: no duplicate summary must have been appended
        task_after = app_ctx.engine.show_task(str(task_id))
        body_after = task_after.body if isinstance(task_after.body, str) else ""
        summary_count = body_after.count("## Decision Request")
        assert summary_count == 1, (
            f"AC-4 real: second call must NOT append a duplicate summary; "
            f"found {summary_count} summaries after second call. "
            f"Body:\n{body_after!r}"
        )
