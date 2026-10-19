"""TD-208, TD-210, TD-330: a task's challenge loop from its first review to its end, the owner's question, a retry."""

import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

from owlbear_delivery_next.change_contracts import tools
from owlbear_delivery_next.change_contracts.inbox import AnswerItem
from owlbear_delivery_next.change_contracts.models import (
    Answer,
    Brief,
    Change,
    Exit,
    Names,
    Plan,
    Question,
    Step,
    StepKind,
    Task,
)
from owlbear_delivery_next.change_contracts.round_records import RECHECK, RoundLoop, RoundPolicy
from owlbear_delivery_next.change_flow import budgets, disputes, loop, round_flow
from owlbear_delivery_next.commands import runner
from owlbear_delivery_next.local_system.processes import Termination
from owlbear_delivery_next.runtimes import step_input
from owlbear_delivery_next.runtimes.session_result import Run
from owlbear_delivery_next.state_store.store import Lock, Store
from owlbear_delivery_next.workflow_steps import retry, review

NOW = datetime(2026, 10, 17, 3, tzinfo=UTC)
DONE = Termination(confirmed=True)
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


def stored(tmp_path: Path, *loops: RoundLoop) -> Store:
    tasks = [Task(id="t1", title="one", scope=["a.txt"]), Task(id="t2", title="two", scope=["a.txt"])]
    c = Change(
        slug="c1",
        brief=Brief(version=1),
        plan=Plan(tasks=tasks),
        names=Names(branch="owlbear/c1", target="main"),
        step=Step(kind=K.BUILD, task="t1"),
        loops={lp.subject: lp for lp in loops},
    )
    store = Store(tmp_path / "store")
    store.write(Lock("c1"), c)
    return store


def step(store: Store, clone: Path) -> Change:
    c = store.read("c1")
    runner._step(store, Lock("c1"), c, c.step, clone)  # noqa: SLF001
    return store.read("c1")


def built(store: Store, clone: Path, monkeypatch, write: str, *reject: str):
    """One build step: the builder commits *write* to a.txt and rejects *reject*; its session config."""
    seen = []

    def kept(_store, _lock, _change, path, config):
        seen.append(cfg := config(path))
        (clone / "a.txt").write_text(write)
        git(clone, "commit", "-qam", f"build {write.strip()}")
        rejected = [{"finding": k, "reason": f"{k} is wrong"} for k in reject]
        payload = tools.BuildResult(summary="Built.", changed_paths=["a.txt"], checks=[], rejected=rejected)
        return Run(cfg.session_id, "result", payload, head=git(clone, "rev-parse", "HEAD"), termination=DONE)

    monkeypatch.setattr(runner, "_kept", kept)
    step(store, clone)
    return seen[0]


def reviewed(store: Store, clone: Path, monkeypatch, found: range = range(0), **judged: bool):
    """One review step finding a.txt:<n> for each n in *found* and judging the rejections in *judged*."""
    seen = []

    def kept(_store, _lock, _change, path, config):
        seen.append(cfg := config(path))
        findings = [{"place": f"a.txt:{n}", "problem": f"problem {n}", "fix": f"fix {n}"} for n in found]
        rechecked = [{"finding": k, "upheld": u, "reason": f"{k} judged"} for k, u in judged.items()]
        payload = tools.ReviewResult(verdict="fix" if found else "pass", findings=findings, rechecked=rechecked)
        return Run(cfg.session_id, "result", payload, head=git(clone, "rev-parse", "HEAD"), termination=DONE)

    monkeypatch.setattr(runner, "_kept", kept)
    step(store, clone)
    return seen[0]


def answer(store: Store, option: str) -> Change:
    c = store.read("c1")
    q = loop.open_question(c)
    c, _ = loop.schedule(c, [AnswerItem(at=NOW, channel="status-view", question=q.id, option=option)], NOW)
    store.write(Lock("c1"), c)
    return c


def at(c: Change) -> tuple:
    return c.step.kind, c.step.task, c.step.mode


