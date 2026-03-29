"""Failing tests for ProcessSupervisor ACP subprocess lifecycle (task #73).

Covers: spawn with correct pipes, FileNotFoundError on missing binary, pipe
verification, __aexit__ terminate/wait/kill sequence, ProcessLookupError
suppression, explicit shutdown(), is_alive property, ensure_running return
and respawn, and restart budget exhaustion + mark_healthy reset.

All tests fail on current HEAD because
``packages/orchestrator/src/owlbear_orchestrator/process_supervisor.py``
does not yet exist.
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from owlbear_orchestrator.process_supervisor import (
    ProcessRestartBudgetExhausted,
    ProcessSupervisor,
)

# ---------------------------------------------------------------------------
# Constants and helpers
# ---------------------------------------------------------------------------

_COMMAND = ["copilot", "--acp", "--stdio"]
_MODULE = "owlbear_orchestrator.process_supervisor"


def _make_proc(*, running: bool = True) -> MagicMock:
    """Return a mock asyncio subprocess."""
    proc = MagicMock()
    proc.stdin = MagicMock()
    proc.stdout = MagicMock()
    proc.returncode = None if running else 1
    proc.terminate = MagicMock()
    proc.kill = MagicMock()
    proc.wait = AsyncMock(return_value=0)
    return proc


# ---------------------------------------------------------------------------
# Helpers for cleaner patch setup
# ---------------------------------------------------------------------------

def _patch_spawn(proc: MagicMock) -> Any:  # noqa: ANN401
    return patch(f"{_MODULE}.asyncio.create_subprocess_exec", new=AsyncMock(return_value=proc))


def _patch_which(*, found: bool = True) -> Any:  # noqa: ANN401
    return patch(f"{_MODULE}.shutil.which", return_value="/usr/bin/copilot" if found else None)


async def _exhaust_budget(supervisor: ProcessSupervisor, n: int = 20) -> None:
    """Keep calling ensure_running until budget exhausts or n iterations pass."""
    for _ in range(n):
        await supervisor.ensure_running()


# ---------------------------------------------------------------------------
# __aenter__ spawn behaviour
# ---------------------------------------------------------------------------


class TestFromAC_Spawn:  # noqa: N801
    """__aenter__ spawns process with correct pipe arguments and validates pipes."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_spawns_with_stdin_pipe(self) -> None:
        proc = _make_proc()
        with _patch_spawn(proc) as mock_spawn, _patch_which():
            async with ProcessSupervisor(_COMMAND):
                _, kwargs = mock_spawn.call_args
                assert kwargs.get("stdin") == asyncio.subprocess.PIPE

    @pytest.mark.asyncio(loop_scope="function")
    async def test_spawns_with_stdout_pipe(self) -> None:
        proc = _make_proc()
        with _patch_spawn(proc) as mock_spawn, _patch_which():
            async with ProcessSupervisor(_COMMAND):
                _, kwargs = mock_spawn.call_args
                assert kwargs.get("stdout") == asyncio.subprocess.PIPE

    @pytest.mark.asyncio(loop_scope="function")
    async def test_spawns_with_stderr_none(self) -> None:
        proc = _make_proc()
        with _patch_spawn(proc) as mock_spawn, _patch_which():
            async with ProcessSupervisor(_COMMAND):
                _, kwargs = mock_spawn.call_args
                assert kwargs.get("stderr") is None

    @pytest.mark.asyncio(loop_scope="function")
    async def test_raises_file_not_found_when_binary_missing(self) -> None:
        with _patch_which(found=False), pytest.raises(FileNotFoundError):
            async with ProcessSupervisor(_COMMAND):
                pass

    @pytest.mark.asyncio(loop_scope="function")
    async def test_raises_when_proc_stdin_is_none(self) -> None:
        """Supervisor must raise when spawn produces proc.stdin = None."""
        proc = _make_proc()
        proc.stdin = None
        with _patch_spawn(proc), _patch_which(), pytest.raises(RuntimeError):
            async with ProcessSupervisor(_COMMAND):
                pass

    @pytest.mark.asyncio(loop_scope="function")
    async def test_raises_when_proc_stdout_is_none(self) -> None:
        """Supervisor must raise when spawn produces proc.stdout = None."""
        proc = _make_proc()
        proc.stdout = None
        with _patch_spawn(proc), _patch_which(), pytest.raises(RuntimeError):
            async with ProcessSupervisor(_COMMAND):
                pass


