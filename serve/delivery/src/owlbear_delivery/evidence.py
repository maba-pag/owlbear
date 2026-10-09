"""Acceptance evidence evaluation, scoped-request applicability and the finalization semantic basis.

One pure evaluator (I7) serves ``publish_result``, ``finalize_change``, the finalization context and
later projections. Digests here prove content integrity, not that a procedure actually ran (R12).
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field

from owlbear_delivery.acceptance_criteria import DeliveryAcceptanceCriterion, acceptance_criteria
from owlbear_delivery.runtime_models import (
    _LEGACY_FINALIZATION_SCHEMA_VERSION,
    AFFIRMATIVE_DECISIONS,
    PROOF_VERDICTS,
    DeliveryConfirmationScope,
    DeliveryEvidenceGap,
    DeliveryEvidenceGapReason,
    DeliveryEvidenceVerdict,
    DeliveryFrontier,
    DeliveryLegacyObservationReceipt,
    DeliveryObservationReceipt,
    DeliveryRequest,
    DeliveryTaskResult,
    _model_content,
)
from owlbear_delivery.target_contract import DeliveryCommitment, DeliveryDecision

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
    """One scoped request the user answered in Cockpit, which an exact-head record may cite."""

    request_id: str
    outcome_id: str
    scope: DeliveryConfirmationScope
    decision: str


class DeliveryFinalizationSemantics(_EvidenceModel):
    """The complete semantic projection and diff boundary shared by Finalizer and reviewer."""

    contract_digest: str
    title: str
    outcomes: tuple[DeliverySemanticsOutcome, ...]
    decisions: tuple[DeliveryDecision, ...] = ()
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


def resolve_request(frontier: DeliveryFrontier, outcome_id: str, request_id: str) -> DeliveryRequest | None:
    """Return the request with this identity retained by the outcome, or ``None``."""
    return next(
        (
            request
            for binding in frontier.bindings
            if binding.outcome_id == outcome_id
            for request in binding.requests
            if request.request_id == request_id
        ),
        None,
    )


def request_applies(
    request: DeliveryRequest,
    observation: DeliveryObservationReceipt,
    outcome_id: str,
) -> DeliveryEvidenceGapReason | None:
    """Return why a cited request does not authorize this record (I6), or ``None`` when it does.

    It authorizes only when the user resolved it, it is scoped to every criterion version the record
    covers and to its procedure, and the user's decision matches the record's result.
    """
    scope = request.applies_to
    resolution = request.resolution
    if resolution is None:
        return "request-unresolved"
    if (
        scope is None
        or request.outcome_id != outcome_id
        or scope.procedure != observation.procedure
        or not set(observation.covers) <= set(scope.acceptance)
    ):
        return "request-not-applicable"
    decision = resolution.selected_option_id
    if observation.result.kind == "waived":
        affirmative = scope.kind == "waive" and decision == AFFIRMATIVE_DECISIONS["waive"]
    else:
        affirmative = scope.kind == "confirm-check" and decision == getattr(observation.result, "assessment", None)
    return None if affirmative else "request-not-applicable"


def observation_gaps(
    observation: DeliveryAnyObservation,
    frontier: DeliveryFrontier,
    criteria: tuple[DeliveryAcceptanceCriterion, ...],
    outcome_id: str | None,
) -> tuple[DeliveryEvidenceGap, ...]:
    """Return why one submitted record is not admissible evidence for the current contract.

    ``outcome_id`` is the result's outcome; ``None`` means a finalization record, whose cited request
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
    if observation.request_id is not None:
        reason = _request_gap(observation, frontier, outcome_id, covered_outcomes)
        if reason is not None:
            gaps.append(DeliveryEvidenceGap(observation_id=observation.observation_id, reason=reason))
    return tuple(gaps)


