"""The one status line, next action and next actor of a Change (D3 §3.4)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.change_contracts.failures import QUOTA, WRONG_MODEL
from owlbear_delivery_next.change_contracts.models import ErrorKind, Exit, StepKind, Waiting
from owlbear_delivery_next.change_flow import loop, picks
from owlbear_delivery_next.change_flow.brief_rounds import MODES
from owlbear_delivery_next.change_flow.budgets import EPISODE_QUIET, RETRY_LIMIT, WRONG_MODEL_LIMIT, episode
from owlbear_delivery_next.change_flow.loop import CONSENT
from owlbear_delivery_next.local_system.mask import redact

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_delivery_next.change_contracts.models import Actor, Change, Stop

_AGENT, _ENGINE = timedelta(minutes=10), timedelta(minutes=2)
QUIET: dict[StepKind, timedelta] = {
    StepKind.SHAPE: _AGENT,
    StepKind.PLAN: _AGENT,
    StepKind.TESTS: _AGENT,
    StepKind.BUILD: _AGENT,
    StepKind.REVIEW: _AGENT,
    StepKind.INTEGRATE: _AGENT,
    StepKind.CHECK: _AGENT,
    StepKind.PUBLISH: _ENGINE,
    StepKind.FOLLOW: _ENGINE,
    StepKind.MERGE: _ENGINE,
    StepKind.CLEANUP: _ENGINE,
}  # a pending wait has no runner, so it is never quiet
# The card's words for a logged event match the activity log's (web/pages/changes/activity.mjs), in lower case.
_STEP_SAID = {
    "shape": "shaping", "plan": "planning", "tests": "test review", "build": "building", "review": "review",
    "integrate": "update with the target", "publish": "publishing", "follow": "following the pull request",
    "check": "check preparation", "merge": "merge", "cleanup": "clean-up",
}  # fmt: skip
_EXIT_SAID = {
    "done": "finished", "retry": "will try again", "ask": "asks you", "back": "went back", "stop": "stopped",
    "pending": "waiting",
}  # fmt: skip
TOOL_SAID = {
    "submit_result": "submitted its result", "ask_question": "asked a question",
    "report_wrong_premise": "reported a wrong premise", "report_missing_tool": "reported a missing tool",
    "lookup_decisions": "looked up decisions", "submit_first_look": "submitted its first look",
    "scan_design": "scanned the design",
}  # fmt: skip


def _tool_said(tool: object) -> str:
    return TOOL_SAID.get(str(tool), f"called {tool}")


_SAID: dict[str, Callable[[dict[str, Any]], str]] = {
    "tool": lambda e: _tool_said(e.get("tool")) + ("" if e.get("accepted", True) else " (refused)"),
    "denied": lambda e: f'denied "{redact(str((e.get("request") or [""])[0]))[:60]}"',
    "session": lambda e: "session resumed" if e.get("resumed") else "session started",
    "step": lambda e: (
        f"{_STEP_SAID.get(str(e.get('kind')), str(e.get('kind')).replace('-', ' '))} "
        + _EXIT_SAID.get(str(e.get("exit")), "ended")
    ),
    "pids": lambda _e: "started a process",
    "force-stop": lambda _e: "stopped the session",
    "wave": lambda _e: "started judges",
    "answer": lambda e: f"answered {e.get('question')}: {str(e.get('class')).replace('_', ' ')}",  # TD-461
}
_WHO = {
    Waiting.CI: "CI",
    Waiting.CHECK_START: "CI to start",
    Waiting.OWNER_ACTION: "your action in GitHub",
    Waiting.GITHUB: "GitHub",
}
_ACTION = {Waiting.PERSON_CHECK: "Report result", Waiting.OWNER_ACTION: "Act in GitHub", Waiting.CHAT: "Approve brief"}
RESUME = "Resume Delivery"
_WORK = {
    StepKind.SHAPE: ("Shape", "shaping", "reviewer"),
    StepKind.PLAN: ("Plan", "planning", "planner"),
    StepKind.TESTS: ("Build", "reviewing tests", "test reviewer"),  # TD-373
    StepKind.BUILD: ("Build", "implementing", "builder"),
    StepKind.REVIEW: ("Build", "reviewing", "reviewer"),
    StepKind.INTEGRATE: ("Build", "updating with the target", "builder"),
    StepKind.CHECK: ("Check", "preparing", "preparer"),
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
    paused: bool = False  # Delivery itself waits for Resume (TD-259)
    waiting_slot: str = ""  # how full the session slots are while its step waits for one (TD-336)


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


def _tool_at(c: Change, tool: dict[str, Any] | None) -> datetime | None:
    """When the current step's latest tool call (the now line) was written; None for an earlier step's."""
    shown = datetime.fromisoformat(tool["at"]) if tool and isinstance(tool.get("at"), str) else None
    return None if shown and c.step.started_at and shown < c.step.started_at else shown


def silent(c: Change, activity: Activity, now: datetime, tool: dict[str, Any] | None = None) -> timedelta | None:
    """How long the running step has had no activity, once that exceeds its kind's quiet threshold."""
    since = max((t for t in (activity.last_event_at, c.step.started_at, _tool_at(c, tool)) if t), default=None)
    if not (activity.runner_alive and since and now - since > QUIET[c.step.kind]):
        return None
    return now - since


