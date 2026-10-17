"""TD-210, TD-214, TD-217: the final review's retry: the owner's task list, the undo of the ticked tasks, a new plan."""

import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from owlbear_delivery_next import api, held, loop, prompts, rebuilds, round_flow, runner, tools
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
from owlbear_delivery_next.processes import Termination
from owlbear_delivery_next.profile_record import Profile, ProfileEntry
from owlbear_delivery_next.round_records import FINAL, Completion, RoundFinding, RoundLoop, RoundPolicy
from owlbear_delivery_next.session_result import Run
from owlbear_delivery_next.status import Activity
from owlbear_delivery_next.steps import retry, review
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
    """One build session of *task*: its base, its commit and the span Delivery recorded."""
    task.base, task.done = git(clone, "rev-parse", "HEAD"), True
    task.spans = [f"{task.base}..{commit(clone, name, text)}"]
    return task


def end(task: Task) -> str:
    return task.spans[-1].split("..")[1]


def asked(clone: Path) -> Change:
    """t1 and its repair t3 change x.txt, t2 changes y.txt; final repairs t4 (of t1) and t5 (of t2), then the question.

    The last round's open F3 names t2; the reviews of t1 and t2 both covered x.txt.
    """
    t1 = build(clone, Task(id="t1", title="one", scope=["x.txt"], checks=["check one"]), "x.txt", "1\n")
    t3 = build(clone, Task(id="t3", title="fix", origin="review", fixes="t1"), "x.txt", "1b\n")
    t2 = build(clone, Task(id="t2", title="two", scope=["y.txt"], checks=["check two"]), "y.txt", "2\n")
    t4 = build(clone, Task(id="t4", title="fix final", origin="review", fixes=FINAL), "x.txt", "1c\n")
    t5 = build(clone, Task(id="t5", title="fix final", origin="review", fixes=FINAL), "y.txt", "2b\n")
    findings = [
        RoundFinding(id="F1", text="x.txt:1: p - fix: f", raised=1, tasks=["t1"], state="fixed", repair="t4"),
        RoundFinding(id="F2", text="y.txt:1: p - fix: f", raised=1, tasks=["t2"], state="fixed", repair="t5"),
        RoundFinding(id="F3", text="y.txt:2: p - fix: f", raised=1, tasks=["t2"]),
    ]
    head = git(clone, "rev-parse", "HEAD")
    lp = RoundLoop(subject=FINAL, policy=RoundPolicy(max_rounds=1), round=1, found=8, last=True, findings=findings)
    lp.completion, lp.head = Completion(head=head), end(t3)
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


def rebuild(store: Store, clone: Path, *tasks: str, **fields) -> Change:
    """The owner's Rebuild of *tasks*, bound to the attempt and head the page showed."""
    shown = {"tasks": list(tasks), "attempt": 1, "head": git(clone, "rev-parse", "HEAD")} | fields
    return answered(store, "rebuild", **shown)


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
    for wrong in (
        {"tasks": []},
        {"tasks": ["t1", "t9"]},
        {"tasks": ["t1"], "attempt": 2},
        {"tasks": ["t1"], "head": ""},
    ):
        assert rebuild(store, clone, **wrong).loops[FINAL].rebuild == []  # the fold checks the whole selection too
    assert loop.open_question(store.read("c1")) is not None
    assert answered(store, "accept", tasks=["t1"]).outcome.exit == Exit.ASK  # tasks belong to Rebuild only
    assert post("/api/next/changes/c1/answers", json=sent | {"tasks": ["t2", "t1"]}).status_code == 200
    c, _ = store.fold(Lock("c1"), "c1", NOW)  # the host's own item, as a runner folds it
    assert (c.loops[FINAL].rebuild, at(c)) == (["t1", "t2"], (K.REVIEW, None, round_flow.RETRY))


