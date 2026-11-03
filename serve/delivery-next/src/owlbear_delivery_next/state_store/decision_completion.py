"""A lead's evidenced completion of wholly finite OwlBear instructions, without changing their intent."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from owlbear_decisions import Scope, State
from owlbear_delivery_next.change_contracts import decision_wording
from owlbear_delivery_next.state_store import decision_store
from owlbear_delivery_next.state_store.decision_actions import (
    Refused,
    _because,
    _entry,
    _in_force,
    _reason,
    _stale,
)

if TYPE_CHECKING:
    from owlbear_delivery_next.local_system.data_repo import DataRepo
    from owlbear_delivery_next.state_store.decision_store import Receipt


@dataclass(frozen=True)
class Proof:
    """The finite binding condition and the lead's supporting facts, kept together."""

    condition: str
    evidence: str


def complete(
    shared: DataRepo | None, project: str, decision_id: str, revision: str, proof: Proof,
) -> list[Receipt]:  # fmt: skip
    """Mark a wholly finite instruction spent, keeping its binding and provenance and recording the lead's proof.

    The lead judges finiteness and evidence truth; a quote match alone proves neither.
    """
    if project != "owlbear":
        msg = "administrative completion is delegated only for OwlBear's project decisions"
        raise Refused(msg, 422)
    view = decision_store.load(shared, project)
    old = _entry(view, decision_id).decision
    if stale := _stale(view, old, revision):
        return stale
    if old.scope is not Scope.PROJECT or old.project != project:
        msg = f"{old.id}: only OwlBear project decisions use administrative completion"
        raise Refused(msg, 422)
    _in_force(old, "completed")
    if not view.snapshot.active(old.id) or old.read_back == "pending":
        msg = f"{old.id}: resolve its conflict, validation findings or pending read-back before completion"
        raise Refused(msg)
    quoted = _reason(proof.condition, "completion condition")
    evidence = _reason(proof.evidence, "completion evidence")
    if quoted not in decision_wording.whole(old):
        msg = "condition: quote the explicit end condition from the whole binding, not its explanation"
        raise Refused(msg, 422)
    rationale = _because(decision_wording.framed(old), "Why it was spent: ", f"{quoted}\nEvidence: {evidence}")
    spent = old.model_copy(update={"state": State.SPENT, "rationale": rationale})
    return [decision_store.save(shared, spent, expected_revision=old.revision, message=f"decisions: complete {old.id}")]
