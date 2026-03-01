"""Integration tests for orchestrator kanban pipeline workflow.

Covers: KanbanToolset instantiated with mocked subprocess — verifies
kanban_pick -> kanban_show -> kanban_move sequence, error handling,
and kanban_edit --block for failure scenarios.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from owlbear.core.hooks import HookRegistry
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
# Pipeline sequence: pick -> show -> move
# ---------------------------------------------------------------------------


class TestKanbanPipelineSequence:
    """Verify pick -> show -> move sequence produces correct CLI calls."""

    @pytest.mark.asyncio
    async def test_pick_show_move_sequence(self) -> None:
        """Full pipeline: pick a task, read its AC, then move to review."""
        pick_proc = _make_proc(stdout='{"id": "42", "title": "My task"}')
        show_proc = _make_proc(stdout='{"id": "42", "body": "## AC\\n- item"}')
        move_proc = _make_proc(stdout="Moved 42 to review")

        hooks = HookRegistry()
        ts = KanbanToolset(kanban_dir=KANBAN_DIR, kanban_bin=KANBAN_BIN, hooks=hooks)

        # Step 1: pick
        with _patch_exec(pick_proc) as mock_exec:
            pick_result = await ts.kanban_pick(status="todo", move="in-progress")

        assert "42" in pick_result
        pick_args = mock_exec.call_args[0]
        assert pick_args[0] == str(KANBAN_BIN)
        assert "pick" in pick_args
        assert "--status" in pick_args
        assert "todo" in pick_args
        assert "--move" in pick_args
        assert "in-progress" in pick_args

        # Step 2: show
        with _patch_exec(show_proc) as mock_exec:
            show_result = await ts.kanban_show("42")

        assert "AC" in show_result or "body" in show_result
        show_args = mock_exec.call_args[0]
        assert "show" in show_args
        assert "42" in show_args

        # Step 3: move to review
        with _patch_exec(move_proc) as mock_exec:
            move_result = await ts.kanban_move("42", "review")

        assert "Moved" in move_result or "review" in move_result
        move_args = mock_exec.call_args[0]
        assert "move" in move_args
        assert "42" in move_args
        assert "review" in move_args

    @pytest.mark.asyncio
    async def test_pick_calls_with_claim_flag(self) -> None:
        """kanban_pick with claim passes --claim to the CLI."""
        proc = _make_proc(stdout='{"id": "99"}')
        ts = KanbanToolset(kanban_dir=KANBAN_DIR, kanban_bin=KANBAN_BIN)

        with _patch_exec(proc) as mock_exec:
            await ts.kanban_pick(status="todo", claim="orchestrator", move="in-progress")

        args = mock_exec.call_args[0]
        assert "--claim" in args
        claim_idx = args.index("--claim")
        assert args[claim_idx + 1] == "orchestrator"


# ---------------------------------------------------------------------------
# Error handling: move returns error string, not exception
# ---------------------------------------------------------------------------


class TestKanbanPipelineErrors:
    """Verify errors return strings, never raise exceptions."""

    @pytest.mark.asyncio
    async def test_move_error_returns_string(self) -> None:
        """Non-zero exit from kanban_move returns 'error: ...' string."""
        proc = _make_proc(stderr="task not found: 999", returncode=1)
        ts = KanbanToolset(kanban_dir=KANBAN_DIR, kanban_bin=KANBAN_BIN)

        with _patch_exec(proc):
            result = await ts.kanban_move("999", "review")

        assert result.startswith("error:")
        assert "999" in result

    @pytest.mark.asyncio
    async def test_pick_error_returns_string(self) -> None:
        """Non-zero exit from kanban_pick returns 'error: ...' string."""
        proc = _make_proc(stderr="no tasks match", returncode=1)
        ts = KanbanToolset(kanban_dir=KANBAN_DIR, kanban_bin=KANBAN_BIN)

        with _patch_exec(proc):
            result = await ts.kanban_pick(status="todo")

        assert result.startswith("error:")
        assert "no tasks match" in result

    @pytest.mark.asyncio
    async def test_show_error_returns_string(self) -> None:
        """Non-zero exit from kanban_show returns 'error: ...' string."""
        proc = _make_proc(stderr="unknown task: abc", returncode=1)
        ts = KanbanToolset(kanban_dir=KANBAN_DIR, kanban_bin=KANBAN_BIN)

        with _patch_exec(proc):
            result = await ts.kanban_show("abc")

        assert result.startswith("error:")
        assert "abc" in result


# ---------------------------------------------------------------------------
# Failure handling: kanban_edit --block
# ---------------------------------------------------------------------------


class TestKanbanPipelineBlockOnFailure:
    """Verify kanban_edit --block called when task processing fails."""

    @pytest.mark.asyncio
    async def test_edit_block_produces_correct_cli_call(self) -> None:
        """kanban_edit with block reason sends --block flag."""
        proc = _make_proc(stdout="Updated 42")
        hooks = HookRegistry()
        ts = KanbanToolset(kanban_dir=KANBAN_DIR, kanban_bin=KANBAN_BIN, hooks=hooks)

        with _patch_exec(proc) as mock_exec:
            result = await ts.kanban_edit("42", block="Build failed: test errors")

        assert "Updated" in result or "42" in result
        args = mock_exec.call_args[0]
        assert "edit" in args
        assert "42" in args
        assert "--block" in args
        block_idx = args.index("--block")
        assert args[block_idx + 1] == "Build failed: test errors"

    @pytest.mark.asyncio
    async def test_edit_block_error_returns_string(self) -> None:
        """If kanban_edit --block fails, return error string not exception."""
        proc = _make_proc(stderr="permission denied", returncode=1)
        ts = KanbanToolset(kanban_dir=KANBAN_DIR, kanban_bin=KANBAN_BIN)

        with _patch_exec(proc):
            result = await ts.kanban_edit("42", block="some reason")

        assert result.startswith("error:")

    @pytest.mark.asyncio
    async def test_edit_block_emits_pre_tool_hook(self) -> None:
        """Mutating kanban_edit emits PRE_TOOL_USE hook."""
        from owlbear.core.hooks import HookEvent

        proc = _make_proc(stdout="Updated 42")
        hooks = HookRegistry()
        hook_calls: list[object] = []

        async def _capture(payload: object) -> None:
            hook_calls.append(payload)

        hooks.register(HookEvent.PRE_TOOL_USE, _capture)
        ts = KanbanToolset(kanban_dir=KANBAN_DIR, kanban_bin=KANBAN_BIN, hooks=hooks)

        with _patch_exec(proc):
            await ts.kanban_edit("42", block="Build failed")

        assert len(hook_calls) == 1
        payload = hook_calls[0]
        assert isinstance(payload, dict)
        assert payload["tool_name"] == "kanban_edit"


# ---------------------------------------------------------------------------
# Orchestrator prompt has Kanban Pipeline section
# ---------------------------------------------------------------------------


class TestOrchestratorKanbanPrompt:
    """Verify orchestrator.md system prompt contains kanban pipeline guidance."""

    def test_prompt_contains_kanban_pipeline_section(self) -> None:
        from owlbear.core.agent_def import parse_agent_definition

        agents_dir = Path(__file__).resolve().parent.parent / "src" / "owlbear" / "agents"
        defn = parse_agent_definition(agents_dir / "orchestrator.md")
        assert "Kanban Pipeline" in defn.system_prompt

    def test_prompt_mentions_kanban_pick(self) -> None:
        from owlbear.core.agent_def import parse_agent_definition

        agents_dir = Path(__file__).resolve().parent.parent / "src" / "owlbear" / "agents"
        defn = parse_agent_definition(agents_dir / "orchestrator.md")
        assert "kanban_pick" in defn.system_prompt

    def test_prompt_mentions_status_lifecycle(self) -> None:
        from owlbear.core.agent_def import parse_agent_definition

        agents_dir = Path(__file__).resolve().parent.parent / "src" / "owlbear" / "agents"
        defn = parse_agent_definition(agents_dir / "orchestrator.md")
        prompt = defn.system_prompt
        assert "todo" in prompt
        assert "in-progress" in prompt
        assert "review" in prompt

    def test_prompt_mentions_dependency_awareness(self) -> None:
        from owlbear.core.agent_def import parse_agent_definition

        agents_dir = Path(__file__).resolve().parent.parent / "src" / "owlbear" / "agents"
        defn = parse_agent_definition(agents_dir / "orchestrator.md")
        assert "unblocked" in defn.system_prompt or "kanban_list" in defn.system_prompt

    def test_prompt_mentions_failure_handling(self) -> None:
        from owlbear.core.agent_def import parse_agent_definition

        agents_dir = Path(__file__).resolve().parent.parent / "src" / "owlbear" / "agents"
        defn = parse_agent_definition(agents_dir / "orchestrator.md")
        assert "kanban_edit" in defn.system_prompt
        assert "block" in defn.system_prompt.lower()

    def test_prompt_mentions_delegation_pattern(self) -> None:
        from owlbear.core.agent_def import parse_agent_definition

        agents_dir = Path(__file__).resolve().parent.parent / "src" / "owlbear" / "agents"
        defn = parse_agent_definition(agents_dir / "orchestrator.md")
        prompt = defn.system_prompt
        # Should mention: pick -> show AC -> delegate -> verify -> move
        assert "kanban_show" in prompt
        assert "kanban_move" in prompt
