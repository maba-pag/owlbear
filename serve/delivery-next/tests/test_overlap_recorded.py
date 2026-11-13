"""Paths a kept plan shares with other open Changes are recorded, whether its challenge passed or sent it back."""

import pytest

from owlbear_delivery_next.change_contracts import tools
from owlbear_delivery_next.change_contracts.models import (
    Brief,
    Change,
    Exit,
    Names,
    Overlap,
    Plan,
    Step,
    StepKind,
    Task,
)
from owlbear_delivery_next.commands import runner
from owlbear_delivery_next.local_system.processes import Termination
from owlbear_delivery_next.runtimes.session_result import Run
from owlbear_delivery_next.state_store.store import Lock, Store

SHARED = [Overlap(other="c2", paths=["src/app.ts"])]


@pytest.fixture
def store(tmp_path, change_repo, monkeypatch, checks_settled) -> Store:
    """Change c1 about to plan ``src/app.ts``, which the open Change c2 plans too."""
    store = Store(tmp_path / "store")
    checks_settled(store)
    names = Names(branch="owlbear/c1", target="main", worktree=str(change_repo))
    brief = Brief(version=1, approved_version=1, challenged=1)
    store.write(Lock("c1"), Change(slug="c1", brief=brief, step=Step(kind=StepKind.PLAN), names=names))
    other = Plan(tasks=[Task(id="t1", title="other", scope=["src/app.ts"])])
    store.write(Lock("c2"), Change(slug="c2", brief=Brief(version=1), plan=other, step=Step(kind=StepKind.BUILD)))
    monkeypatch.setattr(runner.worktree, "ensure", lambda *_a: change_repo)
    return store


@pytest.mark.parametrize(
    ("verdict", "expected"),
    [("pass", (Exit.DONE, StepKind.BUILD, SHARED)), ("fix", (Exit.RETRY, StepKind.PLAN, SHARED))],
)
def test_a_kept_plan_records_overlaps_after_its_challenge(store, change_repo, monkeypatch, verdict, expected):
    async def fake(cfg):
        if cfg.submit is tools.PLAN:
            payload = tools.PlanResult(
                tasks=[{"title": "one", "goal": "AC-1", "scope": ["src/app.ts"], "checks": ["true"]}]
            )
        else:
            findings = (
                [{"place": "src/app.ts", "problem": "AC-1 unclear", "fix": "say more"}] if verdict == "fix" else []
            )
            payload = tools.ReviewResult(verdict=verdict, findings=findings, covered_paths=["src/app.ts"])
        return Run(cfg.session_id, "result", payload, termination=Termination(confirmed=True))

    monkeypatch.setattr(runner.sdk_adapter, "run", fake)
    c = store.read("c1")
    runner._step(store, Lock("c1"), c, c.step, change_repo)  # noqa: SLF001
    c = store.read("c1")
    assert (c.outcome.exit, c.step.kind, c.overlaps) == expected
    if verdict == "fix":
        assert [f.id for f in c.loops["plan"].findings] == ["F1"]  # the planner answers it by its ID (TD-190)
