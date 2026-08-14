"""Mechanical Delivery state and worker-owned transitions."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator

from owlbear_delivery.acceptance import (
    CompletionDisplayMetadata,
    CompletionReceipt,
    CompletionReceiptConflictError,
    CompletionReceiptStore,
)
from owlbear_delivery.draft_pull_request import (
    PublicationPullRequestObservationReceipt,
    PullRequestReadyReceipt,
)
from owlbear_delivery.runtime_transaction import ReplacementTransactionParticipant, RuntimeTransaction

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear_delivery.change_workspace import ChangeWorkspaceManager
    from owlbear_delivery.target_contract import DeliveryContract


class DeliveryStage(StrEnum):
    """Canonical outcome progress stages."""

    DESIGN = "design"
    PLANNING = "planning"
    IMPLEMENTATION = "implementation"
    COMPLETED = "completed"


class DeliveryChangeStage(StrEnum):
    """Canonical Change lifecycle state."""

    DESIGN = "design"
    BUILDING = "building"
    FINALIZED = "finalized"
    AWAITING_MERGE = "awaiting-merge"
    PUBLICATION_ATTENTION = "publication-attention"
    ACCEPTANCE_ATTENTION = "acceptance-attention"
    DEFERRED = "deferred"
    ABANDONED = "abandoned"
    COMPLETED = "completed"


class DeliveryChangeDispositionKind(StrEnum):
    """Nonterminal Change-level attention requiring explicit reconciliation."""

    PUBLICATION_ATTENTION = "publication-attention"
    ACCEPTANCE_ATTENTION = "acceptance-attention"


class DeliveryOutputKind(StrEnum):
    """Minimal phase-output categories consumed by mechanical transitions."""

    DESIGN = "design"
    PLANNING = "planning"
    IMPLEMENTATION = "implementation"
    COMPLETED = "completed"


class DeliveryRequestKind(StrEnum):
    """Bounded user request categories."""

    DECISION = "decision"
    ACTION = "action"


class DeliveryWorkerRole(StrEnum):
    """Worker role selected mechanically from one canonical Delivery stage."""

    PLANNER = "planner"
    BUILDER = "builder"
    INTEGRATION_REPAIRER = "integration-repairer"


class DeliveryCheckpointTriggerKind(StrEnum):
    """Delivery-owned reasons that require Change checkpoint publication."""

    FIRST_PROMOTED_TASK = "first-promoted-task"
    VERIFIED_OUTCOME = "verified-outcome"
    FINALIZATION = "finalization"
    EXPLICIT = "explicit"


class _DeliveryModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class DeliveryChangePublicationIdentity(_DeliveryModel):
    """Provider pull-request identity retained while Change attention clears ready authority."""

    schema_version: Literal[1] = 1
    change_id: str = Field(min_length=1)
    repository: str = Field(min_length=3, pattern=r"^[^\s/]+/[^\s/]+$")
    number: int = Field(gt=0)
    node_id: str = Field(min_length=1)
    head_sha: str = Field(pattern=r"^[0-9a-f]{40}$")


class DeliveryChangeDeferral(_DeliveryModel):
    """Durable user disposition that pauses one nonterminal Change."""

    schema_version: Literal[1] = 1
    deferral_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    change_id: str = Field(min_length=1)
    prior_stage: DeliveryChangeStage
    deferred_at: datetime
    reason: str = Field(min_length=1)

    @classmethod
    def create(
        cls,
        *,
        change_id: str,
        prior_stage: DeliveryChangeStage,
        deferred_at: datetime,
        reason: str,
    ) -> DeliveryChangeDeferral:
        """Create one deterministic deferral receipt."""
        values = {
            "change_id": change_id,
            "prior_stage": prior_stage,
            "deferred_at": deferred_at,
            "reason": reason,
        }
        candidate = cls.model_construct(deferral_id="0" * 64, schema_version=1, **values)
        return cls(deferral_id=_receipt_digest(candidate, "deferral_id"), **values)

    @model_validator(mode="after")
    def _validate_deferral(self) -> DeliveryChangeDeferral:
        if self.prior_stage in {
            DeliveryChangeStage.DEFERRED,
            DeliveryChangeStage.ABANDONED,
            DeliveryChangeStage.COMPLETED,
        }:
            message = "Change deferral must name a non-deferred prior state"
            raise ValueError(message)
        if self.deferred_at.tzinfo is None:
            message = "Change deferral timestamp must include a timezone"
            raise ValueError(message)
        if self.deferral_id != _receipt_digest(self, "deferral_id"):
            message = "Change deferral identity is invalid"
            raise ValueError(message)
        return self


class DeliveryChangeAbandonment(_DeliveryModel):
    """Durable user disposition that terminates one uncompleted Change."""

    schema_version: Literal[1] = 1
    abandonment_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    change_id: str = Field(min_length=1)
    prior_stage: DeliveryChangeStage
    abandoned_at: datetime
    reason: str = Field(min_length=1)

    @classmethod
    def create(
        cls,
        *,
        change_id: str,
        prior_stage: DeliveryChangeStage,
        abandoned_at: datetime,
        reason: str,
    ) -> DeliveryChangeAbandonment:
        """Create one deterministic abandonment receipt."""
        values = {
            "change_id": change_id,
            "prior_stage": prior_stage,
            "abandoned_at": abandoned_at,
            "reason": reason,
        }
        candidate = cls.model_construct(abandonment_id="0" * 64, schema_version=1, **values)
        return cls(abandonment_id=_receipt_digest(candidate, "abandonment_id"), **values)

    @model_validator(mode="after")
    def _validate_abandonment(self) -> DeliveryChangeAbandonment:
        if self.prior_stage in {
            DeliveryChangeStage.ABANDONED,
            DeliveryChangeStage.COMPLETED,
        }:
            message = "Change abandonment must name a non-abandoned prior state"
            raise ValueError(message)
        if self.abandoned_at.tzinfo is None:
            message = "Change abandonment timestamp must include a timezone"
            raise ValueError(message)
        if self.abandonment_id != _receipt_digest(self, "abandonment_id"):
            message = "Change abandonment identity is invalid"
            raise ValueError(message)
        return self


class DeliveryOutputReference(_DeliveryModel):
    """Claim-bound identity and digest of one separately published phase output."""

    output_id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)
    stage: DeliveryStage
    kind: DeliveryOutputKind
    digest: str = Field(pattern=r"^[0-9a-f]{64}$")


class DeliveryTaskDefinition(_DeliveryModel):
    """Immutable executable authority for one bounded implementation result."""

    task_id: str = Field(min_length=1)
    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    plan_scope_id: str = Field(pattern=r"^SCOPE-[0-9]{3}$")
    title: str = Field(min_length=1)
    result: str = Field(min_length=1)
    commitment_ids: tuple[str, ...]
    dependency_ids: tuple[str, ...]
    required_outputs: tuple[str, ...] = Field(min_length=1)
    maintained_surfaces: tuple[str, ...] = Field(min_length=1)
    constraints: tuple[str, ...]
    exclusions: tuple[str, ...]
    acceptance_observations: tuple[str, ...] = Field(min_length=1)
    proof_boundaries: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_references(self) -> DeliveryTaskDefinition:
        for references in (self.commitment_ids, self.dependency_ids):
            if len(references) != len(set(references)):
                message = "Delivery task references must be unique"
                raise ValueError(message)
        return self

    @property
    def digest(self) -> str:
        """Return the canonical immutable task-definition digest."""
        return hashlib.sha256(_model_content(self)).hexdigest()


class DeliveryObservation(_DeliveryModel):
    """Typed validation evidence before its immutable receipt identity is assigned."""

    schema_version: Literal[1] = 1
    change_id: str = Field(min_length=1)
    task_or_finalization_id: str = Field(min_length=1)
    step_id: str | None = Field(default=None, min_length=1)
    exact_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    observation_kind: str = Field(min_length=1)
    command_or_procedure: str = Field(min_length=1)
    exit_status_or_artifact_locator: str = Field(min_length=1)
    observer_or_runner_identity: str = Field(min_length=1)
    observed_at: datetime


class DeliveryObservationReceipt(DeliveryObservation):
    """One exact-commit validation observation retained as lifecycle evidence."""

    observation_id: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def create(
        cls,
        observation: DeliveryObservation,
    ) -> DeliveryObservationReceipt:
        """Create one receipt using the canonical typed-content digest."""
        values = observation.model_dump()
        candidate = cls.model_construct(observation_id="0" * 64, **values)
        return cls(observation_id=_receipt_digest(candidate, "observation_id"), **values)

    @model_validator(mode="after")
    def _validate_receipt(self) -> DeliveryObservationReceipt:
        if self.observed_at.tzinfo is None:
            message = "Delivery observation timestamp must include a timezone"
            raise ValueError(message)
        if self.observation_id != _receipt_digest(self, "observation_id"):
            message = "Delivery observation receipt identity is invalid"
            raise ValueError(message)
        return self


class DeliveryReview(_DeliveryModel):
    """Typed independent advisory pass before receipt identity is assigned."""

    schema_version: Literal[1] = 1
    exact_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    author_id: str = Field(min_length=1)
    reviewer_id: str = Field(min_length=1)
    disposition: Literal["pass"] = "pass"
    evidence: tuple[str, ...] = Field(min_length=1)
    reviewed_at: datetime


class DeliveryReviewReceipt(DeliveryReview):
    """Independent advisory pass bound to one exact implementation commit."""

    review_id: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def create(
        cls,
        review: DeliveryReview,
    ) -> DeliveryReviewReceipt:
        """Create one independent pass receipt using the canonical digest."""
        values = review.model_dump()
        candidate = cls.model_construct(review_id="0" * 64, **values)
        return cls(review_id=_receipt_digest(candidate, "review_id"), **values)

    @model_validator(mode="after")
    def _validate_receipt(self) -> DeliveryReviewReceipt:
        if self.author_id == self.reviewer_id:
            message = "Delivery review must be independent from implementation authorship"
            raise ValueError(message)
        if self.reviewed_at.tzinfo is None:
            message = "Delivery review timestamp must include a timezone"
            raise ValueError(message)
        if self.review_id != _receipt_digest(self, "review_id"):
            message = "Delivery review receipt identity is invalid"
            raise ValueError(message)
        return self


class DeliveryPlanCandidate(_DeliveryModel):
    """One unpromoted claim-scoped canonical task chain."""

    candidate_id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)
    digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    tasks: tuple[DeliveryTaskDefinition, ...] = Field(min_length=1)

    @property
    def output(self) -> DeliveryOutputReference:
        """Return the phase-output reference required for promotion."""
        return DeliveryOutputReference(
            output_id=self.candidate_id,
            claim_id=self.claim_id,
            stage=DeliveryStage.PLANNING,
            kind=DeliveryOutputKind.PLANNING,
            digest=self.digest,
        )


class DeliveryTaskResult(_DeliveryModel):
    """Compact immutable binding from promoted task authority to one exact commit."""

    result_id: str = Field(min_length=1)
    change_id: str = Field(min_length=1)
    authority_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    task_id: str = Field(min_length=1)
    task_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    completed_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    observations: tuple[DeliveryObservationReceipt, ...] = Field(min_length=1)
    review: DeliveryReviewReceipt

    @model_validator(mode="after")
    def _validate_exact_commit_evidence(self) -> DeliveryTaskResult:
        observation_ids = tuple(observation.observation_id for observation in self.observations)
        if len(observation_ids) != len(set(observation_ids)):
            message = "Delivery task result observations must be unique"
            raise ValueError(message)
        if any(
            observation.change_id != self.change_id
            or observation.task_or_finalization_id != self.task_id
            or observation.exact_commit != self.completed_commit
            for observation in self.observations
        ):
            message = "Delivery task result observation evidence does not match the exact task commit"
            raise ValueError(message)
        if self.review.exact_commit != self.completed_commit:
            message = "Delivery task result review evidence does not match the exact task commit"
            raise ValueError(message)
        return self


class DeliveryFinalization(_DeliveryModel):
    """Exact reviewed Change head and evidence prepared for finalization."""

    schema_version: Literal[2] = 2
    operation_id: str = Field(min_length=1)
    change_id: str = Field(min_length=1)
    exact_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    authority_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    result_digests: tuple[str, ...] = Field(min_length=1)
    observations: tuple[DeliveryObservationReceipt, ...] = Field(min_length=1)
    review: DeliveryReviewReceipt
    finalized_at: datetime


class DeliveryFinalizationReceipt(DeliveryFinalization):
    """Durable finalization authority for one exact reviewed Change head."""

    finalization_id: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def create(cls, finalization: DeliveryFinalization) -> DeliveryFinalizationReceipt:
        """Create one finalization receipt using the canonical typed-content digest."""
        values = {field_name: getattr(finalization, field_name) for field_name in type(finalization).model_fields}
        candidate = cls.model_construct(finalization_id="0" * 64, **values)
        return cls(finalization_id=_receipt_digest(candidate, "finalization_id"), **values)

    @model_validator(mode="after")
    def _validate_receipt(self) -> DeliveryFinalizationReceipt:
        if self.finalized_at.tzinfo is None:
            message = "Delivery finalization timestamp must include a timezone"
            raise ValueError(message)
        if len(self.result_digests) != len(set(self.result_digests)):
            message = "Delivery finalization result digests must be unique"
            raise ValueError(message)
        observation_ids = tuple(observation.observation_id for observation in self.observations)
        if len(observation_ids) != len(set(observation_ids)):
            message = "Delivery finalization observations must be unique"
            raise ValueError(message)
        if any(
            observation.change_id != self.change_id
            or observation.task_or_finalization_id != self.operation_id
            or observation.exact_commit != self.exact_head
            for observation in self.observations
        ):
            message = "Delivery finalization observations do not match its exact authority"
            raise ValueError(message)
        if self.review.exact_commit != self.exact_head:
            message = "Delivery finalization review does not match its exact head"
            raise ValueError(message)
        if self.finalization_id != _receipt_digest(self, "finalization_id"):
            message = "Delivery finalization receipt identity is invalid"
            raise ValueError(message)
        return self


class DeliveryFinalizationInvalidation(_DeliveryModel):
    """Observed Change-head drift that invalidates one finalization receipt."""

    schema_version: Literal[1] = 1
    change_id: str = Field(min_length=1)
    finalization_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    observed_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    reason: Literal["head-drift"] = "head-drift"
    invalidated_at: datetime


class DeliveryFinalizationInvalidationReceipt(DeliveryFinalizationInvalidation):
    """Durable evidence that exact-head finalization no longer holds."""

    invalidation_id: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def create(
        cls,
        invalidation: DeliveryFinalizationInvalidation,
    ) -> DeliveryFinalizationInvalidationReceipt:
        """Create one finalization invalidation using the canonical digest."""
        values = invalidation.model_dump()
        candidate = cls.model_construct(invalidation_id="0" * 64, **values)
        return cls(invalidation_id=_receipt_digest(candidate, "invalidation_id"), **values)

    @model_validator(mode="after")
    def _validate_receipt(self) -> DeliveryFinalizationInvalidationReceipt:
        if self.expected_head == self.observed_head:
            message = "Delivery finalization invalidation requires head drift"
            raise ValueError(message)
        if self.invalidated_at.tzinfo is None:
            message = "Delivery finalization invalidation timestamp must include a timezone"
            raise ValueError(message)
        if self.invalidation_id != _receipt_digest(self, "invalidation_id"):
            message = "Delivery finalization invalidation identity is invalid"
            raise ValueError(message)
        return self


class DeliveryMergedPullRequestLatch(_DeliveryModel):
    """Immutable first merged evidence for one finalized pull request."""

    schema_version: Literal[1] = 1
    change_id: str = Field(min_length=1)
    finalization_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    ready_receipt_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    acceptance_observation_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    provider_evidence_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    repository: str = Field(min_length=3, pattern=r"^[^\s/]+/[^\s/]+$")
    number: int = Field(gt=0)
    node_id: str = Field(min_length=1)
    base_branch: str = Field(min_length=1)
    head_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    accepted_merge_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    merged_at: datetime

    @model_validator(mode="after")
    def _validate_timestamp(self) -> DeliveryMergedPullRequestLatch:
        if self.merged_at.tzinfo is None:
            message = "merged pull-request latch timestamp must include a timezone"
            raise ValueError(message)
        return self


class DeliveryChangeCompletion(_DeliveryModel):
    """Minimal terminal projection of one durable completion receipt."""

    completion_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    completed_at: datetime

    @model_validator(mode="after")
    def _validate_timestamp(self) -> DeliveryChangeCompletion:
        if self.completed_at.tzinfo is None:
            message = "Delivery Change completion timestamp must include a timezone"
            raise ValueError(message)
        return self


class DeliveryChangeDisposition(_DeliveryModel):
    """First-write-wins evidence that a Change requires explicit attention."""

    schema_version: Literal[1] = 1
    disposition_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    kind: DeliveryChangeDispositionKind
    change_id: str = Field(min_length=1)
    entered_from: DeliveryChangeStage
    recorded_at: datetime
    diagnostics: tuple[str, ...] = Field(min_length=1)

    @classmethod
    def create(
        cls,
        *,
        kind: DeliveryChangeDispositionKind,
        change_id: str,
        entered_from: DeliveryChangeStage,
        recorded_at: datetime,
        diagnostics: tuple[str, ...],
    ) -> DeliveryChangeDisposition:
        """Create one deterministic attention record from typed evidence."""
        values = {
            "kind": kind,
            "change_id": change_id,
            "entered_from": entered_from,
            "recorded_at": recorded_at,
            "diagnostics": diagnostics,
        }
        candidate = cls.model_construct(disposition_id="0" * 64, schema_version=1, **values)
        return cls(disposition_id=_receipt_digest(candidate, "disposition_id"), **values)

    @model_validator(mode="after")
    def _validate_disposition(self) -> DeliveryChangeDisposition:
        if self.entered_from == DeliveryChangeStage.COMPLETED:
            message = "Change attention cannot be entered from completed state"
            raise ValueError(message)
        if (
            self.kind == DeliveryChangeDispositionKind.ACCEPTANCE_ATTENTION
            and self.entered_from != DeliveryChangeStage.AWAITING_MERGE
        ):
            message = "acceptance attention must be entered from awaiting-merge state"
            raise ValueError(message)
        if self.recorded_at.tzinfo is None:
            message = "Change disposition timestamp must include a timezone"
            raise ValueError(message)
        if self.disposition_id != _receipt_digest(self, "disposition_id"):
            message = "Change disposition identity is invalid"
            raise ValueError(message)
        return self


class DeliveryChangeDispositionResolution(_DeliveryModel):
    """Durable evidence that one Change attention record was explicitly cleared."""

    schema_version: Literal[1] = 1
    resolution_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    change_id: str = Field(min_length=1)
    disposition_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    resolved_at: datetime

    @classmethod
    def create(
        cls,
        *,
        change_id: str,
        disposition_id: str,
        resolved_at: datetime,
    ) -> DeliveryChangeDispositionResolution:
        """Create one deterministic resolution receipt for exact attention authority."""
        values = {
            "change_id": change_id,
            "disposition_id": disposition_id,
            "resolved_at": resolved_at,
        }
        candidate = cls.model_construct(resolution_id="0" * 64, schema_version=1, **values)
        return cls(resolution_id=_receipt_digest(candidate, "resolution_id"), **values)

    @model_validator(mode="after")
    def _validate_resolution(self) -> DeliveryChangeDispositionResolution:
        if self.resolved_at.tzinfo is None:
            message = "Change disposition resolution timestamp must include a timezone"
            raise ValueError(message)
        if self.resolution_id != _receipt_digest(self, "resolution_id"):
            message = "Change disposition resolution identity is invalid"
            raise ValueError(message)
        return self


class DeliveryCheckpointTrigger(_DeliveryModel):
    """One durable reason to publish an exact reviewed Change head."""

    kind: DeliveryCheckpointTriggerKind
    outcome_id: str | None = Field(default=None, pattern=r"^OUT-[0-9]{3}$")

    @model_validator(mode="after")
    def _validate_identity(self) -> DeliveryCheckpointTrigger:
        if self.kind == DeliveryCheckpointTriggerKind.VERIFIED_OUTCOME:
            if self.outcome_id is None:
                message = "verified Outcome checkpoint trigger requires Outcome identity"
                raise ValueError(message)
        elif self.outcome_id is not None:
            message = "Change-level checkpoint trigger cannot name Outcome identity"
            raise ValueError(message)
        return self


class DeliveryPendingCheckpoint(_DeliveryModel):
    """Undrained obligations, anchored only when an exact reviewed head remains valid."""

    head: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    triggers: tuple[DeliveryCheckpointTrigger, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_triggers(self) -> DeliveryPendingCheckpoint:
        identities = tuple(
            (
                trigger.kind,
                trigger.outcome_id if trigger.kind == DeliveryCheckpointTriggerKind.VERIFIED_OUTCOME else None,
            )
            for trigger in self.triggers
        )
        if len(identities) != len(set(identities)):
            message = "pending checkpoint trigger kinds must be unique per scope"
            raise ValueError(message)
        return self


class DeliveryCheckpointPublicationState(_DeliveryModel):
    """Change-scoped checkpoint queue and last acknowledged remote head."""

    change_id: str = Field(min_length=1)
    published_head: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    pending_checkpoint: DeliveryPendingCheckpoint | None = None


class DeliveryResultCandidate(_DeliveryModel):
    """One unpromoted claim-scoped compact implementation result."""

    candidate_id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)
    digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    result: DeliveryTaskResult

    @property
    def output(self) -> DeliveryOutputReference:
        """Return the phase-output reference required for result promotion."""
        return DeliveryOutputReference(
            output_id=self.candidate_id,
            claim_id=self.claim_id,
            stage=DeliveryStage.IMPLEMENTATION,
            kind=DeliveryOutputKind.IMPLEMENTATION,
            digest=self.digest,
        )


class DeliveryRequestOption(_DeliveryModel):
    """One bounded Decision Request option."""

    option_id: str = Field(min_length=1)
    label: str = Field(min_length=1)


class DeliveryRequestResolution(_DeliveryModel):
    """User-owned selected option, free-text answer, or both."""

    selected_option_id: str | None = None
    response_text: str | None = None

    @model_validator(mode="after")
    def _require_answer(self) -> DeliveryRequestResolution:
        if self.selected_option_id is None and (self.response_text is None or not self.response_text.strip()):
            message = "request resolution requires a selected option or response text"
            raise ValueError(message)
        return self


class DeliveryRequest(_DeliveryModel):
    """One bounded request retained because resumed work consumes its answer."""

    request_id: str = Field(min_length=1)
    kind: DeliveryRequestKind
    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    summary: str = Field(min_length=1)
    options: tuple[DeliveryRequestOption, ...] = ()
    resolution: DeliveryRequestResolution | None = None

    @model_validator(mode="after")
    def _validate_options(self) -> DeliveryRequest:
        option_ids = tuple(option.option_id for option in self.options)
        if len(option_ids) != len(set(option_ids)):
            message = "request option identities must be unique"
            raise ValueError(message)
        if self.kind == DeliveryRequestKind.DECISION and not self.options:
            message = "Decision Requests require bounded options"
            raise ValueError(message)
        return self


class DeliveryBlock(_DeliveryModel):
    """Same-stage block and its durable clearing evidence."""

    block_id: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    unblock_condition: str = Field(min_length=1)
    expected_evidence: tuple[str, ...] = Field(min_length=1)
    locators: tuple[str, ...] = Field(min_length=1)
    request_id: str | None = None
    resolution_note: str | None = None
    resolution_locators: tuple[str, ...] = ()
    resume_commit: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")

    @property
    def resolved(self) -> bool:
        """Return whether request or operator evidence cleared this block."""
        return self.resolution_note is not None


class DeliveryOperatorMove(_DeliveryModel):
    """One operator-directed backward movement and invalidated closure."""

    move_id: str = Field(min_length=1)
    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    destination: DeliveryStage
    reason: str = Field(min_length=1)
    invalidated_outcome_ids: tuple[str, ...] = Field(min_length=1)


class DeliveryReturnContext(_DeliveryModel):
    """Exact earlier-stage context consumed by the next owning cycle."""

    target: DeliveryStage
    reason: str = Field(min_length=1)
    locators: tuple[str, ...] = Field(min_length=1)
    preserved_commit: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    completed_boundary: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    source_boundary: str | None = None


class DeliveryRecoveryAttention(_DeliveryModel):
    """Operator-consumed evidence for one Build claim that cannot be removed safely."""

    attempt_id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    worktree_path: str = Field(min_length=1)
    branch_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    worktree_head: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    last_reviewed_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    writer_claim_id: str | None = None
    custody_retained: bool
    retry_condition: str = Field(min_length=1)


class DeliveryIntegrationAttentionDisposition(StrEnum):
    """Operational route for one typed Integration attention."""

    RETRYABLE = "retryable"
    REPAIR_REQUIRED = "repair-required"
    OPERATOR_REQUIRED = "operator-required"


class DeliveryIntegrationAttentionCode(StrEnum):
    """Typed reason that atomic Integration retained completed outcomes."""

    REVISION_PENDING = "revision-pending"
    TARGET_IDENTITY_MISMATCH = "target-identity-mismatch"
    PACKAGE_MUTATED = "package-mutated"
    COMPLETED_HISTORY_MUTATED = "completed-history-mutated"
    REVIEWED_BOUNDARY_MISMATCH = "reviewed-boundary-mismatch"
    REVIEWED_WORKTREE_DIRTY = "reviewed-worktree-dirty"
    MERGE_CONFLICT = "merge-conflict"
    REPAIR_AUTHORITY = "repair-authority"
    CANDIDATE_PROOF_FAILED = "candidate-proof-failed"
    TARGET_CAS_LOST = "target-cas-lost"
    EXTERNAL_ACCEPTANCE_REQUIRED = "external-acceptance-required"


def integration_attention_disposition(
    code: DeliveryIntegrationAttentionCode,
) -> DeliveryIntegrationAttentionDisposition:
    """Return the single operational route owned by an Integration attention code."""
    if code == DeliveryIntegrationAttentionCode.TARGET_CAS_LOST:
        return DeliveryIntegrationAttentionDisposition.RETRYABLE
    if code == DeliveryIntegrationAttentionCode.MERGE_CONFLICT:
        return DeliveryIntegrationAttentionDisposition.REPAIR_REQUIRED
    return DeliveryIntegrationAttentionDisposition.OPERATOR_REQUIRED


class DeliveryIntegrationCompletion(_DeliveryModel):
    """Committed identity of one atomic Integration publication."""

    completion_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    package_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    target_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    completion_path: str = Field(min_length=1)


class DeliveryIntegrationAttention(_DeliveryModel):
    """Retryable evidence for one failed atomic Integration attempt."""

    attention_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    code: DeliveryIntegrationAttentionCode
    change_id: str = Field(min_length=1)
    change_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    target_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    integration_target: str = Field(min_length=1)
    diagnostics: tuple[str, ...] = Field(min_length=1)
    retry_condition: str = Field(min_length=1)


class DeliveryActiveClaim(_DeliveryModel):
    """Recoverable execution identity for one active outcome claim."""

    attempt_id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)
    owner_id: str = Field(min_length=1)
    process_id: str = Field(min_length=1)
    started_at: str = Field(min_length=1)
    worker_role: DeliveryWorkerRole
    task_id: str | None = None


class OutcomeAuthorityBinding(_DeliveryModel):
    """Canonical state and identity bindings for one admitted outcome."""

    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    plan_scope_id: str = Field(pattern=r"^SCOPE-[0-9]{3}$")
    stage: DeliveryStage = DeliveryStage.PLANNING
    tasks: tuple[DeliveryTaskDefinition, ...] = ()
    results: tuple[DeliveryTaskResult, ...] = ()
    active_claim: DeliveryActiveClaim | None = None
    output: DeliveryOutputReference | None = None
    candidate: DeliveryPlanCandidate | None = None
    result_candidate: DeliveryResultCandidate | None = None
    return_context: DeliveryReturnContext | None = None
    recovery_attention: DeliveryRecoveryAttention | None = None
    block: DeliveryBlock | None = None
    requests: tuple[DeliveryRequest, ...] = ()

    @model_validator(mode="after")
    def _validate_state(self) -> OutcomeAuthorityBinding:
        if self.stage == DeliveryStage.COMPLETED and self.active_claim is not None:
            message = "completed outcomes cannot carry an active claim"
            raise ValueError(message)
        self._validate_active_claim()
        self._validate_recovery_attention()
        request_ids = tuple(request.request_id for request in self.requests)
        if len(request_ids) != len(set(request_ids)):
            message = "Delivery request identities must be unique per outcome"
            raise ValueError(message)
        task_ids = self.task_ids
        result_ids = self.result_ids
        if len(task_ids) != len(set(task_ids)) or len(result_ids) != len(set(result_ids)):
            message = "Delivery task and result identities must be unique per outcome"
            raise ValueError(message)
        if not {result.task_id for result in self.results} <= set(task_ids):
            message = "Delivery results must bind promoted task authority"
            raise ValueError(message)
        return self

    def _validate_active_claim(self) -> None:
        if self.active_claim is None:
            return
        expected_role = {
            DeliveryStage.PLANNING: DeliveryWorkerRole.PLANNER,
            DeliveryStage.IMPLEMENTATION: DeliveryWorkerRole.BUILDER,
        }.get(self.stage)
        if self.active_claim.worker_role != expected_role:
            message = "active claim worker role does not match its Delivery stage"
            raise ValueError(message)
        if self.stage == DeliveryStage.IMPLEMENTATION:
            if self.active_claim.task_id not in self.task_ids:
                message = "active Build claim must name promoted task authority"
                raise ValueError(message)
        elif self.active_claim.task_id is not None:
            message = "only active Build claims name task authority"
            raise ValueError(message)

    def _validate_recovery_attention(self) -> None:
        if self.recovery_attention is None:
            return
        if (
            self.active_claim is None
            or self.recovery_attention.attempt_id != self.active_claim.attempt_id
            or self.recovery_attention.claim_id != self.active_claim.claim_id
        ):
            message = "recovery attention must bind the current active claim"
            raise ValueError(message)

    @property
    def task_ids(self) -> tuple[str, ...]:
        """Project promoted task identities from their single typed authority."""
        return tuple(task.task_id for task in self.tasks)

    @property
    def result_ids(self) -> tuple[str, ...]:
        """Project compact result identities from their single typed authority."""
        return tuple(result.result_id for result in self.results)

    @property
    def active_claim_id(self) -> str | None:
        """Project the current claim identity without persisting a duplicate scalar."""
        return self.active_claim.claim_id if self.active_claim is not None else None

    @property
    def active_task_id(self) -> str | None:
        """Project the current task identity from its active claim."""
        return self.active_claim.task_id if self.active_claim is not None else None


class DeliveryFrontier(_DeliveryModel):
    """Canonical outcome and Change checkpoint state persisted beside authority."""

    schema_version: Literal[13] = 13
    bindings: tuple[OutcomeAuthorityBinding, ...]
    published_head: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    pending_checkpoint: DeliveryPendingCheckpoint | None = None
    operator_moves: tuple[DeliveryOperatorMove, ...] = ()
    finalization: DeliveryFinalizationReceipt | None = None
    finalization_invalidation: DeliveryFinalizationInvalidationReceipt | None = None
    ready: PullRequestReadyReceipt | None = None
    change_disposition_publication: DeliveryChangePublicationIdentity | None = None
    merged_pull_request_latch: DeliveryMergedPullRequestLatch | None = None
    change_completion: DeliveryChangeCompletion | None = None
    change_deferral: DeliveryChangeDeferral | None = None
    change_abandonment: DeliveryChangeAbandonment | None = None
    change_disposition: DeliveryChangeDisposition | None = None
    change_disposition_resolution: DeliveryChangeDispositionResolution | None = None
    integration_result_id: str | None = None
    integration_completion: DeliveryIntegrationCompletion | None = None
    integration_attention: DeliveryIntegrationAttention | None = None
    integration_repair_claim: DeliveryActiveClaim | None = None

    @model_validator(mode="after")
    def _validate_identities(self) -> DeliveryFrontier:
        outcome_ids = tuple(binding.outcome_id for binding in self.bindings)
        scope_ids = tuple(binding.plan_scope_id for binding in self.bindings)
        move_ids = tuple(move.move_id for move in self.operator_moves)
        if len(outcome_ids) != len(set(outcome_ids)) or len(scope_ids) != len(set(scope_ids)):
            message = "Delivery frontier identities must be unique"
            raise ValueError(message)
        if len(move_ids) != len(set(move_ids)):
            message = "Delivery operator move identities must be unique"
            raise ValueError(message)
        if (self.integration_result_id is None) != (self.integration_completion is None):
            message = "Integration result identity and completion must be published together"
            raise ValueError(message)
        if (
            self.integration_completion is not None
            and self.integration_result_id != self.integration_completion.completion_id
        ):
            message = "Integration result identity must match its completion"
            raise ValueError(message)
        if self.integration_completion is not None and self.integration_attention is not None:
            message = "completed Integration cannot retain attention"
            raise ValueError(message)
        self._validate_lifecycle_dispositions()
        self._validate_change_disposition()
        if self.finalization is not None and self.finalization_invalidation is not None:
            message = "Delivery finalization and invalidation cannot coexist"
            raise ValueError(message)
        if self.ready is not None and (
            self.finalization is None
            or self.ready.change_id != self.finalization.change_id
            or self.ready.finalization_id != self.finalization.finalization_id
            or self.ready.head_sha != self.finalization.exact_head
        ):
            message = "pull-request ready authority requires its exact current finalization"
            raise ValueError(message)
        if self.finalization is not None and (
            any(binding.stage != DeliveryStage.COMPLETED for binding in self.bindings)
            or any(binding.active_claim is not None for binding in self.bindings)
            or self.integration_repair_claim is not None
            or self.integration_completion is not None
        ):
            message = "Delivery finalization requires completed unclaimed outcome authority"
            raise ValueError(message)
        return self

    def _validate_lifecycle_dispositions(self) -> None:
        if self.change_deferral is not None and self.change_abandonment is not None:
            message = "Change deferral and abandonment cannot coexist"
            raise ValueError(message)
        if self.change_deferral is not None and (
            self.change_completion is not None or self.integration_completion is not None
        ):
            message = "deferred Change cannot retain terminal completion authority"
            raise ValueError(message)
        if self.change_abandonment is not None and (
            self.change_completion is not None
            or self.integration_completion is not None
            or self.change_disposition is not None
            or self.change_disposition_publication is not None
            or self.integration_attention is not None
            or self.integration_repair_claim is not None
            or self.ready is not None
            or self.merged_pull_request_latch is not None
        ):
            message = "abandoned Change cannot retain active or terminal authority"
            raise ValueError(message)
        if self.change_deferral is not None and any(binding.active_claim is not None for binding in self.bindings):
            message = "deferred Change cannot retain an active mutation claim"
            raise ValueError(message)
        if self.change_abandonment is not None and any(binding.active_claim is not None for binding in self.bindings):
            message = "abandoned Change cannot retain an active mutation claim"
            raise ValueError(message)

    def _validate_change_disposition(self) -> None:
        if self.change_disposition is None:
            if self.change_disposition_publication is not None:
                message = "Change publication identity requires current Change attention"
                raise ValueError(message)
            return
        if self.change_completion is not None or self.integration_completion is not None:
            message = "Change disposition cannot coexist with terminal completion authority"
            raise ValueError(message)
        if (
            any(binding.active_claim is not None for binding in self.bindings)
            or self.integration_repair_claim is not None
        ):
            message = "Change attention cannot retain an active mutation claim"
            raise ValueError(message)
        resolution = self.change_disposition_resolution
        if resolution is not None and resolution.change_id != self.change_disposition.change_id:
            message = "Change attention and its resolution must bind the same Change"
            raise ValueError(message)
        publication = self.change_disposition_publication
        if publication is not None and publication.change_id != self.change_disposition.change_id:
            message = "Change attention and its publication identity must bind the same Change"
            raise ValueError(message)
        if resolution is not None and resolution.disposition_id == self.change_disposition.disposition_id:
            message = "Change attention cannot retain its own resolution receipt"
            raise ValueError(message)

    @model_validator(mode="after")
    def _validate_change_completion(self) -> DeliveryFrontier:
        if self.change_completion is None:
            return self
        if self.finalization is None or self.ready is None or self.merged_pull_request_latch is None:
            message = "Delivery Change completion requires finalization, ready, and merged evidence"
            raise ValueError(message)
        if self.integration_result_id is not None or self.integration_completion is not None:
            message = "Delivery Change completion cannot coexist with legacy Integration completion"
            raise ValueError(message)
        return self

    @model_validator(mode="after")
    def _validate_integration_repair_claim(self) -> DeliveryFrontier:
        if self.integration_repair_claim is not None:
            if self.integration_repair_claim.worker_role != DeliveryWorkerRole.INTEGRATION_REPAIRER:
                message = "Integration repair claim must use the repair worker role"
                raise ValueError(message)
            if self.integration_repair_claim.task_id is not None:
                message = "Integration repair claim cannot name task authority"
                raise ValueError(message)
            if (
                self.integration_attention is None
                or integration_attention_disposition(self.integration_attention.code)
                != DeliveryIntegrationAttentionDisposition.REPAIR_REQUIRED
            ):
                message = "Integration repair claim requires current repair attention"
                raise ValueError(message)
            if any(binding.active_claim is not None for binding in self.bindings):
                message = "Integration repair claim cannot coexist with outcome claims"
                raise ValueError(message)
        return self


class ActivateDeliveryClaim(_DeliveryModel):
    """Claim one dependency-ready outcome in its current stage."""

    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    claim: DeliveryActiveClaim

    @property
    def claim_id(self) -> str:
        """Return the nested claim identity used by transition requests."""
        return self.claim.claim_id

    @property
    def task_id(self) -> str | None:
        """Return the nested task identity used by Build selection."""
        return self.claim.task_id


class PublishDeliveryOutput(_DeliveryModel):
    """Publish one claim-scoped candidate output without moving stage."""

    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    claim_id: str = Field(min_length=1)
    output: DeliveryOutputReference


class PublishDeliveryPlan(_DeliveryModel):
    """Publish one complete claim-scoped task-chain candidate."""

    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    claim_id: str = Field(min_length=1)
    tasks: tuple[DeliveryTaskDefinition, ...] = Field(min_length=1)


class PublishDeliveryResult(_DeliveryModel):
    """Publish one compact claim-scoped implementation result."""

    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    claim_id: str = Field(min_length=1)
    result: DeliveryTaskResult


class FinalizeDeliveryChange(_DeliveryModel):
    """Finalize one exact reviewed Change head with exact-commit evidence."""

    operation_id: str = Field(min_length=1)
    exact_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    observations: tuple[DeliveryObservationReceipt, ...] = Field(min_length=1)
    review: DeliveryReviewReceipt

    @model_validator(mode="after")
    def _validate_exact_commit_evidence(self) -> FinalizeDeliveryChange:
        observation_ids = tuple(observation.observation_id for observation in self.observations)
        if len(observation_ids) != len(set(observation_ids)):
            message = "Delivery finalization observations must be unique"
            raise ValueError(message)
        if any(
            observation.task_or_finalization_id != self.operation_id or observation.exact_commit != self.exact_head
            for observation in self.observations
        ):
            message = "Delivery finalization observations do not match the exact head"
            raise ValueError(message)
        if self.review.exact_commit != self.exact_head:
            message = "Delivery finalization review does not match the exact head"
            raise ValueError(message)
        return self


class AdvanceDelivery(_DeliveryModel):
    """Advance after naming the required current-stage output."""

    action: Literal["advance"] = "advance"
    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    claim_id: str = Field(min_length=1)
    output: DeliveryOutputReference


class RetryDelivery(_DeliveryModel):
    """End a claim and leave its outcome in the same stage."""

    action: Literal["retry"] = "retry"
    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    claim_id: str = Field(min_length=1)
    abandoned_commit: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    attempt_id: str | None = None


class ReturnDelivery(_DeliveryModel):
    """Return one claim to an allowed earlier stage with successor context."""

    action: Literal["return"] = "return"
    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    claim_id: str = Field(min_length=1)
    target: DeliveryStage
    reason: str = Field(min_length=1)
    locators: tuple[str, ...] = Field(min_length=1)
    preserved_commit: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    attempt_id: str | None = None
    source_boundary: str | None = None


class BlockDelivery(_DeliveryModel):
    """End one claim in place with an optional bounded user request."""

    action: Literal["block"] = "block"
    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    claim_id: str = Field(min_length=1)
    block_id: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    unblock_condition: str = Field(min_length=1)
    expected_evidence: tuple[str, ...] = Field(min_length=1)
    locators: tuple[str, ...] = Field(min_length=1)
    request: DeliveryRequest | None = None
    resume_commit: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")


type DeliveryTransition = Annotated[
    AdvanceDelivery | RetryDelivery | ReturnDelivery | BlockDelivery,
    Field(discriminator="action"),
]
DELIVERY_TRANSITION_ADAPTER = TypeAdapter(DeliveryTransition)


class AdministrativeDeliveryMove(_DeliveryModel):
    """Authorized operator movement to one earlier canonical stage."""

    move_id: str = Field(min_length=1)
    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    target: DeliveryStage
    reason: str = Field(min_length=1)
    expected_version: str = Field(pattern=r"^[0-9a-f]{64}$")


class AdministrativeDeliveryMovePreview(_DeliveryModel):
    """Exact invalidation closure bound to one frontier version."""

    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    target: DeliveryStage
    snapshot_version: str = Field(pattern=r"^[0-9a-f]{64}$")
    invalidated_outcome_ids: tuple[str, ...] = Field(min_length=1)


class AdministrativeDeliveryMoveResult(_DeliveryModel):
    """Persisted operator movement and its invalidated dependent closure."""

    move: DeliveryOperatorMove
    invalidated_outcome_ids: tuple[str, ...]


class DeliveryRuntimeConflictError(RuntimeError):
    """A Delivery mutation is stale or violates canonical routing invariants."""

    code = "ERR_DELIVERY_RUNTIME_CONFLICT"


class DeliveryChangeDispositionConflictError(DeliveryRuntimeConflictError):
    """An exact Change attention identity is stale or no longer active."""

    retry_safe = False


class DeliveryAcceptanceWaitingError(DeliveryRuntimeConflictError):
    """The bound pull request is still open and has not reached acceptance."""

    code = "ERR_DELIVERY_ACCEPTANCE_WAITING"


class DeliveryRuntimeReferenceError(ValueError):
    """A Delivery mutation references absent contract authority."""

    code = "ERR_DELIVERY_RUNTIME_REFERENCE"


_STAGE_ORDER = {
    DeliveryStage.DESIGN: 0,
    DeliveryStage.PLANNING: 1,
    DeliveryStage.IMPLEMENTATION: 2,
    DeliveryStage.COMPLETED: 3,
}
_PREVIOUS_FRONTIER_SCHEMA_VERSIONS = frozenset({2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12})
_FRONTIER_SCHEMA_VERSION = 13
_FINALIZATION_SCHEMA_VERSION = 2
_LEGACY_FINALIZATION_MESSAGE = "legacy finalization authority requires explicit re-finalization"
_CHECKPOINT_BACKFILL_SCHEMA_VERSIONS = frozenset({1, 2})
_RETURN_TARGETS = {
    DeliveryStage.PLANNING: {DeliveryStage.DESIGN},
    DeliveryStage.IMPLEMENTATION: {DeliveryStage.PLANNING, DeliveryStage.DESIGN},
}
_NORMAL_CHANGE_MUTATIONS = frozenset(
    {
        "record_checkpoint_branch_publication",
        "acknowledge_checkpoint_publication",
        "mark_awaiting_merge",
        "reconcile_pull_request_draft_state",
        "latch_merged_pull_request",
        "complete_change",
        "finalize_change",
        "reconcile_finalization_head",
        "remove_integration_repair_claim",
        "remove_active_claim",
        "publish_recovery_attention",
        "activate_claim",
        "publish_output",
        "publish_plan",
        "publish_result",
        "transition",
        "resolve_request",
        "unblock",
        "administrative_move",
        "defer_change",
        "resume_change",
        "abandon_change",
    }
)


def is_change_terminal(frontier: DeliveryFrontier) -> bool:
    """Return whether one frontier has terminal Change authority."""
    return (
        frontier.change_abandonment is not None
        or frontier.change_completion is not None
        or frontier.integration_result_id is not None
    )


def derive_change_stage(frontier: DeliveryFrontier) -> DeliveryChangeStage:
    """Derive the canonical Change stage from frontier authority."""
    if frontier.change_abandonment is not None:
        stage = DeliveryChangeStage.ABANDONED
    elif frontier.change_deferral is not None:
        stage = DeliveryChangeStage.DEFERRED
    elif frontier.change_disposition is not None:
        stage = {
            DeliveryChangeDispositionKind.PUBLICATION_ATTENTION: DeliveryChangeStage.PUBLICATION_ATTENTION,
            DeliveryChangeDispositionKind.ACCEPTANCE_ATTENTION: DeliveryChangeStage.ACCEPTANCE_ATTENTION,
        }[frontier.change_disposition.kind]
    elif is_change_terminal(frontier):
        stage = DeliveryChangeStage.COMPLETED
    elif frontier.ready is not None:
        stage = DeliveryChangeStage.AWAITING_MERGE
    elif frontier.finalization is not None:
        stage = DeliveryChangeStage.FINALIZED
    elif DeliveryStage.DESIGN in {binding.stage for binding in frontier.bindings}:
        stage = DeliveryChangeStage.DESIGN
    else:
        stage = DeliveryChangeStage.BUILDING
    return stage


class DeliveryRuntime:
    """Apply worker instructions and operator correction to one Delivery frontier."""

    def __init__(
        self,
        runtime_root: Path,
        contract: DeliveryContract,
        *,
        workspace_manager: ChangeWorkspaceManager | None = None,
        migration_reviewed_head: str | None = None,
    ) -> None:
        self._target_root = runtime_root.resolve()
        self._contract = contract
        self._workspace_manager = workspace_manager
        self._migration_reviewed_head = migration_reviewed_head
        self._authority_digest = hashlib.sha256(_model_content(contract)).hexdigest()
        self._frontier_path = self._target_root / "changes" / contract.change_id / "frontier.json"
        self._validate_frontier(self._read()[0])

    @property
    def authority_digest(self) -> str:
        """Return the canonical admitted contract digest bound into task results."""
        return self._authority_digest

    @property
    def contract(self) -> DeliveryContract:
        """Return immutable admitted authority for scoped context projection."""
        return self._contract

    def frontier_bytes(self) -> bytes:
        """Return current canonical frontier bytes for OCC and failure proof."""
        return self._read()[1]

    def integration_completion(self) -> DeliveryIntegrationCompletion | None:
        """Return the committed Integration identity when publication completed."""
        return self._read()[0].integration_completion

    def integration_attention(self) -> DeliveryIntegrationAttention | None:
        """Return current retryable Integration evidence, if any."""
        return self._read()[0].integration_attention

    def change_disposition(self) -> DeliveryChangeDisposition | None:
        """Return current Change-level attention evidence, if any."""
        return self._read()[0].change_disposition

    def change_disposition_resolution(self) -> DeliveryChangeDispositionResolution | None:
        """Return the most recent durable Change attention resolution receipt."""
        return self._read()[0].change_disposition_resolution

    def change_deferral(self) -> DeliveryChangeDeferral | None:
        """Return the current user-requested Change deferral, if any."""
        return self._read()[0].change_deferral

    def change_abandonment(self) -> DeliveryChangeAbandonment | None:
        """Return the terminal user-requested Change abandonment, if any."""
        return self._read()[0].change_abandonment

    def defer_change(self, reason: str, deferred_at: datetime) -> DeliveryChangeDeferral:
        """Pause one nonterminal Change while retaining its exact frontier and worktree."""
        frontier, previous = self._read()
        if frontier.change_deferral is not None:
            return frontier.change_deferral
        _require_change_mutable(frontier, "defer_change")
        if frontier.change_abandonment is not None or is_change_terminal(frontier):
            _conflict("terminal Delivery Change cannot be deferred")
        _require_no_active_change_claim(frontier, "Change deferral")
        prior_stage = derive_change_stage(frontier)
        if prior_stage in {DeliveryChangeStage.DEFERRED, DeliveryChangeStage.ABANDONED}:
            _conflict("Change is not eligible for deferral")
        deferral = DeliveryChangeDeferral.create(
            change_id=self._contract.change_id,
            prior_stage=prior_stage,
            deferred_at=deferred_at,
            reason=reason,
        )
        self._replace(previous, frontier.model_copy(update={"change_deferral": deferral}))
        return deferral

    def resume_change(self) -> DeliveryChangeDeferral:
        """Resume one exact deferred Change and return its preserved prior-state receipt."""
        frontier, previous = self._read()
        if frontier.change_abandonment is not None or is_change_terminal(frontier):
            _conflict("terminal Delivery Change cannot be resumed")
        _require_change_mutable(frontier, "resume_change")
        deferral = frontier.change_deferral
        if deferral is None:
            _conflict("Delivery Change is not deferred")
        _require_no_active_change_claim(frontier, "Change resume")
        self._replace(previous, frontier.model_copy(update={"change_deferral": None}))
        return deferral

    def abandon_change(self, reason: str, abandoned_at: datetime) -> DeliveryChangeAbandonment:
        """Terminate one uncompleted Change without discarding its retained authority."""
        frontier, previous = self._read()
        if frontier.change_abandonment is not None:
            return frontier.change_abandonment
        if frontier.change_completion is not None or frontier.integration_result_id is not None:
            _conflict("completed Delivery Change cannot be abandoned")
        _require_change_mutable(frontier, "abandon_change")
        _require_no_active_change_claim(frontier, "Change abandonment")
        prior_stage = derive_change_stage(frontier)
        if prior_stage == DeliveryChangeStage.ABANDONED:
            _conflict("Change is not eligible for abandonment")
        abandonment = DeliveryChangeAbandonment.create(
            change_id=self._contract.change_id,
            prior_stage=prior_stage,
            abandoned_at=abandoned_at,
            reason=reason,
        )
        self._replace(
            previous,
            frontier.model_copy(
                update={
                    "change_abandonment": abandonment,
                    "change_deferral": None,
                    "change_disposition": None,
                    "change_disposition_publication": None,
                    "pending_checkpoint": None,
                    "ready": None,
                    "merged_pull_request_latch": None,
                    "integration_attention": None,
                    "integration_repair_claim": None,
                }
            ),
        )
        return abandonment

    def capture_change_disposition(
        self,
        disposition: DeliveryChangeDisposition,
        *,
        clear_ready: bool = False,
        publication_identity: DeliveryChangePublicationIdentity | None = None,
    ) -> DeliveryChangeDisposition:
        """Persist one first-write-wins Change attention record."""
        frontier, previous = self._read()
        existing = frontier.change_disposition
        if existing is not None:
            if (
                existing.kind == disposition.kind
                and existing.change_id == disposition.change_id
                and existing.entered_from == disposition.entered_from
                and existing.diagnostics == disposition.diagnostics
            ):
                if publication_identity is not None and frontier.change_disposition_publication is None:
                    self._replace(
                        previous,
                        frontier.model_copy(update={"change_disposition_publication": publication_identity}),
                    )
                elif (
                    publication_identity is not None and frontier.change_disposition_publication != publication_identity
                ):
                    _conflict("Delivery Change attention has different publication identity")
                return existing
            _conflict("Delivery Change already has different attention authority")
        if is_change_terminal(frontier):
            _conflict("completed Delivery Change cannot retain attention")
        _require_no_active_change_claim(frontier, "Change attention capture")
        if disposition.change_id != self._contract.change_id:
            _conflict("Change disposition does not match the admitted Change")
        if disposition.entered_from != derive_change_stage(frontier):
            _conflict("Change disposition does not match the current lifecycle stage")
        retained_publication = publication_identity
        if retained_publication is None and clear_ready:
            retained_publication = _pull_request_identity(frontier.ready)
        updated = frontier.model_copy(
            update={
                "change_disposition": disposition,
                "change_disposition_publication": retained_publication,
                "change_disposition_resolution": None,
                "ready": None if clear_ready else frontier.ready,
            }
        )
        self._replace(previous, updated)
        return disposition

    def resolve_change_disposition(
        self,
        expected_disposition_id: str,
        resolved_at: datetime,
    ) -> DeliveryChangeDispositionResolution:
        """Clear one exact Change attention record without restoring provider authority."""
        frontier, previous = self._read()
        current = frontier.change_disposition
        existing = frontier.change_disposition_resolution
        if current is None:
            if existing is not None and existing.disposition_id == expected_disposition_id:
                return existing
            _attention_conflict("Delivery Change attention is absent or already resolved")
        if current.disposition_id != expected_disposition_id:
            _attention_conflict("Delivery Change attention identity is stale")
        _require_no_active_change_claim(frontier, "Change attention resolution")
        resolution = DeliveryChangeDispositionResolution.create(
            change_id=self._contract.change_id,
            disposition_id=current.disposition_id,
            resolved_at=resolved_at,
        )
        updated = frontier.model_copy(
            update={
                "change_disposition": None,
                "change_disposition_publication": None,
                "change_disposition_resolution": resolution,
            }
        )
        self._replace(previous, updated)
        return resolution

    def capture_publication_attention(
        self,
        recorded_at: datetime,
        diagnostics: tuple[str, ...],
        *,
        clear_ready: bool = False,
    ) -> DeliveryChangeDisposition:
        """Capture provider publication evidence that requires operator reconciliation."""
        return self.capture_change_disposition(
            DeliveryChangeDisposition.create(
                kind=DeliveryChangeDispositionKind.PUBLICATION_ATTENTION,
                change_id=self._contract.change_id,
                entered_from=self.change_stage(),
                recorded_at=recorded_at,
                diagnostics=diagnostics,
            ),
            clear_ready=clear_ready,
        )

    def capture_acceptance_attention(
        self,
        observation: PublicationPullRequestObservationReceipt,
        diagnostics: tuple[str, ...],
    ) -> DeliveryChangeDisposition:
        """Capture one mismatched provider acceptance observation."""
        return self.capture_change_disposition(
            DeliveryChangeDisposition.create(
                kind=DeliveryChangeDispositionKind.ACCEPTANCE_ATTENTION,
                change_id=self._contract.change_id,
                entered_from=DeliveryChangeStage.AWAITING_MERGE,
                recorded_at=observation.observed_at,
                diagnostics=(*diagnostics, f"acceptance-observation:{observation.observation_id}"),
            ),
            clear_ready=True,
            publication_identity=DeliveryChangePublicationIdentity(
                change_id=self._contract.change_id,
                repository=observation.snapshot.repository,
                number=observation.snapshot.number,
                node_id=observation.snapshot.node_id,
                head_sha=observation.snapshot.head_sha,
            ),
        )

    def show_binding(self, outcome_id: str) -> OutcomeAuthorityBinding:
        """Return one current outcome binding."""
        return _find_binding(self._read()[0], outcome_id)

    def bindings(self) -> tuple[OutcomeAuthorityBinding, ...]:
        """Return current outcome bindings in admitted authority order."""
        return self._read()[0].bindings

    def finalization_readiness(self) -> tuple[bool, tuple[str, ...]]:
        """Return the same lifecycle readiness conditions enforced by finalization mutation."""
        frontier, _content = self._read()
        diagnostics: list[str] = []
        if frontier.finalization is not None:
            diagnostics.append("Delivery Change is already finalized")
        if frontier.change_completion is not None:
            diagnostics.append("Delivery Change is already completed")
        if any(binding.stage != DeliveryStage.COMPLETED for binding in frontier.bindings):
            diagnostics.append("every Outcome must be completed")
        if any(binding.active_claim is not None for binding in frontier.bindings):
            diagnostics.append("finalization cannot overlap an active Outcome claim")
        if frontier.integration_repair_claim is not None:
            diagnostics.append("finalization cannot overlap an Integration repair claim")
        if frontier.integration_completion is not None:
            diagnostics.append("completed legacy Integration cannot be finalized as a Change")
        if any(
            tuple(result.task_id for result in binding.results) != binding.task_ids for binding in frontier.bindings
        ):
            diagnostics.append("every Task result must be present in authority order")
        return not diagnostics, tuple(diagnostics)

    def checkpoint_publication_state(self) -> DeliveryCheckpointPublicationState:
        """Return the Change-level checkpoint queue without provider identity."""
        frontier, _content = self._read()
        return DeliveryCheckpointPublicationState(
            change_id=self._contract.change_id,
            published_head=frontier.published_head,
            pending_checkpoint=frontier.pending_checkpoint,
        )

    def record_checkpoint_branch_publication(
        self,
        expected: DeliveryCheckpointPublicationState,
        published_head: str,
    ) -> DeliveryCheckpointPublicationState:
        """Record one exact reconciled remote head without draining its obligations."""
        frontier, previous = self._read()
        _require_change_mutable(frontier, "record_checkpoint_branch_publication")
        pending = expected.pending_checkpoint
        if (
            expected.change_id != self._contract.change_id
            or pending is None
            or pending.head != published_head
            or frontier.published_head != expected.published_head
        ):
            _conflict("checkpoint branch publication no longer matches the durable queue")
        updated = frontier.model_copy(update={"published_head": published_head})
        self._replace(previous, updated)
        return self.checkpoint_publication_state()

    def acknowledge_checkpoint_publication(
        self,
        expected: DeliveryPendingCheckpoint,
        published_head: str,
    ) -> DeliveryCheckpointPublicationState:
        """Drain reconciled obligations while retaining any newer local checkpoint."""
        frontier, previous = self._read()
        _require_change_mutable(frontier, "acknowledge_checkpoint_publication")
        current = frontier.pending_checkpoint
        if expected.head != published_head or frontier.published_head != published_head or current is None:
            _conflict("checkpoint acknowledgment no longer matches the published head")
        if current.head == published_head:
            retained = tuple(trigger for trigger in current.triggers if trigger not in expected.triggers)
        else:
            retained = tuple(
                trigger
                for trigger in current.triggers
                if not (
                    trigger in expected.triggers and trigger.kind == DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK
                )
            )
        pending = current.model_copy(update={"triggers": retained}) if retained else None
        updated = frontier.model_copy(update={"pending_checkpoint": pending})
        self._replace(previous, updated)
        return self.checkpoint_publication_state()

    def finalization(self) -> DeliveryFinalizationReceipt | None:
        """Return current exact-head finalization authority, if any."""
        return self._read()[0].finalization

    def finalization_invalidation(self) -> DeliveryFinalizationInvalidationReceipt | None:
        """Return the latest durable finalization invalidation, if any."""
        return self._read()[0].finalization_invalidation

    def ready_receipt(self) -> PullRequestReadyReceipt | None:
        """Return durable authority that the exact finalized pull request is ready."""
        return self._read()[0].ready

    def completion_receipt(self) -> CompletionReceipt | None:
        """Return the exact terminal receipt while rejecting partial completion state."""
        frontier, _content = self._read()
        store = CompletionReceiptStore(self._target_root)
        try:
            record = store.read_bundle(self._contract.change_id)
        except CompletionReceiptConflictError:
            _conflict("terminal frontier state does not match its completion record")
        if frontier.change_completion is None:
            if record is not None:
                _conflict("completion receipt exists without terminal frontier state")
            return None
        if record is None:
            _conflict("terminal frontier state does not match its completion record")
        stored = record.receipt
        display = record.display
        if (
            stored.completion_id != frontier.change_completion.completion_id
            or stored.completed_at != frontier.change_completion.completed_at
            or display.completion_id != stored.completion_id
            or display.title != self._contract.title
            or display.outcome_titles != tuple(outcome.title for outcome in self._contract.outcomes)
        ):
            _conflict("terminal frontier state does not match its completion record")
        return stored

    def merged_pull_request_latch(self) -> DeliveryMergedPullRequestLatch | None:
        """Return immutable first merged evidence for the bound pull request."""
        return self._read()[0].merged_pull_request_latch

    def mark_awaiting_merge(self, receipt: PullRequestReadyReceipt) -> PullRequestReadyReceipt:
        """Bind provider-observed ready state to the exact current finalization."""
        frontier, previous = self._read()
        _require_change_mutable(frontier, "mark_awaiting_merge")
        finalization = frontier.finalization
        if finalization is None:
            _conflict("pull-request ready state requires current finalization authority")
        if (
            receipt.change_id != self._contract.change_id
            or receipt.finalization_id != finalization.finalization_id
            or receipt.head_sha != finalization.exact_head
        ):
            _conflict("pull-request ready receipt does not match current finalization authority")
        if frontier.ready is not None:
            if frontier.ready == receipt:
                return receipt
            _conflict("Delivery Change is already awaiting merge with different authority")
        self._replace(previous, frontier.model_copy(update={"ready": receipt}))
        return receipt

    def reconcile_pull_request_draft_state(
        self,
        *,
        provider_draft: bool,
        observed_at: datetime | None = None,
        observation_id: str | None = None,
    ) -> PullRequestReadyReceipt | None:
        """Retain ready authority only while the provider reports the PR ready."""
        frontier, _previous = self._read()
        _require_change_mutable(frontier, "reconcile_pull_request_draft_state")
        if frontier.ready is None or not provider_draft:
            return frontier.ready
        diagnostics = ((f"pull-request-observation:{observation_id}",) if observation_id is not None else ()) + (
            "provider pull request regressed to draft",
        )
        disposition = DeliveryChangeDisposition.create(
            kind=DeliveryChangeDispositionKind.PUBLICATION_ATTENTION,
            change_id=self._contract.change_id,
            entered_from=derive_change_stage(frontier),
            recorded_at=observed_at or datetime.now(UTC),
            diagnostics=diagnostics,
        )
        self.capture_change_disposition(disposition, clear_ready=True)
        return None

    def latch_merged_pull_request(
        self,
        observation: PublicationPullRequestObservationReceipt,
    ) -> DeliveryMergedPullRequestLatch:
        """Persist the first exact merged tuple and reject later regression or drift."""
        frontier, previous = self._read()
        _require_change_mutable(frontier, "latch_merged_pull_request")
        finalization = frontier.finalization
        ready = frontier.ready
        snapshot = observation.snapshot
        if finalization is None or ready is None:
            _conflict("merged pull-request evidence requires awaiting-merge authority")
        if (
            observation.change_id != self._contract.change_id
            or ready.change_id != self._contract.change_id
            or ready.finalization_id != finalization.finalization_id
            or snapshot.repository != ready.repository
            or snapshot.number != ready.number
            or snapshot.node_id != ready.node_id
            or snapshot.head_sha != finalization.exact_head
            or snapshot.head_sha != ready.head_sha
        ):
            self.capture_acceptance_attention(
                observation,
                ("provider acceptance evidence does not match awaiting-merge authority",),
            )
            _conflict("merged pull-request evidence does not match awaiting-merge authority")
        if is_acceptance_waiting_observation(observation):
            message = "provider pull request is still open and unmerged"
            raise DeliveryAcceptanceWaitingError(message)
        if not snapshot.merged or snapshot.state != "closed":
            self.capture_acceptance_attention(
                observation,
                ("provider acceptance observation is not merged and closed",),
            )
            _conflict("acceptance observation does not report a merged pull request")
        if snapshot.merged_at is None or snapshot.merge_commit_sha is None:
            self.capture_acceptance_attention(
                observation,
                ("provider acceptance observation is missing merge evidence",),
            )
            _conflict("merged pull-request evidence is incomplete")
        candidate = DeliveryMergedPullRequestLatch(
            change_id=self._contract.change_id,
            finalization_id=finalization.finalization_id,
            ready_receipt_id=ready.receipt_id,
            acceptance_observation_id=observation.observation_id,
            provider_evidence_digest=observation.provider_evidence_digest,
            repository=snapshot.repository,
            number=snapshot.number,
            node_id=snapshot.node_id,
            base_branch=snapshot.base_branch,
            head_sha=snapshot.head_sha,
            accepted_merge_commit=snapshot.merge_commit_sha,
            merged_at=snapshot.merged_at,
        )
        existing = frontier.merged_pull_request_latch
        if existing is not None:
            if (
                existing.repository,
                existing.number,
                existing.node_id,
                existing.base_branch,
                existing.head_sha,
                existing.accepted_merge_commit,
                existing.merged_at,
            ) == (
                candidate.repository,
                candidate.number,
                candidate.node_id,
                candidate.base_branch,
                candidate.head_sha,
                candidate.accepted_merge_commit,
                candidate.merged_at,
            ):
                return existing
            _conflict("merged pull-request evidence conflicts with the immutable latch")
        self._replace(previous, frontier.model_copy(update={"merged_pull_request_latch": candidate}))
        return candidate

    def complete_change(self, receipt: CompletionReceipt) -> CompletionReceipt:
        """Atomically publish one terminal receipt and its minimal frontier projection."""
        frontier, previous = self._read()
        store = CompletionReceiptStore(self._target_root)
        try:
            existing_record = store.read_bundle(self._contract.change_id)
        except CompletionReceiptConflictError:
            _conflict("completion record exists with malformed authority")
        display = CompletionDisplayMetadata.create(
            change_id=self._contract.change_id,
            completion_id=receipt.completion_id,
            title=self._contract.title,
            outcome_titles=tuple(outcome.title for outcome in self._contract.outcomes),
        )
        if frontier.change_completion is not None:
            if (
                existing_record is not None
                and existing_record.receipt == receipt
                and existing_record.display == display
                and frontier.change_completion.completion_id == receipt.completion_id
            ):
                return receipt
            _conflict("Delivery Change is already completed with different authority")
        if existing_record is not None:
            _conflict("completion receipt exists without terminal frontier state")
        _require_change_mutable(frontier, "complete_change")
        finalization = frontier.finalization
        ready = frontier.ready
        latch = frontier.merged_pull_request_latch
        if finalization is None or ready is None or latch is None:
            _conflict("Delivery Change completion requires finalized awaiting-merge evidence")
        if (
            receipt.change_id != self._contract.change_id
            or receipt.finalization_receipt_id != finalization.finalization_id
            or receipt.finalized_change_head != finalization.exact_head
            or receipt.repository_identity != latch.repository
            or receipt.pull_request_identity.number != latch.number
            or receipt.pull_request_identity.node_id != latch.node_id
            or receipt.accepted_target_ref != latch.base_branch
            or receipt.accepted_merge_commit != latch.accepted_merge_commit
            or receipt.merged_at != latch.merged_at
            or receipt.acceptance_observation_id != latch.acceptance_observation_id
            or receipt.review_receipt_ids != (finalization.review.review_id,)
        ):
            _conflict("completion receipt does not match finalization and merged evidence")
        projection = DeliveryChangeCompletion(
            completion_id=receipt.completion_id,
            completed_at=receipt.completed_at,
        )
        replacement = _model_content(frontier.model_copy(update={"change_completion": projection}))
        completion_participant = store.participant(receipt)
        display_participant = store.display_participant(display)
        frontier_participant = ReplacementTransactionParticipant(
            self._target_root,
            self._frontier_path.relative_to(self._target_root),
            previous,
            replacement,
        )
        transaction_id = hashlib.sha256(
            completion_participant.content + display_participant.content + previous + replacement
        ).hexdigest()
        RuntimeTransaction(
            self._target_root,
            f"delivery-completion-{transaction_id}",
            (completion_participant, display_participant, frontier_participant),
        ).commit()
        return receipt

    def finalize_change(
        self,
        request: FinalizeDeliveryChange,
        finalized_at: datetime,
    ) -> DeliveryFinalizationReceipt:
        """Bind completed authority and final validation to one exact Change head."""
        frontier, previous = self._read()
        _require_change_mutable(frontier, "finalize_change")
        existing = frontier.finalization
        if existing is not None:
            if (
                existing.operation_id == request.operation_id
                and existing.exact_head == request.exact_head
                and existing.observations == request.observations
                and existing.review == request.review
            ):
                return existing
            _conflict("Delivery Change is already finalized with different authority")
        if any(binding.stage != DeliveryStage.COMPLETED for binding in frontier.bindings):
            _conflict("Delivery finalization requires every Outcome completed")
        if any(binding.active_claim is not None for binding in frontier.bindings):
            _conflict("Delivery finalization cannot overlap an active Outcome claim")
        if frontier.integration_repair_claim is not None:
            _conflict("Delivery finalization cannot overlap an Integration repair claim")
        if frontier.integration_completion is not None:
            _conflict("completed legacy Integration cannot be finalized as a Change")
        for binding in frontier.bindings:
            if tuple(result.task_id for result in binding.results) != binding.task_ids:
                _conflict("Delivery finalization requires every Task result in authority order")
        if any(observation.change_id != self._contract.change_id for observation in request.observations):
            _conflict("Delivery finalization observations do not match the Change")
        results = tuple(result for binding in frontier.bindings for result in binding.results)
        finalization = DeliveryFinalization(
            operation_id=request.operation_id,
            change_id=self._contract.change_id,
            exact_head=request.exact_head,
            authority_digest=self._authority_digest,
            result_digests=tuple(hashlib.sha256(_model_content(result)).hexdigest() for result in results),
            observations=request.observations,
            review=request.review,
            finalized_at=finalized_at,
        )
        receipt = DeliveryFinalizationReceipt.create(finalization)
        updated = _queue_finalization_checkpoint(
            frontier.model_copy(
                update={
                    "finalization": receipt,
                    "finalization_invalidation": None,
                    "ready": None,
                }
            ),
            request.exact_head,
        )
        self._replace(previous, updated)
        return receipt

    def reconcile_finalization_head(
        self,
        observed_head: str,
        invalidated_at: datetime,
    ) -> DeliveryFinalizationReceipt | DeliveryFinalizationInvalidationReceipt | None:
        """Retain exact finalization or invalidate it after observed Change-head drift."""
        frontier, previous = self._read()
        _require_change_mutable(frontier, "reconcile_finalization_head")
        finalization = frontier.finalization
        if finalization is None:
            invalidation = frontier.finalization_invalidation
            if invalidation is not None and invalidation.observed_head == observed_head:
                return invalidation
            return None
        if finalization.exact_head == observed_head:
            return finalization
        invalidation = DeliveryFinalizationInvalidationReceipt.create(
            DeliveryFinalizationInvalidation(
                change_id=self._contract.change_id,
                finalization_id=finalization.finalization_id,
                expected_head=finalization.exact_head,
                observed_head=observed_head,
                invalidated_at=invalidated_at,
            )
        )
        updated = frontier.model_copy(
            update={
                "finalization": None,
                "finalization_invalidation": invalidation,
                "ready": None,
                "pending_checkpoint": _invalidate_finalization_checkpoint(frontier.pending_checkpoint),
            }
        )
        self._replace(previous, updated)
        return invalidation

    def active_claims(self) -> tuple[tuple[str, DeliveryActiveClaim], ...]:
        """Return active claim identity keyed by outcome in authority order."""
        frontier, _content = self._read()
        return tuple(
            (binding.outcome_id, binding.active_claim)
            for binding in frontier.bindings
            if binding.active_claim is not None
        )

    def integration_repair_claim(self) -> DeliveryActiveClaim | None:
        """Return the current change-level Integration repair claim, if any."""
        return self._read()[0].integration_repair_claim

    def require_integration_repair_claim(self, attempt_id: str, claim_id: str) -> DeliveryActiveClaim:
        """Return the repair claim only when its exact execution identity remains active."""
        claim = self.integration_repair_claim()
        if claim is None or claim.attempt_id != attempt_id or claim.claim_id != claim_id:
            _conflict("execution identity does not match the active Integration repair claim")
        return claim

    def remove_integration_repair_claim(self, attempt_id: str, claim_id: str) -> DeliveryActiveClaim:
        """Remove one exact failed Integration repair claim without clearing attention."""
        frontier, previous = self._read()
        _require_change_mutable(frontier, "remove_integration_repair_claim")
        claim = frontier.integration_repair_claim
        if claim is None or claim.attempt_id != attempt_id or claim.claim_id != claim_id:
            _conflict("claim removal does not match the active Integration repair identity")
        self._replace(previous, frontier.model_copy(update={"integration_repair_claim": None}))
        return claim

    def require_active_claim(
        self,
        outcome_id: str,
        attempt_id: str,
        claim_id: str,
    ) -> OutcomeAuthorityBinding:
        """Return one binding only when its exact execution claim remains active."""
        binding = self.show_binding(outcome_id)
        claim = binding.active_claim
        if claim is None or claim.attempt_id != attempt_id or claim.claim_id != claim_id:
            _conflict("execution identity does not match the active claim")
        return binding

    def remove_active_claim(
        self,
        outcome_id: str,
        attempt_id: str,
        claim_id: str,
    ) -> OutcomeAuthorityBinding:
        """Remove one exact failed claim without changing its canonical stage authority."""
        frontier, previous = self._read()
        _require_change_mutable(frontier, "remove_active_claim")
        binding = _find_binding(frontier, outcome_id)
        claim = binding.active_claim
        if claim is None or claim.attempt_id != attempt_id or claim.claim_id != claim_id:
            _conflict("claim removal does not match the active execution identity")
        recovered = binding.model_copy(
            update={
                "active_claim": None,
                "output": None,
                "candidate": None,
                "result_candidate": None,
                "recovery_attention": None,
            }
        )
        self._replace(previous, _replace_binding(frontier, binding, recovered))
        return recovered

    def publish_recovery_attention(
        self,
        outcome_id: str,
        attention: DeliveryRecoveryAttention,
    ) -> OutcomeAuthorityBinding:
        """Retain one exact active claim with deterministic operator repair evidence."""
        frontier, previous = self._read()
        _require_change_mutable(frontier, "publish_recovery_attention")
        binding = _find_binding(frontier, outcome_id)
        claim = binding.active_claim
        if (
            binding.stage != DeliveryStage.IMPLEMENTATION
            or claim is None
            or claim.attempt_id != attention.attempt_id
            or claim.claim_id != attention.claim_id
        ):
            _conflict("recovery attention does not match an active Build claim")
        if binding.recovery_attention == attention:
            return binding
        updated = binding.model_copy(update={"recovery_attention": attention})
        self._replace(previous, _replace_binding(frontier, binding, updated))
        return updated

    def claimable_outcome_ids(self) -> tuple[str, ...]:
        """Return stable dependency-ready, unblocked, unclaimed outcome identities."""
        frontier, _content = self._read()
        if derive_change_stage(frontier) != DeliveryChangeStage.BUILDING:
            return ()
        completed = {binding.outcome_id for binding in frontier.bindings if binding.stage == DeliveryStage.COMPLETED}
        dependencies = {outcome.outcome_id: set(outcome.dependency_ids) for outcome in self._contract.outcomes}
        return tuple(
            binding.outcome_id
            for binding in frontier.bindings
            if binding.stage not in {DeliveryStage.DESIGN, DeliveryStage.COMPLETED}
            and binding.active_claim_id is None
            and (binding.block is None or binding.block.resolved)
            and dependencies[binding.outcome_id] <= completed
        )

    def claimable_task_ids(self, outcome_id: str) -> tuple[str, ...]:
        """Return promoted tasks whose task dependencies have compact results."""
        if self.change_stage() != DeliveryChangeStage.BUILDING:
            return ()
        binding = self.show_binding(outcome_id)
        if binding.stage != DeliveryStage.IMPLEMENTATION or binding.active_claim_id is not None:
            return ()
        completed = {result.task_id for result in binding.results}
        return tuple(
            task.task_id
            for task in binding.tasks
            if task.task_id not in completed and set(task.dependency_ids) <= completed
        )

    def change_stage(self) -> DeliveryChangeStage:
        """Derive change lifecycle from canonical outcome state."""
        return derive_change_stage(self._read()[0])

    def activate_claim(self, request: ActivateDeliveryClaim) -> OutcomeAuthorityBinding:
        """Bind one fresh claim to a currently claimable outcome."""
        frontier, previous = self._read()
        _require_change_mutable(frontier, "activate_claim")
        binding = _find_binding(frontier, request.outcome_id)
        if frontier.integration_repair_claim is not None:
            _conflict("outcome claims cannot overlap an active Integration repair claim")
        if request.outcome_id not in self.claimable_outcome_ids():
            _conflict("outcome is not claimable")
        if any(item.active_claim_id == request.claim_id for item in frontier.bindings):
            _conflict("active claim identity already exists")
        expected_role = {
            DeliveryStage.PLANNING: DeliveryWorkerRole.PLANNER,
            DeliveryStage.IMPLEMENTATION: DeliveryWorkerRole.BUILDER,
        }.get(binding.stage)
        if request.claim.worker_role != expected_role:
            _conflict("claim worker role does not match the current Delivery stage")
        if binding.stage == DeliveryStage.IMPLEMENTATION:
            if request.task_id not in self.claimable_task_ids(request.outcome_id):
                _conflict("implementation task is not claimable")
        elif request.task_id is not None:
            _conflict("only Implementation claims name a task")
        claimed = binding.model_copy(
            update={
                "active_claim": request.claim,
                "output": None,
                "result_candidate": None,
                "recovery_attention": None,
            }
        )
        self._replace(previous, _replace_binding(frontier, binding, claimed))
        return claimed

    def publish_output(self, request: PublishDeliveryOutput) -> DeliveryOutputReference:
        """Persist one exact active-claim output without changing stage."""
        frontier, previous = self._read()
        _require_change_mutable(frontier, "publish_output")
        binding = _find_binding(frontier, request.outcome_id)
        _require_claim(binding, request.claim_id)
        if (
            request.output.claim_id != request.claim_id
            or request.output.stage != binding.stage
            or request.output.kind.value != binding.stage.value
        ):
            _conflict("output does not match the active claim and stage")
        updated = binding.model_copy(update={"output": request.output})
        self._replace(previous, _replace_binding(frontier, binding, updated))
        return request.output

    def publish_plan(self, request: PublishDeliveryPlan) -> DeliveryPlanCandidate:
        """Validate and persist one idempotent Planning candidate without movement."""
        frontier, previous = self._read()
        _require_change_mutable(frontier, "publish_plan")
        binding = _find_binding(frontier, request.outcome_id)
        _require_claim(binding, request.claim_id)
        if binding.stage != DeliveryStage.PLANNING:
            _conflict("task-chain publication requires Planning stage")
        self._validate_plan(binding, request.tasks)
        digest = hashlib.sha256(b"".join(_model_content(task) for task in request.tasks)).hexdigest()
        candidate = DeliveryPlanCandidate(
            candidate_id=f"plan-{digest}",
            claim_id=request.claim_id,
            digest=digest,
            tasks=request.tasks,
        )
        if binding.candidate == candidate:
            return candidate
        if binding.candidate is not None:
            _conflict("active claim already published another task-chain candidate")
        updated = binding.model_copy(update={"candidate": candidate, "output": candidate.output})
        self._replace(previous, _replace_binding(frontier, binding, updated))
        return candidate

    def publish_result(self, request: PublishDeliveryResult) -> DeliveryResultCandidate:
        """Validate and persist one idempotent compact result without movement."""
        frontier, previous = self._read()
        _require_change_mutable(frontier, "publish_result")
        binding = _find_binding(frontier, request.outcome_id)
        _require_claim(binding, request.claim_id)
        if binding.stage != DeliveryStage.IMPLEMENTATION or binding.active_task_id is None:
            _conflict("result publication requires an active Implementation task")
        task = next((item for item in binding.tasks if item.task_id == binding.active_task_id), None)
        if task is None:
            _reference("active Implementation task authority is absent")
        if (
            request.result.change_id != self._contract.change_id
            or request.result.authority_digest != self._authority_digest
            or request.result.task_id != task.task_id
            or request.result.task_digest != task.digest
        ):
            _conflict("compact result does not match promoted task authority")
        self._require_workspace().validate_writer_head(
            self._contract.change_id,
            request.claim_id,
            request.result.completed_commit,
        )
        digest = hashlib.sha256(_model_content(request.result)).hexdigest()
        candidate = DeliveryResultCandidate(
            candidate_id=f"result-{digest}",
            claim_id=request.claim_id,
            digest=digest,
            result=request.result,
        )
        if binding.result_candidate == candidate:
            return candidate
        if binding.result_candidate is not None:
            _conflict("active claim already published another result candidate")
        updated = binding.model_copy(update={"result_candidate": candidate, "output": candidate.output})
        self._replace(previous, _replace_binding(frontier, binding, updated))
        return candidate

    def transition(self, request: DeliveryTransition) -> OutcomeAuthorityBinding:
        """Apply one worker-owned mechanical transition instruction."""
        frontier, previous = self._read()
        _require_change_mutable(frontier, "transition")
        binding = _find_binding(frontier, request.outcome_id)
        _require_claim(binding, request.claim_id)
        if isinstance(request, AdvanceDelivery):
            updated = self._advance(binding, request)
        elif isinstance(request, RetryDelivery):
            updated = self._retry(binding, request)
        elif isinstance(request, ReturnDelivery):
            updated = self._return(binding, request)
        else:
            updated = self._block(binding, request)
        replacement = _replace_binding(frontier, binding, updated)
        if isinstance(request, AdvanceDelivery) and binding.stage == DeliveryStage.IMPLEMENTATION:
            replacement = _queue_promoted_result_checkpoint(replacement, frontier, binding, updated)
        self._replace(previous, replacement)
        return updated

    def resolve_request(
        self,
        request_id: str,
        resolution: DeliveryRequestResolution,
    ) -> DeliveryRequest:
        """Persist one user answer and clear its same-stage block."""
        frontier, previous = self._read()
        _require_change_mutable(frontier, "resolve_request")
        binding, request = _find_request(frontier, request_id)
        if request.resolution is not None:
            _conflict("request is already resolved")
        if resolution.selected_option_id is not None and resolution.selected_option_id not in {
            option.option_id for option in request.options
        }:
            _reference("selected request option is absent")
        resolved = request.model_copy(update={"resolution": resolution})
        requests = tuple(resolved if item == request else item for item in binding.requests)
        block = binding.block
        if block is None or block.request_id != request_id:
            _conflict("request does not own the current block")
        cleared = block.model_copy(
            update={
                "resolution_note": resolution.response_text or resolution.selected_option_id,
                "resolution_locators": (request_id,),
            }
        )
        updated = binding.model_copy(update={"requests": requests, "block": cleared})
        self._replace(previous, _replace_binding(frontier, binding, updated))
        return resolved

    def unblock(
        self,
        outcome_id: str,
        block_id: str,
        operator_note: str,
        locators: tuple[str, ...],
    ) -> OutcomeAuthorityBinding:
        """Clear a requestless same-stage block with operator evidence."""
        if not operator_note or not locators:
            message = "requestless unblock requires an operator note and locators"
            raise ValueError(message)
        frontier, previous = self._read()
        _require_change_mutable(frontier, "unblock")
        binding = _find_binding(frontier, outcome_id)
        block = binding.block
        if block is None or block.block_id != block_id or block.request_id is not None or block.resolved:
            _conflict("requestless block is not clearable")
        cleared = block.model_copy(update={"resolution_note": operator_note, "resolution_locators": locators})
        updated = binding.model_copy(update={"block": cleared})
        self._replace(previous, _replace_binding(frontier, binding, updated))
        return updated

    def administrative_move(
        self,
        request: AdministrativeDeliveryMove,
    ) -> AdministrativeDeliveryMoveResult:
        """Move backward and invalidate the completed dependent closure."""
        frontier, previous = self._read()
        _require_change_mutable(frontier, "administrative_move")
        if frontier.finalization is not None:
            _conflict("administrative movement cannot cross finalized Change authority")
        if hashlib.sha256(previous).hexdigest() != request.expected_version:
            _conflict("administrative movement preview is stale")
        ordered = _administrative_move_closure(self._contract, frontier, request.outcome_id, request.target)
        invalidated = set(ordered)
        updated_bindings = tuple(
            _reset_binding(item, request.target if item.outcome_id == request.outcome_id else DeliveryStage.PLANNING)
            if item.outcome_id in invalidated
            else item
            for item in frontier.bindings
        )
        move = DeliveryOperatorMove(
            move_id=request.move_id,
            outcome_id=request.outcome_id,
            destination=request.target,
            reason=request.reason,
            invalidated_outcome_ids=ordered,
        )
        if any(item.move_id == move.move_id for item in frontier.operator_moves):
            _conflict("operator move identity already exists")
        updated = frontier.model_copy(
            update={
                "bindings": updated_bindings,
                "operator_moves": (*frontier.operator_moves, move),
                "integration_attention": None,
                "pending_checkpoint": invalidate_checkpoint_publication(
                    frontier.pending_checkpoint,
                    invalidated,
                ),
            }
        )
        self._replace(previous, updated)
        return AdministrativeDeliveryMoveResult(move=move, invalidated_outcome_ids=ordered)

    def preview_administrative_move(
        self,
        outcome_id: str,
        target: DeliveryStage,
    ) -> AdministrativeDeliveryMovePreview:
        """Return the exact invalidation closure without mutating authority."""
        frontier, content = self._read()
        return AdministrativeDeliveryMovePreview(
            outcome_id=outcome_id,
            target=target,
            snapshot_version=hashlib.sha256(content).hexdigest(),
            invalidated_outcome_ids=_administrative_move_closure(self._contract, frontier, outcome_id, target),
        )

    def _advance(
        self,
        binding: OutcomeAuthorityBinding,
        request: AdvanceDelivery,
    ) -> OutcomeAuthorityBinding:
        if binding.output != request.output:
            _conflict("advance output does not match the published claim output")
        if binding.stage == DeliveryStage.PLANNING:
            destination = DeliveryStage.IMPLEMENTATION
            if binding.candidate is None or binding.candidate.output != request.output:
                _conflict("Planning advance requires the published task-chain candidate")
            return binding.model_copy(
                update={
                    "stage": destination,
                    "tasks": binding.candidate.tasks,
                    "active_claim": None,
                    "output": None,
                    "candidate": None,
                    "return_context": None,
                    "recovery_attention": None,
                    "block": None,
                    "requests": (),
                }
            )
        if binding.stage == DeliveryStage.IMPLEMENTATION:
            candidate = binding.result_candidate
            if candidate is None or candidate.output != request.output:
                _conflict("Implementation advance requires the published compact result")
            if any(result.task_id == candidate.result.task_id for result in binding.results):
                _conflict("promoted task already has a compact result")
            self._require_workspace().complete_reviewed(
                self._contract.change_id,
                request.claim_id,
                candidate.result.completed_commit,
            )
            results = (*binding.results, candidate.result)
            completed_tasks = {result.task_id for result in results}
            complete = completed_tasks == {task.task_id for task in binding.tasks}
            destination = DeliveryStage.COMPLETED if complete else DeliveryStage.IMPLEMENTATION
            return binding.model_copy(
                update={
                    "stage": destination,
                    "results": results,
                    "active_claim": None,
                    "output": None,
                    "result_candidate": None,
                    "return_context": None,
                    "recovery_attention": None,
                    "block": None,
                    "requests": (),
                }
            )
        return _conflict("current stage cannot advance")

    def _retry(
        self,
        binding: OutcomeAuthorityBinding,
        request: RetryDelivery,
    ) -> OutcomeAuthorityBinding:
        if binding.stage == DeliveryStage.IMPLEMENTATION:
            if request.abandoned_commit is None or request.attempt_id is None:
                _conflict("Implementation retry requires attempt and abandoned-commit identity")
            manager = self._require_workspace()
            coordination = manager.show(self._contract.change_id)
            if coordination.writer is not None:
                manager.validate_writer_head(
                    self._contract.change_id,
                    request.claim_id,
                    request.abandoned_commit,
                )
                if coordination.writer.attempt_id != request.attempt_id:
                    _conflict("Implementation retry attempt does not own writer custody")
            manager.restart(
                self._contract.change_id,
                request.attempt_id,
                request.abandoned_commit,
            )
        elif request.abandoned_commit is not None or request.attempt_id is not None:
            _conflict("only Implementation retry accepts attempt commit identity")
        return binding.model_copy(
            update={
                "active_claim": None,
                "output": None,
                "candidate": None,
                "result_candidate": None,
                "return_context": None,
                "recovery_attention": None,
            }
        )

    def _require_workspace(self) -> ChangeWorkspaceManager:
        if self._workspace_manager is None:
            _conflict("Implementation result transitions require workspace coordination")
        return self._workspace_manager

    def _validate_plan(
        self,
        binding: OutcomeAuthorityBinding,
        tasks: tuple[DeliveryTaskDefinition, ...],
    ) -> None:
        task_ids = tuple(task.task_id for task in tasks)
        if len(task_ids) != len(set(task_ids)):
            _conflict("Delivery task identities must be unique")
        outcome = next(item for item in self._contract.outcomes if item.outcome_id == binding.outcome_id)
        contract_commitments = set(outcome.commitment_ids)
        for task in tasks:
            if task.outcome_id != binding.outcome_id or task.plan_scope_id != binding.plan_scope_id:
                _reference("Delivery task belongs to another outcome or plan scope")
            if not set(task.commitment_ids) <= contract_commitments:
                _reference("Delivery task references an absent commitment")
            if not set(task.dependency_ids) <= set(task_ids) or task.task_id in task.dependency_ids:
                _reference("Delivery task dependency is absent or self-referential")
        ready = {task.task_id for task in tasks if not task.dependency_ids}
        visited = set(ready)
        while True:
            expanded = visited | {task.task_id for task in tasks if set(task.dependency_ids) <= visited}
            if expanded == visited:
                break
            visited = expanded
        if not ready or visited != set(task_ids):
            _conflict("Delivery task graph must be acyclic with at least one ready task")

    def _return(
        self,
        binding: OutcomeAuthorityBinding,
        request: ReturnDelivery,
    ) -> OutcomeAuthorityBinding:
        if request.target not in _RETURN_TARGETS.get(binding.stage, set()):
            _conflict("return target is not allowed from the current stage")
        if binding.stage == DeliveryStage.IMPLEMENTATION:
            if request.preserved_commit is None or request.attempt_id is None:
                _conflict("Implementation return requires attempt and preserved-commit identity")
            manager = self._require_workspace()
            coordination = manager.show(self._contract.change_id)
            if coordination.writer is not None:
                manager.validate_writer_head(
                    self._contract.change_id,
                    request.claim_id,
                    request.preserved_commit,
                )
                if coordination.writer.attempt_id != request.attempt_id:
                    _conflict("Implementation return attempt does not own writer custody")
            context = DeliveryReturnContext(
                target=request.target,
                reason=request.reason,
                locators=request.locators,
                preserved_commit=request.preserved_commit,
                completed_boundary=coordination.last_reviewed_commit,
            )
            manager.restart(
                self._contract.change_id,
                request.attempt_id,
                request.preserved_commit,
            )
            if request.target == DeliveryStage.DESIGN:
                tasks: tuple[DeliveryTaskDefinition, ...] = ()
                results: tuple[DeliveryTaskResult, ...] = ()
            else:
                completed = {result.task_id for result in binding.results}
                tasks = tuple(task for task in binding.tasks if task.task_id in completed)
                results = binding.results
            return binding.model_copy(
                update={
                    "stage": request.target,
                    "tasks": tasks,
                    "results": results,
                    "active_claim": None,
                    "output": None,
                    "candidate": None,
                    "result_candidate": None,
                    "return_context": context,
                    "recovery_attention": None,
                    "block": None,
                }
            )
        if binding.stage == DeliveryStage.PLANNING and request.source_boundary is None:
            _conflict("Planning return requires its admitted source boundary")
        context = DeliveryReturnContext(
            target=request.target,
            reason=request.reason,
            locators=request.locators,
            source_boundary=request.source_boundary,
        )
        returned = _reset_binding(binding, request.target)
        return returned.model_copy(update={"return_context": context})

    def _block(
        self,
        binding: OutcomeAuthorityBinding,
        request: BlockDelivery,
    ) -> OutcomeAuthorityBinding:
        if request.request is not None and request.request.outcome_id != binding.outcome_id:
            _reference("block request belongs to another outcome")
        if binding.stage == DeliveryStage.IMPLEMENTATION:
            if request.request is None:
                _conflict("Implementation block requires a bounded user request")
            if request.resume_commit is None:
                _conflict("Implementation block requires a clean resume commit")
            self._require_workspace().release_writer_at_head(
                self._contract.change_id,
                request.claim_id,
                request.resume_commit,
            )
        elif request.resume_commit is not None:
            _conflict("only Implementation block accepts a resume commit")
        block = DeliveryBlock(
            block_id=request.block_id,
            reason=request.reason,
            unblock_condition=request.unblock_condition,
            expected_evidence=request.expected_evidence,
            locators=request.locators,
            request_id=request.request.request_id if request.request is not None else None,
            resume_commit=request.resume_commit,
        )
        requests = (*binding.requests, request.request) if request.request is not None else binding.requests
        return binding.model_copy(
            update={
                "active_claim": None,
                "output": None,
                "candidate": None,
                "result_candidate": None,
                "return_context": None,
                "recovery_attention": None,
                "block": block,
                "requests": requests,
            }
        )

    def _read(self) -> tuple[DeliveryFrontier, bytes]:
        RuntimeTransaction.recover_all(self._target_root)
        try:
            content = self._frontier_path.read_bytes()
            frontier, canonical = parse_delivery_frontier(
                content,
                migration_reviewed_head=self._migration_reviewed_head,
                require_checkpoint_backfill=True,
            )
            self._validate_frontier(frontier)
            if canonical != content:
                self._replace_content(content, canonical)
        except (OSError, TypeError, ValueError) as exc:
            message = f"Delivery frontier is missing or invalid: {self._contract.change_id}"
            raise DeliveryRuntimeReferenceError(message) from exc
        else:
            return frontier, canonical

    def _replace(self, previous: bytes, frontier: DeliveryFrontier) -> None:
        self._replace_content(previous, _model_content(frontier))

    def _replace_content(self, previous: bytes, replacement: bytes) -> None:
        """Transactionally replace exact frontier bytes."""
        participant = ReplacementTransactionParticipant(
            self._target_root,
            self._frontier_path.relative_to(self._target_root),
            previous,
            replacement,
        )
        transaction_id = hashlib.sha256(previous + replacement).hexdigest()
        RuntimeTransaction(self._target_root, f"delivery-runtime-{transaction_id}", (participant,)).commit()

    def _validate_frontier(self, frontier: DeliveryFrontier) -> None:
        expected = tuple((scope.outcome_id, scope.scope_id) for scope in self._contract.plan_scopes)
        actual = tuple((binding.outcome_id, binding.plan_scope_id) for binding in frontier.bindings)
        if actual != expected:
            _reference("Delivery frontier does not match its admitted contract")
        resolution = frontier.change_disposition_resolution
        if resolution is not None and resolution.change_id != self._contract.change_id:
            _reference("Delivery Change attention resolution does not match its admitted Change")
        for receipt in (frontier.change_deferral, frontier.change_abandonment):
            if receipt is not None and receipt.change_id != self._contract.change_id:
                _reference("Delivery Change lifecycle receipt does not match its admitted Change")


def _find_binding(frontier: DeliveryFrontier, outcome_id: str) -> OutcomeAuthorityBinding:
    try:
        return next(binding for binding in frontier.bindings if binding.outcome_id == outcome_id)
    except StopIteration as exc:
        _reference(f"Delivery outcome is absent: {outcome_id}", exc)


def _require_change_mutable(frontier: DeliveryFrontier, operation: str) -> None:
    if operation not in _NORMAL_CHANGE_MUTATIONS:
        message = f"unregistered Delivery Change mutation: {operation}"
        raise ValueError(message)
    if frontier.integration_result_id is not None:
        _conflict("completed Integration cannot be mutated")
    if frontier.change_completion is not None:
        _conflict("completed Delivery Change is terminal")
    if frontier.change_abandonment is not None:
        _conflict("abandoned Delivery Change is terminal")
    if frontier.change_deferral is not None and operation not in {"resume_change", "abandon_change"}:
        _conflict("deferred Delivery Change requires resumption before mutation")
    if frontier.change_disposition is not None and operation not in {
        "defer_change",
        "resume_change",
        "abandon_change",
    }:
        _conflict("Delivery Change requires attention resolution before mutation")


def _require_no_active_change_claim(frontier: DeliveryFrontier, operation: str) -> None:
    has_outcome_claim = any(binding.active_claim is not None for binding in frontier.bindings)
    if has_outcome_claim or frontier.integration_repair_claim is not None:
        _conflict(f"{operation} cannot overlap an active mutation claim")


def is_acceptance_waiting_observation(
    observation: PublicationPullRequestObservationReceipt,
) -> bool:
    """Return whether a bound pull request is normally waiting for a user merge."""
    snapshot = observation.snapshot
    return snapshot.state == "open" and not snapshot.merged


def parse_delivery_frontier(
    content: bytes,
    *,
    migration_reviewed_head: str | None = None,
    require_checkpoint_backfill: bool = False,
) -> tuple[DeliveryFrontier, bytes]:
    """Parse canonical frontier bytes and reduce safe pre-Assembly-removal state."""
    payload = json.loads(content)
    if not isinstance(payload, dict):
        raise TypeError
    schema_version = _normalize_frontier_schema(payload)
    _reject_legacy_finalization(payload)
    frontier = DeliveryFrontier.model_validate_json(
        json.dumps(payload, sort_keys=True, separators=(",", ":")),
    )
    if schema_version in _CHECKPOINT_BACKFILL_SCHEMA_VERSIONS:
        frontier = _backfill_checkpoint_state(
            frontier,
            migration_reviewed_head,
            required=require_checkpoint_backfill,
        )
    return frontier, _model_content(frontier)


def _normalize_frontier_schema(payload: dict[str, object]) -> int:
    schema_version = payload.get("schema_version")
    if schema_version == 1:
        _normalize_schema_one_bindings(payload)
    elif schema_version in _PREVIOUS_FRONTIER_SCHEMA_VERSIONS:
        payload["schema_version"] = _FRONTIER_SCHEMA_VERSION
    elif schema_version != _FRONTIER_SCHEMA_VERSION:
        raise ValueError
    return schema_version


def _normalize_schema_one_bindings(payload: dict[str, object]) -> None:
    bindings = payload.get("bindings")
    if not isinstance(bindings, list):
        raise TypeError
    for binding in bindings:
        if not isinstance(binding, dict) or binding.get("stage") == "assembly":
            raise ValueError
        assembly_required = binding.pop("assembly_required", False)
        if assembly_required is not False:
            raise ValueError
    payload["schema_version"] = _FRONTIER_SCHEMA_VERSION


def _reject_legacy_finalization(payload: dict[str, object]) -> None:
    finalization = payload.get("finalization")
    if isinstance(finalization, dict) and finalization.get("schema_version") != _FINALIZATION_SCHEMA_VERSION:
        raise ValueError(_LEGACY_FINALIZATION_MESSAGE)


def _backfill_checkpoint_state(
    frontier: DeliveryFrontier,
    reviewed_head: str | None,
    *,
    required: bool,
) -> DeliveryFrontier:
    if frontier.integration_completion is not None:
        return frontier
    result_bindings = tuple(binding for binding in frontier.bindings if binding.results)
    if not result_bindings:
        return frontier
    if reviewed_head is None:
        if required:
            raise ValueError
        return frontier
    triggers = [
        DeliveryCheckpointTrigger(
            kind=DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK,
        )
    ]
    triggers.extend(
        DeliveryCheckpointTrigger(
            kind=DeliveryCheckpointTriggerKind.VERIFIED_OUTCOME,
            outcome_id=binding.outcome_id,
        )
        for binding in frontier.bindings
        if binding.stage == DeliveryStage.COMPLETED
    )
    return frontier.model_copy(
        update={
            "pending_checkpoint": DeliveryPendingCheckpoint(
                head=reviewed_head,
                triggers=tuple(triggers),
            )
        }
    )


def _find_request(frontier: DeliveryFrontier, request_id: str) -> tuple[OutcomeAuthorityBinding, DeliveryRequest]:
    matches = [
        (binding, request)
        for binding in frontier.bindings
        for request in binding.requests
        if request.request_id == request_id
    ]
    if len(matches) != 1:
        _reference(f"Delivery request is absent or ambiguous: {request_id}")
    return matches[0]


def _replace_binding(
    frontier: DeliveryFrontier,
    previous: OutcomeAuthorityBinding,
    replacement: OutcomeAuthorityBinding,
) -> DeliveryFrontier:
    return frontier.model_copy(
        update={"bindings": tuple(replacement if item == previous else item for item in frontier.bindings)}
    )


def _queue_promoted_result_checkpoint(
    replacement: DeliveryFrontier,
    previous: DeliveryFrontier,
    binding: OutcomeAuthorityBinding,
    updated: OutcomeAuthorityBinding,
) -> DeliveryFrontier:
    candidate = binding.result_candidate
    if candidate is None:
        _conflict("promoted Task checkpoint requires the published result candidate")
    triggers: list[DeliveryCheckpointTrigger] = []
    pending = previous.pending_checkpoint
    if previous.published_head is None and not _has_checkpoint_trigger(
        pending,
        DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK,
    ):
        triggers.append(
            DeliveryCheckpointTrigger(
                kind=DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK,
            )
        )
    if updated.stage == DeliveryStage.COMPLETED:
        triggers.append(
            DeliveryCheckpointTrigger(
                kind=DeliveryCheckpointTriggerKind.VERIFIED_OUTCOME,
                outcome_id=binding.outcome_id,
            )
        )
    if pending is None and not triggers:
        return replacement
    combined = (*(() if pending is None else pending.triggers), *triggers)
    return replacement.model_copy(
        update={
            "pending_checkpoint": DeliveryPendingCheckpoint(
                head=candidate.result.completed_commit,
                triggers=tuple(dict.fromkeys(combined)),
            )
        }
    )


def _queue_finalization_checkpoint(frontier: DeliveryFrontier, exact_head: str) -> DeliveryFrontier:
    pending = frontier.pending_checkpoint
    trigger = DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.FINALIZATION)
    combined = (*(() if pending is None else pending.triggers), trigger)
    return frontier.model_copy(
        update={
            "pending_checkpoint": DeliveryPendingCheckpoint(
                head=exact_head,
                triggers=tuple(dict.fromkeys(combined)),
            )
        }
    )


def _invalidate_finalization_checkpoint(
    pending: DeliveryPendingCheckpoint | None,
) -> DeliveryPendingCheckpoint | None:
    if pending is None:
        return None
    retained = tuple(
        trigger for trigger in pending.triggers if trigger.kind != DeliveryCheckpointTriggerKind.FINALIZATION
    )
    if not retained:
        return None
    return pending.model_copy(update={"head": None, "triggers": retained})


def _has_checkpoint_trigger(
    pending: DeliveryPendingCheckpoint | None,
    kind: DeliveryCheckpointTriggerKind,
) -> bool:
    return pending is not None and any(trigger.kind == kind for trigger in pending.triggers)


def invalidate_checkpoint_publication(
    pending: DeliveryPendingCheckpoint | None,
    invalidated_outcome_ids: set[str],
) -> DeliveryPendingCheckpoint | None:
    """Retain valid obligations while removing their invalidated publication head."""
    if pending is None:
        return None
    if not invalidated_outcome_ids:
        return pending
    retained = tuple(
        trigger
        for trigger in pending.triggers
        if trigger.outcome_id is None or trigger.outcome_id not in invalidated_outcome_ids
    )
    if not retained:
        return None
    return pending.model_copy(update={"head": None, "triggers": retained})


def _require_claim(binding: OutcomeAuthorityBinding, claim_id: str) -> None:
    if binding.active_claim_id != claim_id:
        _conflict("transition does not match the active claim")


def _reset_binding(binding: OutcomeAuthorityBinding, stage: DeliveryStage) -> OutcomeAuthorityBinding:
    return binding.model_copy(
        update={
            "stage": stage,
            "tasks": (),
            "results": (),
            "active_claim": None,
            "output": None,
            "candidate": None,
            "result_candidate": None,
            "return_context": None,
            "recovery_attention": None,
            "block": None,
            "requests": (),
        }
    )


def _completed_dependent_closure(
    contract: DeliveryContract,
    frontier: DeliveryFrontier,
    outcome_id: str,
) -> set[str]:
    bindings = {binding.outcome_id: binding for binding in frontier.bindings}
    invalidated = {outcome_id}
    while True:
        expanded = invalidated | {
            outcome.outcome_id
            for outcome in contract.outcomes
            if bindings[outcome.outcome_id].stage == DeliveryStage.COMPLETED
            if set(outcome.dependency_ids) & invalidated
        }
        if expanded == invalidated:
            return invalidated
        invalidated = expanded


def _administrative_move_closure(
    contract: DeliveryContract,
    frontier: DeliveryFrontier,
    outcome_id: str,
    target: DeliveryStage,
) -> tuple[str, ...]:
    if frontier.integration_repair_claim is not None:
        _conflict("administrative movement cannot overlap an active Integration repair claim")
    if frontier.integration_completion is not None:
        _conflict("completed Integration cannot move backward")
    binding = _find_binding(frontier, outcome_id)
    if _STAGE_ORDER[target] >= _STAGE_ORDER[binding.stage]:
        _conflict("administrative movement must target an earlier stage")
    invalidated = _completed_dependent_closure(contract, frontier, outcome_id)
    return tuple(item.outcome_id for item in frontier.bindings if item.outcome_id in invalidated)


def _model_content(model: BaseModel) -> bytes:
    payload = model.model_dump(mode="json")
    return (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _receipt_digest(receipt: BaseModel, identity_field: str) -> str:
    payload = receipt.model_dump(mode="json", exclude={identity_field})
    content = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(content).hexdigest()


def _pull_request_identity(ready: PullRequestReadyReceipt | None) -> DeliveryChangePublicationIdentity | None:
    if ready is None:
        return None
    return DeliveryChangePublicationIdentity(
        change_id=ready.change_id,
        repository=ready.repository,
        number=ready.number,
        node_id=ready.node_id,
        head_sha=ready.head_sha,
    )


def _attention_conflict(message: str) -> None:
    raise DeliveryChangeDispositionConflictError(message)


def _conflict(message: str) -> None:
    raise DeliveryRuntimeConflictError(message)


def _reference(message: str, cause: Exception | None = None) -> None:
    if cause is None:
        raise DeliveryRuntimeReferenceError(message)
    raise DeliveryRuntimeReferenceError(message) from cause


__all__ = [
    "DELIVERY_TRANSITION_ADAPTER",
    "ActivateDeliveryClaim",
    "AdministrativeDeliveryMove",
    "AdministrativeDeliveryMoveResult",
    "AdvanceDelivery",
    "BlockDelivery",
    "DeliveryAcceptanceWaitingError",
    "DeliveryBlock",
    "DeliveryChangeAbandonment",
    "DeliveryChangeCompletion",
    "DeliveryChangeDeferral",
    "DeliveryChangeDisposition",
    "DeliveryChangeDispositionConflictError",
    "DeliveryChangeDispositionKind",
    "DeliveryChangeDispositionResolution",
    "DeliveryChangePublicationIdentity",
    "DeliveryChangeStage",
    "DeliveryCheckpointPublicationState",
    "DeliveryCheckpointTrigger",
    "DeliveryCheckpointTriggerKind",
    "DeliveryFinalization",
    "DeliveryFinalizationInvalidation",
    "DeliveryFinalizationInvalidationReceipt",
    "DeliveryFinalizationReceipt",
    "DeliveryFrontier",
    "DeliveryIntegrationAttention",
    "DeliveryIntegrationAttentionCode",
    "DeliveryIntegrationCompletion",
    "DeliveryMergedPullRequestLatch",
    "DeliveryObservation",
    "DeliveryObservationReceipt",
    "DeliveryOperatorMove",
    "DeliveryOutputKind",
    "DeliveryOutputReference",
    "DeliveryPendingCheckpoint",
    "DeliveryRequest",
    "DeliveryRequestKind",
    "DeliveryRequestOption",
    "DeliveryRequestResolution",
    "DeliveryResultCandidate",
    "DeliveryReturnContext",
    "DeliveryReview",
    "DeliveryReviewReceipt",
    "DeliveryRuntime",
    "DeliveryRuntimeConflictError",
    "DeliveryRuntimeReferenceError",
    "DeliveryStage",
    "DeliveryTaskDefinition",
    "DeliveryTaskResult",
    "FinalizeDeliveryChange",
    "OutcomeAuthorityBinding",
    "PublishDeliveryOutput",
    "PublishDeliveryPlan",
    "PublishDeliveryResult",
    "RetryDelivery",
    "ReturnDelivery",
    "derive_change_stage",
    "invalidate_checkpoint_publication",
    "is_acceptance_waiting_observation",
    "is_change_terminal",
]
