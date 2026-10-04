"""Acceptance evidence evaluation, confirmation applicability and the finalization semantic basis.

One pure evaluator (I7) serves ``publish_result``, ``finalize_change``, the finalization context and
later projections. Digests here prove content integrity, not that a procedure actually ran (R12).
"""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field

from owlbear_delivery.acceptance_criteria import DeliveryAcceptanceCriterion, acceptance_criteria
from owlbear_delivery.runtime_models import (
    PROOF_VERDICTS,
    DeliveryConfirmationScope,
    DeliveryEvidenceGap,
    DeliveryEvidenceGapReason,
    DeliveryFrontier,
    DeliveryLegacyObservationReceipt,
    DeliveryManualProcedureResult,
    DeliveryObservation,
    DeliveryObservationReceipt,
    DeliveryTaskResult,
    DeliveryUserConfirmation,
    DeliveryWaivedResult,
    _model_content,
)
from owlbear_delivery.target_contract import DeliveryCommitment

if TYPE_CHECKING:
    from collections.abc import Iterable

    from owlbear_delivery.target_contract import DeliveryContract

FINALIZATION_SEMANTICS_MAX_BYTES = 262_144
BASIS_SCHEMA = 1

type DeliveryCriterionStatus = Literal["covered", "waived", "missing", "uncovered", "unknown"]
type DeliveryAnyObservation = DeliveryLegacyObservationReceipt | DeliveryObservationReceipt


class _EvidenceModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class DeliveryCriterionCoverage(_EvidenceModel):
    """Coverage of one current criterion version, decided by the last typed record covering it."""

    acceptance_id: str
    acceptance_version: str = Field(pattern=r"^[0-9a-f]{64}$")
    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    status: DeliveryCriterionStatus
    observation_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


class DeliveryAcceptanceCoverage(_EvidenceModel):
    """Coverage of every current criterion of one admitted contract."""

    criteria: tuple[DeliveryCriterionCoverage, ...]
    legacy_observation_count: int = Field(ge=0)

    @property
    def gaps(self) -> tuple[DeliveryEvidenceGap, ...]:
        """Return one gap for every criterion that is neither covered nor waived."""
        reasons: dict[str, DeliveryEvidenceGapReason] = {
            "missing": "missing",
            "uncovered": "uncovered",
            "unknown": "unknown-legacy-only",
        }
        return tuple(
            DeliveryEvidenceGap(acceptance_id=item.acceptance_id, observation_id=item.observation_id, reason=reason)
            for item in self.criteria
            if (reason := reasons.get(item.status)) is not None
        )


class DeliverySemanticsOutcome(_EvidenceModel):
    """One admitted outcome as the Finalizer and the reviewer must both read it."""

    outcome_id: str
    title: str
    promise: str
    commitment_ids: tuple[str, ...]
    dependency_ids: tuple[str, ...]
    criteria: tuple[DeliveryAcceptanceCriterion, ...]


class DeliverySemanticsTaskResult(_EvidenceModel):
    """One promoted task result and the exact evidence it carries."""

    outcome_id: str
    task_id: str
    title: str
    completed_commit: str
    result_digest: str
    observation_ids: tuple[str, ...]


class DeliverySemanticsTaskAuthority(_EvidenceModel):
    """The bounded promoted authority that one task result was produced against."""

    task_id: str
    task_digest: str
    result: str
    constraints: tuple[str, ...]
    exclusions: tuple[str, ...]
    proof_boundaries: tuple[str, ...]
    acceptance_observations: tuple[str, ...]


class DeliverySemanticsConfirmation(_EvidenceModel):
    """One ledger confirmation that carried task evidence cites or an exact-head record could cite."""

    confirmation_id: str
    outcome_id: str
    scope: DeliveryConfirmationScope
    decision: str
    channel: str


class DeliveryFinalizationSemantics(_EvidenceModel):
    """The complete semantic projection and diff boundary shared by Finalizer and reviewer."""

    contract_digest: str
    title: str
    outcomes: tuple[DeliverySemanticsOutcome, ...]
    commitments: tuple[DeliveryCommitment, ...]
    task_results: tuple[DeliverySemanticsTaskResult, ...]
    task_authority: tuple[DeliverySemanticsTaskAuthority, ...]
    confirmations: tuple[DeliverySemanticsConfirmation, ...]
    diff_base: str = Field(pattern=r"^[0-9a-f]{40}$")
    change_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    coverage: tuple[DeliveryCriterionCoverage, ...]
    basis_digest: str = Field(pattern=r"^[0-9a-f]{64}$")


