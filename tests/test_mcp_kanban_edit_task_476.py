"""Tests for task #476: edit_task returns KanbanTask, raises ToolError, and new flag params.

Covers all AC items from architect review (including revised AC with flag-mapping tests):
  - edit_task returns KanbanTask object (not raw str)
  - edit_task raises ToolError on rc != 0 (not returns "error: ...")
  - edit_task catches ValidationError and raises ToolError with details
  - edit_task is included in outputSchema override loop (same as show_task/move_task/pick_task)
  - SKILL.md: edit_task in ToolError group, new params in edit_task row
  - Flag-mapping: --add-dep, --remove-dep, --parent, --title flags from AC #7
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

_SKILL_MD = Path(__file__).parent.parent / ".github" / "skills" / "h-mcp-kanban" / "SKILL.md"

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

    # AC: edit_task is listed in SKILL.md Tool Summary (params in MCP schema)
    def test_skill_md_edit_task_row_includes_new_params(self) -> None:
        """SKILL.md must have an edit_task table row."""
        content = _SKILL_MD.read_text(encoding="utf-8")
        edit_task_row = next(
            (line for line in content.splitlines() if "edit_task" in line and "|" in line),
            None,
        )
        assert edit_task_row is not None, "SKILL.md must have an edit_task table row"


# ---------------------------------------------------------------------------
# TestFromAC_EditTaskFlagMapping
# AC: flag-mapping assertions verifying _run_kanban.call_args contains
#     --add-dep, --remove-dep, --parent, --title flags (AC #7)
# ---------------------------------------------------------------------------


class TestFromAC_EditTaskFlagMapping:
    """Flag-mapping contract tests for new edit_task parameters (AC #7)."""

    # ------------------------------------------------------------------ add_dep

    # Happy: --add-dep {value} is passed when add_dep > 0
    @pytest.mark.asyncio
    async def test_add_dep_passes_flag_and_value_when_positive(self) -> None:
        """edit_task passes --add-dep {value} to _run_kanban when add_dep > 0."""
        with patch(
            "owlbear_mcp_kanban.server._run_kanban",
            new=AsyncMock(return_value=(_VALID_TASK_JSON, "", 0)),
        ) as mock_run:
            await edit_task(_make_mcp_ctx(), task_id="42", add_dep=7)

        argv = mock_run.call_args[0]
        assert "--add-dep" in argv, "--add-dep must be present when add_dep=7"
        idx = list(argv).index("--add-dep")
        assert argv[idx + 1] == "7", f"--add-dep value must be '7', got {argv[idx + 1]!r}"

    # Boundary: --add-dep NOT passed when add_dep == 0 (sentinel no-op)
    @pytest.mark.asyncio
    async def test_add_dep_omitted_when_zero(self) -> None:
        """edit_task must NOT pass --add-dep when add_dep=0 (zero is the sentinel no-op)."""
        with patch(
            "owlbear_mcp_kanban.server._run_kanban",
            new=AsyncMock(return_value=(_VALID_TASK_JSON, "", 0)),
        ) as mock_run:
            await edit_task(_make_mcp_ctx(), task_id="42", add_dep=0)

        argv = mock_run.call_args[0]
        assert "--add-dep" not in argv, "--add-dep must NOT appear when add_dep=0"

    # ------------------------------------------------------------------ remove_dep

    # Happy: --remove-dep {value} is passed when remove_dep > 0
    @pytest.mark.asyncio
    async def test_remove_dep_passes_flag_and_value_when_positive(self) -> None:
        """edit_task passes --remove-dep {value} to _run_kanban when remove_dep > 0."""
        with patch(
            "owlbear_mcp_kanban.server._run_kanban",
            new=AsyncMock(return_value=(_VALID_TASK_JSON, "", 0)),
        ) as mock_run:
            await edit_task(_make_mcp_ctx(), task_id="42", remove_dep=3)

        argv = mock_run.call_args[0]
        assert "--remove-dep" in argv, "--remove-dep must be present when remove_dep=3"
        idx = list(argv).index("--remove-dep")
        assert argv[idx + 1] == "3", f"--remove-dep value must be '3', got {argv[idx + 1]!r}"

    # Boundary: --remove-dep NOT passed when remove_dep == 0 (sentinel no-op)
    @pytest.mark.asyncio
    async def test_remove_dep_omitted_when_zero(self) -> None:
        """edit_task must NOT pass --remove-dep when remove_dep=0 (zero is the sentinel no-op)."""
        with patch(
            "owlbear_mcp_kanban.server._run_kanban",
            new=AsyncMock(return_value=(_VALID_TASK_JSON, "", 0)),
        ) as mock_run:
            await edit_task(_make_mcp_ctx(), task_id="42", remove_dep=0)

        argv = mock_run.call_args[0]
        assert "--remove-dep" not in argv, "--remove-dep must NOT appear when remove_dep=0"

    # ------------------------------------------------------------------ parent (edit_task specific)

    # Happy: --parent {value} is passed when parent > 0
    @pytest.mark.asyncio
    async def test_parent_passes_flag_and_value_when_positive(self) -> None:
        """edit_task passes --parent {value} to _run_kanban when parent > 0."""
        with patch(
            "owlbear_mcp_kanban.server._run_kanban",
            new=AsyncMock(return_value=(_VALID_TASK_JSON, "", 0)),
        ) as mock_run:
            await edit_task(_make_mcp_ctx(), task_id="42", parent=10)

        argv = mock_run.call_args[0]
        assert "--parent" in argv, "--parent must be present when parent=10"
        idx = list(argv).index("--parent")
        assert argv[idx + 1] == "10", f"--parent value must be '10', got {argv[idx + 1]!r}"

    # Boundary: --parent NOT passed when parent == 0 (sentinel no-op)
    @pytest.mark.asyncio
    async def test_parent_omitted_when_zero(self) -> None:
        """edit_task must NOT pass --parent when parent=0 (zero is the sentinel no-op)."""
        with patch(
            "owlbear_mcp_kanban.server._run_kanban",
            new=AsyncMock(return_value=(_VALID_TASK_JSON, "", 0)),
        ) as mock_run:
            await edit_task(_make_mcp_ctx(), task_id="42", parent=0)

        argv = mock_run.call_args[0]
        assert "--parent" not in argv, "--parent must NOT appear when parent=0"

    # ------------------------------------------------------------------ title

    # Happy: --title {value} is passed when title is non-empty
    @pytest.mark.asyncio
    async def test_title_passes_flag_and_value_when_non_empty(self) -> None:
        """edit_task passes --title {value} to _run_kanban when title is non-empty."""
        with patch(
            "owlbear_mcp_kanban.server._run_kanban",
            new=AsyncMock(return_value=(_VALID_TASK_JSON, "", 0)),
        ) as mock_run:
            await edit_task(_make_mcp_ctx(), task_id="42", title="New Title")

        argv = mock_run.call_args[0]
        assert "--title" in argv, "--title must be present when title='New Title'"
        idx = list(argv).index("--title")
        assert argv[idx + 1] == "New Title", (
            f"--title value must be 'New Title', got {argv[idx + 1]!r}"
        )

    # Boundary: --title NOT passed when title is empty string (default)
    @pytest.mark.asyncio
    async def test_title_omitted_when_empty(self) -> None:
        """edit_task must NOT pass --title when title='' (empty string default)."""
        with patch(
            "owlbear_mcp_kanban.server._run_kanban",
            new=AsyncMock(return_value=(_VALID_TASK_JSON, "", 0)),
        ) as mock_run:
            await edit_task(_make_mcp_ctx(), task_id="42", title="")

        argv = mock_run.call_args[0]
        assert "--title" not in argv, "--title must NOT appear when title=''"

    # ------------------------------------------------------------------ combined flags

    # Edge: add_dep and remove_dep can be set in same call, both flags appear
    @pytest.mark.asyncio
    async def test_add_dep_and_remove_dep_both_passed_when_both_positive(self) -> None:
        """Both --add-dep and --remove-dep must appear when both params > 0."""
        with patch(
            "owlbear_mcp_kanban.server._run_kanban",
            new=AsyncMock(return_value=(_VALID_TASK_JSON, "", 0)),
        ) as mock_run:
            await edit_task(_make_mcp_ctx(), task_id="42", add_dep=5, remove_dep=2)

        argv = mock_run.call_args[0]
        assert "--add-dep" in argv, "--add-dep must appear when add_dep=5"
        assert "--remove-dep" in argv, "--remove-dep must appear when remove_dep=2"

    # Edge: all four new params set together — all four flags appear
    @pytest.mark.asyncio
    async def test_all_new_params_positive_all_flags_appear(self) -> None:
        """All four new flags (--add-dep, --remove-dep, --parent, --title) appear when all params set."""
        with patch(
            "owlbear_mcp_kanban.server._run_kanban",
            new=AsyncMock(return_value=(_VALID_TASK_JSON, "", 0)),
        ) as mock_run:
            await edit_task(
                _make_mcp_ctx(),
                task_id="42",
                add_dep=1,
                remove_dep=2,
                parent=3,
                title="Updated",
            )

        argv = mock_run.call_args[0]
        assert "--add-dep" in argv
        assert "--remove-dep" in argv
        assert "--parent" in argv
        assert "--title" in argv


# ---------------------------------------------------------------------------
# TestFromAC_EditTaskIdempotentHint
# AC: edit_task ToolAnnotations include explicit idempotentHint=False
#     (add_dep/remove_dep are non-idempotent operations)
# ---------------------------------------------------------------------------


class TestFromAC_EditTaskIdempotentHint:
    """edit_task ToolAnnotations must set idempotentHint=False explicitly."""

    # AC6: idempotentHint is explicitly False (not None/True)
    def test_idempotent_hint_is_explicitly_false(self) -> None:
        """edit_task annotations.idempotentHint must be explicitly False (add_dep/remove_dep are non-idempotent)."""
        edit_tool = next(
            (t for t in mcp._tool_manager._tools.values() if t.name == "edit_task"),  # noqa: SLF001
            None,
        )
        assert edit_tool is not None, "edit_task tool must be registered in mcp"
        assert edit_tool.annotations is not None, "edit_task must have ToolAnnotations"
        assert edit_tool.annotations.idempotentHint is False, (
            f"edit_task.annotations.idempotentHint must be explicitly False, "
            f"got {edit_tool.annotations.idempotentHint!r}. "
            "add_dep/remove_dep mutations are non-idempotent."
        )

    # Boundary: idempotentHint must not be None (unset is insufficient — AC requires explicit False)
    def test_idempotent_hint_is_not_none(self) -> None:
        """idempotentHint=None is not acceptable — must be explicitly set to False."""
        edit_tool = next(
            (t for t in mcp._tool_manager._tools.values() if t.name == "edit_task"),  # noqa: SLF001
            None,
        )
        assert edit_tool is not None
        assert edit_tool.annotations.idempotentHint is not None, (
            "edit_task.annotations.idempotentHint must not be None; "
            "the AC requires an *explicit* idempotentHint=False in the @mcp.tool decorator."
        )


# ---------------------------------------------------------------------------
# TestFromAC_JsonFlagAlwaysPresent
# AC9: edit_task unconditionally appends --json to args
# ---------------------------------------------------------------------------


class TestFromAC_JsonFlagAlwaysPresent:
    """--json must always appear in _run_kanban call regardless of params."""

    # Happy: --json present with minimal args (task_id only)
    @pytest.mark.asyncio
    async def test_json_flag_present_with_task_id_only(self) -> None:
        """--json must appear in _run_kanban args even when only task_id is provided."""
        with patch(
            "owlbear_mcp_kanban.server._run_kanban",
            new=AsyncMock(return_value=(_VALID_TASK_JSON, "", 0)),
        ) as mock_run:
            await edit_task(_make_mcp_ctx(), task_id="42")

        argv = mock_run.call_args[0]
        assert "--json" in argv, "--json must always be present in edit_task args"

    # Edge: --json present when all params are at their defaults
    @pytest.mark.asyncio
    async def test_json_flag_present_when_all_params_default(self) -> None:
        """--json must appear even when all optional params are at their zero/empty defaults."""
        with patch(
            "owlbear_mcp_kanban.server._run_kanban",
            new=AsyncMock(return_value=(_VALID_TASK_JSON, "", 0)),
        ) as mock_run:
            await edit_task(
                _make_mcp_ctx(),
                task_id="42",
                add_dep=0,
                remove_dep=0,
                parent=0,
                title="",
                body="",
                status="",
                priority="",
                tags="",
            )

        argv = mock_run.call_args[0]
        assert "--json" in argv, "--json must be present regardless of param values"

    # Edge: --json present when all new params are set
    @pytest.mark.asyncio
    async def test_json_flag_present_when_all_new_params_set(self) -> None:
        """--json must appear when all new params (add_dep, remove_dep, parent, title) are set."""
        with patch(
            "owlbear_mcp_kanban.server._run_kanban",
            new=AsyncMock(return_value=(_VALID_TASK_JSON, "", 0)),
        ) as mock_run:
            await edit_task(
                _make_mcp_ctx(),
                task_id="42",
                add_dep=1,
                remove_dep=2,
                parent=3,
                title="New",
            )

        argv = mock_run.call_args[0]
        assert "--json" in argv, "--json must be unconditionally appended"

    # Boundary: --json must be the LAST element in the args list
    @pytest.mark.asyncio
    async def test_json_flag_is_last_arg(self) -> None:
        """--json must be appended at the end of the args list (unconditional final append)."""
        with patch(
            "owlbear_mcp_kanban.server._run_kanban",
            new=AsyncMock(return_value=(_VALID_TASK_JSON, "", 0)),
        ) as mock_run:
            await edit_task(_make_mcp_ctx(), task_id="42", status="done")

        argv = list(mock_run.call_args[0])
        assert argv[-1] == "--json", (
            f"--json must be the last element in args, got last element {argv[-1]!r}"
        )


# ---------------------------------------------------------------------------
# _FAKE_TASK_JSON: realistic fixture with depends_on, parent, blocked, body fields
# (AC11: fixture must include these optional fields for realistic validation)
# ---------------------------------------------------------------------------

_FAKE_TASK_JSON = json.dumps(
    {
        "id": 99,
        "title": "Fake Task With All Fields",
        "status": "in-progress",
        "priority": "needed",
        "created": "2026-01-15T10:00:00Z",
        "updated": "2026-04-01T12:34:56Z",
        "class": "standard",
        "started": "2026-02-01T08:00:00Z",
        "completed": None,
        "assignee": None,
        "claimed_by": "builder",
        "claimed_at": "2026-03-01T09:00:00Z",
        "tags": ["scope:mcp", "type:build"],
        "due": None,
        "estimate": None,
        "parent": 10,
        "depends_on": [5, 7],
        "blocked": False,
        "block_reason": None,
        "body": "## AC\n- implement stuff\n- write tests",
        "file": "/fake/kanban/tasks/99-fake.md",
    }
)


class TestFromAC_FakeTaskJsonFixture:
    """Tests verifying edit_task validates JSON containing all optional fields (AC11)."""

    # Happy: edit_task validates realistic JSON with depends_on, parent, blocked, body
    @pytest.mark.asyncio
    async def test_validates_json_with_depends_on_field(self) -> None:
        """KanbanTask.model_validate_json must parse depends_on list correctly."""
        with _patch_run(stdout=_FAKE_TASK_JSON):
            result = await edit_task(_make_mcp_ctx(), task_id="99")
        assert result.depends_on == [5, 7], (
            f"depends_on must be [5, 7], got {result.depends_on!r}"
        )

    # Happy: parent field is parsed correctly
    @pytest.mark.asyncio
    async def test_validates_json_with_parent_field(self) -> None:
        """KanbanTask.model_validate_json must parse parent field correctly."""
        with _patch_run(stdout=_FAKE_TASK_JSON):
            result = await edit_task(_make_mcp_ctx(), task_id="99")
        assert result.parent == 10, f"parent must be 10, got {result.parent!r}"

    # Happy: blocked field is parsed correctly
    @pytest.mark.asyncio
    async def test_validates_json_with_blocked_field(self) -> None:
        """KanbanTask.model_validate_json must parse blocked field correctly."""
        with _patch_run(stdout=_FAKE_TASK_JSON):
            result = await edit_task(_make_mcp_ctx(), task_id="99")
        assert result.blocked is False, f"blocked must be False, got {result.blocked!r}"

    # Happy: body field is parsed correctly
    @pytest.mark.asyncio
    async def test_validates_json_with_body_field(self) -> None:
        """KanbanTask.model_validate_json must parse the body field correctly."""
        with _patch_run(stdout=_FAKE_TASK_JSON):
            result = await edit_task(_make_mcp_ctx(), task_id="99")
        assert result.body is not None, "body must not be None when provided in JSON"
        assert "AC" in result.body, f"body must contain task text, got {result.body!r}"

    # Edge: validate KanbanTask is returned (not just passes validation silently)
    @pytest.mark.asyncio
    async def test_realistic_fixture_returns_kanbantask_instance(self) -> None:
        """edit_task with realistic full-field JSON must return a KanbanTask instance."""
        with _patch_run(stdout=_FAKE_TASK_JSON):
            result = await edit_task(_make_mcp_ctx(), task_id="99")
        assert isinstance(result, KanbanTask), (
            f"edit_task must return KanbanTask even with all optional fields set, got {type(result)}"
        )
