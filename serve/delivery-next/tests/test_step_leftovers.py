"""A step's leftovers found by hierarchy (#752): what its commands marked blocks, an unrelated process never does."""

import contextlib
import os
import signal
import subprocess
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import psutil
import pytest

from owlbear_delivery_next.change_contracts.models import Change, Exit, Names, Plan, Question, Step, StepKind, Task
from owlbear_delivery_next.change_flow.loop import StepResult, apply
from owlbear_delivery_next.local_system import processes
from owlbear_delivery_next.project_host.host import Host, RunnerRecord
from owlbear_delivery_next.runtimes import command_marks
from owlbear_delivery_next.state_store import step_pids
from owlbear_delivery_next.state_store.store import Store

SLEEP = "sleep 300 >/dev/null 2>&1"


@pytest.fixture
def store(tmp_path):
    for args in (
        ["init", "-q"],
        ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "i"],
    ):
        subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)  # noqa: S603, S607
    return Store.open(tmp_path)


def runnable(store: Store, tmp_path: Path, slug: str = "c1", ago: float = 10) -> Path:
    """A Change whose step started *ago* seconds ago and may run again; its worktree."""
    work = tmp_path / f"{slug}-wt"
    work.mkdir()
    plan = Plan(tasks=[Task(id="t1", title="greet", checks=["npm test"])])
    started = datetime.now(UTC) - timedelta(seconds=ago)
    step = Step(kind=StepKind.BUILD, task="t1", started_at=started)
    c = Change(slug=slug, plan=plan, step=step, names=Names(worktree=str(work)))
    c = apply(c, StepResult(exit=Exit.ASK, question=Question(step=StepKind.BUILD, text="language?")), started)
    c.outcome, c.step.started_at = None, started
    with store.lock(slug) as lock:
        store.write(lock, c)
    return work


def host(store: Store, tmp_path: Path, said: list[str]) -> Host:
    """A host with the real process seams; its runners are only recorded."""
    h = Host(store, tmp_path, spawn=lambda _s: RunnerRecord(pid=2**22 + 1, created=1.0, started_at=datetime.now(UTC)))
    h.say = said.append
    return h


def marked(store: Store, *, wrapped: bool = False) -> int:
    """Run a shell command marked as c1's runner marks it, leaving a sleep behind; the sleep's pid."""
    with store.lock("c1") as lock, command_marks.marking(store, lock, "c1"):
        script = command_marks.folder(store, "c1") / command_marks.SCRIPT
        argv = ["/bin/bash", "-c", f'. "{script}"; {SLEEP} & echo $!']
        if wrapped:  # bash runs in its parent's new session, so its own pid names no group
            wrapper = "import subprocess, sys; sys.exit(subprocess.run(sys.argv[1:]).returncode)"
            argv = [sys.executable, "-c", wrapper, *argv]
        out = subprocess.run(argv, check=True, capture_output=True, text=True, timeout=30, start_new_session=True)  # noqa: S603
    return int(out.stdout.split()[-1])


def end(pid: int) -> None:
    with contextlib.suppress(OSError):
        os.kill(pid, signal.SIGKILL)
    limit = time.monotonic() + 10
    while processes.alive(pid, None) and time.monotonic() < limit:
        time.sleep(0.05)


def test_an_unrelated_process_in_the_worktree_never_blocks(store, tmp_path) -> None:
    work = runnable(store, tmp_path)
    ended = subprocess.Popen(["true"])  # noqa: S607 - the last step's runner, gone
    created = psutil.Process(ended.pid).create_time()
    ended.wait()
    rec = RunnerRecord(pid=ended.pid, created=created, started_at=datetime.now(UTC) - timedelta(seconds=10))
    (store.root / "changes" / "c1" / "runner.json").write_text(rec.model_dump_json())
    argv = ["/bin/sh", "-c", f'cd "{work}"; {SLEEP} & echo $!']
    other = subprocess.run(argv, check=True, capture_output=True, text=True, timeout=10, start_new_session=True)  # noqa: S603
    sleep = int(other.stdout.split()[-1])  # e.g. a Terminal the owner opened in the worktree
    try:
        assert psutil.Process(sleep).cwd() == str(work.resolve())
        assert host(store, tmp_path, []).tick() == ["c1"]
        assert store.read("c1").blocked is None
    finally:
        end(sleep)


@pytest.mark.parametrize("wrapped", [False, True], ids=["own-session", "setsid-wrapper"])
def test_a_marked_command_left_behind_blocks_until_it_ends(store, tmp_path, wrapped) -> None:
    runnable(store, tmp_path)
    sleep = marked(store, wrapped=wrapped)
    try:
        said: list[str] = []
        assert host(store, tmp_path, said).tick() == []
        blocked = store.read("c1").blocked
        assert (blocked.action, f"{sleep} (sleep)" in blocked.reason) == (f"End processes {sleep}", True)
        end(sleep)
        assert host(store, tmp_path, said).tick() == ["c1"]
        assert store.read("c1").blocked is None
    finally:
        end(sleep)


