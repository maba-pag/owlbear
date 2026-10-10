"""Delivery-next step loop: choose the next step and apply exits and the inbox (D3 §3.3, §3.6)."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 - pydantic resolves StepResult.wake_at at runtime
from typing import TYPE_CHECKING, Literal

from pydantic import Field

from owlbear_delivery_next import budgets, evidence
from owlbear_delivery_next.failures import DEFECT, ENVIRONMENT, kind_of
from owlbear_delivery_next.models import (
    VISUAL,
    Actor,
    Answer,
    AnswerItem,
    BriefApproval,
    CheckResult,
    ConsentItem,
    Exit,
    IntentItem,
    MergeConsent,
    Option,
    Outcome,
    Plan,
    PullItem,
    Question,
    Record,
    Recovery,
    Review,
    Score,
    Step,
    StepKind,
    Stop,
    Task,
    Waiting,
)
from owlbear_delivery_next.moves import ask, enter, go, open_task, resolved

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from owlbear_delivery_next.models import Change, InboxItem

type PrState = Literal["open", "merged", "closed"]
type Seen = tuple[PrState | None, bool]  # the PR's end state; whether a consent wait saw a comment or a new head

_FIVE = frozenset(Exit) - {Exit.PENDING}
EXITS: dict[StepKind, frozenset[Exit]] = {
    StepKind.SHAPE: frozenset(Exit) - {Exit.BACK},
    StepKind.PLAN: _FIVE,
    StepKind.BUILD: _FIVE,
    StepKind.REVIEW: _FIVE,
    StepKind.INTEGRATE: _FIVE,
    StepKind.PUBLISH: frozenset(Exit),
    StepKind.FOLLOW: frozenset(Exit),
    StepKind.CHECK: frozenset(Exit),
    StepKind.MERGE: frozenset(Exit),
    StepKind.CLEANUP: frozenset({Exit.DONE, Exit.RETRY, Exit.STOP, Exit.ASK, Exit.PENDING}),
}
BACK: dict[StepKind, frozenset[StepKind]] = {
    StepKind.PLAN: frozenset({StepKind.SHAPE}),
    StepKind.BUILD: frozenset({StepKind.PLAN, StepKind.INTEGRATE, StepKind.BUILD}),  # build: an I6 integration task
    StepKind.REVIEW: frozenset({StepKind.PLAN}),
    StepKind.INTEGRATE: frozenset({StepKind.PLAN}),
    StepKind.PUBLISH: frozenset({StepKind.INTEGRATE, StepKind.BUILD, StepKind.REVIEW}),
    StepKind.FOLLOW: frozenset({StepKind.BUILD, StepKind.PUBLISH}),  # publish: a reviewed fix not yet pushed
    StepKind.CHECK: frozenset({StepKind.BUILD}),
    StepKind.MERGE: frozenset({StepKind.INTEGRATE, StepKind.BUILD, StepKind.PUBLISH, StepKind.FOLLOW}),
}
PR_CLOSED = "gate:merge:pr-closed"
CONSENT = "gate:merge:consent"
OBSOLETE = "obsolete"  # the answer option of a consent question closed because ask-before-merge is off


class StepResult(Record):
    """What one step attempt reports to the loop; the loop records the exit."""

    exit: Exit
    cause: str | None = None
    reason: str = ""
    back_to: StepKind | None = None
    question: Question | None = None
    stop: Stop | None = None
    waiting: Waiting | None = None
    who: Actor = "delivery"
    wake_at: datetime | None = None
    plan: Plan | None = None
    review: Review | None = None
    fix_task: Task | None = None
    paths: dict[str, str] = Field(default_factory=dict)
    preserved: list[str] = Field(default_factory=list)
    denial: str | None = None
    head: str | None = None  # the pull-request head a passing CI observation was for
    score: Score | None = None  # how far a work failure got; better than the streak's best is progress


def waiting_consent(c: Change) -> bool:
    """The Change waits only for the owner's consent to merge."""
    o = c.outcome
    return bool(o and o.exit == Exit.ASK and o.cause == CONSENT)


def consent_moved(c: Change, offered: str | None, head: str, opened: Iterable[str]) -> bool:
    """While waiting for consent, an open conversation item or a head other than the offered one."""
    return waiting_consent(c) and (head != offered or any(True for _ in opened))


