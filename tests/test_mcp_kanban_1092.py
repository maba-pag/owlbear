"""RED phase tests — MCP lifecycle tool adapters: error routing + no business logic (#1092).

AC Coverage (failing tests):
- AC6: move_task error mapping must call _map_kanban_error helper (not inline raise).
- AC6: start_work error mapping must call _map_kanban_error helper (not inline raise).
- AC6: end_work error mapping must call _map_kanban_error helper (not inline raise).
- AC7: move_task adapter must contain no local archival_reason validation.
       All validation belongs in the engine / AgentView.

Currently failing because:
- move_task: _invoke_view_move_task uses
    ``except KanbanError as exc: raise ToolError(exc.user_message) from exc``
  which bypasses _map_kanban_error entirely.
- start_work: same inline raise pattern in the ``_agent_view_for`` path.
- end_work: same inline raise pattern in the ``_agent_view_for`` path.
- move_task source: contains
    ``"archival_reason is required when status='archived'"``
  which is business logic that belongs in the engine (AC7 violation).

Already satisfied (no failing tests possible for these):
- AC2: move_task forwards (id, status, archival_reason, archival_refs) to view — already done
       via _invoke_view_move_task when view is available.
- AC3: start_work forwards int(task_id) to view.start_work — already done.
- AC4: end_work forwards all 7 params to view.end_work — already done.
- AC5: forbidden-parameter matrix enforced by engine — no local checks in end_work adapter.
- AC1: RED tests from A-05 (#1088) — 1088 archived; no test file to evaluate.
"""

from __future__ import annotations

import inspect
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from owlbear_kanban.errors import KanbanError, ValidationError
from owlbear_kanban.models import SingleTaskResponse
from owlbear_mcp_kanban.server import AppContext, end_work, move_task, start_work

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
        "status": "review",
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
    """AppContext with a mock AgentView for lifecycle adapter tests."""
    from owlbear_kanban import KanbanEngine

    kanban_dir = _make_board(tmp_path)
    engine = KanbanEngine(kanban_dir)
    engine.create_task("Seed task", status="todo", priority="important")
    engine.list_tasks()
    mock_av = MagicMock()
    mock_av.move_task.return_value = _make_single_task_response()
    mock_av.start_work.return_value = _make_single_task_response()
    mock_av.end_work.return_value = _make_single_task_response()
    engine._agent_view = mock_av  # noqa: SLF001
    return AppContext(engine=engine, kanban_dir=kanban_dir), mock_av


# ---------------------------------------------------------------------------
# TestFromAC_LifecycleToolAdapters
# AC6: all three lifecycle adapters must route KanbanError via _map_kanban_error
# AC7: move_task adapter must contain no local archival validation logic
# ---------------------------------------------------------------------------


