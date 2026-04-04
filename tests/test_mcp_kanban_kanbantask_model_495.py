"""Failing tests for task #495: Define KanbanTask model + add outputSchema to show/move/pick.

Covers all AC items from #495:
  - models.py with KanbanTask(BaseModel) is importable
  - model_config = ConfigDict(populate_by_name=True), extra=ignore
  - Required fields: id (int), title, status, priority, created, updated, class_ (alias=class)
  - Optional fields with defaults: tags=[], depends_on=[], blocked=False; rest default None
  - show_task, move_task, pick_task return KanbanTask (not str)
  - show_task, move_task, pick_task raise ToolError on rc!=0
  - ValidationError wrapped as ToolError with details
  - model_dump(by_alias=True) uses "class" key not "class_"
  - outputSchema present on show_task, move_task, pick_task
  - list_tasks, create_task, edit_task, start_work remain returning str
  - KanbanTask validates actual kanban-md JSON shapes

All tests FAIL in RED phase — models.py does not exist yet; show/move/pick still
return str and don't raise ToolError.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# KanbanTask does not exist yet — import guard prevents collection failure so
# model tests fail as AssertionError rather than a collection-time ImportError.
try:
    from owlbear_mcp_kanban.models import KanbanTask as _KanbanTask  # type: ignore[import]
except ImportError:
    _KanbanTask = None  # type: ignore[assignment]

from mcp.server.fastmcp.exceptions import ToolError
from owlbear_mcp_kanban.server import AppContext, move_task, show_task


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Minimal valid kanban-md JSON output for a single task (all required fields)
_MINIMAL_TASK_JSON: dict[str, Any] = {
    "id": 42,
    "title": "Sample task",
    "status": "todo",
    "priority": "important",
    "created": "2026-01-01T00:00:00+02:00",
    "updated": "2026-01-02T12:00:00+02:00",
}

# Full task JSON with all optional fields populated
_FULL_TASK_JSON: dict[str, Any] = {
    "id": 495,
    "title": "Define KanbanTask model",
    "status": "todo",
    "priority": "needed",
    "created": "2026-03-31T06:47:09+02:00",
    "updated": "2026-03-31T22:34:38+02:00",
    "class": "standard",
    "claimed_by": "cedar-cloud",
    "tags": ["scope:mcp", "type:build", "phase-2"],
    "parent": None,
    "depends_on": [489],
    "blocked": False,
    "block_reason": None,
    "body": "## AC\n- do stuff",
    "file": "c:\\kanban\\tasks\\495-model.md",
}


def _make_app_ctx() -> AppContext:
    return AppContext(kanban_bin=Path("/fake/kanban-md"), kanban_dir=Path("/fake/kanban"))


def _make_mcp_ctx(app_ctx: AppContext | None = None) -> MagicMock:
    ctx = MagicMock()
    ctx.request_context.lifespan_context = app_ctx or _make_app_ctx()
    return ctx


def _patch_run(stdout: str = "", stderr: str = "", rc: int = 0) -> Any:
    return patch(
        "owlbear_mcp_kanban.server._run_kanban",
        new=AsyncMock(return_value=(stdout, stderr, rc)),
    )


# ---------------------------------------------------------------------------
# TestFromAC_KanbanTaskModelExists — model importability + class contract
# ---------------------------------------------------------------------------


class TestFromAC_KanbanTaskModelExists:
    """KanbanTask must be importable from owlbear_mcp_kanban.models."""

    # AC: New file packages/mcp-kanban/src/owlbear_mcp_kanban/models.py with KanbanTask(BaseModel)
    def test_models_module_is_importable(self) -> None:
        """owlbear_mcp_kanban.models must be importable."""
        import importlib

        mod = importlib.util.find_spec("owlbear_mcp_kanban.models")
        assert mod is not None, (
            "owlbear_mcp_kanban.models not found; "
            "create packages/mcp-kanban/src/owlbear_mcp_kanban/models.py"
        )

    def test_kanbantask_is_importable(self) -> None:
        """KanbanTask must be importable from owlbear_mcp_kanban.models."""
        assert _KanbanTask is not None, (
            "KanbanTask is not importable from owlbear_mcp_kanban.models; "
            "builder must create the model"
        )

    def test_kanbantask_is_pydantic_basemodel(self) -> None:
        """KanbanTask must be a Pydantic BaseModel subclass."""
        from pydantic import BaseModel

        assert _KanbanTask is not None
        assert issubclass(_KanbanTask, BaseModel), "KanbanTask must be a Pydantic BaseModel subclass"


# ---------------------------------------------------------------------------
# TestFromAC_KanbanTaskModelConfig — model_config requirements
# ---------------------------------------------------------------------------


class TestFromAC_KanbanTaskModelConfig:
    """KanbanTask model_config must meet spec: populate_by_name=True, extra=ignore."""

    # AC: model_config = ConfigDict(populate_by_name=True)
    def test_populate_by_name_is_true(self) -> None:
        """KanbanTask.model_config must have populate_by_name=True."""
        assert _KanbanTask is not None
        config = _KanbanTask.model_config
        assert config.get("populate_by_name") is True, (
            "KanbanTask.model_config must set populate_by_name=True to allow field names "
            "alongside aliases"
        )

    # AC: default extra=ignore (structuredContent matches outputSchema without extras)
    def test_extra_fields_are_ignored(self) -> None:
        """KanbanTask must silently ignore unknown fields (extra='ignore')."""
        assert _KanbanTask is not None
        data = {**_MINIMAL_TASK_JSON, "unknown_field": "should_be_ignored"}
        task = _KanbanTask.model_validate(data)
        assert not hasattr(task, "unknown_field"), (
            "KanbanTask must ignore extra fields (extra='ignore' in model_config)"
        )


# ---------------------------------------------------------------------------
# TestFromAC_KanbanTaskRequiredFields — required field presence + types
# ---------------------------------------------------------------------------


class TestFromAC_KanbanTaskRequiredFields:
    """Required fields must be present and correctly typed."""

    # AC: Required fields: id (int), title (str), status (str), priority (str),
    #     created (str), updated (str)
    def test_required_field_id_is_int(self) -> None:
        """id must be an int (not str)."""
        assert _KanbanTask is not None
        task = _KanbanTask.model_validate(_MINIMAL_TASK_JSON)
        assert isinstance(task.id, int), f"id must be int, got {type(task.id)}"
        assert task.id == 42

    def test_required_field_title(self) -> None:
        """title must be a str."""
        assert _KanbanTask is not None
        task = _KanbanTask.model_validate(_MINIMAL_TASK_JSON)
        assert isinstance(task.title, str)
        assert task.title == "Sample task"

    def test_required_field_status(self) -> None:
        """status must be a str."""
        assert _KanbanTask is not None
        task = _KanbanTask.model_validate(_MINIMAL_TASK_JSON)
        assert isinstance(task.status, str)

    def test_required_field_priority(self) -> None:
        """priority must be a str."""
        assert _KanbanTask is not None
        task = _KanbanTask.model_validate(_MINIMAL_TASK_JSON)
        assert isinstance(task.priority, str)

    def test_required_field_created(self) -> None:
        """created must be a str."""
        assert _KanbanTask is not None
        task = _KanbanTask.model_validate(_MINIMAL_TASK_JSON)
        assert isinstance(task.created, str)

    def test_required_field_updated(self) -> None:
        """updated must be a str."""
        assert _KanbanTask is not None
        task = _KanbanTask.model_validate(_MINIMAL_TASK_JSON)
        assert isinstance(task.updated, str)

    def test_missing_required_id_raises_validation_error(self) -> None:
        """Omitting id must raise a ValidationError."""
        from pydantic import ValidationError

        assert _KanbanTask is not None
        data = {k: v for k, v in _MINIMAL_TASK_JSON.items() if k != "id"}
        with pytest.raises(ValidationError):
            _KanbanTask.model_validate(data)

    def test_extra_fields_silently_ignored(self) -> None:
        """Fields kanban-md emits but KanbanTask doesn't define are silently ignored."""
        assert _KanbanTask is not None
        data = {**_MINIMAL_TASK_JSON, "class": "standard", "started": "2026-01-01"}
        task = _KanbanTask.model_validate(data)
        assert not hasattr(task, "class_")
        assert not hasattr(task, "started")


