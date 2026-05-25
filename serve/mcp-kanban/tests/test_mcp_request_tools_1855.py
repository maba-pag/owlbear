"""RED phase tests — MCP request tools: create_request, list_requests, show_request + pick_tasks annotation fix (#1855)."""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest
from mcp.server.fastmcp.exceptions import ToolError
from owlbear_kanban import KanbanEngine
from owlbear_kanban.errors import NotFoundError, ValidationError
from owlbear_kanban.request_models import RequestRecord
from owlbear_mcp_kanban.server import AppContext, mcp

# ---------------------------------------------------------------------------
# Shared helpers / fixtures
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

# Stable UUID4 used as a known valid request_id in tests.
_VALID_REQUEST_UUID = str(uuid4())


def _make_board(base_dir: Path) -> Path:
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    (kanban_dir / "decisions" / "pending").mkdir(parents=True, exist_ok=True)
    (kanban_dir / "decisions" / "resolved").mkdir(parents=True, exist_ok=True)
    return kanban_dir


def _make_mcp_ctx(app_ctx: object) -> MagicMock:
    ctx = MagicMock()
    ctx.request_context.lifespan_context = app_ctx
    return ctx


def _make_request_record(
    *,
    task_id: int = 1,
    request_id: str | None = None,
    kind: str = "action",
    body: str = "## Summary\nDetails here.",
) -> RequestRecord:
    """Create a minimal valid RequestRecord for mock return values."""
    rid = request_id or _VALID_REQUEST_UUID
    return RequestRecord.model_validate(
        {
            "task_id": task_id,
            "request_id": rid,
            "kind": kind,
            "title": "Test Request",
            "summary": "A test request summary.",
            "agent": "builder",
            "created_at": "2026-01-01T00:00:00+00:00",
            "options": [],
            "resolution": {"selected_option_id": None, "free_text": None, "resolved_at": None},
            "body": body,
        }
    )


def _get_tool_annotations(tool_name: str) -> object | None:
    """Return ToolAnnotations object for a named tool, or None if not found."""
    if hasattr(mcp, "_tool_manager"):
        for t in mcp._tool_manager.list_tools():  # noqa: SLF001
            if getattr(t, "name", None) == tool_name:
                return getattr(t, "annotations", None)
    return None


@pytest.fixture
def app_ctx(tmp_path: Path) -> AppContext:
    kanban_dir = _make_board(tmp_path)
    engine = KanbanEngine(kanban_dir)
    engine.create_task("Task 1", status="todo", priority="needed")
    return AppContext(engine=engine, kanban_dir=kanban_dir)


# ---------------------------------------------------------------------------
# AC1 — create_request tool
# ---------------------------------------------------------------------------