def open_question(c: Change) -> Question | None:
    """The question the Change waits on, if any."""
    o = c.outcome
    return next((q for q in c.questions if o and o.exit == Exit.ASK and q.id == o.question), None)


def ordinary(q: Question) -> bool:
    """A worker's question, answerable in chat; engine-raised decisions with a cause stay Changes-page actions (T6)."""
    return q.cause is None


def brief_ready(c: Change) -> bool:
    """Planning starts only from the approved current brief version its reviewer judged (J2)."""
    b = c.brief
    return b.approved_version == b.version == b.reviewed


def brief_due(c: Change) -> bool:
    """The approved current brief version still waits for its independent review."""
    b = c.brief
    return b.approved_version == b.version and b.reviewed != b.version


def brief_review(change: Change, verdict: StepResult) -> tuple[Change, StepResult]:
    """Bind the reviewer's verdict to the brief version: pass plans; findings ask the owner to revise or approve."""
    c = change.model_copy(deep=True)
    findings = verdict.exit == Exit.BACK or (verdict.exit == Exit.RETRY and verdict.cause is None)
    if verdict.exit != Exit.DONE and not findings:
        return c, verdict  # the session failed or asked: counted or answered, then reviewed again
    c.brief.reviewed = c.brief.version
    if not findings:
        return c, verdict
    text = f"Brief v{c.brief.version} review: {verdict.reason}"
    options = [
        Option(id="change", label="Revise the brief in chat", next=StepKind.SHAPE),
        Option(id="split", label="Split it into smaller Changes in chat", next=StepKind.SHAPE),
        Option(id="approve", label="Plan from this brief as it is", next="done"),
    ]
    question = Question(step=StepKind.SHAPE, text=text, options=options)
    return c, StepResult(exit=Exit.ASK, reason=text, question=question)


def overlaps(plan: Plan, others: Mapping[str, Iterable[str]]) -> dict[str, list[str]]:
    """Each other open Change whose scope shares a path or directory with the plan's task scopes (D7)."""
    mine = {p for t in plan.tasks for p in t.scope}
    found = {h: sorted({p for p in scope if any(evidence.within(p, m) for m in mine)}) for h, scope in others.items()}
    return {h: paths for h, paths in found.items() if paths}


def overlap_ask(planned: StepResult, others: Mapping[str, Iterable[str]]) -> StepResult:
    """An accepted plan that overlaps another open Change asks the owner to order them or proceed."""
    found = overlaps(planned.plan, others) if planned.exit == Exit.DONE and planned.plan else {}
    if not found:
        return planned
    named = "; ".join(f"{h} on {', '.join(p[:5])}" for h, p in sorted(found.items()))
    text = f"The plan overlaps open Changes: {named}. Proceed in parallel (conflicts are resolved when updating), or "
    text += "pause this Change until they merge?"
    options = [
        Option(id="proceed", label="Proceed in parallel", next="done"),
        Option(id="order", label="Pause this Change; resume it after they merge", next="pause"),
    ]
    question = Question(step=StepKind.PLAN, text=text, options=options)
    return planned.model_copy(update={"exit": Exit.ASK, "reason": text, "question": question})


def next_step(c: Change, now: datetime) -> Step | None:
    """Return the step a runner should run now, or None while waiting, paused or finished."""
    o = c.outcome
    if c.finished_at or (c.intent.paused_at and c.step.kind != StepKind.CLEANUP):
        return None
    if o is None or o.exit in {Exit.DONE, Exit.BACK}:
        return c.step
    if o.exit in {Exit.ASK, Exit.STOP} or o.who == "you":
        return None
    return None if o.wake_at and o.wake_at > now else c.step


