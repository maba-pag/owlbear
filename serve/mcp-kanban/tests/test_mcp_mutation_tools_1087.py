"""RED phase tests — MCP mutation tool adapters (#1087).

Tests the 2 mutation tool adapters: create_task, edit_task.
All tests mock AgentView — the adapter is a mechanical translator;
engine validation is AgentView/Brief B's responsibility.

Tests verify:
- Correct AgentView method called with correct args
- SingleTaskResponse returned unmodified
- KanbanError subclasses mapped to MCP ToolError with user_message

AC coverage:
- create_task: title, body, priority, tags, parent, depends_on forwarded to AgentView
- create_task: no status parameter (engine controls entry status per D50)
- create_task: SingleTaskResponse returned
- create_task: dep validation delegated — ValidationError(ERR_DEP_NOT_FOUND) → ToolError (AC24)
- edit_task: all 13 params forwarded to AgentView.edit_task
- edit_task: SingleTaskResponse returned
- edit_task: body + append_body → ValidationError(ERR_BODY_EXCLUSIVE) → ToolError (AC14)
- edit_task: archival_reason/archival_refs on non-archived → ValidationError → ToolError
- edit_task: no-op call → ValidationError(ERR_NO_OP) → ToolError
- Error mapping: all KanbanError subclasses → ToolError with user_message
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from owlbear_kanban.errors import (
    ConcurrencyError,
    NotFoundError,
    ValidationError,
)
from owlbear_kanban.models import SingleTaskResponse

from owlbear_mcp_kanban.server import AppContext, create_task, edit_task


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


def _make_single_task_response(**overrides: object) -> SingleTaskResponse:
    defaults: dict[str, object] = {
        "id": 1,
        "title": "Test Task",
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
        "body": "",
        "guidance": [],
    }
    defaults.update(overrides)
    return SingleTaskResponse.model_validate(defaults)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def app_ctx_with_mock_agent_view(
    tmp_path: Path,
) -> tuple[AppContext, MagicMock]:
    """AppContext with one active task; engine.agent_view() returns MagicMock."""
    from owlbear_kanban import KanbanEngine

    kanban_dir = _make_board(tmp_path)
    engine = KanbanEngine(kanban_dir)
    # Create one task so edit_task calls have a valid target
    engine.create_task("Initial task", status="todo", priority="important")
    engine.list_tasks()  # populate id_to_filename cache
    mock_av = MagicMock()
    mock_av.create_task.return_value = _make_single_task_response()
    mock_av.edit_task.return_value = _make_single_task_response()
    engine._agent_view = mock_av  # noqa: SLF001
    app_ctx = AppContext(engine=engine, kanban_dir=kanban_dir)
    return app_ctx, mock_av


# ---------------------------------------------------------------------------
# TestFromAC_CreateTaskAdapter
# AC: create_task params forwarded to AgentView; no status; SingleTaskResponse returned
# ---------------------------------------------------------------------------


class TestFromAC_CreateTaskAdapter:
    """create_task MCP adapter delegates to AgentView and returns SingleTaskResponse."""

    @pytest.mark.asyncio
    async def test_create_task_calls_agent_view_create_task(
        self, app_ctx_with_mock_agent_view: tuple[AppContext, MagicMock]
    ) -> None:
        """Adapter must call AgentView.create_task (not engine.create_task directly)."""
        app_ctx, mock_av = app_ctx_with_mock_agent_view
        ctx = _make_mcp_ctx(app_ctx)
        await create_task(ctx, title="New Feature")
        mock_av.create_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_task_forwards_title(
        self, app_ctx_with_mock_agent_view: tuple[AppContext, MagicMock]
    ) -> None:
        """Adapter must forward title to AgentView.create_task (positional or keyword)."""
        app_ctx, mock_av = app_ctx_with_mock_agent_view
        ctx = _make_mcp_ctx(app_ctx)
        await create_task(ctx, title="My Feature")
        call = mock_av.create_task.call_args
        title_val = call.args[0] if call.args else call.kwargs.get("title")
        assert title_val == "My Feature", "title not forwarded to AgentView.create_task"

    @pytest.mark.asyncio
    async def test_create_task_forwards_body(
        self, app_ctx_with_mock_agent_view: tuple[AppContext, MagicMock]
    ) -> None:
        """body must be forwarded to AgentView.create_task."""
        app_ctx, mock_av = app_ctx_with_mock_agent_view
        ctx = _make_mcp_ctx(app_ctx)
        await create_task(ctx, title="T", body="## AC\n\n- Do the thing")
        _, kwargs = mock_av.create_task.call_args
        assert kwargs.get("body") == "## AC\n\n- Do the thing", (
            "body not forwarded to AgentView.create_task"
        )

    @pytest.mark.asyncio
    async def test_create_task_forwards_priority(
        self, app_ctx_with_mock_agent_view: tuple[AppContext, MagicMock]
    ) -> None:
        """priority must be forwarded to AgentView.create_task."""
        app_ctx, mock_av = app_ctx_with_mock_agent_view
        ctx = _make_mcp_ctx(app_ctx)
        await create_task(ctx, title="T", priority="critical")
        _, kwargs = mock_av.create_task.call_args
        assert kwargs.get("priority") == "critical", (
            "priority not forwarded to AgentView.create_task"
        )

    @pytest.mark.asyncio
    async def test_create_task_forwards_tags_as_list(
        self, app_ctx_with_mock_agent_view: tuple[AppContext, MagicMock]
    ) -> None:
        """tags must be forwarded to AgentView.create_task as list[str]."""
        app_ctx, mock_av = app_ctx_with_mock_agent_view
        ctx = _make_mcp_ctx(app_ctx)
        await create_task(ctx, title="T", tags=["phase-2", "scope:mcp"])
        _, kwargs = mock_av.create_task.call_args
        assert kwargs.get("tags") == ["phase-2", "scope:mcp"], (
            "tags not forwarded as list to AgentView.create_task"
        )

    @pytest.mark.asyncio
    async def test_create_task_forwards_parent(
        self, app_ctx_with_mock_agent_view: tuple[AppContext, MagicMock]
    ) -> None:
        """parent must be forwarded to AgentView.create_task."""
        app_ctx, mock_av = app_ctx_with_mock_agent_view
        ctx = _make_mcp_ctx(app_ctx)
        await create_task(ctx, title="T", parent=42)
        _, kwargs = mock_av.create_task.call_args
        assert kwargs.get("parent") == 42, (
            "parent not forwarded to AgentView.create_task"
        )

    @pytest.mark.asyncio
    async def test_create_task_forwards_depends_on_as_list(
        self, app_ctx_with_mock_agent_view: tuple[AppContext, MagicMock]
    ) -> None:
        """depends_on must be forwarded to AgentView.create_task as list[int]."""
        app_ctx, mock_av = app_ctx_with_mock_agent_view
        ctx = _make_mcp_ctx(app_ctx)
        await create_task(ctx, title="T", depends_on=[10, 20])
        _, kwargs = mock_av.create_task.call_args
        assert kwargs.get("depends_on") == [10, 20], (
            "depends_on not forwarded as list[int] to AgentView.create_task"
        )

    @pytest.mark.asyncio
    async def test_create_task_returns_single_task_response(
        self, app_ctx_with_mock_agent_view: tuple[AppContext, MagicMock]
    ) -> None:
        """create_task must return SingleTaskResponse (not KanbanTask or Task)."""
        app_ctx, mock_av = app_ctx_with_mock_agent_view
        expected = _make_single_task_response(id=7, title="New Task")
        mock_av.create_task.return_value = expected
        ctx = _make_mcp_ctx(app_ctx)
        result = await create_task(ctx, title="New Task")
        assert result is expected, (
            "create_task must return the unmodified SingleTaskResponse from AgentView — "
            f"passthrough fidelity required; got {type(result).__name__}"
        )

    def test_create_task_has_no_status_parameter(self) -> None:
        """create_task must not accept a status parameter — engine controls entry status (D50)."""
        params = inspect.signature(create_task).parameters
        assert "status" not in params, (
            "create_task must not expose a 'status' parameter per D50; "
            f"got params: {list(params)}"
        )

    @pytest.mark.asyncio
    async def test_create_task_dep_not_found_raises_tool_error(
        self, app_ctx_with_mock_agent_view: tuple[AppContext, MagicMock]
    ) -> None:
        """ValidationError(ERR_DEP_NOT_FOUND) from AgentView maps to ToolError (AC24)."""
        app_ctx, mock_av = app_ctx_with_mock_agent_view
        mock_av.create_task.side_effect = ValidationError(
            code="ERR_DEP_NOT_FOUND",
            user_message="dependency 99999 not found",
        )
        ctx = _make_mcp_ctx(app_ctx)
        with pytest.raises(ToolError) as exc_info:
            await create_task(ctx, title="T", depends_on=[99999])
        mock_av.create_task.assert_called_once()
        assert "dependency 99999 not found" in str(exc_info.value), (
            "ToolError must carry the user_message from ValidationError"
        )


# ---------------------------------------------------------------------------
# TestFromAC_EditTaskAdapter
# AC: edit_task forwards all 14 params to AgentView; SingleTaskResponse returned;
#     error cases mapped to ToolError
# ---------------------------------------------------------------------------


class TestFromAC_EditTaskAdapter:
    """edit_task MCP adapter delegates to AgentView and returns SingleTaskResponse."""

    @pytest.mark.asyncio
    async def test_edit_task_calls_agent_view_edit_task(
        self, app_ctx_with_mock_agent_view: tuple[AppContext, MagicMock]
    ) -> None:
        """Adapter must call AgentView.edit_task (not engine.edit_task directly)."""
        app_ctx, mock_av = app_ctx_with_mock_agent_view
        ctx = _make_mcp_ctx(app_ctx)
        await edit_task(ctx, id="1", priority="critical")
        mock_av.edit_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_edit_task_forwards_all_14_params(
        self, app_ctx_with_mock_agent_view: tuple[AppContext, MagicMock]
    ) -> None:
        """All 14 AgentView.edit_task params must be forwarded from the adapter (§1.5)."""
        app_ctx, mock_av = app_ctx_with_mock_agent_view
        ctx = _make_mcp_ctx(app_ctx)
        await edit_task(
            ctx,
            id="1",
            title="updated title",
            body="new body",
            append_body="appended",
            timestamp=True,
            priority="critical",
            parent=2,
            add_dep=[3],
            remove_dep=[4],
            add_tag=["scope:mcp"],
            remove_tag=["old-tag"],
            block_reason="waiting on upstream",
            archival_reason="dropped",
            archival_refs=[5],
        )
        mock_av.edit_task.assert_called_once()
        _, kwargs = mock_av.edit_task.call_args
        assert kwargs.get("title") == "updated title"
        assert kwargs.get("body") == "new body"
        assert kwargs.get("append_body") == "appended"
        assert kwargs.get("timestamp") is True
        assert kwargs.get("priority") == "critical"
        assert kwargs.get("parent") == 2
        assert kwargs.get("add_dep") == [3]
        assert kwargs.get("remove_dep") == [4]
        assert kwargs.get("add_tag") == ["scope:mcp"]
        assert kwargs.get("remove_tag") == ["old-tag"]
        assert kwargs.get("block_reason") == "waiting on upstream"
        assert kwargs.get("archival_reason") == "dropped"
        assert kwargs.get("archival_refs") == [5]

    @pytest.mark.asyncio
    async def test_edit_task_forwards_id_as_int(
        self, app_ctx_with_mock_agent_view: tuple[AppContext, MagicMock]
    ) -> None:
        """task_id string is coerced to int before forwarding to AgentView.edit_task (id: int)."""
        app_ctx, mock_av = app_ctx_with_mock_agent_view
        ctx = _make_mcp_ctx(app_ctx)
        await edit_task(ctx, id="1", priority="critical")
        args, kwargs = mock_av.edit_task.call_args
        forwarded_id = args[0] if args else kwargs.get("id")
        assert forwarded_id == 1, (
            f"task_id must be forwarded as int; got {forwarded_id!r}"
        )

    @pytest.mark.asyncio
    async def test_edit_task_returns_single_task_response(
        self, app_ctx_with_mock_agent_view: tuple[AppContext, MagicMock]
    ) -> None:
        """edit_task must return SingleTaskResponse (not KanbanTask or Task)."""
        app_ctx, mock_av = app_ctx_with_mock_agent_view
        expected = _make_single_task_response(id=1, title="Edited Task")
        mock_av.edit_task.return_value = expected
        ctx = _make_mcp_ctx(app_ctx)
        result = await edit_task(ctx, id="1", priority="critical")
        assert result is expected, (
            "edit_task must return the unmodified SingleTaskResponse from AgentView — "
            f"passthrough fidelity required; got {type(result).__name__}"
        )

    @pytest.mark.asyncio
    async def test_edit_task_body_and_append_body_raises_tool_error(
        self, app_ctx_with_mock_agent_view: tuple[AppContext, MagicMock]
    ) -> None:
        """body + append_body → ValidationError(ERR_BODY_EXCLUSIVE) from engine → ToolError (AC14)."""
        app_ctx, mock_av = app_ctx_with_mock_agent_view
        mock_av.edit_task.side_effect = ValidationError(
            code="ERR_BODY_EXCLUSIVE",
            user_message="body and append_body cannot both be set",
        )
        ctx = _make_mcp_ctx(app_ctx)
        with pytest.raises(ToolError) as exc_info:
            await edit_task(ctx, id="1", body="replace", append_body="append")
        mock_av.edit_task.assert_called_once()
        assert "body and append_body cannot both be set" in str(exc_info.value), (
            "ToolError must carry the ERR_BODY_EXCLUSIVE user_message"
        )

    @pytest.mark.asyncio
    async def test_edit_task_archival_reason_on_non_archived_raises_tool_error(
        self, app_ctx_with_mock_agent_view: tuple[AppContext, MagicMock]
    ) -> None:
        """archival_reason on non-archived task → ValidationError → ToolError."""
        app_ctx, mock_av = app_ctx_with_mock_agent_view
        mock_av.edit_task.side_effect = ValidationError(
            code="ERR_ARCHIVAL_FIELDS_FORBIDDEN",
            user_message="archival_reason can only be set on archived tasks",
        )
        ctx = _make_mcp_ctx(app_ctx)
        with pytest.raises(ToolError) as exc_info:
            await edit_task(ctx, id="1", archival_reason="dropped")
        mock_av.edit_task.assert_called_once()
        assert "archival_reason can only be set on archived tasks" in str(
            exc_info.value
        ), "ToolError must carry the ERR_ARCHIVAL_FIELDS_FORBIDDEN user_message"

    @pytest.mark.asyncio
    async def test_edit_task_archival_refs_on_non_archived_raises_tool_error(
        self, app_ctx_with_mock_agent_view: tuple[AppContext, MagicMock]
    ) -> None:
        """archival_refs on non-archived task → ValidationError → ToolError."""
        app_ctx, mock_av = app_ctx_with_mock_agent_view
        mock_av.edit_task.side_effect = ValidationError(
            code="ERR_ARCHIVAL_FIELDS_FORBIDDEN",
            user_message="archival_refs can only be set on archived tasks",
        )
        ctx = _make_mcp_ctx(app_ctx)
        with pytest.raises(ToolError) as exc_info:
            await edit_task(ctx, id="1", archival_refs=[42])
        mock_av.edit_task.assert_called_once()
        assert "archival_refs can only be set on archived tasks" in str(
            exc_info.value
        ), "ToolError must carry the ERR_ARCHIVAL_FIELDS_FORBIDDEN user_message"

    @pytest.mark.asyncio
    async def test_edit_task_no_op_raises_tool_error(
        self, app_ctx_with_mock_agent_view: tuple[AppContext, MagicMock]
    ) -> None:
        """No-op edit (no field change) → ValidationError(ERR_NO_OP) → ToolError."""
        app_ctx, mock_av = app_ctx_with_mock_agent_view
        mock_av.edit_task.side_effect = ValidationError(
            code="ERR_NO_OP",
            user_message="no fields would change",
        )
        ctx = _make_mcp_ctx(app_ctx)
        with pytest.raises(ToolError) as exc_info:
            await edit_task(ctx, id="1")
        mock_av.edit_task.assert_called_once()
        assert "no fields would change" in str(exc_info.value), (
            "ToolError must carry the ERR_NO_OP user_message"
        )

    def test_edit_task_block_reason_default_is_none(self) -> None:
        """block_reason param must default to None (not '') to distinguish omission from explicit unblock (D53).

        AgentView.edit_task uses _BLOCK_REASON_UNSET sentinel to tell 'not supplied' from
        'explicitly empty'.  The MCP adapter must mirror that by defaulting block_reason to
        None and forwarding it only when it is not None — so block_reason='' signals unblock
        while a missing block_reason leaves the block state untouched.
        """
        params = inspect.signature(edit_task).parameters
        assert params["block_reason"].default is None, (
            "edit_task block_reason must default to None (not ''); "
            "current default allows no distinction between omission and explicit unblock. "
            f"Got: {params['block_reason'].default!r}"
        )

    @pytest.mark.asyncio
    async def test_edit_task_empty_block_reason_forwarded_to_unblock(
        self, app_ctx_with_mock_agent_view: tuple[AppContext, MagicMock]
    ) -> None:
        """Explicit block_reason='' must be forwarded to AgentView to clear the block (D53).

        AgentView.edit_task interprets an explicit empty string as 'clear block flag'.
        The adapter must not drop the value with a truthy check; it must forward it so the
        engine can apply the unblock mutation.
        """
        app_ctx, mock_av = app_ctx_with_mock_agent_view
        ctx = _make_mcp_ctx(app_ctx)
        await edit_task(ctx, id="1", block_reason="")
        _, kwargs = mock_av.edit_task.call_args
        assert "block_reason" in kwargs, (
            "block_reason='' must be forwarded to AgentView (signals unblock via D53); "
            "adapter must not silently drop it with `if block_reason:`"
        )
        assert kwargs["block_reason"] == "", (
            f"Forwarded block_reason must be '' (the unblock sentinel); got {kwargs['block_reason']!r}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_KanbanErrorMapping
# AC: all KanbanError subclasses mapped to MCP ToolError with user_message
# ---------------------------------------------------------------------------


class TestFromAC_KanbanErrorMapping:
    """All KanbanError subclasses raised by AgentView map to ToolError with user_message."""

    @pytest.mark.asyncio
    async def test_validation_error_user_message_in_tool_error(
        self, app_ctx_with_mock_agent_view: tuple[AppContext, MagicMock]
    ) -> None:
        """ValidationError maps to ToolError with JSON payload carrying code + message."""
        app_ctx, mock_av = app_ctx_with_mock_agent_view
        user_msg = "priority 'invalid' is not a valid priority"
        mock_av.create_task.side_effect = ValidationError(
            code="ERR_INVALID_PRIORITY",
            user_message=user_msg,
        )
        ctx = _make_mcp_ctx(app_ctx)
        with pytest.raises(ToolError) as exc_info:
            await create_task(ctx, title="T", priority="invalid")
        payload = json.loads(str(exc_info.value))
        assert payload["code"] == "ERR_INVALID_PRIORITY", (
            f"ToolError JSON must carry parseable error code; got {payload!r}"
        )
        assert payload["message"] == user_msg, (
            f"ToolError JSON must carry human-readable user_message; got {payload!r}"
        )

    @pytest.mark.asyncio
    async def test_not_found_error_maps_to_tool_error(
        self, app_ctx_with_mock_agent_view: tuple[AppContext, MagicMock]
    ) -> None:
        """NotFoundError from AgentView.edit_task maps to ToolError with JSON payload."""
        app_ctx, mock_av = app_ctx_with_mock_agent_view
        user_msg = "task 9999 not found"
        mock_av.edit_task.side_effect = NotFoundError(
            code="ERR_NOT_FOUND",
            user_message=user_msg,
        )
        ctx = _make_mcp_ctx(app_ctx)
        with pytest.raises(ToolError) as exc_info:
            await edit_task(ctx, id="9999", priority="critical")
        payload = json.loads(str(exc_info.value))
        assert payload["code"] == "ERR_NOT_FOUND", (
            f"ToolError JSON must carry parseable error code; got {payload!r}"
        )
        assert payload["message"] == user_msg, (
            f"ToolError JSON must carry human-readable user_message; got {payload!r}"
        )

    @pytest.mark.asyncio
    async def test_concurrency_error_maps_to_tool_error(
        self, app_ctx_with_mock_agent_view: tuple[AppContext, MagicMock]
    ) -> None:
        """ConcurrencyError from AgentView.edit_task maps to ToolError."""
        app_ctx, mock_av = app_ctx_with_mock_agent_view
        user_msg = "task was modified concurrently; please retry"
        mock_av.edit_task.side_effect = ConcurrencyError(
            code="ERR_STALE",
            user_message=user_msg,
        )
        ctx = _make_mcp_ctx(app_ctx)
        with pytest.raises(ToolError) as exc_info:
            await edit_task(ctx, id="1", priority="critical")
        assert user_msg in str(exc_info.value), (
            "ToolError must embed the ConcurrencyError.user_message verbatim"
        )

    @pytest.mark.asyncio
    async def test_all_kanban_error_subclasses_map_to_tool_error_not_raw_exception(
        self, app_ctx_with_mock_agent_view: tuple[AppContext, MagicMock]
    ) -> None:
        """Any KanbanError subclass must become ToolError; raw KanbanError must not propagate."""
        from owlbear_kanban.errors import KanbanError

        app_ctx, mock_av = app_ctx_with_mock_agent_view
        mock_av.create_task.side_effect = KanbanError(
            code="ERR_DEP_NOT_FOUND",
            user_message="base kanban error",
        )
        ctx = _make_mcp_ctx(app_ctx)
        # Must raise ToolError, not raw KanbanError
        with pytest.raises(ToolError):
            await create_task(ctx, title="T")
