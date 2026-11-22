"""A synthetic Change stopped the way c8 stopped, for tests and the Changes page's preview; never the live store.

``deadline_stopped`` builds it through the engine's own transitions: build task t1's builder runs out of time twice
(attempt 2, ``liveness:build:deadline`` counted 2), Delivery's repair starts, and the repairer's own deadline ends that
repair, so ``repairs.done[0]`` holds it and the Change stops. ``credit_stopped`` is the same record whose repairer
instead hit its credit limit: the stop is the owner's credit-limit policy stop while the outcome keeps the deadline.
Importing this file reads and writes nothing.
"""

from __future__ import annotations

from datetime import UTC, datetime

from owlbear_delivery_next.change_contracts.failures import cause_key
from owlbear_delivery_next.change_contracts.models import (
    Change,
    ErrorKind,
    Exit,
    Names,
    Plan,
    Step,
    StepKind,
    Stop,
    Task,
)
from owlbear_delivery_next.change_flow import repair_recovery, stuck
from owlbear_delivery_next.change_flow.loop import StepResult, apply

__all__ = ["CAUSE", "NOW", "credit_stopped", "deadline_stopped"]

NOW = datetime(2026, 10, 10, 12, tzinfo=UTC)
CAUSE = cause_key(ErrorKind.LIVENESS, StepKind.BUILD, "deadline")


def _timed_out(slug: str, worktree: str) -> Change:
    plan = Plan(tasks=[Task(id="t1", title="Show the stopped step's rerun", checks=["uv run test"])])
    c = Change(slug=slug, plan=plan, step=Step(kind=StepKind.BUILD, task="t1"), names=Names(worktree=worktree))
    for _ in range(2):  # the second timeout of one cause starts Delivery's repair
        c = apply(c, StepResult(exit=Exit.RETRY, cause=CAUSE, reason="step deadline"), NOW)
    return c


def deadline_stopped(slug: str = "c1", worktree: str = "") -> Change:
    """Builder deadline twice, then the repairer's own deadline: the c8 shape."""
    c = _timed_out(slug, worktree)
    stuck.stopped(c, repair_recovery.REPAIRER_DEADLINE, NOW)
    return c


def credit_stopped(slug: str = "c1", worktree: str = "") -> Change:
    """Builder deadline twice, then the repairer's credit limit replaced the stop; the deadline cause stays."""
    c = _timed_out(slug, worktree)
    stuck.stopped(c, "its session's result was voided: credit limit reached: 5.00 of 5", NOW)
    c.stop = Stop(
        kind=ErrorKind.POLICY,
        reason="credit limit reached: 5.00 of 5",
        action="Raise the step's credit limit, or run it without one",
        resume="The step's credit limit allows it to finish",
        at=NOW,
    )
    return c
