"""A test review's moves (TD-373, TD-390): its reviewers' end, the curator's unchanged end, its fixed brief and plan."""

from __future__ import annotations

from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts.models import ErrorKind, Exit, Option, Outcome, StepKind, Stop
from owlbear_delivery_next.change_flow.moves import go

if TYPE_CHECKING:
    from datetime import datetime

    from owlbear_delivery_next.change_contracts.models import Change, Step

CURATE = "t1"  # the fixed plan's one task
FIXED = frozenset({StepKind.SHAPE, StepKind.PLAN})  # never entered: no shaping or planner runs (TD-390)


def reviewed(c: Change) -> None:
    """Every share ended: a share the owner went on without is not reviewed; the curator builds next."""
    for share in c.tests.shares if c.tests else []:
        share.ended = share.ended or "not-reviewed"
    go(c, StepKind.BUILD, CURATE)


def unchanged(c: Change) -> bool:
    """The curator applied nothing at the pinned commit: no review, PR or merge follows, only the cleanup."""
    if not (c.tests and c.tests.unchanged):
        return False
    go(c, StepKind.CLEANUP)
    return True


def without(c: Change) -> list[Option]:
    """While the reviewers run: the owner may go on with the shares that ended; the others are not reviewed."""
    go_on = Option(id="without", label="Go on without the unfinished shares", next="done")
    return [go_on] if c.tests and c.step.kind == StepKind.TESTS else []


def options(c: Change) -> list[Option]:
    """What the owner may do once a test review's step keeps failing: never revise or re-plan it."""
    return [
        Option(id="retry", label="Run it again", next="retry"),
        *without(c),
        Option(id="pause", label="Pause this Change", next="pause"),
        Option(id="abandon", label="Abandon the test review", next="abandon"),
    ]


def stop(c: Change, why: str, cause: str | None, now: datetime) -> None:
    """Stop a test review for the owner where it is, instead of shaping or planning it (TD-390)."""
    reason = f"a test review keeps its fixed brief and plan: {why}"[:300]
    action = 'Abandon the test review, or press "Done: run the step again" on the Changes page to run its step again'
    resume = 'You pressed "Done: run the step again"'
    c.stop = Stop(kind=ErrorKind.SCOPE, reason=reason, action=action, resume=resume, at=now)
    c.outcome = Outcome(exit=Exit.STOP, cause=cause, reason=reason, who="you", at=now)


def fixed(c: Change, before: Step, now: datetime) -> None:
    """A test review that would shape or plan stops there for the owner instead, on the step it was on (TD-390)."""
    if c.tests is None or c.step.kind not in FIXED or c.finished_at:
        return
    why = (c.outcome.reason if c.outcome else "") or f"it would go back to {c.step.kind}"
    c.step = before
    stop(c, why, c.outcome.cause if c.outcome else None, now)
