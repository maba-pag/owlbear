"""Failing tests for VoiceProcessManager — TDD RED phase (task #141).

Covers: spawn with correct pipes, pipe verification, background read loop,
NDJSON parsing, malformed JSON handling, EOF crash detection, send
serialization + drain, BrokenPipeError on write, init handshake + timeout,
non-ready message queuing, 6-phase shutdown sequence, ProcessLookupError
suppression, restart budget exhaustion, counter reset after successful init,
context manager protocol, is_alive property, and receive().

All tests fail on current HEAD because
``packages/orchestrator/src/owlbear/voice/process.py`` does not yet exist.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlbear.voice.process import (
    VoiceInitTimeout,
    VoiceProcessError,
    VoiceProcessManager,
    VoiceRestartBudgetExhausted,
)
from owlbear.voice.protocol import ShutdownMsg, SpeakMsg, TranscriptMsg

# ---------------------------------------------------------------------------
# Protocol line fixtures
# ---------------------------------------------------------------------------

READY_LINE = b'{"type":"status","state":"ready"}\n'
IDLE_LINE = b'{"type":"status","state":"idle"}\n'
TRANSCRIPT_LINE = b'{"type":"transcript","text":"hello","line_idx":0,"final":true}\n'
PARTIAL_LINE = b'{"type":"partial","text":"hel","line_idx":0}\n'
ERROR_LINE = b'{"type":"error","code":"E1","message":"boom"}\n'
MALFORMED_LINE = b"not valid json\n"
EOF = b""

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_COMMAND = ["voice-addon", "--stdio"]
_MODULE = "owlbear.voice.process"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_proc(
    *,
    running: bool = True,
    lines: list[bytes] | None = None,
) -> MagicMock:
    """Return a mock asyncio subprocess.

    lines: sequence of bytes returned by stdout.readline(), followed by
           unlimited EOF. Default: [READY_LINE] so init handshake succeeds.
    """
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
# Exception hierarchy (TestFromAC_Exceptions)
# ---------------------------------------------------------------------------


class TestFromAC_Exceptions:  # noqa: N801
    """Custom exception hierarchy: VoiceProcessError → VoiceInitTimeout / VoiceRestartBudgetExhausted."""

    def test_voice_process_error_is_owlbear_error(self) -> None:
        from owlbear.errors import OwlBearError  # noqa: PLC0415

        assert issubclass(VoiceProcessError, OwlBearError)

    def test_voice_init_timeout_is_voice_process_error(self) -> None:
        assert issubclass(VoiceInitTimeout, VoiceProcessError)

    def test_restart_budget_exhausted_is_voice_process_error(self) -> None:
        assert issubclass(VoiceRestartBudgetExhausted, VoiceProcessError)


# ---------------------------------------------------------------------------
# Spawn (TestFromAC_Spawn)
# ---------------------------------------------------------------------------


class TestFromAC_Spawn:  # noqa: N801
    """__aenter__ spawns with correct pipes and validates non-None streams."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_spawns_with_stdin_pipe(self) -> None:
        proc = _make_proc()
        with _patch_spawn(proc) as mock_spawn:
            async with VoiceProcessManager(_COMMAND):
                _, kwargs = mock_spawn.call_args
                assert kwargs.get("stdin") == asyncio.subprocess.PIPE

    @pytest.mark.asyncio(loop_scope="function")
    async def test_spawns_with_stdout_pipe(self) -> None:
        proc = _make_proc()
        with _patch_spawn(proc) as mock_spawn:
            async with VoiceProcessManager(_COMMAND):
                _, kwargs = mock_spawn.call_args
                assert kwargs.get("stdout") == asyncio.subprocess.PIPE

    @pytest.mark.asyncio(loop_scope="function")
    async def test_spawns_with_stderr_none(self) -> None:
        proc = _make_proc()
        with _patch_spawn(proc) as mock_spawn:
            async with VoiceProcessManager(_COMMAND):
                _, kwargs = mock_spawn.call_args
                assert kwargs.get("stderr") is None

    @pytest.mark.asyncio(loop_scope="function")
    async def test_raises_when_proc_stdin_is_none(self) -> None:
        proc = _make_proc()
        proc.stdin = None
        with _patch_spawn(proc), pytest.raises((RuntimeError, OSError)):
            async with VoiceProcessManager(_COMMAND):
                pass

    @pytest.mark.asyncio(loop_scope="function")
    async def test_raises_when_proc_stdout_is_none(self) -> None:
        proc = _make_proc()
        proc.stdout = None
        with _patch_spawn(proc), pytest.raises((RuntimeError, OSError)):
            async with VoiceProcessManager(_COMMAND):
                pass


