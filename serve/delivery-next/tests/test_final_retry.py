"""TD-210, TD-214, TD-217: the final review's retry: the owner's task list, the undo of the ticked tasks, a new plan."""

import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from owlbear_delivery_next import api, loop, prompts, rebuilds, round_flow, runner
from owlbear_delivery_next.inbox import AnswerItem
from owlbear_delivery_next.models import (
    Brief,
    Change,
    Exit,
    Inputs,
    MergeConsent,
    Names,
    Plan,
    Review,
    Step,
    StepKind,
    Task,
)
from owlbear_delivery_next.moves import ask
from owlbear_delivery_next.profile_record import Profile
from owlbear_delivery_next.round_records import FINAL, Completion, RoundFinding, RoundLoop, RoundPolicy
from owlbear_delivery_next.status import Activity
from owlbear_delivery_next.steps import retry
from owlbear_delivery_next.store import Lock, Store

NOW = datetime(2026, 10, 17, 3, tzinfo=UTC)
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
    git(work, "branch", "main")
    monkeypatch.setattr(runner.worktree, "ensure", lambda *_a: work)
    monkeypatch.setattr(retry.worktree, "ensure", lambda *_a: work)
    return work


def commit(clone: Path, name: str, text: str) -> str:
    (clone / name).write_text(text)
    git(clone, "add", name)
    git(clone, "commit", "-qm", f"{name}: {text.strip()}")
    return git(clone, "rev-parse", "HEAD")


def build(clone: Path, task: Task, name: str, text: str) -> Task:
    """One accepted build of *task*: its base, its commit and the head Delivery recorded."""
    task.base, task.done = git(clone, "rev-parse", "HEAD"), True
    task.head = commit(clone, name, text)
    return task


def asked(clone: Path) -> Change:
    """t1 and its repair t3 change x.txt, t2 changes y.txt; final repairs t4 (of t1) and t5 (of t2), then the question.

    The last round's open F3 names t2; the reviews of t1 and t2 both covered x.txt.
    """
    t1 = build(clone, Task(id="t1", title="one", checks=["check one"]), "x.txt", "1\n")
    t3 = build(clone, Task(id="t3", title="fix", origin="review", fixes="t1"), "x.txt", "1b\n")
    t2 = build(clone, Task(id="t2", title="two", checks=["check two"]), "y.txt", "2\n")
    t4 = build(clone, Task(id="t4", title="fix final", origin="review", fixes=FINAL), "x.txt", "1c\n")
    t5 = build(clone, Task(id="t5", title="fix final", origin="review", fixes=FINAL), "y.txt", "2b\n")
    findings = [
        RoundFinding(id="F1", text="x.txt:1: p - fix: f", raised=1, tasks=["t1"], state="fixed", repair="t4"),
        RoundFinding(id="F2", text="y.txt:1: p - fix: f", raised=1, tasks=["t2"], state="fixed", repair="t5"),
        RoundFinding(id="F3", text="y.txt:2: p - fix: f", raised=1, tasks=["t2"]),
    ]
    head = git(clone, "rev-parse", "HEAD")
    lp = RoundLoop(subject=FINAL, policy=RoundPolicy(max_rounds=1), round=1, found=8, last=True, findings=findings)
    lp.completion, lp.head = Completion(head=head), t3.head or ""
    covered = [Review(task=t, commit=head, inputs=Inputs(paths=p), verdict="pass") for t, p in (
        ("t3", {"x.txt": "b"}), ("t2", {"y.txt": "b", "x.txt": "b"}))]  # fmt: skip
    c = Change(
        slug="c1",
        brief=Brief(version=1),
        plan=Plan(tasks=[t1, t2, t3, t4, t5]),
        names=Names(branch="owlbear/c1", target="main"),
        step=Step(kind=K.BUILD, task="t5"),
        loops={FINAL: lp, "t1": RoundLoop(subject="t1", since=1, policy=RoundPolicy(), ended="clean")},
        reviews=covered,
        consent=MergeConsent(head=head, at=NOW),
    )
    ask(c, round_flow.question(lp, t5), NOW)
    return c


@dataclass
class Host:
    runs: bool = False
    wake = type("W", (), {"set": lambda _self: None})()
    record = None

    def activity(self, _slug):
        return Activity(host_up=True, runner_alive=self.runs)


