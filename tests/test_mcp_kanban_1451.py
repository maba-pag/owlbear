"""Tests for task #1451: normalize MCP filters, annotations, and errors.

AC coverage:
  AC-3 (td:1): move_task and end_work share a single private archival-constraint helper.
  AC-5 (td:1): MCP errors for the 7 enumerated raw ToolError paths surface structured
               {code, message} JSON envelopes — no raw tracebacks or internal paths.

All tests FAIL in RED phase:
  - AC-3: _validate_archival_constraints does not exist in server.py yet.
  - AC-5: all 7 raw ToolError paths raise plain strings, not JSON envelopes.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from mcp.server.fastmcp.exceptions import ToolError

import owlbear_mcp_kanban.server as _server_mod
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

_CONFIG_YAML = """\
next_id: 1
"""


# ---------------------------------------------------------------------------
# Board + context helpers
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def app_ctx_todo_1451(tmp_path: Path) -> AppContext:
    """Real board with one todo task."""
    kanban_dir = _make_board(tmp_path)
    engine = KanbanEngine(kanban_dir)
    engine.create_task("Todo task", status="todo", priority="important")
    engine.list_tasks()
    return AppContext(engine=engine, kanban_dir=kanban_dir)


@pytest.fixture
def app_ctx_claimed_1451(tmp_path: Path) -> AppContext:
    """Real board with one claimed in-progress task."""
    kanban_dir = _make_board(tmp_path)
    engine = KanbanEngine(kanban_dir)
    engine.create_task("Claimed task", status="in-progress", priority="important")
    engine.list_tasks()
    engine.claim_task("1")
    return AppContext(engine=engine, kanban_dir=kanban_dir)


@pytest.fixture
def app_ctx_mock_view_1451(tmp_path: Path) -> tuple[AppContext, MagicMock]:
    """Real board with mocked AgentView — safe for invocation-tracking tests."""
    kanban_dir = _make_board(tmp_path)
    engine = KanbanEngine(kanban_dir)
    engine.create_task("Seed task", status="todo", priority="important")
    engine.list_tasks()

    mock_view = MagicMock()
    mock_view.move_task.return_value = _make_single_task_response(status="in-progress")
    mock_view.end_work.return_value = _make_single_task_response(status="done")
    engine._agent_view = mock_view  # noqa: SLF001
    return AppContext(engine=engine, kanban_dir=kanban_dir), mock_view


# ---------------------------------------------------------------------------
# AC-3: Shared archival-constraint validation helper
# ---------------------------------------------------------------------------


class TestFromAC_SharedArchivalHelper:
    """AC-3: move_task and end_work share one private archival-constraint validation helper.

    The helper centralises: archival-reason requirement, archival-ref constraints,
    completed-only archival check, and archival-field prohibition on non-archive moves.
    Both move_task and end_work must call this helper instead of duplicating
    validate_archival / ERR_ARCHIVAL_FIELDS_FORBIDDEN logic inline.
    """

    def test_shared_archival_validation_helper_exists_in_server_module(self) -> None:
        """Server module must expose _validate_archival_constraints as a module-level private.

        FAIL path: attribute does not exist → AttributeError / AssertionError.
        """
        assert hasattr(_server_mod, "_validate_archival_constraints"), (
            "Server module must have a private '_validate_archival_constraints' helper; "
            "both move_task and end_work must delegate archival constraint validation to it "
            "instead of duplicating the logic inline."
        )

    @pytest.mark.asyncio
    async def test_move_task_invokes_shared_archival_validation_helper(
        self,
        app_ctx_mock_view_1451: tuple[AppContext, MagicMock],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """move_task must call _validate_archival_constraints on every invocation.

        FAIL path: helper absent → AttributeError from monkeypatch; or helper present
        but not called → assertion failure.
        """
        app_ctx, _mock_view = app_ctx_mock_view_1451
        calls: list[object] = []

        def tracking_helper(*args: object, **kwargs: object) -> None:
            calls.append((args, kwargs))

        monkeypatch.setattr(_server_mod, "_validate_archival_constraints", tracking_helper)

        await move_task(_make_ctx(app_ctx), id="1", status="in-progress")

        assert len(calls) >= 1, (
            "move_task must call _validate_archival_constraints at least once; "
            f"got {len(calls)} calls — helper not invoked."
        )

    @pytest.mark.asyncio
    async def test_end_work_invokes_shared_archival_validation_helper(
        self,
        app_ctx_mock_view_1451: tuple[AppContext, MagicMock],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """end_work must call _validate_archival_constraints on every invocation.

        FAIL path: helper absent → AttributeError from monkeypatch; or helper present
        but not called → assertion failure.
        """
        app_ctx, _mock_view = app_ctx_mock_view_1451
        calls: list[object] = []

        def tracking_helper(*args: object, **kwargs: object) -> None:
            calls.append((args, kwargs))

        monkeypatch.setattr(_server_mod, "_validate_archival_constraints", tracking_helper)

        await end_work(
            _make_ctx(app_ctx),
            id="1",
            outcome="success",
            note="done",
        )

        assert len(calls) >= 1, (
            "end_work must call _validate_archival_constraints at least once; "
            f"got {len(calls)} calls — helper not invoked."
        )


# ---------------------------------------------------------------------------
# AC-5: Structured error envelopes for all 7 enumerated raw ToolError paths
# ---------------------------------------------------------------------------


class TestFromAC_StructuredErrors:
    """AC-5: MCP errors surface {code, message} JSON envelopes — no raw strings.

    Seven raw ToolError paths are enumerated in the Architecture Review:
      1. _show_validated    FileNotFoundError  → ERR_NOT_FOUND
      2. create_dr          request_type guard → ERR_PARAM_VALIDATION
      3. move_task          missing status      → ERR_PARAM_VALIDATION
      4. start_work         ValueError          → ERR_PARAM_VALIDATION
      5. start_work         FileNotFoundError   → ERR_NOT_FOUND
      6. end_work           ValueError          → ERR_PARAM_VALIDATION
      7. end_work           FileNotFoundError   → ERR_NOT_FOUND
      8. list_tasks         PydanticValidationError → ERR_PARAM_VALIDATION
      9. pick_tasks         PydanticValidationError → ERR_PARAM_VALIDATION
    """

    # -- Path 1: _show_validated FileNotFoundError → ERR_NOT_FOUND --

    @pytest.mark.asyncio
    async def test_show_validated_file_not_found_raises_json_envelope(
        self, tmp_path: Path
    ) -> None:
        """_show_validated FileNotFoundError must raise ToolError with JSON {code, message}.

        FAIL path: current code raises ToolError(str(exc)) — plain string, not JSON.
        """
        kanban_dir = _make_board(tmp_path)
        engine = KanbanEngine(kanban_dir)
        engine.show_task = MagicMock(  # type: ignore[method-assign]
            side_effect=FileNotFoundError("no such task file")
        )
        app_ctx = AppContext(engine=engine, kanban_dir=kanban_dir)
        with pytest.raises(ToolError) as exc_info:
            await _show_validated(app_ctx, 99)
        payload = json.loads(str(exc_info.value))
        assert "code" in payload
        assert "message" in payload

    @pytest.mark.asyncio
    async def test_show_validated_file_not_found_has_not_found_code(
        self, tmp_path: Path
    ) -> None:
        """_show_validated FileNotFoundError must use ERR_NOT_FOUND code.

        FAIL path: raw string ToolError fails json.loads → JSONDecodeError.
        """
        kanban_dir = _make_board(tmp_path)
        engine = KanbanEngine(kanban_dir)
        engine.show_task = MagicMock(  # type: ignore[method-assign]
            side_effect=FileNotFoundError("no such task file")
        )
        app_ctx = AppContext(engine=engine, kanban_dir=kanban_dir)
        with pytest.raises(ToolError) as exc_info:
            await _show_validated(app_ctx, 99)
        payload = json.loads(str(exc_info.value))
        assert payload["code"] == "ERR_NOT_FOUND"

    # -- Path 2: create_dr request_type guard → ERR_PARAM_VALIDATION --

    @pytest.mark.asyncio
    async def test_create_dr_invalid_request_type_raises_json_envelope(
        self, app_ctx_todo_1451: AppContext
    ) -> None:
        """create_dr invalid request_type must raise ToolError with JSON {code, message}.

        FAIL path: current code raises ToolError('request_type must be one of…') — plain string.
        """
        with pytest.raises(ToolError) as exc_info:
            await create_dr(
                _make_ctx(app_ctx_todo_1451),
                task_id="1",
                agent="builder",
                request_type="invalid",
                body="body",
            )
        payload = json.loads(str(exc_info.value))
        assert "code" in payload
        assert "message" in payload

    @pytest.mark.asyncio
    async def test_create_dr_invalid_request_type_has_param_validation_code(
        self, app_ctx_todo_1451: AppContext
    ) -> None:
        """create_dr invalid request_type must use ERR_PARAM_VALIDATION code.

        FAIL path: raw string ToolError fails json.loads → JSONDecodeError.
        """
        with pytest.raises(ToolError) as exc_info:
            await create_dr(
                _make_ctx(app_ctx_todo_1451),
                task_id="1",
                agent="builder",
                request_type="invalid",
                body="body",
            )
        payload = json.loads(str(exc_info.value))
        assert payload["code"] == "ERR_PARAM_VALIDATION"

    # -- Path 3: move_task missing status → ERR_PARAM_VALIDATION --

    @pytest.mark.asyncio
    async def test_move_task_missing_status_raises_json_envelope(
        self, app_ctx_todo_1451: AppContext
    ) -> None:
        """move_task with status=None must raise ToolError with JSON {code, message}.

        FAIL path: current code raises ToolError('status is required') — plain string.
        """
        with pytest.raises(ToolError) as exc_info:
            await move_task(_make_ctx(app_ctx_todo_1451), id="1")
        payload = json.loads(str(exc_info.value))
        assert "code" in payload
        assert "message" in payload

    @pytest.mark.asyncio
    async def test_move_task_missing_status_has_param_validation_code(
        self, app_ctx_todo_1451: AppContext
    ) -> None:
        """move_task with status=None must use ERR_PARAM_VALIDATION code.

        FAIL path: raw string ToolError fails json.loads → JSONDecodeError.
        """
        with pytest.raises(ToolError) as exc_info:
            await move_task(_make_ctx(app_ctx_todo_1451), id="1")
        payload = json.loads(str(exc_info.value))
        assert payload["code"] == "ERR_PARAM_VALIDATION"

    # -- Path 4: start_work ValueError → ERR_PARAM_VALIDATION --

    @pytest.mark.asyncio
    async def test_start_work_value_error_raises_json_envelope(
        self, app_ctx_todo_1451: AppContext
    ) -> None:
        """start_work ValueError must raise ToolError with JSON {code, message}.

        FAIL path: current code raises ToolError(str(exc)) — plain string.
        """
        mock_view = MagicMock()
        mock_view.start_work.side_effect = ValueError("bad task state")
        app_ctx_todo_1451.engine._agent_view = mock_view  # noqa: SLF001
        with pytest.raises(ToolError) as exc_info:
            await start_work(_make_ctx(app_ctx_todo_1451), id="1")
        payload = json.loads(str(exc_info.value))
        assert "code" in payload
        assert "message" in payload

    @pytest.mark.asyncio
    async def test_start_work_value_error_has_param_validation_code(
        self, app_ctx_todo_1451: AppContext
    ) -> None:
        """start_work ValueError must use ERR_PARAM_VALIDATION code.

        FAIL path: raw string ToolError fails json.loads → JSONDecodeError.
        """
        mock_view = MagicMock()
        mock_view.start_work.side_effect = ValueError("bad task state")
        app_ctx_todo_1451.engine._agent_view = mock_view  # noqa: SLF001
        with pytest.raises(ToolError) as exc_info:
            await start_work(_make_ctx(app_ctx_todo_1451), id="1")
        payload = json.loads(str(exc_info.value))
        assert payload["code"] == "ERR_PARAM_VALIDATION"

    # -- Path 5: start_work FileNotFoundError → ERR_NOT_FOUND --

    @pytest.mark.asyncio
    async def test_start_work_file_not_found_raises_json_envelope(
        self, app_ctx_todo_1451: AppContext
    ) -> None:
        """start_work FileNotFoundError must raise ToolError with JSON {code, message}.

        FAIL path: current code raises ToolError(str(exc)) — plain string.
        """
        mock_view = MagicMock()
        mock_view.start_work.side_effect = FileNotFoundError("task file missing")
        app_ctx_todo_1451.engine._agent_view = mock_view  # noqa: SLF001
        with pytest.raises(ToolError) as exc_info:
            await start_work(_make_ctx(app_ctx_todo_1451), id="1")
        payload = json.loads(str(exc_info.value))
        assert "code" in payload
        assert "message" in payload

    @pytest.mark.asyncio
    async def test_start_work_file_not_found_has_not_found_code(
        self, app_ctx_todo_1451: AppContext
    ) -> None:
        """start_work FileNotFoundError must use ERR_NOT_FOUND code.

        FAIL path: raw string ToolError fails json.loads → JSONDecodeError.
        """
        mock_view = MagicMock()
        mock_view.start_work.side_effect = FileNotFoundError("task file missing")
        app_ctx_todo_1451.engine._agent_view = mock_view  # noqa: SLF001
        with pytest.raises(ToolError) as exc_info:
            await start_work(_make_ctx(app_ctx_todo_1451), id="1")
        payload = json.loads(str(exc_info.value))
        assert payload["code"] == "ERR_NOT_FOUND"

    # -- Path 6: end_work ValueError → ERR_PARAM_VALIDATION --

    @pytest.mark.asyncio
    async def test_end_work_value_error_raises_json_envelope(
        self, app_ctx_claimed_1451: AppContext
    ) -> None:
        """end_work ValueError must raise ToolError with JSON {code, message}.

        FAIL path: current code raises ToolError(str(exc)) — plain string.
        """
        mock_view = MagicMock()
        mock_view.end_work.side_effect = ValueError("invalid outcome state")
        app_ctx_claimed_1451.engine._agent_view = mock_view  # noqa: SLF001
        with pytest.raises(ToolError) as exc_info:
            await end_work(
                _make_ctx(app_ctx_claimed_1451), id="1", outcome="success", note="done"
            )
        payload = json.loads(str(exc_info.value))
        assert "code" in payload
        assert "message" in payload

    @pytest.mark.asyncio
    async def test_end_work_value_error_has_param_validation_code(
        self, app_ctx_claimed_1451: AppContext
    ) -> None:
        """end_work ValueError must use ERR_PARAM_VALIDATION code.

        FAIL path: raw string ToolError fails json.loads → JSONDecodeError.
        """
        mock_view = MagicMock()
        mock_view.end_work.side_effect = ValueError("invalid outcome state")
        app_ctx_claimed_1451.engine._agent_view = mock_view  # noqa: SLF001
        with pytest.raises(ToolError) as exc_info:
            await end_work(
                _make_ctx(app_ctx_claimed_1451), id="1", outcome="success", note="done"
            )
        payload = json.loads(str(exc_info.value))
        assert payload["code"] == "ERR_PARAM_VALIDATION"

    # -- Path 7: end_work FileNotFoundError → ERR_NOT_FOUND --

    @pytest.mark.asyncio
    async def test_end_work_file_not_found_raises_json_envelope(
        self, app_ctx_claimed_1451: AppContext
    ) -> None:
        """end_work FileNotFoundError must raise ToolError with JSON {code, message}.

        FAIL path: current code raises ToolError(str(exc)) — plain string.
        """
        mock_view = MagicMock()
        mock_view.end_work.side_effect = FileNotFoundError("task file missing")
        app_ctx_claimed_1451.engine._agent_view = mock_view  # noqa: SLF001
        with pytest.raises(ToolError) as exc_info:
            await end_work(
                _make_ctx(app_ctx_claimed_1451), id="1", outcome="success", note="done"
            )
        payload = json.loads(str(exc_info.value))
        assert "code" in payload
        assert "message" in payload

    @pytest.mark.asyncio
    async def test_end_work_file_not_found_has_not_found_code(
        self, app_ctx_claimed_1451: AppContext
    ) -> None:
        """end_work FileNotFoundError must use ERR_NOT_FOUND code.

        FAIL path: raw string ToolError fails json.loads → JSONDecodeError.
        """
        mock_view = MagicMock()
        mock_view.end_work.side_effect = FileNotFoundError("task file missing")
        app_ctx_claimed_1451.engine._agent_view = mock_view  # noqa: SLF001
        with pytest.raises(ToolError) as exc_info:
            await end_work(
                _make_ctx(app_ctx_claimed_1451), id="1", outcome="success", note="done"
            )
        payload = json.loads(str(exc_info.value))
        assert payload["code"] == "ERR_NOT_FOUND"

    # -- Path 8: list_tasks PydanticValidationError → ERR_PARAM_VALIDATION --

    @pytest.mark.asyncio
    async def test_list_tasks_pydantic_validation_error_raises_json_envelope(
        self, app_ctx_todo_1451: AppContext
    ) -> None:
        """list_tasks PydanticValidationError must raise ToolError with JSON {code, message}.

        ids combined with status triggers the model validator → PydanticValidationError.
        FAIL path: current code raises ToolError(str(exc)) — plain string.
        """
        with pytest.raises(ToolError) as exc_info:
            await list_tasks(_make_ctx(app_ctx_todo_1451), ids=[1], status="todo")
        payload = json.loads(str(exc_info.value))
        assert "code" in payload
        assert "message" in payload

    @pytest.mark.asyncio
    async def test_list_tasks_pydantic_validation_error_has_param_validation_code(
        self, app_ctx_todo_1451: AppContext
    ) -> None:
        """list_tasks PydanticValidationError must use ERR_PARAM_VALIDATION code.

        FAIL path: raw string ToolError fails json.loads → JSONDecodeError.
        """
        with pytest.raises(ToolError) as exc_info:
            await list_tasks(_make_ctx(app_ctx_todo_1451), ids=[1], status="todo")
        payload = json.loads(str(exc_info.value))
        assert payload["code"] == "ERR_PARAM_VALIDATION"

    # -- Path 9: pick_tasks PydanticValidationError → ERR_PARAM_VALIDATION --

    @pytest.mark.asyncio
    async def test_pick_tasks_pydantic_validation_error_raises_json_envelope(
        self, app_ctx_todo_1451: AppContext
    ) -> None:
        """pick_tasks PydanticValidationError must raise ToolError with JSON {code, message}.

        max_waves as a non-integer string triggers Pydantic int coercion failure.
        FAIL path: current code raises ToolError(str(exc)) — plain string.
        """
        with pytest.raises(ToolError) as exc_info:
            await pick_tasks(
                _make_ctx(app_ctx_todo_1451), max_waves="not-a-number"  # type: ignore[arg-type]
            )
        payload = json.loads(str(exc_info.value))
        assert "code" in payload
        assert "message" in payload

    @pytest.mark.asyncio
    async def test_pick_tasks_pydantic_validation_error_has_param_validation_code(
        self, app_ctx_todo_1451: AppContext
    ) -> None:
        """pick_tasks PydanticValidationError must use ERR_PARAM_VALIDATION code.

        FAIL path: raw string ToolError fails json.loads → JSONDecodeError.
        """
        with pytest.raises(ToolError) as exc_info:
            await pick_tasks(
                _make_ctx(app_ctx_todo_1451), max_waves="not-a-number"  # type: ignore[arg-type]
            )
        payload = json.loads(str(exc_info.value))
        assert payload["code"] == "ERR_PARAM_VALIDATION"
