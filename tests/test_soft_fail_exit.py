"""RED-phase tests for soft-fail exit classification (#765).

Tests the contract defined in #763 AC:
- classify_exit() pure function classifies exit-1-with-stdout as soft failure
- TerminalResult gains a soft_fail: bool = False field
- run_command() populates soft_fail via classify_exit()
- _run_command_wrapper annotates output with (soft-fail) when applicable
"""

from __future__ import annotations

import sys

import pytest

from owlbear.tools.terminal import TerminalResult, TerminalToolset, classify_exit

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PYTHON = sys.executable


# ---------------------------------------------------------------------------
# classify_exit — pure function
# ---------------------------------------------------------------------------


class TestFromAC_ClassifyExit:  # noqa: N801
    """classify_exit(exit_code, stdout) -> bool pure function tests."""

    # -- Happy path: exit 1 with real output = soft fail -------------------

    def test_exit1_with_output_is_soft_fail(self) -> None:
        """AC: classify_exit(1, 'some output') returns True."""
        assert classify_exit(1, "some output") is True

    def test_exit1_with_multiline_output(self) -> None:
        """Exit 1 with multi-line stdout is still soft fail."""
        assert classify_exit(1, "line1\nline2\n") is True

    # -- Edge: empty / whitespace-only stdout = not soft fail ---------------

    def test_exit1_empty_stdout_not_soft_fail(self) -> None:
        """AC: classify_exit(1, '') returns False."""
        assert classify_exit(1, "") is False

    def test_exit1_whitespace_only_not_soft_fail(self) -> None:
        """AC: classify_exit(1, '  \\n') returns False (whitespace-only)."""
        assert classify_exit(1, "  \n") is False

    def test_exit1_tabs_and_spaces_not_soft_fail(self) -> None:
        """Tabs + spaces + newlines = not meaningful output."""
        assert classify_exit(1, "\t  \n  \t\n") is False

    # -- Boundary: exit 0 is never soft fail --------------------------------

    def test_exit0_with_output_not_soft_fail(self) -> None:
        """AC: classify_exit(0, 'output') returns False (success)."""
        assert classify_exit(0, "output") is False

    def test_exit0_empty_not_soft_fail(self) -> None:
        """Exit 0 with no output is also not soft fail."""
        assert classify_exit(0, "") is False

    # -- Boundary: exit >= 2 is real error ----------------------------------

    def test_exit2_with_output_not_soft_fail(self) -> None:
        """AC: classify_exit(2, 'output') returns False (real error)."""
        assert classify_exit(2, "output") is False

    def test_exit127_with_output_not_soft_fail(self) -> None:
        """Exit 127 (command not found) is never soft fail."""
        assert classify_exit(127, "command not found") is False

    def test_negative_exit_code_not_soft_fail(self) -> None:
        """Negative exit code (killed by signal) is never soft fail."""
        assert classify_exit(-9, "output") is False


# ---------------------------------------------------------------------------
# TerminalResult.soft_fail field
# ---------------------------------------------------------------------------


class TestFromAC_TerminalResultSoftFail:  # noqa: N801
    """TerminalResult should have a soft_fail: bool = False field."""

    def test_default_soft_fail_is_false(self) -> None:
        """AC: TerminalResult default soft_fail is False."""
        r = TerminalResult(stdout="out", stderr="", exit_code=0, timed_out=False)
        assert r.soft_fail is False

    def test_soft_fail_can_be_set_true(self) -> None:
        """soft_fail field can be explicitly set to True."""
        r = TerminalResult(stdout="out", stderr="", exit_code=1, timed_out=False, soft_fail=True)
        assert r.soft_fail is True

    def test_soft_fail_frozen(self) -> None:
        """soft_fail should be frozen like other fields."""
        r = TerminalResult(stdout="", stderr="", exit_code=0, timed_out=False)
        with pytest.raises(AttributeError):
            r.soft_fail = True  # type: ignore[misc]


# ---------------------------------------------------------------------------
# run_command() integration — sets soft_fail via classify_exit
# ---------------------------------------------------------------------------


class TestFromAC_RunCommandSoftFail:  # noqa: N801
    """run_command() sets soft_fail=True for exit-1-with-stdout commands."""

    @pytest.mark.asyncio
    async def test_exit1_with_stdout_sets_soft_fail(self) -> None:
        """AC: run_command() sets soft_fail=True for exit-1-with-stdout."""
        ts = TerminalToolset()
        # exit 1 with output → soft_fail=True
        result: TerminalResult = await (
            ts.run_command(f"{PYTHON} -c \"import sys; print('found'); sys.exit(1)\"")
        )
        assert result.exit_code == 1
        assert result.soft_fail is True

    @pytest.mark.asyncio
    async def test_exit1_no_stdout_no_soft_fail(self) -> None:
        """exit 1 with no stdout → soft_fail=False."""
        ts = TerminalToolset()
        result: TerminalResult = await (ts.run_command(f'{PYTHON} -c "import sys; sys.exit(1)"'))
        assert result.exit_code == 1
        assert result.soft_fail is False

    @pytest.mark.asyncio
    async def test_exit0_no_soft_fail(self) -> None:
        """Successful command never gets soft_fail."""
        ts = TerminalToolset()
        result: TerminalResult = await (ts.run_command("echo hello"))
        assert result.exit_code == 0
        assert result.soft_fail is False

    @pytest.mark.asyncio
    async def test_exit2_no_soft_fail(self) -> None:
        """Real error (exit 2) does not get soft_fail."""
        ts = TerminalToolset()
        result: TerminalResult = await (
            ts.run_command(f"{PYTHON} -c \"import sys; print('output'); sys.exit(2)\"")
        )
        assert result.exit_code == 2
        assert result.soft_fail is False


# ---------------------------------------------------------------------------
# _run_command_wrapper — (soft-fail) annotation
# ---------------------------------------------------------------------------


class TestFromAC_WrapperSoftFailAnnotation:  # noqa: N801
    """_run_command_wrapper includes '(soft-fail)' when soft_fail is True."""

    @pytest.mark.asyncio
    async def test_soft_fail_annotation_present(self) -> None:
        """AC: wrapper includes '(soft-fail)' annotation when soft_fail is True."""
        ts = TerminalToolset()
        output: str = await (
            ts._run_command_wrapper(f"{PYTHON} -c \"import sys; print('data'); sys.exit(1)\"")
        )
        assert "(soft-fail)" in output

    @pytest.mark.asyncio
    async def test_no_annotation_on_success(self) -> None:
        """No (soft-fail) annotation for exit 0."""
        ts = TerminalToolset()
        output: str = await (ts._run_command_wrapper("echo hello"))
        assert "(soft-fail)" not in output

    @pytest.mark.asyncio
    async def test_no_annotation_on_real_error(self) -> None:
        """No (soft-fail) annotation for exit >= 2."""
        ts = TerminalToolset()
        output: str = await (
            ts._run_command_wrapper(f"{PYTHON} -c \"import sys; print('err'); sys.exit(2)\"")
        )
        assert "(soft-fail)" not in output
