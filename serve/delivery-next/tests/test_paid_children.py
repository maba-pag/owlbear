"""RUN-04: a paid child session started after an accepted held parent (a plan challenge, TD-190; an amendment
challenge, TD-179) runs once and counts once, whichever write fails, and the owner's later controls win.

Each case runs the runner's own step entry against a temporary store and Git repository, with a fake SDK: the held
parent's session ran once at its gate, the owner accepts it through the inbox, one write, log or cleanup fails, and
fresh stores fold and restart the step until the next step's session starts.
"""

import json
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from owlbear_delivery_next.change_contracts import failures, tool_schema, tools
from owlbear_delivery_next.change_contracts.held_records import PendingChild
from owlbear_delivery_next.change_contracts.inbox import AnswerItem, IntentItem
from owlbear_delivery_next.change_contracts.models import (
    Brief,
    Change,
    Criterion,
    Exit,
    Names,
    Plan,
    Step,
    StepKind,
    Task,
)
from owlbear_delivery_next.change_contracts.round_records import PLAN, RoundLoop, RoundPolicy
from owlbear_delivery_next.change_flow import loop
from owlbear_delivery_next.commands import runner
from owlbear_delivery_next.local_system.processes import Termination
from owlbear_delivery_next.runtimes import amendments
from owlbear_delivery_next.runtimes.session_result import Run
from owlbear_delivery_next.state_store.store import Lock, Store, StoreError
from owlbear_delivery_next.workflow_steps import disposable, held, pending_child, plan_round, sessions

K = StepKind
DONE = Termination(confirmed=True)
FEW = RoundPolicy(max_rounds=3, max_findings=5, last_round_at=0, ask_owner_at=1)
UNREAD = "the usage at the step's end could not be read (RuntimeError)"
PARENT = {  # the held parent's usage, counted at its gate: (usage, why unread, credits, unread sessions)
    "known": ({"credits": 2.5, "models": {"m": {"credits": 2.5, "tokens": 100}}}, "the model could not be read", 2.5),
    "unread": ({"error": "RuntimeError"}, UNREAD, 0.0),
}
CHILD = {"credits": 3.5, "models": {"c": {"credits": 3.5, "tokens": 40}}}
LABELS = {"plan": plan_round.LABEL, "amend": amendments.LABEL}


class NextSessionError(Exception):
    """The step after the settled one started its session: the fake worker boundary."""


def git(cwd: Path, *args: str) -> str:
    done = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)  # noqa: S603, S607
    return done.stdout.strip()


class Paid:
    """The fake SDK: the held parent's one session, then each paid child; any later session is the next step's."""

    def __init__(self, monkeypatch, repo: Path, parent: str, usage: str) -> None:
        self.repo, self.parent, self.usage = repo, parent, usage
        self.parents: list[str] = []
        self.children: list[str] = []
        self.next: list[str] = []
        self.verdicts: list[tools.Args] = []
        self.unread_children = 0  # how many of the next children return with their usage unread
        self.wrong_children = 0  # how many of the next children ran on a wrong model
        monkeypatch.setattr(runner.sdk_adapter, "run", self.run)
        monkeypatch.setattr(runner.worktree, "ensure", lambda *_a: repo)  # the Change's worktree is the test repo

    async def run(self, cfg):
        if cfg.job in LABELS.values():
            self.children.append(cfg.session_id)
            run = Run(cfg.session_id, "result", self.verdicts.pop(0), termination=DONE)
            run.usage, run.tool_calls, run.model_check = dict(CHILD), {"grep": {"calls": 2}}, "verified"
            run.wrong = {"denied": 1}
            if self.unread_children:
                self.unread_children -= 1
                run.usage, run.usage_unread = {"error": "RuntimeError"}, UNREAD
            elif self.wrong_children:
                self.wrong_children -= 1
                run.model_check, run.detail = "mismatch", "the session ran on another model"
            return run
        if self.parents:
            self.next.append(cfg.session_id)
            raise NextSessionError
        self.parents.append(cfg.session_id)
        usage, reason, _ = PARENT[self.usage]
        if self.parent == "plan":
            run = Run(cfg.session_id, "result", tools.PlanResult(tasks=[task(1)]), termination=DONE)
        else:
            payload, _ = tool_schema.parse(tools.WrongPremise, premise())
            run = Run(cfg.session_id, "premise", payload, head=git(self.repo, "rev-parse", "HEAD"), termination=DONE)
        run.usage, run.usage_unread, run.tool_calls = dict(usage), reason, {"bash": {"calls": 3}}
        run.wrong = {"no_result": 1}
        return run


def task(n: int) -> dict:
    return {"title": f"step {n}", "goal": "AC-1", "scope": ["src"], "checks": ["true"]}


def premise() -> dict:
    items = [{"criterion": "AC-1", "text": "greet() trims spaces, not tabs", "why": "tabs are not names"}]
    return {"stage": "brief", "reason": "AC-1 is over-specific", "evidence": ["a.txt:1"], "amendment": items}


def made(parent: str, repo: Path) -> Change:
    names = Names(branch="owlbear/c1", target="main", worktree=str(repo))
    if parent == "plan":
        c = Change(slug="c1", brief=Brief(version=1, approved_version=1, challenged=1), step=Step(kind=K.PLAN))
        c.names = names
        c.loops[PLAN] = RoundLoop(subject=PLAN, policy=FEW)
        return c
    criteria = [Criterion(id="AC-1", text="greet() trims the name"), Criterion(id="AC-2", text="Says Hallo", version=2)]
    brief = Brief(version=3, approved_version=3, challenged=3, criteria=criteria, specified=["AC-2"])
    plan = Plan(tasks=[Task(id="t1", title="one", scope=["a.txt"])])
    return Change(slug="c1", brief=brief, plan=plan, names=names, step=Step(kind=K.BUILD, task="t1"))


def restart(tmp_path: Path, repo: Path, now: datetime | None = None) -> Store:
    """A new runner process: a fresh store, the inbox folded under the lock, the step run."""
    store = Store(tmp_path / "store")
    with store.lock("c1") as lock:
        change, step = store.fold(lock, "c1", now or datetime.now(UTC))
        runner._step(store, lock, change, step, repo)  # noqa: SLF001
    return store


