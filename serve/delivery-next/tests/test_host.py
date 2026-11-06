import importlib.util
import json
import os
import re
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from owlbear_delivery_next.change_contracts.amendment_records import Amending
from owlbear_delivery_next.change_contracts.evidence import check_inputs, next_check
from owlbear_delivery_next.change_contracts.inbox import AnswerItem, CheckResult, IntentItem
from owlbear_delivery_next.change_contracts.merge_records import Pullback
from owlbear_delivery_next.change_contracts.models import (
    VISUAL,
    Answer,
    Brief,
    Change,
    Environment,
    ErrorKind,
    Exit,
    Inputs,
    Names,
    Outcome,
    PersonCheck,
    Plan,
    Question,
    Recipe,
    Step,
    StepKind,
    Stop,
    Task,
    VisualState,
    Waiting,
)
from owlbear_delivery_next.change_contracts.preparation import BASE, Preparation
from owlbear_delivery_next.change_contracts.profile_record import Profile
from owlbear_delivery_next.change_contracts.round_records import BRIEF, RoundLoop, RoundPolicy
from owlbear_delivery_next.change_contracts.visual_records import VisualResult
from owlbear_delivery_next.change_flow import brief_rounds, brief_starts, delivery_target, loop, worktree
from owlbear_delivery_next.change_flow.brief_tools import BriefDraft
from owlbear_delivery_next.change_flow.loop import StepResult, apply
from owlbear_delivery_next.change_flow.status import Activity, status
from owlbear_delivery_next.commands import cli, runner
from owlbear_delivery_next.local_system import codebase, processes
from owlbear_delivery_next.local_system.storage_io import open_lock
from owlbear_delivery_next.project_host import api, brief_routes, host
from owlbear_delivery_next.project_host.host import Host, RunnerRecord
from owlbear_delivery_next.runtimes import command_marks
from owlbear_delivery_next.settings import config
from owlbear_delivery_next.settings.config import Layer
from owlbear_delivery_next.state_store import briefs, machine_settings, step_pids, work_block
from owlbear_delivery_next.state_store.database import put_record
from owlbear_delivery_next.state_store.store import ACTIVITY_LIMIT, Store, StoreError
from owlbear_delivery_next.workflow_steps import check, disposable, prepare

NOW = datetime(2026, 10, 10, 12, tzinfo=UTC)
DRAFT = {
    "title": "Greet", "outcome": "greet(name) says hello in the app package.",
    "criteria": ["greet('Ada') returns 'Hello, Ada!'"], "scope": ["packages/app"],
}  # fmt: skip


@pytest.fixture
def store(tmp_path):
    for args in (
        ["init", "-q"],
        ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "i"],
    ):
        subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)  # noqa: S603, S607
    return Store.open(tmp_path)


class Fake:
    """Process seams: spawned runners stay alive until ended; ``tree`` files each process under its group or session."""

    def __init__(self, store, tmp_path):
        self.live, self.pid = set(), 100
        self.tree: dict[int, tuple[int, str]] | None = {}  # pid -> (group or session id, name); None: unlistable
        (tmp_path / "wt").mkdir(exist_ok=True)
        self.worktree = str(tmp_path / "wt")
        self.host = Host(store, tmp_path, spawn=self.spawn, members=self.members)
        self.host.alive = lambda pid, _created: pid in self.live

    def spawn(self, _slug):
        self.pid += 1
        self.live.add(self.pid)
        return RunnerRecord(pid=self.pid, created=1.0, started_at=NOW)

    def members(self, ids):
        if self.tree is None:
            msg = "the process table could not be listed: denied"
            raise processes.UnlistedError(msg)
        return {p: name for p, (i, name) in self.tree.items() if i in ids}


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
    fake.tree = {4242: (101, "sleep"), 4243: (101, "copilot")}
    assert fake.host.tick(NOW) == []
    blocked = store.read("c1").blocked
    assert blocked.action == "End processes 4242, 4243"
    assert "4242 (sleep)" in status(store.read("c1"), Activity(host_up=True), NOW).line
    fake.tree = None
    assert fake.host.tick(NOW) == []
    reason = (
        "the step's processes could not be looked for: UnlistedError: the process table could not be listed: denied"
    )
    assert store.read("c1").blocked.reason == reason
    fake.tree = {}
    assert fake.host.tick(NOW) == ["c1"]
    assert store.read("c1").blocked is None


def logged(out: str, prefix: str) -> list[str]:
    """The host's log lines that start with *prefix*, each with every line of its text."""
    return re.findall(
        rf"^\d\d:\d\d:\d\dZ {re.escape(prefix)}(.*?)\n(?=\d\d:\d\d:\d\dZ |\Z)", out, re.MULTILINE | re.DOTALL
    )


