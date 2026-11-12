"""The planner's challenge rounds (TD-190, TD-208): findings by ID, rejections judged, the owner, the end."""

import errno
import os
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from owlbear_delivery_next.change_contracts import tools
from owlbear_delivery_next.change_contracts.dispute_tools import SUBMIT as RECONSIDER
from owlbear_delivery_next.change_contracts.dispute_tools import ReconsiderResult
from owlbear_delivery_next.change_contracts.inbox import AnswerItem
from owlbear_delivery_next.change_contracts.models import (
    Answer,
    Brief,
    Change,
    Exit,
    Names,
    Plan,
    Step,
    StepKind,
    Task,
)
from owlbear_delivery_next.change_contracts.profile_record import Profile
from owlbear_delivery_next.change_contracts.round_records import (
    FINAL,
    PLAN,
    UNJUDGED,
    RoundLoop,
    RoundPolicy,
    Verdict,
)
from owlbear_delivery_next.change_contracts.tools import Worktree
from owlbear_delivery_next.change_flow import disputes, loop, plan_rounds, round_flow, round_marks
from owlbear_delivery_next.change_flow.loop import StepResult
from owlbear_delivery_next.commands import runner
from owlbear_delivery_next.local_system.processes import Termination
from owlbear_delivery_next.runtimes import step_input
from owlbear_delivery_next.runtimes.session_result import Run
from owlbear_delivery_next.settings import config
from owlbear_delivery_next.settings.roles import UserConfig
from owlbear_delivery_next.state_store.store import Lock, Store
from owlbear_delivery_next.workflow_steps import plan_round

NOW = datetime(2026, 10, 18, 3, tzinfo=UTC)
K = StepKind
FEW = RoundPolicy(max_rounds=3, max_findings=5, last_round_at=0, ask_owner_at=1)  # every finding goes on


def task(n: int, scope: str = "src") -> dict:
    return {"title": f"step {n}", "goal": "AC-1", "scope": [scope], "checks": ["true"]}


def finding(where: str) -> dict:
    return {"place": where, "problem": "AC-1 untested", "fix": "add a check"}


@pytest.fixture
def store(tmp_path, change_repo, monkeypatch, checks_settled) -> Store:
    """Change c1 at planning, its plan loop pinned to FEW."""
    store = Store(tmp_path / "store")
    checks_settled(store)
    names = Names(branch="owlbear/c1", target="main", worktree=str(change_repo))
    c = Change(slug="c1", brief=Brief(version=1, approved_version=1, challenged=1), step=Step(kind=K.PLAN), names=names)
    c.loops[PLAN] = RoundLoop(subject=PLAN, policy=FEW)
    store.write(Lock("c1"), c)
    other = Plan(tasks=[Task(id="t1", title="other", scope=["src"])])
    store.write(Lock("c2"), Change(slug="c2", brief=Brief(version=1), plan=other, step=Step(kind=K.BUILD)))
    monkeypatch.setattr(runner.worktree, "ensure", lambda *_a: change_repo)
    return store


class Sessions:
    """The planner's, the challenger's and the reconsideration's results, in turn; what each session was told."""

    def __init__(self, monkeypatch) -> None:
        self.plans: list[tools.PlanResult] = []
        self.reviews: list[tools.ReviewResult | None] = []
        self.reconsiders: list[ReconsiderResult] = []
        self.told: list[tuple[str, object]] = []
        monkeypatch.setattr(runner.sdk_adapter, "run", self.run)

    async def run(self, cfg):
        if cfg.submit is tools.PLAN:
            self.told.append(("plan", cfg))
            payload = self.plans.pop(0)
        elif cfg.submit is RECONSIDER:
            self.told.append(("reconsider", cfg))
            payload = self.reconsiders.pop(0)
            if isinstance(payload, tools.WrongPremise):
                return Run(cfg.session_id, "premise", payload, termination=Termination(confirmed=True))
        else:
            self.told.append(("challenge", cfg))
            if (payload := self.reviews.pop(0)) is None:
                return Run(cfg.session_id, "error", detail="boom", termination=Termination(confirmed=True))
            if isinstance(payload, tools.WrongPremise):
                return Run(cfg.session_id, "premise", payload, termination=Termination(confirmed=True))
        return Run(cfg.session_id, "result", payload, termination=Termination(confirmed=True))

    def kinds(self) -> list[str]:
        return [k for k, _ in self.told]

    def said(self, kind: str) -> str:
        return next(cfg.message for k, cfg in reversed(self.told) if k == kind)


