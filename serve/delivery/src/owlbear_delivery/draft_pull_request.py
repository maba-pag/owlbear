"""Idempotent draft pull-request creation for published Change branches."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Literal, Never, Protocol

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from owlbear_delivery.publication_provider import (
    CreateDraftPublicationPullRequest,
    FindPublicationPullRequest,
    ObservePublicationChecks,
    PublicationCheckSnapshot,
    PublicationProvider,
    PublicationProviderError,
    PublicationProviderFailureCode,
    PublicationPullRequest,
    SetPublicationPullRequestDraftState,
    UpdatePublicationPullRequest,
)
from owlbear_delivery.storage_io import atomic_write, locked_roots

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

_CHANGE_ID_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
_CHANGE_BRANCH_PATTERN = r"^owlbear/change/[a-z0-9]+(?:-[a-z0-9]+)*(?:\+s[1-9][0-9]*)?$"
_SUCCESSOR_BRANCH_PATTERN = r"^owlbear/change/[a-z0-9]+(?:-[a-z0-9]+)*\+s[1-9][0-9]*$"
_OPERATION_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$"
_SHA_PATTERN = r"^[0-9a-f]{40}$"
_GENERATED_START = "<!-- owlbear-generated:start -->"
_GENERATED_END = "<!-- owlbear-generated:end -->"
_MAX_PULL_REQUEST_BODY_LENGTH = 65_536


class _DraftPullRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class CreateOrReconcileDraftPullRequest(_DraftPullRequestModel):
    """Bind one stable operation to the first published Change checkpoint."""

    change_id: str = Field(pattern=_CHANGE_ID_PATTERN)
    operation_id: str = Field(pattern=_OPERATION_ID_PATTERN)
    published_head: str = Field(pattern=_SHA_PATTERN)
    title: str = Field(min_length=1, max_length=256)
    generated_summary: str = Field(min_length=1, max_length=50_000)

    @model_validator(mode="after")
    def _validate_generated_summary(self) -> CreateOrReconcileDraftPullRequest:
        _require_safe_generated_summary(self.generated_summary)
        return self


class SupersedeDraftPullRequest(_DraftPullRequestModel):
    """Bind one successor draft PR to the current predecessor publication."""

    change_id: str = Field(pattern=_CHANGE_ID_PATTERN)
    operation_id: str = Field(pattern=_OPERATION_ID_PATTERN)
    expected_predecessor_receipt_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    predecessor_branch: str = Field(pattern=_CHANGE_BRANCH_PATTERN)
    predecessor_head: str = Field(pattern=_SHA_PATTERN)
    successor_branch: str = Field(pattern=_SUCCESSOR_BRANCH_PATTERN)
    superseding_head: str = Field(pattern=_SHA_PATTERN)
    title: str = Field(min_length=1, max_length=256)
    generated_summary: str = Field(min_length=1, max_length=50_000)

    @model_validator(mode="after")
    def _validate_request(self) -> SupersedeDraftPullRequest:
        _require_safe_generated_summary(self.generated_summary)
        if not _is_change_publication_branch(self.predecessor_branch, self.change_id):
            msg = "predecessor branch does not belong to the requested Change"
            raise ValueError(msg)
        if not _is_change_publication_branch(self.successor_branch, self.change_id):
            msg = "successor branch does not belong to the requested Change"
            raise ValueError(msg)
        if self.predecessor_branch == self.successor_branch:
            msg = "supersession requires a distinct successor branch"
            raise ValueError(msg)
        return self


class UpdateGeneratedPullRequestSummary(_DraftPullRequestModel):
    """Replace only OwlBear's generated block at one published Change head."""

    change_id: str = Field(pattern=_CHANGE_ID_PATTERN)
    operation_id: str = Field(pattern=_OPERATION_ID_PATTERN)
    published_head: str = Field(pattern=_SHA_PATTERN)
    generated_summary: str = Field(min_length=1, max_length=50_000)

    @model_validator(mode="after")
    def _validate_generated_summary(self) -> UpdateGeneratedPullRequestSummary:
        _require_safe_generated_summary(self.generated_summary)
        return self


class ObserveChangePublicationChecks(_DraftPullRequestModel):
    """Observe provider checks for one Change-bound published head."""

    change_id: str = Field(pattern=_CHANGE_ID_PATTERN)
    published_head: str = Field(pattern=_SHA_PATTERN)


class ObserveChangePublicationPullRequest(_DraftPullRequestModel):
    """Observe the current provider state of one bound publication pull request."""

    change_id: str = Field(pattern=_CHANGE_ID_PATTERN)


class ReadChangePublicationHistory(_DraftPullRequestModel):
    """Read ordered provider publication identities for one Change."""

    change_id: str = Field(pattern=_CHANGE_ID_PATTERN)


class ReadChangePublicationCheckObservations(_DraftPullRequestModel):
    """Read durable provider check observations for one exact bound PR head."""

    change_id: str = Field(pattern=_CHANGE_ID_PATTERN)
    repository: str = Field(min_length=3, pattern=r"^[^\s/]+/[^\s/]+$")
    number: int = Field(gt=0)
    exact_commit: str = Field(pattern=_SHA_PATTERN)


class _ChangePullRequestDraftStateRequest(_DraftPullRequestModel):
    change_id: str = Field(pattern=_CHANGE_ID_PATTERN)
    operation_id: str = Field(pattern=_OPERATION_ID_PATTERN)
    finalization_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    exact_head: str = Field(pattern=_SHA_PATTERN)


class MarkChangePullRequestReady(_ChangePullRequestDraftStateRequest):
    """Bind one stable operation to an exact finalized pull-request head."""


class ReturnChangePullRequestToDraft(_ChangePullRequestDraftStateRequest):
    """Return one drifted finalized pull request to draft state."""


class DraftPullRequestPublicationReceipt(_DraftPullRequestModel):
    """Immutable local binding to one provider-observed draft pull request."""

    schema_version: Literal[1] = 1
    receipt_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    operation_id: str = Field(pattern=_OPERATION_ID_PATTERN)
    change_id: str = Field(pattern=_CHANGE_ID_PATTERN)
    repository: str = Field(min_length=3, pattern=r"^[^\s/]+/[^\s/]+$")
    number: int = Field(gt=0)
    node_id: str = Field(min_length=1)
    head_branch: str = Field(min_length=1)
    head_sha: str = Field(pattern=_SHA_PATTERN)
    base_branch: str = Field(min_length=1)
    provider_evidence_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _validate_receipt_id(self) -> DraftPullRequestPublicationReceipt:
        payload = self.model_dump(mode="json", exclude={"receipt_id"})
        if self.receipt_id != _digest(payload):
            msg = "draft pull-request receipt identity is invalid"
            raise ValueError(msg)
        return self


class DraftPullRequestPublicationHistory(_DraftPullRequestModel):
    """Ordered immutable publication identities for one Change."""

    schema_version: Literal[1] = 1
    history_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    change_id: str = Field(pattern=_CHANGE_ID_PATTERN)
    publications: tuple[DraftPullRequestPublicationReceipt, ...] = Field(min_length=1)
    predecessor_receipt_ids: tuple[str | None, ...] = Field(min_length=1)
    current_receipt_id: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _validate_history(self) -> DraftPullRequestPublicationHistory:
        if len(self.publications) != len(self.predecessor_receipt_ids):
            msg = "publication history entries and predecessor identities must align"
            raise ValueError(msg)
        receipt_ids = tuple(publication.receipt_id for publication in self.publications)
        if len(receipt_ids) != len(set(receipt_ids)):
            msg = "publication history receipt identities must be unique"
            raise ValueError(msg)
        if any(publication.change_id != self.change_id for publication in self.publications):
            msg = "publication history entries must bind the same Change"
            raise ValueError(msg)
        if self.predecessor_receipt_ids[0] is not None:
            msg = "the first publication history entry cannot have a predecessor"
            raise ValueError(msg)
        for index in range(1, len(receipt_ids)):
            if self.predecessor_receipt_ids[index] != receipt_ids[index - 1]:
                msg = "publication history entries must form one ordered predecessor chain"
                raise ValueError(msg)
        if self.current_receipt_id != receipt_ids[-1]:
            msg = "publication history current identity must be its last entry"
            raise ValueError(msg)
        payload = self.model_dump(mode="json", exclude={"history_id"})
        if self.history_id != _digest(payload):
            msg = "publication history identity is invalid"
            raise ValueError(msg)
        return self


