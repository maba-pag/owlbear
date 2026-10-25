"""A paid child session of a durable parent step (RUN-04): its run is kept until its verdict and spend commit together.

A plan challenge (TD-190) starts once the planned plan and its challenge mode are durable; an amendment challenge
(TD-179) once its candidate and the proposing step's effects, accounting and own route are. The child's validated run
is kept on the Change as soon as it returns, or in a capture file the next run adopts when that write fails, so a
failed settlement is resumed from it without a second paid session. It is not an owner hold: its usage, tool calls
and model check stay as the child reported them, so its own gates decide, and it counts once, in the write that
settles it, with a receipt of its session.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from pydantic import ValidationError

from owlbear_delivery_next.change_contracts.held_records import PendingChild
from owlbear_delivery_next.change_contracts.models import Exit, StepKind
from owlbear_delivery_next.change_contracts.round_records import RECHECK
from owlbear_delivery_next.change_flow import loop, plan_rounds
from owlbear_delivery_next.local_system.storage_io import atomic_write
from owlbear_delivery_next.runtimes import amendments, session_result
from owlbear_delivery_next.state_store.store import StoreError
from owlbear_delivery_next.workflow_steps import held, sessions

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from owlbear_delivery_next.change_contracts.amendment_records import Amendment
    from owlbear_delivery_next.change_contracts.models import Change, Step
    from owlbear_delivery_next.runtimes.session_result import Run
    from owlbear_delivery_next.state_store.store import Lock, Store

type Judged = tuple[loop.StepResult, Run]
CAPTURE = "child-"  # a returned child's run, kept in its own file when its Change write failed


def awaited(label: str, parent: str, route: loop.StepResult, step: Step) -> PendingChild:
    """The record of a child about to start, with the proposing step and its own route kept for its settlement."""
    return PendingChild(
        label=label, parent=parent, route=route.model_dump(mode="json"), step=(step.kind, step.task, step.mode)
    )


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
        _kept(store, lock, change, pending)
    return verdict, run


def _kept(store: Store, lock: Lock, change: Change, pending: PendingChild) -> None:
    """Make the returned child's run durable with its Change before its spend or verdict can be lost.

    When that write fails, the same run is kept in its capture file and the step stops; the next run adopts it into
    the Change it folds (`recovered`), so no second session is paid for it. When the capture fails too, the run is
    printed and the error says so: nothing claims it was kept.
    """
    try:
        store.write(lock, change)
    except (OSError, StoreError) as exc:
        try:
            atomic_write(_capture(store, change.slug, pending), pending.model_dump_json())
        except OSError as lost:
            unkept = {"event": "child-unkept", "slug": change.slug, "child": pending.model_dump(mode="json")}
            sessions.out(json.dumps(unkept))
            exc.add_note(f"the paid child's run could not be kept ({lost}); it is printed above")
        raise


def _capture(store: Store, slug: str, pending: PendingChild) -> Path:
    session = pending.run.session_id if pending.run is not None else ""
    return store.root / "changes" / slug / f"{CAPTURE}{session}.json"


def recovered(store: Store, lock: Lock, change: Change) -> Change:
    """A child run kept only in a capture file joins the folded Change's pending record, once (see `_kept`).

    A capture of a child the Change has counted, or keeps already, is removed. One whose Change waits on another
    child stays until that child settles, so its spend is never lost.
    """
    for path in sorted((store.root / "changes" / change.slug).glob(f"{CAPTURE}*.json")):
        try:
            captured = PendingChild.model_validate_json(path.read_text())
        except ValidationError as exc:
            msg = f"refusing child capture {path}: it is not a record this build reads; it is kept as is"
            raise StoreError(msg) from exc
        pending, run = change.pending_child, captured.run
        if run is None or run.session_id in change.counted_children or (pending and pending.run == run):
            path.unlink(missing_ok=True)
            continue
        if _awaits(pending, captured):
            change.pending_child = captured if pending is None else pending.model_copy(update={"run": run})
            store.write(lock, change)
            path.unlink(missing_ok=True)
    return change


def _awaits(pending: PendingChild | None, captured: PendingChild) -> bool:
    """The Change waits for the captured child: it keeps no child, or this child's record without its run."""
    if pending is None:
        return True
    return pending.run is None and (pending.label, pending.parent) == (captured.label, captured.parent)


def judgeable(verdict: loop.StepResult) -> bool:
    """A child verdict that judges, as the plan challenge counts one: not a stop, a wrong model or a failed session."""
    return verdict.cause is None and verdict.exit in {Exit.DONE, Exit.RETRY}


def booked(change: Change, run: Run, fields: dict[str, object]) -> dict[str, object] | None:
    """Count a kept child once and clear its record, in memory: the caller's one write commits both.

    Returns:
        Its step event, which the caller logs once that write is durable; None for a child that was not kept.
    """
    pending, change.pending_child = change.pending_child, None
    if pending is None or pending.run is None:
        return None
    change.counted_children = [*change.counted_children, run.session_id]
    return sessions.account(change, run, {"kind": pending.label} | fields)


def candidate(change: Change, pending: PendingChild) -> Amendment | None:
    """The amendment an amendment challenge judges."""
    return next((a for a in change.amendments if a.id == pending.parent), None)


def fits(change: Change) -> bool:
    """Whether the step the pending child answers is still the Change's own, so its verdict may still route it.

    An amendment's proposing step is the same step, task and mode on the brief version its candidate was prepared
    against, whatever its session: the owner's retry of a challenge reruns the challenger, never its proposer.
    """
    pending, s = change.pending_child, change.step
    if pending is None:
        return False
    if pending.label == amendments.LABEL:
        made = candidate(change, pending)
        if made is None or made.verdict or made.base != change.brief.version:
            return False
        return pending.step == (s.kind, s.task, s.mode)
    planned = change.plan is not None and str(change.plan.version) == pending.parent
    return planned and s.kind == StepKind.PLAN and s.mode in {plan_rounds.CHALLENGE, RECHECK}


def retired(store: Store, lock: Lock, change: Change) -> Change:
    """A pending child whose step the Change has left, after the owner's abandon or new brief: counted once, unrouted.

    Its spend and tool calls count, and an amendment keeps a verdict it judged; the step it would have routed is gone.
    A pause keeps the step, so its child waits and settles when the step runs again.
    """
    change = recovered(store, lock, change)
    pending = change.pending_child
    if pending is None or fits(change):
        return change
    step = None
    if pending.run is not None:
        run = held.accounted(pending.run)
        verdict = session_result.to_result(run, StepKind.REVIEW, datetime.now(UTC), change.step.kind)
        made = candidate(change, pending) if pending.label == amendments.LABEL else None
        if made is not None and not made.verdict and judgeable(verdict):
            amendments.judged(made, run)
        step = booked(change, run, {"exit": "retired"})
    change.pending_child = None
    store.write(lock, change)
    if step is not None:
        sessions.announce(store, lock, change.slug, step)
    return change