class TestFromAC_LifecycleToolAdapters:
    """Lifecycle MCP tool adapters must use _map_kanban_error and contain no business logic.

    Failure mechanism (AC6 tests): monkeypatch replaces _map_kanban_error with a tracking
    shim.  If the adapter calls the helper, the shim is invoked and helper_calls grows to 1.
    If the adapter uses an inline raise, the shim is never invoked → helper_calls == 0
    → assertion fails.

    Failure mechanism (AC7 test): source inspection — the local archival validation string
    must be absent from server.py after the builder's clean-up.  Currently present → FAIL.
    """

    @pytest.mark.asyncio
    async def test_move_task_kanban_error_routed_via_helper(
        self,
        app_ctx_mock: tuple[AppContext, MagicMock],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC6: move_task must delegate KanbanError handling to _map_kanban_error.

        Currently FAILS: _invoke_view_move_task uses
          ``except KanbanError as exc: raise ToolError(exc.user_message) from exc``
        which bypasses _map_kanban_error entirely.

        Fix: replace inline raise with ``_map_kanban_error(exc)``.
        """
        import owlbear_mcp_kanban.server as _server_mod

        app_ctx, mock_av = app_ctx_mock
        mock_av.move_task.side_effect = ValidationError(
            code="ERR_INVALID_STATUS",
            user_message="status 'bad' is not valid",
        )

        helper_calls: list[KanbanError] = []

        def tracking_helper(exc: KanbanError) -> None:
            helper_calls.append(exc)
            raise ToolError(exc.user_message) from exc

        monkeypatch.setattr(_server_mod, "_map_kanban_error", tracking_helper)
        ctx = _make_mcp_ctx(app_ctx)

        with pytest.raises(ToolError):
            await move_task(ctx, id="1", status="review")

        assert len(helper_calls) == 1, (
            "move_task must call _map_kanban_error(exc) for KanbanError (AC6). "
            "Inline 'raise ToolError(exc.user_message) from exc' in "
            "_invoke_view_move_task does not use the shared helper."
        )

    @pytest.mark.asyncio
    async def test_start_work_kanban_error_routed_via_helper(
        self,
        app_ctx_mock: tuple[AppContext, MagicMock],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC6: start_work must delegate KanbanError handling to _map_kanban_error.

        Currently FAILS: the _agent_view_for path in start_work uses
          ``except KanbanError as exc: raise ToolError(exc.user_message) from exc``
        which bypasses _map_kanban_error entirely.

        Fix: replace inline raise with ``_map_kanban_error(exc)``.
        """
        import owlbear_mcp_kanban.server as _server_mod

        app_ctx, mock_av = app_ctx_mock
        mock_av.start_work.side_effect = ValidationError(
            code="ERR_ALREADY_CLAIMED",
            user_message="Task '1' is already claimed by another agent",
        )

        helper_calls: list[KanbanError] = []

        def tracking_helper(exc: KanbanError) -> None:
            helper_calls.append(exc)
            raise ToolError(exc.user_message) from exc

        monkeypatch.setattr(_server_mod, "_map_kanban_error", tracking_helper)
        ctx = _make_mcp_ctx(app_ctx)

        with pytest.raises(ToolError):
            await start_work(ctx, id="1")

        assert len(helper_calls) == 1, (
            "start_work must call _map_kanban_error(exc) for KanbanError (AC6). "
            "Inline 'raise ToolError(exc.user_message) from exc' in the "
            "_agent_view_for path does not use the shared helper."
        )

    @pytest.mark.asyncio
    async def test_end_work_kanban_error_routed_via_helper(
        self,
        app_ctx_mock: tuple[AppContext, MagicMock],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC6: end_work must delegate KanbanError handling to _map_kanban_error.

        Currently FAILS: the _agent_view_for path in end_work uses
          ``except KanbanError as exc: raise ToolError(exc.user_message) from exc``
        which bypasses _map_kanban_error entirely.

        Fix: replace inline raise with ``_map_kanban_error(exc)``.
        """
        import owlbear_mcp_kanban.server as _server_mod

        app_ctx, mock_av = app_ctx_mock
        mock_av.end_work.side_effect = ValidationError(
            code="ERR_BLOCK_REASON_REQUIRED",
            user_message="block_reason is required when outcome='block'",
        )

        helper_calls: list[KanbanError] = []

        def tracking_helper(exc: KanbanError) -> None:
            helper_calls.append(exc)
            raise ToolError(exc.user_message) from exc

        monkeypatch.setattr(_server_mod, "_map_kanban_error", tracking_helper)
        ctx = _make_mcp_ctx(app_ctx)

        with pytest.raises(ToolError):
            await end_work(
                ctx,
                id="1",
                outcome="block",
                note="blocked",
                block_reason=None,
            )

        assert len(helper_calls) == 1, (
            "end_work must call _map_kanban_error(exc) for KanbanError (AC6). "
            "Inline 'raise ToolError(exc.user_message) from exc' in the "
            "_agent_view_for path does not use the shared helper."
        )

    def test_move_task_no_local_archival_validation_in_source(self) -> None:
        """AC7: move_task adapter must contain no local archival_reason validation.

        Currently FAILS: server.py contains
          ``"archival_reason is required when status='archived'"``
        which is business logic that belongs in the engine/AgentView, not in the adapter.

        Fix: remove the local archival_reason and archival_refs guard blocks from the
        move_task handler.  All validation must be delegated to the engine.
        """
        import owlbear_mcp_kanban.server as _server_mod

        source = inspect.getsource(_server_mod)
        assert "archival_reason is required when status" not in source, (
            "AC7: move_task adapter must not contain local archival_reason validation. "
            "Found 'archival_reason is required when status' in server.py — "
            "this guard belongs in the engine, not the adapter."
        )

    def test_end_work_adapter_no_param_normalization_in_source(self) -> None:
        """AC7 (end_work): adapter must not normalize note or block_reason before forwarding.

        Guard test (loop-breaker closure, 3rd review cycle): implementation is currently
        correct.  This test extends AC7 source-inspection coverage from move_task to
        end_work per architecture review builder guidance.

        Would FAIL if normalization patterns like ``note or ""`` or
        ``block_reason or ""`` were reintroduced into the end_work adapter.
        Currently PASSES because those patterns are absent.
        """
        source = inspect.getsource(end_work)
        assert 'note or ""' not in source, (
            "AC7: end_work adapter must not normalize note before forwarding. "
            "Found 'note or \"\"' in end_work — adapter must forward note verbatim."
        )
        assert "block_reason or" not in source, (
            "AC7: end_work adapter must not normalize block_reason before forwarding."
        )

    def test_end_work_adapter_no_tag_mutation_in_source(self) -> None:
        """AC7 (end_work): adapter must not mutate block:user tag after engine call.

        Guard test (loop-breaker closure, 3rd review cycle): the block:user cleanup
        was moved to engine._apply_outcome.  This test ensures the adapter-side
        tag-mutation path (``edit_task(remove_tags=["block:user"])``) is not
        reintroduced in the end_work adapter.

        Currently PASSES because block:user references are absent from end_work.
        Would FAIL if adapter-owned tag mutation returned.
        """
        source = inspect.getsource(end_work)
        assert "block:user" not in source, (
            "AC7: end_work adapter must not reference 'block:user' tag. "
            "Tag lifecycle belongs in engine._apply_outcome, not the adapter."
        )

    def test_start_work_adapter_no_business_logic_in_source(self) -> None:
        """AC7 (start_work): adapter must forward id only, with no local business logic.

        Guard test (loop-breaker closure, 3rd review cycle): extends AC7
        source-inspection coverage to start_work per architecture review guidance.
        start_work is a simple claim delegation — no parameter normalization or
        predicate checks belong in the adapter.

        Currently PASSES because no forbidden patterns exist in start_work.
        Would FAIL if business logic were introduced into the adapter.
        """
        source = inspect.getsource(start_work)
        assert 'or ""' not in source, (
            "AC7: start_work adapter must not perform parameter normalization."
        )
        assert "claim_timeout" not in source, (
            "AC7: start_work adapter must not contain claim-state business logic."
        )