def schedule(  # noqa: PLR0913 - the PR observation and the profile's consent setting
    change: Change,
    items: Iterable[InboxItem],
    now: datetime,
    pr_state: PrState | None = None,
    *,
    moved: bool = False,
    asking: bool = True,
) -> tuple[Change, Step | None]:
    """Fold the inbox, observe the PR's end and intent flags, and only then apply exclusions."""
    c = fold(change, items, now)
    if not c.finished_at and c.step.kind != StepKind.CLEANUP:
        if not asking and waiting_consent(c) and (q := open_question(c)) is not None:
            q.answer = Answer(option=OBSOLETE, text="ask before merge is off", at=now)
            c.outcome = None  # the merge gate runs again without asking
        if moved and waiting_consent(c):
            c.outcome = None  # the merge step runs again: it routes the comment or offers the moved head
        if pr_state == "merged" or c.intent.abandoned_at:
            go(c, StepKind.CLEANUP, mode=None if pr_state == "merged" else "abandon")
            c.outcome = None
        elif pr_state == "closed" and not any(q.cause == PR_CLOSED and not q.effect_observed_at for q in c.questions):
            # A closed-PR question holds until it is answered and, for reopen, the PR is observed open again.
            go(c, StepKind.MERGE)
            options = [
                Option(id="abandon", label="Abandon this Change", next="abandon"),
                Option(id="reopen", label="Reopen it and continue", next=StepKind.FOLLOW),
            ]
            ask(c, Question(step=StepKind.MERGE, text="The PR was closed", options=options, cause=PR_CLOSED), now)
        elif c.intent.hold and c.step.kind != StepKind.MERGE:
            go(c, StepKind.SHAPE)
            c.intent.hold = False
            c.outcome = None
    return c, next_step(c, now)


def fold(change: Change, items: Iterable[InboxItem], now: datetime) -> Change:  # noqa: C901, PLR0912 - per item kind
    """Apply inbox items in arrival order; a reconciled item makes the Change runnable again."""
    c = change.model_copy(deep=True)
    for item in items:
        match item:
            case BriefApproval(version=version) if version == c.brief.version:
                c.brief.approved_version, c.brief.approved_at = version, item.at
                if all(b.version != version for b in c.brief.approved):
                    c.brief.approved.append(c.brief.model_copy(deep=True, update={"approved": []}))
                if c.step.kind == StepKind.SHAPE:
                    _done(c, None, now)
                    c.outcome = None
            case AnswerItem():
                _answer(c, item, now)
            case CheckResult():  # recorded only; the host settles it by its inputs and ends the wait then
                for check in c.checks:
                    if check.id == item.check:
                        check.answer = Answer(
                            text=item.note, channel=item.channel, at=item.at, passed=item.passed, inputs=item.inputs
                        )
            case Recovery(action=action) if c.stop and c.stop.action == action:
                c.stop = c.outcome = None
            case ConsentItem():
                c.consent = MergeConsent(head=item.head, at=item.at, channel=item.channel, delta=item.delta)
                if c.outcome and c.outcome.cause == CONSENT:
                    answer = AnswerItem(
                        at=item.at, channel=item.channel, question=c.outcome.question or "", text=item.head
                    )
                    _answer(c, answer, now)
                    c.outcome = None
            case IntentItem():
                _intent(c, item)
            case PullItem():
                c.pull_requested = item.at
            case _:
                pass
    return c


def _intent(c: Change, item: IntentItem) -> None:
    match item.intent:
        case "pause":
            c.intent.paused_at, c.intent.pause_reason = item.at, item.text
        case "resume":
            c.intent.paused_at, c.intent.pause_reason = None, ""
        case "abandon":
            c.intent.abandoned_at = item.at
        case "change":
            c.intent.words, c.intent.hold = item.text, True


def _answer(c: Change, item: AnswerItem, now: datetime) -> None:
    q = next((q for q in c.questions if q.id == item.question and q.answer is None), None)
    if q is None:
        return
    q.answer = Answer(option=item.option, text=item.text, channel=item.channel, at=item.at)
    if c.outcome and c.outcome.question == q.id:
        c.outcome = None
    target = next((o.next for o in q.options if o.id == item.option), None)
    if q.cause and kind_of(q.cause) in ENVIRONMENT | DEFECT and target != "pause":
        c.budgets.causes.pop(q.cause, None)  # "Done, continue" starts a new episode or streak
    if target == "pause":
        c.intent.paused_at, c.intent.pause_reason = now, q.text
    elif target == "done":
        _done(c, None, now)
    elif target == "abandon":
        c.intent.abandoned_at = item.at
    elif target is not None:
        enter(c, StepKind(target))


def answer_delivered(change: Change, question_id: str, now: datetime) -> Change:
    """Record that a session acknowledged the answer; delivery alone resets no budget."""
    c = change.model_copy(deep=True)
    for q in c.questions:
        if q.id == question_id and q.answer is not None and q.delivered_at is None:
            q.delivered_at = now
    return c


