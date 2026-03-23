"""Tests for daemon.py coverage gaps — task #663.

Targets uncovered lines identified in review:
- reconcile_tasks: retries exhausted w/ kanban_edit failure
- reconcile_tasks: lint gate failure path
- reconcile_tasks: success path (wip clear, move to review, hooks)
- reconcile_tasks: failure side-effects (wip save, hooks, retry scheduling)
- detect_stale_tasks: stale task cancellation and kanban/channel alerts
- poll_tick: retry re-dispatch loop (step 3)
- poll_tick: dispatch new tasks (step 7) with WIP & priority sort
- poll_loop: exception recovery
- run_daemon: inflight task cancellation in autonomous finally block
- channel_loop: sentinel detection, empty message, error recovery
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from conftest import MockChannel  # type: ignore[import-untyped]

from owlbear.core.delegation import DispatchContext
from owlbear.core.deps import OwlBearDeps
from owlbear.core.hooks import HookEvent
from owlbear.core.lint_gate import LintGateResult
from owlbear.daemon import (
    CONTINUE_FORWARD_PREFIX,
    OrchestratorState,
    RetryEntry,
    RunningTask,
    _apply_hydration,
    channel_loop,
    detect_stale_tasks,
    poll_loop,
    poll_tick,
    reconcile_tasks,
    run_daemon,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_done_task(*, exception: BaseException | None = None, result: object = None) -> MagicMock:
    """Create a mock asyncio.Task that reports done with optional exception."""
    t = MagicMock(spec=asyncio.Task)
    t.done.return_value = True
    t.exception.return_value = exception
    t.result.return_value = result
    return t


def _make_kanban_show_json(
    task_id: str,
    title: str = "Test task",
    body: str = "AC line 1",
) -> str:
    """Build fake kanban-md show output."""
    return json.dumps({"id": task_id, "title": title, "status": "todo", "body": body})


# ---------------------------------------------------------------------------
# reconcile_tasks: retries exhausted + kanban_edit failure path
# ---------------------------------------------------------------------------


class TestFromAC_ReconcileRetryExhaustedKanbanFailure:
    """When task retries are exhausted and kanban_edit raises, the state must
    still be cleaned up (removed from retries and claimed)."""

    @pytest.mark.asyncio
    async def test_kanban_edit_failure_still_cleans_state(self) -> None:
        """kanban_edit raises → task still removed from retries & claimed."""
        state = OrchestratorState()
        mock_kanban = AsyncMock()

        exc = RuntimeError("agent boom")
        state.running["X1"] = RunningTask(task_id="X1", asyncio_task=_make_done_task(exception=exc))
        state.claimed.add("X1")
        # Already at max attempts — next attempt (5+1=6) exceeds default 5
        state.retries["X1"] = RetryEntry(
            task_id="X1",
            attempt=5,
            next_due=datetime.now(UTC),
            last_error="previous failure",
        )

        # kanban_edit raises
        mock_kanban.kanban_edit = AsyncMock(side_effect=OSError("kanban broken"))

        async def go() -> None:
            await reconcile_tasks(state=state, kanban=mock_kanban, max_retry_attempts=5)

        await (go())

        assert "X1" not in state.running
        assert "X1" not in state.retries
        assert "X1" not in state.claimed

    @pytest.mark.asyncio
    async def test_kanban_edit_failure_logs_warning(self) -> None:
        """When kanban_edit fails on exhausted retry, warning is logged."""
        state = OrchestratorState()
        mock_kanban = AsyncMock()

        exc = RuntimeError("agent boom")
        state.running["X2"] = RunningTask(task_id="X2", asyncio_task=_make_done_task(exception=exc))
        state.claimed.add("X2")
        state.retries["X2"] = RetryEntry(
            task_id="X2",
            attempt=5,
            next_due=datetime.now(UTC),
            last_error="previous failure",
        )

        mock_kanban.kanban_edit = AsyncMock(side_effect=OSError("kanban broken"))

        with patch("owlbear.daemon.logger") as mock_logger:

            async def go() -> None:
                await reconcile_tasks(state=state, kanban=mock_kanban, max_retry_attempts=5)

            await (go())

        warn_calls = mock_logger.warning.call_args_list
        assert any("Failed to block exhausted task" in str(c) for c in warn_calls)

    @pytest.mark.asyncio
    async def test_retries_exhausted_blocks_task_with_reason(self) -> None:
        """When retries exhausted and kanban_edit succeeds, task is blocked
        with a reason string mentioning retry exhaustion."""
        state = OrchestratorState()
        mock_kanban = AsyncMock()

        exc = RuntimeError("agent boom")
        state.running["X3"] = RunningTask(task_id="X3", asyncio_task=_make_done_task(exception=exc))
        state.claimed.add("X3")
        state.retries["X3"] = RetryEntry(
            task_id="X3",
            attempt=5,
            next_due=datetime.now(UTC),
            last_error="previous failure",
        )

        async def go() -> None:
            await reconcile_tasks(state=state, kanban=mock_kanban, max_retry_attempts=5)

        await (go())

        mock_kanban.kanban_edit.assert_called_once()
        call_kwargs = mock_kanban.kanban_edit.call_args
        block_reason = call_kwargs.kwargs.get("block") or str(call_kwargs)
        assert "retry" in block_reason.lower() or "exhaust" in block_reason.lower()
        assert "X3" not in state.claimed

    @pytest.mark.asyncio
    async def test_retries_exhausted_boundary_at_max(self) -> None:
        """Exactly at max attempts: attempt=2, max_retry_attempts=2 → next
        attempt is 3 > 2, so retries are exhausted."""
        state = OrchestratorState()
        mock_kanban = AsyncMock()

        exc = RuntimeError("fail again")
        state.running["X4"] = RunningTask(task_id="X4", asyncio_task=_make_done_task(exception=exc))
        state.claimed.add("X4")
        state.retries["X4"] = RetryEntry(
            task_id="X4",
            attempt=2,
            next_due=datetime.now(UTC),
            last_error="fail",
        )

        async def go() -> None:
            await reconcile_tasks(state=state, kanban=mock_kanban, max_retry_attempts=2)

        await (go())

        # Exhausted → kanban_edit called to block
        mock_kanban.kanban_edit.assert_called_once()
        assert "X4" not in state.claimed


# ---------------------------------------------------------------------------
# poll_tick: retry re-dispatch (step 3)
# ---------------------------------------------------------------------------


class TestFromAC_PollTickRetryRedispatch:
    """Due retries in poll_tick step 3 are popped from state.retries,
    task details re-fetched, prompt built, and a new asyncio.Task spawned."""

    @pytest.mark.asyncio
    async def test_due_retry_dispatched(self) -> None:
        """A due RetryEntry is consumed and a new task is spawned."""
        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_registry = MagicMock()

        state.retries["R1"] = RetryEntry(
            task_id="R1",
            attempt=2,
            next_due=datetime.now(UTC) - timedelta(seconds=10),
            last_error="previous failure",
        )
        state.claimed.add("R1")

        mock_kanban.kanban_show.return_value = _make_kanban_show_json("R1")
        mock_kanban.kanban_list.return_value = json.dumps([])

        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(return_value=MagicMock())
        mock_registry.get.return_value = mock_agent

        async def go() -> None:
            await poll_tick(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                max_concurrent=3,
                shutdown_event=asyncio.Event(),
            )

        await (go())

        # Retry entry consumed
        assert "R1" not in state.retries
        # New running task spawned
        assert "R1" in state.running

    @pytest.mark.asyncio
    async def test_due_retry_loads_wip_context(self) -> None:
        """WIP summary is prepended with CONTINUE_FORWARD_PREFIX for retried tasks."""
        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_registry = MagicMock()
        mock_wip = MagicMock()

        state.retries["R2"] = RetryEntry(
            task_id="R2",
            attempt=1,
            next_due=datetime.now(UTC) - timedelta(seconds=10),
            last_error="earlier failure",
        )
        state.claimed.add("R2")

        mock_kanban.kanban_show.return_value = _make_kanban_show_json("R2")
        mock_kanban.kanban_list.return_value = json.dumps([])

        mock_wip.load.return_value = "Previous work summary"

        captured_prompts: list[str] = []

        async def fake_run(prompt: str) -> MagicMock:
            captured_prompts.append(prompt)
            return MagicMock()

        mock_agent = MagicMock()
        mock_agent.run = fake_run
        mock_registry.get.return_value = mock_agent

        async def go() -> None:
            await poll_tick(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                max_concurrent=3,
                shutdown_event=asyncio.Event(),
                wip_store=mock_wip,
            )

        await (go())
        await asyncio.sleep(0)  # drain tasks spawned by poll_tick

        assert len(captured_prompts) == 1
        assert CONTINUE_FORWARD_PREFIX in captured_prompts[0]
        assert "Previous work summary" in captured_prompts[0]

    @pytest.mark.asyncio
    async def test_due_retry_respects_max_concurrent(self) -> None:
        """When all slots are full, due retries are NOT dispatched."""
        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_registry = MagicMock()

        # Fill both slots with running tasks
        for tid in ("A1", "A2"):
            dummy = MagicMock(spec=asyncio.Task)
            dummy.done.return_value = False
            state.running[tid] = RunningTask(task_id=tid, asyncio_task=dummy)

        state.retries["R3"] = RetryEntry(
            task_id="R3",
            attempt=1,
            next_due=datetime.now(UTC) - timedelta(seconds=10),
            last_error="fail",
        )

        mock_kanban.kanban_list.return_value = json.dumps([])

        async def go() -> None:
            await poll_tick(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                max_concurrent=2,
                shutdown_event=asyncio.Event(),
            )

        await (go())

        # Retry NOT dispatched — still in retries
        assert "R3" in state.retries

    @pytest.mark.asyncio
    async def test_due_retry_with_shutdown_exits_cleanly(self) -> None:
        """When shutdown_event is already set, due retries are skipped."""
        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_registry = MagicMock()
        shutdown = asyncio.Event()
        shutdown.set()

        state.retries["R4"] = RetryEntry(
            task_id="R4",
            attempt=1,
            next_due=datetime.now(UTC) - timedelta(seconds=10),
            last_error="fail",
        )

        mock_kanban.kanban_list.return_value = json.dumps([])

        async def go() -> None:
            await poll_tick(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                max_concurrent=3,
                shutdown_event=shutdown,
            )

        await (go())

        # Retry NOT dispatched due to shutdown
        assert "R4" not in state.running

    @pytest.mark.asyncio
    async def test_not_yet_due_retry_stays_pending(self) -> None:
        """A RetryEntry with future next_due is NOT dispatched."""
        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_registry = MagicMock()

        state.retries["R5"] = RetryEntry(
            task_id="R5",
            attempt=1,
            next_due=datetime.now(UTC) + timedelta(hours=1),
            last_error="fail",
        )

        mock_kanban.kanban_list.return_value = json.dumps([])

        async def go() -> None:
            await poll_tick(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                max_concurrent=3,
                shutdown_event=asyncio.Event(),
            )

        await (go())

        # Still pending
        assert "R5" in state.retries
        assert "R5" not in state.running

    @pytest.mark.asyncio
    async def test_due_retry_uses_builder_agent(self) -> None:
        """Retry dispatch resolves 'builder' from the agent registry."""
        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_registry = MagicMock()

        state.retries["R6"] = RetryEntry(
            task_id="R6",
            attempt=1,
            next_due=datetime.now(UTC) - timedelta(seconds=1),
            last_error="fail",
        )
        state.claimed.add("R6")

        mock_kanban.kanban_show.return_value = _make_kanban_show_json("R6")
        mock_kanban.kanban_list.return_value = json.dumps([])

        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(return_value=MagicMock())
        mock_registry.get.return_value = mock_agent

        async def go() -> None:
            await poll_tick(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                max_concurrent=3,
                shutdown_event=asyncio.Event(),
            )

        await (go())

        mock_registry.get.assert_called_with("builder")


# ---------------------------------------------------------------------------
# run_daemon: inflight task cancellation in autonomous finally block
# ---------------------------------------------------------------------------


class TestFromAC_RunDaemonInflightCancellation:
    """When autonomous mode's TaskGroup exits, in-flight tasks spawned by
    poll_loop must be cancelled and awaited with a timeout."""

    @pytest.mark.asyncio
    async def test_inflight_tasks_cancelled_on_exit(self, tmp_path: Path) -> None:
        """Tasks in state.running are cancelled when run_daemon's TaskGroup exits."""
        inflight_task: asyncio.Task[None] | None = None

        async def fake_poll_loop(**kwargs: object) -> None:
            nonlocal inflight_task
            state: OrchestratorState = kwargs["state"]  # type: ignore[assignment]
            shutdown: asyncio.Event = kwargs["shutdown_event"]  # type: ignore[assignment]
            # Simulate a dispatched task still running
            inflight_task = asyncio.create_task(asyncio.sleep(1000), name="inflight-test")
            state.running["test-inflight"] = RunningTask(
                task_id="test-inflight", asyncio_task=inflight_task
            )
            # Signal shutdown so both coroutines exit
            shutdown.set()

        async def fake_channel_loop(
            shutdown_event: asyncio.Event,
            *_args: object,
            **_kwargs: object,
        ) -> None:
            await shutdown_event.wait()

        channel = MockChannel([None])
        mock_agent = AsyncMock()
        mock_agent.hooks = AsyncMock()
        mock_agent.session = MagicMock()
        mock_agent.session.path = Path("/fake/session")
        mock_agent.session.load.return_value = []

        settings = MagicMock()
        settings.autonomous_mode = True
        settings.heartbeat_enabled = False
        settings.lint_gate_enabled = False

        with (
            patch("owlbear.daemon.poll_loop", side_effect=fake_poll_loop),
            patch("owlbear.daemon.channel_loop", side_effect=fake_channel_loop),
            patch("owlbear.memory.wip.WipStore", return_value=MagicMock()),
        ):

            async def go() -> None:
                await run_daemon(
                    channel=channel,
                    agent=mock_agent,
                    config_dir=tmp_path,
                    settings=settings,
                    kanban_toolset=AsyncMock(),
                    agent_registry=MagicMock(),
                )

            await (go())

        assert inflight_task is not None
        assert inflight_task.cancelled()

    @pytest.mark.asyncio
    async def test_no_inflight_tasks_exits_cleanly(self, tmp_path: Path) -> None:
        """When no in-flight tasks exist at exit, the finally block is a no-op."""

        async def fake_poll_loop(**kwargs: object) -> None:
            shutdown: asyncio.Event = kwargs["shutdown_event"]  # type: ignore[assignment]
            shutdown.set()

        async def fake_channel_loop(
            shutdown_event: asyncio.Event,
            *_args: object,
            **_kwargs: object,
        ) -> None:
            await shutdown_event.wait()

        channel = MockChannel([None])
        mock_agent = AsyncMock()
        mock_agent.hooks = AsyncMock()
        mock_agent.session = MagicMock()
        mock_agent.session.path = Path("/fake/session")
        mock_agent.session.load.return_value = []

        settings = MagicMock()
        settings.autonomous_mode = True
        settings.heartbeat_enabled = False
        settings.lint_gate_enabled = False

        with (
            patch("owlbear.daemon.poll_loop", side_effect=fake_poll_loop),
            patch("owlbear.daemon.channel_loop", side_effect=fake_channel_loop),
            patch("owlbear.memory.wip.WipStore", return_value=MagicMock()),
        ):

            async def go() -> None:
                await run_daemon(
                    channel=channel,
                    agent=mock_agent,
                    config_dir=tmp_path,
                    settings=settings,
                    kanban_toolset=AsyncMock(),
                    agent_registry=MagicMock(),
                )

            # Should not raise
            await (go())


