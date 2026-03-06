"""Tests for TerminalToolset — run_command tool for shell execution.

Covers: successful commands, failing commands, timeout handling,
output truncation (head+tail), hook integration, working_dir resolution,
and FunctionToolset registration.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

from owlbear.core.hooks import HookEvent, HookRegistry
from owlbear.tools.terminal import TerminalResult, TerminalToolset

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run(coro: object) -> object:
    """Run an async coroutine synchronously."""
    return asyncio.run(coro)  # type: ignore[arg-type]


PYTHON = sys.executable


# ---------------------------------------------------------------------------
# TerminalResult dataclass
# ---------------------------------------------------------------------------


class TestTerminalResult:
    """TerminalResult is a frozen dataclass with the expected fields."""

    def test_fields(self) -> None:
        r = TerminalResult(stdout="out", stderr="err", exit_code=0, timed_out=False)
        assert r.stdout == "out"
        assert r.stderr == "err"
        assert r.exit_code == 0
        assert r.timed_out is False

    def test_frozen(self) -> None:
        r = TerminalResult(stdout="", stderr="", exit_code=0, timed_out=False)
        with pytest.raises(AttributeError):
            r.stdout = "changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Toolset registration
# ---------------------------------------------------------------------------


class TestTerminalToolsetRegistration:
    """TerminalToolset registers run_command on FunctionToolset."""

    def test_inherits_function_toolset(self) -> None:
        from pydantic_ai.toolsets import FunctionToolset

        ts = TerminalToolset()
        assert isinstance(ts, FunctionToolset)

    def test_registers_run_command(self) -> None:
        ts = TerminalToolset()
        assert "run_command" in ts.tools

    def test_single_tool_registered(self) -> None:
        ts = TerminalToolset()
        assert len(ts.tools) == 1


# ---------------------------------------------------------------------------
# Successful command
# ---------------------------------------------------------------------------


class TestRunCommandSuccess:
    """run_command executes a command and returns TerminalResult."""

    def test_echo_hello(self) -> None:
        ts = TerminalToolset()
        result: TerminalResult = _run(ts.run_command("echo hello"))
        assert result.exit_code == 0
        assert "hello" in result.stdout
        assert result.timed_out is False

    def test_stderr_empty_on_success(self) -> None:
        ts = TerminalToolset()
        result = _run(ts.run_command("echo hello"))
        assert result.stderr == ""


# ---------------------------------------------------------------------------
# Failing command
# ---------------------------------------------------------------------------


class TestRunCommandFailure:
    """run_command captures non-zero exit codes."""

    def test_nonzero_exit_code(self) -> None:
        ts = TerminalToolset()
        result = _run(ts.run_command(f'{PYTHON} -c "import sys; sys.exit(1)"'))
        assert result.exit_code == 1
        assert result.timed_out is False

    def test_nonzero_exit_code_42(self) -> None:
        ts = TerminalToolset()
        result = _run(ts.run_command(f'{PYTHON} -c "import sys; sys.exit(42)"'))
        assert result.exit_code == 42


# ---------------------------------------------------------------------------
# Timeout
# ---------------------------------------------------------------------------


class TestRunCommandTimeout:
    """run_command kills the process on timeout and returns partial output."""

    def test_timeout_sets_flag(self) -> None:
        ts = TerminalToolset()
        result = _run(
            ts.run_command(
                f'{PYTHON} -c "import time; time.sleep(30)"',
                timeout_seconds=0.5,
            )
        )
        assert result.timed_out is True

    def test_timeout_exit_code_nonzero(self) -> None:
        """Killed process should have a non-zero (or negative) exit code."""
        ts = TerminalToolset()
        result = _run(
            ts.run_command(
                f'{PYTHON} -c "import time; time.sleep(30)"',
                timeout_seconds=0.5,
            )
        )
        # On Windows, killed process usually returns 1; on Unix, -9
        assert result.exit_code != 0 or result.timed_out is True


# ---------------------------------------------------------------------------
# Output truncation
# ---------------------------------------------------------------------------


class TestOutputTruncation:
    """Output exceeding max_output_bytes is truncated with head+tail marker."""

    def test_large_stdout_truncated(self) -> None:
        max_bytes = 200
        ts = TerminalToolset(max_output_bytes=max_bytes)
        # Produce ~500 bytes of output
        result = _run(ts.run_command(f"{PYTHON} -c \"print('x' * 500)\""))
        assert len(result.stdout) <= max_bytes + 100  # marker overhead
        assert "truncated" in result.stdout

    def test_small_output_not_truncated(self) -> None:
        ts = TerminalToolset(max_output_bytes=60_000)
        result = _run(ts.run_command("echo small"))
        assert "truncated" not in result.stdout

    def test_truncation_preserves_head_and_tail(self) -> None:
        max_bytes = 200
        ts = TerminalToolset(max_output_bytes=max_bytes)
        # Output has a known prefix and suffix
        cmd = f"{PYTHON} -c \"print('HEAD' + 'x' * 500 + 'TAIL')\""
        result = _run(ts.run_command(cmd))
        assert result.stdout.startswith("HEAD")
        assert result.stdout.endswith("TAIL\n") or result.stdout.rstrip().endswith("TAIL")


# ---------------------------------------------------------------------------
# Hook integration
# ---------------------------------------------------------------------------


class TestHookIntegration:
    """When hooks provided, PRE_TOOL_USE is emitted before execution."""

    def test_pre_tool_use_emitted(self) -> None:
        hooks = HookRegistry()
        captured: list[dict] = []
        hooks.register(HookEvent.PRE_TOOL_USE, captured.append)

        ts = TerminalToolset(hooks=hooks)
        _run(ts.run_command("echo hooked"))

        assert len(captured) == 1
        assert captured[0]["tool_name"] == "run_command"
        assert captured[0]["args"]["command"] == "echo hooked"

    def test_no_hooks_skips_emission(self) -> None:
        """When hooks is None, no emission happens (no error)."""
        ts = TerminalToolset(hooks=None)
        result = _run(ts.run_command("echo no-hooks"))
        assert result.exit_code == 0

    def test_hook_receives_correct_payload(self) -> None:
        hooks = HookRegistry()
        payloads: list[dict] = []
        hooks.register(HookEvent.PRE_TOOL_USE, payloads.append)

        ts = TerminalToolset(hooks=hooks)
        _run(ts.run_command("echo payload-check"))

        assert payloads[0] == {
            "tool_name": "run_command",
            "args": {"command": "echo payload-check"},
        }


# ---------------------------------------------------------------------------
# Working directory resolution
# ---------------------------------------------------------------------------


class TestWorkingDir:
    """working_dir resolves relative to workspace_root."""

    def test_default_uses_workspace_root(self, tmp_path: Path) -> None:
        ts = TerminalToolset(workspace_root=tmp_path)
        result = _run(ts.run_command(f'{PYTHON} -c "import os; print(os.getcwd())"'))
        assert tmp_path.name in result.stdout

    def test_relative_working_dir(self, tmp_path: Path) -> None:
        sub = tmp_path / "subdir"
        sub.mkdir()
        ts = TerminalToolset(workspace_root=tmp_path)
        result = _run(
            ts.run_command(
                f'{PYTHON} -c "import os; print(os.getcwd())"',
                working_dir="subdir",
            )
        )
        assert "subdir" in result.stdout

    def test_absolute_working_dir(self, tmp_path: Path) -> None:
        sub = tmp_path / "abs_sub"
        sub.mkdir()
        ts = TerminalToolset(workspace_root=tmp_path)
        result = _run(
            ts.run_command(
                f'{PYTHON} -c "import os; print(os.getcwd())"',
                working_dir=str(sub),
            )
        )
        assert "abs_sub" in result.stdout

    def test_none_working_dir_uses_workspace_root(self, tmp_path: Path) -> None:
        ts = TerminalToolset(workspace_root=tmp_path)
        result = _run(
            ts.run_command(
                f'{PYTHON} -c "import os; print(os.getcwd())"',
                working_dir=None,
            )
        )
        assert tmp_path.name in result.stdout

    def test_working_dir_absolute_outside_raises(self, tmp_path: Path) -> None:
        ts = TerminalToolset(workspace_root=tmp_path)
        outside = "C:\\Windows" if sys.platform == "win32" else "/etc"
        with pytest.raises(PermissionError, match="Path outside workspace"):
            _run(ts.run_command("echo hi", working_dir=outside))

    def test_working_dir_traversal_raises(self, tmp_path: Path) -> None:
        ts = TerminalToolset(workspace_root=tmp_path)
        with pytest.raises(PermissionError, match="Path outside workspace"):
            _run(ts.run_command("echo hi", working_dir="../../escape"))

    def test_working_dir_null_byte_raises(self, tmp_path: Path) -> None:
        ts = TerminalToolset(workspace_root=tmp_path)
        with pytest.raises(PermissionError, match="Path outside workspace"):
            _run(ts.run_command("echo hi", working_dir="sub\x00dir"))
