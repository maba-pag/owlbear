"""Shipped Delivery fixes that can resume an exhausted repair without repeating an unchanged attempt."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts.failures import kind_of
from owlbear_delivery_next.change_contracts.models import ErrorKind, Exit, StepKind
from owlbear_delivery_next.local_system import codebase

if TYPE_CHECKING:
    from owlbear_delivery_next.change_contracts.models import Change
    from owlbear_delivery_next.change_contracts.repair_records import Repair

FIXED = (1310, 1312)  # declarations travel with the corresponding code fixes, never inferred from version order
LEGACY = {
    "91b09919eb68085ecbcbabaf3ff9604cd27d898f6697ca168296f1f4ea269c22": (1310, "v1.279"),
    "94031b7acb33968ff62c895b8d03bc83786b9eb087e0a254ec928a7ef8834d74": (1312, "v1.284"),
}


def stopped(c: Change) -> Repair | None:
    """The exhausted repair bound to this exact stopped step, if any."""
    if not (c.stop and c.outcome and c.outcome.exit == Exit.STOP) or c.repairs.current:
        return None
    r = next((r for r in reversed(c.repairs.done) if r.cause == c.outcome.cause), None)
    if (
        r and r.phase in {"stopped", "applied"} and c.stop.kind == kind_of(r.cause)
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


def offered(c: Change) -> int | None:
    """One applicable fix absent from the stopped runtime; unknown legacy provenance admits nothing."""
    r = stopped(c)
    if r is None or r.recovered_with or c.finished_at or c.intent.abandoned_at or c.pending_child:
        return None
    if c.pending_question or any(q.answer is None for q in c.questions):
        return None
    old = _legacy(r) if c.stop.fixed_defects is None else None
    if c.stop.fixed_defects is None and old is None:
        return None
    if not version(c) or version(c) == codebase.release():
        return None
    task = next((t for t in c.plan.tasks if t.id == c.step.task), None) if c.plan else None
    for issue in FIXED:
        if issue in (c.stop.fixed_defects or []):
            continue
        url = f"https://github.com/maba-pag/owlbear/issues/{issue}"
        if url not in r.defect.split() and (old is None or old[0] != issue):
            continue
        if issue == 1312 and c.amending and r.cause == f"liveness:{c.step.kind}:runner-gone":
            return issue
        if (
            issue == 1310 and c.step.kind == StepKind.BUILD and c.stop.kind == ErrorKind.PROJECT_ENV
            and task and task.origin == "ci" and not task.done
        ):
            return issue
    return None


def action(c: Change, remedy: int) -> str:
    """The continuation the page can execute, not a generic parent-step rerun."""
    if remedy == 1312 and c.amending:
        return f"Continue amendment {c.amending.id}"
    return "Refresh CI evidence and run the build again"


def pending_ci(c: Change) -> Repair | None:
    """A consumed CI remedy whose current task still needs a fresh check observation."""
    if c.step.kind != StepKind.BUILD:
        return None
    return next(
        (r for r in reversed(c.repairs.done)
         if r.recovered_with == 1310 and r.refreshed_at is None and r.task == c.step.task),
        None,
    )
