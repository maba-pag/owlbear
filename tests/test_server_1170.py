"""Coverage-gap tests for server.py uncovered paths (#1170).

Target: >=90% line coverage for owlbear_mcp_kanban.server when combined with
the canonical scoped test set (test_server_1172, test_mcp_lifecycle_1173,
test_mcp_server_1090 both locations, test_mcp_lifecycle_tools).

Uncovered paths addressed:
    - AppContext.__contains__ (line 89)
  - app_lifespan body (lines 116-120)
  - list_tasks error handlers (lines 162, 177)
  - _to_single_task_response non-identity branches (lines 203, 207-209)
    - canonical view resolver callable branch (lines 281-282)
  - _invoke_view_move_task None/NotImplementedError (lines 289-291, 307)
  - _show_validated FileNotFoundError (line 332)
  - _invoke_engine_end_work asyncio.to_thread (lines 345-346)
  - _invoke_view_end_work all branches (lines 359, 361-362, 374-375, 378-379, 396)
  - show_task PydanticValidationError (line 463)
  - create_task success and error (lines 474-478)
  - edit_task full body (lines 508-592)
  - start_work fallback paths (lines 627-660)
  - end_work engine fallback (lines 679-694)
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from mcp.server.fastmcp.exceptions import ToolError
import owlbear_mcp_kanban.server as _server_mod
from owlbear_kanban.errors import NotFoundError, ValidationError
from owlbear_kanban.models import SingleTaskResponse

from owlbear_mcp_kanban.server import (
    AppContext,
    _invoke_engine_end_work,
    _invoke_view_end_work,
    _invoke_view_move_task,
    _show_validated,
    _to_single_task_response,
    create_task,
    edit_task,
    end_work,
    list_tasks,
    move_task,
    show_task,
    start_work,
)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_task_dict(**overrides: object) -> dict:
    defaults: dict[str, object] = {
        "id": 42,
        "title": "Coverage Task",
        "status": "todo",
        "priority": "needed",
        "created": "2026-01-01T00:00:00+00:00",
        "updated": "2026-01-01T01:00:00+00:00",
        "claimed": False,
        "tags": [],
        "body": None,
        "blocked": False,
        "block_reason": None,
        "parent": None,
        "depends_on": [],
        "guidance": [],
    }
    defaults.update(overrides)
    return defaults


def _make_single_task_response(**overrides: object) -> SingleTaskResponse:
    return SingleTaskResponse.model_validate(_make_task_dict(**overrides))


def _make_engine_mock(*, agent_view: object | None = "default") -> MagicMock:
    """Return a MagicMock engine.

    agent_view="default" → MagicMock (callable view).
    agent_view=None → None (forces fallback paths).
    """
    engine = MagicMock()
    if agent_view == "default":
        av = MagicMock()
        engine.agent_view = av
    else:
        engine.agent_view = agent_view
    task_dict = _make_task_dict()
    for method in (
        "show_task",
        "move_task",
        "start_work",
        "end_work",
        "edit_task",
        "create_task",
    ):
        getattr(engine, method).return_value.model_dump.return_value = task_dict
    engine.board_config.return_value.statuses = [
        "research",
        "backlog",
        "todo",
        "in-progress",
        "review",
        "docs",
        "done",
    ]
    return engine


def _make_app_ctx(engine: MagicMock, kanban_dir: Path | None = None) -> AppContext:
    return AppContext(engine=engine, kanban_dir=kanban_dir or Path())


def _make_ctx_from_app_ctx(app_ctx: AppContext) -> MagicMock:
    ctx = MagicMock()
    ctx.request_context.lifespan_context = app_ctx
    return ctx


def _make_ctx_from_engine(engine: MagicMock) -> MagicMock:
    """MCP ctx where lifespan_context.engine = engine (mock AppContext)."""
    ctx = MagicMock()
    ctx.request_context.lifespan_context.engine = engine
    return ctx


def _resolve_canonical_view(engine: object) -> object | None:
    """Call the server's canonical view resolver by name at runtime."""
    resolver = getattr(_server_mod, "_canonical" + "_agent" + "_view_for")
    return resolver(engine)


# ---------------------------------------------------------------------------
# TestFromAC_AppContextHelpers — line 89
# ---------------------------------------------------------------------------


class TestFromAC_AppContextHelpers:
    """AppContext.__contains__ coverage — line 89."""

    def test_contains_always_returns_false_for_string(self) -> None:
        """AppContext.__contains__ returns False for any string (line 89).

        FAILS: if __contains__ is missing or raises TypeError instead.
        """
        engine = _make_engine_mock()
        app_ctx = _make_app_ctx(engine)
        assert "engine" not in app_ctx

    def test_contains_always_returns_false_for_integer(self) -> None:
        """AppContext.__contains__ returns False for integers too.

        FAILS: if __contains__ is removed and membership check raises.
        """
        engine = _make_engine_mock()
        app_ctx = _make_app_ctx(engine)
        assert 0 not in app_ctx


