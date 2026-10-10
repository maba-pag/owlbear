"""Delivery-next step loop: choose the next step and apply exits, budgets and the inbox (D3 §3.3, §3.6)."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 - pydantic resolves StepResult fields at runtime
from typing import TYPE_CHECKING, Literal

from pydantic import Field

from owlbear_delivery_next.models import (
    Actor,
    Answer,
    AnswerItem,
    BriefApproval,
    Budget,
    CheckResult,
    ConsentItem,
    ErrorKind,
    Exit,
    Inputs,
    IntentItem,
    MergeConsent,
    Option,
    Outcome,
    Plan,
    Question,
    Record,
    Recovery,
    Review,
    Step,
    StepKind,
    Stop,
    Task,
    Waiting,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from owlbear_delivery_next.models import Change, InboxItem, PersonCheck

type PrState = Literal["open", "merged", "closed"]

RETRY_LIMIT = 3
FLAKE_LIMIT = 1
ROUND_LIMIT = 2
REPLAN_LIMIT = 3

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
    StepKind.CLEANUP: frozenset({Exit.DONE, Exit.RETRY, Exit.STOP}),
}
BACK: dict[StepKind, frozenset[StepKind]] = {
    StepKind.PLAN: frozenset({StepKind.SHAPE}),
    StepKind.BUILD: frozenset({StepKind.PLAN, StepKind.INTEGRATE}),
    StepKind.REVIEW: frozenset({StepKind.PLAN}),
    StepKind.INTEGRATE: frozenset({StepKind.PLAN}),
    StepKind.PUBLISH: frozenset({StepKind.INTEGRATE, StepKind.BUILD}),
    StepKind.FOLLOW: frozenset({StepKind.BUILD}),
    StepKind.CHECK: frozenset({StepKind.BUILD}),
    StepKind.MERGE: frozenset({StepKind.INTEGRATE, StepKind.BUILD}),
}
_PR_CLOSED = "gate:merge:pr-closed"


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


def cause_key(kind: ErrorKind, step: StepKind, subject: str | Iterable[str] = "") -> str:
    """Return ``kind:step:subject``; the task id is never part of it, so a cause survives re-planning."""
    text = subject if isinstance(subject, str) else ",".join(sorted(subject))
    return f"{kind}:{step}:{text}"


def inputs_valid(recorded: Inputs, current: Inputs) -> bool:
    """A review or check answer stays valid while every input it recorded is unchanged (P5)."""
    return (
        all(current.criteria.get(k) == v for k, v in recorded.criteria.items())
        and all(current.paths.get(p) == f for p, f in recorded.paths.items())
        and (recorded.procedure, recorded.environment) == (current.procedure, current.environment)
    )


def _criteria(c: Change) -> dict[str, int]:
    return {k.id: k.version for k in c.brief.criteria}


def review_valid(c: Change, review: Review, paths: Mapping[str, str]) -> bool:
    """Return whether a passing review still holds for the observed path fingerprints."""
    return review.verdict == "pass" and inputs_valid(review.inputs, Inputs(criteria=_criteria(c), paths=dict(paths)))


def check_inputs(c: Change, check: PersonCheck, paths: Mapping[str, str]) -> Inputs:
    """Return the current inputs of one person-only check from the brief and observed paths."""
    crit = _criteria(c)
    return Inputs(
        criteria={k: crit[k] for k in check.criteria if k in crit},
        paths={p: paths[p] for p in check.paths if p in paths},
        procedure=check.procedure,
        environment=check.environment,
    )


def next_check(c: Change, paths: Mapping[str, str]) -> PersonCheck | None:
    """Return the first declared person-only check without a valid passing answer."""
    for check in c.checks:
        answer = check.answer
        if not (answer and answer.passed and answer.inputs):
            return check
        if not inputs_valid(answer.inputs, check_inputs(c, check, paths)):
            return check
    return None


def consent_valid(c: Change, head: str) -> bool:
    """Merge consent holds only for the exact head it names."""
    return c.consent is not None and c.consent.head == head


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


def schedule(
    change: Change, items: Iterable[InboxItem], now: datetime, pr_state: PrState | None = None
) -> tuple[Change, Step | None]:
    """Fold the inbox, observe the PR's end and intent flags, and only then apply exclusions."""
    c = fold(change, items, now)
    if not c.finished_at and c.step.kind != StepKind.CLEANUP:
        if pr_state == "merged" or c.intent.abandoned_at:
            _go(c, StepKind.CLEANUP, mode=None if pr_state == "merged" else "abandon")
            c.outcome = None
        elif pr_state == "closed" and not any(q.cause == _PR_CLOSED and q.answer is None for q in c.questions):
            _go(c, StepKind.MERGE)
            options = [
                Option(id="abandon", label="Abandon this Change", next=StepKind.CLEANUP),
                Option(id="reopen", label="Reopen it and continue", next=StepKind.FOLLOW),
            ]
            _ask(c, Question(step=StepKind.MERGE, text="The PR was closed", options=options, cause=_PR_CLOSED), now)
        elif c.intent.hold and c.step.kind != StepKind.MERGE:
            _go(c, StepKind.SHAPE)
            c.intent.hold = False
            c.outcome = None
    return c, next_step(c, now)


