"""Failing tests for HookWorkerSupervisor.

Covers: owned _background_tasks set and _bg_semaphore, schedule() strong-reference
lifecycle, semaphore-bounded concurrency, and shutdown() cancel/drain contract.

All tests fail on current HEAD because
``src/owlbear/core/hook_worker_supervisor.py`` does not yet exist.
"""

from __future__ import annotations

import asyncio

import pytest

from owlbear.core.hook_worker_supervisor import HookWorkerSupervisor

# ---------------------------------------------------------------------------
# Ownership — _background_tasks and _bg_semaphore
# ---------------------------------------------------------------------------


class TestFromAC_HookWorkerSupervisorOwnership:
    """HookWorkerSupervisor owns _background_tasks: set[Task] and _bg_semaphore: Semaphore."""

    def test_owns_background_tasks_set(self) -> None:
        supervisor = HookWorkerSupervisor(bg_concurrency=1)
        assert isinstance(supervisor._background_tasks, set)

    def test_owns_bg_semaphore(self) -> None:
        supervisor = HookWorkerSupervisor(bg_concurrency=1)
        assert isinstance(supervisor._bg_semaphore, asyncio.Semaphore)

    def test_bg_semaphore_reflects_concurrency_param(self) -> None:
        supervisor = HookWorkerSupervisor(bg_concurrency=3)
        # Semaphore internal _value equals the initial concurrency count
        assert supervisor._bg_semaphore._value == 3

    def test_default_bg_concurrency_is_one(self) -> None:
        """Default concurrency must be 1 (matches research recommendation)."""
        supervisor = HookWorkerSupervisor()
        assert supervisor._bg_semaphore._value == 1

    def test_background_tasks_starts_empty(self) -> None:
        supervisor = HookWorkerSupervisor(bg_concurrency=1)
        assert len(supervisor._background_tasks) == 0


# ---------------------------------------------------------------------------
# schedule() — strong reference and done-callback cleanup
# ---------------------------------------------------------------------------


class TestFromAC_HookWorkerSupervisorSchedule:
    """schedule(coro) keeps a strong reference until done, then discards the task."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_schedule_adds_task_to_background_tasks_while_running(self) -> None:
        """Task is tracked in _background_tasks while the coroutine is still running."""
        supervisor = HookWorkerSupervisor(bg_concurrency=1)
        running = asyncio.Event()
        release = asyncio.Event()

        async def slow_worker() -> None:
            running.set()
            await release.wait()

        supervisor.schedule(slow_worker())
        await asyncio.wait_for(running.wait(), timeout=1.0)

        # Strong reference must exist while the coroutine is running
        assert len(supervisor._background_tasks) >= 1

        release.set()
        await asyncio.sleep(0.05)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_done_callback_removes_task_after_completion(self) -> None:
        """After the coroutine finishes, done callback removes the task from the set."""
        supervisor = HookWorkerSupervisor(bg_concurrency=1)
        finished = asyncio.Event()

        async def quick_worker() -> None:
            finished.set()

        supervisor.schedule(quick_worker())
        await asyncio.wait_for(finished.wait(), timeout=1.0)
        await asyncio.sleep(0.05)  # allow done callback to run

        assert len(supervisor._background_tasks) == 0

    @pytest.mark.asyncio(loop_scope="function")
    async def test_schedule_multiple_tasks_all_tracked(self) -> None:
        """Multiple concurrent tasks are all held in _background_tasks simultaneously."""
        supervisor = HookWorkerSupervisor(bg_concurrency=2)
        both_running = asyncio.Event()
        release = asyncio.Event()
        running_count = [0]

        async def worker() -> None:
            running_count[0] += 1
            if running_count[0] == 2:
                both_running.set()
            await release.wait()

        supervisor.schedule(worker())
        supervisor.schedule(worker())
        await asyncio.wait_for(both_running.wait(), timeout=1.0)

        assert len(supervisor._background_tasks) == 2

        release.set()
        await asyncio.sleep(0.05)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_done_callback_cleans_up_each_task_independently(self) -> None:
        """Each completed task is individually removed from _background_tasks."""
        supervisor = HookWorkerSupervisor(bg_concurrency=2)
        first_done, second_done = asyncio.Event(), asyncio.Event()
        release_second = asyncio.Event()

        async def first_worker() -> None:
            first_done.set()

        async def second_worker() -> None:
            await release_second.wait()
            second_done.set()

        supervisor.schedule(first_worker())
        supervisor.schedule(second_worker())

        await asyncio.wait_for(first_done.wait(), timeout=1.0)
        await asyncio.sleep(0.05)

        # First is done; second is still running
        assert len(supervisor._background_tasks) == 1

        release_second.set()
        await asyncio.wait_for(second_done.wait(), timeout=1.0)
        await asyncio.sleep(0.05)

        assert len(supervisor._background_tasks) == 0


# ---------------------------------------------------------------------------
# Semaphore — concurrency bounds
# ---------------------------------------------------------------------------


class TestFromAC_HookWorkerSupervisorSemaphore:
    """_bg_semaphore bounds worker critical sections as specified by bg_concurrency."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_concurrency_1_workers_do_not_overlap(self) -> None:
        """bg_concurrency=1: second worker does not start until first finishes."""
        supervisor = HookWorkerSupervisor(bg_concurrency=1)

        inside = []
        first_holding = asyncio.Event()
        release_first = asyncio.Event()

        async def first_worker() -> None:
            inside.append("first_start")
            first_holding.set()
            await release_first.wait()
            inside.append("first_end")

        async def second_worker() -> None:
            inside.append("second_start")
            inside.append("second_end")

        supervisor.schedule(first_worker())
        supervisor.schedule(second_worker())

        await asyncio.wait_for(first_holding.wait(), timeout=1.0)
        await asyncio.sleep(0)  # give second a chance — it must not start yet

        assert "second_start" not in inside
        assert "first_start" in inside

        release_first.set()
        await asyncio.sleep(0.1)

        assert inside == ["first_start", "first_end", "second_start", "second_end"]

    @pytest.mark.asyncio(loop_scope="function")
    async def test_concurrency_2_allows_two_workers_to_overlap(self) -> None:
        """bg_concurrency=2: two workers may run concurrently inside critical sections."""
        supervisor = HookWorkerSupervisor(bg_concurrency=2)

        inside: set[str] = set()
        both_inside = asyncio.Event()
        release = asyncio.Event()

        async def worker(name: str) -> None:
            inside.add(name)
            if len(inside) == 2:  # exactly two workers
                both_inside.set()
            await release.wait()
            inside.discard(name)

        supervisor.schedule(worker("w1"))
        supervisor.schedule(worker("w2"))

        await asyncio.wait_for(both_inside.wait(), timeout=1.0)
        # Both are running concurrently — semaphore allowed this
        assert len(inside) == 2  # two workers overlapping

        release.set()
        await asyncio.sleep(0.05)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_all_scheduled_workers_complete_with_concurrency_2(self) -> None:
        """All scheduled workers still complete regardless of semaphore bound."""
        supervisor = HookWorkerSupervisor(bg_concurrency=2)
        completed: list[int] = []

        async def worker(i: int) -> None:
            await asyncio.sleep(0.001)
            completed.append(i)

        for i in range(4):
            supervisor.schedule(worker(i))

        await asyncio.sleep(0.2)
        assert len(completed) == 4  # all four workers completed
        assert sorted(completed) == [0, 1, 2, 3]


