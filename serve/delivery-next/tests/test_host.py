import importlib.util
import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from owlbear_delivery_next import cli, codebase, host, runner
from owlbear_delivery_next.evidence import check_inputs, next_check
from owlbear_delivery_next.host import Host, RunnerRecord
from owlbear_delivery_next.inbox import AnswerItem, CheckResult, IntentItem
from owlbear_delivery_next.loop import StepResult, apply
from owlbear_delivery_next.models import (
    VISUAL,
    Answer,
    Brief,
    Change,
    Environment,
    ErrorKind,
    Exit,
    Inputs,
    Names,
    PersonCheck,
    Plan,
    Question,
    Recipe,
    Step,
    StepKind,
    Task,
    VisualState,
)
from owlbear_delivery_next.preparation import BASE, Preparation
from owlbear_delivery_next.process_probe import WorktreeProcessScanError
from owlbear_delivery_next.profile_record import Profile
from owlbear_delivery_next.status import Activity, status
from owlbear_delivery_next.steps import check, disposable, prepare, worktree
from owlbear_delivery_next.storage_io import open_lock
from owlbear_delivery_next.store import Store
from owlbear_delivery_next.visual_records import VisualResult

NOW = datetime(2026, 10, 10, 12, tzinfo=UTC)
HOLD = """\
import os, sys
from pathlib import Path
from owlbear_delivery_next.codebase import CURRENT
from owlbear_delivery_next.host import HostRecord
from owlbear_delivery_next.storage_io import open_lock
from owlbear_delivery_next.store import Store
root = Store.open(Path(sys.argv[1])).root
fd = open_lock(os.open(root, os.O_RDONLY), blocking=False, name="host.lock")
record = HostRecord(
    url="http://127.0.0.1:9/", token="t", pid=os.getpid(), started_at="2026-10-10T12:00:00Z", code=CURRENT
)
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


def test_a_read_only_worktree_left_unconfirmed_is_scanned_before_its_mark_is_cleared(store, tmp_path):
    fake, ro, scanned = Fake(store, tmp_path), tmp_path / "c1.ro", []
    ro.mkdir()
    fake.host.scan = lambda path, _since: (scanned.append(path), fake.found if path == ro else {})[1]
    save(store, asking(fake).model_copy(update={"outcome": None}))
    folder = store.root / "changes" / "c1"
    disposable.begin(folder, ro)
    fake.found = {4242: "copilot"}
    assert fake.host.tick(NOW) == []
    assert (store.read("c1").blocked.action, disposable.live(folder)) == ("End processes 4242", ro)
    assert scanned == [Path(fake.worktree), ro]
    fake.found = {}
    assert fake.host.tick(NOW) == ["c1"]
    assert disposable.live(folder) is None


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
        "Models",
        "  planner: claude-opus-5.5 effort high",
        "  builder: claude-opus-5.5 effort medium",
        "  reviewer: gpt-6.1-sol effort xhigh",
        "  challenger: gpt-6.1-sol effort high",
        "  designer: claude-opus-5.5 effort high",
        "  preparer: claude-haiku-5.5 effort low",
        "  shaper: claude-opus-5.5 effort medium",
        "  updater: claude-opus-5.5 effort high",
    ]


def test_an_unloadable_change_is_reported_once_until_its_file_changes(store, tmp_path, capsys):
    fake = Fake(store, tmp_path)
    path = store.root / "changes" / "c1" / "change.json"
    path.parent.mkdir(parents=True)
    path.write_text('{"format": 0, "slug": 5}')
    for _ in range(3):
        assert fake.host.tick(NOW) == []
    assert capsys.readouterr().out.count("cannot be migrated") == 1
    path.write_text('{"format": 0, "slug": 6, "x": 1}')
    fake.host.tick(NOW)
    assert capsys.readouterr().out.count("cannot be migrated") == 1


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


def test_a_file_added_under_a_covered_directory_voids_a_passing_answer():
    c = checking(ready_at=NOW)
    c.checks[0].paths = ["app"]
    answered(c, NOW, inputs=check_inputs(c, c.checks[0], {"app/main.ts": "f1"}))
    added = {"app/main.ts": "f1", "app/banner.ts": "f2"}
    assert next_check(c, added) is c.checks[0]
    assert check.action(c, live=True, paths=added) == "keep"


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


def prepared(store, check_id: str = "preview") -> None:
    """The check's declared data-only test copy, restored as the runner leaves it for the host's launch."""
    none = Preparation(id="none", kind="data-only", seed="true", cleanup="true", isolation={"APP_ENV": "test"})
    store.update_config(lambda layer: layer.model_copy(update={"preparations": [none]}))
    prepare._write(store, "c1", prepare.Prepared(check=check_id, option=none, ready=True))  # noqa: SLF001


def environment(store, fake, monkeypatch, **env):
    store.write_profile(Profile(version=1))
    c = checking(**env)
    c.names.worktree = fake.worktree
    save(store, c)
    prepared(store, c.env.check)
    calls = {"dispose": [], "start": [], "left": []}

    def dispose(e):
        calls["dispose"].append(dict(e.pids))
        return calls["left"].pop(0) if calls["left"] else {}

    def ready(e, _proc):
        calls["durable"] = store.read("c1").env  # the group is recorded before readiness is awaited
        return e.pids | {901: 2.0}

    def start(e, _root, _log, env=None):
        calls["start"].append(e.command)
        calls["env"] = env
        return Proc()

    monkeypatch.setattr(check, "dispose", dispose)
    monkeypatch.setattr(check, "start", start)
    monkeypatch.setattr(check, "ready", ready)
    monkeypatch.setattr(check, "created", lambda _pid: 2.0)
    return calls


class Proc:
    pid = 900


RECIPE = Recipe(check="preview", command="npm run preview", directory=".", ready_url="http://127.0.0.1:4173/")


@pytest.fixture
def reusable(store, tmp_path, monkeypatch):
    """A check step in the store's own repository whose recipe launched at its HEAD; an agent run is recorded."""
    fake = Fake(store, tmp_path)
    environment(store, fake, monkeypatch)
    c = store.read("c1")
    c.names.worktree, c.env = str(tmp_path), None
    c.recipe = RECIPE.model_copy(update={"inputs": worktree.launch_inputs(tmp_path, ".")})
    save(store, c)
    agents = []
    monkeypatch.setattr(runner, "_agent", lambda *_a: agents.append("agent"))
    return fake, agents