# ---------------------------------------------------------------------------
# Read loop (TestFromAC_ReadLoop)
# ---------------------------------------------------------------------------


class TestFromAC_ReadLoop:  # noqa: N801
    """Background read loop: parses NDJSON, queues messages, handles errors."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_valid_ndjson_pushed_to_receive_queue(self) -> None:
        proc = _make_proc(lines=[READY_LINE, TRANSCRIPT_LINE])
        with _patch_spawn(proc):
            async with VoiceProcessManager(_COMMAND) as manager:
                # Yield to let the read loop process TRANSCRIPT_LINE
                await asyncio.sleep(0)
                await asyncio.sleep(0)
                msg = await manager.receive()
                assert isinstance(msg, TranscriptMsg)
                assert msg.text == "hello"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_malformed_json_does_not_crash_manager(self) -> None:
        proc = _make_proc(lines=[READY_LINE, MALFORMED_LINE, TRANSCRIPT_LINE])
        with _patch_spawn(proc):
            async with VoiceProcessManager(_COMMAND) as manager:
                await asyncio.sleep(0)
                await asyncio.sleep(0)
                # Manager still alive and next valid message is accessible
                assert manager.is_alive

    @pytest.mark.asyncio(loop_scope="function")
    async def test_malformed_json_logs_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        proc = _make_proc(lines=[READY_LINE, MALFORMED_LINE])
        with _patch_spawn(proc):
            async with VoiceProcessManager(_COMMAND):
                with caplog.at_level(logging.WARNING):
                    await asyncio.sleep(0)
                    await asyncio.sleep(0)
        assert any("warn" in r.levelname.lower() for r in caplog.records)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_eof_is_treated_as_process_crash(self) -> None:
        """EOF on stdout triggers a restart attempt (not silent exit)."""
        initial_proc = _make_proc(lines=[READY_LINE, EOF])
        restart_proc = _make_proc(lines=[READY_LINE])  # stays up
        spawn_mock = AsyncMock(side_effect=[initial_proc, restart_proc])
        with patch(f"{_MODULE}.asyncio.create_subprocess_exec", new=spawn_mock):
            async with VoiceProcessManager(_COMMAND, max_restarts=1):
                await asyncio.sleep(0.05)
        # spawn_mock called at least twice: initial + restart after EOF crash
        assert spawn_mock.call_count >= 2  # noqa: PLR2004


# ---------------------------------------------------------------------------
# Write / send (TestFromAC_Send)
# ---------------------------------------------------------------------------


class TestFromAC_Send:  # noqa: N801
    """send() serializes VoiceInMessage via model_dump_json() + newline, then drains."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_send_serializes_with_trailing_newline(self) -> None:
        proc = _make_proc()
        msg = SpeakMsg(text="hello", interrupt=False)
        expected = (msg.model_dump_json() + "\n").encode()

        with _patch_spawn(proc):
            async with VoiceProcessManager(_COMMAND) as manager:
                await manager.send(msg)
        proc.stdin.write.assert_called_once_with(expected)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_send_drains_stdin_after_write(self) -> None:
        proc = _make_proc()
        msg = SpeakMsg(text="hello", interrupt=False)

        with _patch_spawn(proc):
            async with VoiceProcessManager(_COMMAND) as manager:
                await manager.send(msg)
        proc.stdin.drain.assert_awaited()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_send_broken_pipe_triggers_restart(self) -> None:
        """BrokenPipeError during write is treated as crash; restart is attempted."""
        proc = _make_proc()
        proc.stdin.drain.side_effect = BrokenPipeError
        restart_proc = _make_proc(lines=[READY_LINE])

        spawn_mock = AsyncMock(side_effect=[proc, restart_proc])
        msg = SpeakMsg(text="hi", interrupt=False)

        with patch(f"{_MODULE}.asyncio.create_subprocess_exec", new=spawn_mock):
            async with VoiceProcessManager(_COMMAND, max_restarts=1) as manager:
                with contextlib.suppress(BrokenPipeError, OSError):
                    await manager.send(msg)
                await asyncio.sleep(0.05)
        assert spawn_mock.call_count >= 2  # noqa: PLR2004


