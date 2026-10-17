"""TD-208, TD-215, TD-216: the final review's loop, its completion record, a re-entry and the restart."""

import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from owlbear_delivery_next.change_contracts import dispute_tools, tools
from owlbear_delivery_next.change_contracts.inbox import AnswerItem, ConsentItem, RestartItem
from owlbear_delivery_next.change_contracts.models import (
    Brief,
    Change,
    Criterion,
    Exit,
    Inputs,
    MergeConsent,
    Names,
    Plan,
    Question,
    Review,
    Step,
    StepKind,
    Task,
)
from owlbear_delivery_next.change_contracts.permissions import Policy
from owlbear_delivery_next.change_contracts.round_records import FINAL, RECHECK, RoundLoop, RoundPolicy
from owlbear_delivery_next.change_flow import loop, round_flow
from owlbear_delivery_next.change_flow.moves import ask
from owlbear_delivery_next.change_flow.progress import progress
from owlbear_delivery_next.change_flow.status import Activity
from owlbear_delivery_next.commands import runner
from owlbear_delivery_next.local_system.processes import Termination
from owlbear_delivery_next.project_host import api
from owlbear_delivery_next.runtimes import sdk_adapter
from owlbear_delivery_next.runtimes.results import ACCEPTED, Gate
from owlbear_delivery_next.runtimes.session_result import Run
from owlbear_delivery_next.state_store.store import Lock, Store
from owlbear_delivery_next.workflow_steps import publish, reconsider, review

NOW = datetime(2026, 10, 17, 3, tzinfo=UTC)
DONE = Termination(confirmed=True)
K = StepKind
FINAL_STEP = (K.REVIEW, None, "final")


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
    (work / "a.txt").write_text("built\n")
    git(work, "commit", "-qam", "t1")
    monkeypatch.setattr(runner.worktree, "ensure", lambda *_a: work)
    return work


def stored(tmp_path: Path, *loops: RoundLoop) -> Store:
    """A Change whose one plan task is built and reviewed, at its final review."""
    c = Change(
        slug="c1",
        brief=Brief(version=1, criteria=[Criterion(id="AC-1", text="greets")]),
        plan=Plan(tasks=[Task(id="t1", title="one", scope=["a.txt"], done=True)]),
        names=Names(branch="owlbear/c1", target="main"),
        step=Step(kind=K.REVIEW, mode="final"),
        loops={lp.subject: lp for lp in loops},
    )
    store = Store(tmp_path / "store")
    store.write(Lock("c1"), c)
    return store


def step(store: Store, clone: Path) -> Change:
    c = store.read("c1")
    runner._step(store, Lock("c1"), c, c.step, clone)  # noqa: SLF001
    return store.read("c1")


def built(store: Store, clone: Path, monkeypatch, write: str, *reject: str) -> None:
    def kept(_store, _lock, _change, path, config):
        cfg = config(path)
        (clone / "a.txt").write_text(write)
        git(clone, "commit", "-qam", f"build {write.strip()}")
        rejected = [{"finding": k, "reason": f"{k} is wrong"} for k in reject]
        payload = tools.BuildResult(summary="Built.", changed_paths=["a.txt"], checks=[], rejected=rejected)
        return Run(cfg.session_id, "result", payload, head=git(clone, "rev-parse", "HEAD"), termination=DONE)

    monkeypatch.setattr(runner, "_kept", kept)
    step(store, clone)


def reviewed(store: Store, clone: Path, monkeypatch, found: range = range(0), **judged: bool) -> sdk_adapter.Session:
    """One final round finding a.txt:<n>, each naming t1, for each n in *found*, and judging *judged*."""
    seen = []

    def kept(_store, _lock, _change, path, config):
        seen.append(cfg := config(path))
        findings = [
            {"place": f"a.txt:{n}", "problem": f"problem {n}", "fix": f"fix {n}", "tasks": ["t1"]} for n in found
        ]
        rechecked = [{"finding": k, "upheld": u, "reason": f"{k} judged"} for k, u in judged.items()]
        payload = tools.ReviewResult(verdict="fix" if found else "pass", findings=findings, rechecked=rechecked)
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


def at(c: Change) -> tuple:
    return c.step.kind, c.step.task, c.step.mode