def client(store: Store) -> TestClient:
    app = api.create_app(store, "t", Host())
    return TestClient(app, base_url="http://127.0.0.1", headers={"authorization": "Bearer t"})


def answered(store: Store, option: str, **fields) -> Change:
    c = store.read("c1")
    q = loop.open_question(c)
    c, _ = loop.schedule(c, [AnswerItem(at=NOW, question=q.id, option=option, **fields)], NOW)
    store.write(Lock("c1"), c)
    return c


def step(store: Store, clone: Path) -> Change:
    c = store.read("c1")
    runner._step(store, Lock("c1"), c, c.step, clone)  # noqa: SLF001
    return store.read("c1")


def at(c: Change) -> tuple:
    return c.step.kind, c.step.task, c.step.mode


def test_the_page_lists_the_plan_tasks_and_a_rebuild_is_bound_to_what_it_showed(tmp_path, clone):
    store = Store(tmp_path / "store")
    store.write(Lock("c1"), asked(clone))
    shown = client(store).get("/api/next/changes/c1").json()
    retry_list, q = shown["retry"], shown["question"]
    assert [o["label"] for o in q["options"]] == [
        "Rebuild the ticked tasks",
        "Accept as done",
        "Another round",
        "Plan again from the brief on the existing code",
        "Plan again from the brief from a clean state",
    ]
    head = git(clone, "rev-parse", "HEAD")
    assert (retry_list["attempt"], retry_list["head"]) == (1, head)
    assert retry_list["tasks"] == [
        {"id": "t1", "title": "one", "ticked": False, "shares": ["t2"]},  # t3's review covered x.txt, as did t2's
        {"id": "t2", "title": "two", "ticked": True, "shares": ["t1"]},  # F3 is open and names t2
    ]
    post = client(store).post
    sent = {"question": q["id"], "option": "rebuild", "attempt": 1, "head": head}
    assert post("/api/next/changes/c1/answers", json=sent | {"tasks": []}).status_code == 422
    assert post("/api/next/changes/c1/answers", json=sent | {"tasks": ["t3"]}).status_code == 422  # a repair
    assert post("/api/next/changes/c1/answers", json=sent | {"tasks": ["t1"], "head": "b" * 40}).status_code == 409
    assert post("/api/next/changes/c1/answers", json=sent | {"tasks": ["t1"], "attempt": 2}).status_code == 409
    accept = {"question": q["id"], "option": "accept", "tasks": ["t1"]}
    assert post("/api/next/changes/c1/answers", json=accept).status_code == 422  # only Rebuild names tasks
    assert post("/api/next/changes/c1/answers", json=sent | {"tasks": ["t2", "t1"]}).status_code == 200
    assert answered(store, "rebuild").loops[FINAL].rebuild == []  # the fold refuses a Rebuild without tasks
    assert loop.open_question(store.read("c1")) is not None
    c = answered(store, "rebuild", tasks=["t2", "t1"])
    assert (c.loops[FINAL].rebuild, at(c)) == (["t1", "t2"], (K.REVIEW, None, round_flow.RETRY))


def test_a_rebuild_undoes_the_ticked_tasks_own_work_and_builds_them_again(tmp_path, clone, monkeypatch):
    store = Store(tmp_path / "store")
    store.write(Lock("c1"), asked(clone))
    archived = git(clone, "rev-parse", "HEAD")
    answered(store, "rebuild", tasks=["t1"])
    monkeypatch.setattr(runner, "_kept", lambda *_a: pytest.fail("the undo starts no session"))
    c = step(store, clone)
    assert git(clone, "rev-parse", retry.archive("c1", FINAL, 1, archived)) == archived
    assert git(clone, "rev-parse", "HEAD^") == archived  # one forward commit on the same branch
    assert (not (clone / "x.txt").exists(), (clone / "y.txt").read_text()) == (True, "2b\n")  # t1, t3, t4 undone
    t1, t2, t3, t4, t5 = c.plan.tasks
    assert [(t.done, t.base, t.head) for t in (t1, t3, t4)] == [(False, None, None)] + [(True, None, None)] * 2
    assert (t2.head, t5.head) == (git(clone, "rev-parse", "HEAD~3"), archived)  # kept work keeps its range
    assert t1.checks == ["check one", "check two"]  # the last rebuilt task runs every other plan task's checks
    lp = c.loops[FINAL]
    assert (lp.ended, lp.rebuild, lp.completion, c.consent) == ("retried", [], None, None)
    assert (c.loops["t1"].attempt, c.loops["t1"].since, [h.ended for h in c.loops["t1"].history]) == (2, 5, ["retried"])
    assert at(c) == (K.BUILD, "t1", None)


