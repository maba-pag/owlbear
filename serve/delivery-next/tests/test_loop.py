from datetime import UTC, datetime, timedelta

import pytest

from owlbear_delivery_next import loop
from owlbear_delivery_next.loop import StepResult
from owlbear_delivery_next.models import (
    Answer,
    AnswerItem,
    Brief,
    BriefApproval,
    Budget,
    Change,
    CheckResult,
    ConsentItem,
    Criterion,
    ErrorKind,
    Exit,
    Inputs,
    IntentItem,
    MergeConsent,
    PersonCheck,
    Plan,
    Question,
    Recovery,
    Review,
    Step,
    StepKind,
    Stop,
    Task,
    Waiting,
)

NOW = datetime(2026, 10, 10, 12, tzinfo=UTC)
LATER = NOW + timedelta(hours=1)
K = StepKind


def change(kind=K.BUILD, task="t1", mode=None, **fields) -> Change:
    return Change(
        slug="c1",
        brief=Brief(version=1, approved_version=1, criteria=[Criterion(id="AC-1", text="works")]),
        plan=Plan(tasks=[Task(id="t1", title="one", scope=["a"]), Task(id="t2", title="two", scope=["b"])]),
        step=Step(kind=kind, task=task, mode=mode),
        **fields,
    )


def result(kind: StepKind, exit_: Exit, **fields) -> StepResult:
    extra = {
        Exit.RETRY: {"cause": loop.cause_key(ErrorKind.CHECKS, kind, "test")},
        Exit.ASK: {"question": Question(step=kind, text="which key?")},
        Exit.BACK: {
            "back_to": min(loop.BACK.get(kind, {K.PLAN})),
            "cause": loop.cause_key(ErrorKind.SCOPE, kind, "x"),
            "fix_task": Task(id="f1", title="fix"),
        },
        Exit.STOP: {"stop": Stop(kind=ErrorKind.LIVENESS, reason="r", action="End process 7", resume="gone", at=NOW)},
        Exit.PENDING: {"waiting": Waiting.CI, "who": "github"},
    }.get(exit_, {})
    return StepResult(exit=exit_, **(extra | fields))


def resume_items(c: Change) -> list:
    o = c.outcome
    if o.exit == Exit.ASK:
        return [AnswerItem(at=NOW, question=o.question)]
    return [Recovery(at=NOW, action=c.stop.action)] if o.exit == Exit.STOP else []


@pytest.mark.parametrize(("kind", "exit_"), [(k, e) for k, exits in loop.EXITS.items() for e in sorted(exits)])
def test_every_defined_exit_leads_to_a_runnable_step_or_done(kind, exit_):
    c = loop.apply(change(kind), result(kind, exit_), NOW)
    c, step = loop.schedule(c, resume_items(c), LATER)
    assert c.finished_at or step == c.step


@pytest.mark.parametrize(("kind", "exit_"), [(k, e) for k in K for e in sorted(set(Exit) - loop.EXITS[k])])
def test_undefined_exits_are_refused(kind, exit_):
    with pytest.raises(ValueError, match="no"):
        loop.apply(change(kind), result(kind, exit_), NOW)


def test_back_only_to_an_allowed_step():
    with pytest.raises(ValueError, match="cannot go back"):
        loop.apply(change(K.REVIEW), result(K.REVIEW, Exit.BACK, back_to=K.BUILD), NOW)


@pytest.mark.parametrize(
    ("step", "step_result", "error"),
    [
        (Step(kind=K.BUILD, task="t1"), StepResult(exit=Exit.BACK, back_to=K.PLAN), "back needs a cause"),
        (Step(kind=K.REVIEW, mode="final"), StepResult(exit=Exit.RETRY, reason="naming"), "fix_task: empty"),
    ],
)
def test_results_without_their_required_record_are_invalid(step, step_result, error):
    with pytest.raises(ValueError, match=error):
        loop.apply(change().model_copy(update={"step": step}), step_result, NOW)


def test_final_findings_build_their_authored_repair_task():
    fix = StepResult(exit=Exit.RETRY, fix_task=Task(id="f1", title="fix", origin="review"))
    c = loop.apply(change(K.REVIEW, None, "final"), fix, NOW)
    assert (c.step.kind, c.step.task, c.plan.tasks[-1].id) == (K.BUILD, "f1", "f1")