def test_final_rounds_name_tasks_and_the_next_final_round_judges_its_repairs_rejections(tmp_path, clone, monkeypatch):
    store = stored(tmp_path)
    cfg = reviewed(store, clone, monkeypatch, range(1, 6))
    assert (cfg.cap, cfg.plan_tasks, "## Plan tasks" in cfg.message, "- t1: one" in cfg.message) == (
        10,
        ("t1",),
        True,
        True,
    )
    c = store.read("c1")
    lp, fix = c.loops[FINAL], c.plan.tasks[-1]
    assert (lp.round, lp.found, lp.last, [f.tasks for f in lp.findings]) == (1, 5, False, [["t1"]] * 5)
    assert (fix.id, fix.fixes, fix.detail.splitlines()[0], at(c)) == (
        "t2",
        FINAL,
        "- F1: a.txt:1: problem 1 - fix: fix 1",
        (K.BUILD, "t2", None),
    )
    built(store, clone, monkeypatch, "c\n", "F2")
    c = store.read("c1")
    assert (c.plan.tasks[-1].done, c.loops[FINAL].batch, at(c)) == (True, ["t2"], FINAL_STEP)  # no task review
    cfg = reviewed(store, clone, monkeypatch, range(6, 8), F2=False)
    assert (cfg.rechecks, "a.txt:2: problem 2" in cfg.message, "a.txt:1: problem 1" in cfg.message) == (
        ("F2",),
        True,
        False,
    )
    c = store.read("c1")
    assert (c.loops[FINAL].round, c.loops[FINAL].last, c.loops[FINAL].findings[1].state, at(c)) == (
        2,
        True,
        "standing",
        (K.BUILD, "t3", None),
    )
    built(store, clone, monkeypatch, "d\n", "F7")
    assert at(store.read("c1")) == (K.REVIEW, None, RECHECK)
    cfg = reviewed(store, clone, monkeypatch, F7=False)
    assert (cfg.cap, cfg.plan_tasks, cfg.rechecks) == (0, (), ("F7",))
    c = store.read("c1")
    lp = c.loops[FINAL]
    assert (lp.round, lp.ended, lp.unreviewed, at(c)) == (3, "count", ["t3"], (K.PUBLISH, None, None))


def test_a_final_dispute_the_owner_decides_is_fixed_and_ends_the_loop(tmp_path, clone, monkeypatch):
    store = stored(tmp_path)
    reviewed(store, clone, monkeypatch, range(1, 6))
    built(store, clone, monkeypatch, "c\n", "F2")
    reviewed(store, clone, monkeypatch, F2=True)
    q = loop.open_question(store.read("c1"))
    assert ("did not accept the builder's rejection" in q.text, q.cause.endswith("t2 F2")) == (True, True)
    c = answer(store, "fix", "use Hallo")
    assert at(c) == (K.REVIEW, None, "disputed")
    monkeypatch.setattr(runner, "_kept", lambda *_a: pytest.fail("a decided dispute starts no session"))
    c = step(store, clone)
    fix = c.plan.tasks[-1]
    assert (fix.fixes, fix.settled, fix.detail.startswith("- F2: "), at(c)) == (
        FINAL,
        ["F2"],
        True,
        (K.BUILD, "t3", None),
    )
    assert (c.budgets.loops, progress(c).sub) == ({"final": 2}, "Fixing final review findings")
    built(store, clone, monkeypatch, "d\n")
    c = store.read("c1")
    assert (c.loops[FINAL].ended, c.loops[FINAL].findings[1].state, at(c)) == (
        "count",
        "fixed",
        (K.PUBLISH, None, None),
    )


def test_a_final_reconsideration_the_owner_asks_for_runs_before_the_review_completes(tmp_path, clone, monkeypatch):
    store = stored(tmp_path)
    reviewed(store, clone, monkeypatch, range(1, 6))
    built(store, clone, monkeypatch, "c\n", "F2")
    reviewed(store, clone, monkeypatch, F2=True)
    assert at(answer(store, "reconsider", "AC-1 allows English")) == (K.REVIEW, None, "disputed")
    seen = []

    def run(_store, _lock, _change, path, made, _label, **_kw):
        seen.append(made(path))
        verdict = {"finding": "F2", "verdict": "withdrawn", "reason": "AC-1 allows English"}
        result = dispute_tools.ReconsiderResult(reconsidered=[verdict])
        return loop.StepResult(exit=Exit.DONE, reason="judged"), Run("s", "result", result, termination=DONE)

    monkeypatch.setattr(reconsider.sessions, "review_run", run)
    c = step(store, clone)
    assert (seen[0].rechecks, "The owner's note: AC-1 allows English" in seen[0].message) == (("F2",), True)
    assert (c.loops[FINAL].findings[1].state, at(c)) == ("withdrawn", (K.PUBLISH, None, None))