def step(store: Store, repo) -> Change:
    c = store.read("c1")
    runner._step(store, Lock("c1"), c, c.step, repo)  # noqa: SLF001
    return store.read("c1")


def answer(store: Store, option: str, text: str = "") -> Change:
    q = next(q for q in store.read("c1").questions if q.answer is None)
    store.put_inbox("c1", AnswerItem(at=datetime.now(UTC), question=q.id, option=option, text=text))
    return store.fold(Lock("c1"), "c1", datetime.now(UTC))[0]


def plan(n: int, rejected: dict[str, str] | None = None, scope: str = "src") -> tools.PlanResult:
    found = [{"finding": k, "reason": r} for k, r in (rejected or {}).items()]
    return tools.PlanResult(tasks=[task(i, scope) for i in range(1, n + 1)], rejected=found)


def review(*places: str, upheld: dict[str, bool] | None = None) -> tools.ReviewResult:
    judged = [{"finding": k, "upheld": u, "reason": "see t1"} for k, u in (upheld or {}).items()]
    return tools.ReviewResult(verdict="fix" if places else "pass", findings=[finding(p) for p in places],
                              rechecked=judged)  # fmt: skip


def test_a_rejection_the_next_round_upholds_is_delegated_and_its_fix_is_never_rejected(store, change_repo, mp):
    s = mp
    s.plans += [plan(1), plan(1, {"F1": "t1's check covers it"}), plan(2)]
    s.reviews += [review("t1"), review(upheld={"F1": True})]
    c = step(store, change_repo)
    assert (c.outcome.exit, c.outcome.challenged, c.step.mode) == (Exit.RETRY, True, None)
    assert [(f.id, f.state) for f in c.loops[PLAN].findings] == [("F1", "open")]
    c = step(store, change_repo)
    planner = s.said("plan")
    assert "> F1. t1: AC-1 untested - fix: add a check" in planner
    assert "## Rejecting" in planner
    assert "Review findings (data)" not in planner  # the outcome's text is display only (TD-188)
    challenger = s.said("challenge")
    assert "## Rejections to judge" in challenger
    assert "Planner's reason: t1's check covers it" in challenger
    assert s.told[-1][1].rechecks == ("F1",)
    assert (c.outcome.exit, c.questions) == (Exit.RETRY, [])
    assert (c.loops[PLAN].round, c.loops[PLAN].findings[0].state) == (2, "owner-fix")
    assert c.loops[PLAN].findings[0].note == plan_rounds.DELEGATED
    assert (c.step.kind, c.step.mode, c.loops[PLAN].findings[0].state) == (K.PLAN, None, "owner-fix")
    c = step(store, change_repo)
    planner = s.said("plan")
    assert "[the owner's]" in planner
    assert plan_rounds.DELEGATED in planner
    assert "## Rejecting" not in planner
    assert s.told[-1][1].rejectable == ()
    assert s.told[-1][1].settled == ("F1",)
    assert s.kinds() == ["plan", "challenge", "plan", "challenge", "plan"]  # the last round's revision: unreviewed
    assert (c.step.kind, len(c.plan.tasks)) == (K.BUILD, 2)
    lp = c.loops[PLAN]
    assert (lp.ended, lp.unreviewed, lp.findings[0].state) == ("count", ["r2"], "fixed")
    shown = round_marks.shown(c)
    assert [(m["round"], m["kind"]) for m in shown["plan"]] == [(1, "unverified")]  # revised for, not challenged again
    assert shown["unreviewed"] == [{"id": "r2", "title": "the plan as revised after challenge round 2", "loop": PLAN}]