def fold(change: Change, items: Iterable[InboxItem], now: datetime) -> Change:  # noqa: C901 - one case per item kind
    """Apply inbox items in arrival order; a reconciled item makes the Change runnable again."""
    c = change.model_copy(deep=True)
    for item in items:
        match item:
            case BriefApproval(version=version) if version == c.brief.version:
                c.brief.approved_version, c.brief.approved_at = version, item.at
                if c.step.kind == StepKind.SHAPE:
                    _done(c, None, now)
                    c.outcome = None
            case AnswerItem():
                _answer(c, item, now)
            case CheckResult():
                for check in c.checks:
                    if check.id == item.check:
                        check.answer = Answer(
                            text=item.note, channel=item.channel, at=item.at, passed=item.passed, inputs=item.inputs
                        )
                        _wake(c)
            case Recovery(action=action) if c.stop and c.stop.action == action:
                c.stop = c.outcome = None
            case ConsentItem():
                c.consent = MergeConsent(head=item.head, at=item.at, channel=item.channel, delta=item.delta)
                _wake(c)
            case IntentItem():
                _intent(c, item)
            case _:
                pass
    return c


def _wake(c: Change) -> None:
    if c.outcome and c.outcome.who == "you" and c.outcome.exit != Exit.STOP:
        c.outcome = None


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
    if target == "pause":
        c.intent.paused_at, c.intent.pause_reason = now, q.text
    elif target == "done":
        _done(c, None, now)
    elif target is not None:
        _enter(c, StepKind(target))


def effect_observed(change: Change, question_id: str, now: datetime) -> Change:
    """Record that an answer's effect was observed; only then does its cause's count reset."""
    c = change.model_copy(deep=True)
    for q in c.questions:
        if q.id == question_id and q.answer is not None:
            q.effect_observed_at = now
            if q.cause:
                c.budgets.causes.pop(q.cause, None)
    return c


def recovered(change: Change, kind: ErrorKind) -> Change:
    """Observed recovery (network, capacity) resets every count of that error kind."""
    c = change.model_copy(deep=True)
    c.budgets.causes = {k: b for k, b in c.budgets.causes.items() if not k.startswith(f"{kind}:")}
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
    match result.exit:
        case Exit.DONE:
            c.stop = None
            _done(c, result, now)
        case Exit.RETRY:
            _retry(c, result, now)
        case Exit.BACK:
            _back(c, result, now)
        case Exit.ASK if result.question:
            _ask(c, result.question, now)
        case Exit.STOP if result.stop:
            c.stop = result.stop
            c.outcome.who = result.stop.actor
        case Exit.PENDING if result.waiting:
            pass
        case _:
            msg = f"{result.exit} needs its question, stop or waiting condition"
            raise ValueError(msg)
    return c


def _go(c: Change, kind: StepKind, task: str | None = None, mode: str | None = None) -> None:
    c.step = Step(kind=kind, task=task, mode=mode)


def _enter(c: Change, kind: StepKind, task: str | None = None) -> None:
    s = c.step
    keep = task or (s.task if kind in {StepKind.BUILD, StepKind.INTEGRATE} else None)
    caller = s.mode if s.kind == StepKind.INTEGRATE else str(s.kind)
    _go(c, kind, keep, caller if kind == StepKind.INTEGRATE else None)


def _open_task(c: Change) -> Task | None:
    return next((t for t in c.plan.tasks if not t.done), None) if c.plan else None


def _ask(c: Change, question: Question, now: datetime) -> None:
    q = question.model_copy(update={"id": f"q{len(c.questions) + 1}", "step": c.step.kind})
    c.questions.append(q)
    c.outcome = Outcome(exit=Exit.ASK, cause=q.cause, reason=q.text, who="you", question=q.id, at=now)


def _done(c: Change, r: StepResult | None, now: datetime) -> None:  # noqa: C901, PLR0912 - one case per step kind
    s = c.step
    paths = r.paths if r else {}
    match s.kind:
        case StepKind.SHAPE | StepKind.PLAN:
            c.budgets.rounds.pop(str(s.kind), None)
            if s.kind == StepKind.PLAN and r and r.plan:
                c.plan = r.plan
            task = _open_task(c) if s.kind == StepKind.PLAN else None
            _go(c, StepKind.BUILD if s.kind == StepKind.PLAN else StepKind.PLAN, task.id if task else None)
        case StepKind.BUILD:
            _go(c, StepKind.REVIEW, s.task)
        case StepKind.REVIEW:
            if r and r.review:
                c.reviews.append(r.review)
            c.budgets.rounds.pop(s.task or "final", None)
            for t in c.plan.tasks if c.plan else []:
                t.done = t.done or t.id == s.task
            task = _open_task(c)
            if task:
                _go(c, StepKind.BUILD, task.id)
            elif s.mode == "final":
                _go(c, StepKind.PUBLISH)
            else:
                _go(c, StepKind.REVIEW, mode="final")
        case StepKind.INTEGRATE:
            final = next((v for v in reversed(c.reviews) if v.task is None), None)
            if final and not review_valid(c, final, paths):
                _go(c, StepKind.REVIEW, mode="final")
            else:
                _go(c, StepKind(s.mode or StepKind.PUBLISH), s.task)
        case StepKind.PUBLISH:
            _go(c, StepKind.FOLLOW)
        case StepKind.FOLLOW | StepKind.CHECK:
            check = next_check(c, paths)
            if check:
                _go(c, StepKind.CHECK, check.id)
            else:
                _go(c, StepKind.MERGE)
        case StepKind.MERGE:
            _go(c, StepKind.CLEANUP)
        case StepKind.CLEANUP:
            c.finished_at = now
            c.names.preserved += r.preserved if r else []