# ---------------------------------------------------------------------------
# Init handshake (TestFromAC_InitHandshake)
# ---------------------------------------------------------------------------


class TestFromAC_InitHandshake:  # noqa: N801
    """__aenter__ waits for StatusMsg(state=ready) before returning."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_aenter_completes_when_ready_received(self) -> None:
        proc = _make_proc(lines=[READY_LINE])
        with _patch_spawn(proc):
            # Must not raise — ready message arrives before timeout
            async with VoiceProcessManager(_COMMAND, init_timeout=5.0):
                pass

    @pytest.mark.asyncio(loop_scope="function")
    async def test_aenter_raises_voice_init_timeout(self) -> None:
        """If ready message never arrives within init_timeout, VoiceInitTimeout is raised."""
        proc = _make_proc(lines=[])  # no ready message
        # Patch wait_for to simulate timeout
        with _patch_spawn(proc), patch(
            f"{_MODULE}.asyncio.wait_for", side_effect=TimeoutError
        ), pytest.raises(VoiceInitTimeout):
            async with VoiceProcessManager(_COMMAND, init_timeout=0.01):
                pass

    @pytest.mark.asyncio(loop_scope="function")
    async def test_non_ready_messages_queued_during_handshake(self) -> None:
        """Non-ready messages received before ready are available via receive()."""
        proc = _make_proc(lines=[TRANSCRIPT_LINE, READY_LINE])
        with _patch_spawn(proc):
            async with VoiceProcessManager(_COMMAND) as manager:
                await asyncio.sleep(0)
                msg = await manager.receive()
                assert isinstance(msg, TranscriptMsg)


# ---------------------------------------------------------------------------
# Shutdown — 6-phase (TestFromAC_Shutdown)
# ---------------------------------------------------------------------------


class TestFromAC_Shutdown:  # noqa: N801
    """shutdown() / __aexit__ follows the 6-phase sequence exactly."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_phase1_sends_shutdown_msg(self) -> None:
        proc = _make_proc()
        expected_payload = (ShutdownMsg().model_dump_json() + "\n").encode()

        with _patch_spawn(proc):
            async with VoiceProcessManager(_COMMAND):
                pass  # __aexit__ calls shutdown()
        proc.stdin.write.assert_any_call(expected_payload)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_phase2_closes_stdin(self) -> None:
        proc = _make_proc()
        with _patch_spawn(proc):
            async with VoiceProcessManager(_COMMAND):
                pass
        proc.stdin.close.assert_called()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_phase3_waits_with_shutdown_timeout(self) -> None:
        proc = _make_proc()
        wait_mock = AsyncMock(return_value=0)
        with _patch_spawn(proc), patch(f"{_MODULE}.asyncio.wait_for", new=wait_mock):
            manager = VoiceProcessManager(_COMMAND, shutdown_timeout=3.0)
            await manager.__aenter__()
            await manager.shutdown()

        timeouts = [call.kwargs.get("timeout") for call in wait_mock.call_args_list]
        assert 3.0 in timeouts  # shutdown_timeout used in phase 3

    @pytest.mark.asyncio(loop_scope="function")
    async def test_phase4_terminates_process(self) -> None:
        proc = _make_proc()
        with _patch_spawn(proc), patch(
            f"{_MODULE}.asyncio.wait_for", side_effect=TimeoutError
        ):
            async with VoiceProcessManager(_COMMAND):
                pass
        proc.terminate.assert_called()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_phase5_waits_with_kill_timeout(self) -> None:
        proc = _make_proc()
        wait_calls: list[Any] = []

        async def fake_wait_for(coro: Any, **kw: Any) -> Any:  # noqa: ANN401
            t = kw.get("timeout")
            wait_calls.append(t)
            if len(wait_calls) == 1:
                raise TimeoutError  # phase 3 → triggers phase 4
            return await coro  # phase 5 succeeds

        with _patch_spawn(proc), patch(f"{_MODULE}.asyncio.wait_for", side_effect=fake_wait_for):
            async with VoiceProcessManager(_COMMAND, shutdown_timeout=3.0, kill_timeout=1.0):
                pass

        assert 1.0 in wait_calls  # kill_timeout used in phase 5

    @pytest.mark.asyncio(loop_scope="function")
    async def test_phase6_kills_process_when_phase5_times_out(self) -> None:
        proc = _make_proc()
        with _patch_spawn(proc), patch(
            f"{_MODULE}.asyncio.wait_for", side_effect=TimeoutError
        ):
            async with VoiceProcessManager(_COMMAND):
                pass
        proc.kill.assert_called()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_suppresses_process_lookup_error_on_terminate(self) -> None:
        proc = _make_proc()
        proc.terminate.side_effect = ProcessLookupError
        with _patch_spawn(proc), patch(
            f"{_MODULE}.asyncio.wait_for", side_effect=TimeoutError
        ):
            async with VoiceProcessManager(_COMMAND):
                pass  # must not propagate ProcessLookupError

    @pytest.mark.asyncio(loop_scope="function")
    async def test_suppresses_process_lookup_error_on_kill(self) -> None:
        proc = _make_proc()
        proc.kill.side_effect = ProcessLookupError
        with _patch_spawn(proc), patch(
            f"{_MODULE}.asyncio.wait_for", side_effect=TimeoutError
        ):
            async with VoiceProcessManager(_COMMAND):
                pass  # must not propagate ProcessLookupError

    @pytest.mark.asyncio(loop_scope="function")
    async def test_phase1_broken_pipe_skips_gracefully_to_phase2(self) -> None:
        """BrokenPipeError when sending ShutdownMsg: skip to phase 2 (close stdin)."""
        proc = _make_proc()
        proc.stdin.drain.side_effect = BrokenPipeError

        with _patch_spawn(proc):
            async with VoiceProcessManager(_COMMAND):
                pass  # must not raise BrokenPipeError
        proc.stdin.close.assert_called()  # phase 2 still runs

    @pytest.mark.asyncio(loop_scope="function")
    async def test_explicit_shutdown_also_calls_terminate(self) -> None:
        proc = _make_proc()
        with _patch_spawn(proc):
            manager = VoiceProcessManager(_COMMAND)
            await manager.__aenter__()
            with patch(f"{_MODULE}.asyncio.wait_for", side_effect=TimeoutError):
                await manager.shutdown()
        proc.terminate.assert_called()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_shutdown_cancels_read_loop_task(self) -> None:
        """Read loop background task is cancelled during shutdown."""
        proc = _make_proc()
        cancelled_tasks: list[asyncio.Task[Any]] = []

        original_cancel = asyncio.Task.cancel

        def capture_cancel(self: asyncio.Task[Any], *args: Any, **kwargs: Any) -> bool:  # noqa: ANN401
            cancelled_tasks.append(self)
            return original_cancel(self, *args, **kwargs)

        with _patch_spawn(proc), patch.object(asyncio.Task, "cancel", capture_cancel):
            async with VoiceProcessManager(_COMMAND):
                pass
        assert len(cancelled_tasks) > 0