# ---------------------------------------------------------------------------
# reconcile_tasks: lint gate failure path (lines 516-519)
# ---------------------------------------------------------------------------


class TestFromAC_ReconcileLintGate:
    """When a task completes successfully but the lint gate detects errors,
    the task should be treated as failed with a LintGateError."""

    @pytest.mark.asyncio
    async def test_lint_gate_failure_converts_to_error(self) -> None:
        """Successful task + failed lint gate → treated as failure (retried or blocked)."""
        state = OrchestratorState()
        mock_kanban = AsyncMock()

        state.running["LG1"] = RunningTask(
            task_id="LG1",
            asyncio_task=_make_done_task(result="ok"),
        )
        state.claimed.add("LG1")
        lint_result = LintGateResult(
            passed=False,
            errors="E501 line too long",
            files_checked=["a.py"],
        )

        with patch("owlbear.daemon.run_lint_gate", return_value=lint_result):

            async def go() -> None:
                await reconcile_tasks(
                    state=state,
                    kanban=mock_kanban,
                    lint_gate_enabled=True,
                    workspace=Path("/fake"),
                )

            await (go())

        # Task should NOT be moved to review — it failed lint
        mock_kanban.kanban_move.assert_not_called()
        # Should be in retry scheduling (attempt 1)
        assert "LG1" in state.retries
        assert state.retries["LG1"].attempt == 1

    @pytest.mark.asyncio
    async def test_lint_gate_skipped_when_disabled(self) -> None:
        """When lint_gate_enabled=False, lint gate is not run even if workspace is set."""
        state = OrchestratorState()
        mock_kanban = AsyncMock()

        state.running["LG2"] = RunningTask(
            task_id="LG2",
            asyncio_task=_make_done_task(result="ok"),
        )
        state.claimed.add("LG2")

        with patch("owlbear.daemon.run_lint_gate") as mock_lint:

            async def go() -> None:
                await reconcile_tasks(
                    state=state,
                    kanban=mock_kanban,
                    lint_gate_enabled=False,
                    workspace=Path("/fake"),
                )

            await (go())

        mock_lint.assert_not_called()
        # Task moved to review normally
        mock_kanban.kanban_move.assert_called_once_with("LG2", "review")

    @pytest.mark.asyncio
    async def test_lint_gate_skipped_when_no_workspace(self) -> None:
        """When workspace is None, lint gate is not run even if enabled."""
        state = OrchestratorState()
        mock_kanban = AsyncMock()

        state.running["LG3"] = RunningTask(
            task_id="LG3",
            asyncio_task=_make_done_task(result="ok"),
        )
        state.claimed.add("LG3")

        with patch("owlbear.daemon.run_lint_gate") as mock_lint:

            async def go() -> None:
                await reconcile_tasks(
                    state=state,
                    kanban=mock_kanban,
                    lint_gate_enabled=True,
                    workspace=None,
                )

            await (go())

        mock_lint.assert_not_called()
        mock_kanban.kanban_move.assert_called_once_with("LG3", "review")