def test_a_task_loop_judges_rejections_counts_rounds_and_ends_early_with_a_rejections_only_check(
    tmp_path, clone, monkeypatch
):
    store = stored(tmp_path)
    built(store, clone, monkeypatch, "b\n")
    cfg = reviewed(store, clone, monkeypatch, range(1, 6))
    c = store.read("c1")
    lp = c.loops["t1"]
    assert (cfg.cap, lp.round, lp.found, lp.last, at(c)) == (10, 1, 5, False, (K.BUILD, "t3", None))
    assert c.plan.tasks[-1].detail.splitlines()[0] == "- F1: a.txt:1: problem 1 - fix: fix 1"
    assert [line.split(":")[0] for line in c.plan.tasks[-1].detail.splitlines()] == [f"- F{n}" for n in range(1, 6)]
    cfg = built(store, clone, monkeypatch, "c\n", "F2")
    assert cfg.rejectable == ("F1", "F2", "F3", "F4", "F5")
    c = store.read("c1")
    assert [f.state for f in c.loops["t1"].findings] == ["fixed", "rejected", "fixed", "fixed", "fixed"]
    c.budgets.rounds[budgets.round_key(c)] = budgets.ROUND_LIMIT  # the old round gate would ask now
    store.write(Lock("c1"), c)
    cfg = reviewed(store, clone, monkeypatch, range(6, 8), F2=False)
    assert ("## Rejections to judge" in cfg.message, "a.txt:2: problem 2" in cfg.message) == (True, True)
    assert "a.txt:1: problem 1" not in cfg.message  # an accepted finding never reaches the next round
    c = store.read("c1")
    lp = c.loops["t1"]
    assert (lp.round, lp.found, lp.last, c.outcome.question, at(c)) == (2, 2, True, None, (K.BUILD, "t4", None))
    assert lp.reviewed == ["t3"]  # the full round reviewed the repair that reported its fixes
    assert [(f.id, f.state) for f in lp.findings if f.raised == 2] == [("F6", "open"), ("F7", "open")]
    assert lp.findings[1].state == "standing"
    built(store, clone, monkeypatch, "d\n", "F7")
    assert at(store.read("c1")) == (K.REVIEW, "t4", RECHECK)
    cfg = reviewed(store, clone, monkeypatch, F7=False)
    assert (cfg.cap, disputes.ONLY in cfg.message, "settled not to fix" in cfg.message) == (0, True, False)
    assert "(rejection accepted by the reviewer)" in disputes.review_lines(store.read("c1"), None)[-1]  # outside
    c = store.read("c1")
    lp = c.loops["t1"]
    assert (lp.round, lp.ended, lp.unreviewed, at(c)) == (
        2,
        "count",
        ["t4"],
        (K.BUILD, "t2", None),
    )  # TD-330: uncounted
    assert lp.reviewed == ["t3"]  # a rejections-only check reviews no repair
    assert [t.done for t in c.plan.tasks] == [True, False, True, True]


def test_a_last_round_at_the_maximum_gets_its_rejections_judged_outside_the_count(tmp_path, clone, monkeypatch):
    """TD-330: not only a last round ended early by its count; the owner is not asked with fewer than 7 findings."""
    store = stored(tmp_path, RoundLoop(subject="t1", policy=RoundPolicy(max_rounds=1)))
    built(store, clone, monkeypatch, "b\n")
    reviewed(store, clone, monkeypatch, range(1, 6))
    built(store, clone, monkeypatch, "c\n", "F5")
    assert at(store.read("c1")) == (K.REVIEW, "t3", RECHECK)
    cfg = reviewed(store, clone, monkeypatch, F5=False)
    c = store.read("c1")
    lp = c.loops["t1"]
    assert (cfg.cap, lp.round, lp.found, lp.ended, lp.unreviewed) == (0, 1, 5, "max", ["t3"])
    assert (lp.findings[4].state, at(c)) == ("standing", (K.BUILD, "t2", None))


def test_an_early_last_round_without_rejections_leaves_its_repair_unreviewed(tmp_path, clone, monkeypatch):
    store = stored(tmp_path)
    built(store, clone, monkeypatch, "b\n")
    reviewed(store, clone, monkeypatch, range(1, 3))
    built(store, clone, monkeypatch, "c\n")
    c = store.read("c1")
    lp = c.loops["t1"]
    assert (lp.round, lp.ended, lp.unreviewed, at(c)) == (1, "count", ["t3"], (K.BUILD, "t2", None))
    assert [f.state for f in lp.findings] == ["fixed", "fixed"]