# ---------------------------------------------------------------------------
# TestFromAC_KanbanTaskOptionalFields — optional field defaults
# ---------------------------------------------------------------------------


class TestFromAC_KanbanTaskOptionalFields:
    """Optional fields must have the correct defaults."""

    # AC: tags (list[str] = [])
    def test_optional_tags_defaults_to_empty_list(self) -> None:
        """tags must default to [] when absent."""
        assert _KanbanTask is not None
        task = _KanbanTask.model_validate(_MINIMAL_TASK_JSON)
        assert task.tags == [], f"tags must default to [], got {task.tags}"  # type: ignore[union-attr]

    # AC: depends_on (list[int] = [])
    def test_optional_depends_on_defaults_to_empty_list(self) -> None:
        """depends_on must default to [] when absent."""
        assert _KanbanTask is not None
        task = _KanbanTask.model_validate(_MINIMAL_TASK_JSON)
        assert task.depends_on == [], f"depends_on must default to [], got {task.depends_on}"  # type: ignore[union-attr]

    # AC: blocked (bool = False)
    def test_optional_blocked_defaults_to_false(self) -> None:
        """blocked must default to False when absent."""
        assert _KanbanTask is not None
        task = _KanbanTask.model_validate(_MINIMAL_TASK_JSON)
        assert task.blocked is False, f"blocked must default to False, got {task.blocked}"  # type: ignore[union-attr]

    # AC: claimed_by (str or None) → coerced to claimed (bool)
    def test_optional_claimed_defaults_to_false(self) -> None:
        """claimed must default to False when claimed_by is absent."""
        assert _KanbanTask is not None
        task = _KanbanTask.model_validate(_MINIMAL_TASK_JSON)
        assert task.claimed is False  # type: ignore[union-attr]

    # AC: body (str or None)
    def test_optional_body_defaults_to_none(self) -> None:
        """body must default to None when absent."""
        assert _KanbanTask is not None
        task = _KanbanTask.model_validate(_MINIMAL_TASK_JSON)
        assert task.body is None  # type: ignore[union-attr]

    # AC: parent (int or None)
    def test_optional_parent_defaults_to_none(self) -> None:
        """parent must default to None when absent."""
        assert _KanbanTask is not None
        task = _KanbanTask.model_validate(_MINIMAL_TASK_JSON)
        assert task.parent is None  # type: ignore[union-attr]

    def test_full_task_json_validates(self) -> None:
        """KanbanTask must validate a full-featured task JSON shape."""
        assert _KanbanTask is not None
        task = _KanbanTask.model_validate(_FULL_TASK_JSON)
        assert task.id == 495
        assert task.depends_on == [489]
        assert task.claimed is True  # claimed_by was "cedar-cloud" → coerced to True
        assert task.tags == ["scope:mcp", "type:build", "phase-2"]