def test_a_rebuild_undoes_the_ticked_tasks_own_work_and_builds_them_again(tmp_path, clone, monkeypatch):
    store = Store(tmp_path / "store")
    store.write(Lock("c1"), asked(clone))
    archived = git(clone, "rev-parse", "HEAD")
    rebuild(store, clone, "t1")
    monkeypatch.setattr(runner, "_kept", lambda *_a: pytest.fail("the undo starts no session"))
    c = step(store, clone)
    assert git(clone, "rev-parse", retry.archive("c1", FINAL, 1, archived)) == archived
    assert git(clone, "rev-parse", "HEAD^") == archived  # one forward commit on the same branch
    assert (not (clone / "x.txt").exists(), (clone / "y.txt").read_text()) == (True, "2b\n")  # t1, t3, t4 undone
    t1, t2, t3, t4, t5 = c.plan.tasks
    assert [(t.done, t.base, t.spans) for t in (t1, t3, t4)] == [(False, None, [])] + [(True, None, [])] * 2
    assert (end(t2), end(t5)) == (git(clone, "rev-parse", "HEAD~3"), archived)  # kept work keeps its spans
    assert t1.checks == ["check one", "check two"]  # the last rebuilt task runs every other plan task's checks
    assert t1.scope == ["x.txt"]  # its planned scope stays
    lp = c.loops[FINAL]
    assert (lp.ended, lp.rebuild, lp.completion, lp.undo, c.consent) == ("retried", [], None, "", None)
    assert (c.loops["t1"].attempt, c.loops["t1"].since, [h.ended for h in c.loops["t1"].history]) == (2, 5, ["retried"])
    assert at(c) == (K.BUILD, "t1", None)


def test_a_promoted_undo_is_never_repeated_even_after_new_commits(clone):
    c = asked(clone)
    lp = c.loops[FINAL]
    lp.rebuild, start = ["t1"], git(clone, "rev-parse", "HEAD")
    undo, _ = rebuilds.undoing(c, lp)
    assert retry._taken(clone, c, lp, undo, start) == ""  # noqa: SLF001
    owner = commit(clone, "x.txt", "restored by the owner\n")  # before the record was written
    assert retry._landed(clone, start, retry.REBUILD.format(tasks="t1", attempt=1)) is True  # noqa: SLF001
    assert retry._taken(clone, c, lp, undo, start) == ""  # noqa: SLF001 - the restart finds the undo
    assert (git(clone, "rev-parse", "HEAD"), (clone / "x.txt").read_text()) == (owner, "restored by the owner\n")
    assert retry._cleaned(clone, c, lp, owner) == ""  # noqa: SLF001
    after = commit(clone, "n.txt", "new\n")
    assert retry._cleaned(clone, c, lp, owner) == ""  # noqa: SLF001
    assert (git(clone, "rev-parse", "HEAD"), (clone / "n.txt").exists()) == (after, True)


def test_an_undo_whose_branch_moved_before_it_landed_stops(clone):
    c = asked(clone)
    lp = c.loops[FINAL]
    lp.rebuild, start = ["t1"], git(clone, "rev-parse", "HEAD")
    moved = commit(clone, "m.txt", "moved\n")
    undo, _ = rebuilds.undoing(c, lp)
    assert retry._taken(clone, c, lp, undo, start) == "the branch moved since the undo started, without it"  # noqa: SLF001
    assert git(clone, "rev-parse", "HEAD") == moved


def test_commits_made_between_a_tasks_build_sessions_are_not_its_own(clone):
    base = git(clone, "rev-parse", "HEAD")
    first = commit(clone, "x.txt", "1\n")
    owner = commit(clone, "o.txt", "the owner's fix while the build was paused\n")
    integration = Task(id="t6", title="merge", origin="integration", done=True, base=owner)
    integration.spans = [f"{owner}..{commit(clone, 't.txt', 'target\n')}"]
    resumed = git(clone, "rev-parse", "HEAD")
    t1 = Task(
        id="t1",
        title="one",
        done=True,
        base=base,
        spans=[f"{base}..{first}", f"{resumed}..{commit(clone, 'x.txt', '1d\n')}"],
    )
    c = Change(slug="c1", brief=Brief(version=1), plan=Plan(tasks=[t1, integration]))
    lp = RoundLoop(subject=FINAL, policy=RoundPolicy(), rebuild=["t1"])
    undo, why = rebuilds.undoing(c, lp)
    assert ([t.id for t in undo], why) == (["t1"], "")
    t1.spans[-1] = f"{resumed}.."  # a session whose end was never recorded
    assert retry._commits(clone, [t1], git(clone, "rev-parse", "HEAD"))[1] == "the commits of task t1 are not recorded"  # noqa: SLF001
    t1.spans[-1] = f"{resumed}..{git(clone, 'rev-parse', 'HEAD')}"
    assert retry._taken(clone, c, lp, undo, git(clone, "rev-parse", "HEAD")) == ""  # noqa: SLF001
    assert not (clone / "x.txt").exists()
    assert ((clone / "o.txt").exists(), (clone / "t.txt").read_text()) == (True, "target\n")