def test_the_owner_is_asked_only_after_the_last_allowed_round_with_many_findings(tmp_path, clone, monkeypatch):
    store = stored(tmp_path, RoundLoop(subject="t1", policy=RoundPolicy(max_rounds=1)))
    built(store, clone, monkeypatch, "b\n")
    reviewed(store, clone, monkeypatch, range(1, 9))
    built(store, clone, monkeypatch, "c\n", "F8")
    assert at(store.read("c1")) == (K.REVIEW, "t3", RECHECK)  # TD-330: its rejection is judged before the owner
    reviewed(store, clone, monkeypatch, F8=False)
    q = loop.open_question(store.read("c1"))
    assert [o.label for o in q.options] == ["Another round", "Reject the work and retry it"]
    assert "Review round 1 of task t1 found 8 new findings, and it was the last allowed round: " in q.text
    assert "F1 fixed, not re-reviewed: a.txt:1: problem 1 - fix: fix 1; F2 " in q.text
    assert "; F8 rejected; the reviewer accepted that (F8 is wrong): a.txt:8: problem 8 - fix: fix 8. Another" in q.text
    c = answer(store, "another")
    assert (c.loops["t1"].extra, at(c)) == (1, (K.REVIEW, "t3", None))
    reviewed(store, clone, monkeypatch, range(9, 17))
    built(store, clone, monkeypatch, "d\n")
    assert "Review round 2 of task t1" in loop.open_question(store.read("c1")).text
    assert at(answer(store, "retry")) == (K.BUILD, "t1", round_flow.RETRY)
    base, archived = git(clone, "rev-list", "--max-parents=0", "HEAD"), git(clone, "rev-parse", "HEAD")
    monkeypatch.setattr(runner, "_kept", lambda *_a: pytest.fail("the undo starts no session"))
    c = step(store, clone)
    assert (git(clone, "rev-parse", retry.archive("c1", "t1", 1, archived)), git(clone, "rev-parse", "HEAD^")) == (
        archived,
        archived,
    )
    assert ((clone / "a.txt").read_text(), git(clone, "diff", base, "HEAD")) == ("a\n", "")
    lp = c.loops["t1"]
    assert (lp.attempt, lp.round, lp.since, [(h.attempt, h.round, h.ended) for h in lp.history]) == (
        2,
        0,
        4,
        [(1, 2, "retried")],
    )
    assert ([t.done for t in c.plan.tasks], c.plan.tasks[0].base, at(c)) == (
        [False, False, True, True],
        None,
        (K.BUILD, "t1", None),
    )
    assert [(t.base, t.spans) for t in c.plan.tasks[2:]] == [(None, [])] * 2  # undone: no later undo takes them
    built(store, clone, monkeypatch, "e\n")
    assert store.read("c1").plan.tasks[0].base == git(clone, "rev-parse", "HEAD^")  # the fresh build's own base
    reviewed(store, clone, monkeypatch)
    c = store.read("c1")
    assert (c.loops["t1"].ended, c.loops["t1"].round, at(c)) == ("clean", 1, (K.BUILD, "t2", None))


def test_an_undo_that_conflicts_asks_the_owner_and_leaves_the_branch_as_it_was(tmp_path, clone):
    base = git(clone, "rev-parse", "HEAD")
    (clone / "a.txt").write_text("b\n")
    git(clone, "commit", "-qam", "build b")
    built = git(clone, "rev-parse", "HEAD")
    git(clone, "switch", "-qc", "side")
    (clone / "a.txt").write_text("c\n")
    git(clone, "commit", "-qam", "target change")
    git(clone, "switch", "-q", "owlbear/c1")
    git(clone, "merge", "-q", "--no-ff", "-m", "merge the target", "side")  # kept: the undo would have to revert it
    head = git(clone, "rev-parse", "HEAD")
    store = stored(tmp_path, RoundLoop(subject="t1", policy=RoundPolicy()))
    c = store.read("c1")
    c.plan.tasks[0].base, c.plan.tasks[0].spans = base, [f"{base}..{built}"]
    c.plan.tasks.append(Task(id="t3", title="fix", scope=["a.txt"], origin="review", fixes="t1", detail="- F1: x"))
    c.step = Step(kind=K.BUILD, task="t1", mode=round_flow.RETRY)
    store.write(Lock("c1"), c)
    c = step(store, clone)
    q = loop.open_question(c)
    assert ([o.label for o in q.options], q.cause) == (
        ["Another round on the kept work", "Pause this Change"],
        f"{round_flow.PREFIX}t1 t3",
    )
    assert (git(clone, "rev-parse", "HEAD"), (clone / "a.txt").read_text(), c.loops["t1"].attempt) == (head, "c\n", 1)
    assert c.loops["t1"].undo == ""  # a failed undo starts afresh next time
    assert git(clone, "worktree", "list").count("\n") == 0  # the scratch worktree is gone
    c = answer(store, "another")
    assert (c.loops["t1"].extra, at(c)) == (1, (K.REVIEW, "t3", None))