def passing(parent: str) -> tools.Args:
    """A challenger's passing verdict in the form its parent's challenge submits."""
    return tools.ReviewResult(verdict="pass") if parent == "plan" else tools.VisualReviewResult(verdict="pass")


def held_and_accepted(tmp_path: Path, repo: Path, paid: Paid, parent: str) -> Store:
    """The parent's session returned with its usage unread: held, counted at its gate, then accepted in the inbox."""
    store = Store(tmp_path / "store")
    store.write(Lock("c1"), made(parent, repo))
    paid.verdicts = [passing(parent)]
    restart(tmp_path, repo)
    gated = store.read("c1")
    q = loop.open_question(gated)
    assert q is not None
    assert [o.id for o in q.options] == ["accept", "retry"]
    assert (len(paid.parents), paid.children) == (1, [])
    store.put_inbox("c1", AnswerItem(at=datetime.now(UTC), question=q.id, option="accept"))
    return store


def to_next_session(tmp_path: Path, repo: Path, limit: int = 4, now: datetime | None = None) -> Store:
    """Restart until the step after the settled one starts its session; cleanup may take a pass of its own."""
    for _ in range(limit):
        try:
            restart(tmp_path, repo, now)
        except NextSessionError:
            return Store(tmp_path / "store")
    pytest.fail("the step after the settled one never started")


def captures(store: Store) -> list[Path]:
    return sorted((store.root / "changes" / "c1").glob(f"{pending_child.CAPTURE}*.json"))


def child_steps(store: Store, label: str) -> list[dict]:
    return [e for e in store.events("c1") if e.get("event") == "step" and e.get("kind") == label]


def assert_settled_once(store: Store, parent: str, usage: str, paid: Paid) -> Change:
    """The parent applied once, its child run and counted once, each count and record exactly once."""
    c = store.read("c1")
    assert (len(paid.parents), len(paid.children), len(paid.next)) == (1, 1, 1)
    assert c.pending_child is None
    assert c.spend.credits == pytest.approx(PARENT[usage][2] + CHILD["credits"])
    assert c.spend.unread == (paid.parents if usage == "unread" else [])
    assert c.spend.models["c"].tokens == 40
    assert (c.tool_use.tools["bash"].calls, c.tool_use.tools["grep"].calls) == (3, 2)
    assert c.tool_use.wrong == {"no_result": 1, "denied": 1}
    assert len(c.accepted_holds) == len(c.counted_holds) == 1
    assert c.counted_children == paid.children
    assert captures(store) == []
    assert not (store.root / "changes" / "c1" / "held.json").exists()
    assert c.held_fallback is None
    accepted = [e["session"] for e in store.events("c1") if e.get("event") == "held-accepted"]
    assert accepted == paid.parents
    assert len([e for e in store.events("c1") if e.get("event") == "step" and e.get("held")]) == 1
    if parent == "plan":
        assert (c.plan.version, c.loops[PLAN].round, c.step.kind) == (1, 1, K.BUILD)
        assert [t.title for t in c.plan.tasks] == ["step 1"]
    else:
        (a,) = c.amendments
        assert (a.verdict, a.session, a.challenger) == ("equivalent", paid.parents[0], paid.children[0])
        assert (c.step.kind, c.outcome.exit) == (K.PLAN, Exit.BACK)  # the proposer's own route
    return c


FAULTS = [
    "checkpoint-write",
    "capture-write",
    "settlement-write",
    "settlement-log",
    "hold-unlink",
    "accepted-log",
    "fallback-clear",
]
REPROCESSED = {"checkpoint-write", "accepted-log"}  # faults that process the hold again, where usage shows a recount


def fault_cases():
    """Every fault for both parents; usage only for the faults it can change, alternating elsewhere."""
    for i, fault in enumerate(FAULTS):
        for j, parent in enumerate(["plan", "amend"]):
            usages = ["known", "unread"] if fault in REPROCESSED else [["known", "unread"][(i + j) % 2]]
            for usage in usages:
                yield pytest.param(parent, usage, fault, id=f"{parent}-{usage}-{fault}")


@pytest.mark.parametrize(("parent", "usage", "fault"), list(fault_cases()))
def test_an_accepted_parent_and_its_paid_child_run_and_count_once_whichever_write_fails(  # noqa: C901, PLR0913, PLR0915, PLR0917
    tmp_path, change_repo, monkeypatch, parent, usage, fault
):
    paid = Paid(monkeypatch, change_repo, parent, usage)
    label, held_file = LABELS[parent], tmp_path / "store" / "changes" / "c1" / "held.json"
    real_write, real_log, real_unlink, real_atomic = Store.write, Store.log, Path.unlink, held.atomic_write
    armed = [fault]

    def fire(stage: str) -> None:
        if armed == [stage]:
            armed.clear()
            msg = f"{stage} refused"
            raise OSError(msg)

    def write(self, lock, change):
        stored = self.read(change.slug)
        if change.accepted_holds and not stored.accepted_holds:
            fire("checkpoint-write")
        returned = change.pending_child and change.pending_child.run
        if returned and not (stored.pending_child and stored.pending_child.run):
            fire("capture-write")  # the first write of the returned child's run
        if stored.pending_child and stored.pending_child.run and change.pending_child is None:
            fire("settlement-write")
        if stored.held_fallback and change.held_fallback is None and change.accepted_holds:
            fire("fallback-clear")
        return real_write(self, lock, change)

    def log(self, lock, slug, event):
        if event.get("event") == "step" and event.get("kind") == label:
            fire("settlement-log")
        if event.get("event") == "held-accepted":
            fire("accepted-log")
        return real_log(self, lock, slug, event)

    def unlink(self, *args, **kwargs):
        if self == held_file:
            fire("hold-unlink")
        return real_unlink(self, *args, **kwargs)

    def no_file(path, text):  # the hold lives in the Change's fallback, which the checkpoint's cleanup clears
        if path == held_file:
            msg = "held file refused"
            raise OSError(msg)
        return real_atomic(path, text)

    if fault == "fallback-clear":
        monkeypatch.setattr(held, "atomic_write", no_file)
    held_and_accepted(tmp_path, change_repo, paid, parent)
    monkeypatch.setattr(Store, "write", write)
    monkeypatch.setattr(Store, "log", log)
    monkeypatch.setattr(Path, "unlink", unlink)
    with pytest.raises(OSError, match=f"{fault} refused"):
        restart(tmp_path, change_repo)
    assert not armed

    after = Store(tmp_path / "store").read("c1")
    if fault == "checkpoint-write":  # nothing durable: the hold is processed again, its child never ran
        assert (after.accepted_holds, after.pending_child, paid.children) == ([], None, [])
    elif fault == "settlement-write":  # the child's validated run is durable, its spend not yet counted
        assert after.pending_child is not None
        assert after.pending_child.run is not None
        assert after.pending_child.run.session_id == paid.children[0]
        assert after.pending_child.run.usage == CHILD
        assert after.spend.credits == pytest.approx(PARENT[usage][2])
    elif fault == "capture-write":  # the Change lacks the run; its capture keeps the same run for the next runner
        assert after.pending_child is None or after.pending_child.run is None
        (path,) = captures(Store(tmp_path / "store"))
        kept = json.loads(path.read_text())["run"]
        assert (kept["session_id"], kept["usage"]) == (paid.children[0], CHILD)
        assert (kept["tool_calls"], kept["wrong"]) == ({"grep": {"calls": 2}}, {"denied": 1})
        assert after.spend.credits == pytest.approx(PARENT[usage][2])
    else:
        assert len(after.accepted_holds) == 1  # the receipt is durable: the parent is never processed again
    if fault != "checkpoint-write":
        assert child_steps(Store(tmp_path / "store"), label) == []  # logged only once its settlement is durable

    store = to_next_session(tmp_path, change_repo)
    assert_settled_once(store, parent, usage, paid)
    assert len(child_steps(store, label)) == (0 if fault == "settlement-log" else 1)