def _episode(c: Change, now: datetime) -> tuple[str, bool]:
    """The environment failure being waited out, as ``failing for <age>, attempt <n>``, and whether it is quiet."""
    if not (b := episode(c)) or not b.since:
        return "", False
    kind = (c.outcome.cause or "").split(":", 1)[0] if c.outcome else ""
    return f"{kind} failing for {_age(now - b.since)}, attempt {b.attempts}", now - b.since >= EPISODE_QUIET


def card(  # noqa: PLR0913 - the data repository's push state is observed apart from the Change
    c: Change,
    activity: Activity,
    events: list[dict[str, Any]],
    now: datetime,
    tool: dict[str, Any] | None = None,
    *,
    pending: Callable[[], str] | None = None,
) -> dict[str, Any]:
    """The Change card: the step and its latest tool call or logged event, step time, quiet flag and credits.

    *pending* says what the shared data repository has not pushed yet, if anything.
    """
    line, since = stage(c), c.step.started_at
    last = next((e for e in reversed(events) if "at" in e and "event" in e), None)
    shown = _tool_at(c, tool)
    if shown and tool and (not last or shown > datetime.fromisoformat(last["at"])):
        said = tool.get("summary") if tool.get("summary") not in {None, "", tool.get("tool")} else None
        line += f" · {said or _tool_said(tool.get('tool'))} {_age(now - shown)} ago"
    elif last:
        said = _SAID.get(last["event"], lambda e: str(e["event"]))(last)
        line += f" · {said} {_age(now - datetime.fromisoformat(last['at']))} ago"
    failing, quiet = _episode(c, now)
    line += _left(events, since)
    if failing:
        line += f" · {failing}"
    step = sum(
        (e.get("usage") or {}).get("credits") or 0.0
        for e in events
        if e.get("event") == "step" and since and "at" in e and datetime.fromisoformat(e["at"]) >= since
    )
    return {
        "now": line,
        "step_time": _age(now - since) if since and not c.finished_at else None,
        "quiet": quiet or silent(c, activity, now, tool) is not None,
        "credits": {"change": round(c.spend.credits, 2), "step": round(step, 2), "unknown": len(c.spend.unread)},
        "overlaps": [f"overlaps with {o.other}: {', '.join(o.paths[:5])}" for o in c.overlaps],
        "decisions": unpublished(c, pending),
    }


def unpublished(c: Change, pending: Callable[[], str] | None = None) -> list[str]:
    """The brief's project decisions its approval committed but did not push, until a later save pushed (TD-453).

    Shown after the Change finished too: its cleanup never pushes them.
    """
    left = [p for p in c.decisions_published if p.committed and not p.published]  # planned ones: resume's line
    if not left or (pending is not None and not pending()):
        return []
    titles, why = ", ".join(p.title for p in left), left[-1].notice or "not pushed"
    return [f"Project decisions not yet pushed: {titles}: {why}; the data repository's next save pushes them"]


def _left(events: list[dict[str, Any]], since: datetime | None) -> str:
    """A visual round running in waves: the judges not yet ended when its latest wave started (TD-336)."""
    wave = next((e for e in reversed(events) if e.get("event") == "wave"), None)
    if wave and since and datetime.fromisoformat(wave["at"]) >= since:
        n = wave["left"]
        return f" · {n} judge{'s' if n != 1 else ''} left"
    return ""


def passes(c: Change, now: datetime) -> bool:
    """Whether the next step runs while Delivery is paused (TD-287, TD-303).

    A cleanup, or the brief challenge the owner's chat asked for and its decision pick; planning, building, publishing
    and merging wait for Resume.
    """
    step = loop.next_step(c, now)
    shaping = step is not None and step.kind == StepKind.SHAPE and (step.mode in MODES or picks.owed(c))
    return step is not None and (step.kind == StepKind.CLEANUP or shaping)


def status(c: Change, activity: Activity, now: datetime, tool: dict[str, Any] | None = None) -> Status:
    """Derive the status; while Delivery is paused, a step that would start waits for Resume instead (TD-282)."""
    line = _status(c, activity, now, tool)
    if not (activity.paused and activity.host_up) or c.finished_at:
        return line
    if activity.runner_alive:
        return Status(f"{stage(c)} · finishing {c.step.kind} (started before the restart)", None, "delivery")
    if passes(c, now):
        return line
    if line.actor in {"delivery", "github"}:  # nothing is observed or started until Resume
        return Status(f"{stage(c)} · Delivery is paused: continues after Resume", RESUME, "you")
    return line


