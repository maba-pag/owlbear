"""Tests for BoardContextProvider — TTL cache and graceful degradation.

TDD RED phase: all tests target new behaviour described in #851 AC and
must fail against the current stub in src/owlbear/core/board_context.py.
"""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, patch

import pytest

from owlbear.core.board_context import BoardContextProvider

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DEFAULT_CMD = [
    "kanban/kanban-md.exe",
    "list",
    "--compact",
    "--status",
    "in-progress",
    "--status",
    "review",
    "--status",
    "todo",
    "--no-color",
    "--dir",
    "kanban",
]


def _make_proc(
    *,
    stdout: str = "board text\n",
    stderr: str = "",
    returncode: int = 0,
) -> AsyncMock:
    """Return a mock async subprocess with pre-configured communicate()."""
    proc = AsyncMock()
    proc.communicate.return_value = (stdout.encode(), stderr.encode())
    proc.returncode = returncode
    return proc


class _FakeTimer:
    """Controllable monotonic timer for TTL tests."""

    def __init__(self, start: float = 0.0) -> None:
        self._t = start

    def __call__(self) -> float:
        return self._t

    def advance(self, seconds: float) -> None:
        self._t += seconds


# ---------------------------------------------------------------------------
# TestFromAC_Constructor
# ---------------------------------------------------------------------------


class TestFromAC_Constructor:
    """Constructor accepts kanban_cmd, ttl_seconds, and timer (AC line 7)."""

    def test_default_kanban_cmd_is_full_list_command(self) -> None:
        """Default kanban_cmd must be the full list command with all required args."""
        provider = BoardContextProvider()
        assert provider.kanban_cmd == _DEFAULT_CMD

    def test_default_ttl_is_60_seconds(self) -> None:
        """Default TTL must be 60 seconds."""
        provider = BoardContextProvider()
        assert provider.ttl_seconds == 60

    def test_custom_kanban_cmd_is_stored(self) -> None:
        """Constructor stores a custom kanban_cmd."""
        cmd = ["my-kanban", "list", "--compact"]
        provider = BoardContextProvider(kanban_cmd=cmd)
        assert provider.kanban_cmd == cmd

    def test_custom_ttl_seconds_is_stored(self) -> None:
        """Constructor stores a custom ttl_seconds."""
        provider = BoardContextProvider(ttl_seconds=120)
        assert provider.ttl_seconds == 120

    def test_custom_timer_is_stored(self) -> None:
        """Constructor stores a custom timer callable."""
        timer = _FakeTimer()
        provider = BoardContextProvider(timer=timer)
        assert provider.timer is timer


# ---------------------------------------------------------------------------
# TestFromAC_GetContextHappyPath
# ---------------------------------------------------------------------------


class TestFromAC_GetContextHappyPath:
    """get_context() spawns the subprocess and returns decoded stdout (AC lines 1-3)."""

    @pytest.mark.asyncio
    async def test_runs_default_command_via_create_subprocess_exec(self) -> None:
        """get_context() must spawn the default command via create_subprocess_exec."""
        proc = _make_proc(stdout="board summary\n")
        with patch(
            "owlbear.core.board_context.asyncio.create_subprocess_exec",
            return_value=proc,
        ) as mock_exec:
            provider = BoardContextProvider()
            await provider.get_context()

        # Must have been called exactly once with the full default command
        mock_exec.assert_called_once()
        called_args = list(mock_exec.call_args[0])
        assert called_args == _DEFAULT_CMD

    @pytest.mark.asyncio
    async def test_returns_decoded_stdout(self) -> None:
        """get_context() must return the decoded stdout from the subprocess."""
        expected = "## Board\n- task A\n- task B\n"
        proc = _make_proc(stdout=expected)
        with patch(
            "owlbear.core.board_context.asyncio.create_subprocess_exec",
            return_value=proc,
        ):
            provider = BoardContextProvider()
            result = await provider.get_context()

        assert result == expected


# ---------------------------------------------------------------------------
# TestFromAC_TTLCache
# ---------------------------------------------------------------------------