def settlement_fails(tmp_path, change_repo, monkeypatch, parent) -> Paid:
    """An accepted parent whose child returned and was kept, while the write settling it failed."""
    paid = Paid(monkeypatch, change_repo, parent, "known")
    held_and_accepted(tmp_path, change_repo, paid, parent)
    fail_settlement(tmp_path, change_repo, monkeypatch)
    return paid


def fail_settlement(tmp_path, change_repo, monkeypatch) -> None:
    """One restart whose write settling the kept child fails; the writes after it succeed."""
    real_write = Store.write
    armed = [True]

    def write(self, lock, change):
        stored = self.read(change.slug).pending_child
        if armed and stored and stored.run and change.pending_child is None:
            armed.clear()
            msg = "settlement refused"
            raise OSError(msg)
        return real_write(self, lock, change)

    monkeypatch.setattr(Store, "write", write)
    with pytest.raises(OSError, match="settlement refused"):
        restart(tmp_path, change_repo)
    monkeypatch.setattr(Store, "write", real_write)


@pytest.mark.parametrize("parent", ["plan", "amend"])
def test_a_pause_queued_after_a_failed_settlement_waits_and_the_resume_settles_from_the_kept_run(
    tmp_path, change_repo, monkeypatch, parent
):
    paid = settlement_fails(tmp_path, change_repo, monkeypatch, parent)
    store = Store(tmp_path / "store")
    store.put_inbox("c1", IntentItem(at=datetime.now(UTC), intent="pause", text="hold on"))
    paused = restart(tmp_path, change_repo).read("c1")
    assert paused.intent.paused_at is not None
    assert paused.intent.pause_reason == "hold on"
    assert paused.pending_child is not None  # it waits with its step; nothing is paid or lost
    assert (len(paid.children), paused.spend.credits) == (1, pytest.approx(2.5))

    store.put_inbox("c1", IntentItem(at=datetime.now(UTC), intent="resume"))
    done = to_next_session(tmp_path, change_repo)
    assert done.read("c1").intent.paused_at is None
    assert_settled_once(done, parent, "known", paid)
    assert len(child_steps(done, LABELS[parent])) == 1


@pytest.mark.parametrize("intent", ["abandon", "change"])
@pytest.mark.parametrize("parent", ["plan", "amend"])
def test_an_abandon_or_new_brief_after_a_failed_settlement_counts_the_child_once_and_routes_nothing(
    tmp_path, change_repo, monkeypatch, parent, intent
):
    paid = settlement_fails(tmp_path, change_repo, monkeypatch, parent)
    store = Store(tmp_path / "store")
    before = store.read("c1")
    store.put_inbox("c1", IntentItem(at=datetime.now(UTC), intent=intent, text="a different greeting"))
    engine = []
    monkeypatch.setattr(runner, "_engine", lambda *a: engine.append(a[2].step.kind))  # the next step's own work
    for _ in range(2):  # a second restart changes nothing
        c = restart(tmp_path, change_repo).read("c1")
    assert c.pending_child is None
    assert (len(paid.children), c.spend.credits) == (1, pytest.approx(2.5 + 3.5))
    assert c.tool_use.tools["grep"].calls == 2
    assert [e["exit"] for e in child_steps(store, LABELS[parent])] == ["retired"]
    if intent == "abandon":
        assert (c.intent.abandoned_at is not None, c.step.kind) == (True, K.CLEANUP)
    else:
        assert (c.intent.words, c.step.kind) == ("a different greeting", K.SHAPE)
    if parent == "plan":
        assert c.loops[PLAN].round == before.loops[PLAN].round  # the plan it challenged is gone: no round counted
    else:
        assert [a.verdict for a in c.amendments] == ["equivalent"]  # the candidate keeps its verdict
    assert c.questions == before.questions
    assert engine
    assert set(engine) <= {K.CLEANUP, K.SHAPE}