def test_walk_from_brief_approval_to_done():
    checks = [PersonCheck(id="p1", criteria=["AC-1"], paths=["ui"])]
    c = change(K.SHAPE, None, checks=checks).model_copy(update={"plan": None})
    c.brief.approved_version = None
    c, step = loop.schedule(c, [BriefApproval(at=NOW, version=1)], NOW)
    assert (step.kind, c.brief.approved[0].version, c.brief.approved[0].criteria) == (K.PLAN, 1, c.brief.criteria)
    review = Review(commit="abc", inputs=Inputs(criteria={"AC-1": 1}), verdict="pass")
    walk = [
        (StepResult(exit=Exit.DONE, plan=change().plan), (K.BUILD, "t1", None)),
        (StepResult(exit=Exit.DONE), (K.REVIEW, "t1", None)),
        (StepResult(exit=Exit.DONE, review=review), (K.BUILD, "t2", None)),
        (StepResult(exit=Exit.DONE), (K.REVIEW, "t2", None)),
        (StepResult(exit=Exit.DONE, review=review), (K.REVIEW, None, "final")),
        (StepResult(exit=Exit.DONE, review=review), (K.PUBLISH, None, None)),
        (StepResult(exit=Exit.DONE), (K.FOLLOW, None, None)),
        (StepResult(exit=Exit.DONE, paths={"ui": "f1"}), (K.CHECK, "p1", None)),
    ]
    for step_result, expected in walk:
        c = loop.apply(c, step_result, NOW)
        assert (c.step.kind, c.step.task, c.step.mode) == expected
    c = loop.apply(c, StepResult(exit=Exit.PENDING, waiting=Waiting.PERSON_CHECK, who="you"), NOW)
    assert loop.next_step(c, LATER) is None
    inputs = loop.check_inputs(c, c.checks[0], {"ui": "f1"})
    c, step = loop.schedule(c, [CheckResult(at=NOW, check="p1", passed=True, inputs=inputs)], NOW)
    assert step.kind == K.CHECK
    c = loop.apply(c, StepResult(exit=Exit.DONE, paths={"ui": "f1"}), NOW)
    assert c.step.kind == K.MERGE
    c = loop.apply(loop.apply(c, StepResult(exit=Exit.DONE), NOW), StepResult(exit=Exit.DONE, preserved=["x"]), NOW)
    assert c.finished_at == NOW
    assert c.names.preserved == ["x"]
    assert loop.next_step(c, LATER) is None


def test_cause_count_survives_retry_back_replan_and_an_unobserved_answer():
    cause = loop.cause_key(ErrorKind.PROJECT_ENV, K.BUILD, "TEST_API_KEY")
    c = change()
    for exit_, extra in [(Exit.RETRY, {}), (Exit.RETRY, {}), (Exit.BACK, {"back_to": K.PLAN})]:
        c = loop.apply(c, StepResult(exit=exit_, cause=cause, **extra), NOW)
    assert c.step.kind == K.PLAN
    c = loop.apply(c, StepResult(exit=Exit.DONE, plan=Plan(version=2, tasks=[Task(id="t9", title="x")])), NOW)
    assert c.step.task == "t9"
    c = loop.apply(c, StepResult(exit=Exit.RETRY, cause=cause), NOW)
    assert c.outcome.exit == Exit.ASK
    assert [o.id for o in c.questions[-1].options] == ["revise", "narrow", "pause"]
    c, step = loop.schedule(c, [AnswerItem(at=NOW, question=c.outcome.question, option="narrow")], NOW)
    assert step.kind == K.PLAN
    assert c.budgets.causes[cause].count == 4
    assert cause not in loop.effect_observed(c, c.questions[-1].id, NOW).budgets.causes


def test_effect_observation_clears_a_cause_once_per_answer():
    q = Question(id="q1", step=K.BUILD, text="key?", cause="c", answer=Answer(at=NOW))
    c = change(questions=[q])
    c.budgets.causes["c"] = Budget(count=3)
    c = loop.effect_observed(c, "q1", NOW)
    c.budgets.causes["c"] = Budget(count=1)
    assert loop.effect_observed(c, "q1", LATER).budgets.causes["c"].count == 1


def _profile(c):
    c.profile_version += 1


def _brief(c):
    c.brief.approved_version = 2


def _scope(c):
    c.plan.tasks[0].scope = ["z"]


def _other_task(c):
    c.step = Step(kind=K.BUILD, task="t2")


