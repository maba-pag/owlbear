"""Transport-free publication provider contracts for Delivery."""

from __future__ import annotations

import json
import re
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, model_validator

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


class _ProviderModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class PublicationProviderFailureCode(StrEnum):
    """Classify provider failures without exposing transport-specific exceptions."""

    UNAVAILABLE = "unavailable"
    AUTHENTICATION_REQUIRED = "authentication_required"
    RATE_LIMITED = "rate_limited"
    TIMEOUT = "timeout"
    CONFLICT = "conflict"
    NOT_FOUND = "not_found"
    INVALID_RESPONSE = "invalid_response"
    RESPONSE_UNKNOWN = "response_unknown"


class PublicationProviderError(RuntimeError):
    """Typed publication-provider failure safe for lifecycle reconciliation."""

    __slots__ = ("code", "operation", "retry_safe")

    def __init__(
        self,
        code: PublicationProviderFailureCode,
        operation: str,
        detail: str,
        *,
        retry_safe: bool,
    ) -> None:
        self.code = code
        self.operation = operation
        self.retry_safe = retry_safe
        super().__init__(detail)


class PublicationRepository(_ProviderModel):
    """Exact provider repository identity observed from GitHub."""

    repository: str = Field(min_length=3, pattern=r"^[^\s/]+/[^\s/]+$")
    default_branch: str = Field(min_length=1)


class PublicationPullRequest(_ProviderModel):
    """Provider-observed pull request state used by Delivery reconciliation."""

    repository: str = Field(min_length=3, pattern=r"^[^\s/]+/[^\s/]+$")
    number: int = Field(gt=0)
    node_id: str = Field(min_length=1)
    head_branch: str = Field(min_length=1)
    head_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    base_branch: str = Field(min_length=1)
    title: str = Field(min_length=1)
    body: str
    draft: bool
    state: str = Field(pattern=r"^(open|closed)$")
    merged: bool
    mergeable: bool | None = Field(default=None, exclude=True)
    merge_state_status: str | None = Field(default=None, min_length=1, exclude=True)
    merge_commit_sha: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    merged_at: datetime | None = None
    merged_by_login: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def _validate_merge_state(self) -> PublicationPullRequest:
        if self.merged and self.merge_commit_sha is None:
            message = "merged pull requests require one merge commit"
            raise ValueError(message)
        if self.merged and self.merged_at is None:
            message = "merged pull requests require one merge timestamp"
            raise ValueError(message)
        if self.merged_at is not None and self.merged_at.tzinfo is None:
            message = "pull request merge timestamps must be timezone-aware"
            raise ValueError(message)
        if self.merged and self.state != "closed":
            message = "merged pull requests must be closed"
            raise ValueError(message)
        return self


class FindPublicationPullRequest(_ProviderModel):
    """Fixed lookup for one repository/head/base pull request identity."""

    repository: str = Field(min_length=3, pattern=r"^[^\s/]+/[^\s/]+$")
    head_branch: str = Field(min_length=1)
    base_branch: str = Field(min_length=1)


class CreateDraftPublicationPullRequest(_ProviderModel):
    """Fixed inputs for creating one draft pull request."""

    repository: str = Field(min_length=3, pattern=r"^[^\s/]+/[^\s/]+$")
    head_branch: str = Field(min_length=1)
    head_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    base_branch: str = Field(min_length=1)
    title: str = Field(min_length=1)
    body: str


class UpdatePublicationPullRequest(_ProviderModel):
    """Fixed mutable fields for one exact open pull request."""

    repository: str = Field(min_length=3, pattern=r"^[^\s/]+/[^\s/]+$")
    number: int = Field(gt=0)
    expected_head_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    expected_title: str = Field(min_length=1)
    expected_body: str
    title: str = Field(min_length=1)
    body: str


class SetPublicationPullRequestDraftState(_ProviderModel):
    """Fixed draft-state transition for one exact open pull request."""

    repository: str = Field(min_length=3, pattern=r"^[^\s/]+/[^\s/]+$")
    number: int = Field(gt=0)
    node_id: str = Field(min_length=1)
    expected_head_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    draft: bool