def ask_store(tmp_path, change_repo, monkeypatch) -> tuple[Paid, Store]:
    """Round 1 sends the plan back; round 2's planner rejects F1, held and accepted; its challenger upholds F1."""
    paid = Paid(monkeypatch, change_repo, "plan", "known")
    store = Store(tmp_path / "store")
    store.write(Lock("c1"), made("plan", change_repo))
    first = tools.ReviewResult(verdict="fix", findings=[{"place": "t1", "problem": "AC-1 untested", "fix": "add"}])
    upheld = tools.ReviewResult(verdict="pass", rechecked=[{"finding": "F1", "upheld": True, "reason": "see t1"}])
    paid.verdicts = [first, upheld]
    rejected = [{"finding": "F1", "reason": "covered"}]
    plans = [tools.PlanResult(tasks=[task(1)]), tools.PlanResult(tasks=[task(1)], rejected=rejected)]

    async def planner(cfg):
        if cfg.job in LABELS.values():
            return await Paid.run(paid, cfg)
        if len(paid.parents) == len(plans):
            paid.next.append(cfg.session_id)
            raise NextSessionError
        paid.parents.append(cfg.session_id)
        run = Run(cfg.session_id, "result", plans[len(paid.parents) - 1], termination=DONE)
        if len(paid.parents) == 2:  # the second planner's usage stays unread: held
            run.usage, run.usage_unread = dict(PARENT["known"][0]), PARENT["known"][1]
        return run

    monkeypatch.setattr(runner.sdk_adapter, "run", planner)
    restart(tmp_path, change_repo)  # round 1: the plan goes back with F1
    assert store.read("c1").outcome.exit == Exit.RETRY
    restart(tmp_path, change_repo)  # round 2's planner: held at its gate
    q = loop.open_question(store.read("c1"))
    store.put_inbox("c1", AnswerItem(at=datetime.now(UTC), question=q.id, option="accept"))
    return paid, store


@pytest.mark.parametrize("then", ["pause", "abandon", "answer"])
def test_an_upheld_rejection_asks_once_with_a_stable_question_whatever_the_owner_does_next(
    tmp_path, change_repo, monkeypatch, then
):
    paid, store = ask_store(tmp_path, change_repo, monkeypatch)
    fail_settlement(tmp_path, change_repo, monkeypatch)
    restart(tmp_path, change_repo)
    asked = store.read("c1")
    q = loop.open_question(asked)
    assert q is not None
    assert [o.id for o in q.options] == ["fix", "reconsider", "drop"]
    ids = [x.id for x in asked.questions]
    restart(tmp_path, change_repo)  # waiting on the owner: nothing runs, nothing is asked again
    assert [x.id for x in store.read("c1").questions] == ids
    assert (len(paid.parents), len(paid.children)) == (2, 2)

    if then == "answer":
        store.put_inbox("c1", AnswerItem(at=datetime.now(UTC), question=q.id, option="fix"))
        to_next_session(tmp_path, change_repo)  # the planner's next round: the owner's progress
        assert len(paid.next) == 1
    else:
        monkeypatch.setattr(runner, "_engine", lambda *_a: None)
        store.put_inbox("c1", IntentItem(at=datetime.now(UTC), intent=then))
        restart(tmp_path, change_repo)
        assert paid.next == []
    c = store.read("c1")
    assert [x.id for x in c.questions] == ids
    assert c.pending_child is None
    assert (c.loops[PLAN].round, len(paid.children)) == (2, 2)
    assert c.spend.credits == pytest.approx(2.5 + 2 * 3.5)
    assert c.tool_use.tools["grep"].calls == 4
    assert len(child_steps(store, plan_round.LABEL)) == 2
    if then == "pause":
        assert c.intent.paused_at is not None
        assert loop.open_question(c).id == q.id
    if then == "abandon":
        assert c.intent.abandoned_at is not None


@pytest.mark.parametrize("parent", ["plan", "amend"])
def test_a_child_whose_own_usage_is_unread_takes_its_own_gate_and_its_retry_reruns_only_the_child(
    tmp_path, change_repo, monkeypatch, parent
):
    paid = Paid(monkeypatch, change_repo, parent, "known")
    store = held_and_accepted(tmp_path, change_repo, paid, parent)
    paid.verdicts.append(paid.verdicts[0])
    paid.unread_children = 1
    restart(tmp_path, change_repo)
    c = store.read("c1")
    q = loop.open_question(c)
    assert q is not None
    assert [o.id for o in q.options] == ["retry"]  # the owner's accept of the parent never waives the child's check
    assert (c.step.kind, len(c.accepted_holds), len(paid.children)) == (K.PLAN if parent == "plan" else K.BUILD, 1, 1)
    assert c.spend.unread == paid.children  # the child's own usage is unknown, never zero
    assert c.spend.credits == pytest.approx(2.5)
    if parent == "plan":
        assert (c.plan.version, c.loops[PLAN].round) == (1, 0)  # the plan stays checkpointed, unjudged
    else:
        assert [a.verdict for a in c.amendments] == [""]

    store.put_inbox("c1", AnswerItem(at=datetime.now(UTC), question=q.id, option="retry"))
    done = to_next_session(tmp_path, change_repo)
    c = done.read("c1")
    assert (len(paid.parents), len(paid.children), len(paid.next)) == (1, 2, 1)  # the retry reran the child alone
    assert (c.spend.credits, c.spend.unread) == (pytest.approx(2.5 + 3.5), paid.children[:1])
    assert (c.tool_use.tools["bash"].calls, c.tool_use.tools["grep"].calls) == (3, 4)  # each attempt once
    assert c.tool_use.wrong == {"no_result": 1, "denied": 2}
    assert (c.counted_children, c.pending_child) == (paid.children, None)  # each child's receipt once
    if parent == "plan":
        assert (c.plan.version, c.loops[PLAN].round, c.step.kind) == (1, 1, K.BUILD)
    else:
        (a,) = c.amendments  # the same candidate of the same proposer, judged by the retried child
        assert (a.verdict, a.session, a.challenger) == ("equivalent", paid.parents[0], paid.children[1])
        assert (c.step.kind, c.outcome.exit) == (K.PLAN, Exit.BACK)


