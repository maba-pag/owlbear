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
    create_task,
    edit_task,
    end_work,
    move_task,
    start_work,
)

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
