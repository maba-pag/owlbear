"""Durable MCP kanban regression tests promoted from archived task suites."""

from __future__ import annotations

import json
import inspect
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from mcp.server.fastmcp.exceptions import ToolError
import owlbear_mcp_kanban.server as _server_mod

from owlbear_kanban import KanbanEngine
from owlbear_kanban.errors import ConcurrencyError
from owlbear_kanban.errors import KanbanError, ValidationError
from owlbear_kanban.models import SingleTaskResponse
from owlbear_mcp_kanban.server import (
    AppContext,
    _apply_tool_exclusions,
    _show_validated,
    _to_single_task_response,
    create_dr,
    create_task,
    edit_task,
    end_work,
    list_tasks,
    move_task,
    parse_task_id,
    pick_tasks,
    show_task,
    start_work,
)
from owlbear_mcp_kanban.models import KanbanTask

_CONFIG_YAML = """\
next_id: 1
"""


def _make_board(base_dir: Path) -> Path:
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


def _make_ctx(app_ctx: AppContext) -> MagicMock:
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


@pytest.fixture
def app_ctx_with_mock_view(tmp_path: Path) -> tuple[AppContext, MagicMock]:
    kanban_dir = _make_board(tmp_path)
    engine = KanbanEngine(kanban_dir)
    engine.create_task("Seed task", status="todo", priority="important")
    engine.list_tasks()

    mock_view = MagicMock()
    response = _make_single_task_response()
    mock_view.create_task.return_value = response
    mock_view.edit_task.return_value = response
    mock_view.move_task.return_value = response
    mock_view.start_work.return_value = response
    mock_view.end_work.return_value = response

    engine._agent_view = mock_view  # noqa: SLF001
    return AppContext(engine=engine, kanban_dir=kanban_dir), mock_view


@pytest.fixture
def app_ctx_todo(tmp_path: Path) -> AppContext:
    kanban_dir = _make_board(tmp_path)
    engine = KanbanEngine(kanban_dir)
    engine.create_task("Todo task", status="todo", priority="important")
    engine.list_tasks()
    return AppContext(engine=engine, kanban_dir=kanban_dir)


@pytest.fixture
def app_ctx_claimed(tmp_path: Path) -> AppContext:
    kanban_dir = _make_board(tmp_path)
    engine = KanbanEngine(kanban_dir)
    engine.create_task("Claimed task", status="in-progress", priority="important")
    engine.list_tasks()
    engine.claim_task("1")
    return AppContext(engine=engine, kanban_dir=kanban_dir)


