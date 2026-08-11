"""Transport-free publication provider contracts for Delivery."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, model_validator


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
    merge_commit_sha: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")

    @model_validator(mode="after")
    def _validate_merge_state(self) -> PublicationPullRequest:
        if self.merged and self.merge_commit_sha is None:
            message = "merged pull requests require one merge commit"
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
        """Find the unique pull request for one exact head/base identity."""
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