def _request_gap(
    observation: DeliveryObservationReceipt,
    frontier: DeliveryFrontier,
    outcome_id: str | None,
    covered_outcomes: set[str],
) -> DeliveryEvidenceGapReason | None:
    if outcome_id is None:
        if len(covered_outcomes) != 1:
            return "request-not-applicable"
        outcome_id = next(iter(covered_outcomes))
    request_id = observation.request_id
    request = resolve_request(frontier, outcome_id, request_id) if request_id is not None else None
    if request is None:
        return "request-unresolved"
    return request_applies(request, observation, outcome_id)


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
    if _request_gap(observation, frontier, outcome_id, covered_outcomes) is not None:
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
        decisions=contract.decisions,
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
                request_id=request.request_id,
                outcome_id=request.outcome_id,
                scope=request.applies_to,
                decision=request.resolution.selected_option_id,
            )
            for binding in frontier.bindings
            for request in binding.requests
            if request.applies_to is not None
            and request.resolution is not None
            and request.resolution.selected_option_id is not None
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


MAX_CRITERION_EVIDENCE = 16
MAX_UNATTRIBUTED_EVIDENCE = 64

type DeliveryFinalizationRules = Literal["typed", "legacy", "none"]
type DeliveryEvidenceSource = Literal["task", "finalization"]


class DeliveryEvidenceItemView(_EvidenceModel):
    """One retained observation as shown beside a criterion; legacy records carry no verdict."""

    observation_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    observation_schema: Literal[1, 2]
    source: DeliveryEvidenceSource
    task_or_finalization_id: str
    exact_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    observation_kind: str
    procedure: str = Field(max_length=512)
    verdict: DeliveryEvidenceVerdict | None = None
    owner: Literal["agent", "user", "provider", "assisted-check"] | None = None
    reason: str | None = None
    provenance: Literal["machine-observed", "human-confirmed"] | None = None
    request_id: str | None = None
    locator: str | None = None
    summary: str | None = Field(default=None, max_length=240)
    observed_at: str


class DeliveryAcceptanceEvidenceView(_EvidenceModel):
    """One current criterion, its evaluator status and its latest covering records."""

    acceptance_id: str
    acceptance_version: str = Field(pattern=r"^[0-9a-f]{64}$")
    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    statement: str
    identity_source: Literal["authored", "legacy-position"]
    status: DeliveryCriterionStatus
    decided_by: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    evidence: tuple[DeliveryEvidenceItemView, ...] = Field(default=(), max_length=MAX_CRITERION_EVIDENCE)
    evidence_truncated: int = Field(default=0, ge=0)


class DeliveryEvidenceCounts(_EvidenceModel):
    """Criterion totals by status."""

    covered: int = Field(default=0, ge=0)
    waived: int = Field(default=0, ge=0)
    missing: int = Field(default=0, ge=0)
    uncovered: int = Field(default=0, ge=0)
    unknown: int = Field(default=0, ge=0)


class DeliveryEvidenceProjection(_EvidenceModel):
    """Read-only acceptance criterion -> evidence -> status projection of one Change or outcome."""

    change_id: str
    contract_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    frontier_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    finalization_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    finalization_rules: DeliveryFinalizationRules
    criteria: tuple[DeliveryAcceptanceEvidenceView, ...]
    unattributed: tuple[DeliveryEvidenceItemView, ...] = Field(default=(), max_length=MAX_UNATTRIBUTED_EVIDENCE)
    unattributed_truncated: int = Field(default=0, ge=0)
    counts: DeliveryEvidenceCounts


