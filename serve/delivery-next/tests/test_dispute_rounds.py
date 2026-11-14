"""TD-193, TD-208: the next round judges a rejection; the owner decides each one it does not accept, with a note."""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from owlbear_delivery_next.change_contracts import dispute_tools, tools
from owlbear_delivery_next.change_contracts.failures import cause_key
from owlbear_delivery_next.change_contracts.inbox import AnswerItem
from owlbear_delivery_next.change_contracts.models import (
    Brief,
    Change,
    Dispute,
    ErrorKind,
    Exit,
    Names,
    Plan,
    Question,
    Step,
    StepKind,
    Task,
)
from owlbear_delivery_next.change_flow import budgets, disputes, loop
from owlbear_delivery_next.change_flow.moves import ask
from owlbear_delivery_next.change_flow.status import Activity
from owlbear_delivery_next.commands import runner
from owlbear_delivery_next.local_system.processes import Termination
from owlbear_delivery_next.project_host import api
from owlbear_delivery_next.runtimes import sdk_adapter
from owlbear_delivery_next.runtimes.session_result import Run
from owlbear_delivery_next.state_store.store import Lock, Store
from owlbear_delivery_next.workflow_steps import reconsider, review

from . import test_round_flow
from .test_round_flow import answer, git, step

clone = test_round_flow.clone
NOW = datetime(2026, 10, 17, 3, tzinfo=UTC)
DONE = Termination(confirmed=True)
K = StepKind
ONE, TWO = "a.txt:1: AC-1 greets in English - fix: use Hallo", "a.txt:2: no test - fix: add one"
RECONSIDER = "Ask the reviewer to reconsider"
NOTE = "the brief allows English in AC-1"


class Host:
    maintenance = None
    wake = type("W", (), {"set": lambda _self: None})()
    record = None

    def activity(self, _slug):
        return Activity(host_up=True)


def change() -> Change:
    """Task t3 repairs the findings of t1's review that its earlier repair t2 left."""
    tasks = [
        Task(id="t1", title="one", scope=["a.txt"], built_by="s-build", done=True),
        Task(id="t2", title="fix", scope=["a.txt"], origin="review", fixes="t1", detail=f"- {ONE}", done=True),
        Task(id="t3", title="fix", scope=["a.txt"], origin="review", fixes="t2", detail=f"- {ONE}\n- {TWO}",
             resume="s-build"),
    ]  # fmt: skip
    names = Names(branch="owlbear/c1", target="main")
    return Change(
        slug="c1", brief=Brief(version=1), plan=Plan(tasks=tasks), names=names, step=Step(kind=K.BUILD, task="t3")
    )


def stored(tmp_path: Path, c: Change) -> Store:
    store = Store(tmp_path / "store")
    store.write(Lock("c1"), c)
    return store


def build(store: Store, clone: Path, monkeypatch, *keys: str) -> sdk_adapter.Session:
    seen = []

    async def run(cfg):
        seen.append(cfg)
        rejected = [{"finding": k, "reason": f"{k} is wrong"} for k in keys]
        payload = tools.BuildResult(summary="Rejected.", checks=[], rejected=rejected)
        return Run(cfg.session_id, "result", payload, head=git(clone, "rev-parse", "HEAD"), termination=DONE)

    monkeypatch.setattr(runner.sdk_adapter, "run", run)
    step(store, clone)
    return seen[0]


def review_(store: Store, clone: Path, monkeypatch, rechecked: list[dict]) -> sdk_adapter.Session:
    seen = []

    def kept(_store, _lock, _change, path, config):
        seen.append(cfg := config(path))
        payload = tools.ReviewResult(verdict="pass", rechecked=rechecked)
        return Run(cfg.session_id, "result", payload, head=git(clone, "rev-parse", "HEAD"), termination=DONE)

    monkeypatch.setattr(runner, "_kept", kept)
    step(store, clone)
    return seen[0]