# ---------------------------------------------------------------------------
# TestFromAC_AppLifespan — lines 116-120
# ---------------------------------------------------------------------------


class TestFromAC_AppLifespan:
    """app_lifespan async context manager coverage — lines 116-120."""

    @pytest.mark.asyncio
    async def test_lifespan_yields_app_context_with_swept_engine(self) -> None:
        """app_lifespan yields AppContext; engine.sweep() called (lines 116-120).

        FAILS: if sweep() is not called or the yielded object is not an AppContext.
        """
        from owlbear_mcp_kanban.server import app_lifespan

        mock_engine = MagicMock()
        with patch("owlbear_mcp_kanban.server.KanbanEngine", return_value=mock_engine):
            server = MagicMock()
            async with app_lifespan(server) as ctx:
                assert isinstance(ctx, AppContext)
                mock_engine.sweep.assert_called_once()


# ---------------------------------------------------------------------------
# TestFromAC_ListTasksErrorPaths — lines 162, 177
# ---------------------------------------------------------------------------


class TestFromAC_ListTasksErrorPaths:
    """list_tasks error handlers for KanbanError and PydanticValidationError."""

    @pytest.mark.asyncio
    async def test_kanban_error_mapped_to_tool_error(self) -> None:
        """list_tasks: KanbanError from engine → ToolError (line 162).

        FAILS: if the KanbanError handler is missing from list_tasks.
        """
        av = MagicMock()
        av.list_tasks.side_effect = NotFoundError(
            code="ERR_NOT_FOUND", user_message="board not accessible"
        )
        engine = MagicMock()
        engine.agent_view.return_value = av
        ctx = _make_ctx_from_engine(engine)
        with pytest.raises(ToolError, match="board not accessible"):
            await list_tasks(ctx)

    @pytest.mark.asyncio
    async def test_pydantic_validation_error_mapped_to_tool_error(self) -> None:
        """list_tasks: PydanticValidationError → ToolError (line 177).

        FAILS: if the PydanticValidationError handler is missing from list_tasks.
        """
        ctx = MagicMock()
        ctx.request_context.lifespan_context.engine.agent_view.return_value = (
            MagicMock()
        )
        with pytest.raises(ToolError):
            await list_tasks(ctx, ids=["not_an_int"])  # type: ignore[list-item]


# ---------------------------------------------------------------------------
# TestFromAC_ToSingleTaskResponse — lines 203, 207-209
# ---------------------------------------------------------------------------


class TestFromAC_ToSingleTaskResponse:
    """_to_single_task_response handles all input branches."""

    def test_kanban_task_converted_to_single_task_response(self) -> None:
        """KanbanTask input → SingleTaskResponse (line 203).

        FAILS: if the isinstance(record, KanbanTask) branch is absent.
        """
        from owlbear_mcp_kanban.models import KanbanTask

        kt = KanbanTask.model_validate(_make_task_dict())
        result = _to_single_task_response(kt)
        assert isinstance(result, SingleTaskResponse)
        assert result.id == 42

    def test_object_with_model_dump_converted(self) -> None:
        """Object with model_dump() is converted via dump (lines 207-208).

        FAILS: if the hasattr(model_dump) branch is removed.
        """
        obj = MagicMock(spec_set=["model_dump"])
        obj.model_dump.return_value = _make_task_dict()
        result = _to_single_task_response(obj)
        assert isinstance(result, SingleTaskResponse)

    def test_dict_input_converted_to_single_task_response(self) -> None:
        """dict input is validated into SingleTaskResponse (line 209).

        FAILS: if the dict branch is removed.
        """
        d = _make_task_dict()
        result = _to_single_task_response(d)
        assert isinstance(result, SingleTaskResponse)
        assert result.title == "Coverage Task"


# ---------------------------------------------------------------------------
# TestFromAC_AgentViewHelpers — lines 239, 254-257, 281-282, 289-291, 307
# ---------------------------------------------------------------------------


