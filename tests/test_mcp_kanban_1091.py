"""RED phase tests — MCP mutation tool adapter error-helper rollout (#1091).

AC Coverage (failing tests):
- AC6: create_task error mapping must call _map_kanban_error helper (not inline raise).
- AC6: edit_task error mapping must call _map_kanban_error helper (not inline raise).

Currently failing because:
- create_task: ``except KanbanError as exc: raise ToolError(exc.user_message) from exc``
- edit_task:   ``except KanbanError as exc: raise ToolError(exc.user_message) from exc``
Both must be refactored to call ``_map_kanban_error(exc)`` instead, matching the
read-tool pattern established in A-06 (#1090).

Already satisfied (no failing test possible):
- AC2+AC3: create_task forwards params / no status param — verified by #1087 suite.
- AC4:     edit_task forwards all 13 params — verified by #1087 suite.
- AC5:     edit_task has no status param — already true, confirmed by inspect.
"""

from __future__ import annotations

import inspect
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from owlbear_kanban.errors import KanbanError, ValidationError
from owlbear_kanban.models import SingleTaskResponse
from owlbear_mcp_kanban.server import AppContext, create_task, edit_task

# ---------------------------------------------------------------------------
# Board / context helpers
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
def app_ctx_mock(tmp_path: Path) -> tuple[AppContext, MagicMock]:
    """AppContext with a mock AgentView for mutation adapter tests."""
    from owlbear_kanban import KanbanEngine

    kanban_dir = _make_board(tmp_path)
    engine = KanbanEngine(kanban_dir)
    engine.create_task("Seed task", status="todo", priority="important")
    engine.list_tasks()  # populate id cache
    mock_av = MagicMock()
    mock_av.create_task.return_value = _make_single_task_response()
    mock_av.edit_task.return_value = _make_single_task_response()
    engine._agent_view = mock_av  # noqa: SLF001
    return AppContext(engine=engine, kanban_dir=kanban_dir), mock_av


# ---------------------------------------------------------------------------
# TestFromAC_MutationToolErrorHelper
# AC6: create_task and edit_task must route KanbanError through _map_kanban_error
# ---------------------------------------------------------------------------


class TestFromAC_MutationToolErrorHelper:
    """AC6: mutation adapters must call _map_kanban_error — not raise ToolError inline.

    The read tools (list_tasks, show_task, pick_tasks) already call _map_kanban_error.
    Task 1091 requires the same helper be used for create_task and edit_task so that
    error-format logic is centralized in one place (DRY).

    Failure mechanism: monkeypatch replaces _map_kanban_error with a tracking shim.
    If the adapter calls the helper, the shim is invoked and helper_calls grows to 1.
    If the adapter uses an inline raise, the shim is never invoked → helper_calls == 0
    → assertion fails.
    """

    @pytest.mark.asyncio
    async def test_create_task_calls_map_kanban_error_helper(
        self,
        app_ctx_mock: tuple[AppContext, MagicMock],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """create_task must delegate KanbanError handling to _map_kanban_error (AC6).

        Currently FAILS: create_task uses
          ``except KanbanError as exc: raise ToolError(exc.user_message) from exc``
        which bypasses _map_kanban_error entirely.

        Fix: replace with ``_map_kanban_error(exc)``.
        """
        from owlbear_mcp_kanban import server

        app_ctx, mock_av = app_ctx_mock
        mock_av.create_task.side_effect = ValidationError(
            code="ERR_INVALID_PRIORITY",
            user_message="priority 'bad' is not valid",
        )

        helper_calls: list[KanbanError] = []

        def tracking_helper(exc: KanbanError) -> None:
            helper_calls.append(exc)
            raise ToolError(exc.user_message) from exc

        monkeypatch.setattr(server, "_map_kanban_error", tracking_helper)
        ctx = _make_mcp_ctx(app_ctx)

        with pytest.raises(ToolError):
            await create_task(ctx, title="T", priority="bad")

        assert len(helper_calls) == 1, (
            "create_task must call _map_kanban_error(exc) for KanbanError (AC6). "
            "Inline 'raise ToolError(exc.user_message) from exc' does not use the "
            "shared helper — refactor to _map_kanban_error(exc)."
        )

    @pytest.mark.asyncio
    async def test_edit_task_calls_map_kanban_error_helper(
        self,
        app_ctx_mock: tuple[AppContext, MagicMock],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """edit_task must delegate KanbanError handling to _map_kanban_error (AC6).

        Currently FAILS: edit_task uses
          ``except KanbanError as exc: raise ToolError(exc.user_message) from exc``
        which bypasses _map_kanban_error entirely.

        Fix: replace with ``_map_kanban_error(exc)``.
        """
        from owlbear_mcp_kanban import server

        app_ctx, mock_av = app_ctx_mock
        mock_av.edit_task.side_effect = ValidationError(
            code="ERR_NO_OP",
            user_message="no fields would change",
        )

        helper_calls: list[KanbanError] = []

        def tracking_helper(exc: KanbanError) -> None:
            helper_calls.append(exc)
            raise ToolError(exc.user_message) from exc

        monkeypatch.setattr(server, "_map_kanban_error", tracking_helper)
        ctx = _make_mcp_ctx(app_ctx)

        with pytest.raises(ToolError):
            await edit_task(ctx, task_id="1", priority="critical")

        assert len(helper_calls) == 1, (
            "edit_task must call _map_kanban_error(exc) for KanbanError (AC6). "
            "Inline 'raise ToolError(exc.user_message) from exc' does not use the "
            "shared helper — refactor to _map_kanban_error(exc)."
        )


# ---------------------------------------------------------------------------
# TestFromAC_EditTaskSignature
# AC5: edit_task must NOT accept a status parameter
# ---------------------------------------------------------------------------


class TestFromAC_EditTaskSignature:
    """AC5: edit_task must not expose a 'status' parameter (engine controls status).

    Symmetric with test_create_task_has_no_status_parameter in the 1087 suite (AC3).
    Added in retry cycle — architect required executable inspect.signature proof.
    """

    def test_edit_task_has_no_status_parameter(self) -> None:
        """edit_task must not accept a status parameter — engine controls task status."""
        params = inspect.signature(edit_task).parameters
        assert "status" not in params, (
            "edit_task must not expose a 'status' parameter; "
            f"got params: {list(params)}"
        )
