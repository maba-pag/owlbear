"""The findings loop's repair chances (TD-123, TD-175): the producing session repairs once; a fresh one is told."""

import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

from owlbear_delivery_next.change_contracts import tools
from owlbear_delivery_next.change_contracts.models import (
    Answer,
    Brief,
    Change,
    Exit,
    Names,
    Outcome,
    Plan,
    Question,
    Step,
    StepKind,
    Task,
)
from owlbear_delivery_next.change_contracts.round_records import RoundPolicy
from owlbear_delivery_next.change_flow import loop, plan_rounds, repairs
from owlbear_delivery_next.commands import runner
from owlbear_delivery_next.local_system.processes import Termination
from owlbear_delivery_next.runtimes import session_result
from owlbear_delivery_next.runtimes.results import Gate
from owlbear_delivery_next.runtimes.session_result import Run
from owlbear_delivery_next.state_store.store import Lock, Store
from owlbear_delivery_next.workflow_steps import plan_round

NOW = datetime(2026, 10, 16, 3, tzinfo=UTC)
K = StepKind


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
    monkeypatch.setattr(runner.worktree, "ensure", lambda *_a: work)
    return work


def change(*tasks: Task) -> Change:
    names = Names(branch="owlbear/c1", target="main")
    return Change(slug="c1", brief=Brief(version=1), plan=Plan(tasks=list(tasks)), names=names)


def task(c: Change, tid: str) -> Task:
    return next(t for t in c.plan.tasks if t.id == tid)


def findings(c: Change, fix: str, *more: str) -> Change:
    """The current review step finds something: its repair task, and further parts, join the plan."""
    parts = [Task(id=m, title="more", origin="review") for m in more]
    found = loop.StepResult(
        exit=Exit.RETRY, reason="findings", fix_task=Task(id=fix, title="fix", origin="review"), more_fixes=parts
    )
    c.budgets.rounds.clear()  # each round here is progress; the round limit is not what these tests are about
    return loop.apply(c, found, NOW)


def built(c: Change, tid: str, session: str) -> None:
    t = task(c, tid)
    t.built_by, t.earlier, t.done = session, f"{tid} built", True


def test_a_task_review_repair_resumes_the_producing_session_once_and_a_fresh_successor_gets_its_own():
    c = change(Task(id="t1", title="one", built_by="s-build", earlier="Added b."))
    c.step = Step(kind=K.REVIEW, task="t1")
    c = findings(c, "f1", "f1b")
    assert (c.step.kind, c.step.task) == (K.BUILD, "f1")
    assert [(t.fixes, t.resume, t.earlier) for t in c.plan.tasks[1:]] == [("t1", "s-build", "Added b.")] * 2
    built(c, "f1", "s-build")  # the resumed producer built the repair; both parts are one chance
    c.step = Step(kind=K.REVIEW, task="f1")
    c = findings(c, "f2")
    assert (task(c, "f2").fixes, task(c, "f2").resume) == ("f1", "")
    built(c, "f2", "s-fresh")
    c.step = Step(kind=K.REVIEW, task="f2")
    c = findings(c, "f3")
    assert task(c, "f3").resume == "s-fresh"


def test_a_final_review_repair_starts_fresh_then_its_repairer_gets_one_chance():
    c = change(Task(id="t1", title="one", built_by="s1", done=True))
    final = Step(kind=K.REVIEW, mode="final")
    c.step = final.model_copy()
    c = findings(c, "r1")
    assert task(c, "r1").resume == ""  # the whole Change was reviewed: no one session produced it
    built(c, "r1", "s-r1")
    c.step = final.model_copy()
    c = findings(c, "r2")
    assert task(c, "r2").resume == "s-r1"
    built(c, "r2", "s-r1")
    c.step = final.model_copy()
    c = findings(c, "r3")
    assert task(c, "r3").resume == ""


def test_a_challenged_planner_resumes_until_its_plan_is_accepted_then_a_fresh_planner_gets_its_own_chance():
    c = change()
    c.step = Step(kind=K.PLAN, session="p1")
    c.outcome = Outcome(exit=Exit.RETRY, reason="plan challenge: t2 has no check", challenged=True, at=NOW)
    assert (repairs.session(c, None), c.step.repair) == ("p1", "p1")
    c.outcome = Outcome(exit=Exit.RETRY, reason="network", at=NOW)  # the repair failed before a plan came back
    assert repairs.session(c, None) == "p1"  # the chance is still in flight: the replay resumes it again
    planned = loop.StepResult(exit=Exit.DONE, plan=Plan(tasks=[Task(id="t1", title="one")]))
    repairs.bind(c, None, "p1", None, planned)
    assert (c.step.resumed, c.step.repair) == ("p1", "")
    c.outcome = Outcome(exit=Exit.RETRY, reason="plan challenge: still no check", challenged=True, at=NOW)
    assert repairs.session(c, None) == ""
    c.step.session = "p2"
    assert repairs.session(c, None) == "p2"


def test_only_the_typed_flag_marks_a_challenged_plan_never_its_reason_text():
    c = change()
    c.step = Step(kind=K.PLAN, session="p1")
    c.outcome = Outcome(exit=Exit.RETRY, reason="plan challenge: t2 has no check", at=NOW)  # text only
    assert (repairs.session(c, None), c.step.repair) == ("", "")
    result = loop.StepResult(exit=Exit.RETRY, reason="t2 has no check", challenged=True)
    assert loop.apply(c, result, NOW).outcome.challenged is True  # the loop keeps the runner's flag