class ObservePublicationChecks(_ProviderModel):
    """Fixed read of provider checks for one exact pull-request head."""

    repository: str = Field(min_length=3, pattern=r"^[^\s/]+/[^\s/]+$")
    number: int = Field(gt=0)
    expected_head_sha: str = Field(pattern=r"^[0-9a-f]{40}$")


class PublicationCheckKind(StrEnum):
    """Provider check representations included in one status rollup."""

    CHECK_RUN = "check_run"
    STATUS_CONTEXT = "status_context"


class PublicationCheck(_ProviderModel):
    """One provider check; status retains the provider vocabulary for its kind."""

    check_id: str = Field(min_length=1)
    kind: PublicationCheckKind
    name: str = Field(min_length=1)
    head_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    status: str = Field(min_length=1)
    conclusion: str | None = None
    required: bool
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_seconds: float | None = Field(default=None, ge=0)
    details_url: str | None = None


class PublicationCheckBlockingState(StrEnum):
    """Delivery-owned readiness meaning for one observed publication check."""

    BLOCKING = "blocking"
    REQUIRED_PENDING = "required-pending"
    NOT_BLOCKING = "not-blocking"


class PublicationCheckSnapshot(_ProviderModel):
    """Complete bounded provider check observation for one exact PR head."""

    repository: str = Field(min_length=3, pattern=r"^[^\s/]+/[^\s/]+$")
    number: int = Field(gt=0)
    head_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    rollup_state: str | None = Field(default=None, min_length=1)
    checks: tuple[PublicationCheck, ...] = Field(max_length=1_000)

    @model_validator(mode="after")
    def _validate_check_identities(self) -> PublicationCheckSnapshot:
        identities = tuple(check.check_id for check in self.checks)
        if len(identities) != len(set(identities)):
            message = "publication check identities must be unique"
            raise ValueError(message)
        if any(check.head_sha != self.head_sha for check in self.checks):
            message = "publication checks must match the snapshot head"
            raise ValueError(message)
        return self


_SUCCESSFUL_PUBLICATION_CONCLUSIONS = frozenset({"success", "neutral", "skipped"})


def classify_publication_check(check: PublicationCheck) -> PublicationCheckBlockingState:
    """Classify one check using the same readiness semantics as Delivery."""
    if not check.required:
        return PublicationCheckBlockingState.NOT_BLOCKING
    if check.conclusion is None:
        return (
            PublicationCheckBlockingState.BLOCKING
            if check.status.casefold() == "completed"
            else PublicationCheckBlockingState.REQUIRED_PENDING
        )
    return (
        PublicationCheckBlockingState.NOT_BLOCKING
        if check.conclusion.casefold() in _SUCCESSFUL_PUBLICATION_CONCLUSIONS
        else PublicationCheckBlockingState.BLOCKING
    )


def failed_required_publication_checks(
    snapshot: PublicationCheckSnapshot,
) -> tuple[PublicationCheck, ...]:
    """Return required checks with terminal non-success evidence."""
    return tuple(
        check
        for check in snapshot.checks
        if classify_publication_check(check) is PublicationCheckBlockingState.BLOCKING
    )


@runtime_checkable
class PublicationProvider(Protocol):
    """Provider operations available to Delivery lifecycle decisions."""

    def read_repository(self, repository: str) -> PublicationRepository:
        """Read and verify one exact provider repository identity."""
        ...

    def read_pull_request(self, repository: str, number: int) -> PublicationPullRequest:
        """Read one exact pull request."""
        ...

    def find_pull_request(self, request: FindPublicationPullRequest) -> PublicationPullRequest | None:
        """Find the unique open pull request for one exact head/base identity; closed ones are history."""
        ...

    def create_draft_pull_request(self, request: CreateDraftPublicationPullRequest) -> PublicationPullRequest:
        """Create one draft pull request using fixed provider fields."""
        ...

    def update_pull_request(self, request: UpdatePublicationPullRequest) -> PublicationPullRequest:
        """Update metadata for one exact pull request after checking its expected head."""
        ...

    def set_pull_request_draft_state(
        self,
        request: SetPublicationPullRequestDraftState,
    ) -> PublicationPullRequest:
        """Transition one exact pull request between draft and ready state."""
        ...

    def observe_checks(self, request: ObservePublicationChecks) -> PublicationCheckSnapshot:
        """Observe checks for one exact pull-request head without requesting provider work."""
        ...


