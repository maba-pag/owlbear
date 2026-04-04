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

    def test_init_timeout_default_is_30_seconds(self) -> None:
        """AC: __init__(..., init_timeout: float = 30.0, ...)

        The constructor must default init_timeout to 30.0 so that callers
        who omit the parameter get a 30-second handshake deadline, not an
        indefinite block.
        """
        import inspect  # noqa: PLC0415

        sig = inspect.signature(VoiceProcessManager.__init__)
        param = sig.parameters["init_timeout"]
        assert param.default == 30.0, (
            f"init_timeout default must be 30.0 per AC; got {param.default!r}"
        )


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
        """VoiceInitTimeout is raised when asyncio.wait_for fires during handshake.

        Strengthened past LAX version: verifies wait_for is actually called with
        init_timeout — not just that VoiceInitTimeout propagates via EOF.

        Fails on current HEAD because _spawn_and_handshake uses bare readline()
        with no asyncio.wait_for, so recorded_timeouts stays empty.
        """
        proc = _make_proc(lines=[])  # no ready message
        recorded_timeouts: list[float] = []

        async def _timed_out_wait_for(_coro: Any, *, timeout: float, **_kw: Any) -> Any:  # noqa: ASYNC109
            recorded_timeouts.append(timeout)
            raise TimeoutError  # simulate timeout expiry

        with _patch_spawn(proc), patch(
            f"{_MODULE}.asyncio.wait_for", new=_timed_out_wait_for
        ), pytest.raises(VoiceInitTimeout):
            async with VoiceProcessManager(_COMMAND, init_timeout=0.5):
                pass

        # wait_for must have been called with the init_timeout value during handshake.
        # On current HEAD this assertion fails because wait_for is never called —
        # VoiceInitTimeout was raised via EOF, not via the timeout mechanism.
        assert 0.5 in recorded_timeouts, (
            f"asyncio.wait_for must be called with timeout=init_timeout (0.5) "
            f"during _spawn_and_handshake; recorded timeouts: {recorded_timeouts}"
        )

    @pytest.mark.asyncio(loop_scope="function")
    async def test_non_ready_messages_queued_during_handshake(self) -> None:
        """Non-ready messages received before ready are available via receive()."""
        proc = _make_proc(lines=[TRANSCRIPT_LINE, READY_LINE])
        with _patch_spawn(proc):
            async with VoiceProcessManager(_COMMAND) as manager:
                await asyncio.sleep(0)
                msg = await manager.receive()
                assert isinstance(msg, TranscriptMsg)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_init_timeout_enforced_via_wait_for(self) -> None:
        """Handshake must enforce init_timeout by wrapping readline in asyncio.wait_for.

        Fails on current HEAD because _spawn_and_handshake calls readline() directly
        without asyncio.wait_for, so init_timeout is stored but never enforced.
        A silent-but-alive voice process would hang the handshake indefinitely.

        Verifies fix: asyncio.wait_for must be called with timeout=init_timeout
        during the handshake readline loop so a timer-based VoiceInitTimeout fires.
        """
        proc = _make_proc(lines=[READY_LINE])
        captured_timeouts: list[float] = []

        _original_wait_for = asyncio.wait_for  # capture real impl before patching

        async def _recording_wait_for(coro: Any, *, timeout: float, **kw: Any) -> Any:  # noqa: ASYNC109
            captured_timeouts.append(timeout)
            return await _original_wait_for(coro, timeout=timeout, **kw)

        with _patch_spawn(proc), patch(f"{_MODULE}.asyncio.wait_for", new=_recording_wait_for):
            async with VoiceProcessManager(_COMMAND, init_timeout=7.5):
                pass

        # init_timeout (7.5) must appear among wait_for calls made during handshake.
        # On current HEAD only shutdown_timeout (5.0) and kill_timeout (2.0) appear —
        # the assertion below fails, proving the enforcement is absent.
        assert 7.5 in captured_timeouts, (
            f"asyncio.wait_for must be called with timeout=init_timeout (7.5) "
            f"during _spawn_and_handshake; recorded timeouts: {captured_timeouts}"
        )

    @pytest.mark.asyncio(loop_scope="function")
    async def test_default_init_timeout_enforced_via_wait_for(self) -> None:
        """Default init_timeout (30.0) must bound the handshake via asyncio.wait_for.

        AC: 'wait for StatusMsg(state=ready) within init_timeout'. The default of 30.0
        must be enforced — bare readline() with no wait_for is an unbounded wait that
        violates the AC contract for the common no-args call VoiceProcessManager(cmd).

        Fails on current HEAD: _DEFAULT_INIT_TIMEOUT sentinel maps 30.0 to None
        internally, so asyncio.wait_for is never called during the handshake when
        the caller omits init_timeout. Only shutdown timeouts (5.0, 2.0) appear.
        """
        proc = _make_proc(lines=[READY_LINE])
        recorded_timeouts: list[float] = []

        _original_wait_for = asyncio.wait_for  # capture real impl before patching

        async def _recording_wait_for(coro: Any, *, timeout: float, **kw: Any) -> Any:  # noqa: ASYNC109
            recorded_timeouts.append(timeout)
            return await _original_wait_for(coro, timeout=timeout, **kw)

        with _patch_spawn(proc), patch(f"{_MODULE}.asyncio.wait_for", new=_recording_wait_for):
            async with VoiceProcessManager(_COMMAND):  # default init_timeout=30.0
                pass

        # 30.0 must appear among wait_for calls made during the handshake phase.
        # On current HEAD the sentinel maps 30.0 to None so only shutdown_timeout (5.0)
        # appears — the assertion below fails, proving the default is not enforced.
        assert 30.0 in recorded_timeouts, (
            f"asyncio.wait_for must be called with timeout=30.0 for the default "
            f"init_timeout; recorded timeouts (shutdown only): {recorded_timeouts}"
        )


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
        with _patch_spawn(proc):
            manager = VoiceProcessManager(_COMMAND, shutdown_timeout=3.0)
            await manager.__aenter__()
            with patch(f"{_MODULE}.asyncio.wait_for", new=wait_mock):
                await manager.shutdown()

        timeouts = [call.kwargs.get("timeout") for call in wait_mock.call_args_list]
        assert 3.0 in timeouts  # shutdown_timeout used in phase 3

    @pytest.mark.asyncio(loop_scope="function")
    async def test_phase4_terminates_process(self) -> None:
        proc = _make_proc()
        with _patch_spawn(proc):
            manager = VoiceProcessManager(_COMMAND)
            await manager.__aenter__()
            with patch(f"{_MODULE}.asyncio.wait_for", side_effect=TimeoutError):
                await manager.shutdown()
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

        with _patch_spawn(proc):
            manager = VoiceProcessManager(_COMMAND, shutdown_timeout=3.0, kill_timeout=1.0)
            await manager.__aenter__()
            with patch(f"{_MODULE}.asyncio.wait_for", side_effect=fake_wait_for):
                await manager.shutdown()

        assert 1.0 in wait_calls  # kill_timeout used in phase 5

    @pytest.mark.asyncio(loop_scope="function")
    async def test_phase6_kills_process_when_phase5_times_out(self) -> None:
        proc = _make_proc()
        with _patch_spawn(proc):
            manager = VoiceProcessManager(_COMMAND)
            await manager.__aenter__()
            with patch(f"{_MODULE}.asyncio.wait_for", side_effect=TimeoutError):
                await manager.shutdown()
        proc.kill.assert_called()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_suppresses_process_lookup_error_on_terminate(self) -> None:
        proc = _make_proc()
        proc.terminate.side_effect = ProcessLookupError
        with _patch_spawn(proc):
            manager = VoiceProcessManager(_COMMAND)
            await manager.__aenter__()
            with patch(f"{_MODULE}.asyncio.wait_for", side_effect=TimeoutError):
                await manager.shutdown()  # must not propagate ProcessLookupError

    @pytest.mark.asyncio(loop_scope="function")
    async def test_suppresses_process_lookup_error_on_kill(self) -> None:
        proc = _make_proc()
        proc.kill.side_effect = ProcessLookupError
        with _patch_spawn(proc):
            manager = VoiceProcessManager(_COMMAND)
            await manager.__aenter__()
            with patch(f"{_MODULE}.asyncio.wait_for", side_effect=TimeoutError):
                await manager.shutdown()  # must not propagate ProcessLookupError

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
        """Read loop background task is cleaned up during shutdown.

        Avoids patching asyncio.Task.cancel — immutable C type in CPython 3.12.
        Instead, compares asyncio.all_tasks() before, during, and after the
        context manager to verify that background tasks created by the manager
        are done (cancelled or finished) by the time __aexit__ returns.
        """
        proc = _make_proc()
        baseline_tasks: set[asyncio.Task[Any]] = set(asyncio.all_tasks())

        with _patch_spawn(proc):
            async with VoiceProcessManager(_COMMAND):
                running_tasks = set(asyncio.all_tasks()) - baseline_tasks
            await asyncio.sleep(0)  # let cancellation propagate

        assert len(running_tasks) > 0, "expected at least one background task during context"
        assert all(t.done() for t in running_tasks), "all manager background tasks must be done after shutdown"