class DraftPullRequestSupersessionReceipt(_DraftPullRequestModel):
    """Immutable evidence linking one predecessor PR publication to its successor."""

    schema_version: Literal[1] = 1
    receipt_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    operation_id: str = Field(pattern=_OPERATION_ID_PATTERN)
    change_id: str = Field(pattern=_CHANGE_ID_PATTERN)
    predecessor_receipt_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    predecessor_branch: str = Field(pattern=_CHANGE_BRANCH_PATTERN)
    predecessor_head: str = Field(pattern=_SHA_PATTERN)
    successor_receipt_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    successor_branch: str = Field(pattern=_SUCCESSOR_BRANCH_PATTERN)
    superseding_head: str = Field(pattern=_SHA_PATTERN)
    repository: str = Field(min_length=3, pattern=r"^[^\s/]+/[^\s/]+$")
    successor_number: int = Field(gt=0)
    successor_node_id: str = Field(min_length=1)
    base_branch: str = Field(min_length=1)
    provider_evidence_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    predecessor_publication: DraftPullRequestPublicationReceipt
    successor_publication: DraftPullRequestPublicationReceipt

    @model_validator(mode="after")
    def _validate_receipt_id(self) -> DraftPullRequestSupersessionReceipt:
        if (
            self.predecessor_publication.receipt_id != self.predecessor_receipt_id
            or self.predecessor_publication.change_id != self.change_id
            or self.predecessor_publication.head_branch != self.predecessor_branch
            or self.predecessor_publication.head_sha != self.predecessor_head
            or self.successor_publication.receipt_id != self.successor_receipt_id
            or self.successor_publication.change_id != self.change_id
            or self.successor_publication.repository != self.repository
            or self.successor_publication.number != self.successor_number
            or self.successor_publication.node_id != self.successor_node_id
            or self.successor_publication.head_branch != self.successor_branch
            or self.successor_publication.head_sha != self.superseding_head
            or self.successor_publication.base_branch != self.base_branch
            or self.successor_publication.provider_evidence_digest != self.provider_evidence_digest
        ):
            msg = "draft pull-request supersession receipt does not match its successor publication"
            raise ValueError(msg)
        payload = self.model_dump(mode="json", exclude={"receipt_id"})
        if self.receipt_id != _digest(payload):
            msg = "draft pull-request supersession receipt identity is invalid"
            raise ValueError(msg)
        return self


class GeneratedPullRequestSummaryReceipt(_DraftPullRequestModel):
    """Immutable evidence of one exact generated-block update."""

    schema_version: Literal[1] = 1
    receipt_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    operation_id: str = Field(pattern=_OPERATION_ID_PATTERN)
    change_id: str = Field(pattern=_CHANGE_ID_PATTERN)
    repository: str = Field(min_length=3, pattern=r"^[^\s/]+/[^\s/]+$")
    number: int = Field(gt=0)
    head_sha: str = Field(pattern=_SHA_PATTERN)
    body_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    provider_evidence_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _validate_receipt_id(self) -> GeneratedPullRequestSummaryReceipt:
        payload = self.model_dump(mode="json", exclude={"receipt_id"})
        if self.receipt_id != _digest(payload):
            msg = "generated pull-request summary receipt identity is invalid"
            raise ValueError(msg)
        return self


class _PublicationCheckObservationPayload(_DraftPullRequestModel):
    schema_version: Literal[1] = 1
    change_id: str = Field(pattern=_CHANGE_ID_PATTERN)
    repository: str = Field(min_length=3, pattern=r"^[^\s/]+/[^\s/]+$")
    number: int = Field(gt=0)
    exact_commit: str = Field(pattern=_SHA_PATTERN)
    observation_kind: Literal["github-checks"] = "github-checks"
    command_or_procedure: Literal["observe-publication-checks"] = "observe-publication-checks"
    observer_or_runner_identity: Literal["github"] = "github"
    observed_at: datetime
    snapshot: PublicationCheckSnapshot
    provider_evidence_digest: str = Field(pattern=r"^[0-9a-f]{64}$")


class PublicationCheckObservationReceipt(_PublicationCheckObservationPayload):
    """Durable exact-head evidence from one fixed provider check observation."""

    observation_id: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _validate_receipt(self) -> PublicationCheckObservationReceipt:
        if self.observed_at.tzinfo is None:
            msg = "check observation timestamp must include a timezone"
            raise ValueError(msg)
        if (
            self.snapshot.repository != self.repository
            or self.snapshot.number != self.number
            or self.snapshot.head_sha != self.exact_commit
            or self.provider_evidence_digest != _digest(self.snapshot.model_dump(mode="json"))
        ):
            msg = "check observation receipt does not match its provider snapshot"
            raise ValueError(msg)
        payload = self.model_dump(mode="json", exclude={"observation_id"})
        if self.observation_id != _digest(payload):
            msg = "check observation receipt identity is invalid"
            raise ValueError(msg)
        return self


class _PublicationPullRequestObservationPayload(_DraftPullRequestModel):
    schema_version: Literal[1] = 1
    change_id: str = Field(pattern=_CHANGE_ID_PATTERN)
    observed_at: datetime
    snapshot: PublicationPullRequest
    provider_evidence_digest: str = Field(pattern=r"^[0-9a-f]{64}$")


class PublicationPullRequestObservationReceipt(_PublicationPullRequestObservationPayload):
    """Durable provider evidence for the current bound pull-request head and state."""

    mergeable: bool | None = None
    merge_state_status: str | None = Field(default=None, min_length=1)
    observation_id: str = Field(pattern=r"^[0-9a-f]{64}$")

    def _provider_evidence(self) -> dict[str, object]:
        evidence = self.snapshot.model_dump(mode="json")
        if "mergeable" in self.model_fields_set:
            evidence["mergeable"] = self.mergeable
        if "merge_state_status" in self.model_fields_set:
            evidence["merge_state_status"] = self.merge_state_status
        return evidence

    @model_validator(mode="after")
    def _validate_receipt(self) -> PublicationPullRequestObservationReceipt:
        if self.observed_at.tzinfo is None:
            msg = "pull-request observation timestamp must include a timezone"
            raise ValueError(msg)
        if self.provider_evidence_digest != _digest(self._provider_evidence()):
            msg = "pull-request observation receipt does not match its provider snapshot"
            raise ValueError(msg)
        payload = self.model_dump(mode="json", exclude={"observation_id"}, exclude_unset=True)
        if self.observation_id != _digest(payload):
            msg = "pull-request observation receipt identity is invalid"
            raise ValueError(msg)
        return self


class _PullRequestDraftStateReceipt(_DraftPullRequestModel):
    schema_version: Literal[1] = 1
    receipt_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    operation_id: str = Field(pattern=_OPERATION_ID_PATTERN)
    change_id: str = Field(pattern=_CHANGE_ID_PATTERN)
    finalization_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    repository: str = Field(min_length=3, pattern=r"^[^\s/]+/[^\s/]+$")
    number: int = Field(gt=0)
    node_id: str = Field(min_length=1)
    head_sha: str = Field(pattern=_SHA_PATTERN)
    draft: bool
    observed_at: datetime
    provider_evidence_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _validate_receipt(self) -> _PullRequestDraftStateReceipt:
        if self.observed_at.tzinfo is None:
            msg = "pull-request draft-state timestamp must include a timezone"
            raise ValueError(msg)
        payload = self.model_dump(mode="json", exclude={"receipt_id"})
        if self.receipt_id != _digest(payload):
            msg = "pull-request draft-state receipt identity is invalid"
            raise ValueError(msg)
        return self


class PullRequestReadyReceipt(_PullRequestDraftStateReceipt):
    """Durable provider evidence that one finalized pull request is ready."""

    draft: Literal[False] = False


class PullRequestDraftReceipt(_PullRequestDraftStateReceipt):
    """Durable provider evidence that one invalidated pull request is draft."""

    draft: Literal[True] = True


