"""Session limits at launch (TD-336): reservations, the wait outside the runner, the grant in the runner, pack jobs."""

import subprocess
import threading
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from owlbear_delivery_next.change_contracts import tools
from owlbear_delivery_next.change_contracts.inbox import IntentItem
from owlbear_delivery_next.change_contracts.models import Change, Exit, Names, Plan, Question, Step, StepKind, Task
from owlbear_delivery_next.change_contracts.permissions import Policy
from owlbear_delivery_next.change_flow.loop import StepResult, apply
from owlbear_delivery_next.change_flow.status import Activity, card, status
from owlbear_delivery_next.commands import runner
from owlbear_delivery_next.design_packs.design_pack import PackError
from owlbear_delivery_next.local_system import maintenance, processes
from owlbear_delivery_next.local_system.slots import Slots
from owlbear_delivery_next.pack_runs.pack_job import Live
from owlbear_delivery_next.project_host import session_slots
from owlbear_delivery_next.project_host.host import Host, RunnerRecord
from owlbear_delivery_next.runtimes import sdk_adapter
from owlbear_delivery_next.runtimes.session_result import Run
from owlbear_delivery_next.settings.config import Layer
from owlbear_delivery_next.state_store.store import Store
from owlbear_delivery_next.workflow_steps import sessions

NOW = datetime(2026, 10, 10, 12, tzinfo=UTC)
DONE = Run("done", termination=processes.Termination(confirmed=True))


def pack_session(root):
    """The configuration a pack session hands its maintenance ownership; the SDK never runs in these tests."""
    return sdk_adapter.Session(
        kind=StepKind.REVIEW, worktree=root, session_id="pack", message="pack", resume=False,
        policy=Policy(root), observe=lambda: tools.Worktree("", ""), checks=(), model="synthetic",
    )  # fmt: skip


def repo(path):
    path.mkdir(parents=True, exist_ok=True)
    for args in (
        ["init", "-q"],
        ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "i"],
    ):
        subprocess.run(["git", *args], cwd=path, check=True, capture_output=True)  # noqa: S603, S607
    return Store.open(path)


class Fake:
    """A project host whose runners stay alive until ended; *project* is its id among the shared slots."""

    def __init__(self, store, path, slots, project="p"):
        self.live, self.pid, self.store = set(), 100, store
        (path / "wt").mkdir(exist_ok=True)
        self.worktree = str(path / "wt")
        self.host = Host(store, path, spawn=self.spawn, scan=lambda *_a: {}, group=lambda _g: {})
        self.host.alive = lambda pid, _created: pid in self.live
        self.host.slots, self.host.record = slots, self.host.record.model_copy(update={"project": project})
        self.host.maintenance = maintenance.Maintenance(slots)  # bound by the machine host before any project starts
        session_slots.join(self.host)

    def spawn(self, _slug):
        self.pid += 1
        self.live.add(self.pid)
        return RunnerRecord(pid=self.pid, created=1.0, started_at=NOW)

    def ready(self, slug):
        plan = Plan(tasks=[Task(id="t1", title="greet", checks=["npm test"])])
        c = Change(slug=slug, plan=plan, step=Step(kind=StepKind.BUILD, task="t1"), names=Names(worktree=self.worktree))
        with self.store.lock(slug) as lock:
            self.store.write(lock, c)

    def asks(self, slug):
        """Its runner ends with a question: it waits for the owner, and its slot is free once it is gone."""
        asked = StepResult(exit=Exit.ASK, question=Question(step=StepKind.BUILD, text="?"))
        c = apply(self.store.read(slug), asked, NOW)
        with self.store.lock(slug) as lock:
            self.store.write(lock, c)
        self.live.discard(self.host.runner(slug).pid)

    def line(self, slug):
        return status(self.store.read(slug), self.host.activity(slug), NOW).line


@pytest.fixture
def store(tmp_path):
    return repo(tmp_path)