@pytest.fixture
def mp(monkeypatch) -> Sessions:
    return Sessions(monkeypatch)


def test_a_failed_challenge_challenges_the_same_plan_again_without_planning_again(store, change_repo, mp):
    mp.plans += [plan(2)]
    mp.reviews += [None, review()]
    c = step(store, change_repo)
    assert (c.step.kind, c.step.mode, len(c.plan.tasks), c.loops[PLAN].round) == (K.PLAN, "challenge", 2, 0)
    c = step(store, change_repo)
    assert mp.kinds() == ["plan", "challenge", "challenge"]
    assert (c.step.kind, c.loops[PLAN].ended, c.loops[PLAN].round) == (K.BUILD, "clean", 1)


@pytest.mark.parametrize(("instructions", "skills", "memory"), [(True, False, True), (False, True, False)])
def test_the_planner_and_its_challenger_run_with_the_owners_user_config(  # noqa: PLR0913, PLR0917 - fixtures
    store, change_repo, mp, monkeypatch, instructions, skills, memory
):
    switched = {"load_user_instructions": instructions, "load_user_skills": skills, "load_user_memory": memory}
    monkeypatch.setattr(config, "BASE", config.BASE.model_copy(update=switched))
    mp.plans += [plan(1)]
    mp.reviews += [review()]
    step(store, change_repo)
    assert mp.kinds() == ["plan", "challenge"]
    assert [cfg.user for _, cfg in mp.told] == [UserConfig(instructions=instructions, skills=skills, memory=memory)] * 2


def test_a_host_that_dies_during_the_challenge_keeps_the_revision_and_challenges_it(store, change_repo, mp):
    mp.plans += [plan(1), plan(3, {"F1": "no"})]
    mp.reviews += [review("t1"), review(upheld={"F1": False})]
    step(store, change_repo)

    async def died(cfg):
        if cfg.submit is tools.PLAN:
            return await mp.run(cfg)
        raise KeyboardInterrupt

    with pytest.MonkeyPatch.context() as m:
        m.setattr(runner.sdk_adapter, "run", died)
        with pytest.raises(KeyboardInterrupt):
            step(store, change_repo)
    c = store.read("c1")
    assert (c.step.mode, len(c.plan.tasks), c.loops[PLAN].findings[0].state) == ("challenge", 3, "rejected")
    c = step(store, change_repo)  # the crashed session's processes are not confirmed gone yet: refused
    assert (mp.kinds(), c.step.mode, len(c.plan.tasks)) == (["plan", "challenge", "plan"], "challenge", 3)


@pytest.mark.parametrize(("revision", "unreviewed"), [(2, ["r1"])])  # changed; resubmitted unchanged: below
def test_an_early_last_round_with_rejections_gets_a_check_outside_the_count(
    store, change_repo, mp, revision, unreviewed
):
    c = store.read("c1")
    c.loops[PLAN].policy = RoundPolicy(max_rounds=3, max_findings=5, last_round_at=2, ask_owner_at=3)
    store.write(Lock("c1"), c)
    mp.plans += [plan(1), plan(revision, {"F1": "no"})]
    mp.reviews += [review("t1"), review(upheld={"F1": False})]
    step(store, change_repo)
    c = step(store, change_repo)
    assert "Judge only these rejections" in mp.said("challenge")
    assert (mp.told[-1][1].cap, mp.told[-1][1].rechecks) == (0, ("F1",))
    lp = c.loops[PLAN]
    assert (c.step.kind, lp.round, lp.ended, lp.unreviewed, lp.findings[0].state) == (
        K.BUILD, 1, "count" if unreviewed else "clean", unreviewed, "standing"
    )  # fmt: skip
    assert c.plan.version == 2
    assert lp.verdicts == [Verdict(round=1, version=1), Verdict(round=1, version=2, recheck=True, repair=True)]