class TestFromAC_CreateRequestTool:
    """Contract tests for create_request MCP tool (AC1)."""

    # -- Registration --------------------------------------------------------

    def test_create_request_tool_is_registered(self) -> None:
        """create_request must be registered via @mcp.tool()."""
        tool = next(
            (t for t in mcp._tool_manager._tools.values() if t.name == "create_request"),  # noqa: SLF001
            None,
        )
        assert tool is not None, (
            "create_request must be registered via @mcp.tool(); "
            f"registered tools: {[t.name for t in mcp._tool_manager._tools.values()]}"  # noqa: SLF001
        )

    def test_create_request_tool_annotation_destructive_hint_false(self) -> None:
        """create_request must have ToolAnnotations(destructiveHint=False)."""
        annotations = _get_tool_annotations("create_request")
        assert annotations is not None, "create_request must have ToolAnnotations"
        assert getattr(annotations, "destructiveHint", None) is False, (
            f"create_request destructiveHint must be False, got {getattr(annotations, 'destructiveHint', 'MISSING')}"
        )

    # -- Signature -----------------------------------------------------------

    def test_create_request_required_params_present(self) -> None:
        """create_request must have required params: task_id, kind, title, summary, agent."""
        import owlbear_mcp_kanban.server as server_mod  # noqa: PLC0415

        fn = getattr(server_mod, "create_request", None)
        assert callable(fn), "owlbear_mcp_kanban.server.create_request must exist"

        params = inspect.signature(fn).parameters
        for required in ("task_id", "kind", "title", "summary", "agent"):
            assert required in params, f"create_request missing required param: {required}"
            assert params[required].default is inspect.Parameter.empty, (
                f"create_request param '{required}' must be required (no default)"
            )

    def test_create_request_optional_params_present(self) -> None:
        """create_request must have optional params: options (None default), body (str default)."""
        import owlbear_mcp_kanban.server as server_mod  # noqa: PLC0415

        fn = getattr(server_mod, "create_request", None)
        assert callable(fn), "owlbear_mcp_kanban.server.create_request must exist"

        params = inspect.signature(fn).parameters
        assert "options" in params, "create_request must have 'options' optional param"
        assert "body" in params, "create_request must have 'body' optional param"
        # options should default to None
        assert params["options"].default is None or params["options"].default == inspect.Parameter.empty or params["options"].default is None, (
            "create_request 'options' must default to None"
        )

    # -- Happy paths ---------------------------------------------------------

    @pytest.mark.asyncio
    async def test_create_request_action_success_returns_model_dump(self, app_ctx: AppContext) -> None:
        """AC1 happy: create_request returns RequestRecord.model_dump() + guidance=[] when no normalization."""
        import owlbear_mcp_kanban.server as server_mod  # noqa: PLC0415

        fn = getattr(server_mod, "create_request", None)
        assert callable(fn), "owlbear_mcp_kanban.server.create_request must exist"

        ctx = _make_mcp_ctx(app_ctx)
        fake_record = _make_request_record(task_id=1, kind="action")
        app_ctx.engine.create_request = MagicMock(return_value=fake_record)

        result = await fn(
            ctx,
            task_id="1",
            kind="action",
            title="Test Request",
            summary="Please act.",
            agent="builder",
            body="## Body\nNo escaped newlines.",
        )

        assert isinstance(result, dict), "create_request must return a dict"
        assert result["task_id"] == fake_record.task_id
        assert result["kind"] == "action"
        assert "guidance" in result, "create_request result must include 'guidance' key"
        assert result["guidance"] == [], "guidance must be [] when no normalization occurred"

    @pytest.mark.asyncio
    async def test_create_request_forwards_params_to_engine(self, app_ctx: AppContext) -> None:
        """AC1: create_request delegates to engine.create_request with correct args."""
        import owlbear_mcp_kanban.server as server_mod  # noqa: PLC0415

        fn = getattr(server_mod, "create_request", None)
        assert callable(fn), "owlbear_mcp_kanban.server.create_request must exist"

        ctx = _make_mcp_ctx(app_ctx)
        fake_record = _make_request_record(task_id=1, kind="action")
        mock_create = MagicMock(return_value=fake_record)
        app_ctx.engine.create_request = mock_create

        await fn(
            ctx,
            task_id="1",
            kind="action",
            title="My Request",
            summary="Summary text",
            agent="builder",
            body="No escapes.",
        )

        mock_create.assert_called_once()
        call_args = mock_create.call_args
        # task_id must be forwarded as integer
        assert call_args.args[0] == 1 or call_args.kwargs.get("task_id") == 1, (
            f"engine.create_request must receive task_id=1, got {call_args}"
        )

    # -- Newline normalization ------------------------------------------------

    @pytest.mark.asyncio
    async def test_create_request_body_normalization_adds_guidance(self, app_ctx: AppContext) -> None:
        r"""AC1: when body contains literal \n sequences, normalization adds guidance entry."""
        import owlbear_mcp_kanban.server as server_mod  # noqa: PLC0415

        fn = getattr(server_mod, "create_request", None)
        assert callable(fn), "owlbear_mcp_kanban.server.create_request must exist"

        ctx = _make_mcp_ctx(app_ctx)
        fake_record = _make_request_record(task_id=1, kind="action")
        app_ctx.engine.create_request = MagicMock(return_value=fake_record)

        result = await fn(
            ctx,
            task_id="1",
            kind="action",
            title="Test",
            summary="Summary",
            agent="builder",
            body=r"Line one\nLine two",  # literal \n — should trigger normalization
        )

        assert isinstance(result.get("guidance"), list), "guidance must be a list"
        assert len(result["guidance"]) > 0, (
            r"guidance must be non-empty when body contains literal \n sequences"
        )

    @pytest.mark.asyncio
    async def test_create_request_no_body_normalization_guidance_empty(self, app_ctx: AppContext) -> None:
        """AC1: when body has no literal escape sequences, guidance is empty."""
        import owlbear_mcp_kanban.server as server_mod  # noqa: PLC0415

        fn = getattr(server_mod, "create_request", None)
        assert callable(fn), "owlbear_mcp_kanban.server.create_request must exist"

        ctx = _make_mcp_ctx(app_ctx)
        fake_record = _make_request_record(task_id=1, kind="action")
        app_ctx.engine.create_request = MagicMock(return_value=fake_record)

        result = await fn(
            ctx,
            task_id="1",
            kind="action",
            title="Test",
            summary="Summary",
            agent="builder",
            body="Normal body with actual\nnewlines.",  # real newlines, not escaped
        )

        assert result.get("guidance") == [], (
            "guidance must be [] when no literal \\n sequences are in body"
        )

    # -- Error paths ---------------------------------------------------------

    @pytest.mark.asyncio
    async def test_create_request_invalid_task_id_raises_tool_error(self, app_ctx: AppContext) -> None:
        """AC1: invalid task_id format → ToolError with ERR_INVALID_ID."""
        import owlbear_mcp_kanban.server as server_mod  # noqa: PLC0415

        fn = getattr(server_mod, "create_request", None)
        assert callable(fn), "owlbear_mcp_kanban.server.create_request must exist"

        ctx = _make_mcp_ctx(app_ctx)

        with pytest.raises(ToolError) as exc_info:
            await fn(
                ctx,
                task_id="not-an-id",
                kind="action",
                title="Test",
                summary="Summary",
                agent="builder",
            )

        payload = json.loads(str(exc_info.value))
        assert payload.get("code") == "ERR_INVALID_ID", (
            f"Expected ERR_INVALID_ID, got {payload.get('code')}"
        )

    @pytest.mark.asyncio
    async def test_create_request_task_not_found_maps_to_tool_error(self, app_ctx: AppContext) -> None:
        """AC1: NotFoundError from engine → ToolError with ERR_NOT_FOUND."""
        import owlbear_mcp_kanban.server as server_mod  # noqa: PLC0415

        fn = getattr(server_mod, "create_request", None)
        assert callable(fn), "owlbear_mcp_kanban.server.create_request must exist"

        ctx = _make_mcp_ctx(app_ctx)
        app_ctx.engine.create_request = MagicMock(
            side_effect=NotFoundError(code="ERR_NOT_FOUND", user_message="task 999 not found")
        )

        with pytest.raises(ToolError, match="task 999 not found"):
            await fn(
                ctx,
                task_id="999",
                kind="action",
                title="Test",
                summary="Summary",
                agent="builder",
            )

    @pytest.mark.asyncio
    async def test_create_request_pydantic_validation_error_maps_to_tool_error(
        self, app_ctx: AppContext
    ) -> None:
        """AC1: PydanticValidationError (invalid kind/options) → ToolError with ERR_PARAM_VALIDATION."""
        import owlbear_mcp_kanban.server as server_mod  # noqa: PLC0415

        fn = getattr(server_mod, "create_request", None)
        assert callable(fn), "owlbear_mcp_kanban.server.create_request must exist"

        ctx = _make_mcp_ctx(app_ctx)

        # 'kind' must be 'decision' or 'action' — any other value should trigger validation error
        with pytest.raises(ToolError) as exc_info:
            await fn(
                ctx,
                task_id="1",
                kind="invalid-kind",
                title="Test",
                summary="Summary",
                agent="builder",
            )

        payload = json.loads(str(exc_info.value))
        assert payload.get("code") == "ERR_PARAM_VALIDATION", (
            f"PydanticValidationError must map to ERR_PARAM_VALIDATION, got {payload.get('code')}"
        )

    # -- Boundary ------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_create_request_task_id_as_integer_accepted(self, app_ctx: AppContext) -> None:
        """AC1: task_id as int (not str) must be accepted via parse_task_id."""
        import owlbear_mcp_kanban.server as server_mod  # noqa: PLC0415

        fn = getattr(server_mod, "create_request", None)
        assert callable(fn), "owlbear_mcp_kanban.server.create_request must exist"

        ctx = _make_mcp_ctx(app_ctx)
        fake_record = _make_request_record(task_id=1, kind="action")
        app_ctx.engine.create_request = MagicMock(return_value=fake_record)

        # Integer task_id must be accepted and forwarded as int to engine
        result = await fn(
            ctx,
            task_id=1,  # integer, not string
            kind="action",
            title="Test",
            summary="Summary",
            agent="builder",
        )

        assert isinstance(result, dict), "create_request must return dict even with int task_id"
        app_ctx.engine.create_request.assert_called_once()