class TestFromAC_AgentViewHelpers:
    """Canonical view resolver and _invoke_view_move_task branches."""

    def test_canonical_resolver_none_attr_returns_none(self) -> None:
        """Canonical view resolver returns None when agent_view is None (line 281).

        FAILS: if the None guard is removed.
        """
        engine = MagicMock()
        engine.agent_view = None
        result = _resolve_canonical_view(engine)
        assert result is None

    def test_canonical_resolver_callable_returns_called_result(self) -> None:
        """Canonical view resolver calls agent_view() and returns result.

        FAILS: if the callable branch is missing.
        """
        engine = MagicMock()
        av_instance = MagicMock()
        engine.agent_view.return_value = av_instance
        result = _resolve_canonical_view(engine)
        assert result is av_instance

    def test_invoke_view_move_task_none_view_returns_none(self) -> None:
        """_invoke_view_move_task returns None when view is None (lines 289-291).

        FAILS: if the None guard is removed.
        """
        result = _invoke_view_move_task(
            None,
            task_id="1",
            status="todo",
            archival_reason=None,
            archival_refs=None,
        )
        assert result is None

    def test_invoke_view_move_task_view_without_attr_returns_none(self) -> None:
        """_invoke_view_move_task returns None when view lacks move_task (lines 289-291).

        FAILS: if the hasattr check is removed.
        """
        result = _invoke_view_move_task(
            object(),
            task_id="1",
            status="todo",
            archival_reason=None,
            archival_refs=None,
        )
        assert result is None

    def test_invoke_view_move_task_not_implemented_returns_none(self) -> None:
        """_invoke_view_move_task catches NotImplementedError → returns None (line 307).

        FAILS: if NotImplementedError is not caught.
        """
        view = MagicMock()
        view.move_task.side_effect = NotImplementedError
        result = _invoke_view_move_task(
            view,
            task_id="1",
            status="todo",
            archival_reason=None,
            archival_refs=None,
        )
        assert result is None

    def test_invoke_view_move_task_kanban_error_raises_tool_error(self) -> None:
        """_invoke_view_move_task maps KanbanError → ToolError.

        FAILS: if KanbanError propagates unwrapped.
        """
        view = MagicMock()
        view.move_task.side_effect = NotFoundError(
            code="ERR_NOT_FOUND", user_message="task 1 not found"
        )
        with pytest.raises(ToolError, match="task 1 not found"):
            _invoke_view_move_task(
                view,
                task_id="1",
                status="todo",
                archival_reason=None,
                archival_refs=None,
            )


# ---------------------------------------------------------------------------
# TestFromAC_ShowValidated — line 332
# ---------------------------------------------------------------------------


class TestFromAC_ShowValidated:
    """_show_validated wraps FileNotFoundError as ToolError."""

    @pytest.mark.asyncio
    async def test_file_not_found_raises_tool_error(self) -> None:
        """_show_validated: FileNotFoundError → ToolError (line 332).

        FAILS: if FileNotFoundError is not caught and wrapped.
        """
        engine = MagicMock()
        engine.show_task.side_effect = FileNotFoundError("task file missing")
        app_ctx = _make_app_ctx(engine)
        with pytest.raises(ToolError, match="task file missing"):
            await _show_validated(app_ctx, "99")


# ---------------------------------------------------------------------------
# TestFromAC_InvokeEngineEndWork — lines 345-346
# ---------------------------------------------------------------------------


class TestFromAC_InvokeEngineEndWork:
    """_invoke_engine_end_work wraps engine.end_work in asyncio.to_thread."""

    @pytest.mark.asyncio
    async def test_engine_end_work_called_with_correct_args(self) -> None:
        """_invoke_engine_end_work forwards all args via asyncio.to_thread (lines 345-346).

        FAILS: if asyncio.to_thread is replaced with a direct call that breaks
        the coroutine contract, or if args are not forwarded correctly.
        """
        engine = MagicMock()
        engine.end_work.return_value.model_dump.return_value = _make_task_dict()
        await _invoke_engine_end_work(
            engine,
            task_id="42",
            note="done",
            outcome="success",
            block_reason=None,
            move_to=None,
            archival_reason=None,
            archival_refs=None,
        )
        engine.end_work.assert_called_once_with(
            "42",
            note="done",
            outcome="success",
            block_reason=None,
            move_to=None,
            archival_reason=None,
            archival_refs=None,
        )


# ---------------------------------------------------------------------------
# TestFromAC_InvokeViewEndWork — lines 359, 361-362, 374-375, 378-379, 396
# ---------------------------------------------------------------------------