@pytest.mark.parametrize("owner", ["drop", "fix", "approved"])
def test_disputes_are_judged_before_their_disposition(tmp_path, clone, monkeypatch, owner):
    c = change()
    if owner == "approved":
        c.brief.approved_version = 1
    store = stored(tmp_path, c)
    cfg = build(store, clone, monkeypatch, "F1", "F2")
    assert (cfg.rejectable, cfg.settled) == (("F1", "F2"), ())
    assert f"> F1. {ONE}" in cfg.message
    c = store.read("c1")
    assert (c.step.kind, c.step.task, [d.key for d in c.plan.tasks[2].disputes]) == (K.REVIEW, "t3", ["F1", "F2"])
    rechecked = [
        {"finding": "F1", "upheld": True, "reason": "it still greets in English"},
        {"finding": "F2", "upheld": False, "reason": "a test exists"},
    ]
    cfg = review_(store, clone, monkeypatch, rechecked)
    assert (cfg.rechecks, "## Rejections to judge" in cfg.message, disputes.ONLY in cfg.message) == (
        ("F1", "F2"),
        True,
        False,
    )
    c = store.read("c1")
    assert [(d.key, d.upheld) for d in c.plan.tasks[2].disputes] == [("F1", True), ("F2", False)]
    assert "(rejection accepted by the reviewer)" in disputes.review_lines(c, None)[-1]
    if owner == "approved":
        assert (c.questions, len(c.plan.tasks), c.step.kind, c.step.mode) == ([], 3, K.REVIEW, "final")
        assert [e.model_dump() for e in c.left] == [
            {
                "loop": "t1",
                "attempt": 0,
                "id": "F1",
                "text": ONE,
                "reason": "F1 is wrong",
                "judgement": "it still greets in English",
            }
        ]
        assert c.plan.tasks[2].disputes[0].owner == ""
        return
    q = loop.open_question(c)
    assert (c.outcome.exit, q.cause.startswith(disputes.PREFIX), "F1" in q.text) == (Exit.ASK, True, True)
    assert ("did not accept the builder's rejection" in q.text, "it still greets in English" in q.text) == (True, True)
    assert [o.label for o in q.options] == ["Fix it", RECONSIDER, "Drop it"]
    assert (len(c.plan.tasks), c.budgets.rounds, len(c.reviews)) == (3, {}, 1)
    answer(store, owner)
    monkeypatch.setattr(runner, "_kept", lambda *_a: pytest.fail("a decided dispute starts no session"))
    c = step(store, clone)
    if owner == "drop":
        assert ([t.done for t in c.plan.tasks], c.step.kind, c.step.mode) == ([True] * 3, K.REVIEW, "final")
    else:
        fix = c.plan.tasks[-1]
        assert (c.step.kind, c.step.task, fix.fixes, fix.detail) == (K.BUILD, fix.id, "t3", f"- {ONE}")
        assert sum(c.budgets.rounds.values()) == 1
        assert (disputes.rejectable(fix), fix.settled) == ((), ["F1"])


def test_each_upheld_finding_is_decided_on_its_own(tmp_path, clone, monkeypatch):
    store = stored(tmp_path, change())
    build(store, clone, monkeypatch, "F1", "F2")
    review_(store, clone, monkeypatch, [{"finding": k, "upheld": True, "reason": "holds"} for k in ("F1", "F2")])
    assert "F1" in loop.open_question(store.read("c1")).text
    assert "F2" in loop.open_question(answer(store, "drop")).text
    answer(store, "fix")
    monkeypatch.setattr(runner, "_kept", lambda *_a: pytest.fail("a decided dispute starts no session"))
    c = step(store, clone)
    assert c.plan.tasks[-1].detail == f"- {TWO}"
    assert [(d.key, d.owner) for d in c.plan.tasks[2].disputes] == [("F1", "drop"), ("F2", "fix")]