class TestMutationErrorHelper:
    @pytest.mark.asyncio
    async def test_create_task_routes_kanban_errors_via_shared_helper(
        self,
        app_ctx_with_mock_view: tuple[AppContext, MagicMock],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from owlbear_mcp_kanban import server

        app_ctx, mock_view = app_ctx_with_mock_view
        mock_view.create_task.side_effect = ValidationError(
            code="ERR_INVALID_PRIORITY",
            user_message="priority 'bad' is not valid",
        )

        helper_calls: list[KanbanError] = []

        def tracking_helper(exc: KanbanError) -> None:
            helper_calls.append(exc)
            raise ToolError(exc.user_message) from exc

        monkeypatch.setattr(server, "_map_kanban_error", tracking_helper)

        with pytest.raises(ToolError, match="priority 'bad' is not valid"):
            await create_task(_make_ctx(app_ctx), title="Task", priority="bad")

        assert len(helper_calls) == 1

    @pytest.mark.asyncio
    async def test_edit_task_routes_kanban_errors_via_shared_helper(
        self,
        app_ctx_with_mock_view: tuple[AppContext, MagicMock],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from owlbear_mcp_kanban import server

        app_ctx, mock_view = app_ctx_with_mock_view
        mock_view.edit_task.side_effect = ValidationError(
            code="ERR_NO_OP",
            user_message="no fields would change",
        )

        helper_calls: list[KanbanError] = []

        def tracking_helper(exc: KanbanError) -> None:
            helper_calls.append(exc)
            raise ToolError(exc.user_message) from exc

        monkeypatch.setattr(server, "_map_kanban_error", tracking_helper)

        with pytest.raises(ToolError, match="no fields would change"):
            await edit_task(_make_ctx(app_ctx), id="1", priority="critical")

        assert len(helper_calls) == 1

    def test_edit_task_has_no_status_parameter(self) -> None:
        params = inspect.signature(edit_task).parameters
        assert "status" not in params


class TestLifecycleErrorHelper:
    @pytest.mark.asyncio
    async def test_move_task_routes_kanban_errors_via_shared_helper(
        self,
        app_ctx_with_mock_view: tuple[AppContext, MagicMock],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from owlbear_mcp_kanban import server

        app_ctx, mock_view = app_ctx_with_mock_view
        mock_view.move_task.side_effect = ValidationError(
            code="ERR_INVALID_STATUS",
            user_message="status 'bad' is not valid",
        )

        helper_calls: list[KanbanError] = []

        def tracking_helper(exc: KanbanError) -> None:
            helper_calls.append(exc)
            raise ToolError(exc.user_message) from exc

        monkeypatch.setattr(server, "_map_kanban_error", tracking_helper)

        with pytest.raises(ToolError, match="status 'bad' is not valid"):
            await move_task(_make_ctx(app_ctx), id="1", status="review")

        assert len(helper_calls) == 1

    @pytest.mark.asyncio
    async def test_start_work_routes_kanban_errors_via_shared_helper(
        self,
        app_ctx_with_mock_view: tuple[AppContext, MagicMock],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from owlbear_mcp_kanban import server

        app_ctx, mock_view = app_ctx_with_mock_view
        mock_view.start_work.side_effect = ValidationError(
            code="ERR_ALREADY_CLAIMED",
            user_message="Task '1' is already claimed by another agent",
        )

        helper_calls: list[KanbanError] = []

        def tracking_helper(exc: KanbanError) -> None:
            helper_calls.append(exc)
            raise ToolError(exc.user_message) from exc

        monkeypatch.setattr(server, "_map_kanban_error", tracking_helper)

        with pytest.raises(ToolError, match="already claimed"):
            await start_work(_make_ctx(app_ctx), id="1")

        assert len(helper_calls) == 1

    @pytest.mark.asyncio
    async def test_end_work_routes_kanban_errors_via_shared_helper(
        self,
        app_ctx_with_mock_view: tuple[AppContext, MagicMock],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from owlbear_mcp_kanban import server

        app_ctx, mock_view = app_ctx_with_mock_view
        mock_view.end_work.side_effect = ValidationError(
            code="ERR_NO_OP",
            user_message="no fields would change",
        )

        helper_calls: list[KanbanError] = []

        def tracking_helper(exc: KanbanError) -> None:
            helper_calls.append(exc)
            raise ToolError(exc.user_message) from exc

        monkeypatch.setattr(server, "_map_kanban_error", tracking_helper)

        with pytest.raises(ToolError, match="no fields would change"):
            await end_work(_make_ctx(app_ctx), id="1", outcome="success", note=None)

        assert len(helper_calls) == 1


class TestNoRetryOnTypeError:
    @pytest.mark.asyncio
    async def test_end_work_typeerror_propagates_after_one_call(self, app_ctx_claimed: AppContext) -> None:
        mock_view = MagicMock()
        mock_view.end_work.side_effect = TypeError("unexpected kwarg: archival_refs")
        app_ctx_claimed.engine._agent_view = mock_view  # noqa: SLF001

        with pytest.raises(TypeError):
            await end_work(
                _make_ctx(app_ctx_claimed),
                id="1",
                outcome="success",
                note="done",
                move_to=None,
                block_reason=None,
                archival_reason="completed",
                archival_refs=[999],
            )

        assert mock_view.end_work.call_count == 1

    @pytest.mark.asyncio
    async def test_end_work_typeerror_with_null_archival_args_propagates_after_one_call(
        self, app_ctx_claimed: AppContext
    ) -> None:
        mock_view = MagicMock()
        mock_view.end_work.side_effect = TypeError("unexpected kwarg: archival_refs")
        app_ctx_claimed.engine._agent_view = mock_view  # noqa: SLF001

        with pytest.raises(TypeError):
            await end_work(
                _make_ctx(app_ctx_claimed),
                id="1",
                outcome="fail",
                note=None,
                move_to=None,
                block_reason=None,
                archival_reason=None,
                archival_refs=None,
            )

        assert mock_view.end_work.call_count == 1

    @pytest.mark.asyncio
    async def test_move_task_typeerror_propagates_after_one_call(self, app_ctx_todo: AppContext) -> None:
        mock_view = MagicMock()
        mock_view.move_task.side_effect = TypeError("unexpected kwarg: archival_refs")
        app_ctx_todo.engine._agent_view = mock_view  # noqa: SLF001

        with pytest.raises(TypeError):
            await move_task(
                _make_ctx(app_ctx_todo),
                id="1",
                status="done",
                archival_reason="completed",
                archival_refs=[999],
            )

        assert mock_view.move_task.call_count == 1


# ---------------------------------------------------------------------------
# Coverage extension — paths not exercised by the error-routing tests above
# ---------------------------------------------------------------------------


class TestParseTaskIdBoolInputs:
    """bool subclasses int in Python; parse_task_id must reject them explicitly."""

    def test_bool_true_raises_tool_error(self) -> None:
        with pytest.raises(ToolError, match=r"(?i)(integer|numeric|task_id|positive)"):
            parse_task_id(True)  # noqa: FBT003

    def test_bool_false_raises_tool_error(self) -> None:
        with pytest.raises(ToolError, match=r"(?i)(integer|numeric|task_id|positive)"):
            parse_task_id(False)  # noqa: FBT003


class TestAppContextContains:
    def test_contains_always_returns_false(self, tmp_path: Path) -> None:
        kanban_dir = _make_board(tmp_path)
        engine = KanbanEngine(kanban_dir)
        ctx = AppContext(engine=engine, kanban_dir=kanban_dir)
        assert "anything" not in ctx
        assert 42 not in ctx


class TestApplyToolExclusions:
    def test_empty_env_var_returns_empty_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from mcp.server.fastmcp import FastMCP

        monkeypatch.delenv("KANBAN_TOOLS_EXCLUDE", raising=False)
        server = FastMCP("test-empty")
        result = _apply_tool_exclusions(server)
        assert result == set()

    def test_nonexistent_tool_name_is_silently_ignored(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from mcp.server.fastmcp import FastMCP

        monkeypatch.setenv("KANBAN_TOOLS_EXCLUDE", "no_such_tool")
        server = FastMCP("test-missing")
        result = _apply_tool_exclusions(server)
        assert "no_such_tool" not in result

    def test_valid_tool_name_is_excluded(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from mcp.server.fastmcp import FastMCP

        server = FastMCP("test-exclude")

        @server.tool()
        def deletable_tool() -> str:
            return "ok"

        monkeypatch.setenv("KANBAN_TOOLS_EXCLUDE", "deletable_tool")
        result = _apply_tool_exclusions(server)
        assert "deletable_tool" in result

    def test_comma_separated_removes_valid_and_ignores_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from mcp.server.fastmcp import FastMCP

        server = FastMCP("test-multi")

        @server.tool()
        def tool_a() -> str:
            return "a"

        monkeypatch.setenv("KANBAN_TOOLS_EXCLUDE", "tool_a,no_such_tool")
        result = _apply_tool_exclusions(server)
        assert "tool_a" in result
        assert "no_such_tool" not in result


class TestToSingleTaskResponse:
    """_to_single_task_response branch coverage (KanbanTask, dict, model_dump)."""

    _TASK_DICT: dict[str, object] = {  # noqa: RUF012
        "id": 1,
        "title": "T",
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

    def test_kanban_task_input(self) -> None:
        task = KanbanTask.model_validate(self._TASK_DICT)
        result = _to_single_task_response(task)
        assert isinstance(result, SingleTaskResponse)
        assert result.id == 1

    def test_dict_input(self) -> None:
        result = _to_single_task_response(self._TASK_DICT)
        assert isinstance(result, SingleTaskResponse)
        assert result.title == "T"

    def test_object_with_model_dump(self) -> None:
        obj = MagicMock(spec=[])  # no SingleTaskResponse/KanbanTask spec
        obj.model_dump = MagicMock(return_value=self._TASK_DICT)
        result = _to_single_task_response(obj)
        assert isinstance(result, SingleTaskResponse)
        assert result.id == 1

    def test_single_task_response_passthrough(self) -> None:
        original = SingleTaskResponse.model_validate(self._TASK_DICT)
        result = _to_single_task_response(original)
        assert result is original


class TestAgentViewHelpersRemoved:
    """Regression: dead-code helpers were removed in #1360; confirm they are gone."""

    def test_canonical_agent_view_for_not_exported(self) -> None:
        import owlbear_mcp_kanban.server as srv

        assert not hasattr(srv, "_canonical_agent_view_for")

    def test_invoke_view_move_task_not_exported(self) -> None:
        import owlbear_mcp_kanban.server as srv

        assert not hasattr(srv, "_invoke_view_move_task")

    def test_invoke_view_end_work_not_exported(self) -> None:
        import owlbear_mcp_kanban.server as srv

        assert not hasattr(srv, "_invoke_view_end_work")


class TestShowValidated:
    @pytest.mark.asyncio
    async def test_file_not_found_raises_tool_error(self, tmp_path: Path) -> None:
        kanban_dir = _make_board(tmp_path)
        engine = KanbanEngine(kanban_dir)
        app_ctx = AppContext(engine=engine, kanban_dir=kanban_dir)
        engine.show_task = MagicMock(  # type: ignore[method-assign]
            side_effect=FileNotFoundError("no such task file")
        )
        with pytest.raises(ToolError, match="no such task file"):
            await _show_validated(app_ctx, 99)


class TestListTasks:
    @pytest.mark.asyncio
    async def test_happy_path_returns_list_response(self, app_ctx_todo: AppContext) -> None:
        from owlbear_kanban.models import ListTasksResponse

        ctx = _make_ctx(app_ctx_todo)
        result = await list_tasks(ctx)
        assert isinstance(result, ListTasksResponse)
        assert isinstance(result.tasks, list)
        assert len(result.tasks) >= 1

    @pytest.mark.asyncio
    async def test_with_status_filter(self, app_ctx_todo: AppContext) -> None:
        ctx = _make_ctx(app_ctx_todo)
        result = await list_tasks(ctx, status="todo")
        assert hasattr(result, "tasks")

    @pytest.mark.asyncio
    async def test_kanban_error_raises_tool_error(self, app_ctx_todo: AppContext) -> None:
        mock_view = MagicMock()
        mock_view.list_tasks.side_effect = KanbanError(code="ERR_NOT_FOUND", user_message="list failed")
        app_ctx_todo.engine._agent_view = mock_view  # noqa: SLF001
        ctx = _make_ctx(app_ctx_todo)
        with pytest.raises(ToolError, match="list failed"):
            await list_tasks(ctx)


class TestPickTasks:
    @pytest.mark.asyncio
    async def test_happy_path_returns_response(self, app_ctx_todo: AppContext) -> None:
        from owlbear_kanban.models import PickTasksResponse

        ctx = _make_ctx(app_ctx_todo)
        result = await pick_tasks(ctx)
        assert isinstance(result, PickTasksResponse)
        assert isinstance(result.waves, list)

    @pytest.mark.asyncio
    async def test_kanban_error_raises_tool_error(self, app_ctx_todo: AppContext) -> None:
        mock_view = MagicMock()
        mock_view.pick_tasks.side_effect = KanbanError(code="ERR_NOT_FOUND", user_message="pick failed")
        app_ctx_todo.engine._agent_view = mock_view  # noqa: SLF001
        ctx = _make_ctx(app_ctx_todo)
        with pytest.raises(ToolError, match="pick failed"):
            await pick_tasks(ctx)


class TestShowTask:
    @pytest.mark.asyncio
    async def test_happy_path_returns_task(self, app_ctx_todo: AppContext) -> None:
        from owlbear_kanban.models import ShowTaskResponse

        ctx = _make_ctx(app_ctx_todo)
        result = await show_task(ctx, id=1)
        assert isinstance(result, ShowTaskResponse)
        assert result.id == 1  # confirms correct task was returned, not an arbitrary result

    @pytest.mark.asyncio
    async def test_with_section_parameter(self, app_ctx_todo: AppContext) -> None:
        from owlbear_kanban.models import ShowTaskResponse

        ctx = _make_ctx(app_ctx_todo)
        result = await show_task(ctx, id=1, section="Context")
        assert isinstance(result, ShowTaskResponse)

    @pytest.mark.asyncio
    async def test_kanban_error_raises_tool_error(self, app_ctx_todo: AppContext) -> None:
        mock_view = MagicMock()
        mock_view.show_task.side_effect = KanbanError(code="ERR_NOT_FOUND", user_message="show failed")
        app_ctx_todo.engine._agent_view = mock_view  # noqa: SLF001
        ctx = _make_ctx(app_ctx_todo)
        with pytest.raises(ToolError, match="show failed"):
            await show_task(ctx, id=1)

    @pytest.mark.asyncio
    async def test_zero_id_raises_before_engine(self, app_ctx_todo: AppContext) -> None:
        ctx = _make_ctx(app_ctx_todo)
        with pytest.raises(ToolError):
            await show_task(ctx, id=0)


class TestCreateDRExtraBranches:
    @pytest.mark.asyncio
    async def test_invalid_request_type_raises_before_parse(self, app_ctx_todo: AppContext) -> None:
        ctx = _make_ctx(app_ctx_todo)
        with pytest.raises(ToolError, match="request_type must be one of"):
            await create_dr(
                ctx,
                task_id="1",
                agent="builder",
                request_type="invalid",
                body="body",
            )

    @pytest.mark.asyncio
    async def test_kanban_error_from_decisions_raises_tool_error(self, app_ctx_todo: AppContext) -> None:
        from unittest.mock import patch

        ctx = _make_ctx(app_ctx_todo)
        with (
            patch(
                "owlbear_mcp_kanban.server.decisions.create_dr",
                side_effect=KanbanError(code="ERR_NOT_FOUND", user_message="dr create failed"),
            ),
            pytest.raises(ToolError, match="dr create failed"),
        ):
            await create_dr(
                ctx,
                task_id="1",
                agent="builder",
                request_type="decision",
                body="body",
            )


class TestMoveTaskDirectPath:
    """move_task uses engine.agent_view() directly — no fallback path exists (#1360)."""

    @pytest.mark.asyncio
    async def test_direct_path_moves_task(self, app_ctx_todo: AppContext) -> None:
        ctx = _make_ctx(app_ctx_todo)
        result = await move_task(ctx, id="1", status="in-progress")
        assert result.status == "in-progress"

    @pytest.mark.asyncio
    async def test_no_status_raises_tool_error(self, app_ctx_todo: AppContext) -> None:
        ctx = _make_ctx(app_ctx_todo)
        with pytest.raises(ToolError, match="status is required"):
            await move_task(ctx, id="1")

    @pytest.mark.asyncio
    async def test_agent_view_kanban_error_raises_tool_error(self, app_ctx_todo: AppContext) -> None:
        mock_view = MagicMock()
        mock_view.move_task.side_effect = KanbanError(code="ERR_NOT_FOUND", user_message="move failed")
        app_ctx_todo.engine._agent_view = mock_view  # noqa: SLF001
        ctx = _make_ctx(app_ctx_todo)
        with pytest.raises(ToolError, match="move failed"):
            await move_task(ctx, id="1", status="in-progress")

    @pytest.mark.asyncio
    async def test_not_implemented_propagates_without_fallback(self, app_ctx_todo: AppContext) -> None:
        """NotImplementedError from agent_view().move_task() is NOT caught — no engine fallback."""
        mock_view = MagicMock()
        mock_view.move_task.side_effect = NotImplementedError("view unavailable")
        app_ctx_todo.engine._agent_view = mock_view  # noqa: SLF001
        ctx = _make_ctx(app_ctx_todo)
        with pytest.raises(NotImplementedError):
            await move_task(ctx, id="1", status="in-progress")


class TestEditTaskKwargsBranches:
    """edit_task kwargs — each conditional builds a different kwargs dict."""

    @pytest.mark.asyncio
    async def test_body_kwarg(self, app_ctx_with_mock_view: tuple[AppContext, MagicMock]) -> None:
        app_ctx, mock_view = app_ctx_with_mock_view
        await edit_task(_make_ctx(app_ctx), id="1", body="new body")
        call_kwargs = mock_view.edit_task.call_args.kwargs
        assert "body" in call_kwargs

    @pytest.mark.asyncio
    async def test_timestamp_kwarg(self, app_ctx_with_mock_view: tuple[AppContext, MagicMock]) -> None:
        app_ctx, mock_view = app_ctx_with_mock_view
        await edit_task(_make_ctx(app_ctx), id="1", append_body="note", timestamp=True)
        call_kwargs = mock_view.edit_task.call_args.kwargs
        assert call_kwargs.get("timestamp") is True

    @pytest.mark.asyncio
    async def test_parent_kwarg(self, app_ctx_with_mock_view: tuple[AppContext, MagicMock]) -> None:
        app_ctx, mock_view = app_ctx_with_mock_view
        await edit_task(_make_ctx(app_ctx), id="1", parent=2)
        call_kwargs = mock_view.edit_task.call_args.kwargs
        assert call_kwargs.get("parent") == 2

    @pytest.mark.asyncio
    async def test_add_dep_kwarg(self, app_ctx_with_mock_view: tuple[AppContext, MagicMock]) -> None:
        app_ctx, mock_view = app_ctx_with_mock_view
        await edit_task(_make_ctx(app_ctx), id="1", add_dep=[2])
        call_kwargs = mock_view.edit_task.call_args.kwargs
        assert call_kwargs.get("add_dep") == [2]

    @pytest.mark.asyncio
    async def test_remove_dep_kwarg(self, app_ctx_with_mock_view: tuple[AppContext, MagicMock]) -> None:
        app_ctx, mock_view = app_ctx_with_mock_view
        await edit_task(_make_ctx(app_ctx), id="1", remove_dep=[2])
        call_kwargs = mock_view.edit_task.call_args.kwargs
        assert call_kwargs.get("remove_dep") == [2]

    @pytest.mark.asyncio
    async def test_add_tag_kwarg(self, app_ctx_with_mock_view: tuple[AppContext, MagicMock]) -> None:
        app_ctx, mock_view = app_ctx_with_mock_view
        await edit_task(_make_ctx(app_ctx), id="1", add_tag=["security"])
        call_kwargs = mock_view.edit_task.call_args.kwargs
        assert call_kwargs.get("add_tag") == ["security"]

    @pytest.mark.asyncio
    async def test_remove_tag_kwarg(self, app_ctx_with_mock_view: tuple[AppContext, MagicMock]) -> None:
        app_ctx, mock_view = app_ctx_with_mock_view
        await edit_task(_make_ctx(app_ctx), id="1", remove_tag=["old"])
        call_kwargs = mock_view.edit_task.call_args.kwargs
        assert call_kwargs.get("remove_tag") == ["old"]

    @pytest.mark.asyncio
    async def test_block_reason_kwarg(self, app_ctx_with_mock_view: tuple[AppContext, MagicMock]) -> None:
        app_ctx, mock_view = app_ctx_with_mock_view
        await edit_task(_make_ctx(app_ctx), id="1", block_reason="waiting on dep")
        call_kwargs = mock_view.edit_task.call_args.kwargs
        assert call_kwargs.get("block_reason") == "waiting on dep"

    @pytest.mark.asyncio
    async def test_archival_reason_kwarg(self, app_ctx_with_mock_view: tuple[AppContext, MagicMock]) -> None:
        app_ctx, mock_view = app_ctx_with_mock_view
        await edit_task(_make_ctx(app_ctx), id="1", archival_reason="completed")
        call_kwargs = mock_view.edit_task.call_args.kwargs
        assert call_kwargs.get("archival_reason") == "completed"

    @pytest.mark.asyncio
    async def test_archival_refs_kwarg(self, app_ctx_with_mock_view: tuple[AppContext, MagicMock]) -> None:
        app_ctx, mock_view = app_ctx_with_mock_view
        await edit_task(_make_ctx(app_ctx), id="1", archival_refs=[100])
        call_kwargs = mock_view.edit_task.call_args.kwargs
        assert call_kwargs.get("archival_refs") == [100]


class TestStartWorkDirectPath:
    """start_work uses engine.agent_view() directly — no engine fallback (#1360)."""

    @pytest.mark.asyncio
    async def test_not_implemented_propagates_without_fallback(self, app_ctx_todo: AppContext) -> None:
        """NotImplementedError from agent_view().start_work() propagates — no engine fallback."""
        mock_view = MagicMock()
        mock_view.start_work.side_effect = NotImplementedError("view unavailable")
        app_ctx_todo.engine._agent_view = mock_view  # noqa: SLF001
        ctx = _make_ctx(app_ctx_todo)
        with pytest.raises(NotImplementedError):
            await start_work(ctx, id="1")

    @pytest.mark.asyncio
    async def test_agent_view_value_error_raises_tool_error(self, app_ctx_todo: AppContext) -> None:
        """ValueError from agent_view().start_work() is converted to ToolError."""
        mock_view = MagicMock()
        mock_view.start_work.side_effect = ValueError("bad task id")
        app_ctx_todo.engine._agent_view = mock_view  # noqa: SLF001
        with pytest.raises(ToolError, match="bad task id"):
            await start_work(_make_ctx(app_ctx_todo), id="1")


class TestEndWorkDirectPath:
    """end_work uses engine.agent_view() directly — no engine fallback (#1360)."""

    @pytest.mark.asyncio
    async def test_direct_path_advances_task(self, app_ctx_claimed: AppContext) -> None:
        ctx = _make_ctx(app_ctx_claimed)
        result = await end_work(ctx, id="1", outcome="success", note="done")
        assert result.id == 1

    @pytest.mark.asyncio
    async def test_agent_view_kanban_error_raises_tool_error(self, app_ctx_claimed: AppContext) -> None:
        mock_view = MagicMock()
        mock_view.end_work.side_effect = KanbanError(code="ERR_NOT_FOUND", user_message="end failed")
        app_ctx_claimed.engine._agent_view = mock_view  # noqa: SLF001
        ctx = _make_ctx(app_ctx_claimed)
        with pytest.raises(ToolError, match="end failed"):
            await end_work(ctx, id="1", outcome="success", note="done")

    @pytest.mark.asyncio
    async def test_agent_view_value_error_raises_tool_error(self, app_ctx_claimed: AppContext) -> None:
        mock_view = MagicMock()
        mock_view.end_work.side_effect = ValueError("invalid outcome")
        app_ctx_claimed.engine._agent_view = mock_view  # noqa: SLF001
        ctx = _make_ctx(app_ctx_claimed)
        with pytest.raises(ToolError, match="invalid outcome"):
            await end_work(ctx, id="1", outcome="success", note="done")

    @pytest.mark.asyncio
    async def test_not_implemented_propagates_without_fallback(self, app_ctx_claimed: AppContext) -> None:
        """NotImplementedError from agent_view().end_work() propagates — no engine fallback."""
        mock_view = MagicMock()
        mock_view.end_work.side_effect = NotImplementedError("view unavailable")
        app_ctx_claimed.engine._agent_view = mock_view  # noqa: SLF001
        ctx = _make_ctx(app_ctx_claimed)
        with pytest.raises(NotImplementedError):
            await end_work(ctx, id="1", outcome="success", note="done")


class TestEditTaskContractDurable:
    @pytest.mark.asyncio
    async def test_edit_task_non_empty_body_replaces_body(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        engine = KanbanEngine(board)
        task = engine.create_task("Contract Task", body="original", status="todo", priority="important")
        app_ctx = AppContext(engine=engine, kanban_dir=board)

        result = await edit_task(_make_ctx(app_ctx), id=str(task.id), body="updated")

        assert result.body == "updated"
        persisted = engine.show_task(str(task.id))
        assert persisted.body == "updated"

    @pytest.mark.asyncio
    async def test_edit_task_omitted_body_keeps_existing_body(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        engine = KanbanEngine(board)
        task = engine.create_task("Contract Task", body="keep-me", status="todo", priority="important")
        app_ctx = AppContext(engine=engine, kanban_dir=board)

        result = await edit_task(_make_ctx(app_ctx), id=str(task.id), priority="critical")

        assert result.body == "keep-me"
        persisted = engine.show_task(str(task.id))
        assert persisted.body == "keep-me"
        assert persisted.priority == "critical"

    @pytest.mark.asyncio
    async def test_edit_task_null_body_keeps_existing_body(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        engine = KanbanEngine(board)
        task = engine.create_task("Contract Task", body="keep-me", status="todo", priority="important")
        app_ctx = AppContext(engine=engine, kanban_dir=board)

        result = await edit_task(
            _make_ctx(app_ctx),
            id=str(task.id),
            body=None,
            priority="critical",
        )

        assert result.body == "keep-me"
        persisted = engine.show_task(str(task.id))
        assert persisted.body == "keep-me"
        assert persisted.priority == "critical"

    @pytest.mark.asyncio
    async def test_edit_task_body_clear_append_conflict_does_not_mutate_storage(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        engine = KanbanEngine(board)
        task = engine.create_task("Contract Task", body="existing", status="todo", priority="important")
        app_ctx = AppContext(engine=engine, kanban_dir=board)

        with pytest.raises(ToolError):
            await edit_task(
                _make_ctx(app_ctx),
                id=str(task.id),
                body="",
                append_body="more",
            )

        persisted = engine.show_task(str(task.id))
        assert persisted.body == "existing"

    @pytest.mark.asyncio
    async def test_edit_task_empty_body_clears_body(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        engine = KanbanEngine(board)
        task = engine.create_task(
            "Contract Task",
            body="existing content",
            status="todo",
            priority="important",
        )
        app_ctx = AppContext(engine=engine, kanban_dir=board)

        result = await edit_task(_make_ctx(app_ctx), id=str(task.id), body="")

        assert result.body == ""
        persisted = engine.show_task(str(task.id))
        assert persisted.body == ""

    @pytest.mark.asyncio
    async def test_edit_task_parent_zero_clears_parent(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        engine = KanbanEngine(board)
        parent_task = engine.create_task("Parent", status="todo", priority="important")
        child_task = engine.create_task("Child", status="todo", priority="important")
        engine.edit_task(str(child_task.id), parent=parent_task.id)
        app_ctx = AppContext(engine=engine, kanban_dir=board)

        result = await edit_task(_make_ctx(app_ctx), id=str(child_task.id), parent=0)

        assert result.parent is None
        persisted = engine.show_task(str(child_task.id))
        assert persisted.parent is None

    @pytest.mark.asyncio
    async def test_edit_task_title_update_succeeds(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        engine = KanbanEngine(board)
        task = engine.create_task("Original Title", status="todo", priority="important")
        app_ctx = AppContext(engine=engine, kanban_dir=board)

        result = await edit_task(_make_ctx(app_ctx), id=str(task.id), title="Updated Title")

        assert result.title == "Updated Title"
        persisted = engine.show_task(str(task.id))
        assert persisted.title == "Updated Title"

    @pytest.mark.asyncio
    async def test_edit_task_empty_title_raises_tool_error(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        engine = KanbanEngine(board)
        task = engine.create_task("My Task", status="todo", priority="important")
        app_ctx = AppContext(engine=engine, kanban_dir=board)

        with pytest.raises(ToolError):
            await edit_task(_make_ctx(app_ctx), id=str(task.id), title="")

    @pytest.mark.asyncio
    async def test_edit_task_whitespace_title_raises_tool_error(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        engine = KanbanEngine(board)
        task = engine.create_task("My Task", status="todo", priority="important")
        app_ctx = AppContext(engine=engine, kanban_dir=board)

        with pytest.raises(ToolError):
            await edit_task(_make_ctx(app_ctx), id=str(task.id), title="   ")

    @pytest.mark.asyncio
    async def test_edit_task_already_empty_body_clear_raises_noop(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        engine = KanbanEngine(board)
        task = engine.create_task("My Task", status="todo", priority="important")
        # Task has no body — already empty
        app_ctx = AppContext(engine=engine, kanban_dir=board)

        with pytest.raises(ToolError, match="No changes requested"):
            await edit_task(_make_ctx(app_ctx), id=str(task.id), body="")


class TestEditTaskToolSchemaContract:
    def test_edit_task_tool_schema_keeps_body_optional_and_nullable(self) -> None:
        tool = next(t for t in _server_mod.mcp._tool_manager._tools.values() if t.name == "edit_task")
        required_fields = set(tool.parameters.get("required", []))
        body_schema = tool.parameters["properties"]["body"]

        assert "body" not in required_fields
        any_of = body_schema.get("anyOf", [])
        assert any(option.get("type") == "null" for option in any_of)

    def test_edit_task_parent_description_documents_clear_sentinel(self) -> None:
        tool = next(t for t in _server_mod.mcp._tool_manager._tools.values() if t.name == "edit_task")
        parent_description = tool.parameters["properties"]["parent"].get("description", "")
        assert "0 to clear" in parent_description


@pytest.fixture
def app_ctx_mock_1091(tmp_path: Path) -> tuple[AppContext, MagicMock]:
    """Merged from task file 1091 with fixture name adjusted to avoid collisions."""
    kanban_dir = _make_board(tmp_path)
    engine = KanbanEngine(kanban_dir)
    engine.create_task("Seed task", status="todo", priority="important")
    engine.list_tasks()
    mock_view = MagicMock()
    mock_view.create_task.return_value = _make_single_task_response()
    mock_view.edit_task.return_value = _make_single_task_response()
    engine._agent_view = mock_view  # noqa: SLF001
    return AppContext(engine=engine, kanban_dir=kanban_dir), mock_view


@pytest.fixture
def app_ctx_mock_1092(tmp_path: Path) -> tuple[AppContext, MagicMock]:
    """Merged from task file 1092 with fixture name adjusted to avoid collisions."""
    kanban_dir = _make_board(tmp_path)
    engine = KanbanEngine(kanban_dir)
    engine.create_task("Seed task", status="todo", priority="important")
    engine.list_tasks()
    mock_view = MagicMock()
    mock_view.move_task.return_value = _make_single_task_response(status="review")
    mock_view.start_work.return_value = _make_single_task_response(status="review")
    mock_view.end_work.return_value = _make_single_task_response(status="review")
    engine._agent_view = mock_view  # noqa: SLF001
    return AppContext(engine=engine, kanban_dir=kanban_dir), mock_view


@pytest.fixture
def app_ctx_1196(tmp_path: Path) -> AppContext:
    """Merged from task file 1196 with fixture name adjusted to avoid collisions."""
    kanban_dir = _make_board(tmp_path)
    engine = KanbanEngine(kanban_dir)
    return AppContext(engine=engine, kanban_dir=kanban_dir)


@pytest.fixture
def app_ctx_1450(tmp_path: Path) -> AppContext:
    """Merged from task file 1450 with fixture name adjusted to avoid collisions."""
    kanban_dir = _make_board(tmp_path)
    engine = KanbanEngine(kanban_dir)
    engine.create_task("Active task", status="todo", priority="important")
    return AppContext(engine=engine, kanban_dir=kanban_dir)


@pytest.fixture
def app_ctx_with_archived_duplicate_1450(tmp_path: Path) -> AppContext:
    """One archived duplicate task plus one active reference task."""
    kanban_dir = _make_board(tmp_path)
    engine = KanbanEngine(kanban_dir)
    ref_task = engine.create_task("Reference task", status="todo", priority="important")
    dup_task = engine.create_task("Duplicate task", status="todo", priority="important")
    engine.agent_view().move_task(
        dup_task.id,
        "archived",
        archival_reason="duplicate",
        archival_refs=[ref_task.id],
    )
    return AppContext(engine=engine, kanban_dir=kanban_dir)


@pytest.fixture
def app_ctx_with_mixed_archived_1450(tmp_path: Path) -> AppContext:
    """Mixed archived reasons for archival_reason filtering assertions."""
    kanban_dir = _make_board(tmp_path)
    engine = KanbanEngine(kanban_dir)
    dup_task = engine.create_task("Duplicate task", status="todo", priority="important")
    comp_task = engine.create_task("Completed task", status="todo", priority="important")
    ref_task = engine.create_task("Reference task", status="todo", priority="important")
    av = engine.agent_view()
    av.move_task(
        dup_task.id,
        "archived",
        archival_reason="duplicate",
        archival_refs=[ref_task.id],
    )
    av.move_task(comp_task.id, "done")
    av.move_task(comp_task.id, "archived", archival_reason="completed")
    return AppContext(engine=engine, kanban_dir=kanban_dir)


def _get_tool_annotations(tool_name: str) -> object | None:
    """Return ToolAnnotations for a named MCP tool, if present."""
    from owlbear_mcp_kanban.server import mcp  # noqa: PLC0415

    if hasattr(mcp, "_tool_manager"):
        for tool in mcp._tool_manager._tools.values():  # noqa: SLF001
            if tool.name == tool_name:
                return getattr(tool, "annotations", None)
    return None


class TestMergedFrom1091:
    @pytest.mark.asyncio
    async def test_create_task_calls_map_kanban_error_helper(
        self,
        app_ctx_mock_1091: tuple[AppContext, MagicMock],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from owlbear_mcp_kanban import server

        app_ctx, mock_view = app_ctx_mock_1091
        mock_view.create_task.side_effect = ValidationError(
            code="ERR_INVALID_PRIORITY",
            user_message="priority 'bad' is not valid",
        )

        helper_calls: list[KanbanError] = []

        def tracking_helper(exc: KanbanError) -> None:
            helper_calls.append(exc)
            raise ToolError(exc.user_message) from exc

        monkeypatch.setattr(server, "_map_kanban_error", tracking_helper)

        with pytest.raises(ToolError):
            await create_task(_make_ctx(app_ctx), title="T", priority="bad")

        assert len(helper_calls) == 1

    @pytest.mark.asyncio
    async def test_edit_task_calls_map_kanban_error_helper(
        self,
        app_ctx_mock_1091: tuple[AppContext, MagicMock],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from owlbear_mcp_kanban import server

        app_ctx, mock_view = app_ctx_mock_1091
        mock_view.edit_task.side_effect = ValidationError(
            code="ERR_NO_OP",
            user_message="no fields would change",
        )

        helper_calls: list[KanbanError] = []

        def tracking_helper(exc: KanbanError) -> None:
            helper_calls.append(exc)
            raise ToolError(exc.user_message) from exc

        monkeypatch.setattr(server, "_map_kanban_error", tracking_helper)

        with pytest.raises(ToolError):
            await edit_task(_make_ctx(app_ctx), id="1", priority="critical")

        assert len(helper_calls) == 1

    def test_edit_task_has_no_status_parameter_1091(self) -> None:
        params = inspect.signature(edit_task).parameters
        assert "status" not in params


class TestMergedFrom1092:
    @pytest.mark.asyncio
    async def test_move_task_kanban_error_routed_via_helper(
        self,
        app_ctx_mock_1092: tuple[AppContext, MagicMock],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        import owlbear_mcp_kanban.server as server_mod

        app_ctx, mock_view = app_ctx_mock_1092
        mock_view.move_task.side_effect = ValidationError(
            code="ERR_INVALID_STATUS",
            user_message="status 'bad' is not valid",
        )

        helper_calls: list[KanbanError] = []

        def tracking_helper(exc: KanbanError) -> None:
            helper_calls.append(exc)
            raise ToolError(exc.user_message) from exc

        monkeypatch.setattr(server_mod, "_map_kanban_error", tracking_helper)

        with pytest.raises(ToolError):
            await move_task(_make_ctx(app_ctx), id="1", status="review")

        assert len(helper_calls) == 1

    @pytest.mark.asyncio
    async def test_start_work_kanban_error_routed_via_helper(
        self,
        app_ctx_mock_1092: tuple[AppContext, MagicMock],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        import owlbear_mcp_kanban.server as server_mod

        app_ctx, mock_view = app_ctx_mock_1092
        mock_view.start_work.side_effect = ValidationError(
            code="ERR_ALREADY_CLAIMED",
            user_message="Task '1' is already claimed by another agent",
        )

        helper_calls: list[KanbanError] = []

        def tracking_helper(exc: KanbanError) -> None:
            helper_calls.append(exc)
            raise ToolError(exc.user_message) from exc

        monkeypatch.setattr(server_mod, "_map_kanban_error", tracking_helper)

        with pytest.raises(ToolError):
            await start_work(_make_ctx(app_ctx), id="1")

        assert len(helper_calls) == 1

    @pytest.mark.asyncio
    async def test_end_work_kanban_error_routed_via_helper(
        self,
        app_ctx_mock_1092: tuple[AppContext, MagicMock],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        import owlbear_mcp_kanban.server as server_mod

        app_ctx, mock_view = app_ctx_mock_1092
        mock_view.end_work.side_effect = ValidationError(
            code="ERR_BLOCK_REASON_REQUIRED",
            user_message="block_reason is required when outcome='block'",
        )

        helper_calls: list[KanbanError] = []

        def tracking_helper(exc: KanbanError) -> None:
            helper_calls.append(exc)
            raise ToolError(exc.user_message) from exc

        monkeypatch.setattr(server_mod, "_map_kanban_error", tracking_helper)

        with pytest.raises(ToolError):
            await end_work(
                _make_ctx(app_ctx),
                id="1",
                outcome="block",
                note="blocked",
                block_reason=None,
            )

        assert len(helper_calls) == 1

    def test_move_task_no_local_archival_validation_in_source(self) -> None:
        source = inspect.getsource(_server_mod)
        assert "archival_reason is required when status" not in source

    def test_end_work_adapter_no_param_normalization_in_source(self) -> None:
        source = inspect.getsource(end_work)
        assert 'note or ""' not in source
        assert "block_reason or" not in source

    def test_end_work_adapter_no_tag_mutation_in_source(self) -> None:
        source = inspect.getsource(end_work)
        assert "block:user" not in source

    def test_start_work_adapter_no_business_logic_in_source(self) -> None:
        source = inspect.getsource(start_work)
        assert 'or ""' not in source
        assert "claim_timeout" not in source


class TestMergedFrom1126:
    def test_no_except_typeerror_in_server_source(self) -> None:
        source = Path(_server_mod.__file__).read_text(encoding="utf-8")
        assert "except TypeError" not in source


class TestMergedFrom1196:
    @pytest.mark.asyncio
    async def test_empty_string_rejected_with_tool_error(self, app_ctx_1196: AppContext) -> None:
        from unittest.mock import patch

        with (
            patch("owlbear_mcp_kanban.server.decisions.create_dr"),
            pytest.raises(ToolError),
        ):
            await create_dr(
                _make_ctx(app_ctx_1196),
                task_id="",
                agent="builder",
                request_type="decision",
                body="b",
            )

    @pytest.mark.asyncio
    async def test_wildcard_rejected_with_tool_error(self, app_ctx_1196: AppContext) -> None:
        from unittest.mock import patch

        with (
            patch("owlbear_mcp_kanban.server.decisions.create_dr"),
            pytest.raises(ToolError),
        ):
            await create_dr(
                _make_ctx(app_ctx_1196),
                task_id="*",
                agent="builder",
                request_type="decision",
                body="b",
            )

    @pytest.mark.asyncio
    async def test_path_traversal_rejected_with_tool_error(self, app_ctx_1196: AppContext) -> None:
        from unittest.mock import patch

        with (
            patch("owlbear_mcp_kanban.server.decisions.create_dr"),
            pytest.raises(ToolError),
        ):
            await create_dr(
                _make_ctx(app_ctx_1196),
                task_id="../",
                agent="builder",
                request_type="decision",
                body="b",
            )

    @pytest.mark.asyncio
    async def test_non_numeric_string_rejected_with_tool_error(self, app_ctx_1196: AppContext) -> None:
        from unittest.mock import patch

        with (
            patch("owlbear_mcp_kanban.server.decisions.create_dr"),
            pytest.raises(ToolError),
        ):
            await create_dr(
                _make_ctx(app_ctx_1196),
                task_id="abc",
                agent="builder",
                request_type="decision",
                body="b",
            )

    @pytest.mark.asyncio
    async def test_mixed_alphanumeric_rejected_with_tool_error(self, app_ctx_1196: AppContext) -> None:
        from unittest.mock import patch

        with (
            patch("owlbear_mcp_kanban.server.decisions.create_dr"),
            pytest.raises(ToolError),
        ):
            await create_dr(
                _make_ctx(app_ctx_1196),
                task_id="42abc",
                agent="builder",
                request_type="decision",
                body="b",
            )

    @pytest.mark.asyncio
    async def test_wildcard_does_not_reach_decisions_create_dr(self, app_ctx_1196: AppContext) -> None:
        from unittest.mock import patch

        with patch("owlbear_mcp_kanban.server.decisions.create_dr") as mock_create_dr:
            with pytest.raises(ToolError):
                await create_dr(
                    _make_ctx(app_ctx_1196),
                    task_id="*",
                    agent="builder",
                    request_type="decision",
                    body="b",
                )
            mock_create_dr.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_string_does_not_reach_decisions_create_dr(self, app_ctx_1196: AppContext) -> None:
        from unittest.mock import patch

        with patch("owlbear_mcp_kanban.server.decisions.create_dr") as mock_create_dr:
            with pytest.raises(ToolError):
                await create_dr(
                    _make_ctx(app_ctx_1196),
                    task_id="",
                    agent="builder",
                    request_type="decision",
                    body="b",
                )
            mock_create_dr.assert_not_called()

    @pytest.mark.asyncio
    async def test_path_traversal_does_not_reach_decisions_create_dr(self, app_ctx_1196: AppContext) -> None:
        from unittest.mock import patch

        with patch("owlbear_mcp_kanban.server.decisions.create_dr") as mock_create_dr:
            with pytest.raises(ToolError):
                await create_dr(
                    _make_ctx(app_ctx_1196),
                    task_id="../",
                    agent="builder",
                    request_type="decision",
                    body="b",
                )
            mock_create_dr.assert_not_called()

    @pytest.mark.asyncio
    async def test_non_numeric_string_does_not_reach_decisions_create_dr(self, app_ctx_1196: AppContext) -> None:
        from unittest.mock import patch

        with patch("owlbear_mcp_kanban.server.decisions.create_dr") as mock_create_dr:
            with pytest.raises(ToolError):
                await create_dr(
                    _make_ctx(app_ctx_1196),
                    task_id="abc",
                    agent="builder",
                    request_type="decision",
                    body="b",
                )
            mock_create_dr.assert_not_called()

    @pytest.mark.asyncio
    async def test_mixed_alphanumeric_does_not_reach_decisions_create_dr(self, app_ctx_1196: AppContext) -> None:
        from unittest.mock import patch

        with patch("owlbear_mcp_kanban.server.decisions.create_dr") as mock_create_dr:
            with pytest.raises(ToolError):
                await create_dr(
                    _make_ctx(app_ctx_1196),
                    task_id="42abc",
                    agent="builder",
                    request_type="decision",
                    body="b",
                )
            mock_create_dr.assert_not_called()

    @pytest.mark.asyncio
    async def test_numeric_string_coerced_to_int_before_forwarding(self, app_ctx_1196: AppContext) -> None:
        from unittest.mock import patch

        mock_create_dr = MagicMock(return_value=MagicMock())
        with patch("owlbear_mcp_kanban.server.decisions.create_dr", mock_create_dr):
            await create_dr(
                _make_ctx(app_ctx_1196),
                task_id="42",
                agent="builder",
                request_type="decision",
                body="body text",
            )

        call_kwargs = mock_create_dr.call_args.kwargs
        assert call_kwargs["task_id"] == 42
        assert isinstance(call_kwargs["task_id"], int)

    @pytest.mark.asyncio
    async def test_literal_int_task_id_forwarded_unchanged(self, app_ctx_1196: AppContext) -> None:
        from unittest.mock import patch

        mock_create_dr = MagicMock(return_value=MagicMock())
        with patch("owlbear_mcp_kanban.server.decisions.create_dr", mock_create_dr):
            await create_dr(
                _make_ctx(app_ctx_1196),
                task_id=42,
                agent="builder",
                request_type="decision",
                body="body text",
            )

        call_kwargs = mock_create_dr.call_args.kwargs
        assert call_kwargs["task_id"] == 42
        assert isinstance(call_kwargs["task_id"], int)


class TestMergedFrom1197:
    def test_server_has_no_unittest_mock_import(self) -> None:
        server_py = (
            Path(__file__).parent / ".." / "serve" / "mcp-kanban" / "src" / "owlbear_mcp_kanban" / "server.py"
        ).resolve()
        source = server_py.read_text(encoding="utf-8")
        assert "from unittest.mock import Mock" not in source

    def test_server_has_no_isinstance_mock_check(self) -> None:
        server_py = (
            Path(__file__).parent / ".." / "serve" / "mcp-kanban" / "src" / "owlbear_mcp_kanban" / "server.py"
        ).resolve()
        source = server_py.read_text(encoding="utf-8")
        assert "isinstance(return_value, Mock)" not in source

    def test_agent_view_for_not_defined_in_server(self) -> None:
        server_py = (
            Path(__file__).parent / ".." / "serve" / "mcp-kanban" / "src" / "owlbear_mcp_kanban" / "server.py"
        ).resolve()
        source = server_py.read_text(encoding="utf-8")
        assert "def _agent_view_for" not in source

    def test_lifecycle_tools_mock_av_fixture_uses_noncallable_agent_view(self) -> None:
        source = (
            (Path(__file__).parent / ".." / "serve" / "mcp-kanban" / "tests" / "test_mcp_lifecycle_tools.py")
            .resolve()
            .read_text(encoding="utf-8")
        )
        assert "NonCallableMagicMock" in source


class TestMergedFrom1360:
    @pytest.mark.asyncio
    async def test_move_task_not_implemented_propagates_without_fallback(self, app_ctx_todo: AppContext) -> None:
        mock_view = MagicMock()
        mock_view.move_task.side_effect = NotImplementedError("view unavailable")
        app_ctx_todo.engine._agent_view = mock_view  # noqa: SLF001
        ctx = _make_ctx(app_ctx_todo)
        with pytest.raises(NotImplementedError):
            await move_task(ctx, id="1", status="in-progress")

    @pytest.mark.asyncio
    async def test_start_work_not_implemented_propagates_without_fallback(self) -> None:
        mock_view = MagicMock()
        mock_view.start_work.side_effect = NotImplementedError
        ctx = MagicMock()
        ctx.request_context.lifespan_context.engine = MagicMock()
        ctx.request_context.lifespan_context.engine.agent_view = MagicMock(return_value=mock_view)
        with pytest.raises(NotImplementedError):
            await start_work(ctx, id="42")

    @pytest.mark.asyncio
    async def test_end_work_not_implemented_propagates_without_fallback(self) -> None:
        mock_view = MagicMock()
        mock_view.end_work.side_effect = NotImplementedError
        ctx = MagicMock()
        ctx.request_context.lifespan_context.engine = MagicMock()
        ctx.request_context.lifespan_context.engine.agent_view = MagicMock(return_value=mock_view)
        with pytest.raises(NotImplementedError):
            await end_work(ctx, id="42", outcome="success")

    def test_canonical_agent_view_for_helper_removed(self) -> None:
        assert not hasattr(_server_mod, "_canonical_agent_view_for")

    def test_invoke_view_move_task_removed(self) -> None:
        assert not hasattr(_server_mod, "_invoke_view_move_task")

    def test_invoke_view_end_work_removed(self) -> None:
        assert not hasattr(_server_mod, "_invoke_view_end_work")

    def test_invoke_engine_end_work_removed(self) -> None:
        assert not hasattr(_server_mod, "_invoke_engine_end_work")


class TestMergedFrom1450:
    @pytest.mark.asyncio
    async def test_empty_ids_returns_empty_task_list(self, app_ctx_1450: AppContext) -> None:
        result = await list_tasks(_make_ctx(app_ctx_1450), ids=[])
        assert result.tasks == []

    @pytest.mark.asyncio
    async def test_empty_ids_returns_empty_for_multi_task_board(self, tmp_path: Path) -> None:
        kanban_dir = _make_board(tmp_path)
        engine = KanbanEngine(kanban_dir)
        engine.create_task("Alpha task", status="todo", priority="important")
        engine.create_task("Beta task", status="backlog", priority="needed")
        engine.create_task("Gamma task", status="review", priority="needed")
        app_ctx = AppContext(engine=engine, kanban_dir=kanban_dir)
        result = await list_tasks(_make_ctx(app_ctx), ids=[])
        assert result.tasks == []

    @pytest.mark.asyncio
    async def test_empty_ids_returns_missing_ids_is_none(self, app_ctx_1450: AppContext) -> None:
        result = await list_tasks(_make_ctx(app_ctx_1450), ids=[])
        assert result.missing_ids is None

    @pytest.mark.asyncio
    async def test_archival_reason_without_status_finds_archived_task(
        self, app_ctx_with_archived_duplicate_1450: AppContext
    ) -> None:
        result = await list_tasks(_make_ctx(app_ctx_with_archived_duplicate_1450), archival_reason="duplicate")
        assert len(result.tasks) >= 1

    @pytest.mark.asyncio
    async def test_archival_reason_filter_all_returned_tasks_match(
        self, app_ctx_with_archived_duplicate_1450: AppContext
    ) -> None:
        result = await list_tasks(_make_ctx(app_ctx_with_archived_duplicate_1450), archival_reason="duplicate")
        assert result.tasks
        assert all(t.archival_reason == "duplicate" for t in result.tasks)

    @pytest.mark.asyncio
    async def test_archival_reason_duplicate_excludes_completed_reason(
        self, app_ctx_with_mixed_archived_1450: AppContext
    ) -> None:
        result = await list_tasks(_make_ctx(app_ctx_with_mixed_archived_1450), archival_reason="duplicate")
        assert len(result.tasks) == 1
        assert result.tasks[0].archival_reason == "duplicate"

    @pytest.mark.asyncio
    async def test_move_task_invalid_status_raises_tool_error_with_json_payload(self, app_ctx_1450: AppContext) -> None:
        with pytest.raises(ToolError) as exc_info:
            await move_task(_make_ctx(app_ctx_1450), id="1", status="not-a-real-status")
        payload = json.loads(str(exc_info.value))
        assert isinstance(payload, dict)

    @pytest.mark.asyncio
    async def test_move_task_invalid_status_json_has_code_and_message(self, app_ctx_1450: AppContext) -> None:
        with pytest.raises(ToolError) as exc_info:
            await move_task(_make_ctx(app_ctx_1450), id="1", status="not-a-real-status")
        payload = json.loads(str(exc_info.value))
        assert "code" in payload
        assert "message" in payload

    @pytest.mark.asyncio
    async def test_end_work_reject_invalid_move_to_raises_tool_error_with_json_payload(
        self, app_ctx_1450: AppContext
    ) -> None:
        with pytest.raises(ToolError) as exc_info:
            await end_work(
                _make_ctx(app_ctx_1450),
                id="1",
                outcome="reject",
                move_to="not-a-real-status",
            )
        payload = json.loads(str(exc_info.value))
        assert isinstance(payload, dict)

    @pytest.mark.asyncio
    async def test_end_work_reject_invalid_move_to_json_has_code_and_message(self, app_ctx_1450: AppContext) -> None:
        with pytest.raises(ToolError) as exc_info:
            await end_work(
                _make_ctx(app_ctx_1450),
                id="1",
                outcome="reject",
                move_to="not-a-real-status",
            )
        payload = json.loads(str(exc_info.value))
        assert "code" in payload
        assert "message" in payload
        assert payload["code"] == "ERR_INVALID_STATUS"

    def test_move_task_idempotent_hint_is_false(self) -> None:
        ann = _get_tool_annotations("move_task")
        assert ann is not None
        assert ann.idempotentHint is False  # type: ignore[union-attr]

    def test_pick_tasks_read_only_hint_is_true(self) -> None:
        ann = _get_tool_annotations("pick_tasks")
        assert ann is not None
        assert ann.readOnlyHint is True  # type: ignore[union-attr]

    def test_pick_tasks_idempotent_hint_is_true(self) -> None:
        ann = _get_tool_annotations("pick_tasks")
        assert ann is not None
        assert ann.idempotentHint is True  # type: ignore[union-attr]

    def test_non_numeric_id_raises_tool_error_with_json_payload(self) -> None:
        with pytest.raises(ToolError) as exc_info:
            parse_task_id("abc")
        payload = json.loads(str(exc_info.value))
        assert isinstance(payload, dict)

    def test_malformed_id_json_has_code_and_message_fields(self) -> None:
        with pytest.raises(ToolError) as exc_info:
            parse_task_id("not-a-number")
        payload = json.loads(str(exc_info.value))
        assert "code" in payload
        assert "message" in payload

    @pytest.mark.asyncio
    async def test_stale_write_via_edit_task_returns_json_envelope(self, tmp_path: Path) -> None:
        mock_view = MagicMock()
        mock_view.edit_task.side_effect = ConcurrencyError(
            code="ERR_STALE",
            user_message="task was modified concurrently; please retry",
        )
        mock_engine = MagicMock()
        mock_engine.agent_view.return_value = mock_view
        app_ctx = AppContext(engine=mock_engine, kanban_dir=tmp_path)

        with pytest.raises(ToolError) as exc_info:
            await edit_task(_make_ctx(app_ctx), id="1", priority="critical")

        payload = json.loads(str(exc_info.value))
        assert isinstance(payload, dict)

    @pytest.mark.asyncio
    async def test_stale_write_json_has_code_and_message(self, tmp_path: Path) -> None:
        mock_view = MagicMock()
        user_msg = "task was modified concurrently; please retry"
        mock_view.edit_task.side_effect = ConcurrencyError(
            code="ERR_STALE",
            user_message=user_msg,
        )
        mock_engine = MagicMock()
        mock_engine.agent_view.return_value = mock_view
        app_ctx = AppContext(engine=mock_engine, kanban_dir=tmp_path)

        with pytest.raises(ToolError) as exc_info:
            await edit_task(_make_ctx(app_ctx), id="1", priority="critical")

        payload = json.loads(str(exc_info.value))
        assert "code" in payload
        assert "message" in payload
        assert payload["code"] == "ERR_STALE"
        assert payload["message"] == user_msg
