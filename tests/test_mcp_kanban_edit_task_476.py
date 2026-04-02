"""Failing tests for task #476 (revised AC): edit_task returns KanbanTask, raises ToolError.

Covers the REVISED AC items from architect review -- the items NOT yet implemented:
  - edit_task returns KanbanTask object (not raw str)
  - edit_task raises ToolError on rc != 0 (not returns "error: ...")
  - edit_task catches ValidationError and raises ToolError with details
  - edit_task is included in outputSchema override loop (same as show_task/move_task/pick_task)
  - SKILL.md moves edit_task from error-string group to ToolError group

All tests FAIL in RED phase -- current implementation returns str and does not raise ToolError.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from owlbear_mcp_kanban.models import KanbanTask
from owlbear_mcp_kanban.server import (
    AppContext,
    edit_task,
    mcp,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SKILL_MD = Path(__file__).parent.parent / "skills" / "mcp-kanban" / "SKILL.md"

_VALID_TASK_JSON = json.dumps(
    {
        "id": 42,
        "title": "Sample Task",
        "status": "in-progress",
        "priority": "important",
        "created": "2026-01-01T00:00:00Z",
        "updated": "2026-04-01T00:00:00Z",
        "class": "standard",
    }
)

_VALID_TASK_RENAMED_JSON = json.dumps(
    {
        "id": 42,
        "title": "Renamed Task",
        "status": "in-progress",
        "priority": "important",
        "created": "2026-01-01T00:00:00Z",
        "updated": "2026-04-01T00:00:00Z",
        "class": "standard",
    }
)

_VALID_TASK_WITH_PARENT_JSON = json.dumps(
    {
        "id": 42,
        "title": "Child Task",
        "status": "todo",
        "priority": "needed",
        "created": "2026-01-01T00:00:00Z",
        "updated": "2026-04-01T00:00:00Z",
        "class": "standard",
        "parent": 10,
    }
)


def _make_app_ctx() -> AppContext:
    return AppContext(kanban_bin=Path("/fake/kanban-md"), kanban_dir=Path("/fake/kanban"))


def _make_mcp_ctx(app_ctx: AppContext | None = None) -> MagicMock:
    ctx = MagicMock()
    ctx.request_context.lifespan_context = app_ctx or _make_app_ctx()
    return ctx


def _patch_run(stdout: str = _VALID_TASK_JSON, stderr: str = "", rc: int = 0) -> Any:
    return patch(
        "owlbear_mcp_kanban.server._run_kanban",
        new=AsyncMock(return_value=(stdout, stderr, rc)),
    )


# ---------------------------------------------------------------------------
# TestFromAC_EditTaskReturnsKanbanTask
# AC: edit_task returns KanbanTask object (not raw str)
# ---------------------------------------------------------------------------


class TestFromAC_EditTaskReturnsKanbanTask:
    """edit_task must return a KanbanTask, not a raw JSON string."""

    # Happy: basic call returns KanbanTask instance
    @pytest.mark.asyncio
    async def test_success_returns_kanbantask_instance(self) -> None:
        """edit_task must return a KanbanTask object, not a str."""
        with _patch_run(stdout=_VALID_TASK_JSON):
            result = await edit_task(_make_mcp_ctx(), task_id="42")
        assert isinstance(result, KanbanTask), (
            f"edit_task must return KanbanTask, got {type(result).__name__}"
        )

    # Happy: returned KanbanTask id matches task data
    @pytest.mark.asyncio
    async def test_returned_kanbantask_id_is_correct(self) -> None:
        """KanbanTask returned by edit_task must have id=42."""
        with _patch_run(stdout=_VALID_TASK_JSON):
            result = await edit_task(_make_mcp_ctx(), task_id="42")
        assert result.id == 42, f"KanbanTask.id must be 42, got {result.id}"

    # Happy: returned KanbanTask title matches task data
    @pytest.mark.asyncio
    async def test_returned_kanbantask_title_is_correct(self) -> None:
        """KanbanTask returned by edit_task must have the title from kanban-md output."""
        with _patch_run(stdout=_VALID_TASK_JSON):
            result = await edit_task(_make_mcp_ctx(), task_id="42")
        assert result.title == "Sample Task", (
            f"KanbanTask.title must be 'Sample Task', got {result.title!r}"
        )

    # Happy: when title param renames task, returned KanbanTask has new title
    @pytest.mark.asyncio
    async def test_rename_via_title_param_returns_kanbantask_with_new_title(self) -> None:
        """After rename via title param, returned KanbanTask must have the new title."""
        with _patch_run(stdout=_VALID_TASK_RENAMED_JSON):
            result = await edit_task(_make_mcp_ctx(), task_id="42", title="Renamed Task")
        assert isinstance(result, KanbanTask), "edit_task must return KanbanTask even when title is set"
        assert result.title == "Renamed Task", (
            f"KanbanTask.title must be 'Renamed Task', got {result.title!r}"
        )

    # Happy: when parent param is set, returned KanbanTask has parent field
    @pytest.mark.asyncio
    async def test_set_parent_returns_kanbantask_with_parent_field(self) -> None:
        """After setting parent=10, returned KanbanTask must have parent=10."""
        with _patch_run(stdout=_VALID_TASK_WITH_PARENT_JSON):
            result = await edit_task(_make_mcp_ctx(), task_id="42", parent=10)
        assert isinstance(result, KanbanTask), "edit_task must return KanbanTask even when parent is set"
        assert result.parent == 10, f"KanbanTask.parent must be 10, got {result.parent!r}"


# ---------------------------------------------------------------------------
# TestFromAC_EditTaskRaisesToolError
# AC: edit_task raises ToolError on rc != 0 (not returns "error: ..." string)
# ---------------------------------------------------------------------------


class TestFromAC_EditTaskRaisesToolError:
    """edit_task must raise ToolError when kanban-md exits non-zero."""

    # Error: raises ToolError (not returns string) on rc=1
    @pytest.mark.asyncio
    async def test_raises_tool_error_on_nonzero_rc(self) -> None:
        """edit_task must raise ToolError when rc != 0."""
        with _patch_run(stdout="", stderr="task not found", rc=1), pytest.raises(ToolError):
            await edit_task(_make_mcp_ctx(), task_id="999")

    # Error: ToolError message contains stderr text
    @pytest.mark.asyncio
    async def test_tool_error_message_contains_stderr(self) -> None:
        """ToolError message must include the stderr text from kanban-md."""
        with _patch_run(stdout="", stderr="task 999 not found", rc=1), pytest.raises(ToolError, match="task 999 not found"):
            await edit_task(_make_mcp_ctx(), task_id="999")

    # Error: never returns an "error: ..." string (current wrong behavior)
    @pytest.mark.asyncio
    async def test_does_not_return_error_string_on_failure(self) -> None:
        """edit_task must not return a string starting with 'error:'; it must raise ToolError."""
        with _patch_run(stdout="", stderr="not found", rc=1):
            raised = False
            try:
                await edit_task(_make_mcp_ctx(), task_id="999")
            except ToolError:
                raised = True
            assert raised, "edit_task must raise ToolError, not return an error string"

    # Error: parametrized -- multiple error scenarios all raise ToolError
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("stderr_msg", "rc"),
        [
            ("task not found", 1),
            ("invalid status: foobar", 1),
            ("permission denied", 2),
        ],
        ids=["not_found", "invalid_status", "permission_denied"],
    )
    async def test_raises_tool_error_for_various_errors(self, stderr_msg: str, rc: int) -> None:
        """edit_task must raise ToolError for all non-zero rc scenarios."""
        with _patch_run(stdout="", stderr=stderr_msg, rc=rc), pytest.raises(ToolError):
            await edit_task(_make_mcp_ctx(), task_id="42")


# ---------------------------------------------------------------------------
# TestFromAC_EditTaskValidationError
# AC: edit_task catches ValidationError from KanbanTask.model_validate_json and raises ToolError
# ---------------------------------------------------------------------------


class TestFromAC_EditTaskValidationError:
    """edit_task must catch ValidationError and re-raise as ToolError."""

    # Error: malformed JSON raises ToolError
    @pytest.mark.asyncio
    async def test_raises_tool_error_on_malformed_json(self) -> None:
        """When kanban-md outputs invalid JSON (rc=0), edit_task must raise ToolError."""
        with _patch_run(stdout="not valid json at all", stderr="", rc=0), pytest.raises(ToolError):
            await edit_task(_make_mcp_ctx(), task_id="42")

    # Error: valid JSON but missing required KanbanTask fields raises ToolError
    @pytest.mark.asyncio
    async def test_raises_tool_error_on_valid_json_invalid_schema(self) -> None:
        """When JSON is valid but does not match KanbanTask schema, edit_task must raise ToolError."""
        invalid_schema_json = json.dumps({"garbage": "data", "no_required_fields": True})
        with _patch_run(stdout=invalid_schema_json, stderr="", rc=0), pytest.raises(ToolError):
            await edit_task(_make_mcp_ctx(), task_id="42")

    # Boundary: empty stdout with zero rc raises ToolError (not crash)
    @pytest.mark.asyncio
    async def test_raises_tool_error_on_empty_stdout_with_zero_rc(self) -> None:
        """When rc=0 but stdout is empty, edit_task must raise ToolError (not crash)."""
        with _patch_run(stdout="", stderr="", rc=0), pytest.raises(ToolError):
            await edit_task(_make_mcp_ctx(), task_id="42")


# ---------------------------------------------------------------------------
# TestFromAC_EditTaskOutputSchema
# AC: edit_task added to outputSchema override loop (same as show_task/move_task/pick_task)
# ---------------------------------------------------------------------------


class TestFromAC_EditTaskOutputSchema:
    """edit_task outputSchema must be overridden to KanbanTask schema."""

    # AC: edit_task outputSchema equals KanbanTask.model_json_schema(by_alias=True)
    def test_edit_task_output_schema_equals_kanbantask_schema(self) -> None:
        """edit_task tool must have outputSchema set to KanbanTask.model_json_schema(by_alias=True)."""
        edit_tool = next(
            (t for t in mcp._tool_manager._tools.values() if t.name == "edit_task"),  # noqa: SLF001
            None,
        )
        assert edit_tool is not None, "edit_task tool must be registered in mcp"
        expected_schema = KanbanTask.model_json_schema(by_alias=True)
        actual_schema = edit_tool.fn_metadata.output_schema
        assert actual_schema == expected_schema, (
            "edit_task.fn_metadata.output_schema must equal KanbanTask.model_json_schema(by_alias=True). "
            f"Got: {actual_schema!r}"
        )

    # Boundary: schema must use alias key 'class' (not Python name 'class_')
    def test_edit_task_output_schema_uses_alias_class_key(self) -> None:
        """edit_task outputSchema must use alias 'class' (not Python field name 'class_')."""
        edit_tool = next(
            (t for t in mcp._tool_manager._tools.values() if t.name == "edit_task"),  # noqa: SLF001
            None,
        )
        assert edit_tool is not None, "edit_task tool must be registered"
        schema = edit_tool.fn_metadata.output_schema
        assert schema is not None, "edit_task outputSchema must not be None"
        assert isinstance(schema, dict), "outputSchema must be a dict"
        props = schema.get("properties", {})
        assert "class" in props, (
            "outputSchema must use alias 'class' key (not Python field 'class_')"
        )
        assert "class_" not in props, (
            "outputSchema must not use Python field name 'class_'"
        )


# ---------------------------------------------------------------------------
# TestFromAC_EditTaskSkillMdErrorGroup
# AC: SKILL.md moves edit_task from error-string group to ToolError group
# ---------------------------------------------------------------------------


class TestFromAC_EditTaskSkillMdErrorGroup:
    """SKILL.md error handling section must reflect edit_task new ToolError behavior."""

    # AC: edit_task appears in the ToolError group line (with show_task/move_task/pick_task)
    def test_skill_md_edit_task_in_tool_error_group(self) -> None:
        """SKILL.md must list edit_task in the ToolError group alongside show_task/move_task/pick_task."""
        content = _SKILL_MD.read_text(encoding="utf-8")
        tool_error_line = next(
            (
                line
                for line in content.splitlines()
                if "ToolError" in line and "show_task" in line
            ),
            None,
        )
        assert tool_error_line is not None, (
            "SKILL.md must have an error-handling line mentioning both ToolError and show_task"
        )
        assert "edit_task" in tool_error_line, (
            "edit_task must appear in the ToolError group in SKILL.md (same line as show_task)"
        )

    # AC: edit_task does NOT appear in the error-string return group
    def test_skill_md_edit_task_not_in_error_string_group(self) -> None:
        """SKILL.md must not list edit_task in the 'error: string' return group."""
        content = _SKILL_MD.read_text(encoding="utf-8")
        error_string_line = next(
            (
                line
                for line in content.splitlines()
                if "edit_task" in line and "error:" in line and "prefix" in line.lower()
            ),
            None,
        )
        assert error_string_line is None, (
            "edit_task must NOT appear in the error-string return group in SKILL.md. "
            f"Found: {error_string_line!r}"
        )
