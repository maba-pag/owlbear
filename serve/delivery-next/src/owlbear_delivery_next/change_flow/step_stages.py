"""A running step's stage, from its sessions' own events and never from a model (D-01M5WCF6TRXZD7MJG0HEZ4F482, #718).

Once a step's session opened, the SDK runtime marks every event it journals with the session and its role, and ends
each run of it with ``ended`` once its runtime stopped. A session's run belongs to the step when it opened in or after
the step's start second; a session resumed for an answer or a repair chance opens a new run under its old id.
Settlement's ``step`` events come later and are not read here.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.change_contracts.models import StepKind

if TYPE_CHECKING:
    from collections.abc import Sequence

    from owlbear_delivery_next.change_contracts.models import Change

RESULT_TOOLS = frozenset({
    "submit_result", "submit_first_look", "ask_question", "report_wrong_premise", "report_missing_tool",
})  # fmt: skip
_ENGINE = frozenset({StepKind.PUBLISH, StepKind.FOLLOW, StepKind.MERGE, StepKind.CLEANUP})
_HANDING = {
    "builder": "handing in its result", "reviewer": "handing in its verdict", "planner": "handing in the plan",
    "challenger": "handing in its findings",
}  # fmt: skip
_WORKING = {
    "builder": "implementing", "reviewer": "reviewing", "planner": "planning", "preparer": "preparing",
    "test-curator": "curating the tests",
}  # fmt: skip


@dataclass
class _Run:
    """One run of a session: its role, when its earliest retained event was, and its latest result call."""

    role: str
    at: datetime
    open: bool = True
    result: bool | None = None  # its latest result call since it opened: accepted, refused or none


def _runs(events: Sequence[dict[str, Any]], since: datetime) -> list[_Run]:
    """Each session's latest run that opened in or after *since*, in the order they opened."""
    found: dict[str, _Run] = {}
    for e in events:
        sid, role, at = e.get("session"), e.get("role"), e.get("at")
        if not (sid and role and isinstance(at, str)):
            continue  # a startup mark or Delivery's own event: no session of the step
        if e.get("event") == "session" or sid not in found:  # a new run, or one whose opening the store trimmed
            found.pop(sid, None)
            found[sid] = _Run(str(role), datetime.fromisoformat(at))
        run = found[sid]
        if e.get("event") == "ended":
            run.open = False
        elif e.get("event") == "tool" and e.get("tool") in RESULT_TOOLS:
            run.result = e.get("accepted", True) is not False
    return [r for r in found.values() if r.at >= since]


def _judge(c: Change, role: str) -> bool:
    return role in {"design-judge", "test-reviewer"} or (role == "reviewer" and c.step.kind == StepKind.CHECK)


def of(c: Change, events: Sequence[dict[str, Any]], own: str) -> str | None:  # noqa: PLR0911 - one rule per stage
    """The stage of *c*'s running step; None where the caller's words for its *own* role's work stand."""
    if c.step.kind in _ENGINE or c.step.started_at is None:
        return None
    runs = _runs(events, c.step.started_at.replace(microsecond=0))
    if not runs:
        return "starting"
    if running := [r for r in runs if r.open and _judge(c, r.role)]:
        if c.step.kind == StepKind.TESTS:
            return f"reviewing tests: {len(running)} running"
        done = sum(1 for r in runs if not r.open and _judge(c, r.role))
        return f"judging: {done} done, {len(running)} running"
    worker = next((r for r in reversed(runs) if r.open and r.role != "picker"), None)
    if worker and worker.result is False:
        return "fixing its refused result" if worker.role == "builder" else "correcting its refused result"
    if worker and worker.result:
        return _HANDING.get(worker.role, "handing in its result")
    if any(r.open and r.role == "picker" for r in runs):
        return "checking decisions"
    if worker is None:
        return "recording the result"
    if worker.role == "challenger":
        return {StepKind.SHAPE: "challenging the brief", StepKind.PLAN: "challenging the plan"}.get(
            c.step.kind, "challenging"
        )
    if worker.role == "planner" and c.outcome and c.outcome.challenged:
        return "revising for the challenge's findings"
    return None if worker.role == own else _WORKING.get(worker.role)