# ---------------------------------------------------------------------------
# reconcile_tasks: success path (lines 551-571)
# ---------------------------------------------------------------------------


class TestFromAC_ReconcileSuccessPath:
    """When a task completes successfully (no exception, lint passes),
    WIP is cleared, task is moved to review, hooks are emitted, and
    the task is removed from claimed."""

    @pytest.mark.asyncio
    async def test_success_clears_wip_and_moves_to_review(self) -> None:
        """Successful task → wip_store.clear called, kanban_move to review."""
        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_wip = MagicMock()

        state.running["S1"] = RunningTask(
            task_id="S1",
            asyncio_task=_make_done_task(result="done"),
        )
        state.claimed.add("S1")

        async def go() -> None:
            await reconcile_tasks(state=state, kanban=mock_kanban, wip_store=mock_wip)

        await (go())

        mock_wip.clear.assert_called_once_with(agent="builder", task_id="S1")
        mock_kanban.kanban_move.assert_called_once_with("S1", "review")
        assert "S1" not in state.claimed

    @pytest.mark.asyncio
    async def test_success_emits_hook(self) -> None:
        """Successful task → hooks.emit called with success outcome."""
        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_hooks = AsyncMock()

        state.running["S2"] = RunningTask(
            task_id="S2",
            asyncio_task=_make_done_task(result="done"),
        )
        state.claimed.add("S2")

        async def go() -> None:
            await reconcile_tasks(state=state, kanban=mock_kanban, hooks=mock_hooks)

        await (go())

        mock_hooks.emit.assert_called_once_with(
            HookEvent.TASK_COMPLETE,
            {"task_id": "S2", "outcome": "success"},
        )

    @pytest.mark.asyncio
    async def test_success_without_wip_store(self) -> None:
        """Successful task with no wip_store → no crash, still moves to review."""
        state = OrchestratorState()
        mock_kanban = AsyncMock()

        state.running["S3"] = RunningTask(
            task_id="S3",
            asyncio_task=_make_done_task(result="done"),
        )
        state.claimed.add("S3")

        async def go() -> None:
            await reconcile_tasks(state=state, kanban=mock_kanban)

        await (go())

        mock_kanban.kanban_move.assert_called_once_with("S3", "review")
        assert "S3" not in state.claimed


# ---------------------------------------------------------------------------
# reconcile_tasks: failure side-effects (lines 524-525, 531)
# ---------------------------------------------------------------------------


class TestFromAC_ReconcileFailureSideEffects:
    """When a task fails, WIP is saved, hooks emit failure, and retry
    is scheduled with exponential backoff."""

    @pytest.mark.asyncio
    async def test_failure_saves_wip_summary(self) -> None:
        """Failed task → wip_store.save called with truncated summary."""
        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_wip = MagicMock()

        exc = RuntimeError("agent boom")
        state.running["F1"] = RunningTask(
            task_id="F1",
            asyncio_task=_make_done_task(exception=exc),
        )
        state.claimed.add("F1")

        async def go() -> None:
            await reconcile_tasks(state=state, kanban=mock_kanban, wip_store=mock_wip)

        await (go())

        mock_wip.save.assert_called_once()
        call_kwargs = mock_wip.save.call_args.kwargs
        assert call_kwargs["agent"] == "builder"
        assert call_kwargs["task_id"] == "F1"
        assert "RuntimeError" in call_kwargs["summary"]

    @pytest.mark.asyncio
    async def test_failure_emits_hook_with_failure_outcome(self) -> None:
        """Failed task → hooks.emit called with failure outcome."""
        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_hooks = AsyncMock()

        exc = ValueError("bad input")
        state.running["F2"] = RunningTask(
            task_id="F2",
            asyncio_task=_make_done_task(exception=exc),
        )
        state.claimed.add("F2")

        async def go() -> None:
            await reconcile_tasks(state=state, kanban=mock_kanban, hooks=mock_hooks)

        await (go())

        mock_hooks.emit.assert_called_once_with(
            HookEvent.TASK_COMPLETE,
            {"task_id": "F2", "outcome": "failure"},
        )

    @pytest.mark.asyncio
    async def test_failure_schedules_retry_with_backoff(self) -> None:
        """First failure → retry scheduled with attempt=1 and future next_due."""
        state = OrchestratorState()
        mock_kanban = AsyncMock()

        exc = RuntimeError("transient")
        state.running["F3"] = RunningTask(
            task_id="F3",
            asyncio_task=_make_done_task(exception=exc),
        )
        state.claimed.add("F3")
        before = datetime.now(UTC)

        async def go() -> None:
            await reconcile_tasks(state=state, kanban=mock_kanban)

        await (go())

        assert "F3" in state.retries
        entry = state.retries["F3"]
        assert entry.attempt == 1
        assert entry.next_due > before
        assert "transient" in entry.last_error
        # First failure keeps task in claimed for retry
        assert "F3" in state.claimed

    @pytest.mark.asyncio
    async def test_failure_increments_retry_attempt(self) -> None:
        """Second failure → retry attempt incremented to 2."""
        state = OrchestratorState()
        mock_kanban = AsyncMock()

        exc = RuntimeError("again")
        state.running["F4"] = RunningTask(
            task_id="F4",
            asyncio_task=_make_done_task(exception=exc),
        )
        state.claimed.add("F4")
        state.retries["F4"] = RetryEntry(
            task_id="F4",
            attempt=1,
            next_due=datetime.now(UTC),
            last_error="first failure",
        )

        async def go() -> None:
            await reconcile_tasks(state=state, kanban=mock_kanban)

        await (go())

        assert state.retries["F4"].attempt == 2


