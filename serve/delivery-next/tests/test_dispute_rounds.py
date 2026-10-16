"""TD-193, TD-208: the next round judges a rejection; the owner decides each one it does not accept, with a note."""

import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from owlbear_delivery_next import api, budgets, dispute_tools, disputes, loop, runner, sdk_adapter, tools
from owlbear_delivery_next.failures import cause_key
from owlbear_delivery_next.inbox import AnswerItem
from owlbear_delivery_next.models import (
    Brief,
    Change,
    Dispute,
    ErrorKind,
    Exit,
    ItemRef,
    Names,
    Plan,
    Question,
    Step,
    StepKind,
    Task,
)
from owlbear_delivery_next.moves import ask
from owlbear_delivery_next.permissions import Policy
from owlbear_delivery_next.processes import Termination
from owlbear_delivery_next.results import ACCEPTED, Gate
from owlbear_delivery_next.session_result import Run
from owlbear_delivery_next.status import Activity
from owlbear_delivery_next.steps import reconsider, review
from owlbear_delivery_next.store import Lock, Store

NOW = datetime(2026, 10, 17, 3, tzinfo=UTC)
DONE = Termination(confirmed=True)
K = StepKind
ONE, TWO = "a.txt:1: AC-1 greets in English - fix: use Hallo", "a.txt:2: no test - fix: add one"
RECONSIDER = "Ask the reviewer to reconsider"
NOTE = "the brief allows English in AC-1"


class Host:
    wake = type("W", (), {"set": lambda _self: None})()
    record = None

    def activity(self, _slug):
        return Activity(host_up=True)


def git(cwd: Path, *args: str) -> str:
    done = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)  # noqa: S603, S607
    return done.stdout.strip()


@pytest.fixture
def clone(tmp_path, monkeypatch) -> Path:
    (tmp_path / "gitconfig").write_text("")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(tmp_path / "gitconfig"))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    for who in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{who}_NAME", "t")
        monkeypatch.setenv(f"GIT_{who}_EMAIL", "t@t")
    work = tmp_path / "work"
    work.mkdir()
    git(work, "init", "-q", "-b", "owlbear/c1")
    (work / "a.txt").write_text("a\n")
    git(work, "add", "-A")
    git(work, "commit", "-qm", "base")
    git(work, "branch", "main")
    monkeypatch.setattr(runner.worktree, "ensure", lambda *_a: work)
    monkeypatch.setattr(reconsider.worktree, "ensure", lambda *_a: work)
    return work


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


def step(store: Store, clone: Path) -> Change:
    c = store.read("c1")
    runner._step(store, Lock("c1"), c, c.step, clone)  # noqa: SLF001
    return store.read("c1")


def build(store: Store, clone: Path, monkeypatch, *keys: str) -> sdk_adapter.Session:
    seen = []

    async def run(cfg):
        seen.append(cfg)
        rejected = [{"finding": k, "reason": f"{k} is wrong"} for k in keys]
        payload = tools.BuildResult(summary="Rejected.", changed_paths=[], checks=[], rejected=rejected)
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


def answer(store: Store, option: str, text: str = "") -> Change:
    c = store.read("c1")
    q = loop.open_question(c)
    c, _ = loop.schedule(c, [AnswerItem(at=NOW, channel="status-view", question=q.id, option=option, text=text)], NOW)
    store.write(Lock("c1"), c)
    return c


def gate(tmp_path: Path, kind: StepKind, tree: tools.Worktree, submit: tools.Spec, **bounds) -> Gate:
    cfg = sdk_adapter.Session(
        kind, tmp_path, "s1", "m", resume=False, policy=Policy(tmp_path), observe=lambda: tree, checks=("npm test",),
        submit=submit, **bounds,
    )  # fmt: skip
    return Gate(cfg, Run("s1"), lambda **_e: None, lambda: None)


def test_the_next_round_judges_each_rejection_and_the_owner_decides_one_it_does_not_accept(
    tmp_path, clone, monkeypatch
):
    store = stored(tmp_path, change())
    cfg = build(store, clone, monkeypatch, "F1", "F2")
    assert (cfg.rejectable, cfg.settled) == (("F1", "F2"), ())
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
    q = loop.open_question(c)
    assert ("did not accept the builder's rejection" in q.text, "it still greets in English" in q.text) == (True, True)
    assert [o.label for o in q.options] == ["Fix it", RECONSIDER, "Drop it"]
    assert [(d.key, d.upheld) for d in c.plan.tasks[2].disputes] == [("F1", True), ("F2", False)]
    assert "(rejection accepted by the reviewer)" in disputes.review_lines(c, None)[-1]


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


def test_a_withdrawn_finding_is_settled_and_the_review_completes(tmp_path, clone, monkeypatch):
    store = reconsidering(tmp_path, clone, monkeypatch)
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