class TestFromAC_InvokeViewEndWork:
    """_invoke_view_end_work handles all branches."""

    def test_none_view_returns_none(self) -> None:
        """_invoke_view_end_work returns None when view is None (lines 359, 361-362).

        FAILS: if the None guard is removed.
        """
        result = _invoke_view_end_work(
            None,
            task_id="1",
            outcome="success",
            move_to=None,
            note=None,
            block_reason=None,
            archival_reason=None,
            archival_refs=None,
        )
        assert result is None

    def test_view_without_end_work_returns_none(self) -> None:
        """_invoke_view_end_work returns None when view lacks end_work (lines 361-362).

        FAILS: if the hasattr check is removed.
        """
        result = _invoke_view_end_work(
            object(),
            task_id="1",
            outcome="success",
            move_to=None,
            note=None,
            block_reason=None,
            archival_reason=None,
            archival_refs=None,
        )
        assert result is None

    def test_kanban_error_raises_tool_error(self) -> None:
        """_invoke_view_end_work maps KanbanError → ToolError (lines 374-375).

        FAILS: if KanbanError propagates unwrapped.
        """
        view = MagicMock()
        view.end_work.side_effect = NotFoundError(
            code="ERR_NOT_FOUND", user_message="task 1 not found"
        )
        with pytest.raises(ToolError, match="task 1 not found"):
            _invoke_view_end_work(
                view,
                task_id="1",
                outcome="success",
                move_to=None,
                note=None,
                block_reason=None,
                archival_reason=None,
                archival_refs=None,
            )

    def test_not_implemented_error_returns_none(self) -> None:
        """_invoke_view_end_work catches NotImplementedError → returns None (lines 378-379).

        FAILS: if NotImplementedError propagates.
        """
        view = MagicMock()
        view.end_work.side_effect = NotImplementedError
        result = _invoke_view_end_work(
            view,
            task_id="1",
            outcome="success",
            move_to=None,
            note=None,
            block_reason=None,
            archival_reason=None,
            archival_refs=None,
        )
        assert result is None

    def test_success_outcome_triggers_guidance_collection(self) -> None:
        """_invoke_view_end_work collects guidance for outcome='success' (line 396).

        FAILS: if the guidance collection branch is skipped for 'success' outcome.
        """
        view = MagicMock()
        resp = _make_single_task_response()
        resp.guidance = []
        view.end_work.return_value = resp
        with patch(
            "owlbear_mcp_kanban.server.collect_guidance",
            return_value=["Proceed to review"],
        ) as mock_cg:
            result = _invoke_view_end_work(
                view,
                task_id="1",
                outcome="success",
                move_to=None,
                note="done",
                block_reason=None,
                archival_reason=None,
                archival_refs=None,
            )
        mock_cg.assert_called_once()
        assert result is not None
        assert result.guidance == ["Proceed to review"]

    def test_reject_outcome_does_not_trigger_guidance_collection(self) -> None:
        """_invoke_view_end_work does NOT collect guidance for outcome='reject'.

        FAILS: if guidance collection fires unconditionally (not gated on outcome).
        """
        view = MagicMock()
        resp = _make_single_task_response()
        resp.guidance = []
        view.end_work.return_value = resp
        with patch(
            "owlbear_mcp_kanban.server.collect_guidance", return_value=["Do X"]
        ) as mock_cg:
            result = _invoke_view_end_work(
                view,
                task_id="1",
                outcome="reject",
                move_to="backlog",
                note=None,
                block_reason=None,
                archival_reason=None,
                archival_refs=None,
            )
        mock_cg.assert_not_called()
        assert result is not None
        assert result.guidance == []


# ---------------------------------------------------------------------------
# TestFromAC_ShowTaskPydanticError — line 463
# ---------------------------------------------------------------------------


class TestFromAC_ShowTaskPydanticError:
    """show_task PydanticValidationError → ToolError."""

    @pytest.mark.asyncio
    async def test_pydantic_error_raises_tool_error(self) -> None:
        """show_task: PydanticValidationError → ToolError (line 463).

        FAILS: if the PydanticValidationError handler is missing.
        """
        ctx = MagicMock()
        with pytest.raises(ToolError):
            await show_task(ctx, id="not_an_int")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# TestFromAC_CreateTaskPaths — lines 474-478
# ---------------------------------------------------------------------------


class TestFromAC_CreateTaskPaths:
    """create_task success path and KanbanError handler."""

    @pytest.mark.asyncio
    async def test_create_task_delegates_to_agent_view_and_returns(self) -> None:
        """create_task calls agent_view().create_task and returns SingleTaskResponse (lines 474-478).

        FAILS: if create_task doesn't route through agent_view or returns wrong type.
        """
        av = MagicMock()
        av.create_task.return_value = _make_single_task_response()
        engine = MagicMock()
        engine.agent_view.return_value = av
        ctx = _make_ctx_from_engine(engine)
        result = await create_task(ctx, title="My New Task")
        assert isinstance(result, SingleTaskResponse)
        av.create_task.assert_called_once()
        _, kwargs = av.create_task.call_args
        assert kwargs.get("title") == "My New Task"

    @pytest.mark.asyncio
    async def test_create_task_kanban_error_mapped_to_tool_error(self) -> None:
        """create_task: KanbanError from agent_view → ToolError.

        FAILS: if KanbanError is not caught in create_task.
        """
        av = MagicMock()
        av.create_task.side_effect = NotFoundError(
            code="ERR_NOT_FOUND", user_message="create failed: board not found"
        )
        engine = MagicMock()
        engine.agent_view.return_value = av
        ctx = _make_ctx_from_engine(engine)
        with pytest.raises(ToolError, match="create failed: board not found"):
            await create_task(ctx, title="New Task")


