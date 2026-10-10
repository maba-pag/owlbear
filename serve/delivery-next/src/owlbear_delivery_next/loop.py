"""Delivery-next step loop: choose the next step and apply exits, budgets and the inbox (D3 §3.3, §3.6)."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timedelta
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Literal

from pydantic import Field

from owlbear_delivery_next.models import (
    VISUAL,
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

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from owlbear_delivery_next.models import Change, InboxItem, PersonCheck

type PrState = Literal["open", "merged", "closed"]
type Seen = tuple[PrState | None, bool]  # the PR's end state; whether a consent wait saw a comment or a new head

RETRY_LIMIT = 3
FLAKE_LIMIT = 1
ROUND_LIMIT = 2
REPLAN_LIMIT = 3
DEFECT_LIMIT = 3  # the same Delivery defect in a row before asking
ENVIRONMENT = frozenset({ErrorKind.NETWORK, ErrorKind.CAPACITY})  # waits; never budget
DEFECT = frozenset({ErrorKind.TOOLING, ErrorKind.STATE, ErrorKind.RESULT})  # Delivery's adapter, store, tools
# work failures a smaller task can get past; the one alternative before asking is a re-plan that splits the work
SPLITTABLE = frozenset(
    {ErrorKind.CHECKS, ErrorKind.REVIEW, ErrorKind.SCOPE, ErrorKind.COMMIT_POLICY, ErrorKind.CONFLICT}
)
PAUSE = timedelta(minutes=1)
PAUSE_CAP = timedelta(minutes=30)
EPISODE_QUIET = timedelta(hours=1)
EPISODE_ASK = timedelta(hours=24)
TREE = ":tree"  # the fingerprint key of a check without declared paths
QUOTA = "quota"  # the cause subject of an exhausted Copilot quota: waited out, never asked about
_QUOTA = re.compile(r"quota|premium requests?|credits", re.IGNORECASE)
_CAPACITY = re.compile(r"\b429\b|rate.?limit|capacity|overloaded|quota|credits", re.IGNORECASE)
_NETWORK = re.compile(
    r"\b(?:status|http|code|error)\W{0,3}5\d\d\b|\b5\d\d (?:internal|bad gateway|service unavailable|gateway)"
    r"|timed? ?out|timeout|connection|unreachable|temporar|runtime start|network|could not resolve",
    re.IGNORECASE,
)
_NOISE = (
    (re.compile(r"(/private)?/(tmp|var/folders)/\S*"), "<tmp>"),
    (re.compile(r"\b[0-9a-f]{7,40}\b"), "<sha>"),
    (re.compile(r"\d+"), "<n>"),
    (re.compile(r"\s+"), " "),
)

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


def signature(kind: str, step: str, message: str) -> str:
    """Stable identity of one failure: numbers, commit ids and temporary paths do not distinguish it."""
    text = message.lower()
    for pattern, mark in _NOISE:
        text = pattern.sub(mark, text)
    return hashlib.sha256(f"{kind}:{step}:{text.strip()}".encode()).hexdigest()[:16]


def transient(text: str) -> ErrorKind | None:
    """Classify a runtime or provider failure text as capacity, network or neither."""
    if _CAPACITY.search(text):
        return ErrorKind.CAPACITY
    return ErrorKind.NETWORK if _NETWORK.search(text) else None


def quota(text: str) -> bool:
    """Whether a capacity failure text is the Copilot quota, not a provider rate limit."""
    return bool(_QUOTA.search(text))


def _kind(cause: str | None) -> str:
    return (cause or "").split(":", 1)[0]


def episode(c: Change) -> Budget | None:
    """The environment episode the Change is waiting out, if any."""
    o = c.outcome
    if not (o and o.exit == Exit.PENDING and _kind(o.cause) in ENVIRONMENT):
        return None
    b = c.budgets.causes.get(o.cause or "")
    return b if b and b.since else None


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


def check_valid(recorded: Inputs, current: Inputs) -> bool:
    """A person-only check answer holds only while its covered paths are exactly as recorded, added ones included."""
    return recorded.paths == current.paths and inputs_valid(recorded, current)


def changed(recorded: Inputs, current: Inputs) -> list[str]:
    """Name each check input that no longer holds: a criterion, a path, the check's steps or its environment."""
    names = [k for k, v in recorded.criteria.items() if current.criteria.get(k) != v]
    paths = [p for p, f in recorded.paths.items() if current.paths.get(p) != f]
    names += ["the worktree" if p == TREE else p for p in paths + [p for p in current.paths if p not in recorded.paths]]
    names += ["the check's steps"] if recorded.procedure != current.procedure else []
    return names + (["the environment"] if recorded.environment != current.environment else [])


