"""Tests for blocked-task dedup in poll_tick -- task #756.

RED phase: all tests assert on behaviour that does not exist yet.
The implementation (#754) will add ``last_attempted_at`` to
``OrchestratorState`` and a dedup filter in ``poll_tick`` step 5.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Helpers (mirror test_poll_dispatch.py conventions)
# ---------------------------------------------------------------------------


def _run(coro: object) -> object:
    """Run an async coroutine synchronously."""
    return asyncio.run(coro)  # type: ignore[arg-type]


def _make_kanban_list_json(tasks: list[dict[str, str]]) -> str:
    """Build fake kanban-md list --json output, including 'updated' field."""
    return json.dumps(tasks)


def _make_kanban_show_json(
    task_id: str,
    title: str = "Test task",
    priority: str = "important",
    body: str = "AC line 1",
) -> str:
    return json.dumps(
        {
            "id": task_id,
            "title": title,
            "status": "todo",
            "priority": priority,
            "body": body,
        }
    )


def _ts(dt: datetime) -> str:
    """Format a datetime as ISO-8601 string (mimics kanban-md 'updated' field)."""
    return dt.isoformat()


# ---------------------------------------------------------------------------
# TestFromAC_BlockedTaskDedup
# ---------------------------------------------------------------------------


class TestFromAC_BlockedTaskDedup:  # noqa: N801
    """Dedup filter in poll_tick: skip todo tasks that were already attempted
    and have no new kanban activity since then."""

    # -- AC: OrchestratorState has last_attempted_at field -------------------

    def test_orchestrator_state_has_last_attempted_at(self) -> None:
        """OrchestratorState must expose a last_attempted_at dict,
        defaulting to empty on fresh instantiation."""
        from owlbear.daemon import OrchestratorState

        state = OrchestratorState()
        assert isinstance(state.last_attempted_at, dict)
        assert state.last_attempted_at == {}

    # -- AC: task never attempted is always dispatched -----------------------

    def test_never_attempted_task_is_dispatched(self) -> None:
        """A todo task with no last_attempted_at entry must be dispatched."""
        from owlbear.daemon import OrchestratorState, poll_tick

        state = OrchestratorState()

        now = datetime.now(UTC)
        todo_tasks = [
            {"id": "100", "title": "Brand new", "priority": "important", "updated": _ts(now)},
        ]

        mock_kanban = AsyncMock()
        mock_kanban.kanban_list.return_value = _make_kanban_list_json(todo_tasks)
        mock_kanban.kanban_show.return_value = _make_kanban_show_json("100")
        mock_kanban.kanban_move.return_value = "moved"

        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(return_value=MagicMock(data="done"))
        mock_registry = MagicMock()
        mock_registry.get.return_value = mock_agent

        async def go() -> None:
            await poll_tick(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                max_concurrent=3,
                shutdown_event=asyncio.Event(),
            )

        _run(go())

        assert "100" in state.running
        assert "100" in state.claimed
        # last_attempted_at must be recorded for newly dispatched tasks
        assert "100" in state.last_attempted_at

    # -- AC: task with no new activity since last attempt is skipped ----------

    def test_no_new_activity_since_last_attempt_is_skipped(self) -> None:
        """A todo task whose updated timestamp is strictly before
        last_attempted_at[task_id] must NOT be dispatched."""
        from owlbear.daemon import OrchestratorState, poll_tick

        state = OrchestratorState()
        now = datetime.now(UTC)

        last_attempt = now - timedelta(minutes=10)
        task_updated = now - timedelta(minutes=20)

        state.last_attempted_at = {"200": last_attempt}

        todo_tasks = [
            {"id": "200", "title": "Stale", "priority": "important", "updated": _ts(task_updated)},
        ]

        mock_kanban = AsyncMock()
        mock_kanban.kanban_list.return_value = _make_kanban_list_json(todo_tasks)
        mock_kanban.kanban_move.return_value = "moved"

        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(return_value=MagicMock(data="done"))
        mock_registry = MagicMock()
        mock_registry.get.return_value = mock_agent

        async def go() -> None:
            await poll_tick(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                max_concurrent=3,
                shutdown_event=asyncio.Event(),
            )

        _run(go())

        assert "200" not in state.running
        in_progress_calls = [
            c for c in mock_kanban.kanban_move.call_args_list if c.args[1] == "in-progress"
        ]
        for call in in_progress_calls:
            assert call.args[0] != "200"

    # -- AC: task with new activity since last attempt is dispatched ----------

    def test_new_activity_since_last_attempt_is_dispatched(self) -> None:
        """A todo task whose updated timestamp is >= last_attempted_at
        must be dispatched (new kanban activity detected)."""
        from owlbear.daemon import OrchestratorState, poll_tick

        state = OrchestratorState()
        now = datetime.now(UTC)

        last_attempt = now - timedelta(minutes=30)
        task_updated = now - timedelta(minutes=5)

        state.last_attempted_at = {"300": last_attempt}

        todo_tasks = [
            {"id": "300", "title": "Fresh", "priority": "important", "updated": _ts(task_updated)},
        ]

        mock_kanban = AsyncMock()
        mock_kanban.kanban_list.return_value = _make_kanban_list_json(todo_tasks)
        mock_kanban.kanban_show.return_value = _make_kanban_show_json("300")
        mock_kanban.kanban_move.return_value = "moved"

        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(return_value=MagicMock(data="done"))
        mock_registry = MagicMock()
        mock_registry.get.return_value = mock_agent

        async def go() -> None:
            await poll_tick(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                max_concurrent=3,
                shutdown_event=asyncio.Event(),
            )

        before = datetime.now(UTC)
        _run(go())

        assert "300" in state.running
        assert "300" in state.claimed
        # last_attempted_at must be updated by poll_tick to a NEWER timestamp
        assert state.last_attempted_at["300"] >= before

    def test_equal_timestamp_is_dispatched(self) -> None:
        """Boundary: when updated == last_attempted_at, task IS dispatched."""
        from owlbear.daemon import OrchestratorState, poll_tick

        state = OrchestratorState()
        ts = datetime(2026, 3, 12, 10, 0, 0, tzinfo=UTC)

        state.last_attempted_at = {"301": ts}

        todo_tasks = [
            {"id": "301", "title": "Edge", "priority": "important", "updated": _ts(ts)},
        ]

        mock_kanban = AsyncMock()
        mock_kanban.kanban_list.return_value = _make_kanban_list_json(todo_tasks)
        mock_kanban.kanban_show.return_value = _make_kanban_show_json("301")
        mock_kanban.kanban_move.return_value = "moved"

        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(return_value=MagicMock(data="done"))
        mock_registry = MagicMock()
        mock_registry.get.return_value = mock_agent

        async def go() -> None:
            await poll_tick(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                max_concurrent=3,
                shutdown_event=asyncio.Event(),
            )

        before = datetime.now(UTC)
        _run(go())

        assert "301" in state.running
        # Boundary: last_attempted_at must be updated to a NEWER timestamp
        assert state.last_attempted_at["301"] >= before

    # -- AC: skipped tasks are logged at DEBUG level -------------------------

    def test_skipped_task_logged_at_debug(self, caplog: pytest.LogCaptureFixture) -> None:
        """When a task is skipped due to dedup, a DEBUG log message is
        emitted containing the task_id and reason."""
        from owlbear.daemon import OrchestratorState, poll_tick

        state = OrchestratorState()
        now = datetime.now(UTC)

        last_attempt = now - timedelta(minutes=5)
        task_updated = now - timedelta(minutes=15)

        state.last_attempted_at = {"400": last_attempt}

        todo_tasks = [
            {
                "id": "400",
                "title": "Skip me",
                "priority": "important",
                "updated": _ts(task_updated),
            },
        ]

        mock_kanban = AsyncMock()
        mock_kanban.kanban_list.return_value = _make_kanban_list_json(todo_tasks)
        mock_kanban.kanban_move.return_value = "moved"

        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(return_value=MagicMock(data="done"))
        mock_registry = MagicMock()
        mock_registry.get.return_value = mock_agent

        async def go() -> None:
            await poll_tick(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                max_concurrent=3,
                shutdown_event=asyncio.Event(),
            )

        with caplog.at_level(logging.DEBUG, logger="owlbear.daemon"):
            _run(go())

        debug_messages = [r.message for r in caplog.records if r.levelno == logging.DEBUG]
        assert any("400" in msg for msg in debug_messages), (
            f"Expected DEBUG log mentioning task '400', got: {debug_messages}"
        )

    # -- AC: daemon restart (empty state) processes all tasks ----------------

    def test_fresh_state_dispatches_all_tasks(self) -> None:
        """A fresh OrchestratorState (simulating daemon restart) has no
        last_attempted_at entries, so every todo task is dispatched."""
        from owlbear.daemon import OrchestratorState, poll_tick

        state = OrchestratorState()
        assert state.last_attempted_at == {}

        now = datetime.now(UTC)
        todo_tasks = [
            {
                "id": "500",
                "title": "Task A",
                "priority": "important",
                "updated": _ts(now - timedelta(hours=1)),
            },
            {
                "id": "501",
                "title": "Task B",
                "priority": "critical",
                "updated": _ts(now - timedelta(hours=2)),
            },
        ]

        mock_kanban = AsyncMock()
        mock_kanban.kanban_list.return_value = _make_kanban_list_json(todo_tasks)
        mock_kanban.kanban_show.side_effect = [
            _make_kanban_show_json("501", priority="critical"),
            _make_kanban_show_json("500"),
        ]
        mock_kanban.kanban_move.return_value = "moved"

        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(return_value=MagicMock(data="done"))
        mock_registry = MagicMock()
        mock_registry.get.return_value = mock_agent

        async def go() -> None:
            await poll_tick(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                max_concurrent=5,
                shutdown_event=asyncio.Event(),
            )

        _run(go())

        assert "500" in state.running
        assert "501" in state.running

    # -- AC: last_attempted_at recorded after dispatch -----------------------

    def test_last_attempted_at_recorded_after_dispatch(self) -> None:
        """After dispatching a task, poll_tick must record
        last_attempted_at[task_id] with a timestamp close to now."""
        from owlbear.daemon import OrchestratorState, poll_tick

        state = OrchestratorState()

        now = datetime.now(UTC)
        todo_tasks = [
            {"id": "600", "title": "Record me", "priority": "important", "updated": _ts(now)},
        ]

        mock_kanban = AsyncMock()
        mock_kanban.kanban_list.return_value = _make_kanban_list_json(todo_tasks)
        mock_kanban.kanban_show.return_value = _make_kanban_show_json("600")
        mock_kanban.kanban_move.return_value = "moved"

        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(return_value=MagicMock(data="done"))
        mock_registry = MagicMock()
        mock_registry.get.return_value = mock_agent

        async def go() -> None:
            await poll_tick(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                max_concurrent=3,
                shutdown_event=asyncio.Event(),
            )

        before = datetime.now(UTC)
        _run(go())
        after = datetime.now(UTC)

        assert "600" in state.last_attempted_at
        recorded = state.last_attempted_at["600"]
        assert before <= recorded <= after

    # -- AC: retry dispatch also records last_attempted_at -------------------

    def test_retry_dispatch_records_last_attempted_at(self) -> None:
        """When a task is re-dispatched via the retry path (step 3),
        last_attempted_at[task_id] must also be recorded."""
        from owlbear.daemon import OrchestratorState, RetryEntry, poll_tick

        state = OrchestratorState()

        # A retry entry that is due NOW
        past_due = datetime.now(UTC) - timedelta(seconds=1)
        state.retries = {
            "800": RetryEntry(task_id="800", attempt=1, next_due=past_due, last_error="prev fail"),
        }
        state.claimed.add("800")

        mock_kanban = AsyncMock()
        # No new todo tasks — only the retry fires
        mock_kanban.kanban_list.return_value = "[]"
        mock_kanban.kanban_show.return_value = _make_kanban_show_json("800", title="Retry target")
        mock_kanban.kanban_move.return_value = "moved"

        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(return_value=MagicMock(data="done"))
        mock_registry = MagicMock()
        mock_registry.get.return_value = mock_agent

        before = datetime.now(UTC)

        async def go() -> None:
            await poll_tick(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                max_concurrent=3,
                shutdown_event=asyncio.Event(),
            )

        _run(go())
        after = datetime.now(UTC)

        # Task must be in running (dispatched via retry)
        assert "800" in state.running
        # last_attempted_at must be recorded for retry-dispatched tasks too
        assert "800" in state.last_attempted_at, (
            "Retry dispatch did not record last_attempted_at — "
            "only fresh dispatch (step 7) does currently"
        )
        recorded = state.last_attempted_at["800"]
        assert before <= recorded <= after

    # -- Edge: mix of skipped and dispatched in same tick --------------------

    def test_mixed_skip_and_dispatch(self) -> None:
        """When multiple todo tasks exist, only those with no new activity
        are skipped; others are dispatched normally."""
        from owlbear.daemon import OrchestratorState, poll_tick

        state = OrchestratorState()
        now = datetime.now(UTC)

        # Task 700: attempted 10m ago, updated 20m ago -> SKIP
        # Task 701: never attempted -> DISPATCH
        # Task 702: attempted 10m ago, updated 5m ago -> DISPATCH
        state.last_attempted_at = {
            "700": now - timedelta(minutes=10),
            "702": now - timedelta(minutes=10),
        }

        todo_tasks = [
            {
                "id": "700",
                "title": "Stale",
                "priority": "important",
                "updated": _ts(now - timedelta(minutes=20)),
            },
            {
                "id": "701",
                "title": "New",
                "priority": "important",
                "updated": _ts(now - timedelta(minutes=1)),
            },
            {
                "id": "702",
                "title": "Updated",
                "priority": "important",
                "updated": _ts(now - timedelta(minutes=5)),
            },
        ]

        mock_kanban = AsyncMock()
        mock_kanban.kanban_list.return_value = _make_kanban_list_json(todo_tasks)
        mock_kanban.kanban_show.side_effect = [
            _make_kanban_show_json("701"),
            _make_kanban_show_json("702"),
        ]
        mock_kanban.kanban_move.return_value = "moved"

        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(return_value=MagicMock(data="done"))
        mock_registry = MagicMock()
        mock_registry.get.return_value = mock_agent

        async def go() -> None:
            await poll_tick(
                state=state,
                kanban=mock_kanban,
                agent_registry=mock_registry,
                max_concurrent=5,
                shutdown_event=asyncio.Event(),
            )

        _run(go())

        assert "700" not in state.running
        assert "701" in state.running
        assert "702" in state.running
