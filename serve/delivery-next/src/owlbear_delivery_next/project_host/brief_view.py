"""The brief as the Change page shows it: its content, why it can't be approved yet, and its versions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.change_flow import brief_rounds, picks, versions
from owlbear_delivery_next.state_store.briefs import unrevisable
from owlbear_delivery_next.workflow_steps import decisions_gate

if TYPE_CHECKING:
    from owlbear_delivery_next.change_contracts.models import Change
    from owlbear_delivery_next.state_store.store import Store


def shown(store: Store, c: Change) -> dict[str, Any]:
    """The detail's ``brief`` block."""
    b = c.brief
    return {
        "version": b.version,
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
        "unapprovable": brief_rounds.approvable(c),  # TD-249: why the approve button is off
        "revising": brief_rounds.revising(c),  # the findings the shaper revises this version for
        "unrevisable": unrevisable(c),  # why no new shaping chat may revise the saved brief
        "unreviewed": brief_rounds.unreviewed(c),  # TD-255: approving needs the owner's tick
        "read_backs": decisions_gate.checkpoint(store, c),  # TD-427: at most three, never blocking
        "picked": picks.shown(c),  # TD-459: the decisions this version's work follows, by title
        "versions": versions.brief(c),  # each version's state and the challenges that read it
    }
