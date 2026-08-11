from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from threading import Event

import pytest

from owlbear_delivery.draft_pull_request import (
    CreateOrReconcileDraftPullRequest,
    DraftPullRequestPublisher,
)
from owlbear_delivery.publication_provider import (
    CreateDraftPublicationPullRequest,
    FindPublicationPullRequest,
    PublicationProviderError,
    PublicationProviderFailureCode,
    PublicationPullRequest,
    PublicationRepository,
)

_HEAD = "1" * 40


@dataclass
class _Provider:
    lose_create_response: bool = False
    create_started: Event | None = None
    allow_create: Event | None = None
    pull_requests: list[PublicationPullRequest] = field(default_factory=list)
    create_calls: int = 0

    def read_repository(self, repository: str) -> PublicationRepository:
        return PublicationRepository(repository=repository, default_branch="main")

    def find_pull_request(self, request: FindPublicationPullRequest) -> PublicationPullRequest | None:
        matches = [
            pull_request
            for pull_request in self.pull_requests
            if pull_request.repository == request.repository
            and pull_request.head_branch == request.head_branch
            and pull_request.base_branch == request.base_branch
        ]
        return matches[0] if matches else None

    def create_draft_pull_request(self, request: CreateDraftPublicationPullRequest) -> PublicationPullRequest:
        self.create_calls += 1
        if self.create_started is not None:
            self.create_started.set()
        if self.allow_create is not None and not self.allow_create.wait(timeout=5):
            msg = "test provider create remained blocked"
            raise TimeoutError(msg)
        pull_request = PublicationPullRequest(
            repository=request.repository,
            number=7,
            node_id="PR_node_7",
            head_branch=request.head_branch,
            head_sha=request.head_sha,
            base_branch=request.base_branch,
            title=request.title,
            body=request.body,
            draft=True,
            state="open",
            merged=False,
        )
        self.pull_requests.append(pull_request)
        if self.lose_create_response:
            raise PublicationProviderError(
                PublicationProviderFailureCode.RESPONSE_UNKNOWN,
                "create_draft_pull_request",
                "response lost",
                retry_safe=False,
            )
        return pull_request


def _request(**updates: object) -> CreateOrReconcileDraftPullRequest:
    values = {
        "change_id": "change-a",
        "operation_id": "operation-1",
        "published_head": _HEAD,
        "title": "Change A",
        "generated_summary": "First reviewed checkpoint.",
    }
    values.update(updates)
    return CreateOrReconcileDraftPullRequest.model_validate(values)


def _publisher(tmp_path: Path, provider: _Provider) -> DraftPullRequestPublisher:
    return DraftPullRequestPublisher(
        provider,
        repository="example/project",
        target_branch="main",
        state_root=tmp_path / "pull-requests",
    )


def test_creates_one_marked_draft_pr_and_replays_local_receipt(tmp_path: Path) -> None:
    provider = _Provider()
    publisher = _publisher(tmp_path, provider)

    first = publisher.publish(_request())
    replayed = publisher.publish(_request())

    assert replayed == first
    assert first.number == 7
    assert provider.create_calls == 1
    assert provider.pull_requests[0].body.count("<!-- owlbear-change:change-a -->") == 1
    assert (tmp_path / "pull-requests/receipts/change-a.json").is_file()


def test_reconciles_lost_create_response_without_creating_second_pr(tmp_path: Path) -> None:
    provider = _Provider(lose_create_response=True)
    publisher = _publisher(tmp_path, provider)

    receipt = publisher.publish(_request())

    assert receipt.number == 7
    assert provider.create_calls == 1
    assert len(provider.pull_requests) == 1


def test_concurrent_same_change_publishers_create_one_pull_request(tmp_path: Path) -> None:
    create_started = Event()
    allow_create = Event()
    provider = _Provider(create_started=create_started, allow_create=allow_create)
    first_publisher = _publisher(tmp_path, provider)
    second_publisher = _publisher(tmp_path, provider)

    with ThreadPoolExecutor(max_workers=2) as executor:
        first_future = executor.submit(first_publisher.publish, _request())
        assert create_started.wait(timeout=5)
        second_future = executor.submit(second_publisher.publish, _request())
        allow_create.set()
        first = first_future.result(timeout=5)
        second = second_future.result(timeout=5)

    assert second == first
    assert provider.create_calls == 1
    assert len(provider.pull_requests) == 1


def test_rejects_existing_pr_without_exact_change_marker(tmp_path: Path) -> None:
    provider = _Provider()
    provider.pull_requests.append(
        PublicationPullRequest(
            repository="example/project",
            number=8,
            node_id="PR_node_8",
            head_branch="owlbear/change/change-a",
            head_sha=_HEAD,
            base_branch="main",
            title="User PR",
            body="No marker here.",
            draft=True,
            state="open",
            merged=False,
        )
    )

    with pytest.raises(PublicationProviderError) as exc_info:
        _publisher(tmp_path, provider).publish(_request())

    assert exc_info.value.code is PublicationProviderFailureCode.CONFLICT
    assert provider.create_calls == 0


def test_rejects_operation_input_drift_before_provider_write(tmp_path: Path) -> None:
    provider = _Provider()
    publisher = _publisher(tmp_path, provider)
    publisher.publish(_request())

    with pytest.raises(PublicationProviderError) as exc_info:
        publisher.publish(_request(title="Different title"))

    assert exc_info.value.code is PublicationProviderFailureCode.CONFLICT
    assert provider.create_calls == 1


def test_rejects_corrupted_local_receipt_without_another_provider_write(tmp_path: Path) -> None:
    provider = _Provider()
    publisher = _publisher(tmp_path, provider)
    publisher.publish(_request())
    receipt_path = tmp_path / "pull-requests/receipts/change-a.json"
    receipt_path.write_text("{}\n", encoding="utf-8")

    with pytest.raises(PublicationProviderError) as exc_info:
        publisher.publish(_request())

    assert exc_info.value.code is PublicationProviderFailureCode.INVALID_RESPONSE
    assert provider.create_calls == 1


@pytest.mark.parametrize("kind", ["operations", "receipts"])
def test_rejects_symlinked_leaf_state_before_provider_write(tmp_path: Path, kind: str) -> None:
    provider = _Provider()
    state_root = tmp_path / "pull-requests"
    leaf_root = state_root / kind
    leaf_root.mkdir(parents=True)
    target = tmp_path / f"{kind}.json"
    target.write_text("{}\n", encoding="utf-8")
    (leaf_root / "change-a.json").symlink_to(target)

    with pytest.raises(PublicationProviderError) as exc_info:
        _publisher(tmp_path, provider).publish(_request())

    assert exc_info.value.code is PublicationProviderFailureCode.INVALID_RESPONSE
    assert provider.create_calls == 0