# ---------------------------------------------------------------------------
# __aexit__ and shutdown() terminate / wait / kill sequence
# ---------------------------------------------------------------------------


class TestFromAC_Shutdown:  # noqa: N801
    """__aexit__ and explicit shutdown() follow terminate → wait → kill sequence."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_aexit_calls_terminate(self) -> None:
        proc = _make_proc()
        with _patch_spawn(proc), _patch_which():
            async with ProcessSupervisor(_COMMAND):
                pass
        proc.terminate.assert_called()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_aexit_kills_if_not_terminated_within_timeout(self) -> None:
        proc = _make_proc()
        wait_for_timeout = patch(f"{_MODULE}.asyncio.wait_for", side_effect=asyncio.TimeoutError)
        with _patch_spawn(proc), _patch_which(), wait_for_timeout:
            async with ProcessSupervisor(_COMMAND):
                pass
        proc.kill.assert_called()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_aexit_does_not_kill_when_process_exits_cleanly(self) -> None:
        proc = _make_proc()
        with _patch_spawn(proc), _patch_which():
            async with ProcessSupervisor(_COMMAND):
                pass
        proc.kill.assert_not_called()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_aexit_suppresses_process_lookup_error_on_terminate(self) -> None:
        proc = _make_proc()
        proc.terminate.side_effect = ProcessLookupError
        with _patch_spawn(proc), _patch_which():
            async with ProcessSupervisor(_COMMAND):
                pass  # must not propagate ProcessLookupError

    @pytest.mark.asyncio(loop_scope="function")
    async def test_aexit_suppresses_process_lookup_error_on_kill(self) -> None:
        proc = _make_proc()
        proc.kill.side_effect = ProcessLookupError
        wait_for_timeout = patch(f"{_MODULE}.asyncio.wait_for", side_effect=asyncio.TimeoutError)
        with _patch_spawn(proc), _patch_which(), wait_for_timeout:
            async with ProcessSupervisor(_COMMAND):
                pass  # must not propagate ProcessLookupError from kill

    @pytest.mark.asyncio(loop_scope="function")
    async def test_shutdown_explicit_calls_terminate(self) -> None:
        """shutdown() called directly (not via __aexit__) also calls terminate."""
        proc = _make_proc()
        with _patch_spawn(proc), _patch_which():
            supervisor = ProcessSupervisor(_COMMAND)
            await supervisor.__aenter__()
            await supervisor.shutdown()
        proc.terminate.assert_called()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_shutdown_explicit_kills_if_timeout(self) -> None:
        """shutdown() kills the process when it does not exit within the timeout."""
        proc = _make_proc()
        with _patch_spawn(proc), _patch_which():
            supervisor = ProcessSupervisor(_COMMAND)
            await supervisor.__aenter__()
            with patch(f"{_MODULE}.asyncio.wait_for", side_effect=asyncio.TimeoutError):
                await supervisor.shutdown()
        proc.kill.assert_called()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_shutdown_explicit_suppresses_process_lookup_error(self) -> None:
        """shutdown() suppresses ProcessLookupError during cleanup."""
        proc = _make_proc()
        proc.terminate.side_effect = ProcessLookupError
        with _patch_spawn(proc), _patch_which():
            supervisor = ProcessSupervisor(_COMMAND)
            await supervisor.__aenter__()
            await supervisor.shutdown()  # must not raise


# ---------------------------------------------------------------------------
# is_alive property
# ---------------------------------------------------------------------------


class TestFromAC_IsAlive:  # noqa: N801
    """is_alive returns True when process running, False when exited."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_is_alive_true_when_running(self) -> None:
        proc = _make_proc(running=True)
        with _patch_spawn(proc), _patch_which():
            async with ProcessSupervisor(_COMMAND) as supervisor:
                assert supervisor.is_alive is True

    @pytest.mark.asyncio(loop_scope="function")
    async def test_is_alive_false_when_exited(self) -> None:
        proc = _make_proc(running=False)
        with _patch_spawn(proc), _patch_which():
            async with ProcessSupervisor(_COMMAND) as supervisor:
                assert supervisor.is_alive is False


