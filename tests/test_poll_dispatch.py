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
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlbear.config import OwlBearSettings

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run(coro: object) -> object:
    """Run an async coroutine synchronously."""
    return asyncio.run(coro)  # type: ignore[arg-type]


class MockChannel:
    """Minimal ChannelPlugin mock with programmable receive sequence."""

    def __init__(self, messages: list[str | None]) -> None:
        self._messages = list(messages)
        self._index = 0
        self.sent: list[str] = []

    @property
    def name(self) -> str:
        return "mock"

    async def send(self, message: str) -> None:
        self.sent.append(message)

    async def receive(self, *, prompt: str | None = None) -> str | None:  # noqa: ARG002
        if self._index >= len(self._messages):
            return None
        msg = self._messages[self._index]
        self._index += 1
        return msg


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

    def test_both_run_in_task_group(self) -> None:
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

        _run(run_both())

        assert state_holder["channel_ran"]
        assert state_holder["poll_ran"]


# ---------------------------------------------------------------------------
# AC 9: autonomous_mode=False — poll_loop not started, channel_loop alone
# ---------------------------------------------------------------------------


class TestAutonomousModeDisabled:
    """When autonomous_mode=False, only channel_loop runs."""

    def test_poll_loop_not_started(self) -> None:
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
            _run(
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

    def test_tick_calls_in_order(self) -> None:
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

        _run(run_tick())

        # Should have fetched todo list
        mock_kanban.kanban_list.assert_called()

    def test_critical_dispatched_before_nice_to_have(self) -> None:
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

        _run(run_tick())

        # Critical task dispatched first
        assert dispatched_ids[0] == "21"


# ---------------------------------------------------------------------------
# AC 6: Dispatch — task moved to in-progress, asyncio.Task spawned
# ---------------------------------------------------------------------------


class TestDispatch:
    """Dispatch moves task to in-progress and spawns via AgentRegistry.get('builder')."""

    def test_task_moved_to_in_progress(self) -> None:
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

        _run(run_tick())

        # Verify kanban_move called with in-progress
        move_calls = [
            c for c in mock_kanban.kanban_move.call_args_list if c.args[1] == "in-progress"
        ]
        assert len(move_calls) >= 1
        assert move_calls[0].args[0] == "30"

    def test_builder_agent_resolved(self) -> None:
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

        _run(run_tick())

        mock_registry.get.assert_called_with("builder")

    def test_claimed_set_updated(self) -> None:
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

        _run(run_tick())

        assert "32" in state.claimed


# ---------------------------------------------------------------------------
# AC 7: Completed task moved to review via KanbanToolset
# ---------------------------------------------------------------------------


class TestCompletedTaskMovedToReview:
    """When a dispatched task completes successfully, it moves to review."""

    def test_success_moves_to_review(self) -> None:
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

        _run(run_reconcile())

        # Task should be moved to review
        mock_kanban.kanban_move.assert_any_call("40", "review")
        # Task should be removed from running
        assert "40" not in state.running


# ---------------------------------------------------------------------------
# AC 8: Failed dispatch frees slot (error logged, NOT moved to review)
# ---------------------------------------------------------------------------


class TestFailedDispatchFreesSlot:
    """Failed dispatch frees the slot — error logged, task NOT moved to review."""

    def test_exception_frees_slot(self) -> None:
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

        _run(run_reconcile())

        # Task removed from running (slot freed)
        assert "50" not in state.running
        # Task NOT moved to review (no such call)
        review_calls = [
            c for c in mock_kanban.kanban_move.call_args_list if c.args == ("50", "review")
        ]
        assert len(review_calls) == 0

    def test_exception_removes_from_claimed(self) -> None:
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

        _run(run_reconcile())

        assert "51" not in state.claimed


# ---------------------------------------------------------------------------
# AC 10: shutdown_event during poll tick exits cleanly
# ---------------------------------------------------------------------------


class TestShutdownDuringPollTick:
    """Setting shutdown_event during a poll tick causes clean exit."""

    def test_shutdown_event_exits_poll_loop(self) -> None:
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
        _run(run_poll())

        # No kanban calls — exited before first tick
        mock_kanban.kanban_list.assert_not_called()

    def test_shutdown_mid_tick_stops_dispatch(self) -> None:
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

        _run(run_tick())

        # Should not dispatch — shutdown was set
        mock_kanban.kanban_move.assert_not_called()


# ---------------------------------------------------------------------------
# AC 11: max_concurrent_tasks cap — no dispatch when all slots full
# ---------------------------------------------------------------------------


class TestMaxConcurrentTasksCap:
    """No dispatch when all slots are occupied."""

    def test_no_dispatch_when_full(self) -> None:
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

        _run(run_tick())

        # No move to in-progress — slots full
        in_progress_calls = [
            c
            for c in mock_kanban.kanban_move.call_args_list
            if len(c.args) >= 2 and c.args[1] == "in-progress"
        ]
        assert len(in_progress_calls) == 0

    def test_partial_slots_dispatch_limited(self) -> None:
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

        _run(run_tick())

        # Only 1 task dispatched (1 free slot from max 2)
        in_progress_calls = [
            c
            for c in mock_kanban.kanban_move.call_args_list
            if len(c.args) >= 2 and c.args[1] == "in-progress"
        ]
        assert len(in_progress_calls) == 1

    def test_already_claimed_tasks_skipped(self) -> None:
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

        _run(run_tick())

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

    def test_autonomous_passes_deps_to_poll_loop(self) -> None:
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

        with patch("owlbear.daemon.poll_loop", new=fake_poll_loop):
            _run(
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

    def test_autonomous_skips_poll_when_deps_missing(self) -> None:
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
            _run(
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

    def test_shutdown_cancels_running_tasks(self) -> None:
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

        with patch("owlbear.daemon.poll_loop", new=fake_poll_loop):
            _run(
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

    def test_poll_tick_loads_wip_and_prepends_to_prompt(self) -> None:
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

        _run(run_tick())

        # Builder.run() was called
        mock_agent.run.assert_called_once()
        prompt = mock_agent.run.call_args.args[0]

        # Prompt must contain WIP text and CONTINUE FORWARD directive
        assert "Previous cycle made progress on step 2" in prompt
        assert "CONTINUE FORWARD" in prompt

    def test_poll_tick_no_wip_clean_prompt(self) -> None:
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

        _run(run_tick())

        mock_agent.run.assert_called_once()
        prompt = mock_agent.run.call_args.args[0]

        # No CONTINUE FORWARD in a clean prompt
        assert "CONTINUE FORWARD" not in prompt
        # But the task content IS there
        assert "Start from scratch" in prompt


class TestWipReconciliation:
    """WipStore integration with reconcile_tasks."""

    def test_reconcile_saves_wip_on_failure(self) -> None:
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

        _run(run_reconcile())

        # wip_store.save called with exception text as summary
        mock_wip.save.assert_called_once()
        call_kwargs = mock_wip.save.call_args.kwargs
        assert call_kwargs["task_id"] == "110"
        assert "RuntimeError" in call_kwargs["summary"]
        assert "transient failure" in call_kwargs["summary"]

    def test_reconcile_clears_wip_on_success(self) -> None:
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

        _run(run_reconcile())

        # Success → clear WIP (task done, no more cycles)
        mock_wip.clear.assert_called_once()
        call_kwargs = mock_wip.clear.call_args
        assert call_kwargs.kwargs.get("task_id") == "120" or (
            call_kwargs.args and "120" in str(call_kwargs)
        )
        # save should NOT be called on success
        mock_wip.save.assert_not_called()

    def test_reconcile_saves_wip_on_any_failure(self) -> None:
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

        _run(run_reconcile())

        # Failure saves exception context, discards claimed
        assert "130" not in state.claimed
        assert "130" not in state.running
        mock_wip.save.assert_called_once()
        assert "permanent failure" in mock_wip.save.call_args.kwargs["summary"]

    def test_auto_save_truncates_output(self) -> None:
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

        _run(run_reconcile())

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

    def test_emit_called_on_success(self) -> None:
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

        _run(run())

        assert len(captured) == 1
        payload = captured[0]
        assert payload["task_id"] == "200"
        assert payload["outcome"] == "success"


class TestTaskCompleteEmitFailure:
    """reconcile_tasks emits TASK_COMPLETE with outcome='failure' on exception."""

    def test_emit_called_on_failure(self) -> None:
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

        _run(run())

        assert len(captured) == 1
        payload = captured[0]
        assert payload["task_id"] == "201"
        assert payload["outcome"] == "failure"


class TestTaskCompleteHooksNone:
    """hooks=None does not raise — graceful no-op."""

    def test_no_hooks_no_error(self) -> None:
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
        _run(run())

        assert "202" not in state.running
        assert "202" not in state.claimed