def step(store, tmp_path) -> None:
    c = store.read("c1")
    with store.lock("c1") as lock:
        runner._step(store, lock, c, c.step, tmp_path)  # noqa: SLF001


def test_a_later_check_reuses_the_recipe_that_launched_without_an_agent(store, tmp_path, reusable):
    fake, agents = reusable
    step(store, tmp_path)
    after = store.read("c1")
    assert (agents, after.env.check, after.env.command, after.outcome.exit) == (
        [],
        "preview",
        "npm run preview",
        Exit.PENDING,
    )
    assert fake.host.tick(NOW) == []
    assert store.read("c1").env.ready_at is not None  # the host launched it as an agent's recipe


def _other_check(store, _tmp_path):
    c = store.read("c1")
    c.recipe = c.recipe.model_copy(update={"check": VISUAL})
    save(store, c)


def _launch_file(_store, tmp_path, name="package.json"):
    (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / name).write_text(f'{{"scripts": {{"preview": "vite preview {len(name)}"}}}}')
    for args in (["add", "-A"], ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "s"]):
        subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)  # noqa: S603, S607


def test_a_symlinked_launch_directory_is_read_at_its_target(store, tmp_path):
    _launch_file(store, tmp_path, "packages/web/package.json")
    (tmp_path / "preview").symlink_to("packages/web", target_is_directory=True)
    _launch_file(store, tmp_path, "README.md")
    before = worktree.launch_inputs(tmp_path, "preview")
    assert before == worktree.launch_inputs(tmp_path, "packages/web")
    _launch_file(store, tmp_path, "packages/web/vite.config.json")
    assert worktree.launch_inputs(tmp_path, "preview") not in {before, None}
    assert worktree.launch_inputs(tmp_path, "../outside") is None


@pytest.mark.parametrize("change", [_other_check, _launch_file])
def test_a_recipe_for_another_check_or_other_inputs_is_forgotten_and_an_agent_prepares(
    store, tmp_path, reusable, change
):
    _fake, agents = reusable
    change(store, tmp_path)
    step(store, tmp_path)
    after = store.read("c1")
    assert (agents, after.recipe, after.env) == (["agent"], None, None)