def _status(  # noqa: C901, PLR0911, PLR0912 - D3 rules
    c: Change, activity: Activity, now: datetime, tool: dict[str, Any] | None = None
) -> Status:
    """Derive the status by the first matching rule; host-down overlays every unfinished Change."""
    s, o, stop = stage(c), c.outcome, activity.start_failure
    if not activity.host_up and not c.finished_at:
        if stop:
            return Status(f"{s} · stopped: {stop.reason}", stop.action, stop.actor)
        return Status(f"{s} · Delivery is not running", "Start Delivery", "you")
    if c.finished_at:
        if c.intent.abandoned_at:
            return Status("Abandoned · PR closed, branch kept", None, "delivery")
        if c.tests and c.tests.unchanged:  # the curator applied nothing: no PR was opened (TD-390)
            return Status("Done · no test changed", None, "delivery")
        saved = f" · unmerged work saved in {', '.join(c.names.preserved)}" if c.names.preserved else ""
        pr = f" PR #{c.names.pr}" if c.names.pr else ""
        if (p := c.pullback) and p.state == "behind":  # its reason reads "local <target> is behind: <why>"
            return Status(f"Done · merged{pr}{saved} · {p.reason}", "Pull on the Changes page", "you")
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
    if loop.usage_gated(c):
        return Status(f"{s} · stopped: {o.reason}", "Run this step again", "you")
    if o and o.exit == Exit.ASK:
        return Status(f"{s} · waiting for you: {o.reason}", "Approve merge" if o.cause == CONSENT else "Answer", "you")
    if o and o.exit == Exit.STOP and c.stop:
        return Status(f"{s} · stopped: {c.stop.reason}", c.stop.action, c.stop.actor)
    if o and o.exit == Exit.PENDING:
        if o.who == "you":
            action = _ACTION.get(o.waiting) if o.waiting else None
            return Status(f"{s} · waiting for you: {o.reason}", action, "you")
        if o.waiting == Waiting.REVIEWER:  # the reason names the reviewers
            return Status(f"{s} · {o.reason} (checked {_age(now - o.at)} ago)", None, o.who)
        wake = f", next try at {o.wake_at:%H:%M}" if o.wake_at else ""
        if (o.cause or "").endswith(f":{QUOTA}"):  # never asked about: the quota resets on its own
            used = f"{c.spend.shown()} used"
            return Status(f"{s} · waiting for Copilot quota to reset{wake} · {used}", None, o.who)
        if failing := _episode(c, now)[0]:
            capacity = (o.cause or "").startswith(f"{ErrorKind.CAPACITY}:")
            used = f" · {c.spend.shown()} used" if capacity else ""
            return Status(f"{s} · retrying: {o.reason} · {failing}{wake}{used}", None, o.who)
        who = _WHO.get(o.waiting, str(o.waiting)) if o.waiting else o.who
        return Status(f"{s} · waiting for {who}: {o.reason} (checked {_age(now - o.at)} ago)", None, o.who)
    if activity.runner_alive:
        task = next((t for t in c.plan.tasks if t.id == c.step.task), None) if c.plan else None
        items = sum(1 for t in c.plan.tasks if t.item and not t.done) if task and task.item and c.plan else 0
        label = (task.title if task else None) or next((f"check {p.id}" for p in c.checks if p.id == c.step.task), None)
        line = f"{s} · {verb}: {label or c.brief.title or c.brief.outcome}"
        if items:
            line += f" · {items} open conversation item{'s' if items > 1 else ''}"
        if c.tests and c.step.kind == StepKind.TESTS:
            line += f" · {sum(1 for x in c.tests.shares if x.ended)} of {len(c.tests.shares)} shares done"
        last = activity.last_event_at
        if gap := silent(c, activity, now, tool):
            return Status(f"{line} · no activity for {_age(gap)}", None, "delivery")
        if o and o.denial:
            return Status(f"{line} · last denied: {redact(o.denial)}", None, "delivery")
        return Status(f"{line} · {role} active {_age(now - last) if last else '0 s'} ago", None, "delivery")
    if o and o.exit == Exit.RETRY and o.wake_at and o.wake_at > now and o.cause:
        k = c.budgets.causes[o.cause].count if o.cause in c.budgets.causes else 1
        limit = WRONG_MODEL_LIMIT if o.cause.endswith(f":{WRONG_MODEL}") else RETRY_LIMIT
        return Status(f"{s} · retrying: {o.cause} ({k} of {limit}) at {o.wake_at:%H:%M}", None, "delivery")
    if activity.holder_pid:
        return Status(f"{s} · not running: waiting for process {activity.holder_pid} to end", None, "delivery")
    if activity.waiting_slot:
        return Status(f"{s} · waiting for a session slot ({activity.waiting_slot})", None, "delivery")
    return Status(f"{s} · not running: starting {role}", None, "delivery")