# ---------------------------------------------------------------------------
# detect_stale_tasks (lines 588-609)
# ---------------------------------------------------------------------------


class TestFromAC_DetectStaleTasks:
    """Stale tasks (running longer than timeout) are cancelled, removed from
    state, blocked on kanban, and alerted via channel."""

    @pytest.mark.asyncio
    async def test_stale_task_cancelled_and_removed(self) -> None:
        """Task running longer than stale_timeout is cancelled and removed."""
        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_channel = AsyncMock()

        mock_task = MagicMock(spec=asyncio.Task)
        mock_task.done.return_value = False
        state.running["ST1"] = RunningTask(
            task_id="ST1",
            asyncio_task=mock_task,
            started_at=datetime.now(UTC) - timedelta(seconds=600),
        )
        state.claimed.add("ST1")

        async def go() -> None:
            await detect_stale_tasks(
                state=state,
                kanban=mock_kanban,
                channel=mock_channel,
                stale_timeout=300.0,
            )

        await (go())

        mock_task.cancel.assert_called_once()
        assert "ST1" not in state.running
        assert "ST1" not in state.claimed
        mock_kanban.kanban_edit.assert_called_once()
        mock_channel.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_stale_kanban_edit_failure_continues(self) -> None:
        """kanban_edit failure on stale task is logged but processing continues."""
        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_kanban.kanban_edit = AsyncMock(side_effect=OSError("kanban down"))
        mock_channel = AsyncMock()

        mock_task = MagicMock(spec=asyncio.Task)
        mock_task.done.return_value = False
        state.running["ST2"] = RunningTask(
            task_id="ST2",
            asyncio_task=mock_task,
            started_at=datetime.now(UTC) - timedelta(seconds=600),
        )
        state.claimed.add("ST2")

        async def go() -> None:
            await detect_stale_tasks(
                state=state,
                kanban=mock_kanban,
                channel=mock_channel,
                stale_timeout=300.0,
            )

        await (go())

        # Task still cancelled and removed despite kanban failure
        mock_task.cancel.assert_called_once()
        assert "ST2" not in state.running
        # Channel send still attempted
        mock_channel.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_stale_channel_send_failure_continues(self) -> None:
        """channel.send failure on stale alert is logged but does not raise."""
        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_channel = AsyncMock()
        mock_channel.send = AsyncMock(side_effect=OSError("channel broken"))

        mock_task = MagicMock(spec=asyncio.Task)
        mock_task.done.return_value = False
        state.running["ST3"] = RunningTask(
            task_id="ST3",
            asyncio_task=mock_task,
            started_at=datetime.now(UTC) - timedelta(seconds=600),
        )
        state.claimed.add("ST3")

        async def go() -> None:
            await detect_stale_tasks(
                state=state,
                kanban=mock_kanban,
                channel=mock_channel,
                stale_timeout=300.0,
            )

        # Should not raise
        await (go())

        mock_task.cancel.assert_called_once()
        assert "ST3" not in state.running

    @pytest.mark.asyncio
    async def test_non_stale_task_not_cancelled(self) -> None:
        """Task within stale_timeout is left running."""
        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_channel = AsyncMock()

        mock_task = MagicMock(spec=asyncio.Task)
        mock_task.done.return_value = False
        state.running["ST4"] = RunningTask(
            task_id="ST4",
            asyncio_task=mock_task,
            started_at=datetime.now(UTC) - timedelta(seconds=10),
        )

        async def go() -> None:
            await detect_stale_tasks(
                state=state,
                kanban=mock_kanban,
                channel=mock_channel,
                stale_timeout=300.0,
            )

        await (go())

        mock_task.cancel.assert_not_called()
        assert "ST4" in state.running


# ---------------------------------------------------------------------------
# poll_tick: dispatch new tasks step 7 (lines 724-755)
# ---------------------------------------------------------------------------


class TestFromAC_PollTickDispatchNewTasks:
    """Step 7 of poll_tick: fetch todo tasks, filter claimed, sort by
    priority, dispatch up to available slots with WIP context."""

    @pytest.mark.asyncio
    async def test_dispatch_moves_to_in_progress_and_spawns(self) -> None:
        """A todo task is moved to in-progress and an asyncio task spawned."""
        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_registry = MagicMock()

        todo_task = {"id": "T1", "title": "Build foo", "status": "todo", "priority": "important"}
        mock_kanban.kanban_list.return_value = json.dumps([todo_task])
        mock_kanban.kanban_show.return_value = _make_kanban_show_json("T1", "Build foo")

        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(return_value=MagicMock())
        mock_registry.get.return_value = mock_agent

        async def go() -> None:
            await poll_tick(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                max_concurrent=3,
                shutdown_event=asyncio.Event(),
            )

        await (go())

        mock_kanban.kanban_move.assert_called_with("T1", "in-progress")
        assert "T1" in state.claimed
        assert "T1" in state.running

    @pytest.mark.asyncio
    async def test_dispatch_with_wip_prepends_prefix(self) -> None:
        """When WIP exists for a todo task, prompt is prepended with CONTINUE_FORWARD_PREFIX."""
        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_registry = MagicMock()
        mock_wip = MagicMock()

        todo_task = {"id": "T2", "title": "Build bar", "status": "todo", "priority": "important"}
        mock_kanban.kanban_list.return_value = json.dumps([todo_task])
        mock_kanban.kanban_show.return_value = _make_kanban_show_json("T2", "Build bar")

        mock_wip.load.return_value = "Previous cycle notes"

        captured_prompts: list[str] = []

        async def fake_run(prompt: str) -> MagicMock:
            captured_prompts.append(prompt)
            return MagicMock()

        mock_agent = MagicMock()
        mock_agent.run = fake_run
        mock_registry.get.return_value = mock_agent

        async def go() -> None:
            await poll_tick(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                max_concurrent=3,
                shutdown_event=asyncio.Event(),
                wip_store=mock_wip,
            )

        await (go())
        await asyncio.sleep(0)  # drain tasks spawned by poll_tick

        assert len(captured_prompts) == 1
        assert CONTINUE_FORWARD_PREFIX in captured_prompts[0]
        assert "Previous cycle notes" in captured_prompts[0]

    @pytest.mark.asyncio
    async def test_dispatch_respects_priority_sort(self) -> None:
        """Critical tasks are dispatched before nice-to-have tasks."""
        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_registry = MagicMock()

        tasks = [
            {"id": "P1", "title": "Low", "status": "todo", "priority": "nice-to-have"},
            {"id": "P2", "title": "High", "status": "todo", "priority": "critical"},
        ]
        mock_kanban.kanban_list.return_value = json.dumps(tasks)

        dispatched_ids: list[str] = []

        def make_show(tid: str) -> str:
            return _make_kanban_show_json(tid, f"Task {tid}")

        async def fake_show(tid: str) -> str:
            dispatched_ids.append(tid)
            return make_show(tid)

        mock_kanban.kanban_show = fake_show

        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(return_value=MagicMock())
        mock_registry.get.return_value = mock_agent

        async def go() -> None:
            await poll_tick(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                max_concurrent=5,
                shutdown_event=asyncio.Event(),
            )

        await (go())

        # Critical (P2) dispatched before nice-to-have (P1)
        assert dispatched_ids[0] == "P2"
        assert dispatched_ids[1] == "P1"

    @pytest.mark.asyncio
    async def test_dispatch_filters_already_claimed(self) -> None:
        """Claimed tasks are skipped during dispatch."""
        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_registry = MagicMock()

        tasks = [
            {"id": "C1", "title": "Claimed", "status": "todo", "priority": "important"},
            {"id": "C2", "title": "Free", "status": "todo", "priority": "important"},
        ]
        mock_kanban.kanban_list.return_value = json.dumps(tasks)
        mock_kanban.kanban_show.return_value = _make_kanban_show_json("C2", "Free")
        state.claimed.add("C1")

        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(return_value=MagicMock())
        mock_registry.get.return_value = mock_agent

        async def go() -> None:
            await poll_tick(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                max_concurrent=5,
                shutdown_event=asyncio.Event(),
            )

        await (go())

        # Only C2 dispatched, C1 skipped
        assert "C2" in state.running
        assert "C1" not in state.running

    @pytest.mark.asyncio
    async def test_dispatch_limited_by_available_slots(self) -> None:
        """When max_concurrent slots are full, no new tasks dispatched."""
        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_registry = MagicMock()

        # Fill both slots
        for tid in ("FULL1", "FULL2"):
            dummy = MagicMock(spec=asyncio.Task)
            dummy.done.return_value = False
            state.running[tid] = RunningTask(task_id=tid, asyncio_task=dummy)

        tasks = [{"id": "NEW1", "title": "New", "status": "todo", "priority": "important"}]
        mock_kanban.kanban_list.return_value = json.dumps(tasks)

        async def go() -> None:
            await poll_tick(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                max_concurrent=2,
                shutdown_event=asyncio.Event(),
            )

        await (go())

        assert "NEW1" not in state.running