def test_a_promoted_final_undo_is_found_again_and_never_reverted_twice(clone):
    c = asked(clone)
    lp = c.loops[FINAL]
    lp.rebuild = ["t1"]
    undo, _ = rebuilds.undoing(c, lp)
    assert retry._taken(clone, c, lp, undo) == ""  # noqa: SLF001
    head = git(clone, "rev-parse", "HEAD")
    assert retry._taken(clone, c, lp, undo) == ""  # noqa: SLF001 - a restart before the record was written
    assert git(clone, "rev-parse", "HEAD") == head


def test_a_final_repair_of_rebuilt_and_kept_work_stops_the_undo_with_a_question(tmp_path, clone):
    c = asked(clone)
    c.loops[FINAL].findings[1].tasks = ["t1", "t2"]  # t5 fixed a finding of both
    store = Store(tmp_path / "store")
    store.write(Lock("c1"), c)
    head = git(clone, "rev-parse", "HEAD")
    answered(store, "rebuild", tasks=["t1"])
    c = step(store, clone)
    q = loop.open_question(c)
    assert "final repair t5 fixed findings of both rebuilt and kept work" in q.text
    assert ([o.id for o in q.options], q.cause) == (["another", "pause"], f"{round_flow.PREFIX}{FINAL} t5")
    assert (git(clone, "rev-parse", "HEAD"), git(clone, "for-each-ref", "refs/heads/owlbear/archive")) == (head, "")
    c = answered(store, "another")
    assert (c.loops[FINAL].extra, c.loops[FINAL].rebuild, at(c)) == (1, [], (K.REVIEW, None, "final"))


def test_another_tasks_build_inside_an_undone_range_keeps_its_commits(clone):
    t1 = Task(id="t1", title="one", done=True, base=git(clone, "rev-parse", "HEAD"))
    t6 = Task(id="t6", title="merge", origin="integration", done=True, base=commit(clone, "x.txt", "1\n"))
    t6.head = commit(clone, "t.txt", "target\n")
    t1.head = commit(clone, "x.txt", "1d\n")  # t1's build went on after the integration
    c = Change(slug="c1", brief=Brief(version=1), plan=Plan(tasks=[t1, t6]))
    lp = RoundLoop(subject=FINAL, policy=RoundPolicy(), rebuild=["t1"])
    undo, why = rebuilds.undoing(c, lp)
    assert ([t.id for t in undo], why) == (["t1"], "")
    t6.head = None  # an end Delivery never recorded
    refused = retry._commits(clone, c, undo, git(clone, "rev-parse", "HEAD"))[1]  # noqa: SLF001
    assert refused == "task t6 was built inside the undone work and its commits are not recorded"
    t6.head = git(clone, "rev-parse", "HEAD^")
    assert retry._taken(clone, c, lp, undo) == ""  # noqa: SLF001
    assert (not (clone / "x.txt").exists(), (clone / "t.txt").read_text()) == (True, "target\n")


def test_a_task_whose_commits_are_not_recorded_is_not_undone():
    c = Change(slug="c1", brief=Brief(version=1), plan=Plan(tasks=[Task(id="t1", title="one", base="a" * 40)]))
    lp = RoundLoop(subject=FINAL, policy=RoundPolicy(), rebuild=["t1"])
    assert rebuilds.undoing(c, lp) == ([], "the commits of task t1 are not recorded")


def test_a_final_repair_that_also_fixed_a_finding_of_no_task_is_kept_work():
    t1 = Task(id="t1", title="one", base="a" * 40, head="b" * 40)
    t2 = Task(id="t2", title="fix final", origin="review", fixes=FINAL, base="b" * 40, head="c" * 40)
    c = Change(slug="c1", brief=Brief(version=1), plan=Plan(tasks=[t1, t2]))
    found = [RoundFinding(id=f"F{n}", text="x", raised=1, tasks=k, state="fixed", repair="t2") for n, k in (
        (1, ["t1"]), (2, []))]  # fmt: skip
    lp = RoundLoop(subject=FINAL, policy=RoundPolicy(), rebuild=["t1"], findings=found[:1])
    assert [t.id for t in rebuilds.undoing(c, lp)[0]] == ["t1", "t2"]
    lp.history = [RoundLoop(subject=FINAL, policy=RoundPolicy(), findings=found[1:])]  # an earlier attempt's
    assert rebuilds.undoing(c, lp)[1].startswith("final repair t2 fixed findings of both rebuilt and kept work")