@pytest.mark.parametrize("parent", ["plan", "amend"])
def test_a_child_on_a_wrong_model_judges_nothing_and_its_rerun_after_the_wait_does(
    tmp_path, change_repo, monkeypatch, parent
):
    paid = Paid(monkeypatch, change_repo, parent, "known")
    store = held_and_accepted(tmp_path, change_repo, paid, parent)
    paid.verdicts.append(paid.verdicts[0])
    paid.wrong_children = 1
    restart(tmp_path, change_repo)
    c = store.read("c1")
    assert (c.outcome.exit, c.outcome.cause.endswith(":wrong-model")) == (Exit.RETRY, True)
    assert c.outcome.wake_at is not None
    assert (c.step.kind, c.counted_children) == (K.PLAN if parent == "plan" else K.BUILD, paid.children)
    assert len(paid.children) == 1
    assert c.spend.credits == pytest.approx(2.5 + 3.5)  # the wrong model's attempt counts once, as it reported
    if parent == "plan":
        assert (c.loops[PLAN].round, c.step.mode) == (0, "challenge")
    else:
        assert [a.verdict for a in c.amendments] == [""]  # its payload never judges the candidate
        assert c.pending_child is not None  # the same candidate waits for the next challenger
        assert (c.pending_child.parent, c.pending_child.run) == (c.amendments[0].id, None)
    restart(tmp_path, change_repo)  # within the wait: nothing runs
    assert len(paid.children) == 1

    later = c.outcome.wake_at + timedelta(seconds=1)
    done = to_next_session(tmp_path, change_repo, now=later)
    c = done.read("c1")
    assert (len(paid.parents), len(paid.children), len(paid.next)) == (1, 2, 1)
    assert c.spend.credits == pytest.approx(2.5 + 2 * 3.5)
    assert (c.tool_use.tools["bash"].calls, c.tool_use.tools["grep"].calls) == (3, 4)
    assert (c.counted_children, c.pending_child) == (paid.children, None)
    if parent == "plan":
        assert (c.loops[PLAN].round, c.step.kind) == (1, K.BUILD)
    else:
        (a,) = c.amendments
        assert (a.verdict, a.session, a.challenger) == ("equivalent", paid.parents[0], paid.children[1])
        assert (c.step.kind, c.outcome.exit) == (K.PLAN, Exit.BACK)


def test_a_child_run_no_storage_keeps_is_printed_and_reported_never_claimed(tmp_path, change_repo, monkeypatch, capsys):
    paid = Paid(monkeypatch, change_repo, "plan", "known")
    held_and_accepted(tmp_path, change_repo, paid, "plan")
    paid.verdicts.append(paid.verdicts[0])
    real_write = Store.write

    def write(self, lock, change):
        if change.pending_child and change.pending_child.run:
            msg = "change refused"
            raise OSError(msg)
        return real_write(self, lock, change)

    def no_capture(path, _text):
        msg = f"{path.name} refused"
        raise OSError(msg)

    monkeypatch.setattr(Store, "write", write)
    monkeypatch.setattr(pending_child, "atomic_write", no_capture)
    with pytest.raises(OSError, match="change refused") as failed:
        restart(tmp_path, change_repo)
    assert any("could not be kept" in note for note in failed.value.__notes__)
    printed = [json.loads(line) for line in capsys.readouterr().out.splitlines() if "child-unkept" in line]
    assert [p["child"]["run"]["session_id"] for p in printed] == paid.children
    monkeypatch.setattr(Store, "write", real_write)
    store = to_next_session(tmp_path, change_repo)
    c = store.read("c1")
    assert len(paid.children) == 2  # nothing kept the first run, so its challenge ran again, as reported
    assert (c.counted_children, c.spend.credits) == (paid.children[1:], pytest.approx(2.5 + 3.5))


CLEANUPS = ["cleanup", "cleanup+capture-write", "cleanup+both-media"]


@pytest.mark.parametrize("parent", ["plan", "amend"])
def test_a_kept_child_whose_result_no_longer_loads_counts_once_judges_nothing_and_its_challenge_reruns(
    tmp_path, change_repo, monkeypatch, parent
):
    paid = settlement_fails(tmp_path, change_repo, monkeypatch, parent)
    paid.verdicts.append(passing(parent))
    store = Store(tmp_path / "store")
    data = json.loads(stored(store))
    data["pending_child"]["run"]["payload"]["model"] = "NoSuchResult"
    with store.db.write() as db:
        db.execute("UPDATE changes SET record = ? WHERE slug = 'c1'", (json.dumps(data),))
    c = restart(tmp_path, change_repo).read("c1")
    assert (c.counted_children, c.spend.credits) == (paid.children, pytest.approx(2.5 + 3.5))
    assert (c.outcome.exit, c.outcome.cause is not None) == (Exit.RETRY, True)  # a failed attempt, judging nothing
    if parent == "plan":
        assert (c.loops[PLAN].round, c.step.mode) == (0, "challenge")
    else:
        assert [a.verdict for a in c.amendments] == [""]

    c = restart(tmp_path, change_repo).read("c1")  # its retry: a new challenger, never the parent again
    assert (len(paid.parents), len(paid.children)) == (1, 2)
    assert (c.counted_children, c.spend.credits) == (paid.children, pytest.approx(2.5 + 2 * 3.5))
    if parent == "plan":
        assert (c.loops[PLAN].round, c.step.kind) == (1, K.BUILD)
    else:
        (a,) = c.amendments
        assert (a.verdict, a.session, a.challenger) == ("equivalent", paid.parents[0], paid.children[1])