def coverage(c: Change) -> list[str]:
    """Conservative paths of a person-only check: the brief's scope and every task's scope."""
    tasks = c.plan.tasks if c.plan else []
    return sorted({*c.brief.scope, *(p for t in tasks for p in t.scope)})


def _cover(c: Change) -> None:
    for check in c.checks:
        check.paths = coverage(c)


def _criteria(c: Change) -> dict[str, int]:
    return {k.id: k.version for k in c.brief.criteria}


def review_valid(c: Change, review: Review, paths: Mapping[str, str], changed: Iterable[str] | None = None) -> bool:
    """Return whether a passing review still holds for the observed fingerprints and, given, the changed paths.

    Every path changed against the base must lie in the review's engine-computed coverage (F3).
    """
    if changed is not None and not set(changed) <= review.inputs.paths.keys():
        return False
    return review.verdict == "pass" and inputs_valid(review.inputs, Inputs(criteria=_criteria(c), paths=dict(paths)))


def check_inputs(c: Change, check: PersonCheck, paths: Mapping[str, str]) -> Inputs:
    """Return the current inputs of one person-only check from the brief and observed paths.

    A check without declared paths depends on the whole tree (``TREE``), so any tree change voids it (F3).
    """
    crit = _criteria(c)
    return Inputs(
        criteria={k: crit[k] for k in check.criteria if k in crit},
        paths={
            k: f
            for k, f in paths.items()
            if (k != TREE and any(_within(k, p) for p in check.paths)) or (k == TREE and not check.paths)
        },
        procedure=check.procedure,
        environment=check.environment,
    )


def visual_valid(c: Change, head: str | None, tree: str | None = None) -> bool:
    """A passed visual result holds only for its exact head (and tree, when given) and the current state versions."""
    r = c.visual
    if r is None or not r.passed or r.head != head or (tree is not None and r.tree != tree):
        return False
    return r.states == {s.name: s.version for s in c.brief.visual} and r.criteria == _criteria(c)


def next_check(c: Change, paths: Mapping[str, str]) -> PersonCheck | None:
    """Return the first declared person-only check without a valid passing answer."""
    for check in c.checks:
        answer = check.answer
        if not (answer and answer.passed and answer.inputs):
            return check
        if not check_valid(answer.inputs, check_inputs(c, check, paths)):
            return check
    return None


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


def _within(a: str, b: str) -> bool:
    """One path contains the other; an empty or root scope contains every path."""
    pa, pb = (tuple(x for x in PurePosixPath(p).parts if x != "/") for p in (a, b))
    n = min(len(pa), len(pb))
    return pa[:n] == pb[:n]


def overlaps(plan: Plan, others: Mapping[str, Iterable[str]]) -> dict[str, list[str]]:
    """Each other open Change whose scope shares a path or directory with the plan's task scopes (D7)."""
    mine = {p for t in plan.tasks for p in t.scope}
    found = {h: sorted({p for p in scope if any(_within(p, m) for m in mine)}) for h, scope in others.items()}
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
            _go(c, StepKind.CLEANUP, mode=None if pr_state == "merged" else "abandon")
            c.outcome = None
        elif pr_state == "closed" and not any(q.cause == PR_CLOSED and not q.effect_observed_at for q in c.questions):
            # A closed-PR question holds until it is answered and, for reopen, the PR is observed open again.
            _go(c, StepKind.MERGE)
            options = [
                Option(id="abandon", label="Abandon this Change", next="abandon"),
                Option(id="reopen", label="Reopen it and continue", next=StepKind.FOLLOW),
            ]
            _ask(c, Question(step=StepKind.MERGE, text="The PR was closed", options=options, cause=PR_CLOSED), now)
        elif c.intent.hold and c.step.kind != StepKind.MERGE:
            _go(c, StepKind.SHAPE)
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
    if q.cause and _kind(q.cause) in ENVIRONMENT | DEFECT and target != "pause":
        c.budgets.causes.pop(q.cause, None)  # "Done, continue" starts a new episode or streak
    if target == "pause":
        c.intent.paused_at, c.intent.pause_reason = now, q.text
    elif target == "done":
        _done(c, None, now)
    elif target == "abandon":
        c.intent.abandoned_at = item.at
    elif target is not None:
        _enter(c, StepKind(target))


