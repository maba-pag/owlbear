"""The decisions a brief version's work follows, as its picker chose them (TD-459): owed, picked or failed.

The first challenge request for a version owes its pick; the runner picks before the challenger runs. A retry picks
again without a challenge round. Only a successful pick for the current version is approvable; a failed one is shown
with its reason, never as an empty set.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.change_contracts.decision_records import Pick
from owlbear_delivery_next.change_contracts.models import StepKind

if TYPE_CHECKING:
    from owlbear_delivery_next.change_contracts.models import Change

RETRY = "ask for it again: challenge_brief with retry_pick"


def current(c: Change) -> Pick | None:
    """The pick of the current brief version, if one was asked for."""
    p = c.brief.picked
    return p if p is not None and p.version == c.brief.version else None


def owed(c: Change) -> bool:
    """Whether the runner picks next for the current version."""
    return (p := current(c)) is not None and p.status == "owed"


def owe(c: Change) -> None:
    """A challenge request owes the current version's pick, once: a version picked or picking keeps its pick."""
    if current(c) is None:
        c.brief.picked = Pick(version=c.brief.version)


def retry(c: Change, version: int) -> str:
    """Pick *version* again after a failed pick or a changed list, without a challenge round; why not, or "".

    The runner picks during the chat's wait, which stays (`loop.next_step`).
    """
    b = c.brief
    if c.step.kind != StepKind.SHAPE or c.finished_at or c.intent.abandoned_at:
        return "the Change is not being shaped"
    if version != b.version:
        return f"brief v{version} is not the current draft v{b.version}"
    if b.approved_version == version:
        return f"brief v{version} is approved; its pick is pinned"
    if version not in {b.requested, b.challenged}:
        return f"ask for brief v{version}'s challenge first; its decisions are picked then"
    if owed(c):
        return f"the decisions of brief v{version} are being picked; ask again after it"
    c.brief.picked = Pick(version=version)
    return ""


def unready(c: Change) -> str:
    """Why the current version's pick keeps it from approval, as its record tells; "" without one."""
    p, v = current(c), c.brief.version
    if p is None or p.status == "ok":
        return ""
    if p.status == "owed":
        return f"Delivery picks the decisions brief v{v} must follow"
    return f"the picker failed: {p.reason}; {RETRY}"


def shown(c: Change) -> dict[str, Any] | None:
    """The current version's pick as the chat and the page show it: its state, reason and decision titles."""
    if (p := current(c)) is None:
        return None
    titles = [d.title for d in p.decisions]
    return {"version": p.version, "status": p.status, "reason": p.reason, "decisions": titles, "dropped": p.dropped}