_MAX_PROVIDER_MESSAGE_LENGTH = 500
_DIRECT_MERGE_ACTION = "direct_merge"


def bounded_provider_message(message: str | None) -> str | None:
    """Return a single-line provider message bounded for persisted diagnostics."""
    if message is None:
        return None
    collapsed = " ".join(message.split())
    return collapsed[:_MAX_PROVIDER_MESSAGE_LENGTH] or None


class PublicationMergeMethod(StrEnum):
    """Merge methods a merge request may name; no queue or rule-bypass option exists."""

    MERGE = "merge"
    SQUASH = "squash"
    REBASE = "rebase"


class RequestPublicationMerge(_ProviderModel):
    """Fixed inputs for one exact-head direct merge request."""

    repository: str = Field(min_length=3, pattern=r"^[^\s/]+/[^\s/]+$")
    number: int = Field(gt=0)
    node_id: str = Field(min_length=1)
    expected_head_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    merge_method: PublicationMergeMethod


def merge_request_body(request: RequestPublicationMerge) -> bytes:
    """Return the canonical frozen JSON body of one direct, non-bypassing merge request."""
    body = {
        "bypass_rules": False,
        "merge_action": "direct_merge",
        "merge_method": request.merge_method.value,
        "sha": request.expected_head_sha,
    }
    return json.dumps(body, sort_keys=True, separators=(",", ":")).encode()


class PendingMergeRequest(_ProviderModel):
    """Provider-reported pending merge request and the options the provider reported for it."""

    request_id: str = Field(min_length=1, max_length=128)
    expected_head_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    merge_method: str = Field(min_length=1, max_length=32)
    merge_action: str = Field(min_length=1, max_length=32)
    bypass_rules: bool

    def matches(self, request: RequestPublicationMerge) -> bool:
        """Return whether the reported options equal one approved direct merge request."""
        return (
            self.expected_head_sha == request.expected_head_sha
            and self.merge_method == request.merge_method.value
            and self.merge_action == _DIRECT_MERGE_ACTION
            and self.bypass_rules is False
        )


class PublicationMergeRefusalReason(StrEnum):
    """Complete provider refusals of one merge submission."""

    HEAD_CHANGED = "head-changed"
    NOT_MERGEABLE = "not-mergeable"
    CLOSED_OR_DRAFT = "closed-or-draft"
    RULES_FAILED = "rules-failed"
    FORBIDDEN = "forbidden"
    QUEUE_REQUIRED = "queue-required"
    VALIDATION = "validation"


class PublicationMergeRefusal(_ProviderModel):
    """One complete provider refusal with its bounded provider message."""

    reason: PublicationMergeRefusalReason
    http_status: int | None = Field(default=None, ge=100, le=599)
    message: str | None = Field(default=None, max_length=_MAX_PROVIDER_MESSAGE_LENGTH)


class PublicationMergeRequestStatus(StrEnum):
    """Outcome categories of one merge submission or its readback."""

    PENDING = "pending"
    MERGED = "merged"
    REFUSED = "refused"
    UNAVAILABLE = "unavailable"


class PublicationMergeRequestResult(_ProviderModel):
    """Result of one merge submission or one request-identity readback."""

    status: PublicationMergeRequestStatus
    pending: PendingMergeRequest | None = None
    existing_request: bool = False
    merge_commit_sha: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    refusal: PublicationMergeRefusal | None = None
    message: str | None = Field(default=None, max_length=_MAX_PROVIDER_MESSAGE_LENGTH)

    @model_validator(mode="after")
    def _validate_status_fields(self) -> PublicationMergeRequestResult:
        status = self.status
        if (self.pending is not None) != (status is PublicationMergeRequestStatus.PENDING):
            message = "only pending merge results carry a pending request"
            raise ValueError(message)
        if self.existing_request and status is not PublicationMergeRequestStatus.PENDING:
            message = "only pending merge results can report an existing request"
            raise ValueError(message)
        if (self.merge_commit_sha is not None) != (status is PublicationMergeRequestStatus.MERGED):
            message = "only merged results carry exactly one merge commit"
            raise ValueError(message)
        if (self.refusal is not None) != (status is PublicationMergeRequestStatus.REFUSED):
            message = "only refused merge results carry a refusal"
            raise ValueError(message)
        return self


