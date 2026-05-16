"""RED phase tests — MCP read tool adapters (#1086).

Tests the 3 read-only tool adapters: list_tasks, show_task, pick_tasks.
All tests mock AgentView — the adapter is a mechanical translator;
engine behaviour is Brief B's responsibility.

Tests verify:
- Correct AgentView method called with correct args
- Response envelope returned unmodified
- KanbanError subclasses mapped to MCP ToolError with user_message

AC coverage:
- list_tasks: all params forwarded to AgentView.list_tasks; ListTasksResponse returned
- list_tasks: ids exclusivity enforced (AC15) — adapter maps ValidationError to ToolError
- show_task: id + section forwarded; ShowTaskResponse returned including missing_sections case (AC11)
- show_task: missing id → ToolError (AC via engine NotFoundError mapping)
- pick_tasks: wave_size + max_waves forwarded; PickTasksResponse with waves returned (AC22, AC23)
- Error mapping: engine ValidationError → MCP ToolError with user_message
- Error mapping: engine NotFoundError → MCP ToolError with user_message
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from owlbear_kanban.errors import NotFoundError, ValidationError
from owlbear_kanban.models import (
    DispatchEntry,
    ListTasksResponse,
    PickTasksResponse,
    ShowTaskResponse,
    TaskSummary,
    Wave,
)


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
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


def _make_mcp_ctx(app_ctx: object) -> MagicMock:
    """Wrap an AppContext in a MagicMock mimicking MCP Context."""
    ctx = MagicMock()
    ctx.request_context.lifespan_context = app_ctx
    return ctx


def _make_task_summary(**overrides: object) -> TaskSummary:
    defaults: dict[str, object] = {
        "id": 1,
        "title": "Alpha",
        "status": "todo",
        "priority": "important",
        "updated": "2026-01-01T00:00:00+00:00",
        "tags": [],
        "depends_on": [],
        "blocked": False,
        "block_reason": None,
        "claimed": False,
        "claimed_at": None,
        "archival_reason": None,
        "archival_refs": [],
        "dep_status": None,
    }
    defaults.update(overrides)
    return TaskSummary.model_validate(defaults)


def _make_show_task_response(**overrides: object) -> ShowTaskResponse:
    defaults: dict[str, object] = {
        "id": 42,
        "title": "Show me",
        "status": "todo",
        "priority": "important",
        "tags": [],
        "depends_on": [],
        "blocked": False,
        "block_reason": None,
        "claimed": False,
        "claimed_at": None,
        "archival_reason": None,
        "archival_refs": [],
        "dep_status": None,
        "created": "2026-01-01T00:00:00+00:00",
        "updated": "2026-01-01T00:00:00+00:00",
        "body": "## Notes\n\nHello",
        "missing_sections": None,
        "guidance": [],
    }
    defaults.update(overrides)
    return ShowTaskResponse.model_validate(defaults)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def app_ctx_with_mock_agent_view(tmp_path: Path) -> tuple[object, MagicMock]:
    """AppContext whose engine.agent_view() returns a MagicMock AgentView."""
    from owlbear_kanban import KanbanEngine
    from owlbear_mcp_kanban.server import AppContext

    kanban_dir = _make_board(tmp_path)
    engine = KanbanEngine(kanban_dir)
    mock_av = MagicMock()
    engine._agent_view = mock_av  # noqa: SLF001
    app_ctx = AppContext(engine=engine, kanban_dir=kanban_dir)
    return app_ctx, mock_av


# ---------------------------------------------------------------------------
# TestFromAC_ListTasksAdapter
# AC: list_tasks params forwarded; ListTasksResponse returned; errors mapped
# ---------------------------------------------------------------------------


class TestFromAC_ListTasksAdapter:
    """list_tasks MCP adapter delegates to AgentView and returns ListTasksResponse."""

    @pytest.mark.asyncio
    async def test_list_tasks_returns_list_tasks_response(
        self, app_ctx_with_mock_agent_view: tuple[object, MagicMock]
    ) -> None:
        """list_tasks returns a ListTasksResponse envelope, not a bare list."""
        from owlbear_mcp_kanban.server import list_tasks

        app_ctx, mock_av = app_ctx_with_mock_agent_view
        expected = ListTasksResponse(tasks=[_make_task_summary()], guidance=[], missing_ids=None)
        mock_av.list_tasks.return_value = expected

        ctx = _make_mcp_ctx(app_ctx)
        result = await list_tasks(ctx)

        assert isinstance(result, ListTasksResponse), "list_tasks must return ListTasksResponse, not a bare list"

    @pytest.mark.asyncio
    async def test_list_tasks_delegates_to_agent_view(
        self, app_ctx_with_mock_agent_view: tuple[object, MagicMock]
    ) -> None:
        """list_tasks calls engine.agent_view().list_tasks(), not engine.list_tasks()."""
        from owlbear_mcp_kanban.server import list_tasks

        app_ctx, mock_av = app_ctx_with_mock_agent_view
        mock_av.list_tasks.return_value = ListTasksResponse(tasks=[], guidance=[])

        ctx = _make_mcp_ctx(app_ctx)
        await list_tasks(ctx)

        mock_av.list_tasks.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_tasks_forwards_status_param(
        self, app_ctx_with_mock_agent_view: tuple[object, MagicMock]
    ) -> None:
        """list_tasks forwards status= to AgentView.list_tasks."""
        from owlbear_mcp_kanban.server import list_tasks

        app_ctx, mock_av = app_ctx_with_mock_agent_view
        mock_av.list_tasks.return_value = ListTasksResponse(tasks=[], guidance=[])

        ctx = _make_mcp_ctx(app_ctx)
        await list_tasks(ctx, status="todo")

        call_kwargs = mock_av.list_tasks.call_args
        assert call_kwargs is not None
        assert "todo" in str(call_kwargs), "status='todo' must be forwarded to AgentView.list_tasks"

    @pytest.mark.asyncio
    async def test_list_tasks_forwards_tag_param(self, app_ctx_with_mock_agent_view: tuple[object, MagicMock]) -> None:
        """list_tasks forwards tag= to AgentView.list_tasks."""
        from owlbear_mcp_kanban.server import list_tasks

        app_ctx, mock_av = app_ctx_with_mock_agent_view
        mock_av.list_tasks.return_value = ListTasksResponse(tasks=[], guidance=[])

        ctx = _make_mcp_ctx(app_ctx)
        await list_tasks(ctx, tag="phase-2")

        assert "phase-2" in str(mock_av.list_tasks.call_args), "tag='phase-2' must be forwarded to AgentView.list_tasks"

    @pytest.mark.asyncio
    async def test_list_tasks_forwards_priority_param(
        self, app_ctx_with_mock_agent_view: tuple[object, MagicMock]
    ) -> None:
        """list_tasks forwards priority= to AgentView.list_tasks."""
        from owlbear_mcp_kanban.server import list_tasks

        app_ctx, mock_av = app_ctx_with_mock_agent_view
        mock_av.list_tasks.return_value = ListTasksResponse(tasks=[], guidance=[])

        ctx = _make_mcp_ctx(app_ctx)
        await list_tasks(ctx, priority="critical")

        assert "critical" in str(mock_av.list_tasks.call_args), (
            "priority='critical' must be forwarded to AgentView.list_tasks"
        )

    @pytest.mark.asyncio
    async def test_list_tasks_forwards_ids_param(self, app_ctx_with_mock_agent_view: tuple[object, MagicMock]) -> None:
        """list_tasks forwards ids= to AgentView.list_tasks."""
        from owlbear_mcp_kanban.server import list_tasks

        app_ctx, mock_av = app_ctx_with_mock_agent_view
        ids = [1, 2, 3]
        mock_av.list_tasks.return_value = ListTasksResponse(tasks=[], guidance=[], missing_ids=[])

        ctx = _make_mcp_ctx(app_ctx)
        await list_tasks(ctx, ids=ids)

        assert str(ids) in str(mock_av.list_tasks.call_args), "ids=[1,2,3] must be forwarded to AgentView.list_tasks"

    @pytest.mark.asyncio
    async def test_list_tasks_envelope_returned_unmodified(
        self, app_ctx_with_mock_agent_view: tuple[object, MagicMock]
    ) -> None:
        """list_tasks returns the exact ListTasksResponse from AgentView unchanged."""
        from owlbear_mcp_kanban.server import list_tasks

        app_ctx, mock_av = app_ctx_with_mock_agent_view
        expected = ListTasksResponse(
            tasks=[_make_task_summary(id=7, title="Lucky")],
            guidance=["hint: check something"],
            missing_ids=None,
        )
        mock_av.list_tasks.return_value = expected

        ctx = _make_mcp_ctx(app_ctx)
        result = await list_tasks(ctx)

        assert result is expected or result == expected, "list_tasks must return ListTasksResponse envelope unmodified"

    @pytest.mark.asyncio
    async def test_list_tasks_ids_exclusivity_validation_error_mapped_to_tool_error(
        self, app_ctx_with_mock_agent_view: tuple[object, MagicMock]
    ) -> None:
        """AC15: ids + other filter → engine ValidationError → ToolError with user_message."""
        from owlbear_mcp_kanban.server import list_tasks

        app_ctx, mock_av = app_ctx_with_mock_agent_view
        mock_av.list_tasks.side_effect = ValidationError(
            code="ERR_IDS_EXCLUSIVE",
            user_message="ids cannot be combined with other filter parameters",
        )

        ctx = _make_mcp_ctx(app_ctx)
        with pytest.raises(ToolError) as exc_info:
            await list_tasks(ctx, status="todo", ids=[1])

        assert "ids" in str(exc_info.value).lower() or "exclusive" in str(exc_info.value).lower(), (
            "ToolError must carry user_message about ids exclusivity"
        )

    @pytest.mark.asyncio
    async def test_list_tasks_validation_error_message_preserved(
        self, app_ctx_with_mock_agent_view: tuple[object, MagicMock]
    ) -> None:
        """Engine ValidationError.user_message is forwarded as-is in ToolError."""
        from owlbear_mcp_kanban.server import list_tasks

        app_ctx, mock_av = app_ctx_with_mock_agent_view
        user_msg = "ids cannot be combined with other filter parameters"
        mock_av.list_tasks.side_effect = ValidationError(code="ERR_IDS_EXCLUSIVE", user_message=user_msg)

        ctx = _make_mcp_ctx(app_ctx)
        with pytest.raises(ToolError) as exc_info:
            await list_tasks(ctx, ids=[1], status="todo")

        assert user_msg in str(exc_info.value), "user_message from ValidationError must appear in ToolError"

    @pytest.mark.asyncio
    async def test_list_tasks_missing_ids_populated_in_envelope(
        self, app_ctx_with_mock_agent_view: tuple[object, MagicMock]
    ) -> None:
        """When ids used, ListTasksResponse.missing_ids may be non-empty."""
        from owlbear_mcp_kanban.server import list_tasks

        app_ctx, mock_av = app_ctx_with_mock_agent_view
        expected = ListTasksResponse(tasks=[], guidance=[], missing_ids=[99, 100])
        mock_av.list_tasks.return_value = expected

        ctx = _make_mcp_ctx(app_ctx)
        result = await list_tasks(ctx, ids=[1, 99, 100])

        assert isinstance(result, ListTasksResponse)
        assert result.missing_ids == [99, 100], "missing_ids from engine response must appear in returned envelope"

    # -- Retry: exact-kwargs tests for 7 params with no prior TestFromAC coverage --

    @pytest.mark.asyncio
    async def test_list_tasks_forwards_search_exact(
        self, app_ctx_with_mock_agent_view: tuple[object, MagicMock]
    ) -> None:
        """AC1: search= forwarded to AgentView.list_tasks — exact kwarg check."""
        from owlbear_mcp_kanban.server import list_tasks

        app_ctx, mock_av = app_ctx_with_mock_agent_view
        mock_av.list_tasks.return_value = ListTasksResponse(tasks=[], guidance=[])

        ctx = _make_mcp_ctx(app_ctx)
        await list_tasks(ctx, search="hello world")

        kw = mock_av.list_tasks.call_args.kwargs
        assert kw.get("search") == "hello world", (
            "search='hello world' must be forwarded as exact kwarg to AgentView.list_tasks"
        )

    @pytest.mark.asyncio
    async def test_list_tasks_forwards_sort_exact(self, app_ctx_with_mock_agent_view: tuple[object, MagicMock]) -> None:
        """AC1: sort= forwarded to AgentView.list_tasks — exact kwarg check."""
        from owlbear_mcp_kanban.server import list_tasks

        app_ctx, mock_av = app_ctx_with_mock_agent_view
        mock_av.list_tasks.return_value = ListTasksResponse(tasks=[], guidance=[])

        ctx = _make_mcp_ctx(app_ctx)
        await list_tasks(ctx, sort="priority")

        kw = mock_av.list_tasks.call_args.kwargs
        assert kw.get("sort") == "priority", "sort='priority' must be forwarded as exact kwarg to AgentView.list_tasks"

    @pytest.mark.asyncio
    async def test_list_tasks_forwards_unclaimed_exact(
        self, app_ctx_with_mock_agent_view: tuple[object, MagicMock]
    ) -> None:
        """AC1: unclaimed= forwarded to AgentView.list_tasks — exact kwarg check."""
        from owlbear_mcp_kanban.server import list_tasks

        app_ctx, mock_av = app_ctx_with_mock_agent_view
        mock_av.list_tasks.return_value = ListTasksResponse(tasks=[], guidance=[])

        ctx = _make_mcp_ctx(app_ctx)
        await list_tasks(ctx, unclaimed=True)

        kw = mock_av.list_tasks.call_args.kwargs
        assert kw.get("unclaimed") is True, "unclaimed=True must be forwarded as exact kwarg to AgentView.list_tasks"

    @pytest.mark.asyncio
    async def test_list_tasks_forwards_archival_reason_exact(
        self, app_ctx_with_mock_agent_view: tuple[object, MagicMock]
    ) -> None:
        """AC1: archival_reason= forwarded to AgentView.list_tasks — no legacy archived: bool."""
        from owlbear_mcp_kanban.server import list_tasks

        app_ctx, mock_av = app_ctx_with_mock_agent_view
        mock_av.list_tasks.return_value = ListTasksResponse(tasks=[], guidance=[])

        ctx = _make_mcp_ctx(app_ctx)
        await list_tasks(ctx, archival_reason="completed")

        kw = mock_av.list_tasks.call_args.kwargs
        assert kw.get("archival_reason") == "completed", (
            "archival_reason='completed' must be forwarded as exact kwarg to AgentView.list_tasks"
        )

    @pytest.mark.asyncio
    async def test_list_tasks_forwards_parent_exact(
        self, app_ctx_with_mock_agent_view: tuple[object, MagicMock]
    ) -> None:
        """AC1: parent= forwarded to AgentView.list_tasks — Brief A §5.1 field."""
        from owlbear_mcp_kanban.server import list_tasks

        app_ctx, mock_av = app_ctx_with_mock_agent_view
        mock_av.list_tasks.return_value = ListTasksResponse(tasks=[], guidance=[])

        ctx = _make_mcp_ctx(app_ctx)
        await list_tasks(ctx, parent=7)

        kw = mock_av.list_tasks.call_args.kwargs
        assert kw.get("parent") == 7, "parent=7 must be forwarded as exact kwarg to AgentView.list_tasks"

    @pytest.mark.asyncio
    async def test_list_tasks_forwards_limit_exact(
        self, app_ctx_with_mock_agent_view: tuple[object, MagicMock]
    ) -> None:
        """AC1: limit= forwarded to AgentView.list_tasks — exact kwarg check."""
        from owlbear_mcp_kanban.server import list_tasks

        app_ctx, mock_av = app_ctx_with_mock_agent_view
        mock_av.list_tasks.return_value = ListTasksResponse(tasks=[], guidance=[])

        ctx = _make_mcp_ctx(app_ctx)
        await list_tasks(ctx, limit=10)

        kw = mock_av.list_tasks.call_args.kwargs
        assert kw.get("limit") == 10, "limit=10 must be forwarded as exact kwarg to AgentView.list_tasks"

    @pytest.mark.asyncio
    async def test_list_tasks_forwards_reverse_exact(
        self, app_ctx_with_mock_agent_view: tuple[object, MagicMock]
    ) -> None:
        """AC1: reverse= forwarded to AgentView.list_tasks — exact kwarg check."""
        from owlbear_mcp_kanban.server import list_tasks

        app_ctx, mock_av = app_ctx_with_mock_agent_view
        mock_av.list_tasks.return_value = ListTasksResponse(tasks=[], guidance=[])

        ctx = _make_mcp_ctx(app_ctx)
        await list_tasks(ctx, reverse=True)

        kw = mock_av.list_tasks.call_args.kwargs
        assert kw.get("reverse") is True, "reverse=True must be forwarded as exact kwarg to AgentView.list_tasks"

    @pytest.mark.asyncio
    async def test_list_tasks_forwards_blocked_exact(
        self, app_ctx_with_mock_agent_view: tuple[object, MagicMock]
    ) -> None:
        """AC1: blocked= forwarded to AgentView.list_tasks — exact kwarg check."""
        from owlbear_mcp_kanban.server import list_tasks

        app_ctx, mock_av = app_ctx_with_mock_agent_view
        mock_av.list_tasks.return_value = ListTasksResponse(tasks=[], guidance=[])

        ctx = _make_mcp_ctx(app_ctx)
        await list_tasks(ctx, blocked=True)

        kw = mock_av.list_tasks.call_args.kwargs
        assert kw.get("blocked") is True, "blocked=True must be forwarded as exact kwarg to AgentView.list_tasks"

    @pytest.mark.asyncio
    async def test_list_tasks_forwards_all_twelve_params_exact(
        self, app_ctx_with_mock_agent_view: tuple[object, MagicMock]
    ) -> None:
        """AC1: 11 non-ids Brief A §5.1 params forwarded to AgentView — no legacy archived: bool.

        NOTE: ids= cannot be combined with other filter params per ListTasksParams validator
        (AC15 exclusivity). This test verifies the 11 non-ids params forwarded together.
        ids forwarding proven by test_list_tasks_forwards_ids_param.
        """
        from owlbear_mcp_kanban.server import list_tasks

        app_ctx, mock_av = app_ctx_with_mock_agent_view
        mock_av.list_tasks.return_value = ListTasksResponse(tasks=[], guidance=[], missing_ids=[])

        ctx = _make_mcp_ctx(app_ctx)
        await list_tasks(
            ctx,
            status="todo",
            tag="phase-2",
            priority="critical",
            archival_reason="completed",
            unclaimed=True,
            blocked=True,
            parent=5,
            search="hello",
            sort="priority",
            reverse=True,
            limit=5,
            # ids omitted: cannot be combined with other filter params (ListTasksParams)
        )

        kw = mock_av.list_tasks.call_args.kwargs
        assert kw["status"] == "todo"
        assert kw["tag"] == "phase-2"
        assert kw["priority"] == "critical"
        assert kw["archival_reason"] == "completed"
        assert kw["unclaimed"] is True
        assert kw["blocked"] is True
        assert kw["parent"] == 5
        assert kw["search"] == "hello"
        assert kw["sort"] == "priority"
        assert kw["reverse"] is True
        assert kw["limit"] == 5
        assert "archived" not in kw, "legacy archived: bool must NOT appear on the MCP surface (Brief A §5.1)"


# ---------------------------------------------------------------------------
# TestFromAC_ShowTaskAdapter
# AC: show_task id + section forwarded; ShowTaskResponse returned;
#     missing_sections case (AC11); NotFoundError → ToolError
# ---------------------------------------------------------------------------


class TestFromAC_ShowTaskAdapter:
    """show_task MCP adapter delegates to AgentView and returns ShowTaskResponse."""

    @pytest.mark.asyncio
    async def test_show_task_returns_show_task_response(
        self, app_ctx_with_mock_agent_view: tuple[object, MagicMock]
    ) -> None:
        """show_task returns a ShowTaskResponse, not a KanbanTask."""
        from owlbear_mcp_kanban.server import show_task

        app_ctx, mock_av = app_ctx_with_mock_agent_view
        expected = _make_show_task_response()
        mock_av.show_task.return_value = expected

        ctx = _make_mcp_ctx(app_ctx)
        result = await show_task(ctx, id=42)

        assert isinstance(result, ShowTaskResponse), "show_task must return ShowTaskResponse, not KanbanTask"

    @pytest.mark.asyncio
    async def test_show_task_delegates_to_agent_view(
        self, app_ctx_with_mock_agent_view: tuple[object, MagicMock]
    ) -> None:
        """show_task calls engine.agent_view().show_task(), not engine.show_task()."""
        from owlbear_mcp_kanban.server import show_task

        app_ctx, mock_av = app_ctx_with_mock_agent_view
        mock_av.show_task.return_value = _make_show_task_response()

        ctx = _make_mcp_ctx(app_ctx)
        await show_task(ctx, id=42)

        mock_av.show_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_show_task_forwards_task_id(self, app_ctx_with_mock_agent_view: tuple[object, MagicMock]) -> None:
        """show_task forwards task id to AgentView.show_task."""
        from owlbear_mcp_kanban.server import show_task

        app_ctx, mock_av = app_ctx_with_mock_agent_view
        mock_av.show_task.return_value = _make_show_task_response(id=42)

        ctx = _make_mcp_ctx(app_ctx)
        await show_task(ctx, id=42)

        # id 42 must appear in the call arguments
        assert "42" in str(mock_av.show_task.call_args) or 42 in str(mock_av.show_task.call_args), (
            "task id=42 must be forwarded to AgentView.show_task"
        )

    @pytest.mark.asyncio
    async def test_show_task_forwards_section_param(
        self, app_ctx_with_mock_agent_view: tuple[object, MagicMock]
    ) -> None:
        """show_task forwards section= kwarg to AgentView.show_task."""
        from owlbear_mcp_kanban.server import show_task

        app_ctx, mock_av = app_ctx_with_mock_agent_view
        mock_av.show_task.return_value = _make_show_task_response(body="## Notes\nHello", missing_sections=None)

        ctx = _make_mcp_ctx(app_ctx)
        await show_task(ctx, id=42, section="Notes")

        assert "Notes" in str(mock_av.show_task.call_args), "section='Notes' must be forwarded to AgentView.show_task"

    @pytest.mark.asyncio
    async def test_show_task_envelope_returned_unmodified(
        self, app_ctx_with_mock_agent_view: tuple[object, MagicMock]
    ) -> None:
        """show_task returns the ShowTaskResponse from AgentView unchanged."""
        from owlbear_mcp_kanban.server import show_task

        app_ctx, mock_av = app_ctx_with_mock_agent_view
        expected = _make_show_task_response(id=42, body="Full body", guidance=["hint1"])
        mock_av.show_task.return_value = expected

        ctx = _make_mcp_ctx(app_ctx)
        result = await show_task(ctx, id=42)

        assert result is expected or result == expected, "show_task must return ShowTaskResponse envelope unmodified"

    @pytest.mark.asyncio
    async def test_show_task_missing_sections_case_preserved(
        self, app_ctx_with_mock_agent_view: tuple[object, MagicMock]
    ) -> None:
        """AC11: when section not found, ShowTaskResponse.missing_sections is populated."""
        from owlbear_mcp_kanban.server import show_task

        app_ctx, mock_av = app_ctx_with_mock_agent_view
        expected = _make_show_task_response(body=None, missing_sections=["NonExistentSection"], guidance=[])
        mock_av.show_task.return_value = expected

        ctx = _make_mcp_ctx(app_ctx)
        result = await show_task(ctx, id=42, section="NonExistentSection")

        assert isinstance(result, ShowTaskResponse)
        assert result.missing_sections == ["NonExistentSection"], (
            "missing_sections from engine must be present in returned ShowTaskResponse"
        )
        assert result.body is None, "body must be None when section not found"

    @pytest.mark.asyncio
    async def test_show_task_not_found_raises_tool_error(
        self, app_ctx_with_mock_agent_view: tuple[object, MagicMock]
    ) -> None:
        """show_task: engine NotFoundError from AgentView → MCP ToolError."""
        from owlbear_mcp_kanban.server import show_task

        app_ctx, mock_av = app_ctx_with_mock_agent_view
        mock_av.show_task.side_effect = NotFoundError(
            code="ERR_NOT_FOUND",
            user_message="task 999 not found",
        )

        ctx = _make_mcp_ctx(app_ctx)
        with pytest.raises(ToolError):
            await show_task(ctx, id=999)

        # The error must originate from AgentView.show_task, not engine.show_task.
        mock_av.show_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_show_task_not_found_user_message_in_tool_error(
        self, app_ctx_with_mock_agent_view: tuple[object, MagicMock]
    ) -> None:
        """show_task: NotFoundError.user_message is forwarded in ToolError."""
        from owlbear_mcp_kanban.server import show_task

        app_ctx, mock_av = app_ctx_with_mock_agent_view
        user_msg = "task 999 not found"
        mock_av.show_task.side_effect = NotFoundError(code="ERR_NOT_FOUND", user_message=user_msg)

        ctx = _make_mcp_ctx(app_ctx)
        with pytest.raises(ToolError) as exc_info:
            await show_task(ctx, id=999)

        assert user_msg in str(exc_info.value), "user_message from NotFoundError must appear in ToolError"

    @pytest.mark.asyncio
    async def test_show_task_validation_error_mapped_to_tool_error(
        self, app_ctx_with_mock_agent_view: tuple[object, MagicMock]
    ) -> None:
        """show_task: engine ValidationError (e.g. empty section) → MCP ToolError."""
        from owlbear_mcp_kanban.server import show_task

        app_ctx, mock_av = app_ctx_with_mock_agent_view
        mock_av.show_task.side_effect = ValidationError(
            code="ERR_SECTION_EMPTY",
            user_message="section must not be an empty string",
        )

        ctx = _make_mcp_ctx(app_ctx)
        with pytest.raises(ToolError) as exc_info:
            await show_task(ctx, id=42, section="")

        assert "section" in str(exc_info.value).lower() or "empty" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_show_task_empty_section_not_normalized_passthrough(
        self, app_ctx_with_mock_agent_view: tuple[object, MagicMock]
    ) -> None:
        """AC2: section='' must be passed through to engine unmodified — engine raises ValidationError.

        Brief A §5.2: adapter must NOT normalize section='' to None. Engine is the authority
        on what section values are valid; ValidationError from engine → ToolError.
        """
        from owlbear_mcp_kanban.server import show_task

        app_ctx, mock_av = app_ctx_with_mock_agent_view
        mock_av.show_task.side_effect = ValidationError(
            code="ERR_SECTION_EMPTY",
            user_message="section must not be an empty string",
        )

        ctx = _make_mcp_ctx(app_ctx)
        with pytest.raises(ToolError):
            await show_task(ctx, id=42, section="")

        # Engine was called with section="" not section=None — no adapter normalization
        kw = mock_av.show_task.call_args.kwargs
        assert kw.get("section") == "", (
            "adapter must forward section='' to engine as-is (Brief A §5.2); engine raises ValidationError, not adapter"
        )

    @pytest.mark.asyncio
    async def test_show_task_nonempty_section_forwarded_exact(
        self, app_ctx_with_mock_agent_view: tuple[object, MagicMock]
    ) -> None:
        """AC2: non-empty section= forwarded as exact kwarg to AgentView.show_task."""
        from owlbear_mcp_kanban.server import show_task

        app_ctx, mock_av = app_ctx_with_mock_agent_view
        mock_av.show_task.return_value = _make_show_task_response()

        ctx = _make_mcp_ctx(app_ctx)
        await show_task(ctx, id=42, section="Builder Notes")

        kw = mock_av.show_task.call_args.kwargs
        assert kw.get("section") == "Builder Notes", (
            "section='Builder Notes' must be forwarded as exact kwarg to AgentView.show_task"
        )

    @pytest.mark.asyncio
    async def test_show_task_id_forwarded_exact(self, app_ctx_with_mock_agent_view: tuple[object, MagicMock]) -> None:
        """AC2: id= forwarded to AgentView.show_task matching ShowTaskParams.id: int."""
        from owlbear_mcp_kanban.server import show_task

        app_ctx, mock_av = app_ctx_with_mock_agent_view
        mock_av.show_task.return_value = _make_show_task_response(id=77)

        ctx = _make_mcp_ctx(app_ctx)
        await show_task(ctx, id=77)

        kw = mock_av.show_task.call_args.kwargs
        assert kw.get("task_id") == 77, "id=77 must be forwarded as task_id kwarg to AgentView.show_task"


# ---------------------------------------------------------------------------
# TestFromAC_PickTasksAdapter
# AC: wave_size + max_waves forwarded; PickTasksResponse with waves returned (AC22, AC23)
# ---------------------------------------------------------------------------


class TestFromAC_PickTasksAdapter:
    """pick_tasks MCP adapter delegates to AgentView and returns PickTasksResponse."""

    @pytest.mark.asyncio
    async def test_pick_tasks_returns_pick_tasks_response(
        self, app_ctx_with_mock_agent_view: tuple[object, MagicMock]
    ) -> None:
        """pick_tasks returns a PickTasksResponse envelope with waves."""
        from owlbear_mcp_kanban.server import pick_tasks

        app_ctx, mock_av = app_ctx_with_mock_agent_view
        expected = PickTasksResponse(waves=[], guidance=[])
        mock_av.pick_tasks.return_value = expected

        ctx = _make_mcp_ctx(app_ctx)
        result = await pick_tasks(ctx)

        assert isinstance(result, PickTasksResponse), "pick_tasks must return PickTasksResponse, not a dict"

    @pytest.mark.asyncio
    async def test_pick_tasks_delegates_to_agent_view(
        self, app_ctx_with_mock_agent_view: tuple[object, MagicMock]
    ) -> None:
        """pick_tasks calls engine.agent_view().pick_tasks()."""
        from owlbear_mcp_kanban.server import pick_tasks

        app_ctx, mock_av = app_ctx_with_mock_agent_view
        mock_av.pick_tasks.return_value = PickTasksResponse(waves=[], guidance=[])

        ctx = _make_mcp_ctx(app_ctx)
        await pick_tasks(ctx)

        mock_av.pick_tasks.assert_called_once()

    @pytest.mark.asyncio
    async def test_pick_tasks_forwards_wave_size(self, app_ctx_with_mock_agent_view: tuple[object, MagicMock]) -> None:
        """AC22: wave_size forwarded to AgentView.pick_tasks."""
        from owlbear_mcp_kanban.server import pick_tasks

        app_ctx, mock_av = app_ctx_with_mock_agent_view
        mock_av.pick_tasks.return_value = PickTasksResponse(waves=[], guidance=[])

        ctx = _make_mcp_ctx(app_ctx)
        await pick_tasks(ctx, wave_size=2)

        assert "2" in str(mock_av.pick_tasks.call_args) or 2 in str(mock_av.pick_tasks.call_args), (
            "wave_size=2 must be forwarded to AgentView.pick_tasks"
        )

    @pytest.mark.asyncio
    async def test_pick_tasks_forwards_max_waves(self, app_ctx_with_mock_agent_view: tuple[object, MagicMock]) -> None:
        """AC23: max_waves forwarded to AgentView.pick_tasks."""
        from owlbear_mcp_kanban.server import pick_tasks

        app_ctx, mock_av = app_ctx_with_mock_agent_view
        mock_av.pick_tasks.return_value = PickTasksResponse(waves=[], guidance=[])

        ctx = _make_mcp_ctx(app_ctx)
        await pick_tasks(ctx, max_waves=5)

        assert "5" in str(mock_av.pick_tasks.call_args) or 5 in str(mock_av.pick_tasks.call_args), (
            "max_waves=5 must be forwarded to AgentView.pick_tasks"
        )

    @pytest.mark.asyncio
    async def test_pick_tasks_envelope_returned_unmodified(
        self, app_ctx_with_mock_agent_view: tuple[object, MagicMock]
    ) -> None:
        """pick_tasks returns the PickTasksResponse from AgentView unchanged."""
        from owlbear_mcp_kanban.server import pick_tasks

        app_ctx, mock_av = app_ctx_with_mock_agent_view
        dispatch_entry = DispatchEntry(id=1, status="todo", priority="important", title="Task A", agent="builder")
        wave = Wave(index=0, tasks=[dispatch_entry])
        expected = PickTasksResponse(waves=[wave], guidance=["dispatch ready"])
        mock_av.pick_tasks.return_value = expected

        ctx = _make_mcp_ctx(app_ctx)
        result = await pick_tasks(ctx)

        assert isinstance(result, PickTasksResponse)
        assert len(result.waves) == 1, "waves must be returned unmodified"
        assert result.waves[0].tasks[0].id == 1

    @pytest.mark.asyncio
    async def test_pick_tasks_wave_size_none_forwarded(
        self, app_ctx_with_mock_agent_view: tuple[object, MagicMock]
    ) -> None:
        """wave_size=None (default) falls back to engine config default — must be forwarded."""
        from owlbear_mcp_kanban.server import pick_tasks

        app_ctx, mock_av = app_ctx_with_mock_agent_view
        mock_av.pick_tasks.return_value = PickTasksResponse(waves=[], guidance=[])

        ctx = _make_mcp_ctx(app_ctx)
        # Call with no wave_size — None should be forwarded
        await pick_tasks(ctx, max_waves=3)

        mock_av.pick_tasks.assert_called_once()
        call = mock_av.pick_tasks.call_args
        # wave_size=None must appear (not be suppressed)
        assert call is not None, "AgentView.pick_tasks must have been called"

    @pytest.mark.asyncio
    async def test_pick_tasks_validation_error_mapped_to_tool_error(
        self, app_ctx_with_mock_agent_view: tuple[object, MagicMock]
    ) -> None:
        """pick_tasks: engine ValidationError (wave_size < 1) → MCP ToolError."""
        from owlbear_mcp_kanban.server import pick_tasks

        app_ctx, mock_av = app_ctx_with_mock_agent_view
        mock_av.pick_tasks.side_effect = ValidationError(
            code="ERR_INVALID_WAVE_PARAM",
            user_message="wave_size must be >= 1",
        )

        ctx = _make_mcp_ctx(app_ctx)
        with pytest.raises(ToolError) as exc_info:
            await pick_tasks(ctx, wave_size=0)

        assert "wave" in str(exc_info.value).lower() or "1" in str(exc_info.value), (
            "ToolError must carry user_message about invalid wave_size"
        )

    @pytest.mark.asyncio
    async def test_pick_tasks_max_waves_validation_error_mapped(
        self, app_ctx_with_mock_agent_view: tuple[object, MagicMock]
    ) -> None:
        """pick_tasks: engine ValidationError (max_waves < 1) → MCP ToolError."""
        from owlbear_mcp_kanban.server import pick_tasks

        app_ctx, mock_av = app_ctx_with_mock_agent_view
        mock_av.pick_tasks.side_effect = ValidationError(
            code="ERR_INVALID_WAVE_PARAM",
            user_message="max_waves must be >= 1",
        )

        ctx = _make_mcp_ctx(app_ctx)
        with pytest.raises(ToolError) as exc_info:
            await pick_tasks(ctx, max_waves=0)

        assert "max_waves" in str(exc_info.value).lower() or "1" in str(exc_info.value), (
            "ToolError must carry user_message about invalid max_waves"
        )

    # -- Retry: exact-kwargs forwarding tests for pick_tasks --

    @pytest.mark.asyncio
    async def test_pick_tasks_forwards_wave_size_exact(
        self, app_ctx_with_mock_agent_view: tuple[object, MagicMock]
    ) -> None:
        """AC5/AC22: wave_size= forwarded to AgentView.pick_tasks as exact kwarg."""
        from owlbear_mcp_kanban.server import pick_tasks

        app_ctx, mock_av = app_ctx_with_mock_agent_view
        mock_av.pick_tasks.return_value = PickTasksResponse(waves=[], guidance=[])

        ctx = _make_mcp_ctx(app_ctx)
        await pick_tasks(ctx, wave_size=4)

        kw = mock_av.pick_tasks.call_args.kwargs
        assert kw.get("wave_size") == 4, "wave_size=4 must be forwarded as exact kwarg to AgentView.pick_tasks"

    @pytest.mark.asyncio
    async def test_pick_tasks_forwards_max_waves_exact(
        self, app_ctx_with_mock_agent_view: tuple[object, MagicMock]
    ) -> None:
        """AC5/AC23: max_waves= forwarded to AgentView.pick_tasks as exact kwarg."""
        from owlbear_mcp_kanban.server import pick_tasks

        app_ctx, mock_av = app_ctx_with_mock_agent_view
        mock_av.pick_tasks.return_value = PickTasksResponse(waves=[], guidance=[])

        ctx = _make_mcp_ctx(app_ctx)
        await pick_tasks(ctx, max_waves=7)

        kw = mock_av.pick_tasks.call_args.kwargs
        assert kw.get("max_waves") == 7, "max_waves=7 must be forwarded as exact kwarg to AgentView.pick_tasks"

    @pytest.mark.asyncio
    async def test_pick_tasks_wave_size_none_forwarded_exact(
        self, app_ctx_with_mock_agent_view: tuple[object, MagicMock]
    ) -> None:
        """AC5: wave_size=None (default) forwarded to AgentView with exact None kwarg."""
        from owlbear_mcp_kanban.server import pick_tasks

        app_ctx, mock_av = app_ctx_with_mock_agent_view
        mock_av.pick_tasks.return_value = PickTasksResponse(waves=[], guidance=[])

        ctx = _make_mcp_ctx(app_ctx)
        await pick_tasks(ctx)

        kw = mock_av.pick_tasks.call_args.kwargs
        assert "wave_size" in kw, "wave_size kwarg must be present even when None"
        assert kw["wave_size"] is None, "wave_size=None must be forwarded as exact None kwarg to AgentView.pick_tasks"


# ---------------------------------------------------------------------------
# TestFromAC_ErrorMapping
# AC: KanbanError subclasses (ValidationError, NotFoundError) → ToolError with user_message
# Cross-cutting across all 3 adapters
# ---------------------------------------------------------------------------


class TestFromAC_ErrorMapping:
    """Cross-cutting: KanbanError subclasses → MCP ToolError with user_message."""

    @pytest.mark.asyncio
    async def test_list_tasks_not_found_error_mapped_to_tool_error(
        self, app_ctx_with_mock_agent_view: tuple[object, MagicMock]
    ) -> None:
        """list_tasks: engine NotFoundError → ToolError (e.g. invalid ids lookup)."""
        from owlbear_mcp_kanban.server import list_tasks

        app_ctx, mock_av = app_ctx_with_mock_agent_view
        mock_av.list_tasks.side_effect = NotFoundError(
            code="ERR_NOT_FOUND",
            user_message="task 99 not found",
        )

        ctx = _make_mcp_ctx(app_ctx)
        with pytest.raises(ToolError) as exc_info:
            await list_tasks(ctx, ids=[99])

        assert "99" in str(exc_info.value) or "not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_tool_error_carries_user_message_not_code(
        self, app_ctx_with_mock_agent_view: tuple[object, MagicMock]
    ) -> None:
        """ToolError text is JSON with both 'code' and 'message' fields."""
        from owlbear_mcp_kanban.server import show_task

        app_ctx, mock_av = app_ctx_with_mock_agent_view
        user_msg = "task 42 not found"
        mock_av.show_task.side_effect = NotFoundError(code="ERR_NOT_FOUND", user_message=user_msg)

        ctx = _make_mcp_ctx(app_ctx)
        with pytest.raises(ToolError) as exc_info:
            await show_task(ctx, id=42)

        payload = json.loads(str(exc_info.value))
        assert payload["code"] == "ERR_NOT_FOUND", f"ToolError JSON must carry parseable error code; got {payload!r}"
        assert payload["message"] == user_msg, f"ToolError JSON must carry human-readable user_message; got {payload!r}"

    @pytest.mark.asyncio
    async def test_pick_tasks_not_found_mapped_to_tool_error(
        self, app_ctx_with_mock_agent_view: tuple[object, MagicMock]
    ) -> None:
        """pick_tasks: any NotFoundError from AgentView → MCP ToolError."""
        from owlbear_mcp_kanban.server import pick_tasks

        app_ctx, mock_av = app_ctx_with_mock_agent_view
        mock_av.pick_tasks.side_effect = NotFoundError(
            code="ERR_NOT_FOUND",
            user_message="internal dependency not found",
        )

        ctx = _make_mcp_ctx(app_ctx)
        with pytest.raises(ToolError):
            await pick_tasks(ctx)

    # -- Retry: exact user_message preservation tests --

    @pytest.mark.asyncio
    async def test_list_tasks_not_found_user_message_preserved_exact(
        self, app_ctx_with_mock_agent_view: tuple[object, MagicMock]
    ) -> None:
        """AC7: list_tasks NotFoundError.user_message preserved exactly in ToolError."""
        from owlbear_mcp_kanban.server import list_tasks

        app_ctx, mock_av = app_ctx_with_mock_agent_view
        user_msg = "task 99 not found"
        mock_av.list_tasks.side_effect = NotFoundError(code="ERR_NOT_FOUND", user_message=user_msg)

        ctx = _make_mcp_ctx(app_ctx)
        with pytest.raises(ToolError) as exc_info:
            await list_tasks(ctx, ids=[99])

        assert user_msg in str(exc_info.value), (
            "NotFoundError.user_message must be preserved in ToolError for list_tasks"
        )

    @pytest.mark.asyncio
    async def test_pick_tasks_not_found_user_message_preserved_exact(
        self, app_ctx_with_mock_agent_view: tuple[object, MagicMock]
    ) -> None:
        """AC7: pick_tasks NotFoundError.user_message preserved in ToolError (exact check)."""
        from owlbear_mcp_kanban.server import pick_tasks

        app_ctx, mock_av = app_ctx_with_mock_agent_view
        user_msg = "internal dependency not found"
        mock_av.pick_tasks.side_effect = NotFoundError(code="ERR_NOT_FOUND", user_message=user_msg)

        ctx = _make_mcp_ctx(app_ctx)
        with pytest.raises(ToolError) as exc_info:
            await pick_tasks(ctx)

        assert user_msg in str(exc_info.value), (
            "NotFoundError.user_message must be preserved in ToolError for pick_tasks"
        )

    @pytest.mark.asyncio
    async def test_pick_tasks_validation_error_user_message_preserved_exact(
        self, app_ctx_with_mock_agent_view: tuple[object, MagicMock]
    ) -> None:
        """AC6: pick_tasks ValidationError.user_message preserved exactly in ToolError."""
        from owlbear_mcp_kanban.server import pick_tasks

        app_ctx, mock_av = app_ctx_with_mock_agent_view
        user_msg = "wave_size must be >= 1"
        mock_av.pick_tasks.side_effect = ValidationError(code="ERR_INVALID_WAVE_PARAM", user_message=user_msg)

        ctx = _make_mcp_ctx(app_ctx)
        with pytest.raises(ToolError) as exc_info:
            await pick_tasks(ctx, wave_size=0)

        assert user_msg in str(exc_info.value), (
            "ValidationError.user_message must be preserved exactly in ToolError for pick_tasks"
        )

    @pytest.mark.asyncio
    async def test_show_task_validation_error_user_message_preserved_exact(
        self, app_ctx_with_mock_agent_view: tuple[object, MagicMock]
    ) -> None:
        """AC6: show_task ValidationError.user_message preserved exactly in ToolError."""
        from owlbear_mcp_kanban.server import show_task

        app_ctx, mock_av = app_ctx_with_mock_agent_view
        user_msg = "section must not be an empty string"
        mock_av.show_task.side_effect = ValidationError(code="ERR_SECTION_EMPTY", user_message=user_msg)

        ctx = _make_mcp_ctx(app_ctx)
        with pytest.raises(ToolError) as exc_info:
            await show_task(ctx, id=42, section="")

        assert user_msg in str(exc_info.value), (
            "ValidationError.user_message must be preserved exactly in ToolError for show_task"
        )
