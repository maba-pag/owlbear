"""A worker's proposed wording for a generated criterion (TD-179): validated, recorded, challenged, not applied."""

import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

from owlbear_delivery_next import amendments, loop, runner, sdk_adapter, tools
from owlbear_delivery_next.models import Brief, Change, Criterion, Exit, Names, Plan, Step, StepKind, Task
from owlbear_delivery_next.permissions import Policy
from owlbear_delivery_next.processes import Termination
from owlbear_delivery_next.results import ACCEPTED, Gate
from owlbear_delivery_next.session_result import Run
from owlbear_delivery_next.steps import amend
from owlbear_delivery_next.store import Lock, Store

NOW = datetime(2026, 10, 16, 3, tzinfo=UTC)
K = StepKind
DONE = Termination(confirmed=True)


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
    return work


def change() -> Change:
    criteria = [Criterion(id="AC-1", text="greet() trims the name"), Criterion(id="AC-2", text="Says Hallo", version=2)]
    brief = Brief(version=3, approved_version=3, challenged=3, criteria=criteria, specified=["AC-2"])
    plan = Plan(tasks=[Task(id="t1", title="one", scope=["a.txt"])])
    names = Names(branch="owlbear/c1", target="main")
    return Change(slug="c1", brief=brief, plan=plan, names=names, step=Step(kind=K.BUILD, task="t1"))


def premise(*amended: tuple[str, str], stage: str = "brief") -> dict:
    items = [{"criterion": k, "text": t, "why": "tabs are not names"} for k, t in amended]
    return {"stage": stage, "reason": "AC-1 is over-specific", "evidence": ["a.txt:1"], "amendment": items}


def test_amendable_criteria_are_generated_ones_while_the_limit_lasts():
    c = change()
    assert amendments.amendable(c) == ("AC-1",)  # AC-2 is the owner's own
    c.amendments = [amendments.Amendment(id=f"A{i}", at=NOW, step="build", session="s", base=3, items=[])
                    for i in range(amendments.LIMIT)]  # fmt: skip
    assert amendments.amendable(c) == ()


@pytest.mark.parametrize(
    ("args", "error"),
    [
        (premise(("AC-1", "greet() trims spaces")), None),
        (premise(("AC-1", "x"), stage="plan"), "amendment: only with stage brief"),
        (premise(("AC-2", "Says Hello")), "amendment: AC-2 cannot be proposed"),
        (premise(("AC-1", "x"), ("AC-1", "y")), "amendment: AC-1 listed twice"),
    ],
)
def test_a_premise_may_propose_wording_only_for_generated_criteria(tmp_path, args, error):
    cfg = sdk_adapter.Session(
        K.BUILD, tmp_path, "s1", "m", resume=False, policy=Policy(tmp_path), observe=lambda: None, checks=(),
        amendable=("AC-1",),
    )  # fmt: skip
    text, ok = Gate(cfg, Run("s1"), lambda **_e: None, lambda: None).call(tools.PREMISE, args)
    assert (ok, text) == (True, ACCEPTED) if error is None else (not ok and error in text)


def proposing(store: Store, clone: Path, monkeypatch, args: dict) -> list:
    async def build(cfg):
        payload, _ = tools.parse(tools.WrongPremise, args)
        return Run(cfg.session_id, "premise", payload, head=git(clone, "rev-parse", "HEAD"), termination=DONE)

    judged = []

    def review_run(_store, _lock, _change, source, made, label, *, submit):
        judged.append((label, submit, made(source).message))
        verdict = tools.VisualReviewResult(
            verdict="fix", findings=[{"place": "AC-1", "problem": "tabs could now pass", "fix": "keep trimming tabs"}]
        )
        return loop.StepResult(exit=Exit.RETRY), Run("c1-amend", "result", verdict, termination=DONE)

    monkeypatch.setattr(runner.sdk_adapter, "run", build)
    monkeypatch.setattr(amend.sessions, "review_run", review_run)
    c = store.read("c1")
    runner._step(store, Lock("c1"), c, c.step, clone)  # noqa: SLF001
    return judged


def test_a_proposal_is_recorded_exactly_and_challenged_while_the_premise_keeps_its_route(tmp_path, clone, monkeypatch):
    store = Store(tmp_path / "store")
    store.write(Lock("c1"), change())
    judged = proposing(store, clone, monkeypatch, premise(("AC-1", "greet() trims spaces, not tabs")))
    c = store.read("c1")
    (a,) = c.amendments
    assert (a.base, a.step, a.reason, a.evidence) == (3, "build", "AC-1 is over-specific", ["a.txt:1"])
    assert [(i.criterion, i.version, i.old, i.new) for i in a.items] == [
        ("AC-1", 1, "greet() trims the name", "greet() trims spaces, not tabs")
    ]
    assert (a.verdict, a.judged, a.challenger) == ("weaker", "AC-1: tabs could now pass", "c1-amend")
    label, submit, message = judged[0]
    assert (label, submit) == (amendments.LABEL, amendments.SUBMIT)
    assert "approved: greet() trims the name" in message
    assert "proposed: greet() trims spaces, not tabs" in message
    assert (c.step.kind, c.outcome.exit) == (K.PLAN, Exit.BACK)  # the builder's premise goes back to planning as before
    assert ([k.text for k in c.brief.criteria], c.brief.version) == (["greet() trims the name", "Says Hallo"], 3)


def test_a_premise_without_amendment_starts_no_challenge(tmp_path, clone, monkeypatch):
    store = Store(tmp_path / "store")
    store.write(Lock("c1"), change())
    args = premise()
    del args["amendment"]
    assert proposing(store, clone, monkeypatch, args) == []
    assert store.read("c1").amendments == []


def test_a_lost_challenge_leaves_the_exact_candidate_unjudged(tmp_path):
    store = Store(tmp_path / "store")
    c = change()
    store.write(Lock("c1"), c)
    payload, _ = tools.parse(tools.WrongPremise, premise(("AC-1", "trims spaces"), ("AC-2", "Says Hello")))

    def lost(*_a, **_kw):
        raise TimeoutError  # the challenger session never returned

    run = Run("c1-build", "premise", payload, termination=DONE)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(amend.sessions, "review_run", lost)
        with pytest.raises(TimeoutError):
            amend.challenge(store, Lock("c1"), c, tmp_path, run)
    (a,) = store.read("c1").amendments
    assert ([i.criterion for i in a.items], a.verdict) == (["AC-1"], "")  # the owner's AC-2 is never a candidate
