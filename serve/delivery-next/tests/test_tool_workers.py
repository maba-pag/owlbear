"""Cancelled asyncio waiters do not release synchronous tool operations that can still run."""

import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from owlbear_delivery_next.change_contracts import tools
from owlbear_delivery_next.change_contracts.models import StepKind
from owlbear_delivery_next.change_contracts.permissions import Policy
from owlbear_delivery_next.local_system import processes
from owlbear_delivery_next.runtimes import sdk_adapter, sdk_teardown, tool_workers


@pytest.mark.parametrize("failed", [False, True])
def test_completed_tool_work_releases_its_lease_and_preserves_value_or_error(failed, caplog):
    async def scenario():
        workers = tool_workers.Workers()

        def operation():
            if failed:
                msg = "synthetic tool failure"
                raise ValueError(msg)
            return 7

        if failed:
            with pytest.raises(ValueError, match="synthetic tool failure"):
                await workers.call(operation)
            assert "ValueError" in caplog.text
        else:
            assert await workers.call(operation) == 7
        assert workers.count() == 0

    asyncio.run(scenario())


def test_cancelled_queued_work_is_revoked_even_if_the_executor_dispatches_it_later(monkeypatch):
    async def scenario():
        workers = tool_workers.Workers()
        captured, calls = [], []
        queued = asyncio.Event()

        async def delayed(operation):
            captured.append(operation)
            queued.set()
            await asyncio.Event().wait()

        monkeypatch.setattr(tool_workers.asyncio, "to_thread", delayed)
        task = asyncio.create_task(workers.call(lambda: calls.append("must not run")))
        await asyncio.wait_for(queued.wait(), 1)
        assert workers.count() == 1
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert workers.count() == 0
        with pytest.raises(asyncio.CancelledError):
            captured[0]()
        assert calls == []

    asyncio.run(scenario())


def test_cancelled_running_tool_retains_ownership_and_cannot_confirm_teardown(tmp_path, monkeypatch):
    async def scenario():
        loop = asyncio.get_running_loop()
        loop.set_default_executor(ThreadPoolExecutor(max_workers=1))
        cfg = sdk_adapter.Session(
            kind=StepKind.BUILD,
            worktree=tmp_path,
            session_id="synthetic-tool-owner",
            message="Synthetic",
            resume=False,
            policy=Policy(tmp_path),
            observe=lambda: tools.Worktree("", ""),
            checks=(),
            model="synthetic-model",
        )
        step = sdk_adapter._Step(cfg, loop)  # noqa: SLF001 - the actual teardown owner
        step.run.runtime_pid, step.run.pids = 4242, {4242: 1.0}
        started, release = asyncio.Event(), threading.Event()

        def operation():
            loop.call_soon_threadsafe(started.set)
            assert release.wait(5)

        class Client:
            async def stop(self):
                return None

        monkeypatch.setattr(step, "runtime", lambda _client: None)
        monkeypatch.setattr(processes, "alive", lambda *_args: False)
        monkeypatch.setattr(processes, "kill", lambda *_args: pytest.fail("no real signals in a synthetic test"))
        monkeypatch.setattr(sdk_teardown, "STOP_CALL", 0.001)
        monkeypatch.setattr(sdk_teardown, "SETTLE", 0.001)
        task = asyncio.create_task(step.workers.call(operation))
        try:
            await asyncio.wait_for(started.wait(), 1)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert step.workers.count() == 1
            termination = await sdk_teardown.teardown(Client(), None, step)
            assert not termination.confirmed
            assert any("tool worker" in problem for problem in termination.problems)
        finally:
            release.set()
            await loop.run_in_executor(None, lambda: None)
            await asyncio.gather(task, return_exceptions=True)
        assert step.workers.count() == 0

    asyncio.run(scenario())