def answer_delivered(change: Change, question_id: str, now: datetime) -> Change:
    """Record that a session acknowledged the answer; delivery alone resets no budget."""
    c = change.model_copy(deep=True)
    for q in c.questions:
        if q.id == question_id and q.answer is not None and q.delivered_at is None:
            q.delivered_at = now
    return c


def charge(change: Change, cause: str, now: datetime) -> tuple[Change, bool]:
    """Count one occurrence of *cause* outside a step exit; False once it exceeds the retry limit."""
    c = change.model_copy(deep=True)
    return c, _count(c, cause, now) <= RETRY_LIMIT


def effect_observed(change: Change, question_id: str, now: datetime) -> Change:
    """Record that an answer's effect was observed; only then, and only once, does its cause's count reset."""
    c = change.model_copy(deep=True)
    for q in c.questions:
        if q.id == question_id and q.answer is not None and q.effect_observed_at is None:
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
    _streaks(c, result)
    match result.exit:
        case Exit.DONE:
            c.stop = None
            _done(c, result, now)
        case Exit.RETRY:
            _retry(c, result, now)
        case Exit.BACK:
            _back(c, result, now)
        case Exit.ASK if result.question:
            if kind == StepKind.PLAN and result.plan:
                c.plan = result.plan  # an accepted plan that overlaps: kept for the owner's answer
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


def _streaks(c: Change, r: StepResult) -> None:
    """An attempt that got past a failure ends its environment episode; any other attempt breaks a defect streak."""
    step = f":{c.step.kind}:"
    c.budgets.causes = {
        k: b
        for k, b in c.budgets.causes.items()
        if step not in k or k == r.cause or _kind(k) not in ENVIRONMENT | DEFECT
    }


def _go(c: Change, kind: StepKind, task: str | None = None, mode: str | None = None) -> None:
    c.step = Step(kind=kind, task=task, mode=mode)


def _enter(c: Change, kind: StepKind, task: str | None = None) -> None:
    s = c.step
    again = kind == s.kind == StepKind.CHECK  # an answer during a check returns to that same check
    keep = task or (s.task if kind in {StepKind.BUILD, StepKind.INTEGRATE} or again else None)
    caller = s.mode if s.kind == StepKind.INTEGRATE else str(s.kind)
    final = "final" if kind == StepKind.REVIEW and keep is None else None  # a review without a task is final
    _go(c, kind, keep, caller if kind == StepKind.INTEGRATE else final)


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
            if s.kind == StepKind.SHAPE and not brief_ready(c):
                return  # the shape step reviews the approved version first
            c.budgets.rounds.pop(str(s.kind), None)
            if s.kind == StepKind.PLAN and r and r.plan:
                c.plan = r.plan
            if s.kind == StepKind.PLAN:
                _cover(c)
            task = _open_task(c) if s.kind == StepKind.PLAN else None
            _go(c, StepKind.BUILD if s.kind == StepKind.PLAN else StepKind.PLAN, task.id if task else None)
        case StepKind.BUILD:
            _go(c, StepKind.REVIEW, s.task)
        case StepKind.REVIEW:
            if r and r.review:
                c.reviews.append(r.review)
            c.budgets.rounds.pop(_round_key(c), None)
            resolved = _resolved(c, s.task)
            for t in c.plan.tasks if c.plan else []:
                t.done = t.done or t.id in resolved
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
            from owlbear_delivery_next.steps import visual  # noqa: PLC0415 - visual imports loop

            check, person = next_check(c, paths), any(p.visual for p in c.checks)
            states = visual.need(ui=c.brief.ui, states=bool(c.brief.visual), person=person) == "states"
            if s.kind == StepKind.FOLLOW and states and not visual_valid(c, r.head if r else None):
                _go(c, StepKind.CHECK, VISUAL)  # the visual check runs before person-only checks
            elif check:
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
    return _scope(c, task_id)


def _scope(c: Change, task_id: str | None) -> str | None:
    task = next((t for t in c.plan.tasks if t.id == task_id), None) if c.plan else None
    return "scope:" + ",".join(sorted(task.scope)) if task else None


def _round_key(c: Change) -> str:
    """Review rounds count per task scope, so a renamed task with the same scope keeps its rounds."""
    return _scope(c, c.step.task) or c.step.mode or str(c.step.kind)


