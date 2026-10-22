"""An answer to a worker's question that changes the approved brief (TD-461; decision-intent-build §2, slice 5).

Whoever relays the owner's answer (a lead chat or the Changes page) classes it as an event, a clarification or a
brief change. A brief change, or a clarification its check found to change the brief, is never delivered: the work
stops with one owner question. Amendments are not built yet (item 16), so it offers to answer the worker's question
again within the brief, or to stop the Change.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from owlbear_decisions import new_id
from owlbear_delivery_next.change_contracts.failures import cause_key
from owlbear_delivery_next.change_contracts.inbox import AnswerItem
from owlbear_delivery_next.change_contracts.models import ErrorKind, Exit, Option, Outcome, Question

if TYPE_CHECKING:
    from collections.abc import Iterable

    from owlbear_delivery_next.change_contracts.inbox import InboxItem
    from owlbear_delivery_next.change_contracts.models import Change

SUBJECT = "brief-change"
WITHIN = "within"
OPTIONS = [
    Option(id=WITHIN, label="Answer within the brief", next="retry"),
    Option(id="stop", label="Stop the Change", next="abandon"),
]
TEXT = (
    'Your answer to the question "{asked}" changes the approved brief{why}, so it was not passed on. Changing an '
    "approved brief is not built yet. Answer within the brief: the question opens again for a new answer. Stop the "
    "Change: it is abandoned."
)


def logged(c: Change, items: Iterable[InboxItem], now: datetime) -> list[dict[str, Any]]:
    """An activity event per classed answer *c* recorded from *items*: the question's history shows its class."""
    kept = {(q.id, q.answer.at) for q in c.questions if q.answer and q.answer.kind}
    said = [i for i in items if isinstance(i, AnswerItem) and (i.question, i.at) in kept]
    return [{"event": "answer", "at": now.isoformat(timespec="seconds"), "question": i.question, "class": i.classed}
            for i in said]  # fmt: skip


def delivered_next(c: Change) -> Question | None:
    """The answered question of the current step whose answer the step's session receives next, if any.

    An answer that changes the brief, or a clarification not yet checked within it, is never delivered.
    """
    s = c.step
    return next(
        (q for q in reversed(c.questions) if q.step == s.kind and q.answer and not q.effect_observed_at
         and q.answer.kind != "brief_change" and not unchecked(c, q)),
        None,
    )  # fmt: skip


def decision_id(c: Change, q: Question) -> str:
    """The id of the decision *q*'s clarification becomes: the same on every check of the same answer."""
    at = q.answer.at if q.answer else datetime.now(UTC)
    return new_id(at, seed=f"{c.slug}\n{q.id}\n{at.isoformat()}\nclarification")


def unchecked(c: Change, q: Question) -> bool:
    """Whether *q*'s answer is a clarification its check has not yet found within the brief: no role reads it."""
    return bool(q.answer and q.answer.kind == "clarification") and all(d.id != decision_id(c, q) for d in c.decisions)


def first_unchecked(c: Change) -> Question | None:
    """The oldest clarification not yet checked, at whatever step it was asked or the Change now is."""
    return next((q for q in c.questions if unchecked(c, q)), None)


def question(c: Change, q: Question, why: str = "") -> Question:
    """The owner's question about the worker's question *q*, whose answer changes the brief, with *why* if known."""
    said = f" ({' '.join(why.split())[:300]})" if why.strip() else ""
    text = TEXT.format(asked=" ".join(q.text.split())[:300], why=said)
    cause = cause_key(ErrorKind.SCOPE, c.step.kind, f"{SUBJECT}:{q.id}")
    return Question(step=c.step.kind, text=text, options=[o.model_copy() for o in OPTIONS], cause=cause)


def owned(q: Question) -> bool:
    """Whether *q* asks about an answer that changes the brief."""
    parts = (q.cause or "").split(":")
    return len(parts) == 4 and parts[0] == ErrorKind.SCOPE and parts[2] == SUBJECT  # noqa: PLR2004 - kind:step:sub:q


def decided(c: Change, q: Question, target: str, at: datetime) -> None:
    """Answer within the brief: the worker's question is open again and its answer, never delivered, withdrawn."""
    asked = next((x for x in c.questions if x.id == (q.cause or "").rsplit(":", 1)[-1]), None)
    if target != "retry" or asked is None or asked.delivered_at is not None:
        return
    asked.answer = None
    c.outcome = Outcome(exit=Exit.ASK, reason=asked.text, who="you", question=asked.id, at=at)