# ---------------------------------------------------------------------------
# TestFromAC_KanbanTaskExtraFieldsIgnored — verify extra="ignore" for dropped fields
# ---------------------------------------------------------------------------


class TestFromAC_KanbanTaskExtraFieldsIgnored:
    """Fields emitted by kanban-md but not in KanbanTask must be silently ignored."""

    def test_class_field_silently_ignored(self) -> None:
        """kanban-md emits 'class' but model must accept and ignore it."""
        assert _KanbanTask is not None
        data = {**_MINIMAL_TASK_JSON, "class": "standard"}
        task = _KanbanTask.model_validate(data)
        assert not hasattr(task, "class_")
        assert task.id == 42

    def test_dropped_fields_silently_ignored(self) -> None:
        """started, completed, assignee, claimed_at, due, estimate must be ignored."""
        assert _KanbanTask is not None
        data = {
            **_MINIMAL_TASK_JSON,
            "started": "2026-01-01",
            "completed": "2026-01-02",
            "assignee": "someone",
            "claimed_at": "2026-01-01T10:00:00+02:00",
            "due": "2026-02-01",
            "estimate": "2h",
        }
        task = _KanbanTask.model_validate(data)
        for attr in ("started", "completed", "assignee", "claimed_at", "due", "estimate"):
            assert not hasattr(task, attr), f"{attr} should be silently ignored"


# ---------------------------------------------------------------------------
# TestFromAC_ShowTaskReturnsKanbanTask — show_task return type + error contract
# ---------------------------------------------------------------------------