@pytest.mark.parametrize(
    ("finding", "error"),
    [
        ({"tasks": ["t1"]}, None),
        ({"no_task": "the shared config file belongs to no task"}, None),
        ({}, "findings[1]: name its plan tasks in `tasks`, or say in `no_task` why none fits"),
        ({"tasks": ["t9"]}, "findings[1].tasks: t9 is no plan task - use t1"),
    ],
)
def test_a_final_finding_names_its_plan_tasks_or_says_why_none_fits(tmp_path, finding, error):
    tree = tools.Worktree(head="b", base="a")
    cfg = sdk_adapter.Session(
        K.REVIEW, tmp_path, "s1", "m", resume=False, policy=Policy(tmp_path), observe=lambda: tree, checks=(),
        submit=tools.REVIEW, plan_tasks=("t1",),
    )  # fmt: skip
    g = Gate(cfg, Run("s1"), lambda **_e: None, lambda: None)
    found = [{"place": "a.txt:1", "problem": "p", "fix": "f"} | finding]
    text, ok = g.call(tools.REVIEW, {"verdict": "fix", "findings": found})
    assert (ok, text) == (True, ACCEPTED) if error is None else (not ok and error in text)


def test_a_final_loop_ended_unreviewed_publishes_on_its_completion_for_that_content_only(tmp_path, clone, monkeypatch):
    store = stored(tmp_path)
    reviewed(store, clone, monkeypatch, range(1, 3))
    built(store, clone, monkeypatch, "c\n")
    c = store.read("c1")
    head = git(clone, "rev-parse", "HEAD")
    assert (c.loops[FINAL].ended, c.loops[FINAL].completion.head, at(c)) == ("count", head, (K.PUBLISH, None, None))
    assert publish.reviewed(c, clone, head) is True
    git(clone, "commit", "-q", "--allow-empty", "-m", "same content")
    assert publish.reviewed(c, clone, git(clone, "rev-parse", "HEAD")) is True
    moved = c.model_copy(deep=True)
    moved.brief.criteria[0].version = 2
    assert publish.reviewed(moved, clone, head) is False  # a changed criterion voids it, as it voids a review
    (clone / "a.txt").write_text("new work\n")
    git(clone, "commit", "-qam", "new work")
    assert publish.reviewed(c, clone, git(clone, "rev-parse", "HEAD")) is False


def test_new_work_after_the_final_loop_ended_adds_one_focused_round(tmp_path, clone, monkeypatch):
    store = stored(tmp_path, RoundLoop(subject=FINAL, policy=RoundPolicy(max_rounds=1)))
    reviewed(store, clone, monkeypatch, range(1, 3))
    built(store, clone, monkeypatch, "c\n", "F2")  # the last round's rejection stays unjudged for now
    c = store.read("c1")
    reviewed_head = c.loops[FINAL].head
    c.plan.tasks.append(Task(id="t3", title="Fix the failing CI check", scope=["a.txt"], origin="ci"))
    c.step = Step(kind=K.BUILD, task="t3")  # CI failed after publishing
    store.write(Lock("c1"), c)
    built(store, clone, monkeypatch, "ci fix\n")
    assert at(store.read("c1")) == FINAL_STEP  # no review of its own
    cfg = reviewed(store, clone, monkeypatch, F2=False)
    assert f"## New since the last round: `git diff {reviewed_head[:12]}..HEAD`" in cfg.message
    assert (round_flow.FOCUS in cfg.message, cfg.rechecks) == (True, ("F2",))
    c = store.read("c1")
    lp = c.loops[FINAL]
    assert (lp.round, lp.extra, lp.ended, lp.reentry, lp.completion, lp.findings[1].state, at(c)) == (
        2,
        1,
        "clean",
        False,
        None,
        "standing",
        (K.PUBLISH, None, None),
    )


def test_the_owner_is_asked_after_the_last_final_round_and_may_accept_it_as_done(tmp_path, clone, monkeypatch):
    store = stored(tmp_path, RoundLoop(subject=FINAL, policy=RoundPolicy(max_rounds=1)))
    reviewed(store, clone, monkeypatch, range(1, 9))
    built(store, clone, monkeypatch, "c\n", "F8")
    q = loop.open_question(store.read("c1"))
    assert [o.id for o in q.options] == ["rebuild", "accept", "another", "replan", "clean"]
    assert q.text.startswith("Final review round 1 found 8 new findings, and it was the last allowed round: F1 fixed")
    c = answer(store, "another")
    assert (c.loops[FINAL].extra, c.loops[FINAL].completion, at(c)) == (1, None, FINAL_STEP)
    reviewed(store, clone, monkeypatch, range(9, 17), F8=False)
    built(store, clone, monkeypatch, "d\n")
    assert "Final review round 2" in loop.open_question(store.read("c1")).text
    c = answer(store, "accept")
    head = git(clone, "rev-parse", "HEAD")
    assert (c.loops[FINAL].ended, c.loops[FINAL].unreviewed, at(c)) == ("accepted", ["t3"], (K.PUBLISH, None, None))
    assert publish.reviewed(c, clone, head) is True