def test_a_plan_resubmitted_unchanged_after_the_last_round_is_no_unreviewed_revision(store, change_repo, mp):
    """TD-330: a last round at the maximum gets its rejections judged too; the owner only with many findings."""
    c = store.read("c1")
    c.loops[PLAN].policy = RoundPolicy(max_rounds=1, max_findings=5, last_round_at=0, ask_owner_at=2)
    store.write(Lock("c1"), c)
    mp.plans += [plan(1), plan(1, {"F1": "no"})]
    mp.reviews += [review("t1"), review(upheld={"F1": False})]
    step(store, change_repo)
    c = step(store, change_repo)
    assert (mp.told[-1][1].cap, mp.told[-1][1].rechecks) == (0, ("F1",))
    lp = c.loops[PLAN]
    assert (c.step.kind, lp.round, lp.ended, lp.unreviewed, lp.findings[0].state) == (
        K.BUILD,
        1,
        "clean",
        [],
        "standing",
    )


def test_a_wrong_premise_in_the_check_is_revised_for_and_the_check_never_runs_again(store, change_repo, mp):
    """Sol: a check that reports a wrong premise judges nothing; its rejection stands, said so, and the loop ends."""
    c = store.read("c1")
    c.loops[PLAN].policy = RoundPolicy(max_rounds=3, max_findings=5, last_round_at=2, ask_owner_at=3)
    store.write(Lock("c1"), c)
    mp.plans += [plan(1), plan(1, {"F1": "no"}), plan(2)]
    mp.reviews += [review("t1"), tools.WrongPremise(stage="plan", reason="AC-1 contradicts AC-2", evidence=["brief"])]
    step(store, change_repo)
    step(store, change_repo)
    c = step(store, change_repo)
    lp = c.loops[PLAN]
    assert [(f.state, f.judgement) for f in lp.findings] == [("standing", UNJUDGED), ("fixed", "")]
    assert (mp.kinds(), lp.round, lp.ended, c.step.kind) == (
        ["plan", "challenge", "plan", "challenge", "plan"],
        1,
        "count",
        K.BUILD,
    )


def test_a_check_at_the_maximum_whose_upheld_rejection_delivery_keeps_is_revised_at_max(store, change_repo, mp):
    c = store.read("c1")
    c.loops[PLAN].policy = RoundPolicy(max_rounds=1, max_findings=5, last_round_at=0, ask_owner_at=2)
    store.write(Lock("c1"), c)
    mp.plans += [plan(1), plan(2, {"F1": "no"}), plan(3)]
    mp.reviews += [review("t1"), review(upheld={"F1": True})]
    step(store, change_repo)
    c = step(store, change_repo)
    assert (c.questions, c.loops[PLAN].findings[0].state) == ([], "owner-fix")
    c = step(store, change_repo)
    lp = c.loops[PLAN]
    assert (lp.findings[0].state, lp.round, lp.unreviewed, lp.ended, c.step.kind) == (
        "fixed", 1, ["r1"], "max", K.BUILD
    )  # fmt: skip


def test_after_the_last_round_many_findings_stop_without_asking_for_another_round(store, change_repo, mp):
    c = store.read("c1")
    c.loops[PLAN].policy = RoundPolicy(max_rounds=1, max_findings=5, last_round_at=0, ask_owner_at=1)
    store.write(Lock("c1"), c)
    mp.plans += [plan(1), plan(1, {"F1": "no"})]
    mp.reviews += [review("t1"), review(upheld={"F1": False})]
    step(store, change_repo)
    c = step(store, change_repo)
    assert (mp.told[-1][1].cap, mp.told[-1][1].rechecks) == (0, ("F1",))
    assert (c.outcome.exit, c.questions, c.stop.action) == (Exit.STOP, [], "Run the step again")
    assert c.stop.reason.startswith(plan_rounds.LAST_STOP)
    assert "F1 rejected; the challenger accepted that (no)" in c.stop.reason
    assert (c.loops[PLAN].findings[0].state, c.loops[PLAN].round) == ("standing", 1)
    assert loop.next_step(c, datetime.now(UTC)) is None