# ---------------------------------------------------------------------------
# Restart budget (TestFromAC_RestartBudget)
# ---------------------------------------------------------------------------


class TestFromAC_RestartBudget:  # noqa: N801
    """Auto-restart budget: max_restarts exhaustion and counter reset on ready."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_raises_budget_exhausted_after_max_restarts(self) -> None:
        """After max_restarts crashes, VoiceRestartBudgetExhausted is raised."""
        # Each proc: ready (init ok) then EOF (crash triggers restart)
        def _crash_proc() -> MagicMock:
            return _make_proc(lines=[READY_LINE, EOF])

        spawn_mock = AsyncMock(side_effect=[_crash_proc() for _ in range(10)])
        with patch(f"{_MODULE}.asyncio.create_subprocess_exec", new=spawn_mock), pytest.raises(
            VoiceRestartBudgetExhausted
        ):
            async with VoiceProcessManager(_COMMAND, max_restarts=2):
                await asyncio.sleep(0.3)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_restart_counter_resets_after_successful_init(self) -> None:
        """Counter resets to 0 after each successful init; extends effective lifetime."""
        # max_restarts=1: without reset, would fail on 2nd crash.
        # With reset after each ready, should survive 3 restarts total.
        def _crash_proc() -> MagicMock:
            return _make_proc(lines=[READY_LINE, EOF])

        stable_proc = _make_proc(lines=[READY_LINE] * 200)
        spawn_mock = AsyncMock(
            side_effect=[
                _crash_proc(),  # initial: ok, crash → restart 1 (counter was 0 → resets after ok)
                _crash_proc(),  # restart 1: ok, crash → restart 2 (counter resets again)
                _crash_proc(),  # restart 2: ok, crash → restart 3 (ok resets)
                stable_proc,    # restart 3: stays up
            ]
        )
        with patch(f"{_MODULE}.asyncio.create_subprocess_exec", new=spawn_mock):
            # With max_restarts=1 and NO counter reset, this would raise after 2 spawns.
            # With counter reset it should reach the stable_proc.
            async with VoiceProcessManager(_COMMAND, max_restarts=1):
                await asyncio.sleep(0.1)
                assert spawn_mock.call_count >= 4  # noqa: PLR2004


# ---------------------------------------------------------------------------
# Context manager (TestFromAC_ContextManager)
# ---------------------------------------------------------------------------


class TestFromAC_ContextManager:  # noqa: N801
    """__aenter__ returns the manager instance; __aexit__ calls shutdown."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_aenter_returns_self(self) -> None:
        proc = _make_proc()
        with _patch_spawn(proc):
            manager = VoiceProcessManager(_COMMAND)
            result = await manager.__aenter__()
            await manager.__aexit__(None, None, None)
        assert result is manager

    @pytest.mark.asyncio(loop_scope="function")
    async def test_aexit_calls_shutdown(self) -> None:
        proc = _make_proc()
        with _patch_spawn(proc):
            manager = VoiceProcessManager(_COMMAND)
            manager.shutdown = AsyncMock()
            await manager.__aenter__()
            await manager.__aexit__(None, None, None)
        manager.shutdown.assert_awaited()