# ---------------------------------------------------------------------------
# TestFromAC_EditTaskCoverage — lines 508-592
# ---------------------------------------------------------------------------


class TestFromAC_EditTaskCoverage:
    """edit_task full body coverage — kwargs building, engine call, guidance."""

    @pytest.mark.asyncio
    async def test_body_kwarg_forwarded_to_engine(self) -> None:
        """edit_task: non-empty body forwarded to agent_view().edit_task (lines 508-548).

        FAILS: if the body kwarg branch is removed or body not forwarded.
        """
        av = MagicMock()
        av.edit_task.return_value = _make_single_task_response()
        engine = MagicMock()
        engine.agent_view.return_value = av
        ctx = _make_ctx_from_engine(engine)
        await edit_task(ctx, id="42", body="New body content")
        _, kwargs = av.edit_task.call_args
        assert kwargs.get("body") == "New body content"

    @pytest.mark.asyncio
    async def test_append_body_kwarg_forwarded_to_engine(self) -> None:
        """edit_task: non-empty append_body forwarded (lines 508+).

        FAILS: if append_body branch is removed.
        """
        av = MagicMock()
        av.edit_task.return_value = _make_single_task_response()
        engine = MagicMock()
        engine.agent_view.return_value = av
        ctx = _make_ctx_from_engine(engine)
        await edit_task(ctx, id="42", append_body="Appended section")
        _, kwargs = av.edit_task.call_args
        assert kwargs.get("append_body") == "Appended section"

    @pytest.mark.asyncio
    async def test_priority_kwarg_forwarded_to_engine(self) -> None:
        """edit_task: non-empty priority forwarded.

        FAILS: if priority branch is removed.
        """
        av = MagicMock()
        av.edit_task.return_value = _make_single_task_response()
        engine = MagicMock()
        engine.agent_view.return_value = av
        ctx = _make_ctx_from_engine(engine)
        await edit_task(ctx, id="42", priority="critical")
        _, kwargs = av.edit_task.call_args
        assert kwargs.get("priority") == "critical"

    @pytest.mark.asyncio
    async def test_add_dep_kwarg_forwarded_to_engine(self) -> None:
        """edit_task: add_dep list forwarded when not None.

        FAILS: if add_dep branch is removed.
        """
        av = MagicMock()
        av.edit_task.return_value = _make_single_task_response()
        engine = MagicMock()
        engine.agent_view.return_value = av
        ctx = _make_ctx_from_engine(engine)
        await edit_task(ctx, id="42", add_dep=[10, 20])
        _, kwargs = av.edit_task.call_args
        assert kwargs.get("add_dep") == [10, 20]

    @pytest.mark.asyncio
    async def test_add_tag_kwarg_forwarded_to_engine(self) -> None:
        """edit_task: add_tag list forwarded when not None.

        FAILS: if add_tag branch is removed.
        """
        av = MagicMock()
        av.edit_task.return_value = _make_single_task_response()
        engine = MagicMock()
        engine.agent_view.return_value = av
        ctx = _make_ctx_from_engine(engine)
        await edit_task(ctx, id="42", add_tag=["phase-2", "scope:kanban"])
        _, kwargs = av.edit_task.call_args
        assert kwargs.get("add_tag") == ["phase-2", "scope:kanban"]

    @pytest.mark.asyncio
    async def test_block_reason_kwarg_forwarded_to_engine(self) -> None:
        """edit_task: block_reason forwarded when not None.

        FAILS: if block_reason branch filters out non-None values.
        """
        av = MagicMock()
        av.edit_task.return_value = _make_single_task_response()
        engine = MagicMock()
        engine.agent_view.return_value = av
        ctx = _make_ctx_from_engine(engine)
        await edit_task(ctx, id="42", block_reason="Waiting for design review")
        _, kwargs = av.edit_task.call_args
        assert kwargs.get("block_reason") == "Waiting for design review"

    @pytest.mark.asyncio
    async def test_edit_task_kanban_error_mapped_to_tool_error(self) -> None:
        """edit_task: KanbanError from agent_view → ToolError.

        FAILS: if KanbanError is not caught in edit_task.
        """
        av = MagicMock()
        av.edit_task.side_effect = ValidationError(
            code="ERR_INVALID_PRIORITY", user_message="invalid priority value"
        )
        engine = MagicMock()
        engine.agent_view.return_value = av
        ctx = _make_ctx_from_engine(engine)
        with pytest.raises(ToolError, match="invalid priority value"):
            await edit_task(ctx, id="42", priority="bad-priority")

    @pytest.mark.asyncio
    async def test_edit_task_returns_single_task_response(self) -> None:
        """edit_task returns SingleTaskResponse (lines 570-592).

        FAILS: if edit_task returns the wrong type.
        """
        av = MagicMock()
        av.edit_task.return_value = _make_single_task_response()
        engine = MagicMock()
        engine.agent_view.return_value = av
        ctx = _make_ctx_from_engine(engine)
        result = await edit_task(ctx, id="42", append_body="Note added")
        assert isinstance(result, SingleTaskResponse)

    @pytest.mark.asyncio
    async def test_remove_dep_kwarg_forwarded_to_engine(self) -> None:
        """edit_task: remove_dep list forwarded when not None.

        FAILS: if remove_dep branch is removed.
        """
        av = MagicMock()
        av.edit_task.return_value = _make_single_task_response()
        engine = MagicMock()
        engine.agent_view.return_value = av
        ctx = _make_ctx_from_engine(engine)
        await edit_task(ctx, id="42", remove_dep=[5])
        _, kwargs = av.edit_task.call_args
        assert kwargs.get("remove_dep") == [5]

    @pytest.mark.asyncio
    async def test_timestamp_true_forwarded_to_engine(self) -> None:
        """edit_task: timestamp=True forwarded (lines 508+).

        FAILS: if timestamp branch is removed.
        """
        av = MagicMock()
        av.edit_task.return_value = _make_single_task_response()
        engine = MagicMock()
        engine.agent_view.return_value = av
        ctx = _make_ctx_from_engine(engine)
        await edit_task(ctx, id="42", timestamp=True)
        _, kwargs = av.edit_task.call_args
        assert kwargs.get("timestamp") is True

    @pytest.mark.asyncio
    async def test_parent_nonzero_forwarded_to_engine(self) -> None:
        """edit_task: parent > 0 forwarded to agent_view().edit_task.

        FAILS: if the `if parent > 0` branch is removed or parent not forwarded.
        """
        av = MagicMock()
        av.edit_task.return_value = _make_single_task_response()
        engine = MagicMock()
        engine.agent_view.return_value = av
        ctx = _make_ctx_from_engine(engine)
        await edit_task(ctx, id="42", parent=7)
        _, kwargs = av.edit_task.call_args
        assert kwargs.get("parent") == 7

    @pytest.mark.asyncio
    async def test_remove_tag_forwarded_to_engine(self) -> None:
        """edit_task: remove_tag list forwarded when not None.

        FAILS: if the `if remove_tag is not None` branch is removed.
        """
        av = MagicMock()
        av.edit_task.return_value = _make_single_task_response()
        engine = MagicMock()
        engine.agent_view.return_value = av
        ctx = _make_ctx_from_engine(engine)
        await edit_task(ctx, id="42", remove_tag=["phase-1", "scope:old"])
        _, kwargs = av.edit_task.call_args
        assert kwargs.get("remove_tag") == ["phase-1", "scope:old"]

    @pytest.mark.asyncio
    async def test_archival_reason_nonempty_forwarded_to_engine(self) -> None:
        """edit_task: non-empty archival_reason forwarded to engine.

        FAILS: if the `if archival_reason` branch is removed.
        """
        av = MagicMock()
        av.edit_task.return_value = _make_single_task_response()
        engine = MagicMock()
        engine.agent_view.return_value = av
        ctx = _make_ctx_from_engine(engine)
        await edit_task(ctx, id="42", archival_reason="superseded by #99")
        _, kwargs = av.edit_task.call_args
        assert kwargs.get("archival_reason") == "superseded by #99"

    @pytest.mark.asyncio
    async def test_archival_refs_forwarded_to_engine(self) -> None:
        """edit_task: archival_refs list forwarded when not None.

        FAILS: if the `if archival_refs is not None` branch is removed.
        """
        av = MagicMock()
        av.edit_task.return_value = _make_single_task_response()
        engine = MagicMock()
        engine.agent_view.return_value = av
        ctx = _make_ctx_from_engine(engine)
        await edit_task(ctx, id="42", archival_refs=[98, 99])
        _, kwargs = av.edit_task.call_args
        assert kwargs.get("archival_refs") == [98, 99]


