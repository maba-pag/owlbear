"""Failing tests for task #475: Add status and parent params to create_task, switch to JSON output.

Covers all AC items from #475:
  - create_task accepts status: str = "" parameter; non-empty appends --status {value}
  - create_task accepts parent: int = 0 parameter; >0 appends --parent {value}
  - create_task appends --json to args unconditionally
  - create_task returns the raw JSON stdout from kanban-md
  - Unit: --status backlog in args when status="backlog"; no --status when empty
  - Unit: --parent 42 in args when parent=42; no --parent when parent=0; --json always present
  - Integration: create with status override + show roundtrip confirms correct status
  - Integration: create with parent + show roundtrip confirms parent field
  - .github/skills/h-mcp-kanban/SKILL.md create_task row updated to include status and parent

All tests FAIL in RED phase — the current implementation does not have status/parent params,
does not append --json, and does not return raw JSON.
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
    create_task,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SKILL_MD = Path(__file__).parent.parent / ".github" / "skills" / "h-mcp-kanban" / "SKILL.md"

_SAMPLE_TASK_JSON = json.dumps({
    "id": "99",
    "title": "Test task",
    "status": "backlog",
    "priority": "important",
    "created": "2026-01-01T00:00:00Z",
    "updated": "2026-01-01T00:00:00Z",
    "parent": 0,
    "class": "standard",
    "file": "/kanban/tasks/99-test-task.md",
})

_SAMPLE_TASK_WITH_PARENT_JSON = json.dumps({
    "id": "100",
    "title": "Child task",
    "status": "todo",
    "priority": "important",
    "created": "2026-01-01T00:00:00Z",
    "updated": "2026-01-01T00:00:00Z",
    "parent": 42,
    "class": "standard",
    "file": "/kanban/tasks/100-child-task.md",
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
# TestFromAC_CreateTaskSignature — parameter contract
# ---------------------------------------------------------------------------


class TestFromAC_CreateTaskSignature:
    """Tests that create_task exposes the new parameter contract from #475 AC."""

    # AC: create_task accepts status: str = "" parameter
    def test_has_status_parameter_with_str_default_empty(self) -> None:
        """create_task must accept `status: str = \"\"`."""
        sig = inspect.signature(create_task)
        assert "status" in sig.parameters, "create_task must have `status` parameter"
        param = sig.parameters["status"]
        assert param.default == "", "`status` default must be empty string"

    # AC: create_task accepts parent: int = 0 parameter
    def test_has_parent_parameter_with_int_default_zero(self) -> None:
        """create_task must accept `parent: int = 0`."""
        sig = inspect.signature(create_task)
        assert "parent" in sig.parameters, "create_task must have `parent` parameter"
        param = sig.parameters["parent"]
        assert param.default == 0, "`parent` default must be 0"


# ---------------------------------------------------------------------------
# TestFromAC_CreateTaskArgs — argument building (unit tests)
# ---------------------------------------------------------------------------


