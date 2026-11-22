"""Shipped Delivery fixes that can resume an exhausted repair without repeating an unchanged attempt."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts.failures import cause_key, kind_of
from owlbear_delivery_next.change_contracts.models import VISUAL, ErrorKind, Exit, StepKind
from owlbear_delivery_next.change_flow import asking, moves, plan_rounds
from owlbear_delivery_next.local_system import codebase

if TYPE_CHECKING:
    from owlbear_delivery_next.change_contracts.inbox import Recovery
    from owlbear_delivery_next.change_contracts.models import Change
    from owlbear_delivery_next.change_contracts.repair_records import Repair

CI_LOG, AMENDMENT_EXIT, MERGE_BASIS, PLAN_CUT = 1310, 1312, 1342, 1361
FIXED = (CI_LOG, AMENDMENT_EXIT, MERGE_BASIS, PLAN_CUT)  # travels with actual fixes, never inferred from version order
LEGACY = {
    "91b09919eb68085ecbcbabaf3ff9604cd27d898f6697ca168296f1f4ea269c22": (1310, "v1.279"),
    "94031b7acb33968ff62c895b8d03bc83786b9eb087e0a254ec928a7ef8834d74": (1312, "v1.284"),
}
REPAIRER_DEADLINE = "its own step deadline ended the repair before it proved a fix"
DEFECT = " OwlBear defect issue: "  # a stopped repair's reason ends with it once it filed a defect issue
OWN = {StepKind.PLAN: {None}, StepKind.BUILD: {None}, StepKind.CHECK: {None}, StepKind.REVIEW: {None, "final"}}


def stopped(c: Change) -> Repair | None:
    """The exhausted repair bound to this exact stopped step, if any."""
    if not (c.stop and c.outcome and c.outcome.exit == Exit.STOP) or c.repairs.current:
        return None
    r = next((r for r in reversed(c.repairs.done) if r.cause == c.outcome.cause), None)
    if (
        r
        and r.phase in {"stopped", "applied"}
        and c.stop.kind == kind_of(r.cause)
        and (r.step, r.task) == (c.step.kind, c.step.task)
    ):
        return r
    return None


def _legacy(r: Repair) -> tuple[int, str] | None:
    return LEGACY.get(hashlib.sha256(f"{r.evidence}\0{r.found}".encode()).hexdigest())


def version(c: Change) -> str:
    """The stopped runtime from its receipt, or an exact, source-verified legacy incident."""
    if c.stop and c.stop.runtime:
        return c.stop.runtime
    r = stopped(c)
    old = _legacy(r) if r else None
    return old[1] if old else ""


def inventory(c: Change) -> bool:
    """The pre-fix no-repair inventory stop, not another gate or a newly exhausted allowance."""
    q = next((q for q in reversed(c.questions) if (q.cause or "").startswith(asking.DECLARED) and q.answer), None)
    if not asking.inventory_stop(c) or q is None or c.stop is None or c.outcome is None:
        return False
    expected = ", ".join(q.id for q in c.questions if asking.root(q) == asking.DECLARED.rstrip("-"))
    return bool(
        asking.legacy_inventory(q)
        and q.ci_basis is None
        and q.cause == c.outcome.cause
        and c.stop.action == asking.RERUN
        and c.stop.resume == "the step runs again"
        and c.stop.reason.startswith("Delivery could not resolve this by itself.\n\nDetails: ")
        and c.stop.reason.endswith(f"It reached you twice already ({expected}): Delivery handles it now.")
        and not any(r.step in {StepKind.FOLLOW, StepKind.MERGE} for r in c.repairs.done)
    )


def _gate(c: Change) -> bool:
    """Whether another gate is open that a stop's continuation must not bypass."""
    return bool(
        c.finished_at
        or c.intent.abandoned_at
        or c.pending_child
        or c.pending_question
        or c.blocked
        or c.amending
        or c.queue
        or any(q.answer is None for q in c.questions)
    )


def offered(c: Change) -> int | None:
    """One applicable fix absent from the stopped runtime; unknown legacy provenance admits nothing."""
    if (
        MERGE_BASIS in FIXED
        and inventory(c)
        and c.stop
        and MERGE_BASIS not in (c.stop.fixed_defects or [])
        and not _gate(c)
    ):
        return MERGE_BASIS
    return _repair(c)


def _bound(c: Change) -> list[Repair]:
    """The finished repairs of this step's cause, on this step and task."""
    cause = c.outcome.cause if c.outcome else None
    return [r for r in c.repairs.done if (r.cause, r.step, r.task) == (cause, c.step.kind, c.step.task)]