def test_a_clarified_finding_goes_to_the_builder_as_the_owners(tmp_path, clone, monkeypatch):
    store = reconsidering(tmp_path, clone, monkeypatch)
    c = store.read("c1")
    c.budgets.rounds[budgets.round_key(c)] = budgets.ROUND_LIMIT  # the owner's decision passes the gate once
    store.write(Lock("c1"), c)
    narrower = "a.txt:1: AC-1 greets German users in English - fix: use Hallo for de"
    judge(monkeypatch, {"finding": "F1", "verdict": "clarified", "text": narrower, "reason": "narrowed"})
    c = step(store, clone)
    fix = c.plan.tasks[-1]
    assert (c.step.kind, c.step.task, fix.settled) == (K.BUILD, fix.id, ["F1"])
    assert (fix.detail, fix.notes) == (f"- {narrower}", {"F1": NOTE})


def test_an_unsure_reconsideration_asks_the_owner_to_fix_or_drop(tmp_path, clone, monkeypatch):
    store = reconsidering(tmp_path, clone, monkeypatch)
    judge(monkeypatch, {"finding": "F1", "verdict": "unsure", "reason": "only the owner knows the audience"})
    q = loop.open_question(step(store, clone))
    assert ([o.label for o in q.options], "could not settle" in q.text) == (["Fix it", "Drop it"], True)
    assert "only the owner knows the audience" in q.text
    c = answer(store, "fix", "use Hallo")
    assert (c.step.kind, c.step.mode) == (K.REVIEW, disputes.DISPUTED)
    assert disputes.kept(c.plan.tasks[2]) == {f"- {ONE}": "use Hallo"}


def test_a_failed_reconsideration_is_the_steps_result_and_runs_again(tmp_path, clone, monkeypatch):
    store = reconsidering(tmp_path, clone, monkeypatch)
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


@pytest.mark.parametrize(
    ("offered", "keys", "error"),
    [
        (("F2",), ("F1", "F2"), "rejected: F1 is the owner's decision"),
        (("F2",), ("F2",), "changes: no commit - fix and commit F1"),
        (("F2",), ("F3",), "rejected: F3 is no finding key of this task - use F2"),
        ((), ("F1",), "rejected: the owner decided every finding"),
    ],
)
def test_a_finding_the_owner_decided_is_never_rejected(tmp_path, offered, keys, error):
    g = gate(tmp_path, K.BUILD, tools.Worktree(head="a", base="a"), tools.SUBMIT, rejectable=offered, settled=("F1",))
    rejected = [{"finding": k, "reason": "r"} for k in keys]
    text, ok = g.call(tools.SUBMIT, {"summary": "R.", "changed_paths": [], "checks": [], "rejected": rejected})
    assert (ok, error in text, "or reject" in text) == (False, True, False)


def test_a_conversation_reply_never_skips_a_finding_the_owner_decided(tmp_path):
    item = ItemRef(id="c1", kind="comment", version="v1", task="t1")
    tree = tools.Worktree(head="a", base="a")
    g = gate(tmp_path, K.BUILD, tree, tools.SUBMIT, rejectable=("F2",), settled=("F1",), item=item)
    reply = {"how": "answered", "text": "It already greets in German."}
    text, ok = g.call(tools.SUBMIT, {"summary": "R.", "changed_paths": [], "checks": [], "response": reply})
    assert (ok, "changes: no commit - fix and commit F2, F1" in text) == (False, True)


@pytest.mark.parametrize(
    ("given", "cap", "error"),
    [
        ({"upheld": True}, 1, None),
        ({}, 1, "rechecked: F1 needs upheld true or false"),
        ({"upheld": False}, 0, "findings: 1 given, at most 0"),  # a rejections-only check finds nothing new
    ],
)
def test_a_judgement_needs_a_verdict_and_new_findings_stay_within_the_cap(tmp_path, given, cap, error):
    g = gate(tmp_path, K.REVIEW, tools.Worktree(head="b", base="a"), tools.REVIEW, rechecks=("F1",), cap=cap)
    found = [{"place": "a.txt:3", "problem": "p", "fix": "f"}]
    args = {"verdict": "fix", "findings": found, "rechecked": [{"finding": "F1", "reason": "r"} | given]}
    text, ok = g.call(tools.REVIEW, args)
    assert (ok, text) == (True, ACCEPTED) if error is None else (not ok and error in text)


@pytest.mark.parametrize(
    ("given", "error"),
    [
        ([("F1", "withdrawn", ""), ("F2", "clarified", "a.txt:2: p - fix: f")], None),
        ([("F1", "withdrawn", "")], "reconsidered: missing F2"),
        ([("F1", "withdrawn", ""), ("F2", "clarified", " ")], "reconsidered: F2 is clarified but has no text"),
    ],
)
def test_a_reconsideration_answers_each_finding_and_restates_a_clarified_one(tmp_path, given, error):
    tree = tools.Worktree(head="a", base="a")
    g = gate(tmp_path, K.REVIEW, tree, dispute_tools.SUBMIT, rechecks=("F1", "F2"))
    verdicts = [{"finding": k, "verdict": v, "text": t, "reason": "r"} for k, v, t in given]
    text, ok = g.call(dispute_tools.SUBMIT, {"reconsidered": verdicts})
    assert (ok, text) == (True, ACCEPTED) if error is None else (not ok and error in text)


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
