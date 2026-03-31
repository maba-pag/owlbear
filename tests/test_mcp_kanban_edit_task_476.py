"""Failing tests for task #476: Add dep/parent/title params to edit_task, switch to JSON output.

Covers all AC items from #476:
  - edit_task accepts add_dep: int = 0 parameter; when > 0, appends --add-dep {value}
  - edit_task accepts remove_dep: int = 0 parameter; when > 0, appends --remove-dep {value}
  - edit_task accepts parent: int = 0 parameter; when > 0, appends --parent {value}
  - edit_task accepts title: str = "" parameter; when non-empty, appends --title {value}
  - edit_task appends --json to args unconditionally
  - edit_task returns the raw JSON stdout from kanban-md
  - skills/mcp-kanban/SKILL.md edit_task row updated to include new parameters
  - ruff clean

All tests FAIL in RED phase — the current implementation does not have
add_dep/remove_dep/parent/title params, does not append --json, and does not
return raw JSON.
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlbear_mcp_kanban.server import (  # type: ignore[import]
    AppContext,
    edit_task,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SKILL_MD = Path(__file__).parent.parent / "skills" / "mcp-kanban" / "SKILL.md"

_SAMPLE_TASK_JSON = json.dumps({
    "id": "476",
    "title": "Original Title",
    "status": "todo",
    "priority": "needed",
    "created": "2026-01-01T00:00:00Z",
    "updated": "2026-03-31T00:00:00Z",
    "parent": 0,
    "class": "standard",
    "file": "/kanban/tasks/476-task.md",
})

_SAMPLE_TASK_WITH_PARENT_JSON = json.dumps({
    "id": "476",
    "title": "Child task",
    "status": "todo",
    "priority": "needed",
    "created": "2026-01-01T00:00:00Z",
    "updated": "2026-03-31T00:00:00Z",
    "parent": 10,
    "class": "standard",
    "file": "/kanban/tasks/476-task.md",
})


def _make_app_ctx() -> AppContext:
    return AppContext(kanban_bin=Path("/fake/kanban-md"), kanban_dir=Path("/fake/kanban"))


def _make_mcp_ctx(app_ctx: AppContext | None = None) -> MagicMock:
    ctx = MagicMock()
    ctx.request_context.lifespan_context = app_ctx or _make_app_ctx()
    return ctx


def _patch_run(stdout: str = _SAMPLE_TASK_JSON, stderr: str = "", rc: int = 0) -> Any:
    return patch(
        "owlbear_mcp_kanban.server._run_kanban",
        new=AsyncMock(return_value=(stdout, stderr, rc)),
    )


# ---------------------------------------------------------------------------
# TestFromAC_EditTaskSignature — parameter contract
# ---------------------------------------------------------------------------


class TestFromAC_EditTaskSignature:
    """Tests that edit_task exposes the new parameter contract from #476 AC."""

    # AC: edit_task accepts add_dep: int = 0 parameter
    def test_has_add_dep_parameter_with_int_default_zero(self) -> None:
        """edit_task must accept `add_dep: int = 0`."""
        sig = inspect.signature(edit_task)
        assert "add_dep" in sig.parameters, "edit_task must have `add_dep` parameter"
        param = sig.parameters["add_dep"]
        assert param.default == 0, "`add_dep` default must be 0"

    # AC: edit_task accepts remove_dep: int = 0 parameter
    def test_has_remove_dep_parameter_with_int_default_zero(self) -> None:
        """edit_task must accept `remove_dep: int = 0`."""
        sig = inspect.signature(edit_task)
        assert "remove_dep" in sig.parameters, "edit_task must have `remove_dep` parameter"
        param = sig.parameters["remove_dep"]
        assert param.default == 0, "`remove_dep` default must be 0"

    # AC: edit_task accepts parent: int = 0 parameter
    def test_has_parent_parameter_with_int_default_zero(self) -> None:
        """edit_task must accept `parent: int = 0`."""
        sig = inspect.signature(edit_task)
        assert "parent" in sig.parameters, "edit_task must have `parent` parameter"
        param = sig.parameters["parent"]
        assert param.default == 0, "`parent` default must be 0"

    # AC: edit_task accepts title: str = "" parameter
    def test_has_title_parameter_with_str_default_empty(self) -> None:
        """edit_task must accept `title: str = \"\"`."""
        sig = inspect.signature(edit_task)
        assert "title" in sig.parameters, "edit_task must have `title` parameter"
        param = sig.parameters["title"]
        assert param.default == "", "`title` default must be empty string"


