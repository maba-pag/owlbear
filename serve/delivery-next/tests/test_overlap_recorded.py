"""Paths a kept plan shares with other open Changes are recorded, whether its challenge passed or the owner chose it."""

from datetime import UTC, datetime

import pytest

from owlbear_delivery_next import runner, tools
from owlbear_delivery_next.budgets import ROUND_LIMIT
from owlbear_delivery_next.inbox import AnswerItem
from owlbear_delivery_next.models import Brief, Change, Exit, Names, Overlap, Plan, Step, StepKind, Task
from owlbear_delivery_next.processes import Termination
from owlbear_delivery_next.session_result import Run
from owlbear_delivery_next.store import Lock, Store

SHARED = [Overlap(other="c2", paths=["src/app.ts"])]


@pytest.fixture
def store(tmp_path, change_repo, monkeypatch) -> Store:
    """Change c1 about to plan ``src/app.ts``, which the open Change c2 plans too."""
    store = Store(tmp_path / "store")
    names = Names(branch="owlbear/c1", target="main", worktree=str(change_repo))
    brief = Brief(version=1, approved_version=1, challenged=1)
    store.write(Lock("c1"), Change(slug="c1", brief=brief, step=Step(kind=StepKind.PLAN), names=names))
    other = Plan(tasks=[Task(id="t1", title="other", scope=["src/app.ts"])])
    store.write(Lock("c2"), Change(slug="c2", brief=Brief(version=1), plan=other, step=Step(kind=StepKind.BUILD)))
    monkeypatch.setattr(runner.worktree, "ensure", lambda *_a: change_repo)
    return store


def planned(store: Store, repo, monkeypatch, verdict: str) -> Change:
    """Run c1's plan step with a challenge that gives *verdict*."""

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
    change = store.read("c1")
    runner._step(store, Lock("c1"), change, change.step, repo)  # noqa: SLF001
    return store.read("c1")


def test_a_plan_whose_challenge_passes_records_its_overlaps(store, change_repo, monkeypatch):
    c = planned(store, change_repo, monkeypatch, "pass")
    assert (c.outcome.exit, c.step.kind, c.overlaps) == (Exit.DONE, StepKind.BUILD, SHARED)


def test_a_plan_the_owner_accepts_after_its_challenge_asked_records_its_overlaps(store, change_repo, monkeypatch):
    c = store.read("c1")
    c.budgets.rounds[str(StepKind.PLAN)] = ROUND_LIMIT  # the challenge's next findings ask the owner
    store.write(Lock("c1"), c)
    c = planned(store, change_repo, monkeypatch, "fix")
    question = next(q for q in c.questions if q.answer is None)
    assert [o.id for o in question.options] == ["fix", "accept"]
    now = datetime.now(UTC)
    store.put_inbox("c1", AnswerItem(at=now, question=question.id, option="accept"))
    c, _ = store.fold(Lock("c1"), "c1", now)
    assert (c.step.kind, [t.scope for t in c.plan.tasks], c.overlaps) == (StepKind.BUILD, [["src/app.ts"]], SHARED)
