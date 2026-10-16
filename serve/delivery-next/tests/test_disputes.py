"""A builder's rejection of review findings (TD-124, TD-176): rechecked by a fresh reviewer, then the owner decides."""

import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

from owlbear_delivery_next import disputes, loop, runner, sdk_adapter, tool_schema, tools
from owlbear_delivery_next.inbox import AnswerItem
from owlbear_delivery_next.models import Brief, Change, Exit, Names, Plan, Step, StepKind, Task
from owlbear_delivery_next.permissions import Policy
from owlbear_delivery_next.processes import Termination
from owlbear_delivery_next.results import ACCEPTED, Gate
from owlbear_delivery_next.session_result import Run
from owlbear_delivery_next.steps import review
from owlbear_delivery_next.store import Lock, Store

NOW = datetime(2026, 10, 16, 3, tzinfo=UTC)
DONE = Termination(confirmed=True)
K = StepKind
FOUND = "- a.txt:1: AC-1 greets in English - fix: use Hallo\n- a.txt:2: no test - fix: add one"


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
    git(work, "branch", "main")  # the target the review measures its diff against
    monkeypatch.setattr(runner.worktree, "ensure", lambda *_a: work)
    return work


def repair_change() -> Change:
    tasks = [
        Task(id="t1", title="one", scope=["a.txt"], built_by="s-build", done=True),
        Task(id="t2", title="fix", scope=["a.txt"], origin="review", fixes="t1", detail=FOUND, resume="s-build"),
    ]
    names = Names(branch="owlbear/c1", target="main")
    return Change(
        slug="c1", brief=Brief(version=1), plan=Plan(tasks=tasks), names=names, step=Step(kind=K.BUILD, task="t2")
    )


def gate(tmp_path: Path, kind: StepKind, tree: tools.Worktree, **bounds: tuple[str, ...]) -> Gate:
    cfg = sdk_adapter.Session(
        kind, tmp_path, "s1", "m", resume=False, policy=Policy(tmp_path), observe=lambda: tree, checks=("npm test",),
        submit=tools.REVIEW if kind == K.REVIEW else tools.SUBMIT, **bounds,
    )  # fmt: skip
    return Gate(cfg, Run("s1"), lambda **_e: None, lambda: None)


def rejecting(*keys: str) -> dict:
    rejected = [{"finding": k, "reason": "a.txt:1 already says Hallo"} for k in keys]
    return {"summary": "Rejected.", "changed_paths": [], "checks": [], "rejected": rejected}


def test_both_results_offer_their_dispute_fields_to_every_runtime():
    assert "rejected" in tool_schema.schema(tools.SUBMIT)["properties"]
    assert "rechecked" in tool_schema.schema(tools.REVIEW)["properties"]


def test_a_finding_is_known_by_its_place_and_problem_on_every_path():
    finding = tools.Finding(place="a.txt:1", problem="AC-1\n greets in English", fix="use Hallo")
    line = review.lines(tools.ReviewResult(verdict="fix", findings=[finding]))[0]
    assert line == "- a.txt:1: AC-1 greets in English - fix: use Hallo"  # one line, so a repair task can key it
    assert review.score([line], K.REVIEW) == review.score([line.replace("Hallo", "Servus")], K.REVIEW)


@pytest.mark.parametrize(
    ("offered", "keys", "error"),
    [
        (("F1", "F2"), ("F1", "F2"), None),  # every finding rejected: no commit, no checks
        (("F1", "F2"), ("F1",), "changes: no commit - fix and commit F2"),
        (("F1", "F2"), ("F3",), "rejected: F3 is no finding key"),
        (("F1", "F2"), ("F1", "F1", "F2"), "rejected: F1 listed twice"),
        ((), ("F1",), "rejected: this task offers no rejection"),
    ],
)
def test_a_rejection_only_result_needs_every_finding_rejected(tmp_path, offered, keys, error):
    g = gate(tmp_path, K.BUILD, tools.Worktree(head="a", base="a"), rejectable=offered)
    text, ok = g.call(tools.SUBMIT, rejecting(*keys))
    assert (ok, text) == (True, ACCEPTED) if error is None else (not ok and error in text)


@pytest.mark.parametrize(
    ("keys", "error"),
    [(("F1", "F2"), None), (("F1",), "rechecked: missing F2"), (("F1", "F2", "F3"), "F3 is not listed")],
)
def test_a_review_answers_each_listed_recheck_once(tmp_path, keys, error):
    g = gate(tmp_path, K.REVIEW, tools.Worktree(head="b", base="a"), rechecks=("F1", "F2"))
    rechecked = [{"finding": k, "upheld": False, "reason": "it trims"} for k in keys]
    text, ok = g.call(tools.REVIEW, {"verdict": "pass", "rechecked": rechecked})
    assert ok if error is None else (not ok and error in text)


def build_run(cfg, head: str, payload: tools.BuildResult) -> Run:
    return Run(cfg.session_id, "result", payload, head=head, termination=DONE)


def run_build(store: Store, c: Change, clone: Path, monkeypatch, *keys: str) -> Change:
    seen = []

    async def build(cfg):
        seen.append(cfg)
        return build_run(cfg, git(clone, "rev-parse", "HEAD"), tools.BuildResult(**rejecting(*keys)))

    monkeypatch.setattr(runner.sdk_adapter, "run", build)
    runner._step(store, Lock("c1"), c, c.step, clone)  # noqa: SLF001
    assert seen[0].rejectable == ("F1", "F2")
    assert "> F1. a.txt:1: AC-1 greets in English - fix: use Hallo" in seen[0].message
    return store.read("c1")


