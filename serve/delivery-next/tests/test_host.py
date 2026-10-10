import subprocess
import sys
from datetime import UTC, datetime, timedelta

import pytest

from owlbear_delivery_next import cli, host
from owlbear_delivery_next.host import Host, RunnerRecord
from owlbear_delivery_next.loop import StepResult, apply, check_inputs
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
        assert "already running: http://127.0.0.1:9/#token=t\n" in capsys.readouterr().out
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


def answered(c, at, *, passed=True, inputs=None):
    inputs = check_inputs(c, c.checks[0], {}) if inputs is None else inputs
    c.checks[0].answer = Answer(at=at, passed=passed, text="no greeting", inputs=inputs)
    return c


@pytest.mark.parametrize(
    ("change", "live", "expected"),
    [
        (checking(), False, "launch"),
        (checking(), True, "launch"),  # spawned but never ready: relaunched, after disposal
        (checking(ready_at=NOW), True, "keep"),
        (checking(ready_at=NOW), False, "launch"),
        (answered(checking(ready_at=NOW), NOW - timedelta(minutes=1)), True, "settle"),  # given before a relaunch
        (answered(checking(ready_at=NOW), NOW, inputs=Inputs()), True, "keep"),  # stale inputs
        (checking(ready_at=NOW).model_copy(update={"step": Step(kind=StepKind.BUILD, task="t2")}), True, "dispose"),
        (checking(ready_at=NOW).model_copy(update={"finished_at": NOW}), True, "dispose"),
        (Change(slug="c1"), True, None),
    ],
)
def test_check_environment_decisions(change, live, expected):
    assert check.action(change, live=live, paths={}) == expected


def test_a_failed_check_goes_back_to_build_with_the_owners_note_and_settles_no_later_round():
    c = answered(checking(ready_at=NOW), NOW, passed=False)
    after = check.settle(c, NOW, {})
    assert (after.step.kind, after.step.task, after.plan.tasks[-1].origin) == (StepKind.BUILD, "t2", "person-check")
    assert "no greeting" in after.plan.tasks[-1].title
    again = after.model_copy(update={"step": Step(kind=StepKind.CHECK, task="preview"), "env": checking().env})
    assert check.action(again, live=False, paths={}) == "launch"


def test_a_passing_path_backed_answer_settles_against_current_fingerprints():
    c = checking(ready_at=NOW)
    c.checks[0].paths = ["src/a.ts"]
    answered(c, NOW, inputs=check_inputs(c, c.checks[0], {"src/a.ts": "f1"}))
    assert check.settle(c, NOW, {"src/a.ts": "f1"}).step.kind == StepKind.MERGE
    assert check.settle(c, NOW, {"src/a.ts": "f2"}).step == Step(kind=StepKind.CHECK, task="preview")


def test_a_runner_gone_without_an_exit_is_charged_once_and_the_fourth_asks(store, tmp_path):
    fake = Fake(store, tmp_path)
    save(store, asking(fake).model_copy(update={"outcome": None}))
    clock, spawn = [NOW], fake.host.spawn
    fake.host.spawn = lambda s: spawn(s).model_copy(update={"started_at": clock[0] + timedelta(seconds=1)})
    assert fake.host.tick(NOW) == ["c1"]
    for n in range(1, 5):
        fake.live.clear()
        clock[0] = NOW + timedelta(minutes=n)
        assert fake.host.tick(clock[0]) == (["c1"] if n < 4 else [])
        assert fake.host.tick(clock[0]) == []  # the replacement is alive; nothing is charged twice
    c = store.read("c1")
    assert (c.outcome.exit, c.outcome.cause) == (Exit.ASK, "liveness:build:runner-gone")
    later = NOW + timedelta(hours=1)
    committed = apply(c, StepResult(exit=Exit.DONE), later)
    rec = RunnerRecord(pid=1, created=1.0, started_at=later - timedelta(seconds=5))
    assert not host.disappeared(committed, rec, later)
    assert host.disappeared(committed, rec.model_copy(update={"started_at": later + timedelta(seconds=1)}), later)


def test_disposal_is_verified_over_recorded_pids_and_the_whole_group_without_its_leader():
    e = checking(pids={900: 2.0, 901: 2.0, 903: None}, pgid=900).env
    alive = {900: False, 901: None, 903: False}
    found = check.remaining(e, lambda p, _t: alive[p], lambda g, _leader: {902: "node"} if g == 900 else {})
    assert found == {901: "", 902: "node"}


def environment(store, fake, monkeypatch, **env):
    entry = ProfileEntry(state="known", value="npm run preview")
    store.write_profile(Profile(version=1, entries={"allow:check": entry}))
    c = checking(**env)
    c.names.worktree = fake.worktree
    save(store, c)
    calls = {"dispose": [], "start": [], "left": []}

    def dispose(e):
        calls["dispose"].append(dict(e.pids))
        return calls["left"].pop(0) if calls["left"] else {}

    def ready(e, _proc):
        calls["durable"] = store.read("c1").env  # the group is recorded before readiness is awaited
        return e.pids | {901: 2.0}

    monkeypatch.setattr(check, "dispose", dispose)
    monkeypatch.setattr(check, "start", lambda e, _root, _log: calls["start"].append(e.command) or Proc())
    monkeypatch.setattr(check, "ready", ready)
    monkeypatch.setattr(check, "created", lambda _pid: 2.0)
    return calls


class Proc:
    pid = 900


def test_an_uncertain_launch_is_disposed_from_the_worktree_scan_before_another_copy(store, tmp_path, monkeypatch):
    fake = Fake(store, tmp_path)
    calls = environment(store, fake, monkeypatch, launched_at=NOW)
    fake.found, calls["left"] = {77: "npm"}, [{77: "npm"}]
    assert fake.host.tick(NOW) == []
    assert (calls["start"], store.read("c1").blocked.action) == ([], "End processes 77")
    fake.found = {}
    assert fake.host.tick(NOW) == []
    assert (calls["dispose"][0], calls["start"]) == ({77: 2.0}, ["npm run preview"])


def test_the_environment_launches_after_the_builder_is_gone_and_is_disposed_on_the_result(store, tmp_path, monkeypatch):
    fake = Fake(store, tmp_path)
    calls = environment(store, fake, monkeypatch)
    (store.root / "changes" / "c1" / "runner.json").write_text(
        RunnerRecord(pid=5, created=1.0, started_at=NOW).model_dump_json()
    )
    fake.found = {55: "vite"}
    assert fake.host.tick(NOW) == []
    assert calls["start"] == []
    fake.found = {}
    assert fake.host.tick(NOW) == []
    assert calls["start"] == ["npm run preview"]
    assert (calls["durable"].pgid, calls["durable"].pids, calls["durable"].ready_at) == (900, {900: 2.0}, None)
    waiting = store.read("c1")
    assert (waiting.outcome.who, waiting.env.pids) == ("you", {900: 2.0, 901: 2.0})
    fake.live |= {900, 901}
    inputs = check_inputs(waiting, waiting.checks[0], {})
    store.put_inbox("c1", CheckResult(at=NOW - timedelta(hours=1), check="preview", passed=True, inputs=inputs))
    calls["left"] = [{902: "node"}]
    assert fake.host.tick() == []
    blocked = store.read("c1")
    assert (blocked.blocked.action, blocked.outcome.who, blocked.env.pgid) == ("End processes 902", "you", 900)
    assert fake.host.tick() == ["c1"]
    done = store.read("c1")
    assert (done.env, done.step.kind) == (None, StepKind.MERGE)