def test_a_review_whose_session_stops_consumes_no_recheck(tmp_path, clone, monkeypatch):
    store = stored(tmp_path, change())
    build(store, clone, monkeypatch, "F1", "F2")
    payload = tools.ReviewResult(
        verdict="pass", rechecked=[{"finding": k, "upheld": True, "reason": "holds"} for k in ("F1", "F2")]
    )
    monkeypatch.setattr(
        runner,
        "_kept",
        lambda _s, _l, _c, path, config: Run(
            config(path).session_id,
            "result",
            payload,
            head=git(clone, "rev-parse", "HEAD"),
            termination=Termination(confirmed=False),
        ),
    )
    c = step(store, clone)
    assert c.outcome.exit == Exit.STOP
    assert [d.upheld for d in c.plan.tasks[2].disputes] == [None, None]
    assert not c.reviews


def reconsidering(tmp_path: Path, clone: Path, monkeypatch) -> Store:
    """The builder rejects both findings, the next round upholds F1, the owner asks for a reconsideration."""
    store = stored(tmp_path, change())
    build(store, clone, monkeypatch, "F1", "F2")
    upheld = {"finding": "F1", "upheld": True, "reason": "it greets in English"}
    review_(store, clone, monkeypatch, [upheld, {"finding": "F2", "upheld": False, "reason": "a test exists"}])
    c = answer(store, "reconsider", NOTE)
    assert (c.step.kind, c.step.mode) == (K.REVIEW, disputes.DISPUTED)
    return store


def judge(monkeypatch, verdict: dict | None = None, result: loop.StepResult | None = None) -> list:
    seen = []

    def run(_store, _lock, _change, path, made, label, *, submit):
        seen.append((label, submit, cfg := made(path)))
        payload = dispute_tools.ReconsiderResult(reconsidered=[verdict]) if verdict else None
        done = result or loop.StepResult(exit=Exit.DONE, reason="judged")
        return done, Run(cfg.session_id, "result" if verdict else "unread", payload, termination=DONE)

    monkeypatch.setattr(reconsider.sessions, "review_run", run)
    return seen


def test_each_reconsideration_outcome_settles_clarifies_asks_or_runs_again(tmp_path, clone, monkeypatch):
    asked = reconsidering(tmp_path, clone, monkeypatch).read("c1")

    def fresh(name: str, c: Change | None = None) -> Store:
        """An independent store holding a deep copy of the reconsidering Change; the clone is only read."""
        return stored(tmp_path / name, c or asked.model_copy(deep=True))

    # withdrawn: settled, and the review completes
    store = fresh("withdrawn")
    seen = judge(monkeypatch, {"finding": "F1", "verdict": "withdrawn", "reason": "AC-1 allows English"})
    c = step(store, clone)
    label, submit, cfg = seen[0]
    assert (label, submit, cfg.rechecks) == (dispute_tools.LABEL, dispute_tools.SUBMIT, ("F1",))
    assert f"The owner's note: {NOTE}" in cfg.message
    assert (c.step.kind, c.step.mode, c.plan.tasks[2].done) == (K.REVIEW, "final", True)
    assert (
        "- a.txt:1: AC-1 greets in English - fix: use Hallo (withdrawn after the owner's note: AC-1 allows "
        "English)" in disputes.review_lines(c, None)
    )

    # clarified: goes to the builder as the owner's
    c = asked.model_copy(deep=True)
    c.budgets.rounds[budgets.round_key(c)] = budgets.ROUND_LIMIT  # the owner's decision passes the gate once
    store = fresh("clarified", c)
    narrower = "a.txt:1: AC-1 greets German users in English - fix: use Hallo for de"
    judge(monkeypatch, {"finding": "F1", "verdict": "clarified", "text": narrower, "reason": "narrowed"})
    c = step(store, clone)
    fix = c.plan.tasks[-1]
    assert (c.step.kind, c.step.task, fix.settled) == (K.BUILD, fix.id, ["F1"])
    assert (fix.detail, fix.notes) == (f"- {narrower}", {"F1": NOTE})

    # unsure: asks the owner to fix or drop
    store = fresh("unsure")
    judge(monkeypatch, {"finding": "F1", "verdict": "unsure", "reason": "only the owner knows the audience"})
    q = loop.open_question(step(store, clone))
    assert ([o.label for o in q.options], "could not settle" in q.text) == (["Fix it", "Drop it"], True)
    assert "only the owner knows the audience" in q.text
    c = answer(store, "fix", "use Hallo")
    assert (c.step.kind, c.step.mode) == (K.REVIEW, disputes.DISPUTED)
    assert disputes.kept(c.plan.tasks[2]) == {f"- {ONE}": "use Hallo"}

    # failed: the session's failure is the step's result, and it runs again
    store = fresh("failed")
    failed = loop.StepResult(exit=Exit.RETRY, cause=cause_key(ErrorKind.LIVENESS, K.REVIEW, "transcript"), reason="x")
    judge(monkeypatch, result=failed)
    c = step(store, clone)
    assert (c.outcome.exit, c.step.kind, c.step.mode) == (Exit.RETRY, K.REVIEW, disputes.DISPUTED)
    assert [d.reconsidered for d in c.plan.tasks[2].disputes if d.owner == "reconsider"] == [""]