class TestFromAC_TTLCache:
    """Caching: warm cache avoids subprocess; expiry and invalidation force refresh."""

    @pytest.mark.asyncio
    async def test_second_call_within_ttl_skips_subprocess(self) -> None:
        """Second call within the TTL window must not spawn a new subprocess."""
        timer = _FakeTimer(start=0.0)
        proc = _make_proc(stdout="board\n")
        with patch(
            "owlbear.core.board_context.asyncio.create_subprocess_exec",
            return_value=proc,
        ) as mock_exec:
            provider = BoardContextProvider(ttl_seconds=60, timer=timer)
            first = await provider.get_context()
            timer.advance(30)  # still within 60 s TTL
            second = await provider.get_context()

        assert mock_exec.call_count == 1
        assert second == first

    @pytest.mark.asyncio
    async def test_expired_ttl_reruns_subprocess(self) -> None:
        """After TTL expires the next call must spawn a fresh subprocess."""
        timer = _FakeTimer(start=0.0)
        proc_first = _make_proc(stdout="old board\n")
        proc_second = _make_proc(stdout="new board\n")
        with patch(
            "owlbear.core.board_context.asyncio.create_subprocess_exec",
            side_effect=[proc_first, proc_second],
        ) as mock_exec:
            provider = BoardContextProvider(ttl_seconds=60, timer=timer)
            first = await provider.get_context()
            timer.advance(61)  # past the 60 s TTL
            second = await provider.get_context()

        assert mock_exec.call_count == 2
        assert first == "old board\n"
        assert second == "new board\n"

    @pytest.mark.asyncio
    async def test_invalidate_forces_refresh_before_ttl(self) -> None:
        """invalidate() must cause the very next get_context() to rerun the subprocess."""
        timer = _FakeTimer(start=0.0)
        proc_first = _make_proc(stdout="stale\n")
        proc_second = _make_proc(stdout="fresh\n")
        with patch(
            "owlbear.core.board_context.asyncio.create_subprocess_exec",
            side_effect=[proc_first, proc_second],
        ) as mock_exec:
            provider = BoardContextProvider(ttl_seconds=60, timer=timer)
            first = await provider.get_context()
            timer.advance(5)  # well within TTL
            provider.invalidate()
            second = await provider.get_context()

        assert mock_exec.call_count == 2
        assert first == "stale\n"
        assert second == "fresh\n"

    def test_invalidate_before_any_call_does_not_raise(self) -> None:
        """invalidate() on a provider with no prior get_context() must not raise."""
        provider = BoardContextProvider()
        provider.invalidate()  # must not raise


# ---------------------------------------------------------------------------
# TestFromAC_GracefulDegradation
# ---------------------------------------------------------------------------


class TestFromAC_GracefulDegradation:
    """OSError and non-zero exit return '' and log WARNING — no propagation (AC lines 8-9)."""

    @pytest.mark.asyncio
    async def test_os_error_returns_empty_string(self) -> None:
        """OSError during subprocess spawn must return empty string (not propagate)."""
        with patch(
            "owlbear.core.board_context.asyncio.create_subprocess_exec",
            side_effect=OSError("spawn failed"),
        ) as mock_exec:
            provider = BoardContextProvider()
            result = await provider.get_context()

        mock_exec.assert_called_once()  # implementation must attempt the call
        assert result == ""

    @pytest.mark.asyncio
    async def test_os_error_logs_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        """OSError must emit a WARNING log — not propagate the exception."""
        with (
            patch(
                "owlbear.core.board_context.asyncio.create_subprocess_exec",
                side_effect=OSError("no binary"),
            ),
            caplog.at_level(logging.WARNING, logger="owlbear.core.board_context"),
        ):
            provider = BoardContextProvider()
            await provider.get_context()

        assert any(r.levelno == logging.WARNING for r in caplog.records)

    @pytest.mark.asyncio
    async def test_nonzero_exit_returns_empty_string(self) -> None:
        """Non-zero subprocess return code must yield empty string."""
        proc = _make_proc(stdout="should be ignored\n", stderr="error detail", returncode=1)
        with patch(
            "owlbear.core.board_context.asyncio.create_subprocess_exec",
            return_value=proc,
        ) as mock_exec:
            provider = BoardContextProvider()
            result = await provider.get_context()

        mock_exec.assert_called_once()
        assert result == ""

    @pytest.mark.asyncio
    async def test_nonzero_exit_logs_warning_with_return_code(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Non-zero exit must log a WARNING that includes the return code value."""
        proc = _make_proc(stdout="", stderr="bang", returncode=2)
        with (
            patch(
                "owlbear.core.board_context.asyncio.create_subprocess_exec",
                return_value=proc,
            ),
            caplog.at_level(logging.WARNING, logger="owlbear.core.board_context"),
        ):
            provider = BoardContextProvider()
            await provider.get_context()

        warning_msgs = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
        assert warning_msgs, "Expected at least one WARNING log entry"
        assert any("2" in msg for msg in warning_msgs), (
            "Expected the return code (2) to appear in at least one WARNING message"
        )