# ---------------------------------------------------------------------------
# TestFromAC_EditTaskAddDep — --add-dep argument building
# ---------------------------------------------------------------------------


class TestFromAC_EditTaskAddDep:
    """Unit tests for the add_dep parameter argument building."""

    # AC: Unit: --add-dep 42 in args when add_dep=42
    @pytest.mark.asyncio
    async def test_add_dep_positive_appends_add_dep_flag(self) -> None:
        """When add_dep=42, --add-dep 42 must appear in the args passed to _run_kanban."""
        with _patch_run() as mock_run:
            await edit_task(_make_mcp_ctx(), task_id="42", add_dep=42)
        call_args = mock_run.call_args[0]
        assert "--add-dep" in call_args, "--add-dep flag must be passed when add_dep > 0"
        idx = list(call_args).index("--add-dep")
        assert call_args[idx + 1] == "42", "--add-dep must be followed by string '42'"

    # AC: Unit: no --add-dep when add_dep=0
    @pytest.mark.asyncio
    async def test_add_dep_zero_does_not_append_add_dep_flag(self) -> None:
        """When add_dep=0, --add-dep must NOT appear in args passed to _run_kanban."""
        with _patch_run() as mock_run:
            await edit_task(_make_mcp_ctx(), task_id="42", add_dep=0)
        call_args = mock_run.call_args[0]
        assert "--add-dep" not in call_args, "--add-dep must not be passed when add_dep is 0"

    # Edge: boundary value 1 (minimum positive)
    @pytest.mark.asyncio
    async def test_add_dep_boundary_value_one(self) -> None:
        """add_dep=1 (minimum positive) must append --add-dep 1."""
        with _patch_run() as mock_run:
            await edit_task(_make_mcp_ctx(), task_id="42", add_dep=1)
        call_args = mock_run.call_args[0]
        assert "--add-dep" in call_args, "--add-dep must be added for add_dep=1"
        idx = list(call_args).index("--add-dep")
        assert call_args[idx + 1] == "1", "--add-dep value must be '1'"

    # Edge: negative add_dep treated like zero (no --add-dep)
    @pytest.mark.asyncio
    async def test_add_dep_negative_does_not_append_add_dep_flag(self) -> None:
        """add_dep=-1 (invalid) must not append --add-dep (same guard as add_dep=0)."""
        with _patch_run() as mock_run:
            await edit_task(_make_mcp_ctx(), task_id="42", add_dep=-1)
        call_args = mock_run.call_args[0]
        assert "--add-dep" not in call_args, "--add-dep must not be passed when add_dep <= 0"


# ---------------------------------------------------------------------------
# TestFromAC_EditTaskRemoveDep — --remove-dep argument building
# ---------------------------------------------------------------------------


class TestFromAC_EditTaskRemoveDep:
    """Unit tests for the remove_dep parameter argument building."""

    # AC: Unit: --remove-dep 42 in args when remove_dep=42
    @pytest.mark.asyncio
    async def test_remove_dep_positive_appends_remove_dep_flag(self) -> None:
        """When remove_dep=42, --remove-dep 42 must appear in the args passed to _run_kanban."""
        with _patch_run() as mock_run:
            await edit_task(_make_mcp_ctx(), task_id="42", remove_dep=42)
        call_args = mock_run.call_args[0]
        assert "--remove-dep" in call_args, "--remove-dep flag must be passed when remove_dep > 0"
        idx = list(call_args).index("--remove-dep")
        assert call_args[idx + 1] == "42", "--remove-dep must be followed by string '42'"

    # AC: Unit: no --remove-dep when remove_dep=0
    @pytest.mark.asyncio
    async def test_remove_dep_zero_does_not_append_remove_dep_flag(self) -> None:
        """When remove_dep=0, --remove-dep must NOT appear in args passed to _run_kanban."""
        with _patch_run() as mock_run:
            await edit_task(_make_mcp_ctx(), task_id="42", remove_dep=0)
        call_args = mock_run.call_args[0]
        assert "--remove-dep" not in call_args, "--remove-dep must not be passed when remove_dep is 0"

    # Edge: boundary value 1 (minimum positive)
    @pytest.mark.asyncio
    async def test_remove_dep_boundary_value_one(self) -> None:
        """remove_dep=1 (minimum positive) must append --remove-dep 1."""
        with _patch_run() as mock_run:
            await edit_task(_make_mcp_ctx(), task_id="42", remove_dep=1)
        call_args = mock_run.call_args[0]
        assert "--remove-dep" in call_args, "--remove-dep must be added for remove_dep=1"
        idx = list(call_args).index("--remove-dep")
        assert call_args[idx + 1] == "1", "--remove-dep value must be '1'"

    # Edge: negative remove_dep treated like zero (no --remove-dep)
    @pytest.mark.asyncio
    async def test_remove_dep_negative_does_not_append_remove_dep_flag(self) -> None:
        """remove_dep=-1 (invalid) must not append --remove-dep."""
        with _patch_run() as mock_run:
            await edit_task(_make_mcp_ctx(), task_id="42", remove_dep=-1)
        call_args = mock_run.call_args[0]
        assert "--remove-dep" not in call_args, "--remove-dep must not be passed when remove_dep <= 0"

    # Edge: add_dep and remove_dep are independent — both can be non-zero simultaneously
    @pytest.mark.asyncio
    async def test_add_dep_and_remove_dep_both_nonzero(self) -> None:
        """add_dep=5 and remove_dep=3 can both be passed simultaneously."""
        with _patch_run() as mock_run:
            await edit_task(_make_mcp_ctx(), task_id="42", add_dep=5, remove_dep=3)
        call_args = mock_run.call_args[0]
        assert "--add-dep" in call_args, "--add-dep must appear when add_dep=5"
        assert "--remove-dep" in call_args, "--remove-dep must appear when remove_dep=3"


