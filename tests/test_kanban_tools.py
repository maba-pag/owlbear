"""Tests for KanbanToolset — subprocess kanban-md operations.

Covers: kanban_list, kanban_show, kanban_create, kanban_move, kanban_edit,
kanban_pick, kanban_context, error handling, constructor, hook integration,
and FunctionToolset registration.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from owlbear.core.hooks import HookEvent, HookRegistry
from owlbear.tools.kanban import KanbanToolset

KANBAN_DIR = Path("/fake/kanban")
KANBAN_BIN = Path("/fake/kanban/kanban-md.exe")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_proc(stdout: str = "", stderr: str = "", returncode: int = 0) -> AsyncMock:
    """Build a mock subprocess with the given outputs and return code."""
    proc = AsyncMock()
    proc.communicate.return_value = (
        stdout.encode("utf-8"),
        stderr.encode("utf-8"),
    )
    proc.returncode = returncode
    return proc


def _patch_exec(proc: AsyncMock):
    """Patch asyncio.create_subprocess_exec to return *proc*."""
    return patch(
        "owlbear.tools.kanban.asyncio.create_subprocess_exec",
        return_value=proc,
    )


# ---------------------------------------------------------------------------
# Constructor
# ---------------------------------------------------------------------------


class TestConstructor:
    """KanbanToolset stores kanban_dir, kanban_bin, and hooks."""

    def test_kanban_dir_stored(self) -> None:
        ts = KanbanToolset(kanban_dir=KANBAN_DIR, kanban_bin=KANBAN_BIN)
        assert ts._kanban_dir == KANBAN_DIR

    def test_kanban_bin_stored(self) -> None:
        ts = KanbanToolset(kanban_dir=KANBAN_DIR, kanban_bin=KANBAN_BIN)
        assert ts._kanban_bin == KANBAN_BIN

    def test_hooks_stored_when_provided(self) -> None:
        hooks = HookRegistry()
        ts = KanbanToolset(kanban_dir=KANBAN_DIR, kanban_bin=KANBAN_BIN, hooks=hooks)
        assert ts._hooks is hooks

    def test_hooks_default_none(self) -> None:
        ts = KanbanToolset(kanban_dir=KANBAN_DIR, kanban_bin=KANBAN_BIN)
        assert ts._hooks is None

    def test_inherits_function_toolset(self) -> None:
        from pydantic_ai.toolsets import FunctionToolset

        ts = KanbanToolset(kanban_dir=KANBAN_DIR, kanban_bin=KANBAN_BIN)
        assert isinstance(ts, FunctionToolset)

    def test_kanban_bin_auto_detect(self) -> None:
        """When kanban_bin is None, auto-detect kanban_dir / 'kanban-md.exe'."""
        ts = KanbanToolset(kanban_dir=KANBAN_DIR)
        assert ts._kanban_bin == KANBAN_DIR / "kanban-md.exe"


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------


class TestToolRegistration:
    """All 7 kanban tools are registered on the FunctionToolset."""

    def test_all_tools_registered(self) -> None:
        ts = KanbanToolset(kanban_dir=KANBAN_DIR, kanban_bin=KANBAN_BIN)
        expected = {
            "kanban_list",
            "kanban_show",
            "kanban_create",
            "kanban_move",
            "kanban_edit",
            "kanban_pick",
            "kanban_context",
        }
        assert expected == set(ts.tools)

    def test_tool_count(self) -> None:
        ts = KanbanToolset(kanban_dir=KANBAN_DIR, kanban_bin=KANBAN_BIN)
        assert len(ts.tools) == 7


# ---------------------------------------------------------------------------
# kanban_list
# ---------------------------------------------------------------------------


class TestKanbanList:
    """kanban_list calls list --compact --no-color --dir {dir}."""

    @pytest.mark.asyncio
    async def test_basic_list_flags(self) -> None:
        proc = _make_proc(stdout="task1\ntask2\n")
        with _patch_exec(proc) as mock_exec:
            ts = KanbanToolset(kanban_dir=KANBAN_DIR, kanban_bin=KANBAN_BIN)
            await ts.kanban_list()

        mock_exec.assert_called_once()
        args = mock_exec.call_args[0]
        assert args[0] == str(KANBAN_BIN)
        assert "list" in args
        assert "--compact" in args
        assert "--no-color" in args
        assert "--dir" in args
        dir_idx = args.index("--dir")
        assert args[dir_idx + 1] == str(KANBAN_DIR)

    @pytest.mark.asyncio
    async def test_returns_list_output(self) -> None:
        proc = _make_proc(stdout="task1\ntask2\n")
        with _patch_exec(proc):
            ts = KanbanToolset(kanban_dir=KANBAN_DIR, kanban_bin=KANBAN_BIN)
            result = await ts.kanban_list()

        assert "task1" in result
        assert "task2" in result

    @pytest.mark.asyncio
    async def test_status_filter(self) -> None:
        proc = _make_proc(stdout="todo tasks\n")
        with _patch_exec(proc) as mock_exec:
            ts = KanbanToolset(kanban_dir=KANBAN_DIR, kanban_bin=KANBAN_BIN)
            await ts.kanban_list(status="todo")

        args = mock_exec.call_args[0]
        assert "--status" in args
        status_idx = args.index("--status")
        assert args[status_idx + 1] == "todo"

    @pytest.mark.asyncio
    async def test_tag_filter(self) -> None:
        proc = _make_proc(stdout="tagged tasks\n")
        with _patch_exec(proc) as mock_exec:
            ts = KanbanToolset(kanban_dir=KANBAN_DIR, kanban_bin=KANBAN_BIN)
            await ts.kanban_list(tag="phase-1")

        args = mock_exec.call_args[0]
        assert "--tag" in args
        tag_idx = args.index("--tag")
        assert args[tag_idx + 1] == "phase-1"

    @pytest.mark.asyncio
    async def test_priority_filter(self) -> None:
        proc = _make_proc(stdout="critical tasks\n")
        with _patch_exec(proc) as mock_exec:
            ts = KanbanToolset(kanban_dir=KANBAN_DIR, kanban_bin=KANBAN_BIN)
            await ts.kanban_list(priority="critical")

        args = mock_exec.call_args[0]
        assert "--priority" in args
        pri_idx = args.index("--priority")
        assert args[pri_idx + 1] == "critical"

    @pytest.mark.asyncio
    async def test_blocked_filter(self) -> None:
        proc = _make_proc(stdout="blocked tasks\n")
        with _patch_exec(proc) as mock_exec:
            ts = KanbanToolset(kanban_dir=KANBAN_DIR, kanban_bin=KANBAN_BIN)
            await ts.kanban_list(blocked=True)

        args = mock_exec.call_args[0]
        assert "--blocked" in args

    @pytest.mark.asyncio
    async def test_not_blocked_filter(self) -> None:
        proc = _make_proc(stdout="unblocked tasks\n")
        with _patch_exec(proc) as mock_exec:
            ts = KanbanToolset(kanban_dir=KANBAN_DIR, kanban_bin=KANBAN_BIN)
            await ts.kanban_list(not_blocked=True)

        args = mock_exec.call_args[0]
        assert "--not-blocked" in args

    @pytest.mark.asyncio
    async def test_unblocked_filter(self) -> None:
        proc = _make_proc(stdout="unblocked tasks\n")
        with _patch_exec(proc) as mock_exec:
            ts = KanbanToolset(kanban_dir=KANBAN_DIR, kanban_bin=KANBAN_BIN)
            await ts.kanban_list(unblocked=True)

        args = mock_exec.call_args[0]
        assert "--unblocked" in args

    @pytest.mark.asyncio
    async def test_no_optional_filters(self) -> None:
        """When no filters provided, only base flags appear."""
        proc = _make_proc(stdout="all tasks\n")
        with _patch_exec(proc) as mock_exec:
            ts = KanbanToolset(kanban_dir=KANBAN_DIR, kanban_bin=KANBAN_BIN)
            await ts.kanban_list()

        args = mock_exec.call_args[0]
        assert "--status" not in args
        assert "--tag" not in args
        assert "--priority" not in args
        assert "--blocked" not in args
        assert "--not-blocked" not in args
        assert "--unblocked" not in args

    @pytest.mark.asyncio
    async def test_combined_filters(self) -> None:
        proc = _make_proc(stdout="filtered tasks\n")
        with _patch_exec(proc) as mock_exec:
            ts = KanbanToolset(kanban_dir=KANBAN_DIR, kanban_bin=KANBAN_BIN)
            await ts.kanban_list(status="in-progress", tag="auth", priority="needed")

        args = mock_exec.call_args[0]
        assert "--status" in args
        assert "--tag" in args
        assert "--priority" in args


# ---------------------------------------------------------------------------
# kanban_show
# ---------------------------------------------------------------------------


class TestKanbanShow:
    """kanban_show calls show {id} --json --no-color --dir {dir}."""

    @pytest.mark.asyncio
    async def test_show_command_args(self) -> None:
        proc = _make_proc(stdout='{"id": "42", "title": "test"}\n')
        with _patch_exec(proc) as mock_exec:
            ts = KanbanToolset(kanban_dir=KANBAN_DIR, kanban_bin=KANBAN_BIN)
            await ts.kanban_show(task_id="42")

        args = mock_exec.call_args[0]
        assert args[0] == str(KANBAN_BIN)
        assert "show" in args
        assert "42" in args
        assert "--json" in args
        assert "--no-color" in args
        assert "--dir" in args

    @pytest.mark.asyncio
    async def test_returns_json_output(self) -> None:
        json_str = '{"id": "42", "title": "test task"}\n'
        proc = _make_proc(stdout=json_str)
        with _patch_exec(proc):
            ts = KanbanToolset(kanban_dir=KANBAN_DIR, kanban_bin=KANBAN_BIN)
            result = await ts.kanban_show(task_id="42")

        assert '"id": "42"' in result


# ---------------------------------------------------------------------------
# kanban_create
# ---------------------------------------------------------------------------


class TestKanbanCreate:
    """kanban_create calls create {title} with optional flags."""

    @pytest.mark.asyncio
    async def test_create_basic(self) -> None:
        proc = _make_proc(stdout="Created task #99\n")
        with _patch_exec(proc) as mock_exec:
            ts = KanbanToolset(kanban_dir=KANBAN_DIR, kanban_bin=KANBAN_BIN)
            result = await ts.kanban_create(title="New task")

        args = mock_exec.call_args[0]
        assert "create" in args
        assert "New task" in args
        assert "--no-color" in args
        assert "--dir" in args
        assert "Created" in result

    @pytest.mark.asyncio
    async def test_create_with_priority(self) -> None:
        proc = _make_proc(stdout="Created task #100\n")
        with _patch_exec(proc) as mock_exec:
            ts = KanbanToolset(kanban_dir=KANBAN_DIR, kanban_bin=KANBAN_BIN)
            await ts.kanban_create(title="Urgent", priority="critical")

        args = mock_exec.call_args[0]
        assert "--priority" in args
        pri_idx = args.index("--priority")
        assert args[pri_idx + 1] == "critical"

    @pytest.mark.asyncio
    async def test_create_with_tags(self) -> None:
        proc = _make_proc(stdout="Created task #101\n")
        with _patch_exec(proc) as mock_exec:
            ts = KanbanToolset(kanban_dir=KANBAN_DIR, kanban_bin=KANBAN_BIN)
            await ts.kanban_create(title="Tagged", tags="auth,phase-1")

        args = mock_exec.call_args[0]
        assert "--tags" in args
        tags_idx = args.index("--tags")
        assert args[tags_idx + 1] == "auth,phase-1"

    @pytest.mark.asyncio
    async def test_create_with_body(self) -> None:
        proc = _make_proc(stdout="Created task #102\n")
        with _patch_exec(proc) as mock_exec:
            ts = KanbanToolset(kanban_dir=KANBAN_DIR, kanban_bin=KANBAN_BIN)
            await ts.kanban_create(title="Detailed", body="AC: do the thing")

        args = mock_exec.call_args[0]
        assert "--body" in args
        body_idx = args.index("--body")
        assert args[body_idx + 1] == "AC: do the thing"

    @pytest.mark.asyncio
    async def test_create_with_depends_on(self) -> None:
        proc = _make_proc(stdout="Created task #103\n")
        with _patch_exec(proc) as mock_exec:
            ts = KanbanToolset(kanban_dir=KANBAN_DIR, kanban_bin=KANBAN_BIN)
            await ts.kanban_create(title="Dependent", depends_on="42")

        args = mock_exec.call_args[0]
        assert "--depends-on" in args
        dep_idx = args.index("--depends-on")
        assert args[dep_idx + 1] == "42"

    @pytest.mark.asyncio
    async def test_create_no_optional_flags(self) -> None:
        proc = _make_proc(stdout="Created task #104\n")
        with _patch_exec(proc) as mock_exec:
            ts = KanbanToolset(kanban_dir=KANBAN_DIR, kanban_bin=KANBAN_BIN)
            await ts.kanban_create(title="Simple")

        args = mock_exec.call_args[0]
        assert "--priority" not in args
        assert "--tags" not in args
        assert "--body" not in args
        assert "--depends-on" not in args


# ---------------------------------------------------------------------------
# kanban_move
# ---------------------------------------------------------------------------


class TestKanbanMove:
    """kanban_move calls move {id} {status}."""

    @pytest.mark.asyncio
    async def test_move_command(self) -> None:
        proc = _make_proc(stdout="Moved task #42 to in-progress\n")
        with _patch_exec(proc) as mock_exec:
            ts = KanbanToolset(kanban_dir=KANBAN_DIR, kanban_bin=KANBAN_BIN)
            result = await ts.kanban_move(task_id="42", status="in-progress")

        args = mock_exec.call_args[0]
        assert "move" in args
        assert "42" in args
        assert "in-progress" in args
        assert "--no-color" in args
        assert "--dir" in args
        assert "Moved" in result

    @pytest.mark.asyncio
    async def test_move_different_status(self) -> None:
        proc = _make_proc(stdout="Moved task #10 to review\n")
        with _patch_exec(proc) as mock_exec:
            ts = KanbanToolset(kanban_dir=KANBAN_DIR, kanban_bin=KANBAN_BIN)
            await ts.kanban_move(task_id="10", status="review")

        args = mock_exec.call_args[0]
        assert "10" in args
        assert "review" in args


# ---------------------------------------------------------------------------
# kanban_edit
# ---------------------------------------------------------------------------


class TestKanbanEdit:
    """kanban_edit calls edit {id} with optional flags."""

    @pytest.mark.asyncio
    async def test_edit_body(self) -> None:
        proc = _make_proc(stdout="Updated task #42\n")
        with _patch_exec(proc) as mock_exec:
            ts = KanbanToolset(kanban_dir=KANBAN_DIR, kanban_bin=KANBAN_BIN)
            await ts.kanban_edit(task_id="42", body="New body")

        args = mock_exec.call_args[0]
        assert "edit" in args
        assert "42" in args
        assert "--body" in args
        body_idx = args.index("--body")
        assert args[body_idx + 1] == "New body"

    @pytest.mark.asyncio
    async def test_edit_block(self) -> None:
        proc = _make_proc(stdout="Updated task #42\n")
        with _patch_exec(proc) as mock_exec:
            ts = KanbanToolset(kanban_dir=KANBAN_DIR, kanban_bin=KANBAN_BIN)
            await ts.kanban_edit(task_id="42", block="waiting on user")

        args = mock_exec.call_args[0]
        assert "--block" in args
        block_idx = args.index("--block")
        assert args[block_idx + 1] == "waiting on user"

    @pytest.mark.asyncio
    async def test_edit_unblock(self) -> None:
        proc = _make_proc(stdout="Updated task #42\n")
        with _patch_exec(proc) as mock_exec:
            ts = KanbanToolset(kanban_dir=KANBAN_DIR, kanban_bin=KANBAN_BIN)
            await ts.kanban_edit(task_id="42", unblock=True)

        args = mock_exec.call_args[0]
        assert "--unblock" in args

    @pytest.mark.asyncio
    async def test_edit_tags(self) -> None:
        proc = _make_proc(stdout="Updated task #42\n")
        with _patch_exec(proc) as mock_exec:
            ts = KanbanToolset(kanban_dir=KANBAN_DIR, kanban_bin=KANBAN_BIN)
            await ts.kanban_edit(task_id="42", tags="auth,phase-2")

        args = mock_exec.call_args[0]
        assert "--tags" in args
        tags_idx = args.index("--tags")
        assert args[tags_idx + 1] == "auth,phase-2"

    @pytest.mark.asyncio
    async def test_edit_priority(self) -> None:
        proc = _make_proc(stdout="Updated task #42\n")
        with _patch_exec(proc) as mock_exec:
            ts = KanbanToolset(kanban_dir=KANBAN_DIR, kanban_bin=KANBAN_BIN)
            await ts.kanban_edit(task_id="42", priority="needed")

        args = mock_exec.call_args[0]
        assert "--priority" in args
        pri_idx = args.index("--priority")
        assert args[pri_idx + 1] == "needed"

    @pytest.mark.asyncio
    async def test_edit_append_body(self) -> None:
        proc = _make_proc(stdout="Updated task #42\n")
        with _patch_exec(proc) as mock_exec:
            ts = KanbanToolset(kanban_dir=KANBAN_DIR, kanban_bin=KANBAN_BIN)
            await ts.kanban_edit(task_id="42", append_body="Extra note")

        args = mock_exec.call_args[0]
        assert "--append-body" in args
        ab_idx = args.index("--append-body")
        assert args[ab_idx + 1] == "Extra note"

    @pytest.mark.asyncio
    async def test_edit_no_optional_flags(self) -> None:
        proc = _make_proc(stdout="Updated task #42\n")
        with _patch_exec(proc) as mock_exec:
            ts = KanbanToolset(kanban_dir=KANBAN_DIR, kanban_bin=KANBAN_BIN)
            await ts.kanban_edit(task_id="42")

        args = mock_exec.call_args[0]
        assert "--body" not in args
        assert "--block" not in args
        assert "--unblock" not in args
        assert "--tags" not in args
        assert "--priority" not in args
        assert "--append-body" not in args

    @pytest.mark.asyncio
    async def test_edit_combined_flags(self) -> None:
        proc = _make_proc(stdout="Updated task #42\n")
        with _patch_exec(proc) as mock_exec:
            ts = KanbanToolset(kanban_dir=KANBAN_DIR, kanban_bin=KANBAN_BIN)
            await ts.kanban_edit(
                task_id="42",
                priority="critical",
                tags="urgent",
                append_body="Hot fix required",
            )

        args = mock_exec.call_args[0]
        assert "--priority" in args
        assert "--tags" in args
        assert "--append-body" in args


# ---------------------------------------------------------------------------
# kanban_pick
# ---------------------------------------------------------------------------


class TestKanbanPick:
    """kanban_pick calls pick with optional flags."""

    @pytest.mark.asyncio
    async def test_pick_basic(self) -> None:
        proc = _make_proc(stdout="Picked task #55\n")
        with _patch_exec(proc) as mock_exec:
            ts = KanbanToolset(kanban_dir=KANBAN_DIR, kanban_bin=KANBAN_BIN)
            result = await ts.kanban_pick()

        args = mock_exec.call_args[0]
        assert "pick" in args
        assert "--no-color" in args
        assert "--dir" in args
        assert "Picked" in result

    @pytest.mark.asyncio
    async def test_pick_with_status(self) -> None:
        proc = _make_proc(stdout="Picked task #56\n")
        with _patch_exec(proc) as mock_exec:
            ts = KanbanToolset(kanban_dir=KANBAN_DIR, kanban_bin=KANBAN_BIN)
            await ts.kanban_pick(status="todo")

        args = mock_exec.call_args[0]
        assert "--status" in args
        status_idx = args.index("--status")
        assert args[status_idx + 1] == "todo"

    @pytest.mark.asyncio
    async def test_pick_with_claim(self) -> None:
        proc = _make_proc(stdout="Picked task #57\n")
        with _patch_exec(proc) as mock_exec:
            ts = KanbanToolset(kanban_dir=KANBAN_DIR, kanban_bin=KANBAN_BIN)
            await ts.kanban_pick(claim="builder")

        args = mock_exec.call_args[0]
        assert "--claim" in args
        claim_idx = args.index("--claim")
        assert args[claim_idx + 1] == "builder"

    @pytest.mark.asyncio
    async def test_pick_with_move(self) -> None:
        proc = _make_proc(stdout="Picked task #58\n")
        with _patch_exec(proc) as mock_exec:
            ts = KanbanToolset(kanban_dir=KANBAN_DIR, kanban_bin=KANBAN_BIN)
            await ts.kanban_pick(move="in-progress")

        args = mock_exec.call_args[0]
        assert "--move" in args
        move_idx = args.index("--move")
        assert args[move_idx + 1] == "in-progress"

    @pytest.mark.asyncio
    async def test_pick_no_optional_flags(self) -> None:
        proc = _make_proc(stdout="Picked task\n")
        with _patch_exec(proc) as mock_exec:
            ts = KanbanToolset(kanban_dir=KANBAN_DIR, kanban_bin=KANBAN_BIN)
            await ts.kanban_pick()

        args = mock_exec.call_args[0]
        assert "--status" not in args
        assert "--claim" not in args
        assert "--move" not in args


# ---------------------------------------------------------------------------
# kanban_context
# ---------------------------------------------------------------------------


class TestKanbanContext:
    """kanban_context calls context."""

    @pytest.mark.asyncio
    async def test_context_command(self) -> None:
        proc = _make_proc(stdout="Board context summary\n")
        with _patch_exec(proc) as mock_exec:
            ts = KanbanToolset(kanban_dir=KANBAN_DIR, kanban_bin=KANBAN_BIN)
            result = await ts.kanban_context()

        args = mock_exec.call_args[0]
        assert args[0] == str(KANBAN_BIN)
        assert "context" in args
        assert "--no-color" in args
        assert "--dir" in args
        assert "Board context" in result


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """Non-zero exit codes return error strings, not exceptions."""

    @pytest.mark.asyncio
    async def test_list_error(self) -> None:
        proc = _make_proc(stderr="no tasks found", returncode=1)
        with _patch_exec(proc):
            ts = KanbanToolset(kanban_dir=KANBAN_DIR, kanban_bin=KANBAN_BIN)
            result = await ts.kanban_list()

        assert isinstance(result, str)
        assert "error:" in result
        assert "no tasks found" in result

    @pytest.mark.asyncio
    async def test_show_error(self) -> None:
        proc = _make_proc(stderr="task not found", returncode=1)
        with _patch_exec(proc):
            ts = KanbanToolset(kanban_dir=KANBAN_DIR, kanban_bin=KANBAN_BIN)
            result = await ts.kanban_show(task_id="999")

        assert "error:" in result
        assert "task not found" in result

    @pytest.mark.asyncio
    async def test_create_error(self) -> None:
        proc = _make_proc(stderr="invalid title", returncode=1)
        with _patch_exec(proc):
            ts = KanbanToolset(kanban_dir=KANBAN_DIR, kanban_bin=KANBAN_BIN)
            result = await ts.kanban_create(title="")

        assert "error:" in result

    @pytest.mark.asyncio
    async def test_move_error(self) -> None:
        proc = _make_proc(stderr="invalid status", returncode=1)
        with _patch_exec(proc):
            ts = KanbanToolset(kanban_dir=KANBAN_DIR, kanban_bin=KANBAN_BIN)
            result = await ts.kanban_move(task_id="42", status="nonexistent")

        assert "error:" in result
        assert "invalid status" in result

    @pytest.mark.asyncio
    async def test_edit_error(self) -> None:
        proc = _make_proc(stderr="task not found", returncode=1)
        with _patch_exec(proc):
            ts = KanbanToolset(kanban_dir=KANBAN_DIR, kanban_bin=KANBAN_BIN)
            result = await ts.kanban_edit(task_id="999")

        assert "error:" in result

    @pytest.mark.asyncio
    async def test_pick_error(self) -> None:
        proc = _make_proc(stderr="nothing to pick", returncode=1)
        with _patch_exec(proc):
            ts = KanbanToolset(kanban_dir=KANBAN_DIR, kanban_bin=KANBAN_BIN)
            result = await ts.kanban_pick()

        assert "error:" in result
        assert "nothing to pick" in result

    @pytest.mark.asyncio
    async def test_context_error(self) -> None:
        proc = _make_proc(stderr="board error", returncode=1)
        with _patch_exec(proc):
            ts = KanbanToolset(kanban_dir=KANBAN_DIR, kanban_bin=KANBAN_BIN)
            result = await ts.kanban_context()

        assert "error:" in result

    @pytest.mark.asyncio
    async def test_error_returns_string_not_exception(self) -> None:
        """Verify that errors don't raise — they return a string."""
        proc = _make_proc(stderr="something failed", returncode=1)
        with _patch_exec(proc):
            ts = KanbanToolset(kanban_dir=KANBAN_DIR, kanban_bin=KANBAN_BIN)
            # Should NOT raise
            result = await ts.kanban_list()

        assert isinstance(result, str)
        assert "error:" in result