def test_a_change_waits_for_its_projects_slot_without_launching_and_owner_input_still_folds(store, tmp_path):
    fake = Fake(store, tmp_path, Slots(lambda: 4))
    assert (
        store.save(store.config_path, Layer, lambda cur: cur.model_copy(update={"sessions": 1}), "setup", owner=True)
        == ""
    )
    fake.ready("c1")
    fake.ready("c2")
    assert fake.host.tick(NOW) == ["c1"]
    assert (fake.host.runner("c1").sessions, fake.host.runner("c2")) == (1, None)
    assert "waiting for a session slot (this machine 1 of 4, this project 1 of 1)" in fake.line("c2")
    store.put_inbox("c2", IntentItem(at=NOW, intent="pause"))
    assert fake.host.tick(NOW) == []
    assert (store.read("c2").intent.paused_at, fake.host.activity("c2").waiting_slot) == (NOW, "")  # not waiting
    store.put_inbox("c2", IntentItem(at=NOW, intent="resume"))
    fake.asks("c1")
    fake.host.tick(NOW)
    assert (fake.host.runner("c1"), fake.host.runner("c2").sessions) == (None, 1)  # c1's slot went to c2


def test_waiters_of_one_project_keep_their_order_while_the_host_confirms_ended_runners(store, tmp_path):
    fake = Fake(store, tmp_path, Slots(lambda: 4))
    assert (
        store.save(store.config_path, Layer, lambda cur: cur.model_copy(update={"sessions": 1}), "setup", owner=True)
        == ""
    )
    for slug in ("c1", "c2", "c3"):
        fake.ready(slug)
    assert fake.host.tick(NOW) == ["c1"]
    assert fake.host.tick(NOW) == []  # c2 and c3 wait; each pass confirms them without a runner
    fake.asks("c1")
    assert fake.host.tick(NOW) == ["c2"]  # Sol: a release never requeues a waiter behind another
    fake.asks("c2")
    assert fake.host.tick(NOW) == ["c3"]


def test_a_pass_that_fails_still_forgets_the_waits_it_did_not_ask(store, tmp_path, monkeypatch):
    slots = Slots(lambda: 1)
    fake = Fake(store, tmp_path, slots)
    fake.ready("c1")
    fake.ready("c2")
    assert fake.host.tick(NOW) == ["c1"]
    assert set(slots.waiting) == {("p", "c2")}
    fake.asks("c1")
    monkeypatch.setattr(fake.host, "_one", lambda *_a: (_ for _ in ()).throw(PermissionError("settled")))
    with pytest.raises(PermissionError):
        fake.host.tick(NOW)
    assert slots.waiting == {}
    assert slots.take("q", "q1", 1, 1) == 0  # c1's ended runner still holds its slot
    slots.give("p", "c1")
    assert slots.take("q", "q1", 1, 1) == 1  # Sol: no stale wait of p owns the turn


def test_a_freed_slot_wakes_the_next_project_and_goes_round_robin(tmp_path):
    slots = Slots(lambda: 1)
    a = Fake(repo(tmp_path / "a"), tmp_path / "a", slots, "a")
    b = Fake(repo(tmp_path / "b"), tmp_path / "b", slots, "b")
    a.ready("a1")
    a.ready("a2")
    b.ready("b1")
    assert (a.host.tick(NOW), b.host.tick(NOW)) == (["a1"], [])
    assert "this machine 1 of 1, this project 0 of 2" in b.line("b1")
    b.host.wake.clear()
    a.asks("a1")
    assert a.host.tick(NOW) == []  # a2 waits: the turn after a is b's
    assert b.host.wake.is_set()
    assert b.host.tick(NOW) == ["b1"]


def test_a_restarted_host_counts_its_live_runners_before_anything_is_granted(store, tmp_path):
    fake = Fake(store, tmp_path, Slots(lambda: 1))
    fake.ready("c1")
    assert fake.host.tick(NOW) == ["c1"]
    slots = Slots(lambda: 1, closed=True)  # the machine host starts again; c1's runner still runs
    again = Fake(store, tmp_path, slots)
    again.live = fake.live
    slots.open()
    assert slots.take("q", "q1", 1, 2) == 0
    again.asks("c1")
    again.host.tick(NOW)
    assert slots.take("q", "q1", 1, 2) == 1