def undoing(clone: Path, *tasks: Task) -> tuple[Change, Task, RoundLoop]:
    """Task t1, built from the clone's base commit, and the loop of its first attempt."""
    task = Task(id="t1", title="one", base=git(clone, "rev-parse", "HEAD"))
    c = Change(slug="c1", brief=Brief(version=1), plan=Plan(tasks=[task, *tasks]))
    return c, task, RoundLoop(subject="t1", since=1, policy=RoundPolicy())


def head(clone: Path) -> str:
    return git(clone, "rev-parse", "HEAD")


def test_a_promoted_undo_is_found_again_and_each_retried_head_keeps_its_own_archive(clone):
    c, task, lp = undoing(clone)
    (clone / "a.txt").write_text("b\n")
    git(clone, "commit", "-qam", "build b")
    first = git(clone, "rev-parse", "HEAD")
    git(clone, "update-ref", retry.archive("c1", "t1", 1, first), first)  # an undo that failed after archiving
    (clone / "a.txt").write_text("c\n")
    git(clone, "commit", "-qam", "another round's repair")
    task.spans = [f"{task.base}..{head(clone)}"]
    (clone / "left.txt").write_text("an edit")
    assert retry._undo(clone, c, task, lp, head(clone)) == "the worktree has uncommitted edits"  # noqa: SLF001
    (clone / "left.txt").unlink()
    start = head(clone)
    assert retry._undo(clone, c, task, lp, start) == ""  # noqa: SLF001
    undone = git(clone, "rev-parse", "HEAD")
    assert git(clone, "rev-parse", retry.archive("c1", "t1", 1, git(clone, "rev-parse", "HEAD^"))) != first
    assert retry._undo(clone, c, task, lp, start) == ""  # noqa: SLF001 - a restart before the record was written
    assert (git(clone, "rev-parse", "HEAD"), (clone / "a.txt").read_text()) == (undone, "a\n")
    assert git(clone, "rev-parse", retry.archive("c1", "t1", 1, first)) == first  # never deleted
    assert len(git(clone, "for-each-ref", "refs/heads/owlbear/archive").splitlines()) == 2  # none of the undo


def test_an_undo_keeps_the_target_merges_in_its_range(clone):
    c, task, lp = undoing(clone)
    (clone / "a.txt").write_text("b\n")
    git(clone, "commit", "-qam", "build b")
    task.spans = [f"{task.base}..{head(clone)}"]
    git(clone, "switch", "-qc", "side", "main")
    (clone / "t.txt").write_text("target\n")
    git(clone, "add", "t.txt")
    git(clone, "commit", "-qm", "target change")
    git(clone, "switch", "-q", "owlbear/c1")
    git(clone, "merge", "-q", "--no-ff", "-m", "merge the target", "side")
    assert retry._undo(clone, c, task, lp, head(clone)) == ""  # noqa: SLF001
    assert ((clone / "a.txt").read_text(), (clone / "t.txt").read_text()) == ("a\n", "target\n")


def test_an_attempt_with_another_tasks_build_inside_it_is_not_undone(clone):
    integration = Task(id="t2", title="merge", origin="integration", base=git(clone, "rev-parse", "HEAD"))
    c, task, lp = undoing(clone, integration)
    git(clone, "switch", "-q", "main")
    (clone / "t.txt").write_text("target\n")
    git(clone, "add", "t.txt")
    git(clone, "commit", "-qm", "target change")
    git(clone, "switch", "-q", "owlbear/c1")
    git(clone, "merge", "-q", "--ff-only", "main")  # the integration's fast-forward: no merge commit marks it
    assert retry._undo(clone, c, task, lp, head(clone)).startswith("task t2 was built during this attempt")  # noqa: SLF001
    assert ((clone / "t.txt").read_text(), git(clone, "for-each-ref", "refs/heads/owlbear/archive")) == ("target\n", "")