def run_review(store: Store, c: Change, clone: Path, monkeypatch, upheld: dict[str, bool]) -> Change:
    seen = []

    def kept(_store, _lock, _change, path, config):
        seen.append(cfg := config(path))
        rechecked = [{"finding": k, "upheld": u, "reason": f"{k} judged"} for k, u in upheld.items()]
        review = tools.ReviewResult(verdict="pass", rechecked=rechecked)
        return Run(cfg.session_id, "result", review, head=git(clone, "rev-parse", "HEAD"), termination=DONE)

    monkeypatch.setattr(runner, "_kept", kept)
    runner._step(store, Lock("c1"), c, c.step, clone)  # noqa: SLF001
    assert seen[0].rechecks == tuple(upheld)
    assert "## Rechecks" in seen[0].message
    return store.read("c1")


def answer(store: Store, c: Change, option: str) -> Change:
    q = loop.open_question(c)
    c, _ = loop.schedule(c, [AnswerItem(at=NOW, channel="status-view", question=q.id, option=option)], NOW)
    store.write(Lock("c1"), c)
    return c


def unrun(store: Store, c: Change, clone: Path, monkeypatch) -> Change:
    monkeypatch.setattr(runner, "_kept", lambda *_a: pytest.fail("a decided dispute starts no session"))
    runner._step(store, Lock("c1"), c, c.step, clone)  # noqa: SLF001
    return store.read("c1")


@pytest.mark.parametrize("owner", ["drop", "fix"])
def test_an_upheld_rejection_goes_to_the_owner_before_any_repair_round(tmp_path, clone, monkeypatch, owner):
    store = Store(tmp_path / "store")
    store.write(Lock("c1"), repair_change())
    c = run_build(store, store.read("c1"), clone, monkeypatch, "F1", "F2")
    assert (c.step.kind, c.step.task, [d.key for d in c.plan.tasks[1].disputes]) == (K.REVIEW, "t2", ["F1", "F2"])
    c = run_review(store, c, clone, monkeypatch, {"F1": True, "F2": False})
    q = loop.open_question(c)
    assert (c.outcome.exit, [o.label for o in q.options]) == (Exit.ASK, ["Fix it", "Drop it"])
    assert q.cause.startswith(disputes.PREFIX)
    assert "F1" in q.text
    assert "F1 judged" in q.text
    assert (len(c.plan.tasks), c.budgets.rounds, len(c.reviews)) == (2, {}, 1)  # held: no repair, no round yet
    c = unrun(store, answer(store, c, owner), clone, monkeypatch)
    if owner == "drop":
        assert ([t.done for t in c.plan.tasks], c.step.kind, c.step.mode) == ([True, True], K.REVIEW, "final")
    else:
        fix = c.plan.tasks[-1]
        assert (c.step.kind, c.step.task, fix.fixes, fix.detail) == (
            K.BUILD,
            fix.id,
            "t2",
            f"- {FOUND.splitlines()[0][2:]}",
        )
        assert sum(c.budgets.rounds.values()) == 1
        assert disputes.rejectable(c, fix) == ()  # the subject had its one recheck


def test_each_upheld_finding_is_decided_on_its_own(tmp_path, clone, monkeypatch):
    store = Store(tmp_path / "store")
    store.write(Lock("c1"), repair_change())
    c = run_build(store, store.read("c1"), clone, monkeypatch, "F1", "F2")
    c = run_review(store, c, clone, monkeypatch, {"F1": True, "F2": True})
    assert "F1" in loop.open_question(c).text
    c = answer(store, c, "drop")
    assert "F2" in loop.open_question(c).text
    c = unrun(store, answer(store, c, "fix"), clone, monkeypatch)
    assert c.plan.tasks[-1].detail == f"- {FOUND.splitlines()[1][2:]}"
    assert [(d.key, d.owner) for d in c.plan.tasks[1].disputes] == [("F1", "drop"), ("F2", "fix")]


def test_a_review_whose_session_stops_consumes_no_recheck(tmp_path, clone, monkeypatch):
    store = Store(tmp_path / "store")
    store.write(Lock("c1"), repair_change())
    c = run_build(store, store.read("c1"), clone, monkeypatch, "F1", "F2")
    upheld = [{"finding": k, "upheld": True, "reason": "holds"} for k in ("F1", "F2")]
    review = tools.ReviewResult(verdict="pass", rechecked=upheld)
    head = git(clone, "rev-parse", "HEAD")
    unconfirmed = Termination(confirmed=False)  # its processes are not observed gone: the step stops, nothing counts
    monkeypatch.setattr(
        runner, "_kept", lambda _s, _l, _c, path, config: Run(config(path).session_id, "result", review, head=head,
                                                              termination=unconfirmed)
    )  # fmt: skip
    runner._step(store, Lock("c1"), c, c.step, clone)  # noqa: SLF001
    c = store.read("c1")
    assert c.outcome.exit == Exit.STOP
    assert [d.upheld for d in c.plan.tasks[1].disputes] == [None, None]
    assert not c.reviews