# ---------------------------------------------------------------------------
# ensure_running — return pipes and respawn on crash
# ---------------------------------------------------------------------------


class TestFromAC_EnsureRunning:  # noqa: N801
    """ensure_running() returns (stdin, stdout) and respawns dead processes."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_returns_stdin_stdout_tuple_when_alive(self) -> None:
        proc = _make_proc(running=True)
        with _patch_spawn(proc), _patch_which():
            async with ProcessSupervisor(_COMMAND) as supervisor:
                result = await supervisor.ensure_running()
                assert isinstance(result, tuple)
                assert len(result) == 2  # noqa: PLR2004

    @pytest.mark.asyncio(loop_scope="function")
    async def test_returns_correct_stdin_and_stdout_objects(self) -> None:
        proc = _make_proc(running=True)
        with _patch_spawn(proc), _patch_which():
            async with ProcessSupervisor(_COMMAND) as supervisor:
                stdin, stdout = await supervisor.ensure_running()
                assert stdin is proc.stdin
                assert stdout is proc.stdout

    @pytest.mark.asyncio(loop_scope="function")
    async def test_respawns_dead_process_when_called(self) -> None:
        dead = _make_proc(running=False)
        new = _make_proc(running=True)
        spawn_mock = AsyncMock(side_effect=[dead, new])
        with patch(f"{_MODULE}.asyncio.create_subprocess_exec", new=spawn_mock), _patch_which():
            async with ProcessSupervisor(_COMMAND) as supervisor:
                await supervisor.ensure_running()
                assert spawn_mock.call_count == 2  # noqa: PLR2004 — initial + 1 respawn

    @pytest.mark.asyncio(loop_scope="function")
    async def test_returns_new_pipes_after_respawn(self) -> None:
        dead = _make_proc(running=False)
        new = _make_proc(running=True)
        spawn_mock = AsyncMock(side_effect=[dead, new])
        with patch(f"{_MODULE}.asyncio.create_subprocess_exec", new=spawn_mock), _patch_which():
            async with ProcessSupervisor(_COMMAND) as supervisor:
                stdin, stdout = await supervisor.ensure_running()
                assert stdin is new.stdin
                assert stdout is new.stdout


# ---------------------------------------------------------------------------
# Restart budget and mark_healthy
# ---------------------------------------------------------------------------


class TestFromAC_RestartBudget:  # noqa: N801
    """ensure_running raises after max_restarts; mark_healthy resets the counter."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_raises_budget_exhausted_after_max_restarts(self) -> None:
        """ensure_running raises ProcessRestartBudgetExhausted once budget is exhausted."""
        dead_procs = [_make_proc(running=False)] * 20
        spawn_mock = AsyncMock(side_effect=dead_procs)
        with patch(f"{_MODULE}.asyncio.create_subprocess_exec", new=spawn_mock), _patch_which():
            async with ProcessSupervisor(_COMMAND, max_restarts=3) as supervisor:
                with pytest.raises(ProcessRestartBudgetExhausted):
                    await _exhaust_budget(supervisor)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_mark_healthy_resets_restart_counter(self) -> None:
        """After mark_healthy(), restarts are allowed again."""
        # Enough dead procs to exhaust budget (initial + 3 restarts = 4 dead,
        # then one more spawn after mark_healthy which succeeds)
        dead_initial = [_make_proc(running=False)] * 20
        alive_after_reset = _make_proc(running=True)
        spawn_mock = AsyncMock(side_effect=[*dead_initial, alive_after_reset])
        with patch(f"{_MODULE}.asyncio.create_subprocess_exec", new=spawn_mock), _patch_which():
            async with ProcessSupervisor(_COMMAND, max_restarts=3) as supervisor:
                # Exhaust the budget
                with pytest.raises(ProcessRestartBudgetExhausted):
                    await _exhaust_budget(supervisor)
                # Reset via mark_healthy
                supervisor.mark_healthy()
                # Should not raise — budget is reset
                await supervisor.ensure_running()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_counter_reset_allows_full_budget_after_mark_healthy(self) -> None:
        """mark_healthy() resets to 0, granting a full new restart budget."""
        # Exhaust with max_restarts=1: initial (dead) + 1 restart (dead) = 2 procs
        # After mark_healthy: 1 more restart allowed before it raises again
        dead = [_make_proc(running=False)] * 10
        spawn_mock = AsyncMock(side_effect=dead)
        with patch(f"{_MODULE}.asyncio.create_subprocess_exec", new=spawn_mock), _patch_which():
            async with ProcessSupervisor(_COMMAND, max_restarts=1) as supervisor:
                # First exhaust (1 restart budget)
                with pytest.raises(ProcessRestartBudgetExhausted):
                    await _exhaust_budget(supervisor, n=10)
                # Reset
                supervisor.mark_healthy()
                # Second exhaust (another 1-restart budget) — should also exhaust
                with pytest.raises(ProcessRestartBudgetExhausted):
                    await _exhaust_budget(supervisor, n=10)