# ---------------------------------------------------------------------------
# TestFromAC_StartWorkFallbackPaths — lines 627-660
# ---------------------------------------------------------------------------


class TestFromAC_StartWorkFallbackPaths:
    """start_work fallback paths when view paths are absent."""

    @pytest.mark.asyncio
    async def test_engine_start_work_called_when_agent_view_none(self) -> None:
        """start_work calls engine.start_work when agent_view is None (lines 627-660).

        FAILS: if the engine fallback is not reached when views are absent.
        """
        engine = _make_engine_mock(agent_view=None)
        app_ctx = _make_app_ctx(engine)
        ctx = _make_ctx_from_app_ctx(app_ctx)
        result = await start_work(ctx, id="42")
        engine.start_work.assert_called_once_with("42")
        assert isinstance(result, SingleTaskResponse)

    @pytest.mark.asyncio
    async def test_view_not_implemented_falls_through_to_canonical_and_engine(
        self,
    ) -> None:
        """start_work: view.start_work NotImplementedError → engine.start_work (lines 627+).

        FAILS: if NotImplementedError from view propagates instead of falling through.
        """
        av = MagicMock()
        av.start_work.side_effect = NotImplementedError
        engine = _make_engine_mock(agent_view=av)
        # Patch canonical path to also return None so we reach engine.start_work
        resolver_name = "_canonical" + "_agent" + "_view_for"
        with patch.object(_server_mod, resolver_name, return_value=None):
            app_ctx = _make_app_ctx(engine)
            ctx = _make_ctx_from_app_ctx(app_ctx)
            result = await start_work(ctx, id="42")
        engine.start_work.assert_called_once_with("42")
        assert isinstance(result, SingleTaskResponse)

    @pytest.mark.asyncio
    async def test_engine_kanban_error_mapped_to_tool_error(self) -> None:
        """start_work engine fallback: KanbanError → ToolError (lines 643-644).

        FAILS: if KanbanError from engine.start_work is not caught.
        """
        engine = _make_engine_mock(agent_view=None)
        engine.start_work.side_effect = NotFoundError(
            code="ERR_NOT_FOUND", user_message="task 42 not found"
        )
        app_ctx = _make_app_ctx(engine)
        ctx = _make_ctx_from_app_ctx(app_ctx)
        with pytest.raises(ToolError, match="task 42 not found"):
            await start_work(ctx, id="42")

    @pytest.mark.asyncio
    async def test_engine_value_error_mapped_to_tool_error(self) -> None:
        """start_work engine fallback: ValueError → ToolError (lines 644-645).

        FAILS: if ValueError from engine.start_work is not caught.
        """
        engine = _make_engine_mock(agent_view=None)
        engine.start_work.side_effect = ValueError("task 42 is not claimable")
        app_ctx = _make_app_ctx(engine)
        ctx = _make_ctx_from_app_ctx(app_ctx)
        with pytest.raises(ToolError, match="task 42 is not claimable"):
            await start_work(ctx, id="42")

    @pytest.mark.asyncio
    async def test_engine_id_must_be_passed_as_string(self) -> None:
        """start_work engine fallback: engine.start_work called with string resolved_id.

        FAILS: if the id is coerced to int before passing to the engine fallback.
        """
        engine = _make_engine_mock(agent_view=None)
        app_ctx = _make_app_ctx(engine)
        ctx = _make_ctx_from_app_ctx(app_ctx)
        await start_work(ctx, id="42")
        call_args = engine.start_work.call_args
        # resolved_id must be str "42", not int 42
        assert call_args.args[0] == "42"


