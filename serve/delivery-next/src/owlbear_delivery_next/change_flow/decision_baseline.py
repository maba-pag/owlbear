"""The owner's answer to a decisions question: continue on the decisions now in force, or pause (TD-419 slice 4)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

    from owlbear_delivery_next.change_contracts.decision_records import DecisionBaseline
    from owlbear_delivery_next.change_contracts.models import Change, Question

PREFIX = "decisions:"


def owned(q: Question) -> bool:
    """A question the runner's decision gate asked."""
    return (q.cause or "").startswith(PREFIX)


def approved(c: Change, baseline: DecisionBaseline | None, unpinned_at: datetime | None = None) -> None:
    """A brief approval pins its decisions; *unpinned_at*: they could not be read, so the owner confirms them later."""
    c.decisions_baseline, c.decisions_offered, c.decisions_unpinned_at = baseline, None, unpinned_at


def decided(c: Change, target: str) -> None:
    """The owner's Continue pins the set the question showed; a later difference asks again. The brief stays."""
    if target == "accept" and c.decisions_offered is not None:
        c.decisions_baseline, c.decisions_unpinned_at = c.decisions_offered, None
    c.decisions_offered = None