def test_a_challenged_plan_comes_back_with_the_flag_and_a_display_reason():
    c = change()
    c.step = Step(kind=K.PLAN, mode=plan_rounds.CHALLENGE)
    plan_rounds.loop(c, RoundPolicy(), NOW)
    found = loop.StepResult(exit=Exit.RETRY, reason="t2 has no check")
    review = tools.ReviewResult(verdict="fix", findings=[{"place": "t2", "problem": "AC-1", "fix": "add a check"}])
    back = plan_round.judged(c, found, review)
    assert (back.exit, back.challenged, back.reason) == (
        Exit.RETRY,
        True,
        "plan challenge: t2: AC-1 - fix: add a check",
    )


def built_run(cfg, head: str) -> Run:
    payload = tools.BuildResult(summary="Fixed b.", checks=[])
    run = Run(cfg.session_id, "result", payload, head=head, termination=Termination(confirmed=True))
    run.usage = {"models": {}}
    return run


def gated_run(cfg) -> Run:
    """The builder's result through Delivery's own gate, which reads the worktree the runner points it at."""
    run = Run(cfg.session_id, termination=Termination(confirmed=True))
    text, ok = Gate(cfg, run, lambda **_e: None, lambda: None).call(tools.SUBMIT, {"summary": "Fixed b.", "checks": []})
    assert ok, text
    run.usage = {"models": {}}
    return run


def save(work: Path, name: str, text: str) -> None:
    (work / name).write_text(text)
    git(work, "add", "-A")
    git(work, "commit", "-qm", name)


def repairing(tmp_path) -> tuple[Store, Change]:
    store = Store(tmp_path / "store")
    c = change(
        Task(id="t1", title="one", built_by="s-build", earlier="Added b.", done=True),
        Task(id="f1", title="fix", origin="review", fixes="t1", resume="s-build", earlier="Added b."),
    )
    c.step = Step(kind=K.BUILD, task="f1")
    store.write(Lock("c1"), c)
    return store, c


def test_the_repair_build_resumes_the_producer_and_binds_the_accepted_result(tmp_path, clone, monkeypatch):
    store, c = repairing(tmp_path)
    seen = []

    git(clone, "branch", "main")

    async def build(cfg):
        seen.append((cfg.session_id, cfg.resume, cfg.fresh))
        save(clone, "b.txt", "b\n")
        return gated_run(cfg)

    monkeypatch.setattr(runner.sdk_adapter, "run", build)
    runner._step(store, Lock("c1"), c, c.step, clone)  # noqa: SLF001
    assert seen[0][:2] == ("s-build", True)
    assert seen[0][2].endswith(repairs.EARLIER.format("Added b."))  # what a fresh fallback would be told
    after = task(store.read("c1"), "f1")
    assert (after.built_by, after.earlier) == ("s-build", "Fixed b. Changed: b.txt")


def test_a_repair_is_told_the_paths_delivery_read_at_the_accepted_head(tmp_path, clone, monkeypatch):
    store, c = repairing(tmp_path)
    git(clone, "branch", "main")

    async def build(cfg):
        git(clone, "mv", "a.txt", "moved.txt")
        git(clone, "commit", "-qm", "move")
        git(clone, "checkout", "-q", "main")
        save(clone, "target.txt", "the target's own\n")
        git(clone, "checkout", "-q", "owlbear/c1")
        git(clone, "merge", "-q", "--no-edit", "main")  # a target merge: its paths are not the task's work
        save(clone, "new.txt", "n\n")
        return gated_run(cfg)

    monkeypatch.setattr(runner.sdk_adapter, "run", build)
    runner._step(store, Lock("c1"), c, c.step, clone)  # noqa: SLF001
    after = task(store.read("c1"), "f1")
    assert after.earlier == "Fixed b. Changed: a.txt, moved.txt, new.txt"  # both ends of the rename
    assert after.earlier in repairs.fallback(after)


def test_a_missing_producer_falls_back_to_a_fresh_session_without_charging_a_budget(tmp_path, clone, monkeypatch):
    store, c = repairing(tmp_path)

    async def build(cfg):
        fresh = cfg.journal.replaced()  # the runtime found no producing session to resume
        return built_run(type("C", (), {"session_id": fresh})(), git(clone, "rev-parse", "HEAD"))

    monkeypatch.setattr(runner.sdk_adapter, "run", build)
    runner._step(store, Lock("c1"), c, c.step, clone)  # noqa: SLF001
    after = store.read("c1")
    fell = [e for e in store.events("c1") if e.get("event") == "repair-fallback"]
    assert [e["session"] for e in fell] == ["s-build"]
    assert task(after, "f1").built_by == fell[0]["fresh"] != "s-build"
    assert session_result.missing_cause(K.BUILD) not in after.budgets.causes


def test_an_answered_repair_session_keeps_its_free_fallback(tmp_path, clone, monkeypatch):
    store, c = repairing(tmp_path)
    c.step.session = "s-build"  # the resumed producer asked the owner during its repair
    c.questions = [Question(id="q1", step=K.BUILD, text="Which?", answer=Answer(text="This one.", at=NOW))]
    store.write(Lock("c1"), c)
    seen = []

    async def build(cfg):
        seen.append(cfg)
        fresh = cfg.journal.replaced()
        return built_run(type("C", (), {"session_id": fresh})(), git(clone, "rev-parse", "HEAD"))

    monkeypatch.setattr(runner.sdk_adapter, "run", build)
    runner._step(store, Lock("c1"), c, c.step, clone)  # noqa: SLF001
    assert (seen[0].session_id, seen[0].resume) == ("s-build", True)
    assert [e["session"] for e in store.events("c1") if e.get("event") == "repair-fallback"] == ["s-build"]
    assert session_result.missing_cause(K.BUILD) not in store.read("c1").budgets.causes
