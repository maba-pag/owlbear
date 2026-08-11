"""Deterministic in-memory publication provider for Delivery tests."""

from __future__ import annotations

from dataclasses import dataclass, field

from owlbear_delivery.publication_provider import (
    CreateDraftPublicationPullRequest,
    FindPublicationPullRequest,
    PublicationProviderError,
    PublicationProviderFailureCode,
    PublicationPullRequest,
    PublicationRepository,
    SetPublicationPullRequestDraftState,
    UpdatePublicationPullRequest,
)


@dataclass(slots=True)
class InMemoryPublicationProvider:
    """Implement fixed publication operations without network or subprocess effects."""

    repositories: dict[str, PublicationRepository] = field(default_factory=dict)
    pull_requests: dict[tuple[str, int], PublicationPullRequest] = field(default_factory=dict)

    def add_repository(self, repository: PublicationRepository) -> None:
        """Register one exact provider repository identity."""
        self.repositories[repository.repository] = repository

    def read_repository(self, repository: str) -> PublicationRepository:
        """Read one registered repository."""
        try:
            return self.repositories[repository]
        except KeyError as exc:
            raise PublicationProviderError(
                PublicationProviderFailureCode.NOT_FOUND,
                "read_repository",
                "publication repository was not found",
                retry_safe=False,
            ) from exc

    def read_pull_request(self, repository: str, number: int) -> PublicationPullRequest:
        """Read one registered pull request."""
        try:
            return self.pull_requests[(repository, number)]
        except KeyError as exc:
            raise PublicationProviderError(
                PublicationProviderFailureCode.NOT_FOUND,
                "read_pull_request",
                "publication pull request was not found",
                retry_safe=False,
            ) from exc

    def find_pull_request(self, request: FindPublicationPullRequest) -> PublicationPullRequest | None:
        """Find the unique open or closed pull request for one head/base identity."""
        matches = tuple(
            pull_request
            for pull_request in self.pull_requests.values()
            if pull_request.repository == request.repository
            and pull_request.head_branch == request.head_branch
            and pull_request.base_branch == request.base_branch
        )
        if len(matches) > 1:
            raise PublicationProviderError(
                PublicationProviderFailureCode.CONFLICT,
                "find_pull_request",
                "multiple pull requests match the publication identity",
                retry_safe=False,
            )
        return matches[0] if matches else None

    def create_draft_pull_request(self, request: CreateDraftPublicationPullRequest) -> PublicationPullRequest:
        """Create one draft pull request after rejecting duplicate head/base identity."""
        self.read_repository(request.repository)
        existing = self.find_pull_request(
            FindPublicationPullRequest(
                repository=request.repository,
                head_branch=request.head_branch,
                base_branch=request.base_branch,
            )
        )
        if existing is not None:
            raise PublicationProviderError(
                PublicationProviderFailureCode.CONFLICT,
                "create_draft_pull_request",
                "publication pull request already exists",
                retry_safe=False,
            )
        next_number = (
            max(
                (number for repository, number in self.pull_requests if repository == request.repository),
                default=0,
            )
            + 1
        )
        pull_request = PublicationPullRequest(
            repository=request.repository,
            number=next_number,
            node_id=f"PR_{next_number}",
            head_branch=request.head_branch,
            head_sha=request.head_sha,
            base_branch=request.base_branch,
            title=request.title,
            body=request.body,
            draft=True,
            state="open",
            merged=False,
        )
        self.pull_requests[(request.repository, next_number)] = pull_request
        return pull_request

    def update_pull_request(self, request: UpdatePublicationPullRequest) -> PublicationPullRequest:
        """Update fixed generated fields after exact-head fencing."""
        current = self.read_pull_request(request.repository, request.number)
        if current.head_sha != request.expected_head_sha or current.state != "open" or current.merged:
            raise PublicationProviderError(
                PublicationProviderFailureCode.CONFLICT,
                "update_pull_request",
                "publication pull request state does not match the update fence",
                retry_safe=False,
            )
        updated = current.model_copy(
            update={
                "title": request.title,
                "body": request.body,
            }
        )
        self.pull_requests[(request.repository, request.number)] = updated
        return updated

    def set_pull_request_draft_state(
        self,
        request: SetPublicationPullRequestDraftState,
    ) -> PublicationPullRequest:
        """Transition draft state after exact node and head fencing."""
        current = self.read_pull_request(request.repository, request.number)
        if (
            current.node_id != request.node_id
            or current.head_sha != request.expected_head_sha
            or current.state != "open"
            or current.merged
        ):
            raise PublicationProviderError(
                PublicationProviderFailureCode.CONFLICT,
                "set_pull_request_draft_state",
                "publication pull request state does not match the draft-state fence",
                retry_safe=False,
            )
        updated = current.model_copy(update={"draft": request.draft})
        self.pull_requests[(request.repository, request.number)] = updated
        return updated
