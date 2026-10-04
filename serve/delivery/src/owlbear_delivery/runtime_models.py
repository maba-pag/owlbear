"""Delivery runtime stages, records, frontier and transition models."""

from __future__ import annotations

import hashlib
import inspect
import json
import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType
from typing import TYPE_CHECKING, Annotated, Literal, TypedDict, Unpack, cast

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator

from owlbear_delivery.acceptance_criteria import ACCEPTANCE_ID_PATTERN, DeliveryAcceptanceRef
from owlbear_delivery.change_workspace import (
    ChangeExternalHeadAdoptionReceipt,
    ChangeExternalHeadPromotionReceipt,
    ChangeTargetSyncReceipt,
)
from owlbear_delivery.draft_pull_request import (
    PullRequestReadyReceipt,
)

if TYPE_CHECKING:
    from collections.abc import Mapping


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


class DeliveryLegacyObservation(_DeliveryModel):
    """Schema-1 free-text validation evidence, read-only since observation schema 2."""

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


class DeliveryLegacyObservationReceipt(DeliveryLegacyObservation):
    """One retained schema-1 observation; its coverage is unknown and it is never relabeled."""

    observation_id: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _validate_receipt(self) -> DeliveryLegacyObservationReceipt:
        if self.observed_at.tzinfo is None:
            message = "Delivery observation timestamp must include a timezone"
            raise ValueError(message)
        if self.observation_id != _receipt_digest(self, "observation_id"):
            message = "Delivery observation receipt identity is invalid"
            raise ValueError(message)
        return self


_SHA256 = r"^[0-9a-f]{64}$"
_LOCATOR = re.compile(r"(?:path|ci-run|check-run|request|report):\S+")
_ENVIRONMENT_LABEL = r"^[a-z0-9][a-z0-9.+_-]{0,63}(:[A-Za-z0-9.+_-]{1,64})?$"


class DeliveryCommandResult(_DeliveryModel):
    """Machine-run command evidence whose verdict is derived from exit status and expectation."""

    kind: Literal["command"] = "command"
    exit_status: int = Field(ge=-255, le=255)
    expectation: Literal["success", "expected-failure"] = "success"
    expected_exit_status: int | None = Field(default=None, ge=-255, le=255)

    @model_validator(mode="after")
    def _validate_expectation(self) -> DeliveryCommandResult:
        if (self.expectation == "expected-failure") != (self.expected_exit_status is not None):
            message = "an expected exit status is required exactly for an expected-failure command"
            raise ValueError(message)
        if self.expected_exit_status == 0:
            message = "an expected-failure command must expect a nonzero exit status"
            raise ValueError(message)
        return self

    @property
    def verdict(self) -> DeliveryEvidenceVerdict:
        """Derive the command verdict; it can never contradict exit status and expectation."""
        if self.expectation == "success":
            return "passed" if self.exit_status == 0 else "failed"
        return "expected-negative" if self.exit_status == self.expected_exit_status else "failed"


class DeliveryManualProcedureResult(_DeliveryModel):
    """Evidence from a named manual procedure with an explicit assessment."""

    kind: Literal["manual-procedure"] = "manual-procedure"
    assessment: Literal["passed", "failed"]

    @property
    def verdict(self) -> DeliveryEvidenceVerdict:
        """Return the explicit assessment."""
        return self.assessment


class DeliveryArtifactResult(_DeliveryModel):
    """Evidence from one retained artifact with an explicit assessment."""

    kind: Literal["artifact"] = "artifact"
    assessment: Literal["passed", "failed"]
    artifact_digest: str | None = Field(default=None, pattern=_SHA256)

    @property
    def verdict(self) -> DeliveryEvidenceVerdict:
        """Return the explicit assessment."""
        return self.assessment


class DeliveryMissingResult(_DeliveryModel):
    """A durable, owned gap: required evidence that does not exist yet."""

    kind: Literal["missing"] = "missing"
    owner: Literal["agent", "user", "provider", "assisted-check"]
    reason: str = Field(min_length=1, max_length=240)

    @property
    def verdict(self) -> DeliveryEvidenceVerdict:
        """Return the missing verdict."""
        return "missing"


class DeliveryWaivedResult(_DeliveryModel):
    """An explicit user waiver; it applies only with a matching ledger confirmation."""

    kind: Literal["waived"] = "waived"
    owner: Literal["user"] = "user"
    reason: str = Field(min_length=1, max_length=240)
    confirmation_id: str = Field(pattern=_SHA256)

    @property
    def verdict(self) -> DeliveryEvidenceVerdict:
        """Return the waived verdict."""
        return "waived"


