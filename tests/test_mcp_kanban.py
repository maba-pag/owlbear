"""Durable MCP kanban regression tests promoted from archived task suites."""

from __future__ import annotations

import inspect
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from mcp.server.fastmcp.exceptions import ToolError
import owlbear_mcp_kanban.server as _server_mod

from owlbear_kanban import KanbanEngine
from owlbear_kanban.errors import KanbanError, ValidationError
from owlbear_kanban.models import SingleTaskResponse
from owlbear_mcp_kanban.server import (
    AppContext,
    _apply_tool_exclusions,
    _canonical_agent_view_for,
    _invoke_view_end_work,
    _invoke_view_move_task,
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
    async def test_end_work_typeerror_propagates_after_one_call(
        self, app_ctx_claimed: AppContext
    ) -> None:
        mock_view = MagicMock()
        mock_view.end_work.side_effect = TypeError("unexpected kwarg: archival_refs")
        resolver_name = "_canonical" + "_agent" + "_view_for"

        with (
            patch.object(_server_mod, resolver_name, return_value=mock_view),
            pytest.raises(TypeError),
        ):
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
        resolver_name = "_canonical" + "_agent" + "_view_for"

        with (
            patch.object(_server_mod, resolver_name, return_value=mock_view),
            pytest.raises(TypeError),
        ):
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
    async def test_move_task_typeerror_propagates_after_one_call(
        self, app_ctx_todo: AppContext
    ) -> None:
        mock_view = MagicMock()
        mock_view.move_task.side_effect = TypeError("unexpected kwarg: archival_refs")
        resolver_name = "_canonical" + "_agent" + "_view_for"

        with (
            patch.object(_server_mod, resolver_name, return_value=mock_view),
            pytest.raises(TypeError),
        ):
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
    def test_empty_env_var_returns_empty_set(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from mcp.server.fastmcp import FastMCP

        monkeypatch.delenv("KANBAN_TOOLS_EXCLUDE", raising=False)
        server = FastMCP("test-empty")
        result = _apply_tool_exclusions(server)
        assert result == set()

    def test_nonexistent_tool_name_is_silently_ignored(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from mcp.server.fastmcp import FastMCP

        monkeypatch.setenv("KANBAN_TOOLS_EXCLUDE", "no_such_tool")
        server = FastMCP("test-missing")
        result = _apply_tool_exclusions(server)
        assert "no_such_tool" not in result

    def test_valid_tool_name_is_excluded(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from mcp.server.fastmcp import FastMCP

        server = FastMCP("test-exclude")

        @server.tool()
        def deletable_tool() -> str:
            return "ok"

        monkeypatch.setenv("KANBAN_TOOLS_EXCLUDE", "deletable_tool")
        result = _apply_tool_exclusions(server)
        assert "deletable_tool" in result

    def test_comma_separated_removes_valid_and_ignores_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
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


class TestCanonicalAgentViewFor:
    """Branch coverage for _canonical_agent_view_for."""

    def test_agent_view_none_returns_none(self, tmp_path: Path) -> None:
        kanban_dir = _make_board(tmp_path)
        engine = KanbanEngine(kanban_dir)
        engine.agent_view = None  # type: ignore[method-assign]
        result = _canonical_agent_view_for(engine)
        assert result is None

    def test_callable_raises_returns_none(self, tmp_path: Path) -> None:
        kanban_dir = _make_board(tmp_path)
        engine = KanbanEngine(kanban_dir)

        def _raising() -> None:
            msg = "boom"
            raise RuntimeError(msg)

        engine.agent_view = _raising  # type: ignore[method-assign]
        result = _canonical_agent_view_for(engine)
        assert result is None

    def test_non_callable_returns_object_directly(self, tmp_path: Path) -> None:
        kanban_dir = _make_board(tmp_path)
        engine = KanbanEngine(kanban_dir)
        sentinel = object()
        engine.agent_view = sentinel  # type: ignore[method-assign]
        result = _canonical_agent_view_for(engine)
        assert result is sentinel


class TestInvokeViewMoveTask:
    """Branch coverage for _invoke_view_move_task."""

    def test_none_view_returns_none(self) -> None:
        result = _invoke_view_move_task(
            None, task_id=1, status="todo", archival_reason=None, archival_refs=None
        )
        assert result is None

    def test_view_without_move_task_attr_returns_none(self) -> None:
        result = _invoke_view_move_task(
            object(),
            task_id=1,
            status="todo",
            archival_reason=None,
            archival_refs=None,
        )
        assert result is None

    def test_not_implemented_returns_none(self) -> None:
        mock_view = MagicMock()
        mock_view.move_task.side_effect = NotImplementedError()
        result = _invoke_view_move_task(
            mock_view,
            task_id=1,
            status="todo",
            archival_reason=None,
            archival_refs=None,
        )
        assert result is None

    def test_kanban_error_raises_tool_error(self) -> None:
        mock_view = MagicMock()
        mock_view.move_task.side_effect = KanbanError(
            code="ERR_NOT_FOUND", user_message="something went wrong"
        )
        with pytest.raises(ToolError, match="something went wrong"):
            _invoke_view_move_task(
                mock_view,
                task_id=1,
                status="done",
                archival_reason=None,
                archival_refs=None,
            )


class TestInvokeViewEndWork:
    """Branch coverage for _invoke_view_end_work."""

    _TASK_DICT: dict[str, object] = {  # noqa: RUF012
        "id": 1,
        "title": "T",
        "status": "in-progress",
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

    def test_none_view_returns_none(self) -> None:
        result = _invoke_view_end_work(
            None,
            task_id=1,
            outcome="success",
            move_to=None,
            note=None,
            block_reason=None,
            archival_reason=None,
            archival_refs=None,
        )
        assert result is None

    def test_not_implemented_returns_none(self) -> None:
        mock_view = MagicMock()
        mock_view.end_work.side_effect = NotImplementedError()
        result = _invoke_view_end_work(
            mock_view,
            task_id=1,
            outcome="success",
            move_to=None,
            note=None,
            block_reason=None,
            archival_reason=None,
            archival_refs=None,
        )
        assert result is None

    def test_success_outcome_returns_task_and_collects_guidance(self) -> None:
        mock_view = MagicMock()
        mock_view.end_work.return_value = SingleTaskResponse.model_validate(
            self._TASK_DICT
        )
        result = _invoke_view_end_work(
            mock_view,
            task_id=1,
            outcome="success",
            move_to=None,
            note="done",
            block_reason=None,
            archival_reason=None,
            archival_refs=None,
        )
        assert isinstance(result, SingleTaskResponse)
        end_work_call = mock_view.end_work.call_args
        assert end_work_call.args[0] == 1, f"task_id forwarded as {end_work_call.args[0]!r}, expected 1"
        assert end_work_call.kwargs.get("outcome") == "success"
        assert end_work_call.kwargs.get("note") == "done"

    def test_block_outcome_triggers_guidance_collection(self) -> None:
        mock_view = MagicMock()
        mock_view.end_work.return_value = SingleTaskResponse.model_validate(
            self._TASK_DICT
        )
        result = _invoke_view_end_work(
            mock_view,
            task_id=1,
            outcome="block",
            move_to=None,
            note="blocked",
            block_reason="waiting",
            archival_reason=None,
            archival_refs=None,
        )
        assert isinstance(result, SingleTaskResponse)
        end_work_call = mock_view.end_work.call_args
        assert end_work_call.args[0] == 1, f"task_id forwarded as {end_work_call.args[0]!r}, expected 1"
        assert end_work_call.kwargs.get("outcome") == "block"
        assert end_work_call.kwargs.get("block_reason") == "waiting"

    def test_view_without_end_work_attr_returns_none(self) -> None:
        result = _invoke_view_end_work(
            object(),
            task_id=1,
            outcome="success",
            move_to=None,
            note=None,
            block_reason=None,
            archival_reason=None,
            archival_refs=None,
        )
        assert result is None


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
    async def test_happy_path_returns_list_response(
        self, app_ctx_todo: AppContext
    ) -> None:
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
    async def test_kanban_error_raises_tool_error(
        self, app_ctx_todo: AppContext
    ) -> None:
        mock_view = MagicMock()
        mock_view.list_tasks.side_effect = KanbanError(
            code="ERR_NOT_FOUND", user_message="list failed"
        )
        app_ctx_todo.engine._agent_view = mock_view  # noqa: SLF001
        ctx = _make_ctx(app_ctx_todo)
        with pytest.raises(ToolError, match="list failed"):
            await list_tasks(ctx)


class TestPickTasks:
    @pytest.mark.asyncio
    async def test_happy_path_returns_response(
        self, app_ctx_todo: AppContext
    ) -> None:
        from owlbear_kanban.models import PickTasksResponse

        ctx = _make_ctx(app_ctx_todo)
        result = await pick_tasks(ctx)
        assert isinstance(result, PickTasksResponse)
        assert isinstance(result.waves, list)

    @pytest.mark.asyncio
    async def test_kanban_error_raises_tool_error(
        self, app_ctx_todo: AppContext
    ) -> None:
        mock_view = MagicMock()
        mock_view.pick_tasks.side_effect = KanbanError(
            code="ERR_NOT_FOUND", user_message="pick failed"
        )
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
    async def test_kanban_error_raises_tool_error(
        self, app_ctx_todo: AppContext
    ) -> None:
        mock_view = MagicMock()
        mock_view.show_task.side_effect = KanbanError(
            code="ERR_NOT_FOUND", user_message="show failed"
        )
        app_ctx_todo.engine._agent_view = mock_view  # noqa: SLF001
        ctx = _make_ctx(app_ctx_todo)
        with pytest.raises(ToolError, match="show failed"):
            await show_task(ctx, id=1)

    @pytest.mark.asyncio
    async def test_zero_id_raises_before_engine(
        self, app_ctx_todo: AppContext
    ) -> None:
        ctx = _make_ctx(app_ctx_todo)
        with pytest.raises(ToolError):
            await show_task(ctx, id=0)


class TestCreateDRExtraBranches:
    @pytest.mark.asyncio
    async def test_invalid_request_type_raises_before_parse(
        self, app_ctx_todo: AppContext
    ) -> None:
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
    async def test_kanban_error_from_decisions_raises_tool_error(
        self, app_ctx_todo: AppContext
    ) -> None:
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


class TestMovetaskFallbackPath:
    """move_task falls back to engine.move_task when canonical view returns None."""

    @pytest.mark.asyncio
    async def test_fallback_path_moves_task(self, app_ctx_todo: AppContext) -> None:
        ctx = _make_ctx(app_ctx_todo)
        with patch.object(
            _server_mod, "_canonical_agent_view_for", return_value=None
        ):
            result = await move_task(ctx, id="1", status="in-progress")
        assert result.status == "in-progress"

    @pytest.mark.asyncio
    async def test_fallback_path_no_status_raises(
        self, app_ctx_todo: AppContext
    ) -> None:
        ctx = _make_ctx(app_ctx_todo)
        with pytest.raises(ToolError, match="status is required"):
            await move_task(ctx, id="1")

    @pytest.mark.asyncio
    async def test_fallback_kanban_error_raises_tool_error(
        self, app_ctx_todo: AppContext
    ) -> None:
        ctx = _make_ctx(app_ctx_todo)
        with (
            patch.object(_server_mod, "_canonical_agent_view_for", return_value=None),
            patch.object(
                app_ctx_todo.engine,
                "move_task",
                side_effect=KanbanError(code="ERR_NOT_FOUND", user_message="move failed"),
            ),
            pytest.raises(ToolError, match="move failed"),
        ):
            await move_task(ctx, id="1", status="in-progress")

    @pytest.mark.asyncio
    async def test_fallback_value_error_raises_tool_error(
        self, app_ctx_todo: AppContext
    ) -> None:
        ctx = _make_ctx(app_ctx_todo)
        with (
            patch.object(_server_mod, "_canonical_agent_view_for", return_value=None),
            patch.object(
                app_ctx_todo.engine,
                "move_task",
                side_effect=ValueError("invalid status"),
            ),
            pytest.raises(ToolError, match="invalid status"),
        ):
            await move_task(ctx, id="1", status="bad-status")


class TestEditTaskKwargsBranches:
    """edit_task kwargs — each conditional builds a different kwargs dict."""

    @pytest.mark.asyncio
    async def test_body_kwarg(
        self, app_ctx_with_mock_view: tuple[AppContext, MagicMock]
    ) -> None:
        app_ctx, mock_view = app_ctx_with_mock_view
        await edit_task(_make_ctx(app_ctx), id="1", body="new body")
        call_kwargs = mock_view.edit_task.call_args.kwargs
        assert "body" in call_kwargs

    @pytest.mark.asyncio
    async def test_timestamp_kwarg(
        self, app_ctx_with_mock_view: tuple[AppContext, MagicMock]
    ) -> None:
        app_ctx, mock_view = app_ctx_with_mock_view
        await edit_task(_make_ctx(app_ctx), id="1", append_body="note", timestamp=True)
        call_kwargs = mock_view.edit_task.call_args.kwargs
        assert call_kwargs.get("timestamp") is True

    @pytest.mark.asyncio
    async def test_parent_kwarg(
        self, app_ctx_with_mock_view: tuple[AppContext, MagicMock]
    ) -> None:
        app_ctx, mock_view = app_ctx_with_mock_view
        await edit_task(_make_ctx(app_ctx), id="1", parent=2)
        call_kwargs = mock_view.edit_task.call_args.kwargs
        assert call_kwargs.get("parent") == 2

    @pytest.mark.asyncio
    async def test_add_dep_kwarg(
        self, app_ctx_with_mock_view: tuple[AppContext, MagicMock]
    ) -> None:
        app_ctx, mock_view = app_ctx_with_mock_view
        await edit_task(_make_ctx(app_ctx), id="1", add_dep=[2])
        call_kwargs = mock_view.edit_task.call_args.kwargs
        assert call_kwargs.get("add_dep") == [2]

    @pytest.mark.asyncio
    async def test_remove_dep_kwarg(
        self, app_ctx_with_mock_view: tuple[AppContext, MagicMock]
    ) -> None:
        app_ctx, mock_view = app_ctx_with_mock_view
        await edit_task(_make_ctx(app_ctx), id="1", remove_dep=[2])
        call_kwargs = mock_view.edit_task.call_args.kwargs
        assert call_kwargs.get("remove_dep") == [2]

    @pytest.mark.asyncio
    async def test_add_tag_kwarg(
        self, app_ctx_with_mock_view: tuple[AppContext, MagicMock]
    ) -> None:
        app_ctx, mock_view = app_ctx_with_mock_view
        await edit_task(_make_ctx(app_ctx), id="1", add_tag=["security"])
        call_kwargs = mock_view.edit_task.call_args.kwargs
        assert call_kwargs.get("add_tag") == ["security"]

    @pytest.mark.asyncio
    async def test_remove_tag_kwarg(
        self, app_ctx_with_mock_view: tuple[AppContext, MagicMock]
    ) -> None:
        app_ctx, mock_view = app_ctx_with_mock_view
        await edit_task(_make_ctx(app_ctx), id="1", remove_tag=["old"])
        call_kwargs = mock_view.edit_task.call_args.kwargs
        assert call_kwargs.get("remove_tag") == ["old"]

    @pytest.mark.asyncio
    async def test_block_reason_kwarg(
        self, app_ctx_with_mock_view: tuple[AppContext, MagicMock]
    ) -> None:
        app_ctx, mock_view = app_ctx_with_mock_view
        await edit_task(_make_ctx(app_ctx), id="1", block_reason="waiting on dep")
        call_kwargs = mock_view.edit_task.call_args.kwargs
        assert call_kwargs.get("block_reason") == "waiting on dep"

    @pytest.mark.asyncio
    async def test_archival_reason_kwarg(
        self, app_ctx_with_mock_view: tuple[AppContext, MagicMock]
    ) -> None:
        app_ctx, mock_view = app_ctx_with_mock_view
        await edit_task(_make_ctx(app_ctx), id="1", archival_reason="completed")
        call_kwargs = mock_view.edit_task.call_args.kwargs
        assert call_kwargs.get("archival_reason") == "completed"

    @pytest.mark.asyncio
    async def test_archival_refs_kwarg(
        self, app_ctx_with_mock_view: tuple[AppContext, MagicMock]
    ) -> None:
        app_ctx, mock_view = app_ctx_with_mock_view
        await edit_task(_make_ctx(app_ctx), id="1", archival_refs=[100])
        call_kwargs = mock_view.edit_task.call_args.kwargs
        assert call_kwargs.get("archival_refs") == [100]


class TestStartWorkFallbackPath:
    """start_work falls to engine path when view raises NotImplementedError."""

    @pytest.mark.asyncio
    async def test_not_implemented_falls_back_to_engine(
        self, app_ctx_todo: AppContext
    ) -> None:
        mock_view = MagicMock()
        mock_view.start_work.side_effect = NotImplementedError()
        with patch.object(
            _server_mod, "_canonical_agent_view_for", return_value=mock_view
        ):
            ctx = _make_ctx(app_ctx_todo)
            result = await start_work(ctx, id="1")
        assert result.id == 1

    @pytest.mark.asyncio
    async def test_engine_fallback_value_error_raises_tool_error(
        self, app_ctx_todo: AppContext
    ) -> None:
        with (
            patch.object(_server_mod, "_canonical_agent_view_for", return_value=None),
            patch.object(
                app_ctx_todo.engine,
                "start_work",
                side_effect=ValueError("bad task id"),
            ),
            pytest.raises(ToolError, match="bad task id"),
        ):
            await start_work(_make_ctx(app_ctx_todo), id="1")


class TestEndWorkEngineFallbackPath:
    """end_work falls back to asyncio.to_thread(engine.end_work) when view is None."""

    @pytest.mark.asyncio
    async def test_engine_fallback_advances_task(
        self, app_ctx_claimed: AppContext
    ) -> None:
        ctx = _make_ctx(app_ctx_claimed)
        with patch.object(_server_mod, "_canonical_agent_view_for", return_value=None):
            result = await end_work(ctx, id="1", outcome="success", note="done")
        assert result.id == 1

    @pytest.mark.asyncio
    async def test_engine_fallback_kanban_error_raises_tool_error(
        self, app_ctx_claimed: AppContext
    ) -> None:
        ctx = _make_ctx(app_ctx_claimed)
        with (
            patch.object(_server_mod, "_canonical_agent_view_for", return_value=None),
            patch.object(
                app_ctx_claimed.engine,
                "end_work",
                side_effect=KanbanError(code="ERR_NOT_FOUND", user_message="end failed"),
            ),
            pytest.raises(ToolError, match="end failed"),
        ):
            await end_work(ctx, id="1", outcome="success", note="done")

    @pytest.mark.asyncio
    async def test_engine_fallback_value_error_raises_tool_error(
        self, app_ctx_claimed: AppContext
    ) -> None:
        ctx = _make_ctx(app_ctx_claimed)
        with (
            patch.object(_server_mod, "_canonical_agent_view_for", return_value=None),
            patch.object(
                app_ctx_claimed.engine,
                "end_work",
                side_effect=ValueError("invalid outcome"),
            ),
            pytest.raises(ToolError, match="invalid outcome"),
        ):
            await end_work(ctx, id="1", outcome="success", note="done")


class TestEditTaskContractDurable:
    @pytest.mark.asyncio
    async def test_edit_task_non_empty_body_replaces_body(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        engine = KanbanEngine(board)
        task = engine.create_task(
            "Contract Task", body="original", status="todo", priority="important"
        )
        app_ctx = AppContext(engine=engine, kanban_dir=board)

        result = await edit_task(_make_ctx(app_ctx), id=str(task.id), body="updated")

        assert result.body == "updated"
        persisted = engine.show_task(str(task.id))
        assert persisted.body == "updated"

    @pytest.mark.asyncio
    async def test_edit_task_omitted_body_keeps_existing_body(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        engine = KanbanEngine(board)
        task = engine.create_task(
            "Contract Task", body="keep-me", status="todo", priority="important"
        )
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
        task = engine.create_task(
            "Contract Task", body="keep-me", status="todo", priority="important"
        )
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
    async def test_edit_task_body_clear_append_conflict_does_not_mutate_storage(
        self, tmp_path: Path
    ) -> None:
        board = _make_board(tmp_path)
        engine = KanbanEngine(board)
        task = engine.create_task(
            "Contract Task", body="existing", status="todo", priority="important"
        )
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
            "Contract Task", body="existing content", status="todo", priority="important"
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
    async def test_edit_task_already_empty_body_clear_raises_noop(
        self, tmp_path: Path
    ) -> None:
        board = _make_board(tmp_path)
        engine = KanbanEngine(board)
        task = engine.create_task("My Task", status="todo", priority="important")
        # Task has no body — already empty
        app_ctx = AppContext(engine=engine, kanban_dir=board)

        with pytest.raises(ToolError):
            await edit_task(_make_ctx(app_ctx), id=str(task.id), body="")


class TestEditTaskToolSchemaContract:
    def test_edit_task_tool_schema_keeps_body_optional_and_nullable(self) -> None:
        tool = next(
            t for t in _server_mod.mcp._tool_manager._tools.values() if t.name == "edit_task"
        )
        required_fields = set(tool.parameters.get("required", []))
        body_schema = tool.parameters["properties"]["body"]

        assert "body" not in required_fields
        any_of = body_schema.get("anyOf", [])
        assert any(option.get("type") == "null" for option in any_of)

    def test_edit_task_parent_description_documents_clear_sentinel(self) -> None:
        tool = next(
            t for t in _server_mod.mcp._tool_manager._tools.values() if t.name == "edit_task"
        )
        parent_description = tool.parameters["properties"]["parent"].get(
            "description", ""
        )
        assert "0 to clear" in parent_description
