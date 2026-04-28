"""RED phase tests — MCP read tool adapters: list_tasks, show_task, pick_tasks (#1090).

AC Coverage:
- AC2: show_task adapter must translate MCP 'id' param → engine 'task_id' kwarg.
       view.show_task(task_id=params.id, section=params.section) — NOT id=params.id.
       Also: integration proof that a real engine call succeeds end-to-end.
- AC3: pick_tasks accepts wave_size + max_waves matching PickTasksParams; delegates
       to AgentView.pick_tasks with those exact kwargs.
- AC5: KanbanError → ToolError via _map_kanban_error in show_task and pick_tasks
       handlers; ToolError.__cause__ chains original exception (raise ... from exc).
- AC6: list_tasks fn_metadata.output_schema matches ListTasksResponse.model_json_schema()
       (structural proof following test_outputschema_541.py pattern).
- AC8: Adjacent guidance test suite (test_mcp_guidance_1089.py) must use
       show_task(id=...) not legacy show_task(task_id=...) on the MCP surface.

Note: AC1 (12-param list_tasks surface), AC4 (model_validate), and the
_map_kanban_error helper existence/behaviour (AC5 helper) are already verified by
the pre-existing passing tests. This file covers the remaining gaps.
"""

from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from owlbear_kanban.models import ShowTaskResponse

# ---------------------------------------------------------------------------
# Helpers for boundary model tests
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


def _make_board_1090(base_dir: Path) -> Path:
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


def _make_mcp_ctx_1090(app_ctx: object) -> MagicMock:
    ctx = MagicMock()
    ctx.request_context.lifespan_context = app_ctx
    return ctx


def _make_show_task_response_1090(**overrides: object) -> ShowTaskResponse:
    defaults: dict[str, object] = {
        "id": 42,
        "title": "Show me",
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
        "body": "## Notes\n\nHello",
        "missing_sections": None,
        "guidance": [],
    }
    defaults.update(overrides)
    return ShowTaskResponse.model_validate(defaults)


@pytest.fixture
def app_ctx_1090(tmp_path: Path) -> tuple[object, MagicMock]:
    """AppContext with mock AgentView for boundary model tests."""
    from owlbear_kanban import KanbanEngine
    from owlbear_mcp_kanban.server import AppContext

    kanban_dir = _make_board_1090(tmp_path)
    engine = KanbanEngine(kanban_dir)
    mock_av = MagicMock()
    engine._agent_view = mock_av  # noqa: SLF001
    app_ctx = AppContext(engine=engine, kanban_dir=kanban_dir)
    return app_ctx, mock_av


# ---------------------------------------------------------------------------
# TestFromAC_ShowTaskKwargTranslation
# AC2: show_task adapter translates MCP 'id' param → engine 'task_id' kwarg.
# The critical bug: server.py currently calls view.show_task(id=params.id, ...)
# but AgentView.show_task(self, task_id: int, section: str | None = None)
# expects 'task_id'. The adapter must translate.
# ---------------------------------------------------------------------------