# ---------------------------------------------------------------------------
# AC2 — list_requests tool
# ---------------------------------------------------------------------------


class TestFromAC_ListRequestsTool:
    """Contract tests for list_requests MCP tool (AC2)."""

    # -- Registration --------------------------------------------------------

    def test_list_requests_tool_is_registered(self) -> None:
        """list_requests must be registered via @mcp.tool()."""
        tool = next(
            (t for t in mcp._tool_manager._tools.values() if t.name == "list_requests"),  # noqa: SLF001
            None,
        )
        assert tool is not None, (
            "list_requests must be registered via @mcp.tool(); "
            f"registered tools: {[t.name for t in mcp._tool_manager._tools.values()]}"  # noqa: SLF001
        )

    def test_list_requests_tool_annotations_read_only(self) -> None:
        """list_requests must have ToolAnnotations(readOnlyHint=True, idempotentHint=True)."""
        annotations = _get_tool_annotations("list_requests")
        assert annotations is not None, "list_requests must have ToolAnnotations"
        assert getattr(annotations, "readOnlyHint", None) is True, (
            f"list_requests readOnlyHint must be True, got {getattr(annotations, 'readOnlyHint', 'MISSING')}"
        )
        assert getattr(annotations, "idempotentHint", None) is True, (
            f"list_requests idempotentHint must be True, got {getattr(annotations, 'idempotentHint', 'MISSING')}"
        )

    # -- Happy paths ---------------------------------------------------------

    @pytest.mark.asyncio
    async def test_list_requests_returns_list_excluding_body(self, app_ctx: AppContext) -> None:
        """AC2: list_requests returns [r.model_dump(exclude={'body'}) for r in records] — body excluded."""
        import owlbear_mcp_kanban.server as server_mod  # noqa: PLC0415

        fn = getattr(server_mod, "list_requests", None)
        assert callable(fn), "owlbear_mcp_kanban.server.list_requests must exist"

        ctx = _make_mcp_ctx(app_ctx)
        fake_record = _make_request_record(task_id=1, kind="action", body="## Secret body content")
        app_ctx.engine.list_requests = MagicMock(return_value=[fake_record])

        result = await fn(ctx, status="pending")

        assert isinstance(result, list), "list_requests must return a list"
        assert len(result) == 1
        item = result[0]
        assert isinstance(item, dict), "each item must be a dict"
        assert "body" not in item, "body must be excluded from list_requests results"
        assert "task_id" in item, "task_id must be included in list_requests results"
        assert "request_id" in item, "request_id must be included in list_requests results"
        assert "kind" in item, "kind must be included in list_requests results"
        assert "title" in item, "title must be included in list_requests results"
        assert "summary" in item, "summary must be included in list_requests results"
        assert "agent" in item, "agent must be included in list_requests results"
        assert "created_at" in item, "created_at must be included in list_requests results"

    @pytest.mark.asyncio
    async def test_list_requests_default_status_is_pending(self, app_ctx: AppContext) -> None:
        """AC2: status defaults to 'pending' when not supplied."""
        import owlbear_mcp_kanban.server as server_mod  # noqa: PLC0415

        fn = getattr(server_mod, "list_requests", None)
        assert callable(fn), "owlbear_mcp_kanban.server.list_requests must exist"

        ctx = _make_mcp_ctx(app_ctx)
        app_ctx.engine.list_requests = MagicMock(return_value=[])

        # Call without status argument — default must be 'pending'
        await fn(ctx)

        app_ctx.engine.list_requests.assert_called_once()
        call_args = app_ctx.engine.list_requests.call_args
        forwarded_status = call_args.args[0] if call_args.args else call_args.kwargs.get("status")
        assert forwarded_status == "pending", (
            f"list_requests must default status to 'pending', forwarded {forwarded_status!r}"
        )

    @pytest.mark.asyncio
    async def test_list_requests_forwards_status_and_task_id_to_engine(self, app_ctx: AppContext) -> None:
        """AC2: list_requests forwards status and parsed task_id to engine.list_requests."""
        import owlbear_mcp_kanban.server as server_mod  # noqa: PLC0415

        fn = getattr(server_mod, "list_requests", None)
        assert callable(fn), "owlbear_mcp_kanban.server.list_requests must exist"

        ctx = _make_mcp_ctx(app_ctx)
        app_ctx.engine.list_requests = MagicMock(return_value=[])

        await fn(ctx, status="resolved", task_id="1")

        app_ctx.engine.list_requests.assert_called_once()
        call_args = app_ctx.engine.list_requests.call_args
        # task_id must be forwarded as integer (parse_task_id converts it)
        all_args = list(call_args.args) + list(call_args.kwargs.values())
        assert 1 in all_args or call_args.kwargs.get("task_id") == 1, (
            f"engine.list_requests must receive task_id=1 (int), got {call_args}"
        )

    @pytest.mark.asyncio
    async def test_list_requests_empty_result_when_no_records(self, app_ctx: AppContext) -> None:
        """AC2 edge: list_requests returns [] when engine returns empty list."""
        import owlbear_mcp_kanban.server as server_mod  # noqa: PLC0415

        fn = getattr(server_mod, "list_requests", None)
        assert callable(fn), "owlbear_mcp_kanban.server.list_requests must exist"

        ctx = _make_mcp_ctx(app_ctx)
        app_ctx.engine.list_requests = MagicMock(return_value=[])

        result = await fn(ctx, status="pending")

        assert result == [], f"list_requests must return [] when engine returns empty list, got {result!r}"

    # -- Error paths ---------------------------------------------------------

    @pytest.mark.asyncio
    async def test_list_requests_invalid_task_id_raises_tool_error(self, app_ctx: AppContext) -> None:
        """AC2: invalid task_id format → ToolError with ERR_INVALID_ID."""
        import owlbear_mcp_kanban.server as server_mod  # noqa: PLC0415

        fn = getattr(server_mod, "list_requests", None)
        assert callable(fn), "owlbear_mcp_kanban.server.list_requests must exist"

        ctx = _make_mcp_ctx(app_ctx)

        with pytest.raises(ToolError) as exc_info:
            await fn(ctx, task_id="abc")

        payload = json.loads(str(exc_info.value))
        assert payload.get("code") == "ERR_INVALID_ID", (
            f"Invalid task_id must raise ERR_INVALID_ID, got {payload.get('code')}"
        )

    @pytest.mark.asyncio
    async def test_list_requests_kanban_error_maps_to_tool_error(self, app_ctx: AppContext) -> None:
        """AC2: KanbanError from engine → ToolError with engine's error code."""
        import owlbear_mcp_kanban.server as server_mod  # noqa: PLC0415

        fn = getattr(server_mod, "list_requests", None)
        assert callable(fn), "owlbear_mcp_kanban.server.list_requests must exist"

        ctx = _make_mcp_ctx(app_ctx)
        app_ctx.engine.list_requests = MagicMock(
            side_effect=ValidationError(code="ERR_INVALID_STATUS", user_message="invalid status value")
        )

        with pytest.raises(ToolError, match="invalid status value"):
            await fn(ctx, status="bogus")

    # -- Boundary ------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_list_requests_null_task_id_not_parsed(self, app_ctx: AppContext) -> None:
        """AC2 edge: task_id=None must not invoke parse_task_id; engine receives None."""
        import owlbear_mcp_kanban.server as server_mod  # noqa: PLC0415

        fn = getattr(server_mod, "list_requests", None)
        assert callable(fn), "owlbear_mcp_kanban.server.list_requests must exist"

        ctx = _make_mcp_ctx(app_ctx)
        app_ctx.engine.list_requests = MagicMock(return_value=[])

        # task_id=None must not crash (parse_task_id should only run when non-None)
        result = await fn(ctx, status="pending", task_id=None)

        assert isinstance(result, list), "list_requests with task_id=None must return a list"
        call_kwargs = app_ctx.engine.list_requests.call_args.kwargs
        forwarded_task_id = call_kwargs.get("task_id", "NOT_IN_KWARGS")
        # None should be forwarded, not converted
        assert forwarded_task_id is None or forwarded_task_id == "NOT_IN_KWARGS" or (
            app_ctx.engine.list_requests.call_args.args and None in app_ctx.engine.list_requests.call_args.args
        ), f"task_id=None must be forwarded to engine as None, got {forwarded_task_id!r}"