# ---------------------------------------------------------------------------
# TestFromAC_EditTaskParent — --parent argument building
# ---------------------------------------------------------------------------


class TestFromAC_EditTaskParent:
    """Unit tests for the parent parameter argument building."""

    # AC: Unit: --parent 10 in args when parent=10
    @pytest.mark.asyncio
    async def test_parent_positive_appends_parent_flag(self) -> None:
        """When parent=10, --parent 10 must appear in the args passed to _run_kanban."""
        with _patch_run() as mock_run:
            await edit_task(_make_mcp_ctx(), task_id="42", parent=10)
        call_args = mock_run.call_args[0]
        assert "--parent" in call_args, "--parent flag must be passed when parent > 0"
        idx = list(call_args).index("--parent")
        assert call_args[idx + 1] == "10", "--parent must be followed by string '10'"

    # AC: Unit: no --parent when parent=0
    @pytest.mark.asyncio
    async def test_parent_zero_does_not_append_parent_flag(self) -> None:
        """When parent=0, --parent must NOT appear in args passed to _run_kanban."""
        with _patch_run() as mock_run:
            await edit_task(_make_mcp_ctx(), task_id="42", parent=0)
        call_args = mock_run.call_args[0]
        assert "--parent" not in call_args, "--parent must not be passed when parent is 0"

    # Edge: boundary value 1 (minimum positive)
    @pytest.mark.asyncio
    async def test_parent_boundary_value_one(self) -> None:
        """parent=1 (minimum positive) must append --parent 1."""
        with _patch_run() as mock_run:
            await edit_task(_make_mcp_ctx(), task_id="42", parent=1)
        call_args = mock_run.call_args[0]
        assert "--parent" in call_args, "--parent must be added for parent=1"
        idx = list(call_args).index("--parent")
        assert call_args[idx + 1] == "1", "--parent value must be '1'"

    # Edge: negative parent treated like zero (no --parent)
    @pytest.mark.asyncio
    async def test_parent_negative_does_not_append_parent_flag(self) -> None:
        """parent=-1 (invalid) must not append --parent."""
        with _patch_run() as mock_run:
            await edit_task(_make_mcp_ctx(), task_id="42", parent=-1)
        call_args = mock_run.call_args[0]
        assert "--parent" not in call_args, "--parent must not be passed when parent <= 0"


# ---------------------------------------------------------------------------
# TestFromAC_EditTaskTitle — --title argument building
# ---------------------------------------------------------------------------