def deadline(c: Change) -> bool:
    """Whether the step's own session deadline identifiably stopped it and one owner-confirmed rerun is open.

    The stop agrees with its liveness deadline cause (a policy or credit stop replacing it never qualifies), the
    step's mode runs that step's own role, no other gate is open and no repair of the cause was rerun already.
    """
    s, o, stop = c.step, c.outcome, c.stop
    if not (stop and o and o.exit == Exit.STOP and stop.kind == ErrorKind.LIVENESS) or c.repairs.current:
        return False
    if o.cause != cause_key(ErrorKind.LIVENESS, s.kind, "deadline") or s.mode not in OWN.get(s.kind, ()):
        return False
    if (s.kind, s.task) == (StepKind.CHECK, VISUAL) or _gate(c):
        return False
    return all(r.recovered_at is None for r in _bound(c))


def repairer_timed_out(c: Change) -> bool:
    """Whether the exhausted repair of this deadline stop ended on the repairer's own deadline."""
    r = stopped(c)
    return bool(r and (r.stopped == REPAIRER_DEADLINE or r.stopped.startswith(f"{REPAIRER_DEADLINE}.{DEFECT}")))


def _repair(c: Change) -> int | None:
    """An applicable fix for a recorded repair."""
    r, stop = stopped(c), c.stop
    if r is None or stop is None or r.recovered_with or c.finished_at or c.intent.abandoned_at or c.pending_child:
        return None
    if c.pending_question or any(q.answer is None for q in c.questions):
        return None
    old = _legacy(r) if stop.fixed_defects is None else None
    if (stop.fixed_defects is None and old is None) or not version(c) or version(c) == codebase.release():
        return None
    task = next((t for t in c.plan.tasks if t.id == c.step.task), None) if c.plan else None
    for issue in FIXED:
        if issue in (stop.fixed_defects or []):
            continue
        url = f"https://github.com/maba-pag/owlbear/issues/{issue}"
        if url not in r.defect.split() and (old is None or old[0] != issue):
            continue
        amendment = issue == AMENDMENT_EXIT and c.amending and r.cause == f"liveness:{c.step.kind}:runner-gone"
        ci = (
            issue == CI_LOG
            and c.step.kind == StepKind.BUILD
            and stop.kind == ErrorKind.PROJECT_ENV
            and task
            and task.origin == "ci"
            and not task.done
        )
        plan = issue == PLAN_CUT and c.step.kind == StepKind.PLAN and c.step.mode == plan_rounds.CHALLENGE
        if amendment or ci or (plan and not c.amending):
            return issue
    return None


def action(c: Change, remedy: int) -> str:
    """The continuation the page can execute, not a generic parent-step rerun."""
    if remedy == MERGE_BASIS:
        return "Recheck merge checks and continue"
    if remedy == AMENDMENT_EXIT and c.amending:
        return f"Continue amendment {c.amending.id}"
    if remedy == PLAN_CUT:
        return "Challenge the whole plan again"
    return "Refresh CI evidence and run the build again"


def pending_ci(c: Change) -> Repair | None:
    """A consumed CI remedy whose current task still needs a fresh check observation."""
    if c.step.kind != StepKind.BUILD or c.plan is None:
        return None
    return next(
        (
            r
            for r in reversed(c.repairs.done)
            if r.recovered_with == CI_LOG
            and r.refreshed_at is None
            and r.recovered_plan == c.plan.version
            and r.task == c.step.task
        ),
        None,
    )


def _rerun(c: Change, item: Recovery) -> bool:
    """Run a deadline-stopped step once more, keeping its work, gates and cause's count; True when it did."""
    if not (c.stop and item.action == asking.RERUN and item.stop_at == c.stop.at and deadline(c)):
        return False
    for r in _bound(c):
        r.recovered_at = item.at  # the count stays: a repeat timeout is repaired as usual
    moves.go(c, c.step.kind, c.step.task, c.step.mode)
    c.stop = c.outcome = None
    return True


def consume(c: Change, item: Recovery, *, unchanged: bool) -> None:
    """Recheck the queued stop and fix against the code actually folding the owner's action."""
    if c.stop is None or (item.stop_at is not None and item.stop_at != c.stop.at):
        return
    if item.remedy is None:
        if not _rerun(c, item) and unchanged and item.action == c.stop.action and not asking.inventory_stop(c):
            c.stop = c.outcome = None
        return
    remedy, r = offered(c), stopped(c)
    if remedy is None or item.remedy != remedy or item.action != action(c, remedy):
        return
    if remedy == MERGE_BASIS:
        if item.stop_at != c.stop.at:
            return
        c.stop = c.outcome = None
        return
    if r is None:
        return
    r.recovered_with, r.recovered_at = remedy, item.at
    r.recovered_plan = c.plan.version if c.plan else None
    c.budgets.causes.pop(r.cause, None)
    moves.go(c, c.step.kind, c.step.task, c.step.mode)
    c.stop = c.outcome = None
