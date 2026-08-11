"""Behavioral tests for the deterministic publication-provider double."""

from __future__ import annotations

import pytest

from owlbear_delivery import (
    CreateDraftPublicationPullRequest,
    FindPublicationPullRequest,
    PublicationProvider,
    PublicationProviderError,
    PublicationProviderFailureCode,
    PublicationPullRequest,
    PublicationRepository,
    SetPublicationPullRequestDraftState,
    UpdatePublicationPullRequest,
)
from owlbear_delivery_github import InMemoryPublicationProvider

_REPOSITORY = "example/project"
_HEAD = "a" * 40
_OTHER_HEAD = "b" * 40


def _provider() -> InMemoryPublicationProvider:
    provider = InMemoryPublicationProvider()
    provider.add_repository(PublicationRepository(repository=_REPOSITORY, default_branch="main"))
    return provider


def _create_request() -> CreateDraftPublicationPullRequest:
    return CreateDraftPublicationPullRequest(
        repository=_REPOSITORY,
        head_branch="owlbear/change/example",
        head_sha=_HEAD,
        base_branch="main",
        title="Example change",
        body="Generated summary",
    )


def test_lost_create_response_reconciles_to_one_draft_pull_request() -> None:
    provider = _provider()
    assert isinstance(provider, PublicationProvider)

    created = provider.create_draft_pull_request(_create_request())
    reconciled = provider.find_pull_request(
        FindPublicationPullRequest(
            repository=_REPOSITORY,
            head_branch=created.head_branch,
            base_branch=created.base_branch,
        )
    )

    assert reconciled == created
    assert len(provider.pull_requests) == 1
    with pytest.raises(PublicationProviderError) as exc_info:
        provider.create_draft_pull_request(_create_request())
    assert exc_info.value.code is PublicationProviderFailureCode.CONFLICT
    assert len(provider.pull_requests) == 1


def test_update_requires_exact_current_head_and_exposes_no_merge_operation() -> None:
    provider = _provider()
    created = provider.create_draft_pull_request(_create_request())

    with pytest.raises(PublicationProviderError) as exc_info:
        provider.update_pull_request(
            UpdatePublicationPullRequest(
                repository=_REPOSITORY,
                number=created.number,
                expected_head_sha=_OTHER_HEAD,
                title="Changed title",
                body="Changed body",
            )
        )

    assert exc_info.value.code is PublicationProviderFailureCode.CONFLICT
    assert provider.read_pull_request(_REPOSITORY, created.number) == created
    ready = provider.set_pull_request_draft_state(
        SetPublicationPullRequestDraftState(
            repository=_REPOSITORY,
            number=created.number,
            node_id=created.node_id,
            expected_head_sha=created.head_sha,
            draft=False,
        )
    )
    assert ready.draft is False
    assert not hasattr(provider, "merge_pull_request")
    assert not hasattr(provider, "request")


def test_unmerged_pull_request_may_report_provider_test_merge_sha() -> None:
    pull_request = PublicationPullRequest(
        repository=_REPOSITORY,
        number=1,
        node_id="PR_1",
        head_branch="owlbear/change/example",
        head_sha=_HEAD,
        base_branch="main",
        title="Example change",
        body="Generated summary",
        draft=True,
        state="open",
        merged=False,
        merge_commit_sha=_OTHER_HEAD,
    )

    assert pull_request.merged is False
    assert pull_request.merge_commit_sha == _OTHER_HEAD