def test_a_looped_review_batch_is_one_repair():
    c = Change(slug="c1", brief=Brief(version=1), plan=Plan(tasks=[Task(id="t1", title="one", scope=["a.txt"])]))
    c.step = Step(kind=K.REVIEW, task="t1")
    lp = c.loops["t1"] = RoundLoop(subject="t1", policy=RoundPolicy())
    long = [f.line for f in lp.raise_findings([f"a.txt:{i}: {'x' * 1500} - fix: y" for i in range(4)])]
    assert [len(t.detail.splitlines()) for t in review.repair(c, c.plan.tasks[0], long)] == [4]


def test_a_challenged_review_leaves_out_the_owners_answers_on_findings():
    c = Change(slug="c1", brief=Brief(version=1))
    said = Answer(option="fix", text="use Hallo", at=NOW)
    c.questions = [
        Question(step=K.REVIEW, text="finding F1", cause=f"{disputes.PREFIX}t3 F1", answer=said),
        Question(step=K.BUILD, text="which port", answer=Answer(text="8080", at=NOW)),
    ]
    assert sum("use Hallo" in line for line in step_input._brief(c)) == 1  # noqa: SLF001
    assert [line for line in step_input._brief(c, challenged=True) if "use Hallo" in line or "8080" in line] == [  # noqa: SLF001
        "- which port: 8080"
    ]


def test_a_task_built_before_its_loop_existed_keeps_the_earlier_rules(tmp_path, clone, monkeypatch):
    store = stored(tmp_path)
    c = store.read("c1")
    c.plan.tasks[0].base = git(clone, "rev-parse", "HEAD")
    store.write(Lock("c1"), c)
    built(store, clone, monkeypatch, "b\n")
    cfg = reviewed(store, clone, monkeypatch, range(1, 3))
    c = store.read("c1")
    assert (cfg.cap, c.loops, c.outcome.exit, c.plan.tasks[-1].detail.startswith("- a.txt:1:")) == (
        20,
        {},
        Exit.RETRY,
        True,
    )


@pytest.mark.parametrize("origin", ["ci", "pr-feedback", "integration", "person-check", "review"])
def test_work_added_to_reviewed_work_gets_no_review_of_its_own(tmp_path, clone, monkeypatch, origin):
    store = stored(tmp_path)
    c = store.read("c1")
    c.plan.tasks[0].done = True
    c.plan.tasks[1].done = True
    c.plan.tasks.append(Task(id="t3", title="fix", scope=["a.txt"], origin=origin))  # a visual repair, if "review"
    c.step = Step(kind=K.BUILD, task="t3")
    store.write(Lock("c1"), c)
    built(store, clone, monkeypatch, "b\n")
    c = store.read("c1")
    assert (c.plan.tasks[-1].done, c.loops, at(c)) == (True, {}, (K.REVIEW, None, "final"))  # the final round


@pytest.mark.parametrize("upheld", [False, True])
def test_a_repair_of_no_task_whose_builder_rejects_a_finding_gets_only_that_judged(
    tmp_path, clone, monkeypatch, upheld
):
    store = stored(tmp_path)
    c = store.read("c1")
    c.plan.tasks[0].done = c.plan.tasks[1].done = True
    c.plan.tasks.append(Task(id="t3", title="fix", scope=["a.txt"], origin="review", detail="- a.txt:1: p - fix: f"))
    c.step = Step(kind=K.BUILD, task="t3")  # a visual check's repair, or a final review's from before TD-208
    store.write(Lock("c1"), c)
    built(store, clone, monkeypatch, "b\n", "F1")
    assert at(store.read("c1")) == (K.REVIEW, "t3", RECHECK)
    cfg = reviewed(store, clone, monkeypatch, F1=upheld)
    assert (cfg.cap, disputes.ONLY in cfg.message) == (0, True)
    if upheld:  # you decide it; the repair you asked for goes to the final round, unreviewed on its own (TD-235)
        answer(store, "fix")
        monkeypatch.setattr(runner, "_kept", lambda *_a: pytest.fail("a decided dispute starts no session"))
        step(store, clone)
        built(store, clone, monkeypatch, "c\n")
    c = store.read("c1")
    assert ([t.done for t in c.plan.tasks[2:]], at(c)) == ([True] * (2 if upheld else 1), (K.REVIEW, None, "final"))