class DeliveryContextRefusal(_EvidenceModel):
    """Why the finalization semantics are withheld as a whole; nothing is ever truncated."""

    code: Literal["finalization-context-oversized", "finalization-basis-unavailable"]
    measured_bytes: int | None = Field(default=None, ge=0)
    budget_bytes: int = FINALIZATION_SEMANTICS_MAX_BYTES


def resolve_confirmation(frontier: DeliveryFrontier, confirmation_id: str) -> DeliveryUserConfirmation | None:
    """Return the ledger confirmation with this identity, or ``None``."""
    return next(
        (item for item in frontier.confirmations or () if item.confirmation_id == confirmation_id),
        None,
    )


def confirmation_applies(
    confirmation: DeliveryUserConfirmation,
    observation: DeliveryObservationReceipt,
    outcome_id: str,
) -> DeliveryEvidenceGapReason | None:
    """Return why a ledger confirmation does not authorize this record (I6), or ``None`` when it does."""
    scope = confirmation.scope
    covered = set(scope.acceptance)
    if (
        confirmation.outcome_id != outcome_id
        or confirmation.change_id != observation.change_id
        or scope.procedure != observation.procedure
        or not set(observation.covers) <= covered
    ):
        return "confirmation-not-applicable"
    result = observation.result
    if result.kind == "waived":
        affirmative = scope.kind == "waive" and confirmation.decision == "waive"
    else:
        assessment = getattr(result, "assessment", None)
        affirmative = scope.kind == "confirm-check" and confirmation.decision == assessment
    return None if affirmative else "confirmation-not-applicable"


def _finalization_citable(
    confirmation: DeliveryUserConfirmation,
    criteria: tuple[DeliveryAcceptanceCriterion, ...],
) -> bool:
    """Return whether ``confirmation_applies`` admits it for an exact-head record a Finalizer could submit.

    That record covers the current criterion versions of its scope in its outcome, uses its exact procedure
    and carries the affirmative result for its kind: a waiver, or a passed manual assessment.
    """
    current = {criterion.ref: criterion for criterion in criteria}
    scope = confirmation.scope
    covers = tuple(
        ref for ref in scope.acceptance if ref in current and current[ref].outcome_id == confirmation.outcome_id
    )
    if not covers:
        return False
    confirmation_id = confirmation.confirmation_id
    result = (
        DeliveryWaivedResult(reason="Waived by the user.", confirmation_id=confirmation_id)
        if scope.kind == "waive"
        else DeliveryManualProcedureResult(assessment="passed")
    )
    record = DeliveryObservationReceipt.create(
        DeliveryObservation(
            change_id=confirmation.change_id,
            task_or_finalization_id=confirmation.request_id,
            exact_commit="0" * 40,
            observation_kind="user-confirmation",
            procedure=scope.procedure,
            result=result,
            covers=covers,
            provenance="human-confirmed",
            confirmation_id=confirmation_id,
            observer_or_runner_identity="user",
            observed_at=confirmation.confirmed_at,
        )
    )
    return confirmation_applies(confirmation, record, confirmation.outcome_id) is None


def observation_gaps(
    observation: DeliveryAnyObservation,
    frontier: DeliveryFrontier,
    criteria: tuple[DeliveryAcceptanceCriterion, ...],
    outcome_id: str | None,
) -> tuple[DeliveryEvidenceGap, ...]:
    """Return why one submitted record is not admissible evidence for the current contract.

    ``outcome_id`` is the result's outcome; ``None`` means a finalization record, whose confirmation
    must belong to the outcome of every criterion it covers.
    """
    if isinstance(observation, DeliveryLegacyObservationReceipt):
        return (DeliveryEvidenceGap(observation_id=observation.observation_id, reason="legacy-observation"),)
    gaps: list[DeliveryEvidenceGap] = []
    current = {criterion.acceptance_id: criterion for criterion in criteria}
    covered_outcomes: set[str] = set()
    for reference in observation.covers:
        criterion = current.get(reference.acceptance_id)
        reason: DeliveryEvidenceGapReason | None = None
        if criterion is None:
            reason = "unknown-acceptance"
        elif criterion.acceptance_version != reference.acceptance_version:
            reason = "stale-acceptance-version"
        else:
            covered_outcomes.add(criterion.outcome_id)
        if reason is not None:
            gaps.append(
                DeliveryEvidenceGap(
                    acceptance_id=reference.acceptance_id,
                    observation_id=observation.observation_id,
                    reason=reason,
                )
            )
    if observation.confirmation_id is not None:
        reason = _confirmation_gap(observation, frontier, outcome_id, covered_outcomes)
        if reason is not None:
            gaps.append(DeliveryEvidenceGap(observation_id=observation.observation_id, reason=reason))
    return tuple(gaps)