# ---------------------------------------------------------------------------
# shutdown_timeout constructor parameter  (AC #58 gap — not in task #73 scope)
# ---------------------------------------------------------------------------


class TestFromAC_ShutdownTimeout:  # noqa: N801
    """__init__ exposes shutdown_timeout: float = 5.0 used by shutdown()."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_accepts_shutdown_timeout_parameter(self) -> None:
        """Constructor must accept a shutdown_timeout keyword argument."""
        proc = _make_proc()
        with _patch_spawn(proc), _patch_which():
            async with ProcessSupervisor(_COMMAND, shutdown_timeout=2.0):
                pass  # must not raise TypeError

    @pytest.mark.asyncio(loop_scope="function")
    async def test_shutdown_uses_configured_timeout(self) -> None:
        """shutdown() passes shutdown_timeout to asyncio.wait_for, not a hardcoded value."""
        proc = _make_proc()
        wait_mock = AsyncMock(return_value=0)
        with (
            _patch_spawn(proc),
            _patch_which(),
            patch(f"{_MODULE}.asyncio.wait_for", new=wait_mock),
        ):
            supervisor = ProcessSupervisor(_COMMAND, shutdown_timeout=2.0)
            await supervisor.__aenter__()
            await supervisor.shutdown()
        _, kwargs = wait_mock.call_args
        assert kwargs.get("timeout") == 2.0  # noqa: PLR2004


# ---------------------------------------------------------------------------
# ProcessRestartBudgetExhausted base class  (AC #58 gap — not in task #73 scope)
# ---------------------------------------------------------------------------


class TestFromAC_ExceptionBase:  # noqa: N801
    """ProcessRestartBudgetExhausted must inherit from OwlBearError."""

    def test_restart_budget_exhausted_inherits_owlbear_error(self) -> None:
        """ProcessRestartBudgetExhausted(OwlBearError) — part of OwlBear error taxonomy."""
        from owlbear.errors import OwlBearError  # noqa: PLC0415

        assert issubclass(ProcessRestartBudgetExhausted, OwlBearError)
