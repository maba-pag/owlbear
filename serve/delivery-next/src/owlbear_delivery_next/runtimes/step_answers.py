"""The owner's answers as a worker reads them: resumed into its session, or listed in a fresh one (TD-461).

A clarification reaches a worker only once its check found it within the brief, and then only as the statement the
owner confirmed: never the option label or his words. An answer that changes the brief never reaches one.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from owlbear_delivery_next.change_flow import answer_kinds, disputes

if TYPE_CHECKING:
    from owlbear_delivery_next.change_contracts.models import Change, Question


def _one(text: str, limit: int = 400) -> str:
    return " ".join((text if len(text) <= limit else text[:limit] + " ...(cut)").split())


def answer_text(question: Question) -> str:
    """The chosen option's label and the owner's words; a clarification's confirmed statement alone."""
    a = question.answer
    if a is None:
        return ""
    if a.kind == "clarification":
        return _one(a.statement)
    label = next((o.label for o in question.options if o.id == a.option), "")
    return _one(" - ".join(part for part in (label, a.text) if part))


def answered(change: Change, *, challenged: bool = False, own: str = "") -> list[str]:
    """The "answers so far" lines: no unchecked clarification and none a challenged review leaves out."""
    kept = [
        q for q in change.questions
        if q.answer and not disputes.hidden(q, challenged=challenged, own=own) and not answer_kinds.unchecked(change, q)
        and not answer_kinds.owned(q)  # its text says why the rejected clarification changed the brief
    ]  # fmt: skip
    return ["", "The owner's answers so far:", *(f"- {_one(q.text)}: {answer_text(q)}" for q in kept)] if kept else []


def answer(question: Question) -> str:
    """Return the message that delivers a stored answer to the resumed session."""
    return (
        f'The owner answered your question "{_one(question.text)}":\n> {answer_text(question)}\n'
        "Continue with this answer and end the step as the Finish section of your first message says."
    )