class TestFromAC_EditTaskTitle:
    """Unit tests for the title parameter argument building."""

    # AC: Unit: --title "New Name" in args when title="New Name"
    @pytest.mark.asyncio
    async def test_title_non_empty_appends_title_flag(self) -> None:
        """When title='New Name', --title 'New Name' must appear in args passed to _run_kanban."""
        with _patch_run() as mock_run:
            await edit_task(_make_mcp_ctx(), task_id="42", title="New Name")
        call_args = mock_run.call_args[0]
        assert "--title" in call_args, "--title flag must be passed when title is non-empty"
        idx = list(call_args).index("--title")
        assert call_args[idx + 1] == "New Name", "--title must be followed by 'New Name'"

    # AC: Unit: no --title when title=""
    @pytest.mark.asyncio
    async def test_title_empty_does_not_append_title_flag(self) -> None:
        """When title='', --title must NOT appear in args passed to _run_kanban."""
        with _patch_run() as mock_run:
            await edit_task(_make_mcp_ctx(), task_id="42", title="")
        call_args = mock_run.call_args[0]
        assert "--title" not in call_args, "--title must not be passed when title is empty"

    # Edge: title with only whitespace treated as non-empty (preserves caller intent)
    @pytest.mark.asyncio
    async def test_title_whitespace_only_appends_title_flag(self) -> None:
        """title='   ' (whitespace only) must still append --title (caller's responsibility to validate)."""
        with _patch_run() as mock_run:
            await edit_task(_make_mcp_ctx(), task_id="42", title="   ")
        call_args = mock_run.call_args[0]
        assert "--title" in call_args, "--title must be passed when title is whitespace-only string"

    # Edge: title with special characters
    @pytest.mark.asyncio
    async def test_title_with_special_characters(self) -> None:
        """title with special chars must be passed verbatim to _run_kanban."""
        special_title = "Fix: handle `None` in #42 [urgent]"
        with _patch_run() as mock_run:
            await edit_task(_make_mcp_ctx(), task_id="42", title=special_title)
        call_args = mock_run.call_args[0]
        assert "--title" in call_args, "--title must be passed with special character title"
        idx = list(call_args).index("--title")
        assert call_args[idx + 1] == special_title, "--title value must be passed verbatim"


# ---------------------------------------------------------------------------
# TestFromAC_EditTaskJsonFlag — --json unconditional appending
# ---------------------------------------------------------------------------


class TestFromAC_EditTaskJsonFlag:
    """Tests that --json is appended to edit_task args unconditionally."""

    # AC: edit_task appends --json to args unconditionally
    @pytest.mark.asyncio
    async def test_json_flag_always_present_with_no_optional_params(self) -> None:
        """--json must be present when only task_id is provided."""
        with _patch_run() as mock_run:
            await edit_task(_make_mcp_ctx(), task_id="42")
        call_args = mock_run.call_args[0]
        assert "--json" in call_args, "--json must always be appended to edit_task args"

    # AC: --json always present with all new params
    @pytest.mark.asyncio
    async def test_json_flag_always_present_with_all_new_params(self) -> None:
        """--json must be present when all new optional params are supplied."""
        with _patch_run() as mock_run:
            await edit_task(_make_mcp_ctx(), task_id="42", add_dep=5, remove_dep=3, parent=10, title="New")
        call_args = mock_run.call_args[0]
        assert "--json" in call_args, "--json must always be appended even with all new params"

    # AC: --json always present with existing params (not broken by new additions)
    @pytest.mark.asyncio
    async def test_json_flag_present_with_existing_params(self) -> None:
        """--json must still be present when using existing params (body, status, etc.)."""
        with _patch_run() as mock_run:
            await edit_task(_make_mcp_ctx(), task_id="42", body="updated body", status="in-progress")
        call_args = mock_run.call_args[0]
        assert "--json" in call_args, "--json must be present regardless of which params are used"

    # Boundary: --json must be last or present at any position — just present
    @pytest.mark.asyncio
    async def test_json_flag_present_with_boolean_params(self) -> None:
        """--json must be present even when boolean flags (unblock, release, timestamp) are set."""
        with _patch_run() as mock_run:
            await edit_task(_make_mcp_ctx(), task_id="42", unblock=True, release=True, timestamp=True)
        call_args = mock_run.call_args[0]
        assert "--json" in call_args, "--json must be present with boolean params set"


# ---------------------------------------------------------------------------
# TestFromAC_EditTaskReturn — return value contract
# ---------------------------------------------------------------------------