type DeliveryEvidenceVerdict = Literal["passed", "expected-negative", "failed", "missing", "waived"]
DeliveryEvidenceResult = Annotated[
    DeliveryCommandResult
    | DeliveryManualProcedureResult
    | DeliveryArtifactResult
    | DeliveryMissingResult
    | DeliveryWaivedResult,
    Field(discriminator="kind"),
]
PROOF_VERDICTS: frozenset[str] = frozenset({"passed", "expected-negative"})


class DeliveryObservationEnvironment(_DeliveryModel):
    """Environment constraints that bound where an observation applies."""

    platform: Literal["macos", "linux"] | None = None
    labels: tuple[Annotated[str, Field(pattern=_ENVIRONMENT_LABEL)], ...] = Field(default=(), max_length=8)


class DeliveryObservation(_DeliveryModel):
    """Typed schema-2 validation evidence before its immutable receipt identity is assigned."""

    schema_version: Literal[2] = 2
    change_id: str = Field(min_length=1)
    task_or_finalization_id: str = Field(min_length=1)
    step_id: str | None = Field(default=None, min_length=1)
    exact_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    observation_kind: str = Field(min_length=1, max_length=64)
    procedure: str = Field(min_length=1, max_length=512)
    procedure_registration_digest: str | None = Field(default=None, pattern=_SHA256)
    result: DeliveryEvidenceResult
    covers: tuple[DeliveryAcceptanceRef, ...] = Field(default=(), max_length=32)
    environment: DeliveryObservationEnvironment = DeliveryObservationEnvironment()
    target_class: str | None = Field(default=None, pattern=r"^[a-z0-9][a-z0-9-]{0,63}$")
    provenance: Literal["machine-observed", "human-confirmed"] = "machine-observed"
    confirmation_id: str | None = Field(default=None, pattern=_SHA256)
    locator: str | None = Field(default=None, max_length=256)
    summary: str | None = Field(default=None, max_length=240)
    observer_or_runner_identity: str = Field(min_length=1)
    observed_at: datetime

    @model_validator(mode="after")
    def _validate_evidence(self) -> DeliveryObservation:
        identities = tuple(reference.acceptance_id for reference in self.covers)
        if len(identities) != len(set(identities)):
            message = "an observation covers each acceptance criterion at most once"
            raise ValueError(message)
        kind = self.result.kind
        if self.provenance == "human-confirmed" and kind not in {"manual-procedure", "artifact", "waived"}:
            message = "human-confirmed provenance applies only to manual, artifact, or waived evidence"
            raise ValueError(message)
        needs_confirmation = self.provenance == "human-confirmed" or kind == "waived"
        if needs_confirmation != (self.confirmation_id is not None):
            message = "a confirmation is cited exactly by human-confirmed or waived evidence"
            raise ValueError(message)
        if isinstance(self.result, DeliveryWaivedResult) and self.result.confirmation_id != self.confirmation_id:
            message = "a waiver must cite its own confirmation"
            raise ValueError(message)
        if kind == "artifact" and self.locator is None:
            message = "artifact evidence requires a retained locator"
            raise ValueError(message)
        if self.locator is not None and not _valid_locator(self.locator):
            message = "observation locator must be a bounded scheme:value without URLs or parent segments"
            raise ValueError(message)
        return self

    @property
    def verdict(self) -> DeliveryEvidenceVerdict:
        """Return the derived verdict of the typed result."""
        return self.result.verdict


def _valid_locator(locator: str) -> bool:
    if _LOCATOR.fullmatch(locator) is None or "://" in locator:
        return False
    return ".." not in locator.split(":", 1)[1].split("/")


class DeliveryObservationReceipt(DeliveryObservation):
    """One exact-commit schema-2 observation retained as lifecycle evidence."""

    observation_id: str = Field(pattern=_SHA256)

    @classmethod
    def create(
        cls,
        observation: DeliveryObservation,
    ) -> DeliveryObservationReceipt:
        """Create one receipt using the canonical typed-content digest."""
        values = {field_name: getattr(observation, field_name) for field_name in DeliveryObservation.model_fields}
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


DeliveryAnyObservationReceipt = Annotated[
    DeliveryLegacyObservationReceipt | DeliveryObservationReceipt,
    Field(discriminator="schema_version"),
]


