import subprocess
import sys
from datetime import UTC, datetime, timedelta

import pytest

from owlbear_delivery_next import cli, host
from owlbear_delivery_next.host import Host, RunnerRecord
from owlbear_delivery_next.loop import StepResult, apply
from owlbear_delivery_next.models import (
    Answer,
    AnswerItem,
    Change,
    CheckResult,
    Environment,
    Exit,
    Inputs,
    IntentItem,
    Names,
    PersonCheck,
    Plan,
    Profile,
    ProfileEntry,
    Question,
    Step,
    StepKind,
    Task,
)
from owlbear_delivery_next.process_probe import WorktreeProcessScanError
from owlbear_delivery_next.status import Activity, status
from owlbear_delivery_next.steps import check
from owlbear_delivery_next.store import Store

NOW = datetime(2026, 10, 10, 12, tzinfo=UTC)
HOLD = """\
import os, sys
from pathlib import Path
from owlbear_delivery_next.host import HostRecord
from owlbear_delivery_next.storage_io import open_lock
from owlbear_delivery_next.store import Store
root = Store.open(Path(sys.argv[1])).root
fd = open_lock(os.open(root, os.O_RDONLY), blocking=False, name="host.lock")
record = HostRecord(url="http://127.0.0.1:9/", token="t", pid=os.getpid(), started_at="2026-10-10T12:00:00Z")
(root / "host.json").write_text(record.model_dump_json())
print("held", flush=True)
sys.stdin.read()
"""


@pytest.fixture
def store(tmp_path):
    for args in (
        ["init", "-q"],
        ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "i"],
    ):
        subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)  # noqa: S603, S607
    return Store.open(tmp_path)


class Fake:
    """Process seams: spawned runners stay alive until ended; the worktree scan reports what a test puts there."""

    def __init__(self, store, tmp_path):
        self.live, self.found, self.groups, self.pid = set(), {}, {}, 100
        (tmp_path / "wt").mkdir(exist_ok=True)
        self.worktree = str(tmp_path / "wt")
        self.host = Host(store, tmp_path, spawn=self.spawn, scan=self.scan, group=lambda g: self.groups.get(g, {}))
        self.host.alive = lambda pid, _created: pid in self.live

    def spawn(self, _slug):
        self.pid += 1
        self.live.add(self.pid)
        return RunnerRecord(pid=self.pid, created=1.0, started_at=NOW)

    def scan(self, _path, _since):
        if self.found is None:
            raise WorktreeProcessScanError
        return self.found


def save(store, change):
    with store.lock(change.slug) as lock:
        store.write(lock, change)


def asking(fake):
    plan = Plan(tasks=[Task(id="t1", title="greet", checks=["npm test"])])
    c = Change(slug="c1", plan=plan, step=Step(kind=StepKind.BUILD, task="t1"), names=Names(worktree=fake.worktree))
    return apply(c, StepResult(exit=Exit.ASK, question=Question(step=StepKind.BUILD, text="language?")), NOW)


def test_the_inbox_is_folded_before_a_waiting_change_is_skipped_and_one_runner_starts(store, tmp_path):
    fake = Fake(store, tmp_path)
    save(store, asking(fake))
    assert fake.host.tick(NOW) == []
    store.put_inbox("c1", AnswerItem(at=NOW, question="q1", text="German"))
    assert fake.host.tick(NOW) == ["c1"]
    assert store.read("c1").outcome is None
    store.put_inbox("c1", IntentItem(at=NOW, intent="resume"))
    assert fake.host.tick(NOW) == []
    assert fake.host.runner("c1").pid == 101


def test_no_writer_starts_until_the_former_runner_and_its_processes_are_gone(store, tmp_path):
    fake = Fake(store, tmp_path)
    save(store, asking(fake).model_copy(update={"outcome": None}))
    assert fake.host.tick(NOW) == ["c1"]
    fake.live.clear()
    fake.found, fake.groups = {4242: "sleep"}, {101: {4243: "copilot"}}
    assert fake.host.tick(NOW) == []
    blocked = store.read("c1").blocked
    assert blocked.action == "End processes 4242, 4243"
    assert "4242 (sleep)" in status(store.read("c1"), Activity(host_up=True), NOW).line
    fake.groups = {}
    fake.found = None
    assert fake.host.tick(NOW) == []
    assert store.read("c1").blocked.reason == "the process table could not be scanned"
    fake.found = {}
    assert fake.host.tick(NOW) == ["c1"]
    assert store.read("c1").blocked is None


def test_recorded_pids_of_the_runner_block_until_gone(store, tmp_path):
    fake = Fake(store, tmp_path)
    save(store, asking(fake).model_copy(update={"outcome": None}))
    fake.host.tick(NOW)
    with store.lock("c1") as lock:
        store.log(lock, "c1", {"event": "pids", "at": NOW.isoformat(), "pids": {"777": 1.0}})
    fake.live = {777}
    assert fake.host.tick(NOW) == []
    assert "777" in store.read("c1").blocked.action
    fake.live.clear()
    assert fake.host.tick(NOW) == ["c1"]


