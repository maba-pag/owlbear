"""Shared N03-A evidence fixtures: schema-2 finalization proof bound to engine-derived semantics."""

from __future__ import annotations

from typing import TYPE_CHECKING

from owlbear_delivery.acceptance_criteria import DeliveryAcceptanceRef
from owlbear_delivery.delivery_runtime import (
    DeliveryCommandResult,
    DeliveryObservation,
    DeliveryObservationReceipt,
    DeliveryReview,
    DeliveryReviewReceipt,
    FinalizeDeliveryChange,
)
from owlbear_delivery.evidence import DeliveryFinalizationSemantics

if TYPE_CHECKING:
    from datetime import datetime

    from owlbear_delivery.delivery_runtime import DeliveryRuntime
    from owlbear_delivery.evidence import DeliveryContextRefusal

_UNAVAILABLE_BASIS = "0" * 64


def finalization_proof(  # noqa: PLR0913 - one fixture binds every finalization evidence field.
    semantics: DeliveryFinalizationSemantics | DeliveryContextRefusal,
    *,
    change_id: str,
    exact_head: str,
    operation_id: str,
    observed_at: datetime,
    procedure: str,
    author_id: str,
    reviewer_id: str,
    evidence: str,
) -> FinalizeDeliveryChange:
    """Return one finalization covering every criterion that carried task evidence leaves open."""
    covers: tuple[DeliveryAcceptanceRef, ...] = ()
    basis_digest = _UNAVAILABLE_BASIS
    if isinstance(semantics, DeliveryFinalizationSemantics):
        basis_digest = semantics.basis_digest
        covers = tuple(
            DeliveryAcceptanceRef(acceptance_id=item.acceptance_id, acceptance_version=item.acceptance_version)
            for item in semantics.coverage
            if item.status not in {"covered", "waived"}
        )
    observation = DeliveryObservationReceipt.create(
        DeliveryObservation(
            change_id=change_id,
            task_or_finalization_id=operation_id,
            exact_commit=exact_head,
            observation_kind="pytest",
            procedure=procedure,
            result=DeliveryCommandResult(exit_status=0),
            covers=covers,
            observer_or_runner_identity="pytest",
            observed_at=observed_at,
        )
    )
    review = DeliveryReviewReceipt.create(
        DeliveryReview(
            review_mode="finalization",
            basis_digest=basis_digest,
            observation_ids=(observation.observation_id,),
            exact_commit=exact_head,
            author_id=author_id,
            reviewer_id=reviewer_id,
            evidence=(evidence,),
            reviewed_at=observed_at,
        )
    )
    return FinalizeDeliveryChange(
        operation_id=operation_id,
        exact_head=exact_head,
        observations=(observation,),
        review=review,
    )


def runtime_finalization_proof(
    runtime: DeliveryRuntime,
    exact_head: str,
    operation_id: str,
    observed_at: datetime,
) -> FinalizeDeliveryChange:
    """Return one finalization proof bound to the runtime's current semantics for ``exact_head``."""
    return finalization_proof(
        runtime.finalization_semantics(exact_head),
        change_id=runtime.contract.change_id,
        exact_head=exact_head,
        operation_id=operation_id,
        observed_at=observed_at,
        procedure="full Delivery finalization validation",
        author_id="Delivery finalization author",
        reviewer_id="Delivery finalization reviewer",
        evidence="The exact Change head satisfies finalization authority.",
    )