@pytest.mark.parametrize(
    ("where", "said"),
    [
        ("pids", "the step's recorded processes could not be read: "),
        ("marks", "the step's command marks could not be read: "),
        ("table", "the step's processes could not be looked for: "),
        ("clear", "the check environment's processes could not be looked for: "),
        ("record", ""),
    ],
)
def test_a_blocked_or_unloadable_change_keeps_its_whole_error(  # noqa: PLR0913, PLR0917 - its fixtures
    store, tmp_path, monkeypatch, capsys, whole_error, where, said
):
    """Why no writer starts, or why a Change cannot be read, reaches its record and the host's log whole (#971)."""
    error = {"table": processes.UnlistedError, "record": StoreError}.get(where, OSError)(whole_error)
    error.add_note("a note added on the way up")

    def failing(*_args: object) -> None:
        raise error

    fake = Fake(store, tmp_path)
    if where == "clear":  # the environment is stopped before a stop when idle
        paused(fake, [True])
        environment(store, fake, monkeypatch, pids={900: 2.0}, pgid=900, ready_at=NOW, launched_at=NOW)
        fake.host.draining = lambda: True
        monkeypatch.setattr(check, "dispose", failing)
    else:
        save(store, asking(fake).model_copy(update={"outcome": None}))
        assert fake.host.tick(NOW) == ["c1"]
        fake.live.clear()  # the runner ended: what it left is looked for
        seams = {"pids": (step_pids, "recorded"), "marks": (command_marks, "read"), "record": (store, "read")}
        if where == "table":
            fake.host.members = failing
        else:
            monkeypatch.setattr(*seams[where], failing)
    capsys.readouterr()
    assert fake.host.tick(NOW) == []
    whole = f"{said}{type(error).__name__}: {whole_error}\na note added on the way up"
    if where == "record":
        assert logged(capsys.readouterr().out, "c1: ") == [whole]
        c = client(store, fake)  # the Change's card and its refused detail say it whole too
        assert c.get("/api/next/changes").json()[0]["line"] == f"stopped: {whole}"
        detail = c.get("/api/next/changes/c1")
        assert (detail.status_code, detail.json()["detail"]) == (409, whole)
        return
    assert store.read("c1").blocked.reason == whole
    assert logged(capsys.readouterr().out, "c1: no writer starts: ") == [whole]


def test_a_failed_pass_is_logged_and_noted_on_the_changes_page_whole_until_a_pass_succeeds(
    store, tmp_path, capsys, whole_error
):
    """The scheduler's failed pass reaches its log and the project's notes whole, and a passing one clears it (#971)."""
    fake = Fake(store, tmp_path)
    c = client(store, fake)
    error = RuntimeError(whole_error)
    error.add_note("a note added on the way up")
    seen = []

    def probe(_now: datetime) -> None:  # the first thing a pass does
        if not seen:
            seen.append("failing")
            fake.host.wake.set()
            raise error
        seen.append(c.get("/api/next/project").json())  # the next pass, before it ends
        fake.host.stopped.set()

    fake.host._probe = probe  # noqa: SLF001 - the pass's own first step fails
    fake.host.run()
    whole = f"RuntimeError: {whole_error}\na note added on the way up"
    assert seen == ["failing", {"notes": [f"The host's last pass failed: {whole}"]}]
    assert logged(capsys.readouterr().out, "pass failed: ") == [whole]
    assert (fake.host.failed, c.get("/api/next/project").json()) == ("", {"notes": []})


def test_recorded_pids_of_the_runner_block_until_gone(store, tmp_path):
    fake = Fake(store, tmp_path)
    save(store, asking(fake).model_copy(update={"outcome": None}))
    fake.host.tick(NOW)
    with store.lock("c1") as lock:
        store.log(lock, "c1", {"event": "pids", "at": NOW.isoformat(), "pids": {"777": 1.0}})
        for _ in range(ACTIVITY_LIMIT):  # a long step's later activity evicts the record from the log
            store.log(lock, "c1", {"event": "tool", "at": NOW.isoformat()})
    fake.live = {777}
    assert fake.host.tick(NOW) == []
    assert "777" in store.read("c1").blocked.action
    fake.live.clear()
    assert fake.host.tick(NOW) == ["c1"]


def test_a_read_only_copys_install_left_behind_blocks_until_gone(store, tmp_path):
    fake, ro = Fake(store, tmp_path), tmp_path / "c1.ro"
    ro.mkdir()
    c = asking(fake).model_copy(update={"outcome": None})
    c.step.started_at = NOW - timedelta(minutes=1)
    save(store, c)
    folder = store.root / "changes" / "c1"
    disposable.begin(folder, ro)
    with store.lock("c1") as lock:  # the install's leader, ended, as check.run journals it
        store.log(lock, "c1", {"event": "pids", "at": (NOW - timedelta(seconds=30)).isoformat(), "pids": {"900": 1.0}})
    fake.tree = {4242: (900, "copilot")}
    assert fake.host.tick(NOW) == []
    assert (store.read("c1").blocked.action, disposable.live(folder)) == ("End processes 4242", ro)
    fake.tree = {}
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


def test_status_reads_the_host_lock_and_shows_host_down(store):
    save(store, Change(slug="c1", step=Step(kind=StepKind.BUILD)))
    record = host.HostRecord(
        url="http://127.0.0.1:9/",
        token="t",  # noqa: S106
        pid=os.getpid(),
        started_at=NOW,
        code=codebase.CURRENT,
    )
    (store.root / "host.json").write_text(record.model_dump_json())
    dir_fd = os.open(store.root, os.O_RDONLY)
    lock_fd = open_lock(dir_fd, blocking=False, name="host.lock")  # flock conflicts across open files in one process
    os.close(dir_fd)
    try:
        assert host.running(store).pid == os.getpid()
        assert "Delivery is not running" not in cli.show_status(store, NOW)
    finally:
        os.close(lock_fd)
    assert host.running(store) is None
    assert cli.show_status(store, NOW).splitlines() == [
        f"Delivery is not running — {cli.START}",
        "c1: Build · Delivery is not running",
        f"  next: Start Delivery ({cli.START})",
        "Models",
        "  planner: claude-opus-5.5 effort high",
        "  builder: claude-opus-5.5 effort medium",
        "  reviewer: gpt-6.1-sol effort xhigh",
        "  challenger: gpt-6.1-sol effort high",
        "  design-judge: claude-opus-5.5 effort high",
        "  preparer: claude-haiku-5.5 effort low",
        "  shaper: claude-opus-5.5 effort medium",
        "  updater: claude-opus-5.5 effort high",
        "  test-reviewer: gpt-6.1-sol effort medium",
        "  test-curator: claude-opus-5.5 effort high",
        "  picker: gpt-6.1-sol effort medium",
        "  curator: gpt-6.1-sol effort high",
        "  spotter: gpt-6-luna effort medium",
        "  retro: gpt-6.1-sol effort medium",
        "  retro-review: gpt-6.1-sol effort medium",
        "  auditor: gpt-6.1-sol effort medium",
    ]