@pytest.mark.parametrize("fault", CLEANUPS)
@pytest.mark.parametrize("parent", ["plan", "amend"])
def test_a_confirmed_child_whose_read_only_cleanup_fails_is_kept_before_it_and_never_paid_again(  # noqa: C901, PLR0913, PLR0915, PLR0917
    tmp_path, change_repo, monkeypatch, capsys, parent, fault
):
    paid = Paid(monkeypatch, change_repo, parent, "known")
    held_and_accepted(tmp_path, change_repo, paid, parent)
    paid.verdicts.append(paid.verdicts[0])
    real_unlink, real_write = Path.unlink, Store.write
    armed = set(fault.split("+"))

    def unlink(self, *args, **kwargs):
        if "cleanup" in armed and self.name == disposable.LIVE:  # after the child returned, its processes gone
            armed.discard("cleanup")
            assert paid.children, "the cleanup fails only after the confirmed child returned"
            msg = "cleanup refused"
            raise OSError(msg)
        return real_unlink(self, *args, **kwargs)

    def write(self, lock, change):
        returned = change.pending_child and change.pending_child.run
        if returned and armed & {"capture-write", "both-media"}:
            armed.difference_update({"capture-write", "both-media"})
            msg = "change refused"
            raise OSError(msg)
        return real_write(self, lock, change)

    def no_capture(path, _text):
        msg = f"{path.name} refused"
        raise OSError(msg)

    monkeypatch.setattr(Path, "unlink", unlink)
    monkeypatch.setattr(Store, "write", write)
    if fault == "cleanup+both-media":
        monkeypatch.setattr(pending_child, "atomic_write", no_capture)
    with pytest.raises(OSError, match="cleanup refused") as failed:  # the cleanup's own failure, as it is
        restart(tmp_path, change_repo)
    assert not armed
    monkeypatch.setattr(Path, "unlink", real_unlink)
    monkeypatch.setattr(Store, "write", real_write)
    after = Store(tmp_path / "store")
    kept = after.read("c1").pending_child
    if fault == "cleanup":  # kept with its Change before the cleanup ran
        assert kept is not None
        assert kept.run is not None
        assert (kept.run.session_id, kept.run.usage) == (paid.children[0], CHILD)
    elif fault == "cleanup+capture-write":  # its Change write failed too: its capture keeps the same run
        (path,) = captures(after)
        assert json.loads(path.read_text())["run"]["session_id"] == paid.children[0]
        assert isinstance(failed.value.__context__, OSError)
    else:  # nothing kept it: it is printed and the error says so, never claimed
        assert "change refused" in str(failed.value.__context__)
        assert any("could not be kept" in n for n in failed.value.__context__.__notes__)
        printed = [json.loads(x) for x in capsys.readouterr().out.splitlines() if "child-unkept" in x]
        assert [p["child"]["run"]["session_id"] for p in printed] == paid.children
        assert captures(after) == []

    if fault == "cleanup+both-media":
        (live := after.root / "changes" / "c1" / disposable.LIVE).unlink()  # the owner confirmed it gone
        assert not live.exists()
    restart(tmp_path, change_repo)
    c = Store(tmp_path / "store").read("c1")
    honest = fault == "cleanup+both-media"  # its challenge ran again, as reported; only that run counted
    assert (len(paid.parents), len(paid.children)) == (1, 2 if honest else 1)
    assert (c.counted_children, c.pending_child) == (paid.children[-1:], None)
    assert c.spend.credits == pytest.approx(2.5 + 3.5)
    assert (c.tool_use.tools["bash"].calls, c.tool_use.tools["grep"].calls) == (3, 2)
    assert captures(Store(tmp_path / "store")) == []
    if parent == "plan":
        assert (c.plan.version, c.loops[PLAN].round, c.step.kind) == (1, 1, K.BUILD)
    else:
        (a,) = c.amendments
        assert (a.verdict, a.session, a.challenger) == ("equivalent", paid.parents[0], paid.children[-1])
        assert (c.step.kind, c.outcome.exit) == (K.PLAN, Exit.BACK)