# ---------------------------------------------------------------------------
# AC3 — show_request tool
# ---------------------------------------------------------------------------


class TestFromAC_ShowRequestTool:
    """Contract tests for show_request MCP tool (AC3)."""

    # -- Registration --------------------------------------------------------

    def test_show_request_tool_is_registered(self) -> None:
        """show_request must be registered via @mcp.tool()."""
        tool = next(
            (t for t in mcp._tool_manager._tools.values() if t.name == "show_request"),  # noqa: SLF001
            None,
        )
        assert tool is not None, (
            "show_request must be registered via @mcp.tool(); "
            f"registered tools: {[t.name for t in mcp._tool_manager._tools.values()]}"  # noqa: SLF001
        )

    def test_show_request_tool_annotations_read_only(self) -> None:
        """show_request must have ToolAnnotations(readOnlyHint=True, idempotentHint=True)."""
        annotations = _get_tool_annotations("show_request")
        assert annotations is not None, "show_request must have ToolAnnotations"
        assert getattr(annotations, "readOnlyHint", None) is True, (
            f"show_request readOnlyHint must be True, got {getattr(annotations, 'readOnlyHint', 'MISSING')}"
        )
        assert getattr(annotations, "idempotentHint", None) is True, (
            f"show_request idempotentHint must be True, got {getattr(annotations, 'idempotentHint', 'MISSING')}"
        )

    # -- Happy paths ---------------------------------------------------------

    @pytest.mark.asyncio
    async def test_show_request_success_returns_full_model_dump(self, app_ctx: AppContext) -> None:
        """AC3: show_request returns RequestRecord.model_dump() including body and resolution."""
        import owlbear_mcp_kanban.server as server_mod  # noqa: PLC0415

        fn = getattr(server_mod, "show_request", None)
        assert callable(fn), "owlbear_mcp_kanban.server.show_request must exist"

        ctx = _make_mcp_ctx(app_ctx)
        fake_record = _make_request_record(
            task_id=1, kind="action", body="## Full details\nVisible body."
        )
        app_ctx.engine.get_request = MagicMock(return_value=fake_record)

        result = await fn(ctx, request_id=_VALID_REQUEST_UUID)

        assert isinstance(result, dict), "show_request must return a dict"
        assert "body" in result, "body must be included in show_request result (full detail)"
        assert result["body"] == "## Full details\nVisible body."
        assert "resolution" in result, "resolution must be included in show_request result"
        assert "task_id" in result
        assert "request_id" in result
        assert "kind" in result

    @pytest.mark.asyncio
    async def test_show_request_delegates_request_id_to_engine(self, app_ctx: AppContext) -> None:
        """AC3: show_request passes request_id to engine.get_request."""
        import owlbear_mcp_kanban.server as server_mod  # noqa: PLC0415

        fn = getattr(server_mod, "show_request", None)
        assert callable(fn), "owlbear_mcp_kanban.server.show_request must exist"

        ctx = _make_mcp_ctx(app_ctx)
        fake_record = _make_request_record(task_id=1)
        mock_get = MagicMock(return_value=fake_record)
        app_ctx.engine.get_request = mock_get

        await fn(ctx, request_id=_VALID_REQUEST_UUID)

        mock_get.assert_called_once()
        call_args = mock_get.call_args
        forwarded_id = call_args.args[0] if call_args.args else call_args.kwargs.get("request_id")
        assert forwarded_id == _VALID_REQUEST_UUID, (
            f"engine.get_request must receive the UUID string, got {forwarded_id!r}"
        )

    # -- Error paths ---------------------------------------------------------

    @pytest.mark.asyncio
    async def test_show_request_non_uuid_raises_tool_error(self, app_ctx: AppContext) -> None:
        """AC3: non-UUID request_id → ToolError with ERR_PARAM_VALIDATION (before engine call)."""
        import owlbear_mcp_kanban.server as server_mod  # noqa: PLC0415

        fn = getattr(server_mod, "show_request", None)
        assert callable(fn), "owlbear_mcp_kanban.server.show_request must exist"

        ctx = _make_mcp_ctx(app_ctx)
        app_ctx.engine.get_request = MagicMock()

        with pytest.raises(ToolError) as exc_info:
            await fn(ctx, request_id="not-a-uuid-at-all")

        payload = json.loads(str(exc_info.value))
        assert payload.get("code") == "ERR_PARAM_VALIDATION", (
            f"Non-UUID request_id must raise ERR_PARAM_VALIDATION, got {payload.get('code')}"
        )
        app_ctx.engine.get_request.assert_not_called()  # must fail before engine call

    @pytest.mark.asyncio
    async def test_show_request_uuid_v1_raises_tool_error(self, app_ctx: AppContext) -> None:
        """AC3: UUID that is not version 4 → ToolError with ERR_PARAM_VALIDATION."""
        import owlbear_mcp_kanban.server as server_mod  # noqa: PLC0415

        fn = getattr(server_mod, "show_request", None)
        assert callable(fn), "owlbear_mcp_kanban.server.show_request must exist"

        ctx = _make_mcp_ctx(app_ctx)
        app_ctx.engine.get_request = MagicMock()

        # UUID v1 (not v4) — valid UUID format but wrong version
        uuid_v1 = "550e8400-e29b-11d4-a716-446655440000"
        assert UUID(uuid_v1).version == 1, "precondition: ensure this is UUID v1"

        with pytest.raises(ToolError) as exc_info:
            await fn(ctx, request_id=uuid_v1)

        payload = json.loads(str(exc_info.value))
        assert payload.get("code") == "ERR_PARAM_VALIDATION", (
            f"UUID v1 must raise ERR_PARAM_VALIDATION (only UUID4 accepted), got {payload.get('code')}"
        )
        app_ctx.engine.get_request.assert_not_called()

    @pytest.mark.asyncio
    async def test_show_request_not_found_maps_to_tool_error(self, app_ctx: AppContext) -> None:
        """AC3: NotFoundError from engine → ToolError with ERR_NOT_FOUND."""
        import owlbear_mcp_kanban.server as server_mod  # noqa: PLC0415

        fn = getattr(server_mod, "show_request", None)
        assert callable(fn), "owlbear_mcp_kanban.server.show_request must exist"

        ctx = _make_mcp_ctx(app_ctx)
        app_ctx.engine.get_request = MagicMock(
            side_effect=NotFoundError(
                code="ERR_NOT_FOUND",
                user_message=f"request '{_VALID_REQUEST_UUID}' not found",
            )
        )

        with pytest.raises(ToolError) as exc_info:
            await fn(ctx, request_id=_VALID_REQUEST_UUID)

        payload = json.loads(str(exc_info.value))
        assert payload.get("code") == "ERR_NOT_FOUND", (
            f"NotFoundError must map to ERR_NOT_FOUND, got {payload.get('code')}"
        )

    # -- Boundary ------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_show_request_path_traversal_rejected(self, app_ctx: AppContext) -> None:
        """AC3 security: path-traversal strings (../../) rejected as non-UUID → ERR_PARAM_VALIDATION."""
        import owlbear_mcp_kanban.server as server_mod  # noqa: PLC0415

        fn = getattr(server_mod, "show_request", None)
        assert callable(fn), "owlbear_mcp_kanban.server.show_request must exist"

        ctx = _make_mcp_ctx(app_ctx)
        app_ctx.engine.get_request = MagicMock()

        traversal_attempts = [
            "../../etc/passwd",
            "../secrets/key",
            "/etc/passwd",
            "../../../../config.yml",
        ]
        for malicious_id in traversal_attempts:
            with pytest.raises(ToolError) as exc_info:
                await fn(ctx, request_id=malicious_id)

            payload = json.loads(str(exc_info.value))
            assert payload.get("code") == "ERR_PARAM_VALIDATION", (
                f"Path traversal attempt {malicious_id!r} must raise ERR_PARAM_VALIDATION"
            )

        app_ctx.engine.get_request.assert_not_called()