def _confirmation_gap(
    observation: DeliveryObservationReceipt,
    frontier: DeliveryFrontier,
    outcome_id: str | None,
    covered_outcomes: set[str],
) -> DeliveryEvidenceGapReason | None:
    confirmation_id = observation.confirmation_id
    confirmation = resolve_confirmation(frontier, confirmation_id) if confirmation_id is not None else None
    if confirmation is None:
        return "confirmation-unresolved"
    if outcome_id is None:
        if len(covered_outcomes) != 1:
            return "confirmation-not-applicable"
        outcome_id = next(iter(covered_outcomes))
    return confirmation_applies(confirmation, observation, outcome_id)


def evaluate_acceptance_evidence(
    contract: DeliveryContract,
    frontier: DeliveryFrontier,
    request_observations: tuple[DeliveryAnyObservation, ...] = (),
) -> DeliveryAcceptanceCoverage:
    """Fold task evidence in authority order, then the finalization request; the last record wins (D5)."""
    criteria = acceptance_criteria(contract)
    current = {criterion.ref: criterion for criterion in criteria}
    decided: dict[str, tuple[DeliveryCriterionStatus, str]] = {}
    legacy = 0
    for outcome_id, observation in _ordered_records(frontier, request_observations):
        if isinstance(observation, DeliveryLegacyObservationReceipt):
            legacy += 1
            continue
        status = _record_status(observation, frontier, outcome_id, current)
        if status is None:
            continue
        for reference in observation.covers:
            criterion = current.get(reference)
            if criterion is not None:
                decided[criterion.acceptance_id] = (status, observation.observation_id)
    coverage = []
    for criterion in criteria:
        status, observation_id = decided.get(criterion.acceptance_id, (None, None))
        coverage.append(
            DeliveryCriterionCoverage(
                acceptance_id=criterion.acceptance_id,
                acceptance_version=criterion.acceptance_version,
                outcome_id=criterion.outcome_id,
                status=status or ("unknown" if legacy else "uncovered"),
                observation_id=observation_id,
            )
        )
    return DeliveryAcceptanceCoverage(criteria=tuple(coverage), legacy_observation_count=legacy)


def _ordered_records(
    frontier: DeliveryFrontier,
    request_observations: tuple[DeliveryAnyObservation, ...],
) -> Iterable[tuple[str | None, DeliveryAnyObservation]]:
    for binding in frontier.bindings:
        for result in binding.results:
            for observation in result.observations:
                yield binding.outcome_id, observation
    finalization = frontier.finalization
    if finalization is not None and not request_observations:
        request_observations = finalization.observations
    for observation in request_observations:
        yield None, observation


def _record_status(
    observation: DeliveryObservationReceipt,
    frontier: DeliveryFrontier,
    outcome_id: str | None,
    current: dict[object, DeliveryAcceptanceCriterion],
) -> DeliveryCriterionStatus | None:
    verdict = observation.verdict
    if verdict in PROOF_VERDICTS and observation.provenance == "machine-observed":
        return "covered"
    if verdict == "missing":
        return "missing"
    if verdict not in {*PROOF_VERDICTS, "waived"}:
        return None
    covered_outcomes = {current[ref].outcome_id for ref in observation.covers if ref in current}
    if _confirmation_gap(observation, frontier, outcome_id, covered_outcomes) is not None:
        return None
    return "waived" if verdict == "waived" else "covered"


