"""Retry-cycle proof tests for MCP read adapter boundary validation (#1090).

AC4: Boundary validation via model_validate (not model_construct) — executable test
     in serve/mcp-kanban/tests/ proving type-invalid MCP input is rejected at the
     adapter boundary, not passed through to the engine.

AC6: list_tasks output_schema equality — executable equality assertion proving the
     registered schema matches ListTasksResponse.model_json_schema() exactly.

Location: serve/mcp-kanban/tests/ as required by AC4/AC6 and reviewer directive.

Proof semantics:
- AC4 tests assert ToolError is raised AND engine was NOT called. If model_construct
  replaced model_validate, the string would pass through silently: engine would be
  called (no ToolError), so assert_not_called() would fail the test.
- AC6 test asserts exact equality of the registered schema dict. If the schema
  registration were removed or changed, the assertion would fail.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from owlbear_kanban.models import ListTasksResponse, ShowTaskResponse

# ---------------------------------------------------------------------------
# Board / context helpers (mirrors test_mcp_read_tools.py pattern)
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


def _make_board_1090b(base_dir: Path) -> Path:
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


def _make_mcp_ctx_1090b(app_ctx: object) -> MagicMock:
    ctx = MagicMock()
    ctx.request_context.lifespan_context = app_ctx
    return ctx


def _make_show_task_response_1090b(**overrides: object) -> ShowTaskResponse:
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
def app_ctx_1090b(tmp_path: Path) -> tuple[object, MagicMock]:
    """AppContext with mock AgentView for boundary proof tests."""
    from owlbear_kanban import KanbanEngine
    from owlbear_mcp_kanban.server import AppContext

    kanban_dir = _make_board_1090b(tmp_path)
    engine = KanbanEngine(kanban_dir)
    mock_av = MagicMock()
    engine._agent_view = mock_av  # noqa: SLF001
    app_ctx = AppContext(engine=engine, kanban_dir=kanban_dir)
    return app_ctx, mock_av


# ---------------------------------------------------------------------------
# TestFromAC_BoundaryValidation
# AC4: model_validate (not model_construct) is proven by passing type-invalid
#      input through the MCP handler and asserting ToolError.
#
# Mutation proof: if model_construct replaced model_validate, the type-invalid
# input would reach the engine (no PydanticValidationError). The mock would
# return a MagicMock — no ToolError would be raised — pytest.raises() would
# fail. engine.assert_not_called() would also fail. Both assertions enforce
# that validation occurs at the boundary, not the engine.
# ---------------------------------------------------------------------------


class TestFromAC_BoundaryValidation:
    """AC4: type-invalid MCP input → ToolError via model_validate boundary."""

    @pytest.mark.asyncio
    async def test_show_task_type_invalid_id_raises_tool_error(
        self,
        app_ctx_1090b: tuple[object, MagicMock],
    ) -> None:
        """AC4: show_task(id="not_an_int") → ToolError; engine NOT called.

        ShowTaskParams.id: int with model_validate rejects non-numeric strings.
        model_construct would silently accept the string and forward it to the
        engine — no ToolError would be raised.

        Fails if model_validate is replaced with model_construct: no ToolError
        → pytest.raises exits without exception → test fails. Additionally,
        assert_not_called() fails because engine.show_task is invoked with the
        invalid string.
        """
        from owlbear_mcp_kanban.server import show_task

        app_ctx, mock_av = app_ctx_1090b
        ctx = _make_mcp_ctx_1090b(app_ctx)

        with pytest.raises(ToolError):
            await show_task(ctx, id="not_an_int")  # type: ignore[arg-type]

        mock_av.show_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_list_tasks_type_invalid_ids_element_raises_tool_error(
        self,
        app_ctx_1090b: tuple[object, MagicMock],
    ) -> None:
        """AC4: list_tasks(ids=["not_an_int"]) → ToolError; engine NOT called.

        ListTasksParams.ids: list[int] | None with model_validate rejects a list
        containing a non-numeric string. model_construct would accept it silently
        and forward the malformed list to the engine.

        Fails if model_validate is replaced with model_construct: no ToolError
        → pytest.raises exits without exception → test fails. assert_not_called()
        also fails because engine.list_tasks would be invoked.
        """
        from owlbear_mcp_kanban.server import list_tasks

        app_ctx, mock_av = app_ctx_1090b
        ctx = _make_mcp_ctx_1090b(app_ctx)

        with pytest.raises(ToolError):
            await list_tasks(ctx, ids=["not_an_int"])  # type: ignore[list-item]

        mock_av.list_tasks.assert_not_called()


# ---------------------------------------------------------------------------
# TestFromAC_OutputSchema
# AC6: list_tasks output_schema is set from ListTasksResponse.model_json_schema().
#      Executable equality assertion in serve/mcp-kanban/tests/ (not comment-only).
# ---------------------------------------------------------------------------


class TestFromAC_OutputSchema:
    """AC6: list_tasks output_schema equals ListTasksResponse.model_json_schema()."""

    def test_list_tasks_output_schema_equals_model_json_schema(self) -> None:
        """AC6: list_tasks.fn_metadata.output_schema == ListTasksResponse.model_json_schema().

        The registered output_schema must equal the serialization schema of
        ListTasksResponse. Fails if the schema registration is removed or uses a
        different model (e.g., KanbanTask) or a hardcoded dict that drifts from
        the model definition.
        """
        from owlbear_mcp_kanban.server import mcp

        tool_obj = next(
            (t for t in mcp._tool_manager._tools.values() if t.name == "list_tasks"),
            None,
        )
        assert tool_obj is not None, (
            "AC6: 'list_tasks' tool must be registered in the MCP server"
        )
        registered = tool_obj.fn_metadata.output_schema
        expected = ListTasksResponse.model_json_schema()
        assert registered == expected, (
            f"AC6: list_tasks output_schema must equal ListTasksResponse.model_json_schema(). "
            f"Registered: {registered!r}. Expected: {expected!r}"
        )