class PublicationMergeStack(_ProviderModel):
    """Provider-reported stack membership of one pull request."""

    size: int = Field(ge=1)
    position: int = Field(ge=1)
    base_branch: str = Field(min_length=1)
    base_sha: str = Field(pattern=r"^[0-9a-f]{40}$")


class PublicationMergeEvidence(_ProviderModel):
    """Fresh merge-relevant facts of one pull request, including post-merge commit parents."""

    repository: str = Field(min_length=3, pattern=r"^[^\s/]+/[^\s/]+$")
    number: int = Field(gt=0)
    node_id: str = Field(min_length=1)
    state: str = Field(pattern=r"^(open|closed)$")
    draft: bool
    merged: bool
    head_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    base_branch: str = Field(min_length=1)
    stack: PublicationMergeStack | None = None
    merge_commit_sha: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    merge_commit_parents: tuple[str, ...] = Field(default=(), max_length=2)
    merged_at: datetime | None = None

    @model_validator(mode="after")
    def _validate_merge_evidence(self) -> PublicationMergeEvidence:
        if any(re.fullmatch(r"[0-9a-f]{40}", parent) is None for parent in self.merge_commit_parents):
            message = "merge commit parents must be commit identities"
            raise ValueError(message)
        if not self.merged:
            if self.merge_commit_sha is not None or self.merge_commit_parents or self.merged_at is not None:
                message = "unmerged pull requests carry no merge evidence"
                raise ValueError(message)
            return self
        if self.state != "closed" or self.merge_commit_sha is None or not self.merge_commit_parents:
            message = "merged pull requests require closed state, one merge commit and its parents"
            raise ValueError(message)
        if self.merged_at is None or self.merged_at.tzinfo is None:
            message = "merged pull requests require one timezone-aware merge timestamp"
            raise ValueError(message)
        return self


class PublicationBranchHead(_ProviderModel):
    """Provider-observed head commit of one branch."""

    repository: str = Field(min_length=3, pattern=r"^[^\s/]+/[^\s/]+$")
    branch: str = Field(min_length=1)
    head_sha: str = Field(pattern=r"^[0-9a-f]{40}$")


class PublicationMergeSettings(_ProviderModel):
    """Provider facts that decide whether Delivery may send a merge for one target branch."""

    repository: str = Field(min_length=3, pattern=r"^[^\s/]+/[^\s/]+$")
    branch: str = Field(min_length=1)
    allowed_methods: tuple[PublicationMergeMethod, ...] = Field(max_length=3)
    viewer_can_push: bool
    rule_types: tuple[str, ...] = Field(max_length=100)
    queue_required: bool
    strict_up_to_date_required: bool
    execution_scope_enforced: bool


@runtime_checkable
class PublicationMergeProvider(Protocol):
    """Merge transport beside ``PublicationProvider``; readback never sends a request."""

    def read_merge_settings(self, repository: str, branch: str) -> PublicationMergeSettings:
        """Read repository merge settings, viewer permission and target-branch rules."""
        ...

    def read_branch_head(self, repository: str, branch: str) -> PublicationBranchHead:
        """Read the current head of one branch."""
        ...

    def request_merge(
        self,
        request: RequestPublicationMerge,
        *,
        body_path: Path,
        release: Callable[[int, str], None],
    ) -> PublicationMergeRequestResult:
        """Send one frozen merge body after ``release`` records the spawned process group."""
        ...

    def read_merge_request(self, repository: str, number: int, request_id: str) -> PublicationMergeRequestResult:
        """Read the provider result for one merge request identity without sending a request."""
        ...

    def read_merge_evidence(self, repository: str, number: int) -> PublicationMergeEvidence:
        """Read fresh merge, head, base, stack and merge-commit facts for one pull request."""
        ...