def _progress(c: Change, cause: str, score: Score | None) -> bool:
    """Record *score* against the streak's best; True when it is progress, which then becomes the best.

    Progress is a strict subset of the best's failures, or more criteria satisfied with no new failure.
    Swapping one failure for another is not progress, and the best moves only on progress.
    """
    if score is None:
        return False
    budget = c.budgets.causes.setdefault(cause, Budget())
    best = budget.progress
    if best is None:
        budget.progress = score
        return False
    now, was = set(score.findings), set(best.findings)
    better = now < was or (now <= was and score.satisfied > best.satisfied)
    if better:
        budget.progress = score
    return better


def _count(c: Change, cause: str, now: datetime, score: Score | None = None, reason: str = "") -> int:
    """Count one failure of *cause* under its normalised signature; a premise change or progress resets."""
    budget = c.budgets.causes.get(cause)
    if budget is None or _premise(c, cause, budget.task) not in {None, budget.premise}:
        budget = Budget(alternative=budget.alternative if budget else False)
        c.budgets.causes[cause] = budget
    sig = signature(_kind(cause), str(c.step.kind), reason)
    counts = {} if _progress(c, cause, score) else dict(budget.counts)
    counts[sig] = counts.get(sig, 0) + 1
    task = c.step.task
    premise = _premise(c, cause, task) or budget.premise
    update = {"count": counts[sig], "counts": counts, "signature": sig, "premise": premise, "task": task, "at": now}
    c.budgets.causes[cause] = budget.model_copy(update=update)
    return counts[sig]


def _environment(c: Change, r: StepResult, now: datetime) -> None:
    """Wait out a network or capacity failure with growing pauses; ask only after a day of the same failure.

    An exhausted Copilot quota is never asked about: it waits for its reset time, else the capped pause.
    """
    cause, kind = r.cause or "", _kind(r.cause)
    quota = cause.endswith(f":{QUOTA}")
    sig = signature(kind, str(c.step.kind), "quota" if quota else r.reason)
    b = c.budgets.causes.get(cause)
    if b is None or b.since is None or b.signature != sig:
        b = Budget(signature=sig, since=now)
    b = b.model_copy(update={"attempts": b.attempts + 1, "at": now})
    c.budgets.causes[cause] = b
    if not quota and now - (b.since or now) >= EPISODE_ASK:
        text = f"{kind} keeps failing for {c.step.kind} since {b.since:%Y-%m-%d %H:%M}; last error: {r.reason}"
        _ask(c, Question(step=c.step.kind, text=text, options=_resolve_or_pause(), cause=cause), now)
        return
    if kind == ErrorKind.CAPACITY and r.wake_at and r.wake_at > now:
        wake = r.wake_at  # a quota or rate limit resets at its own time
    else:
        base = r.wake_at - now if r.wake_at and r.wake_at > now else PAUSE
        wake = now + min(base * 2 ** min(b.attempts - 1, 10), PAUSE_CAP)
    reason = "waiting for Copilot quota to reset" if quota else r.reason
    c.outcome = Outcome(exit=Exit.PENDING, cause=cause, reason=reason, waiting=Waiting.NETWORK, wake_at=wake, at=now)


def _defect(c: Change, r: StepResult, now: datetime) -> None:
    """Retry a Delivery defect; the same signature three times in a row asks with the error."""
    cause = r.cause or ""
    sig = signature(_kind(cause), str(c.step.kind), r.reason)
    b = c.budgets.causes.get(cause)
    count = b.count + 1 if b and b.signature == sig else 1
    c.budgets.causes[cause] = Budget(count=count, signature=sig, task=c.step.task, at=now)
    if count >= DEFECT_LIMIT:
        text = f"Delivery failed the same way {count} times ({cause}): {r.reason}"
        _ask(c, Question(step=c.step.kind, text=text, options=_resolve_or_pause(), cause=cause), now)
    else:
        c.step.attempt += 1


def _resolve_or_pause() -> list[Option]:
    return [Option(id="done", label="Done, continue"), Option(id="pause", label="Pause", next="pause")]


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
    if _alternative(c, r, now):
        return
    options = [
        Option(id="revise", label="Revise the requirement", next=StepKind.SHAPE),
        Option(id="narrow", label="Narrow the scope", next=StepKind.PLAN),
        Option(id="pause", label="Pause this Change", next="pause"),
    ]
    _ask(c, Question(step=c.step.kind, text=f"{r.reason} keeps failing ({cause})", options=options, cause=cause), now)