def raw(store, slug, text):
    with store.db.write() as db:
        put_record(db, slug, text)


def test_an_unloadable_change_is_reported_once_until_its_record_changes(store, tmp_path, capsys):
    fake = Fake(store, tmp_path)
    raw(store, "c1", '{"format": 0, "slug": 5}')
    for _ in range(3):
        assert fake.host.tick(NOW) == []
    assert capsys.readouterr().out.count("cannot be migrated") == 1
    raw(store, "c1", '{"format": 0, "slug": 6, "x": 1}')
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
        (checking(ready_at=NOW).model_copy(update={"amending": Amending(id="A1")}), True, "dispose"),  # TD-185
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
    assert (
        store.save(
            store.config_path,
            Layer,
            lambda layer: layer.model_copy(update={"preparations": [none]}),
            "setup",
            owner=True,
        )
        == ""
    )
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

    def start(e, _root, _log, env=None, _pidfile=None):
        calls["start"].append(e.command)
        calls["env"] = env
        return Proc()

    monkeypatch.setattr(check, "dispose", dispose)
    monkeypatch.setattr(check, "start", start)
    monkeypatch.setattr(check, "ready", ready)
    monkeypatch.setattr(check, "created", lambda _pid: 2.0)
    monkeypatch.setattr(check, "taken", lambda e, _leader: e.pids)
    return calls


class Proc:
    pid = 900
    stdin = None


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
    assert (
        store.save(
            store.config_path, Layer, lambda layer: layer.model_copy(update={"preparations": []}), "setup", owner=True
        )
        == ""
    )
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


def test_a_leader_gone_before_readiness_leaves_its_members_recorded_for_disposal(store, tmp_path, monkeypatch):
    fake = Fake(store, tmp_path)
    calls = environment(store, fake, monkeypatch)
    calls["left"] = [{}, {902: "node"}]  # the launch's own clearing, then the failed launch's
    monkeypatch.setattr(check, "ready", lambda _e, _proc: None)
    monkeypatch.setattr(check, "taken", lambda e, leader: e.pids | ({902: 3.0} if leader == Proc.pid else {}))
    fake.host.tick(NOW)
    assert calls["dispose"][-1] == {900: 2.0, 902: 3.0}
    assert store.read("c1").env.pids == {900: 2.0, 902: 3.0}  # still blocked: the next try proves 902 the launch's


def test_a_check_without_a_test_preparation_never_launches(store, tmp_path, monkeypatch):
    fake = Fake(store, tmp_path)
    calls = environment(store, fake, monkeypatch)
    for path in (store.root / "changes" / "c1" / "prepare").glob("*.json"):
        path.unlink()
    assert fake.host.tick(NOW) == []
    after = store.read("c1")
    assert (calls["start"], after.env, after.outcome.exit) == ([], None, Exit.RETRY)
    assert after.outcome.reason == "the check has no test preparation; nothing launches without one"


def launched(store, pid):
    """The pid file a launch's wrapper wrote at ``NOW`` before the host recorded its group."""
    path = store.root / "changes" / "c1" / check.PIDFILE
    path.write_text(f"{pid}\n")
    os.utime(path, (NOW.timestamp(), NOW.timestamp()))
    return NOW.timestamp()


def test_an_uncertain_launch_is_disposed_from_its_pid_file_before_another_copy(store, tmp_path, monkeypatch):
    fake = Fake(store, tmp_path)
    calls = environment(store, fake, monkeypatch, launched_at=NOW)
    at, calls["left"] = launched(store, 77), [{77: "npm"}]
    assert fake.host.tick(NOW) == []
    assert (calls["start"], store.read("c1").blocked.action) == ([], "End processes 77")
    assert fake.host.tick(NOW) == []
    assert (calls["dispose"][0], calls["start"]) == ({77: at}, ["npm run preview"])


def test_the_environment_launches_after_the_builder_is_gone_and_is_disposed_on_the_result(store, tmp_path, monkeypatch):
    fake = Fake(store, tmp_path)
    calls = environment(store, fake, monkeypatch)
    (store.root / "changes" / "c1" / "runner.json").write_text(
        RunnerRecord(pid=5, created=1.0, started_at=NOW).model_dump_json()
    )
    fake.tree = {55: (5, "vite")}
    assert fake.host.tick(NOW) == []
    assert calls["start"] == []
    fake.tree = {}
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


