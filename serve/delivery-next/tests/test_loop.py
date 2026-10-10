from datetime import UTC, datetime, timedelta

import pytest

from owlbear_delivery_next import budgets, evidence, failures, loop
from owlbear_delivery_next.github import merge_offer
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
    Outcome,
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
        Exit.RETRY: {"cause": failures.cause_key(ErrorKind.CHECKS, kind, "test")},
        Exit.ASK: {"question": Question(step=kind, text="which key?")},
        Exit.BACK: {
            "back_to": min(loop.BACK.get(kind, {K.PLAN})),
            "cause": failures.cause_key(ErrorKind.SCOPE, kind, "x"),
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


def test_a_task_whose_findings_were_fixed_is_not_built_again():
    c = change(K.REVIEW)
    for task in ("f1", "f2"):  # findings on t1, then on its fix f1
        c = loop.apply(c, StepResult(exit=Exit.RETRY, fix_task=Task(id=task, title="fix", origin="review")), NOW)
        c = loop.apply(c, StepResult(exit=Exit.DONE), NOW)
    c = loop.apply(c, StepResult(exit=Exit.DONE), NOW)
    assert (c.step.kind, c.step.task) == (K.BUILD, "t2")
    assert [t.done for t in c.plan.tasks] == [True, False, True, True]


def test_walk_from_brief_approval_to_done():
    checks = [PersonCheck(id="p1", criteria=["AC-1"], paths=["ui"])]
    c = change(K.SHAPE, None, checks=checks).model_copy(update={"plan": None})
    c.brief.approved_version = None
    c, step = loop.schedule(c, [BriefApproval(at=NOW, version=1)], NOW)
    assert (step.kind, c.brief.approved[0].version, c.brief.approved[0].criteria) == (K.SHAPE, 1, c.brief.criteria)
    c = loop.apply(*loop.brief_review(c, StepResult(exit=Exit.DONE, reason="review passed")), NOW)
    assert (c.step.kind, c.brief.reviewed) == (K.PLAN, 1)
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
    inputs = evidence.check_inputs(c, c.checks[0], {"ui": "f1"})
    c, step = loop.schedule(c, [CheckResult(at=NOW, check="p1", passed=True, inputs=inputs)], NOW)
    assert step is None  # recorded; the host settles it and ends the wait
    assert c.checks[0].answer.inputs == inputs
    c = loop.apply(c, StepResult(exit=Exit.DONE, paths={"ui": "f1"}), NOW)
    assert c.step.kind == K.MERGE
    c = loop.apply(loop.apply(c, StepResult(exit=Exit.DONE), NOW), StepResult(exit=Exit.DONE, preserved=["x"]), NOW)
    assert c.finished_at == NOW
    assert c.names.preserved == ["x"]
    assert loop.next_step(c, LATER) is None


def test_brief_review_binds_the_version_and_findings_return_to_the_owner():
    c = change(K.SHAPE, None).model_copy(update={"plan": None})
    c.brief.approved_version = None
    c, _ = loop.schedule(c, [BriefApproval(at=NOW, version=1)], NOW)
    assert (c.step.kind, loop.brief_due(c)) == (K.SHAPE, True)
    failed = StepResult(exit=Exit.RETRY, cause=failures.cause_key(ErrorKind.TOOLING, K.REVIEW, "sdk"))
    assert loop.brief_review(c, failed) == (c, failed)  # a failed session judged nothing
    c, asked = loop.brief_review(c, StepResult(exit=Exit.RETRY, reason="AC-1: cannot be checked"))
    c = loop.apply(c, asked, NOW)
    q = loop.open_question(c)
    assert (c.brief.reviewed, c.step.kind, [o.id for o in q.options]) == (1, K.SHAPE, ["change", "split", "approve"])
    assert (loop.ordinary(q), "AC-1: cannot be checked" in q.text) == (True, True)
    revised, step = loop.schedule(c, [AnswerItem(at=NOW, question=q.id, option="change")], NOW)
    assert (step.kind, loop.brief_due(revised)) == (K.SHAPE, False)  # the runner waits for the chat
    revised.brief.version = 2
    revised, _ = loop.schedule(revised, [BriefApproval(at=NOW, version=2)], NOW)
    assert (revised.step.kind, loop.brief_due(revised)) == (K.SHAPE, True)
    _, step = loop.schedule(c, [AnswerItem(at=NOW, question=q.id, option="approve")], NOW)
    assert step.kind == K.PLAN


def test_an_accepted_plan_overlapping_another_open_change_asks_to_order_or_proceed():
    plan = Plan(tasks=[Task(id="t1", title="one", scope=["packages/app/src"])])
    others = {"c2": ["packages/app"], "c3": ["packages/web"], "c4": ["."]}
    assert loop.overlaps(plan, others) == {"c2": ["packages/app"], "c4": ["."]}
    done = StepResult(exit=Exit.DONE, plan=plan)
    assert loop.overlap_ask(done, {"c3": ["packages/web"]}) is done
    c = loop.apply(change(K.PLAN, None).model_copy(update={"plan": None}), loop.overlap_ask(done, others), NOW)
    q = loop.open_question(c)
    assert ([o.id for o in q.options], c.plan, "c2 on packages/app" in q.text) == (["proceed", "order"], plan, True)
    _, step = loop.schedule(c, [AnswerItem(at=NOW, question=q.id, option="proceed")], NOW)
    assert (step.kind, step.task) == (K.BUILD, "t1")
    paused, step = loop.schedule(c, [AnswerItem(at=NOW, question=q.id, option="order")], NOW)
    assert (step, paused.intent.paused_at) == (None, NOW)


def test_cause_count_survives_retry_back_replan_and_an_unobserved_answer():
    cause = failures.cause_key(ErrorKind.PROJECT_ENV, K.BUILD, "TEST_API_KEY")
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
    assert cause not in budgets.effect_observed(c, c.questions[-1].id, NOW).budgets.causes


def test_effect_observation_clears_a_cause_once_per_answer_and_delivery_alone_clears_nothing():
    q = Question(id="q1", step=K.BUILD, text="key?", cause="c", answer=Answer(at=NOW))
    c = change(questions=[q])
    c.budgets.causes["c"] = Budget(count=3)
    c = loop.answer_delivered(c, "q1", NOW)
    assert (c.questions[0].delivered_at, c.questions[0].effect_observed_at, c.budgets.causes["c"].count) == (
        NOW,
        None,
        3,
    )
    assert loop.answer_delivered(c, "q1", LATER).questions[0].delivered_at == NOW
    c = budgets.effect_observed(c, "q1", NOW)
    c.budgets.causes["c"] = Budget(count=1)
    assert budgets.effect_observed(c, "q1", LATER).budgets.causes["c"].count == 1


def test_a_charged_cause_reports_exhaustion_after_the_retry_limit():
    c, within = change(), []
    for _ in range(budgets.RETRY_LIMIT + 1):
        c, ok = budgets.charge(c, "state:build:session-missing", NOW)
        within.append(ok)
    assert within == [True] * budgets.RETRY_LIMIT + [False]


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
    cause = failures.cause_key(kind, step, "x")
    c = loop.apply(change(step), StepResult(exit=Exit.RETRY, cause=cause), NOW)
    premise_change(c)
    c = loop.apply(c, StepResult(exit=Exit.RETRY, cause=cause), NOW)
    assert c.budgets.causes[cause].count == count


def test_recovery_resets_network_counts_only():
    c = change()
    for kind in (ErrorKind.NETWORK, ErrorKind.CHECKS):
        c = loop.apply(c, StepResult(exit=Exit.RETRY, cause=failures.cause_key(kind, K.BUILD)), NOW)
    assert list(budgets.recovered(c, ErrorKind.NETWORK).budgets.causes) == ["checks:build:"]


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
    c.budgets.replans = budgets.REPLAN_LIMIT
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


@pytest.mark.parametrize("wait", [_asked, _stopped, _paused, _consent_asked])
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
        (_check_pending, CheckResult(at=NOW, check="p1", passed=True, inputs=Inputs())),
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


def test_closed_pr_reopen_holds_until_the_pr_is_seen_open_again():
    c, _ = loop.schedule(change(), [], NOW, "closed")
    c, step = loop.schedule(c, [AnswerItem(at=NOW, question="q1", option="reopen")], NOW, "closed")
    assert (step.kind, len(c.questions)) == (K.FOLLOW, 1)
    c, _ = loop.schedule(loop.apply(c, StepResult(exit=Exit.DONE), NOW), [], NOW, "closed")
    assert len(c.questions) == 1
    c, step = loop.schedule(budgets.effect_observed(c, "q1", NOW), [], NOW, "closed")
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
        item = CheckResult(at=NOW, check=check_id, passed=passed, inputs=evidence.check_inputs(c, check, paths))
        return loop.fold(c, [item], NOW)

    c = answer(c, "p1", passed=True)
    assert evidence.next_check(c, paths).id == "p2"
    c = answer(c, "p2", passed=False)
    assert evidence.next_check(c, paths).id == "p2"
    c = answer(c, "p2", passed=True)
    assert evidence.next_check(c, paths) is None
    assert evidence.next_check(c, paths | {"a": "2"}).id == "p1"
    c.brief.criteria[0].version = 2
    assert evidence.next_check(c, paths).id == "p1"


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
    assert merge_offer.consent(c.consent.head, "a1c3f02") == "valid"
    assert merge_offer.consent(c.consent.head, "b7e2a91") == "void"


def test_an_open_consent_question_is_closed_as_obsolete_when_ask_before_merge_is_off():
    c = change(K.MERGE, None, "publish")
    q = Question(step=K.MERGE, text="approve merging abc", cause=loop.CONSENT)
    c.questions = [q]
    c.outcome = Outcome(exit=Exit.ASK, question=q.id, cause=loop.CONSENT, at=NOW)
    asked, _ = loop.schedule(c.model_copy(deep=True), [], NOW)
    assert (asked.outcome is None, asked.questions[0].answer) == (False, None)
    closed, step = loop.schedule(c, [], NOW, asking=False)
    assert (closed.outcome, closed.questions[0].answer.option, step.kind) == (None, loop.OBSOLETE, K.MERGE)


@pytest.mark.parametrize(
    ("head", "opened", "moved"),
    [("abc", [], False), ("abc", ["7"], True), ("def", [], True)],
)
def test_a_consent_wait_reruns_merge_for_an_open_item_or_head(head, opened, moved):
    c, _ = _consent_asked(change())
    assert loop.consent_moved(c, "abc", head, opened) is moved
    assert not loop.consent_moved(change(K.MERGE), "abc", head, opened)
    assert loop.schedule(c, [], NOW, "open", moved=moved)[1] == (c.step if moved else None)