def test_a_last_round_stop_keeps_the_plan_and_attempt_instead_of_starting_a_new_plan(store, change_repo, mp):
    c = store.read("c1")
    c.loops[PLAN].policy = RoundPolicy(max_rounds=1, max_findings=5, last_round_at=0, ask_owner_at=1)
    store.write(Lock("c1"), c)
    mp.plans += [plan(1), plan(1)]
    mp.reviews += [review("t1")]
    step(store, change_repo)
    c = step(store, change_repo)
    lp = c.loops[PLAN]
    assert (c.outcome.exit, c.questions, lp.attempt, lp.round, lp.history) == (Exit.STOP, [], 1, 1, [])
    assert c.stop.reason.startswith(plan_rounds.LAST_STOP)
    assert "F1 revised for, not challenged again" in c.stop.reason
    assert (c.plan.version, len(c.plan.tasks)) == (2, 1)
    assert mp.kinds() == ["plan", "challenge", "plan"]
    assert loop.next_step(c, datetime.now(UTC)) is None


def test_an_already_asked_dispute_is_reconsidered_once_and_its_drop_settles_the_plan(store, change_repo, mp):
    mp.plans += [plan(1, scope="lib"), plan(1, {"F1": "no"}), plan(2)]
    mp.reviews += [review("t1"), review(upheld={"F1": True})]
    mp.reconsiders += [
        ReconsiderResult(reconsidered=[{"finding": "F1", "verdict": "unsure", "reason": "only the owner knows"}])
    ]
    step(store, change_repo)
    step(store, change_repo)
    c = store.read("c1")
    lp = c.loops[PLAN]
    lp.findings[0].state, lp.findings[0].note = "escalated", ""
    loop.ask(c, plan_rounds.question(lp, lp.findings[0]), NOW)  # a dispute persisted before delegation was introduced
    store.write(Lock("c1"), c)
    c = answer(store, "reconsider")
    assert c.outcome.exit == Exit.ASK  # a reconsideration needs the owner's note
    c = answer(store, "reconsider", "the brief says one task")
    assert c.step.mode == "reconsider"
    c = step(store, change_repo)
    assert "The owner's note: the brief says one task" in mp.said("reconsider")
    q = loop.open_question(c)
    assert [o.id for o in q.options] == ["fix", "drop"]  # reconsidered once
    assert len(c.questions) == 2
    c = answer(store, "drop", "fine as is")
    assert (c.step.mode, c.loops[PLAN].findings[0].state) == ("settled", "owner-drop")
    c = step(store, change_repo)
    assert mp.kinds() == ["plan", "challenge", "plan", "challenge", "reconsider"]
    assert (c.step.kind, len(c.plan.tasks)) == (K.BUILD, 1)
    assert [o.other for o in c.overlaps] == ["c2"]  # recorded before the challenge


def test_an_already_asked_disputes_reconsidered_premise_returns_to_the_owner_as_unsure(store, change_repo, mp):
    mp.plans += [plan(1), plan(1, {"F1": "no"})]
    mp.reviews += [review("t1"), review(upheld={"F1": True})]
    mp.reconsiders += [tools.WrongPremise(stage="brief", reason="AC-1 contradicts AC-2", evidence=["brief"])]
    step(store, change_repo)
    step(store, change_repo)
    c = store.read("c1")
    lp = c.loops[PLAN]
    lp.findings[0].state, lp.findings[0].note = "escalated", ""
    loop.ask(c, plan_rounds.question(lp, lp.findings[0]), NOW)  # a dispute persisted before delegation was introduced
    store.write(Lock("c1"), c)
    answer(store, "reconsider", "look again")
    c = step(store, change_repo)
    q = next(q for q in c.questions if q.answer is None)
    assert ([o.id for o in q.options], c.loops[PLAN].findings[0].clarified) == (
        ["fix", "drop"], "premise: AC-1 contradicts AC-2"
    )  # fmt: skip


