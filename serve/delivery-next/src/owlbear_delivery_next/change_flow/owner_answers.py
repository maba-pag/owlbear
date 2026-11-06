"""Owner answers that settle more than a step move: one that changes the brief (TD-185), or a visual round's (TD-79).

A conflict the design judge found between a design rule and the brief is never sent to the builder. The owner keeps
the brief with Pass, or takes the conflict: that answer starts the brief amendment for it alone.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts.visual_records import OwnerDecision
from owlbear_delivery_next.change_flow import amending

if TYPE_CHECKING:
    from datetime import datetime

    from owlbear_delivery_next.change_contracts.inbox import AnswerItem
    from owlbear_delivery_next.change_contracts.models import Change, Question


def amended(c: Change, q: Question, item: AnswerItem, how: tuple[str | None, str | None], now: datetime) -> str | None:
    """An answer that changes the brief is never delivered: its amendment runs first (TD-185); None for others.

    A worker's question answered as a brief change starts it with the owner's words; a visual round's taken conflict
    with that conflict alone, or says why not.
    """
    kind, target = how
    if kind == "brief_change":
        amending.start(c, "answer", reason=item.text, now=now, question=q.id)
        return ""
    if target != "amend":
        return None
    ident, kept = item.text.strip(), c.visual_rounds[-1] if c.visual_rounds else None
    k = next((k for v in (kept.verdicts if kept else []) for k in v.conflicts if k.id == ident), None)
    if k is None or k.departs in kept.owner:  # an owner's criterion is withdrawn, not amended
        q.answer = None
        return f"question {q.id}: the last visual round has no conflict {ident} with the brief to take"
    where = f"{k.state}{f' at {k.width}px' if k.width else ''}"
    said = f"The owner takes the design judge's conflict {k.id} ({where}, {k.rule}): {k.text.rstrip('.')}"
    said += f". It departs from {k.departs}"
    amending.start(c, "answer", reason=said, evidence=[said], now=now, question=q.id)
    return ""


def decided(c: Change, decision: str, item: AnswerItem) -> None:
    """Record the owner's decision on the round it was about, while that round still waits for it (TD-79)."""
    kept = c.visual_rounds[-1] if c.visual_rounds else None
    if kept and kept.number == item.round and kept.outcome == "ask" and kept.decision is None:
        outcome = "pass" if decision == "accept" else "fail"
        kept.decision = OwnerDecision(outcome=outcome, findings=item.findings, comment=item.text, at=item.at)