# ---------------------------------------------------------------------------
# is_alive (TestFromAC_IsAlive)
# ---------------------------------------------------------------------------


class TestFromAC_IsAlive:  # noqa: N801
    """is_alive reflects whether the managed process is running."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_is_alive_true_when_process_running(self) -> None:
        proc = _make_proc(running=True)
        with _patch_spawn(proc):
            async with VoiceProcessManager(_COMMAND) as manager:
                assert manager.is_alive is True

    @pytest.mark.asyncio(loop_scope="function")
    async def test_is_alive_false_when_process_exited(self) -> None:
        proc = _make_proc(running=False)
        with _patch_spawn(proc):
            async with VoiceProcessManager(_COMMAND) as manager:
                assert manager.is_alive is False

    def test_is_alive_false_before_entry(self) -> None:
        """is_alive is False before the context manager has been entered."""
        manager = VoiceProcessManager(_COMMAND)
        assert manager.is_alive is False


# ---------------------------------------------------------------------------
# receive (TestFromAC_Receive)
# ---------------------------------------------------------------------------


class TestFromAC_Receive:  # noqa: N801
    """receive() returns the next VoiceOutMessage from the internal queue."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_receive_returns_voice_out_message(self) -> None:
        proc = _make_proc(lines=[READY_LINE, TRANSCRIPT_LINE])
        with _patch_spawn(proc):
            async with VoiceProcessManager(_COMMAND) as manager:
                await asyncio.sleep(0)
                await asyncio.sleep(0)
                msg = await manager.receive()
        # Must be a valid VoiceOutMessage discriminated union member
        assert isinstance(msg, TranscriptMsg)
        assert msg.text == "hello"
        assert msg.line_idx == 0
        assert msg.final is True