@pytest.mark.parametrize("parent", ["plan", "amend"])
def test_an_unread_child_whose_cleanup_fails_keeps_its_own_gate_and_count_until_the_owner_retries(
    tmp_path, change_repo, monkeypatch, parent
):
    paid = Paid(monkeypatch, change_repo, parent, "known")
    store = held_and_accepted(tmp_path, change_repo, paid, parent)
    paid.verdicts.append(passing(parent))
    paid.unread_children = 1
    real_unlink, armed = Path.unlink, [True]

    def unlink(self, *args, **kwargs):
        if armed and self.name == disposable.LIVE:
            armed.clear()
            msg = "cleanup refused"
            raise OSError(msg)
        return real_unlink(self, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", unlink)
    with pytest.raises(OSError, match="cleanup refused") as failed:  # the cleanup's own failure, as it is
        restart(tmp_path, change_repo)
    assert isinstance(failed.value.__context__, sessions.UsageUnreadError)
    monkeypatch.setattr(Path, "unlink", real_unlink)
    (store.root / "changes" / "c1" / disposable.LIVE).unlink()  # its process ended: only the stale marker is cleared

    for _ in range(2):  # the child's own gate waits for the owner: nothing runs, nothing counts again
        c = restart(tmp_path, change_repo).read("c1")
        q = loop.open_question(c)
        assert q is not None
        assert [o.id for o in q.options] == ["retry"]  # its own gate, never the parent's accept
        assert len(paid.children) == 1
        assert (c.counted_children, c.spend.unread, c.spend.credits) == (paid.children, paid.children, 2.5)
        assert (c.tool_use.tools["bash"].calls, c.tool_use.tools["grep"].calls) == (3, 2)
        assert [e["label"] for e in Store(tmp_path / "store").events("c1") if e.get("label") == LABELS[parent]] == [
            LABELS[parent]
        ]
    if parent == "amend":
        assert c.pending_child is not None  # the same candidate waits, its proposer's route kept
        assert (c.pending_child.parent, c.pending_child.run, [a.verdict for a in c.amendments]) == (
            c.amendments[0].id,
            None,
            [""],
        )
    else:
        assert (c.plan.version, c.loops[PLAN].round, c.step.mode) == (1, 0, "challenge")

    store.put_inbox("c1", AnswerItem(at=datetime.now(UTC), question=q.id, option="retry"))
    c = restart(tmp_path, change_repo).read("c1")  # the owner's retry runs the child alone
    assert (len(paid.parents), len(paid.children)) == (1, 2)
    assert (c.counted_children, c.spend.unread, c.spend.credits) == (paid.children, paid.children[:1], 2.5 + 3.5)
    assert (c.tool_use.tools["bash"].calls, c.tool_use.tools["grep"].calls) == (3, 4)
    if parent == "plan":
        assert (c.plan.version, c.loops[PLAN].round, c.step.kind) == (1, 1, K.BUILD)
    else:
        (a,) = c.amendments
        assert (a.verdict, a.session, a.challenger) == ("equivalent", paid.parents[0], paid.children[1])
        assert (c.step.kind, c.outcome.exit) == (K.PLAN, Exit.BACK)


GATE_FAULTS = ["gate-write", "gate-write+cleanup", "both-media"]


@pytest.mark.parametrize("fault", GATE_FAULTS)
@pytest.mark.parametrize("parent", ["plan", "amend"])
def test_an_unread_child_whose_gate_write_fails_is_gated_from_its_capture_and_never_paid_again(  # noqa: C901, PLR0913, PLR0915, PLR0917
    tmp_path, change_repo, monkeypatch, capsys, parent, fault
):
    paid = Paid(monkeypatch, change_repo, parent, "known")
    store = held_and_accepted(tmp_path, change_repo, paid, parent)
    paid.verdicts += [passing(parent), passing(parent)]
    paid.unread_children = 1
    real_write, real_unlink = Store.write, Path.unlink
    armed = {"gate", *(["cleanup"] if "cleanup" in fault else [])}

    def write(self, lock, change):
        if "gate" in armed and set(change.counted_children) - set(self.read(change.slug).counted_children):
            armed.discard("gate")  # the one write of the unread child's gate and count
            msg = "gate refused"
            raise OSError(msg)
        return real_write(self, lock, change)

    def unlink(self, *args, **kwargs):
        if "cleanup" in armed and self.name == disposable.LIVE:
            armed.discard("cleanup")
            msg = "cleanup refused"
            raise OSError(msg)
        return real_unlink(self, *args, **kwargs)

    def no_capture(path, _text):
        msg = f"{path.name} refused"
        raise OSError(msg)

    monkeypatch.setattr(Store, "write", write)
    monkeypatch.setattr(Path, "unlink", unlink)
    if fault == "both-media":
        monkeypatch.setattr(pending_child, "atomic_write", no_capture)
    with pytest.raises(OSError, match="cleanup refused" if "cleanup" in fault else "gate refused") as failed:
        restart(tmp_path, change_repo)
    assert not armed
    gate_error = failed.value.__context__ if "cleanup" in fault else failed.value
    assert "gate refused" in str(gate_error)  # the cleanup's own error, with the gate's as its context
    monkeypatch.setattr(Store, "write", real_write)
    monkeypatch.setattr(Path, "unlink", real_unlink)
    if (live := store.root / "changes" / "c1" / disposable.LIVE).exists():
        live.unlink()  # its process ended: only the stale marker is cleared
    after = Store(tmp_path / "store").read("c1")
    assert (after.counted_children, after.spend.unread, loop.open_question(after)) == ([], [], None)

    if fault == "both-media":  # nothing kept it: printed, and the error says so; the next run honestly reruns it
        assert any("could not be kept" in n for n in gate_error.__notes__)
        printed = [json.loads(x) for x in capsys.readouterr().out.splitlines() if "child-unkept" in x]
        assert [p["child"]["run"]["session_id"] for p in printed] == paid.children
        assert captures(store) == []
        c = restart(tmp_path, change_repo).read("c1")
        assert len(paid.children) == 2
        assert paid.children[0] not in c.counted_children
        return

    (path,) = captures(store)  # the same child's evidence, its usage unread
    kept = json.loads(path.read_text())["run"]
    assert (kept["session_id"], kept["usage_unread"]) == (paid.children[0], UNREAD)
    for _ in range(2):  # its own gate and count come back from the capture; nothing runs until the owner retries
        c = restart(tmp_path, change_repo).read("c1")
        q = loop.open_question(c)
        assert q is not None
        assert [o.id for o in q.options] == ["retry"]  # its own gate, never the parent's accept
        assert len(paid.children) == 1
        assert (c.counted_children, c.spend.unread, c.spend.credits) == (paid.children, paid.children, 2.5)
        assert (c.tool_use.tools["bash"].calls, c.tool_use.tools["grep"].calls) == (3, 2)
        assert captures(Store(tmp_path / "store")) == []
    if parent == "amend":
        assert c.pending_child is not None
        assert (c.pending_child.run, [a.verdict for a in c.amendments]) == (None, [""])
    else:
        assert (c.plan.version, c.loops[PLAN].round, c.step.mode) == (1, 0, "challenge")

    store.put_inbox("c1", AnswerItem(at=datetime.now(UTC), question=q.id, option="retry"))
    c = restart(tmp_path, change_repo).read("c1")  # the owner's retry runs the child alone
    assert (len(paid.parents), len(paid.children)) == (1, 2)
    assert (c.counted_children, c.spend.unread, c.spend.credits) == (paid.children, paid.children[:1], 2.5 + 3.5)
    assert (c.tool_use.tools["bash"].calls, c.tool_use.tools["grep"].calls) == (3, 4)
    if parent == "plan":
        assert (c.plan.version, c.loops[PLAN].round, c.step.kind) == (1, 1, K.BUILD)
    else:
        (a,) = c.amendments
        assert (a.verdict, a.session, a.challenger) == ("equivalent", paid.parents[0], paid.children[1])


def unread_captured(tmp_path, change_repo, monkeypatch, parent) -> tuple[Paid, Store]:
    """An unread child whose own gate write failed once: its evidence is only in its capture file."""
    paid = Paid(monkeypatch, change_repo, parent, "known")
    store = held_and_accepted(tmp_path, change_repo, paid, parent)
    paid.unread_children = 1
    real_write, armed = Store.write, [True]

    def write(self, lock, change):
        if armed and set(change.counted_children) - set(self.read(change.slug).counted_children):
            armed.clear()
            msg = "gate refused"
            raise OSError(msg)
        return real_write(self, lock, change)

    monkeypatch.setattr(Store, "write", write)
    with pytest.raises(OSError, match="gate refused"):
        restart(tmp_path, change_repo)
    monkeypatch.setattr(Store, "write", real_write)
    assert len(captures(store)) == 1
    return paid, store


@pytest.mark.parametrize("parent", ["plan", "amend"])
def test_an_old_unread_capture_only_counts_under_a_later_child_and_never_gates_it(
    tmp_path, change_repo, monkeypatch, parent
):
    paid, store = unread_captured(tmp_path, change_repo, monkeypatch, parent)
    c = store.read("c1")
    c.outcome = None
    if parent == "plan":  # a later checkpoint: plan v2 in its challenge, its own child returned and kept
        c.plan = c.plan.model_copy(update={"version": 2})
        c.step.mode = "challenge"
        later = Run("c1-plan-challenge-v2", "result", tools.ReviewResult(verdict="pass"), termination=DONE)
        later.usage, later.tool_calls, later.model_check = dict(CHILD), {"grep": {"calls": 2}}, "verified"
        c.pending_child = PendingChild(
            label=plan_round.LABEL, parent="2", brief=c.brief.version, run=held.dump_run(later)
        )
    else:  # another candidate awaits its own challenge
        (a1,) = c.amendments
        c.amendments.append(a1.model_copy(update={"id": "A2"}))
        c.pending_child = c.pending_child.model_copy(update={"parent": "A2"})
        paid.verdicts.append(passing(parent))
    store.write(Lock("c1"), c)

    c = restart(tmp_path, change_repo).read("c1")
    old = paid.children[0]
    assert captures(store) == []
    unread = [q for q in c.questions if (q.cause or "").endswith(f":{failures.UNREAD}") and q.answer is None]
    assert unread == []  # no gate for the old child; the parent's own was answered at its acceptance
    assert (c.spend.unread, c.counted_children[0]) == ([old], old)  # counted once
    assert (c.pending_child, c.tool_use.tools["grep"].calls) == (None, 4)
    assert c.spend.credits == pytest.approx(2.5 + 3.5)
    if parent == "plan":  # the later child settles from its kept run: no session, its round counted
        assert (len(paid.children), c.counted_children) == (1, [old, "c1-plan-challenge-v2"])
        assert (c.plan.version, c.loops[PLAN].round, c.step.kind) == (2, 1, K.BUILD)
    else:  # the awaited candidate is judged by its own challenger; the old one stays unjudged
        assert (len(paid.children), c.counted_children) == (2, paid.children)
        assert [(a.id, a.verdict) for a in c.amendments] == [(c.amendments[0].id, ""), ("A2", "equivalent")]
        assert (c.step.kind, c.outcome.exit) == (K.PLAN, Exit.BACK)
    with pytest.raises(NextSessionError):  # the next step goes on: no gate, nothing of the old child again
        restart(tmp_path, change_repo)
    assert store.read("c1").counted_children == c.counted_children  # nothing counts twice


@pytest.mark.parametrize("parent", ["plan", "amend"])
def test_an_unread_capture_of_a_departed_brief_only_counts_when_a_new_brief_reuses_its_ids(
    tmp_path, change_repo, monkeypatch, parent
):
    paid, store = unread_captured(tmp_path, change_repo, monkeypatch, parent)
    (path,) = captures(store)
    old_brief = json.loads(path.read_text())["brief"]
    c = store.read("c1")
    assert old_brief == c.brief.version  # the capture is bound to the generation it ran on
    new = c.brief.version + 1
    c.brief = c.brief.model_copy(update={"version": new, "approved_version": new, "challenged": new})
    c.outcome = None
    paid.verdicts.append(passing(parent))
    if parent == "plan":  # a new brief's plan, its version 1 again, in its challenge: no child of its own yet
        c.plan = Plan(tasks=[Task(id="t1", title="another plan", scope=["src"])])
        c.step.mode = "challenge"
    else:  # a new brief's candidate, its id the old one's again, awaiting its own challenge
        (a1,) = c.amendments
        c.amendments = [a1.model_copy(update={"base": new, "reason": "the new brief's proposal"})]
        route = loop.StepResult(exit=Exit.BACK, back_to=K.PLAN, cause="review:build:premise", reason="new")
        c.pending_child = pending_child.awaited(amendments.LABEL, a1.id, route, c)
    assert c.pending_child is None or c.pending_child.parent == json.loads(path.read_text())["parent"]
    store.write(Lock("c1"), c)

    c = restart(tmp_path, change_repo).read("c1")
    old = paid.children[0]
    unread = [q for q in c.questions if (q.cause or "").endswith(f":{failures.UNREAD}") and q.answer is None]
    assert unread == []  # no gate for the departed brief's child
    assert (c.spend.unread, c.counted_children) == ([old], paid.children)  # old counted once; the new child too
    assert (len(paid.parents), len(paid.children)) == (1, 2)  # the new target's own challenger ran
    assert (c.pending_child, captures(store)) == (None, [])
    if parent == "plan":
        assert (c.plan.version, c.loops[PLAN].round, c.step.kind) == (1, 1, K.BUILD)
    else:
        (a,) = c.amendments
        assert (a.verdict, a.base, a.challenger) == ("equivalent", new, paid.children[1])
        assert (c.step.kind, c.outcome.exit) == (K.PLAN, Exit.BACK)


def stored(store: Store) -> str:
    with store.db.read() as db:
        return db.execute("SELECT record FROM changes WHERE slug = 'c1'").fetchone()[0]


@pytest.mark.parametrize("where", ["held_fallback", "pending_child"])
def test_a_run_record_with_an_unknown_field_is_refused_on_restart_and_never_rewritten(
    tmp_path, change_repo, monkeypatch, where
):
    if where == "pending_child":
        paid = settlement_fails(tmp_path, change_repo, monkeypatch, "plan")
    else:  # the hold's file cannot be written, so the Change keeps it

        def no_file(path, _text):
            msg = f"{path.name} refused"
            raise OSError(msg)

        monkeypatch.setattr(held, "atomic_write", no_file)
        paid = Paid(monkeypatch, change_repo, "plan", "known")
        held_and_accepted(tmp_path, change_repo, paid, "plan")
    store = Store(tmp_path / "store")
    data = json.loads(stored(store))
    assert data[where]["run"]["session_id"]
    data[where]["run"]["surprise"] = True
    raw = json.dumps(data)
    with store.db.write() as db:
        db.execute("UPDATE changes SET record = ? WHERE slug = 'c1'", (raw,))
    with pytest.raises(StoreError, match="unknown field"):
        restart(tmp_path, change_repo)
    assert stored(Store(tmp_path / "store")) == raw  # kept byte for byte: nothing read it lossily or rewrote it
    assert len(paid.children) == (1 if where == "pending_child" else 0)
