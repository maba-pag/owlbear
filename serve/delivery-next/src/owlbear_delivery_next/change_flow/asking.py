"""One gate for every question recorded after brief approval (#1062, #1064; D-01M776YT24FGD86TMX9T682EHT).

D-01M6RT4ADHEEH6FFAF6HVW55QZ: after approval the owner is asked only what changes what he gets and what a decision
reserves for him; a question about Delivery's own problem (``subject="internal"``) is never recorded: its step is
repaired (``stuck.start``), else the Change stops with the whole evidence. D-01M6RT531EE3GHW2QGQQT63GZH: one cause
reaches him at most twice; its second question names the answer that did not resolve it, and its third goes the
internal way. A cause is a question's root: the question a worker's re-ask follows, else its engine cause (a
read-back of typed commands is part of the question it reads back), else the question itself.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts.failures import cause_key, kind_of
from owlbear_delivery_next.change_contracts.models import ErrorKind, Exit, Outcome, Stop

if TYPE_CHECKING:
    from datetime import datetime

    from owlbear_delivery_next.change_contracts.models import Change, Question

READ_BACK = "-typed-"  # the cause infix of a project-check read-back (``project_checks``): never a question of its own
LIMIT = 2  # questions one cause may put to the owner
RERUN = "Run the step again"


def root(q: Question) -> str:
    """The cause *q* asks about, as the limit counts it."""
    return q.follows or (q.cause or "").split(READ_BACK, 1)[0] or q.id


def _counted(c: Change, key: str) -> list[Question]:
    return [x for x in c.questions if root(x) == key and READ_BACK not in (x.cause or "")]


def offered(c: Change, q: Question, now: datetime) -> Question | None:
    """The question to record, with its preface on a cause's second question; None when it went elsewhere."""
    if c.brief.approved_version is None or READ_BACK in (q.cause or ""):
        return q
    if q.subject == "internal":
        routed(c, q.cause or "", q.text, now, root(q))
        return None
    key = root(q)
    earlier = _counted(c, key) if key else []
    if len(earlier) >= LIMIT:
        twice = ", ".join(x.id for x in earlier)
        said = f"{q.text}\n\nIt reached you twice already ({twice}): Delivery handles it now."
        routed(c, q.cause or cause_key(ErrorKind.PROJECT_ENV, c.step.kind, f"question-{key}"), said, now, key)
        return None
    if earlier and q.cause:  # a worker's re-ask says itself why (worker_questions.admitted)
        again = f"{failed(earlier[-1])} the same problem stopped the work again."
        return q.model_copy(update={"text": f"{again}\n\n{q.text}"})
    return q


def failed(prev: Question) -> str:
    """The second question's opening: which of the owner's answers did not resolve the cause."""
    a = prev.answer
    label = next((o.label for o in prev.options if a and o.id == a.option), "") if a else ""
    said = label or (a.text if a else "") or "no answer yet"
    return f"Your answer to {prev.id} ({said}) did not resolve this:"


def routed(c: Change, cause: str, evidence: str, now: datetime, key: str = "") -> None:
    """Repair the step when a repair can run, else stop it with the whole evidence; never a question."""
    from owlbear_delivery_next.change_flow import stuck  # noqa: PLC0415 - stuck asks through moves, which asks here

    if (r := c.repairs.current) is not None and r.cause == cause:  # the repair's own proposal, a third time
        stuck.stopped(c, "its fix would put the same problem to you a third time", now)
        return
    if stuck.repaired(c):
        stuck.start(c, cause, evidence, now, root=key)
        return
    stop(c, cause, "Delivery could not resolve this by itself", evidence, now)


def stop(c: Change, cause: str, reason: str, detail: str, now: datetime) -> None:
    """Stop the step for the owner's rerun, the plain reason first and the whole evidence after it."""
    kind = kind_of(cause)
    said = f"{reason}.\n\nDetails: {detail}"
    error = ErrorKind(kind) if kind in {e.value for e in ErrorKind} else ErrorKind.STATE
    c.stop = Stop(kind=error, reason=said, action=RERUN, resume="the step runs again", at=now)
    c.outcome = Outcome(exit=Exit.STOP, cause=cause, reason=said, who="you", at=now)
