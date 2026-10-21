"""The read-back queue (TD-427, §8): what waits for the owner, most urgent first, then oldest first."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from owlbear_decisions.models import ReadBackKind, State

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable

    from owlbear_decisions.models import Decision

ORDER = tuple(ReadBackKind)
CONFLICT = "It is flagged in conflict with another successor of the same decision; resolve it by keeping one."


@dataclass(frozen=True)
class Queued:
    """A decision waiting to be read back; *derived* when only its `conflict` flag queues it (nothing is written)."""

    decision: Decision
    kind: ReadBackKind
    why: str
    derived: bool


def queued(decision: Decision) -> Queued | None:
    """The decision's place in the queue: a pending read-back, or a conflict (blocked work); else None."""
    if decision.state not in {State.DRAFT, State.IN_FORCE}:
        return None
    pending = decision.read_back == "pending" and decision.read_back_kind is not None
    if not (pending or decision.conflict):
        return None
    kinds = [decision.read_back_kind] if pending else []
    if decision.conflict:
        kinds.append(ReadBackKind.BLOCKED)
    kind = min(kinds, key=ORDER.index)
    return Queued(decision, kind, decision.read_back_why if pending else CONFLICT, derived=not pending)


def queue(decisions: Iterable[Decision], last: Collection[str] = ()) -> list[Queued]:
    """The waiting read-backs in order: by kind, then oldest decision first; the ids in *last* go to the bottom."""
    found = [q for d in decisions if (q := queued(d)) is not None]
    return sorted(
        found, key=lambda q: (q.decision.id in last, ORDER.index(q.kind), q.decision.created_at, q.decision.id)
    )