STATES = [("open", True), ("escalated", True), ("owner-fix", True), ("fixed", False), ("rejected", False),
    ("standing", False), ("owner-drop", False), ("withdrawn", False)]  # fmt: skip


@pytest.mark.parametrize(("state", "ticked"), STATES)
def test_a_task_with_a_finding_still_to_fix_starts_ticked(state, ticked):
    tasks = [Task(id="t1", title="one"), Task(id="t2", title="two")]
    c = Change(slug="c1", brief=Brief(version=1), plan=Plan(tasks=tasks))
    c.loops = {
        FINAL: RoundLoop(
            subject=FINAL,
            policy=RoundPolicy(),
            findings=[RoundFinding(id="F1", text="x", raised=1, tasks=["t1"], state=state)],
        ),
        "t2": RoundLoop(
            subject="t2", policy=RoundPolicy(), findings=[RoundFinding(id="F1", text="x", raised=1, state=state)]
        ),
    }
    ask(c, round_flow.question(c.loops[FINAL], c.plan.tasks[0]), NOW)
    listed = rebuilds.shown(c, c.questions[0])["tasks"]
    assert [(t["ticked"], t["shares"]) for t in listed] == [(ticked, []), (ticked, [])]  # no shared files known


def test_a_clean_plan_undoes_all_the_changes_work_and_plans_again(tmp_path, clone):
    git(clone, "switch", "-qc", "side", "main")
    commit(clone, "t.txt", "target\n")
    git(clone, "switch", "-q", "owlbear/c1")
    c = asked(clone)
    git(clone, "merge", "-q", "--no-ff", "-m", "merge the target", "side")
    git(clone, "branch", "-qf", "main", "side")
    store = Store(tmp_path / "store")
    store.write(Lock("c1"), c)
    archived = git(clone, "rev-parse", "HEAD")
    answered(store, "clean")
    c = step(store, clone)
    assert git(clone, "rev-parse", retry.archive("c1", FINAL, 1, archived)) == archived
    assert (git(clone, "diff", "main", "HEAD"), git(clone, "rev-parse", "HEAD^")) == ("", archived)
    lp = c.loops[FINAL]
    assert (list(c.loops), lp.attempt, lp.round, [(h.subject, h.ended) for h in lp.history]) == (
        [FINAL],
        2,
        0,
        [(FINAL, "retried"), ("t1", "clean")],
    )
    assert (at(c), c.outcome.exit, c.consent) == ((K.PLAN, None, None), Exit.BACK, None)
    assert c.outcome.reason.startswith("The owner rejected the work after final review round 1 and asked for a new ")
    assert "from a clean state" in c.outcome.reason
    assert "F3: y.txt:2: p - fix: f" in c.outcome.reason
    message = prompts.plan(c, Profile(), clone, {})
    assert "## Why the Change is planned again" in message
    assert "from a clean state" in message


def test_a_plan_on_the_existing_code_keeps_the_branch_as_it_is(tmp_path, clone):
    store = Store(tmp_path / "store")
    store.write(Lock("c1"), asked(clone))
    head = git(clone, "rev-parse", "HEAD")
    c = answered(store, "replan")
    assert (at(c), c.outcome.exit, c.loops[FINAL].attempt, git(clone, "rev-parse", "HEAD")) == (
        (K.PLAN, None, None),
        Exit.BACK,
        2,
        head,
    )
    assert "on the existing code" in c.outcome.reason


def test_a_build_records_the_head_it_was_accepted_at():
    c = Change(slug="c1", brief=Brief(version=1), plan=Plan(tasks=[Task(id="t1", title="one")]))
    c.step = Step(kind=K.BUILD, task="t1")
    round_flow.built(c, loop.StepResult(exit=Exit.DONE, head="b" * 40), NOW)
    assert c.plan.tasks[0].head == "b" * 40
