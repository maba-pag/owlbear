"""The one status line, next action and next actor of a Change (D3 §3.4)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING

from owlbear_delivery_next.loop import RETRY_LIMIT
from owlbear_delivery_next.models import Exit, StepKind, Waiting

if TYPE_CHECKING:
    from datetime import datetime

    from owlbear_delivery_next.models import Actor, Change, Stop

QUIET = timedelta(minutes=10)
_STAGE = {
    StepKind.SHAPE: "Shape",
    StepKind.PLAN: "Plan",
    StepKind.PUBLISH: "Publish",
    StepKind.FOLLOW: "Publish",
    StepKind.CHECK: "Check",
    StepKind.MERGE: "Merge",
    StepKind.CLEANUP: "Done",
}
_WORK = {
    StepKind.SHAPE: ("shaping", "reviewer"),
    StepKind.PLAN: ("planning", "planner"),
    StepKind.BUILD: ("implementing", "builder"),
    StepKind.REVIEW: ("reviewing", "reviewer"),
    StepKind.INTEGRATE: ("updating with the target", "builder"),
    StepKind.CHECK: ("preparing", "builder"),
    StepKind.PUBLISH: ("publishing", "delivery"),
    StepKind.FOLLOW: ("following", "delivery"),
    StepKind.MERGE: ("merging", "delivery"),
    StepKind.CLEANUP: ("cleaning up", "delivery"),
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
    seconds = int(delta.total_seconds())
    if seconds < 60:  # noqa: PLR2004 - one minute
        return f"{seconds} s"
    if seconds < 3600:  # noqa: PLR2004 - one hour
        return f"{seconds // 60} min"
    if seconds < 86400:  # noqa: PLR2004 - one day
        return f"{seconds // 3600} h"
    days = seconds // 86400
    return f"{days} day{'s' if days > 1 else ''}"


def stage(c: Change) -> str:
    """Return the stage shown for the current step, with the task position while building."""
    kind = StepKind(c.step.mode) if c.step.kind == StepKind.INTEGRATE and c.step.mode else c.step.kind
    if kind in {StepKind.BUILD, StepKind.REVIEW} and c.plan and c.plan.tasks:
        ids = [t.id for t in c.plan.tasks]
        return f"Build {ids.index(c.step.task) + 1 if c.step.task in ids else len(ids)}/{len(ids)}"
    return _STAGE.get(kind, "Build")


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
        return Status(f"Done · merged{saved}", None, "delivery")
    verb, role = _WORK[c.step.kind]
    if c.intent.paused_at:
        if activity.runner_alive:
            return Status(f"{s} · pausing: finishing {c.step.kind}", None, "delivery")
        return Status(f"{s} · paused by you {_age(now - c.intent.paused_at)} ago", "Resume", "you")
    if o and o.exit == Exit.ASK:
        return Status(f"{s} · waiting for you: {o.reason}", "Answer", "you")
    if o and o.exit == Exit.STOP and c.stop:
        return Status(f"{s} · stopped: {c.stop.reason}", c.stop.action, c.stop.actor)
    if o and o.exit == Exit.PENDING:
        if o.who == "you":
            action = "Report result" if o.waiting == Waiting.PERSON_CHECK else None
            return Status(f"{s} · waiting for you: {o.reason}", action, "you")
        return Status(f"{s} · waiting for {o.waiting}: {o.reason} (checked {_age(now - o.at)} ago)", None, o.who)
    if activity.runner_alive:
        task = next((t.title for t in c.plan.tasks if t.id == c.step.task), None) if c.plan else None
        line = f"{s} · {verb}: {task or c.brief.outcome}"
        last = activity.last_event_at
        if last and now - last > QUIET:
            return Status(f"{line} · no activity for {_age(now - last)}", None, "delivery")
        return Status(f"{line} · {role} active {_age(now - last) if last else '0 s'} ago", None, "delivery")
    if o and o.exit == Exit.RETRY and o.wake_at and o.wake_at > now and o.cause:
        k = c.budgets.causes[o.cause].count if o.cause in c.budgets.causes else 1
        return Status(f"{s} · retrying: {o.cause} ({k} of {RETRY_LIMIT}) at {o.wake_at:%H:%M}", None, "delivery")
    if activity.holder_pid:
        return Status(f"{s} · not running: waiting for process {activity.holder_pid} to end", None, "delivery")
    return Status(f"{s} · not running: starting {role}", None, "delivery")