def finalization_basis_digest(
    contract_digest: str,
    change_head: str,
    diff_base: str,
    result_digests: tuple[str, ...],
    criteria: tuple[DeliveryAcceptanceCriterion, ...],
) -> str:
    """Return the digest of the semantic basis that the Finalizer and the reviewer both attest."""
    payload = {
        "schema": BASIS_SCHEMA,
        "contract_digest": contract_digest,
        "change_head": change_head,
        "diff_base": diff_base,
        "result_digests": list(result_digests),
        "acceptance": [[criterion.acceptance_id, criterion.acceptance_version] for criterion in criteria],
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def result_digest(result: DeliveryTaskResult) -> str:
    """Return the canonical digest that finalization binds for one task result."""
    return hashlib.sha256(_model_content(result)).hexdigest()


def build_finalization_semantics(
    contract: DeliveryContract,
    frontier: DeliveryFrontier,
    *,
    contract_digest: str,
    change_head: str,
    diff_base: str,
) -> DeliveryFinalizationSemantics:
    """Build the complete semantic context; size is measured by the caller (D12)."""
    criteria = acceptance_criteria(contract)
    by_outcome: dict[str, list[DeliveryAcceptanceCriterion]] = {}
    for criterion in criteria:
        by_outcome.setdefault(criterion.outcome_id, []).append(criterion)
    results = tuple((binding, result) for binding in frontier.bindings for result in binding.results)
    digests = tuple(result_digest(result) for _binding, result in results)
    tasks = {task.task_id: task for binding in frontier.bindings for task in binding.tasks}
    cited = {
        observation.confirmation_id
        for _binding, result in results
        for observation in result.observations
        if isinstance(observation, DeliveryObservationReceipt) and observation.confirmation_id is not None
    }
    return DeliveryFinalizationSemantics(
        contract_digest=contract_digest,
        title=contract.title,
        outcomes=tuple(
            DeliverySemanticsOutcome(
                outcome_id=outcome.outcome_id,
                title=outcome.title,
                promise=outcome.promise,
                commitment_ids=outcome.commitment_ids,
                dependency_ids=outcome.dependency_ids,
                criteria=tuple(by_outcome.get(outcome.outcome_id, ())),
            )
            for outcome in contract.outcomes
        ),
        commitments=contract.commitments,
        task_results=tuple(
            DeliverySemanticsTaskResult(
                outcome_id=binding.outcome_id,
                task_id=result.task_id,
                title=tasks[result.task_id].title if result.task_id in tasks else result.task_id,
                completed_commit=result.completed_commit,
                result_digest=digest,
                observation_ids=tuple(item.observation_id for item in result.observations),
            )
            for (binding, result), digest in zip(results, digests, strict=True)
        ),
        task_authority=tuple(
            DeliverySemanticsTaskAuthority(
                task_id=task.task_id,
                task_digest=task.digest,
                result=task.result,
                constraints=task.constraints,
                exclusions=task.exclusions,
                proof_boundaries=task.proof_boundaries,
                acceptance_observations=task.acceptance_observations,
            )
            for _binding, result in results
            if (task := tasks.get(result.task_id)) is not None
        ),
        confirmations=tuple(
            DeliverySemanticsConfirmation(
                confirmation_id=item.confirmation_id,
                outcome_id=item.outcome_id,
                scope=item.scope,
                decision=item.decision,
                channel=item.channel,
            )
            for item in frontier.confirmations or ()
            if item.confirmation_id in cited
            or (item.change_id == contract.change_id and _finalization_citable(item, criteria))
        ),
        diff_base=diff_base,
        change_head=change_head,
        coverage=evaluate_acceptance_evidence(contract, frontier.model_copy(update={"finalization": None})).criteria,
        basis_digest=finalization_basis_digest(contract_digest, change_head, diff_base, digests, criteria),
    )


def measure_semantics(semantics: DeliveryFinalizationSemantics) -> int:
    """Return the canonical UTF-8 size of the complete semantics value."""
    encoded = json.dumps(semantics.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return len(encoded.encode())


def finalization_semantics_or_refusal(
    contract: DeliveryContract,
    frontier: DeliveryFrontier,
    *,
    contract_digest: str,
    change_head: str | None,
    diff_base: str | None,
) -> DeliveryFinalizationSemantics | DeliveryContextRefusal:
    """Return the complete semantics within the byte budget, else a typed refusal (D12)."""
    if change_head is None or diff_base is None:
        return DeliveryContextRefusal(code="finalization-basis-unavailable")
    semantics = build_finalization_semantics(
        contract,
        frontier,
        contract_digest=contract_digest,
        change_head=change_head,
        diff_base=diff_base,
    )
    measured = measure_semantics(semantics)
    if measured > FINALIZATION_SEMANTICS_MAX_BYTES:
        return DeliveryContextRefusal(
            code="finalization-context-oversized",
            measured_bytes=measured,
            budget_bytes=FINALIZATION_SEMANTICS_MAX_BYTES,
        )
    return semantics


__all__ = [
    "FINALIZATION_SEMANTICS_MAX_BYTES",
    "DeliveryAcceptanceCoverage",
    "DeliveryContextRefusal",
    "DeliveryCriterionCoverage",
    "DeliveryFinalizationSemantics",
    "DeliverySemanticsConfirmation",
    "DeliverySemanticsOutcome",
    "DeliverySemanticsTaskAuthority",
    "DeliverySemanticsTaskResult",
    "build_finalization_semantics",
    "confirmation_applies",
    "evaluate_acceptance_evidence",
    "finalization_basis_digest",
    "finalization_semantics_or_refusal",
    "measure_semantics",
    "observation_gaps",
    "resolve_confirmation",
    "result_digest",
]