# ---------------------------------------------------------------------------
# poll_loop: exception recovery (lines 800-801)
# ---------------------------------------------------------------------------


class TestFromAC_PollLoopExceptionRecovery:
    """When poll_tick raises, poll_loop logs the exception and continues."""

    @pytest.mark.asyncio
    async def test_poll_tick_failure_logged_and_continues(self) -> None:
        """poll_tick raises → logged via logger.exception, loop continues."""
        call_count = 0

        async def failing_poll_tick(**kwargs: object) -> None:
            nonlocal call_count
            call_count += 1
            shutdown: asyncio.Event = kwargs["shutdown_event"]  # type: ignore[assignment]
            if call_count >= 2:
                shutdown.set()
                return
            msg = "poll_tick exploded"
            raise RuntimeError(msg)

        settings = MagicMock()
        settings.max_concurrent_tasks = 2
        settings.poll_interval = 0.01
        settings.stale_task_timeout = 300.0
        settings.task_retry_max_attempts = 5
        settings.task_retry_backoff_base = 10.0
        settings.task_retry_backoff_max = 320.0

        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_registry = MagicMock()
        shutdown = asyncio.Event()

        with patch("owlbear.daemon.poll_tick", side_effect=failing_poll_tick):

            async def go() -> None:
                await poll_loop(
                    state=state,
                    kanban=mock_kanban,
                    agent_registry=mock_registry,
                    settings=settings,
                    shutdown_event=shutdown,
                )

            await (go())

        assert call_count >= 2  # Loop continued after first failure


# ---------------------------------------------------------------------------
# channel_loop: sentinel detection, empty message, error recovery
# ---------------------------------------------------------------------------


class TestFromAC_ChannelLoopPaths:
    """Exercise channel_loop paths for sentinel detection, empty messages,
    and error recovery."""

    @pytest.mark.asyncio
    async def test_sentinel_file_triggers_shutdown(self, tmp_path: Path) -> None:
        """When sentinel file exists, channel_loop sets shutdown and exits."""
        sentinel = tmp_path / "owlbear.stop"
        sentinel.touch()

        shutdown = asyncio.Event()
        mock_agent = AsyncMock()

        async def go() -> None:
            await channel_loop(
                shutdown,
                sentinel,
                MockChannel(["hello"]),
                mock_agent,
            )

        await (go())

        assert shutdown.is_set()

    @pytest.mark.asyncio
    async def test_empty_message_skipped(self) -> None:
        """Empty/whitespace messages are skipped, loop continues."""
        channel = MockChannel(["", "   ", "real message", None])
        mock_agent = AsyncMock()
        mock_agent.turn = AsyncMock(return_value="response")

        shutdown = asyncio.Event()
        sentinel = Path("/nonexistent/sentinel")

        async def go() -> None:
            await channel_loop(shutdown, sentinel, channel, mock_agent)

        await (go())

        # Only the "real message" should have been processed
        mock_agent.turn.assert_called_once_with("real message")

    @pytest.mark.asyncio
    async def test_error_recovery_on_agent_turn_failure(self) -> None:
        """When agent.turn raises, _recover_from_error is called."""
        channel = MockChannel(["trigger error", None])
        mock_agent = AsyncMock()
        mock_agent.turn = AsyncMock(side_effect=RuntimeError("model failed"))

        shutdown = asyncio.Event()
        sentinel = Path("/nonexistent/sentinel")

        with patch("owlbear.daemon._recover_from_error", new_callable=AsyncMock) as mock_recover:

            async def go() -> None:
                await channel_loop(
                    shutdown,
                    sentinel,
                    channel,
                    mock_agent,
                )

            await (go())

        mock_recover.assert_called_once()
        call_args = mock_recover.call_args
        assert isinstance(call_args[0][0], RuntimeError)


# ---------------------------------------------------------------------------
# _apply_hydration: section building from hydrator result (lines 620-636)
# ---------------------------------------------------------------------------


class TestFromAC_ApplyHydration:
    """_apply_hydration appends URL/file sections from the hydrator result
    to the prompt string."""

    @pytest.mark.asyncio
    async def test_hydrator_none_returns_prompt_unchanged(self) -> None:
        """When hydrator is None, prompt is returned unchanged."""

        async def go() -> str:
            return await _apply_hydration(None, "original", "body")

        assert await (go()) == "original"

    @pytest.mark.asyncio
    async def test_empty_body_returns_prompt_unchanged(self) -> None:
        """When body is empty, prompt is returned unchanged."""
        hydrator = AsyncMock()

        async def go() -> str:
            return await _apply_hydration(hydrator, "original", "")

        assert await (go()) == "original"
        hydrator.assert_not_called()

    @pytest.mark.asyncio
    async def test_hydrator_with_urls_appends_sections(self) -> None:
        """Hydrator result with URLs → URL sections appended to prompt."""
        result = MagicMock()
        result.urls = {"https://example.com": "Page content"}
        result.files = {}

        async def hydrator(body: str) -> object:  # noqa: ARG001
            return result

        async def go() -> str:
            return await _apply_hydration(hydrator, "base prompt", "some body")

        output = await (go())
        assert "## Pre-hydrated Context" in output
        assert "### https://example.com" in output
        assert "Page content" in output

    @pytest.mark.asyncio
    async def test_hydrator_with_files_appends_sections(self) -> None:
        """Hydrator result with files → file sections appended to prompt."""
        result = MagicMock()
        result.urls = {}
        result.files = {"src/main.py": "def main(): pass"}

        async def hydrator(body: str) -> object:  # noqa: ARG001
            return result

        async def go() -> str:
            return await _apply_hydration(hydrator, "base prompt", "some body")

        output = await (go())
        assert "## Pre-hydrated Context" in output
        assert "### src/main.py" in output
        assert "def main(): pass" in output

    @pytest.mark.asyncio
    async def test_hydrator_with_urls_and_files(self) -> None:
        """Hydrator result with both URLs and files → all sections appended."""
        result = MagicMock()
        result.urls = {"https://docs.example.com": "API docs"}
        result.files = {"README.md": "# Project"}

        async def hydrator(body: str) -> object:  # noqa: ARG001
            return result

        async def go() -> str:
            return await _apply_hydration(hydrator, "prompt", "body text")

        output = await (go())
        assert "### https://docs.example.com" in output
        assert "### README.md" in output

    @pytest.mark.asyncio
    async def test_hydrator_failure_returns_prompt_unchanged(self) -> None:
        """When hydrator raises, prompt is returned unchanged."""

        async def failing_hydrator(body: str) -> object:  # noqa: ARG001
            msg = "hydrator failed"
            raise RuntimeError(msg)

        async def go() -> str:
            return await _apply_hydration(failing_hydrator, "original", "body")

        assert await (go()) == "original"

    @pytest.mark.asyncio
    async def test_hydrator_empty_result_no_sections(self) -> None:
        """When hydrator result has no urls/files, prompt unchanged."""
        result = MagicMock()
        result.urls = {}
        result.files = {}

        async def hydrator(body: str) -> object:  # noqa: ARG001
            return result

        async def go() -> str:
            return await _apply_hydration(hydrator, "original", "body")

        assert await (go()) == "original"


# ---------------------------------------------------------------------------
# poll_tick: stale detection with channel (line 678)
# ---------------------------------------------------------------------------


