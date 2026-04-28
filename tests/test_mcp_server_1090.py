"""RED phase tests — MCP read tool adapter error-mapping helper (#1090).

AC Coverage:
- KanbanError → ToolError mapping helper (_map_kanban_error) established in server
  module as a reusable callable — reused by later mutation/lifecycle tasks.
- Helper maps all KanbanError subclasses (ValidationError, NotFoundError,
  ConcurrencyError) to MCP ToolError with user_message.
- Helper is exported in server.__all__ for discoverability.
- ToolError raised by helper chains the original exception (__cause__).

Retry cycle additions (AC4, AC2):
- AC4: list_tasks must use model_validate (not model_construct) — ids+other filter
  combination must be caught by boundary model BEFORE the engine is called.
- AC2: show_task must NOT accept legacy task_id= kwarg — only id + section (ShowTaskParams).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from owlbear_kanban.errors import (
    ConcurrencyError,
    NotFoundError,
    ValidationError,
)
from owlbear_kanban.models import ListTasksResponse, ShowTaskResponse

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
# TestFromAC_ErrorMappingHelper
# AC: KanbanError → ToolError mapping helper established (reused by later tasks)
# ---------------------------------------------------------------------------


class TestFromAC_ErrorMappingHelper:
    """Named _map_kanban_error helper exists in server module and is reusable."""

    def test_error_mapping_helper_is_importable(self) -> None:
        """AC: _map_kanban_error must be importable from owlbear_mcp_kanban.server."""
        from owlbear_mcp_kanban.server import _map_kanban_error  # noqa: F401

    def test_error_mapping_helper_is_in_module_all(self) -> None:
        """AC: _map_kanban_error must appear in server.__all__ for reuse by later tasks."""
        from owlbear_mcp_kanban import server

        assert "_map_kanban_error" in server.__all__, (
            "_map_kanban_error must be listed in server.__all__ so later tasks can import it"
        )

    def test_error_mapping_helper_is_callable(self) -> None:
        """AC: _map_kanban_error must be a callable (function or callable object)."""
        from owlbear_mcp_kanban.server import _map_kanban_error

        assert callable(_map_kanban_error), "_map_kanban_error must be callable"

    def test_error_mapping_helper_raises_tool_error_for_validation_error(self) -> None:
        """AC: _map_kanban_error(ValidationError) raises MCP ToolError."""
        from owlbear_mcp_kanban.server import _map_kanban_error

        exc = ValidationError(code="ERR_STALE", user_message="validation failed")
        with pytest.raises(ToolError):
            _map_kanban_error(exc)

    def test_error_mapping_helper_raises_tool_error_for_not_found_error(self) -> None:
        """AC: _map_kanban_error(NotFoundError) raises MCP ToolError."""
        from owlbear_mcp_kanban.server import _map_kanban_error

        exc = NotFoundError(code="ERR_NOT_FOUND", user_message="task 42 not found")
        with pytest.raises(ToolError):
            _map_kanban_error(exc)

    def test_error_mapping_helper_raises_tool_error_for_concurrency_error(self) -> None:
        """AC: _map_kanban_error(ConcurrencyError) raises MCP ToolError.

        ConcurrencyError is a KanbanError subclass — the helper must handle it,
        not just ValidationError/NotFoundError.
        """
        from owlbear_mcp_kanban.server import _map_kanban_error

        exc = ConcurrencyError(code="ERR_STALE", user_message="write conflict detected")
        with pytest.raises(ToolError):
            _map_kanban_error(exc)

    def test_error_mapping_helper_preserves_user_message_exactly(self) -> None:
        """AC: ToolError raised by helper contains the exact user_message from KanbanError."""
        from owlbear_mcp_kanban.server import _map_kanban_error

        user_msg = "ids cannot be combined with other filter parameters"
        exc = ValidationError(code="ERR_STALE", user_message=user_msg)
        with pytest.raises(ToolError) as exc_info:
            _map_kanban_error(exc)

        assert user_msg in str(exc_info.value), (
            "ToolError from _map_kanban_error must contain the exact user_message"
        )

    def test_error_mapping_helper_chains_original_exception(self) -> None:
        """AC: ToolError.__cause__ is the original KanbanError (raise ... from exc pattern)."""
        from owlbear_mcp_kanban.server import _map_kanban_error

        original = ValidationError(code="ERR_STALE", user_message="chained test")
        with pytest.raises(ToolError) as exc_info:
            _map_kanban_error(original)

        assert exc_info.value.__cause__ is original, (
            "ToolError raised by _map_kanban_error must chain the original KanbanError "
            "as __cause__ (i.e. 'raise ToolError(...) from exc')"
        )


# ---------------------------------------------------------------------------
# TestFromAC_ReadAdapterBriefA
# AC: Brief A §5.1-§5.3 boundary model alignment - signature and surface contracts
# ---------------------------------------------------------------------------


class TestFromAC_ReadAdapterBriefA:
    """Brief A §5.1-§5.3 contract tests - adapter parameter surface matches boundary models."""

    import inspect as _inspect

    # -- AC1: list_tasks 12-param surface, no legacy archived: bool --

    def test_list_tasks_no_archived_param_on_mcp_surface(self) -> None:
        """AC1: list_tasks must NOT expose 'archived: bool' (Brief A §5.1 — no legacy param)."""
        import inspect

        from owlbear_mcp_kanban.server import list_tasks

        sig = inspect.signature(list_tasks)
        assert "archived" not in sig.parameters, (
            "Brief A §5.1 prohibits 'archived: bool' on the MCP surface; "
            "use 'archival_reason: str | None' instead"
        )

    def test_list_tasks_has_archival_reason_param(self) -> None:
        """AC1: list_tasks must expose 'archival_reason' matching ListTasksParams.archival_reason."""
        import inspect

        from owlbear_mcp_kanban.server import list_tasks

        sig = inspect.signature(list_tasks)
        assert "archival_reason" in sig.parameters, (
            "list_tasks must accept 'archival_reason' (Brief A §5.1 / ListTasksParams field)"
        )

    def test_list_tasks_has_parent_param(self) -> None:
        """AC1: list_tasks must expose 'parent' matching ListTasksParams.parent."""
        import inspect

        from owlbear_mcp_kanban.server import list_tasks

        sig = inspect.signature(list_tasks)
        assert "parent" in sig.parameters, (
            "list_tasks must accept 'parent' (Brief A §5.1 / ListTasksParams field)"
        )

    def test_list_tasks_param_set_matches_list_tasks_params_model(self) -> None:
        """AC4: list_tasks parameter names must align with ListTasksParams fields (boundary model)."""
        import inspect

        from owlbear_mcp_kanban.models import ListTasksParams
        from owlbear_mcp_kanban.server import list_tasks

        sig = inspect.signature(list_tasks)
        # Exclude 'ctx' (MCP context) — it's infrastructure, not a user param
        adapter_params = {k for k in sig.parameters if k != "ctx"}
        model_fields = set(ListTasksParams.model_fields)

        missing_from_adapter = model_fields - adapter_params
        assert not missing_from_adapter, (
            f"list_tasks is missing params that ListTasksParams defines: {missing_from_adapter!r}. "
            "Adapter must wire MCP args to model fields (AC4)."
        )

    # -- AC2: show_task accepts id: int (not task_id: StrId), section passthrough --

    def test_show_task_has_id_param_not_task_id(self) -> None:
        """AC2: show_task parameter must be 'id: int' matching ShowTaskParams.id, not 'task_id'."""
        import inspect

        from owlbear_mcp_kanban.server import show_task

        sig = inspect.signature(show_task)
        assert "id" in sig.parameters, (
            "show_task must accept 'id' (ShowTaskParams.id: int per Brief A §5.2)"
        )
        assert "task_id" not in sig.parameters, (
            "show_task must use 'id' (not 'task_id: StrId') to match ShowTaskParams boundary model"
        )

    def test_show_task_id_param_is_int_type(self) -> None:
        """AC2: show_task 'id' parameter must accept int (matching ShowTaskParams.id: int)."""
        import inspect

        from owlbear_mcp_kanban.server import show_task

        sig = inspect.signature(show_task)
        assert "id" in sig.parameters, "show_task must have 'id' parameter"
        # Annotation should be int (not StrId / str)
        ann = sig.parameters["id"].annotation
        assert ann is int or ann == "int", (
            f"show_task 'id' must be annotated as int (ShowTaskParams.id: int), got {ann!r}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_BoundaryModelDeserialization
# AC4: list_tasks uses model_validate (not model_construct) — ids+other filter
#      combination must raise ToolError BEFORE the engine is called.
# AC2: show_task accepts only id + section — legacy task_id= kwarg must be rejected.
# ---------------------------------------------------------------------------


class TestFromAC_BoundaryModelDeserialization:
    """AC4 and AC2: boundary model validation enforced before engine delegation."""

    @pytest.mark.asyncio
    async def test_list_tasks_boundary_model_rejects_ids_combined_with_status_no_engine_call(
        self,
        app_ctx_1090: tuple[object, MagicMock],
    ) -> None:
        """AC4: list_tasks uses model_validate — ids+status raises ToolError before engine call.

        With model_construct (current impl): validation is skipped entirely.
        AgentView is called normally, mock returns OK — no ToolError → this test FAILS.

        With model_validate (required): ListTasksParams._validate_ids_exclusivity raises
        PydanticValidationError → ToolError. AgentView must NOT be called.
        """
        from owlbear_mcp_kanban.server import list_tasks

        app_ctx, mock_av = app_ctx_1090
        # Mock returns successfully — proves any ToolError comes from model, not engine
        mock_av.list_tasks.return_value = ListTasksResponse(tasks=[], guidance=[])

        ctx = _make_mcp_ctx_1090(app_ctx)
        with pytest.raises(ToolError):
            await list_tasks(ctx, ids=[1], status="todo")

        # Engine MUST NOT have been called — boundary model rejected the input first
        mock_av.list_tasks.assert_not_called()

    @pytest.mark.asyncio
    async def test_show_task_rejects_legacy_task_id_kwarg(
        self,
        app_ctx_1090: tuple[object, MagicMock],
    ) -> None:
        """AC2: show_task accepts only id + section (ShowTaskParams) — task_id= must be rejected.

        Brief A §5.2 requires the MCP surface to be exactly id + section.
        The legacy_kwargs.pop("task_id", id) compatibility path must be removed.

        Currently FAILS: task_id= is silently routed via legacy compat and engine is called.
        Once legacy compat is removed: calling show_task(ctx, task_id=42) raises
        ToolError (unknown kwarg) or TypeError (unexpected keyword arg) — either proves
        the legacy compat path no longer exists.
        """
        from owlbear_mcp_kanban.server import show_task

        app_ctx, mock_av = app_ctx_1090
        mock_av.show_task.return_value = _make_show_task_response_1090(id=42)

        ctx = _make_mcp_ctx_1090(app_ctx)
        with pytest.raises((ToolError, TypeError)):
            await show_task(ctx, task_id=42)  # type: ignore[call-arg]

        # Engine must NOT have been called — legacy compat path must not exist
        mock_av.show_task.assert_not_called()