def test_the_planner_whose_rejection_delivery_overrules_revises_with_its_own_repair_chance(store, change_repo, mp):
    mp.plans += [plan(1), plan(1), plan(1, {"F2": "no"}), plan(2)]
    mp.reviews += [review("t1"), review("t2"), review(upheld={"F2": True})]
    for _ in range(3):
        step(store, change_repo)
    assert store.read("c1").questions == []
    assert store.read("c1").loops[PLAN].findings[-1].note == plan_rounds.DELEGATED
    c = step(store, change_repo)
    planners = [cfg for k, cfg in mp.told if k == "plan"]
    assert [cfg.resume for cfg in planners] == [False, True, False, True]  # each producer once (TD-123)
    assert planners[3].session_id == planners[2].session_id
    assert c.step.kind == K.BUILD


def test_an_already_asked_disputes_clarified_finding_goes_to_the_planner_as_the_owners(store, change_repo, mp):
    mp.plans += [plan(1), plan(1, {"F1": "no"}), plan(2)]
    mp.reviews += [review("t1"), review(upheld={"F1": True})]
    mp.reconsiders += [
        ReconsiderResult(
            reconsidered=[{"finding": "F1", "verdict": "clarified", "text": "t1: AC-1 edge", "reason": "r"}]
        )
    ]
    step(store, change_repo)
    step(store, change_repo)
    c = store.read("c1")
    lp = c.loops[PLAN]
    lp.findings[0].state, lp.findings[0].note = "escalated", ""
    loop.ask(c, plan_rounds.question(lp, lp.findings[0]), NOW)  # a dispute persisted before delegation was introduced
    store.write(Lock("c1"), c)
    answer(store, "reconsider", "narrow it")
    c = step(store, change_repo)
    assert (c.step.mode, c.loops[PLAN].findings[0].state) == (None, "owner-fix")
    step(store, change_repo)
    assert "> F1. t1: AC-1 edge [the owner's]" in mp.said("plan")


def test_a_delegated_upheld_rejection_survives_replaced_outcome_without_asking_again(store, change_repo, mp):
    mp.plans += [plan(1), plan(1, {"F1": "no"}), plan(2)]
    mp.reviews += [review("t1"), review(upheld={"F1": True})]
    step(store, change_repo)
    c = step(store, change_repo)
    c.outcome = None  # a stop and its recovery took the delegated outcome's place
    store.write(Lock("c1"), c)
    c = step(store, change_repo)
    assert mp.kinds() == ["plan", "challenge", "plan", "challenge", "plan"]
    assert (c.questions, c.step.kind, c.loops[PLAN].findings[0].state) == ([], K.BUILD, "fixed")
    assert plan_rounds.DELEGATED in mp.said("plan")


