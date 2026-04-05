"""Failing tests for task #472: Modernize list_tasks: lean JSON, archived, limit, blocked tri-state.

Covers all AC items from #472:
  - archived: bool = False parameter: when True adds --archived flag
  - limit: int = 0 parameter: when >0 adds --limit N; when 0, no flag
  - reverse: bool = False parameter: when True adds --reverse flag
  - blocked tri-state (Optional[bool]): None=no filter, True=--blocked, False=--not-blocked
  - block_filter parameter removed (calling with it raises TypeError)
  - --json flag used instead of --compact
  - Server-side strip of body/file/created/updated from JSON output
  - outputSchema defined on the tool
  - structuredContent returned alongside text content

All tests FAIL in RED phase — the current implementation uses --compact, has block_filter
param, lacks archived/limit/reverse/blocked params, and performs no JSON transformation.
"""

from __future__ import annotations

import inspect
import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlbear_mcp_kanban.server import (  # type: ignore[import]
    AppContext,
    list_tasks,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_LEAN_FIELDS = {"id", "title", "status", "priority", "tags", "depends_on", "class",
                "blocked", "block_reason", "claimed_by"}
_STRIPPED_FIELDS = {"body", "file", "created", "updated"}

_SAMPLE_FULL_TASK = {
    "id": "42",
    "title": "Sample task",
    "status": "todo",
    "priority": "important",
    "created": "2026-01-01T00:00:00Z",
    "updated": "2026-01-02T00:00:00Z",
    "tags": ["phase-1"],
    "depends_on": "",
    "class": "standard",
    "body": "## AC\n- do stuff",
    "file": "/kanban/tasks/42-sample.md",
    "blocked": False,
    "block_reason": "",
    "claimed_by": "",
}

_SAMPLE_FULL_JSON = json.dumps([_SAMPLE_FULL_TASK])
_SAMPLE_MULTI_JSON = json.dumps([_SAMPLE_FULL_TASK, {**_SAMPLE_FULL_TASK, "id": "43"}])


def _make_app_ctx() -> AppContext:
    from pathlib import Path
    return AppContext(kanban_bin=Path("/fake/kanban-md"), kanban_dir=Path("/fake/kanban"))


def _make_mcp_ctx(app_ctx: AppContext | None = None) -> MagicMock:
    ctx = MagicMock()
    ctx.request_context.lifespan_context = app_ctx or _make_app_ctx()
    return ctx


def _patch_run(stdout: str = _SAMPLE_FULL_JSON, stderr: str = "", rc: int = 0) -> Any:
    return patch(
        "owlbear_mcp_kanban.server._run_kanban",
        new=AsyncMock(return_value=(stdout, stderr, rc)),
    )


# ---------------------------------------------------------------------------
# TestFromAC_ListTasksSignature — parameter contract
# ---------------------------------------------------------------------------


class TestFromAC_ListTasksSignature:
    """Tests that list_tasks exposes the new parameter contract from #472 AC."""

    # AC: Add `archived: bool = False` parameter
    def test_has_archived_parameter_with_bool_default_false(self) -> None:
        """list_tasks must accept `archived: bool = False`."""
        sig = inspect.signature(list_tasks)
        assert "archived" in sig.parameters, "list_tasks must have `archived` parameter"
        param = sig.parameters["archived"]
        assert param.default is False, "`archived` default must be False"

    # AC: Add `limit: int = 0` parameter
    def test_has_limit_parameter_with_int_default_zero(self) -> None:
        """list_tasks must accept `limit: int = 0`."""
        sig = inspect.signature(list_tasks)
        assert "limit" in sig.parameters, "list_tasks must have `limit` parameter"
        param = sig.parameters["limit"]
        assert param.default == 0, "`limit` default must be 0"

    # AC: Add `reverse: bool = False` parameter
    def test_has_reverse_parameter_with_bool_default_false(self) -> None:
        """list_tasks must accept `reverse: bool = False`."""
        sig = inspect.signature(list_tasks)
        assert "reverse" in sig.parameters, "list_tasks must have `reverse` parameter"
        param = sig.parameters["reverse"]
        assert param.default is False, "`reverse` default must be False"

    # AC: Change block_filter: str to blocked: bool | None = None (tri-state)
    def test_has_blocked_parameter_with_none_default(self) -> None:
        """list_tasks must accept `blocked: bool | None = None` (tri-state)."""
        sig = inspect.signature(list_tasks)
        assert "blocked" in sig.parameters, "list_tasks must have `blocked` parameter"
        param = sig.parameters["blocked"]
        assert param.default is None, "`blocked` default must be None"

    # AC: Change block_filter removed — calling with it is a TypeError
    def test_block_filter_param_no_longer_exists(self) -> None:
        """list_tasks must NOT accept `block_filter` — it is removed in #472."""
        sig = inspect.signature(list_tasks)
        assert "block_filter" not in sig.parameters, (
            "`block_filter` was removed in #472 — list_tasks must no longer accept it"
        )


# ---------------------------------------------------------------------------
# TestFromAC_ListTasksCliFlags — CLI arg contract
# ---------------------------------------------------------------------------


class TestFromAC_ListTasksCliFlags:
    """Tests that new parameters map to the correct kanban-md CLI flags."""

    # AC: Switch to --json (not --compact)
    @pytest.mark.asyncio
    async def test_uses_json_flag_not_compact(self) -> None:
        """list_tasks must pass --json to kanban-md, NOT --compact."""
        mcp_ctx = _make_mcp_ctx()
        with _patch_run() as mock_run:
            await list_tasks(mcp_ctx)

        args: tuple[Any, ...] = mock_run.call_args[0]
        assert "--json" in args, "list_tasks must pass --json flag (not --compact)"
        assert "--compact" not in args, "list_tasks must NOT pass --compact (replaced by --json)"

    # AC: archived=True → pass --archived flag
    @pytest.mark.asyncio
    async def test_archived_true_passes_archived_flag(self) -> None:
        """list_tasks with archived=True must pass --archived to kanban-md."""
        mcp_ctx = _make_mcp_ctx()
        with _patch_run() as mock_run:
            await list_tasks(mcp_ctx, archived=True)

        args: tuple[Any, ...] = mock_run.call_args[0]
        assert "--archived" in args, "--archived must be passed when archived=True"

    # AC: archived=False (default) → --archived NOT passed
    @pytest.mark.asyncio
    async def test_archived_false_omits_archived_flag(self) -> None:
        """list_tasks with archived=False (default) must NOT pass --archived."""
        mcp_ctx = _make_mcp_ctx()
        with _patch_run() as mock_run:
            await list_tasks(mcp_ctx, archived=False)

        args: tuple[Any, ...] = mock_run.call_args[0]
        assert "--archived" not in args, "--archived must NOT be passed when archived=False"

    # AC: limit > 0 → pass --limit N
    @pytest.mark.asyncio
    async def test_limit_positive_passes_limit_flag_and_value(self) -> None:
        """list_tasks with limit=5 must pass --limit 5 to kanban-md."""
        mcp_ctx = _make_mcp_ctx()
        with _patch_run() as mock_run:
            await list_tasks(mcp_ctx, limit=5)

        args: tuple[Any, ...] = mock_run.call_args[0]
        assert "--limit" in args, "--limit must be passed when limit > 0"
        limit_idx = list(args).index("--limit")
        assert args[limit_idx + 1] == "5", "limit value must be passed as string '5'"

    # AC: limit = 0 (default) → --limit NOT passed
    @pytest.mark.asyncio
    async def test_limit_zero_omits_limit_flag(self) -> None:
        """list_tasks with limit=0 (default, no limit) must NOT pass --limit."""
        mcp_ctx = _make_mcp_ctx()
        with _patch_run() as mock_run:
            await list_tasks(mcp_ctx, limit=0)

        args: tuple[Any, ...] = mock_run.call_args[0]
        assert "--limit" not in args, "--limit must NOT be passed when limit=0"

    # Boundary: limit = 1 (minimum positive)
    @pytest.mark.asyncio
    async def test_limit_one_passes_limit_1(self) -> None:
        """list_tasks with limit=1 must pass --limit 1 (minimum positive boundary)."""
        mcp_ctx = _make_mcp_ctx()
        with _patch_run() as mock_run:
            await list_tasks(mcp_ctx, limit=1)

        args: tuple[Any, ...] = mock_run.call_args[0]
        assert "--limit" in args
        limit_idx = list(args).index("--limit")
        assert args[limit_idx + 1] == "1"

    # AC: reverse=True → pass --reverse
    @pytest.mark.asyncio
    async def test_reverse_true_passes_reverse_flag(self) -> None:
        """list_tasks with reverse=True must pass --reverse to kanban-md."""
        mcp_ctx = _make_mcp_ctx()
        with _patch_run() as mock_run:
            await list_tasks(mcp_ctx, reverse=True)

        args: tuple[Any, ...] = mock_run.call_args[0]
        assert "--reverse" in args, "--reverse must be passed when reverse=True"

    # Edge: reverse=False (default) → --reverse NOT passed
    @pytest.mark.asyncio
    async def test_reverse_false_omits_reverse_flag(self) -> None:
        """list_tasks with reverse=False (default) must NOT pass --reverse."""
        mcp_ctx = _make_mcp_ctx()
        with _patch_run() as mock_run:
            await list_tasks(mcp_ctx, reverse=False)

        args: tuple[Any, ...] = mock_run.call_args[0]
        assert "--reverse" not in args

    # AC: blocked=True → pass --blocked (tri-state True)
    @pytest.mark.asyncio
    async def test_blocked_true_passes_blocked_flag(self) -> None:
        """list_tasks with blocked=True must pass --blocked to kanban-md."""
        mcp_ctx = _make_mcp_ctx()
        with _patch_run() as mock_run:
            await list_tasks(mcp_ctx, blocked=True)

        args: tuple[Any, ...] = mock_run.call_args[0]
        assert "--blocked" in args, "--blocked must be passed when blocked=True"
        assert "--not-blocked" not in args, "--not-blocked must NOT be passed when blocked=True"

    # AC: blocked=False → pass --not-blocked (tri-state False)
    @pytest.mark.asyncio
    async def test_blocked_false_passes_not_blocked_flag(self) -> None:
        """list_tasks with blocked=False must pass --not-blocked to kanban-md."""
        mcp_ctx = _make_mcp_ctx()
        with _patch_run() as mock_run:
            await list_tasks(mcp_ctx, blocked=False)

        args: tuple[Any, ...] = mock_run.call_args[0]
        assert "--not-blocked" in args, "--not-blocked must be passed when blocked=False"
        assert "--blocked" not in args, "--blocked must NOT be passed when blocked=False"

    # AC: blocked=None (default) → neither --blocked nor --not-blocked
    @pytest.mark.asyncio
    async def test_blocked_none_passes_no_block_filter_flags(self) -> None:
        """list_tasks with blocked=None (default) must pass neither --blocked nor --not-blocked."""
        mcp_ctx = _make_mcp_ctx()
        with _patch_run() as mock_run:
            await list_tasks(mcp_ctx, blocked=None)

        args: tuple[Any, ...] = mock_run.call_args[0]
        assert "--blocked" not in args, "--blocked must NOT be passed when blocked=None"
        assert "--not-blocked" not in args, "--not-blocked must NOT be passed when blocked=None"


# ---------------------------------------------------------------------------
# TestFromAC_ListTasksLeanJson — server-side JSON transformation contract
# ---------------------------------------------------------------------------


class TestFromAC_ListTasksLeanJson:
    """Tests that list_tasks strips body/file/created/updated from kanban-md JSON output."""

    # AC: Strip body, file, created, updated fields from each task object
    @pytest.mark.asyncio
    async def test_stripped_fields_absent_from_result(self) -> None:
        """list_tasks must remove body/file/created/updated from the JSON output."""
        mcp_ctx = _make_mcp_ctx()
        with _patch_run(stdout=_SAMPLE_FULL_JSON):
            result = await list_tasks(mcp_ctx)

        tasks = result
        assert isinstance(tasks, list)
        task = tasks[0]
        for field in _STRIPPED_FIELDS:
            assert field not in task, (
                f"Field '{field}' must be stripped from list_tasks output but is present"
            )

    # Edge: Multiple tasks all stripped correctly
    @pytest.mark.asyncio
    async def test_all_tasks_in_list_have_fields_stripped(self) -> None:
        """list_tasks must strip body/file/created/updated from every task in the list."""
        mcp_ctx = _make_mcp_ctx()
        with _patch_run(stdout=_SAMPLE_MULTI_JSON):
            result = await list_tasks(mcp_ctx)

        tasks = result
        assert len(tasks) == 2, "Both tasks must be present in the output"
        for task in tasks:
            for field in _STRIPPED_FIELDS:
                assert field not in task, (
                    f"Field '{field}' must be stripped from every task in output"
                )


# ---------------------------------------------------------------------------
# TestFromAC_ListTasksLeanJsonPresence — lean fields are RETAINED (not over-stripped)
# ---------------------------------------------------------------------------


class TestFromAC_ListTasksLeanJsonPresence:
    """Tests that lean JSON output RETAINS expected fields (guards against over-stripping).

    The reviewer cited a mutation: `lean = [{} for task in tasks]` passes all existing
    tests because only absence of stripped fields was checked.  These tests assert
    PRESENCE of the fields that must survive stripping, making that mutation fail.
    """

    # Core lean fields must all survive stripping
    @pytest.mark.asyncio
    async def test_lean_json_retains_all_expected_lean_fields(self) -> None:
        """list_tasks lean output must contain id, title, status, priority, tags, etc."""
        mcp_ctx = _make_mcp_ctx()
        with _patch_run(stdout=_SAMPLE_FULL_JSON):
            result = await list_tasks(mcp_ctx)

        tasks = result
        assert isinstance(tasks, list)
        assert len(tasks) > 0
        task = tasks[0]
        # _LEAN_FIELDS must ALL be present — mutation [{} for …] would break this
        for field in _LEAN_FIELDS:
            assert field in task, (
                f"Expected lean field '{field}' is absent — stripping removed too much"
            )

    # Individual boundary: id is retained
    @pytest.mark.asyncio
    async def test_lean_json_retains_id(self) -> None:
        """list_tasks lean output must retain the 'id' field."""
        mcp_ctx = _make_mcp_ctx()
        with _patch_run(stdout=_SAMPLE_FULL_JSON):
            result = await list_tasks(mcp_ctx)

        task = result[0]
        assert "id" in task, "'id' must be present in lean output"
        assert task["id"] == _SAMPLE_FULL_TASK["id"]

    # Individual boundary: title is retained
    @pytest.mark.asyncio
    async def test_lean_json_retains_title(self) -> None:
        """list_tasks lean output must retain the 'title' field."""
        mcp_ctx = _make_mcp_ctx()
        with _patch_run(stdout=_SAMPLE_FULL_JSON):
            result = await list_tasks(mcp_ctx)

        task = result[0]
        assert "title" in task, "'title' must be present in lean output"
        assert task["title"] == _SAMPLE_FULL_TASK["title"]

    # Boundary: exactly the 4 noisy fields are stripped, nothing else
    @pytest.mark.asyncio
    async def test_lean_json_strips_exactly_four_fields(self) -> None:
        """list_tasks must strip exactly body/file/created/updated — no more, no less."""
        mcp_ctx = _make_mcp_ctx()
        with _patch_run(stdout=_SAMPLE_FULL_JSON):
            result = await list_tasks(mcp_ctx)

        task = result[0]
        original_key_count = len(_SAMPLE_FULL_TASK)
        expected_key_count = original_key_count - len(_STRIPPED_FIELDS)
        assert len(task) == expected_key_count, (
            f"Expected exactly {expected_key_count} fields in lean output "
            f"(original {original_key_count} minus 4 stripped), got {len(task)}"
        )

    # Edge: multi-task list — all tasks retain lean fields
    @pytest.mark.asyncio
    async def test_lean_json_multi_task_all_retain_id_and_title(self) -> None:
        """list_tasks with multiple tasks must retain id and title in every task."""
        mcp_ctx = _make_mcp_ctx()
        with _patch_run(stdout=_SAMPLE_MULTI_JSON):
            result = await list_tasks(mcp_ctx)

        tasks = result
        assert len(tasks) == 2
        for i, task in enumerate(tasks):
            assert "id" in task, f"Task[{i}] missing 'id' in lean output"
            assert "title" in task, f"Task[{i}] missing 'title' in lean output"
            assert "status" in task, f"Task[{i}] missing 'status' in lean output"


# ---------------------------------------------------------------------------
# TestFromAC_ListTasksStructuredContent — outputSchema + structuredContent contract
# ---------------------------------------------------------------------------


class TestFromAC_ListTasksStructuredContent:
    """Tests that list_tasks returns structuredContent alongside text content (#472 update AC)."""

    # AC: Define outputSchema for list_tasks (array type)
    def test_list_tasks_tool_has_output_schema(self) -> None:
        """list_tasks tool must have an outputSchema and it must describe an array type."""
        from owlbear_mcp_kanban.server import mcp  # type: ignore[import]
        tool_name = "list_tasks"
        tools = {t.name: t for t in mcp._tool_manager._tools.values()}  # type: ignore[union-attr]
        assert tool_name in tools, f"'{tool_name}' tool must be registered in FastMCP"
        tool = tools[tool_name]
        assert hasattr(tool, "output_schema"), "list_tasks tool must have output_schema attribute"
        assert tool.output_schema is not None, "list_tasks tool must have an outputSchema defined"
        assert tool.output_schema.get("type") == "array", (
            "list_tasks outputSchema must be type 'array' (list of lean task objects)"
        )

    # AC: outputSchema is array of lean task objects (id, title, status, priority, tags, ...)
    def test_output_schema_is_array_type(self) -> None:
        """list_tasks outputSchema must describe an array of lean task objects."""
        from owlbear_mcp_kanban.server import mcp  # type: ignore[import]
        tools = {t.name: t for t in mcp._tool_manager._tools.values()}  # type: ignore[union-attr]
        tool = tools["list_tasks"]
        schema = tool.output_schema
        # JSON Schema convention: top-level type is "array"
        assert schema.get("type") == "array", (
            "outputSchema must be an array type (list of lean task objects)"
        )

    # AC: Return structuredContent alongside text content — result is lean JSON array
    @pytest.mark.asyncio
    async def test_result_is_lean_json_array_with_no_stripped_fields(self) -> None:
        """list_tasks text result must be a JSON array with body/file/created/updated absent."""
        mcp_ctx = _make_mcp_ctx()
        with _patch_run(stdout=_SAMPLE_FULL_JSON):
            result = await list_tasks(mcp_ctx)

        parsed = result
        assert isinstance(parsed, list), "list_tasks result must be a JSON array"
        task = parsed[0]
        for field in _STRIPPED_FIELDS:
            assert field not in task, (
                f"'{field}' must be absent from structuredContent-ready lean output"
            )