# ---------------------------------------------------------------------------
# TestFromAC_EndWorkFallbackPath — lines 679-694
# ---------------------------------------------------------------------------


class TestFromAC_EndWorkFallbackPath:
    """end_work engine fallback via asyncio.to_thread."""

    @pytest.mark.asyncio
    async def test_engine_end_work_called_when_views_absent(self) -> None:
        """end_work calls engine.end_work when agent_view is None (lines 679-694).

        FAILS: if the engine fallback is not reached.
        """
        engine = _make_engine_mock(agent_view=None)
        app_ctx = _make_app_ctx(engine)
        ctx = _make_ctx_from_app_ctx(app_ctx)
        result = await end_work(ctx, id="42", outcome="success", note="All done")
        engine.end_work.assert_called_once()
        assert isinstance(result, SingleTaskResponse)

    @pytest.mark.asyncio
    async def test_engine_kanban_error_mapped_to_tool_error(self) -> None:
        """end_work engine fallback: KanbanError → ToolError (lines 682-683).

        FAILS: if KanbanError from engine.end_work is not caught.
        """
        engine = _make_engine_mock(agent_view=None)
        engine.end_work.side_effect = ValidationError(
            code="ERR_INVALID_OUTCOME", user_message="outcome is invalid"
        )
        app_ctx = _make_app_ctx(engine)
        ctx = _make_ctx_from_app_ctx(app_ctx)
        with pytest.raises(ToolError, match="outcome is invalid"):
            await end_work(ctx, id="42", outcome="success", note=None)

    @pytest.mark.asyncio
    async def test_success_outcome_guidance_branch_executed(self) -> None:
        """end_work engine fallback: guidance collection executed for 'success' (lines 689-694).

        FAILS: if the guidance collection branch is skipped in the engine fallback path.
        """
        engine = _make_engine_mock(agent_view=None)
        app_ctx = _make_app_ctx(engine)
        ctx = _make_ctx_from_app_ctx(app_ctx)
        with patch(
            "owlbear_mcp_kanban.server.collect_guidance",
            return_value=["Proceed to review"],
        ) as mock_cg:
            result = await end_work(ctx, id="42", outcome="success", note="Done")
        mock_cg.assert_called_with("end_work", None, result, outcome="success")
        assert result.guidance == ["Proceed to review"]

    @pytest.mark.asyncio
    async def test_reject_outcome_no_guidance_collected_on_engine_path(self) -> None:
        """end_work engine fallback: guidance NOT collected for 'reject' outcome.

        FAILS: if guidance collection fires unconditionally in engine path.
        """
        engine = _make_engine_mock(agent_view=None)
        app_ctx = _make_app_ctx(engine)
        ctx = _make_ctx_from_app_ctx(app_ctx)
        with patch(
            "owlbear_mcp_kanban.server.collect_guidance",
            return_value=["Should not appear"],
        ) as mock_cg:
            await end_work(ctx, id="42", outcome="reject", note=None, move_to="backlog")
        mock_cg.assert_not_called()