def test_a_plan_question_settles_only_while_it_is_the_open_one_and_retires_with_its_attempt():
    c = Change(slug="c1", brief=Brief(version=1), step=Step(kind=K.PLAN), plan=Plan(tasks=[Task(id="t1", title="a")]))
    lp = plan_rounds.loop(c, FEW, NOW)
    lp.raise_findings(["t1: x - fix: y", "t1: z - fix: w"])
    for f in lp.findings:
        f.state, f.reason = "escalated", "no"
    c.questions.append(plan_rounds.question(lp, lp.findings[1]).model_copy(update={"id": "q1"}))  # never asked
    loop.ask(c, plan_rounds.question(lp, lp.findings[0]), NOW)
    c = loop.fold(c, [AnswerItem(at=NOW, question="q1", option="drop")], NOW)
    assert (c.questions[0].answer, c.loops[PLAN].findings[1].state) == (None, "escalated")  # not the open question
    c = loop.fold(c, [AnswerItem(at=NOW, question="q2", option="drop")], NOW)
    assert c.loops[PLAN].findings[0].state == "owner-drop"
    assert c.outcome.question == "q3"  # the next undecided finding, asked anew
    c.loops[PLAN].ended = "replanned"
    plan_rounds.accepted(c, NOW)
    assert all(q.answer is not None for q in c.questions)  # retired with the attempt


def test_the_plan_challenger_never_sees_the_owners_plan_decisions_but_the_planner_does():
    c = Change(slug="c1", brief=Brief(version=1), step=Step(kind=K.PLAN), plan=Plan(tasks=[Task(id="t1", title="a")]))
    lp = plan_rounds.loop(c, FEW, NOW)
    lp.raise_findings(["t1: secret finding - fix: y"])
    f = lp.findings[0]
    f.state, f.reason = "escalated", "no"
    q = plan_rounds.question(lp, f).model_copy(update={"id": "q1"})
    q.answer = Answer(option="fix", text="do it", at=NOW)
    c.questions.append(q)
    assert "secret finding" not in step_input.plan_challenge(c, c.plan, Profile(), Path("/w"), {})
    assert "secret finding" in step_input.plan(c, Profile(), Path("/w"), {})


def test_the_planner_rejects_only_the_listed_findings_never_the_owners_and_needs_no_commit():
    tree = Worktree(head="a", base="a", changed=(), dirty=())
    check = lambda keys, allowed, settled=(): disputes.check(  # noqa: E731
        plan(1, dict.fromkeys(keys, "r")), tree, allowed, (), settled=settled
    )
    assert check(["F1"], ("F1", "F2")) == []
    assert check(["F3"], ("F1",)) == ["rejected: F3 is no finding key of this task - use F1"]
    assert check(["F2"], ("F1",), ("F2",))[0].startswith("rejected: F2 is the owner's decision")
    assert check([], ("F1",), ("F2",)) == []  # revising for every finding needs no commit


def test_an_accepted_new_plan_retires_the_old_plans_task_loops_and_a_final_replan_keeps_the_planners_loop():
    c = Change(slug="c1", brief=Brief(version=1), step=Step(kind=K.PLAN), plan=Plan(tasks=[Task(id="t1", title="a")]))
    lp = plan_rounds.loop(c, FEW, NOW)
    lp.round, lp.ended = 1, "clean"
    c.loops["t1"] = RoundLoop(subject="t1", policy=FEW, round=2)
    c.loops[FINAL] = RoundLoop(subject=FINAL, policy=FEW)
    round_flow.replan(c, c.loops[FINAL], "why", NOW)
    assert set(c.loops) == {FINAL, PLAN}
    assert [h.subject for h in c.loops[FINAL].history] == [FINAL, "t1"]
    c.loops["t1"] = RoundLoop(subject="t1", policy=FEW, round=2)
    lp = plan_rounds.loop(c, FEW, NOW)  # the new plan's first challenge: a new attempt
    assert (lp.attempt, [h.ended for h in lp.history]) == (2, ["clean"])
    c = loop.apply(c, StepResult(exit=Exit.DONE, plan=Plan(tasks=[Task(id="t1", title="b")])), NOW)
    assert "t1" not in c.loops  # the new plan's t1 starts its own loop
    assert c.loops[PLAN].history[-1].subject == "t1"
    assert c.loops[PLAN].ended == "clean"


