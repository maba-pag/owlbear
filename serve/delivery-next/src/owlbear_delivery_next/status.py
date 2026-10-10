"""The one status line, next action and next actor of a Change (D3 §3.4)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING

from owlbear_delivery_next.loop import CONSENT, RETRY_LIMIT
from owlbear_delivery_next.models import Exit, StepKind, Waiting

if TYPE_CHECKING:
    from datetime import datetime

    from owlbear_delivery_next.models import Actor, Change, Stop

QUIET = timedelta(minutes=10)
_WHO = {
    Waiting.CI: "CI",
    Waiting.CHECK_START: "CI to start",
    Waiting.OWNER_ACTION: "your action in GitHub",
    Waiting.MERGE_QUEUE: "GitHub",
}
_ACTION = {Waiting.PERSON_CHECK: "Report result", Waiting.OWNER_ACTION: "Act in GitHub", Waiting.CHAT: "Approve brief"}
_WORK = {
    StepKind.SHAPE: ("Shape", "shaping", "reviewer"),
    StepKind.PLAN: ("Plan", "planning", "planner"),
    StepKind.BUILD: ("Build", "implementing", "builder"),
    StepKind.REVIEW: ("Build", "reviewing", "reviewer"),
    StepKind.INTEGRATE: ("Build", "updating with the target", "builder"),
    StepKind.CHECK: ("Check", "preparing", "builder"),
    StepKind.PUBLISH: ("Publish", "publishing", "delivery"),
    StepKind.FOLLOW: ("Publish", "following", "delivery"),
    StepKind.MERGE: ("Merge", "merging", "delivery"),
    StepKind.CLEANUP: ("Done", "cleaning up", "delivery"),
}


@dataclass(frozen=True)
class Activity:
    """Observed liveness; never inferred from the record alone."""

    host_up: bool
    runner_alive: bool = False
    holder_pid: int | None = None
    last_event_at: datetime | None = None
    start_failure: Stop | None = None


@dataclass(frozen=True)
class Status:
    """One line, the one next action (None when nothing is needed) and who takes it."""

    line: str
    action: str | None
    actor: Actor


def _age(delta: timedelta) -> str:
    n = int(delta.total_seconds())
    for size, unit in ((86400, "day"), (3600, "h"), (60, "min")):
        if n >= size:
            return f"{n // size} {unit}{'s' if unit == 'day' and n >= 2 * size else ''}"
    return f"{n} s"


def stage(c: Change) -> str:
    """Return the stage shown for the current step, with the task position while building."""
    kind = StepKind(c.step.mode) if c.step.kind == StepKind.INTEGRATE and c.step.mode else c.step.kind
    if kind in {StepKind.BUILD, StepKind.REVIEW} and c.plan and c.plan.tasks:
        ids = [t.id for t in c.plan.tasks]
        return f"Build {ids.index(c.step.task) + 1 if c.step.task in ids else len(ids)}/{len(ids)}"
    return _WORK[kind][0]


def unloadable(stop: Stop) -> Status:
    """Status of a Change whose state cannot load, from the store error's stop (restore or upgrade)."""
    return Status(f"stopped: {stop.reason}", stop.action, stop.actor)


def status(c: Change, activity: Activity, now: datetime) -> Status:  # noqa: C901, PLR0911, PLR0912 - D3 rules
    """Derive the status by the first matching rule; host-down overlays every unfinished Change."""
    s, o, stop = stage(c), c.outcome, activity.start_failure
    if not activity.host_up and not c.finished_at:
        if stop:
            return Status(f"{s} · stopped: {stop.reason}", stop.action, stop.actor)
        return Status(f"{s} · Delivery is not running", "Start Delivery", "you")
    if c.finished_at:
        if c.intent.abandoned_at:
            return Status("Abandoned · PR closed, branch kept", None, "delivery")
        saved = f" · unmerged work saved in {', '.join(c.names.preserved)}" if c.names.preserved else ""
        pr = f" PR #{c.names.pr}" if c.names.pr else ""
        return Status(f"Done · merged{pr}{saved}", None, "delivery")
    _, verb, role = _WORK[c.step.kind]
    if (b := c.blocked) and not activity.runner_alive:
        return Status(f"{s} · stopped: {b.reason}", b.action, b.actor)
    if c.intent.paused_at:
        if activity.runner_alive:
            return Status(f"{s} · pausing: finishing {c.step.kind}", None, "delivery")
        return Status(f"{s} · paused by you {_age(now - c.intent.paused_at)} ago", "Resume", "you")
    if c.intent.hold and activity.runner_alive:
        return Status(f"{s} · holding for your change: finishing {c.step.kind}", None, "delivery")
    if o and o.exit == Exit.ASK:
        return Status(f"{s} · waiting for you: {o.reason}", "Approve merge" if o.cause == CONSENT else "Answer", "you")
    if o and o.exit == Exit.STOP and c.stop:
        return Status(f"{s} · stopped: {c.stop.reason}", c.stop.action, c.stop.actor)
    if o and o.exit == Exit.PENDING:
        if o.who == "you":
            action = _ACTION.get(o.waiting) if o.waiting else None
            return Status(f"{s} · waiting for you: {o.reason}", action, "you")
        who = _WHO.get(o.waiting, str(o.waiting)) if o.waiting else o.who
        return Status(f"{s} · waiting for {who}: {o.reason} (checked {_age(now - o.at)} ago)", None, o.who)
    if activity.runner_alive:
        task = next((t for t in c.plan.tasks if t.id == c.step.task), None) if c.plan else None
        items = sum(1 for t in c.plan.tasks if t.item and not t.done) if task and task.item and c.plan else 0
        label = (task.title if task else None) or next((f"check {p.id}" for p in c.checks if p.id == c.step.task), None)
        line = f"{s} · {verb}: {label or c.brief.title or c.brief.outcome}"
        if items:
            line += f" · {items} open conversation item{'s' if items > 1 else ''}"
        last = activity.last_event_at
        if last and now - last > QUIET:
            return Status(f"{line} · no activity for {_age(now - last)}", None, "delivery")
        if o and o.denial:
            return Status(f"{line} · last denied: {o.denial}", None, "delivery")
        return Status(f"{line} · {role} active {_age(now - last) if last else '0 s'} ago", None, "delivery")
    if o and o.exit == Exit.RETRY and o.wake_at and o.wake_at > now and o.cause:
        k = c.budgets.causes[o.cause].count if o.cause in c.budgets.causes else 1
        return Status(f"{s} · retrying: {o.cause} ({k} of {RETRY_LIMIT}) at {o.wake_at:%H:%M}", None, "delivery")
    if activity.holder_pid:
        return Status(f"{s} · not running: waiting for process {activity.holder_pid} to end", None, "delivery")
    return Status(f"{s} · not running: starting {role}", None, "delivery")