# ---------------------------------------------------------------------------
# AC4 — pick_tasks annotation fix
# ---------------------------------------------------------------------------


class TestFromAC_PickTasksAnnotationFix:
    """Contract tests for pick_tasks annotation fix (AC4 — readOnlyHint=False)."""

    def test_pick_tasks_read_only_hint_is_false(self) -> None:
        """AC4: pick_tasks readOnlyHint must be False (sweep_requests writes to filesystem)."""
        annotations = _get_tool_annotations("pick_tasks")
        assert annotations is not None, "pick_tasks must have ToolAnnotations"
        assert getattr(annotations, "readOnlyHint", None) is False, (
            f"pick_tasks readOnlyHint must be False (sweep_requests writes), "
            f"got {getattr(annotations, 'readOnlyHint', 'MISSING')}"
        )

    def test_pick_tasks_docstring_does_not_claim_read_only(self) -> None:
        """AC4: pick_tasks docstring must not contain 'Read-only' claim."""
        import owlbear_mcp_kanban.server as server_mod  # noqa: PLC0415

        fn = getattr(server_mod, "pick_tasks", None)
        assert callable(fn), "owlbear_mcp_kanban.server.pick_tasks must exist"

        doc = (fn.__doc__ or "").strip()
        assert "Read-only" not in doc, (
            f"pick_tasks docstring must not contain 'Read-only' (tool writes via sweep_requests); "
            f"current docstring: {doc!r}"
        )