def _alternative(c: Change, r: StepResult, now: datetime) -> bool:
    """Once per cause, re-plan to split the work instead of asking; the planner sees why."""
    b = c.budgets.causes.get(r.cause or "")
    if b is None or b.alternative or _kind(r.cause) not in SPLITTABLE or c.plan is None:
        return False
    if c.step.kind in {StepKind.SHAPE, StepKind.PLAN} or c.budgets.replans >= REPLAN_LIMIT:
        return False
    c.budgets.replans += 1
    c.budgets.causes[r.cause or ""] = b.model_copy(update={"alternative": True})  # the next exhaustion asks
    reason = f"re-plan to split the work after {r.cause} kept failing: {r.reason}"
    c.outcome = Outcome(exit=Exit.BACK, cause=r.cause, reason=reason, at=now)
    _enter(c, StepKind.PLAN)
    return True


def _resolved(c: Change, task_id: str | None) -> set[str]:
    """The passed task and, transitively, each task whose review findings it fixed."""
    tasks = {t.id: t for t in c.plan.tasks} if c.plan else {}
    found: set[str] = set()
    while task_id and task_id not in found:
        found.add(task_id)
        task_id = tasks[task_id].fixes if task_id in tasks else None
    return found


def _fix_task(c: Change, r: StepResult, fixes: str | None = None) -> str | None:
    if r.fix_task is None or c.plan is None:
        return None
    if any(t.id == r.fix_task.id for t in c.plan.tasks):
        return r.fix_task.id  # an unfinished task already in the plan is resumed, not duplicated
    c.plan.tasks.append(r.fix_task.model_copy(update={"fixes": fixes}))
    _cover(c)
    return r.fix_task.id


def _round(c: Change, r: StepResult, now: datetime) -> None:
    """One more shaping, planning or review round; resolving a previous finding starts the rounds again."""
    s, key = c.step, _round_key(c)
    if _progress(c, cause_key(ErrorKind.REVIEW, s.kind, key), r.score):
        c.budgets.rounds[key] = 0
    c.budgets.rounds[key] = c.budgets.rounds.get(key, 0) + 1
    if c.budgets.rounds[key] > ROUND_LIMIT:
        fix = StepKind.BUILD if s.kind == StepKind.REVIEW else s.kind
        options = [
            Option(id="fix", label="Fix the findings", next=fix),
            Option(id="accept", label="Accept as it is", next="done"),
        ]
        text = f"Findings remain after {ROUND_LIMIT} rounds: {r.reason}"
        cause = cause_key(ErrorKind.REVIEW, s.kind, key)
        _ask(c, Question(step=s.kind, text=text, options=options, cause=cause), now)
    elif s.kind == StepKind.REVIEW:
        _go(c, StepKind.BUILD, _fix_task(c, r, s.task) or s.task)
    else:
        s.attempt += 1


def _retry(c: Change, r: StepResult, now: datetime) -> None:
    s = c.step
    if s.kind == StepKind.PLAN and r.plan:
        c.plan = r.plan  # the challenged plan: kept for the next round, or accepted as it is
    if r.cause is None:
        if s.kind not in {StepKind.SHAPE, StepKind.PLAN, StepKind.REVIEW}:
            msg = f"{s.kind} retry needs a cause"
            raise ValueError(msg)
        if s.mode == "final" and r.fix_task is None:
            msg = 'fix_task: empty - final review findings need a repair task, e.g. Task(id="f1", title="fix")'
            raise ValueError(msg)
        _round(c, r, now)
        return
    if _kind(r.cause) in ENVIRONMENT:
        _environment(c, r, now)
        return
    if _kind(r.cause) in DEFECT:
        _defect(c, r, now)
        return
    limit = FLAKE_LIMIT if s.kind == StepKind.FOLLOW else RETRY_LIMIT
    if _count(c, r.cause, now, r.score, r.reason) > limit:
        _exhausted(c, r, now)
    else:
        s.attempt += 1


def _back(c: Change, r: StepResult, now: datetime) -> None:
    s = c.step
    target = r.back_to
    if target is None or target not in BACK.get(s.kind, frozenset()):
        msg = f"{s.kind} cannot go back to {target}"
        raise ValueError(msg)
    if r.cause is None:
        msg = f"{s.kind} back needs a cause"
        raise ValueError(msg)
    if _count(c, r.cause, now, r.score, r.reason) > RETRY_LIMIT:
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
