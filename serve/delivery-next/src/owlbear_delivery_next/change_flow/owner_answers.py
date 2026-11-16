"""Owner answers that settle more than a step move: one that changes the brief (TD-185), or a visual round's (TD-79).

A conflict the design judge found between a design rule and the brief is never sent to the builder. The owner keeps
the brief with Pass, or takes the conflict: that answer starts the brief amendment for it alone.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts.models import ErrorKind
from owlbear_delivery_next.change_contracts.visual_records import OwnerDecision
from owlbear_delivery_next.change_flow import amending, answer_kinds, stuck
from owlbear_delivery_next.change_flow.moves import resume

if TYPE_CHECKING:
    from datetime import datetime

    from owlbear_delivery_next.change_contracts.inbox import AnswerItem, IntentItem
    from owlbear_delivery_next.change_contracts.models import Change, Question


def intent(c: Change, item: IntentItem) -> None:
    """Fold an owner's intent; approved work changes through an amendment, not a fresh shaping session."""
    match item.intent:
        case "pause":
            c.intent.paused_at, c.intent.pause_reason = item.at, item.text
        case "resume":
            resume(c)
        case "abandon":
            c.intent.abandoned_at = item.at
        case "change":
            c.intent.words = item.text
            if c.tests or c.brief.approved_version != c.brief.version:
                c.intent.hold = True
                return
            amending.left(c, "superseded by the owner's new request")
            stuck.retire(c, "the owner requested a brief amendment")
            stop, outcome = c.stop, c.outcome
            c.intent.hold = False
            amending.start(c, "request", reason=item.text, now=item.at)
            if stop and stop.kind == ErrorKind.LIVENESS:
                c.outcome = outcome  # the host must still verify that the previous step's processes ended
            else:
                c.stop = None


def admitted(q: Question) -> bool:
    """A worker menu with admitted actions, not a legacy menu or an engine gate."""
    return q.cause is None and not q.repair and bool(q.options) and all(o.action is not None for o in q.options)


def refused(q: Question, target: str | None, item: AnswerItem, decisions: frozenset[str]) -> bool:
    """Engine gates need their options; admitted worker choices also take continue or the owner's own words."""
    worker = admitted(q)
    text = item.statement if item.classed == "clarification" else item.text
    if worker and item.option is None and not text.strip():
        return True
    continuing = worker and (
        (item.option is None and bool(text.strip()))
        or any(o.id == item.option and o.action == "continue" and o.next is None for o in q.options)
    )
    unchosen = target is None and not continuing and bool(worker or {o.next for o in q.options} & decisions or q.repair)
    return unchosen or (target == "reconsider" and not item.text.strip())


def amended(
    c: Change, q: Question, item: AnswerItem, how: tuple[str | None, str | None, bool], now: datetime
) -> str | None:
    """An answer that changes the brief is never delivered: its amendment runs first (TD-185); None for others.

    A worker's question answered as a brief change starts it with the owner's words; a visual round's taken conflict
    with that conflict alone, while the Change waits on that round (*how*'s last part), or says why not.
    """
    kind, target, waits = how
    if kind == "brief_change":
        amending.start(c, "answer", reason=answer_kinds.answer_text(q), now=now, question=q.id)
        return ""
    if target != "amend":
        return None
    if not waits:  # a reshape since left the round's question behind: its conflicts are not this brief's
        q.answer = None
        return f"the Change moved on since question {q.id} asked"
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