class TestFromAC_EditTaskReturn:
    """Tests that edit_task returns the raw JSON stdout from kanban-md."""

    # AC: edit_task returns the raw JSON stdout from kanban-md
    @pytest.mark.asyncio
    async def test_returns_raw_json_stdout_on_success(self) -> None:
        """edit_task must pass --json to kanban-md and return the raw JSON stdout."""
        with _patch_run(stdout=_SAMPLE_TASK_JSON) as mock_run:
            result = await edit_task(_make_mcp_ctx(), task_id="476")
        call_args = mock_run.call_args[0]
        assert "--json" in call_args, (
            "edit_task must pass --json to kanban-md to receive JSON output"
        )
        assert result == _SAMPLE_TASK_JSON, (
            "edit_task must return the raw JSON stdout, not a transformed/summarised value"
        )

    # AC: JSON task object must include expected fields
    @pytest.mark.asyncio
    async def test_returned_json_is_parseable_task_object(self) -> None:
        """Raw JSON stdout must be parseable and contain expected fields."""
        with _patch_run(stdout=_SAMPLE_TASK_JSON) as mock_run:
            result = await edit_task(_make_mcp_ctx(), task_id="476")
        call_args = mock_run.call_args[0]
        assert "--json" in call_args, "--json must be in args to produce parseable JSON"
        task = json.loads(result)
        required_fields = {"id", "title", "status", "priority", "created", "updated", "parent", "class", "file"}
        missing = required_fields - task.keys()
        assert not missing, f"Returned JSON task object is missing fields: {missing}"

    # Error path: when rc != 0, error string is returned; --json is still passed
    @pytest.mark.asyncio
    async def test_returns_error_string_on_nonzero_rc(self) -> None:
        """When _run_kanban returns rc != 0, edit_task must return an 'error: ...' string.

        --json is still appended unconditionally even on the error path.
        """
        with _patch_run(stdout="", stderr="task not found", rc=1) as mock_run:
            result = await edit_task(_make_mcp_ctx(), task_id="999")
        call_args = mock_run.call_args[0]
        assert "--json" in call_args, "--json must be passed unconditionally, even on error path"
        assert result.startswith("error:"), (
            "When kanban-md exits non-zero, edit_task must return 'error: ...' string"
        )

    # Edge: returned JSON reflects parent when parent was set
    @pytest.mark.asyncio
    async def test_returns_json_with_parent_field_when_parent_set(self) -> None:
        """When parent=10 produces JSON with parent=10, that JSON is returned verbatim."""
        with _patch_run(stdout=_SAMPLE_TASK_WITH_PARENT_JSON):
            result = await edit_task(_make_mcp_ctx(), task_id="476", parent=10)
        task = json.loads(result)
        assert task["parent"] == 10, "Returned JSON must include the parent field value from kanban-md"


# ---------------------------------------------------------------------------
# TestFromAC_EditTaskSkillDoc — SKILL.md documentation contract
# ---------------------------------------------------------------------------


class TestFromAC_EditTaskSkillDoc:
    """Tests that skills/mcp-kanban/SKILL.md documents the new edit_task parameters."""

    # AC: skills/mcp-kanban/SKILL.md edit_task row updated to include new parameters
    def test_skill_md_mentions_add_dep(self) -> None:
        """SKILL.md must mention add_dep in the edit_task documentation."""
        content = _SKILL_MD.read_text(encoding="utf-8")
        assert "add_dep" in content, (
            "skills/mcp-kanban/SKILL.md must document the `add_dep` parameter for edit_task"
        )

    def test_skill_md_mentions_remove_dep(self) -> None:
        """SKILL.md must mention remove_dep in the edit_task documentation."""
        content = _SKILL_MD.read_text(encoding="utf-8")
        assert "remove_dep" in content, (
            "skills/mcp-kanban/SKILL.md must document the `remove_dep` parameter for edit_task"
        )

    def test_skill_md_mentions_parent_for_edit_task(self) -> None:
        """SKILL.md must mention parent in the edit_task documentation."""
        content = _SKILL_MD.read_text(encoding="utf-8")
        assert "parent" in content, (
            "skills/mcp-kanban/SKILL.md must document the `parent` parameter for edit_task"
        )

    def test_skill_md_mentions_title_for_edit_task(self) -> None:
        """SKILL.md edit_task row must mention the title parameter."""
        content = _SKILL_MD.read_text(encoding="utf-8")
        # "title" appears in create_task already — check it appears in the edit_task row
        edit_task_line = next(
            (line for line in content.splitlines() if "edit_task" in line and "|" in line and "task_id" in line),
            None,
        )
        assert edit_task_line is not None, (
            "skills/mcp-kanban/SKILL.md must have a table row for edit_task with parameters"
        )
        assert "title" in edit_task_line, (
            "skills/mcp-kanban/SKILL.md edit_task row must document the `title` parameter"
        )