# ---------------------------------------------------------------------------
# Restart budget (TestFromAC_RestartBudget)
# ---------------------------------------------------------------------------


class TestFromAC_RestartBudget:  # noqa: N801
    """Auto-restart budget: max_restarts exhaustion and counter reset on ready."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_raises_budget_exhausted_after_max_restarts(self) -> None:
        """VoiceRestartBudgetExhausted raised when restart count exceeds max_restarts.

        With max_restarts=0, the first crash increments restart_count to 1 which
        exceeds the budget of 0 allowed restarts.  This avoids the contradiction
        with test_restart_counter_resets_after_successful_init: the reset-on-ready
        behaviour keeps the counter ≤ 1 when max_restarts ≥ 2, so the budget test
        uses max_restarts=0 to guarantee exhaustion on the very first crash.
        """
        # Proc completes init (ready), then crashes (EOF) → restart_count = 1 > 0
        proc = _make_proc(lines=[READY_LINE, EOF])
        spawn_mock = AsyncMock(side_effect=[proc, *[_make_proc() for _ in range(5)]])
        with patch(f"{_MODULE}.asyncio.create_subprocess_exec", new=spawn_mock), pytest.raises(
            VoiceRestartBudgetExhausted
        ):
            async with VoiceProcessManager(_COMMAND, max_restarts=0):
                await asyncio.sleep(0.2)

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