# ---------------------------------------------------------------------------
# AC5 — Delegation proof contracts
# ---------------------------------------------------------------------------


class TestFromAC_DelegationContracts:
    """AC5 delegation proof contracts — full parameter forwarding verification."""

    # -- AC5(a): create_request full parameter forwarding --------------------

    @pytest.mark.asyncio
    async def test_create_request_engine_receives_all_positional_params(self, app_ctx: AppContext) -> None:
        """AC5(a): create_request forwards task_id, kind, title, summary, agent all to engine."""
        import owlbear_mcp_kanban.server as server_mod  # noqa: PLC0415

        fn = getattr(server_mod, "create_request", None)
        assert callable(fn), "owlbear_mcp_kanban.server.create_request must exist"

        ctx = _make_mcp_ctx(app_ctx)
        fake_record = _make_request_record(task_id=1, kind="decision")
        mock_create = MagicMock(return_value=fake_record)
        app_ctx.engine.create_request = mock_create

        await fn(
            ctx,
            task_id="1",
            kind="decision",
            title="Unique Title Value",
            summary="Unique Summary Value",
            agent="reviewer",
            body="Plain body.",
        )

        mock_create.assert_called_once()
        pos = list(mock_create.call_args.args)
        kw = mock_create.call_args.kwargs
        # task_id as int at position 0, or keyword
        assert pos[0] == 1 or kw.get("task_id") == 1, (
            f"task_id=1 (int) must be forwarded; call was {mock_create.call_args}"
        )
        assert pos[1] == "decision" or kw.get("kind") == "decision", (
            f"kind='decision' must be forwarded; call was {mock_create.call_args}"
        )
        assert pos[2] == "Unique Title Value" or kw.get("title") == "Unique Title Value", (
            f"title='Unique Title Value' must be forwarded; call was {mock_create.call_args}"
        )
        assert pos[3] == "Unique Summary Value" or kw.get("summary") == "Unique Summary Value", (
            f"summary='Unique Summary Value' must be forwarded; call was {mock_create.call_args}"
        )
        assert pos[4] == "reviewer" or kw.get("agent") == "reviewer", (
            f"agent='reviewer' must be forwarded; call was {mock_create.call_args}"
        )

    @pytest.mark.asyncio
    async def test_create_request_engine_receives_options_kwarg(self, app_ctx: AppContext) -> None:
        """AC5(a): options is forwarded as-is when provided."""
        import owlbear_mcp_kanban.server as server_mod  # noqa: PLC0415

        fn = getattr(server_mod, "create_request", None)
        assert callable(fn), "owlbear_mcp_kanban.server.create_request must exist"

        ctx = _make_mcp_ctx(app_ctx)
        fake_record = _make_request_record(task_id=1, kind="decision")
        mock_create = MagicMock(return_value=fake_record)
        app_ctx.engine.create_request = mock_create

        options_val = [{"id": "opt-alpha", "label": "Alpha"}, {"id": "opt-beta", "label": "Beta"}]
        await fn(
            ctx,
            task_id="1",
            kind="decision",
            title="Decision Title",
            summary="Pick one",
            agent="builder",
            options=options_val,
        )

        mock_create.assert_called_once()
        forwarded_options = mock_create.call_args.kwargs.get("options")
        assert forwarded_options == options_val, (
            f"options must be forwarded unchanged to engine, got {forwarded_options!r}"
        )

    @pytest.mark.asyncio
    async def test_create_request_normalization_forwards_normalized_body_not_raw(
        self, app_ctx: AppContext
    ) -> None:
        r"""AC5(a): normalized body (actual \n chars) is forwarded to engine, not the raw escaped string."""
        import owlbear_mcp_kanban.server as server_mod  # noqa: PLC0415

        fn = getattr(server_mod, "create_request", None)
        assert callable(fn), "owlbear_mcp_kanban.server.create_request must exist"

        ctx = _make_mcp_ctx(app_ctx)
        fake_record = _make_request_record(task_id=1)
        mock_create = MagicMock(return_value=fake_record)
        app_ctx.engine.create_request = mock_create

        raw_body = r"Line one\nLine two\nLine three"  # literal \n sequences
        expected_normalized = "Line one\nLine two\nLine three"  # actual newlines after normalization

        await fn(
            ctx,
            task_id="1",
            kind="action",
            title="Test",
            summary="Summary",
            agent="builder",
            body=raw_body,
        )

        mock_create.assert_called_once()
        forwarded_body = mock_create.call_args.kwargs.get("body")
        assert forwarded_body == expected_normalized, (
            f"engine must receive normalized body with real newlines, not raw escaped string; "
            f"expected {expected_normalized!r}, got {forwarded_body!r}"
        )
        # Raw body must NOT be forwarded
        assert forwarded_body != raw_body, (
            f"raw escaped body {raw_body!r} must not be forwarded — normalization must apply first"
        )

    # -- AC5(b): list_requests explicit status forwarding --------------------

    @pytest.mark.asyncio
    async def test_list_requests_explicit_resolved_status_forwarded_to_engine(
        self, app_ctx: AppContext
    ) -> None:
        """AC5(b): when caller passes status='resolved', engine receives exactly 'resolved'."""
        import owlbear_mcp_kanban.server as server_mod  # noqa: PLC0415

        fn = getattr(server_mod, "list_requests", None)
        assert callable(fn), "owlbear_mcp_kanban.server.list_requests must exist"

        ctx = _make_mcp_ctx(app_ctx)
        mock_list = MagicMock(return_value=[])
        app_ctx.engine.list_requests = mock_list

        await fn(ctx, status="resolved")

        mock_list.assert_called_once()
        call_args = mock_list.call_args
        forwarded_status = call_args.args[0] if call_args.args else call_args.kwargs.get("status")
        assert forwarded_status == "resolved", (
            f"explicit status='resolved' must be forwarded to engine as 'resolved', "
            f"got {forwarded_status!r} — an adapter that always sends the default would false-green the prior test"
        )

    @pytest.mark.asyncio
    async def test_list_requests_explicit_all_status_forwarded_to_engine(
        self, app_ctx: AppContext
    ) -> None:
        """AC5(b): when caller passes status='all', engine receives exactly 'all' (not default 'pending')."""
        import owlbear_mcp_kanban.server as server_mod  # noqa: PLC0415

        fn = getattr(server_mod, "list_requests", None)
        assert callable(fn), "owlbear_mcp_kanban.server.list_requests must exist"

        ctx = _make_mcp_ctx(app_ctx)
        mock_list = MagicMock(return_value=[])
        app_ctx.engine.list_requests = mock_list

        app_ctx.engine.list_requests.side_effect = None  # ensure no leftover side_effect
        app_ctx.engine.list_requests = MagicMock(return_value=[])

        await fn(ctx, status="all")

        app_ctx.engine.list_requests.assert_called_once()
        call_args = app_ctx.engine.list_requests.call_args
        forwarded_status = call_args.args[0] if call_args.args else call_args.kwargs.get("status")
        assert forwarded_status == "all", (
            f"explicit status='all' must be forwarded as 'all' to engine, got {forwarded_status!r}"
        )