class TestFromAC_PollTickWithChannel:
    """When channel is passed to poll_tick, detect_stale_tasks is called."""

    @pytest.mark.asyncio
    async def test_poll_tick_calls_detect_stale_when_channel_provided(self) -> None:
        """poll_tick invokes detect_stale_tasks when channel is not None."""
        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_registry = MagicMock()
        mock_channel = AsyncMock()

        mock_kanban.kanban_list.return_value = json.dumps([])

        with patch(
            "owlbear.daemon.detect_stale_tasks",
            new_callable=AsyncMock,
        ) as mock_stale:

            async def go() -> None:
                await poll_tick(
                    state=state,
                    kanban=mock_kanban,
                    agent_registry=mock_registry,
                    max_concurrent=3,
                    shutdown_event=asyncio.Event(),
                    channel=mock_channel,
                )

            await (go())

        mock_stale.assert_called_once()

    @pytest.mark.asyncio
    async def test_poll_tick_skips_stale_when_no_channel(self) -> None:
        """poll_tick does NOT call detect_stale_tasks when channel is None."""
        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_registry = MagicMock()

        mock_kanban.kanban_list.return_value = json.dumps([])

        with patch(
            "owlbear.daemon.detect_stale_tasks",
            new_callable=AsyncMock,
        ) as mock_stale:

            async def go() -> None:
                await poll_tick(
                    state=state,
                    kanban=mock_kanban,
                    agent_registry=mock_registry,
                    max_concurrent=3,
                    shutdown_event=asyncio.Event(),
                    channel=None,
                )

            await (go())

        mock_stale.assert_not_called()


# ---------------------------------------------------------------------------
# poll_tick: shutdown during dispatch step 7 (line 736)
# ---------------------------------------------------------------------------


class TestFromAC_PollTickShutdownDuringDispatch:
    """When shutdown_event is set during step 7 dispatch, loop exits early."""

    @pytest.mark.asyncio
    async def test_shutdown_during_dispatch_exits(self) -> None:
        """shutdown mid-dispatch aborts further task processing."""
        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_registry = MagicMock()
        shutdown = asyncio.Event()

        tasks = [
            {"id": "SD1", "title": "First", "status": "todo", "priority": "important"},
            {"id": "SD2", "title": "Second", "status": "todo", "priority": "important"},
        ]
        mock_kanban.kanban_list.return_value = json.dumps(tasks)

        dispatch_count = 0

        async def fake_move(tid: str, status: str) -> None:  # noqa: ARG001
            nonlocal dispatch_count
            dispatch_count += 1
            if dispatch_count >= 1:
                shutdown.set()  # Set shutdown after first dispatch

        mock_kanban.kanban_move = fake_move
        mock_kanban.kanban_show.return_value = _make_kanban_show_json("SD1")

        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(return_value=MagicMock())
        mock_registry.get.return_value = mock_agent

        async def go() -> None:
            await poll_tick(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                max_concurrent=5,
                shutdown_event=shutdown,
            )

        await (go())

        # Second task should not be dispatched due to shutdown
        assert "SD2" not in state.running

    @pytest.mark.asyncio
    async def test_shutdown_after_kanban_list_exits(self) -> None:
        """shutdown_event set during kanban_list call → exits before dispatch."""
        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_registry = MagicMock()
        shutdown = asyncio.Event()

        async def list_and_shutdown(**kwargs: object) -> str:  # noqa: ARG001
            shutdown.set()
            return json.dumps([{"id": "X", "title": "T", "status": "todo"}])

        mock_kanban.kanban_list = list_and_shutdown

        async def go() -> None:
            await poll_tick(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                max_concurrent=5,
                shutdown_event=shutdown,
            )

        await (go())

        assert "X" not in state.running


# ---------------------------------------------------------------------------
# run_daemon: session.load returns coroutine (lines 984-985)
# ---------------------------------------------------------------------------


class TestFromAC_RunDaemonSessionLoadCoroutine:
    """When session.load() returns a coroutine (async store), run_daemon's
    finally block awaits it."""

    @pytest.mark.asyncio
    async def test_async_session_load_awaited(self, tmp_path: Path) -> None:
        """session.load returns coroutine → awaited correctly."""
        channel = MockChannel([None])
        mock_agent = AsyncMock()
        mock_agent.hooks = AsyncMock()

        async def async_load() -> list[str]:
            return ["msg1", "msg2"]

        mock_agent.session = MagicMock()
        mock_agent.session.path = Path("/fake/session")
        mock_agent.session.load = async_load

        settings = MagicMock()
        settings.autonomous_mode = False
        settings.heartbeat_enabled = False

        async def go() -> None:
            await run_daemon(
                channel=channel,
                agent=mock_agent,
                config_dir=tmp_path,
                settings=settings,
            )

        await (go())

        # SESSION_END emitted with the awaited messages
        emit_calls = mock_agent.hooks.emit.call_args_list
        session_end_calls = [c for c in emit_calls if c[0][0] == HookEvent.SESSION_END]
        assert len(session_end_calls) == 1
        payload = session_end_calls[0][0][1]
        assert payload["messages"] == ["msg1", "msg2"]


# ---------------------------------------------------------------------------
# poll_tick: retry branch (step 3) — dispatch context reuse
# ---------------------------------------------------------------------------