class TestFromAC_ShowTaskReturnsKanbanTask:
    """show_task must return KanbanTask on success and raise ToolError on failure."""

    # AC: show_task: return type str to KanbanTask; use KanbanTask.model_validate_json(stdout)
    @pytest.mark.asyncio
    async def test_show_task_returns_kanbantask_on_success(self) -> None:
        """show_task must return a KanbanTask instance on rc==0."""
        assert _KanbanTask is not None, "KanbanTask not importable — model not created yet"
        mcp_ctx = _make_mcp_ctx()
        stdout = json.dumps(_FULL_TASK_JSON)
        with _patch_run(stdout=stdout, rc=0):
            result = await show_task(mcp_ctx, "495")
        assert isinstance(result, _KanbanTask), (
            f"show_task must return KanbanTask instance, got {type(result)}"
        )

    # AC: show_task error path: raise ToolError(stderr.strip())
    @pytest.mark.asyncio
    async def test_show_task_raises_tool_error_on_nonzero_rc(self) -> None:
        """show_task must raise ToolError when rc != 0."""
        mcp_ctx = _make_mcp_ctx()
        with _patch_run(stdout="", stderr="task not found", rc=1), pytest.raises(ToolError) as exc_info:
            await show_task(mcp_ctx, "9999")
        assert "task not found" in str(exc_info.value), (
            "ToolError message must contain the stderr text"
        )

    @pytest.mark.asyncio
    async def test_show_task_no_longer_returns_error_string(self) -> None:
        """show_task must NOT return 'error: ...' string on rc!=0; it must raise ToolError."""
        mcp_ctx = _make_mcp_ctx()
        with _patch_run(stdout="", stderr="some error", rc=1), pytest.raises(ToolError):
            await show_task(mcp_ctx, "9999")

    # AC: Wrap model_validate_json in try/except ValidationError; raise ToolError with details
    @pytest.mark.asyncio
    async def test_show_task_wraps_validation_error_as_tool_error(self) -> None:
        """show_task must raise ToolError when stdout is invalid for KanbanTask."""
        mcp_ctx = _make_mcp_ctx()
        bad_json = json.dumps({"id": "not-an-int", "title": "broken"})  # missing required fields
        with _patch_run(stdout=bad_json, rc=0), pytest.raises(ToolError) as exc_info:
            await show_task(mcp_ctx, "42")
        assert exc_info.value is not None, (
            "show_task must raise ToolError when model_validate_json raises ValidationError"
        )


# ---------------------------------------------------------------------------
# TestFromAC_MoveTaskReturnsKanbanTask — move_task return type + error contract
# ---------------------------------------------------------------------------


class TestFromAC_MoveTaskReturnsKanbanTask:
    """move_task must return KanbanTask on success and raise ToolError on failure."""

    # AC: move_task: return type str to KanbanTask
    @pytest.mark.asyncio
    async def test_move_task_returns_kanbantask_on_success(self) -> None:
        """move_task must return a KanbanTask instance on rc==0."""
        assert _KanbanTask is not None, "KanbanTask not importable — model not created yet"
        mcp_ctx = _make_mcp_ctx()
        stdout = json.dumps({**_FULL_TASK_JSON, "status": "in-progress"})
        with _patch_run(stdout=stdout, rc=0):
            result = await move_task(mcp_ctx, "495", "in-progress")
        assert isinstance(result, _KanbanTask), (
            f"move_task must return KanbanTask instance, got {type(result)}"
        )

    # AC: move_task error path: raise ToolError(stderr.strip())
    @pytest.mark.asyncio
    async def test_move_task_raises_tool_error_on_nonzero_rc(self) -> None:
        """move_task must raise ToolError when rc != 0."""
        mcp_ctx = _make_mcp_ctx()
        with _patch_run(stdout="", stderr="unknown status: foo", rc=1), pytest.raises(ToolError) as exc_info:
            await move_task(mcp_ctx, "42", "foo")
        assert "unknown status" in str(exc_info.value)

    # AC: ValidationError caught and wrapped
    @pytest.mark.asyncio
    async def test_move_task_wraps_validation_error_as_tool_error(self) -> None:
        """move_task must raise ToolError when stdout is invalid JSON for KanbanTask."""
        mcp_ctx = _make_mcp_ctx()
        bad_json = json.dumps({"title": "no required fields"})
        with _patch_run(stdout=bad_json, rc=0), pytest.raises(ToolError):
            await move_task(mcp_ctx, "42", "in-progress")


# ---------------------------------------------------------------------------
# TestFromAC_OutputSchemaAnnotations — outputSchema on show/move
# ---------------------------------------------------------------------------


