"""Tests for ContextInjectionHook — SESSION_START context injection.

Covers: register on SESSION_START, fire with file + kanban context,
missing instructions file, kanban command failure, context format,
and HookRegistry integration.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from owlbear.core.context_hook import ContextInjectionHook
from owlbear.core.hooks import HookEvent, HookRegistry

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _session_data(session_id: str = "test-session") -> dict[str, object]:
    """Build a SESSION_START payload."""
    return {"session_id": session_id}


def _make_mock_process(*, stdout: str = "", stderr: str = "", returncode: int = 0) -> AsyncMock:
    """Create a mock async subprocess with communicate()."""
    proc = AsyncMock()
    proc.communicate.return_value = (stdout.encode(), stderr.encode())
    proc.returncode = returncode
    return proc


# ---------------------------------------------------------------------------
# Constructor defaults
# ---------------------------------------------------------------------------


class TestContextInjectionHookDefaults:
    """Constructor sets sensible defaults."""

    def test_default_instructions_path(self) -> None:
        hook = ContextInjectionHook()
        assert hook.instructions_path == Path(".github/copilot-instructions.md")

    def test_default_kanban_cmd(self) -> None:
        hook = ContextInjectionHook()
        assert hook.kanban_cmd == ["kanban/kanban-md.exe", "context"]

    def test_custom_instructions_path(self) -> None:
        custom = Path("docs/custom.md")
        hook = ContextInjectionHook(instructions_path=custom)
        assert hook.instructions_path == custom

    def test_custom_kanban_cmd(self) -> None:
        cmd = ["my-kanban", "summary"]
        hook = ContextInjectionHook(kanban_cmd=cmd)
        assert hook.kanban_cmd == cmd


# ---------------------------------------------------------------------------
# Register with HookRegistry
# ---------------------------------------------------------------------------


class TestContextInjectionHookRegister:
    """register() hooks into SESSION_START."""

    def test_register_adds_to_session_start(self) -> None:
        registry = HookRegistry()
        hook = ContextInjectionHook()
        hook.register(registry)
        assert hook in registry.handlers.get(HookEvent.SESSION_START, [])

    def test_register_does_not_add_to_other_events(self) -> None:
        registry = HookRegistry()
        hook = ContextInjectionHook()
        hook.register(registry)
        for event in HookEvent:
            if event != HookEvent.SESSION_START:
                assert hook not in registry.handlers.get(event, [])


# ---------------------------------------------------------------------------
# __call__ — happy path
# ---------------------------------------------------------------------------


class TestContextInjectionHookCall:
    """__call__ reads instructions file and runs kanban command."""

    @patch("owlbear.core.context_hook.asyncio.create_subprocess_exec")
    @patch("owlbear.core.context_hook.asyncio.to_thread")
    @pytest.mark.asyncio
    async def test_injects_context_into_data(
        self,
        mock_to_thread: AsyncMock,
        mock_exec: AsyncMock,
    ) -> None:
        instructions_content = "# OwlBear\nProject purpose text."
        mock_to_thread.return_value = instructions_content
        mock_exec.return_value = _make_mock_process(
            stdout="## Board Summary\n- 3 in-progress",
        )
        hook = ContextInjectionHook(
            instructions_path=Path("fake/instructions.md"),
        )
        data = _session_data()
        await (hook(data))

        assert "context" in data
        ctx = data["context"]
        assert isinstance(ctx, dict)
        assert ctx["instructions"] == instructions_content
        assert ctx["kanban_summary"] == "## Board Summary\n- 3 in-progress"

    @patch("owlbear.core.context_hook.asyncio.create_subprocess_exec")
    @patch("owlbear.core.context_hook.asyncio.to_thread")
    @pytest.mark.asyncio
    async def test_kanban_cmd_called_with_correct_args(
        self,
        mock_to_thread: AsyncMock,
        mock_exec: AsyncMock,
    ) -> None:
        mock_to_thread.return_value = "content"
        mock_exec.return_value = _make_mock_process(stdout="summary")
        cmd = ["kanban/kanban-md.exe", "context"]
        hook = ContextInjectionHook(
            instructions_path=Path("fake.md"),
            kanban_cmd=cmd,
        )
        data = _session_data()
        await (hook(data))

        mock_exec.assert_called_once_with(
            cmd[0],
            *cmd[1:],
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )



# ---------------------------------------------------------------------------
# Missing instructions file
# ---------------------------------------------------------------------------


class TestContextInjectionHookMissingFile:
    """Gracefully handles missing instructions file."""

    @patch("owlbear.core.context_hook.asyncio.create_subprocess_exec")
    @patch("owlbear.core.context_hook.asyncio.to_thread")
    @pytest.mark.asyncio
    async def test_missing_file_logs_warning(
        self,
        mock_to_thread: AsyncMock,
        mock_exec: AsyncMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        mock_to_thread.side_effect = FileNotFoundError("gone")
        mock_exec.return_value = _make_mock_process(stdout="board")
        hook = ContextInjectionHook(
            instructions_path=Path("nonexistent/file.md"),
        )
        data = _session_data()

        with caplog.at_level("WARNING", logger="owlbear.core.context_hook"):
            await (hook(data))

        assert any("file.md" in r.message for r in caplog.records)

    @patch("owlbear.core.context_hook.asyncio.create_subprocess_exec")
    @patch("owlbear.core.context_hook.asyncio.to_thread")
    @pytest.mark.asyncio
    async def test_missing_file_sets_empty_instructions(
        self,
        mock_to_thread: AsyncMock,
        mock_exec: AsyncMock,
    ) -> None:
        mock_to_thread.side_effect = FileNotFoundError("gone")
        mock_exec.return_value = _make_mock_process(stdout="board")
        hook = ContextInjectionHook(
            instructions_path=Path("nonexistent/file.md"),
        )
        data = _session_data()
        await (hook(data))

        assert data["context"]["instructions"] == ""  # type: ignore[index]


# ---------------------------------------------------------------------------
# Kanban command failure
# ---------------------------------------------------------------------------


class TestContextInjectionHookKanbanFailure:
    """Gracefully handles kanban command failures."""

    @patch("owlbear.core.context_hook.asyncio.to_thread")
    @patch("owlbear.core.context_hook.asyncio.create_subprocess_exec")
    @pytest.mark.asyncio
    async def test_kanban_failure_logs_warning(
        self,
        mock_exec: AsyncMock,
        mock_to_thread: AsyncMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        mock_to_thread.return_value = "content"
        mock_exec.return_value = _make_mock_process(
            stderr="error text",
            returncode=1,
        )
        hook = ContextInjectionHook(
            instructions_path=Path("fake.md"),
        )
        data = _session_data()

        with caplog.at_level("WARNING", logger="owlbear.core.context_hook"):
            await (hook(data))

        assert any("kanban" in r.message.lower() for r in caplog.records)

    @patch("owlbear.core.context_hook.asyncio.to_thread")
    @patch("owlbear.core.context_hook.asyncio.create_subprocess_exec")
    @pytest.mark.asyncio
    async def test_kanban_failure_sets_empty_summary(
        self,
        mock_exec: AsyncMock,
        mock_to_thread: AsyncMock,
    ) -> None:
        mock_to_thread.return_value = "content"
        mock_exec.return_value = _make_mock_process(
            stderr="error",
            returncode=1,
        )
        hook = ContextInjectionHook(
            instructions_path=Path("fake.md"),
        )
        data = _session_data()
        await (hook(data))

        assert data["context"]["kanban_summary"] == ""  # type: ignore[index]

    @patch("owlbear.core.context_hook.asyncio.to_thread")
    @patch("owlbear.core.context_hook.asyncio.create_subprocess_exec")
    @pytest.mark.asyncio
    async def test_kanban_exception_sets_empty_summary(
        self,
        mock_exec: AsyncMock,
        mock_to_thread: AsyncMock,
    ) -> None:
        mock_to_thread.return_value = "content"
        mock_exec.side_effect = OSError("command not found")
        hook = ContextInjectionHook(
            instructions_path=Path("fake.md"),
        )
        data = _session_data()
        await (hook(data))

        assert data["context"]["kanban_summary"] == ""  # type: ignore[index]


# ---------------------------------------------------------------------------
# Integration with HookRegistry
# ---------------------------------------------------------------------------


class TestContextInjectionHookIntegration:
    """End-to-end: register + emit fires the hook."""

    @patch("owlbear.core.context_hook.asyncio.create_subprocess_exec")
    @patch("owlbear.core.context_hook.asyncio.to_thread")
    @pytest.mark.asyncio
    async def test_emit_session_start_fires_hook(
        self,
        mock_to_thread: AsyncMock,
        mock_exec: AsyncMock,
    ) -> None:
        mock_to_thread.return_value = "# Project"
        mock_exec.return_value = _make_mock_process(stdout="board ctx")
        registry = HookRegistry()
        hook = ContextInjectionHook(
            instructions_path=Path("fake.md"),
        )
        hook.register(registry)

        data = _session_data("s1")
        await (registry.emit(HookEvent.SESSION_START, data))

        ctx = data["context"]
        assert isinstance(ctx, dict)
        assert ctx["instructions"] == "# Project"
        assert ctx["kanban_summary"] == "board ctx"

    @patch("owlbear.core.context_hook.asyncio.create_subprocess_exec")
    @pytest.mark.asyncio
    async def test_emit_other_event_does_not_fire(self, mock_exec: AsyncMock) -> None:
        registry = HookRegistry()
        hook = ContextInjectionHook()
        hook.register(registry)

        data: dict[str, object] = {"session_id": "s1"}
        await (registry.emit(HookEvent.ON_MESSAGE, data))

        assert "context" not in data
        mock_exec.assert_not_called()