# ---------------------------------------------------------------------------
# AC6+AC7 — Response-shape proof contracts
# ---------------------------------------------------------------------------

# All field names that RequestRecord.model_dump() produces.
_REQUEST_RECORD_KEYS = frozenset(
    {"task_id", "request_id", "kind", "title", "summary", "agent", "created_at", "options", "resolution", "body"}
)
# model_dump(exclude={"body"}) keys — body omitted.
_LIST_RECORD_KEYS = _REQUEST_RECORD_KEYS - {"body"}


class TestFromAC_ResponseShapeContracts:
    """AC6+AC7 response-shape proof — returned dicts must contain all expected keys."""

    # -- AC6: create_request full response shape ----------------------------

    @pytest.mark.asyncio
    async def test_create_request_success_returns_all_record_keys_plus_guidance(
        self, app_ctx: AppContext
    ) -> None:
        """AC6: create_request result must contain all 10 RequestRecord.model_dump() keys plus 'guidance'."""
        import owlbear_mcp_kanban.server as server_mod  # noqa: PLC0415

        fn = getattr(server_mod, "create_request", None)
        assert callable(fn), "owlbear_mcp_kanban.server.create_request must exist"

        ctx = _make_mcp_ctx(app_ctx)
        fake_record = _make_request_record(task_id=1, kind="action")
        app_ctx.engine.create_request = MagicMock(return_value=fake_record)

        result = await fn(
            ctx,
            task_id="1",
            kind="action",
            title="Shape Test",
            summary="Full shape check.",
            agent="builder",
            body="Clean body.",
        )

        assert isinstance(result, dict), "create_request must return a dict"
        missing = _REQUEST_RECORD_KEYS - result.keys()
        assert not missing, (
            f"create_request result is missing RequestRecord keys: {missing!r}; "
            f"got keys: {set(result.keys())!r}"
        )
        assert "guidance" in result, (
            f"create_request result must include 'guidance' key; got keys: {set(result.keys())!r}"
        )

    # -- AC7: list_requests full response shape per record ------------------

    @pytest.mark.asyncio
    async def test_list_requests_success_each_record_has_all_expected_keys_body_absent(
        self, app_ctx: AppContext
    ) -> None:
        """AC7: each dict in list_requests result must have all model_dump(exclude={'body'}) keys and no 'body'."""
        import owlbear_mcp_kanban.server as server_mod  # noqa: PLC0415

        fn = getattr(server_mod, "list_requests", None)
        assert callable(fn), "owlbear_mcp_kanban.server.list_requests must exist"

        ctx = _make_mcp_ctx(app_ctx)
        fake_record = _make_request_record(task_id=1, kind="action", body="## Hidden body")
        app_ctx.engine.list_requests = MagicMock(return_value=[fake_record])

        result = await fn(ctx, status="pending")

        assert isinstance(result, list), f"list_requests must return a list, got {result!r}"
        assert len(result) == 1, f"list_requests must return one item, got {len(result)}"
        item = result[0]
        assert isinstance(item, dict), "each item must be a dict"

        missing = _LIST_RECORD_KEYS - item.keys()
        assert not missing, (
            f"list_requests record is missing expected keys: {missing!r}; "
            f"got keys: {set(item.keys())!r}"
        )
        assert "body" not in item, (
            f"'body' must be excluded from list_requests records; got keys: {set(item.keys())!r}"
        )

    # -- AC7: show_request full response shape ------------------------------

    @pytest.mark.asyncio
    async def test_show_request_success_returns_all_record_keys(self, app_ctx: AppContext) -> None:
        """AC7: show_request result must contain all 10 RequestRecord.model_dump() keys."""
        import owlbear_mcp_kanban.server as server_mod  # noqa: PLC0415

        fn = getattr(server_mod, "show_request", None)
        assert callable(fn), "owlbear_mcp_kanban.server.show_request must exist"

        ctx = _make_mcp_ctx(app_ctx)
        fake_record = _make_request_record(task_id=1, kind="action", body="## Full body visible")
        app_ctx.engine.get_request = MagicMock(return_value=fake_record)

        result = await fn(ctx, request_id=_VALID_REQUEST_UUID)

        assert isinstance(result, dict), "show_request must return a dict"
        missing = _REQUEST_RECORD_KEYS - result.keys()
        assert not missing, (
            f"show_request result is missing RequestRecord keys: {missing!r}; "
            f"got keys: {set(result.keys())!r}"
        )