class TestFromAC_PollTickRetryDispatchContext:
    """builder.run() must receive instructions= and deps= (with DispatchContext)
    in the retry re-dispatch branch (poll_tick step 3).

    All tests fail today: poll_tick dispatches builder.run(prompt) with
    no instructions= or deps= kwargs.  (#961 makes them pass.)
    """

    @staticmethod
    def _setup() -> tuple[OrchestratorState, AsyncMock, MagicMock, AsyncMock]:
        """Configure state with one due retry entry and matching mocks."""
        state = OrchestratorState()
        mock_kanban: AsyncMock = AsyncMock()
        mock_registry = MagicMock()

        state.retries["RDC1"] = RetryEntry(
            task_id="RDC1",
            attempt=1,
            next_due=datetime.now(UTC) - timedelta(seconds=5),
            last_error="prior failure",
        )
        state.claimed.add("RDC1")

        mock_kanban.kanban_show.return_value = _make_kanban_show_json(
            "RDC1", "Retry title", "Retry task body text"
        )
        mock_kanban.kanban_list.return_value = json.dumps([])

        mock_agent: AsyncMock = AsyncMock()
        mock_agent.run = AsyncMock(return_value=MagicMock())
        mock_registry.get.return_value = mock_agent

        return state, mock_kanban, mock_registry, mock_agent

    @pytest.mark.asyncio
    async def test_builder_run_receives_instructions_kwarg(self, tmp_path: Path) -> None:
        """builder.run() receives instructions= kwarg in retry dispatch branch."""
        state, mock_kanban, mock_registry, mock_agent = self._setup()
        channel = MagicMock()
        channel.name = "test-channel"

        async def go() -> None:
            await poll_tick(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                max_concurrent=3,
                shutdown_event=asyncio.Event(),
                channel=channel,
                workspace=tmp_path,
            )

        await (go())
        await asyncio.sleep(0)

        call = mock_agent.run.call_args
        assert call is not None, "builder.run() was not called"
        assert "instructions" in call[1], (
            "builder.run() must receive instructions= kwarg produced by format_dispatch_context()"
        )

    @pytest.mark.asyncio
    async def test_builder_run_receives_deps_kwarg(self, tmp_path: Path) -> None:
        """builder.run() receives deps= (OwlBearDeps) kwarg in retry branch."""
        state, mock_kanban, mock_registry, mock_agent = self._setup()
        channel = MagicMock()
        channel.name = "test-channel"

        async def go() -> None:
            await poll_tick(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                max_concurrent=3,
                shutdown_event=asyncio.Event(),
                channel=channel,
                workspace=tmp_path,
            )

        await (go())
        await asyncio.sleep(0)

        call = mock_agent.run.call_args
        assert call is not None, "builder.run() was not called"
        assert "deps" in call[1], (
            "builder.run() must receive deps= kwarg containing OwlBearDeps"
        )

    @pytest.mark.asyncio
    async def test_deps_has_dispatch_context_populated(self, tmp_path: Path) -> None:
        """deps.dispatch_context is a DispatchContext instance in retry branch."""
        state, mock_kanban, mock_registry, mock_agent = self._setup()
        channel = MagicMock()
        channel.name = "test-channel"

        async def go() -> None:
            await poll_tick(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                max_concurrent=3,
                shutdown_event=asyncio.Event(),
                channel=channel,
                workspace=tmp_path,
            )

        await (go())
        await asyncio.sleep(0)

        call = mock_agent.run.call_args
        assert call is not None
        assert "deps" in call[1], "builder.run() must receive deps= kwarg"
        deps_obj = call[1]["deps"]
        assert isinstance(deps_obj, OwlBearDeps), f"deps must be OwlBearDeps, got {type(deps_obj)}"
        assert deps_obj.dispatch_context is not None, "dispatch_context must be populated"
        assert isinstance(deps_obj.dispatch_context, DispatchContext), (
            f"dispatch_context must be DispatchContext, got {type(deps_obj.dispatch_context)}"
        )

    @pytest.mark.asyncio
    async def test_dispatch_context_workspace_root_matches_param(self, tmp_path: Path) -> None:
        """dispatch_context.workspace_root equals str(workspace) in retry branch."""
        state, mock_kanban, mock_registry, mock_agent = self._setup()
        channel = MagicMock()
        channel.name = "test-channel"

        async def go() -> None:
            await poll_tick(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                max_concurrent=3,
                shutdown_event=asyncio.Event(),
                channel=channel,
                workspace=tmp_path,
            )

        await (go())
        await asyncio.sleep(0)

        call = mock_agent.run.call_args
        assert call is not None
        assert "deps" in call[1], "builder.run() must receive deps= kwarg"
        ctx = call[1]["deps"].dispatch_context
        assert ctx is not None, "dispatch_context must be populated"
        assert ctx.workspace_root == str(tmp_path), (
            f"workspace_root should be '{tmp_path!s}', got {ctx.workspace_root!r}"
        )

    @pytest.mark.asyncio
    async def test_dispatch_context_task_id_matches_retry_entry(self, tmp_path: Path) -> None:
        """dispatch_context.task_id equals the retry entry's task ID."""
        state, mock_kanban, mock_registry, mock_agent = self._setup()
        channel = MagicMock()
        channel.name = "test-channel"

        async def go() -> None:
            await poll_tick(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                max_concurrent=3,
                shutdown_event=asyncio.Event(),
                channel=channel,
                workspace=tmp_path,
            )

        await (go())
        await asyncio.sleep(0)

        call = mock_agent.run.call_args
        assert call is not None
        assert "deps" in call[1], "builder.run() must receive deps= kwarg"
        ctx = call[1]["deps"].dispatch_context
        assert ctx is not None, "dispatch_context must be populated"
        assert ctx.task_id == "RDC1", f"task_id must be 'RDC1', got {ctx.task_id!r}"

    @pytest.mark.asyncio
    async def test_task_body_stays_in_prompt_not_migrated_to_instructions(
        self, tmp_path: Path
    ) -> None:
        """Task body stays in positional prompt; it must not appear in instructions=."""
        state, mock_kanban, mock_registry, mock_agent = self._setup()
        channel = MagicMock()
        channel.name = "test-channel"

        async def go() -> None:
            await poll_tick(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                max_concurrent=3,
                shutdown_event=asyncio.Event(),
                channel=channel,
                workspace=tmp_path,
            )

        await (go())
        await asyncio.sleep(0)

        call = mock_agent.run.call_args
        assert call is not None
        prompt_arg = call[0][0]
        assert "Retry task body text" in prompt_arg, "task body must remain in positional prompt"
        assert "instructions" in call[1], (
            "instructions= must be present for the migration check to be meaningful"
        )
        assert "Retry task body text" not in call[1]["instructions"], (
            "task body must NOT migrate into instructions="
        )

    @pytest.mark.asyncio
    async def test_wip_summary_stays_in_prompt_alongside_instructions_kwarg(
        self, tmp_path: Path
    ) -> None:
        """WIP summary stays in positional prompt and instructions= is also present."""
        state = OrchestratorState()
        mock_kanban: AsyncMock = AsyncMock()
        mock_registry = MagicMock()
        mock_wip = MagicMock()

        state.retries["RDC3"] = RetryEntry(
            task_id="RDC3",
            attempt=1,
            next_due=datetime.now(UTC) - timedelta(seconds=5),
            last_error="prior error",
        )
        state.claimed.add("RDC3")

        mock_kanban.kanban_show.return_value = _make_kanban_show_json("RDC3", "WIP task", "Body")
        mock_kanban.kanban_list.return_value = json.dumps([])
        mock_wip.load.return_value = "Prior cycle WIP notes"

        mock_agent: AsyncMock = AsyncMock()
        mock_agent.run = AsyncMock(return_value=MagicMock())
        mock_registry.get.return_value = mock_agent

        channel = MagicMock()
        channel.name = "test-channel"

        async def go() -> None:
            await poll_tick(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                max_concurrent=3,
                shutdown_event=asyncio.Event(),
                channel=channel,
                workspace=tmp_path,
                wip_store=mock_wip,
            )

        await (go())
        await asyncio.sleep(0)

        call = mock_agent.run.call_args
        assert call is not None
        prompt_arg = call[0][0]
        assert CONTINUE_FORWARD_PREFIX in prompt_arg, "WIP prefix must remain in positional prompt"
        assert "Prior cycle WIP notes" in prompt_arg, "WIP text must remain in positional prompt"
        assert "instructions" in call[1], (
            "instructions= kwarg must also be present alongside WIP-bearing prompt"
        )


# ---------------------------------------------------------------------------
# poll_tick: fresh-dispatch branch (step 7) — dispatch context reuse
# ---------------------------------------------------------------------------