def test_a_final_repair_of_rebuilt_and_kept_work_stops_the_undo_with_a_question(tmp_path, clone):
    c = asked(clone)
    c.loops[FINAL].findings[1].tasks = ["t1", "t2"]  # t5 fixed a finding of both
    store = Store(tmp_path / "store")
    store.write(Lock("c1"), c)
    head = git(clone, "rev-parse", "HEAD")
    rebuild(store, clone, "t1")
    c = step(store, clone)
    q = loop.open_question(c)
    assert "final repair t5 fixed findings of both rebuilt and kept work" in q.text
    assert ([o.id for o in q.options], q.cause) == (["another", "pause"], f"{round_flow.PREFIX}{FINAL} t5")
    assert (git(clone, "rev-parse", "HEAD"), git(clone, "for-each-ref", "refs/heads/owlbear/archive")) == (head, "")
    c = answered(store, "another")
    assert (c.loops[FINAL].extra, c.loops[FINAL].rebuild, at(c)) == (1, [], (K.REVIEW, None, "final"))


def test_a_repair_of_an_earlier_plan_never_counts_for_the_current_one():
    t1 = Task(id="t1", title="one", base="a" * 40, spans=[f"{'a' * 40}..{'b' * 40}"])
    t3 = Task(
        id="t3", title="fix final", origin="review", fixes=FINAL, base="b" * 40, spans=[f"{'b' * 40}..{'c' * 40}"]
    )
    c = Change(slug="c1", brief=Brief(version=1), plan=Plan(tasks=[t1, t3]))
    mine = RoundFinding(id="F1", text="x", raised=1, tasks=["t1"], state="fixed", repair="t3")
    theirs = RoundFinding(id="F1", text="x", raised=1, tasks=["t2"], state="fixed", repair="t3")  # the old t2's t3
    old = RoundLoop(subject=FINAL, policy=RoundPolicy(), ended="replanned", findings=[theirs])
    lp = RoundLoop(subject=FINAL, policy=RoundPolicy(), rebuild=["t1"], findings=[mine], history=[old])
    assert [t.id for t in rebuilds.undoing(c, lp)[0]] == ["t1", "t3"]


def test_a_task_whose_commits_are_not_recorded_is_not_undone():
    c = Change(slug="c1", brief=Brief(version=1), plan=Plan(tasks=[Task(id="t1", title="one", base="a" * 40)]))
    lp = RoundLoop(subject=FINAL, policy=RoundPolicy(), rebuild=["t1"])
    assert rebuilds.undoing(c, lp) == ([], "the commits of task t1 are not recorded")


def test_a_final_repair_that_also_fixed_a_finding_of_no_task_is_kept_work():
    t1 = Task(id="t1", title="one", base="a" * 40, spans=[f"{'a' * 40}..{'b' * 40}"])
    t2 = Task(
        id="t2", title="fix final", origin="review", fixes=FINAL, base="b" * 40, spans=[f"{'b' * 40}..{'c' * 40}"]
    )
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
        [(FINAL, "replanned"), ("t1", "clean")],
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