def asked(tmp_path: Path) -> tuple[Store, Change]:
    c = change()
    c.step = Step(kind=K.REVIEW, task="t3")
    task = c.plan.tasks[2]
    task.disputes = [Dispute(key="F1", finding=ONE, reason="r", upheld=True, recheck="holds")]
    ask(c, disputes.question(task, task.disputes[0]), NOW)
    return stored(tmp_path, c), c


def test_a_reconsideration_needs_the_owners_note(tmp_path):
    store, c = asked(tmp_path)
    q = loop.open_question(c)
    after, _ = loop.schedule(c, [AnswerItem(at=NOW, channel="status-view", question=q.id, option="reconsider")], NOW)
    assert (after.questions[-1].answer, after.step) == (None, c.step)  # still open: nothing decided
    client = TestClient(
        api.create_app(store, "t", Host()), base_url="http://127.0.0.1", headers={"authorization": "Bearer t"}
    )
    url = "/api/next/changes/c1/answers"
    refused = client.post(url, json={"question": q.id, "option": "reconsider", "text": "  "})
    assert (refused.status_code, "needs your note" in refused.json()["detail"]) == (422, True)
    assert client.post(url, json={"question": q.id, "option": "reconsider", "text": NOTE}).status_code == 200


def test_the_owners_fix_passes_the_round_gate_once():
    c = change()
    c.step = Step(kind=K.REVIEW, task="t3")
    c.budgets.rounds[budgets.round_key(c)] = budgets.ROUND_LIMIT
    fix = Task(id="t4", title="fix", origin="review", detail=f"- {ONE}")
    r = loop.StepResult(exit=Exit.RETRY, reason="1 finding(s) to fix", fix_task=fix, ungated=True)
    done = loop.apply(c, r, NOW)
    assert (done.step.kind, done.step.task, done.outcome.question) == (K.BUILD, "t4", None)
    assert loop.apply(c, r.model_copy(update={"ungated": False}), NOW).outcome.exit == Exit.ASK


def gate_asked() -> Change:
    """Round 3 of t3's review still finds something: the gate asks, holding the repair t4."""
    c = change()
    c.step = Step(kind=K.REVIEW, task="t3")
    c.budgets.rounds[budgets.round_key(c)] = budgets.ROUND_LIMIT
    fix = Task(id="t4", title="fix", origin="review", detail=f"- {TWO}")
    return loop.apply(c, loop.StepResult(exit=Exit.RETRY, reason="1 finding(s) to fix", fix_task=fix), NOW)


@pytest.mark.parametrize(
    ("option", "tasks", "kind", "task"), [("fix", 4, K.BUILD, "t4"), ("accept", 3, K.REVIEW, None)]
)
def test_the_round_gate_builds_the_held_findings_only_on_fix(option, tasks, kind, task):
    asked = gate_asked()
    q = loop.open_question(asked)
    assert (len(asked.plan.tasks), [t.id for t in q.repair]) == (3, ["t4"])
    after, _ = loop.schedule(asked, [AnswerItem(at=NOW, channel="status-view", question=q.id, option=option)], NOW)
    assert (len(after.plan.tasks), after.step.kind, after.step.task) == (tasks, kind, task)
    last = after.plan.tasks[-1]
    assert (last.id, last.fixes) == (("t4", "t3") if option == "fix" else ("t3", "t2"))