def test_a_project_without_a_preparation_option_asks_and_neither_reuses_nor_prepares(store, tmp_path, reusable):
    _fake, agents = reusable
    store.update_config(lambda layer: layer.model_copy(update={"preparations": []}))
    step(store, tmp_path)
    after = store.read("c1")
    assert (agents, after.env, after.outcome.exit, after.outcome.cause) == (
        [], None, Exit.ASK, "project-env:check:preparation-missing"
    )  # fmt: skip


def test_a_failed_launch_forgets_the_recipe_so_an_agent_prepares_again(store, tmp_path, monkeypatch):
    fake = Fake(store, tmp_path)
    environment(store, fake, monkeypatch)
    c = store.read("c1")
    c.recipe = RECIPE
    save(store, c)
    monkeypatch.setattr(check, "ready", lambda _e, _proc: None)
    assert fake.host.tick(NOW) == []
    after = store.read("c1")
    assert (after.recipe, after.env, after.outcome.exit) == (None, None, Exit.RETRY)


def test_a_check_without_a_test_preparation_never_launches(store, tmp_path, monkeypatch):
    fake = Fake(store, tmp_path)
    calls = environment(store, fake, monkeypatch)
    for path in (store.root / "changes" / "c1" / "prepare").glob("*.json"):
        path.unlink()
    assert fake.host.tick(NOW) == []
    after = store.read("c1")
    assert (calls["start"], after.env, after.outcome.exit) == ([], None, Exit.RETRY)
    assert after.outcome.reason == "the check has no test preparation; nothing launches without one"


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
    assert set(calls["env"]) - set(BASE) == {"APP_ENV"}  # the explicit test environment, never the host's own
    assert (calls["durable"].pgid, calls["durable"].pids, calls["durable"].ready_at) == (900, {900: 2.0}, None)
    waiting = store.read("c1")
    assert (waiting.outcome.who, waiting.env.pids) == ("you", {900: 2.0, 901: 2.0})
    assert waiting.recipe == RECIPE.model_copy(update={"inputs": worktree.launch_inputs(tmp_path / "wt", ".")})
    fake.live |= {900, 901}
    inputs = check_inputs(waiting, waiting.checks[0], check.fingerprints(waiting, waiting.checks[0]))
    store.put_inbox("c1", CheckResult(at=NOW - timedelta(hours=1), check="preview", passed=True, inputs=inputs))
    calls["left"] = [{902: "node"}]
    assert fake.host.tick() == []
    blocked = store.read("c1")
    assert (blocked.blocked.action, blocked.outcome.who, blocked.env.pgid) == ("End processes 902", "you", 900)
    assert fake.host.tick() == ["c1"]
    done = store.read("c1")
    assert (done.env, done.step.kind) == (None, StepKind.MERGE)


def test_the_visual_launch_waits_for_one_before_capture_and_its_runner_is_not_charged(store, tmp_path, monkeypatch):
    fake = Fake(store, tmp_path)
    calls = environment(store, fake, monkeypatch)
    c = store.read("c1")
    c.checks, c.step, c.env = [], Step(kind=StepKind.CHECK, task=VISUAL), c.env.model_copy(update={"check": VISUAL})
    c.brief = Brief(version=1, ui=True, visual=[VisualState(name="home", path="/", expect="a greeting")])
    save(store, c)
    prepared(store, VISUAL)
    assert (fake.host.tick(NOW), calls["start"]) == (["c1"], [])  # a runner renders the "before" states first
    c = store.read("c1")
    c.before = VisualResult(head="b" * 40, tree="t", at=NOW)
    save(store, c)
    fake.live.clear()
    assert fake.host.tick(NOW) == ["c1"]  # then the preview starts and the capture runner follows
    after = store.read("c1")
    assert (calls["start"], after.outcome.waiting, after.outcome.cause) == (["npm run preview"], "reviewer", None)