# ---------------------------------------------------------------------------
# Hook emission
# ---------------------------------------------------------------------------


class TestHookEmission:
    """Mutating ops emit PRE_TOOL_USE, read-only ops don't."""

    @pytest.mark.asyncio
    async def test_create_emits_hook(self) -> None:
        hooks = HookRegistry()
        captured: list[dict] = []
        hooks.register(HookEvent.PRE_TOOL_USE, captured.append)

        proc = _make_proc(stdout="Created task #99\n")
        with _patch_exec(proc):
            ts = KanbanToolset(kanban_dir=KANBAN_DIR, kanban_bin=KANBAN_BIN, hooks=hooks)
            await ts.kanban_create(title="Hooked task")

        assert len(captured) == 1
        assert captured[0]["tool_name"] == "kanban_create"

    @pytest.mark.asyncio
    async def test_move_emits_hook(self) -> None:
        hooks = HookRegistry()
        captured: list[dict] = []
        hooks.register(HookEvent.PRE_TOOL_USE, captured.append)

        proc = _make_proc(stdout="Moved task #42\n")
        with _patch_exec(proc):
            ts = KanbanToolset(kanban_dir=KANBAN_DIR, kanban_bin=KANBAN_BIN, hooks=hooks)
            await ts.kanban_move(task_id="42", status="review")

        assert len(captured) == 1
        assert captured[0]["tool_name"] == "kanban_move"

    @pytest.mark.asyncio
    async def test_edit_emits_hook(self) -> None:
        hooks = HookRegistry()
        captured: list[dict] = []
        hooks.register(HookEvent.PRE_TOOL_USE, captured.append)

        proc = _make_proc(stdout="Updated task #42\n")
        with _patch_exec(proc):
            ts = KanbanToolset(kanban_dir=KANBAN_DIR, kanban_bin=KANBAN_BIN, hooks=hooks)
            await ts.kanban_edit(task_id="42", body="new body")

        assert len(captured) == 1
        assert captured[0]["tool_name"] == "kanban_edit"

    @pytest.mark.asyncio
    async def test_pick_emits_hook(self) -> None:
        hooks = HookRegistry()
        captured: list[dict] = []
        hooks.register(HookEvent.PRE_TOOL_USE, captured.append)

        proc = _make_proc(stdout="Picked task #55\n")
        with _patch_exec(proc):
            ts = KanbanToolset(kanban_dir=KANBAN_DIR, kanban_bin=KANBAN_BIN, hooks=hooks)
            await ts.kanban_pick()

        assert len(captured) == 1
        assert captured[0]["tool_name"] == "kanban_pick"

    @pytest.mark.asyncio
    async def test_list_does_not_emit_hook(self) -> None:
        hooks = HookRegistry()
        captured: list[dict] = []
        hooks.register(HookEvent.PRE_TOOL_USE, captured.append)

        proc = _make_proc(stdout="tasks\n")
        with _patch_exec(proc):
            ts = KanbanToolset(kanban_dir=KANBAN_DIR, kanban_bin=KANBAN_BIN, hooks=hooks)
            await ts.kanban_list()

        assert len(captured) == 0

    @pytest.mark.asyncio
    async def test_show_does_not_emit_hook(self) -> None:
        hooks = HookRegistry()
        captured: list[dict] = []
        hooks.register(HookEvent.PRE_TOOL_USE, captured.append)

        proc = _make_proc(stdout='{"id": "42"}\n')
        with _patch_exec(proc):
            ts = KanbanToolset(kanban_dir=KANBAN_DIR, kanban_bin=KANBAN_BIN, hooks=hooks)
            await ts.kanban_show(task_id="42")

        assert len(captured) == 0

    @pytest.mark.asyncio
    async def test_context_does_not_emit_hook(self) -> None:
        hooks = HookRegistry()
        captured: list[dict] = []
        hooks.register(HookEvent.PRE_TOOL_USE, captured.append)

        proc = _make_proc(stdout="context\n")
        with _patch_exec(proc):
            ts = KanbanToolset(kanban_dir=KANBAN_DIR, kanban_bin=KANBAN_BIN, hooks=hooks)
            await ts.kanban_context()

        assert len(captured) == 0

    @pytest.mark.asyncio
    async def test_hook_emitted_before_subprocess(self) -> None:
        """PRE_TOOL_USE must be emitted BEFORE the subprocess call."""
        call_order: list[str] = []

        hooks = HookRegistry()
        hooks.register(HookEvent.PRE_TOOL_USE, lambda _: call_order.append("hook"))

        proc = _make_proc(stdout="Created\n")

        async def tracking_exec(*_args: object, **_kwargs: object) -> AsyncMock:
            call_order.append("subprocess")
            return proc

        with patch(
            "owlbear.tools.kanban.asyncio.create_subprocess_exec",
            side_effect=tracking_exec,
        ):
            ts = KanbanToolset(kanban_dir=KANBAN_DIR, kanban_bin=KANBAN_BIN, hooks=hooks)
            await ts.kanban_create(title="ordered task")

        assert call_order == ["hook", "subprocess"]

    @pytest.mark.asyncio
    async def test_no_hooks_no_error(self) -> None:
        """Mutating ops work fine when hooks is None."""
        proc = _make_proc(stdout="Created\n")
        with _patch_exec(proc):
            ts = KanbanToolset(kanban_dir=KANBAN_DIR, kanban_bin=KANBAN_BIN, hooks=None)
            result = await ts.kanban_create(title="no hooks")

        assert "Created" in result
