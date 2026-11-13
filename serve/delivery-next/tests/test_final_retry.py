"""TD-210, TD-214, TD-217: the final review's retry: the owner's task list, the undo of the ticked tasks, a new plan."""

import json
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from owlbear_delivery_next.change_contracts import check_hint, tools
from owlbear_delivery_next.change_contracts.inbox import AnswerItem
from owlbear_delivery_next.change_contracts.models import (
    Brief,
    Change,
    Criterion,
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
from owlbear_delivery_next.change_contracts.profile_record import Profile, ProfileEntry
from owlbear_delivery_next.change_contracts.round_records import FINAL, Completion, RoundFinding, RoundLoop, RoundPolicy
from owlbear_delivery_next.change_flow import loop, rebuilds, round_flow, stuck
from owlbear_delivery_next.change_flow.moves import ask
from owlbear_delivery_next.change_flow.status import Activity
from owlbear_delivery_next.commands import cli, runner
from owlbear_delivery_next.local_system.processes import Termination
from owlbear_delivery_next.project_host import api
from owlbear_delivery_next.runtimes import step_input
from owlbear_delivery_next.runtimes.session_result import Run
from owlbear_delivery_next.settings.profile import confirm
from owlbear_delivery_next.state_store.store import Lock, Store
from owlbear_delivery_next.workflow_steps import held, publish, retry, review, step_repair

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


def asked(tasks: list[Task] | None = None) -> Change:
    """The same final question for model rules and real recorded builds."""
    if tasks is None:
        tasks = [
            Task(id="t1", title="one", scope=["x.txt"], checks=["cd . && check one"]),
            Task(id="t2", title="two", scope=["y.txt"], checks=["cd . && check two"]),
            Task(id="t3", title="fix", origin="review", fixes="t1"),
            Task(id="t4", title="fix final", origin="review", fixes=FINAL),
            Task(id="t5", title="fix final", origin="review", fixes=FINAL),
        ]
        for n, task in enumerate((tasks[0], tasks[2], tasks[1], tasks[3], tasks[4])):
            task.base, task.done, task.spans = str(n) * 40, True, [f"{str(n) * 40}..{str(n + 1) * 40}"]
    t1, t2, t3, t4, t5 = tasks
    findings = [
        RoundFinding(id="F1", text="x.txt:1: p - fix: f", raised=1, tasks=["t1"], state="fixed", repair="t4"),
        RoundFinding(id="F2", text="y.txt:1: p - fix: f", raised=1, tasks=["t2"], state="fixed", repair="t5"),
        RoundFinding(id="F3", text="y.txt:2: p - fix: f", raised=1, tasks=["t2"]),
    ]
    head = end(t5)
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
    ask(c, round_flow.question(c, lp, t5), NOW)
    return c


def built_change(clone: Path) -> Change:
    c = asked()
    tasks = {t.id: t for t in c.plan.tasks}
    for task, name, text in (
        ("t1", "x.txt", "1\n"),
        ("t3", "x.txt", "1b\n"),
        ("t2", "y.txt", "2\n"),
        ("t4", "x.txt", "1c\n"),
        ("t5", "y.txt", "2b\n"),
    ):
        build(clone, tasks[task], name, text)
    return asked(c.plan.tasks)


@dataclass
class Host:
    maintenance = None
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


def rebuild(store: Store, *tasks: str, **fields) -> Change:
    """The owner's Rebuild of *tasks*, bound to the attempt and head the page showed."""
    c = store.read("c1")
    shown = {"tasks": list(tasks), "attempt": 1, "head": rebuilds.head(c.loops[FINAL])} | fields
    return answered(store, "rebuild", **shown)


def step(store: Store, clone: Path) -> Change:
    c = store.read("c1")
    runner._step(store, Lock("c1"), c, c.step, clone)  # noqa: SLF001
    return store.read("c1")


def at(c: Change) -> tuple:
    return c.step.kind, c.step.task, c.step.mode


def test_retry_answers_reject_invalid_or_stale_bindings(tmp_path):
    store = Store(tmp_path / "store")
    c = asked()
    store.write(Lock("c1"), c)
    q, head = loop.open_question(c), rebuilds.head(c.loops[FINAL])
    post = client(store).post
    sent = {"question": q.id, "option": "rebuild", "attempt": 1, "head": head}
    assert post("/api/next/changes/c1/answers", json=sent | {"tasks": []}).status_code == 422
    assert post("/api/next/changes/c1/answers", json=sent | {"tasks": ["t3"]}).status_code == 422  # a repair
    assert post("/api/next/changes/c1/answers", json=sent | {"tasks": ["t1"], "head": "b" * 40}).status_code == 409
    assert post("/api/next/changes/c1/answers", json=sent | {"tasks": ["t1"], "attempt": 2}).status_code == 409
    accept = {"question": q.id, "option": "accept", "tasks": ["t1"]}
    assert post("/api/next/changes/c1/answers", json=accept).status_code == 422  # only Rebuild names tasks
    with store.db.read() as db:
        assert db.execute("SELECT count(*) FROM inbox").fetchone()[0] == 0
    for wrong in (
        {"tasks": []},
        {"tasks": ["t1", "t9"]},
        {"tasks": ["t1"], "attempt": 2},
        {"tasks": ["t1"], "head": ""},
    ):
        assert rebuild(store, **wrong).loops[FINAL].rebuild == []  # the fold checks the whole selection too
    assert loop.open_question(store.read("c1")) is not None
    assert answered(store, "accept", tasks=["t1"]).outcome.exit == Exit.ASK  # tasks belong to Rebuild only
    assert post("/api/next/changes/c1/answers", json=sent | {"tasks": ["t2", "t1"]}).status_code == 200
    c, _ = store.fold(Lock("c1"), "c1", NOW)  # the host's own item, as a runner folds it
    assert (c.loops[FINAL].rebuild, at(c)) == (["t1", "t2"], (K.REVIEW, None, round_flow.RETRY))


def test_console_retry_show_and_answer_share_page_authority(tmp_path, monkeypatch, capsys):
    """#676: the console's Rebuild is checked and bound as the page's is, after showing what the page shows."""
    store = Store(tmp_path / "store")
    c = asked()
    c.brief = Brief(version=1, criteria=[Criterion(id="AC-1", text="rule AC-1")])
    c.loops[FINAL].findings[2].text = "y.txt:2: AC-1 not met - fix: f"  # the open F3 names it
    store.write(Lock("c1"), c)
    q, head = loop.open_question(c), rebuilds.head(c.loops[FINAL])
    assert rebuilds.shown(c, q)["unmet"] == ["AC-1: rule AC-1"]
    monkeypatch.setattr(cli.Store, "open", lambda *_a, **_k: store)

    def said(*args: str) -> int:
        return cli.main(["--repo", str(tmp_path), *args])

    def inbox() -> int:
        with store.db.read() as db:
            return db.execute("SELECT count(*) FROM inbox").fetchone()[0]

    assert said("show", "c1") == 0
    shown = capsys.readouterr().out
    for line in (
        f"final retry attempt 1 at {head}",
        "[ ] t1 one (shares files with t2)",
        "[x] t2 two (shares files with t1)",
        "unmet: AC-1: rule AC-1",
        f"answer with --attempt 1 --head {head}; a Rebuild adds --task ID for each task",
    ):
        assert line in shown
    rebuilding = ["answer", "c1", "--question", q.id, "--option", "rebuild", "--attempt", "1"]
    assert (said(*rebuilding, "--task", "t1", "--head", "b" * 40), inbox()) == (1, 0)
    assert "moved on since the page was shown" in capsys.readouterr().err
    assert said(*rebuilding, "--task", "t2", "--task", "t1", "--head", head) == 0
    c, _ = store.fold(Lock("c1"), "c1", NOW)
    assert (c.loops[FINAL].rebuild, at(c)) == (["t1", "t2"], (K.REVIEW, None, round_flow.RETRY))


def test_accept_unmet_criteria_is_wording_bound_and_published(tmp_path):
    """TD-341: later reviews and the pull request see them accepted, until the criterion's text changes."""
    store = Store(tmp_path / "store")
    c = asked()
    c.brief = Brief(
        version=1,
        criteria=[
            Criterion(id="AC-1", text="greets"),
            Criterion(id="AC-2", text="waves"),
            Criterion(id="AC-10", text="ten"),
        ],
    )
    found = c.loops[FINAL].findings
    found[0].text, found[2].text = "x.txt:1: AC-2 broken - fix: f", "y.txt:2: AC-1 not met - fix: f"
    assert rebuilds.shown(c, loop.open_question(c))["unmet"] == ["AC-1: greets"]
    found[2].text = "y.txt:2: no criterion - fix: f"
    assert rebuilds.shown(c, loop.open_question(c))["unmet"] == []
    found[2].text = "y.txt:2: AC-1 not met - fix: f"
    store.write(Lock("c1"), c)
    done = answered(store, "accept")
    assert done.waived == {"AC-1": "greets"}
    note = " (the owner accepted it unmet as his decision)"
    said = step_input.brief(done)
    assert (f"- AC-1: greets{note}" in said, "- AC-2: waves" in said) == (True, True)
    assert f"- AC-1: greets{note}\n- AC-2: waves" in publish._body(done, marker=False)  # noqa: SLF001
    done.brief.criteria[0].text = "greets twice"  # amended, or removed and added again in other words
    assert "- AC-1: greets twice" in step_input.brief(done)


def test_page_rebuild_preserves_kept_work_and_restarts_selected_tasks(tmp_path, clone, monkeypatch):
    store = Store(tmp_path / "store")
    store.write(Lock("c1"), built_change(clone))
    archived = git(clone, "rev-parse", "HEAD")
    page = client(store)
    shown = page.get("/api/next/changes/c1").json()
    retry_list, q = shown["retry"], shown["question"]
    assert [o["label"] for o in q["options"]] == [
        "Rebuild the ticked tasks",
        "Accept as done",
        "Another round",
        "Plan again from the brief on the existing code",
        "Plan again from the brief from a clean state",
    ]
    assert (retry_list["attempt"], retry_list["head"]) == (1, archived)
    assert retry_list["tasks"] == [
        {"id": "t1", "title": "one", "ticked": False, "shares": ["t2"]},
        {"id": "t2", "title": "two", "ticked": True, "shares": ["t1"]},
    ]
    sent = {"question": q["id"], "option": "rebuild", "tasks": ["t1"], "attempt": 1, "head": archived}
    assert page.post("/api/next/changes/c1/answers", json=sent).status_code == 200
    c, _ = store.fold(Lock("c1"), "c1", NOW)
    assert (c.loops[FINAL].rebuild, at(c)) == (["t1"], (K.REVIEW, None, round_flow.RETRY))
    monkeypatch.setattr(runner, "_kept", lambda *_a: pytest.fail("the undo starts no session"))
    c = step(store, clone)
    assert git(clone, "rev-parse", retry.archive("c1", FINAL, 1, archived)) == archived
    assert git(clone, "rev-parse", "HEAD^") == archived  # one forward commit on the same branch
    assert (not (clone / "x.txt").exists(), (clone / "y.txt").read_text()) == (True, "2b\n")  # t1, t3, t4 undone
    t1, t2, t3, t4, t5 = c.plan.tasks
    assert [(t.done, t.base, t.spans) for t in (t1, t3, t4)] == [(False, None, [])] + [(True, None, [])] * 2
    assert (end(t2), end(t5)) == (git(clone, "rev-parse", "HEAD~3"), archived)  # kept work keeps its spans
    assert t1.checks == ["cd . && check one", "cd . && check two"]  # the last rebuilt task runs all kept checks
    assert t1.scope == ["x.txt"]  # its planned scope stays
    lp = c.loops[FINAL]
    assert (lp.ended, lp.rebuild, lp.completion, lp.undo, c.consent) == ("retried", ["t1"], None, "", None)
    assert (c.loops["t1"].attempt, c.loops["t1"].since, [h.ended for h in c.loops["t1"].history]) == (2, 5, ["retried"])
    assert at(c) == (K.BUILD, "t1", None)


def test_rebuild_checks_bind_new_spans_in_build_and_repair_witnesses(tmp_path, clone):
    profile = confirm(Profile(), "check:.", "uv run test --changed", NOW)
    command = "cd . && uv run test --changed"
    t1 = build(clone, Task(id="t1", title="one", scope=["."], checks=[command]), "old_module.py", "v = 1\n")
    t2 = build(clone, Task(id="t2", title="two", scope=["."], checks=[command]), "second.py", "v = 2\n")
    old = t1.spans[0]
    lp = RoundLoop(subject=FINAL, policy=RoundPolicy(), rebuild=["t1", "t2"])
    c = Change(
        slug="c1",
        brief=Brief(version=1),
        plan=Plan(tasks=[t1, t2]),
        names=Names(branch="owlbear/c1", target="main"),
        loops={FINAL: lp, "t2": RoundLoop(subject="t2", policy=RoundPolicy())},
    )
    undone, why = rebuilds.undoing(c, lp)
    assert why == ""
    required = rebuilds.checks(c, lp, profile, undone)
    root = check_hint.changed_runner(required[0])
    assert root is not None
    assert root[1] == []
    assert retry._taken(clone, c, lp, undone, git(clone, "rev-parse", "HEAD")) == ""  # noqa: SLF001
    rebuilds.rotated(c, lp, undone, required)
    build(clone, t1, "replacement.py", "v = 3\n")
    c.step = Step(kind=K.BUILD, task="t2")
    settings = Store(tmp_path / "settings").settings()
    review.started(c, t2, clone, settings)
    parts = step_input.session(c, profile, clone, {})
    root = check_hint.changed_runner(parts.checks[0])
    assert root is not None
    assert root[1] == t1.spans
    assert old not in parts.checks[0]
    t2.checks = list(required)
    stuck.start(c, "project-env:build:check-pytest", "check needs repair", NOW)
    repair = c.repairs.current
    assert repair is not None
    repair.base = t2.base
    witness = step_repair._witness(c, profile, clone)  # noqa: SLF001
    root = check_hint.changed_runner(witness[0])
    assert root is not None
    assert root[1] == t1.spans
    (clone / "serve/tools").mkdir(parents=True)
    (clone / "serve/tools/pyproject.toml").write_text("[project\n")
    git(clone, "add", "serve/tools/pyproject.toml")
    git(clone, "commit", "-qm", "malformed original runner manifest")
    t2.checks = list(required)
    witness = step_repair._witness(c, profile, clone)  # noqa: SLF001
    assert f"--keep-span {t1.spans[0]}" in witness[0]
    assert witness[0].count("--keep-span") == len(t1.spans)
    assert "TOMLDecodeError" in repair.evidence
    c.step = Step(kind=K.REVIEW, mode="final")
    review.started(c, None, clone, settings)
    assert lp.rebuild == []


def test_undo_restart_preserves_later_commits_and_refuses_unrelated_movement(clone):
    task = build(clone, Task(id="t1", title="one"), "x.txt", "1\n")
    lp = RoundLoop(subject=FINAL, policy=RoundPolicy(), rebuild=["t1"])
    c = Change(
        slug="c1",
        brief=Brief(version=1),
        plan=Plan(tasks=[task]),
        names=Names(branch="owlbear/c1", target="main"),
        loops={FINAL: lp},
    )
    start = git(clone, "rev-parse", "HEAD")
    moved = commit(clone, "m.txt", "moved\n")
    undo, _ = rebuilds.undoing(c, lp)
    assert retry._taken(clone, c, lp, undo, start) == "the branch moved since the undo started, without it"  # noqa: SLF001
    assert git(clone, "rev-parse", "HEAD") == moved
    start = moved
    assert retry._taken(clone, c, lp, undo, start) == ""  # noqa: SLF001
    owner = commit(clone, "x.txt", "restored by the owner\n")  # before the record was written
    assert retry._taken(clone, c, lp, undo, start) == ""  # noqa: SLF001 - the restart finds the undo
    assert (git(clone, "rev-parse", "HEAD"), (clone / "x.txt").read_text()) == (owner, "restored by the owner\n")
    assert retry._cleaned(clone, c, lp, owner) == ""  # noqa: SLF001
    after = commit(clone, "n.txt", "new\n")
    assert retry._cleaned(clone, c, lp, owner) == ""  # noqa: SLF001
    assert (git(clone, "rev-parse", "HEAD"), (clone / "n.txt").exists()) == (after, True)


def test_recorded_session_spans_exclude_owner_and_integration_work(tmp_path, clone):
    t1 = Task(id="t1", title="one", done=True)
    c = Change(slug="c1", brief=Brief(version=1), plan=Plan(tasks=[t1]), step=Step(kind=K.BUILD, task="t1"))
    settings, base = Store(tmp_path / "s").settings(), git(clone, "rev-parse", "HEAD")
    review.started(c, t1, clone, settings)
    first = commit(clone, "x.txt", "1\n")
    review.recorded(c, t1, Run("s1", "result", None, head=first), clone, loop.StepResult(exit=Exit.RETRY, cause="x"))
    owner = commit(clone, "o.txt", "the owner's fix while the build was paused\n")
    integration = Task(id="t6", title="merge", origin="integration", done=True, base=owner)
    integration.spans = [f"{owner}..{commit(clone, 't.txt', 'target\n')}"]
    resumed = git(clone, "rev-parse", "HEAD")
    c.plan.tasks.append(integration)
    review.started(c, t1, clone, settings)
    last = commit(clone, "x.txt", "1d\n")
    review.recorded(c, t1, Run("s2", "result", None, head=last), clone, loop.StepResult(exit=Exit.RETRY, cause="x"))
    assert (t1.base, t1.spans) == (base, [f"{base}..{first}", f"{resumed}..{last}"])
    lp = RoundLoop(subject=FINAL, policy=RoundPolicy(), rebuild=["t1"])
    undo, why = rebuilds.undoing(c, lp)
    assert ([t.id for t in undo], why) == (["t1"], "")
    t1.spans[-1] = f"{resumed}.."  # a session whose end was never recorded
    assert retry._commits(clone, [t1], git(clone, "rev-parse", "HEAD"))[1] == "the commits of task t1 are not recorded"  # noqa: SLF001
    t1.spans[-1] = f"{resumed}..{git(clone, 'rev-parse', 'HEAD')}"
    assert retry._taken(clone, c, lp, undo, git(clone, "rev-parse", "HEAD")) == ""  # noqa: SLF001
    assert not (clone / "x.txt").exists()
    assert ((clone / "o.txt").exists(), (clone / "t.txt").read_text()) == (True, "target\n")


def test_unsplittable_final_repair_asks_before_any_git_mutation(tmp_path, clone):
    c = asked()
    c.loops[FINAL].findings[1].tasks = ["t1", "t2"]  # t5 fixed a finding of both
    store = Store(tmp_path / "store")
    store.write(Lock("c1"), c)
    head = git(clone, "rev-parse", "HEAD")
    rebuild(store, "t1")
    c = step(store, clone)
    q = loop.open_question(c)
    assert "final repair t5 fixed findings of both rebuilt and kept work" in q.text
    assert ([o.id for o in q.options], q.cause) == (["another", "pause"], f"{round_flow.PREFIX}{FINAL} t5")
    assert (git(clone, "rev-parse", "HEAD"), git(clone, "for-each-ref", "refs/heads/owlbear/archive")) == (head, "")
    c = answered(store, "another")
    assert (c.loops[FINAL].extra, c.loops[FINAL].rebuild, at(c)) == (1, [], (K.REVIEW, None, "final"))


def test_rebuild_lineage_and_kept_check_spans_follow_the_current_plan():
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
    t2 = Task(id="t2", title="kept", base="b" * 40, spans=[f"{'b' * 40}..{'d' * 40}"])
    t4 = Task(
        id="t4",
        title="kept task repair",
        origin="review",
        fixes="t2",
        base="d" * 40,
        spans=[f"{'d' * 40}..{'e' * 40}"],
    )
    t5 = Task(
        id="t5",
        title="kept final repair",
        origin="review",
        fixes=FINAL,
        base="e" * 40,
        spans=[f"{'e' * 40}..{'f' * 40}"],
    )
    t6 = Task(
        id="t6",
        title="earlier plan repair",
        origin="review",
        fixes=FINAL,
        base="f" * 40,
        spans=[f"{'f' * 40}..{'a' * 40}"],
    )
    lp.findings.append(RoundFinding(id="F2", text="kept", raised=1, tasks=["t2"], state="fixed", repair="t5"))
    old.findings.append(RoundFinding(id="F3", text="old", raised=1, tasks=["t2"], state="fixed", repair="t6"))
    c.plan.tasks = [t1, t2, t3, t4, t5, t6]
    for task in c.plan.tasks:
        task.done = True
    t1.checks = t2.checks = ["cd . && uv run test --changed"]
    profile = Profile(entries={"check:.": ProfileEntry(state="known", value="uv run test --changed")})
    undone, why = rebuilds.undoing(c, lp)
    assert why == ""
    expected = check_hint.freeze(t1.checks[0], [*t2.spans, *t4.spans, *t5.spans])
    required = rebuilds.checks(c, lp, profile, undone)
    assert required == [expected]
    rebuilds.rotated(c, lp, undone, required)
    assert t1.checks == [expected]
    assert t3.spans == []
    t1.base, t1.spans, t1.done = "a" * 40, [f"{'a' * 40}..{'c' * 40}"], True
    t7 = Task(
        id="t7",
        title="repair inheriting frozen checks",
        origin="review",
        fixes="t1",
        base="c" * 40,
        spans=[f"{'c' * 40}..{'e' * 40}"],
        checks=list(t1.checks),
        done=True,
    )
    c.plan.tasks.append(t7)
    again = lp.model_copy(update={"rebuild": ["t2"]})
    undone, why = rebuilds.undoing(c, again)
    assert why == ""
    expected = check_hint.freeze(t2.checks[0], [*t1.spans, *t7.spans])
    required = rebuilds.checks(c, again, profile, undone)
    assert required == [expected]
    rebuilds.rotated(c, again, undone, required)
    assert all((root := check_hint.changed_runner(task.checks[0])) is not None and root[1] == [] for task in (t1, t7))


def test_unknown_ownership_and_taskless_repairs_cannot_be_undone():
    t1 = Task(id="t1", title="one", base="a" * 40)
    c = Change(slug="c1", brief=Brief(version=1), plan=Plan(tasks=[t1]))
    lp = RoundLoop(subject=FINAL, policy=RoundPolicy(), rebuild=["t1"])
    assert rebuilds.undoing(c, lp) == ([], "the commits of task t1 are not recorded")
    t1.spans = [f"{'a' * 40}..{'b' * 40}"]
    t2 = Task(
        id="t2", title="fix final", origin="review", fixes=FINAL, base="b" * 40, spans=[f"{'b' * 40}..{'c' * 40}"]
    )
    c.plan.tasks.append(t2)
    found = [RoundFinding(id=f"F{n}", text="x", raised=1, tasks=k, state="fixed", repair="t2") for n, k in (
        (1, ["t1"]), (2, []))]  # fmt: skip
    lp = RoundLoop(subject=FINAL, policy=RoundPolicy(), rebuild=["t1"], findings=found[:1])
    assert [t.id for t in rebuilds.undoing(c, lp)[0]] == ["t1", "t2"]
    lp.history = [RoundLoop(subject=FINAL, policy=RoundPolicy(), findings=found[1:])]  # an earlier attempt's
    assert rebuilds.undoing(c, lp)[1].startswith("final repair t2 fixed findings of both rebuilt and kept work")


STATES = [("open", True), ("escalated", True), ("owner-fix", True), ("fixed", False), ("rejected", False),
    ("standing", False), ("owner-drop", False), ("withdrawn", False)]  # fmt: skip


@pytest.mark.parametrize(("state", "ticked"), STATES)
def test_unresolved_findings_select_plan_tasks(state, ticked):
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
    ask(c, round_flow.question(c, c.loops[FINAL], c.plan.tasks[0]), NOW)
    listed = rebuilds.shown(c, c.questions[0])["tasks"]
    assert [(t["ticked"], t["shares"]) for t in listed] == [(ticked, []), (ticked, [])]  # no shared files known


@pytest.mark.parametrize("mode", ["clean", "replan"])
def test_replan_preserves_the_selected_starting_state(tmp_path, clone, mode):
    if mode == "clean":
        git(clone, "switch", "-qc", "side", "main")
        commit(clone, "t.txt", "target\n")
        git(clone, "switch", "-q", "owlbear/c1")
    c = built_change(clone)
    if mode == "clean":
        git(clone, "merge", "-q", "--no-ff", "-m", "merge the target", "side")
        git(clone, "branch", "-qf", "main", "side")
    store = Store(tmp_path / "store")
    store.write(Lock("c1"), c)
    archived = git(clone, "rev-parse", "HEAD")
    c = answered(store, mode)
    if mode == "clean":
        c = step(store, clone)
        assert git(clone, "rev-parse", retry.archive("c1", FINAL, 1, archived)) == archived
        assert (git(clone, "diff", "main", "HEAD"), git(clone, "rev-parse", "HEAD^")) == ("", archived)
    else:
        assert git(clone, "rev-parse", "HEAD") == archived
    lp = c.loops[FINAL]
    assert (list(c.loops), lp.attempt, lp.round, [(h.subject, h.ended) for h in lp.history]) == (
        [FINAL],
        2,
        0,
        [(FINAL, "replanned"), ("t1", "clean")],
    )
    assert (at(c), c.outcome.exit, c.consent) == ((K.PLAN, None, None), Exit.BACK, None)
    assert c.outcome.reason.startswith("The owner rejected the work after final review round 1 and asked for a new ")
    how = "from a clean state" if mode == "clean" else "on the existing code"
    assert how in c.outcome.reason
    assert "F3: y.txt:2: p - fix: f" in c.outcome.reason
    message = step_input.plan(c, Profile(), clone, {})
    assert "## Why the Change is planned again" in message
    assert how in message


def test_rebuilt_checks_keep_package_identity():
    entries = {f"check:{p}": ProfileEntry(state="known", value="npm test") for p in ("packages/a", "packages/b", ".")}
    profile = Profile(
        entries=entries
        | {
            "check:packages/c": ProfileEntry(state="known", value="uv run pytest"),
            "check:docs": ProfileEntry(state="known", value="make docs"),
        }
    )
    for key, value in profile.entries.items():
        profile = confirm(profile, key, value.value, NOW)
    t1 = Task(id="t1", title="one", scope=["packages/a/x.ts"], checks=["cd packages/a && npm test"])
    t2 = Task(
        id="t2",
        title="two",
        scope=["packages/b/y.ts", "packages/c"],
        checks=["cd packages/b && npm test", "cd packages/c && uv run pytest"],
    )
    t3 = Task(id="t3", title="three", scope=["docs/z.md"], checks=["cd docs && make docs"])
    c = Change(slug="c1", brief=Brief(version=1), plan=Plan(tasks=[t1, t2, t3]))
    lp = RoundLoop(subject=FINAL, policy=RoundPolicy(), rebuild=["t1"])
    rebuilds.rotated(c, lp, [], rebuilds.checks(c, lp, profile, []))
    assert t1.checks == [
        "cd packages/a && npm test",  # its own too: a report from another package never stands in for it
        "cd packages/b && npm test",
        "cd packages/c && uv run pytest",
        "cd docs && make docs",
    ]
    assert t1.scope == ["packages/a/x.ts"]
    a = Task(id="t1", title="one", scope=["src/a.ts"], checks=["cd . && npm test"])
    twice = Change(slug="c1", brief=Brief(version=1), plan=Plan(tasks=[a, Task(**t2.model_dump())]))
    for _ in range(2):  # a second retry places the checks as the first did
        again = RoundLoop(subject=FINAL, policy=RoundPolicy(), rebuild=["t1"])
        rebuilds.rotated(
            twice,
            again,
            [],
            rebuilds.checks(twice, again, profile, []),
        )
        assert a.checks == ["cd . && npm test", "cd packages/b && npm test", "cd packages/c && uv run pytest"]
    ran = tools.BuildResult(summary="b", checks=[{"command": "cd packages/b && npm test", "exit_code": 0}])
    tree = tools.Worktree(head="b", base="a")
    missing = [
        e for e in tools.check_build(ran, tree, ["cd . && npm test", "cd packages/b && npm test"]) if "missing" in e
    ]
    assert missing == [
        (
            'checks: "cd . && npm test" missing - run it on your commit and report it, '
            'e.g. {"command": "cd . && npm test", "exit_code": 0}'
        )
    ]
    t4 = Task(id="t4", title="four", scope=["my app/q.ts"], checks=["cd 'my app' && npm test"])
    spaced = Profile(entries={"check:my app": ProfileEntry(state="known", value="npm test")})
    c.plan = Plan(tasks=[t4])
    lp.rebuild = ["t4"]
    assert rebuilds.checks(c, lp, spaced, []) == ["cd 'my app' && npm test"]
    t5 = Task(id="t5", title="five", scope=["packages/ab/z.ts"], checks=["cd . && npm test"])
    c.plan = Plan(tasks=[t5])
    lp.rebuild = ["t5"]
    assert rebuilds.checks(c, lp, profile, []) == ["cd . && npm test"]  # never relocate a selected check
    both = ["cd packages/b && npm test", "cd packages/b && npm test:unit"]
    ran = tools.BuildResult(summary="b", checks=[{"command": k, "exit_code": 0} for k in both])
    assert [e for e in tools.check_build(ran, tree, both) if "missing" in e] == []


def test_emitted_checks_run_in_confirmed_folders(change_repo, monkeypatch):
    package = change_repo / "packages/app"
    package.mkdir(parents=True)
    elsewhere = change_repo.parent / "elsewhere"
    other = elsewhere / "packages/app"
    other.mkdir(parents=True)
    for home in (change_repo, package):
        (home / "Makefile").write_text("check:\n\t@pwd\n")
    git(change_repo, "add", "Makefile", "packages/app")
    git(change_repo, "commit", "-qm", "root and package check targets")
    command = "make check & make check; wait # both in this package"
    profile = confirm(confirm(Profile(), "check:.", command, NOW), "check:packages/app", command, NOW)
    c = Change(slug="c1", brief=Brief(version=1), step=Step(kind=K.PLAN))
    choices = step_input.session(c, profile, change_repo, {})
    assert choices.checks == (f"cd . && {{\n{command}\n}}", f"cd ./packages/app && {{\n{command}\n}}")
    task = Task(id="t1", title="one", scope=["packages/app"], checks=list(choices.checks))
    c.plan, c.step = Plan(tasks=[task]), Step(kind=K.BUILD, task="t1")
    parts = step_input.session(c, profile, change_repo, {})
    assert parts.checks == choices.checks
    monkeypatch.setenv("CDPATH", str(elsewhere))
    reports = []
    for command, home in zip(parts.checks, (change_repo, package), strict=True):
        done = subprocess.run(  # noqa: S603 - emitted commands of the fixture's confirmed checks
            ["/bin/sh", "-c", command],
            cwd=change_repo,
            check=True,
            capture_output=True,
            text=True,
        )
        assert done.stdout.splitlines() == [str(home), str(home)]
        reports.append({"command": command, "exit_code": done.returncode})
    tree = runner.worktree.observe(change_repo, "main")
    assert tools.check_build(tools.BuildResult(summary="checked", checks=reports), tree, parts.checks) == []
    for omitted in reports:
        result = tools.BuildResult(summary="checked", checks=[r for r in reports if r is not omitted])
        errors = tools.check_build(result, tree, parts.checks)
        assert errors == [
            (
                f'checks: "{omitted["command"]}" missing - run it on your commit and report it, '
                f"e.g. {json.dumps(omitted)}"
            )
        ]


def test_unknown_session_spans_refuse_undo_and_held_span_closes(tmp_path, clone):
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
    # a session whose usage stayed unread ends at its held head
    pending = held.hold(store, Lock("c1"), c, run, asked, {})
    assert pending.change.plan.tasks[0].spans[-1] == f"{asked}..{asked}"