def test_marks_of_another_change_or_before_the_step_do_not_count(store, tmp_path) -> None:
    live = subprocess.Popen(["sleep", "300"], start_new_session=True)  # noqa: S607 - a group marked as it started
    try:
        mark = f"{live.pid} {time.strftime(command_marks.LSTART, time.gmtime())}\n"
        runnable(store, tmp_path, "c2")
        time.sleep(3.1)  # marks are whole seconds, kept from 1 s before the step: c1's step starts after this one
        runnable(store, tmp_path, ago=0)
        (command_marks.folder(store, "c2") / command_marks.FILE).write_text(mark)
        (command_marks.folder(store, "c1") / command_marks.FILE).write_text(mark)
        assert host(store, tmp_path, []).tick() == ["c1"]
        assert (store.read("c1").blocked, store.read("c2").blocked.action) == (None, f"End processes {live.pid}")
    finally:
        live.kill()
        live.wait()


@pytest.mark.parametrize(
    ("field", "shown"),
    [("name", "{pid} (name unreadable: "), ("status", "{pid} (sleep; status unreadable: "),
     ("create_time", "{pid} (sleep; start time unreadable: ")],
)  # fmt: skip
def test_an_unreadable_member_is_named_with_what_failed(store, tmp_path, monkeypatch, field, shown) -> None:
    runnable(store, tmp_path)
    sleep = marked(store)
    read = getattr(psutil.Process, field)

    def denied(self, *a, **kw):
        if self.pid == sleep:
            raise psutil.AccessDenied(self.pid)
        return read(self, *a, **kw)

    try:
        said: list[str] = []
        with monkeypatch.context() as m:
            m.setattr(psutil.Process, field, denied)
            assert host(store, tmp_path, said).tick() == []
        reason = store.read("c1").blocked.reason
        detail = shown.format(pid=sleep) + f"AccessDenied: (pid={sleep})"
        assert detail in reason
        assert any(detail in line for line in said)
    finally:
        end(sleep)


def _no_table():
    raise psutil.AccessDenied


def _no_group(_pid):
    raise PermissionError(1, "Operation not permitted")


@pytest.mark.parametrize(
    ("what", "detail"),
    [
        ("table", "the step's processes could not be looked for: the process table could not be listed: "),
        ("group", "its group or session could not be read: [Errno 1] Operation not permitted"),
        ("marks", "the step's command marks could not be read: [Errno 21] Is a directory"),
        ("pids", "the step's recorded processes could not be read: [Errno 21] Is a directory"),
    ],
)
def test_unreadable_marks_or_table_block_with_their_details(store, tmp_path, monkeypatch, what, detail) -> None:
    runnable(store, tmp_path)
    marks = command_marks.folder(store, "c1") / command_marks.FILE
    if what == "pids":
        (command_marks.folder(store, "c1") / step_pids.FILE).mkdir()
    if what == "marks":
        marks.mkdir()
    else:
        marks.write_text(f"{2**22 + 2} {time.strftime(command_marks.LSTART, time.gmtime())}\n")
    said: list[str] = []
    with monkeypatch.context() as m:
        if what == "table":
            m.setattr(psutil, "pids", _no_table)
        if what == "group":
            m.setattr(os, "getpgid", _no_group)
        assert host(store, tmp_path, said).tick() == []
    assert detail in store.read("c1").blocked.reason
    assert any(detail in line for line in said)


def test_a_runner_runs_only_once_its_record_is_written(store, tmp_path, monkeypatch) -> None:
    ran = tmp_path / "ran"
    runner = tmp_path / "runner"
    runner.write_text(f'#!/bin/sh\necho "$@" > "{ran}"\n')
    runner.chmod(0o755)
    monkeypatch.setattr(sys, "executable", str(runner))
    (store.root / "changes" / "c1").mkdir(parents=True)
    h = Host(store, tmp_path)
    rec = h.spawn("c1")
    time.sleep(1.0)  # an unrecorded runner would have run by now
    assert not ran.exists()
    h._record("c1", rec)  # noqa: SLF001 - the write that lets the runner run
    end = time.monotonic() + 10
    while not ran.exists() and time.monotonic() < end:
        time.sleep(0.05)
    assert ran.read_text().startswith("-m owlbear_delivery_next run c1")
    assert RunnerRecord.model_validate_json((store.root / "changes" / "c1" / "runner.json").read_text()).pid == rec.pid


def test_a_runner_whose_host_dies_before_its_record_never_runs(store, tmp_path, monkeypatch) -> None:
    ran = tmp_path / "ran"
    runner = tmp_path / "runner"
    runner.write_text(f'#!/bin/sh\ntouch "{ran}"\n')
    runner.chmod(0o755)
    monkeypatch.setattr(sys, "executable", str(runner))
    (store.root / "changes" / "c1").mkdir(parents=True)
    h = Host(store, tmp_path)
    rec = h.spawn("c1")
    held = h.held.pop(rec.pid)
    held.stdin.close()  # what the host's death does to the pipe
    assert held.wait(10) != 0
    assert not ran.exists()
