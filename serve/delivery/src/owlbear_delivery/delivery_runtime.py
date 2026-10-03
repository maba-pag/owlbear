"""Mechanical Delivery state and worker-owned transitions."""

from __future__ import annotations

import hashlib
import inspect
import json
import re
import stat
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from itertools import pairwise
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, Annotated, Literal, TypedDict, Unpack, cast

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator

from owlbear_delivery.acceptance import (
    CompletionDisplayMetadata,
    CompletionReceipt,
    CompletionReceiptBundle,
    CompletionReceiptConflictError,
    CompletionReceiptStore,
)
from owlbear_delivery.change_workspace import (
    ChangeDesignPackageSnapshotReceipt,
    ChangeExternalHeadAdoptionReceipt,
    ChangeExternalHeadPromotionReceipt,
    ChangeFinalizationAttention,
    ChangeTargetSyncReceipt,
    ChangeWriter,
    PublicationLock,
)
from owlbear_delivery.draft_pull_request import (
    PublicationPullRequestObservationReceipt,
    PullRequestReadyReceipt,
)
from owlbear_delivery.recovery import (
    DeliveryWorkerExclusionRequiredError,
    RecoveryIntent,
    RecoveryReceipt,
    RetryEpisodeSummary,
    RetryFailureClass,
    RetryLedger,
    digest,
    encoded,
    journal_path,
    read_record,
)
from owlbear_delivery.runtime_transaction import (
    ReplacementTransactionParticipant,
    RuntimeTransaction,
    TransactionParticipant,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from pathlib import Path

    from owlbear_delivery.change_workspace import (
        ChangeWorkspaceManager,
        PreparedBuilderHandoff,
    )
    from owlbear_delivery.target_contract import DeliveryContract


_MAX_WORKER_RETRIES = 3
_MAX_COMPLETED_REPAIR_RECEIPTS = 256
_MAX_BUILDER_HANDOFF_CHANGE_INTENTS = 32
_MAX_BUILDER_HANDOFF_CHANGE_INTENT_RECEIPTS = _MAX_BUILDER_HANDOFF_CHANGE_INTENTS + 1
_BUILDER_HANDOFF_CHANGE_INTENT_FRONTIER_FIELDS = frozenset(
    {"change_deferral", "change_abandonment", "pending_checkpoint"}
)
_SHA256_HEX_LENGTH = 64


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


class DeliveryAcceptanceAttentionReason(StrEnum):
    """Typed provider condition that caused acceptance attention."""

    HEAD_MOVED = "head-moved"
    CLOSED_UNMERGED = "closed-unmerged"
    IDENTITY_MISMATCH = "identity-mismatch"
    MERGE_EVIDENCE_MISSING = "merge-evidence-missing"
    LATCH_REGRESSION = "latch-regression"


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

    ADMITTED_DESIGN = "admitted-design"
    FIRST_PROMOTED_TASK = "first-promoted-task"
    VERIFIED_TASK = "verified-task"
    VERIFIED_OUTCOME = "verified-outcome"
    FINALIZATION = "finalization"
    EXPLICIT = "explicit"


class _DeliveryModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


def _omit_when_none(value: object) -> bool:
    # Optional fields added after frontier schema 18 keep pre-existing bytes and snapshot identities.
    return value is None


class DeliveryChangePublicationIdentity(_DeliveryModel):
    """Provider pull-request identity retained while Change attention clears ready authority."""

    schema_version: Literal[1] = 1
    change_id: str = Field(min_length=1, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    repository: str = Field(min_length=3, pattern=r"^[^\s/]+/[^\s/]+$")
    number: int = Field(gt=0)
    node_id: str = Field(min_length=1)
    head_sha: str = Field(pattern=r"^[0-9a-f]{40}$")


class DeliveryChangePublicationHistory(_DeliveryModel):
    """Ordered provider pull-request identities retained across supersession."""

    schema_version: Literal[1] = 1
    change_id: str = Field(min_length=1)
    publications: tuple[DeliveryChangePublicationIdentity, ...] = Field(min_length=1)

    @property
    def current(self) -> DeliveryChangePublicationIdentity:
        """Return the current successor publication identity."""
        return self.publications[-1]

    @classmethod
    def create(
        cls,
        publication: DeliveryChangePublicationIdentity,
    ) -> DeliveryChangePublicationHistory:
        """Create history from the first exact publication identity."""
        return cls(change_id=publication.change_id, publications=(publication,))

    def _replace_publications(
        self,
        publications: tuple[DeliveryChangePublicationIdentity, ...],
    ) -> DeliveryChangePublicationHistory:
        payload = self.model_dump(mode="python")
        payload["publications"] = publications
        return DeliveryChangePublicationHistory.model_validate(payload)

    def append(
        self,
        predecessor: DeliveryChangePublicationIdentity,
        successor: DeliveryChangePublicationIdentity,
    ) -> DeliveryChangePublicationHistory:
        """Append one exact successor after the current publication."""
        if self.current != predecessor:
            message = "publication successor does not match the current predecessor"
            raise ValueError(message)
        return self._replace_publications((*self.publications, successor))

    def refresh_current(
        self,
        publication: DeliveryChangePublicationIdentity,
    ) -> DeliveryChangePublicationHistory:
        """Refresh the exact head of the current provider PR without adding a generation."""
        current = self.current
        if (current.repository, current.number, current.node_id) != (
            publication.repository,
            publication.number,
            publication.node_id,
        ):
            message = "publication head refresh does not match the current publication"
            raise ValueError(message)
        return self._replace_publications((*self.publications[:-1], publication))

    @model_validator(mode="after")
    def _validate_history(self) -> DeliveryChangePublicationHistory:
        identities = tuple(
            (publication.repository, publication.number, publication.node_id) for publication in self.publications
        )
        if len(identities) != len(set(identities)):
            message = "Delivery publication history identities must be unique"
            raise ValueError(message)
        if any(publication.change_id != self.change_id for publication in self.publications):
            message = "Delivery publication history must bind one Change"
            raise ValueError(message)
        return self


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


class DeliveryPendingStatePublication(_DeliveryModel):
    """Local durable intent for replaying a state snapshot publication."""

    schema_version: Literal[1] = 1
    status: Literal["pending", "acknowledged"]
    base_frontier_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    frontier_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    transition_request_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def pending(
        cls,
        base_frontier_digest: str,
        frontier_digest: str,
        transition_request_digest: str | None = None,
    ) -> DeliveryPendingStatePublication:
        """Create one pending local publication intent."""
        return cls(
            status="pending",
            base_frontier_digest=base_frontier_digest,
            frontier_digest=frontier_digest,
            transition_request_digest=transition_request_digest,
        )

    def acknowledge(self) -> DeliveryPendingStatePublication:
        """Return the same intent marked as remotely acknowledged."""
        return self.model_copy(update={"status": "acknowledged"})


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
    reason: Literal["head-drift", "target-sync-conflict", "review-repair"] = "head-drift"
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
        return cls(invalidation_id=_finalization_invalidation_digest(candidate), **values)

    @model_validator(mode="after")
    def _validate_receipt(self) -> DeliveryFinalizationInvalidationReceipt:
        if self.expected_head == self.observed_head and self.reason != "review-repair":
            message = "Delivery finalization invalidation requires head drift"
            raise ValueError(message)
        if self.invalidated_at.tzinfo is None:
            message = "Delivery finalization invalidation timestamp must include a timezone"
            raise ValueError(message)
        if self.invalidation_id != _finalization_invalidation_digest(self):
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
    acceptance_reason: DeliveryAcceptanceAttentionReason | None = None

    @classmethod
    def create(  # noqa: PLR0913 - acceptance reason binds one additional typed authority field.
        cls,
        *,
        kind: DeliveryChangeDispositionKind,
        change_id: str,
        entered_from: DeliveryChangeStage,
        recorded_at: datetime,
        diagnostics: tuple[str, ...],
        acceptance_reason: DeliveryAcceptanceAttentionReason | None = None,
    ) -> DeliveryChangeDisposition:
        """Create one deterministic attention record from typed evidence."""
        values = {
            "kind": kind,
            "change_id": change_id,
            "entered_from": entered_from,
            "recorded_at": recorded_at,
            "diagnostics": diagnostics,
            "acceptance_reason": acceptance_reason,
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
        if self.kind != DeliveryChangeDispositionKind.ACCEPTANCE_ATTENTION and self.acceptance_reason is not None:
            message = "acceptance attention reason requires acceptance attention"
            raise ValueError(message)
        if self.recorded_at.tzinfo is None:
            message = "Change disposition timestamp must include a timezone"
            raise ValueError(message)
        expected_id = _receipt_digest(self, "disposition_id")
        if self.disposition_id != expected_id:
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
    attempt_count: int = Field(default=0, ge=0)
    last_attempted_at: datetime | None = None
    last_error_code: str | None = Field(default=None, min_length=1, max_length=120)
    last_error_detail: str | None = Field(default=None, min_length=1, max_length=240)

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
        if self.last_attempted_at is not None and self.last_attempted_at.tzinfo is None:
            message = "pending checkpoint attempt timestamp must include a timezone"
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
    provenance: Literal["user-confirmed"] | None = None

    @model_validator(mode="after")
    def _require_answer(self) -> DeliveryRequestResolution:
        if self.selected_option_id is None and (self.response_text is None or not self.response_text.strip()):
            message = "request resolution requires a selected option or response text"
            raise ValueError(message)
        if self.response_text is not None and self.response_text.strip() and self.provenance != "user-confirmed":
            message = "free-text request resolution requires user-confirmed provenance"
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


class RetryDelivery(_DeliveryModel):
    """End a claim and leave its outcome in the same stage."""

    action: Literal["retry"]
    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    claim_id: str = Field(min_length=1)
    abandoned_commit: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    attempt_id: str | None = None
    failure_code: str = Field(default="worker-retry", pattern=r"^[a-z0-9][a-z0-9._-]{0,63}$")


class DeliveryRetryDiagnostic(_DeliveryModel):
    """Exact refused retry request bound to the active worker attempt."""

    code: Literal["ERR_DELIVERY_WORKER_EXCLUSION_REQUIRED"] = "ERR_DELIVERY_WORKER_EXCLUSION_REQUIRED"
    attempt_id: str = Field(min_length=1)
    transition: RetryDelivery


class DeliveryBuilderHandoffContext(_DeliveryModel):
    """Exact Builder settlement authority retained for an owning handoff route."""

    settlement_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    original_task_id: str = Field(min_length=1, max_length=256)
    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    attempt_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    last_reviewed_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    branch_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    metadata_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    route: Literal["same-task", "same-outcome-planner", "same-outcome-design"]
    original_task_commitment_ids: tuple[str, ...] = ()
    original_task_maintained_surfaces: tuple[str, ...] = ()


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
    diagnostic_transition: Annotated[BlockDelivery | ReturnDelivery, Field(discriminator="action")] | None = Field(
        default=None, exclude_if=_omit_when_none
    )


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
    continuation: bool = False


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
    builder_handoff_context: DeliveryBuilderHandoffContext | None = Field(default=None, exclude_if=_omit_when_none)
    recovery_attention: DeliveryRecoveryAttention | None = None
    retry_diagnostic: DeliveryRetryDiagnostic | None = Field(default=None, exclude_if=_omit_when_none)
    block: DeliveryBlock | None = None
    requests: tuple[DeliveryRequest, ...] = ()
    retry_fingerprint: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    retry_count: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def _validate_state(self) -> OutcomeAuthorityBinding:
        if self.stage == DeliveryStage.COMPLETED and self.active_claim is not None:
            message = "completed outcomes cannot carry an active claim"
            raise ValueError(message)
        self._validate_active_claim()
        self._validate_recovery_attention()
        self._validate_retry_diagnostic()
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
        self._validate_builder_handoff()
        return self

    def _validate_builder_handoff(self) -> None:
        handoff = self.builder_handoff_context
        if handoff is None:
            return
        if handoff.outcome_id != self.outcome_id or handoff.original_task_id not in self.task_ids:
            message = "Builder handoff context must bind retained task authority for its outcome"
            raise ValueError(message)
        expected_stage = (
            DeliveryStage.PLANNING
            if handoff.route == "same-outcome-planner"
            else DeliveryStage.DESIGN
            if handoff.route == "same-outcome-design"
            else DeliveryStage.IMPLEMENTATION
        )
        if self.stage != expected_stage:
            message = (
                "Planning Builder handoff context requires Planning stage"
                if handoff.route == "same-outcome-planner"
                else "Design Builder handoff context requires Design stage"
                if handoff.route == "same-outcome-design"
                else "same-task Builder handoff context requires Implementation stage"
            )
            raise ValueError(message)
        original_task = next(task for task in self.tasks if task.task_id == handoff.original_task_id)
        if (
            handoff.route in {"same-outcome-planner", "same-outcome-design"}
            or handoff.original_task_maintained_surfaces
        ) and (
            original_task.commitment_ids != handoff.original_task_commitment_ids
            or original_task.maintained_surfaces != handoff.original_task_maintained_surfaces
        ):
            message = "Builder handoff context must retain its original task lineage"
            raise ValueError(message)
        if (
            self.active_claim is not None
            and handoff.route == "same-task"
            and self.active_claim.task_id != handoff.original_task_id
        ):
            message = "active claim cannot consume a different Builder handoff task"
            raise ValueError(message)

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
        diagnostic = self.recovery_attention.diagnostic_transition
        if diagnostic is not None and (
            self.stage != DeliveryStage.IMPLEMENTATION
            or diagnostic.outcome_id != self.outcome_id
            or diagnostic.claim_id != self.active_claim.claim_id
            or (isinstance(diagnostic, ReturnDelivery) and diagnostic.attempt_id != self.active_claim.attempt_id)
            or (
                isinstance(diagnostic, BlockDelivery)
                and (diagnostic.request is None or diagnostic.request.outcome_id != self.outcome_id)
            )
        ):
            message = "diagnostic transition must bind the current active Builder claim and outcome"
            raise ValueError(message)

    def _validate_retry_diagnostic(self) -> None:
        diagnostic = self.retry_diagnostic
        if diagnostic is None:
            return
        claim = self.active_claim
        request = diagnostic.transition
        if (
            claim is None
            or diagnostic.attempt_id != claim.attempt_id
            or request.outcome_id != self.outcome_id
            or request.claim_id != claim.claim_id
        ):
            message = "retry diagnostic must bind the current active claim and outcome"
            raise ValueError(message)
        if self.stage == DeliveryStage.PLANNING:
            if request.attempt_id is not None or request.abandoned_commit is not None:
                message = "Planning retry diagnostic cannot contain Implementation identity"
                raise ValueError(message)
        elif request.attempt_id != claim.attempt_id or request.abandoned_commit is None:
            message = "Implementation retry diagnostic must bind its attempt and abandoned commit"
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

    schema_version: Literal[18] = 18
    bindings: tuple[OutcomeAuthorityBinding, ...]
    published_head: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    pending_checkpoint: DeliveryPendingCheckpoint | None = None
    operator_moves: tuple[DeliveryOperatorMove, ...] = ()
    finalization: DeliveryFinalizationReceipt | None = None
    finalization_invalidation: DeliveryFinalizationInvalidationReceipt | None = None
    ready: PullRequestReadyReceipt | None = None
    change_disposition_publication: DeliveryChangePublicationIdentity | None = None
    change_publication_history: DeliveryChangePublicationHistory | None = None
    target_sync_receipt: ChangeTargetSyncReceipt | None = None
    external_head_adoption_receipt: ChangeExternalHeadAdoptionReceipt | None = None
    external_head_promotion_receipt: ChangeExternalHeadPromotionReceipt | None = None
    merged_pull_request_latch: DeliveryMergedPullRequestLatch | None = None
    change_completion: DeliveryChangeCompletion | None = None
    change_deferral: DeliveryChangeDeferral | None = None
    change_abandonment: DeliveryChangeAbandonment | None = None
    change_disposition: DeliveryChangeDisposition | None = None
    change_disposition_resolution: DeliveryChangeDispositionResolution | None = None
    integration_attention: DeliveryIntegrationAttention | None = None
    integration_repair_claim: DeliveryActiveClaim | None = None

    @model_validator(mode="after")
    def _discard_stale_target_sync_receipt(self) -> DeliveryFrontier:
        disposition = self.change_disposition
        if disposition is None or not any(
            item.startswith("target-sync-operation:") for item in disposition.diagnostics
        ):
            return self
        if self.target_sync_receipt is None:
            return self
        return self.model_copy(update={"target_sync_receipt": None})

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
        ):
            message = "Delivery finalization requires completed unclaimed outcome authority"
            raise ValueError(message)
        promotion = self.external_head_promotion_receipt
        adoption = self.external_head_adoption_receipt
        if promotion is not None and (
            adoption is None
            or promotion.adoption_receipt_id != adoption.receipt_id
            or promotion.promoted_head != adoption.adopted_head
        ):
            message = "external Change head promotion must bind the current adoption receipt"
            raise ValueError(message)
        return self

    def _validate_lifecycle_dispositions(self) -> None:
        if self.change_deferral is not None and self.change_abandonment is not None:
            message = "Change deferral and abandonment cannot coexist"
            raise ValueError(message)
        if self.change_deferral is not None and self.change_completion is not None:
            message = "deferred Change cannot retain terminal completion authority"
            raise ValueError(message)
        if self.change_abandonment is not None and (
            self.change_completion is not None
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
        if self.change_completion is not None:
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
    expected_frontier_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @property
    def claim_id(self) -> str:
        """Return the nested claim identity used by transition requests."""
        return self.claim.claim_id

    @property
    def task_id(self) -> str | None:
        """Return the nested task identity used by Build selection."""
        return self.claim.task_id


class PrepareCompletedOutcomeRepair(_DeliveryModel):
    """Engine-owned request to append one bounded repair task to a completed outcome."""

    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    owning_task_id: str = Field(min_length=1)
    episode_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._-]+$")
    attempt_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._-]+$")
    defect_code: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._-]+$")
    finding_boundary: Literal["implementation", "proof-procedure"]
    original_action_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._-]+$")
    preservation_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_frontier_digest: str = Field(pattern=r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class _CompletedOutcomeRepairLineage:
    previous_task_ids: tuple[str, ...]
    previous_result_ids: tuple[str, ...]


class _CompletedOutcomeRepairCreateFields(TypedDict, total=False):
    change_id: str
    request: PrepareCompletedOutcomeRepair
    repair_task_id: str
    previous_task_ids: tuple[str, ...]
    previous_result_ids: tuple[str, ...]
    finished_at: str


_COMPLETED_OUTCOME_REPAIR_CREATE_SIGNATURE = inspect.Signature(
    tuple(
        inspect.Parameter(name, inspect.Parameter.POSITIONAL_OR_KEYWORD)
        for name in _CompletedOutcomeRepairCreateFields.__annotations__
    )
)


class CompletedOutcomeRepairReceipt(_DeliveryModel):
    """Immutable evidence joining a proof repair, its lineage, and custody release."""

    schema_version: Literal[1] = 1
    receipt_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    change_id: str = Field(min_length=1, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    owning_task_id: str = Field(min_length=1)
    repair_task_id: str = Field(min_length=1)
    episode_id: str = Field(min_length=1, max_length=128)
    attempt_id: str = Field(min_length=1, max_length=128)
    defect_code: str = Field(min_length=1, max_length=128)
    finding_boundary: Literal["implementation", "proof-procedure"]
    original_action_id: str = Field(min_length=1, max_length=128)
    preservation_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_frontier_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    previous_task_ids: tuple[str, ...]
    previous_result_ids: tuple[str, ...]
    custody: Literal["failed-finalizer-released"] = "failed-finalizer-released"
    finished_at: str = Field(min_length=1, max_length=64)

    @classmethod
    def create(
        cls,
        *args: object,
        **kwargs: Unpack[_CompletedOutcomeRepairCreateFields],
    ) -> CompletedOutcomeRepairReceipt:
        """Create a receipt while preserving legacy calls; reflection sees the variadic implementation."""
        fields = cast(
            "_CompletedOutcomeRepairCreateFields",
            _COMPLETED_OUTCOME_REPAIR_CREATE_SIGNATURE.bind(*args, **kwargs).arguments,
        )
        values = {
            "change_id": fields["change_id"],
            "outcome_id": fields["request"].outcome_id,
            "owning_task_id": fields["request"].owning_task_id,
            "repair_task_id": fields["repair_task_id"],
            "episode_id": fields["request"].episode_id,
            "attempt_id": fields["request"].attempt_id,
            "defect_code": fields["request"].defect_code,
            "finding_boundary": fields["request"].finding_boundary,
            "original_action_id": fields["request"].original_action_id,
            "preservation_id": fields["request"].preservation_id,
            "expected_frontier_digest": fields["request"].expected_frontier_digest,
            "previous_task_ids": fields["previous_task_ids"],
            "previous_result_ids": fields["previous_result_ids"],
            "finished_at": fields["finished_at"],
        }
        candidate = cls.model_construct(receipt_id="0" * 64, **values)
        payload = candidate.model_dump(mode="json", exclude={"receipt_id"})
        receipt_id = hashlib.sha256(
            (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
        ).hexdigest()
        return cls(receipt_id=receipt_id, **values)

    @model_validator(mode="after")
    def _validate_identity(self) -> CompletedOutcomeRepairReceipt:
        payload = self.model_dump(mode="json", exclude={"receipt_id"})
        expected = hashlib.sha256(
            (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
        ).hexdigest()
        if self.receipt_id != expected:
            _reference("completed-outcome repair receipt identity is invalid")
        return self


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

    action: Literal["advance"]
    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    claim_id: str = Field(min_length=1)
    output: DeliveryOutputReference


class ReturnDelivery(_DeliveryModel):
    """Return one claim to an allowed earlier stage with successor context."""

    action: Literal["return"]
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

    action: Literal["block"]
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

# Engine-observed endings of invocations that can no longer progress; never accepted from callers.
ENGINE_WORKER_SETTLEMENT_FAILURE_CODES: Mapping[str, str] = MappingProxyType(
    {"host-lost": "worker-host-lost", "released-stuck": "worker-released-stuck"}
)
# Ended invocations without a typed inner request, keyed to their reserved retry failure codes.
REQUESTLESS_WORKER_SETTLEMENT_FAILURE_CODES: Mapping[str, str] = MappingProxyType(
    {
        "completed-timeout": "worker-timeout",
        "ended-without-result": "worker-ended-without-result",
        **ENGINE_WORKER_SETTLEMENT_FAILURE_CODES,
    }
)
type EngineWorkerDisposition = Literal["host-lost", "released-stuck"]


class DeliveryPlanningRetrySettlement(_DeliveryModel):
    """Trusted Orchestrator report for one ended Planner retry invocation."""

    change_id: str = Field(min_length=1, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    claim_id: str = Field(min_length=1)
    attempt_id: str = Field(min_length=1)
    disposition: Literal["normal-return", "completed-timeout", "ended-without-result"]
    request: RetryDelivery | None = None

    @model_validator(mode="after")
    def _validate_completed_invocation(self) -> DeliveryPlanningRetrySettlement:
        if self.disposition == "normal-return":
            if self.request is None:
                message = "normal Planner retry settlement requires its unchanged RetryDelivery"
                raise ValueError(message)
            if self.request.outcome_id != self.outcome_id or self.request.claim_id != self.claim_id:
                message = "Planner retry request does not match its settlement identity"
                raise ValueError(message)
            if self.request.failure_code in REQUESTLESS_WORKER_SETTLEMENT_FAILURE_CODES.values():
                message = f"{self.request.failure_code} is reserved for request-less Planner settlements"
                raise ValueError(message)
        elif self.request is not None:
            message = f"{self.disposition} Planner settlement cannot carry an inner request"
            raise ValueError(message)
        return self


class DeliveryBuilderInvocationSettlement(_DeliveryModel):
    """Trusted Orchestrator report for one ended Builder invocation."""

    change_id: str = Field(min_length=1, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    claim_id: str = Field(min_length=1)
    attempt_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    task_id: str = Field(min_length=1, max_length=256)
    expected_last_reviewed_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    disposition: Literal["normal-return", "completed-timeout", "ended-without-result"]
    request: RetryDelivery | BlockDelivery | ReturnDelivery | None = None

    @model_validator(mode="after")
    def _validate_completed_invocation(self) -> DeliveryBuilderInvocationSettlement:
        if self.disposition == "normal-return":
            self._validate_normal_return()
        elif self.request is not None:
            message = f"{self.disposition} Builder settlement cannot carry an inner request"
            raise ValueError(message)
        return self

    def _validate_normal_return(self) -> None:
        request = self.request
        if request is None:
            message = "normal Builder settlement requires its unchanged RetryDelivery, BlockDelivery, or ReturnDelivery"
            raise ValueError(message)
        if request.outcome_id != self.outcome_id or request.claim_id != self.claim_id:
            message = "Builder settlement request does not match its outcome and claim"
            raise ValueError(message)
        if isinstance(request, RetryDelivery):
            if request.failure_code in REQUESTLESS_WORKER_SETTLEMENT_FAILURE_CODES.values():
                message = f"{request.failure_code} is reserved for request-less Builder settlements"
                raise ValueError(message)
            if request.attempt_id != self.attempt_id:
                message = "Builder retry request does not match its attempt"
                raise ValueError(message)
        elif isinstance(request, BlockDelivery):
            if request.request is None or request.request.resolution is not None:
                message = "Builder block settlement requires an unanswered bounded user request"
                raise ValueError(message)
            if request.request.outcome_id != self.outcome_id:
                message = "Builder block request does not match its outcome"
                raise ValueError(message)
        elif request.attempt_id != self.attempt_id:
            message = "Builder return request does not match its attempt"
            raise ValueError(message)


class DeliveryEnginePlanningSettlement(DeliveryPlanningRetrySettlement):
    """Engine-authored end of one Planner invocation whose worker can no longer progress."""

    disposition: EngineWorkerDisposition  # type: ignore[assignment]


class DeliveryEngineBuilderSettlement(DeliveryBuilderInvocationSettlement):
    """Engine-authored end of one Builder invocation whose worker can no longer progress."""

    disposition: EngineWorkerDisposition  # type: ignore[assignment]


class _DeliveryPlanningRetrySettlementReceipt(_DeliveryModel):
    """Immutable result for replaying one exact completed Planner retry invocation."""

    schema_version: Literal[1] = 1
    envelope: DeliveryEnginePlanningSettlement | DeliveryPlanningRetrySettlement
    result: OutcomeAuthorityBinding

    @model_validator(mode="after")
    def _validate_receipt(self) -> _DeliveryPlanningRetrySettlementReceipt:
        if (
            self.result.outcome_id != self.envelope.outcome_id
            or self.result.stage != DeliveryStage.PLANNING
            or self.result.active_claim is not None
        ):
            message = "Planning retry settlement receipt result does not match its completed claim"
            raise ValueError(message)
        return self


class _DeliveryBuilderInvocationSettlementReceipt(_DeliveryModel):
    """Immutable result for replaying one exact completed Builder invocation."""

    schema_version: Literal[1] = 1
    settlement_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    envelope: DeliveryEngineBuilderSettlement | DeliveryBuilderInvocationSettlement
    handoff_context: DeliveryBuilderHandoffContext
    result: OutcomeAuthorityBinding

    @model_validator(mode="after")
    def _validate_receipt(self) -> _DeliveryBuilderInvocationSettlementReceipt:
        context = self.handoff_context
        if (
            self.settlement_id != hashlib.sha256(_model_content(self.envelope)).hexdigest()
            or context.settlement_id != self.settlement_id
            or context.outcome_id != self.envelope.outcome_id
            or context.original_task_id != self.envelope.task_id
            or context.attempt_id != self.envelope.attempt_id
            or context.last_reviewed_commit != self.envelope.expected_last_reviewed_commit
            or self.result.outcome_id != self.envelope.outcome_id
            or self.result.active_claim is not None
            or self.result.builder_handoff_context != context
        ):
            message = "Builder invocation settlement receipt does not match its exact handoff"
            raise ValueError(message)
        expected_stage = (
            DeliveryStage.PLANNING
            if context.route == "same-outcome-planner"
            else DeliveryStage.DESIGN
            if context.route == "same-outcome-design"
            else DeliveryStage.IMPLEMENTATION
        )
        if self.result.stage != expected_stage:
            message = "Builder invocation settlement receipt has an incompatible route stage"
            raise ValueError(message)
        return self


class _DeliveryBuilderPlanPromotionReceipt(_DeliveryModel):
    """Immutable proof that one retained Builder return was promoted through Planning."""

    schema_version: Literal[1] = 1
    promotion_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    change_id: str = Field(min_length=1, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    settlement_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    planner_claim: DeliveryActiveClaim
    source_binding: OutcomeAuthorityBinding
    candidate: DeliveryPlanCandidate
    result_binding: OutcomeAuthorityBinding

    @classmethod
    def create(
        cls,
        *,
        change_id: str,
        source_binding: OutcomeAuthorityBinding,
        result_binding: OutcomeAuthorityBinding,
    ) -> _DeliveryBuilderPlanPromotionReceipt:
        """Create one exact receipt from the published Planner candidate and its successor."""
        context = source_binding.builder_handoff_context
        planner_claim = source_binding.active_claim
        candidate = source_binding.candidate
        if context is None or planner_claim is None or candidate is None:
            message = "Builder return promotion requires its exact Planning handoff, claim, and candidate"
            raise ValueError(message)
        values = {
            "change_id": change_id,
            "outcome_id": context.outcome_id,
            "settlement_id": context.settlement_id,
            "planner_claim": planner_claim,
            "source_binding": source_binding,
            "candidate": candidate,
            "result_binding": result_binding,
        }
        receipt = cls.model_construct(promotion_id="0" * 64, schema_version=1, **values)
        return cls(promotion_id=_receipt_digest(receipt, "promotion_id"), **values)

    @model_validator(mode="after")
    def _validate_receipt(self) -> _DeliveryBuilderPlanPromotionReceipt:
        self._validate_identity()
        self._validate_task_lineage()
        self._validate_successor()
        if self.promotion_id != _receipt_digest(self, "promotion_id"):
            message = "Builder plan promotion receipt identity is invalid"
            raise ValueError(message)
        return self

    def _validate_identity(self) -> None:
        source = self.source_binding
        context = source.builder_handoff_context
        candidate = self.candidate
        task_chain_digest = hashlib.sha256(b"".join(_model_content(task) for task in candidate.tasks)).hexdigest()
        if (
            context is None
            or context.route != "same-outcome-planner"
            or context.outcome_id != self.outcome_id
            or context.settlement_id != self.settlement_id
            or source.outcome_id != self.outcome_id
            or source.stage != DeliveryStage.PLANNING
            or source.active_claim != self.planner_claim
            or self.planner_claim.worker_role != DeliveryWorkerRole.PLANNER
            or self.planner_claim.task_id is not None
            or source.result_candidate is not None
            or source.candidate != candidate
            or candidate.claim_id != self.planner_claim.claim_id
            or candidate.digest != task_chain_digest
            or candidate.candidate_id != f"plan-{task_chain_digest}"
            or source.output != candidate.output
        ):
            message = "Builder plan promotion receipt does not bind its exact Planner candidate"
            raise ValueError(message)

    def _validate_task_lineage(self) -> None:
        source = self.source_binding
        context = source.builder_handoff_context
        candidate_tasks = {task.task_id: task for task in self.candidate.tasks}
        source_tasks = {task.task_id: task for task in source.tasks}
        completed_task_ids = {result.task_id for result in source.results}
        original_task = candidate_tasks.get(context.original_task_id)
        if (
            len(candidate_tasks) != len(self.candidate.tasks)
            or any(
                task.outcome_id != self.outcome_id or task.plan_scope_id != source.plan_scope_id
                for task in self.candidate.tasks
            )
            or any(
                task_id not in candidate_tasks or candidate_tasks[task_id] != source_tasks.get(task_id)
                for task_id in completed_task_ids
            )
            or original_task is None
            or context.original_task_id in completed_task_ids
            or original_task.commitment_ids != context.original_task_commitment_ids
            or original_task.maintained_surfaces != context.original_task_maintained_surfaces
            or not set(original_task.dependency_ids) <= completed_task_ids
        ):
            message = "Builder plan promotion receipt changes completed or original task lineage"
            raise ValueError(message)

    def _validate_successor(self) -> None:
        context = self.source_binding.builder_handoff_context
        expected = self.source_binding.model_copy(
            update={
                "stage": DeliveryStage.IMPLEMENTATION,
                "tasks": self.candidate.tasks,
                "active_claim": None,
                "output": None,
                "candidate": None,
                "return_context": None,
                "builder_handoff_context": context.model_copy(update={"route": "same-task"}),
                "recovery_attention": None,
                "retry_diagnostic": None,
                "block": None,
                "requests": (),
                "retry_fingerprint": None,
                "retry_count": 0,
            }
        )
        if self.result_binding != expected or self.result_binding.results != self.source_binding.results:
            message = "Builder plan promotion receipt does not bind its exact same-task successor"
            raise ValueError(message)


class _DeliveryBuilderRequestResolutionReceipt(_DeliveryModel):
    """Immutable user answer bound to one exact local Builder pause."""

    schema_version: Literal[1] = 1
    change_id: str = Field(min_length=1, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    request_id: str = Field(min_length=1)
    settlement_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    builder_handoff_context: DeliveryBuilderHandoffContext
    resolved_request: DeliveryRequest
    updated_block: DeliveryBlock

    @model_validator(mode="after")
    def _validate_receipt(self) -> _DeliveryBuilderRequestResolutionReceipt:
        context = self.builder_handoff_context
        resolution = self.resolved_request.resolution
        expected_note = None if resolution is None else resolution.response_text or resolution.selected_option_id
        if (
            context.route != "same-task"
            or context.outcome_id != self.outcome_id
            or context.settlement_id != self.settlement_id
            or self.resolved_request.request_id != self.request_id
            or self.resolved_request.outcome_id != self.outcome_id
            or resolution is None
            or (
                self.resolved_request.kind is DeliveryRequestKind.DECISION
                and (
                    resolution.selected_option_id is None
                    or resolution.selected_option_id
                    not in {option.option_id for option in self.resolved_request.options}
                )
            )
            or self.updated_block.request_id != self.request_id
            or not self.updated_block.resolved
            or self.updated_block.resolution_note != expected_note
            or self.updated_block.resolution_locators != (self.request_id,)
        ):
            message = "Builder request resolution receipt does not match its exact handoff"
            raise ValueError(message)
        return self


class _DeliveryBuilderHandoffChangeIntentReceipt(_DeliveryModel):
    """Immutable proof of one supported lifecycle intent during a retained Builder handoff."""

    schema_version: Literal[1] = 1
    receipt_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    action: Literal["defer", "resume", "abandon"]
    change_id: str = Field(min_length=1, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    settlement_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    builder_handoff_context: DeliveryBuilderHandoffContext
    sequence: int = Field(ge=1, le=_MAX_BUILDER_HANDOFF_CHANGE_INTENT_RECEIPTS)
    previous_receipt_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    before_frontier_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    after_frontier_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    before_frontier: DeliveryFrontier
    after_frontier: DeliveryFrontier
    deferral: DeliveryChangeDeferral | None = None
    abandonment: DeliveryChangeAbandonment | None = None

    @classmethod
    def create(  # noqa: PLR0913 - the receipt binds the exact typed transition and its frontier boundary.
        cls,
        *,
        action: Literal["defer", "resume", "abandon"],
        change_id: str,
        outcome_id: str,
        context: DeliveryBuilderHandoffContext,
        sequence: int,
        previous_receipt_id: str | None,
        before_frontier: DeliveryFrontier,
        after_frontier: DeliveryFrontier,
        deferral: DeliveryChangeDeferral | None,
        abandonment: DeliveryChangeAbandonment | None,
    ) -> _DeliveryBuilderHandoffChangeIntentReceipt:
        """Create one receipt from exact before/after typed frontier state."""
        values = {
            "action": action,
            "change_id": change_id,
            "outcome_id": outcome_id,
            "settlement_id": context.settlement_id,
            "builder_handoff_context": context,
            "sequence": sequence,
            "previous_receipt_id": previous_receipt_id,
            "before_frontier_digest": hashlib.sha256(_model_content(before_frontier)).hexdigest(),
            "after_frontier_digest": hashlib.sha256(_model_content(after_frontier)).hexdigest(),
            "before_frontier": before_frontier,
            "after_frontier": after_frontier,
            "deferral": deferral,
            "abandonment": abandonment,
        }
        candidate = cls.model_construct(receipt_id="0" * 64, schema_version=1, **values)
        return cls(receipt_id=_receipt_digest(candidate, "receipt_id"), **values)

    @model_validator(mode="after")
    def _validate_receipt(self) -> _DeliveryBuilderHandoffChangeIntentReceipt:
        self._validate_identity()
        self._validate_bound_frontiers()
        self._validate_action(self._changed_frontier_fields())
        if self.receipt_id != _receipt_digest(self, "receipt_id"):
            message = "Builder handoff change-intent receipt identity is invalid"
            raise ValueError(message)
        return self

    def _validate_identity(self) -> None:
        if (
            self.settlement_id != self.builder_handoff_context.settlement_id
            or self.outcome_id != self.builder_handoff_context.outcome_id
            or (self.sequence == 1) != (self.previous_receipt_id is None)
            or self.before_frontier_digest != hashlib.sha256(_model_content(self.before_frontier)).hexdigest()
            or self.after_frontier_digest != hashlib.sha256(_model_content(self.after_frontier)).hexdigest()
        ):
            message = "Builder handoff change-intent receipt identity is invalid"
            raise ValueError(message)

    def _validate_bound_frontiers(self) -> None:
        for frontier in (self.before_frontier, self.after_frontier):
            if any(binding.active_claim is not None for binding in frontier.bindings):
                message = "Builder handoff change-intent receipt cannot overlap an active claim"
                raise ValueError(message)
            if frontier.integration_repair_claim is not None:
                message = "Builder handoff change-intent receipt cannot overlap an active Integration claim"
                raise ValueError(message)
            matches = [binding for binding in frontier.bindings if binding.outcome_id == self.outcome_id]
            if len(matches) != 1 or matches[0].builder_handoff_context != self.builder_handoff_context:
                message = "Builder handoff change-intent receipt does not bind its retained context"
                raise ValueError(message)

    def _changed_frontier_fields(self) -> set[str]:
        return {
            field_name
            for field_name in DeliveryFrontier.model_fields
            if getattr(self.before_frontier, field_name) != getattr(self.after_frontier, field_name)
        }

    def _validate_action(self, changed_fields: set[str]) -> None:
        if not changed_fields <= _BUILDER_HANDOFF_CHANGE_INTENT_FRONTIER_FIELDS:
            message = "Builder handoff change-intent receipt changes unsupported frontier fields"
            raise ValueError(message)
        if self.action == "defer":
            self._validate_deferral(changed_fields)
        elif self.action == "resume":
            self._validate_resume(changed_fields)
        else:
            self._validate_abandonment(changed_fields)

    def _validate_deferral(self, changed_fields: set[str]) -> None:
        deferral = self.after_frontier.change_deferral
        if (
            self.before_frontier.change_deferral is not None
            or self.before_frontier.change_abandonment is not None
            or deferral is None
            or self.deferral != deferral
            or self.abandonment is not None
            or deferral.change_id != self.change_id
            or deferral.prior_stage != derive_change_stage(self.before_frontier)
            or changed_fields != {"change_deferral"}
        ):
            message = "Builder handoff deferral receipt does not match its exact typed transition"
            raise ValueError(message)

    def _validate_resume(self, changed_fields: set[str]) -> None:
        deferral = self.before_frontier.change_deferral
        if (
            deferral is None
            or self.before_frontier.change_abandonment is not None
            or self.after_frontier.change_deferral is not None
            or self.after_frontier.change_abandonment is not None
            or self.deferral != deferral
            or self.abandonment is not None
            or deferral.change_id != self.change_id
            or changed_fields != {"change_deferral"}
        ):
            message = "Builder handoff resume receipt does not remove its exact typed deferral"
            raise ValueError(message)

    def _validate_abandonment(self, changed_fields: set[str]) -> None:
        abandonment = self.after_frontier.change_abandonment
        expected_changed_fields = {"change_abandonment"}
        if self.before_frontier.change_deferral is not None:
            expected_changed_fields.add("change_deferral")
        if self.before_frontier.pending_checkpoint is not None:
            expected_changed_fields.add("pending_checkpoint")
        if (
            self.before_frontier.change_abandonment is not None
            or self.before_frontier.change_completion is not None
            or abandonment is None
            or self.abandonment != abandonment
            or self.deferral != self.before_frontier.change_deferral
            or self.after_frontier.change_deferral is not None
            or self.after_frontier.pending_checkpoint is not None
            or abandonment.change_id != self.change_id
            or abandonment.prior_stage != derive_change_stage(self.before_frontier)
            or changed_fields != expected_changed_fields
        ):
            message = "Builder handoff abandonment receipt does not match its exact typed transition"
            raise ValueError(message)


class _DeliveryBuilderHandoffChangeIntentHead(_DeliveryModel):
    """CAS-updated reference to the latest immutable handoff intent receipt."""

    schema_version: Literal[1] = 1
    change_id: str = Field(min_length=1, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    settlement_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    builder_handoff_context: DeliveryBuilderHandoffContext
    latest_receipt_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    sequence: int = Field(ge=1, le=_MAX_BUILDER_HANDOFF_CHANGE_INTENT_RECEIPTS)

    @model_validator(mode="after")
    def _validate_head(self) -> _DeliveryBuilderHandoffChangeIntentHead:
        if (
            self.settlement_id != self.builder_handoff_context.settlement_id
            or self.outcome_id != self.builder_handoff_context.outcome_id
        ):
            message = "Builder handoff change-intent head identity is invalid"
            raise ValueError(message)
        return self


@dataclass(frozen=True)
class _BuilderHandoffChangeIntentMutation:
    before: DeliveryFrontier
    after: DeliveryFrontier
    action: Literal["defer", "resume", "abandon"]
    deferral: DeliveryChangeDeferral | None
    abandonment: DeliveryChangeAbandonment | None


class _DeliveryPlanningPauseReplay(_DeliveryModel):
    """Immutable result for replaying one exact request-bearing Planning pause."""

    schema_version: Literal[1] = 1
    change_id: str = Field(min_length=1, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    claim_id: str = Field(min_length=1)
    request_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    request: BlockDelivery
    result: OutcomeAuthorityBinding

    @model_validator(mode="after")
    def _validate_replay(self) -> _DeliveryPlanningPauseReplay:
        delivery_request = self.request.request
        block = self.result.block
        if delivery_request is None:
            message = "Planning pause replay requires its original bounded request"
            raise ValueError(message)
        if (
            self.request_digest != hashlib.sha256(_model_content(self.request)).hexdigest()
            or self.request.outcome_id != self.outcome_id
            or self.request.claim_id != self.claim_id
            or delivery_request.outcome_id != self.outcome_id
            or self.result.outcome_id != self.outcome_id
            or self.result.stage != DeliveryStage.PLANNING
            or self.result.active_claim is not None
            or block is None
            or block.block_id != self.request.block_id
            or block.reason != self.request.reason
            or block.unblock_condition != self.request.unblock_condition
            or block.expected_evidence != self.request.expected_evidence
            or block.locators != self.request.locators
            or block.request_id != delivery_request.request_id
            or block.resume_commit != self.request.resume_commit
            or not self.result.requests
            or self.result.requests[-1] != delivery_request
        ):
            message = "Planning pause replay receipt does not bind its original transition"
            raise ValueError(message)
        return self


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


class DeliveryActionSelectionConflictError(DeliveryRuntimeConflictError):
    """A selected action needs fresh authority before another acquisition attempt."""

    code = "ERR_DELIVERY_ACTION_SELECTION_STALE"


class DeliveryChangeDispositionConflictError(DeliveryRuntimeConflictError):
    """An exact Change attention identity is stale or no longer active."""

    retry_safe = False


class DeliveryChangeDispositionBusyError(DeliveryRuntimeConflictError):
    """A Change attention resolution is temporarily blocked by another mutation."""

    code = "ERR_DELIVERY_ATTENTION_RESOLVE_BUSY"


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
_LEGACY_FRONTIER_SCHEMA_VERSION = 17
_FRONTIER_SCHEMA_VERSION = 18
_RETURN_TARGETS = {
    DeliveryStage.PLANNING: {DeliveryStage.DESIGN},
    DeliveryStage.IMPLEMENTATION: {DeliveryStage.PLANNING, DeliveryStage.DESIGN},
}
_NORMAL_CHANGE_MUTATIONS = frozenset(
    {
        "record_checkpoint_branch_publication",
        "record_design_package_snapshot",
        "queue_admitted_design_checkpoint",
        "queue_explicit_checkpoint",
        "acknowledge_checkpoint_publication",
        "record_checkpoint_failure",
        "record_publication_identity",
        "record_publication_successor",
        "record_target_sync",
        "record_resolved_target_sync",
        "record_target_sync_abort",
        "record_external_head_adoption",
        "record_external_head_promotion",
        "capture_target_sync_conflict",
        "mark_awaiting_merge",
        "clear_ready_for_head_change",
        "reconcile_pull_request_draft_state",
        "latch_merged_pull_request",
        "complete_change",
        "finalize_change",
        "prepare_review_repair",
        "prepare_completed_outcome_repair",
        "reconcile_finalization_head",
        "remove_integration_repair_claim",
        "remove_active_claim",
        "complete_recovery",
        "publish_recovery_attention",
        "activate_claim",
        "publish_output",
        "publish_plan",
        "publish_result",
        "transition",
        "settle_planning_retry",
        "settle_builder_invocation",
        "_retry",
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
    return frontier.change_abandonment is not None or frontier.change_completion is not None


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
    ) -> None:
        self._target_root = runtime_root.resolve()
        if workspace_manager is not None and workspace_manager.runtime_root != self._target_root:
            _conflict("runtime and workspace coordination must share one transaction root")
        self._contract = contract
        self._workspace_manager = workspace_manager
        self._authority_digest = hashlib.sha256(_model_content(contract)).hexdigest()
        self._frontier_path = self._target_root / "changes" / contract.change_id / "frontier.json"
        self._pending_publication_path = self._frontier_path.with_name("state-publication.json")
        self._validate_frontier(self._read()[0])

    @property
    def authority_digest(self) -> str:
        """Return the canonical admitted contract digest bound into task results."""
        return self._authority_digest

    def retry_ledger(self, *, clock: Callable[[], datetime | str] | None = None) -> RetryLedger:
        """Return the Change-scoped durable retry authority."""
        return RetryLedger(self._target_root, self._contract.change_id, clock=clock)

    @property
    def contract(self) -> DeliveryContract:
        """Return immutable admitted authority for scoped context projection."""
        return self._contract

    def frontier_bytes(self) -> bytes:
        """Return current canonical frontier bytes for OCC and failure proof."""
        return self._read()[1]

    def pending_state_publication(self) -> DeliveryPendingStatePublication | None:
        """Return the unacknowledged local state publication intent, if any."""
        if not self._pending_publication_path.is_file():
            return None
        try:
            intent = DeliveryPendingStatePublication.model_validate_json(
                self._pending_publication_path.read_bytes(), strict=False
            )
        except OSError, TypeError, ValueError:
            _reference("Delivery state publication intent is invalid")
        return intent if intent.status == "pending" else None

    def publication_base_digest(self, content: bytes) -> str:
        """Digest the portable projection that remote state can legitimately contain."""
        frontier, _canonical = parse_delivery_frontier(content)
        portable_bindings = tuple(
            binding.model_copy(
                update={
                    "active_claim": None,
                    "output": None,
                    "candidate": None,
                    "result_candidate": None,
                    "recovery_attention": None,
                    "retry_diagnostic": None,
                }
            )
            for binding in frontier.bindings
        )
        portable = frontier.model_copy(update={"bindings": portable_bindings})
        return hashlib.sha256(_model_content(portable)).hexdigest()

    def acknowledge_pending_publication(self, frontier_digest: str) -> None:
        """Mark the matching local publication intent acknowledged after remote push."""
        if not self._pending_publication_path.is_file():
            return
        current_content = self._pending_publication_path.read_bytes()
        current = DeliveryPendingStatePublication.model_validate_json(current_content, strict=False)
        if current.status != "pending" or current.frontier_digest != frontier_digest:
            return
        replacement = _model_content(current.acknowledge())
        participant = ReplacementTransactionParticipant(
            self._target_root,
            self._pending_publication_path.relative_to(self._target_root),
            current_content,
            replacement,
        )
        RuntimeTransaction(
            self._target_root,
            f"delivery-state-ack-{frontier_digest}",
            (participant,),
        ).commit()

    def reanchor_pending_publication(self, base_frontier_digest: str) -> None:
        """Re-anchor a pending publication after a validated authority revision."""
        if not self._pending_publication_path.is_file():
            return
        current_content = self._pending_publication_path.read_bytes()
        current = DeliveryPendingStatePublication.model_validate_json(current_content, strict=False)
        frontier_content = self.frontier_bytes()
        frontier_digest = hashlib.sha256(frontier_content).hexdigest()
        if current.status != "pending" or current.frontier_digest == frontier_digest:
            return
        replacement = _model_content(
            DeliveryPendingStatePublication.pending(
                base_frontier_digest,
                frontier_digest,
                current.transition_request_digest,
            )
        )
        participant = ReplacementTransactionParticipant(
            self._target_root,
            self._pending_publication_path.relative_to(self._target_root),
            current_content,
            replacement,
        )
        RuntimeTransaction(
            self._target_root,
            f"delivery-state-reanchor-{frontier_digest}",
            (participant,),
        ).commit()

    def integration_attention(self) -> DeliveryIntegrationAttention | None:
        """Return current retryable Integration evidence, if any."""
        return self._read()[0].integration_attention

    def change_disposition(self) -> DeliveryChangeDisposition | None:
        """Return current Change-level attention evidence, if any."""
        return self._read()[0].change_disposition

    def change_disposition_publication(self) -> DeliveryChangePublicationIdentity | None:
        """Return the publication identity retained by current Change attention."""
        return self._read()[0].change_disposition_publication

    def change_disposition_resolution(self) -> DeliveryChangeDispositionResolution | None:
        """Return the most recent durable Change attention resolution receipt."""
        return self._read()[0].change_disposition_resolution

    def change_deferral(self) -> DeliveryChangeDeferral | None:
        """Return the current user-requested Change deferral, if any."""
        return self._read()[0].change_deferral

    def change_abandonment(self) -> DeliveryChangeAbandonment | None:
        """Return the terminal user-requested Change abandonment, if any."""
        return self._read()[0].change_abandonment

    def defer_change(
        self,
        reason: str,
        deferred_at: datetime,
        *,
        expected_finalization_attention: ChangeFinalizationAttention | None = None,
    ) -> DeliveryChangeDeferral:
        """Pause one nonterminal Change while retaining its exact frontier and worktree."""
        frontier, previous = self._read()
        if frontier.change_deferral is not None:
            self._require_recorded_builder_handoff_change_intent(frontier)
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
        replacement = frontier.model_copy(update={"change_deferral": deferral})
        participants = self._builder_handoff_change_intent_participants(
            frontier,
            replacement,
            "defer",
            deferral=deferral,
        )
        participants = self._change_intent_custody_participants(participants, expected_finalization_attention)
        self._replace(
            previous,
            replacement,
            additional_participants=participants,
            include_custody_guard=False,
        )
        return deferral

    def resume_change(
        self,
        *,
        expected_finalization_attention: ChangeFinalizationAttention | None = None,
    ) -> DeliveryChangeDeferral:
        """Resume one exact deferred Change and return its preserved prior-state receipt."""
        frontier, previous = self._read()
        if frontier.change_abandonment is not None or is_change_terminal(frontier):
            _conflict("terminal Delivery Change cannot be resumed")
        _require_change_mutable(frontier, "resume_change")
        deferral = frontier.change_deferral
        if deferral is None:
            _conflict("Delivery Change is not deferred")
        _require_no_active_change_claim(frontier, "Change resume")
        replacement = frontier.model_copy(update={"change_deferral": None})
        participants = self._builder_handoff_change_intent_participants(
            frontier,
            replacement,
            "resume",
            deferral=deferral,
        )
        participants = self._change_intent_custody_participants(participants, expected_finalization_attention)
        self._replace(
            previous,
            replacement,
            additional_participants=participants,
            include_custody_guard=False,
        )
        return deferral

    def abandon_change(
        self,
        reason: str,
        abandoned_at: datetime,
        *,
        expected_finalization_attention: ChangeFinalizationAttention | None = None,
    ) -> DeliveryChangeAbandonment:
        """Terminate one uncompleted Change without discarding its retained authority."""
        frontier, previous = self._read()
        if frontier.change_abandonment is not None:
            self._require_recorded_builder_handoff_change_intent(frontier)
            return frontier.change_abandonment
        if frontier.change_completion is not None:
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
        replacement = frontier.model_copy(
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
        )
        participants = self._builder_handoff_change_intent_participants(
            frontier,
            replacement,
            "abandon",
            deferral=frontier.change_deferral,
            abandonment=abandonment,
        )
        participants = self._change_intent_custody_participants(participants, expected_finalization_attention)
        self._replace(
            previous,
            replacement,
            additional_participants=participants,
            include_custody_guard=False,
        )
        return abandonment

    def _capture_existing_change_disposition(
        self,
        frontier: DeliveryFrontier,
        existing: DeliveryChangeDisposition,
        disposition: DeliveryChangeDisposition,
        publication_identity: DeliveryChangePublicationIdentity | None,
    ) -> tuple[DeliveryChangeDisposition, DeliveryFrontier | None]:
        if not (
            existing.kind == disposition.kind
            and existing.change_id == disposition.change_id
            and existing.entered_from == disposition.entered_from
            and existing.diagnostics == disposition.diagnostics
            and existing.acceptance_reason == disposition.acceptance_reason
        ):
            _conflict("Delivery Change already has different attention authority")
        if publication_identity is None:
            return existing, None
        if publication_identity.change_id != self._contract.change_id:
            _conflict("Change publication identity does not match the admitted Change")
        current = frontier.change_disposition_publication
        if current is None:
            return (
                existing,
                frontier.model_copy(update={"change_disposition_publication": publication_identity}),
            )
        if current != publication_identity:
            _conflict("Delivery Change attention has different publication identity")
        return existing, None

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
            result, updated = self._capture_existing_change_disposition(
                frontier,
                existing,
                disposition,
                publication_identity,
            )
            if updated is not None:
                self._replace(previous, updated)
            return result
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
        if retained_publication is not None and retained_publication.change_id != self._contract.change_id:
            _conflict("Change publication identity does not match the admitted Change")
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
        if _target_sync_operation_id(current) is not None:
            _attention_conflict("target synchronization requires an explicit conflict exit")
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
        publication_identity: DeliveryChangePublicationIdentity | None = None,
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
            publication_identity=publication_identity,
        )

    def capture_acceptance_attention(
        self,
        observation: PublicationPullRequestObservationReceipt,
        diagnostics: tuple[str, ...],
        *,
        reason: DeliveryAcceptanceAttentionReason = DeliveryAcceptanceAttentionReason.IDENTITY_MISMATCH,
    ) -> DeliveryChangeDisposition:
        """Capture one mismatched provider acceptance observation."""
        return self.capture_change_disposition(
            DeliveryChangeDisposition.create(
                kind=DeliveryChangeDispositionKind.ACCEPTANCE_ATTENTION,
                change_id=self._contract.change_id,
                entered_from=DeliveryChangeStage.AWAITING_MERGE,
                recorded_at=observation.observed_at,
                diagnostics=(*diagnostics, f"acceptance-observation:{observation.observation_id}"),
                acceptance_reason=reason,
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

    def record_publication_successor(
        self,
        predecessor: DeliveryChangePublicationIdentity,
        successor: DeliveryChangePublicationIdentity,
    ) -> DeliveryChangePublicationHistory:
        """Append one exact successor publication while retaining publication attention."""
        frontier, previous = self._read()
        _require_change_mutable(frontier, "record_publication_successor")
        _require_no_active_change_claim(frontier, "publication supersession")
        disposition = frontier.change_disposition
        if disposition is None or disposition.kind != DeliveryChangeDispositionKind.PUBLICATION_ATTENTION:
            _conflict("publication supersession requires current publication attention")
        if (
            predecessor.change_id != self._contract.change_id
            or successor.change_id != self._contract.change_id
            or frontier.change_disposition_publication != predecessor
        ):
            _conflict("publication supersession predecessor does not match current attention")
        if predecessor == successor:
            _conflict("publication supersession requires a distinct successor identity")
        history = frontier.change_publication_history or DeliveryChangePublicationHistory.create(predecessor)
        try:
            updated_history = history.append(predecessor, successor)
        except ValueError as exc:
            _conflict(str(exc))
        updated = frontier.model_copy(
            update={
                "change_disposition_publication": successor,
                "change_publication_history": updated_history,
            }
        )
        self._replace(previous, updated)
        return updated_history

    def record_publication_identity(
        self,
        publication: DeliveryChangePublicationIdentity,
    ) -> DeliveryChangePublicationHistory:
        """Record the first publication or refresh the exact head of the current PR."""
        frontier, previous = self._read()
        _require_change_mutable(frontier, "record_publication_identity")
        if publication.change_id != self._contract.change_id:
            _conflict("Change publication identity does not match the admitted Change")
        history = frontier.change_publication_history
        if history is None:
            updated_history = DeliveryChangePublicationHistory.create(publication)
        elif history.current == publication:
            return history
        else:
            try:
                updated_history = history.refresh_current(publication)
            except ValueError as exc:
                _conflict(str(exc))
        self._replace(previous, frontier.model_copy(update={"change_publication_history": updated_history}))
        return updated_history

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
        pending_publication = self.pending_state_publication()
        self._replace_content(
            previous,
            _model_content(updated),
            base_frontier_digest=(
                pending_publication.base_frontier_digest
                if pending_publication is not None
                else self.publication_base_digest(previous)
            ),
            transition_request_digest=(
                pending_publication.transition_request_digest if pending_publication is not None else None
            ),
        )
        return self.checkpoint_publication_state()

    def record_design_package_snapshot(
        self,
        expected: DeliveryCheckpointPublicationState,
        receipt: ChangeDesignPackageSnapshotReceipt,
    ) -> DeliveryCheckpointPublicationState:
        """Re-anchor the first checkpoint to its admitted package snapshot commit."""
        frontier, previous = self._read()
        _require_change_mutable(frontier, "record_design_package_snapshot")
        current = frontier.pending_checkpoint
        if current is not None and current.head == receipt.snapshot_head:
            return self.checkpoint_publication_state()
        if (
            expected.change_id != self._contract.change_id
            or expected.pending_checkpoint is None
            or current != expected.pending_checkpoint
            or frontier.published_head != expected.published_head
            or receipt.change_id != self._contract.change_id
            or (
                expected.pending_checkpoint.head is not None
                and receipt.previous_head != expected.pending_checkpoint.head
            )
        ):
            _conflict("Design package snapshot no longer matches the checkpoint queue")
        updated = frontier.model_copy(
            update={"pending_checkpoint": _checkpoint_with_head(current, receipt.snapshot_head)}
        )
        self._replace(previous, updated)
        return self.checkpoint_publication_state()

    def queue_admitted_design_checkpoint(self, reviewed_head: str) -> DeliveryCheckpointPublicationState:
        """Queue the first remote checkpoint for an admitted Design package."""
        frontier, previous = self._read()
        _require_change_mutable(frontier, "queue_admitted_design_checkpoint")
        pending = frontier.pending_checkpoint
        trigger = DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.ADMITTED_DESIGN)
        if pending is not None:
            if pending.head != reviewed_head:
                _conflict("admitted Design checkpoint no longer matches the reviewed boundary")
            if trigger in pending.triggers:
                return self.checkpoint_publication_state()
            updated = frontier.model_copy(
                update={"pending_checkpoint": pending.model_copy(update={"triggers": (*pending.triggers, trigger)})}
            )
        elif frontier.published_head is not None:
            return self.checkpoint_publication_state()
        else:
            updated = frontier.model_copy(
                update={"pending_checkpoint": DeliveryPendingCheckpoint(head=reviewed_head, triggers=(trigger,))}
            )
        self._replace(previous, updated)
        return self.checkpoint_publication_state()

    def queue_explicit_checkpoint(self, reviewed_head: str) -> DeliveryCheckpointPublicationState:
        """Queue one explicit checkpoint for the current reviewed Change head."""
        frontier, previous = self._read()
        _require_change_mutable(frontier, "queue_explicit_checkpoint", allow_attention=True)
        _require_no_active_change_claim(frontier, "explicit checkpoint")
        trigger = DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.EXPLICIT)
        pending = frontier.pending_checkpoint
        if pending is not None:
            if pending.head != reviewed_head:
                _conflict("explicit checkpoint no longer matches the reviewed boundary")
            if trigger in pending.triggers:
                return self.checkpoint_publication_state()
            updated = frontier.model_copy(
                update={"pending_checkpoint": pending.model_copy(update={"triggers": (*pending.triggers, trigger)})}
            )
        elif frontier.published_head == reviewed_head:
            return self.checkpoint_publication_state()
        else:
            updated = frontier.model_copy(
                update={"pending_checkpoint": DeliveryPendingCheckpoint(head=reviewed_head, triggers=(trigger,))}
            )
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
                    trigger in expected.triggers
                    and trigger.kind
                    in {
                        DeliveryCheckpointTriggerKind.ADMITTED_DESIGN,
                        DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK,
                    }
                )
            )
        pending = current.model_copy(update={"triggers": retained}) if retained else None
        updated = frontier.model_copy(update={"pending_checkpoint": pending})
        self._replace_content(previous, _model_content(updated), record_pending_publication=False)
        return self.checkpoint_publication_state()

    def record_checkpoint_failure(
        self,
        expected: DeliveryPendingCheckpoint,
        attempted_at: datetime,
        error_code: str,
        error_detail: str,
    ) -> DeliveryCheckpointPublicationState:
        """Persist one failed checkpoint attempt without changing its obligation."""
        if attempted_at.tzinfo is None:
            message = "pending checkpoint failure timestamp must include a timezone"
            raise ValueError(message)
        if not error_code or not error_detail:
            message = "pending checkpoint failure requires an error code and detail"
            raise ValueError(message)
        frontier, previous = self._read()
        _require_change_mutable(frontier, "record_checkpoint_failure", allow_attention=True)
        current = frontier.pending_checkpoint
        if current is None or current != expected:
            _conflict("checkpoint failure no longer matches the durable queue")
        updated_pending = current.model_copy(
            update={
                "attempt_count": current.attempt_count + 1,
                "last_attempted_at": attempted_at,
                "last_error_code": error_code,
                "last_error_detail": error_detail,
            }
        )
        self._replace(previous, frontier.model_copy(update={"pending_checkpoint": updated_pending}))
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

    def publication_history(self) -> DeliveryChangePublicationHistory | None:
        """Return ordered provider publication identities for this Change."""
        return self._read()[0].change_publication_history

    def target_sync_receipt(self) -> ChangeTargetSyncReceipt | None:
        """Return the latest exact target synchronization receipt, if any."""
        return self._read()[0].target_sync_receipt

    def external_head_adoption_receipt(self) -> ChangeExternalHeadAdoptionReceipt | None:
        """Return the latest exact external Change-head adoption receipt, if any."""
        return self._read()[0].external_head_adoption_receipt

    def external_head_promotion_receipt(self) -> ChangeExternalHeadPromotionReceipt | None:
        """Return the latest exact external Change-head promotion receipt, if any."""
        return self._read()[0].external_head_promotion_receipt

    def validate_target_sync_conflict(
        self,
        expected_disposition_id: str,
        operation_id: str,
    ) -> DeliveryChangeDisposition:
        """Require one exact target-sync operation attention record."""
        frontier, _content = self._read()
        return _require_target_sync_attention(frontier, expected_disposition_id, operation_id)

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
        publication = _pull_request_identity(receipt)
        history = frontier.change_publication_history
        if history is None:
            updated_history = DeliveryChangePublicationHistory.create(publication)
        elif (
            history.current.repository,
            history.current.number,
            history.current.node_id,
        ) == (
            publication.repository,
            publication.number,
            publication.node_id,
        ):
            try:
                updated_history = history.refresh_current(publication)
            except ValueError as exc:
                _conflict(str(exc))
        else:
            _conflict("pull-request ready receipt does not match the current publication")
        if frontier.ready is not None:
            if frontier.ready == receipt:
                if frontier.change_publication_history != updated_history:
                    self._replace(
                        previous,
                        frontier.model_copy(update={"change_publication_history": updated_history}),
                    )
                return receipt
            _conflict("Delivery Change is already awaiting merge with different authority")
        self._replace(
            previous,
            frontier.model_copy(update={"ready": receipt, "change_publication_history": updated_history}),
        )
        return receipt

    def clear_ready_for_head_change(
        self,
        finalization_id: str,
        exact_head: str,
    ) -> PullRequestReadyReceipt | None:
        """Clear local ready authority after its provider pull request returns to draft."""
        frontier, previous = self._read()
        _require_change_mutable(frontier, "clear_ready_for_head_change")
        finalization = frontier.finalization
        ready = frontier.ready
        if ready is None:
            return None
        if (
            finalization is None
            or finalization.finalization_id != finalization_id
            or finalization.exact_head != exact_head
            or ready.finalization_id != finalization_id
            or ready.head_sha != exact_head
        ):
            _conflict("ready authority does not match the head-change boundary")
        self._replace(previous, frontier.model_copy(update={"ready": None}))
        return ready

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
                reason=DeliveryAcceptanceAttentionReason.IDENTITY_MISMATCH,
            )
            _conflict("merged pull-request evidence does not match awaiting-merge authority")
        existing = frontier.merged_pull_request_latch
        if existing is not None and (
            snapshot.state != "closed"
            or not snapshot.merged
            or snapshot.merge_commit_sha is None
            or snapshot.merged_at is None
        ):
            self.capture_acceptance_attention(
                observation,
                ("provider acceptance evidence regressed from the immutable merged latch",),
                reason=DeliveryAcceptanceAttentionReason.LATCH_REGRESSION,
            )
            _conflict("provider acceptance evidence regressed from the immutable merged latch")
        if is_acceptance_waiting_observation(observation):
            message = "provider pull request is still open and unmerged"
            raise DeliveryAcceptanceWaitingError(message)
        if not snapshot.merged or snapshot.state != "closed":
            self.capture_acceptance_attention(
                observation,
                ("provider acceptance observation is not merged and closed",),
                reason=DeliveryAcceptanceAttentionReason.CLOSED_UNMERGED,
            )
            _conflict("acceptance observation does not report a merged pull request")
        if snapshot.merged_at is None or snapshot.merge_commit_sha is None:
            self.capture_acceptance_attention(
                observation,
                ("provider acceptance observation is missing merge evidence",),
                reason=DeliveryAcceptanceAttentionReason.MERGE_EVIDENCE_MISSING,
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
            self.capture_acceptance_attention(
                observation,
                ("provider acceptance evidence conflicts with the immutable merged latch",),
                reason=DeliveryAcceptanceAttentionReason.LATCH_REGRESSION,
            )
            _conflict("merged pull-request evidence conflicts with the immutable latch")
        self._replace(previous, frontier.model_copy(update={"merged_pull_request_latch": candidate}))
        return candidate

    def complete_change(
        self, receipt: CompletionReceipt, *, additional_participants: tuple[TransactionParticipant, ...] = ()
    ) -> CompletionReceipt:
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
            outcome_promises=tuple(outcome.promise for outcome in self._contract.outcomes),
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
        pending_participant = self._pending_publication_participant(
            replacement,
            self.publication_base_digest(previous),
        )
        transaction_id = hashlib.sha256(
            completion_participant.content
            + display_participant.content
            + previous
            + replacement
            + b"".join(participant.content for participant in additional_participants)
        ).hexdigest()
        RuntimeTransaction(
            self._target_root,
            f"delivery-completion-{transaction_id}",
            (
                completion_participant,
                display_participant,
                frontier_participant,
                pending_participant,
                *additional_participants,
            ),
        ).commit()
        return receipt

    def completion_bundle(self) -> CompletionReceiptBundle | None:
        """Return the immutable completion evidence for this Change, if present."""
        return CompletionReceiptStore(self._target_root).read_bundle(self._contract.change_id)

    def finalize_change(
        self,
        request: FinalizeDeliveryChange,
        finalized_at: datetime,
        *,
        additional_participants: tuple[ReplacementTransactionParticipant, ...] = (),
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
        invalidation = frontier.finalization_invalidation
        if (
            invalidation is not None
            and invalidation.reason == "review-repair"
            and request.exact_head == invalidation.expected_head
        ):
            _conflict("review repair requires a new Change commit before finalization")
        if any(binding.active_claim is not None for binding in frontier.bindings):
            _conflict("Delivery finalization cannot overlap an active Outcome claim")
        if frontier.integration_repair_claim is not None:
            _conflict("Delivery finalization cannot overlap an Integration repair claim")
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
        replacement = _model_content(updated)
        frontier_participant = ReplacementTransactionParticipant(
            self._target_root,
            self._frontier_path.relative_to(self._target_root),
            previous,
            replacement,
        )
        participant_content = b"".join(
            b"\0".join(
                (
                    str(participant.root.resolve()).encode(),
                    participant.relative_path.as_posix().encode(),
                    participant.expected_content,
                    participant.replacement_content,
                )
            )
            for participant in additional_participants
        )
        transaction_id = hashlib.sha256(previous + replacement + participant_content).hexdigest()
        RuntimeTransaction(
            self._target_root,
            f"delivery-finalization-{transaction_id}",
            (
                frontier_participant,
                self._pending_publication_participant(replacement, self.publication_base_digest(previous)),
                *additional_participants,
                *self.retry_ledger().owner_result_participants(request.operation_id, accepted=True, now=finalized_at),
            ),
        ).commit()
        return receipt

    def reconcile_finalization_head(
        self,
        observed_head: str,
        invalidated_at: datetime,
    ) -> DeliveryFinalizationReceipt | DeliveryFinalizationInvalidationReceipt | None:
        """Retain exact finalization or invalidate it after observed Change-head drift."""
        frontier, previous = self._read()
        _require_change_mutable(frontier, "reconcile_finalization_head", allow_attention=True)
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

    def prepare_review_repair(
        self,
        expected_finalization_id: str,
        invalidated_at: datetime,
    ) -> DeliveryFinalizationInvalidationReceipt:
        """Invalidate current finalization before repairing external review feedback."""
        frontier, previous = self._read()
        _require_change_mutable(frontier, "prepare_review_repair", allow_attention=True)
        finalization = frontier.finalization
        existing = frontier.finalization_invalidation
        if finalization is None:
            if (
                existing is not None
                and existing.reason == "review-repair"
                and existing.finalization_id == expected_finalization_id
            ):
                return existing
            _conflict("review repair requires current finalization authority")
        if finalization.finalization_id != expected_finalization_id:
            _conflict("review repair finalization identity is stale")
        if frontier.merged_pull_request_latch is not None:
            _conflict("merged Change cannot be reopened for review repair")
        if frontier.change_disposition is not None:
            _conflict("review repair requires current Change attention resolution")
        invalidation = DeliveryFinalizationInvalidationReceipt.create(
            DeliveryFinalizationInvalidation(
                change_id=self._contract.change_id,
                finalization_id=finalization.finalization_id,
                expected_head=finalization.exact_head,
                observed_head=finalization.exact_head,
                reason="review-repair",
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

    def prepare_completed_outcome_repair(
        self,
        request: PrepareCompletedOutcomeRepair,
    ) -> OutcomeAuthorityBinding:
        """Append one derived Builder repair task without erasing prior evidence."""
        frontier, previous = self._read()
        _require_change_mutable(frontier, "prepare_completed_outcome_repair", allow_attention=True)
        if frontier.finalization is not None or frontier.ready is not None:
            _conflict("completed-outcome repair requires no successful finalization authority")
        if frontier.merged_pull_request_latch is not None:
            _conflict("merged Change cannot be reopened for completed-outcome repair")
        if self._workspace_manager is None:
            _conflict("completed-outcome repair requires finalizer custody authority")
        binding = _find_binding(frontier, request.outcome_id)
        source = next((task for task in binding.tasks if task.task_id == request.owning_task_id), None)
        if source is None:
            _reference("completed-outcome repair task ownership is absent")
        repair_id = _completed_outcome_repair_id(self._contract.change_id, request, source.digest)
        repair_task_id = f"repair-{repair_id}"
        existing = next((task for task in binding.tasks if task.task_id == repair_task_id), None)
        persisted, lineage = self._completed_outcome_repair_history(
            binding,
            existing,
            repair_id,
            repair_task_id,
        )
        finished_at = persisted.finished_at if persisted is not None else datetime.now(UTC).isoformat()
        receipt = CompletedOutcomeRepairReceipt.create(
            self._contract.change_id,
            request,
            repair_task_id,
            lineage.previous_task_ids,
            lineage.previous_result_ids,
            finished_at,
        )
        repair_binding = self.retry_ledger().repair_binding_participant(
            original_attempt_id=request.original_action_id,
            repair_attempt_id=request.attempt_id,
            repair_task_id=repair_task_id,
            outcome_id=request.outcome_id,
            now=finished_at,
            allow_settled=existing is not None,
        )
        repair = self._completed_outcome_repair_task(source, request, repair_task_id, lineage.previous_task_ids)
        if self._completed_outcome_repair_replay(existing, persisted, repair, receipt):
            return binding
        if binding.stage != DeliveryStage.COMPLETED:
            _conflict("completed-outcome repair requires one completed owning outcome")
        if len(binding.results) != len(binding.tasks) or {result.task_id for result in binding.results} != set(
            binding.task_ids
        ):
            _conflict("completed-outcome repair requires all prior task results")
        if hashlib.sha256(previous).hexdigest() != request.expected_frontier_digest:
            _conflict("completed-outcome repair frontier changed")
        updated_binding = binding.model_copy(
            update={
                "stage": DeliveryStage.IMPLEMENTATION,
                "tasks": (*binding.tasks, repair),
                "active_claim": None,
                "output": None,
                "candidate": None,
                "result_candidate": None,
                "recovery_attention": None,
                "return_context": None,
                "block": None,
                "retry_fingerprint": None,
                "retry_count": 0,
            }
        )
        additional_participants: tuple[TransactionParticipant | ReplacementTransactionParticipant, ...] = (
            TransactionParticipant(
                self._target_root,
                journal_path(self._contract.change_id, repair_id, "receipt"),
                encoded(receipt),
            ),
            repair_binding,
        )
        custody = self._workspace_manager.prepare_finalization_repair_release(
            self._contract.change_id,
            request.original_action_id,
            finished_at,
        )
        additional_participants = (*additional_participants, custody)
        replacement = _replace_binding(frontier, binding, updated_binding)
        # The exact finalizer release is one of the participants below, so the
        # ordinary no-active-finalizer guard must not be added here.
        self._replace_content(
            previous,
            _model_content(replacement),
            additional_participants=additional_participants,
        )
        return updated_binding

    def _completed_outcome_repair_history(
        self,
        binding: OutcomeAuthorityBinding,
        existing: DeliveryTaskDefinition | None,
        repair_id: str,
        repair_task_id: str,
    ) -> tuple[CompletedOutcomeRepairReceipt | None, _CompletedOutcomeRepairLineage]:
        if existing is not None:
            try:
                persisted = CompletedOutcomeRepairReceipt.model_validate_json(
                    read_record(self._target_root, journal_path(self._contract.change_id, repair_id, "receipt"))
                )
            except (OSError, TypeError, ValueError) as exc:
                _reference("completed-outcome repair receipt is missing or invalid", exc)
            lineage = _CompletedOutcomeRepairLineage(
                persisted.previous_task_ids,
                persisted.previous_result_ids,
            )
            if (
                tuple(task.task_id for task in binding.tasks if task.task_id != repair_task_id)
                != lineage.previous_task_ids
                or tuple(result.result_id for result in binding.results if result.task_id in lineage.previous_task_ids)
                != lineage.previous_result_ids
            ):
                _conflict("completed-outcome repair receipt no longer matches its retained lineage")
            return persisted, lineage
        lineage = _CompletedOutcomeRepairLineage(
            binding.task_ids,
            tuple(result.result_id for result in binding.results),
        )
        return None, lineage

    @staticmethod
    def _completed_outcome_repair_task(
        source: DeliveryTaskDefinition,
        request: PrepareCompletedOutcomeRepair,
        repair_task_id: str,
        previous_task_ids: tuple[str, ...],
    ) -> DeliveryTaskDefinition:
        return DeliveryTaskDefinition(
            task_id=repair_task_id,
            outcome_id=source.outcome_id,
            plan_scope_id=source.plan_scope_id,
            title=f"Repair reproduced {request.defect_code}",
            result=(
                f"Correct the reproduced {request.finding_boundary} defect {request.defect_code}; "
                f"resume original action {request.original_action_id} only after the repair proof passes."
            ),
            commitment_ids=source.commitment_ids,
            dependency_ids=previous_task_ids,
            required_outputs=source.required_outputs,
            maintained_surfaces=source.maintained_surfaces,
            constraints=(
                *source.constraints,
                f"Use preserved workspace evidence {request.preservation_id}.",
            ),
            exclusions=source.exclusions,
            acceptance_observations=source.acceptance_observations,
            proof_boundaries=(
                *source.proof_boundaries,
                f"Repair episode {request.episode_id} attempt {request.attempt_id} must be independently reproven.",
            ),
        )

    @staticmethod
    def _completed_outcome_repair_replay(
        existing: DeliveryTaskDefinition | None,
        persisted: CompletedOutcomeRepairReceipt | None,
        repair: DeliveryTaskDefinition,
        receipt: CompletedOutcomeRepairReceipt,
    ) -> bool:
        if existing is None:
            return False
        if existing != repair:
            _conflict("completed-outcome repair publication conflicts with its episode identity")
        if persisted is None:
            _reference("completed-outcome repair receipt is missing or invalid")
        if persisted != receipt:
            _conflict("completed-outcome repair receipt conflicts with its episode identity")
        return True

    def has_completed_outcome_repair(self, request: PrepareCompletedOutcomeRepair) -> bool:
        """Return whether the exact engine-derived repair task is already present."""
        frontier, _previous = self._read()
        binding = _find_binding(frontier, request.outcome_id)
        source = next((task for task in binding.tasks if task.task_id == request.owning_task_id), None)
        if source is None:
            return False
        repair_id = _completed_outcome_repair_id(self._contract.change_id, request, source.digest)
        return any(task.task_id == f"repair-{repair_id}" for task in binding.tasks)

    def record_target_sync(
        self,
        receipt: ChangeTargetSyncReceipt,
        synced_at: datetime,
    ) -> ChangeTargetSyncReceipt:
        """Persist one exact target-sync result and invalidate stale finalization authority."""
        frontier, previous = self._read()
        _require_change_mutable(frontier, "record_target_sync")
        _require_no_active_change_claim(frontier, "target synchronization")
        _require_no_review_repair(frontier, "target synchronization")
        if receipt.change_id != self._contract.change_id:
            _conflict("target synchronization receipt does not match the admitted Change")
        existing = frontier.target_sync_receipt
        if existing is not None and existing.operation_id == receipt.operation_id:
            if existing != receipt:
                _conflict("target synchronization operation has different receipt evidence")
            return existing
        updated = self._target_sync_update(frontier, receipt, synced_at)
        self._replace(previous, updated)
        return receipt

    def record_external_head_adoption(
        self,
        receipt: ChangeExternalHeadAdoptionReceipt,
        adopted_at: datetime,
    ) -> ChangeExternalHeadAdoptionReceipt:
        """Persist one adopted external head, invalidate stale finalization, and queue publication."""
        frontier, previous = self._read()
        _require_change_mutable(frontier, "record_external_head_adoption")
        _require_no_active_change_claim(frontier, "external Change head adoption")
        _require_no_review_repair(frontier, "external Change head adoption")
        if adopted_at.tzinfo is None:
            message = "external Change head adoption timestamp must include a timezone"
            raise ValueError(message)
        if receipt.change_id != self._contract.change_id:
            _conflict("external Change head adoption receipt does not match the admitted Change")
        existing = frontier.external_head_adoption_receipt
        if existing is not None and existing.operation_id == receipt.operation_id:
            if existing != receipt:
                _conflict("external Change head adoption operation has different receipt evidence")
            return existing
        updated = self._external_head_adoption_update(frontier, receipt, adopted_at)
        self._replace(previous, updated)
        return receipt

    def record_external_head_promotion(
        self,
        receipt: ChangeExternalHeadPromotionReceipt,
        promoted_at: datetime,
    ) -> ChangeExternalHeadPromotionReceipt:
        """Persist one exact external Change-head review admission."""
        frontier, previous = self._read()
        _require_change_mutable(frontier, "record_external_head_promotion")
        _require_no_active_change_claim(frontier, "external Change head promotion")
        _require_no_review_repair(frontier, "external Change head promotion")
        if promoted_at.tzinfo is None:
            message = "external Change head promotion timestamp must include a timezone"
            raise ValueError(message)
        if receipt.change_id != self._contract.change_id:
            _conflict("external Change head promotion receipt does not match the admitted Change")
        adoption = frontier.external_head_adoption_receipt
        if adoption is None or receipt.adoption_receipt_id != adoption.receipt_id:
            _conflict("external Change head promotion receipt does not match current adoption evidence")
        if receipt.promoted_head != adoption.adopted_head:
            _conflict("external Change head promotion receipt does not match the adopted head")
        existing = frontier.external_head_promotion_receipt
        if existing is not None and existing.operation_id == receipt.operation_id:
            if existing != receipt:
                _conflict("external Change head promotion operation has different receipt evidence")
            return existing
        updated = frontier.model_copy(update={"external_head_promotion_receipt": receipt})
        self._replace(previous, updated)
        return receipt

    def record_resolved_target_sync(
        self,
        receipt: ChangeTargetSyncReceipt,
        expected_disposition_id: str,
        operation_id: str,
        synced_at: datetime,
    ) -> ChangeTargetSyncReceipt:
        """Record one resolved merge while atomically clearing its exact attention."""
        frontier, previous = self._read()
        _require_change_mutable(frontier, "record_resolved_target_sync", allow_attention=True)
        _require_no_active_change_claim(frontier, "target synchronization resolution")
        _require_target_sync_attention(frontier, expected_disposition_id, operation_id)
        if receipt.change_id != self._contract.change_id:
            _conflict("target synchronization receipt does not match the admitted Change")
        existing = frontier.target_sync_receipt
        if existing is not None and existing.operation_id == receipt.operation_id:
            if existing != receipt:
                _conflict("target synchronization operation has different receipt evidence")
            return existing
        updated = self._target_sync_update(frontier, receipt, synced_at)
        resolution = DeliveryChangeDispositionResolution.create(
            change_id=self._contract.change_id,
            disposition_id=expected_disposition_id,
            resolved_at=synced_at,
        )
        updated = updated.model_copy(
            update={
                "change_disposition": None,
                "change_disposition_publication": None,
                "change_disposition_resolution": resolution,
            }
        )
        self._replace(previous, updated)
        return receipt

    def record_target_sync_abort(
        self,
        expected_disposition_id: str,
        operation_id: str,
        resolved_at: datetime,
    ) -> DeliveryChangeDispositionResolution:
        """Clear one exact target-sync attention after its workspace abort receipt exists."""
        frontier, previous = self._read()
        _require_change_mutable(frontier, "record_target_sync_abort", allow_attention=True)
        _require_target_sync_attention(frontier, expected_disposition_id, operation_id)
        _require_no_active_change_claim(frontier, "target synchronization abort")
        resolution = DeliveryChangeDispositionResolution.create(
            change_id=self._contract.change_id,
            disposition_id=expected_disposition_id,
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

    def _target_sync_update(
        self,
        frontier: DeliveryFrontier,
        receipt: ChangeTargetSyncReceipt,
        synced_at: datetime,
    ) -> DeliveryFrontier:
        if synced_at.tzinfo is None:
            message = "target synchronization timestamp must include a timezone"
            raise ValueError(message)
        finalization = frontier.finalization
        invalidation = frontier.finalization_invalidation
        ready = frontier.ready
        if finalization is not None and finalization.exact_head != receipt.merged_head:
            invalidation = DeliveryFinalizationInvalidationReceipt.create(
                DeliveryFinalizationInvalidation(
                    change_id=self._contract.change_id,
                    finalization_id=finalization.finalization_id,
                    expected_head=finalization.exact_head,
                    observed_head=receipt.merged_head,
                    invalidated_at=synced_at,
                )
            )
            finalization = None
            ready = None

        pending = frontier.pending_checkpoint
        triggers = (
            ()
            if pending is None
            else tuple(
                trigger for trigger in pending.triggers if trigger.kind != DeliveryCheckpointTriggerKind.FINALIZATION
            )
        )
        explicit = DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.EXPLICIT)
        if explicit not in triggers:
            triggers = (*triggers, explicit)
        return frontier.model_copy(
            update={
                "target_sync_receipt": receipt,
                "finalization": finalization,
                "finalization_invalidation": invalidation,
                "ready": ready,
                "pending_checkpoint": _checkpoint_with_head(
                    pending,
                    receipt.merged_head,
                    triggers,
                ),
            }
        )

    def _external_head_adoption_update(
        self,
        frontier: DeliveryFrontier,
        receipt: ChangeExternalHeadAdoptionReceipt,
        adopted_at: datetime,
    ) -> DeliveryFrontier:
        finalization = frontier.finalization
        invalidation = frontier.finalization_invalidation
        ready = frontier.ready
        if finalization is not None and finalization.exact_head != receipt.adopted_head:
            invalidation = DeliveryFinalizationInvalidationReceipt.create(
                DeliveryFinalizationInvalidation(
                    change_id=self._contract.change_id,
                    finalization_id=finalization.finalization_id,
                    expected_head=finalization.exact_head,
                    observed_head=receipt.adopted_head,
                    invalidated_at=adopted_at,
                )
            )
            finalization = None
            ready = None

        pending = frontier.pending_checkpoint
        triggers = (
            ()
            if pending is None
            else tuple(
                trigger for trigger in pending.triggers if trigger.kind != DeliveryCheckpointTriggerKind.FINALIZATION
            )
        )
        explicit = DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.EXPLICIT)
        if explicit not in triggers:
            triggers = (*triggers, explicit)
        return frontier.model_copy(
            update={
                "external_head_adoption_receipt": receipt,
                "external_head_promotion_receipt": None,
                "finalization": finalization,
                "finalization_invalidation": invalidation,
                "ready": ready,
                "pending_checkpoint": _checkpoint_with_head(
                    pending,
                    receipt.adopted_head,
                    triggers,
                ),
            }
        )

    def capture_target_sync_conflict(
        self,
        operation_id: str,
        target_head: str,
        recorded_at: datetime,
        diagnostics: tuple[str, ...],
        *,
        publication_identity: DeliveryChangePublicationIdentity | None = None,
    ) -> DeliveryChangeDisposition:
        """Retain target-merge attention and invalidate authority exposed to the conflict."""
        frontier, previous = self._read()
        existing = frontier.change_disposition
        if existing is not None:
            _require_target_sync_attention(frontier, existing.disposition_id, operation_id)
            return existing
        _require_change_mutable(frontier, "capture_target_sync_conflict")
        _require_no_active_change_claim(frontier, "target synchronization attention capture")
        if recorded_at.tzinfo is None:
            message = "target synchronization attention timestamp must include a timezone"
            raise ValueError(message)
        if publication_identity is None and frontier.ready is not None:
            publication_identity = _pull_request_identity(frontier.ready)
        if publication_identity is not None and publication_identity.change_id != self._contract.change_id:
            _conflict("Change publication identity does not match the admitted Change")

        invalidation = frontier.finalization_invalidation
        if frontier.finalization is not None:
            if frontier.finalization.exact_head == target_head:
                _conflict("target synchronization conflict head must differ from finalized Change head")
            invalidation = DeliveryFinalizationInvalidationReceipt.create(
                DeliveryFinalizationInvalidation(
                    change_id=self._contract.change_id,
                    finalization_id=frontier.finalization.finalization_id,
                    expected_head=frontier.finalization.exact_head,
                    observed_head=target_head,
                    reason="target-sync-conflict",
                    invalidated_at=recorded_at,
                )
            )
        disposition = DeliveryChangeDisposition.create(
            kind=DeliveryChangeDispositionKind.PUBLICATION_ATTENTION,
            change_id=self._contract.change_id,
            entered_from=self.change_stage(),
            recorded_at=recorded_at,
            diagnostics=(f"target-sync-operation:{operation_id}", *diagnostics),
        )
        updated = frontier.model_copy(
            update={
                "target_sync_receipt": None,
                "change_disposition": disposition,
                "change_disposition_publication": publication_identity,
                "change_disposition_resolution": None,
                "finalization": None,
                "finalization_invalidation": invalidation,
                "ready": None,
                "pending_checkpoint": _invalidate_finalization_checkpoint(frontier.pending_checkpoint),
            }
        )
        self._replace(previous, updated)
        return disposition

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
        """Validate identity but refuse unsupported Integration custody release."""
        frontier, _previous = self._read()
        _require_change_mutable(frontier, "remove_integration_repair_claim")
        claim = frontier.integration_repair_claim
        if claim is None or claim.attempt_id != attempt_id or claim.claim_id != claim_id:
            _conflict("claim removal does not match the active Integration repair identity")
        raise DeliveryWorkerExclusionRequiredError

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
        """Validate identity but refuse unsupported failed-claim custody release."""
        frontier, _previous = self._read()
        _require_change_mutable(frontier, "remove_active_claim")
        binding = _find_binding(frontier, outcome_id)
        claim = binding.active_claim
        if claim is None or claim.attempt_id != attempt_id or claim.claim_id != claim_id:
            _conflict("claim removal does not match the active execution identity")
        raise DeliveryWorkerExclusionRequiredError

    def complete_recovery(self, intent: RecoveryIntent, receipt: RecoveryReceipt) -> None:
        """Atomically publish a verified recovery receipt and retire only its exact owner."""
        frontier, previous = self._read()
        _require_change_mutable(frontier, "complete_recovery")
        request = intent.invocation.request
        if request.change_id != self._contract.change_id or digest(previous) != intent.frontier_digest:
            raise DeliveryWorkerExclusionRequiredError
        replacement = frontier
        if intent.kind == "clean-claim":
            binding = self.require_active_claim(request.outcome_id, request.attempt_id, request.owner_id)
            if (
                binding.output is not None
                or binding.result_candidate is not None
                or binding.candidate is not None
                or binding.builder_handoff_context is not None
            ):
                raise DeliveryWorkerExclusionRequiredError
            replacement = _replace_binding(
                frontier,
                binding,
                binding.model_copy(update={"active_claim": None, "recovery_attention": None, "retry_diagnostic": None}),
            )
        elif any(binding.active_claim is not None for binding in frontier.bindings):
            raise DeliveryWorkerExclusionRequiredError
        if frontier.integration_repair_claim is not None:
            raise DeliveryWorkerExclusionRequiredError
        custody = self._require_workspace().prepare_recovery_release(intent, receipt)
        participants = (
            TransactionParticipant(
                self._target_root, journal_path(request.change_id, intent.recovery_id, "receipt"), encoded(receipt)
            ),
            custody,
        )
        # The exact custody replacement and completed receipt replace the ordinary no-change
        # guard. They cannot be split from this centrally admitted frontier mutation.
        portable = not any(binding.active_claim is not None for binding in replacement.bindings)
        portable = portable and not any(binding.builder_handoff_context is not None for binding in replacement.bindings)
        portable = portable and replacement.integration_repair_claim is None
        self._replace_content(
            previous,
            _model_content(replacement),
            record_pending_publication=replacement != frontier and portable,
            additional_participants=participants,
        )

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
        planner_handoff_ids = {
            binding.outcome_id
            for binding in frontier.bindings
            if binding.builder_handoff_context is not None
            and binding.builder_handoff_context.route == "same-outcome-planner"
        }
        if len(planner_handoff_ids) > 1:
            return ()
        planner_handoff_id = next(iter(planner_handoff_ids), None)
        return tuple(
            binding.outcome_id
            for binding in frontier.bindings
            if binding.stage not in {DeliveryStage.DESIGN, DeliveryStage.COMPLETED}
            and binding.active_claim_id is None
            and (binding.block is None or binding.block.resolved)
            and (planner_handoff_id is None or binding.outcome_id == planner_handoff_id)
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
        claimable = tuple(
            task.task_id
            for task in binding.tasks
            if task.task_id not in completed and set(task.dependency_ids) <= completed
        )
        handoff = binding.builder_handoff_context
        if handoff is None:
            return claimable
        return tuple(task_id for task_id in claimable if task_id == handoff.original_task_id)

    def change_stage(self) -> DeliveryChangeStage:
        """Derive change lifecycle from canonical outcome state."""
        return derive_change_stage(self._read()[0])

    def activate_claim(
        self,
        request: ActivateDeliveryClaim,
        *,
        builder_handoff_participant: ReplacementTransactionParticipant | None = None,
        builder_handoff_lock: PublicationLock | None = None,
    ) -> OutcomeAuthorityBinding:
        """Bind one fresh claim to a currently claimable outcome."""
        frontier, previous = self._read()
        if (
            request.expected_frontier_digest is not None
            and hashlib.sha256(previous).hexdigest() != request.expected_frontier_digest
        ):
            message = "selected action frontier changed before claim activation"
            raise DeliveryActionSelectionConflictError(message)
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
        handoff_participant = self._validate_builder_handoff_activation(
            request,
            binding,
            builder_handoff_participant,
            builder_handoff_lock,
        )
        claimed = binding.model_copy(
            update={
                "active_claim": request.claim,
                "output": None,
                "result_candidate": None,
                "recovery_attention": None,
                "retry_diagnostic": None,
            }
        )
        self._replace(
            previous,
            _replace_binding(frontier, binding, claimed),
            additional_participants=(handoff_participant,) if handoff_participant is not None else (),
            include_custody_guard=handoff_participant is None,
        )
        return claimed

    def _validate_builder_handoff_activation(
        self,
        request: ActivateDeliveryClaim,
        binding: OutcomeAuthorityBinding,
        participant: ReplacementTransactionParticipant | None,
        lock: PublicationLock | None,
    ) -> ReplacementTransactionParticipant | None:
        context = binding.builder_handoff_context
        if context is None:
            if participant is not None or lock is not None:
                _conflict("Builder handoff activation has no retained same-task authority")
            return None
        if context.route == "same-outcome-planner":
            return self._validate_planner_handoff_activation(request, binding, participant, lock, context)
        if (
            binding.stage != DeliveryStage.IMPLEMENTATION
            or context.route != "same-task"
            or context.outcome_id != request.outcome_id
            or context.original_task_id != request.task_id
        ):
            _conflict("Builder handoff activation requires its exact retained same-task authority")
        if participant is None or lock is None:
            _conflict("Builder handoff activation requires jointly prepared workspace consumption")
        if self._workspace_manager is None or type(lock) is not PublicationLock:
            _conflict("Builder handoff activation requires its active workspace publication lock")
        if type(participant) is not ReplacementTransactionParticipant:
            _conflict("Builder handoff activation requires a prepared workspace replacement")

        change_id = self._contract.change_id
        handoff = self._workspace_manager.show(change_id).builder_handoff
        if handoff is None or (
            handoff.change_id != change_id
            or handoff.settlement_id != context.settlement_id
            or handoff.original_task_id != context.original_task_id
            or handoff.original_writer.attempt_id != context.attempt_id
            or handoff.last_reviewed_commit != context.last_reviewed_commit
            or handoff.branch_head != context.branch_head
            or handoff.metadata_fingerprint != context.metadata_fingerprint
        ):
            _conflict("Builder handoff activation requires its exact retained workspace custody")

        claim = request.claim
        writer = ChangeWriter(
            attempt_id=claim.attempt_id,
            claim_id=claim.claim_id,
            actor_id=claim.owner_id,
            process_id=claim.process_id,
            claimed_at=claim.started_at,
            job_id=1,
            kind="build",
        )
        prepared = self._workspace_manager.prepare_builder_handoff_acquisition(
            change_id,
            writer,
            handoff,
            lock,
            task_id=context.original_task_id,
        )
        if (
            participant.root != prepared.root
            or participant.relative_path != prepared.relative_path
            or participant.expected_content != prepared.expected_content
            or participant.replacement_content != prepared.replacement_content
        ):
            _conflict("Builder handoff activation participant does not match the exact prepared workspace consumption")
        return prepared

    def _validate_planner_handoff_activation(
        self,
        request: ActivateDeliveryClaim,
        binding: OutcomeAuthorityBinding,
        participant: ReplacementTransactionParticipant | None,
        lock: PublicationLock | None,
        context: DeliveryBuilderHandoffContext,
    ) -> None:
        if (
            binding.stage != DeliveryStage.PLANNING
            or binding.return_context is None
            or binding.return_context.target != DeliveryStage.PLANNING
            or context.outcome_id != request.outcome_id
            or request.task_id is not None
            or request.claim.worker_role != DeliveryWorkerRole.PLANNER
            or participant is not None
        ):
            _conflict("Planner handoff activation requires its exact task-less Planning claim")
        manager = self._workspace_manager
        if manager is None or type(lock) is not PublicationLock:
            _conflict("Planner handoff activation requires its exact passive workspace custody fence")
        coordination = manager.show(self._contract.change_id)
        handoff = coordination.builder_handoff
        if handoff is None or (
            handoff.settlement_id != context.settlement_id
            or handoff.original_task_id != context.original_task_id
            or handoff.original_writer.attempt_id != context.attempt_id
            or handoff.last_reviewed_commit != context.last_reviewed_commit
            or handoff.branch_head != context.branch_head
            or handoff.metadata_fingerprint != context.metadata_fingerprint
            or coordination.writer != handoff.original_writer.model_copy(update={"kind": "handoff"})
        ):
            _conflict("Planner handoff activation requires its exact retained workspace custody")

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
        self._require_workspace().validate_writer_head(
            self._contract.change_id,
            request.claim_id,
            request.result.completed_commit,
        )
        updated = binding.model_copy(update={"result_candidate": candidate, "output": candidate.output})
        self._replace(previous, _replace_binding(frontier, binding, updated))
        return candidate

    @staticmethod
    def _pending_transition_matches(
        pending_publication: DeliveryPendingStatePublication | None,
        previous: bytes,
        request_digest: str,
    ) -> bool:
        return (
            pending_publication is not None
            and pending_publication.frontier_digest == hashlib.sha256(previous).hexdigest()
            and pending_publication.transition_request_digest == request_digest
        )

    def transition(
        self, request: DeliveryTransition, *, retry_observed_at: datetime | str | None = None
    ) -> OutcomeAuthorityBinding:
        """Apply one worker-owned mechanical transition instruction."""
        frontier, previous = self._read()
        request_digest = hashlib.sha256(_model_content(request)).hexdigest()
        replay_result = self._planning_pause_replay_result(request, request_digest)
        if replay_result is not None:
            return replay_result
        _require_change_mutable(frontier, "transition")
        binding = _find_binding(frontier, request.outcome_id)
        pending_publication = self.pending_state_publication()
        if self._pending_transition_matches(pending_publication, previous, request_digest):
            return binding
        _require_claim(binding, request.claim_id)
        if self._workspace_manager is not None:
            self._workspace_manager.prepare_runtime_custody_guard(self._contract.change_id)
        updated = self._transitioned_binding(binding, request)
        if isinstance(request, AdvanceDelivery) and binding.builder_handoff_context is not None:
            updated = self._advanced_builder_handoff(binding, updated)
        replacement = _replace_binding(frontier, binding, updated)
        result_participants = ()
        if isinstance(request, AdvanceDelivery) and binding.stage == DeliveryStage.IMPLEMENTATION:
            replacement = _queue_promoted_result_checkpoint(replacement, frontier, binding, updated)
            candidate = binding.result_candidate
            if candidate is None:
                _conflict("result promotion requires original claim custody")
            result_participants = (
                TransactionParticipant(
                    self._target_root,
                    self._result_receipt_path(binding.outcome_id, candidate.digest),
                    _model_content(candidate),
                ),
            )
        if (
            isinstance(request, AdvanceDelivery)
            and binding.stage == DeliveryStage.PLANNING
            and binding.builder_handoff_context is not None
            and binding.builder_handoff_context.route == "same-outcome-planner"
        ):
            promotion_receipt = _DeliveryBuilderPlanPromotionReceipt.create(
                change_id=self._contract.change_id,
                source_binding=binding,
                result_binding=updated,
            )
            result_participants = (
                *result_participants,
                self._builder_plan_promotion_receipt_participant(promotion_receipt),
            )
        if isinstance(request, (AdvanceDelivery, BlockDelivery, ReturnDelivery)) and binding.active_claim is not None:
            paused = (
                isinstance(request, BlockDelivery)
                and binding.stage == DeliveryStage.PLANNING
                and request.request is not None
            )
            result_participants = (
                *result_participants,
                *self.retry_ledger().owner_result_participants(
                    binding.active_claim.attempt_id,
                    accepted=isinstance(request, AdvanceDelivery),
                    accepted_progress=not paused,
                    paused=paused,
                    now=retry_observed_at or datetime.now(UTC),
                    failure_code="worker-returned" if isinstance(request, ReturnDelivery) else "worker-blocked",
                ),
            )
        result_participants = (
            *result_participants,
            *self._planning_pause_replay_participants(request, binding, updated, request_digest),
        )
        if isinstance(request, AdvanceDelivery):
            result_participants = (
                *result_participants,
                *self._repair_owner_result_participants(
                    binding,
                    retry_observed_at=retry_observed_at or datetime.now(UTC),
                ),
            )
        self._replace(
            previous, replacement, transition_request_digest=request_digest, additional_participants=result_participants
        )
        return _find_binding(replacement, request.outcome_id)

    @staticmethod
    def _advanced_builder_handoff(
        binding: OutcomeAuthorityBinding,
        updated: OutcomeAuthorityBinding,
    ) -> OutcomeAuthorityBinding:
        context = binding.builder_handoff_context
        if context is None:
            return updated
        if binding.stage == DeliveryStage.PLANNING and context.route == "same-outcome-planner":
            if binding.candidate is None or updated.tasks != binding.candidate.tasks:
                _conflict("Planning handoff advance requires its exact published task-chain candidate")
            return updated.model_copy(
                update={"builder_handoff_context": context.model_copy(update={"route": "same-task"})}
            )
        if binding.stage == DeliveryStage.IMPLEMENTATION and context.route == "same-task":
            if binding.active_task_id != context.original_task_id:
                _conflict("Builder handoff can only be consumed by advancing its original task")
            return updated.model_copy(update={"builder_handoff_context": None})
        return _conflict("Builder handoff advance does not match its owning stage and route")

    def settle_planning_retry(
        self, envelope: DeliveryPlanningRetrySettlement, *, retry_observed_at: datetime | str | None = None
    ) -> OutcomeAuthorityBinding:
        """Settle one exact normally returned, completed-timeout, or ended-without-result Planner invocation."""
        envelope_type = type(envelope)
        if envelope_type not in {DeliveryPlanningRetrySettlement, DeliveryEnginePlanningSettlement}:
            _conflict("Planning retry settlement requires a typed completed-invocation envelope")
        try:
            envelope = envelope_type.model_validate_json(_model_content(envelope), strict=True)
        except TypeError, ValueError:
            _conflict("Planning retry settlement envelope is invalid")
        if envelope.change_id != self._contract.change_id:
            _conflict("Planning retry settlement belongs to another Change")

        frontier, previous = self._read()
        replay_result = self._planning_retry_settlement_replay_result(envelope)
        if replay_result is not None:
            return replay_result
        _require_change_mutable(frontier, "settle_planning_retry")
        binding = _find_binding(frontier, envelope.outcome_id)
        claim = binding.active_claim
        if binding.stage != DeliveryStage.PLANNING or claim is None:
            _conflict("Planning retry settlement requires an active Planner claim")
        if claim.claim_id != envelope.claim_id or claim.attempt_id != envelope.attempt_id:
            _conflict("Planning retry settlement does not match the active claim and attempt")
        if claim.worker_role != DeliveryWorkerRole.PLANNER or claim.task_id is not None:
            _conflict("Planning retry settlement cannot accept a Builder task")

        if envelope.disposition == "normal-return":
            request = envelope.request
            if request is None:
                _conflict("normal Planner retry settlement requires its unchanged RetryDelivery")
            self._validate_retry_identity(binding, request, claim)
            failure_code = request.failure_code
        else:
            failure_code = REQUESTLESS_WORKER_SETTLEMENT_FAILURE_CODES[envelope.disposition]

        result = binding.model_copy(
            update={
                "active_claim": None,
                "output": None,
                "candidate": None,
                "recovery_attention": None,
                "retry_diagnostic": None,
            }
        )
        receipt = _DeliveryPlanningRetrySettlementReceipt(envelope=envelope, result=result)
        participants = (
            *self.retry_ledger().owner_result_participants(
                claim.attempt_id,
                accepted=False,
                accepted_progress=True,
                failure_code=failure_code,
                now=retry_observed_at or datetime.now(UTC),
            ),
            self._planning_retry_settlement_participant(receipt),
        )
        self._replace(
            previous,
            _replace_binding(frontier, binding, result),
            transition_request_digest=hashlib.sha256(_model_content(envelope)).hexdigest(),
            additional_participants=participants,
        )
        return result

    def settle_builder_invocation(
        self,
        envelope: DeliveryBuilderInvocationSettlement,
        *,
        retry_observed_at: datetime | str | None = None,
    ) -> OutcomeAuthorityBinding:
        """Settle one exact Builder invocation without rewriting its registered worktree."""
        envelope_type = type(envelope)
        if envelope_type not in {DeliveryBuilderInvocationSettlement, DeliveryEngineBuilderSettlement}:
            _conflict("Builder invocation settlement requires a typed completed-invocation envelope")
        try:
            envelope = envelope_type.model_validate_json(_model_content(envelope), strict=True)
        except TypeError, ValueError:
            _conflict("Builder invocation settlement envelope is invalid")
        if envelope.change_id != self._contract.change_id:
            _conflict("Builder invocation settlement belongs to another Change")
        manager = self._require_workspace()
        with manager._coordinator.publication_lock(envelope.change_id) as lock:  # noqa: SLF001
            frontier, previous = self._read()
            replay_result = self._builder_invocation_settlement_replay_result(envelope)
            if replay_result is not None:
                return replay_result
            _require_change_mutable(frontier, "settle_builder_invocation")
            binding = _find_binding(frontier, envelope.outcome_id)
            claim, prepared = self._prepare_builder_invocation_handoff(binding, envelope, manager, lock)
            ledger, episode = self._builder_invocation_retry_episode(envelope)
            settlement_id = hashlib.sha256(_model_content(envelope)).hexdigest()
            original_task = next((task for task in binding.tasks if task.task_id == envelope.task_id), None)
            if original_task is None:
                _reference("Builder invocation settlement task authority is absent")
            context = DeliveryBuilderHandoffContext(
                settlement_id=settlement_id,
                original_task_id=envelope.task_id,
                outcome_id=envelope.outcome_id,
                attempt_id=envelope.attempt_id,
                last_reviewed_commit=envelope.expected_last_reviewed_commit,
                branch_head=prepared.metadata.branch_head,
                metadata_fingerprint=prepared.metadata.fingerprint,
                route=(
                    "same-outcome-design"
                    if isinstance(envelope.request, ReturnDelivery) and envelope.request.target == DeliveryStage.DESIGN
                    else "same-outcome-planner"
                    if isinstance(envelope.request, ReturnDelivery)
                    else "same-task"
                ),
                original_task_commitment_ids=original_task.commitment_ids,
                original_task_maintained_surfaces=original_task.maintained_surfaces,
            )
            result, paused, failure_code = self._builder_invocation_settled_binding(
                binding, envelope, context, episode, ledger
            )
            receipt = _DeliveryBuilderInvocationSettlementReceipt(
                settlement_id=settlement_id,
                envelope=envelope,
                handoff_context=context,
                result=result,
            )
            participants = (
                *ledger.owner_result_participants(
                    claim.attempt_id,
                    accepted=False,
                    accepted_progress=not paused,
                    paused=paused,
                    failure_code=failure_code,
                    now=retry_observed_at or datetime.now(UTC),
                ),
                self._builder_invocation_settlement_participant(receipt),
                prepared.participant,
            )
            replacement = _replace_binding(frontier, binding, result)
            portable = not any(item.active_claim is not None for item in replacement.bindings)
            portable = portable and not any(item.builder_handoff_context is not None for item in replacement.bindings)
            portable = portable and replacement.integration_repair_claim is None
            self._replace_content(
                previous,
                _model_content(replacement),
                record_pending_publication=portable,
                transition_request_digest=settlement_id,
                additional_participants=participants,
            )
            return result

    def _transitioned_binding(
        self,
        binding: OutcomeAuthorityBinding,
        request: DeliveryTransition,
    ) -> OutcomeAuthorityBinding:
        if isinstance(request, AdvanceDelivery):
            return self._advance(binding, request)
        if isinstance(request, RetryDelivery):
            return self._retry(binding, request)
        if isinstance(request, ReturnDelivery):
            return self._return(binding, request)
        return self._block(binding, request)

    def _repair_owner_result_participants(
        self,
        binding: OutcomeAuthorityBinding,
        *,
        retry_observed_at: datetime | str,
    ) -> tuple[TransactionParticipant, ...]:
        """Publish exact completed-repair accounting only with its accepted task result."""
        if binding.stage != DeliveryStage.IMPLEMENTATION or binding.active_claim is None:
            return ()
        task_id = binding.active_claim.task_id
        candidate = binding.result_candidate
        if task_id is None or candidate is None or candidate.result.task_id != task_id:
            return ()
        ledger = self.retry_ledger()
        bindings = tuple(
            item
            for item in ledger.repair_bindings()
            if item.outcome_id == binding.outcome_id and item.repair_task_id == task_id
        )
        if not bindings:
            return ()
        if len(bindings) != 1:
            msg = "completed-outcome repair has multiple retry bindings"
            raise DeliveryRuntimeConflictError(msg)
        repair_binding = bindings[0]
        receipt = self._completed_outcome_repair_receipt(binding.outcome_id, task_id)
        if (
            receipt is None
            or receipt.episode_id != repair_binding.episode_id
            or receipt.attempt_id != repair_binding.repair_attempt_id
            or receipt.outcome_id != repair_binding.outcome_id
            or receipt.repair_task_id != repair_binding.repair_task_id
        ):
            msg = "completed-outcome repair receipt identity is unavailable"
            raise DeliveryRuntimeReferenceError(msg)
        return ledger.owner_result_participants(
            receipt.attempt_id,
            accepted=True,
            accepted_progress=False,
            repair_outcome_id=receipt.outcome_id,
            repair_task_id=receipt.repair_task_id,
            completed_commit=candidate.result.completed_commit,
            now=retry_observed_at,
        )

    def _completed_outcome_repair_receipt(
        self,
        outcome_id: str,
        repair_task_id: str,
    ) -> CompletedOutcomeRepairReceipt | None:
        """Find one validated repair receipt without deriving authority from a task name."""
        base = self._target_root / "changes" / self._contract.change_id / "recovery-receipts"
        try:
            entries = tuple(sorted(base.iterdir(), key=lambda item: item.name))
        except FileNotFoundError:
            return None
        except OSError as exc:
            msg = "completed-outcome repair receipt inventory is unavailable"
            raise DeliveryRuntimeReferenceError(msg) from exc
        if len(entries) > _MAX_COMPLETED_REPAIR_RECEIPTS:
            msg = "completed-outcome repair receipt inventory exceeds its bound"
            raise DeliveryRuntimeReferenceError(msg)
        matches: list[CompletedOutcomeRepairReceipt] = []
        for entry in entries:
            receipt = self._completed_outcome_repair_receipt_entry(entry, outcome_id, repair_task_id)
            if receipt is not None:
                matches.append(receipt)
        if len(matches) > 1:
            msg = "completed-outcome repair has multiple matching receipts"
            raise DeliveryRuntimeConflictError(msg)
        return matches[0] if matches else None

    def _completed_outcome_repair_receipt_entry(
        self,
        entry: Path,
        outcome_id: str,
        repair_task_id: str,
    ) -> CompletedOutcomeRepairReceipt | None:
        try:
            entry_mode = entry.lstat().st_mode
        except OSError:
            entry_mode = None
        if entry_mode is None or not stat.S_ISDIR(entry_mode):
            return None
        if len(entry.name) != _SHA256_HEX_LENGTH or any(
            character not in "0123456789abcdef" for character in entry.name
        ):
            return None
        try:
            content = read_record(
                self._target_root,
                journal_path(self._contract.change_id, entry.name, "receipt"),
            )
        except FileNotFoundError:
            return None
        except (OSError, DeliveryWorkerExclusionRequiredError) as exc:
            msg = "completed-outcome repair receipt is unavailable"
            raise DeliveryRuntimeReferenceError(msg) from exc
        try:
            receipt = CompletedOutcomeRepairReceipt.model_validate_json(content)
        except (TypeError, ValueError) as exc:
            try:
                payload = json.loads(content)
            except TypeError, ValueError, json.JSONDecodeError:
                payload = None
            if isinstance(payload, dict) and "repair_task_id" in payload:
                msg = "completed-outcome repair receipt is malformed"
                raise DeliveryRuntimeReferenceError(msg) from exc
            return None
        if (
            receipt.change_id == self._contract.change_id
            and receipt.outcome_id == outcome_id
            and receipt.repair_task_id == repair_task_id
        ):
            return receipt
        return None

    def require_result_replay(self, outcome_id: str, claim_id: str, result: DeliveryTaskResult) -> None:
        """Require immutable original claim provenance before replaying a promoted result."""
        binding = self.show_binding(outcome_id)
        if result not in binding.results:
            _conflict("result replay requires current promoted authority")
        digest = hashlib.sha256(_model_content(result)).hexdigest()
        path = self._target_root / self._result_receipt_path(binding.outcome_id, digest)
        try:
            receipt = DeliveryResultCandidate.model_validate_json(path.read_bytes())
        except (OSError, ValueError) as exc:
            _reference("original result claim receipt is unavailable", exc)
        if receipt != DeliveryResultCandidate(
            candidate_id=f"result-{digest}", claim_id=claim_id, digest=digest, result=result
        ):
            _conflict("submitted result replay does not match original claim custody")

    def _result_receipt_path(self, outcome_id: str, digest: str) -> Path:
        return (
            self._frontier_path.parent.relative_to(self._target_root)
            / "result-receipts"
            / outcome_id
            / f"{digest}.json"
        )

    def _planning_pause_replay_result(
        self,
        request: DeliveryTransition,
        request_digest: str,
    ) -> OutcomeAuthorityBinding | None:
        if not isinstance(request, BlockDelivery) or request.request is None:
            return None
        relative_path = self._planning_pause_replay_path(request.outcome_id, request_digest)
        path = self._target_root / relative_path
        try:
            content = path.read_bytes()
        except FileNotFoundError:
            return None
        except OSError as exc:
            _reference("Planning pause replay receipt is unavailable", exc)
        try:
            receipt = _DeliveryPlanningPauseReplay.model_validate_json(content, strict=False)
        except (TypeError, ValueError) as exc:
            _reference("Planning pause replay receipt is invalid", exc)
        if (
            receipt.change_id != self._contract.change_id
            or receipt.outcome_id != request.outcome_id
            or receipt.claim_id != request.claim_id
            or receipt.request_digest != request_digest
            or receipt.request != request
        ):
            _reference("Planning pause replay receipt does not match its original request")
        return receipt.result

    def _planning_retry_settlement_replay_result(
        self,
        envelope: DeliveryPlanningRetrySettlement,
    ) -> OutcomeAuthorityBinding | None:
        path = self._target_root / self._planning_retry_settlement_path(envelope)
        try:
            content = path.read_bytes()
        except FileNotFoundError:
            return None
        except OSError as exc:
            _reference("Planning retry settlement receipt is unavailable", exc)
        try:
            receipt = _DeliveryPlanningRetrySettlementReceipt.model_validate_json(content, strict=True)
        except (TypeError, ValueError) as exc:
            _reference("Planning retry settlement receipt is invalid", exc)
        if receipt.envelope != envelope:
            _conflict("Planning retry settlement conflicts with the immutable attempt receipt")
        return receipt.result

    def _planning_retry_settlement_participant(
        self,
        receipt: _DeliveryPlanningRetrySettlementReceipt,
    ) -> TransactionParticipant:
        return TransactionParticipant(
            self._target_root,
            self._planning_retry_settlement_path(receipt.envelope),
            _model_content(receipt),
        )

    def _planning_retry_settlement_path(self, envelope: DeliveryPlanningRetrySettlement) -> Path:
        attempt_digest = hashlib.sha256(envelope.attempt_id.encode("utf-8")).hexdigest()
        return (
            self._frontier_path.parent.relative_to(self._target_root)
            / "planning-retry-receipts"
            / envelope.outcome_id
            / f"{attempt_digest}.json"
        )

    def engine_worker_settlement_replay(
        self,
        outcome_id: str,
        attempt_id: str,
        claim_id: str,
        disposition: EngineWorkerDisposition,
    ) -> OutcomeAuthorityBinding | None:
        """Return the immutable result of one exact engine-settled worker attempt, if any."""
        if re.fullmatch(r"OUT-[0-9]{3}", outcome_id) is None:
            return None
        attempt_digest = hashlib.sha256(attempt_id.encode("utf-8")).hexdigest()
        receipts: tuple[tuple[Path, type[_DeliveryModel]], ...] = (
            (
                self._frontier_path.parent / "planning-retry-receipts" / outcome_id / f"{attempt_digest}.json",
                _DeliveryPlanningRetrySettlementReceipt,
            ),
            (
                self._target_root / self._builder_invocation_settlement_path(attempt_id),
                _DeliveryBuilderInvocationSettlementReceipt,
            ),
        )
        for path, receipt_type in receipts:
            try:
                content = path.read_bytes()
            except FileNotFoundError:
                continue
            except OSError as exc:
                _reference("worker settlement receipt is unavailable", exc)
            try:
                receipt = receipt_type.model_validate_json(content, strict=True)
            except (TypeError, ValueError) as exc:
                _reference("worker settlement receipt is invalid", exc)
            envelope = receipt.envelope
            if (
                isinstance(envelope, (DeliveryEnginePlanningSettlement, DeliveryEngineBuilderSettlement))
                and envelope.outcome_id == outcome_id
                and envelope.claim_id == claim_id
                and envelope.disposition == disposition
            ):
                return receipt.result
            _conflict("worker attempt is already settled with different authority")
        return None

    def _prepare_builder_invocation_handoff(
        self,
        binding: OutcomeAuthorityBinding,
        envelope: DeliveryBuilderInvocationSettlement,
        manager: ChangeWorkspaceManager,
        lock: PublicationLock,
    ) -> tuple[DeliveryActiveClaim, PreparedBuilderHandoff]:
        claim = binding.active_claim
        if (
            binding.stage != DeliveryStage.IMPLEMENTATION
            or claim is None
            or claim.worker_role != DeliveryWorkerRole.BUILDER
            or claim.claim_id != envelope.claim_id
            or claim.attempt_id != envelope.attempt_id
            or claim.task_id != envelope.task_id
            or not any(task.task_id == envelope.task_id for task in binding.tasks)
        ):
            _conflict("Builder invocation settlement does not match the active task claim")
        coordination = manager.show(envelope.change_id)
        writer = coordination.writer
        if (
            writer is None
            or writer.kind != "build"
            or writer.claim_id != claim.claim_id
            or writer.attempt_id != claim.attempt_id
            or coordination.last_reviewed_commit != envelope.expected_last_reviewed_commit
        ):
            _conflict("Builder invocation settlement does not match exact Change workspace custody")
        settlement_id = hashlib.sha256(_model_content(envelope)).hexdigest()
        prepared = manager.prepare_builder_handoff(
            envelope.change_id,
            writer,
            settlement_id,
            envelope.task_id,
            lock,
        )
        metadata = prepared.metadata
        if (
            metadata.change_id != envelope.change_id
            or metadata.branch != coordination.branch
            or metadata.worktree_path != coordination.worktree_path
            or metadata.last_reviewed_commit != envelope.expected_last_reviewed_commit
            or metadata.registration.path != metadata.worktree_path
            or metadata.registration.branch != metadata.branch
            or metadata.registration.head != metadata.branch_head
        ):
            _conflict("Builder handoff metadata does not match its registered branch and reviewed boundary")
        request = envelope.request
        if isinstance(request, RetryDelivery) and request.abandoned_commit != metadata.branch_head:
            _conflict("Builder retry commit does not match the registered branch head")
        if isinstance(request, BlockDelivery) and request.resume_commit != metadata.branch_head:
            _conflict("Builder block commit does not match the registered branch head")
        if isinstance(request, ReturnDelivery) and request.preserved_commit != metadata.branch_head:
            _conflict("Builder return commit does not match the registered branch head")
        self._validate_builder_result_candidate(binding, claim, envelope.task_id)
        return claim, prepared

    @staticmethod
    def _validate_builder_result_candidate(
        binding: OutcomeAuthorityBinding,
        claim: DeliveryActiveClaim,
        task_id: str,
    ) -> None:
        candidate = binding.result_candidate
        if candidate is None:
            return
        if candidate.claim_id != claim.claim_id or candidate.result.task_id != task_id:
            _conflict("published Builder result candidate does not match its active task claim")
        accepted = next((result for result in binding.results if result.task_id == candidate.result.task_id), None)
        if accepted is not None and accepted != candidate.result:
            _conflict("published Builder result candidate conflicts with its accepted result")

    def _builder_invocation_retry_episode(
        self,
        envelope: DeliveryBuilderInvocationSettlement,
    ) -> tuple[RetryLedger, RetryEpisodeSummary]:
        ledger = self.retry_ledger()
        episode = ledger.episode_for_attempt(envelope.attempt_id)
        if episode is None:
            _conflict("Builder invocation settlement requires its exact reserved retry episode")
        key = episode.key
        reviewed_head_matches = key.exact_head == envelope.expected_last_reviewed_commit or any(
            alias.alias_kind == "commit" and alias.value == envelope.expected_last_reviewed_commit
            for alias in episode.aliases
        )
        if (
            episode.failure_class != RetryFailureClass.MECHANICAL
            or key.change_id != envelope.change_id
            or key.action_kind != "builder-claim"
            or not reviewed_head_matches
            or key.contract_digest != self._authority_digest
            or key.outcome_id != envelope.outcome_id
            or key.task_lineage != envelope.task_id
            or key.procedure_class != DeliveryWorkerRole.BUILDER.value
            or envelope.attempt_id not in episode.attempt_ids
        ):
            _conflict("Builder invocation settlement retry episode does not match its exact task authority")
        owner_result_path = (
            self._target_root
            / "changes"
            / envelope.change_id
            / "retry-ledger"
            / "owner-results"
            / f"{envelope.attempt_id}.json"
        )
        if owner_result_path.exists():
            _conflict("Builder invocation settlement already has an owner result without its exact receipt")
        return ledger, episode

    def _builder_invocation_settled_binding(
        self,
        binding: OutcomeAuthorityBinding,
        envelope: DeliveryBuilderInvocationSettlement,
        context: DeliveryBuilderHandoffContext,
        episode: RetryEpisodeSummary,
        ledger: RetryLedger,
    ) -> tuple[OutcomeAuthorityBinding, bool, str]:
        request = envelope.request
        paused = isinstance(request, BlockDelivery)
        requestless_code = REQUESTLESS_WORKER_SETTLEMENT_FAILURE_CODES.get(envelope.disposition)
        failure_code = (
            requestless_code
            if requestless_code is not None
            else "worker-blocked"
            if paused
            else "worker-returned"
            if isinstance(request, ReturnDelivery)
            else request.failure_code
        )
        exhausted = not paused and episode.total_attempts >= ledger.mechanical_repairs + 1
        if requestless_code is not None or isinstance(request, RetryDelivery):
            result = self._builder_retry_settled_binding(binding, context, envelope, exhausted=exhausted)
        elif isinstance(request, BlockDelivery):
            result = self._builder_pause_settled_binding(binding, context, request)
        elif isinstance(request, ReturnDelivery):
            result = self._builder_return_settled_binding(binding, context, request, exhausted=exhausted)
        else:
            _conflict("Builder invocation settlement has no supported completed disposition")
        return result, paused, failure_code

    @staticmethod
    def _builder_retry_settled_binding(
        binding: OutcomeAuthorityBinding,
        context: DeliveryBuilderHandoffContext,
        envelope: DeliveryBuilderInvocationSettlement,
        *,
        exhausted: bool,
    ) -> OutcomeAuthorityBinding:
        updates = {
            "active_claim": None,
            "output": None,
            "candidate": None,
            "result_candidate": None,
            "return_context": None,
            "builder_handoff_context": context,
            "recovery_attention": None,
            "retry_diagnostic": None,
            "block": None,
        }
        if exhausted:
            updates["block"] = DeliveryBlock(
                block_id=f"builder-attempt-limit-{context.settlement_id}",
                reason="The Builder retry episode reached its three-attempt limit.",
                unblock_condition="Use a supported operator disposition without resetting this retry episode.",
                expected_evidence=("An exact operator disposition for the retained Builder task.",),
                locators=(envelope.task_id,),
            )
        return binding.model_copy(update=updates)

    @staticmethod
    def _builder_pause_settled_binding(
        binding: OutcomeAuthorityBinding,
        context: DeliveryBuilderHandoffContext,
        request: BlockDelivery,
    ) -> OutcomeAuthorityBinding:
        delivery_request = request.request
        if delivery_request is None or any(
            existing.request_id == delivery_request.request_id for existing in binding.requests
        ):
            _conflict("Builder pause request is absent or already active")
        block = DeliveryBlock(
            block_id=request.block_id,
            reason=request.reason,
            unblock_condition=request.unblock_condition,
            expected_evidence=request.expected_evidence,
            locators=request.locators,
            request_id=delivery_request.request_id,
            resume_commit=request.resume_commit,
        )
        return binding.model_copy(
            update={
                "active_claim": None,
                "builder_handoff_context": context,
                "output": None,
                "candidate": None,
                "result_candidate": None,
                "recovery_attention": None,
                "retry_diagnostic": None,
                "return_context": None,
                "block": block,
                "requests": (*binding.requests, delivery_request),
            }
        )

    @staticmethod
    def _builder_return_settled_binding(
        binding: OutcomeAuthorityBinding,
        context: DeliveryBuilderHandoffContext,
        request: ReturnDelivery,
        *,
        exhausted: bool,
    ) -> OutcomeAuthorityBinding:
        if request.target not in {DeliveryStage.PLANNING, DeliveryStage.DESIGN}:
            _conflict("Builder return target has no supported workspace owner route")
        block = (
            DeliveryBlock(
                block_id=f"builder-{request.target.value}-route-{context.settlement_id}",
                reason="The Builder retry episode reached its three-attempt limit.",
                unblock_condition="The retry episode is eligible to continue.",
                expected_evidence=("A retry episode below its attempt limit.",),
                locators=request.locators,
            )
            if exhausted
            else None
        )
        return binding.model_copy(
            update={
                "stage": request.target,
                "active_claim": None,
                "output": None,
                "candidate": None,
                "result_candidate": None,
                "builder_handoff_context": context,
                "recovery_attention": None,
                "retry_diagnostic": None,
                "return_context": DeliveryReturnContext(
                    target=request.target,
                    reason=request.reason,
                    locators=request.locators,
                    preserved_commit=request.preserved_commit,
                    completed_boundary=context.last_reviewed_commit,
                ),
                "block": block,
            }
        )

    def _builder_invocation_settlement_replay_result(
        self,
        envelope: DeliveryBuilderInvocationSettlement,
    ) -> OutcomeAuthorityBinding | None:
        path = self._target_root / self._builder_invocation_settlement_path(envelope.attempt_id)
        try:
            content = path.read_bytes()
        except FileNotFoundError:
            return None
        except OSError as exc:
            _reference("Builder invocation settlement receipt is unavailable", exc)
        try:
            receipt = _DeliveryBuilderInvocationSettlementReceipt.model_validate_json(content, strict=True)
        except (TypeError, ValueError) as exc:
            _reference("Builder invocation settlement receipt is invalid", exc)
        if receipt.envelope != envelope:
            _conflict("Builder invocation settlement conflicts with the immutable attempt receipt")
        return receipt.result

    def _builder_invocation_settlement_participant(
        self,
        receipt: _DeliveryBuilderInvocationSettlementReceipt,
    ) -> TransactionParticipant:
        return TransactionParticipant(
            self._target_root,
            self._builder_invocation_settlement_path(receipt.envelope.attempt_id),
            _model_content(receipt),
        )

    def _builder_plan_promotion_receipt_participant(
        self,
        receipt: _DeliveryBuilderPlanPromotionReceipt,
    ) -> TransactionParticipant:
        return TransactionParticipant(
            self._target_root,
            self._builder_plan_promotion_receipt_path(receipt.settlement_id),
            _model_content(receipt),
        )

    def _builder_plan_promotion_receipt_path(self, settlement_id: str) -> Path:
        return (
            self._frontier_path.parent.relative_to(self._target_root)
            / "builder-plan-promotion-receipts"
            / f"{settlement_id}.json"
        )

    def _builder_invocation_settlement_path(self, attempt_id: str) -> Path:
        attempt_digest = hashlib.sha256(attempt_id.encode("utf-8")).hexdigest()
        return (
            self._frontier_path.parent.relative_to(self._target_root)
            / "builder-invocation-receipts"
            / f"{attempt_digest}.json"
        )

    def _builder_request_resolution_receipt_participant(
        self,
        binding: OutcomeAuthorityBinding,
        request: DeliveryRequest,
        resolved_request: DeliveryRequest,
        updated_block: DeliveryBlock,
    ) -> TransactionParticipant | None:
        context = binding.builder_handoff_context
        block = binding.block
        if context is None or context.route != "same-task":
            return None
        if (
            binding.stage != DeliveryStage.IMPLEMENTATION
            or context.original_task_id not in binding.task_ids
            or block is None
            or block.request_id != request.request_id
        ):
            return None

        settlement_receipt = self._read_builder_invocation_settlement_receipt(context)
        original_block = settlement_receipt.envelope.request
        if not isinstance(original_block, BlockDelivery) or original_block.request is None:
            _conflict("Builder request resolution does not match an exact same-task pause")
        expected_block = DeliveryBlock(
            block_id=original_block.block_id,
            reason=original_block.reason,
            unblock_condition=original_block.unblock_condition,
            expected_evidence=original_block.expected_evidence,
            locators=original_block.locators,
            request_id=original_block.request.request_id,
            resume_commit=original_block.resume_commit,
        )
        if not (
            settlement_receipt.handoff_context == context
            and settlement_receipt.result == binding
            and settlement_receipt.envelope.change_id == self._contract.change_id
            and settlement_receipt.envelope.outcome_id == binding.outcome_id
            and settlement_receipt.envelope.task_id == context.original_task_id
            and original_block.request == request
            and expected_block == block
            and request.outcome_id == binding.outcome_id
        ):
            _conflict("Builder request resolution does not match its exact same-task pause")

        receipt = _DeliveryBuilderRequestResolutionReceipt(
            change_id=self._contract.change_id,
            outcome_id=binding.outcome_id,
            request_id=request.request_id,
            settlement_id=context.settlement_id,
            builder_handoff_context=context,
            resolved_request=resolved_request,
            updated_block=updated_block,
        )
        receipt_path = _builder_request_resolution_receipt_path(
            self._target_root,
            self._contract.change_id,
            context,
        )
        receipt_directory = receipt_path.parent
        if any(
            path.is_symlink()
            for path in (self._target_root / "changes", self._frontier_path.parent, receipt_directory, receipt_path)
        ):
            _reference("Builder request resolution receipt path is unsafe")
        return TransactionParticipant(
            self._target_root,
            receipt_path.relative_to(self._target_root),
            _model_content(receipt),
        )

    def _read_builder_invocation_settlement_receipt(
        self,
        context: DeliveryBuilderHandoffContext,
    ) -> _DeliveryBuilderInvocationSettlementReceipt:
        settlement_path = self._target_root / self._builder_invocation_settlement_path(context.attempt_id)
        settlement_directory = settlement_path.parent
        if any(
            path.is_symlink()
            for path in (
                self._target_root / "changes",
                self._frontier_path.parent,
                settlement_directory,
                settlement_path,
            )
        ):
            _reference("Builder invocation settlement receipt path is unsafe")
        try:
            settlement_content = settlement_path.read_bytes()
        except OSError as exc:
            _reference("Builder invocation settlement receipt is unavailable", exc)
        try:
            receipt = _DeliveryBuilderInvocationSettlementReceipt.model_validate_json(
                settlement_content,
                strict=True,
            )
        except (TypeError, ValueError) as exc:
            _reference("Builder invocation settlement receipt is invalid", exc)
        return receipt

    def _planner_handoff_pause_return_context(
        self,
        binding: OutcomeAuthorityBinding,
    ) -> DeliveryReturnContext | None:
        """Return the retained Planning return context for one exact Planner pause on a Builder return."""
        context = binding.builder_handoff_context
        block = binding.block
        if (
            context is None
            or context.route != "same-outcome-planner"
            or binding.stage != DeliveryStage.PLANNING
            or binding.active_claim is not None
            or block is None
        ):
            return None
        settlement = self._read_builder_invocation_settlement_receipt(context)
        returned = settlement.envelope.request
        if not (
            isinstance(returned, ReturnDelivery)
            and returned.target == DeliveryStage.PLANNING
            and settlement.handoff_context == context
            and settlement.envelope.change_id == self._contract.change_id
            and settlement.result.block is None
            and settlement.result.return_context is not None
            and settlement.result.tasks == binding.tasks
            and settlement.result.results == binding.results
        ):
            return None
        if block.request_id is not None and not self._planning_pause_receipt_matches(binding):
            return None
        return settlement.result.return_context

    def _planning_pause_receipt_matches(self, binding: OutcomeAuthorityBinding) -> bool:
        directory = self._target_root / self._planning_pause_replay_path(binding.outcome_id, "0" * 64).parent
        if any(
            path.is_symlink()
            for path in (self._target_root / "changes", self._frontier_path.parent, directory.parent, directory)
        ):
            _reference("Planning pause replay receipt path is unsafe")
        if not directory.is_dir():
            return False
        for path in sorted(directory.glob("*.json")):
            if path.is_symlink():
                _reference("Planning pause replay receipt path is unsafe")
            try:
                receipt = _DeliveryPlanningPauseReplay.model_validate_json(path.read_bytes(), strict=False)
            except (OSError, TypeError, ValueError) as exc:
                _reference("Planning pause replay receipt is invalid", exc)
            if (
                receipt.change_id == self._contract.change_id
                and path.name == f"{receipt.request_digest}.json"
                and receipt.result == binding
            ):
                return True
        return False

    def _require_recorded_builder_handoff_change_intent(self, frontier: DeliveryFrontier) -> None:
        for binding in frontier.bindings:
            context = binding.builder_handoff_context
            if context is None:
                continue
            receipts = _read_builder_handoff_change_intent_receipts(
                self._target_root,
                self._contract.change_id,
                context,
            )
            if not receipts or (
                receipts[-1].after_frontier.change_deferral != frontier.change_deferral
                or receipts[-1].after_frontier.change_abandonment != frontier.change_abandonment
            ):
                _conflict("retained Builder handoff lifecycle intent has no matching receipt")

    def _builder_handoff_change_intent_participants(
        self,
        before: DeliveryFrontier,
        after: DeliveryFrontier,
        action: Literal["defer", "resume", "abandon"],
        *,
        deferral: DeliveryChangeDeferral | None = None,
        abandonment: DeliveryChangeAbandonment | None = None,
    ) -> tuple[TransactionParticipant | ReplacementTransactionParticipant, ...]:
        handoffs = tuple(binding for binding in before.bindings if binding.builder_handoff_context is not None)
        if not handoffs:
            return ()
        if (
            any(binding.active_claim is not None for binding in before.bindings)
            or before.integration_repair_claim is not None
        ):
            _conflict("Builder handoff lifecycle intent cannot overlap an active mutation claim")

        mutation = _BuilderHandoffChangeIntentMutation(before, after, action, deferral, abandonment)
        participants: list[TransactionParticipant | ReplacementTransactionParticipant] = []
        for binding in handoffs:
            context = binding.builder_handoff_context
            if context is None:
                continue
            receipts = self._builder_handoff_change_intent_chain(before, context, action)
            receipt, head = self._new_builder_handoff_change_intent_receipt(
                binding,
                mutation,
                receipts,
            )
            participants.extend(self._builder_handoff_change_intent_storage(receipt, head, context, receipts))
        return tuple(participants)

    def _builder_handoff_change_intent_chain(
        self,
        before: DeliveryFrontier,
        context: DeliveryBuilderHandoffContext,
        action: Literal["defer", "resume", "abandon"],
    ) -> tuple[_DeliveryBuilderHandoffChangeIntentReceipt, ...]:
        receipts = _read_builder_handoff_change_intent_receipts(self._target_root, self._contract.change_id, context)
        if receipts:
            latest = receipts[-1].after_frontier
            if (
                latest.change_deferral != before.change_deferral
                or latest.change_abandonment != before.change_abandonment
            ):
                _conflict("Builder handoff lifecycle flags do not match the recorded receipt chain")
        elif before.change_deferral is not None or before.change_abandonment is not None:
            _conflict("Builder handoff lifecycle flags are missing their receipt chain")
        if len(receipts) > _MAX_BUILDER_HANDOFF_CHANGE_INTENTS or (
            len(receipts) == _MAX_BUILDER_HANDOFF_CHANGE_INTENTS and action != "abandon"
        ):
            _conflict("Builder handoff change-intent receipt chain is exhausted")
        return receipts

    def _new_builder_handoff_change_intent_receipt(
        self,
        binding: OutcomeAuthorityBinding,
        mutation: _BuilderHandoffChangeIntentMutation,
        receipts: tuple[_DeliveryBuilderHandoffChangeIntentReceipt, ...],
    ) -> tuple[_DeliveryBuilderHandoffChangeIntentReceipt, _DeliveryBuilderHandoffChangeIntentHead]:
        context = binding.builder_handoff_context
        if context is None:
            _conflict("Builder handoff change-intent receipt requires retained context")
        try:
            receipt = _DeliveryBuilderHandoffChangeIntentReceipt.create(
                action=mutation.action,
                change_id=self._contract.change_id,
                outcome_id=binding.outcome_id,
                context=context,
                sequence=len(receipts) + 1,
                previous_receipt_id=receipts[-1].receipt_id if receipts else None,
                before_frontier=mutation.before,
                after_frontier=mutation.after,
                deferral=mutation.deferral,
                abandonment=mutation.abandonment,
            )
            head = _DeliveryBuilderHandoffChangeIntentHead(
                change_id=self._contract.change_id,
                outcome_id=binding.outcome_id,
                settlement_id=context.settlement_id,
                builder_handoff_context=context,
                latest_receipt_id=receipt.receipt_id,
                sequence=receipt.sequence,
            )
        except TypeError, ValueError:
            _conflict("Builder handoff lifecycle intent cannot prove an exact supported frontier delta")
        return receipt, head

    def _builder_handoff_change_intent_storage(
        self,
        receipt: _DeliveryBuilderHandoffChangeIntentReceipt,
        head: _DeliveryBuilderHandoffChangeIntentHead,
        context: DeliveryBuilderHandoffContext,
        receipts: tuple[_DeliveryBuilderHandoffChangeIntentReceipt, ...],
    ) -> tuple[TransactionParticipant | ReplacementTransactionParticipant, ...]:
        directory = _builder_handoff_change_intent_directory(self._target_root, self._contract.change_id, context)
        receipt_path = directory / f"{receipt.receipt_id}.json"
        head_path = _builder_handoff_change_intent_head_path(self._target_root, self._contract.change_id, context)
        if any(
            path.is_symlink()
            for path in (
                self._target_root / "changes",
                self._frontier_path.parent,
                directory,
                receipt_path,
                head_path,
            )
        ):
            _reference("Builder handoff change-intent receipt path is unsafe")
        if receipt_path.exists():
            _reference("Builder handoff change-intent receipt path already exists")
        return (
            TransactionParticipant(
                self._target_root,
                receipt_path.relative_to(self._target_root),
                _model_content(receipt),
            ),
            self._builder_handoff_change_intent_head_participant(head_path, head, context, receipts),
        )

    def _builder_handoff_change_intent_head_participant(
        self,
        head_path: Path,
        head: _DeliveryBuilderHandoffChangeIntentHead,
        context: DeliveryBuilderHandoffContext,
        receipts: tuple[_DeliveryBuilderHandoffChangeIntentReceipt, ...],
    ) -> TransactionParticipant | ReplacementTransactionParticipant:
        head_content = _model_content(head)
        if not head_path.exists():
            if receipts:
                _reference("Builder handoff change-intent head is unavailable")
            return TransactionParticipant(
                self._target_root,
                head_path.relative_to(self._target_root),
                head_content,
            )
        try:
            previous_head_content = head_path.read_bytes()
            previous_head = _DeliveryBuilderHandoffChangeIntentHead.model_validate_json(
                previous_head_content,
                strict=True,
            )
        except (OSError, TypeError, ValueError) as exc:
            _reference("Builder handoff change-intent head is invalid", exc)
        if not receipts or (
            previous_head_content != _model_content(previous_head)
            or previous_head.change_id != self._contract.change_id
            or previous_head.outcome_id != head.outcome_id
            or previous_head.builder_handoff_context != context
            or previous_head.latest_receipt_id != receipts[-1].receipt_id
            or previous_head.sequence != len(receipts)
        ):
            _reference("Builder handoff change-intent head does not match its receipt chain")
        return ReplacementTransactionParticipant(
            self._target_root,
            head_path.relative_to(self._target_root),
            previous_head_content,
            head_content,
        )

    def _planning_pause_replay_participant(
        self,
        request: BlockDelivery,
        result: OutcomeAuthorityBinding,
        request_digest: str,
    ) -> TransactionParticipant:
        receipt = _DeliveryPlanningPauseReplay(
            change_id=self._contract.change_id,
            outcome_id=request.outcome_id,
            claim_id=request.claim_id,
            request_digest=request_digest,
            request=request,
            result=result,
        )
        return TransactionParticipant(
            self._target_root,
            self._planning_pause_replay_path(request.outcome_id, request_digest),
            _model_content(receipt),
        )

    def _planning_pause_replay_participants(
        self,
        request: DeliveryTransition,
        binding: OutcomeAuthorityBinding,
        result: OutcomeAuthorityBinding,
        request_digest: str,
    ) -> tuple[TransactionParticipant, ...]:
        if not isinstance(request, BlockDelivery) or binding.stage != DeliveryStage.PLANNING or request.request is None:
            return ()
        return (self._planning_pause_replay_participant(request, result, request_digest),)

    def _planning_pause_replay_path(self, outcome_id: str, request_digest: str) -> Path:
        return (
            self._frontier_path.parent.relative_to(self._target_root)
            / "planning-pause-receipts"
            / outcome_id
            / f"{request_digest}.json"
        )

    def resolve_request(
        self,
        request_id: str,
        resolution: DeliveryRequestResolution,
    ) -> DeliveryRequest:
        """Persist one user answer and clear its same-stage block."""
        frontier, previous = self._read()
        _require_change_mutable(frontier, "resolve_request")
        binding, request = _find_request(frontier, request_id)
        _require_no_active_change_claim(frontier, "request resolution")
        handoff_retained = any(item.builder_handoff_context is not None for item in frontier.bindings)
        if handoff_retained and (
            binding.builder_handoff_context is None
            or binding.builder_handoff_context.route not in {"same-task", "same-outcome-planner"}
            or binding.block is None
            or binding.block.request_id != request_id
        ):
            _conflict("request resolution cannot mutate outside the exact retained Builder handoff")
        if request.kind is DeliveryRequestKind.DECISION and resolution.selected_option_id is None:
            _reference("Decision requests require a selected option")
        if request.resolution is not None:
            if request.resolution == resolution:
                return request
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
        receipt_participant = self._builder_request_resolution_receipt_participant(
            binding,
            request,
            resolved,
            cleared,
        )
        if receipt_participant is None and handoff_retained:
            return_context = self._planner_handoff_pause_return_context(binding)
            if return_context is None:
                _conflict("request resolution lacks the exact retained Builder handoff receipt")
            updated = updated.model_copy(update={"return_context": return_context})
        self._replace(
            previous,
            _replace_binding(frontier, binding, updated),
            additional_participants=(receipt_participant,) if receipt_participant is not None else (),
        )
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
        handoff_retained = any(item.builder_handoff_context is not None for item in frontier.bindings)
        if handoff_retained and (
            binding.builder_handoff_context is None or binding.builder_handoff_context.route != "same-outcome-planner"
        ):
            _conflict("requestless unblock cannot mutate while a Builder handoff is retained")
        block = binding.block
        if block is None or block.block_id != block_id or block.request_id is not None:
            _conflict("requestless block is not clearable")
        _require_no_active_change_claim(frontier, "requestless block resolution")
        if block.resolved:
            if block.resolution_note == operator_note and block.resolution_locators == locators:
                return binding
            _conflict("requestless block is not clearable")
        cleared = block.model_copy(update={"resolution_note": operator_note, "resolution_locators": locators})
        updated = binding.model_copy(update={"block": cleared})
        if handoff_retained:
            return_context = self._planner_handoff_pause_return_context(binding)
            if return_context is None:
                _conflict("requestless unblock cannot mutate while a Builder handoff is retained")
            updated = updated.model_copy(update={"return_context": return_context})
        self._replace(previous, _replace_binding(frontier, binding, updated))
        return updated

    def administrative_move(
        self,
        request: AdministrativeDeliveryMove,
    ) -> AdministrativeDeliveryMoveResult:
        """Move backward and invalidate the completed dependent closure."""
        frontier, previous = self._read()
        _require_change_mutable(frontier, "administrative_move")
        _require_no_active_change_claim(frontier, "administrative movement")
        if frontier.finalization is not None:
            _conflict("administrative movement cannot cross finalized Change authority")
        if hashlib.sha256(previous).hexdigest() != request.expected_version:
            _conflict("administrative movement preview is stale")
        ordered = _administrative_move_closure(self._contract, frontier, request.outcome_id, request.target)
        self._require_no_handoff_in_administrative_closure(frontier, ordered)
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
        ordered = _administrative_move_closure(self._contract, frontier, outcome_id, target)
        self._require_no_handoff_in_administrative_closure(frontier, ordered)
        return AdministrativeDeliveryMovePreview(
            outcome_id=outcome_id,
            target=target,
            snapshot_version=hashlib.sha256(content).hexdigest(),
            invalidated_outcome_ids=ordered,
        )

    @staticmethod
    def _require_no_handoff_in_administrative_closure(frontier: DeliveryFrontier, outcome_ids: tuple[str, ...]) -> None:
        if any(
            binding.builder_handoff_context is not None and binding.outcome_id in outcome_ids
            for binding in frontier.bindings
        ):
            _conflict("administrative movement cannot orphan a preserved Builder handoff")

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
                    "retry_diagnostic": None,
                    "block": None,
                    "requests": (),
                    "retry_fingerprint": None,
                    "retry_count": 0,
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
                    "retry_diagnostic": None,
                    "block": None,
                    "requests": (),
                    "retry_fingerprint": None,
                    "retry_count": 0,
                }
            )
        return _conflict("current stage cannot advance")

    def _retry(
        self,
        binding: OutcomeAuthorityBinding,
        request: RetryDelivery,
    ) -> OutcomeAuthorityBinding:
        claim = binding.active_claim
        if claim is None:
            _conflict("retry requires an active claim")
        self._validate_retry_identity(binding, request, claim)
        diagnostic = DeliveryRetryDiagnostic(attempt_id=claim.attempt_id, transition=request)
        frontier, previous = self._read()
        _require_change_mutable(frontier, "_retry")
        current = _find_binding(frontier, binding.outcome_id)
        if current != binding:
            _conflict("active claim changed before retry diagnostic persistence")
        if current.retry_diagnostic is not None:
            if current.retry_diagnostic == diagnostic:
                raise DeliveryWorkerExclusionRequiredError
            _conflict("active claim already has a different refused retry diagnostic")
        updated = current.model_copy(update={"retry_diagnostic": diagnostic})
        self._replace(previous, _replace_binding(frontier, current, updated))
        raise DeliveryWorkerExclusionRequiredError

    def _validate_retry_identity(
        self,
        binding: OutcomeAuthorityBinding,
        request: RetryDelivery,
        claim: DeliveryActiveClaim,
    ) -> None:
        if binding.stage == DeliveryStage.IMPLEMENTATION:
            if request.abandoned_commit is None or request.attempt_id is None:
                _conflict("Implementation retry requires attempt and abandoned-commit identity")
            if request.attempt_id != claim.attempt_id:
                _conflict("Implementation retry attempt does not match the active claim")
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
        elif request.abandoned_commit is not None or request.attempt_id is not None:
            _conflict("only Implementation retry accepts attempt commit identity")

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
        self._validate_planner_return_plan(binding, tasks)
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

    @staticmethod
    def _validate_planner_return_plan(
        binding: OutcomeAuthorityBinding,
        tasks: tuple[DeliveryTaskDefinition, ...],
    ) -> None:
        handoff = binding.builder_handoff_context
        if handoff is None or handoff.route != "same-outcome-planner":
            return
        tasks_by_id = {task.task_id: task for task in tasks}
        completed_task_ids = {result.task_id for result in binding.results}
        if any(
            task.task_id not in tasks_by_id or _model_content(tasks_by_id[task.task_id]) != _model_content(task)
            for task in binding.tasks
            if task.task_id in completed_task_ids
        ):
            _conflict("Planning return must preserve completed task definitions and results")
        original_task = tasks_by_id.get(handoff.original_task_id)
        if (
            original_task is None
            or original_task.task_id in completed_task_ids
            or original_task.commitment_ids != handoff.original_task_commitment_ids
            or original_task.maintained_surfaces != handoff.original_task_maintained_surfaces
        ):
            _conflict("Planning return must preserve the original task's maintained surfaces and commitments")
        if not set(original_task.dependency_ids) <= completed_task_ids:
            _conflict("Planning return must leave its original task claimable after advance")

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
            self._require_builder_transition_exclusion(binding, request)
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
                    "retry_diagnostic": None,
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
        return returned.model_copy(update={"return_context": context, "retry_diagnostic": None})

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
            self._require_builder_transition_exclusion(binding, request)
            claim = binding.active_claim
            if claim is None:
                _conflict("Implementation block requires an active claim")
            self._require_workspace().restart(
                self._contract.change_id,
                claim.attempt_id,
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
                "retry_diagnostic": None,
                "block": block,
                "requests": requests,
            }
        )

    def _require_builder_transition_exclusion(
        self, binding: OutcomeAuthorityBinding, request: BlockDelivery | ReturnDelivery
    ) -> None:
        claim = binding.active_claim
        if claim is None or claim.claim_id != request.claim_id:
            _conflict("diagnostic transition does not match the active Builder claim")
        if isinstance(request, ReturnDelivery) and request.attempt_id != claim.attempt_id:
            _conflict("diagnostic return does not match the active Builder attempt")
        snapshot = self._require_workspace().recovery_snapshot(self._contract.change_id, claim.attempt_id)
        if (
            snapshot.writer is None
            or snapshot.writer.claim_id != claim.claim_id
            or snapshot.writer.attempt_id != claim.attempt_id
        ):
            _conflict("diagnostic transition does not match Builder writer custody")
        submitted_commit = request.resume_commit if isinstance(request, BlockDelivery) else request.preserved_commit
        if submitted_commit != snapshot.branch_head:
            raise DeliveryWorkerExclusionRequiredError
        self.publish_recovery_attention(
            binding.outcome_id,
            DeliveryRecoveryAttention(
                attempt_id=claim.attempt_id,
                claim_id=claim.claim_id,
                reason=request.reason,
                worktree_path=str(snapshot.worktree_path),
                branch_head=snapshot.branch_head,
                worktree_head=snapshot.worktree_head,
                last_reviewed_commit=snapshot.last_reviewed_commit,
                writer_claim_id=snapshot.writer.claim_id,
                custody_retained=True,
                retry_condition=(
                    "Diagnostic only: the current Builder retains custody. Host worker-exclusion evidence is missing; "
                    "no transition or restart is authorized. Resume requires verified exclusion through a supported "
                    "host recovery path, whose availability is not established by this diagnostic."
                ),
                diagnostic_transition=request,
            ),
        )
        raise DeliveryWorkerExclusionRequiredError

    def _read(self) -> tuple[DeliveryFrontier, bytes]:
        RuntimeTransaction.recover_all(self._target_root)
        try:
            content = self._frontier_path.read_bytes()
            frontier, canonical = parse_delivery_frontier(content)
            self._validate_frontier(frontier)
            if canonical != content:
                self._replace_content(content, canonical, record_pending_publication=False)
        except (OSError, TypeError, ValueError) as exc:
            message = f"Delivery frontier is missing or invalid: {self._contract.change_id}"
            raise DeliveryRuntimeReferenceError(message) from exc
        else:
            return frontier, canonical

    def _change_intent_custody_participants(
        self,
        participants: tuple[TransactionParticipant | ReplacementTransactionParticipant, ...],
        expected_finalization_attention: ChangeFinalizationAttention | None,
    ) -> tuple[TransactionParticipant | ReplacementTransactionParticipant, ...]:
        if self._workspace_manager is None:
            return participants
        guard = self._workspace_manager.prepare_runtime_custody_guard(
            self._contract.change_id,
            expected_finalization_attention=expected_finalization_attention,
        )
        return (*participants, guard)

    def _replace(
        self,
        previous: bytes,
        frontier: DeliveryFrontier,
        *,
        transition_request_digest: str | None = None,
        additional_participants: tuple[TransactionParticipant | ReplacementTransactionParticipant, ...] = (),
        include_custody_guard: bool = True,
    ) -> None:
        if self._workspace_manager is not None and include_custody_guard:
            guard = self._workspace_manager.prepare_runtime_custody_guard(self._contract.change_id)
            additional_participants = (*additional_participants, guard)
        portable = not any(binding.active_claim is not None for binding in frontier.bindings)
        portable = portable and not any(binding.builder_handoff_context is not None for binding in frontier.bindings)
        portable = portable and frontier.integration_repair_claim is None
        self._replace_content(
            previous,
            _model_content(frontier),
            transition_request_digest=transition_request_digest if portable else None,
            record_pending_publication=portable,
            additional_participants=additional_participants,
        )

    def _replace_content(  # noqa: PLR0913 - one transaction binds state, publication intent, and immutable receipts.
        self,
        previous: bytes,
        replacement: bytes,
        *,
        record_pending_publication: bool = True,
        transition_request_digest: str | None = None,
        base_frontier_digest: str | None = None,
        additional_participants: tuple[TransactionParticipant | ReplacementTransactionParticipant, ...] = (),
    ) -> None:
        """Transactionally replace frontier bytes and its local publication intent."""
        participant = ReplacementTransactionParticipant(
            self._target_root,
            self._frontier_path.relative_to(self._target_root),
            previous,
            replacement,
        )
        participants: list[TransactionParticipant | ReplacementTransactionParticipant] = [
            participant,
            *additional_participants,
        ]
        if record_pending_publication:
            participants.append(
                self._pending_publication_participant(
                    replacement,
                    base_frontier_digest or self.publication_base_digest(previous),
                    transition_request_digest,
                )
            )
        transaction_id = hashlib.sha256(previous + replacement).hexdigest()
        RuntimeTransaction(self._target_root, f"delivery-runtime-{transaction_id}", tuple(participants)).commit()

    def _pending_publication_participant(
        self,
        replacement: bytes,
        base_frontier_digest: str,
        transition_request_digest: str | None = None,
    ) -> TransactionParticipant | ReplacementTransactionParticipant:
        """Build the marker participant that tracks one exact local frontier replacement."""
        content = _model_content(
            DeliveryPendingStatePublication.pending(
                base_frontier_digest,
                hashlib.sha256(replacement).hexdigest(),
                transition_request_digest,
            )
        )
        relative_path = self._pending_publication_path.relative_to(self._target_root)
        if self._pending_publication_path.exists():
            return ReplacementTransactionParticipant(
                self._target_root,
                relative_path,
                self._pending_publication_path.read_bytes(),
                content,
            )
        return TransactionParticipant(self._target_root, relative_path, content)

    def _validate_frontier(self, frontier: DeliveryFrontier) -> None:
        expected = tuple((scope.outcome_id, scope.scope_id) for scope in self._contract.plan_scopes)
        actual = tuple((binding.outcome_id, binding.plan_scope_id) for binding in frontier.bindings)
        if actual != expected:
            _reference("Delivery frontier does not match its admitted contract")
        resolution = frontier.change_disposition_resolution
        if resolution is not None and resolution.change_id != self._contract.change_id:
            _reference("Delivery Change attention resolution does not match its admitted Change")
        history = frontier.change_publication_history
        if history is not None and history.change_id != self._contract.change_id:
            _reference("Delivery publication history does not match its admitted Change")
        target_sync = frontier.target_sync_receipt
        if target_sync is not None and target_sync.change_id != self._contract.change_id:
            _reference("Delivery target synchronization receipt does not match its admitted Change")
        adoption = frontier.external_head_adoption_receipt
        if adoption is not None and adoption.change_id != self._contract.change_id:
            _reference("Delivery external Change-head adoption receipt does not match its admitted Change")
        promotion = frontier.external_head_promotion_receipt
        if promotion is not None and (
            promotion.change_id != self._contract.change_id
            or adoption is None
            or promotion.adoption_receipt_id != adoption.receipt_id
            or promotion.promoted_head != adoption.adopted_head
        ):
            _reference("Delivery external Change-head promotion receipt does not match its adoption evidence")
        for receipt in (frontier.change_deferral, frontier.change_abandonment):
            if receipt is not None and receipt.change_id != self._contract.change_id:
                _reference("Delivery Change lifecycle receipt does not match its admitted Change")


def _find_binding(frontier: DeliveryFrontier, outcome_id: str) -> OutcomeAuthorityBinding:
    try:
        return next(binding for binding in frontier.bindings if binding.outcome_id == outcome_id)
    except StopIteration as exc:
        _reference(f"Delivery outcome is absent: {outcome_id}", exc)


def _require_change_mutable(
    frontier: DeliveryFrontier,
    operation: str,
    *,
    allow_attention: bool = False,
) -> None:
    if operation not in _NORMAL_CHANGE_MUTATIONS:
        message = f"unregistered Delivery Change mutation: {operation}"
        raise ValueError(message)
    if frontier.change_completion is not None:
        _conflict("completed Delivery Change is terminal")
    if frontier.change_abandonment is not None:
        _conflict("abandoned Delivery Change is terminal")
    if frontier.change_deferral is not None and operation not in {"resume_change", "abandon_change"}:
        _conflict("deferred Delivery Change requires resumption before mutation")
    if (
        frontier.change_disposition is not None
        and not allow_attention
        and operation
        not in {
            "defer_change",
            "resume_change",
            "abandon_change",
            "record_publication_successor",
        }
    ):
        _conflict("Delivery Change requires attention resolution before mutation")


def _require_no_active_change_claim(frontier: DeliveryFrontier, operation: str) -> None:
    has_outcome_claim = any(binding.active_claim is not None for binding in frontier.bindings)
    if frontier.integration_repair_claim is not None:
        _conflict(f"{operation} cannot overlap an active Integration repair claim")
    if has_outcome_claim:
        _conflict(f"{operation} cannot overlap an active mutation claim")


def _require_no_review_repair(frontier: DeliveryFrontier, operation: str) -> None:
    """Reject head mutations while external review repair owns the Change boundary."""
    invalidation = frontier.finalization_invalidation
    if invalidation is not None and invalidation.reason == "review-repair":
        _conflict(f"{operation} cannot overlap an active review repair")


def is_acceptance_waiting_observation(
    observation: PublicationPullRequestObservationReceipt,
) -> bool:
    """Return whether a bound pull request is normally waiting for a user merge."""
    snapshot = observation.snapshot
    return snapshot.state == "open" and not snapshot.merged


def parse_delivery_frontier(
    content: bytes,
) -> tuple[DeliveryFrontier, bytes]:
    """Parse one frontier and canonicalize the immediately prior persisted schema."""
    payload = json.loads(content)
    if not isinstance(payload, dict):
        raise TypeError
    schema_version = payload.get("schema_version")
    if schema_version == _LEGACY_FRONTIER_SCHEMA_VERSION:
        payload = {**payload, "schema_version": _FRONTIER_SCHEMA_VERSION}
    elif schema_version != _FRONTIER_SCHEMA_VERSION:
        raise ValueError
    frontier = DeliveryFrontier.model_validate(payload, strict=False)
    return frontier, _model_content(frontier)


def repair_missing_request_provenance(  # noqa: C901 - narrow structural migration validates each legacy layer.
    content: bytes,
    request_id: str,
) -> tuple[DeliveryFrontier, bytes]:
    """Repair only one legacy free-text request lacking explicit confirmation."""
    payload = json.loads(content)
    if not isinstance(payload, dict):
        raise TypeError
    bindings = payload.get("bindings")
    if not isinstance(bindings, list):
        _reference("Delivery frontier bindings are invalid")
    missing: list[tuple[dict[str, object], dict[str, object]]] = []
    for binding in bindings:
        if not isinstance(binding, dict):
            _reference("Delivery frontier binding is invalid")
        requests = binding.get("requests")
        if not isinstance(requests, list):
            _reference("Delivery frontier requests are invalid")
        for request in requests:
            if not isinstance(request, dict):
                _reference("Delivery frontier request is invalid")
            resolution = request.get("resolution")
            if not isinstance(resolution, dict):
                continue
            response_text = resolution.get("response_text")
            if isinstance(response_text, str) and response_text.strip() and resolution.get("provenance") is None:
                missing.append((request, resolution))
    if len(missing) != 1 or missing[0][0].get("request_id") != request_id:
        _reference("frontier contains an unsupported request-provenance defect")
    missing[0][1]["provenance"] = "user-confirmed"
    repaired_payload = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return parse_delivery_frontier(repaired_payload)


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


def _builder_request_resolution_receipt_path(
    runtime_root: Path,
    change_id: str,
    builder_handoff_context: DeliveryBuilderHandoffContext,
) -> Path:
    return (
        runtime_root
        / "changes"
        / change_id
        / "builder-request-resolution-receipts"
        / f"{builder_handoff_context.settlement_id}.json"
    )


def _builder_handoff_change_intent_directory(
    runtime_root: Path,
    change_id: str,
    builder_handoff_context: DeliveryBuilderHandoffContext,
) -> Path:
    return (
        runtime_root
        / "changes"
        / change_id
        / "builder-handoff-change-intent-receipts"
        / builder_handoff_context.settlement_id
    )


def _builder_handoff_change_intent_head_path(
    runtime_root: Path,
    change_id: str,
    builder_handoff_context: DeliveryBuilderHandoffContext,
) -> Path:
    return _builder_handoff_change_intent_directory(runtime_root, change_id, builder_handoff_context) / "head.json"


def _read_builder_handoff_change_intent_receipts(
    runtime_root: Path,
    change_id: str,
    builder_handoff_context: DeliveryBuilderHandoffContext,
) -> tuple[_DeliveryBuilderHandoffChangeIntentReceipt, ...]:
    """Read only the bounded receipt chain addressed by one known Builder handoff."""
    root = runtime_root.resolve()
    directory = _builder_handoff_change_intent_directory(root, change_id, builder_handoff_context)
    head = _read_builder_handoff_change_intent_head(root, change_id, builder_handoff_context)
    if head is None:
        return ()

    reverse_chain: list[_DeliveryBuilderHandoffChangeIntentReceipt] = []
    receipt_id: str | None = head.latest_receipt_id
    for sequence in range(head.sequence, 0, -1):
        if receipt_id is None:
            _reference("Builder handoff change-intent receipt chain is incomplete")
        receipt = _read_builder_handoff_change_intent_receipt(
            directory,
            change_id,
            builder_handoff_context,
            receipt_id,
        )
        if receipt.sequence != sequence:
            _reference("Builder handoff change-intent receipt chain is invalid")
        reverse_chain.append(receipt)
        receipt_id = receipt.previous_receipt_id
        if sequence > 1 and receipt_id is None:
            _reference("Builder handoff change-intent receipt chain is incomplete")
    if receipt_id is not None:
        _reference("Builder handoff change-intent receipt chain has an unknown predecessor")

    chain = tuple(reversed(reverse_chain))
    _validate_builder_handoff_change_intent_chain(chain, head)
    return chain


def _read_builder_handoff_change_intent_head(
    runtime_root: Path,
    change_id: str,
    builder_handoff_context: DeliveryBuilderHandoffContext,
) -> _DeliveryBuilderHandoffChangeIntentHead | None:
    head_path = _builder_handoff_change_intent_head_path(runtime_root, change_id, builder_handoff_context)
    change_root = runtime_root / "changes" / change_id
    if any(path.is_symlink() for path in (runtime_root / "changes", change_root, head_path.parent, head_path)):
        _reference("Builder handoff change-intent receipt path is unsafe")
    try:
        content = head_path.read_bytes()
    except FileNotFoundError:
        return None
    except OSError as exc:
        _reference("Builder handoff change-intent head is unavailable", exc)
    try:
        head = _DeliveryBuilderHandoffChangeIntentHead.model_validate_json(content, strict=True)
    except (TypeError, ValueError) as exc:
        _reference("Builder handoff change-intent head is invalid", exc)
    if (
        content != _model_content(head)
        or head.change_id != change_id
        or head.builder_handoff_context != builder_handoff_context
    ):
        _reference("Builder handoff change-intent head does not match its known settlement")
    return head


def _read_builder_handoff_change_intent_receipt(
    directory: Path,
    change_id: str,
    builder_handoff_context: DeliveryBuilderHandoffContext,
    receipt_id: str,
) -> _DeliveryBuilderHandoffChangeIntentReceipt:
    receipt_path = directory / f"{receipt_id}.json"
    if receipt_path.is_symlink():
        _reference("Builder handoff change-intent receipt path is unsafe")
    try:
        content = receipt_path.read_bytes()
    except OSError as exc:
        _reference("Builder handoff change-intent receipt is unavailable", exc)
    try:
        receipt = _DeliveryBuilderHandoffChangeIntentReceipt.model_validate_json(content, strict=True)
    except (TypeError, ValueError) as exc:
        _reference("Builder handoff change-intent receipt is invalid", exc)
    if (
        content != _model_content(receipt)
        or receipt.receipt_id != receipt_id
        or receipt.change_id != change_id
        or receipt.builder_handoff_context != builder_handoff_context
    ):
        _reference("Builder handoff change-intent receipt chain is invalid")
    return receipt


def _validate_builder_handoff_change_intent_chain(
    chain: tuple[_DeliveryBuilderHandoffChangeIntentReceipt, ...],
    head: _DeliveryBuilderHandoffChangeIntentHead,
) -> None:
    if not chain or (
        chain[-1].receipt_id != head.latest_receipt_id
        or chain[-1].sequence != head.sequence
        or chain[-1].outcome_id != head.outcome_id
    ):
        _reference("Builder handoff change-intent head does not identify the end of its receipt chain")
    if len(chain) > _MAX_BUILDER_HANDOFF_CHANGE_INTENTS and (
        len(chain) != _MAX_BUILDER_HANDOFF_CHANGE_INTENT_RECEIPTS or chain[-1].action != "abandon"
    ):
        _reference("Builder handoff change-intent receipt chain exceeds its supported limit")
    for previous, current in pairwise(chain):
        if current.previous_receipt_id != previous.receipt_id or current.sequence != previous.sequence + 1:
            _reference("Builder handoff change-intent receipt chain is invalid")


def _read_builder_request_resolution_receipt(
    runtime_root: Path,
    change_id: str,
    request_id: str,
    builder_handoff_context: DeliveryBuilderHandoffContext,
) -> _DeliveryBuilderRequestResolutionReceipt:
    """Read one exact local Builder answer without constructing a DeliveryRuntime."""
    receipt_path = _builder_request_resolution_receipt_path(runtime_root, change_id, builder_handoff_context)
    change_root = runtime_root / "changes" / change_id
    receipt_directory = receipt_path.parent
    if any(path.is_symlink() for path in (runtime_root / "changes", change_root, receipt_directory, receipt_path)):
        _reference("Builder request resolution receipt path is unsafe")
    try:
        content = receipt_path.read_bytes()
    except OSError as exc:
        _reference("Builder request resolution receipt is unavailable", exc)
    try:
        receipt = _DeliveryBuilderRequestResolutionReceipt.model_validate_json(content, strict=True)
    except (TypeError, ValueError) as exc:
        _reference("Builder request resolution receipt is invalid", exc)
    if (
        receipt.change_id != change_id
        or receipt.request_id != request_id
        or receipt.builder_handoff_context != builder_handoff_context
    ):
        _reference("Builder request resolution receipt does not match its exact handoff")
    return receipt


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
    if not any(item.results for item in previous.bindings) and not _has_checkpoint_trigger(
        pending,
        DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK,
    ):
        triggers.append(
            DeliveryCheckpointTrigger(
                kind=DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK,
            )
        )
    elif pending is None and updated.stage != DeliveryStage.COMPLETED:
        triggers.append(
            DeliveryCheckpointTrigger(
                kind=DeliveryCheckpointTriggerKind.VERIFIED_TASK,
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
            "pending_checkpoint": _checkpoint_with_head(
                pending,
                candidate.result.completed_commit,
                tuple(dict.fromkeys(combined)),
            )
        }
    )


def _queue_finalization_checkpoint(frontier: DeliveryFrontier, exact_head: str) -> DeliveryFrontier:
    pending = frontier.pending_checkpoint
    trigger = DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.FINALIZATION)
    combined = (*(() if pending is None else pending.triggers), trigger)
    return frontier.model_copy(
        update={"pending_checkpoint": _checkpoint_with_head(pending, exact_head, tuple(dict.fromkeys(combined)))}
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
    return _checkpoint_with_head(pending, None, retained)


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
    return _checkpoint_with_head(pending, None, retained)


def _checkpoint_with_head(
    previous: DeliveryPendingCheckpoint | None,
    head: str | None,
    triggers: tuple[DeliveryCheckpointTrigger, ...] | None = None,
) -> DeliveryPendingCheckpoint:
    """Create or re-anchor one checkpoint, retaining retry metadata only for the same head."""
    next_triggers = triggers if triggers is not None else (() if previous is None else previous.triggers)
    if previous is not None and previous.head == head:
        return previous.model_copy(update={"triggers": next_triggers})
    return DeliveryPendingCheckpoint(head=head, triggers=next_triggers)


def _require_claim(binding: OutcomeAuthorityBinding, claim_id: str) -> None:
    if binding.active_claim_id != claim_id:
        _conflict("transition does not match the active claim")


def _retry_fingerprint(
    change_id: str,
    outcome_id: str,
    worker_role: DeliveryWorkerRole,
    failure_code: str,
) -> str:
    """Return a stable fingerprint for one repeated worker failure class."""
    payload = f"{change_id}\0{outcome_id}\0{worker_role.value}\0{failure_code.casefold()}"
    return hashlib.sha256(payload.encode()).hexdigest()


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


def _finalization_invalidation_digest(receipt: DeliveryFinalizationInvalidationReceipt) -> str:
    payload = receipt.model_dump(mode="json", exclude={"invalidation_id"})
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


def _completed_outcome_repair_id(
    change_id: str,
    request: PrepareCompletedOutcomeRepair,
    source_digest: str,
) -> str:
    """Derive one stable repair identity from admitted lineage and evidence."""
    material = (
        f"{change_id}\0{request.outcome_id}\0{request.owning_task_id}\0{source_digest}\0"
        f"{request.episode_id}\0{request.attempt_id}\0{request.defect_code}\0{request.finding_boundary}\0"
        f"{request.original_action_id}\0{request.preservation_id}\0{request.expected_frontier_digest}"
    )
    return hashlib.sha256(material.encode()).hexdigest()


def _target_sync_operation_id(disposition: DeliveryChangeDisposition) -> str | None:
    prefix = "target-sync-operation:"
    for diagnostic in disposition.diagnostics:
        if diagnostic.startswith(prefix):
            return diagnostic.removeprefix(prefix)
    return None


def _require_target_sync_attention(
    frontier: DeliveryFrontier,
    expected_disposition_id: str,
    operation_id: str,
) -> DeliveryChangeDisposition:
    current = frontier.change_disposition
    if current is None:
        _attention_conflict("target synchronization attention is absent or already resolved")
    if current.disposition_id != expected_disposition_id:
        _attention_conflict("target synchronization attention identity is stale")
    if current.kind != DeliveryChangeDispositionKind.PUBLICATION_ATTENTION:
        _attention_conflict("target synchronization attention has the wrong disposition kind")
    if _target_sync_operation_id(current) != operation_id:
        _attention_conflict("target synchronization operation identity is stale")
    return current


def _conflict(message: str) -> None:
    raise DeliveryRuntimeConflictError(message)


def _reference(message: str, cause: Exception | None = None) -> None:
    if cause is None:
        raise DeliveryRuntimeReferenceError(message)
    raise DeliveryRuntimeReferenceError(message) from cause


# Forward references resolve only now; incomplete models fail bare serialization in adapters.
DeliveryRecoveryAttention.model_rebuild()
OutcomeAuthorityBinding.model_rebuild()
DeliveryFrontier.model_rebuild()


__all__ = [
    "DELIVERY_TRANSITION_ADAPTER",
    "ActivateDeliveryClaim",
    "AdministrativeDeliveryMove",
    "AdministrativeDeliveryMoveResult",
    "AdvanceDelivery",
    "BlockDelivery",
    "CompletedOutcomeRepairReceipt",
    "DeliveryAcceptanceAttentionReason",
    "DeliveryAcceptanceWaitingError",
    "DeliveryBlock",
    "DeliveryBuilderInvocationSettlement",
    "DeliveryChangeAbandonment",
    "DeliveryChangeCompletion",
    "DeliveryChangeDeferral",
    "DeliveryChangeDisposition",
    "DeliveryChangeDispositionBusyError",
    "DeliveryChangeDispositionConflictError",
    "DeliveryChangeDispositionKind",
    "DeliveryChangeDispositionResolution",
    "DeliveryChangePublicationHistory",
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
    "DeliveryMergedPullRequestLatch",
    "DeliveryObservation",
    "DeliveryObservationReceipt",
    "DeliveryOperatorMove",
    "DeliveryOutputKind",
    "DeliveryOutputReference",
    "DeliveryPendingCheckpoint",
    "DeliveryPendingStatePublication",
    "DeliveryPlanningRetrySettlement",
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
    "PrepareCompletedOutcomeRepair",
    "PublishDeliveryOutput",
    "PublishDeliveryPlan",
    "PublishDeliveryResult",
    "RetryDelivery",
    "ReturnDelivery",
    "derive_change_stage",
    "invalidate_checkpoint_publication",
    "is_acceptance_waiting_observation",
    "is_change_terminal",
    "parse_delivery_frontier",
    "repair_missing_request_provenance",
]