def test_a_round_gate_settles_only_by_its_options_while_it_is_open(tmp_path):
    asked = gate_asked()
    q = loop.open_question(asked)
    said = AnswerItem(at=NOW, channel="status-view", question=q.id, text="Fix the findings")
    worded, _ = loop.schedule(asked, [said], NOW)
    assert (worded.questions[-1].answer, loop.open_question(worded).id, len(worded.plan.tasks)) == (None, q.id, 3)
    moved = asked.model_copy(deep=True)
    ask(moved, Question(step=K.REVIEW, text="Another question"), NOW)  # the Change moved on
    stale, _ = loop.schedule(moved, [AnswerItem(at=NOW, channel="status-view", question=q.id, option="fix")], NOW)
    assert (len(stale.plan.tasks), stale.step.kind, stale.step.task) == (3, K.REVIEW, "t3")
    assert stale.questions[0].answer is None  # recorded, a resumed session would receive it as the owner's answer
    store = stored(tmp_path, asked)
    client = TestClient(
        api.create_app(store, "t", Host()), base_url="http://127.0.0.1", headers={"authorization": "Bearer t"}
    )
    url = "/api/next/changes/c1/answers"
    assert client.post(url, json={"question": q.id, "text": "Fix the findings"}).status_code == 422
    store.write(Lock("c1"), moved)
    assert client.post(url, json={"question": q.id, "option": "fix"}).status_code == 409


def test_the_owners_note_guides_the_fix_and_authorises_its_round():
    task = change().plan.tasks[2]
    note = "use Grüß Gott " * 140  # a whole note of 2000 characters reaches the builder
    task.disputes = [
        Dispute(key="F1", finding=ONE, reason="r", upheld=True, owner="fix", note=note),
        Dispute(key="F2", finding=TWO, reason="r", upheld=True, owner="drop", note="out of scope"),
    ]
    assert (disputes.kept(task), disputes.authorised(task)) == ({f"- {ONE}": note}, True)
    c = change()
    c.step = Step(kind=K.REVIEW, task="t3")
    fix = review.repair(c, task, [f"- {ONE}", f"- {TWO}"], disputes.kept(task))[0]
    assert f"> F1: {note.strip()}" in disputes.build_lines(fix)
    task.disputes[0].owner = "drop"
    assert (disputes.kept(task), disputes.authorised(task)) == ({}, False)


def test_each_repair_part_marks_the_findings_the_owner_decided():
    c = change()
    c.step = Step(kind=K.REVIEW, task="t3")
    found = [f"- a.txt:{i}: {'x' * 1500} - fix: y" for i in range(1, 5)]
    parts = review.repair(c, c.plan.tasks[2], found, kept={found[2]: "a note", found[3]: ""})
    assert [(t.settled, t.notes) for t in parts] == [([], {}), (["F1", "F2"], {"F1": "a note"})]


def test_a_repair_lists_every_finding_and_marks_the_owners():
    task = change().plan.tasks[2]
    task.settled = ["F1"]
    assert (disputes.rejectable(task), disputes.settled(task)) == (("F2",), ("F1",))
    lines = disputes.build_lines(task)
    assert (f"> F1. {ONE} [the owner's]" in lines, f"> F2. {TWO}" in lines) == (True, True)
    assert (disputes.REJECT in lines, disputes.OWNERS in lines) == (True, True)
    task.settled = ["F1", "F2"]
    assert disputes.REJECT not in disputes.build_lines(task)


def test_every_finding_settled_not_to_fix_reaches_later_reviews():
    c = change()
    c.plan.tasks[1].disputes = [
        Dispute(key=f"F{i}", finding=f"a.txt:{i}: p - fix: f", reason="r", upheld=True, owner="drop", note="later")
        for i in range(12)
    ]
    assert sum("(dropped by the owner: later)" in line for line in disputes.review_lines(c, None)) == 12