class TestFromAC_ShowTaskKwargTranslation:
    """AC2: show_task translates MCP surface id → engine task_id kwarg."""

    @pytest.mark.asyncio
    async def test_show_task_engine_view_called_with_task_id_kwarg_not_id(
        self,
        app_ctx_1090: tuple[object, MagicMock],
    ) -> None:
        """AC2: view.show_task must be called with task_id=params.id, NOT id=params.id.

        The MCP surface uses 'id' (ShowTaskParams.id) but AgentView.show_task(task_id)
        uses 'task_id'. The adapter must translate.

        FAILS: current server.py calls view.show_task(id=params.id, section=params.section).
        The mock records call_args as {'id': 42, 'section': ''}, so
        assert_called_once_with(task_id=42, section="") raises AssertionError.
        """
        from owlbear_mcp_kanban.server import show_task

        app_ctx, mock_av = app_ctx_1090
        mock_av.show_task.return_value = _make_show_task_response_1090(id=42)
        ctx = _make_mcp_ctx_1090(app_ctx)

        await show_task(ctx, id=42)

        # Must be called with task_id=42, NOT id=42
        mock_av.show_task.assert_called_once_with(task_id=42, section="")

    @pytest.mark.asyncio
    async def test_show_task_engine_view_not_called_with_id_kwarg(
        self,
        app_ctx_1090: tuple[object, MagicMock],
    ) -> None:
        """AC2: the engine view must NOT receive 'id=' kwarg — only 'task_id='.

        Using the 'id' Python builtin as a kwarg name to AgentView.show_task
        is wrong and will raise TypeError with a real engine.

        FAILS: current impl passes id= to the mock; call_args.kwargs will contain
        'id' and not 'task_id'.
        """
        from owlbear_mcp_kanban.server import show_task

        app_ctx, mock_av = app_ctx_1090
        mock_av.show_task.return_value = _make_show_task_response_1090(id=7)
        ctx = _make_mcp_ctx_1090(app_ctx)

        await show_task(ctx, id=7, section="Notes")

        actual_kwargs = mock_av.show_task.call_args.kwargs
        assert "task_id" in actual_kwargs, (
            f"view.show_task must be called with task_id= kwarg; got kwargs={actual_kwargs!r}"
        )
        assert "id" not in actual_kwargs, (
            f"view.show_task must NOT have 'id=' in kwargs (that's the MCP surface name); "
            f"got kwargs={actual_kwargs!r}"
        )

    @pytest.mark.asyncio
    async def test_show_task_integration_with_real_engine_succeeds(
        self,
        tmp_path: Path,
    ) -> None:
        """AC2: end-to-end — show_task(ctx, id=N) returns a ShowTaskResponse via real engine.

        With the correct adapter (task_id= kwarg), the call chain works:
          show_task(ctx, id=N) → ShowTaskParams(id=N) → view.show_task(task_id=N) → response.

        FAILS: current impl calls view.show_task(id=N) which raises TypeError
        (AgentView.show_task has no 'id' parameter). TypeError propagates uncaught
        through show_task → pytest reports ERRORS/FAILED.
        """
        from owlbear_kanban import KanbanEngine
        from owlbear_mcp_kanban.server import AppContext, show_task

        kanban_dir = _make_board_1090(tmp_path)
        engine = KanbanEngine(kanban_dir)
        task = engine.agent_view().create_task(title="Integration target", body="")
        task_id = task.id

        app_ctx = AppContext(engine=engine, kanban_dir=kanban_dir)
        ctx = _make_mcp_ctx_1090(app_ctx)

        result = await show_task(ctx, id=task_id)

        assert isinstance(result, ShowTaskResponse), (
            f"show_task(id={task_id}) must return ShowTaskResponse; got {type(result)!r}"
        )
        assert result.id == task_id, (
            f"Returned task id {result.id!r} must match requested id {task_id!r}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_GuidanceCallerRollout
# AC8: Adjacent guidance test suite (test_mcp_guidance_1089.py) must be updated
# to use show_task(id=...) on the MCP surface — not legacy show_task(task_id=...).
# Lines 226, 254, 444 in test_mcp_guidance_1089.py use the old kwarg.
# ---------------------------------------------------------------------------


class TestFromAC_GuidanceCallerRollout:
    """AC8: Guidance test callers use id= not task_id= on MCP show_task surface."""

    def test_guidance_suite_show_task_callers_use_id_not_task_id(self) -> None:
        """AC8: test_mcp_guidance_1089.py must use show_task(id=...) not show_task(task_id=...).

        Brief A §5.2 changed the MCP surface: 'id: int' replaces legacy 'task_id: StrId'.
        The three callers at lines 226, 254, 444 in the guidance suite still use task_id=.
        The builder must update them as part of this task's rollout.

        FAILS until the guidance test file is updated: re.findall will find 3 matches.
        """
        guidance_test_file = (
            Path(__file__).parent.parent
            / "serve"
            / "mcp-kanban"
            / "tests"
            / "test_mcp_guidance_1089.py"
        )
        content = guidance_test_file.read_text(encoding="utf-8")

        bad_callers = re.findall(r"show_task\([^)]*task_id\s*=", content)
        assert not bad_callers, (
            f"test_mcp_guidance_1089.py has {len(bad_callers)} show_task call(s) using "
            f"legacy 'task_id=' kwarg (lines 226, 254, 444). "
            f"Must be updated to 'id=' to match Brief A §5.2 / AC8. "
            f"Found: {bad_callers!r}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_PickTasksAdapter
# AC3: pick_tasks accepts wave_size + max_waves matching PickTasksParams;
#      delegates to AgentView.pick_tasks with those kwargs.
# AC5: KanbanError in pick_tasks → ToolError (via _map_kanban_error).
#
# Note: AC3 delegation, AC5 KanbanError mapping in show_task/pick_tasks, and
# AC6 (list_tasks output_schema) are already implemented in server.py — no
# failing tests are possible for these ACs. Verified passing by quality-runner;
# tests removed per RED phase rules. Documented here for AC coverage record.
# ---------------------------------------------------------------------------

