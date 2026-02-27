"""Tests for ContextInjectionHook — SESSION_START context injection.

Covers: register on SESSION_START, fire with file + kanban context,
missing instructions file, kanban command failure, context format,
and HookRegistry integration.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from owlbear.core.context_hook import ContextInjectionHook
from owlbear.core.hooks import HookEvent, HookRegistry

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run(coro: object) -> None:
    """Convenience wrapper around asyncio.run for coroutines."""
    asyncio.run(coro)  # type: ignore[arg-type]


def _session_data(session_id: str = "test-session") -> dict[str, object]:
    """Build a SESSION_START payload."""
    return {"session_id": session_id}


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

    @patch("owlbear.core.context_hook.subprocess.run")
    def test_injects_context_into_data(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            stdout="## Board Summary\n- 3 in-progress",
            returncode=0,
        )
        instructions_content = "# OwlBear\nProject purpose text."
        hook = ContextInjectionHook(
            instructions_path=Path("fake/instructions.md"),
        )
        data = _session_data()

        with patch.object(Path, "read_text", return_value=instructions_content):
            _run(hook(data))

        assert "context" in data
        ctx = data["context"]
        assert isinstance(ctx, dict)
        assert ctx["instructions"] == instructions_content
        assert ctx["kanban_summary"] == "## Board Summary\n- 3 in-progress"

    @patch("owlbear.core.context_hook.subprocess.run")
    def test_kanban_cmd_called_with_correct_args(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(stdout="summary", returncode=0)
        cmd = ["tools/kanban-md.exe", "context"]
        hook = ContextInjectionHook(
            instructions_path=Path("fake.md"),
            kanban_cmd=cmd,
        )
        data = _session_data()

        with patch.object(Path, "read_text", return_value="content"):
            _run(hook(data))

        mock_run.assert_called_once_with(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )

    @patch("owlbear.core.context_hook.subprocess.run")
    def test_non_dict_data_ignored(self, mock_run: MagicMock) -> None:
        """Non-dict payload is silently ignored (no crash)."""
        hook = ContextInjectionHook()
        _run(hook("not a dict"))  # type: ignore[arg-type]
        mock_run.assert_not_called()


# ---------------------------------------------------------------------------
# Missing instructions file
# ---------------------------------------------------------------------------


class TestContextInjectionHookMissingFile:
    """Gracefully handles missing instructions file."""

    @patch("owlbear.core.context_hook.subprocess.run")
    def test_missing_file_logs_warning(
        self,
        mock_run: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        mock_run.return_value = MagicMock(stdout="board", returncode=0)
        hook = ContextInjectionHook(
            instructions_path=Path("nonexistent/file.md"),
        )
        data = _session_data()

        with (
            patch.object(Path, "read_text", side_effect=FileNotFoundError("gone")),
            caplog.at_level("WARNING", logger="owlbear.core.context_hook"),
        ):
            _run(hook(data))

        assert any("file.md" in r.message for r in caplog.records)

    @patch("owlbear.core.context_hook.subprocess.run")
    def test_missing_file_sets_empty_instructions(
        self,
        mock_run: MagicMock,
    ) -> None:
        mock_run.return_value = MagicMock(stdout="board", returncode=0)
        hook = ContextInjectionHook(
            instructions_path=Path("nonexistent/file.md"),
        )
        data = _session_data()

        with patch.object(Path, "read_text", side_effect=FileNotFoundError("gone")):
            _run(hook(data))

        assert data["context"]["instructions"] == ""  # type: ignore[index]


# ---------------------------------------------------------------------------
# Kanban command failure
# ---------------------------------------------------------------------------


class TestContextInjectionHookKanbanFailure:
    """Gracefully handles kanban command failures."""

    @patch("owlbear.core.context_hook.subprocess.run")
    def test_kanban_failure_logs_warning(
        self,
        mock_run: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        mock_run.return_value = MagicMock(
            stdout="",
            stderr="error text",
            returncode=1,
        )
        hook = ContextInjectionHook(
            instructions_path=Path("fake.md"),
        )
        data = _session_data()

        with (
            patch.object(Path, "read_text", return_value="content"),
            caplog.at_level("WARNING", logger="owlbear.core.context_hook"),
        ):
            _run(hook(data))

        assert any("kanban" in r.message.lower() for r in caplog.records)

    @patch("owlbear.core.context_hook.subprocess.run")
    def test_kanban_failure_sets_empty_summary(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            stdout="",
            stderr="error",
            returncode=1,
        )
        hook = ContextInjectionHook(
            instructions_path=Path("fake.md"),
        )
        data = _session_data()

        with patch.object(Path, "read_text", return_value="content"):
            _run(hook(data))

        assert data["context"]["kanban_summary"] == ""  # type: ignore[index]

    @patch("owlbear.core.context_hook.subprocess.run")
    def test_kanban_exception_sets_empty_summary(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = OSError("command not found")
        hook = ContextInjectionHook(
            instructions_path=Path("fake.md"),
        )
        data = _session_data()

        with patch.object(Path, "read_text", return_value="content"):
            _run(hook(data))

        assert data["context"]["kanban_summary"] == ""  # type: ignore[index]


# ---------------------------------------------------------------------------
# Integration with HookRegistry
# ---------------------------------------------------------------------------


class TestContextInjectionHookIntegration:
    """End-to-end: register + emit fires the hook."""

    @patch("owlbear.core.context_hook.subprocess.run")
    def test_emit_session_start_fires_hook(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(stdout="board ctx", returncode=0)
        registry = HookRegistry()
        hook = ContextInjectionHook(
            instructions_path=Path("fake.md"),
        )
        hook.register(registry)

        data = _session_data("s1")

        with patch.object(Path, "read_text", return_value="# Project"):
            _run(registry.emit(HookEvent.SESSION_START, data))

        ctx = data["context"]
        assert isinstance(ctx, dict)
        assert ctx["instructions"] == "# Project"
        assert ctx["kanban_summary"] == "board ctx"

    @patch("owlbear.core.context_hook.subprocess.run")
    def test_emit_other_event_does_not_fire(self, mock_run: MagicMock) -> None:
        registry = HookRegistry()
        hook = ContextInjectionHook()
        hook.register(registry)

        data: dict[str, object] = {"session_id": "s1"}
        _run(registry.emit(HookEvent.ON_MESSAGE, data))

        assert "context" not in data
        mock_run.assert_not_called()