def _premise(c: Change, cause: str, task_id: str | None) -> str | None:
    kind, step, _ = cause.split(":", 2)
    if kind == ErrorKind.PROJECT_ENV:
        return f"profile:{c.profile_version}"
    if step in {StepKind.SHAPE, StepKind.PLAN} or kind == ErrorKind.REVIEW:
        return f"brief:{c.brief.approved_version}"
    task = next((t for t in c.plan.tasks if t.id == task_id), None) if c.plan else None
    return "scope:" + ",".join(sorted(task.scope)) if task else None


def _count(c: Change, cause: str, now: datetime) -> int:
    budget = c.budgets.causes.get(cause)
    if budget is None or _premise(c, cause, budget.task) not in {None, budget.premise}:
        budget = Budget()
    task = c.step.task
    premise = _premise(c, cause, task) or budget.premise
    c.budgets.causes[cause] = Budget(count=budget.count + 1, premise=premise, task=task, at=now)
    return budget.count + 1


def _exhausted(c: Change, r: StepResult, now: datetime) -> None:
    cause = r.cause or ""
    if c.step.kind == StepKind.CLEANUP:
        c.stop = Stop(
            kind=ErrorKind(cause.split(":")[0]),
            reason=r.reason,
            action=f"Resolve {cause}",
            resume="Cleanup succeeds",
            at=now,
        )
        c.outcome = Outcome(exit=Exit.STOP, cause=cause, reason=r.reason, who="you", at=now)
        return
    options = [
        Option(id="revise", label="Revise the requirement", next=StepKind.SHAPE),
        Option(id="narrow", label="Narrow the scope", next=StepKind.PLAN),
        Option(id="pause", label="Pause this Change", next="pause"),
    ]
    _ask(c, Question(step=c.step.kind, text=f"{r.reason} keeps failing ({cause})", options=options, cause=cause), now)


def _fix_task(c: Change, r: StepResult) -> str | None:
    if r.fix_task is None or c.plan is None:
        return None
    c.plan.tasks.append(r.fix_task)
    return r.fix_task.id


def _retry(c: Change, r: StepResult, now: datetime) -> None:
    s = c.step
    if r.cause is None:
        if s.kind not in {StepKind.SHAPE, StepKind.PLAN, StepKind.REVIEW}:
            msg = f"{s.kind} retry needs a cause"
            raise ValueError(msg)
        key = s.task or s.mode or str(s.kind)
        c.budgets.rounds[key] = c.budgets.rounds.get(key, 0) + 1
        if c.budgets.rounds[key] > ROUND_LIMIT:
            fix = StepKind.BUILD if s.kind == StepKind.REVIEW else s.kind
            options = [
                Option(id="fix", label="Fix the findings", next=fix),
                Option(id="accept", label="Accept as it is", next="done"),
            ]
            text = f"Findings remain after {ROUND_LIMIT} rounds: {r.reason}"
            _ask(
                c,
                Question(step=s.kind, text=text, options=options, cause=cause_key(ErrorKind.REVIEW, s.kind, key)),
                now,
            )
        elif s.kind == StepKind.REVIEW:
            _go(c, StepKind.BUILD, _fix_task(c, r) or s.task)
        else:
            s.attempt += 1
        return
    limit = FLAKE_LIMIT if s.kind == StepKind.FOLLOW else RETRY_LIMIT
    if _count(c, r.cause, now) > limit:
        _exhausted(c, r, now)
    else:
        s.attempt += 1


def _back(c: Change, r: StepResult, now: datetime) -> None:
    s = c.step
    target = r.back_to
    if target is None or target not in BACK.get(s.kind, frozenset()):
        msg = f"{s.kind} cannot go back to {target}"
        raise ValueError(msg)
    if r.cause and _count(c, r.cause, now) > RETRY_LIMIT:
        _exhausted(c, r, now)
        return
    if target == StepKind.PLAN:
        c.budgets.replans += 1
        if c.budgets.replans > REPLAN_LIMIT:
            options = [
                Option(id="revise", label="Narrow or split the brief", next=StepKind.SHAPE),
                Option(id="pause", label="Pause this Change", next="pause"),
            ]
            text = f"Re-planned {REPLAN_LIMIT} times: {r.reason}"
            _ask(c, Question(step=s.kind, text=text, options=options, cause=r.cause), now)
            return
    _enter(c, target, _fix_task(c, r) if target == StepKind.BUILD else None)
