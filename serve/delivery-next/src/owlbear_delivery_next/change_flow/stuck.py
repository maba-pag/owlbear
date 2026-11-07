"""A stuck step's repair: the one entry point for a cause and the step's evidence (#1065, #1066).

Setup problems arrive here once (D-01M6RT5QHWHB0ZHBBY0BE34FBE), and the same cause the second time it stops a step
(D-01M6RT5QHXFM58C9BPQXEK3QFB); #1062, #1064 and a red CI after publishing hand their causes to ``start`` too. The
stuck step stays the Change's step while ``workflow_steps.step_repair`` finds the cause and proves a fix in a throwaway
copy: a fix in Delivery's reach is applied and the step runs again; another is the owner's yes or no; when nothing
works the Change stops listing every fix tried and what the repair spent. Credits never decide
(D-01M5DW3X00SM0ZRT4DWY35VV3A).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts.failures import kind_of
from owlbear_delivery_next.change_contracts.models import ErrorKind, Exit, Option, Outcome, Question, StepKind, Stop
from owlbear_delivery_next.change_contracts.repair_records import Repair
from owlbear_delivery_next.change_flow.moves import ask, go

if TYPE_CHECKING:
    from datetime import datetime

    from owlbear_delivery_next.change_contracts.models import Change

APPLY, DECLINE = "repair-apply", "repair-stop"
REPAIRED = frozenset({StepKind.PLAN, StepKind.BUILD, StepKind.REVIEW, StepKind.CHECK})  # agent steps


def start(c: Change, cause: str, evidence: str, now: datetime) -> None:
    """Repair the step *c* is on, stopped by *cause*; *evidence* is what the step reported, whole.

    A cause that comes back after its repair's fix was applied stops instead of being repaired again.
    """
    s = c.step
    if again := next((r for r in reversed(c.repairs.done) if r.cause == cause and r.phase == "applied"), None):
        said = f"needs repair again: {evidence}; it came back after its repair applied {again.applied[:12]}"
        _stop(c, cause, said, now)
        return
    c.repairs.current = Repair(cause=cause, evidence=evidence, step=s.kind, task=s.task, mode=s.mode, at=now)
    c.stop = None
    c.outcome = Outcome(exit=Exit.RETRY, cause=cause, reason=f"repairing: {obstruction(evidence)}", at=now)


def obstruction(evidence: str) -> str:
    """The first sentence of what stopped the step, as the owner reads it in the status line."""
    first = evidence.strip().splitlines()[0] if evidence.strip() else "the step stopped"
    return first.split(". ", 1)[0]


def repaired(c: Change) -> bool:
    """Whether a counted cause the second time is this step's to repair, rather than its own loop's or the owner's."""
    return c.step.kind in REPAIRED and c.tests is None and c.repairs.current is None


def asked(c: Change, text: str, now: datetime) -> None:
    """The proven fix is the owner's yes or no: it reaches outside the brief or touches a file reserved for him."""
    r = c.repairs.current
    assert r is not None  # noqa: S101 - only a running repair asks
    options = [
        Option(id="yes", label="Apply the fix and run the step again", next=APPLY),
        Option(id="no", label="Don't apply it; stop with what was tried", next=DECLINE),
    ]
    ask(c, Question(step=c.step.kind, text=text, options=options, cause=r.cause), now)
    r.phase, r.question = "asked", c.questions[-1].id


def owned(c: Change, question: str) -> bool:
    """Whether *question* is the running repair's own."""
    r = c.repairs.current
    return r is not None and r.phase == "asked" and r.question == question


def decided(c: Change, target: str, now: datetime) -> None:
    """The owner's yes applies the fix at the next pass; his no stops the Change with what was tried."""
    r = c.repairs.current
    assert r is not None  # noqa: S101 - owned() checked it
    if target == APPLY:
        r.phase = "approved"
        c.outcome = Outcome(exit=Exit.RETRY, cause=r.cause, reason=f"applying the repair of {r.cause}", at=now)
    else:
        stopped(c, "you declined the fix", now)


def applied(c: Change, commit: str) -> None:
    """The fix is on the Change's branch (or in the profile): the cause's count starts again and the step reruns."""
    r = c.repairs.current
    assert r is not None  # noqa: S101 - only a repair applies
    r.phase, r.applied = "applied", commit
    c.repairs.done.append(r)
    c.repairs.current = None
    c.budgets.causes.pop(r.cause, None)
    go(c, StepKind(r.step), r.task, r.mode)
    c.outcome = None


def stopped(c: Change, why: str, now: datetime) -> None:
    """Nothing worked, a fix was refused or declined: stop listing every fix tried and the repair's spend."""
    r = c.repairs.current
    assert r is not None  # noqa: S101 - only a repair stops
    tried = " ".join(f"{i}. {t.fix}: {t.outcome}" for i, t in enumerate(r.tried, 1)) or "nothing"
    spent = f"{r.credits:.2f} credits" if r.credits is not None else "an unknown number of credits"
    found = f" It found: {r.found}." if r.found else ""
    r.phase, r.stopped = "stopped", why
    c.repairs.done.append(r)
    c.repairs.current = None
    _stop(c, r.cause, f"repair stopped, {why}: {r.evidence}.{found} Tried: {tried} Spent {spent}.", now)


def _stop(c: Change, cause: str, reason: str, now: datetime) -> None:
    c.stop = Stop(
        kind=ErrorKind(kind_of(cause)), reason=reason, action=f"Resolve {cause}", resume="the step runs again", at=now
    )
    c.outcome = Outcome(exit=Exit.STOP, cause=cause, reason=reason, who="you", at=now)