class TestFromAC_PollTickFreshDispatchContext:
    """builder.run() must receive instructions= and deps= (with DispatchContext)
    in the fresh-dispatch branch (poll_tick step 7).

    All tests fail today: poll_tick dispatches builder.run(prompt) with
    no instructions= or deps= kwargs.  (#961 makes them pass.)
    """

    @staticmethod
    def _make_todo_task(tid: str = "FDC1", title: str = "Fresh task") -> dict[str, str]:
        """Return a minimal todo-task dict for kanban_list responses."""
        return {"id": tid, "title": title, "status": "todo", "priority": "important"}

    @pytest.mark.asyncio
    async def test_builder_run_receives_instructions_kwarg(self, tmp_path: Path) -> None:
        """builder.run() receives instructions= kwarg in fresh-dispatch branch."""
        state = OrchestratorState()
        mock_kanban: AsyncMock = AsyncMock()
        mock_registry = MagicMock()
        channel = MagicMock()
        channel.name = "test-channel"

        mock_kanban.kanban_list.return_value = json.dumps([self._make_todo_task()])
        mock_kanban.kanban_show.return_value = _make_kanban_show_json(
            "FDC1", "Fresh task", "Fresh task body"
        )

        mock_agent: AsyncMock = AsyncMock()
        mock_agent.run = AsyncMock(return_value=MagicMock())
        mock_registry.get.return_value = mock_agent

        async def go() -> None:
            await poll_tick(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                max_concurrent=3,
                shutdown_event=asyncio.Event(),
                channel=channel,
                workspace=tmp_path,
            )

        await (go())
        await asyncio.sleep(0)

        call = mock_agent.run.call_args
        assert call is not None, "builder.run() was not called"
        assert "instructions" in call[1], (
            "builder.run() must receive instructions= kwarg from format_dispatch_context()"
        )

    @pytest.mark.asyncio
    async def test_builder_run_receives_deps_kwarg(self, tmp_path: Path) -> None:
        """builder.run() receives deps= (OwlBearDeps) kwarg in fresh-dispatch branch."""
        state = OrchestratorState()
        mock_kanban: AsyncMock = AsyncMock()
        mock_registry = MagicMock()
        channel = MagicMock()
        channel.name = "test-channel"

        mock_kanban.kanban_list.return_value = json.dumps([self._make_todo_task()])
        mock_kanban.kanban_show.return_value = _make_kanban_show_json(
            "FDC1", "Fresh task", "Fresh task body"
        )

        mock_agent: AsyncMock = AsyncMock()
        mock_agent.run = AsyncMock(return_value=MagicMock())
        mock_registry.get.return_value = mock_agent

        async def go() -> None:
            await poll_tick(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                max_concurrent=3,
                shutdown_event=asyncio.Event(),
                channel=channel,
                workspace=tmp_path,
            )

        await (go())
        await asyncio.sleep(0)

        call = mock_agent.run.call_args
        assert call is not None, "builder.run() was not called"
        assert "deps" in call[1], (
            "builder.run() must receive deps= kwarg containing OwlBearDeps"
        )

    @pytest.mark.asyncio
    async def test_deps_has_dispatch_context_populated(self, tmp_path: Path) -> None:
        """deps.dispatch_context is a DispatchContext instance in fresh-dispatch branch."""
        state = OrchestratorState()
        mock_kanban: AsyncMock = AsyncMock()
        mock_registry = MagicMock()
        channel = MagicMock()
        channel.name = "test-channel"

        mock_kanban.kanban_list.return_value = json.dumps([self._make_todo_task()])
        mock_kanban.kanban_show.return_value = _make_kanban_show_json(
            "FDC1", "Fresh task", "Fresh task body"
        )

        mock_agent: AsyncMock = AsyncMock()
        mock_agent.run = AsyncMock(return_value=MagicMock())
        mock_registry.get.return_value = mock_agent

        async def go() -> None:
            await poll_tick(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                max_concurrent=3,
                shutdown_event=asyncio.Event(),
                channel=channel,
                workspace=tmp_path,
            )

        await (go())
        await asyncio.sleep(0)

        call = mock_agent.run.call_args
        assert call is not None
        assert "deps" in call[1], "builder.run() must receive deps= kwarg"
        deps_obj = call[1]["deps"]
        assert isinstance(deps_obj, OwlBearDeps), f"deps must be OwlBearDeps, got {type(deps_obj)}"
        assert deps_obj.dispatch_context is not None, "dispatch_context must be populated"
        assert isinstance(deps_obj.dispatch_context, DispatchContext), (
            f"dispatch_context must be DispatchContext, got {type(deps_obj.dispatch_context)}"
        )

    @pytest.mark.asyncio
    async def test_dispatch_context_workspace_root_matches_param(self, tmp_path: Path) -> None:
        """dispatch_context.workspace_root equals str(workspace) in fresh-dispatch branch."""
        state = OrchestratorState()
        mock_kanban: AsyncMock = AsyncMock()
        mock_registry = MagicMock()
        channel = MagicMock()
        channel.name = "test-channel"

        mock_kanban.kanban_list.return_value = json.dumps([self._make_todo_task()])
        mock_kanban.kanban_show.return_value = _make_kanban_show_json(
            "FDC1", "Fresh task", "Fresh task body"
        )

        mock_agent: AsyncMock = AsyncMock()
        mock_agent.run = AsyncMock(return_value=MagicMock())
        mock_registry.get.return_value = mock_agent

        async def go() -> None:
            await poll_tick(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                max_concurrent=3,
                shutdown_event=asyncio.Event(),
                channel=channel,
                workspace=tmp_path,
            )

        await (go())
        await asyncio.sleep(0)

        call = mock_agent.run.call_args
        assert call is not None
        assert "deps" in call[1], "builder.run() must receive deps= kwarg"
        ctx = call[1]["deps"].dispatch_context
        assert ctx is not None, "dispatch_context must be populated"
        assert ctx.workspace_root == str(tmp_path), (
            f"workspace_root should be '{tmp_path!s}', got {ctx.workspace_root!r}"
        )

    @pytest.mark.asyncio
    async def test_dispatch_context_task_id_matches_dispatched_task(self, tmp_path: Path) -> None:
        """dispatch_context.task_id equals the dispatched todo task's ID."""
        state = OrchestratorState()
        mock_kanban: AsyncMock = AsyncMock()
        mock_registry = MagicMock()
        channel = MagicMock()
        channel.name = "test-channel"

        mock_kanban.kanban_list.return_value = json.dumps([self._make_todo_task("FDC2")])
        mock_kanban.kanban_show.return_value = _make_kanban_show_json("FDC2", "Task title", "Body")

        mock_agent: AsyncMock = AsyncMock()
        mock_agent.run = AsyncMock(return_value=MagicMock())
        mock_registry.get.return_value = mock_agent

        async def go() -> None:
            await poll_tick(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                max_concurrent=3,
                shutdown_event=asyncio.Event(),
                channel=channel,
                workspace=tmp_path,
            )

        await (go())
        await asyncio.sleep(0)

        call = mock_agent.run.call_args
        assert call is not None
        assert "deps" in call[1], "builder.run() must receive deps= kwarg"
        ctx = call[1]["deps"].dispatch_context
        assert ctx is not None, "dispatch_context must be populated"
        assert ctx.task_id == "FDC2", f"task_id must be 'FDC2', got {ctx.task_id!r}"

    @pytest.mark.asyncio
    async def test_task_body_stays_in_prompt_not_migrated_to_instructions(
        self, tmp_path: Path
    ) -> None:
        """Task body stays in positional prompt; it must not appear in instructions=."""
        state = OrchestratorState()
        mock_kanban: AsyncMock = AsyncMock()
        mock_registry = MagicMock()
        channel = MagicMock()
        channel.name = "test-channel"

        task_body = "Fresh dispatch task body content"
        mock_kanban.kanban_list.return_value = json.dumps([self._make_todo_task()])
        mock_kanban.kanban_show.return_value = _make_kanban_show_json(
            "FDC1", "Fresh task", task_body
        )

        mock_agent: AsyncMock = AsyncMock()
        mock_agent.run = AsyncMock(return_value=MagicMock())
        mock_registry.get.return_value = mock_agent

        async def go() -> None:
            await poll_tick(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                max_concurrent=3,
                shutdown_event=asyncio.Event(),
                channel=channel,
                workspace=tmp_path,
            )

        await (go())
        await asyncio.sleep(0)

        call = mock_agent.run.call_args
        assert call is not None
        prompt_arg = call[0][0]
        assert task_body in prompt_arg, "task body must remain in positional prompt"
        assert "instructions" in call[1], (
            "instructions= must be present for the migration check to be meaningful"
        )
        assert task_body not in call[1]["instructions"], (
            "task body must NOT migrate into instructions="
        )

    @pytest.mark.asyncio
    async def test_hydrated_content_stays_in_prompt_alongside_instructions_kwarg(
        self, tmp_path: Path
    ) -> None:
        """Pre-hydrated content stays in positional prompt; instructions= is also present."""
        state = OrchestratorState()
        mock_kanban: AsyncMock = AsyncMock()
        mock_registry = MagicMock()
        channel = MagicMock()
        channel.name = "test-channel"

        mock_kanban.kanban_list.return_value = json.dumps([self._make_todo_task()])
        mock_kanban.kanban_show.return_value = _make_kanban_show_json(
            "FDC1", "Fresh task", "Body with refs"
        )

        hydrated_result = MagicMock()
        hydrated_result.urls = {"https://example.com/page": "HydratedPageContent"}
        hydrated_result.files = {}

        async def fake_hydrator(body: str) -> object:  # noqa: ARG001
            return hydrated_result

        mock_agent: AsyncMock = AsyncMock()
        mock_agent.run = AsyncMock(return_value=MagicMock())
        mock_registry.get.return_value = mock_agent

        async def go() -> None:
            await poll_tick(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                max_concurrent=3,
                shutdown_event=asyncio.Event(),
                channel=channel,
                workspace=tmp_path,
                hydrator=fake_hydrator,
            )

        await (go())
        await asyncio.sleep(0)

        call = mock_agent.run.call_args
        assert call is not None
        prompt_arg = call[0][0]
        assert "HydratedPageContent" in prompt_arg, (
            "hydrated content must remain in positional prompt"
        )
        assert "instructions" in call[1], (
            "instructions= must be present for the migration check to be meaningful"
        )
        assert "HydratedPageContent" not in call[1]["instructions"], (
            "hydrated content must NOT migrate into instructions="
        )