def apply(change: Change, result: StepResult, now: datetime) -> Change:
    """Record one step attempt's exit or pending condition and move the Change on (D3 exit table).

    Raises:
        ValueError: The exit is not defined for the current step kind or lacks its record.
    """
    c = change.model_copy(deep=True)
    kind = c.step.kind
    if result.exit not in EXITS[kind]:
        msg = f"{kind} has no {result.exit} exit"
        raise ValueError(msg)
    c.outcome = Outcome(
        exit=result.exit,
        cause=result.cause,
        reason=result.reason,
        who=result.who,
        waiting=result.waiting,
        wake_at=result.wake_at,
        denial=result.denial,
        at=now,
    )
    budgets.streaks(c, result)
    match result.exit:
        case Exit.DONE:
            c.stop = None
            _done(c, result, now)
        case Exit.RETRY:
            budgets.retry(c, result, now)
        case Exit.BACK:
            if result.back_to is None or result.back_to not in BACK.get(kind, frozenset()):
                msg = f"{kind} cannot go back to {result.back_to}"
                raise ValueError(msg)
            budgets.back(c, result, now)
        case Exit.ASK if result.question:
            if kind == StepKind.PLAN and result.plan:
                c.plan = result.plan  # an accepted plan that overlaps: kept for the owner's answer
            ask(c, result.question, now)
        case Exit.STOP if result.stop:
            c.stop = result.stop
            c.outcome.who = result.stop.actor
        case Exit.PENDING if result.waiting:
            pass
        case _:
            msg = f"{result.exit} needs its question, stop or waiting condition"
            raise ValueError(msg)
    return c


def _done(c: Change, r: StepResult | None, now: datetime) -> None:  # noqa: C901, PLR0912 - one case per step kind
    s = c.step
    paths = r.paths if r else {}
    match s.kind:
        case StepKind.SHAPE | StepKind.PLAN:
            if s.kind == StepKind.SHAPE and not brief_ready(c):
                return  # the shape step reviews the approved version first
            c.budgets.rounds.pop(str(s.kind), None)
            if s.kind == StepKind.PLAN and r and r.plan:
                c.plan = r.plan
            if s.kind == StepKind.PLAN:
                evidence.cover(c)
            task = open_task(c) if s.kind == StepKind.PLAN else None
            go(c, StepKind.BUILD if s.kind == StepKind.PLAN else StepKind.PLAN, task.id if task else None)
        case StepKind.BUILD:
            go(c, StepKind.REVIEW, s.task)
        case StepKind.REVIEW:
            if r and r.review:
                c.reviews.append(r.review)
            c.budgets.rounds.pop(budgets.round_key(c), None)
            done = resolved(c, s.task)
            for t in c.plan.tasks if c.plan else []:
                t.done = t.done or t.id in done
            task = open_task(c)
            if task:
                go(c, StepKind.BUILD, task.id)
            elif s.mode == "final":
                go(c, StepKind.PUBLISH)
            else:
                go(c, StepKind.REVIEW, mode="final")
        case StepKind.INTEGRATE:
            final = next((v for v in reversed(c.reviews) if v.task is None), None)
            if final and not evidence.review_valid(c, final, paths):
                go(c, StepKind.REVIEW, mode="final")
            else:
                go(c, StepKind(s.mode or StepKind.PUBLISH), s.task)
        case StepKind.PUBLISH:
            go(c, StepKind.FOLLOW)
        case StepKind.FOLLOW | StepKind.CHECK:
            check, person = evidence.next_check(c, paths), any(p.visual for p in c.checks)
            states = evidence.need(ui=c.brief.ui, states=bool(c.brief.visual), person=person) == "states"
            if s.kind == StepKind.FOLLOW and states and not evidence.visual_valid(c, r.head if r else None):
                go(c, StepKind.CHECK, VISUAL)  # the visual check runs before person-only checks
            elif check:
                go(c, StepKind.CHECK, check.id)
            else:
                go(c, StepKind.MERGE)
        case StepKind.MERGE:
            go(c, StepKind.CLEANUP)
        case StepKind.CLEANUP:
            c.finished_at = now
            c.names.preserved += r.preserved if r else []
