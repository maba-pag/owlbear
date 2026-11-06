"""The brief as the Change page shows it: its content, why it can't be approved yet, and its versions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.change_flow import brief_rounds, brief_starts, picks, versions
from owlbear_delivery_next.project_host import shaping_chat
from owlbear_delivery_next.state_store import decision_store
from owlbear_delivery_next.state_store.briefs import unrevisable
from owlbear_delivery_next.workflow_steps import decisions_gate

if TYPE_CHECKING:
    from owlbear_delivery_next.change_contracts.models import Change
    from owlbear_delivery_next.state_store.store import Store

PICK_AGAIN = "use Pick the decisions again under Open items"  # the page's way to the chat's retry_pick


def shown(store: Store, c: Change, *, paused: bool = False) -> dict[str, Any]:
    """The detail's ``brief`` block."""
    b = c.brief
    return {
        "version": b.version,
        "chat": shaping_chat.shown(c, paused=paused),
        "approved": b.approved_version,
        "title": b.title,
        "outcome": b.outcome,
        "scope": b.scope,
        "non_goals": b.non_goals,
        "decisions": [x.model_dump(exclude={"id", "replaces"}) for x in b.decisions],  # as drafted
        "specified": b.specified,
        "approved_at": b.approved_at.isoformat() if b.approved_at else None,
        "ui": b.ui,
        "visual": [s.model_dump() for s in b.visual],
        **approve(c),  # TD-249, #986: why Approve is off; the shaping chat reads brief_rounds.approvable as before
        "revising": brief_rounds.revising(c),  # the findings the shaper revises this version for
        "unrevisable": unrevisable(c),  # why no new shaping chat may revise the saved brief
        "unreviewed": brief_rounds.unreviewed(c),  # TD-255: approving needs the owner's tick
        "read_backs": decisions_gate.checkpoint(store, c),  # TD-427: at most three, never blocking
        "picked": picks.shown(c),  # TD-459: the decisions this version's work follows, by title
        **placed(store, c),  # where each picked decision applies, for the page's grouped list
        "versions": versions.brief(c),  # each version's state and the challenges that read it
    }


def approve(c: Change) -> dict[str, Any]:
    """Approve's state (#986): why it is off, a refusal of the approval the owner asked for, and the start time."""
    b, o, waits = c.brief, c.outcome, brief_starts.waiting(c)
    if waits:
        off = "this Change is paused: resume it to approve" if c.intent.paused_at else ""
    elif b.approve_if_clean == b.version and c.step.mode in brief_rounds.MODES:
        off = f"the challenge of brief v{b.version} is running; your approval takes effect if it is clean"
    else:
        off = brief_rounds.approvable(c).replace(picks.RETRY, PICK_AGAIN)
    refused = o.reason if o and o.cause == brief_starts.REFUSED else ""
    starts = o.wake_at.isoformat() if waits and o and o.wake_at else None
    return {"approve_off": off, "approve_refused": refused, "challenge_waits": waits, "starts_at": starts}


def placed(store: Store, c: Change) -> dict[str, Any]:
    """The current pick's decisions with the scope and state the decision list holds now, or why it can't be read.

    An id the list no longer holds keeps its stored title with no scope; nothing is read without a picked decision.
    """
    p = picks.current(c)
    if p is None or not p.decisions:
        return {"picked_items": None, "picked_unavailable": None}
    try:
        seen = decision_store.load(store.shared, store.name).snapshot
    except decision_store.DecisionsUnavailable as exc:
        return {"picked_items": None, "picked_unavailable": str(exc)}
    items = []
    for d in p.decisions:
        e = seen.get(d.id)
        held = {"scope": str(e.decision.scope), "state": str(e.decision.state)} if e else {"scope": None, "state": None}
        items.append({"id": d.id, "title": d.title, **held})
    return {"picked_items": items, "picked_unavailable": None}