class _DraftPullRequestOperation(_DraftPullRequestModel):
    schema_version: Literal[1] = 1
    operation_id: str = Field(pattern=_OPERATION_ID_PATTERN)
    change_id: str = Field(pattern=_CHANGE_ID_PATTERN)
    repository: str = Field(min_length=3, pattern=r"^[^\s/]+/[^\s/]+$")
    head_branch: str = Field(min_length=1)
    head_sha: str = Field(pattern=_SHA_PATTERN)
    base_branch: str = Field(min_length=1)
    title: str = Field(min_length=1, max_length=256)
    body: str = Field(min_length=1, max_length=_MAX_PULL_REQUEST_BODY_LENGTH)


class _DraftPullRequestSupersessionOperation(_DraftPullRequestModel):
    schema_version: Literal[1] = 1
    operation_id: str = Field(pattern=_OPERATION_ID_PATTERN)
    change_id: str = Field(pattern=_CHANGE_ID_PATTERN)
    repository: str = Field(min_length=3, pattern=r"^[^\s/]+/[^\s/]+$")
    expected_predecessor_receipt_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    predecessor_branch: str = Field(pattern=_CHANGE_BRANCH_PATTERN)
    predecessor_head: str = Field(pattern=_SHA_PATTERN)
    successor_branch: str = Field(pattern=_SUCCESSOR_BRANCH_PATTERN)
    superseding_head: str = Field(pattern=_SHA_PATTERN)
    base_branch: str = Field(min_length=1)
    title: str = Field(min_length=1, max_length=256)
    body: str = Field(min_length=1, max_length=_MAX_PULL_REQUEST_BODY_LENGTH)

    @property
    def head_branch(self) -> str:
        """Project the shared provider-operation branch field."""
        return self.successor_branch

    @property
    def head_sha(self) -> str:
        """Project the shared provider-operation head field."""
        return self.superseding_head


class _PublicationOperationLike(Protocol):
    change_id: str
    repository: str
    head_branch: str
    head_sha: str
    base_branch: str
    title: str
    body: str


class _GeneratedSummaryOperation(_DraftPullRequestModel):
    schema_version: Literal[1] = 1
    operation_id: str = Field(pattern=_OPERATION_ID_PATTERN)
    change_id: str = Field(pattern=_CHANGE_ID_PATTERN)
    repository: str = Field(min_length=3, pattern=r"^[^\s/]+/[^\s/]+$")
    number: int = Field(gt=0)
    node_id: str = Field(min_length=1)
    head_branch: str = Field(min_length=1)
    head_sha: str = Field(pattern=_SHA_PATTERN)
    base_branch: str = Field(min_length=1)
    generated_summary_digest: str = Field(pattern=r"^[0-9a-f]{64}$")


class _DraftStateOperation(_DraftPullRequestModel):
    schema_version: Literal[1] = 1
    operation_id: str = Field(pattern=_OPERATION_ID_PATTERN)
    change_id: str = Field(pattern=_CHANGE_ID_PATTERN)
    finalization_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    repository: str = Field(min_length=3, pattern=r"^[^\s/]+/[^\s/]+$")
    number: int = Field(gt=0)
    node_id: str = Field(min_length=1)
    head_branch: str = Field(min_length=1)
    head_sha: str = Field(pattern=_SHA_PATTERN)
    base_branch: str = Field(min_length=1)
    draft: bool


type _PublicationRequest = (
    CreateOrReconcileDraftPullRequest
    | MarkChangePullRequestReady
    | ObserveChangePublicationChecks
    | ObserveChangePublicationPullRequest
    | ReadChangePublicationHistory
    | ReadChangePublicationCheckObservations
    | ReturnChangePullRequestToDraft
    | SupersedeDraftPullRequest
    | UpdateGeneratedPullRequestSummary
)