def test_the_code_identity_covers_shipped_files_and_ignores_incidental_ones(tmp_path):
    pkg = tmp_path / "pkg"
    (pkg / "web").mkdir(parents=True)
    (pkg / "skills" / "delivery").mkdir(parents=True)
    (pkg / "a.py").write_text("x = 1\n")
    (pkg / "web" / "page.html").write_text("<p>")
    (pkg / "skills" / "delivery" / "SKILL.md").write_text("# skill")
    first = codebase.identity(pkg)
    (pkg / "__pycache__").mkdir()
    (pkg / "__pycache__" / "a.cpython-314.pyc").write_bytes(b"pyc")
    for name in (".DS_Store", "foo.orig", "x.pyc", ".a.py.swp", "a.py~", ".#a.py", "web/page.html.orig"):
        (pkg / name).write_bytes(b"incidental")
    (pkg / "skills" / "delivery" / "SKILL.md.bak").write_text("old")
    assert codebase.identity(pkg) == first
    (pkg / "a.py").write_text("x = 2\n")
    assert codebase.identity(pkg) != first
    (pkg / "a.py").write_text("x = 1\n")
    assert codebase.identity(pkg) == first
    (pkg / "web" / "page.html").write_text("<p>!")
    assert codebase.identity(pkg) != first
    assert Host(Store(tmp_path), tmp_path).record.code == codebase.CURRENT == codebase.identity()


def test_every_file_the_package_tracks_is_in_its_code_identity():
    tracked = subprocess.run(
        ["git", "ls-files", "-z", "."],  # noqa: S607
        cwd=codebase.ROOT,
        capture_output=True,
        check=True,
        text=True,
    ).stdout.split("\0")
    assert {Path(p) for p in tracked if p} <= {p.relative_to(codebase.ROOT) for p in codebase.shipped()}


