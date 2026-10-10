"""Retry budgets: count failures by cause, wait out the environment, and ask once a budget is spent (D3 §3.6)."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from owlbear_delivery_next.failures import DEFECT, ENVIRONMENT, QUOTA, SPLITTABLE, cause_key, kind_of, signature
from owlbear_delivery_next.models import Budget, ErrorKind, Exit, Option, Outcome, Question, StepKind, Stop, Waiting
from owlbear_delivery_next.moves import ask, enter, fix_task, go

if TYPE_CHECKING:
    from datetime import datetime

    from owlbear_delivery_next.loop import StepResult
    from owlbear_delivery_next.models import Change, Score

RETRY_LIMIT = 3
FLAKE_LIMIT = 1
ROUND_LIMIT = 2
REPLAN_LIMIT = 3
DEFECT_LIMIT = 3  # the same Delivery defect in a row before asking
PAUSE = timedelta(minutes=1)
PAUSE_CAP = timedelta(minutes=30)
EPISODE_QUIET = timedelta(hours=1)
EPISODE_ASK = timedelta(hours=24)


def episode(c: Change) -> Budget | None:
    """The environment episode the Change is waiting out, if any."""
    o = c.outcome
    if not (o and o.exit == Exit.PENDING and kind_of(o.cause) in ENVIRONMENT):
        return None
    b = c.budgets.causes.get(o.cause or "")
    return b if b and b.since else None


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


def streaks(c: Change, r: StepResult) -> None:
    """An attempt that got past a failure ends its environment episode; any other attempt breaks a defect streak."""
    step = f":{c.step.kind}:"
    c.budgets.causes = {
        k: b
        for k, b in c.budgets.causes.items()
        if step not in k or k == r.cause or kind_of(k) not in ENVIRONMENT | DEFECT
    }


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


def round_key(c: Change) -> str:
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
    sig = signature(kind_of(cause), str(c.step.kind), reason)
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
    cause, kind = r.cause or "", kind_of(r.cause)
    quota = cause.endswith(f":{QUOTA}")
    sig = signature(kind, str(c.step.kind), "quota" if quota else r.reason)
    b = c.budgets.causes.get(cause)
    if b is None or b.since is None or b.signature != sig:
        b = Budget(signature=sig, since=now)
    b = b.model_copy(update={"attempts": b.attempts + 1, "at": now})
    c.budgets.causes[cause] = b
    if not quota and now - (b.since or now) >= EPISODE_ASK:
        text = f"{kind} keeps failing for {c.step.kind} since {b.since:%Y-%m-%d %H:%M}; last error: {r.reason}"
        ask(c, Question(step=c.step.kind, text=text, options=_resolve_or_pause(), cause=cause), now)
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
    sig = signature(kind_of(cause), str(c.step.kind), r.reason)
    b = c.budgets.causes.get(cause)
    count = b.count + 1 if b and b.signature == sig else 1
    c.budgets.causes[cause] = Budget(count=count, signature=sig, task=c.step.task, at=now)
    if count >= DEFECT_LIMIT:
        text = f"Delivery failed the same way {count} times ({cause}): {r.reason}"
        ask(c, Question(step=c.step.kind, text=text, options=_resolve_or_pause(), cause=cause), now)
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
    ask(c, Question(step=c.step.kind, text=f"{r.reason} keeps failing ({cause})", options=options, cause=cause), now)


def _alternative(c: Change, r: StepResult, now: datetime) -> bool:
    """Once per cause, re-plan to split the work instead of asking; the planner sees why."""
    b = c.budgets.causes.get(r.cause or "")
    if b is None or b.alternative or kind_of(r.cause) not in SPLITTABLE or c.plan is None:
        return False
    if c.step.kind in {StepKind.SHAPE, StepKind.PLAN} or c.budgets.replans >= REPLAN_LIMIT:
        return False
    c.budgets.replans += 1
    c.budgets.causes[r.cause or ""] = b.model_copy(update={"alternative": True})  # the next exhaustion asks
    reason = f"re-plan to split the work after {r.cause} kept failing: {r.reason}"
    c.outcome = Outcome(exit=Exit.BACK, cause=r.cause, reason=reason, at=now)
    enter(c, StepKind.PLAN)
    return True


def _round(c: Change, r: StepResult, now: datetime) -> None:
    """One more shaping, planning or review round; resolving a previous finding starts the rounds again."""
    s, key = c.step, round_key(c)
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
        ask(c, Question(step=s.kind, text=text, options=options, cause=cause), now)
    elif s.kind == StepKind.REVIEW:
        go(c, StepKind.BUILD, fix_task(c, r, s.task) or s.task)
    else:
        s.attempt += 1


def retry(c: Change, r: StepResult, now: datetime) -> None:
    """Apply a retry exit: another round, an environment wait, a defect streak or a counted cause.

    Raises:
        ValueError: The retry lacks the cause or repair task its step needs.
    """
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
    if kind_of(r.cause) in ENVIRONMENT:
        _environment(c, r, now)
        return
    if kind_of(r.cause) in DEFECT:
        _defect(c, r, now)
        return
    limit = FLAKE_LIMIT if s.kind == StepKind.FOLLOW else RETRY_LIMIT
    if _count(c, r.cause, now, r.score, r.reason) > limit:
        _exhausted(c, r, now)
    else:
        s.attempt += 1


def back(c: Change, r: StepResult, now: datetime) -> None:
    """Apply a back exit to an allowed earlier step; re-planning too often asks the owner.

    Raises:
        ValueError: The back exit has no cause.
    """
    s = c.step
    target = r.back_to
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
            ask(c, Question(step=s.kind, text=text, options=options, cause=r.cause), now)
            return
    enter(c, target, fix_task(c, r) if target == StepKind.BUILD else None)