class DeliveryReview(_DeliveryModel):
    """Typed independent advisory pass before receipt identity is assigned."""

    schema_version: Literal[1, 2] = 2
    exact_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    author_id: str = Field(min_length=1)
    reviewer_id: str = Field(min_length=1)
    disposition: Literal["pass"] = "pass"
    evidence: tuple[str, ...] = Field(min_length=1)
    reviewed_at: datetime
    review_mode: Literal["task", "finalization"] | None = Field(default=None, exclude_if=_omit_when_none)
    basis_digest: str | None = Field(default=None, pattern=_SHA256, exclude_if=_omit_when_none)
    observation_ids: tuple[Annotated[str, Field(pattern=_SHA256)], ...] | None = Field(
        default=None, exclude_if=_omit_when_none
    )

    @model_validator(mode="after")
    def _validate_review_version(self) -> DeliveryReview:
        if self.schema_version == 1:
            if self.review_mode is not None or self.basis_digest is not None or self.observation_ids is not None:
                message = "schema-1 Delivery review cannot carry review mode, basis, or observation binding"
                raise ValueError(message)
            return self
        if self.review_mode is None:
            message = "schema-2 Delivery review requires its review mode"
            raise ValueError(message)
        if self.review_mode == "task" and self.basis_digest is not None:
            message = "a task review cannot bind a finalization basis"
            raise ValueError(message)
        return self


class DeliveryReviewReceipt(DeliveryReview):
    """Independent advisory pass bound to one exact implementation commit."""

    review_id: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def create(
        cls,
        review: DeliveryReview,
    ) -> DeliveryReviewReceipt:
        """Create one independent pass receipt using the canonical digest."""
        values = {field_name: getattr(review, field_name) for field_name in DeliveryReview.model_fields}
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
    observations: tuple[DeliveryAnyObservationReceipt, ...] = Field(min_length=1)
    review: DeliveryReviewReceipt

    @property
    def has_n03_content(self) -> bool:
        """Return whether this result holds content that only frontier 19 may carry."""
        typed = _TYPED_EVIDENCE_SCHEMA_VERSION
        return self.review.schema_version == typed or any(item.schema_version == typed for item in self.observations)

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

    schema_version: Literal[2, 3] = 3
    operation_id: str = Field(min_length=1)
    change_id: str = Field(min_length=1)
    exact_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    authority_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    result_digests: tuple[str, ...] = Field(min_length=1)
    observations: tuple[DeliveryAnyObservationReceipt, ...]
    review: DeliveryReviewReceipt
    finalized_at: datetime

    @model_validator(mode="after")
    def _validate_finalization_version(self) -> DeliveryFinalization:
        typed = tuple(item.schema_version != 1 for item in self.observations)
        if self.schema_version == _LEGACY_FINALIZATION_SCHEMA_VERSION:
            if not self.observations or any(typed) or self.review.schema_version != 1:
                message = "schema-2 Delivery finalization holds only schema-1 evidence and at least one observation"
                raise ValueError(message)
            return self
        if (
            not all(typed)
            or self.review.review_mode != "finalization"
            or self.review.observation_ids != tuple(item.observation_id for item in self.observations)
        ):
            message = "schema-3 Delivery finalization requires typed evidence and its matching finalization review"
            raise ValueError(message)
        return self


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
    confirmation_id: str | None = Field(default=None, pattern=_SHA256, exclude_if=_omit_when_none)

    @model_validator(mode="after")
    def _require_answer(self) -> DeliveryRequestResolution:
        if self.selected_option_id is None and (self.response_text is None or not self.response_text.strip()):
            message = "request resolution requires a selected option or response text"
            raise ValueError(message)
        if self.response_text is not None and self.response_text.strip() and self.provenance != "user-confirmed":
            message = "free-text request resolution requires user-confirmed provenance"
            raise ValueError(message)
        return self


CONFIRMATION_DECISIONS: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {"waive": ("waive", "keep-required"), "confirm-check": ("passed", "failed")}
)
# The decision that makes a confirmation affirmative for each scope kind (I6).
AFFIRMATIVE_DECISIONS: Mapping[str, str] = MappingProxyType({"waive": "waive", "confirm-check": "passed"})
MAX_LEDGER_CONFIRMATIONS = 256


