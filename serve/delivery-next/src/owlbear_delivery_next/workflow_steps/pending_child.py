"""A paid child session of a durable parent step (RUN-04): its run is kept until its verdict and spend commit together.

A plan challenge (TD-190) starts once the planned plan and its challenge mode are durable; an amendment challenge
(TD-179) once its candidate and the proposing step's effects, accounting and own route are. The child's validated run
is kept on the Change as soon as it returns, so a failed settlement is resumed from it without a second paid session.
It is not an owner hold: its usage, tool calls and model check stay as the child reported them, so its own gates
decide, and it counts once, in the write that settles it.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts.held_records import PendingChild
from owlbear_delivery_next.change_contracts.models import StepKind
from owlbear_delivery_next.change_contracts.round_records import RECHECK
from owlbear_delivery_next.change_flow import loop, plan_rounds
from owlbear_delivery_next.runtimes import amendments, session_result
from owlbear_delivery_next.workflow_steps import held, sessions

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_delivery_next.change_contracts.amendment_records import Amendment
    from owlbear_delivery_next.change_contracts.models import Change
    from owlbear_delivery_next.runtimes.session_result import Run
    from owlbear_delivery_next.state_store.store import Lock, Store

type Judged = tuple[loop.StepResult, Run]


def awaited(label: str, parent: str, route: loop.StepResult) -> PendingChild:
    """The record of a child about to start, with the proposing step's own route kept for its settlement."""
    return PendingChild(label=label, parent=parent, route=route.model_dump(mode="json"))


def route_of(pending: PendingChild) -> loop.StepResult:
    """The proposing step's own result, as it was before its child started."""
    if pending.route is None:
        msg = f"the pending {pending.label} keeps no result of the step that started it"
        raise ValueError(msg)
    return loop.StepResult.model_validate(pending.route)


def child(store: Store, lock: Lock, change: Change, parent: tuple[str, str], start: Callable[[], Judged]) -> Judged:
    """The child's verdict and run: its kept run when it returned before, else a session kept as soon as it returns.

    *parent* is the child's label and what it judges. A run that is not confirmed gone, or whose usage is unread,
    is not kept: the session's own gates decide it, as without a pending record.
    """
    pending = change.pending_child
    if pending is not None and pending.run is not None:
        run = held.accounted(pending.run)
        return session_result.to_result(run, StepKind.REVIEW, datetime.now(UTC), change.step.kind), run
    verdict, run = start()
    if sessions.deferrable(run):
        label, judged = parent
        pending = change.pending_child or PendingChild(label=label, parent=judged)
        pending.run = held.dump_run(run)
        change.pending_child = pending
        store.write(lock, change)  # the validated run is durable before its spend or verdict can be lost
    return verdict, run


def booked(change: Change, run: Run, fields: dict[str, object]) -> dict[str, object] | None:
    """Count a kept child once and clear its record, in memory: the caller's one write commits both.

    Returns:
        Its step event, which the caller logs once that write is durable; None for a child that was not kept.
    """
    pending, change.pending_child = change.pending_child, None
    if pending is None or pending.run is None:
        return None
    return sessions.account(change, run, {"kind": pending.label} | fields)


def candidate(change: Change, pending: PendingChild) -> Amendment | None:
    """The amendment an amendment challenge judges."""
    return next((a for a in change.amendments if a.id == pending.parent), None)


def fits(change: Change) -> bool:
    """Whether the step the pending child answers is still the Change's own, so its verdict may still route it."""
    pending, s = change.pending_child, change.step
    if pending is None:
        return False
    if pending.label == amendments.LABEL:
        made = candidate(change, pending)
        return made is not None and not made.verdict and (s.kind, s.session) == (made.step, made.session)
    planned = change.plan is not None and str(change.plan.version) == pending.parent
    return planned and s.kind == StepKind.PLAN and s.mode in {plan_rounds.CHALLENGE, RECHECK}


def retired(store: Store, lock: Lock, change: Change) -> Change:
    """A pending child whose step the Change has left, after the owner's abandon or new brief: counted once, unrouted.

    Its spend and tool calls count, and an amendment keeps its verdict; the step it would have routed is gone. A pause
    keeps the step, so its child waits and settles when the step runs again.
    """
    pending = change.pending_child
    if pending is None or fits(change):
        return change
    step = None
    if pending.run is not None:
        run = held.accounted(pending.run)
        if pending.label == amendments.LABEL and (made := candidate(change, pending)) is not None and not made.verdict:
            amendments.judged(made, run)
        step = booked(change, run, {"exit": "retired"})
    change.pending_child = None
    store.write(lock, change)
    if step is not None:
        sessions.announce(store, lock, change.slug, step)
    return change