def test_a_merged_pr_is_observed_before_a_paused_waiting_change_is_skipped(store, tmp_path):
    fake = Fake(store, tmp_path)
    save(store, asking(fake))
    store.put_inbox("c1", IntentItem(at=NOW, intent="pause"))
    assert fake.host.tick(NOW) == []
    fake.host.pr_states["c1"] = "merged"
    assert fake.host.tick(NOW) == ["c1"]
    assert store.read("c1").step.kind == StepKind.CLEANUP


def test_host_lock_excludes_a_second_host_and_status_shows_host_down(store, tmp_path, capsys):
    save(store, Change(slug="c1", step=Step(kind=StepKind.BUILD)))
    child = subprocess.Popen(  # noqa: S603
        [sys.executable, "-c", HOLD, str(tmp_path)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True
    )
    try:
        assert child.stdout.readline().strip() == "held"
        assert host.serve(tmp_path) == 0
        assert "already running: http://127.0.0.1:9/" in capsys.readouterr().out
        assert host.running(store).pid == child.pid
        assert "Delivery is not running" not in cli.show_status(store, NOW)
    finally:
        child.kill()
        child.wait()
    assert host.running(store) is None
    assert cli.show_status(store, NOW).splitlines() == [
        "Delivery is not running — run `owlbear-next host`",
        "c1: Build · Delivery is not running",
        "  next: Start Delivery (run `owlbear-next host`)",
    ]


def checking(**env):
    person = PersonCheck(id="preview", steps=["open the preview"])
    e = Environment(check="preview", command="npm run preview", directory=".", ready_url="http://127.0.0.1:4173/")
    plan = Plan(tasks=[Task(id="t1", title="greet", done=True)])
    step = Step(kind=StepKind.CHECK, task="preview")
    return Change(slug="c1", plan=plan, checks=[person], step=step, env=e.model_copy(update=env))


def answered(c, at, *, passed=True):
    c.checks[0].answer = Answer(at=at, passed=passed, text="no greeting", inputs=Inputs())
    return c


@pytest.mark.parametrize(
    ("change", "live", "expected"),
    [
        (checking(), False, "launch"),
        (checking(ready_at=NOW), True, "keep"),
        (checking(ready_at=NOW), False, "launch"),
        (answered(checking(ready_at=NOW), NOW - timedelta(minutes=1)), True, "keep"),
        (answered(checking(ready_at=NOW), NOW), True, "settle"),
        (checking(ready_at=NOW).model_copy(update={"step": Step(kind=StepKind.BUILD, task="t2")}), True, "dispose"),
        (checking(ready_at=NOW).model_copy(update={"finished_at": NOW}), True, "dispose"),
        (Change(slug="c1"), True, None),
    ],
)
def test_check_environment_decisions(change, live, expected):
    assert check.action(change, live=live) == expected


def test_a_failed_check_goes_back_to_build_with_the_owners_note():
    c = answered(checking(ready_at=NOW), NOW, passed=False)
    after = apply(c, check.settle(c, NOW), NOW)
    assert (after.step.kind, after.step.task, after.plan.tasks[-1].origin) == (StepKind.BUILD, "t2", "person-check")
    assert "no greeting" in after.plan.tasks[-1].title


def test_the_environment_launches_after_the_builder_is_gone_and_is_disposed_on_the_result(store, tmp_path, monkeypatch):
    fake = Fake(store, tmp_path)
    disposed, launched = [], []
    monkeypatch.setattr(check, "dispose", lambda pids: disposed.append(dict(pids)) or ())
    monkeypatch.setattr(check, "launch", lambda e, _root, _log: launched.append(e.command) or {900: 2.0})
    entry = ProfileEntry(state="known", value="npm run preview")
    store.write_profile(Profile(version=1, entries={"allow:check": entry}))
    c = checking()
    c.names.worktree = fake.worktree
    save(store, c)
    (store.root / "changes" / "c1" / "runner.json").write_text(
        RunnerRecord(pid=5, created=1.0, started_at=NOW).model_dump_json()
    )
    fake.found = {55: "vite"}
    assert fake.host.tick(NOW) == []
    assert launched == []
    fake.found = {}
    assert fake.host.tick(NOW) == []
    assert launched == ["npm run preview"]
    waiting = store.read("c1")
    assert (waiting.outcome.who, waiting.env.pids) == ("you", {900: 2.0})
    fake.live.add(900)
    store.put_inbox("c1", CheckResult(at=datetime.now(UTC), check="preview", passed=True, inputs=Inputs(procedure=1)))
    assert fake.host.tick() == ["c1"]
    assert disposed[-1] == {900: 2.0}
    done = store.read("c1")
    assert (done.env, done.step.kind) == (None, StepKind.MERGE)
