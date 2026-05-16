"""Durable tests for MCP read tool adapter behavior and suite rollout.

Promoted from archived task #1090 during test curation.

AC coverage:
- AC2+AC7: show_task makes single unconditional call view.show_task(task_id=params.id,
           section=params.section). When section=None, None passes through — NOT "".
           The Mock-specific branch (isinstance(view, Mock) → section="") violates AC2+AC7.
- AC7:     No isinstance(view, Mock) check in show_task handler source. Structural proof.
- AC8(b):  test_mcp_read_tools.py ~L807 kw.get("id") must be kw.get("task_id").
           Durable test asserts wrong kwarg name; builder must correct it.

Already implemented (no failing test possible):
- AC1: 12-param list_tasks surface (no legacy archived: bool) — verified by durable suite.
- AC3: pick_tasks delegates to AgentView.pick_tasks — verified by durable suite.
- AC4: model_validate rejects type-invalid input → ToolError — model_validate already in use.
- AC5: KanbanError → ToolError via _map_kanban_error — verified by durable suite.
- AC6: list_tasks output_schema = ListTasksResponse.model_json_schema() — already set.
- AC8(a): test_mcp_guidance_1089.py uses id= not task_id= — already fixed.
"""

from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from owlbear_kanban.models import ShowTaskResponse

# Promoted from archived task #1090.

# ---------------------------------------------------------------------------
# Helpers for boundary model tests
# ---------------------------------------------------------------------------

_CONFIG_YAML = """\
next_id: 1
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
# TestFromAC_ShowTaskUnconditionalCall
# AC2+AC7: show_task must make a single unconditional call:
#   view.show_task(task_id=params.id, section=params.section)
# When section=None, it must be passed as None — NOT converted to "".
# The current Mock branch (isinstance(view, Mock) → section="") violates AC2+AC7.
# ---------------------------------------------------------------------------


class TestFromAC_ShowTaskUnconditionalCall:
    """AC2+AC7: show_task passes section=None through as None, no Mock branching."""

    @pytest.mark.asyncio
    async def test_section_none_passes_through_as_none_not_empty_string(
        self,
        app_ctx_1090: tuple[object, MagicMock],
    ) -> None:
        """AC2+AC7: When no section is provided, view.show_task receives section=None.

        AC2 mandates a single unconditional call: view.show_task(task_id=params.id,
        section=params.section). When section is omitted, params.section is None —
        it must be forwarded as None, not coerced to "".

        The current Mock-specific branch sets view_section="" whenever the view is a
        Mock instance and section is None (server.py:337-338). This violates both
        AC2 (unconditional call) and AC7 (no isinstance(view, Mock)).
        """
        from owlbear_mcp_kanban.server import show_task

        app_ctx, mock_av = app_ctx_1090
        mock_av.show_task.return_value = _make_show_task_response_1090(id=42)
        ctx = _make_mcp_ctx_1090(app_ctx)

        await show_task(ctx, id=42)

        kw = mock_av.show_task.call_args.kwargs
        assert kw.get("section") is None, (
            f"AC2: view.show_task must receive section=None when no section is provided; "
            f"got section={kw.get('section')!r}. "
            f"The isinstance(view, Mock) branch at server.py:337-338 must be removed (AC7)."
        )

    def test_show_task_source_has_no_isinstance_mock_check(self) -> None:
        """AC7: No isinstance(view, Mock) check in show_task handler source.

        The Mock-specific branch at server.py:337-338 reads:
          if view_section is None and isinstance(view, Mock): view_section = ""
        This branch must be removed. The Mock import at module level may stay
        (used by _agent_view_for), but isinstance(view, Mock) must not appear
        in the show_task function body.
        """
        import inspect

        from owlbear_mcp_kanban.server import show_task

        source = inspect.getsource(show_task)
        assert "isinstance(view, Mock)" not in source, (
            "AC7: show_task handler must not contain isinstance(view, Mock) check. "
            "Remove the Mock-specific section-handling branch at server.py:337-338."
        )


# ---------------------------------------------------------------------------
# TestFromAC_DurableSuiteRollout
# AC8(b): test_mcp_read_tools.py ~L807 asserts kw.get("id") == 77.
# The adapter correctly uses task_id= kwarg; the durable test assertion is wrong.
# Builder must update the assertion to kw.get("task_id") == 77.
# ---------------------------------------------------------------------------


class TestFromAC_DurableSuiteRollout:
    """AC8(b): Durable read-tools suite uses kw.get("task_id") for engine kwarg assertion."""

    def test_read_tools_suite_show_task_id_assertion_uses_task_id_kwarg(self) -> None:
        """AC8(b): test_mcp_read_tools.py must assert kw.get("task_id"), not kw.get("id").

        The adapter calls view.show_task(task_id=params.id, ...). The durable suite
        test_show_task_id_forwarded_exact (test_mcp_read_tools.py ~L807) still asserts
        kw.get("id") == 77, which is the WRONG kwarg name for the engine call.
        The assertion must be updated to kw.get("task_id") == 77.
        """
        read_tools_file = Path(__file__).parent.parent / "serve" / "mcp-kanban" / "tests" / "test_mcp_read_tools.py"
        content = read_tools_file.read_text(encoding="utf-8")

        bad_assertions = re.findall(r'kw\.get\("id"\)\s*==', content)
        assert not bad_assertions, (
            f"test_mcp_read_tools.py has {len(bad_assertions)} wrong kwarg assertion(s) "
            f'using kw.get("id"). '
            f'Must be updated to kw.get("task_id") to match the adapter\'s engine call. '
            f"See test_show_task_id_forwarded_exact (~L807). "
            f"Found: {bad_assertions!r}"
        )


# ---------------------------------------------------------------------------
# Notes: already implemented — no failing test possible
# AC3: pick_tasks delegates to AgentView.pick_tasks — verified by durable suite.
# AC5: KanbanError → ToolError via _map_kanban_error — verified by durable suite.
# AC6: list_tasks output_schema = ListTasksResponse.model_json_schema() — already set.
# ---------------------------------------------------------------------------