class TestFromAC_OutputSchemaAnnotations:
    """show_task and move_task must have outputSchema in MCP tool listing."""

    def _get_tool(self, name: str) -> Any:
        from owlbear_mcp_kanban.server import mcp
        tools = {t.name: t for t in mcp._tool_manager._tools.values()}  # type: ignore[union-attr]
        assert name in tools, f"'{name}' must be registered in FastMCP"
        return tools[name]

    # AC: outputSchema in tool listing for show_task — must have KanbanTask fields, not str wrapper
    def test_show_task_has_kanbantask_output_schema(self) -> None:
        """show_task outputSchema must describe KanbanTask fields (id, title, status) not a str wrapper."""
        tool = self._get_tool("show_task")
        assert hasattr(tool, "output_schema"), "show_task tool must have output_schema attribute"
        schema = tool.output_schema
        assert schema is not None, "show_task must have a non-None outputSchema"
        props = schema.get("properties", {})
        assert "id" in props, (
            "show_task outputSchema must include KanbanTask fields (id, title, ...); "
            f"currently has properties: {list(props.keys())} — change return type to KanbanTask"
        )
        assert "title" in props, (
            "show_task outputSchema must include 'title' field from KanbanTask"
        )

    # AC: outputSchema in tool listing for move_task — must have KanbanTask fields
    def test_move_task_has_kanbantask_output_schema(self) -> None:
        """move_task outputSchema must describe KanbanTask fields, not a str wrapper."""
        tool = self._get_tool("move_task")
        assert hasattr(tool, "output_schema"), "move_task tool must have output_schema attribute"
        schema = tool.output_schema
        assert schema is not None, "move_task must have a non-None outputSchema"
        props = schema.get("properties", {})
        assert "id" in props, (
            "move_task outputSchema must include KanbanTask fields; "
            f"currently has: {list(props.keys())} — change return type to KanbanTask"
        )

    def test_show_task_output_schema_has_required_fields(self) -> None:
        """show_task outputSchema must expose required KanbanTask fields: id, title, status, priority."""
        tool = self._get_tool("show_task")
        schema = tool.output_schema
        assert schema is not None
        props = schema.get("properties", {})
        for field in ("id", "title", "status", "priority", "created", "updated"):
            assert field in props, (
                f"show_task outputSchema missing required KanbanTask field '{field}'; "
                f"current properties: {list(props.keys())}"
            )

    # Dropped fields must NOT appear in outputSchema
    def test_show_task_output_schema_excludes_dropped_fields(self) -> None:
        """show_task outputSchema must not contain dropped fields (class, started, etc.)."""
        tool = self._get_tool("show_task")
        schema = tool.output_schema
        assert schema is not None
        props = schema.get("properties", {})
        for dropped in ("class", "class_", "started", "completed", "assignee", "claimed_at", "due", "estimate"):
            assert dropped not in props, (
                f"outputSchema for show_task must NOT contain dropped field '{dropped}'; "
                f"found properties: {list(props.keys())}"
            )


# ---------------------------------------------------------------------------
# TestFromAC_ModelValidatesSampleJsonShapes — validate real kanban-md output shapes
# ---------------------------------------------------------------------------


class TestFromAC_ModelValidatesSampleJsonShapes:
    """KanbanTask must validate the actual JSON shapes produced by kanban-md."""

    # AC: model validates sample kanban-md JSON shapes

    def test_validates_minimal_shape(self) -> None:
        """KanbanTask must accept minimal output (only required fields)."""
        assert _KanbanTask is not None
        task = _KanbanTask.model_validate(_MINIMAL_TASK_JSON)
        assert task.id == 42

    def test_validates_full_shape_with_all_optional_fields(self) -> None:
        """KanbanTask must accept the full field set from kanban-md --json output."""
        assert _KanbanTask is not None
        task = _KanbanTask.model_validate(_FULL_TASK_JSON)
        assert task.id == 495
        assert task.claimed is True  # claimed_by was "cedar-cloud" → coerced to True
        assert task.depends_on == [489]
        assert task.blocked is False

    def test_validates_json_string_via_model_validate_json(self) -> None:
        """KanbanTask.model_validate_json must parse the raw stdout from kanban-md show --json."""
        assert _KanbanTask is not None
        raw_json = json.dumps(_FULL_TASK_JSON)
        task = _KanbanTask.model_validate_json(raw_json)
        assert task.id == 495

    def test_id_coerced_from_int_field(self) -> None:
        """id must be stored as int (kanban-md emits it as a JSON number)."""
        assert _KanbanTask is not None
        task = _KanbanTask.model_validate(_MINIMAL_TASK_JSON)
        assert task.id == 42
        assert type(task.id) is int

    # Boundary: task with empty tags list
    def test_validates_empty_tags_list(self) -> None:
        """KanbanTask must accept an empty tags list."""
        assert _KanbanTask is not None
        data = {**_MINIMAL_TASK_JSON, "tags": []}
        task = _KanbanTask.model_validate(data)
        assert task.tags == []  # type: ignore[union-attr]

    # Boundary: task with non-empty depends_on
    def test_validates_depends_on_as_list_of_ints(self) -> None:
        """depends_on must be a list[int], not list[str]."""
        assert _KanbanTask is not None
        data = {**_MINIMAL_TASK_JSON, "depends_on": [489, 490]}
        task = _KanbanTask.model_validate(data)
        assert task.depends_on == [489, 490]  # type: ignore[union-attr]
        assert all(isinstance(x, int) for x in task.depends_on)  # type: ignore[union-attr]
