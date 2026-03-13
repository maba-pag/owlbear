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
from owlbear.tools.terminal import TerminalResult, TerminalToolset, _truncate

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


# ---------------------------------------------------------------------------
# Line-boundary truncation (RED tests for #764)
# ---------------------------------------------------------------------------


class TestFromAC_LineBoundaryTruncation:  # noqa: N801
    """Tests for _truncate() line-boundary snapping contract (#764).

    The new _truncate() must snap at newline boundaries, use a 60/40
    head/tail byte budget, and produce a marker with line/byte stats.
    """

    # -- AC: head section ends at a newline boundary (not mid-line) -----------

    def test_head_ends_at_newline_boundary(self) -> None:
        """Head section must end exactly at a newline, never mid-line."""
        # 18-byte lines; naive half=200 → 200/18=11.1 → mid-line cut
        lines = [f"line-{i:04d}-padding\n" for i in range(60)]
        output = "".join(lines)  # 1080 bytes
        max_bytes = 400  # half=200 → falls mid-line for naive split
        result = _truncate(output, max_bytes)
        # Extract head before the marker
        marker_start = result.index("[")
        head = result[:marker_start].rstrip("\n")
        # Head must end with a complete line (not a fragment like "li")
        last_head_line = head.rsplit("\n", 1)[-1]
        assert last_head_line.endswith("padding"), (
            f"Head ends mid-line with fragment: {last_head_line!r}"
        )

    def test_head_contains_only_complete_lines(self) -> None:
        """Every line in the head portion should be a complete line from the original."""
        lines = [f"row-{i:04d}-data\n" for i in range(80)]
        output = "".join(lines)
        max_bytes = len(output) // 3
        result = _truncate(output, max_bytes)
        head = result.split("[")[0]
        # Each line in head must appear verbatim in the original
        for line in head.splitlines(keepends=True):
            assert line in output

    # -- AC: tail section starts at a newline boundary (not mid-line) ---------

    def test_tail_starts_at_newline_boundary(self) -> None:
        """Tail section must begin at the start of a line, never mid-line."""
        # 18-byte lines; naive tail at output[-200:] starts mid-line
        lines = [f"line-{i:04d}-padding\n" for i in range(60)]
        output = "".join(lines)  # 1080 bytes
        max_bytes = 400
        result = _truncate(output, max_bytes)
        # Extract tail: everything after the marker
        marker_end = result.index("]") + 1
        tail = result[marker_end:].lstrip("\n")
        # Tail must start with a complete line, not a fragment like "dding"
        first_tail_line = tail.split("\n", 1)[0]
        assert first_tail_line.startswith("line-"), (
            f"Tail starts with fragment: {first_tail_line!r}"
        )

    # -- AC: head gets ~60% of byte budget, tail gets ~40% -------------------

    def test_head_tail_ratio_approximately_60_40(self) -> None:
        """Head should get roughly 60% of the byte budget, tail ~40%."""
        lines = [f"line-{i:04d}\n" for i in range(200)]
        output = "".join(lines)
        max_bytes = len(output) // 3  # force significant truncation
        result = _truncate(output, max_bytes)

        # Extract head and tail around the marker
        marker_start = result.index("[")
        marker_end = result.index("]") + 1
        head = result[:marker_start]
        tail = result[marker_end:].lstrip("\n")

        head_bytes = len(head)
        tail_bytes = len(tail)
        total_kept = head_bytes + tail_bytes

        # Head should be ~60% of total kept bytes (strict enough to
        # exclude the current 50/50 split — old ratio ≈0.50)
        head_ratio = head_bytes / total_kept if total_kept else 0
        assert 0.55 <= head_ratio <= 0.65, f"Head ratio {head_ratio:.2f} not in [0.55, 0.65]"

    # -- AC: marker format matches expected pattern ---------------------------

    def test_marker_format_matches_spec(self) -> None:
        """Marker must match: [N lines / X.YKB truncated -- showing first A + last B lines]"""
        import re

        lines = [f"line-{i:03d}\n" for i in range(100)]
        output = "".join(lines)
        max_bytes = len(output) // 2
        result = _truncate(output, max_bytes)

        pattern = r"\[\d+ lines / \d+\.\d+KB truncated -- showing first \d+ \+ last \d+ lines\]"
        assert re.search(pattern, result), f"Marker not found in result. Got:\n{result}"

    def test_marker_line_counts_are_accurate(self) -> None:
        """The 'first A + last B lines' in the marker should match actual line counts."""
        import re

        lines = [f"line-{i:03d}\n" for i in range(100)]
        output = "".join(lines)
        max_bytes = len(output) // 2
        result = _truncate(output, max_bytes)

        match = re.search(
            r"\[(\d+) lines / [\d.]+KB truncated -- showing first (\d+) \+ last (\d+) lines\]",
            result,
        )
        assert match, "Marker not found"
        truncated_lines = int(match.group(1))
        first_n = int(match.group(2))
        last_n = int(match.group(3))

        # Count actual head and tail lines
        marker_start = result.index("[")
        marker_end = result.index("]") + 1
        head = result[:marker_start]
        tail = result[marker_end:].strip("\n")
        actual_head_lines = len(head.strip("\n").split("\n"))
        actual_tail_lines = len(tail.strip("\n").split("\n"))

        assert first_n == actual_head_lines
        assert last_n == actual_tail_lines
        assert truncated_lines == 100 - first_n - last_n

    def test_marker_kb_value_is_accurate(self) -> None:
        """The X.YKB in the marker should reflect actual truncated byte count."""
        import re

        lines = [f"line-{i:03d}\n" for i in range(100)]
        output = "".join(lines)
        max_bytes = len(output) // 2
        result = _truncate(output, max_bytes)

        match = re.search(r"\[\d+ lines / ([\d.]+)KB truncated", result)
        assert match, "Marker not found"
        reported_kb = float(match.group(1))

        # Compute actual omitted bytes
        marker_start = result.index("[")
        marker_end = result.index("]") + 1
        head = result[:marker_start]
        tail = result[marker_end:].lstrip("\n")
        omitted_bytes = len(output) - len(head) - len(tail)
        expected_kb = round(omitted_bytes / 1024, 1)

        assert abs(reported_kb - expected_kb) < 0.2, (
            f"Reported {reported_kb}KB but expected ~{expected_kb}KB"
        )

    # -- AC: output under max_bytes returned unchanged (regression guard) -----

    def test_output_under_max_bytes_unchanged(self) -> None:
        """Output shorter than max_bytes must be returned verbatim."""
        output = "short output\nwith lines\n"
        result = _truncate(output, max_bytes=10_000)
        assert result == output

    def test_output_exactly_at_max_bytes_unchanged(self) -> None:
        """Output exactly equal to max_bytes must be returned verbatim."""
        output = "a" * 500 + "\n"
        result = _truncate(output, max_bytes=len(output))
        assert result == output

    # -- AC: single-line output exceeding max_bytes truncates cleanly ---------

    def test_single_line_exceeding_max_bytes_truncates(self) -> None:
        """A single long line with no newlines should still be truncated."""
        import re

        output = "x" * 5000
        max_bytes = 500
        result = _truncate(output, max_bytes)
        assert len(result) < len(output)
        # Must use the new-style marker, not the old "[...truncated N bytes...]"
        pattern = r"\[\d+ lines / \d+\.\d+KB truncated -- showing first \d+ \+ last \d+ lines\]"
        assert re.search(pattern, result), (
            f"Expected new-style marker for single-line truncation. Got:\n{result}"
        )

    def test_single_line_preserves_head_and_tail_content(self) -> None:
        """Even with one line, head/tail content should follow 60/40 ratio."""
        output = "START" + "m" * 5000 + "END"
        max_bytes = 500
        result = _truncate(output, max_bytes)
        assert result.startswith("START")
        assert result.rstrip().endswith("END")
        # Head should be larger than tail (60/40 split, not 50/50)
        marker_start = result.index("[")
        marker_end = result.index("]") + 1
        head = result[:marker_start]
        tail = result[marker_end:]
        assert len(head) > len(tail), (
            f"Expected head > tail (60/40), got head={len(head)} tail={len(tail)}"
        )

    # -- AC: output with no newlines falls back to character-boundary split ---

    def test_no_newlines_falls_back_to_character_split(self) -> None:
        """When output has zero newlines, character-boundary split is used."""
        output = "a" * 3000
        max_bytes = 500
        result = _truncate(output, max_bytes)
        # Should still truncate with a marker
        assert "truncated" in result.lower()
        # Head + tail should be raw character slices (no newline to snap to)
        marker_start = result.index("[")
        head = result[:marker_start]
        assert head == "a" * len(head)

    def test_no_newlines_respects_byte_budget(self) -> None:
        """Character-boundary fallback must use new marker format."""
        import re

        output = "b" * 4000
        max_bytes = 600
        result = _truncate(output, max_bytes)
        assert len(result) < max_bytes + 200  # generous overhead for marker
        # Must use new-style marker even for no-newline content
        pattern = r"\[\d+ lines / \d+\.\d+KB truncated -- showing first \d+ \+ last \d+ lines\]"
        assert re.search(pattern, result), (
            f"Expected new-style marker in no-newlines truncation. Got:\n{result}"
        )