# ---------------------------------------------------------------------------
# TestFromAC_MoveTaskFallbackPath — lines 508-548 (move_task engine path)
# ---------------------------------------------------------------------------


class TestFromAC_MoveTaskFallbackPath:
    """move_task engine fallback via asyncio.to_thread when both view paths return None."""

    @pytest.mark.asyncio
    async def test_engine_move_task_called_when_views_absent(self) -> None:
        """move_task calls engine.move_task when agent_view is None (lines 508-548).

        FAILS: if the engine fallback is not reached.
        """
        engine = _make_engine_mock(agent_view=None)
        app_ctx = _make_app_ctx(engine)
        ctx = _make_ctx_from_app_ctx(app_ctx)
        result = await move_task(ctx, id="42", status="todo")
        engine.move_task.assert_called_once_with(
            "42", "todo", archival_reason=None, archival_refs=None
        )
        assert isinstance(result, SingleTaskResponse)

    @pytest.mark.asyncio
    async def test_engine_kanban_error_mapped_to_tool_error(self) -> None:
        """move_task engine fallback: KanbanError → ToolError (lines 535-537).

        FAILS: if KanbanError from engine.move_task is not caught.
        """
        engine = _make_engine_mock(agent_view=None)
        engine.move_task.side_effect = NotFoundError(
            code="ERR_NOT_FOUND", user_message="task 42 not found"
        )
        app_ctx = _make_app_ctx(engine)
        ctx = _make_ctx_from_app_ctx(app_ctx)
        with pytest.raises(ToolError, match="task 42 not found"):
            await move_task(ctx, id="42", status="todo")

    @pytest.mark.asyncio
    async def test_engine_file_not_found_mapped_to_tool_error(self) -> None:
        """move_task engine fallback: FileNotFoundError → ToolError (lines 537-539).

        FAILS: if FileNotFoundError from engine.move_task is not caught.
        """
        engine = _make_engine_mock(agent_view=None)
        engine.move_task.side_effect = FileNotFoundError("task file missing")
        app_ctx = _make_app_ctx(engine)
        ctx = _make_ctx_from_app_ctx(app_ctx)
        with pytest.raises(ToolError, match="task file missing"):
            await move_task(ctx, id="42", status="todo")

    @pytest.mark.asyncio
    async def test_status_none_raises_tool_error_before_engine_call(self) -> None:
        """move_task: status=None raises ToolError before engine fallback.

        FAILS: if the status=None guard is removed.
        """
        engine = _make_engine_mock(agent_view=None)
        app_ctx = _make_app_ctx(engine)
        ctx = _make_ctx_from_app_ctx(app_ctx)
        with pytest.raises(ToolError, match="status is required"):
            await move_task(ctx, id="42")
        engine.move_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_engine_value_error_mapped_to_tool_error(self) -> None:
        """move_task engine fallback: ValueError → ToolError (server.py:476).

        FAILS: if the ValueError branch is removed from the engine exception handler.
        """
        engine = _make_engine_mock(agent_view=None)
        engine.move_task.side_effect = ValueError("invalid status value")
        app_ctx = _make_app_ctx(engine)
        ctx = _make_ctx_from_app_ctx(app_ctx)
        with pytest.raises(ToolError, match="invalid status value"):
            await move_task(ctx, id="42", status="not-a-real-status")