class TestFromAC_CreateTaskArgs:
    """Unit tests verifying correct CLI args are built from the new parameters."""

    # AC: Unit: --status backlog in args when status="backlog"
    @pytest.mark.asyncio
    async def test_status_non_empty_appends_status_flag(self) -> None:
        """When status='backlog', --status backlog must appear in the args passed to _run_kanban."""
        with _patch_run() as mock_run:
            await create_task(_make_mcp_ctx(), title="T", status="backlog")
        call_args = mock_run.call_args[0]  # positional args: (ctx, *cmd_args)
        assert "--status" in call_args, "--status flag must be passed when status is non-empty"
        idx = list(call_args).index("--status")
        assert call_args[idx + 1] == "backlog", "--status must be followed by 'backlog'"

    # AC: Unit: no --status when empty
    @pytest.mark.asyncio
    async def test_status_empty_does_not_append_status_flag(self) -> None:
        """When status='', --status must NOT appear in args passed to _run_kanban."""
        with _patch_run() as mock_run:
            await create_task(_make_mcp_ctx(), title="T", status="")
        call_args = mock_run.call_args[0]
        assert "--status" not in call_args, "--status must not be passed when status is empty"

    # AC: Unit: --parent 42 in args when parent=42
    @pytest.mark.asyncio
    async def test_parent_positive_appends_parent_flag(self) -> None:
        """When parent=42, --parent 42 must appear in the args passed to _run_kanban."""
        with _patch_run() as mock_run:
            await create_task(_make_mcp_ctx(), title="T", parent=42)
        call_args = mock_run.call_args[0]
        assert "--parent" in call_args, "--parent flag must be passed when parent > 0"
        idx = list(call_args).index("--parent")
        assert call_args[idx + 1] == "42", "--parent must be followed by string '42'"

    # AC: Unit: no --parent when parent=0
    @pytest.mark.asyncio
    async def test_parent_zero_does_not_append_parent_flag(self) -> None:
        """When parent=0, --parent must NOT appear in args passed to _run_kanban."""
        with _patch_run() as mock_run:
            await create_task(_make_mcp_ctx(), title="T", parent=0)
        call_args = mock_run.call_args[0]
        assert "--parent" not in call_args, "--parent must not be passed when parent is 0"

    # AC: Unit: --json always present
    @pytest.mark.asyncio
    async def test_json_flag_always_present_with_all_params(self) -> None:
        """--json must be present when all optional params are supplied."""
        with _patch_run() as mock_run:
            await create_task(_make_mcp_ctx(), title="T", status="todo", parent=1)
        call_args = mock_run.call_args[0]
        assert "--json" in call_args, "--json must always be appended to create_task args"

    # AC: Unit: --json always present (minimal call)
    @pytest.mark.asyncio
    async def test_json_flag_always_present_with_title_only(self) -> None:
        """--json must be present even when only title is provided."""
        with _patch_run() as mock_run:
            await create_task(_make_mcp_ctx(), title="Minimal")
        call_args = mock_run.call_args[0]
        assert "--json" in call_args, "--json must always be appended even with title-only call"

    # AC: Unit: --json always present (boundary: parent=1, minimum positive)
    @pytest.mark.asyncio
    async def test_parent_boundary_value_one(self) -> None:
        """parent=1 (minimum positive) must append --parent 1."""
        with _patch_run() as mock_run:
            await create_task(_make_mcp_ctx(), title="T", parent=1)
        call_args = mock_run.call_args[0]
        assert "--parent" in call_args, "--parent must be added for parent=1"
        idx = list(call_args).index("--parent")
        assert call_args[idx + 1] == "1", "--parent value must be '1'"

    # Edge: negative parent treated like zero (no --parent)
    @pytest.mark.asyncio
    async def test_parent_negative_does_not_append_parent_flag(self) -> None:
        """parent=-1 (invalid) must not append --parent (same as parent=0 guard)."""
        with _patch_run() as mock_run:
            await create_task(_make_mcp_ctx(), title="T", parent=-1)
        call_args = mock_run.call_args[0]
        assert "--parent" not in call_args, "--parent must not be passed when parent <= 0"


# ---------------------------------------------------------------------------
# TestFromAC_CreateTaskReturn — return value contract
# ---------------------------------------------------------------------------


class TestFromAC_CreateTaskReturn:
    """Tests that create_task returns the raw JSON stdout from kanban-md."""

    # AC: create_task returns the raw JSON stdout from kanban-md
    # This requires --json to have been passed so kanban-md produces JSON
    @pytest.mark.asyncio
    async def test_returns_raw_json_stdout_on_success(self) -> None:
        """create_task must pass --json to kanban-md and return the raw JSON stdout."""
        with _patch_run(stdout=_SAMPLE_TASK_JSON) as mock_run:
            result = await create_task(_make_mcp_ctx(), title="T")
        call_args = mock_run.call_args[0]
        assert "--json" in call_args, (
            "create_task must pass --json to kanban-md to receive JSON output "
            "(required for raw JSON return contract)"
        )
        assert result == _SAMPLE_TASK_JSON, (
            "create_task must return the raw JSON stdout, not a transformed/summarised value"
        )

    # AC: JSON task object must include expected fields (id, title, status, priority, created, updated, parent, class, file)
    @pytest.mark.asyncio
    async def test_returned_json_is_parseable_task_object(self) -> None:
        """Raw JSON stdout must be parseable and --json must have been passed to produce it."""
        with _patch_run(stdout=_SAMPLE_TASK_JSON) as mock_run:
            result = await create_task(_make_mcp_ctx(), title="T")
        call_args = mock_run.call_args[0]
        assert "--json" in call_args, (
            "--json must be in args — it is what causes kanban-md to produce parseable JSON"
        )
        task = json.loads(result)
        required_fields = {"id", "title", "status", "priority", "created", "updated", "parent", "class", "file"}
        missing = required_fields - task.keys()
        assert not missing, f"Returned JSON task object is missing fields: {missing}"

    # Error path: when rc != 0, error string is returned; --json is still passed
    @pytest.mark.asyncio
    async def test_returns_error_string_on_nonzero_rc(self) -> None:
        """When _run_kanban returns rc != 0, create_task must return an error: string.

        --json is still appended unconditionally even on the error path.
        """
        with _patch_run(stdout="", stderr="task file conflict", rc=1) as mock_run:
            result = await create_task(_make_mcp_ctx(), title="T")
        call_args = mock_run.call_args[0]
        assert "--json" in call_args, "--json must be passed unconditionally, even on error path"
        assert result.startswith("error:"), (
            "When kanban-md exits non-zero, create_task must return 'error: ...' string"
        )


