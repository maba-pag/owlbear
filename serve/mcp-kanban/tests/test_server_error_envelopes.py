"""Durable MCP server regression tests for archival validation and error envelopes."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from mcp.server.fastmcp.exceptions import ToolError

import owlbear_mcp_kanban.server as server_mod
from owlbear_kanban import KanbanEngine
from owlbear_kanban.models import SingleTaskResponse
from owlbear_mcp_kanban.server import (
    AppContext,
    _show_validated,
    create_dr,
    end_work,
    list_tasks,
    move_task,
    pick_tasks,
    start_work,
)

_CONFIG_YAML = "next_id: 1\n"


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


@pytest.fixture
def app_ctx_mock_view(tmp_path: Path) -> tuple[AppContext, MagicMock]:
    kanban_dir = _make_board(tmp_path)
    engine = KanbanEngine(kanban_dir)
    engine.create_task("Seed task", status="todo", priority="important")
    engine.list_tasks()

    mock_view = MagicMock()
    mock_view.move_task.return_value = _make_single_task_response(status="in-progress")
    mock_view.end_work.return_value = _make_single_task_response(status="done")
    engine._agent_view = mock_view  # noqa: SLF001
    return AppContext(engine=engine, kanban_dir=kanban_dir), mock_view


class TestArchivalConstraintHelper:
    def test_shared_archival_validation_helper_exists_in_server_module(self) -> None:
        assert hasattr(server_mod, "_validate_archival_constraints")

    @pytest.mark.asyncio
    async def test_move_task_invokes_shared_archival_validation_helper(
        self,
        app_ctx_mock_view: tuple[AppContext, MagicMock],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        app_ctx, _mock_view = app_ctx_mock_view
        calls: list[object] = []

        def tracking_helper(*args: object, **kwargs: object) -> None:
            calls.append((args, kwargs))

        monkeypatch.setattr(server_mod, "_validate_archival_constraints", tracking_helper)

        await move_task(_make_ctx(app_ctx), id="1", status="in-progress")

        assert len(calls) >= 1

    @pytest.mark.asyncio
    async def test_end_work_invokes_shared_archival_validation_helper(
        self,
        app_ctx_mock_view: tuple[AppContext, MagicMock],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        app_ctx, _mock_view = app_ctx_mock_view
        calls: list[object] = []

        def tracking_helper(*args: object, **kwargs: object) -> None:
            calls.append((args, kwargs))

        monkeypatch.setattr(server_mod, "_validate_archival_constraints", tracking_helper)

        await end_work(
            _make_ctx(app_ctx),
            id="1",
            outcome="success",
            note="done",
        )

        assert len(calls) >= 1


class TestStructuredErrorEnvelopes:
    @pytest.mark.asyncio
    async def test_show_validated_file_not_found_raises_json_envelope(self, tmp_path: Path) -> None:
        kanban_dir = _make_board(tmp_path)
        engine = KanbanEngine(kanban_dir)
        engine.show_task = MagicMock(side_effect=FileNotFoundError("no such task file"))  # type: ignore[method-assign]
        app_ctx = AppContext(engine=engine, kanban_dir=kanban_dir)
        with pytest.raises(ToolError) as exc_info:
            await _show_validated(app_ctx, 99)
        payload = json.loads(str(exc_info.value))
        assert "code" in payload
        assert "message" in payload

    @pytest.mark.asyncio
    async def test_show_validated_file_not_found_has_not_found_code(self, tmp_path: Path) -> None:
        kanban_dir = _make_board(tmp_path)
        engine = KanbanEngine(kanban_dir)
        engine.show_task = MagicMock(side_effect=FileNotFoundError("no such task file"))  # type: ignore[method-assign]
        app_ctx = AppContext(engine=engine, kanban_dir=kanban_dir)
        with pytest.raises(ToolError) as exc_info:
            await _show_validated(app_ctx, 99)
        payload = json.loads(str(exc_info.value))
        assert payload["code"] == "ERR_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_create_dr_invalid_request_type_raises_json_envelope(self, app_ctx_todo: AppContext) -> None:
        with pytest.raises(ToolError) as exc_info:
            await create_dr(
                _make_ctx(app_ctx_todo),
                task_id="1",
                agent="builder",
                request_type="invalid",
                body="body",
            )
        payload = json.loads(str(exc_info.value))
        assert "code" in payload
        assert "message" in payload

    @pytest.mark.asyncio
    async def test_create_dr_invalid_request_type_has_param_validation_code(self, app_ctx_todo: AppContext) -> None:
        with pytest.raises(ToolError) as exc_info:
            await create_dr(
                _make_ctx(app_ctx_todo),
                task_id="1",
                agent="builder",
                request_type="invalid",
                body="body",
            )
        payload = json.loads(str(exc_info.value))
        assert payload["code"] == "ERR_PARAM_VALIDATION"

    @pytest.mark.asyncio
    async def test_move_task_missing_status_raises_json_envelope(self, app_ctx_todo: AppContext) -> None:
        with pytest.raises(ToolError) as exc_info:
            await move_task(_make_ctx(app_ctx_todo), id="1")
        payload = json.loads(str(exc_info.value))
        assert "code" in payload
        assert "message" in payload

    @pytest.mark.asyncio
    async def test_move_task_missing_status_has_param_validation_code(self, app_ctx_todo: AppContext) -> None:
        with pytest.raises(ToolError) as exc_info:
            await move_task(_make_ctx(app_ctx_todo), id="1")
        payload = json.loads(str(exc_info.value))
        assert payload["code"] == "ERR_PARAM_VALIDATION"

    @pytest.mark.asyncio
    async def test_start_work_value_error_raises_json_envelope(self, app_ctx_todo: AppContext) -> None:
        mock_view = MagicMock()
        mock_view.start_work.side_effect = ValueError("bad task state")
        app_ctx_todo.engine._agent_view = mock_view  # noqa: SLF001
        with pytest.raises(ToolError) as exc_info:
            await start_work(_make_ctx(app_ctx_todo), id="1")
        payload = json.loads(str(exc_info.value))
        assert "code" in payload
        assert "message" in payload

    @pytest.mark.asyncio
    async def test_start_work_value_error_has_param_validation_code(self, app_ctx_todo: AppContext) -> None:
        mock_view = MagicMock()
        mock_view.start_work.side_effect = ValueError("bad task state")
        app_ctx_todo.engine._agent_view = mock_view  # noqa: SLF001
        with pytest.raises(ToolError) as exc_info:
            await start_work(_make_ctx(app_ctx_todo), id="1")
        payload = json.loads(str(exc_info.value))
        assert payload["code"] == "ERR_PARAM_VALIDATION"

    @pytest.mark.asyncio
    async def test_start_work_file_not_found_raises_json_envelope(self, app_ctx_todo: AppContext) -> None:
        mock_view = MagicMock()
        mock_view.start_work.side_effect = FileNotFoundError("task file missing")
        app_ctx_todo.engine._agent_view = mock_view  # noqa: SLF001
        with pytest.raises(ToolError) as exc_info:
            await start_work(_make_ctx(app_ctx_todo), id="1")
        payload = json.loads(str(exc_info.value))
        assert "code" in payload
        assert "message" in payload

    @pytest.mark.asyncio
    async def test_start_work_file_not_found_has_not_found_code(self, app_ctx_todo: AppContext) -> None:
        mock_view = MagicMock()
        mock_view.start_work.side_effect = FileNotFoundError("task file missing")
        app_ctx_todo.engine._agent_view = mock_view  # noqa: SLF001
        with pytest.raises(ToolError) as exc_info:
            await start_work(_make_ctx(app_ctx_todo), id="1")
        payload = json.loads(str(exc_info.value))
        assert payload["code"] == "ERR_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_end_work_value_error_raises_json_envelope(self, app_ctx_claimed: AppContext) -> None:
        mock_view = MagicMock()
        mock_view.end_work.side_effect = ValueError("invalid outcome state")
        app_ctx_claimed.engine._agent_view = mock_view  # noqa: SLF001
        with pytest.raises(ToolError) as exc_info:
            await end_work(_make_ctx(app_ctx_claimed), id="1", outcome="success", note="done")
        payload = json.loads(str(exc_info.value))
        assert "code" in payload
        assert "message" in payload

    @pytest.mark.asyncio
    async def test_end_work_value_error_has_param_validation_code(self, app_ctx_claimed: AppContext) -> None:
        mock_view = MagicMock()
        mock_view.end_work.side_effect = ValueError("invalid outcome state")
        app_ctx_claimed.engine._agent_view = mock_view  # noqa: SLF001
        with pytest.raises(ToolError) as exc_info:
            await end_work(_make_ctx(app_ctx_claimed), id="1", outcome="success", note="done")
        payload = json.loads(str(exc_info.value))
        assert payload["code"] == "ERR_PARAM_VALIDATION"

    @pytest.mark.asyncio
    async def test_end_work_file_not_found_raises_json_envelope(self, app_ctx_claimed: AppContext) -> None:
        mock_view = MagicMock()
        mock_view.end_work.side_effect = FileNotFoundError("task file missing")
        app_ctx_claimed.engine._agent_view = mock_view  # noqa: SLF001
        with pytest.raises(ToolError) as exc_info:
            await end_work(_make_ctx(app_ctx_claimed), id="1", outcome="success", note="done")
        payload = json.loads(str(exc_info.value))
        assert "code" in payload
        assert "message" in payload

    @pytest.mark.asyncio
    async def test_end_work_file_not_found_has_not_found_code(self, app_ctx_claimed: AppContext) -> None:
        mock_view = MagicMock()
        mock_view.end_work.side_effect = FileNotFoundError("task file missing")
        app_ctx_claimed.engine._agent_view = mock_view  # noqa: SLF001
        with pytest.raises(ToolError) as exc_info:
            await end_work(_make_ctx(app_ctx_claimed), id="1", outcome="success", note="done")
        payload = json.loads(str(exc_info.value))
        assert payload["code"] == "ERR_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_list_tasks_pydantic_validation_error_raises_json_envelope(self, app_ctx_todo: AppContext) -> None:
        with pytest.raises(ToolError) as exc_info:
            await list_tasks(_make_ctx(app_ctx_todo), ids=[1], status="todo")
        payload = json.loads(str(exc_info.value))
        assert "code" in payload
        assert "message" in payload

    @pytest.mark.asyncio
    async def test_list_tasks_pydantic_validation_error_has_param_validation_code(
        self, app_ctx_todo: AppContext
    ) -> None:
        with pytest.raises(ToolError) as exc_info:
            await list_tasks(_make_ctx(app_ctx_todo), ids=[1], status="todo")
        payload = json.loads(str(exc_info.value))
        assert payload["code"] == "ERR_PARAM_VALIDATION"

    @pytest.mark.asyncio
    async def test_pick_tasks_pydantic_validation_error_raises_json_envelope(self, app_ctx_todo: AppContext) -> None:
        with pytest.raises(ToolError) as exc_info:
            await pick_tasks(
                _make_ctx(app_ctx_todo),
                max_waves="not-a-number",  # type: ignore[arg-type]
            )
        payload = json.loads(str(exc_info.value))
        assert "code" in payload
        assert "message" in payload

    @pytest.mark.asyncio
    async def test_pick_tasks_pydantic_validation_error_has_param_validation_code(
        self, app_ctx_todo: AppContext
    ) -> None:
        with pytest.raises(ToolError) as exc_info:
            await pick_tasks(
                _make_ctx(app_ctx_todo),
                max_waves="not-a-number",  # type: ignore[arg-type]
            )
        payload = json.loads(str(exc_info.value))
        assert payload["code"] == "ERR_PARAM_VALIDATION"

    @pytest.mark.asyncio
    async def test_show_validated_path_like_not_found_scrubs_internal_path(self, tmp_path: Path) -> None:
        kanban_dir = _make_board(tmp_path)
        engine = KanbanEngine(kanban_dir)
        engine.show_task = MagicMock(side_effect=FileNotFoundError("/var/data/kanban/tasks/99.md"))  # type: ignore[method-assign]
        app_ctx = AppContext(engine=engine, kanban_dir=kanban_dir)
        with pytest.raises(ToolError) as exc_info:
            await _show_validated(app_ctx, 99)
        payload = json.loads(str(exc_info.value))
        assert payload["message"] == "Task '99' not found"
        assert "/var/" not in payload["message"]
