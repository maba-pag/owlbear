"""Why the host refuses an answer's selection: a visual round's decision (TD-79) or a final retry's tasks (TD-217)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from owlbear_delivery_next import rebuilds
from owlbear_delivery_next.steps import decision

if TYPE_CHECKING:
    from owlbear_delivery_next.api import AnswerBody
    from owlbear_delivery_next.models import Change, Question


def refused(c: Change, q: Question, body: AnswerBody) -> tuple[int, str] | None:
    """The status and reason a Changes-page answer is refused with, or None."""
    if q.cause == decision.CAUSE and body.option in {"pass", "fail"}:
        return _visual(c, body)
    return rebuilds.refused(c, q, body.option, body.tasks, (body.attempt, body.head))


def _visual(c: Change, body: AnswerBody) -> tuple[int, str] | None:
    """Why a Pass or Fail is refused: its round, capture or pack changed since the page showed them, or it is empty."""
    kept = c.visual_rounds[-1] if c.visual_rounds else None
    shown = (body.round, body.head, body.pack)
    if kept is None or kept.outcome != "ask" or kept.decision or shown != (kept.number, kept.head, kept.pack):
        return 409, "the capture or the design pack changed since the page was shown; reload"
    if unknown := sorted(set(body.findings) - {f.id for v in kept.verdicts for f in v.findings}):
        return 422, f"findings {unknown} are not in round {kept.number}"
    if body.option == "fail" and not body.findings and not body.text.strip():
        return 422, "a Fail ticks a finding or says what is wrong"
    return None