def test_a_change_with_an_earlier_final_review_keeps_the_old_rules(tmp_path, clone):
    c = Change(slug="c1", brief=Brief(version=1), step=Step(kind=K.REVIEW, mode="final"))
    c.reviews = [Review(commit="a" * 40, inputs=Inputs(), verdict="fix")]
    review.started(c, None, clone, Store(tmp_path / "s").settings())
    assert c.loops == {}


def test_a_repair_of_no_task_goes_to_the_next_final_round_and_is_no_final_loop_repair():
    visual = Task(id="t2", title="Fix: the visual check of home", origin="review")
    c = Change(slug="c1", brief=Brief(version=1), plan=Plan(tasks=[Task(id="t1", title="one", done=True), visual]))
    c.loops[FINAL] = RoundLoop(subject=FINAL, policy=RoundPolicy(), last=True)
    c.step = Step(kind=K.BUILD, task="t2")
    round_flow.built(c, loop.StepResult(exit=Exit.DONE, head="b" * 40), NOW)
    assert (at(c), visual.done, c.loops[FINAL].batch, c.loops[FINAL].completion) == (FINAL_STEP, True, [], None)


@dataclass
class Host:
    runs: bool = False
    wake = type("W", (), {"set": lambda _self: None})()
    record = None

    def activity(self, _slug):
        return Activity(host_up=True, runner_alive=self.runs)


def test_the_restart_runs_only_at_or_after_the_final_review_and_starts_a_new_attempt(tmp_path):
    lp = RoundLoop(subject=FINAL, policy=RoundPolicy(), round=2, ended="count", batch=["t2"])
    c = Change(
        slug="c1",
        brief=Brief(version=1),
        plan=Plan(tasks=[Task(id="t1", title="one", done=True), Task(id="t2", title="fix", fixes=FINAL)]),
        step=Step(kind=K.MERGE),
        loops={FINAL: lp},
    )
    ask(c, Question(step=K.MERGE, text="merge?", cause=loop.CONSENT), NOW)
    store = Store(tmp_path / "store")
    store.write(Lock("c1"), c)
    host = Host(runs=True)
    client = TestClient(
        api.create_app(store, "t", host), base_url="http://127.0.0.1", headers={"authorization": "Bearer t"}
    )
    assert client.get("/api/next/changes/c1").json()["restartable"] is True
    assert client.post("/api/next/changes/c1/restart-review").status_code == 409  # a step is running
    host.runs = False
    assert client.post("/api/next/changes/c1/restart-review").json() == {"accepted": "restart-review"}
    after = loop.fold(c, [RestartItem(at=NOW)], NOW)
    new = after.loops[FINAL]
    assert (new.attempt, new.round, [(h.attempt, h.round, h.ended) for h in new.history]) == (2, 0, [(1, 2, "count")])
    q = after.questions[0]
    assert (q.answer.option, q.effect_observed_at, after.outcome, after.plan.tasks[1].done, at(after)) == (
        round_flow.RESTARTED,
        NOW,
        None,
        True,
        FINAL_STEP,
    )
    late = loop.fold(c, [RestartItem(at=NOW), ConsentItem(at=NOW, head="b" * 40)], NOW)
    assert (late.consent, at(late)) == (None, FINAL_STEP)  # a consent from the old dialog revives nothing
    assert loop.fold(c, [ConsentItem(at=NOW, head="b" * 40)], NOW).consent.head == "b" * 40  # while it waits
    c.consent = MergeConsent(head="a" * 40, at=NOW)  # an earlier head's consent while the new head waits for one
    assert round_flow.restartable(c) == ""
    c.outcome = None  # consented: the merge runs
    assert round_flow.restartable(c) == "a merge is under way"
    assert loop.fold(c, [RestartItem(at=NOW)], NOW).loops[FINAL].attempt == 1  # refused again under the lock
    c.step = Step(kind=K.FOLLOW)  # an earlier head's consent, while the pull request is followed
    assert loop.fold(c, [RestartItem(at=NOW)], NOW).consent is None
    c.consent, c.step = None, Step(kind=K.BUILD, task="t1")
    store.write(Lock("c1"), c)
    assert client.get("/api/next/changes/c1").json()["restartable"] is False
    assert client.post("/api/next/changes/c1/restart-review").status_code == 409