# ---------------------------------------------------------------------------
# shutdown() — signal, cancel, drain, empty set
# ---------------------------------------------------------------------------


class TestFromAC_HookWorkerSupervisorShutdown:
    """shutdown() cancels unfinished tasks, drains, and leaves _background_tasks empty."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_shutdown_cancels_unfinished_task(self) -> None:
        """Unfinished tasks receive CancelledError during shutdown()."""
        supervisor = HookWorkerSupervisor(bg_concurrency=1)
        was_cancelled = asyncio.Event()

        async def hanging_worker() -> None:
            try:
                await asyncio.sleep(100)
            except asyncio.CancelledError:
                was_cancelled.set()
                raise

        supervisor.schedule(hanging_worker())
        await asyncio.sleep(0.05)  # let task start

        await supervisor.shutdown()

        assert was_cancelled.is_set()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_shutdown_leaves_background_tasks_empty(self) -> None:
        """_background_tasks is empty after shutdown() returns."""
        supervisor = HookWorkerSupervisor(bg_concurrency=1)

        async def hanging_worker() -> None:
            await asyncio.sleep(100)

        supervisor.schedule(hanging_worker())
        await asyncio.sleep(0.05)

        await supervisor.shutdown()

        assert len(supervisor._background_tasks) == 0

    @pytest.mark.asyncio(loop_scope="function")
    async def test_shutdown_awaits_cleanup_before_returning(self) -> None:
        """shutdown() returns only after all tracked tasks have been cleaned up."""
        supervisor = HookWorkerSupervisor(bg_concurrency=1)
        cleanup_order: list[str] = []

        async def hanging_worker() -> None:
            try:
                await asyncio.sleep(100)
            except asyncio.CancelledError:
                cleanup_order.append("task_cleaned")
                raise

        supervisor.schedule(hanging_worker())
        await asyncio.sleep(0.05)

        await supervisor.shutdown()
        cleanup_order.append("shutdown_returned")

        # Task cleanup must happen before shutdown returns
        assert cleanup_order[0] == "task_cleaned"
        assert cleanup_order[1] == "shutdown_returned"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_shutdown_with_no_tracked_tasks_returns_immediately(self) -> None:
        """shutdown() on a supervisor with no active tasks returns without hanging."""
        supervisor = HookWorkerSupervisor(bg_concurrency=1)
        await asyncio.wait_for(supervisor.shutdown(), timeout=1.0)
        assert len(supervisor._background_tasks) == 0

    @pytest.mark.asyncio(loop_scope="function")
    async def test_shutdown_multiple_unfinished_tasks_all_cancelled(self) -> None:
        """All unfinished tasks are cancelled, not just the first one."""
        supervisor = HookWorkerSupervisor(bg_concurrency=3)
        cancelled_count = [0]

        async def hanging_worker() -> None:
            try:
                await asyncio.sleep(100)
            except asyncio.CancelledError:
                cancelled_count[0] += 1
                raise

        for _ in range(3):
            supervisor.schedule(hanging_worker())

        await asyncio.sleep(0.05)

        await supervisor.shutdown()

        assert cancelled_count[0] == 3  # all three workers cancelled
        assert len(supervisor._background_tasks) == 0

    @pytest.mark.asyncio(loop_scope="function")
    async def test_shutdown_signal_prevents_new_schedules(self) -> None:
        """After shutdown(), schedule() must not start new background work.

        The AC requires shutdown() to set a supervisor shutdown signal.  The
        observable contract is that subsequent schedule() calls are no-ops —
        they must not enqueue or execute new coroutines after shutdown.
        """
        supervisor = HookWorkerSupervisor(bg_concurrency=1)
        await supervisor.shutdown()

        ran = asyncio.Event()

        async def probe_worker() -> None:
            ran.set()

        supervisor.schedule(probe_worker())
        await asyncio.sleep(0.05)  # give the event loop time to dispatch any new task

        assert not ran.is_set(), "schedule() after shutdown() must not run new background work"