@pytest.mark.parametrize(
    ("kind", "step", "premise_change", "count"),
    [
        (ErrorKind.PROJECT_ENV, K.BUILD, _profile, 1),
        (ErrorKind.CHECKS, K.BUILD, _profile, 2),
        (ErrorKind.CHECKS, K.PLAN, _brief, 1),
        (ErrorKind.CHECKS, K.BUILD, _scope, 1),
        (ErrorKind.CHECKS, K.BUILD, _other_task, 2),
        (ErrorKind.CHECKS, K.BUILD, lambda _: None, 2),
    ],
)
def test_count_resets_only_when_its_premise_changes(kind, step, premise_change, count):
    cause = loop.cause_key(kind, step, "x")
    c = loop.apply(change(step), StepResult(exit=Exit.RETRY, cause=cause), NOW)
    premise_change(c)
    c = loop.apply(c, StepResult(exit=Exit.RETRY, cause=cause), NOW)
    assert c.budgets.causes[cause].count == count


def test_recovery_resets_network_counts_only():
    c = change()
    for kind in (ErrorKind.NETWORK, ErrorKind.CHECKS):
        c = loop.apply(c, StepResult(exit=Exit.RETRY, cause=loop.cause_key(kind, K.BUILD)), NOW)
    assert list(loop.recovered(c, ErrorKind.NETWORK).budgets.causes) == ["checks:build:"]


def test_third_round_of_findings_asks_and_accepting_moves_on():
    c = change(K.REVIEW)
    for _ in range(2):
        c = loop.apply(c, StepResult(exit=Exit.RETRY, reason="naming"), NOW)
        assert (c.step.kind, c.step.task) == (K.BUILD, "t1")
        c = loop.apply(c, StepResult(exit=Exit.DONE), NOW)
    c = loop.apply(c, StepResult(exit=Exit.RETRY, reason="naming"), NOW)
    assert c.outcome.exit == Exit.ASK
    c, step = loop.schedule(c, [AnswerItem(at=NOW, question=c.outcome.question, option="accept")], NOW)
    assert (step.kind, step.task) == (K.BUILD, "t2")


def test_renamed_task_with_the_same_scope_keeps_its_review_rounds():
    c = change(K.REVIEW)
    for task in ("t1", "t1b", "t1c"):
        c.plan.tasks[0].id = task
        c.step = Step(kind=K.REVIEW, task=task)
        c = loop.apply(c, StepResult(exit=Exit.RETRY, reason="naming"), NOW)
    assert c.outcome.exit == Exit.ASK


def test_fourth_replan_asks():
    c = change()
    c.budgets.replans = loop.REPLAN_LIMIT
    c = loop.apply(c, StepResult(exit=Exit.BACK, back_to=K.PLAN, cause="scope:build:x"), NOW)
    assert (c.step.kind, c.outcome.exit) == (K.BUILD, Exit.ASK)


def _asked(c):
    return loop.apply(c, result(K.BUILD, Exit.ASK), NOW), AnswerItem(at=NOW, question="q1")


def _stopped(c):
    return loop.apply(c, result(K.BUILD, Exit.STOP), NOW), Recovery(at=NOW, action="End process 7")


def _paused(c):
    c.intent.paused_at = NOW
    return c, IntentItem(at=NOW, intent="resume")


def _check_pending(c):
    pending = result(K.CHECK, Exit.PENDING, waiting=Waiting.PERSON_CHECK, who="you")
    c = loop.apply(c.model_copy(update={"step": Step(kind=K.CHECK, task="p1")}), pending, NOW)
    return c, CheckResult(at=NOW, check="p1", passed=True, inputs=Inputs())


def _consent_asked(c):
    asked = StepResult(exit=Exit.ASK, question=Question(step=K.MERGE, text="approve abc", cause=loop.CONSENT))
    return loop.apply(c.model_copy(update={"step": Step(kind=K.MERGE)}), asked, NOW), ConsentItem(at=NOW, head="abc")


@pytest.mark.parametrize("wait", [_asked, _stopped, _paused, _check_pending, _consent_asked])
def test_inbox_is_folded_before_exclusions(wait):
    c, item = wait(change(checks=[PersonCheck(id="p1")]))
    assert loop.schedule(c, [], NOW)[1] is None
    c, step = loop.schedule(c, [item], NOW)
    assert step == c.step


