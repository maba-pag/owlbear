"""The planner's challenge rounds (TD-190, TD-208): findings by ID, rejections judged, the owner, the end."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from owlbear_delivery_next import disputes, loop, plan_rounds, prompts, round_flow, round_marks, runner, tools
from owlbear_delivery_next.dispute_tools import SUBMIT as RECONSIDER
from owlbear_delivery_next.dispute_tools import ReconsiderResult
from owlbear_delivery_next.inbox import AnswerItem
from owlbear_delivery_next.loop import StepResult
from owlbear_delivery_next.models import Answer, Brief, Change, Exit, Names, Plan, Question, Step, StepKind, Task
from owlbear_delivery_next.processes import Termination
from owlbear_delivery_next.profile_record import Profile
from owlbear_delivery_next.round_records import FINAL, PLAN, RoundLoop, RoundPolicy
from owlbear_delivery_next.session_result import Run
from owlbear_delivery_next.store import Lock, Store
from owlbear_delivery_next.tools import Worktree

NOW = datetime(2026, 10, 18, 3, tzinfo=UTC)
K = StepKind
FEW = RoundPolicy(max_rounds=3, max_findings=5, last_round_at=0, ask_owner_at=1)  # every finding goes on


def task(n: int, scope: str = "src") -> dict:
    return {"title": f"step {n}", "goal": "AC-1", "scope": [scope], "checks": ["true"]}


def finding(where: str) -> dict:
    return {"place": where, "problem": "AC-1 untested", "fix": "add a check"}


@pytest.fixture
def store(tmp_path, change_repo, monkeypatch) -> Store:
    """Change c1 at planning, its plan loop pinned to FEW."""
    store = Store(tmp_path / "store")
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


def test_a_rejection_the_next_round_upholds_goes_to_the_owner_and_his_fix_is_never_rejected(store, change_repo, mp):
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
    assert c.outcome.exit == Exit.ASK
    q = next(q for q in c.questions if q.answer is None)
    assert [o.id for o in q.options] == ["fix", "reconsider", "drop"]
    assert (c.loops[PLAN].round, c.loops[PLAN].findings[0].state) == (2, "escalated")
    c = answer(store, "fix", "keep one task per check")
    assert (c.step.kind, c.step.mode, c.loops[PLAN].findings[0].state) == (K.PLAN, None, "owner-fix")
    c = step(store, change_repo)
    planner = s.said("plan")
    assert "[the owner's]" in planner
    assert "keep one task per check" in planner
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


@pytest.mark.parametrize(("revision", "unreviewed"), [(2, ["r1"]), (1, [])])  # changed, or resubmitted unchanged
def test_an_early_last_round_with_rejections_gets_a_rejections_only_check(store, change_repo, mp, revision, unreviewed):
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
        K.BUILD, 2, "count" if unreviewed else "clean", unreviewed, "standing"
    )  # fmt: skip


def test_a_plan_resubmitted_unchanged_after_the_last_round_is_no_unreviewed_revision(store, change_repo, mp):
    c = store.read("c1")
    c.loops[PLAN].policy = RoundPolicy(max_rounds=1, max_findings=5, last_round_at=0, ask_owner_at=2)
    store.write(Lock("c1"), c)
    mp.plans += [plan(1), plan(1, {"F1": "no"})]
    mp.reviews += [review("t1")]
    step(store, change_repo)
    c = step(store, change_repo)
    assert (c.step.kind, c.loops[PLAN].ended, c.loops[PLAN].unreviewed) == (K.BUILD, "max", [])


def test_after_the_last_round_the_owner_has_another_round_or_a_new_plan(store, change_repo, mp):
    c = store.read("c1")
    c.loops[PLAN].policy = RoundPolicy(max_rounds=1, max_findings=5, last_round_at=0, ask_owner_at=1)
    store.write(Lock("c1"), c)
    mp.plans += [plan(1), plan(1, {"F1": "no"}), plan(3)]
    mp.reviews += [review("t1"), review(upheld={"F1": False})]
    step(store, change_repo)
    c = step(store, change_repo)
    q = next(q for q in c.questions if q.answer is None)
    assert [o.id for o in q.options] == ["another", "retry"]
    assert "F1 rejected (no)" in q.text
    c = answer(store, "another")
    assert (c.step.mode, c.loops[PLAN].extra) == ("challenge", 1)
    c = step(store, change_repo)
    assert mp.kinds()[-1] == "challenge"  # no planner session for another round
    assert (c.loops[PLAN].findings[0].state, c.step.kind) == ("standing", K.BUILD)


def test_plan_again_from_the_brief_is_a_new_attempt_told_why_without_the_old_plan(store, change_repo, mp):
    c = store.read("c1")
    c.loops[PLAN].policy = RoundPolicy(max_rounds=1, max_findings=5, last_round_at=0, ask_owner_at=1)
    store.write(Lock("c1"), c)
    mp.plans += [plan(1), plan(1), plan(4)]
    mp.reviews += [review("t1"), review()]
    step(store, change_repo)
    step(store, change_repo)
    c = store.read("c1")
    orphan = Question(step=K.PLAN, text="old", options=plan_rounds.OPTIONS, cause=f"{plan_rounds.DISPUTE}1 F9")
    c.questions.append(orphan.model_copy(update={"id": "q9"}))
    store.write(Lock("c1"), c)
    c = answer(store, "retry")
    assert c.questions[-1].answer.option == plan_rounds.RETIRED  # a question of the attempt that ended
    lp = c.loops[PLAN]
    assert (lp.attempt, lp.round, [h.ended for h in lp.history]) == (2, 0, ["retried"])
    c = step(store, change_repo)
    planner = mp.said("plan")
    assert "## Why the Change is planned again" in planner
    assert "challenge round 1" in planner
    assert "## Your previous plan" not in planner
    assert (c.step.kind, len(c.plan.tasks)) == (K.BUILD, 4)


def test_a_reconsideration_clarifies_or_returns_unsure_once_and_a_drop_settles_the_plan(store, change_repo, mp):
    mp.plans += [plan(1, scope="lib"), plan(1, {"F1": "no"}), plan(2)]
    mp.reviews += [review("t1"), review(upheld={"F1": True})]
    mp.reconsiders += [
        ReconsiderResult(reconsidered=[{"finding": "F1", "verdict": "unsure", "reason": "only the owner knows"}])
    ]
    step(store, change_repo)
    step(store, change_repo)
    c = answer(store, "reconsider")
    assert c.outcome.exit == Exit.ASK  # a reconsideration needs the owner's note
    c = answer(store, "reconsider", "the brief says one task")
    assert c.step.mode == "reconsider"
    c = step(store, change_repo)
    assert "The owner's note: the brief says one task" in mp.said("reconsider")
    q = next(q for q in c.questions if q.answer is None)
    assert [o.id for o in q.options] == ["fix", "drop"]  # reconsidered once
    c = answer(store, "drop", "fine as is")
    assert (c.step.mode, c.loops[PLAN].findings[0].state) == ("settled", "owner-drop")
    c = step(store, change_repo)
    assert mp.kinds() == ["plan", "challenge", "plan", "challenge", "reconsider"]
    assert (c.step.kind, len(c.plan.tasks)) == (K.BUILD, 1)
    assert [o.other for o in c.overlaps] == ["c2"]  # recorded with the plan, before its challenge asked


def test_a_premise_the_reconsidering_challenger_reports_goes_to_the_owner_as_unsure(store, change_repo, mp):
    mp.plans += [plan(1), plan(1, {"F1": "no"})]
    mp.reviews += [review("t1"), review(upheld={"F1": True})]
    mp.reconsiders += [tools.WrongPremise(stage="brief", reason="AC-1 contradicts AC-2", evidence=["brief"])]
    step(store, change_repo)
    step(store, change_repo)
    answer(store, "reconsider", "look again")
    c = step(store, change_repo)
    q = next(q for q in c.questions if q.answer is None)
    assert ([o.id for o in q.options], c.loops[PLAN].findings[0].clarified) == (
        ["fix", "drop"], "premise: AC-1 contradicts AC-2"
    )  # fmt: skip


def test_the_planner_whose_rejection_the_owner_overrules_revises_with_its_own_repair_chance(store, change_repo, mp):
    mp.plans += [plan(1), plan(1), plan(1, {"F2": "no"}), plan(2)]
    mp.reviews += [review("t1"), review("t2"), review(upheld={"F2": True})]
    for _ in range(3):
        step(store, change_repo)
    answer(store, "fix")
    c = step(store, change_repo)
    planners = [cfg for k, cfg in mp.told if k == "plan"]
    assert [cfg.resume for cfg in planners] == [False, True, False, True]  # each producer once (TD-123)
    assert planners[3].session_id == planners[2].session_id
    assert c.step.kind == K.BUILD


def test_a_clarified_finding_goes_to_the_planner_as_the_owners(store, change_repo, mp):
    mp.plans += [plan(1), plan(1, {"F1": "no"}), plan(2)]
    mp.reviews += [review("t1"), review(upheld={"F1": True})]
    mp.reconsiders += [
        ReconsiderResult(
            reconsidered=[{"finding": "F1", "verdict": "clarified", "text": "t1: AC-1 edge", "reason": "r"}]
        )
    ]
    step(store, change_repo)
    step(store, change_repo)
    answer(store, "reconsider", "narrow it")
    c = step(store, change_repo)
    assert (c.step.mode, c.loops[PLAN].findings[0].state) == (None, "owner-fix")
    step(store, change_repo)
    assert "> F1. t1: AC-1 edge [the owner's]" in mp.said("plan")


def test_an_upheld_rejection_whose_question_a_stop_replaced_is_asked_again_before_any_planning(store, change_repo, mp):
    mp.plans += [plan(1), plan(1, {"F1": "no"})]
    mp.reviews += [review("t1"), review(upheld={"F1": True})]
    step(store, change_repo)
    c = step(store, change_repo)
    c.outcome = None  # a stop and its recovery took the question's place
    store.write(Lock("c1"), c)
    c = step(store, change_repo)
    assert (mp.kinds(), c.outcome.exit) == (["plan", "challenge", "plan", "challenge"], Exit.ASK)
    assert [q.cause for q in c.questions if q.answer is None] == [f"{plan_rounds.DISPUTE}1 F1"] * 2


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
    assert "secret finding" not in prompts.plan_challenge(c, c.plan, Profile(), Path("/w"), {})
    assert "secret finding" in prompts.plan(c, Profile(), Path("/w"), {})


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