def test_an_unreadable_shipped_file_is_the_identity_and_does_not_fail_import(tmp_path):
    pkg = tmp_path / "pkg"
    (pkg / "agents").mkdir(parents=True)
    (pkg / "codebase.py").write_text(Path(codebase.__file__).read_text())
    (pkg / "agents" / "builder.md").write_text("# builder")
    (pkg / "agents" / "builder.md").chmod(0)
    try:
        spec = importlib.util.spec_from_file_location("copied_codebase", pkg / "codebase.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        assert module.CURRENT == codebase.identity(pkg) == "unreadable: agents/builder.md"
    finally:
        (pkg / "agents" / "builder.md").chmod(0o644)


def test_a_host_starts_no_runner_while_its_code_differs_and_again_once_it_returns(store, tmp_path, capsys):
    fake = Fake(store, tmp_path)
    save(store, asking(fake).model_copy(update={"outcome": None}))
    fake.host.code = lambda: "edited"
    assert fake.host.tick(NOW) == []
    assert fake.host.tick(NOW) == []
    assert capsys.readouterr().out.count(host.RESTART) == 1
    assert fake.host.runner("c1") is None
    fake.host.code = lambda: "unreadable: web/changes.html"
    assert fake.host.tick(NOW) == []
    assert fake.host.tick(NOW) == []
    assert capsys.readouterr().out.count("no runner starts: Delivery's code cannot be read: web/changes.html") == 1
    fake.host.code = lambda: fake.host.record.code
    assert fake.host.tick(NOW) == ["c1"]
    assert "runners start again" in capsys.readouterr().out


def test_a_host_whose_own_code_was_unreadable_at_start_starts_no_runner(store, tmp_path, capsys):
    fake = Fake(store, tmp_path)
    save(store, asking(fake).model_copy(update={"outcome": None}))
    fake.host.record = fake.host.record.model_copy(update={"code": "unreadable: golden/good.html"})
    fake.host.code = lambda: "unreadable: golden/good.html"
    assert fake.host.tick(NOW) == []
    assert "cannot be read: golden/good.html" in capsys.readouterr().out


def test_a_runner_beside_a_host_of_other_code_runs_and_writes_nothing(store, tmp_path, capsys):
    save(store, Change(slug="c1", step=Step(kind=StepKind.BUILD)))
    store.put_inbox("c1", IntentItem(at=NOW, intent="pause"))
    before = (store.root / "changes" / "c1" / "change.json").read_text()
    record = host.HostRecord(url="http://127.0.0.1:9/", token="t", pid=os.getpid(), started_at=NOW, code="older")  # noqa: S106
    (store.root / "host.json").write_text(record.model_dump_json())
    dir_fd = os.open(store.root, os.O_RDONLY)
    lock_fd = open_lock(dir_fd, blocking=False, name="host.lock")
    os.close(dir_fd)
    try:
        assert runner.main(["c1", "--repo", str(tmp_path)]) == 1
        assert capsys.readouterr().out == f"c1: {host.RESTART}\n"
        assert (store.root / "changes" / "c1" / "change.json").read_text() == before
        assert len(list((store.root / "changes" / "c1" / "inbox").glob("*.json"))) == 1
        assert host.RESTART in cli.show_status(store, NOW).splitlines()
    finally:
        os.close(lock_fd)


def waiting_on(fake, kind, when=NOW):
    c = Change(slug="c1", step=Step(kind=StepKind.BUILD), names=Names(worktree=fake.worktree))
    return apply(c, StepResult(exit=Exit.RETRY, cause=f"{kind}:build:sdk", reason="HTTP 503"), when)


def probing(fake, *answers):
    probes, left = [], iter(answers)
    fake.host.reach = lambda name: (probes.append(name), next(left))[1]
    return probes


def at(seconds):
    return NOW + timedelta(seconds=seconds)


def tick(fake, seconds):
    fake.host.clock = lambda: float(seconds)
    return fake.host.tick(at(seconds))


def test_a_change_waiting_on_the_network_wakes_once_the_probe_sees_the_network_return(store, tmp_path):
    fake = Fake(store, tmp_path)
    probes = probing(fake, "unreachable", None)
    save(store, waiting_on(fake, ErrorKind.NETWORK))
    assert tick(fake, 0) == []
    assert tick(fake, 1) == []
    assert tick(fake, 5) == []  # at most one probe every ten seconds
    assert tick(fake, 11) == ["c1"]  # long before the pause ends at 60 s
    assert probes == ["github.com", "github.com"]
    assert store.read("c1").outcome.wake_at == at(11)


def test_no_wait_ends_early_without_an_observed_return_or_for_a_capacity_wait(store, tmp_path):
    fake = Fake(store, tmp_path)
    probes = probing(fake, None, None)
    save(store, waiting_on(fake, ErrorKind.NETWORK))
    assert [tick(fake, s) for s in (0, 1, 11)] == [[], [], []]  # the network never looked down
    assert probes == ["github.com", "github.com"]
    fake = Fake(store, tmp_path)
    probes = probing(fake, "unreachable", None)
    save(store, waiting_on(fake, ErrorKind.CAPACITY))
    assert [tick(fake, s) for s in (0, 1, 11)] == [[], [], []]
    assert probes == []


def test_a_network_return_wakes_a_change_that_was_locked_when_the_probe_saw_it(store, tmp_path):
    fake = Fake(store, tmp_path)
    probes = probing(fake, "unreachable", None)
    save(store, waiting_on(fake, ErrorKind.NETWORK))
    assert [tick(fake, s) for s in (0, 1)] == [[], []]
    with store.lock("c1"):
        assert tick(fake, 11) == []  # the network returned while another writer held c1
    assert tick(fake, 12) == ["c1"]
    assert probes == ["github.com", "github.com"]
    assert store.read("c1").outcome.wake_at == at(12)


def test_a_network_return_does_not_wake_a_wait_that_began_after_it(store, tmp_path):
    fake = Fake(store, tmp_path)
    probing(fake, "unreachable", None)
    save(store, waiting_on(fake, ErrorKind.NETWORK))
    assert [tick(fake, s) for s in (0, 1)] == [[], []]
    with store.lock("c1"):
        assert tick(fake, 11) == []
    save(store, later := waiting_on(fake, ErrorKind.NETWORK, at(11.5)))
    assert [tick(fake, s) for s in (12, 13)] == [[], []]
    assert store.read("c1").outcome.wake_at == later.outcome.wake_at


def test_network_probes_keep_a_ten_second_schedule_from_each_probe_start(store, tmp_path):
    fake = Fake(store, tmp_path)
    clock, probes = [0.0], []
    fake.host.clock = lambda: clock[0]
    fake.host.reach = lambda _name: (probes.append(clock[0]), clock.__setitem__(0, clock[0] + 3), "unreachable")[2]
    save(store, waiting_on(fake, ErrorKind.NETWORK))
    assert fake.host.interval() == host.TICK  # no Change was seen waiting yet
    fake.host.tick(at(0))
    assert fake.host.interval() == 0  # the first probe is due
    fake.host.tick(at(0))  # the probe takes three seconds
    assert (probes, clock[0], fake.host.interval()) == ([0.0], 3.0, 7.0)
    clock[0] = 9.9
    fake.host.tick(at(10))
    clock[0] = 10.0
    fake.host.tick(at(10))
    assert probes == [0.0, 10.0]