@pytest.mark.parametrize(
    ("wait", "item"),
    [
        (_asked, CheckResult(at=NOW, check="p1", passed=True, inputs=Inputs())),
        (_asked, ConsentItem(at=NOW, head="abc")),
        (_check_pending, CheckResult(at=NOW, check="p2", passed=True, inputs=Inputs())),
        (_check_pending, ConsentItem(at=NOW, head="abc")),
        (_consent_asked, AnswerItem(at=NOW, question="q9")),
    ],
)
def test_unrelated_items_leave_a_wait_in_place(wait, item):
    c, _ = wait(change(checks=[PersonCheck(id="p1"), PersonCheck(id="p2")]))
    assert loop.schedule(c, [item], NOW)[1] is None


def test_merged_pr_reaches_cleanup_while_paused_and_waiting():
    c, _ = _asked(change())
    c.intent.paused_at = NOW
    assert loop.schedule(c, [], NOW, "merged")[1].kind == K.CLEANUP


def test_closed_pr_asks_once():
    c, step = loop.schedule(change(), [], NOW, "closed")
    c, step = loop.schedule(c, [], NOW, "closed")
    assert (step, c.step.kind, len(c.questions)) == (None, K.MERGE, 1)


def test_closed_pr_reopen_runs_before_the_pr_is_judged_again():
    c, _ = loop.schedule(change(), [], NOW, "closed")
    c, step = loop.schedule(c, [AnswerItem(at=NOW, question="q1", option="reopen")], NOW, "closed")
    assert (step.kind, len(c.questions)) == (K.FOLLOW, 1)
    c, step = loop.schedule(loop.apply(c, StepResult(exit=Exit.DONE), NOW), [], NOW, "closed")
    assert (step, len(c.questions)) == (None, 2)


def test_closed_pr_abandon_cleans_up_as_abandoned():
    c, _ = loop.schedule(change(), [], NOW, "closed")
    c, step = loop.schedule(c, [AnswerItem(at=NOW, question="q1", option="abandon")], NOW, "closed")
    assert (step.kind, step.mode) == (K.CLEANUP, "abandon")
    c = loop.apply(c, StepResult(exit=Exit.DONE), NOW)
    assert (c.finished_at, c.intent.abandoned_at) == (NOW, NOW)


def test_next_check_needs_a_passing_answer_on_unchanged_inputs():
    c = change(checks=[PersonCheck(id="p1", criteria=["AC-1"], paths=["a"]), PersonCheck(id="p2", paths=["b"])])
    paths = {"a": "1", "b": "1"}

    def answer(c, check_id, passed):
        check = next(k for k in c.checks if k.id == check_id)
        item = CheckResult(at=NOW, check=check_id, passed=passed, inputs=loop.check_inputs(c, check, paths))
        return loop.fold(c, [item], NOW)

    c = answer(c, "p1", passed=True)
    assert loop.next_check(c, paths).id == "p2"
    c = answer(c, "p2", passed=False)
    assert loop.next_check(c, paths).id == "p2"
    c = answer(c, "p2", passed=True)
    assert loop.next_check(c, paths) is None
    assert loop.next_check(c, paths | {"a": "2"}).id == "p1"
    c.brief.criteria[0].version = 2
    assert loop.next_check(c, paths).id == "p1"


@pytest.mark.parametrize(
    ("paths", "criterion_version", "next_kind"),
    [
        ({"a": "1"}, 1, K.PUBLISH),
        ({"a": "1", "z": "9"}, 1, K.PUBLISH),
        ({"a": "2"}, 1, K.REVIEW),
        ({}, 1, K.REVIEW),
        ({"a": "1"}, 2, K.REVIEW),
    ],
)
def test_integration_rereviews_only_when_a_recorded_input_changed(paths, criterion_version, next_kind):
    c = change(K.INTEGRATE, None, "publish")
    c.reviews = [Review(commit="abc", inputs=Inputs(criteria={"AC-1": 1}, paths={"a": "1"}), verdict="pass")]
    c.brief.criteria[0].version = criterion_version
    assert loop.apply(c, StepResult(exit=Exit.DONE, paths=paths), NOW).step.kind == next_kind


def test_merge_consent_is_void_for_another_head():
    c = change(consent=MergeConsent(head="a1c3f02", at=NOW))
    assert loop.consent_valid(c, "a1c3f02")
    assert not loop.consent_valid(c, "b7e2a91")