class DraftPullRequestPublisher:
    """Create or reconcile one exact draft PR without provider transport knowledge."""

    def __init__(
        self,
        provider: PublicationProvider,
        *,
        repository: str,
        target_branch: str,
        state_root: Path,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._provider = provider
        self._repository = repository
        self._target_branch = target_branch
        self._state_root = state_root.resolve()
        self._clock = clock
        if state_root.is_symlink():
            msg = "draft pull-request state root must not be a symlink"
            raise ValueError(msg)

    @property
    def repository(self) -> str:
        """Return the configured provider repository identity."""
        return self._repository

    @property
    def target_branch(self) -> str:
        """Return the configured pull-request target branch."""
        return self._target_branch

    def publish(self, request: CreateOrReconcileDraftPullRequest) -> DraftPullRequestPublicationReceipt:
        """Create or recover the unique draft PR for one first checkpoint."""
        lock_root = self._state_root / "locks" / request.change_id
        with locked_roots((lock_root,)):
            return self._publish_locked(request)

    def supersede(self, request: SupersedeDraftPullRequest) -> DraftPullRequestSupersessionReceipt:
        """Create or recover one successor draft PR for an exact predecessor publication."""
        lock_root = self._state_root / "locks" / request.change_id
        with locked_roots((lock_root,)):
            return self._supersede_locked(request)

    def read_publication_history(
        self,
        request: ReadChangePublicationHistory,
    ) -> DraftPullRequestPublicationHistory | None:
        """Read ordered publication identities without observing provider state."""
        lock_root = self._state_root / "locks" / request.change_id
        with locked_roots((lock_root,)):
            history = self._read_history(request)
            if history is not None:
                return history
            receipt = self._read_receipt(request)
            if receipt is None:
                return None
            return _publication_history((receipt,), (None,), request.change_id)

    def update_generated_summary(
        self,
        request: UpdateGeneratedPullRequestSummary,
    ) -> GeneratedPullRequestSummaryReceipt:
        """Replace or reconcile one generated PR summary without changing user prose."""
        lock_root = self._state_root / "locks" / request.change_id
        with locked_roots((lock_root,)):
            return self._update_generated_summary_locked(request)

    def observe_checks(self, request: ObserveChangePublicationChecks) -> PublicationCheckObservationReceipt:
        """Observe and durably record checks for one exact Change publication."""
        lock_root = self._state_root / "locks" / request.change_id
        with locked_roots((lock_root,)):
            return self._observe_checks_locked(request)

    def observe_pull_request(
        self,
        request: ObserveChangePublicationPullRequest,
    ) -> PublicationPullRequestObservationReceipt | None:
        """Observe and durably record current provider state for one bound pull request."""
        lock_root = self._state_root / "locks" / request.change_id
        with locked_roots((lock_root,)):
            publication = self._read_receipt(request)
            if publication is None:
                return None
            snapshot = self._provider.read_pull_request(publication.repository, publication.number)
            if (
                snapshot.repository != publication.repository
                or snapshot.number != publication.number
                or snapshot.node_id != publication.node_id
                or snapshot.head_branch != publication.head_branch
                or snapshot.base_branch != publication.base_branch
            ):
                self._conflict(request, "provider pull request does not match the bound publication identity")
            evidence = snapshot.model_dump(mode="json")
            evidence["mergeable"] = snapshot.mergeable
            evidence["merge_state_status"] = snapshot.merge_state_status
            evidence_digest = _digest(evidence)
            payload = _PublicationPullRequestObservationPayload(
                change_id=request.change_id,
                observed_at=self._clock(),
                snapshot=snapshot,
                provider_evidence_digest=evidence_digest,
            )
            values = {
                "mergeable": snapshot.mergeable,
                "merge_state_status": snapshot.merge_state_status,
                **payload.model_dump(),
            }
            candidate = PublicationPullRequestObservationReceipt.model_construct(observation_id="0" * 64, **values)
            receipt = PublicationPullRequestObservationReceipt(
                observation_id=_digest(candidate.model_dump(mode="json", exclude={"observation_id"})),
                **values,
            )
            return self._publish_or_read(
                self._pull_request_observation_path(request, evidence_digest),
                receipt,
                PublicationPullRequestObservationReceipt,
                request,
            )

    def read_check_observations(
        self,
        request: ReadChangePublicationCheckObservations,
    ) -> tuple[PublicationCheckObservationReceipt, ...]:
        """Read every durable check observation matching one bound PR and exact head."""
        lock_root = self._state_root / "locks" / request.change_id
        with locked_roots((lock_root,)):
            root = self._state_root / "check-observations" / request.change_id
            if root.is_symlink():
                self._invalid_response(request, "stored check observation directory is invalid")
            if not root.exists():
                return ()
            if not root.is_dir():
                self._invalid_response(request, "stored check observation directory is invalid")
            receipts = tuple(
                receipt
                for path in sorted(root.glob("*.json"))
                for receipt in (self._read_state(path, PublicationCheckObservationReceipt, request),)
                if receipt is not None
                and receipt.change_id == request.change_id
                and receipt.repository == request.repository
                and receipt.number == request.number
                and receipt.exact_commit == request.exact_commit
            )
            return tuple(sorted(receipts, key=lambda receipt: receipt.observation_id))

    def mark_ready(self, request: MarkChangePullRequestReady) -> PullRequestReadyReceipt:
        """Mark one exact finalized pull request ready and retain provider evidence."""
        lock_root = self._state_root / "locks" / request.change_id
        with locked_roots((lock_root,)):
            return self._set_draft_state(request, draft=False, receipt_type=PullRequestReadyReceipt)

    def return_to_draft(self, request: ReturnChangePullRequestToDraft) -> PullRequestDraftReceipt:
        """Return one invalidated pull request to draft and retain provider evidence."""
        lock_root = self._state_root / "locks" / request.change_id
        with locked_roots((lock_root,)):
            return self._set_draft_state(request, draft=True, receipt_type=PullRequestDraftReceipt)

    def _set_draft_state[ReceiptT: _PullRequestDraftStateReceipt](
        self,
        request: _ChangePullRequestDraftStateRequest,
        *,
        draft: bool,
        receipt_type: type[ReceiptT],
    ) -> ReceiptT:
        publication = self._read_receipt(request)
        if publication is None:
            self._conflict(request, "Change has no draft pull-request publication receipt")
        operation = _DraftStateOperation(
            operation_id=request.operation_id,
            change_id=request.change_id,
            finalization_id=request.finalization_id,
            repository=publication.repository,
            number=publication.number,
            node_id=publication.node_id,
            head_branch=publication.head_branch,
            head_sha=request.exact_head,
            base_branch=publication.base_branch,
            draft=draft,
        )
        operation_path = self._draft_state_path("draft-state-operations", request)
        stored_operation = self._publish_or_read(operation_path, operation, _DraftStateOperation, request)
        if stored_operation != operation:
            self._conflict(request, "pull-request draft-state operation differs from the stored operation")
        receipt_path = self._draft_state_path("draft-state-receipts", request)
        existing = self._read_state(receipt_path, receipt_type, request)
        current = self._provider.read_pull_request(operation.repository, operation.number)
        self._validate_draft_state_identity(current, operation, request)
        if existing is not None:
            if current.draft != draft:
                self._conflict(request, "provider pull request no longer matches the draft-state receipt")
            return existing
        if current.draft != draft:
            self._mutate_draft_state(operation)
        observed = self._provider.read_pull_request(operation.repository, operation.number)
        self._validate_draft_state_identity(observed, operation, request)
        if observed.draft != draft:
            self._invalid_response(request, "provider did not apply the requested pull-request draft state")
        return self._bind_draft_state_receipt(operation, observed, request, receipt_type, receipt_path)

    def _mutate_draft_state(
        self,
        operation: _DraftStateOperation,
    ) -> None:
        try:
            self._provider.set_pull_request_draft_state(
                SetPublicationPullRequestDraftState(
                    repository=operation.repository,
                    number=operation.number,
                    node_id=operation.node_id,
                    expected_head_sha=operation.head_sha,
                    draft=operation.draft,
                )
            )
        except PublicationProviderError as exc:
            if exc.code is not PublicationProviderFailureCode.RESPONSE_UNKNOWN:
                raise

    def _bind_draft_state_receipt[ReceiptT: _PullRequestDraftStateReceipt](
        self,
        operation: _DraftStateOperation,
        observed: PublicationPullRequest,
        request: _ChangePullRequestDraftStateRequest,
        receipt_type: type[ReceiptT],
        receipt_path: Path,
    ) -> ReceiptT:
        observed_at = self._clock()
        payload = {
            "schema_version": 1,
            "operation_id": operation.operation_id,
            "change_id": operation.change_id,
            "finalization_id": operation.finalization_id,
            "repository": operation.repository,
            "number": operation.number,
            "node_id": operation.node_id,
            "head_sha": operation.head_sha,
            "draft": operation.draft,
            "observed_at": observed_at,
            "provider_evidence_digest": _digest(observed.model_dump(mode="json")),
        }
        candidate = receipt_type.model_construct(receipt_id="0" * 64, **payload)
        receipt_id = _digest(candidate.model_dump(mode="json", exclude={"receipt_id"}))
        receipt = receipt_type(receipt_id=receipt_id, **payload)
        stored_receipt = self._publish_or_read(receipt_path, receipt, receipt_type, request)
        if stored_receipt != receipt:
            self._conflict(request, "pull-request draft-state receipt differs from the provider result")
        return stored_receipt

    def _validate_draft_state_identity(
        self,
        pull_request: PublicationPullRequest,
        operation: _DraftStateOperation,
        request: _ChangePullRequestDraftStateRequest,
    ) -> None:
        if (
            pull_request.repository != operation.repository
            or pull_request.number != operation.number
            or pull_request.node_id != operation.node_id
            or pull_request.head_branch != operation.head_branch
            or pull_request.head_sha != operation.head_sha
            or pull_request.base_branch != operation.base_branch
            or pull_request.state != "open"
            or pull_request.merged
        ):
            self._conflict(request, "provider pull request moved outside the finalization fence")

    def _observe_checks_locked(
        self,
        request: ObserveChangePublicationChecks,
    ) -> PublicationCheckObservationReceipt:
        publication = self._read_receipt(request)
        if publication is None:
            self._conflict(request, "Change has no draft pull-request publication receipt")
        current = self._provider.read_pull_request(publication.repository, publication.number)
        self._validate_publication_identity(current, publication, request)
        snapshot = self._provider.observe_checks(
            ObservePublicationChecks(
                repository=publication.repository,
                number=publication.number,
                expected_head_sha=request.published_head,
            )
        )
        if (
            snapshot.repository != publication.repository
            or snapshot.number != publication.number
            or snapshot.head_sha != request.published_head
        ):
            self._invalid_response(request, "provider returned checks for a different publication identity")
        observed = self._provider.read_pull_request(publication.repository, publication.number)
        self._validate_publication_identity(observed, publication, request)
        return self._record_check_observation(request, snapshot)

    def _record_check_observation(
        self,
        request: ObserveChangePublicationChecks,
        snapshot: PublicationCheckSnapshot,
    ) -> PublicationCheckObservationReceipt:
        evidence_digest = _digest(snapshot.model_dump(mode="json"))
        path = self._check_observation_path(request, evidence_digest)
        existing = self._read_state(path, PublicationCheckObservationReceipt, request)
        if existing is not None:
            self._validate_check_observation(existing, request, snapshot)
            return existing
        payload = _PublicationCheckObservationPayload(
            change_id=request.change_id,
            repository=snapshot.repository,
            number=snapshot.number,
            exact_commit=snapshot.head_sha,
            observed_at=self._clock(),
            snapshot=snapshot,
            provider_evidence_digest=evidence_digest,
        )
        receipt = PublicationCheckObservationReceipt(
            observation_id=_digest(payload.model_dump(mode="json")),
            **payload.model_dump(),
        )
        return self._publish_or_read(path, receipt, PublicationCheckObservationReceipt, request)

    def _validate_check_observation(
        self,
        receipt: PublicationCheckObservationReceipt,
        request: ObserveChangePublicationChecks,
        snapshot: PublicationCheckSnapshot,
    ) -> None:
        if (
            receipt.change_id != request.change_id
            or receipt.exact_commit != request.published_head
            or receipt.snapshot != snapshot
        ):
            self._conflict(request, "stored check observation differs from the provider snapshot")

    def _update_generated_summary_locked(
        self,
        request: UpdateGeneratedPullRequestSummary,
    ) -> GeneratedPullRequestSummaryReceipt:
        operation = self._read_summary_operation(request)
        if operation is None:
            operation = self._bind_summary_operation(self._summary_operation(request), request)
        else:
            self._validate_summary_request(operation, request)

        existing = self._read_summary_receipt(request)
        if existing is not None:
            self._validate_summary_receipt(existing, operation, request)
            return existing

        current = self._provider.read_pull_request(operation.repository, operation.number)
        self._validate_summary_pull_request(current, operation, request)
        desired_body = _replace_generated_block(current.body, request.generated_summary, request)
        if current.body == desired_body:
            return self._bind_summary_receipt(self._summary_receipt(operation, current), request)

        try:
            updated = self._provider.update_pull_request(
                UpdatePublicationPullRequest(
                    repository=operation.repository,
                    number=operation.number,
                    expected_head_sha=operation.head_sha,
                    expected_title=current.title,
                    expected_body=current.body,
                    title=current.title,
                    body=desired_body,
                )
            )
        except PublicationProviderError as exc:
            if exc.code is not PublicationProviderFailureCode.RESPONSE_UNKNOWN:
                raise
            reconciled = self._provider.read_pull_request(operation.repository, operation.number)
            self._validate_summary_pull_request(reconciled, operation, request)
            reconciled_body = _replace_generated_block(reconciled.body, request.generated_summary, request)
            if reconciled.body == reconciled_body:
                return self._bind_summary_receipt(self._summary_receipt(operation, reconciled), request)
            raise

        self._validate_summary_pull_request(updated, operation, request)
        if updated.title != current.title or updated.body != desired_body:
            self._invalid_response(request, "provider did not apply the generated pull-request summary")
        return self._bind_summary_receipt(self._summary_receipt(operation, updated), request)

    def _summary_operation(self, request: UpdateGeneratedPullRequestSummary) -> _GeneratedSummaryOperation:
        publication = self._read_receipt(request)
        if publication is None:
            self._conflict(request, "Change has no draft pull-request publication receipt")
        current = self._provider.read_pull_request(publication.repository, publication.number)
        self._validate_publication_identity(current, publication, request)
        _generated_block_bounds(current.body, request)
        return _GeneratedSummaryOperation(
            operation_id=request.operation_id,
            change_id=request.change_id,
            repository=publication.repository,
            number=publication.number,
            node_id=publication.node_id,
            head_branch=publication.head_branch,
            head_sha=request.published_head,
            base_branch=publication.base_branch,
            generated_summary_digest=_digest(request.generated_summary),
        )

    def _publish_locked(
        self,
        request: CreateOrReconcileDraftPullRequest,
    ) -> DraftPullRequestPublicationReceipt:
        operation = self._bind_operation(self._operation(request), request)
        existing = self._read_receipt(request)
        if existing is not None:
            history = self._read_history(request)
            if history is not None:
                matching = next(
                    (
                        publication
                        for publication in history.publications
                        if publication.operation_id == operation.operation_id
                    ),
                    None,
                )
                if matching is None:
                    self._conflict(request, "Change publication has already been superseded")
                existing = matching
            self._validate_receipt(existing, operation, request)
            current = self._provider.read_pull_request(existing.repository, existing.number)
            self._validate_publication_identity(current, existing, request)
            if current.body.count(_change_marker(request.change_id)) != 1:
                self._conflict(request, "provider pull request does not contain the exact Change marker")
            return existing

        repository = self._provider.read_repository(self._repository)
        if repository.repository != self._repository:
            self._invalid_response(request, "provider returned a different repository identity")
        pull_request = self._find(operation)
        if pull_request is None:
            pull_request = self._create_or_reconcile(operation)
        self._validate_pull_request(pull_request, operation, request)
        return self._bind_receipt(self._receipt(operation, pull_request), request)

    def _supersede_locked(
        self,
        request: SupersedeDraftPullRequest,
    ) -> DraftPullRequestSupersessionReceipt:
        operation = self._read_supersession_operation(request)
        predecessor: DraftPullRequestPublicationReceipt | None = None
        if operation is None:
            predecessor = self._read_receipt(request)
            if predecessor is None:
                self._conflict(request, "Change has no predecessor pull-request publication receipt")
            self._validate_supersession_predecessor(predecessor, request)
            self._validate_predecessor_pull_request(predecessor, request)
            operation = self._bind_supersession_operation(self._supersession_operation(request), request)
        else:
            self._validate_supersession_operation(operation, request)

        existing = self._read_supersession_receipt(request)
        if existing is not None:
            self._validate_supersession_receipt(existing, operation, request)
            self._persist_superseded_publication(existing, request)
            return existing
        if predecessor is None:
            predecessor = self._predecessor_publication(operation, request)
            self._validate_supersession_predecessor(predecessor, request)
            self._validate_predecessor_pull_request(predecessor, request)

        repository = self._provider.read_repository(operation.repository)
        if repository.repository != operation.repository:
            self._invalid_response(request, "provider returned a different repository identity")
        pull_request = self._find(operation)
        if pull_request is None:
            pull_request = self._create_or_reconcile(operation)
        self._validate_pull_request(pull_request, operation, request)
        successor = self._supersession_publication(operation, pull_request)
        receipt = self._supersession_receipt(
            operation,
            predecessor or self._predecessor_publication(operation, request),
            successor,
            pull_request,
        )
        bound = self._bind_supersession_receipt(receipt, request)
        self._persist_superseded_publication(bound, request)
        return bound

    def _supersession_operation(
        self,
        request: SupersedeDraftPullRequest,
    ) -> _DraftPullRequestSupersessionOperation:
        return _DraftPullRequestSupersessionOperation(
            operation_id=request.operation_id,
            change_id=request.change_id,
            repository=self._repository,
            expected_predecessor_receipt_id=request.expected_predecessor_receipt_id,
            predecessor_branch=request.predecessor_branch,
            predecessor_head=request.predecessor_head,
            successor_branch=request.successor_branch,
            superseding_head=request.superseding_head,
            base_branch=self._target_branch,
            title=request.title,
            body=_draft_body(request.change_id, request.generated_summary),
        )

    def _bind_supersession_operation(
        self,
        operation: _DraftPullRequestSupersessionOperation,
        request: SupersedeDraftPullRequest,
    ) -> _DraftPullRequestSupersessionOperation:
        path = self._supersession_operation_path(request)
        existing = self._publish_or_read(path, operation, _DraftPullRequestSupersessionOperation, request)
        if existing != operation:
            self._conflict(request, "draft pull-request supersession operation differs from stored operation")
        return existing

    def _read_supersession_operation(
        self,
        request: SupersedeDraftPullRequest,
    ) -> _DraftPullRequestSupersessionOperation | None:
        return self._read_state(
            self._supersession_operation_path(request),
            _DraftPullRequestSupersessionOperation,
            request,
        )

    def _validate_supersession_operation(
        self,
        operation: _DraftPullRequestSupersessionOperation,
        request: SupersedeDraftPullRequest,
    ) -> None:
        expected = self._supersession_operation(request)
        if operation != expected:
            self._conflict(request, "draft pull-request supersession request differs from stored operation")

    def _validate_supersession_predecessor(
        self,
        predecessor: DraftPullRequestPublicationReceipt,
        request: SupersedeDraftPullRequest,
    ) -> None:
        if (
            predecessor.receipt_id != request.expected_predecessor_receipt_id
            or predecessor.change_id != request.change_id
            or predecessor.head_branch != request.predecessor_branch
            or predecessor.head_sha != request.predecessor_head
            or predecessor.base_branch != self._target_branch
        ):
            self._conflict(request, "supersession predecessor does not match the requested publication identity")

    def _validate_predecessor_pull_request(
        self,
        predecessor: DraftPullRequestPublicationReceipt,
        request: SupersedeDraftPullRequest,
    ) -> None:
        pull_request = self._provider.read_pull_request(predecessor.repository, predecessor.number)
        if (
            pull_request.repository != predecessor.repository
            or pull_request.number != predecessor.number
            or pull_request.node_id != predecessor.node_id
            or pull_request.head_branch != predecessor.head_branch
            or pull_request.head_sha != predecessor.head_sha
            or pull_request.base_branch != predecessor.base_branch
        ):
            self._conflict(request, "provider predecessor pull request moved outside its publication identity")
        if pull_request.merged:
            self._conflict(request, "merged predecessor pull request cannot be superseded")

    def _predecessor_publication(
        self,
        operation: _DraftPullRequestSupersessionOperation,
        request: SupersedeDraftPullRequest,
    ) -> DraftPullRequestPublicationReceipt:
        history = self._read_history(request)
        if history is not None:
            for publication in history.publications:
                if publication.receipt_id == operation.expected_predecessor_receipt_id:
                    return publication
        receipt = self._read_receipt(request)
        if receipt is not None and receipt.receipt_id == operation.expected_predecessor_receipt_id:
            return receipt
        return self._conflict(request, "supersession predecessor publication is unavailable")

    def _supersession_publication(
        self,
        operation: _DraftPullRequestSupersessionOperation,
        pull_request: PublicationPullRequest,
    ) -> DraftPullRequestPublicationReceipt:
        payload = {
            "schema_version": 1,
            "operation_id": operation.operation_id,
            "change_id": operation.change_id,
            "repository": pull_request.repository,
            "number": pull_request.number,
            "node_id": pull_request.node_id,
            "head_branch": pull_request.head_branch,
            "head_sha": pull_request.head_sha,
            "base_branch": pull_request.base_branch,
            "provider_evidence_digest": _digest(pull_request.model_dump(mode="json")),
        }
        return DraftPullRequestPublicationReceipt(receipt_id=_digest(payload), **payload)

    def _supersession_receipt(
        self,
        operation: _DraftPullRequestSupersessionOperation,
        predecessor: DraftPullRequestPublicationReceipt,
        successor: DraftPullRequestPublicationReceipt,
        pull_request: PublicationPullRequest,
    ) -> DraftPullRequestSupersessionReceipt:
        payload = {
            "schema_version": 1,
            "operation_id": operation.operation_id,
            "change_id": operation.change_id,
            "predecessor_receipt_id": predecessor.receipt_id,
            "predecessor_branch": predecessor.head_branch,
            "predecessor_head": predecessor.head_sha,
            "successor_receipt_id": successor.receipt_id,
            "successor_branch": successor.head_branch,
            "superseding_head": successor.head_sha,
            "repository": pull_request.repository,
            "successor_number": pull_request.number,
            "successor_node_id": pull_request.node_id,
            "base_branch": pull_request.base_branch,
            "provider_evidence_digest": successor.provider_evidence_digest,
            "predecessor_publication": predecessor,
            "successor_publication": successor,
        }
        candidate = DraftPullRequestSupersessionReceipt.model_construct(receipt_id="0" * 64, **payload)
        receipt_id = _digest(candidate.model_dump(mode="json", exclude={"receipt_id"}))
        return DraftPullRequestSupersessionReceipt(receipt_id=receipt_id, **payload)

    def _read_supersession_receipt(
        self,
        request: SupersedeDraftPullRequest,
    ) -> DraftPullRequestSupersessionReceipt | None:
        return self._read_state(
            self._supersession_receipt_path(request),
            DraftPullRequestSupersessionReceipt,
            request,
        )

    def _bind_supersession_receipt(
        self,
        receipt: DraftPullRequestSupersessionReceipt,
        request: SupersedeDraftPullRequest,
    ) -> DraftPullRequestSupersessionReceipt:
        path = self._supersession_receipt_path(request)
        existing = self._publish_or_read(path, receipt, DraftPullRequestSupersessionReceipt, request)
        if existing != receipt:
            self._conflict(request, "Change is already bound to a different supersession receipt")
        return existing

    def _validate_supersession_receipt(
        self,
        receipt: DraftPullRequestSupersessionReceipt,
        operation: _DraftPullRequestSupersessionOperation,
        request: SupersedeDraftPullRequest,
    ) -> None:
        if (
            receipt.operation_id != operation.operation_id
            or receipt.change_id != operation.change_id
            or receipt.predecessor_receipt_id != operation.expected_predecessor_receipt_id
            or receipt.predecessor_branch != operation.predecessor_branch
            or receipt.predecessor_head != operation.predecessor_head
            or receipt.successor_branch != operation.successor_branch
            or receipt.superseding_head != operation.superseding_head
            or receipt.base_branch != operation.base_branch
            or receipt.successor_publication.operation_id != operation.operation_id
        ):
            self._conflict(request, "stored supersession receipt differs from the operation")

    def _persist_superseded_publication(
        self,
        receipt: DraftPullRequestSupersessionReceipt,
        request: SupersedeDraftPullRequest,
    ) -> None:
        history = self._read_history(request)
        if history is None:
            candidate = _publication_history(
                (receipt.predecessor_publication, receipt.successor_publication),
                (None, receipt.predecessor_receipt_id),
                request.change_id,
            )
        elif history.current_receipt_id == receipt.successor_receipt_id:
            candidate = history
        else:
            if history.current_receipt_id != receipt.predecessor_receipt_id:
                self._conflict(request, "publication history has a different current predecessor")
            candidate = _publication_history(
                (*history.publications, receipt.successor_publication),
                (*history.predecessor_receipt_ids, receipt.predecessor_receipt_id),
                request.change_id,
            )
        self._write_history(candidate, request)
        self._write_current_receipt(receipt.successor_publication, receipt, request)

    def _write_history(
        self,
        history: DraftPullRequestPublicationHistory,
        request: _PublicationRequest,
    ) -> None:
        path = self._history_path(request.change_id)
        with locked_roots((self._state_root,)):
            self._require_directory(path.parent)
            self._reject_symlink(path, request)
            try:
                content = path.read_bytes()
            except FileNotFoundError:
                atomic_write(path, history.model_dump_json(indent=2) + "\n")
                return
        try:
            existing = DraftPullRequestPublicationHistory.model_validate_json(content)
        except ValidationError as exc:
            self._invalid_response(request, "stored publication history is invalid", cause=exc)
        if existing == history:
            return
        if (
            history.change_id != existing.change_id
            or history.publications[:-1] != existing.publications
            or history.predecessor_receipt_ids[:-1] != existing.predecessor_receipt_ids
            or history.publications[-1].receipt_id != history.current_receipt_id
        ):
            self._conflict(request, "stored publication history differs from the supersession result")
        with locked_roots((self._state_root,)):
            atomic_write(path, history.model_dump_json(indent=2) + "\n")

    def _write_current_receipt(
        self,
        successor: DraftPullRequestPublicationReceipt,
        supersession: DraftPullRequestSupersessionReceipt,
        request: SupersedeDraftPullRequest,
    ) -> None:
        path = self._path("receipts", request.change_id)
        with locked_roots((self._state_root,)):
            self._require_directory(path.parent)
            self._reject_symlink(path, request)
            try:
                content = path.read_bytes()
            except FileNotFoundError:
                atomic_write(path, successor.model_dump_json(indent=2) + "\n")
                return
        try:
            existing = DraftPullRequestPublicationReceipt.model_validate_json(content)
        except ValidationError as exc:
            self._invalid_response(request, "stored draft pull-request receipt is invalid", cause=exc)
        history = self._read_history(request)
        allowed_receipt_ids = (
            {publication.receipt_id for publication in history.publications}
            if history is not None
            else {supersession.predecessor_receipt_id, supersession.successor_receipt_id}
        )
        if existing.receipt_id not in allowed_receipt_ids:
            self._conflict(request, "stored draft pull-request receipt is outside the supersession history")
        if existing != successor:
            with locked_roots((self._state_root,)):
                atomic_write(path, successor.model_dump_json(indent=2) + "\n")

    def _operation(self, request: CreateOrReconcileDraftPullRequest) -> _DraftPullRequestOperation:
        return _DraftPullRequestOperation(
            operation_id=request.operation_id,
            change_id=request.change_id,
            repository=self._repository,
            head_branch=f"owlbear/change/{request.change_id}",
            head_sha=request.published_head,
            base_branch=self._target_branch,
            title=request.title,
            body=_draft_body(request.change_id, request.generated_summary),
        )

    def _find(self, operation: _PublicationOperationLike) -> PublicationPullRequest | None:
        return self._provider.find_pull_request(
            FindPublicationPullRequest(
                repository=operation.repository,
                head_branch=operation.head_branch,
                base_branch=operation.base_branch,
            )
        )

    def _create_or_reconcile(
        self,
        operation: _PublicationOperationLike,
    ) -> PublicationPullRequest:
        try:
            return self._provider.create_draft_pull_request(
                CreateDraftPublicationPullRequest(
                    repository=operation.repository,
                    head_branch=operation.head_branch,
                    head_sha=operation.head_sha,
                    base_branch=operation.base_branch,
                    title=operation.title,
                    body=operation.body,
                )
            )
        except PublicationProviderError as exc:
            if exc.code not in {
                PublicationProviderFailureCode.CONFLICT,
                PublicationProviderFailureCode.RESPONSE_UNKNOWN,
            }:
                raise
            reconciled = self._find(operation)
            if reconciled is not None:
                return reconciled
            raise

    def _validate_pull_request(
        self,
        pull_request: PublicationPullRequest,
        operation: _PublicationOperationLike,
        request: _PublicationRequest,
    ) -> None:
        if (
            pull_request.repository != operation.repository
            or pull_request.head_branch != operation.head_branch
            or pull_request.head_sha != operation.head_sha
            or pull_request.base_branch != operation.base_branch
            or pull_request.state != "open"
            or pull_request.merged
            or not pull_request.draft
        ):
            self._conflict(request, "provider pull request does not match the draft publication identity")
        marker = _change_marker(operation.change_id)
        if pull_request.body.count(marker) != 1:
            self._conflict(request, "provider pull request does not contain the exact Change marker")

    def _receipt(
        self,
        operation: _DraftPullRequestOperation,
        pull_request: PublicationPullRequest,
    ) -> DraftPullRequestPublicationReceipt:
        payload = {
            "schema_version": 1,
            "operation_id": operation.operation_id,
            "change_id": operation.change_id,
            "repository": pull_request.repository,
            "number": pull_request.number,
            "node_id": pull_request.node_id,
            "head_branch": pull_request.head_branch,
            "head_sha": pull_request.head_sha,
            "base_branch": pull_request.base_branch,
            "provider_evidence_digest": _digest(pull_request.model_dump(mode="json")),
        }
        return DraftPullRequestPublicationReceipt(receipt_id=_digest(payload), **payload)

    def _bind_operation(
        self,
        operation: _DraftPullRequestOperation,
        request: CreateOrReconcileDraftPullRequest,
    ) -> _DraftPullRequestOperation:
        path = self._operation_path(request)
        existing = self._publish_or_read(path, operation, _DraftPullRequestOperation, request)
        if existing != operation:
            self._conflict(request, "draft pull-request operation differs from the stored operation")
        return existing

    def _read_receipt(
        self,
        request: _PublicationRequest,
    ) -> DraftPullRequestPublicationReceipt | None:
        history = self._read_history(request)
        if history is not None:
            path = self._path("receipts", request.change_id)
            with locked_roots((self._state_root,)):
                self._reject_symlink(path, request)
                try:
                    content = path.read_bytes()
                except FileNotFoundError:
                    return history.publications[-1]
            try:
                current = DraftPullRequestPublicationReceipt.model_validate_json(content)
            except ValidationError as exc:
                self._invalid_response(request, "stored draft pull-request receipt is invalid", cause=exc)
            if current.receipt_id not in {publication.receipt_id for publication in history.publications}:
                self._conflict(request, "stored draft pull-request receipt is outside the publication history")
            return history.publications[-1]
        path = self._path("receipts", request.change_id)
        with locked_roots((self._state_root,)):
            self._reject_symlink(path, request)
            try:
                content = path.read_bytes()
            except FileNotFoundError:
                return None
        try:
            return DraftPullRequestPublicationReceipt.model_validate_json(content)
        except ValidationError as exc:
            self._invalid_response(request, "stored draft pull-request receipt is invalid", cause=exc)

    def _read_history(
        self,
        request: _PublicationRequest,
    ) -> DraftPullRequestPublicationHistory | None:
        return self._read_state(
            self._history_path(request.change_id),
            DraftPullRequestPublicationHistory,
            request,
        )

    def _bind_receipt(
        self,
        receipt: DraftPullRequestPublicationReceipt,
        request: CreateOrReconcileDraftPullRequest,
    ) -> DraftPullRequestPublicationReceipt:
        path = self._path("receipts", request.change_id)
        existing = self._publish_or_read(path, receipt, DraftPullRequestPublicationReceipt, request)
        if existing != receipt:
            self._conflict(request, "Change is already bound to a different pull request")
        return existing

    def _read_summary_operation(
        self,
        request: UpdateGeneratedPullRequestSummary,
    ) -> _GeneratedSummaryOperation | None:
        return self._read_state(
            self._summary_path("summary-operations", request),
            _GeneratedSummaryOperation,
            request,
        )

    def _bind_summary_operation(
        self,
        operation: _GeneratedSummaryOperation,
        request: UpdateGeneratedPullRequestSummary,
    ) -> _GeneratedSummaryOperation:
        path = self._summary_path("summary-operations", request)
        existing = self._publish_or_read(path, operation, _GeneratedSummaryOperation, request)
        if existing != operation:
            self._conflict(request, "generated-summary operation differs from the stored operation")
        return existing

    def _read_summary_receipt(
        self,
        request: UpdateGeneratedPullRequestSummary,
    ) -> GeneratedPullRequestSummaryReceipt | None:
        return self._read_state(
            self._summary_path("summary-receipts", request),
            GeneratedPullRequestSummaryReceipt,
            request,
        )

    def _bind_summary_receipt(
        self,
        receipt: GeneratedPullRequestSummaryReceipt,
        request: UpdateGeneratedPullRequestSummary,
    ) -> GeneratedPullRequestSummaryReceipt:
        path = self._summary_path("summary-receipts", request)
        existing = self._publish_or_read(path, receipt, GeneratedPullRequestSummaryReceipt, request)
        if existing != receipt:
            self._conflict(request, "generated-summary receipt differs from the provider result")
        return existing

    def _read_state[ModelT: _DraftPullRequestModel](
        self,
        path: Path,
        model_type: type[ModelT],
        request: _PublicationRequest,
    ) -> ModelT | None:
        with locked_roots((self._state_root,)):
            self._reject_symlink(path, request)
            try:
                content = path.read_bytes()
            except FileNotFoundError:
                return None
        try:
            return model_type.model_validate_json(content)
        except ValidationError as exc:
            self._invalid_response(request, "stored draft pull-request state is invalid", cause=exc)

    def _validate_summary_request(
        self,
        operation: _GeneratedSummaryOperation,
        request: UpdateGeneratedPullRequestSummary,
    ) -> None:
        if (
            operation.operation_id != request.operation_id
            or operation.change_id != request.change_id
            or operation.head_sha != request.published_head
            or operation.generated_summary_digest != _digest(request.generated_summary)
        ):
            self._conflict(request, "generated-summary request differs from the stored operation")

    def _validate_summary_receipt(
        self,
        receipt: GeneratedPullRequestSummaryReceipt,
        operation: _GeneratedSummaryOperation,
        request: UpdateGeneratedPullRequestSummary,
    ) -> None:
        if (
            receipt.operation_id != operation.operation_id
            or receipt.change_id != operation.change_id
            or receipt.repository != operation.repository
            or receipt.number != operation.number
            or receipt.head_sha != operation.head_sha
        ):
            self._conflict(request, "stored generated-summary receipt differs from the operation")

    def _validate_publication_identity(
        self,
        pull_request: PublicationPullRequest,
        publication: DraftPullRequestPublicationReceipt,
        request: _PublicationRequest,
    ) -> None:
        if (
            pull_request.repository != publication.repository
            or pull_request.number != publication.number
            or pull_request.node_id != publication.node_id
            or pull_request.head_branch != publication.head_branch
            or pull_request.head_sha != request.published_head
            or pull_request.base_branch != publication.base_branch
            or pull_request.state != "open"
            or pull_request.merged
        ):
            self._conflict(request, "provider pull request does not match the bound publication identity")

    def _validate_summary_pull_request(
        self,
        pull_request: PublicationPullRequest,
        operation: _GeneratedSummaryOperation,
        request: UpdateGeneratedPullRequestSummary,
    ) -> None:
        if (
            pull_request.repository != operation.repository
            or pull_request.number != operation.number
            or pull_request.node_id != operation.node_id
            or pull_request.head_branch != operation.head_branch
            or pull_request.head_sha != operation.head_sha
            or pull_request.base_branch != operation.base_branch
            or pull_request.state != "open"
            or pull_request.merged
        ):
            self._conflict(request, "provider pull request moved outside the generated-summary fence")
        _generated_block_bounds(pull_request.body, request)

    @staticmethod
    def _summary_receipt(
        operation: _GeneratedSummaryOperation,
        pull_request: PublicationPullRequest,
    ) -> GeneratedPullRequestSummaryReceipt:
        payload = {
            "schema_version": 1,
            "operation_id": operation.operation_id,
            "change_id": operation.change_id,
            "repository": operation.repository,
            "number": operation.number,
            "head_sha": operation.head_sha,
            "body_digest": _digest(pull_request.body),
            "provider_evidence_digest": _digest(pull_request.model_dump(mode="json")),
        }
        return GeneratedPullRequestSummaryReceipt(receipt_id=_digest(payload), **payload)

    def _publish_or_read[ModelT: _DraftPullRequestModel](
        self,
        path: Path,
        model: ModelT,
        model_type: type[ModelT],
        request: _PublicationRequest,
    ) -> ModelT:
        with locked_roots((self._state_root,)):
            self._require_directory(path.parent)
            self._reject_symlink(path, request)
            try:
                content = path.read_bytes()
            except FileNotFoundError:
                try:
                    atomic_write(path, model.model_dump_json(indent=2) + "\n")
                except OSError as exc:
                    self._unavailable(request, "draft pull-request state could not be persisted", cause=exc)
                return model
        try:
            return model_type.model_validate_json(content)
        except ValidationError as exc:
            self._invalid_response(request, "stored draft pull-request state is invalid", cause=exc)

    def _validate_receipt(
        self,
        receipt: DraftPullRequestPublicationReceipt,
        operation: _DraftPullRequestOperation,
        request: CreateOrReconcileDraftPullRequest,
    ) -> None:
        if (
            receipt.change_id != operation.change_id
            or receipt.repository != operation.repository
            or receipt.head_branch != operation.head_branch
            or receipt.base_branch != operation.base_branch
        ):
            self._conflict(request, "stored draft pull-request receipt differs from the operation")

    def _operation_path(self, request: CreateOrReconcileDraftPullRequest) -> Path:
        return self._state_root / "operations" / f"{request.change_id}--{request.operation_id}.json"

    def _supersession_operation_path(self, request: SupersedeDraftPullRequest) -> Path:
        return self._state_root / "supersession-operations" / f"{request.change_id}--{request.operation_id}.json"

    def _supersession_receipt_path(self, request: SupersedeDraftPullRequest) -> Path:
        return self._state_root / "supersession-receipts" / f"{request.change_id}--{request.operation_id}.json"

    def _history_path(self, change_id: str) -> Path:
        return self._state_root / "publication-history" / f"{change_id}.json"

    def _path(self, kind: str, change_id: str) -> Path:
        return self._state_root / kind / f"{change_id}.json"

    def _summary_path(self, kind: str, request: UpdateGeneratedPullRequestSummary) -> Path:
        return self._state_root / kind / f"{request.change_id}--{request.operation_id}.json"

    def _draft_state_path(self, kind: str, request: _ChangePullRequestDraftStateRequest) -> Path:
        return self._state_root / kind / f"{request.change_id}--{request.operation_id}.json"

    def _check_observation_path(
        self,
        request: ObserveChangePublicationChecks,
        evidence_digest: str,
    ) -> Path:
        return self._state_root / "check-observations" / request.change_id / f"{evidence_digest}.json"

    def _pull_request_observation_path(
        self,
        request: ObserveChangePublicationPullRequest,
        evidence_digest: str,
    ) -> Path:
        return self._state_root / "pull-request-observations" / request.change_id / f"{evidence_digest}.json"

    @staticmethod
    def _require_directory(path: Path) -> None:
        if path.is_symlink():
            msg = "draft pull-request state directory must not be a symlink"
            raise ValueError(msg)
        path.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _reject_symlink(path: Path, request: _PublicationRequest) -> None:
        if path.is_symlink():
            DraftPullRequestPublisher._invalid_response(
                request,
                "draft pull-request state file must not be a symlink",
            )

    @staticmethod
    def _conflict(request: _PublicationRequest, detail: str) -> Never:
        _raise_conflict(request, detail)

    @staticmethod
    def _invalid_response(
        request: _PublicationRequest,
        detail: str,
        *,
        cause: Exception | None = None,
    ) -> Never:
        error = PublicationProviderError(
            PublicationProviderFailureCode.INVALID_RESPONSE,
            _request_operation(request),
            detail,
            retry_safe=False,
        )
        raise error from cause

    @staticmethod
    def _unavailable(
        request: _PublicationRequest,
        detail: str,
        *,
        cause: Exception,
    ) -> Never:
        error = PublicationProviderError(
            PublicationProviderFailureCode.UNAVAILABLE,
            _request_operation(request),
            detail,
            retry_safe=True,
        )
        raise error from cause


def _change_marker(change_id: str) -> str:
    return f"<!-- owlbear-change:{change_id} -->"


def _is_change_publication_branch(branch: str, change_id: str) -> bool:
    canonical = f"owlbear/change/{change_id}"
    if branch == canonical:
        return True
    suffix = branch.removeprefix(f"{canonical}+s")
    return suffix.isdecimal() and not suffix.startswith("0")


def _draft_body(change_id: str, generated_summary: str) -> str:
    marker = _change_marker(change_id)
    summary = generated_summary.rstrip()
    return f"{marker}\n\n{_GENERATED_START}\n{summary}\n{_GENERATED_END}\n"


def _publication_history(
    publications: tuple[DraftPullRequestPublicationReceipt, ...],
    predecessor_receipt_ids: tuple[str | None, ...],
    change_id: str,
) -> DraftPullRequestPublicationHistory:
    payload = {
        "schema_version": 1,
        "change_id": change_id,
        "publications": publications,
        "predecessor_receipt_ids": predecessor_receipt_ids,
        "current_receipt_id": publications[-1].receipt_id,
    }
    candidate = DraftPullRequestPublicationHistory.model_construct(history_id="0" * 64, **payload)
    return DraftPullRequestPublicationHistory(
        history_id=_digest(candidate.model_dump(mode="json", exclude={"history_id"})),
        **payload,
    )


def _require_safe_generated_summary(generated_summary: str) -> None:
    reserved_tokens = (_GENERATED_START, _GENERATED_END, "<!-- owlbear-change:")
    if any(token in generated_summary for token in reserved_tokens):
        msg = "generated pull-request summary contains a reserved ownership marker"
        raise ValueError(msg)


def _raise_conflict(request: _PublicationRequest, detail: str) -> Never:
    raise PublicationProviderError(
        PublicationProviderFailureCode.CONFLICT,
        _request_operation(request),
        detail,
        retry_safe=False,
    )


def _request_operation(request: _PublicationRequest) -> str:
    if isinstance(request, ObserveChangePublicationChecks):
        return "observe_change_publication_checks"
    if isinstance(request, ObserveChangePublicationPullRequest):
        return "observe_change_publication_pull_request"
    if isinstance(request, ReadChangePublicationHistory):
        return "read_change_publication_history"
    return request.operation_id


def _generated_block_bounds(body: str, request: _PublicationRequest) -> tuple[int, int]:
    if body.count(_change_marker(request.change_id)) != 1:
        _raise_conflict(request, "pull request body has an invalid Change marker")
    if body.count(_GENERATED_START) != 1 or body.count(_GENERATED_END) != 1:
        _raise_conflict(request, "pull request body has invalid generated-block delimiters")
    start = body.index(_GENERATED_START)
    end = body.index(_GENERATED_END)
    if start >= end:
        _raise_conflict(request, "pull request generated-block delimiters are out of order")
    return start, end


def _replace_generated_block(
    body: str,
    generated_summary: str,
    request: UpdateGeneratedPullRequestSummary,
) -> str:
    start, end = _generated_block_bounds(body, request)
    suffix_start = end + len(_GENERATED_END)
    generated_block = f"{_GENERATED_START}\n{generated_summary.rstrip()}\n{_GENERATED_END}"
    rendered = f"{body[:start]}{generated_block}{body[suffix_start:]}"
    if len(rendered) > _MAX_PULL_REQUEST_BODY_LENGTH:
        _raise_conflict(request, "generated pull-request body exceeds the provider limit")
    return rendered


def _digest(payload: object) -> str:
    content = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(content.encode()).hexdigest()
