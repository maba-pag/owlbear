"""Retry tests for VoiceProcessManager — TDD RED phase (task #62, retry cycle).

AC gap: 'Timeout: kill process and raise VoiceInitTimeout'.
The existing tests verify the exception is raised but not that the process is
killed before propagation. Since __aexit__ is never reached when __aenter__
raises, proc.kill() must be called inside _spawn_and_handshake to avoid leaks.

All tests fail on current HEAD: process is never killed on init failure.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlbear.voice.process import VoiceInitTimeout, VoiceProcessManager

# ---------------------------------------------------------------------------
# Fixtures / helpers (mirrors test_voice_process_manager.py conventions)
# ---------------------------------------------------------------------------

READY_LINE = b'{"type":"status","state":"ready"}\n'
EOF = b""

_COMMAND = ["voice-addon", "--stdio"]
_MODULE = "owlbear.voice.process"


def _make_proc(
    *,
    running: bool = True,
    lines: list[bytes] | None = None,
) -> MagicMock:
    proc = MagicMock()
    proc.stdin = AsyncMock()
    proc.stdin.write = MagicMock()
    proc.stdin.drain = AsyncMock()
    proc.stdin.close = MagicMock()
    proc.stdout = AsyncMock()
    proc.returncode = None if running else 1
    proc.terminate = MagicMock()
    proc.kill = MagicMock()
    proc.wait = AsyncMock(return_value=0)

    feed = lines if lines is not None else [READY_LINE]
    proc.stdout.readline = AsyncMock(side_effect=[*feed, *([EOF] * 200)])
    return proc


def _patch_spawn(proc: MagicMock) -> Any:  # noqa: ANN401
    return patch(
        f"{_MODULE}.asyncio.create_subprocess_exec",
        new=AsyncMock(return_value=proc),
    )


# ---------------------------------------------------------------------------
# Kill-on-init-failure (TestFromAC_InitKill)
# ---------------------------------------------------------------------------


class TestFromAC_InitKill:  # noqa: N801
    """AC: 'Timeout: kill process and raise VoiceInitTimeout'

    The spawned subprocess must be killed before VoiceInitTimeout propagates
    in both init failure cases: wait_for timeout and EOF without ready.
    """

    @pytest.mark.asyncio(loop_scope="function")
    async def test_init_timeout_kills_process_before_raising(self) -> None:
        """AC: 'Timeout: kill process and raise VoiceInitTimeout' (wait_for path)

        When asyncio.wait_for fires during the init handshake, the spawned
        subprocess must be killed before VoiceInitTimeout propagates. Because
        __aexit__ is never reached when __aenter__ raises, the manager cannot
        clean up via shutdown() -- kill must happen inside _spawn_and_handshake.

        Fails on current HEAD: TimeoutError is caught and immediately converted
        to VoiceInitTimeout without calling proc.kill(). The subprocess leaks.
        """
        proc = _make_proc(lines=[])

        async def _timed_out_wait_for(_coro: Any, *, timeout: float, **_kw: Any) -> Any:  # noqa: ASYNC109,ARG001
            raise TimeoutError

        with (
            _patch_spawn(proc),
            patch(f"{_MODULE}.asyncio.wait_for", new=_timed_out_wait_for),
            pytest.raises(VoiceInitTimeout),
        ):
            async with VoiceProcessManager(_COMMAND, init_timeout=0.5):
                pass

        # Process must be killed so it does not leak when __aenter__ raises.
        # On current HEAD proc.kill() is never called -- assertion fails.
        proc.kill.assert_called()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_init_eof_kills_process_before_raising(self) -> None:
        """AC: 'Timeout: kill process and raise VoiceInitTimeout' (EOF path)

        When stdout EOF arrives before the ready message, VoiceInitTimeout is
        raised. As with the wait_for timeout, __aexit__ is never reached, so the
        process must be explicitly killed inside _spawn_and_handshake.

        Fails on current HEAD: the EOF branch raises VoiceInitTimeout directly
        without calling proc.kill(). The subprocess leaks.
        """
        proc = _make_proc(lines=[EOF])  # EOF before ready message

        with _patch_spawn(proc), pytest.raises(VoiceInitTimeout):
            async with VoiceProcessManager(_COMMAND, init_timeout=5.0):
                pass

        # Process must be killed on EOF-as-crash during init.
        # On current HEAD proc.kill() is never called -- assertion fails.
        proc.kill.assert_called()