@pytest.mark.parametrize("passed", [None, False, True])
def test_a_delivery_discrepancy_disposes_person_check_without_settling_or_relaunching(
    store,
    tmp_path,
    monkeypatch,
    passed,
):
    fake = Fake(store, tmp_path)
    calls = environment(store, fake, monkeypatch, ready_at=NOW, pids={900: 2.0}, pgid=900)
    c = store.read("c1")
    c.names.pr, c.names.branch, c.names.target = 7, "owlbear/c1", "main"
    delivery_target.halt(c, "PR #7 merged into the wrong target", NOW)
    gate = loop.open_question(c).id
    save(store, c)
    if passed is not None:
        inputs = check_inputs(c, c.checks[0], check.fingerprints(c, c.checks[0]))
        store.put_inbox("c1", CheckResult(at=NOW, check="preview", passed=passed, inputs=inputs))
    fake.host.observe_pr = lambda _slug: (None, False)

    assert fake.host.tick(NOW) == []

    after = store.read("c1")
    assert calls["start"] == []
    assert calls["dispose"]
    assert after.env is None
    assert after.step.kind is StepKind.CHECK
    assert delivery_target.held(after)
    assert loop.open_question(after).id == gate
    assert loop.next_step(after, NOW) is None
    if passed is not None:
        assert after.checks[0].answer.passed is passed


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
    (pkg / "skills" / "owlbear-change-shaping").mkdir(parents=True)
    (pkg / "a.py").write_text("x = 1\n")
    (pkg / "web" / "page.html").write_text("<p>")
    (pkg / "skills" / "owlbear-change-shaping" / "SKILL.md").write_text("# skill")
    first = codebase.identity(pkg)
    (pkg / "__pycache__").mkdir()
    (pkg / "__pycache__" / "a.cpython-314.pyc").write_bytes(b"pyc")
    for name in (".DS_Store", "foo.orig", "x.pyc", ".a.py.swp", "a.py~", ".#a.py", "web/page.html.orig"):
        (pkg / name).write_bytes(b"incidental")
    (pkg / "skills" / "owlbear-change-shaping" / "SKILL.md.bak").write_text("old")
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
    (pkg / "local_system").mkdir()
    (pkg / "local_system" / "codebase.py").write_text(Path(codebase.__file__).read_text())
    (pkg / "agents" / "owlbear-builder.agent.md").write_text("# builder")
    (pkg / "agents" / "owlbear-builder.agent.md").chmod(0)
    try:
        spec = importlib.util.spec_from_file_location("copied_codebase", pkg / "local_system" / "codebase.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        assert module.CURRENT == codebase.identity(pkg) == "unreadable: agents/owlbear-builder.agent.md"
    finally:
        (pkg / "agents" / "owlbear-builder.agent.md").chmod(0o644)


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
    before = store.rev("c1")
    record = host.HostRecord(url="http://127.0.0.1:9/", token="t", pid=os.getpid(), started_at=NOW, code="older")  # noqa: S106
    (store.root / "host.json").write_text(record.model_dump_json())
    dir_fd = os.open(store.root, os.O_RDONLY)
    lock_fd = open_lock(dir_fd, blocking=False, name="host.lock")
    os.close(dir_fd)
    try:
        assert runner.main(["c1", "--repo", str(tmp_path)]) == 1
        assert capsys.readouterr().out == f"c1: {host.RESTART}\n"
        assert store.rev("c1") == before
        with store.db.read() as db:
            assert db.execute("SELECT count(*) FROM inbox").fetchone() == (1,)
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


def paused(fake, flag):
    fake.host.paused = lambda: flag[0]
    fake.host.observe_pr = lambda _slug: ("open", True)  # neither applied while paused: only a PR's end is


def test_while_paused_input_and_the_owners_pull_are_applied_and_nothing_else_starts(store, tmp_path, monkeypatch):
    fake, flag = Fake(store, tmp_path), [True]
    paused(fake, flag)
    save(store, asking(fake).model_copy(update={"pull_requested": NOW}))
    store.put_inbox("c1", AnswerItem(at=NOW, question="q1", text="German"))
    pulled = []
    monkeypatch.setattr(host.pullback, "run", lambda *_a: pulled.append(True) or Pullback(state="updated", at=NOW))
    assert fake.host.tick(NOW) == []
    c = store.read("c1")
    assert (c.outcome, c.pull_requested, fake.host.runner("c1"), pulled) == (None, None, None, [True])  # TD-287
    said = status(c, fake.host.activity("c1"), NOW)
    assert (said.line, said.action, said.actor) == ("Build 1/1 · Delivery is paused: continues after Resume",
                                                     "Resume Delivery", "you")  # fmt: skip
    flag[0] = False
    fake.host.observe_pr = lambda _slug: (None, False)
    assert fake.host.tick(NOW) == ["c1"]


def test_a_pr_merged_while_paused_starts_its_cleanup(store, tmp_path):
    """TD-303: maintenance OwlBear starts itself runs while paused, a merged PR's cleanup with it."""
    fake = Fake(store, tmp_path)
    paused(fake, [True])
    save(store, asking(fake))
    fake.host.observe_pr = lambda _slug: ("merged", False)
    merges = []
    fake.host.merged = lambda: merges.append(True)  # the machine may curate the project's memory (item 5 slice 4)
    assert (fake.host.tick(NOW), store.read("c1").step.kind) == (["c1"], StepKind.CLEANUP)
    fake.host.tick(NOW)  # its cleanup's passes are no second merge
    assert merges == [True]


def test_a_permission_to_pass_the_pause_holds_only_for_its_own_pass(store, tmp_path):
    fake, flag = Fake(store, tmp_path), [True]
    paused(fake, flag)
    c = asking(fake).model_copy(update={"outcome": None, "step": Step(kind=StepKind.SHAPE, mode="challenge")})
    save(store, c)
    assert fake.host._one("c1", NOW)  # noqa: SLF001 - a paused pass lets the challenge through
    save(store, store.read("c1").model_copy(update={"step": Step(kind=StepKind.PLAN)}))
    flag[0] = False
    assert fake.host._one("c1", NOW)  # noqa: SLF001 - planning is due once resumed
    flag[0] = True  # paused again before that pass launches
    assert fake.host._launch("c1") is False  # noqa: SLF001


def test_a_paused_fold_still_takes_a_queued_pr_out_through_the_barrier(store, tmp_path, monkeypatch):
    fake = Fake(store, tmp_path)
    paused(fake, [True])
    seen = []

    def barrier(_store, _repo):
        return lambda before, after: seen.append((before.intent.paused_at, after.intent.paused_at)) or after

    monkeypatch.setattr(host.queue, "barrier", barrier)
    save(store, asking(fake))
    store.put_inbox("c1", IntentItem(at=NOW, intent="pause"))
    assert (fake.host.tick(NOW), seen) == ([], [(None, NOW)])  # TD-284: the dequeue goes out at once


@pytest.mark.parametrize(
    ("kind", "mode", "runs"),
    [(StepKind.CLEANUP, None, True), (StepKind.SHAPE, "challenge", True), (StepKind.SHAPE, "planned", False),
     (StepKind.BUILD, None, False)],
)  # fmt: skip
def test_while_paused_only_a_cleanup_or_the_owners_brief_challenge_starts(store, tmp_path, kind, mode, runs):
    """TD-287, TD-303: never while OwlBear or the project stops, nor once the owner asked to stop when idle."""
    fake = Fake(store, tmp_path)
    paused(fake, [True])
    c = asking(fake).model_copy(update={"outcome": None, "step": Step(kind=kind, mode=mode, task="t1")})
    save(store, c)
    assert (status(c, fake.host.activity("c1"), NOW).action == "Resume Delivery") is not runs
    fake.host.draining = lambda: True
    assert fake.host.tick(NOW) == []
    fake.host.draining, fake.host.closed = (lambda: False), (lambda: True)
    assert fake.host.tick(NOW) == []
    fake.host.closed = lambda: False
    assert fake.host.tick(NOW) == (["c1"] if runs else [])


def test_the_owners_one_more_brief_challenge_runs_while_paused_and_what_follows_waits(store, tmp_path):
    """#966: asked for on the Changes page, it passes the pause as the chat's request does (TD-287); planning waits."""
    fake, flag = Fake(store, tmp_path), [True]
    paused(fake, flag)
    c = Change(slug="c1", brief=Brief(version=2, requested=2, challenged=2), step=Step(kind=StepKind.SHAPE),
               names=Names(worktree=fake.worktree))  # fmt: skip
    c.loops[BRIEF] = RoundLoop(subject=BRIEF, policy=RoundPolicy(max_rounds=1), round=1, head="1", ended="count",
                               unreviewed=["v2"])  # fmt: skip
    save(store, c.model_copy(update={"outcome": Outcome(exit=Exit.PENDING, waiting=Waiting.CHAT, who="you",
                                                        reason="approve brief v2", at=NOW)}))  # fmt: skip
    http = client(store, fake)
    assert fake.host.tick(NOW) == []
    asked = http.post("/api/next/changes/c1/challenge-brief", json={"version": 2})
    assert asked.json() == {"accepted": "brief-challenge"}
    assert fake.host.tick(NOW) == ["c1"]
    with store.lock("c1") as lock:  # the challenger's clean verdict, as brief_round.judged counts it
        c = store.read("c1")
        brief_rounds.counted(c, [], {}, NOW)
        store.write(lock, c)
    fake.live.clear()
    assert http.post("/api/next/changes/c1/approve-brief", json={"version": 2}).json() == {"accepted": "brief-approval"}
    assert (fake.host.tick(NOW), store.read("c1").step.kind) == ([], StepKind.PLAN)
    flag[0] = False
    assert fake.host.tick(NOW) == ["c1"]


def test_a_runner_gone_while_paused_is_charged_and_forgotten_and_nothing_starts(store, tmp_path):
    fake, flag = Fake(store, tmp_path), [False]
    paused(fake, flag)
    fake.host.observe_pr = lambda _slug: (None, False)
    save(store, asking(fake).model_copy(update={"outcome": None}))
    assert fake.host.tick(NOW) == ["c1"]
    flag[0] = True
    assert fake.host.tick(NOW) == []  # alive: it finishes on its own (TD-282)
    finishing = status(store.read("c1"), Activity(host_up=True, runner_alive=True, paused=True), NOW)
    assert finishing.line == "Build 1/1 · finishing build (started before the restart)"
    fake.live.clear()
    fake.host.observe_pr = lambda _slug: ("open", True)  # only a PR's end applies while paused (TD-303)
    assert fake.host.tick(NOW) == []
    c = store.read("c1")
    assert (c.outcome.exit, fake.host.runner("c1"), fake.pid) == (Exit.RETRY, None, 101)


def test_while_paused_no_check_environment_launches_or_is_disposed(store, tmp_path, monkeypatch):
    fake = Fake(store, tmp_path)
    paused(fake, [True])
    calls = environment(store, fake, monkeypatch)
    assert (fake.host.tick(NOW), calls["start"], calls["dispose"]) == ([], [], [])
    assert store.read("c1").env.pgid is None


def test_before_a_stop_when_idle_the_paused_pass_stops_the_check_environment(store, tmp_path, monkeypatch):
    """TD-288: it launches again after the next start, since nothing of it is recorded as running."""
    fake = Fake(store, tmp_path)
    paused(fake, [True])
    calls = environment(store, fake, monkeypatch, pids={900: 2.0}, pgid=900, ready_at=NOW, launched_at=NOW)
    fake.host.draining = lambda: True
    calls["left"] = [{900: "npm"}]
    assert (fake.host.tick(NOW), store.read("c1").blocked.action) == ([], "End processes 900")
    assert (fake.host.tick(NOW), calls["dispose"], calls["start"]) == ([], [{900: 2.0}, {900: 2.0}], [])
    e = store.read("c1").env
    assert (e.pids, e.pgid, e.ready_at, e.launched_at, fake.host.env_action(store.read("c1"))) == (
        {}, None, None, None, "launch"
    )  # fmt: skip


def test_a_launch_that_left_no_pids_is_found_and_stopped_before_a_stop_when_idle(store, tmp_path, monkeypatch):
    fake = Fake(store, tmp_path)
    paused(fake, [True])
    calls = environment(store, fake, monkeypatch, launched_at=NOW)
    fake.host.draining = lambda: True
    at = launched(store, 902)  # the crash came before its group was recorded
    assert (fake.host.tick(NOW), calls["dispose"], store.read("c1").env.launched_at) == ([], [{902: at}], None)


def test_a_liveness_stop_found_while_paused_clears_once_its_processes_are_gone(store, tmp_path):
    fake, flag = Fake(store, tmp_path), [False]
    paused(fake, flag)
    fake.host.observe_pr = lambda _slug: (None, False)
    save(store, asking(fake).model_copy(update={"outcome": None}))
    assert fake.host.tick(NOW) == ["c1"]
    flag[0] = True
    fake.live.clear()
    fake.tree = {4242: (101, "sleep")}
    assert fake.host.tick(NOW) == []
    assert (store.read("c1").blocked.action, fake.host.runner("c1").pid) == ("End processes 4242", 101)
    fake.tree = {}
    assert fake.host.tick(NOW) == []
    assert (store.read("c1").blocked, fake.host.runner("c1"), fake.pid) == (None, None, 101)


def test_a_network_wait_while_paused_never_spins_the_scheduler(store, tmp_path):
    fake = Fake(store, tmp_path)
    paused(fake, [True])
    fake.host.offline = {"c1"}  # its probe deadline passed long ago; no probe runs while paused
    assert fake.host.interval() == host.TICK


def test_no_check_environment_starts_once_the_host_pauses_during_its_pass(store, tmp_path, monkeypatch):
    fake = Fake(store, tmp_path)
    calls = environment(store, fake, monkeypatch)
    asked = [0]

    def paused():  # the pass began before a project's stop closed its gate
        asked[0] += 1
        return asked[0] > 2

    fake.host.paused = paused
    assert fake.host.tick(NOW) == []
    assert (calls["start"], store.read("c1").env.launched_at, asked[0]) == ([], None, 3)


def client(store, fake, **headers):
    auth = {"authorization": "Bearer tok"} | headers
    return TestClient(api.create_app(store, "tok", fake.host), base_url="http://127.0.0.1", headers=auth)


def queued(store):
    with store.db.read() as db:
        return [item for (item,) in db.execute("SELECT item FROM inbox WHERE slug = 'c1'")]


def stopped(fake, kind=StepKind.BUILD, stop=None):
    c = asking(fake).model_copy(update={"step": Step(kind=kind, task="t1")})
    stop = stop or Stop(kind=ErrorKind.STATE, reason="GitHub refused", action="Resolve it in GitHub",
                        resume="GitHub agrees", at=NOW)  # fmt: skip
    return apply(c, StepResult(exit=Exit.STOP, reason=stop.reason, stop=stop), NOW)


SHOWN = {"action": "Resolve it in GitHub", "at": "2026-10-10T12:00:00Z"}  # the stop of stopped(), as the page shows it


def test_resume_leaves_a_stop_and_the_owners_recovery_reruns_its_step(store, tmp_path):
    """#754: Resume clears only a pause; the owner's recovery on the Changes page clears the stop."""
    fake = Fake(store, tmp_path)
    save(store, stopped(fake))
    api_ = client(store, fake)
    assert api_.post("/api/next/changes/c1/intent", json={"intent": "resume"}).status_code == 200
    assert fake.host.tick(NOW) == []
    assert store.read("c1").outcome.exit == Exit.STOP
    assert (
        api_.get("/api/next/changes/c1").json()["recovery"]
        == {"reason": "GitHub refused", "unset": None, "settings": {"count": 0, "reason": ""}} | SHOWN
    )
    answer = api_.post("/api/next/changes/c1/recovery", json=SHOWN)
    assert (answer.status_code, answer.json()) == (200, {"accepted": "recovery"})
    assert [(i["kind"], i["action"]) for i in map(json.loads, queued(store))] == [("recovery", "Resolve it in GitHub")]
    assert fake.host.tick(NOW) == ["c1"]
    assert (store.read("c1").stop, store.read("c1").outcome) == (None, None)


@pytest.mark.parametrize("kind", [StepKind.BUILD, StepKind.CLEANUP])
@pytest.mark.parametrize("pause", ["change", "delivery"])
def test_a_recovery_while_paused_clears_the_stop_and_only_a_cleanup_runs_before_resume(store, tmp_path, pause, kind):
    fake, flag = Fake(store, tmp_path), [pause == "delivery"]
    paused(fake, flag)
    c = stopped(fake, kind)
    save(store, c.model_copy(update={"intent": c.intent.model_copy(update={"paused_at": NOW})}) if pause == "change"
         else c)  # fmt: skip
    api_ = client(store, fake)
    assert api_.post("/api/next/changes/c1/recovery", json=SHOWN).status_code == 200
    runs = ["c1"] if kind == StepKind.CLEANUP else []
    assert fake.host.tick(NOW) == runs
    after = store.read("c1")
    assert (after.stop, after.intent.paused_at is not None, fake.host.paused()) == (None, pause == "change",
                                                                                   pause == "delivery")  # fmt: skip
    if runs:
        return
    if pause == "change":
        api_.post("/api/next/changes/c1/intent", json={"intent": "resume"})
    flag[0] = False
    fake.host.observe_pr = lambda _slug: (None, False)
    assert fake.host.tick(NOW) == ["c1"]


def wrong_merge(fake, store):
    c = asking(fake).model_copy(update={"outcome": None})
    delivery_target.halt(c, "PR #7 merged into release, not main", NOW)
    save(store, c)
    store.put_inbox("c1", AnswerItem(at=NOW, question=loop.open_question(c).id, option="pause"))
    with store.lock("c1") as lock:
        return store.fold(lock, "c1", NOW)[0]


NOT_STOPPED, STALE = "This Change is not stopped", "The stop changed since the page showed it; reload"
LIVENESS = Stop(kind=ErrorKind.LIVENESS, reason="processes still present: 7", action="End processes 7",
                resume="The host sees none of them", at=NOW)  # fmt: skip


@pytest.mark.parametrize(
    ("case", "why"),
    [("asking", NOT_STOPPED), ("finished", "This Change has finished"), ("wrong merge", NOT_STOPPED),
     ("held", "This stop ends only when you abandon or pause the Change; answer its question"),
     ("liveness", "This stop clears itself once the host sees none of the step's processes"), ("stale", STALE),
     ("older page", STALE)],
)  # fmt: skip
def test_a_stop_the_owner_cannot_clear_is_refused_and_nothing_is_queued(store, tmp_path, case, why):
    fake = Fake(store, tmp_path)
    held = delivery_target.stop(asking(fake), "PR #7 merged into release, not main", NOW)
    c = {
        "asking": lambda: asking(fake), "finished": lambda: stopped(fake).model_copy(update={"finished_at": NOW}),
        "wrong merge": lambda: wrong_merge(fake, store), "held": lambda: stopped(fake, stop=held),
        "liveness": lambda: stopped(fake, stop=LIVENESS), "stale": lambda: stopped(fake),
        "older page": lambda: stopped(fake),
    }[case]()  # fmt: skip
    save(store, c)
    api_ = client(store, fake)
    changed = {"stale": {"action": "Resolve it elsewhere"}, "older page": {"at": "2026-10-10T11:00:00Z"}}
    answer = api_.post("/api/next/changes/c1/recovery", json=SHOWN | changed.get(case, {}))
    assert (answer.status_code, answer.json()["detail"], queued(store)) == (409, why, [])
    assert (api_.get("/api/next/changes/c1").json()["recovery"] is None) is (case not in changed)
    with store.lock("c1") as lock:
        assert store.fold(lock, "c1", NOW)[0].stop == c.stop


@pytest.mark.parametrize(("unset", "unreadable"), [(True, False), (False, True), (True, True)])
def test_the_recovery_read_counts_the_unset_settings_and_keeps_why_they_cannot_be_read(
    store, tmp_path, monkeypatch, unset, unreadable
):
    """The page says how many are unset, never their keys, and never hides an unreadable file behind that count."""
    if unset:
        monkeypatch.setattr(machine_settings, "BASE", None)
    if unreadable:
        store.config_path.write_text("{not json")
    fake = Fake(store, tmp_path)
    save(store, stopped(fake))
    recovery = client(store, fake).get("/api/next/changes/c1").json()["recovery"]
    block = work_block.of_store(store)
    assert (bool(block.keys), bool(block.reason)) == (unset, unreadable)
    assert recovery["settings"] == {"count": len(block.keys), "reason": block.reason}  # one read: parts and words agree
    assert recovery["unset"].startswith("The settings can't be read" if unreadable else "Settings unset: ")


@pytest.mark.parametrize("layer", [machine_settings, config])
def test_no_recovery_while_a_setting_is_unset(store, tmp_path, monkeypatch, layer):
    """D-01M61SBWK4VE4MNTD35TR0VPS8: no work starts while a setting is unset, this machine's included."""
    monkeypatch.setattr(layer, "BASE", None)
    fake = Fake(store, tmp_path)
    save(store, stopped(fake))
    api_ = client(store, fake)
    why = api_.get("/api/next/changes/c1").json()["recovery"]["unset"]
    assert why.startswith("Settings unset: ")
    answer = api_.post("/api/next/changes/c1/recovery", json=SHOWN)
    assert (answer.status_code, answer.json()["detail"], queued(store)) == (409, why, [])


def test_a_recovery_is_checked_and_queued_under_the_changes_lock(store, tmp_path):
    """No pass can stop the Change again between the route's check and its queueing."""
    fake = Fake(store, tmp_path)
    save(store, stopped(fake))
    with store.lock("c1"):
        answer = client(store, fake).post("/api/next/changes/c1/recovery", json=SHOWN)
    assert (answer.status_code, answer.json()["detail"].endswith("; try again"), queued(store)) == (409, True, [])


def test_a_chat_cannot_clear_a_stop(store, tmp_path):
    fake = Fake(store, tmp_path)
    save(store, stopped(fake))
    answer = client(store, fake, **{"x-owlbear-use": "chat"}).post("/api/next/changes/c1/recovery", json=SHOWN)
    refused = "Only the owner clears a stop, on the Changes page"
    assert (answer.status_code, answer.json()["detail"], queued(store)) == (403, refused, [])


def test_a_running_steps_stage_reaches_the_status_and_owlbear_status_from_the_store(store):
    """#718: events the runner's sessions log in the store reach the shared status through host.activity."""
    started = datetime.now(UTC) - timedelta(minutes=2)
    c = Change(slug="c1", plan=Plan(tasks=[Task(id="t1", title="greet")]),
               step=Step(kind=StepKind.BUILD, task="t1", started_at=started))  # fmt: skip
    save(store, c)
    record = host.HostRecord(url="http://127.0.0.1:9/", token="t", pid=1, started_at=NOW, code=codebase.CURRENT)  # noqa: S106
    (store.root / "host.json").write_text(record.model_dump_json())
    dir_fd = os.open(store.root, os.O_RDONLY)
    host_fd = open_lock(dir_fd, blocking=False, name="host.lock")
    os.close(dir_fd)
    at = datetime.now(UTC).isoformat(timespec="seconds")
    who = {"at": at, "session": "b1", "role": "builder"}
    try:
        with store.lock("c1") as lock:  # the runner, another process than the host
            store.log(lock, "c1", who | {"event": "session", "id": "b1", "resumed": False})
            store.log(lock, "c1", who | {"event": "tool", "tool": "submit_result", "accepted": False, "errors": ["x"]})
            now = datetime.now(UTC)
            line = status(store.read("c1"), host.activity(store, "c1", host.running(store)), now).line
            assert line.startswith("Build 1/1 · fixing its refused result: greet · builder active")
            assert f"c1: {line}" in cli.show_status(store, now).splitlines()
    finally:
        os.close(host_fd)


def briefed(fake, *, approving: bool = False) -> Change:
    """Brief v2 saved after its loop ended on v1 (#986); *approving*: its round ended clean, the owner approving."""
    policy = RoundPolicy(max_rounds=3, max_findings=10, last_round_at=4, ask_owner_at=7)
    head, reason = ("2", "approve brief v2") if approving else ("1", "challenge brief v2, then approve it")
    ended = RoundLoop(subject=BRIEF, policy=policy, round=2, ended="clean", head=head)
    brief = Brief(version=2, challenged=int(head), requested=int(head), approve_if_clean=2 if approving else None)
    return Change(
        slug="c1", handle="c1", brief=brief, loops={BRIEF: ended}, step=Step(kind=StepKind.SHAPE),
        outcome=Outcome(exit=Exit.PENDING, waiting=Waiting.CHAT, who="you", reason=reason, at=NOW),
        names=Names(worktree=fake.worktree),
    )  # fmt: skip


def test_a_brief_version_saved_after_its_loop_ended_has_its_challenge_started_after_the_shapers_wait(store, tmp_path):
    fake = Fake(store, tmp_path)
    save(store, briefed(fake))
    assert fake.host.tick(NOW) == []
    assert store.read("c1").outcome.wake_at == NOW + timedelta(minutes=15)  # the save's time and the shaper's wait
    with store.lock("c1") as lock:  # a new save restarts the wait
        store.write(lock, briefs.drafted(store.read("c1"), BriefDraft.model_validate(DRAFT), "c1", "c1", Profile()))
    saved = store.read("c1").outcome
    assert (saved.wake_at, saved.at > NOW) == (None, True)
    assert fake.host.tick(NOW) == []
    assert store.read("c1").outcome.wake_at == saved.at + timedelta(minutes=15)
    assert fake.host.tick(saved.at + timedelta(minutes=14)) == []
    assert fake.host.tick(saved.at + timedelta(minutes=15)) == ["c1"]
    c = store.read("c1")
    assert (c.step.mode, c.brief.requested, c.loops[BRIEF].ended, c.outcome) == ("challenge", 3, "", None)


@pytest.mark.parametrize("pause", ["delivery", "change"])
def test_no_brief_challenge_starts_by_itself_while_delivery_or_the_change_is_paused(store, tmp_path, pause):
    fake, flag, later = Fake(store, tmp_path), [True], NOW + timedelta(minutes=16)
    save(store, briefed(fake))
    if pause == "delivery":
        paused(fake, flag)
    else:
        store.put_inbox("c1", IntentItem(at=NOW, intent="pause"))
    assert fake.host.tick(later) == []
    c = store.read("c1")
    assert (c.step.mode, c.brief.requested, c.outcome.wake_at) == (None, 1, NOW + timedelta(minutes=15))
    if pause == "delivery":
        flag[0] = False
    else:
        store.put_inbox("c1", IntentItem(at=later, intent="resume"))
    assert fake.host.tick(later) == ["c1"]
    assert store.read("c1").step.mode == "challenge"


def test_no_start_time_is_set_while_the_shapers_wait_is_unset(store, tmp_path, monkeypatch):
    shaper = config.BASE.agents["shaper"].model_copy(update={"challenge_wait": None})
    agents = config.BASE.agents | {"shaper": shaper}
    monkeypatch.setattr(config, "BASE", config.BASE.model_copy(update={"agents": agents}))
    fake = Fake(store, tmp_path)
    save(store, briefed(fake))
    assert fake.host.tick(NOW + timedelta(days=1)) == []
    assert store.read("c1").outcome.wake_at is None


def test_a_refused_approval_the_owner_asked_for_waits_for_him_with_its_whole_reason(store, tmp_path, monkeypatch):
    why = "brief v2 cannot be approved yet: the decision list could not be read: OSError: [Errno 5] /data: offline"
    monkeypatch.setattr(brief_routes, "approved", lambda *_a: why)
    fake = Fake(store, tmp_path)
    save(store, briefed(fake, approving=True))
    assert fake.host.tick(NOW) == []
    c = store.read("c1")
    assert (c.brief.approve_if_clean, c.brief.approved_version, c.outcome.cause) == (None, None, brief_starts.REFUSED)
    assert c.outcome.reason == f"approve brief v2: the approval you asked for was refused: {why}"
    http = client(store, fake)  # where it surfaces: the approval panel, Approve usable again, and the list, whole
    brief = http.get("/api/next/changes/c1").json()["brief"]
    assert (brief["approve_refused"], brief["approve_off"]) == (c.outcome.reason, "")
    (row,) = http.get("/api/next/changes").json()
    assert (row["error"], row["line"].endswith(why)) == (True, True)


def test_an_abandonment_queued_during_the_challenge_publishes_nothing(store, tmp_path, monkeypatch):
    called = []
    monkeypatch.setattr(brief_routes, "approved", lambda *a: called.append(a) or "")
    fake = Fake(store, tmp_path)
    save(store, briefed(fake, approving=True))
    store.put_inbox("c1", IntentItem(at=NOW, intent="abandon"))  # pressed while the round ran
    fake.host.tick(NOW)
    c = store.read("c1")
    assert (c.step.kind, c.brief.approved_version) == (StepKind.CLEANUP, None)
    assert (called, c.decisions_published) == ([], [])


class Killed(BaseException):
    """The host process, killed in the middle of its pass."""


def test_an_approval_killed_before_it_is_written_is_made_by_the_next_pass(store, tmp_path, monkeypatch):
    fake, real = Fake(store, tmp_path), brief_routes.approved
    save(store, briefed(fake, approving=True))

    def killed(*_a: object) -> str:
        raise Killed

    monkeypatch.setattr(brief_routes, "approved", killed)
    with pytest.raises(Killed):
        fake.host.tick(NOW)
    assert store.read("c1").brief.approve_if_clean == 2  # still the owner's: no press is lost
    monkeypatch.setattr(brief_routes, "approved", real)
    fake.host.tick(NOW)
    c = store.read("c1")
    assert (c.brief.approved_version, c.brief.approve_if_clean, c.step.kind) == (2, None, StepKind.PLAN)
    assert c.brief.approved[-1].approve_if_clean is None  # consumed with the approval, never kept in its copy