# ---------------------------------------------------------------------------
# AC6+AC7 — Value equality contracts (full payload equality, not key presence)
# ---------------------------------------------------------------------------


class TestFromAC_ValueEqualityContracts:
    """AC6+AC7 value-equality proof — returned dicts must equal model_dump() exactly, not merely share keys."""

    # -- AC6: create_request non-normalized path (guidance=[]) ---------------

    @pytest.mark.asyncio
    async def test_create_request_success_full_value_equality_non_normalized(
        self, app_ctx: AppContext
    ) -> None:
        """AC6: create_request result must equal fake_record.model_dump() | {'guidance': []} exactly."""
        import owlbear_mcp_kanban.server as server_mod  # noqa: PLC0415

        fn = getattr(server_mod, "create_request", None)
        assert callable(fn), "owlbear_mcp_kanban.server.create_request must exist"

        ctx = _make_mcp_ctx(app_ctx)
        fake_record = _make_request_record(task_id=1, kind="action")
        app_ctx.engine.create_request = MagicMock(return_value=fake_record)

        result = await fn(
            ctx,
            task_id="1",
            kind="action",
            title="Value Equality Test",
            summary="No normalization.",
            agent="builder",
            body="Clean body with actual\nnewlines only.",  # real newlines, no literal \n
        )

        expected = fake_record.model_dump() | {"guidance": []}
        assert result == expected, (
            f"create_request result must equal model_dump() merged with guidance=[]; "
            f"diff keys: {set(result.keys()) ^ set(expected.keys())}; "
            f"wrong values: {[(k, result.get(k), expected.get(k)) for k in expected if result.get(k) != expected.get(k)]!r}"
        )

    # -- AC6: create_request normalization path (guidance non-empty) ---------

    @pytest.mark.asyncio
    async def test_create_request_normalization_path_full_value_equality(
        self, app_ctx: AppContext
    ) -> None:
        r"""AC6: normalization-path result must equal fake_record.model_dump() on all record fields + non-empty guidance."""
        import owlbear_mcp_kanban.server as server_mod  # noqa: PLC0415

        fn = getattr(server_mod, "create_request", None)
        assert callable(fn), "owlbear_mcp_kanban.server.create_request must exist"

        ctx = _make_mcp_ctx(app_ctx)
        fake_record = _make_request_record(task_id=1, kind="action")
        app_ctx.engine.create_request = MagicMock(return_value=fake_record)

        result = await fn(
            ctx,
            task_id="1",
            kind="action",
            title="Norm Value Test",
            summary="Has escapes.",
            agent="builder",
            body=r"Line one\nLine two\nLine three",  # literal \n — triggers normalization
        )

        # All 10 record fields must match model_dump() exactly.
        expected_record_fields = fake_record.model_dump()
        result_record_fields = {k: v for k, v in result.items() if k != "guidance"}
        assert result_record_fields == expected_record_fields, (
            f"create_request normalization path: record fields must equal model_dump(); "
            f"wrong values: {[(k, result_record_fields.get(k), expected_record_fields.get(k)) for k in expected_record_fields if result_record_fields.get(k) != expected_record_fields.get(k)]!r}"
        )
        # guidance must be non-empty after normalization.
        guidance = result.get("guidance")
        assert isinstance(guidance, list), (
            f"create_request normalization path: guidance must be a list; got {guidance!r}"
        )
        assert len(guidance) > 0, (
            f"create_request normalization path: guidance must be non-empty; got {guidance!r}"
        )

    # -- AC7: list_requests full value equality per item ---------------------

    @pytest.mark.asyncio
    async def test_list_requests_success_full_value_equality(self, app_ctx: AppContext) -> None:
        """AC7: each item in list_requests result must equal fake_record.model_dump(exclude={'body'}) exactly."""
        import owlbear_mcp_kanban.server as server_mod  # noqa: PLC0415

        fn = getattr(server_mod, "list_requests", None)
        assert callable(fn), "owlbear_mcp_kanban.server.list_requests must exist"

        ctx = _make_mcp_ctx(app_ctx)
        fake_record = _make_request_record(task_id=1, kind="action", body="## Hidden body content")
        app_ctx.engine.list_requests = MagicMock(return_value=[fake_record])

        result = await fn(ctx, status="pending")

        assert isinstance(result, list), f"list_requests must return a list, got {result!r}"
        assert len(result) == 1, f"list_requests must return one item, got {len(result)!r}"
        expected_item = fake_record.model_dump(exclude={"body"})
        actual_item = result[0]
        assert actual_item == expected_item, (
            f"list_requests item must equal model_dump(exclude={{'body'}}) exactly; "
            f"wrong values: {[(k, actual_item.get(k), expected_item.get(k)) for k in expected_item if actual_item.get(k) != expected_item.get(k)]!r}"
        )

    # -- AC7: show_request full value equality --------------------------------

    @pytest.mark.asyncio
    async def test_show_request_success_full_value_equality(self, app_ctx: AppContext) -> None:
        """AC7: show_request result must equal fake_record.model_dump() exactly (full value equality)."""
        import owlbear_mcp_kanban.server as server_mod  # noqa: PLC0415

        fn = getattr(server_mod, "show_request", None)
        assert callable(fn), "owlbear_mcp_kanban.server.show_request must exist"

        ctx = _make_mcp_ctx(app_ctx)
        fake_record = _make_request_record(
            task_id=1,
            kind="action",
            body="## Full body visible\nWith nested content.",
        )
        app_ctx.engine.get_request = MagicMock(return_value=fake_record)

        result = await fn(ctx, request_id=_VALID_REQUEST_UUID)

        expected = fake_record.model_dump()
        assert result == expected, (
            f"show_request result must equal model_dump() exactly; "
            f"wrong values: {[(k, result.get(k), expected.get(k)) for k in expected if result.get(k) != expected.get(k)]!r}"
        )