# ---------------------------------------------------------------------------
# TestFromAC_CreateTaskIntegration — roundtrip integration tests
# ---------------------------------------------------------------------------


class TestFromAC_CreateTaskStatusIntegration:
    """Integration tests for create_task status override and parent roundtrip."""

    # AC: Integration: create with status override + show roundtrip confirms correct status
    @pytest.mark.asyncio
    async def test_status_override_roundtrip_returns_correct_status(self) -> None:
        """create_task with status='backlog' must result in returned JSON showing status='backlog'."""
        expected_json = json.dumps({
            "id": "55",
            "title": "Status test",
            "status": "backlog",
            "priority": "important",
            "created": "2026-01-01T00:00:00Z",
            "updated": "2026-01-01T00:00:00Z",
            "parent": 0,
            "class": "standard",
            "file": "/kanban/tasks/55-status-test.md",
        })
        with _patch_run(stdout=expected_json):
            result = await create_task(_make_mcp_ctx(), title="Status test", status="backlog")

        task = json.loads(result)
        assert task["status"] == "backlog", (
            "Roundtrip: returned task JSON must reflect the requested status='backlog'"
        )

    # AC: Integration: create with parent + show roundtrip confirms parent field
    @pytest.mark.asyncio
    async def test_parent_roundtrip_returns_correct_parent(self) -> None:
        """create_task with parent=42 must result in returned JSON showing parent=42."""
        with _patch_run(stdout=_SAMPLE_TASK_WITH_PARENT_JSON):
            result = await create_task(_make_mcp_ctx(), title="Child task", parent=42)

        task = json.loads(result)
        assert task.get("parent") == 42, (
            "Roundtrip: returned task JSON must reflect the requested parent=42"
        )


# ---------------------------------------------------------------------------
# TestFromAC_CreateTaskSkillDoc — SKILL.md documentation update
# ---------------------------------------------------------------------------


class TestFromAC_CreateTaskSkillDoc:
    """Tests that .github/skills/h-mcp-kanban/SKILL.md mentions create_task."""

    # AC: .github/skills/h-mcp-kanban/SKILL.md lists create_task in Tool Summary
    def test_skill_md_create_task_row_includes_status(self) -> None:
        """.github/skills/h-mcp-kanban/SKILL.md must have a create_task entry."""
        content = _SKILL_MD.read_text(encoding="utf-8")
        create_task_lines = [ln for ln in content.splitlines() if "create_task" in ln and "|" in ln]
        assert create_task_lines, "SKILL.md must have a table row containing 'create_task'"

    # AC: parameters are documented via MCP schema (enum constraints on status/priority)
    def test_skill_md_create_task_row_includes_parent(self) -> None:
        """.github/skills/h-mcp-kanban/SKILL.md must have a create_task entry."""
        content = _SKILL_MD.read_text(encoding="utf-8")
        create_task_lines = [ln for ln in content.splitlines() if "create_task" in ln and "|" in ln]
        assert create_task_lines, "SKILL.md must have a table row containing 'create_task'"