def test_a_step_without_an_agent_reserves_nothing_and_a_visual_check_asks_for_the_projects_limit(store, tmp_path):
    fake = Fake(store, tmp_path, Slots(lambda: 1))
    c = Change(slug="c1", step=Step(kind=StepKind.MERGE))
    assert [session_slots.wanted(c, s) for s in (None, Step(kind=StepKind.MERGE), Step(kind=StepKind.BUILD))] == [
        0,
        0,
        1,
    ]
    fake.host.wants["m1"] = 0
    assert fake.host.slots.take("q", "q1", 1, 1) == 1  # the machine is full
    assert session_slots.reserve(fake.host, "m1") == 0  # a merge still runs
    assert (
        store.save(store.config_path, Layer, lambda cur: cur.model_copy(update={"sessions": 3}), "setup", owner=True)
        == ""
    )
    fake.host.slots = Slots(lambda: 4)
    fake.host.wants["v1"] = session_slots.ALL
    assert session_slots.reserve(fake.host, "v1") == 3


def test_a_session_under_a_grant_of_0_is_refused_before_any_adapter_and_stops_the_change(store, tmp_path, monkeypatch):
    monkeypatch.setattr(sessions, "GRANT", 0)
    monkeypatch.setattr(sessions.sdk_adapter, "run", lambda _cfg: pytest.fail("an adapter started"))
    cfg = SimpleNamespace(job="", kind=StepKind.BUILD)
    with pytest.raises(sessions.SessionGrantError, match="no session slot"):
        sessions.run(store, cfg)
    Fake(store, tmp_path, Slots(lambda: 1)).ready("c1")
    monkeypatch.setattr(runner, "_agent", lambda *_a: sessions.run(store, cfg))
    c = store.read("c1")
    with store.lock("c1") as lock:
        runner._step(store, lock, c, c.step, tmp_path)  # noqa: SLF001
    after = store.read("c1")
    why = "Delivery started build with no session slot granted to its step"
    assert (after.outcome.exit, after.stop.reason) == (Exit.STOP, why)


def test_a_pack_updates_sessions_hold_the_projects_slots_and_its_wait_is_logged(store, tmp_path):
    fake = Fake(store, tmp_path, Slots(lambda: 1))
    assert fake.host.slots.take("p", "c1", 1, 2) == 1  # a step of the same project holds the only slot
    notes, ran = [], threading.Event()
    live = session_slots.pack_live(fake.host, Live(update=lambda *_a: ran.set() or DONE), notes.append)
    worker = threading.Thread(target=lambda: live.update(store, pack_session(tmp_path)))
    worker.start()
    worker.join(0.3)
    assert (ran.is_set(), notes) == (False, ["waiting for a session slot"])
    fake.host.slots.give("p", "c1")
    worker.join(5)
    assert ran.is_set()
    assert fake.host.slots.counts("p") == (0, 1, 0)  # given back once the session call returned


def test_a_pack_update_waiting_when_owlbear_stops_gives_up_its_place(store, tmp_path):
    fake = Fake(store, tmp_path, Slots(lambda: 1))
    fake.host.slots.take("q", "q1", 1, 1)
    fake.host.stopped.set()
    live = session_slots.pack_live(fake.host, Live(challenge=lambda *_a: pytest.fail("ran")), lambda _n: None)
    with pytest.raises(PackError, match="did not get a session slot"):
        live.challenge(store, pack_session(tmp_path))
    assert fake.host.slots.waiting == {}


def test_the_card_shows_the_judges_left_while_a_round_runs_in_waves():
    c = Change(slug="c1", step=Step(kind=StepKind.CHECK, task="visual", started_at=NOW))
    wave = {"event": "wave", "at": NOW.isoformat(), "left": 3}
    later = {"event": "tool", "at": NOW.isoformat(), "tool": tools.VISUAL_REVIEW.name}
    assert card(c, Activity(host_up=True, runner_alive=True), [wave, later], NOW)["now"].endswith(" · 3 judges left")
    old = c.model_copy(update={"step": c.step.model_copy(update={"started_at": NOW.replace(hour=13)})})
    assert "judges left" not in card(old, Activity(host_up=True, runner_alive=True), [wave], NOW)["now"]