def test_a_kept_check_runs_from_each_package_of_its_task():
    entries = {f"check:{p}": ProfileEntry(state="known", value="npm test") for p in ("packages/a", "packages/b", ".")}
    profile = Profile(entries=entries | {"check:packages/c": ProfileEntry(state="known", value="uv run pytest")})
    t1 = Task(id="t1", title="one", scope=["packages/a/x.ts"], checks=["npm test"])
    t2 = Task(id="t2", title="two", scope=["packages/b/y.ts", "packages/c"], checks=["npm test", "uv run pytest"])
    t3 = Task(id="t3", title="three", scope=["docs/z.md"], checks=["make docs"])
    c = Change(slug="c1", brief=Brief(version=1), plan=Plan(tasks=[t1, t2, t3]))
    lp = RoundLoop(subject=FINAL, policy=RoundPolicy(), rebuild=["t1"])
    rebuilds.rotated(c, lp, [], profile)
    assert t1.checks == [
        "cd packages/a && npm test",  # its own too: a report from another package never stands in for it
        "cd packages/b && npm test",
        "cd packages/c && uv run pytest",
        "make docs",
    ]
    assert t1.scope == ["packages/a/x.ts"]
    root = Profile(entries=entries)  # npm test also runs at the repository root
    a = Task(id="t1", title="one", scope=["src/a.ts"], checks=["npm test"])
    twice = Change(slug="c1", brief=Brief(version=1), plan=Plan(tasks=[a, Task(**t2.model_dump())]))
    for _ in range(2):  # a second retry places the checks as the first did
        rebuilds.rotated(twice, RoundLoop(subject=FINAL, policy=RoundPolicy(), rebuild=["t1"]), [], root)
        assert a.checks == ["npm test", "cd packages/b && npm test", "uv run pytest"]
    ran = tools.BuildResult(
        summary="b", changed_paths=[], checks=[{"command": "cd packages/b && npm test", "exit_code": 0}]
    )
    tree = tools.Worktree(head="b", base="a")
    missing = [e for e in tools.check_build(ran, tree, ["npm test", "cd packages/b && npm test"]) if "missing" in e]
    assert missing == [
        'checks: "npm test" missing - run it on your commit and report it, e.g. {"command": "npm test", "exit_code": 0}'
    ]
    t4 = Task(id="t4", title="four", scope=["my app/q.ts"], checks=["npm test"])
    spaced = Profile(entries={"check:my app": ProfileEntry(state="known", value="npm test")})
    assert rebuilds._placed(spaced, [t4]) == ["cd 'my app' && npm test"]  # noqa: SLF001
    t5 = Task(id="t5", title="five", scope=["packages/ab/z.ts"], checks=["npm test"])
    assert rebuilds._placed(profile, [t5]) == ["npm test"]  # noqa: SLF001 - packages/a holds nothing of packages/ab
    both = ["cd packages/b && npm test", "cd packages/b && npm test:unit"]
    ran = tools.BuildResult(summary="b", changed_paths=[], checks=[{"command": k, "exit_code": 0} for k in both])
    assert [e for e in tools.check_build(ran, tree, both) if "missing" in e] == []


def test_each_build_session_records_its_own_span(tmp_path, clone):
    task = Task(id="t1", title="one")
    c = Change(slug="c1", brief=Brief(version=1), plan=Plan(tasks=[task]), step=Step(kind=K.BUILD, task="t1"))
    settings, base = Store(tmp_path / "s").settings(), git(clone, "rev-parse", "HEAD")
    review.started(c, task, clone, settings)
    built = commit(clone, "x.txt", "1\n")
    run = Run("s1", "result", None, head=built, termination=Termination(confirmed=True))
    review.recorded(c, task, run, clone, loop.StepResult(exit=Exit.RETRY, cause="x"))  # a failed session's own
    owner = commit(clone, "o.txt", "the owner's\n")
    review.started(c, task, clone, settings)
    crashed = commit(clone, "x.txt", "2\n")  # its session ends without a record: its end stays unknown
    review.started(c, task, clone, settings)
    asked = commit(clone, "x.txt", "3\n")
    review.recorded(
        c,
        task,
        Run("s2", "ask", None, termination=Termination(confirmed=True)),
        clone,
        loop.StepResult(exit=Exit.RETRY, cause="x"),
    )
    assert (task.base, task.spans) == (base, [f"{base}..{built}", f"{owner}..", f"{crashed}..{asked}"])
    assert retry._commits(clone, [task], asked)[1] == "the commits of task t1 are not recorded"  # noqa: SLF001
    lp = RoundLoop(subject=FINAL, policy=RoundPolicy(), rebuild=["t1"])
    assert rebuilds.undoing(c, lp) == ([], "the commits of task t1 are not recorded")
    review.started(c, task, clone, settings)
    store = Store(tmp_path / "store")
    store.write(Lock("c1"), c)
    held.keep(store, Lock("c1"), c, run, asked)  # a session whose usage stayed unread ends at its held head
    assert store.read("c1").plan.tasks[0].spans[-1] == f"{asked}..{asked}"