def test_going_back_to_the_brief_ends_the_plan_attempt():
    c = Change(slug="c1", brief=Brief(version=1), step=Step(kind=K.PLAN))
    plan_rounds.loop(c, FEW, NOW)
    back = StepResult(exit=Exit.BACK, back_to=K.SHAPE, cause="scope:plan:brief", reason="AC-1 is wrong")
    c = loop.apply(c, back, NOW)
    assert c.loops[PLAN].ended == "replanned"


def test_many_plan_rounds_never_reach_the_old_plan_gate():
    c = Change(slug="c1", brief=Brief(version=1), step=Step(kind=K.PLAN), plan=Plan(tasks=[Task(id="t1", title="a")]))
    for _ in range(5):
        r = StepResult(exit=Exit.RETRY, plan=c.plan, reason="plan challenge: x", challenged=True, ungated=True)
        c = loop.apply(c, r, NOW)
    assert (c.step.kind, c.outcome.exit, c.questions) == (K.PLAN, Exit.RETRY, [])


def test_a_known_usage_challenge_whose_settlement_write_fails_is_charged_once_across_a_fresh_reload(
    store, change_repo, mp, tmp_path, monkeypatch
):
    """The paid challenge's verdict, spend and round are one settlement: a fault there must not re-run the child."""
    real_run = mp.run

    async def billed(cfg):
        done = await real_run(cfg)
        paid = 1.0 if cfg.submit is tools.PLAN else 3.5
        return replace(done, usage={"credits": paid})

    monkeypatch.setattr(runner.sdk_adapter, "run", billed)
    real_write = Store.write
    armed = {"on": True}

    def faulty(self, lock, change):
        if armed["on"] and change.slug == "c1" and change.step.mode is None and change.spend.credits >= 4.5:
            armed["on"] = False  # the settlement write: the verdict, the spend and the round together
            raise OSError(errno.ENOSPC, os.strerror(errno.ENOSPC))
        return real_write(self, lock, change)

    monkeypatch.setattr(Store, "write", faulty)
    mp.plans += [plan(1)]
    mp.reviews += [review(upheld={})]  # a pass: the challenge's one round
    with pytest.raises(OSError, match="No space left"):
        step(store, change_repo)

    assert [e for e in store.events("c1") if e.get("kind") == "plan-challenge"] == []  # logged only once durable
    monkeypatch.setattr(Store, "write", real_write)
    fresh = Store(tmp_path / "store")
    step(fresh, change_repo)
    c = fresh.read("c1")
    assert mp.kinds().count("challenge") == 1  # the paid challenge ran once, never again after the fault
    assert c.spend.credits == pytest.approx(4.5)  # planner 1.0 + challenge 3.5, once each
    assert [e["kind"] for e in fresh.events("c1") if e.get("kind") == "plan-challenge"] == ["plan-challenge"]
    assert (c.step.mode, c.outcome.exit) == (None, Exit.DONE)


def test_a_continued_plan_challenge_records_its_start_before_its_challenger_runs(tmp_path, monkeypatch):
    """#718: the challenger's session is the step's own; its stage shows from the step's start, not as starting."""
    store = Store(tmp_path / "store")
    plan = Plan(tasks=[Task(id="t1", title="greet")])
    store.write(Lock("c1"), Change(slug="c1", plan=plan, step=Step(kind=StepKind.PLAN, mode=plan_rounds.CHALLENGE)))
    seen = []

    def challenge(store_, _lock, change, *_args):
        seen.append(store_.read("c1").step.started_at is not None)
        return loop.StepResult(exit=Exit.DONE, plan=change.plan, reason="the plan challenge passed")

    monkeypatch.setattr(plan_round.worktree, "ensure", lambda *_a: tmp_path)
    monkeypatch.setattr(plan_round, "git_common_dir", lambda repo: repo)
    monkeypatch.setattr(plan_round, "scopes", lambda *_a: {})
    monkeypatch.setattr(plan_round, "challenge", challenge)
    assert plan_round.continued(store, Lock("c1"), store.read("c1"), tmp_path)
    assert seen == [True]
