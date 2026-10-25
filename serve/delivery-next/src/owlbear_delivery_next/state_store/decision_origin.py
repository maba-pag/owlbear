"""The owner's origin correction: a decision he never decided is marked as what it was (2026-10-23).

An origin is lowered only (`decided`, `approved`, `autonomous`), on his confirmed statement, such as `decided` to
`approved` for an agent's proposal he accepted without intent of his own (TD-179). An accepted decision's origin never
changes in place (TD-430), so one in force gets a successor with the same rule which replaces it; a draft is corrected
in place.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from owlbear_decisions import Decision, Link, LinkType, Origin, State
from owlbear_delivery_next.change_contracts import decision_wording
from owlbear_delivery_next.state_store import decision_store
from owlbear_delivery_next.state_store.decision_actions import (
    EFFECT,
    EFFECTS,
    LINEAGE,
    RETIRED,
    Refused,
    _because,
    _entry,
    _marked,
    _new,
    _reason,
    _retire,
    _stale,
    rivals,
)

if TYPE_CHECKING:
    from owlbear_delivery_next.local_system.data_repo import DataRepo
    from owlbear_delivery_next.state_store.decision_store import Receipt

CORRECTED = "Origin corrected: "
AUTHORITY = {Origin.AUTONOMOUS: 0, Origin.APPROVED: 1, Origin.DECIDED: 2}
UNSTATED = "only the owner corrects an origin: read his statement back to him, then pass confirmed=true"


def correct_origin(  # noqa: PLR0913 - the owner's statement, the new origin and the revision read
    shared: DataRepo | None, project: str, decision_id: str, revision: str, *, origin: Origin, reason: str,
    confirmed: bool, by: str,
) -> list[Receipt]:  # fmt: skip
    """Lower a decision's origin on the owner's confirmed statement; its rationale says why.

    One that changed the rule it replaced is refused: fixes for that change may depend on it staying in force.

    Such as `decided` to `approved` for an agent's proposal he accepted without intent of his own. A draft is
    corrected in place; a decision in force, whose origin never changes once accepted (TD-430), by a successor with
    the same title, topic, statement, scope and read-back, marked wording only, which replaces it. Raising an origin
    takes a replacement he confirms as his own decision; a read-back only reconfirms and leaves the origin.
    """
    if not confirmed:
        raise Refused(UNSTATED, 422)
    why = _reason(reason, "correcting an origin")
    view = decision_store.load(shared, project)
    old = _entry(view, decision_id).decision
    if stale := _stale(view, old, revision):
        return stale
    if old.state in RETIRED:
        msg = f"{old.id} is {old.state}: only a draft or a decision in force is corrected"
        raise Refused(msg)
    if AUTHORITY[origin] >= AUTHORITY[old.origin]:
        msg = f"{old.id} is {old.origin}: an origin is only corrected downward; raising it is the owner's"
        raise Refused(msg)
    if old.state is State.IN_FORCE and (old.conflict or rivals(view, old, shared)):
        msg = f"{old.id} competes with another successor: the owner resolves the conflict first, then corrects it"
        raise Refused(msg)
    if old.state is State.IN_FORCE and _changed_a_rule(old):
        msg = (f"{old.id} changed the rule it replaced, and fixes may depend on it: its origin is not corrected; "
               "the owner replaces it himself if he wants")  # fmt: skip
        raise Refused(msg)
    rationale = _because(decision_wording.framed(old), CORRECTED, f"{old.origin} to {origin}: {why}")
    if old.state is State.DRAFT:
        update = {"origin": origin, "rationale": rationale}
        said = f"decisions: correct-origin {old.id} ({by})"
        return [decision_store.save(shared, old.model_copy(update=update), expected_revision=old.revision,
                                    message=said)]  # fmt: skip
    kept = tuple(link for link in old.links if link.type not in LINEAGE)
    new = _new(
        old, title=old.title, statement=old.statement, rationale=_marked(rationale, "wording"), scope=old.scope,
        project=old.project, change=old.change, origin=origin, actor=old.actor, source=old.source,
        read_back=old.read_back, read_back_why=old.read_back_why, read_back_kind=old.read_back_kind,
        read_back_settled=old.read_back_settled,
        inherited=old.inherited, state=State.IN_FORCE,
        links=(Link(type=LinkType.REPLACES, target=old.id), *kept),
    )  # fmt: skip
    return _retire(shared, new, old, f"decisions: correct-origin {old.id} with {new.id} ({by})")


def _changed_a_rule(decision: Decision) -> bool:
    """It replaced a decision and is not marked wording only: its replacement may owe fixes (TD-428)."""
    if not any(link.type is LinkType.REPLACES for link in decision.links):
        return False
    marks = [p for p in decision.rationale.split("\n\n") if p.startswith(EFFECT)]
    return not marks or marks[-1] != EFFECT + EFFECTS["wording"]
