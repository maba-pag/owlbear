"""The actual synchronous SDK caller cannot wait forever for a cancellation-resistant asynchronous request."""

import json
import os
import subprocess
import sys

import pytest

CHILD = """
import asyncio
import dataclasses
import json
import sys
import threading
import time
from pathlib import Path

from owlbear_delivery_next.change_contracts import tools
from owlbear_delivery_next.change_contracts.models import StepKind
from owlbear_delivery_next.change_contracts.permissions import Policy
from owlbear_delivery_next.local_system.processes import Termination
from owlbear_delivery_next.runtimes import sdk_adapter
from owlbear_delivery_next.runtimes.session_result import Run
from owlbear_delivery_next.state_store.store import Store
from owlbear_delivery_next.workflow_steps import sessions

root, mode = Path(sys.argv[1]), sys.argv[2]
owner = sys.modules.get("owlbear_delivery_next.runtimes.loop_owner")
if owner is not None:
    owner.SHUTDOWN = 0.05
    owner.RETRY = 0.01
calls, cancels = 0, 0
executor_done = threading.Event()

class PrimaryError(RuntimeError):
    pass

async def stubborn():
    global cancels
    while True:
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            cancels += 1

async def cooperative():
    await asyncio.Event().wait()

async def fake(cfg):
    global calls
    calls += 1
    if mode == "synchronous":
        started = asyncio.Event()
        loop = asyncio.get_running_loop()
        def work():
            loop.call_soon_threadsafe(started.set)
            time.sleep(0.1)
            executor_done.set()
        asyncio.create_task(asyncio.to_thread(work))
        await started.wait()
    elif mode == "cooperative":
        asyncio.create_task(cooperative())
        await asyncio.sleep(0)
    elif mode != "clean":
        task = asyncio.create_task(stubborn(), name="stubborn-request")
        await asyncio.sleep(0)
        for _ in range(2):
            task.cancel()
            await asyncio.sleep(0)
    if mode == "primary":
        raise PrimaryError("synthetic primary")
    return Run(
        cfg.session_id, "result", payload=tools.BuildResult(summary="kept", checks=[]),
        usage={"input_tokens": 7}, pids={4242: 1.0}, termination=Termination(confirmed=True),
        model_check="verified",
    )

sdk_adapter.run = fake
sessions.GRANT = 1
cfg = sdk_adapter.Session(
    kind=StepKind.BUILD, worktree=root, session_id="synthetic-owner", message="Synthetic work", resume=False,
    policy=Policy(root), observe=lambda: tools.Worktree("", ""), checks=(), model="synthetic-model",
)
print("READY", flush=True)
started = time.monotonic()
try:
    runs = (
        sessions._waves([cfg, dataclasses.replace(cfg, session_id="second")], lambda _: None)
        if mode == "wave" else [sessions.run(Store(root / "store"), cfg)]
    )
    result = {
        "confirmed": [run.termination.confirmed for run in runs],
        "problems": [list(run.termination.problems) for run in runs],
        "spent": sum(run.usage.get("input_tokens", 0) for run in runs),
        "payload": runs[0].payload.summary,
        "pids": runs[0].pids,
        "not_run": mode == "wave" and runs[1].detail == sessions.NOT_RUN,
        "executor_done": executor_done.is_set(),
    }
except PrimaryError as error:
    result = {"error": str(error), "notes": getattr(error, "__notes__", [])}
result.update(elapsed=time.monotonic() - started, calls=calls, cancels=cancels)
print(json.dumps(result))
"""


@pytest.mark.parametrize("mode", ["clean", "cooperative", "synchronous", "stubborn", "wave", "primary"])
def test_synchronous_sdk_boundary_stays_bounded_and_keeps_its_real_accounting(tmp_path, mode):
    environment = os.environ | {"HOME": str(tmp_path), "OWLBEAR_HOME": str(tmp_path / "home")}
    result = subprocess.run(  # noqa: S603 - fixed synthetic child, never a real SDK/provider
        [sys.executable, "-c", CHILD, str(tmp_path), mode],
        env=environment,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    lines = result.stdout.splitlines()
    assert lines[0] == "READY"
    proof = json.loads(lines[1])
    assert proof["elapsed"] < 1.0
    assert proof["calls"] == 1
    if mode == "primary":
        assert proof["error"] == "synthetic primary"
        assert any("asynchronous shutdown" in note for note in proof["notes"])
    else:
        assert proof["spent"] == 7
        assert proof["payload"] == "kept"
        assert proof["pids"] == {"4242": 1.0}
        assert proof["confirmed"][0] is (mode in {"clean", "cooperative", "synchronous"})
        if mode == "synchronous":
            assert proof["executor_done"]
        if mode in {"stubborn", "wave"}:
            assert any("asynchronous shutdown" in problem for problem in proof["problems"][0])
            assert proof["cancels"] >= 2
        if mode == "wave":
            assert proof["not_run"]
            assert proof["confirmed"][1] is True