class DeliveryConfirmationScope(_DeliveryModel):
    """Exact criterion versions and procedure that a user confirmation may apply to."""

    kind: Literal["waive", "confirm-check"]
    acceptance: tuple[DeliveryAcceptanceRef, ...] = Field(min_length=1, max_length=32)
    procedure: str = Field(min_length=1, max_length=512)

    @model_validator(mode="after")
    def _validate_scope(self) -> DeliveryConfirmationScope:
        identities = tuple(reference.acceptance_id for reference in self.acceptance)
        if len(identities) != len(set(identities)):
            message = "a confirmation scope names each acceptance criterion at most once"
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
    applies_to: DeliveryConfirmationScope | None = Field(default=None, exclude_if=_omit_when_none)

    @model_validator(mode="after")
    def _validate_options(self) -> DeliveryRequest:
        option_ids = tuple(option.option_id for option in self.options)
        if len(option_ids) != len(set(option_ids)):
            message = "request option identities must be unique"
            raise ValueError(message)
        if self.kind == DeliveryRequestKind.DECISION and not self.options:
            message = "Decision Requests require bounded options"
            raise ValueError(message)
        self._validate_confirmation_scope()
        return self

    def _validate_confirmation_scope(self) -> None:
        scope = self.applies_to
        confirmation_id = self.resolution.confirmation_id if self.resolution is not None else None
        if scope is None:
            if confirmation_id is not None:
                message = "only a scoped request resolution cites a user confirmation"
                raise ValueError(message)
            return
        if self.kind != DeliveryRequestKind.DECISION or {option.option_id for option in self.options} != set(
            CONFIRMATION_DECISIONS[scope.kind]
        ):
            message = "a scoped request is a Decision Request whose options are exactly its confirmation decisions"
            raise ValueError(message)
        resolution = self.resolution
        if resolution is not None and (
            confirmation_id is None
            or resolution.provenance != "user-confirmed"
            or resolution.selected_option_id not in CONFIRMATION_DECISIONS[scope.kind]
            or resolution.response_text is not None
        ):
            message = "a scoped request resolution must be the user-confirmed decision of its ledger confirmation"
            raise ValueError(message)

    @property
    def has_n03_content(self) -> bool:
        """Return whether this request holds content that only frontier 19 may carry."""
        return self.applies_to is not None or (
            self.resolution is not None and self.resolution.confirmation_id is not None
        )