def build_evidence_projection(
    contract: DeliveryContract,
    frontier: DeliveryFrontier,
    *,
    contract_digest: str,
    frontier_digest: str,
    outcome_id: str | None = None,
) -> DeliveryEvidenceProjection:
    """Project the evaluator's statuses with their records; ``outcome_id`` limits it to one outcome."""
    criteria = acceptance_criteria(contract)
    coverage = {item.acceptance_id: item for item in evaluate_acceptance_evidence(contract, frontier).criteria}
    current = {criterion.ref: criterion.acceptance_id for criterion in criteria}
    by_criterion: dict[str, list[DeliveryEvidenceItemView]] = {}
    unattributed: list[DeliveryEvidenceItemView] = []
    for record_outcome, observation in reversed(tuple(_ordered_records(frontier, ()))):
        item = _evidence_item(observation, "task" if record_outcome is not None else "finalization")
        covered = (
            [current[ref] for ref in observation.covers if ref in current]
            if isinstance(observation, DeliveryObservationReceipt)
            else []
        )
        for acceptance_id in covered:
            by_criterion.setdefault(acceptance_id, []).append(item)
        if not covered and (outcome_id is None or record_outcome == outcome_id):
            unattributed.append(item)
    views = tuple(
        DeliveryAcceptanceEvidenceView(
            acceptance_id=criterion.acceptance_id,
            acceptance_version=criterion.acceptance_version,
            outcome_id=criterion.outcome_id,
            statement=criterion.statement,
            identity_source=criterion.identity_source,
            status=coverage[criterion.acceptance_id].status,
            decided_by=coverage[criterion.acceptance_id].observation_id,
            evidence=tuple(items[:MAX_CRITERION_EVIDENCE]),
            evidence_truncated=max(len(items) - MAX_CRITERION_EVIDENCE, 0),
        )
        for criterion in criteria
        if outcome_id is None or criterion.outcome_id == outcome_id
        for items in (by_criterion.get(criterion.acceptance_id, []),)
    )
    finalization = frontier.finalization
    return DeliveryEvidenceProjection(
        change_id=contract.change_id,
        contract_digest=contract_digest,
        frontier_digest=frontier_digest,
        finalization_id=finalization.finalization_id if finalization is not None else None,
        finalization_rules=(
            "none"
            if finalization is None
            else "legacy"
            if finalization.schema_version == _LEGACY_FINALIZATION_SCHEMA_VERSION
            else "typed"
        ),
        criteria=views,
        unattributed=tuple(unattributed[:MAX_UNATTRIBUTED_EVIDENCE]),
        unattributed_truncated=max(len(unattributed) - MAX_UNATTRIBUTED_EVIDENCE, 0),
        counts=DeliveryEvidenceCounts(**Counter(view.status for view in views)),
    )


def _evidence_item(observation: DeliveryAnyObservation, source: DeliveryEvidenceSource) -> DeliveryEvidenceItemView:
    common = {
        "observation_id": observation.observation_id,
        "observation_schema": observation.schema_version,
        "source": source,
        "task_or_finalization_id": observation.task_or_finalization_id,
        "exact_commit": observation.exact_commit,
        "observation_kind": observation.observation_kind,
        "observed_at": observation.observed_at.isoformat(),
    }
    if isinstance(observation, DeliveryLegacyObservationReceipt):
        return DeliveryEvidenceItemView(
            **common,
            procedure=observation.command_or_procedure[:512],
            summary=observation.exit_status_or_artifact_locator[:240],
        )
    result = observation.result
    return DeliveryEvidenceItemView(
        **common,
        procedure=observation.procedure,
        verdict=observation.verdict,
        owner=getattr(result, "owner", None),
        reason=getattr(result, "reason", None),
        provenance=observation.provenance,
        request_id=observation.request_id,
        locator=observation.locator,
        summary=observation.summary,
    )


__all__ = [
    "FINALIZATION_SEMANTICS_MAX_BYTES",
    "MAX_CRITERION_EVIDENCE",
    "MAX_UNATTRIBUTED_EVIDENCE",
    "DeliveryAcceptanceCoverage",
    "DeliveryAcceptanceEvidenceView",
    "DeliveryContextRefusal",
    "DeliveryCriterionCoverage",
    "DeliveryEvidenceCounts",
    "DeliveryEvidenceItemView",
    "DeliveryEvidenceProjection",
    "DeliveryFinalizationSemantics",
    "DeliverySemanticsConfirmation",
    "DeliverySemanticsOutcome",
    "DeliverySemanticsTaskAuthority",
    "DeliverySemanticsTaskResult",
    "build_evidence_projection",
    "build_finalization_semantics",
    "evaluate_acceptance_evidence",
    "finalization_basis_digest",
    "finalization_semantics_or_refusal",
    "measure_semantics",
    "observation_gaps",
    "request_applies",
    "resolve_request",
    "result_digest",
]
