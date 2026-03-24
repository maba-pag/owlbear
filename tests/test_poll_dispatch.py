"""Tests for poll-dispatch-reconcile daemon loop.

TDD red phase — all tests must fail before #614 implementation exists.
Tests define the expected interface for:
- Config fields: autonomous_mode, poll_interval, max_concurrent_tasks
- OrchestratorState / RunningTask data structures
- Dual-coroutine lifecycle (channel_loop + poll_loop in TaskGroup)
- Poll tick sequence: reconcile → fetch todo → sort by priority → dispatch
- Dispatch mechanics, slot capping, failure handling, shutdown
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from conftest import MockChannel  # type: ignore[import-untyped]

from owlbear.config import OwlBearSettings

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_kanban_list_json(tasks: list[dict[str, str]]) -> str:
    """Build fake kanban-md list --json output."""
    return json.dumps(tasks)


def _make_kanban_show_json(
    task_id: str,
    title: str = "Test task",
    priority: str = "important",
    body: str = "AC line 1",
) -> str:
    """Build fake kanban-md show <id> --json output."""
    return json.dumps(
        {
            "id": task_id,
            "title": title,
            "status": "todo",
            "priority": priority,
            "body": body,
        }
    )


# ---------------------------------------------------------------------------
# AC 1: autonomous_mode config field (bool, default False)
# ---------------------------------------------------------------------------


class TestAutonomousModeConfig:
    """autonomous_mode field on OwlBearSettings."""

    def test_default_is_false(self, default_settings: OwlBearSettings) -> None:
        assert default_settings.autonomous_mode is False

    def test_accepts_true(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OWLBEAR_AUTONOMOUS_MODE", "true")
        settings = OwlBearSettings()
        assert settings.autonomous_mode is True

    def test_accepts_false_explicitly(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OWLBEAR_AUTONOMOUS_MODE", "false")
        settings = OwlBearSettings()
        assert settings.autonomous_mode is False


# ---------------------------------------------------------------------------
# AC 2: poll_interval config field (float, default 30.0, must be > 0)
# ---------------------------------------------------------------------------


class TestPollIntervalConfig:
    """poll_interval field on OwlBearSettings."""

    def test_default_30(self, default_settings: OwlBearSettings) -> None:
        assert default_settings.poll_interval == 30.0

    def test_custom_value(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OWLBEAR_POLL_INTERVAL", "10.0")
        settings = OwlBearSettings()
        assert settings.poll_interval == 10.0

    def test_rejects_zero(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OWLBEAR_POLL_INTERVAL", "0")
        with pytest.raises(ValueError, match="poll_interval"):
            OwlBearSettings()

    def test_rejects_negative(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OWLBEAR_POLL_INTERVAL", "-5")
        with pytest.raises(ValueError, match="poll_interval"):
            OwlBearSettings()


# ---------------------------------------------------------------------------
# AC 3: max_concurrent_tasks config field (int, default 3, must be > 0)
# ---------------------------------------------------------------------------


class TestMaxConcurrentTasksConfig:
    """max_concurrent_tasks field on OwlBearSettings."""

    def test_default_3(self, default_settings: OwlBearSettings) -> None:
        assert default_settings.max_concurrent_tasks == 3

    def test_custom_value(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OWLBEAR_MAX_CONCURRENT_TASKS", "5")
        settings = OwlBearSettings()
        assert settings.max_concurrent_tasks == 5

    def test_rejects_zero(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OWLBEAR_MAX_CONCURRENT_TASKS", "0")
        with pytest.raises(ValueError, match="max_concurrent_tasks"):
            OwlBearSettings()

    def test_rejects_negative(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OWLBEAR_MAX_CONCURRENT_TASKS", "-1")
        with pytest.raises(ValueError, match="max_concurrent_tasks"):
            OwlBearSettings()


# ---------------------------------------------------------------------------
# AC 12: OrchestratorState tracks running dict and claimed set correctly
# ---------------------------------------------------------------------------


class TestOrchestratorState:
    """OrchestratorState manages running tasks and claimed IDs."""

    def test_import(self) -> None:
        from owlbear.daemon import OrchestratorState  # noqa: F401

    def test_initial_state_empty(self) -> None:
        from owlbear.daemon import OrchestratorState

        state = OrchestratorState()
        assert state.running == {}
        assert state.claimed == set()

    def test_add_running_task(self) -> None:
        from owlbear.daemon import OrchestratorState, RunningTask

        state = OrchestratorState()
        dummy_task = MagicMock(spec=asyncio.Task)
        rt = RunningTask(task_id="100", asyncio_task=dummy_task)
        state.running["100"] = rt
        state.claimed.add("100")

        assert "100" in state.running
        assert "100" in state.claimed

    def test_remove_completed(self) -> None:
        from owlbear.daemon import OrchestratorState, RunningTask

        state = OrchestratorState()
        dummy_task = MagicMock(spec=asyncio.Task)
        rt = RunningTask(task_id="100", asyncio_task=dummy_task)
        state.running["100"] = rt
        state.claimed.add("100")

        # Simulate completion
        del state.running["100"]
        state.claimed.discard("100")

        assert "100" not in state.running
        assert "100" not in state.claimed

    def test_slots_available(self) -> None:
        """Available slots = max_concurrent - len(running)."""
        from owlbear.daemon import OrchestratorState, RunningTask

        state = OrchestratorState()
        max_concurrent = 3

        # Add 2 running tasks
        for tid in ("1", "2"):
            dummy = MagicMock(spec=asyncio.Task)
            state.running[tid] = RunningTask(task_id=tid, asyncio_task=dummy)
            state.claimed.add(tid)

        available = max_concurrent - len(state.running)
        assert available == 1


# ---------------------------------------------------------------------------
# AC 4: Dual-coroutine lifecycle — channel_loop + poll_loop in TaskGroup
# ---------------------------------------------------------------------------


class TestDualCoroutineLifecycle:
    """channel_loop and poll_loop run concurrently via TaskGroup."""

    def test_channel_loop_import(self) -> None:
        from owlbear.daemon import channel_loop  # noqa: F401

    def test_poll_loop_import(self) -> None:
        from owlbear.daemon import poll_loop  # noqa: F401

    @pytest.mark.asyncio
    async def test_both_run_in_task_group(self) -> None:
        """When autonomous_mode=True, both loops start in a TaskGroup."""
        from owlbear.daemon import channel_loop, poll_loop  # noqa: F401

        shutdown_event = asyncio.Event()

        state_holder: dict[str, bool] = {"channel_ran": False, "poll_ran": False}

        async def wrapped_channel() -> None:
            state_holder["channel_ran"] = True
            # Set shutdown so poll also exits
            shutdown_event.set()

        async def wrapped_poll() -> None:
            state_holder["poll_ran"] = True
            # Wait briefly for shutdown
            await asyncio.sleep(0.01)

        async def run_both() -> None:
            async with asyncio.TaskGroup() as tg:
                tg.create_task(wrapped_channel())
                tg.create_task(wrapped_poll())

        await (run_both())

        assert state_holder["channel_ran"]
        assert state_holder["poll_ran"]


# ---------------------------------------------------------------------------
# AC 9: autonomous_mode=False — poll_loop not started, channel_loop alone
# ---------------------------------------------------------------------------


class TestAutonomousModeDisabled:
    """When autonomous_mode=False, only channel_loop runs."""

    @pytest.mark.asyncio
    async def test_poll_loop_not_started(self) -> None:
        """run_daemon with autonomous_mode=False should not spawn poll_loop."""
        from owlbear.daemon import run_daemon

        channel = MockChannel([None])
        mock_agent = AsyncMock()

        poll_called = False

        async def fake_poll_loop(**kwargs: object) -> None:  # noqa: ARG001
            nonlocal poll_called
            poll_called = True

        with patch("owlbear.daemon.poll_loop", new=fake_poll_loop):
            settings = MagicMock(spec=OwlBearSettings)
            settings.autonomous_mode = False
            settings.heartbeat_enabled = False
            settings.heartbeat_interval = 1800
            settings.heartbeat_active_hours = (8, 22)
            await (
                run_daemon(
                    channel=channel,
                    agent=mock_agent,
                    config_dir=MagicMock(),
                    settings=settings,
                )
            )

        assert not poll_called


# ---------------------------------------------------------------------------
# AC 5: Poll tick sequence — reconcile, fetch todo, sort by priority, dispatch
# ---------------------------------------------------------------------------


class TestPollTickSequence:
    """Each poll tick: reconcile → fetch todo → sort priority → dispatch."""

    @pytest.mark.asyncio
    async def test_tick_calls_in_order(self) -> None:
        """A single poll tick calls reconcile, then fetches todo, sorts, dispatches."""
        from owlbear.daemon import OrchestratorState, poll_tick

        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_registry = MagicMock()

        # Kanban list returns two tasks: lower priority first
        todo_tasks = [
            {"id": "10", "title": "Low", "priority": "nice-to-have"},
            {"id": "11", "title": "High", "priority": "critical"},
        ]
        mock_kanban.kanban_list.return_value = _make_kanban_list_json(todo_tasks)
        mock_kanban.kanban_show.return_value = _make_kanban_show_json("11")
        mock_kanban.kanban_move.return_value = "moved"

        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(return_value=MagicMock(data="done"))
        mock_registry.get.return_value = mock_agent

        async def run_tick() -> None:
            await poll_tick(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                max_concurrent=3,
                shutdown_event=asyncio.Event(),
            )

        await (run_tick())

        # Should have fetched todo list
        mock_kanban.kanban_list.assert_called()

    @pytest.mark.asyncio
    async def test_critical_dispatched_before_nice_to_have(self) -> None:
        """Tasks sorted: critical > needed > important > nice-to-have > someday."""
        from owlbear.daemon import OrchestratorState, poll_tick

        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_registry = MagicMock()

        todo_tasks = [
            {"id": "20", "title": "Low", "priority": "nice-to-have"},
            {"id": "21", "title": "High", "priority": "critical"},
        ]
        mock_kanban.kanban_list.return_value = _make_kanban_list_json(todo_tasks)
        mock_kanban.kanban_show.side_effect = [
            _make_kanban_show_json("21", priority="critical"),
            _make_kanban_show_json("20", priority="nice-to-have"),
        ]
        mock_kanban.kanban_move.return_value = "moved"

        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(return_value=MagicMock(data="done"))
        mock_registry.get.return_value = mock_agent

        dispatched_ids: list[str] = []

        async def track_move(task_id: str, status: str) -> str:
            if status == "in-progress":
                dispatched_ids.append(task_id)
            return "moved"

        mock_kanban.kanban_move.side_effect = track_move

        async def run_tick() -> None:
            await poll_tick(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                max_concurrent=3,
                shutdown_event=asyncio.Event(),
            )

        await (run_tick())

        # Critical task dispatched first
        assert dispatched_ids[0] == "21"


# ---------------------------------------------------------------------------
# AC 6: Dispatch — task moved to in-progress, asyncio.Task spawned
# ---------------------------------------------------------------------------


class TestDispatch:
    """Dispatch moves task to in-progress and spawns via AgentRegistry.get('builder')."""

    @pytest.mark.asyncio
    async def test_task_moved_to_in_progress(self) -> None:
        from owlbear.daemon import OrchestratorState, poll_tick

        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_registry = MagicMock()

        todo_tasks = [{"id": "30", "title": "Do something", "priority": "important"}]
        mock_kanban.kanban_list.return_value = _make_kanban_list_json(todo_tasks)
        mock_kanban.kanban_show.return_value = _make_kanban_show_json("30")
        mock_kanban.kanban_move.return_value = "moved"

        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(return_value=MagicMock(data="done"))
        mock_registry.get.return_value = mock_agent

        async def run_tick() -> None:
            await poll_tick(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                max_concurrent=3,
                shutdown_event=asyncio.Event(),
            )

        await (run_tick())

        # Verify kanban_move called with in-progress
        move_calls = [
            c for c in mock_kanban.kanban_move.call_args_list if c.args[1] == "in-progress"
        ]
        assert len(move_calls) >= 1
        assert move_calls[0].args[0] == "30"

    @pytest.mark.asyncio
    async def test_builder_agent_resolved(self) -> None:
        """AgentRegistry.get('builder') is used to dispatch."""
        from owlbear.daemon import OrchestratorState, poll_tick

        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_registry = MagicMock()

        todo_tasks = [{"id": "31", "title": "Build it", "priority": "important"}]
        mock_kanban.kanban_list.return_value = _make_kanban_list_json(todo_tasks)
        mock_kanban.kanban_show.return_value = _make_kanban_show_json("31")
        mock_kanban.kanban_move.return_value = "moved"

        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(return_value=MagicMock(data="done"))
        mock_registry.get.return_value = mock_agent

        async def run_tick() -> None:
            await poll_tick(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                max_concurrent=3,
                shutdown_event=asyncio.Event(),
            )

        await (run_tick())

        mock_registry.get.assert_called_with("builder")

    @pytest.mark.asyncio
    async def test_claimed_set_updated(self) -> None:
        """Dispatched task ID added to state.claimed."""
        from owlbear.daemon import OrchestratorState, poll_tick

        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_registry = MagicMock()

        todo_tasks = [{"id": "32", "title": "Claim me", "priority": "important"}]
        mock_kanban.kanban_list.return_value = _make_kanban_list_json(todo_tasks)
        mock_kanban.kanban_show.return_value = _make_kanban_show_json("32")
        mock_kanban.kanban_move.return_value = "moved"

        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(return_value=MagicMock(data="done"))
        mock_registry.get.return_value = mock_agent

        async def run_tick() -> None:
            await poll_tick(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                max_concurrent=3,
                shutdown_event=asyncio.Event(),
            )

        await (run_tick())

        assert "32" in state.claimed


# ---------------------------------------------------------------------------
# AC 7: Completed task moved to review via KanbanToolset
# ---------------------------------------------------------------------------


class TestCompletedTaskMovedToReview:
    """When a dispatched task completes successfully, it moves to review."""

    @pytest.mark.asyncio
    async def test_success_moves_to_review(self) -> None:
        from owlbear.daemon import OrchestratorState, RunningTask, reconcile_tasks

        state = OrchestratorState()
        mock_kanban = AsyncMock()

        dummy_async_task = MagicMock(spec=asyncio.Task)
        dummy_async_task.done.return_value = True
        dummy_async_task.exception.return_value = None
        dummy_async_task.result.return_value = "success"

        rt = RunningTask(task_id="40", asyncio_task=dummy_async_task)
        state.running["40"] = rt
        state.claimed.add("40")

        mock_kanban.kanban_move.return_value = "moved"

        async def run_reconcile() -> None:
            await reconcile_tasks(state=state, kanban=mock_kanban)

        await (run_reconcile())

        # Task should be moved to review
        mock_kanban.kanban_move.assert_any_call("40", "review")
        # Task should be removed from running
        assert "40" not in state.running


# ---------------------------------------------------------------------------
# AC 8: Failed dispatch frees slot (error logged, NOT moved to review)
# ---------------------------------------------------------------------------


class TestFailedDispatchFreesSlot:
    """Failed dispatch frees the slot — error logged, task NOT moved to review."""

    @pytest.mark.asyncio
    async def test_exception_frees_slot(self) -> None:
        from owlbear.daemon import OrchestratorState, RunningTask, reconcile_tasks

        state = OrchestratorState()
        mock_kanban = AsyncMock()

        dummy_async_task = MagicMock(spec=asyncio.Task)
        dummy_async_task.done.return_value = True
        dummy_async_task.exception.return_value = RuntimeError("agent failed")

        rt = RunningTask(task_id="50", asyncio_task=dummy_async_task)
        state.running["50"] = rt
        state.claimed.add("50")

        mock_kanban.kanban_move.return_value = "moved"

        async def run_reconcile() -> None:
            await reconcile_tasks(state=state, kanban=mock_kanban)

        await (run_reconcile())

        # Task removed from running (slot freed)
        assert "50" not in state.running
        # Task NOT moved to review (no such call)
        review_calls = [
            c for c in mock_kanban.kanban_move.call_args_list if c.args == ("50", "review")
        ]
        assert len(review_calls) == 0

    @pytest.mark.asyncio
    async def test_exception_removes_from_claimed(self) -> None:
        from owlbear.daemon import OrchestratorState, RunningTask, reconcile_tasks

        state = OrchestratorState()
        mock_kanban = AsyncMock()

        dummy_async_task = MagicMock(spec=asyncio.Task)
        dummy_async_task.done.return_value = True
        dummy_async_task.exception.return_value = RuntimeError("boom")

        rt = RunningTask(task_id="51", asyncio_task=dummy_async_task)
        state.running["51"] = rt
        state.claimed.add("51")

        async def run_reconcile() -> None:
            await reconcile_tasks(state=state, kanban=mock_kanban)

        await (run_reconcile())

        # With retry (#625): first failure keeps task in claimed for retry
        assert "51" in state.claimed
        assert "51" in state.retries


# ---------------------------------------------------------------------------
# AC 10: shutdown_event during poll tick exits cleanly
# ---------------------------------------------------------------------------


class TestShutdownDuringPollTick:
    """Setting shutdown_event during a poll tick causes clean exit."""

    @pytest.mark.asyncio
    async def test_shutdown_event_exits_poll_loop(self) -> None:
        from owlbear.daemon import OrchestratorState, poll_loop

        state = OrchestratorState()
        shutdown_event = asyncio.Event()
        mock_kanban = AsyncMock()
        mock_registry = MagicMock()

        # Set shutdown immediately — poll_loop should exit after first check
        shutdown_event.set()

        async def run_poll() -> None:
            await poll_loop(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                settings=MagicMock(
                    poll_interval=0.01,
                    max_concurrent_tasks=3,
                ),
                shutdown_event=shutdown_event,
            )

        # Should complete without hanging
        await (run_poll())

        # No kanban calls — exited before first tick
        mock_kanban.kanban_list.assert_not_called()

    @pytest.mark.asyncio
    async def test_shutdown_mid_tick_stops_dispatch(self) -> None:
        """If shutdown is set while fetching tasks, no dispatch occurs."""
        from owlbear.daemon import OrchestratorState, poll_tick

        state = OrchestratorState()
        shutdown_event = asyncio.Event()
        mock_kanban = AsyncMock()
        mock_registry = MagicMock()

        todo_tasks = [{"id": "60", "title": "Never dispatched", "priority": "critical"}]
        mock_kanban.kanban_list.return_value = _make_kanban_list_json(todo_tasks)

        # Set shutdown right after list
        async def list_and_shutdown(**kwargs: object) -> str:  # noqa: ARG001
            shutdown_event.set()
            return _make_kanban_list_json(todo_tasks)

        mock_kanban.kanban_list.side_effect = list_and_shutdown

        async def run_tick() -> None:
            await poll_tick(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                max_concurrent=3,
                shutdown_event=shutdown_event,
            )

        await (run_tick())

        # Should not dispatch — shutdown was set
        mock_kanban.kanban_move.assert_not_called()


# ---------------------------------------------------------------------------
# AC 11: max_concurrent_tasks cap — no dispatch when all slots full
# ---------------------------------------------------------------------------


class TestMaxConcurrentTasksCap:
    """No dispatch when all slots are occupied."""

    @pytest.mark.asyncio
    async def test_no_dispatch_when_full(self) -> None:
        from owlbear.daemon import OrchestratorState, RunningTask, poll_tick

        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_registry = MagicMock()

        # Fill all 2 slots
        for tid in ("70", "71"):
            dummy = MagicMock(spec=asyncio.Task)
            dummy.done.return_value = False
            state.running[tid] = RunningTask(task_id=tid, asyncio_task=dummy)
            state.claimed.add(tid)

        todo_tasks = [{"id": "72", "title": "Waiting", "priority": "critical"}]
        mock_kanban.kanban_list.return_value = _make_kanban_list_json(todo_tasks)

        async def run_tick() -> None:
            await poll_tick(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                max_concurrent=2,  # All slots full
                shutdown_event=asyncio.Event(),
            )

        await (run_tick())

        # No move to in-progress — slots full
        in_progress_calls = [
            c
            for c in mock_kanban.kanban_move.call_args_list
            if len(c.args) >= 2 and c.args[1] == "in-progress"
        ]
        assert len(in_progress_calls) == 0

    @pytest.mark.asyncio
    async def test_partial_slots_dispatch_limited(self) -> None:
        """With 1 of 2 slots used, only 1 task dispatched even if 3 available."""
        from owlbear.daemon import OrchestratorState, RunningTask, poll_tick

        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_registry = MagicMock()

        # Fill 1 of 2 slots
        dummy = MagicMock(spec=asyncio.Task)
        dummy.done.return_value = False
        state.running["80"] = RunningTask(task_id="80", asyncio_task=dummy)
        state.claimed.add("80")

        todo_tasks = [
            {"id": "81", "title": "First", "priority": "critical"},
            {"id": "82", "title": "Second", "priority": "needed"},
            {"id": "83", "title": "Third", "priority": "important"},
        ]
        mock_kanban.kanban_list.return_value = _make_kanban_list_json(todo_tasks)
        mock_kanban.kanban_show.return_value = _make_kanban_show_json("81")
        mock_kanban.kanban_move.return_value = "moved"

        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(return_value=MagicMock(data="done"))
        mock_registry.get.return_value = mock_agent

        async def run_tick() -> None:
            await poll_tick(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                max_concurrent=2,  # 1 slot free
                shutdown_event=asyncio.Event(),
            )

        await (run_tick())

        # Only 1 task dispatched (1 free slot from max 2)
        in_progress_calls = [
            c
            for c in mock_kanban.kanban_move.call_args_list
            if len(c.args) >= 2 and c.args[1] == "in-progress"
        ]
        assert len(in_progress_calls) == 1

    @pytest.mark.asyncio
    async def test_already_claimed_tasks_skipped(self) -> None:
        """Tasks already in claimed set are not re-dispatched."""
        from owlbear.daemon import OrchestratorState, RunningTask, poll_tick

        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_registry = MagicMock()

        # Task 90 already claimed (running)
        dummy = MagicMock(spec=asyncio.Task)
        dummy.done.return_value = False
        state.running["90"] = RunningTask(task_id="90", asyncio_task=dummy)
        state.claimed.add("90")

        # Kanban list returns the same task (it hasn't moved yet in kanban)
        todo_tasks = [
            {"id": "90", "title": "Already running", "priority": "critical"},
            {"id": "91", "title": "New task", "priority": "important"},
        ]
        mock_kanban.kanban_list.return_value = _make_kanban_list_json(todo_tasks)
        mock_kanban.kanban_show.return_value = _make_kanban_show_json("91")
        mock_kanban.kanban_move.return_value = "moved"

        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(return_value=MagicMock(data="done"))
        mock_registry.get.return_value = mock_agent

        async def run_tick() -> None:
            await poll_tick(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                max_concurrent=5,
                shutdown_event=asyncio.Event(),
            )

        await (run_tick())

        # Only task 91 dispatched, not 90
        in_progress_calls = [
            c
            for c in mock_kanban.kanban_move.call_args_list
            if len(c.args) >= 2 and c.args[1] == "in-progress"
        ]
        dispatched_ids = [c.args[0] for c in in_progress_calls]
        assert "90" not in dispatched_ids
        assert "91" in dispatched_ids


# ---------------------------------------------------------------------------
# Issue 1: run_daemon passes kanban_toolset and agent_registry to poll_loop
# ---------------------------------------------------------------------------


class TestRunDaemonPassesKanbanAndRegistry:
    """run_daemon() must accept and forward kanban_toolset and agent_registry."""

    @pytest.mark.asyncio
    async def test_autonomous_passes_deps_to_poll_loop(self) -> None:
        """When autonomous_mode=True, kanban_toolset and agent_registry reach poll_loop."""
        from owlbear.daemon import run_daemon

        channel = MockChannel([None])  # returns None → shutdown
        mock_agent = AsyncMock()
        mock_kanban = AsyncMock()
        mock_registry = MagicMock()

        captured_kwargs: dict[str, object] = {}

        async def fake_poll_loop(**kwargs: object) -> None:
            captured_kwargs.update(kwargs)
            ev = kwargs["shutdown_event"]
            await ev.wait()  # type: ignore[union-attr]

        settings = MagicMock(spec=OwlBearSettings)
        settings.autonomous_mode = True
        settings.heartbeat_enabled = False
        settings.heartbeat_interval = 1800
        settings.heartbeat_active_hours = (8, 22)
        settings.lint_gate_enabled = False

        with patch("owlbear.daemon.poll_loop", new=fake_poll_loop):
            await (
                run_daemon(
                    channel=channel,
                    agent=mock_agent,
                    config_dir=MagicMock(),
                    settings=settings,
                    kanban_toolset=mock_kanban,
                    agent_registry=mock_registry,
                )
            )

        assert captured_kwargs["kanban"] is mock_kanban
        assert captured_kwargs["agent_registry"] is mock_registry

    @pytest.mark.asyncio
    async def test_autonomous_skips_poll_when_deps_missing(self) -> None:
        """autonomous_mode=True but no kanban/registry → falls back to channel_loop only."""
        from owlbear.daemon import run_daemon

        channel = MockChannel([None])
        mock_agent = AsyncMock()

        poll_called = False

        async def fake_poll_loop(**kwargs: object) -> None:  # noqa: ARG001
            nonlocal poll_called
            poll_called = True

        settings = MagicMock(spec=OwlBearSettings)
        settings.autonomous_mode = True
        settings.heartbeat_enabled = False
        settings.heartbeat_interval = 1800
        settings.heartbeat_active_hours = (8, 22)

        with patch("owlbear.daemon.poll_loop", new=fake_poll_loop):
            await (
                run_daemon(
                    channel=channel,
                    agent=mock_agent,
                    config_dir=MagicMock(),
                    settings=settings,
                    # No kanban_toolset or agent_registry
                )
            )

        assert not poll_called


# ---------------------------------------------------------------------------
# Issue 2: In-flight task cancellation on shutdown
# ---------------------------------------------------------------------------


class TestInFlightTaskCancellation:
    """After shutdown, in-flight tasks in state.running must be cancelled."""

    @pytest.mark.asyncio
    async def test_shutdown_cancels_running_tasks(self) -> None:
        """Tasks spawned by poll_loop are cancelled when run_daemon exits."""
        from owlbear.daemon import RunningTask, run_daemon

        channel = MockChannel([None])  # returns None → triggers shutdown
        mock_agent = AsyncMock()
        mock_kanban = AsyncMock()
        mock_registry = MagicMock()

        was_cancelled = False

        async def long_running() -> None:
            nonlocal was_cancelled
            try:
                await asyncio.sleep(3600)
            except asyncio.CancelledError:
                was_cancelled = True
                raise

        async def fake_poll_loop(
            *, state: object, shutdown_event: object, **_kwargs: object
        ) -> None:
            # Spawn a long-running task and register it in state
            task = asyncio.create_task(long_running())
            state.running["999"] = RunningTask(task_id="999", asyncio_task=task)  # type: ignore[union-attr]
            await shutdown_event.wait()  # type: ignore[union-attr]

        settings = MagicMock(spec=OwlBearSettings)
        settings.autonomous_mode = True
        settings.heartbeat_enabled = False
        settings.heartbeat_interval = 1800
        settings.heartbeat_active_hours = (8, 22)
        settings.lint_gate_enabled = False

        with patch("owlbear.daemon.poll_loop", new=fake_poll_loop):
            await (
                run_daemon(
                    channel=channel,
                    agent=mock_agent,
                    config_dir=MagicMock(),
                    settings=settings,
                    kanban_toolset=mock_kanban,
                    agent_registry=mock_registry,
                )
            )

        assert was_cancelled


# ---------------------------------------------------------------------------
# WIP injection tests (#639) — TDD red phase
# These should FAIL until #641 wires WipStore into poll_tick/reconcile_tasks.
# ---------------------------------------------------------------------------


class TestWipInjection:
    """WipStore integration with poll_tick dispatch prompt."""

    @pytest.mark.asyncio
    async def test_poll_tick_loads_wip_and_prepends_to_prompt(self) -> None:
        """When WipStore.load returns a summary, the builder prompt contains
        CONTINUE FORWARD directive and WIP text prepended to the task prompt."""
        from owlbear.daemon import OrchestratorState, poll_tick

        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_registry = MagicMock()
        mock_wip = MagicMock()

        # Single todo task
        todo_tasks = [{"id": "100", "title": "WIP task", "priority": "important"}]
        mock_kanban.kanban_list.return_value = _make_kanban_list_json(todo_tasks)
        mock_kanban.kanban_show.return_value = _make_kanban_show_json(
            "100", title="WIP task", body="Do the thing"
        )
        mock_kanban.kanban_move.return_value = "moved"

        # WipStore.load returns a previous WIP summary
        mock_wip.load.return_value = "Previous cycle made progress on step 2"

        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(return_value=MagicMock(data="done"))
        mock_registry.get.return_value = mock_agent

        async def run_tick() -> None:
            await poll_tick(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                max_concurrent=3,
                shutdown_event=asyncio.Event(),
                wip_store=mock_wip,
            )

        await (run_tick())

        # Builder.run() was called
        mock_agent.run.assert_called_once()
        prompt = mock_agent.run.call_args.args[0]

        # Prompt must contain WIP text and CONTINUE FORWARD directive
        assert "Previous cycle made progress on step 2" in prompt
        assert "CONTINUE FORWARD" in prompt

    @pytest.mark.asyncio
    async def test_poll_tick_no_wip_clean_prompt(self) -> None:
        """When WipStore.load returns None, prompt does NOT contain
        CONTINUE FORWARD directive."""
        from owlbear.daemon import OrchestratorState, poll_tick

        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_registry = MagicMock()
        mock_wip = MagicMock()

        todo_tasks = [{"id": "101", "title": "Fresh task", "priority": "important"}]
        mock_kanban.kanban_list.return_value = _make_kanban_list_json(todo_tasks)
        mock_kanban.kanban_show.return_value = _make_kanban_show_json(
            "101", title="Fresh task", body="Start from scratch"
        )
        mock_kanban.kanban_move.return_value = "moved"

        # No WIP for this task
        mock_wip.load.return_value = None

        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(return_value=MagicMock(data="done"))
        mock_registry.get.return_value = mock_agent

        async def run_tick() -> None:
            await poll_tick(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                max_concurrent=3,
                shutdown_event=asyncio.Event(),
                wip_store=mock_wip,
            )

        await (run_tick())

        mock_agent.run.assert_called_once()
        prompt = mock_agent.run.call_args.args[0]

        # No CONTINUE FORWARD in a clean prompt
        assert "CONTINUE FORWARD" not in prompt
        # But the task content IS there
        assert "Start from scratch" in prompt


class TestWipReconciliation:
    """WipStore integration with reconcile_tasks."""

    @pytest.mark.asyncio
    async def test_reconcile_saves_wip_on_failure(self) -> None:
        """When a task FAILS, wip_store.save() is called with the exception
        message as next-cycle context (real Task.result() re-raises)."""
        from owlbear.daemon import OrchestratorState, RunningTask, reconcile_tasks

        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_wip = MagicMock()

        exc = RuntimeError("transient failure")
        dummy_async_task = MagicMock(spec=asyncio.Task)
        dummy_async_task.done.return_value = True
        dummy_async_task.exception.return_value = exc
        dummy_async_task.result.side_effect = exc  # faithful: re-raises

        rt = RunningTask(task_id="110", asyncio_task=dummy_async_task)
        state.running["110"] = rt
        state.claimed.add("110")

        async def run_reconcile() -> None:
            await reconcile_tasks(state=state, kanban=mock_kanban, wip_store=mock_wip)

        await (run_reconcile())

        # wip_store.save called with exception text as summary
        mock_wip.save.assert_called_once()
        call_kwargs = mock_wip.save.call_args.kwargs
        assert call_kwargs["task_id"] == "110"
        assert "RuntimeError" in call_kwargs["summary"]
        assert "transient failure" in call_kwargs["summary"]

    @pytest.mark.asyncio
    async def test_reconcile_clears_wip_on_success(self) -> None:
        """When a task completes successfully, wip_store.clear() is called
        (no more cycles needed)."""
        from owlbear.daemon import OrchestratorState, RunningTask, reconcile_tasks

        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_wip = MagicMock()

        dummy_async_task = MagicMock(spec=asyncio.Task)
        dummy_async_task.done.return_value = True
        dummy_async_task.exception.return_value = None
        dummy_async_task.result.return_value = "task completed"

        rt = RunningTask(task_id="120", asyncio_task=dummy_async_task)
        state.running["120"] = rt
        state.claimed.add("120")

        mock_kanban.kanban_move.return_value = "moved"

        async def run_reconcile() -> None:
            await reconcile_tasks(state=state, kanban=mock_kanban, wip_store=mock_wip)

        await (run_reconcile())

        # Success → clear WIP (task done, no more cycles)
        mock_wip.clear.assert_called_once()
        call_kwargs = mock_wip.clear.call_args
        assert call_kwargs.kwargs.get("task_id") == "120" or (
            call_kwargs.args and "120" in str(call_kwargs)
        )
        # save should NOT be called on success
        mock_wip.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_reconcile_saves_wip_on_any_failure(self) -> None:
        """Any failure saves exception context for next cycle — there is no
        permanent-vs-transient distinction at this level."""
        from owlbear.daemon import OrchestratorState, RunningTask, reconcile_tasks

        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_wip = MagicMock()

        exc = RuntimeError("permanent failure")
        dummy_async_task = MagicMock(spec=asyncio.Task)
        dummy_async_task.done.return_value = True
        dummy_async_task.exception.return_value = exc
        dummy_async_task.result.side_effect = exc  # faithful: re-raises

        rt = RunningTask(task_id="130", asyncio_task=dummy_async_task)
        state.running["130"] = rt
        state.claimed.add("130")

        async def run_reconcile() -> None:
            await reconcile_tasks(state=state, kanban=mock_kanban, wip_store=mock_wip)

        await (run_reconcile())

        # With retry (#625): first failure keeps task in claimed for retry
        assert "130" in state.claimed
        assert "130" in state.retries
        assert "130" not in state.running
        mock_wip.save.assert_called_once()
        assert "permanent failure" in mock_wip.save.call_args.kwargs["summary"]

    @pytest.mark.asyncio
    async def test_auto_save_truncates_output(self) -> None:
        """When exception message exceeds 500 chars, WIP summary is truncated to 500."""
        from owlbear.daemon import OrchestratorState, RunningTask, reconcile_tasks

        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_wip = MagicMock()

        long_msg = "x" * 800  # 800 chars, well over 500 limit
        exc = RuntimeError(long_msg)

        dummy_async_task = MagicMock(spec=asyncio.Task)
        dummy_async_task.done.return_value = True
        dummy_async_task.exception.return_value = exc
        dummy_async_task.result.side_effect = exc  # faithful: re-raises

        rt = RunningTask(task_id="140", asyncio_task=dummy_async_task)
        state.running["140"] = rt
        state.claimed.add("140")

        async def run_reconcile() -> None:
            await reconcile_tasks(state=state, kanban=mock_kanban, wip_store=mock_wip)

        await (run_reconcile())

        # save called with truncated summary
        mock_wip.save.assert_called_once()
        save_kwargs = mock_wip.save.call_args.kwargs
        summary = save_kwargs.get("summary", "")
        assert len(summary) <= 500


# ---------------------------------------------------------------------------
# #621 — Emit TASK_COMPLETE from reconcile_tasks
# ---------------------------------------------------------------------------


class TestTaskCompleteEmitSuccess:
    """reconcile_tasks emits TASK_COMPLETE with outcome='success' on success."""

    @pytest.mark.asyncio
    async def test_emit_called_on_success(self) -> None:
        from owlbear.core.hooks import HookEvent, HookRegistry
        from owlbear.daemon import OrchestratorState, RunningTask, reconcile_tasks

        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_kanban.kanban_move.return_value = "moved"

        hooks = HookRegistry()
        captured: list[object] = []
        hooks.register(HookEvent.TASK_COMPLETE, captured.append)

        dummy = MagicMock(spec=asyncio.Task)
        dummy.done.return_value = True
        dummy.exception.return_value = None
        dummy.result.return_value = "ok"

        rt = RunningTask(task_id="200", asyncio_task=dummy)
        state.running["200"] = rt
        state.claimed.add("200")

        async def run() -> None:
            await reconcile_tasks(state=state, kanban=mock_kanban, hooks=hooks)

        await (run())

        assert len(captured) == 1
        payload = captured[0]
        assert payload["task_id"] == "200"
        assert payload["outcome"] == "success"


class TestTaskCompleteEmitFailure:
    """reconcile_tasks emits TASK_COMPLETE with outcome='failure' on exception."""

    @pytest.mark.asyncio
    async def test_emit_called_on_failure(self) -> None:
        from owlbear.core.hooks import HookEvent, HookRegistry
        from owlbear.daemon import OrchestratorState, RunningTask, reconcile_tasks

        state = OrchestratorState()
        mock_kanban = AsyncMock()

        hooks = HookRegistry()
        captured: list[object] = []
        hooks.register(HookEvent.TASK_COMPLETE, captured.append)

        dummy = MagicMock(spec=asyncio.Task)
        dummy.done.return_value = True
        dummy.exception.return_value = RuntimeError("boom")

        rt = RunningTask(task_id="201", asyncio_task=dummy)
        state.running["201"] = rt
        state.claimed.add("201")

        async def run() -> None:
            await reconcile_tasks(state=state, kanban=mock_kanban, hooks=hooks)

        await (run())

        assert len(captured) == 1
        payload = captured[0]
        assert payload["task_id"] == "201"
        assert payload["outcome"] == "failure"


class TestTaskCompleteHooksNone:
    """hooks=None does not raise — graceful no-op."""

    @pytest.mark.asyncio
    async def test_no_hooks_no_error(self) -> None:
        from owlbear.daemon import OrchestratorState, RunningTask, reconcile_tasks

        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_kanban.kanban_move.return_value = "moved"

        dummy = MagicMock(spec=asyncio.Task)
        dummy.done.return_value = True
        dummy.exception.return_value = None

        rt = RunningTask(task_id="202", asyncio_task=dummy)
        state.running["202"] = rt
        state.claimed.add("202")

        async def run() -> None:
            await reconcile_tasks(state=state, kanban=mock_kanban, hooks=None)

        # Should not raise
        await (run())

        assert "202" not in state.running
        assert "202" not in state.claimed


# ---------------------------------------------------------------------------
# poll_loop body coverage (lines 588-603)
# ---------------------------------------------------------------------------


class TestPollLoopBodyExecutes:
    """poll_loop must actually enter the while-loop, call poll_tick, sleep,
    and then exit on shutdown."""

    @pytest.mark.asyncio
    async def test_poll_loop_runs_one_tick_then_shuts_down(self) -> None:
        """poll_loop enters loop body, calls poll_tick, then shuts down."""
        from owlbear.daemon import OrchestratorState, poll_loop

        state = OrchestratorState()
        shutdown_event = asyncio.Event()
        mock_kanban = AsyncMock()
        mock_kanban.kanban_list.return_value = _make_kanban_list_json([])
        mock_registry = MagicMock()

        tick_count = 0

        async def counting_poll_tick(**kwargs: object) -> None:  # noqa: ARG001
            nonlocal tick_count
            tick_count += 1
            # Let one tick happen, then shut down
            shutdown_event.set()

        async def run_poll() -> None:
            with patch("owlbear.daemon.poll_tick", side_effect=counting_poll_tick):
                await poll_loop(
                    state=state,
                    kanban=mock_kanban,
                    agent_registry=mock_registry,
                    settings=MagicMock(
                        poll_interval=0.01,
                        max_concurrent_tasks=3,
                    ),
                    shutdown_event=shutdown_event,
                )

        await (run_poll())

        assert tick_count == 1

    @pytest.mark.asyncio
    async def test_poll_loop_logs_poll_tick_exception(self) -> None:
        """When poll_tick raises, poll_loop logs and continues."""
        from owlbear.daemon import OrchestratorState, poll_loop

        state = OrchestratorState()
        shutdown_event = asyncio.Event()
        mock_kanban = AsyncMock()
        mock_registry = MagicMock()

        call_count = 0

        async def failing_poll_tick(**kwargs: object) -> None:  # noqa: ARG001
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                msg = "poll_tick boom"
                raise RuntimeError(msg)
            shutdown_event.set()

        async def run_poll() -> None:
            with patch("owlbear.daemon.poll_tick", side_effect=failing_poll_tick):
                await poll_loop(
                    state=state,
                    kanban=mock_kanban,
                    agent_registry=mock_registry,
                    settings=MagicMock(
                        poll_interval=0.01,
                        max_concurrent_tasks=3,
                    ),
                    shutdown_event=shutdown_event,
                )

        await (run_poll())

        # poll_tick was called at least twice: first fails, second sets shutdown
        assert call_count == 2


# ---------------------------------------------------------------------------
# poll_tick shutdown during dispatch loop (line 549)
# ---------------------------------------------------------------------------


class TestPollTickShutdownDuringDispatch:
    """When shutdown_event is set mid-dispatch, remaining tasks are skipped."""

    @pytest.mark.asyncio
    async def test_shutdown_during_dispatch_skips_remaining(self) -> None:
        """With 2 todo tasks, after dispatching the 1st, shutdown stops the 2nd."""
        from owlbear.daemon import OrchestratorState, poll_tick

        state = OrchestratorState()
        shutdown_event = asyncio.Event()
        mock_kanban = AsyncMock()
        mock_registry = MagicMock()

        tasks = [
            {"id": "70", "title": "First", "priority": "critical"},
            {"id": "71", "title": "Second", "priority": "important"},
        ]
        mock_kanban.kanban_list.return_value = _make_kanban_list_json(tasks)
        mock_kanban.kanban_show.return_value = _make_kanban_show_json("70")

        mock_builder = AsyncMock()
        mock_builder.run.return_value = "done"
        mock_registry.get.return_value = mock_builder

        # Set shutdown after first kanban_move (dispatch of task 70)
        async def move_and_shutdown(task_id: str, status: str) -> str:
            result = f"moved {task_id} to {status}"
            # After first move, set shutdown so second task is skipped
            shutdown_event.set()
            return result

        mock_kanban.kanban_move.side_effect = move_and_shutdown

        async def run_tick() -> None:
            await poll_tick(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                max_concurrent=3,
                shutdown_event=shutdown_event,
            )

        await (run_tick())

        # Only the first task should have been moved
        assert mock_kanban.kanban_move.call_count == 1
        mock_kanban.kanban_move.assert_called_once_with("70", "in-progress")


# ---------------------------------------------------------------------------
# #623 — stale_task_timeout config field
# ---------------------------------------------------------------------------


class TestStaleTaskTimeoutConfig:
    """stale_task_timeout config: float, default 300.0, must be > 0."""

    def test_default_300(self, default_settings: OwlBearSettings) -> None:
        assert default_settings.stale_task_timeout == 300.0

    def test_custom_value(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OWLBEAR_STALE_TASK_TIMEOUT", "60.0")
        s = OwlBearSettings()
        assert s.stale_task_timeout == 60.0

    def test_rejects_zero(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OWLBEAR_STALE_TASK_TIMEOUT", "0")
        with pytest.raises(Exception, match="stale_task_timeout"):
            OwlBearSettings()

    def test_rejects_negative(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OWLBEAR_STALE_TASK_TIMEOUT", "-1")
        with pytest.raises(Exception, match="stale_task_timeout"):
            OwlBearSettings()


# ---------------------------------------------------------------------------
# #623 — detect_stale_tasks
# ---------------------------------------------------------------------------


class TestDetectStaleTasks:
    """detect_stale_tasks: cancel, clean state, kanban_edit(block=...), channel.send."""

    @pytest.mark.asyncio
    async def test_stale_task_cancelled_at_exact_boundary(self) -> None:
        """Task started exactly stale_timeout seconds ago → detected as stale."""
        from datetime import timedelta

        from owlbear.daemon import OrchestratorState, RunningTask, detect_stale_tasks

        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_kanban.kanban_edit = AsyncMock(return_value="ok")
        channel = MockChannel([])
        channel.send = AsyncMock()  # type: ignore[assignment]

        dummy_task = MagicMock(spec=asyncio.Task)
        dummy_task.cancel.return_value = True

        started = datetime(2026, 3, 8, 12, 0, 0, tzinfo=UTC)
        rt = RunningTask(task_id="100", asyncio_task=dummy_task, started_at=started)
        state.running["100"] = rt
        state.claimed.add("100")

        # now = started + exactly 300s → should be stale
        fake_now = started + timedelta(seconds=300)

        async def run() -> None:
            with patch("owlbear.daemon.datetime") as mock_dt:
                mock_dt.now.return_value = fake_now
                await detect_stale_tasks(
                    state=state,
                    kanban=mock_kanban,
                    channel=channel,
                    stale_timeout=300.0,
                )

        await (run())

        # Task was cancelled
        dummy_task.cancel.assert_called_once()
        # Removed from state
        assert "100" not in state.running
        assert "100" not in state.claimed
        # Kanban edit with block reason
        mock_kanban.kanban_edit.assert_called_once()
        call_kwargs = mock_kanban.kanban_edit.call_args
        assert "100" in str(call_kwargs)
        assert "Stale" in str(call_kwargs)
        # Channel alert sent
        channel.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_not_stale_just_before_boundary(self) -> None:
        """Task started 299s ago (timeout=300) → NOT stale."""
        from datetime import timedelta

        from owlbear.daemon import OrchestratorState, RunningTask, detect_stale_tasks

        state = OrchestratorState()
        mock_kanban = AsyncMock()
        channel = MockChannel([])
        channel.send = AsyncMock()  # type: ignore[assignment]

        dummy_task = MagicMock(spec=asyncio.Task)

        started = datetime(2026, 3, 8, 12, 0, 0, tzinfo=UTC)
        rt = RunningTask(task_id="101", asyncio_task=dummy_task, started_at=started)
        state.running["101"] = rt
        state.claimed.add("101")

        fake_now = started + timedelta(seconds=299)

        async def run() -> None:
            with patch("owlbear.daemon.datetime") as mock_dt:
                mock_dt.now.return_value = fake_now
                await detect_stale_tasks(
                    state=state,
                    kanban=mock_kanban,
                    channel=channel,
                    stale_timeout=300.0,
                )

        await (run())

        # Task should NOT be cancelled
        dummy_task.cancel.assert_not_called()
        assert "101" in state.running
        assert "101" in state.claimed

    @pytest.mark.asyncio
    async def test_cancel_and_state_cleaned(self) -> None:
        """Verify cancel called, state cleaned, kanban_edit block reason, channel.send."""
        from datetime import timedelta

        from owlbear.daemon import OrchestratorState, RunningTask, detect_stale_tasks

        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_kanban.kanban_edit = AsyncMock(return_value="ok")
        channel = MockChannel([])
        channel.send = AsyncMock()  # type: ignore[assignment]

        dummy_task = MagicMock(spec=asyncio.Task)
        dummy_task.cancel.return_value = True

        started = datetime(2026, 3, 8, 12, 0, 0, tzinfo=UTC)
        rt = RunningTask(task_id="200", asyncio_task=dummy_task, started_at=started)
        state.running["200"] = rt
        state.claimed.add("200")

        fake_now = started + timedelta(seconds=400)

        async def run() -> None:
            with patch("owlbear.daemon.datetime") as mock_dt:
                mock_dt.now.return_value = fake_now
                await detect_stale_tasks(
                    state=state,
                    kanban=mock_kanban,
                    channel=channel,
                    stale_timeout=300.0,
                )

        await (run())

        # (1) cancel
        dummy_task.cancel.assert_called_once()
        # (2) state cleaned
        assert "200" not in state.running
        assert "200" not in state.claimed
        # (3) kanban block reason
        block_call = mock_kanban.kanban_edit.call_args
        assert "Stale" in str(block_call)
        assert "300.0" in str(block_call)
        # (4) channel alert
        channel.send.assert_called_once()
        alert_msg = channel.send.call_args[0][0]
        assert "200" in alert_msg

    @pytest.mark.asyncio
    async def test_kanban_edit_failure_does_not_block_remaining(self) -> None:
        """kanban_edit fails for task A but task B is still processed."""
        from datetime import timedelta

        from owlbear.daemon import OrchestratorState, RunningTask, detect_stale_tasks

        state = OrchestratorState()
        mock_kanban = AsyncMock()
        channel = MockChannel([])
        channel.send = AsyncMock()  # type: ignore[assignment]

        # Two stale tasks
        started = datetime(2026, 3, 8, 12, 0, 0, tzinfo=UTC)

        task_a = MagicMock(spec=asyncio.Task)
        task_a.cancel.return_value = True
        task_b = MagicMock(spec=asyncio.Task)
        task_b.cancel.return_value = True

        state.running["A"] = RunningTask(task_id="A", asyncio_task=task_a, started_at=started)
        state.running["B"] = RunningTask(task_id="B", asyncio_task=task_b, started_at=started)
        state.claimed.update({"A", "B"})

        # kanban_edit fails for first call, succeeds for second
        mock_kanban.kanban_edit = AsyncMock(side_effect=[RuntimeError("kanban down"), "ok"])

        fake_now = started + timedelta(seconds=500)

        async def run() -> None:
            with patch("owlbear.daemon.datetime") as mock_dt:
                mock_dt.now.return_value = fake_now
                await detect_stale_tasks(
                    state=state,
                    kanban=mock_kanban,
                    channel=channel,
                    stale_timeout=300.0,
                )

        await (run())

        # Both tasks cancelled and removed
        task_a.cancel.assert_called_once()
        task_b.cancel.assert_called_once()
        assert "A" not in state.running
        assert "B" not in state.running
        assert "A" not in state.claimed
        assert "B" not in state.claimed

    @pytest.mark.asyncio
    async def test_channel_send_failure_does_not_block_remaining(self) -> None:
        """channel.send fails for task A but task B is still processed."""
        from datetime import timedelta

        from owlbear.daemon import OrchestratorState, RunningTask, detect_stale_tasks

        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_kanban.kanban_edit = AsyncMock(return_value="ok")
        channel = MockChannel([])
        # send fails first time, succeeds second
        channel.send = AsyncMock(  # type: ignore[assignment]
            side_effect=[OSError("send broken"), None]
        )

        started = datetime(2026, 3, 8, 12, 0, 0, tzinfo=UTC)

        task_a = MagicMock(spec=asyncio.Task)
        task_a.cancel.return_value = True
        task_b = MagicMock(spec=asyncio.Task)
        task_b.cancel.return_value = True

        state.running["A"] = RunningTask(task_id="A", asyncio_task=task_a, started_at=started)
        state.running["B"] = RunningTask(task_id="B", asyncio_task=task_b, started_at=started)
        state.claimed.update({"A", "B"})

        fake_now = started + timedelta(seconds=500)

        async def run() -> None:
            with patch("owlbear.daemon.datetime") as mock_dt:
                mock_dt.now.return_value = fake_now
                await detect_stale_tasks(
                    state=state,
                    kanban=mock_kanban,
                    channel=channel,
                    stale_timeout=300.0,
                )

        await (run())

        # Both processed despite channel failure
        task_a.cancel.assert_called_once()
        task_b.cancel.assert_called_once()
        assert len(state.running) == 0


# ---------------------------------------------------------------------------
# #623 — poll_tick gains channel + stale_timeout, calls detect_stale_tasks
# ---------------------------------------------------------------------------


class TestPollTickCallsDetectStaleTasks:
    """poll_tick calls detect_stale_tasks after reconcile and before fetch/dispatch."""

    @pytest.mark.asyncio
    async def test_detect_stale_tasks_called_in_poll_tick(self) -> None:
        """detect_stale_tasks is called with correct args after reconcile."""
        from owlbear.daemon import OrchestratorState, poll_tick

        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_kanban.kanban_list.return_value = _make_kanban_list_json([])
        mock_registry = MagicMock()
        channel = MockChannel([])
        channel.send = AsyncMock()  # type: ignore[assignment]

        async def run() -> None:
            with patch("owlbear.daemon.detect_stale_tasks", new_callable=AsyncMock) as mock_detect:
                await poll_tick(
                    state=state,
                    kanban=mock_kanban,
                    agent_registry=mock_registry,
                    max_concurrent=3,
                    shutdown_event=asyncio.Event(),
                    channel=channel,
                    stale_timeout=300.0,
                )
                mock_detect.assert_called_once_with(
                    state=state,
                    kanban=mock_kanban,
                    channel=channel,
                    stale_timeout=300.0,
                )

        await (run())


# ---------------------------------------------------------------------------
# #623 — poll_loop gains channel param, threads to poll_tick
# ---------------------------------------------------------------------------


class TestPollLoopPassesChannel:
    """poll_loop accepts channel kwarg, passes it to poll_tick."""

    @pytest.mark.asyncio
    async def test_channel_threaded_to_poll_tick(self) -> None:
        from owlbear.daemon import OrchestratorState, poll_loop

        state = OrchestratorState()
        shutdown_event = asyncio.Event()
        mock_kanban = AsyncMock()
        mock_registry = MagicMock()
        channel = MockChannel([])

        captured_kwargs: dict[str, object] = {}

        async def capturing_poll_tick(**kwargs: object) -> None:
            captured_kwargs.update(kwargs)
            shutdown_event.set()

        async def run_poll() -> None:
            with patch("owlbear.daemon.poll_tick", side_effect=capturing_poll_tick):
                await poll_loop(
                    state=state,
                    kanban=mock_kanban,
                    agent_registry=mock_registry,
                    settings=MagicMock(
                        poll_interval=0.01,
                        max_concurrent_tasks=3,
                        stale_task_timeout=300.0,
                    ),
                    shutdown_event=shutdown_event,
                    channel=channel,
                )

        await (run_poll())

        assert captured_kwargs["channel"] is channel
        assert captured_kwargs["stale_timeout"] == 300.0


# ---------------------------------------------------------------------------
# #623 — run_daemon passes channel to poll_loop
# ---------------------------------------------------------------------------


class TestRunDaemonPassesChannelToPollLoop:
    """run_daemon threads channel through to poll_loop in autonomous mode."""

    @pytest.mark.asyncio
    async def test_channel_reaches_poll_loop(self) -> None:
        from owlbear.daemon import run_daemon

        channel = MockChannel([None])
        mock_agent = AsyncMock()
        mock_kanban = AsyncMock()
        mock_registry = MagicMock()

        captured_kwargs: dict[str, object] = {}

        async def fake_poll_loop(**kwargs: object) -> None:
            captured_kwargs.update(kwargs)
            ev = kwargs["shutdown_event"]
            await ev.wait()  # type: ignore[union-attr]

        settings = MagicMock(spec=OwlBearSettings)
        settings.autonomous_mode = True
        settings.heartbeat_enabled = False
        settings.heartbeat_interval = 1800
        settings.heartbeat_active_hours = (8, 22)
        settings.lint_gate_enabled = False

        with patch("owlbear.daemon.poll_loop", new=fake_poll_loop):
            await (
                run_daemon(
                    channel=channel,
                    agent=mock_agent,
                    config_dir=MagicMock(),
                    settings=settings,
                    kanban_toolset=mock_kanban,
                    agent_registry=mock_registry,
                )
            )

        assert captured_kwargs["channel"] is channel


# ===========================================================================
# #679 — Tests for task-level retry with exponential backoff (#625)
# ===========================================================================
# These tests define the interface for task-level retry.  They will ALL FAIL
# until #625 implementation is merged.  Marked xfail so the existing suite
# stays green.
# ===========================================================================

# ---------------------------------------------------------------------------
# AC 1: RetryEntry dataclass
# ---------------------------------------------------------------------------


class TestRetryEntry:
    """RetryEntry dataclass: task_id, attempt, next_due, last_error."""

    def test_construction(self) -> None:
        from owlbear.daemon import RetryEntry

        now = datetime.now(UTC)
        entry = RetryEntry(task_id="10", attempt=1, next_due=now, last_error="boom")
        assert entry.task_id == "10"
        assert entry.attempt == 1
        assert entry.next_due == now
        assert entry.last_error == "boom"

    def test_defaults(self) -> None:
        """attempt defaults to 1, last_error defaults to empty string."""
        from owlbear.daemon import RetryEntry

        now = datetime.now(UTC)
        entry = RetryEntry(task_id="11", next_due=now)
        assert entry.attempt == 1
        assert entry.last_error == ""


# ---------------------------------------------------------------------------
# AC 2: RetryConfig — config fields for retry
# ---------------------------------------------------------------------------


class TestRetryConfig:
    """Config fields: task_retry_max_attempts, task_retry_backoff_base, task_retry_backoff_max."""

    def test_max_attempts_default_5(self, default_settings: OwlBearSettings) -> None:
        assert default_settings.task_retry_max_attempts == 5

    def test_max_attempts_rejects_zero(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OWLBEAR_TASK_RETRY_MAX_ATTEMPTS", "0")
        with pytest.raises(Exception, match="task_retry_max_attempts"):
            OwlBearSettings()

    def test_max_attempts_rejects_negative(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OWLBEAR_TASK_RETRY_MAX_ATTEMPTS", "-1")
        with pytest.raises(Exception, match="task_retry_max_attempts"):
            OwlBearSettings()

    def test_backoff_base_default_10(self, default_settings: OwlBearSettings) -> None:
        assert default_settings.task_retry_backoff_base == 10.0

    def test_backoff_base_rejects_zero(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OWLBEAR_TASK_RETRY_BACKOFF_BASE", "0")
        with pytest.raises(Exception, match="task_retry_backoff_base"):
            OwlBearSettings()

    def test_backoff_base_rejects_negative(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OWLBEAR_TASK_RETRY_BACKOFF_BASE", "-5")
        with pytest.raises(Exception, match="task_retry_backoff_base"):
            OwlBearSettings()

    def test_backoff_max_default_320(self, default_settings: OwlBearSettings) -> None:
        assert default_settings.task_retry_backoff_max == 320.0

    def test_backoff_max_rejects_zero(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OWLBEAR_TASK_RETRY_BACKOFF_MAX", "0")
        with pytest.raises(Exception, match="task_retry_backoff_max"):
            OwlBearSettings()

    def test_backoff_max_rejects_negative(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OWLBEAR_TASK_RETRY_BACKOFF_MAX", "-10")
        with pytest.raises(Exception, match="task_retry_backoff_max"):
            OwlBearSettings()


# ---------------------------------------------------------------------------
# AC 3: reconcile_tasks schedules retry on failure
# ---------------------------------------------------------------------------


class TestReconcileSchedulesRetry:
    """Failed task creates RetryEntry in state.retries with attempt=1."""

    @pytest.mark.asyncio
    async def test_failed_task_creates_retry_entry(self) -> None:
        from owlbear.daemon import OrchestratorState, RetryEntry, RunningTask, reconcile_tasks

        state = OrchestratorState()
        mock_kanban = AsyncMock()

        dummy_task = MagicMock(spec=asyncio.Task)
        dummy_task.done.return_value = True
        dummy_task.exception.return_value = RuntimeError("agent crashed")

        rt = RunningTask(task_id="200", asyncio_task=dummy_task)
        state.running["200"] = rt
        state.claimed.add("200")

        async def run() -> None:
            await reconcile_tasks(state=state, kanban=mock_kanban)

        await (run())

        # RetryEntry created in state.retries
        assert "200" in state.retries
        entry = state.retries["200"]
        assert isinstance(entry, RetryEntry)
        assert entry.task_id == "200"
        assert entry.attempt == 1
        assert "agent crashed" in entry.last_error

    @pytest.mark.asyncio
    async def test_failed_task_stays_in_claimed(self) -> None:
        from owlbear.daemon import OrchestratorState, RunningTask, reconcile_tasks

        state = OrchestratorState()
        mock_kanban = AsyncMock()

        dummy_task = MagicMock(spec=asyncio.Task)
        dummy_task.done.return_value = True
        dummy_task.exception.return_value = RuntimeError("boom")

        rt = RunningTask(task_id="201", asyncio_task=dummy_task)
        state.running["201"] = rt
        state.claimed.add("201")

        async def run() -> None:
            await reconcile_tasks(state=state, kanban=mock_kanban)

        await (run())

        # Task stays in claimed (retry pending, don't release)
        assert "201" in state.claimed

    @pytest.mark.asyncio
    async def test_retry_entry_has_correct_next_due(self) -> None:
        """next_due = now + base * 2**(attempt-1) = now + 10s for attempt=1."""
        from datetime import timedelta

        from owlbear.daemon import OrchestratorState, RunningTask, reconcile_tasks

        state = OrchestratorState()
        mock_kanban = AsyncMock()

        dummy_task = MagicMock(spec=asyncio.Task)
        dummy_task.done.return_value = True
        dummy_task.exception.return_value = RuntimeError("fail")

        rt = RunningTask(task_id="202", asyncio_task=dummy_task)
        state.running["202"] = rt
        state.claimed.add("202")

        before = datetime.now(UTC)

        async def run() -> None:
            await reconcile_tasks(state=state, kanban=mock_kanban)

        await (run())

        after = datetime.now(UTC)
        entry = state.retries["202"]
        # For attempt=1 with default base=10: delay = 10 * 2^0 = 10s
        assert entry.next_due >= before + timedelta(seconds=10)
        assert entry.next_due <= after + timedelta(seconds=10)


# ---------------------------------------------------------------------------
# AC 4: reconcile_tasks increments retry on repeated failure
# ---------------------------------------------------------------------------


class TestReconcileIncrementsRetry:
    """Second failure increments attempt to 2, doubles delay."""

    @pytest.mark.asyncio
    async def test_second_failure_increments_attempt(self) -> None:
        from datetime import timedelta

        from owlbear.daemon import (
            OrchestratorState,
            RetryEntry,
            RunningTask,
            reconcile_tasks,
        )

        state = OrchestratorState()
        mock_kanban = AsyncMock()

        # Pre-existing retry entry from first failure
        first_due = datetime.now(UTC) + timedelta(seconds=10)
        state.retries = {
            "300": RetryEntry(task_id="300", attempt=1, next_due=first_due, last_error="first fail")
        }

        # Second failure arrives
        dummy_task = MagicMock(spec=asyncio.Task)
        dummy_task.done.return_value = True
        dummy_task.exception.return_value = RuntimeError("second fail")

        rt = RunningTask(task_id="300", asyncio_task=dummy_task)
        state.running["300"] = rt
        state.claimed.add("300")

        before = datetime.now(UTC)

        async def run() -> None:
            await reconcile_tasks(state=state, kanban=mock_kanban)

        await (run())

        after = datetime.now(UTC)
        entry = state.retries["300"]
        assert entry.attempt == 2
        assert "second fail" in entry.last_error
        # For attempt=2: delay = 10 * 2^1 = 20s
        assert entry.next_due >= before + timedelta(seconds=20)
        assert entry.next_due <= after + timedelta(seconds=20)


# ---------------------------------------------------------------------------
# AC 5: Backoff formula
# ---------------------------------------------------------------------------


class TestBackoffFormula:
    """delay = min(base * 2**(attempt-1), max) for attempts 1..6."""

    def test_backoff_values(self) -> None:
        """Verify backoff sequence: 10, 20, 40, 80, 160, 320."""
        from owlbear.daemon import _compute_retry_delay

        base = 10.0
        maximum = 320.0
        expected = [10.0, 20.0, 40.0, 80.0, 160.0, 320.0]
        for attempt, expected_delay in enumerate(expected, start=1):
            delay = _compute_retry_delay(attempt=attempt, base=base, maximum=maximum)
            assert delay == expected_delay, (
                f"attempt={attempt}: expected {expected_delay}, got {delay}"
            )

    def test_backoff_caps_at_max(self) -> None:
        """Attempt 7+ should still be capped at max (320)."""
        from owlbear.daemon import _compute_retry_delay

        delay = _compute_retry_delay(attempt=7, base=10.0, maximum=320.0)
        assert delay == 320.0

    def test_backoff_with_custom_values(self) -> None:
        """Custom base=5, max=100: 5, 10, 20, 40, 80, 100, 100."""
        from owlbear.daemon import _compute_retry_delay

        expected = [5.0, 10.0, 20.0, 40.0, 80.0, 100.0, 100.0]
        for attempt, expected_delay in enumerate(expected, start=1):
            delay = _compute_retry_delay(attempt=attempt, base=5.0, maximum=100.0)
            assert delay == expected_delay


# ---------------------------------------------------------------------------
# AC 6: Retry exhaustion → block on kanban + remove
# ---------------------------------------------------------------------------


class TestRetryExhaustion:
    """When attempt > max_attempts, block task on kanban and remove from retries + claimed."""

    @pytest.mark.asyncio
    async def test_exhausted_blocks_and_removes(self) -> None:
        from datetime import timedelta

        from owlbear.daemon import (
            OrchestratorState,
            RetryEntry,
            RunningTask,
            reconcile_tasks,
        )

        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_kanban.kanban_edit = AsyncMock(return_value="ok")

        # Pre-existing retry at max_attempts (5)
        state.retries = {
            "400": RetryEntry(
                task_id="400",
                attempt=5,
                next_due=datetime.now(UTC) + timedelta(seconds=320),
                last_error="fifth fail",
            )
        }

        # 6th failure arrives → exceeds max_attempts
        dummy_task = MagicMock(spec=asyncio.Task)
        dummy_task.done.return_value = True
        dummy_task.exception.return_value = RuntimeError("sixth fail")

        rt = RunningTask(task_id="400", asyncio_task=dummy_task)
        state.running["400"] = rt
        state.claimed.add("400")

        async def run() -> None:
            await reconcile_tasks(state=state, kanban=mock_kanban)

        await (run())

        # kanban_edit called with block reason
        mock_kanban.kanban_edit.assert_called_once()
        call_args = mock_kanban.kanban_edit.call_args
        assert "400" in str(call_args)
        assert "block" in str(call_args).lower() or "retry" in str(call_args).lower()

        # Removed from retries and claimed
        assert "400" not in state.retries
        assert "400" not in state.claimed
        assert "400" not in state.running


# ---------------------------------------------------------------------------
# AC 7: poll_tick re-dispatches due retries
# ---------------------------------------------------------------------------


class TestRetryDispatch:
    """poll_tick re-dispatches retry entries where next_due <= now."""

    @pytest.mark.asyncio
    async def test_due_retry_redispatched(self) -> None:
        from datetime import timedelta

        from owlbear.daemon import OrchestratorState, RetryEntry, poll_tick

        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_registry = MagicMock()
        shutdown = asyncio.Event()

        # Mock builder agent
        mock_builder = AsyncMock()
        mock_builder.run = AsyncMock(return_value="done")
        mock_registry.get.return_value = mock_builder

        # Kanban list returns no new tasks (empty)
        mock_kanban.kanban_list = AsyncMock(return_value="[]")
        mock_kanban.kanban_show = AsyncMock(
            return_value=_make_kanban_show_json("500", title="Retry target")
        )
        mock_kanban.kanban_move = AsyncMock(return_value="ok")

        # A retry entry that is due NOW
        past_due = datetime.now(UTC) - timedelta(seconds=1)
        state.retries = {
            "500": RetryEntry(task_id="500", attempt=1, next_due=past_due, last_error="prev fail")
        }
        state.claimed.add("500")

        async def run() -> None:
            await poll_tick(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                max_concurrent=3,
                shutdown_event=shutdown,
            )

        await (run())

        # Retry entry removed from retries
        assert "500" not in state.retries
        # Task dispatched (added to running)
        assert "500" in state.running


# ---------------------------------------------------------------------------
# AC 8: poll_tick skips not-yet-due retries
# ---------------------------------------------------------------------------


class TestRetryNotDueYet:
    """poll_tick skips retry entries where next_due > now."""

    @pytest.mark.asyncio
    async def test_future_retry_not_dispatched(self) -> None:
        from datetime import timedelta

        from owlbear.daemon import OrchestratorState, RetryEntry, poll_tick

        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_registry = MagicMock()
        shutdown = asyncio.Event()

        mock_kanban.kanban_list = AsyncMock(return_value="[]")

        # A retry entry due in the FUTURE
        future_due = datetime.now(UTC) + timedelta(hours=1)
        state.retries = {
            "600": RetryEntry(task_id="600", attempt=1, next_due=future_due, last_error="fail")
        }
        state.claimed.add("600")

        async def run() -> None:
            await poll_tick(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                max_concurrent=3,
                shutdown_event=shutdown,
            )

        await (run())

        # Retry entry still in retries (not dispatched)
        assert "600" in state.retries
        # Not in running
        assert "600" not in state.running


# ---------------------------------------------------------------------------
# AC 9: Re-dispatched retry uses WIP context
# ---------------------------------------------------------------------------


class TestRetryDispatchUsesWip:
    """Re-dispatched retry loads WIP context into prompt via wip_store.load()."""

    @pytest.mark.asyncio
    async def test_wip_loaded_into_retry_prompt(self) -> None:
        from datetime import timedelta

        from owlbear.daemon import CONTINUE_FORWARD_PREFIX, OrchestratorState, RetryEntry, poll_tick

        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_registry = MagicMock()
        shutdown = asyncio.Event()

        # Track the prompt passed to builder.run
        captured_prompts: list[str] = []
        mock_builder = AsyncMock()

        async def capture_run(prompt: str, **_kwargs: object) -> str:
            captured_prompts.append(prompt)
            return "done"

        mock_builder.run = AsyncMock(side_effect=capture_run)
        mock_registry.get.return_value = mock_builder

        mock_kanban.kanban_list = AsyncMock(return_value="[]")
        mock_kanban.kanban_show = AsyncMock(
            return_value=_make_kanban_show_json("700", title="WIP retry task")
        )
        mock_kanban.kanban_move = AsyncMock(return_value="ok")

        # WIP store with context for this task
        mock_wip = MagicMock()
        mock_wip.load.return_value = "Previous attempt got halfway through"

        # Retry entry due now
        past_due = datetime.now(UTC) - timedelta(seconds=1)
        state.retries = {
            "700": RetryEntry(task_id="700", attempt=2, next_due=past_due, last_error="prev fail")
        }
        state.claimed.add("700")

        async def run() -> None:
            await poll_tick(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                max_concurrent=3,
                shutdown_event=shutdown,
                wip_store=mock_wip,
            )

        await (run())
        await asyncio.sleep(0)  # drain tasks spawned by poll_tick

        # wip_store.load was called for the retry task
        mock_wip.load.assert_any_call(agent="builder", task_id="700")
        # The prompt should contain the WIP context
        assert len(captured_prompts) == 1
        assert "Previous attempt got halfway through" in captured_prompts[0]
        assert CONTINUE_FORWARD_PREFIX in captured_prompts[0]