class DeliveryUserConfirmation(_DeliveryModel):
    """One user decision captured through the confirmation boundary; the ledger is its only authority."""

    schema_version: Literal[1] = 1
    change_id: str = Field(min_length=1, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    request_id: str = Field(min_length=1)
    scope: DeliveryConfirmationScope
    decision: Literal["waive", "keep-required", "passed", "failed"]
    channel: Literal["mcp-elicitation"] = "mcp-elicitation"
    question_digest: str = Field(pattern=_SHA256)
    generation_id: str = Field(pattern=_SHA256)
    confirmed_at: datetime
    confirmation_id: str = Field(pattern=_SHA256)

    @classmethod
    def create(  # noqa: PLR0913 - the confirmation binds every element of the answered question.
        cls,
        *,
        change_id: str,
        request: DeliveryRequest,
        decision: str,
        question_digest: str,
        generation_id: str,
        confirmed_at: datetime,
    ) -> DeliveryUserConfirmation:
        """Create one deterministic confirmation for an answered scoped request."""
        if request.applies_to is None:
            message = "only a scoped request can record a user confirmation"
            raise ValueError(message)
        values = {
            "change_id": change_id,
            "outcome_id": request.outcome_id,
            "request_id": request.request_id,
            "scope": request.applies_to,
            "decision": decision,
            "channel": "mcp-elicitation",
            "question_digest": question_digest,
            "generation_id": generation_id,
            "confirmed_at": confirmed_at,
        }
        candidate = cls.model_construct(confirmation_id="0" * 64, schema_version=1, **values)
        return cls(confirmation_id=_receipt_digest(candidate, "confirmation_id"), **values)

    @model_validator(mode="after")
    def _validate_confirmation(self) -> DeliveryUserConfirmation:
        if self.decision not in CONFIRMATION_DECISIONS[self.scope.kind]:
            message = "confirmation decision does not belong to its scope kind"
            raise ValueError(message)
        if self.confirmed_at.tzinfo is None:
            message = "confirmation timestamp must include a timezone"
            raise ValueError(message)
        if self.confirmation_id != _receipt_digest(self, "confirmation_id"):
            message = "user confirmation identity is invalid"
            raise ValueError(message)
        return self

    @property
    def affirmative(self) -> bool:
        """Return whether the recorded decision is the affirmative one for its scope kind."""
        return self.decision == AFFIRMATIVE_DECISIONS[self.scope.kind]


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

    schema_version: Literal[18, 19] = 19
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
    confirmations: tuple[DeliveryUserConfirmation, ...] | None = Field(
        default=None, min_length=1, max_length=MAX_LEDGER_CONFIRMATIONS, exclude_if=_omit_when_none
    )

    @model_validator(mode="after")
    def _validate_version_content(self) -> DeliveryFrontier:
        confirmations = self.confirmations or ()
        identities = tuple(item.confirmation_id for item in confirmations)
        if len(identities) != len(set(identities)) or len({item.change_id for item in confirmations}) > 1:
            message = "Delivery confirmation ledger entries must be unique and bind one Change"
            raise ValueError(message)
        if self.schema_version == _READABLE_LEGACY_FRONTIER_SCHEMA_VERSION and frontier_has_n03_content(self):
            message = "Delivery frontier schema 18 cannot carry schema-19 evidence or confirmations"
            raise ValueError(message)
        return self

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
    observations: tuple[DeliveryAnyObservationReceipt, ...] = ()
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

    @model_validator(mode="after")
    def _validate_scoped_request(self) -> BlockDelivery:
        if self.request is not None and self.request.applies_to is not None and self.request.resolution is not None:
            message = "a scoped request cannot carry a resolution when it is created"
            raise ValueError(message)
        return self


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


type DeliveryEvidenceGapReason = Literal[
    "uncovered",
    "unknown-legacy-only",
    "missing",
    "failed",
    "legacy-observation",
    "unknown-acceptance",
    "stale-acceptance-version",
    "confirmation-unresolved",
    "confirmation-not-applicable",
    "review-basis-missing",
    "review-basis-stale",
    "review-observations-mismatch",
    "finalization-basis-unavailable",
    "finalization-context-oversized",
]
MAX_EVIDENCE_GAPS = 64


class DeliveryEvidenceGap(_DeliveryModel):
    """One bounded reason why evidence cannot support a result or finalization."""

    acceptance_id: str | None = Field(default=None, pattern=ACCEPTANCE_ID_PATTERN)
    observation_id: str | None = Field(default=None, pattern=_SHA256)
    reason: DeliveryEvidenceGapReason


class DeliveryAcceptanceEvidenceError(DeliveryRuntimeConflictError):
    """Submitted evidence does not satisfy the admitted acceptance authority; nothing was written."""

    code = "ERR_DELIVERY_ACCEPTANCE_EVIDENCE"
    retry_safe = False

    def __init__(self, gaps: tuple[DeliveryEvidenceGap, ...]) -> None:
        self.gaps = gaps[:MAX_EVIDENCE_GAPS]
        reasons = ", ".join(dict.fromkeys(gap.reason for gap in self.gaps))
        super().__init__(f"acceptance evidence is insufficient: {reasons}")


type DeliveryConfirmationRefusal = Literal[
    "confirmation-required", "declined", "channel-unavailable", "ledger-full", "question-closed"
]


class DeliveryConfirmationError(DeliveryRuntimeConflictError):
    """A scoped request needs a user confirmation that the boundary did not provide."""

    code = "ERR_DELIVERY_CONFIRMATION"
    retry_safe = False

    def __init__(self, reason: DeliveryConfirmationRefusal, detail: str | None = None) -> None:
        self.reason = reason
        super().__init__(f"{reason}: {detail}" if detail else reason)


def frontier_has_n03_content(frontier: DeliveryFrontier) -> bool:
    """Return whether a frontier holds evidence, requests, or confirmations that need schema 19."""
    if frontier.confirmations is not None:
        return True
    finalization = frontier.finalization
    if finalization is not None and finalization.schema_version != _LEGACY_FINALIZATION_SCHEMA_VERSION:
        return True
    return any(binding_has_n03_content(binding) for binding in frontier.bindings)


def binding_has_n03_content(binding: OutcomeAuthorityBinding) -> bool:
    """Return whether one binding holds content that only frontier 19 and receipts 2 may carry."""
    if any(result.has_n03_content for result in binding.results):
        return True
    if binding.result_candidate is not None and binding.result_candidate.result.has_n03_content:
        return True
    if any(request.has_n03_content for request in binding.requests):
        return True
    attention = binding.recovery_attention
    diagnostic = attention.diagnostic_transition if attention is not None else None
    return (
        isinstance(diagnostic, BlockDelivery) and diagnostic.request is not None and diagnostic.request.has_n03_content
    )


_STAGE_ORDER = {
    DeliveryStage.DESIGN: 0,
    DeliveryStage.PLANNING: 1,
    DeliveryStage.IMPLEMENTATION: 2,
    DeliveryStage.COMPLETED: 3,
}


_LEGACY_FRONTIER_SCHEMA_VERSION = 17


_READABLE_LEGACY_FRONTIER_SCHEMA_VERSION = 18


_FRONTIER_SCHEMA_VERSION = 19


_LEGACY_FINALIZATION_SCHEMA_VERSION = 2


_TYPED_EVIDENCE_SCHEMA_VERSION = 2


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
# Attention writers outside the central registry (they guard terminal state themselves).
_DISPOSITION_MUTATIONS = frozenset({"capture_change_disposition", "resolve_change_disposition"})

# N09-A2 K7: classes of every frontier writer while a Pause request exists.
# Completion: allowed anywhere (the started owner ends, settles or records its own effect).
_PAUSE_COMPLETION_MUTATIONS = frozenset(
    {
        "remove_active_claim",
        "publish_output",
        "publish_plan",
        "publish_result",
        "transition",
        "settle_planning_retry",
        "settle_builder_invocation",
        "_retry",
        "complete_recovery",
        "publish_recovery_attention",
        "remove_integration_repair_claim",
        "finalize_change",
        "record_checkpoint_branch_publication",
        "acknowledge_checkpoint_publication",
        "record_checkpoint_failure",
        "record_publication_identity",
        "defer_change",
        "resume_change",
        "abandon_change",
    }
)
# Owner-drain: allowed only inside a matching K2 drain-authority token.
_PAUSE_OWNER_DRAIN_MUTATIONS = frozenset(
    {
        "record_target_sync",
        "capture_target_sync_conflict",
        "mark_awaiting_merge",
        "clear_ready_for_head_change",
        "reconcile_finalization_head",
        "record_publication_successor",
        "record_design_package_snapshot",
        "latch_merged_pull_request",
        "complete_change",
        "capture_change_disposition",
        "record_external_head_promotion",
    }
)
# Pause-gated: new work; refused while a request exists.
_PAUSE_GATED_MUTATIONS = frozenset(
    {
        "queue_admitted_design_checkpoint",
        "queue_explicit_checkpoint",
        "record_resolved_target_sync",
        "record_target_sync_abort",
        "record_external_head_adoption",
        "reconcile_pull_request_draft_state",
        "prepare_review_repair",
        "prepare_completed_outcome_repair",
        "activate_claim",
        "resolve_request",
        "unblock",
        "administrative_move",
        "resolve_change_disposition",
    }
)


def pause_mutation_class(operation: str | None) -> Literal["completion", "owner-drain", "pause-gated"]:
    """Classify one frontier writer for Pause (K7); unknown or absent names are pause-gated."""
    if operation in _PAUSE_COMPLETION_MUTATIONS:
        return "completion"
    if operation in _PAUSE_OWNER_DRAIN_MUTATIONS:
        return "owner-drain"
    return "pause-gated"


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


def _model_content(model: BaseModel) -> bytes:
    payload = model.model_dump(mode="json")
    return (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _normalize_frontier(frontier: DeliveryFrontier) -> DeliveryFrontier:
    if frontier.schema_version == _FRONTIER_SCHEMA_VERSION:
        return frontier
    return frontier.model_copy(update={"schema_version": _FRONTIER_SCHEMA_VERSION})


def _receipt_digest(receipt: BaseModel, identity_field: str) -> str:
    payload = receipt.model_dump(mode="json", exclude={identity_field})
    content = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(content).hexdigest()


def _finalization_invalidation_digest(receipt: DeliveryFinalizationInvalidationReceipt) -> str:
    payload = receipt.model_dump(mode="json", exclude={"invalidation_id"})
    content = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(content).hexdigest()


def _reference(message: str, cause: Exception | None = None) -> None:
    if cause is None:
        raise DeliveryRuntimeReferenceError(message)
    raise DeliveryRuntimeReferenceError(message) from cause


# Forward references resolve only now; incomplete models fail bare serialization in adapters.
DeliveryRecoveryAttention.model_rebuild()


OutcomeAuthorityBinding.model_rebuild()


DeliveryFrontier.model_rebuild()
