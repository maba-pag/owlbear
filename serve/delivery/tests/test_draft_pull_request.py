from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from threading import Event

import pytest

from owlbear_delivery.draft_pull_request import (
    CreateOrReconcileDraftPullRequest,
    DraftPullRequestPublicationReceipt,
    DraftPullRequestPublisher,
    MarkChangePullRequestReady,
    ObserveChangePublicationChecks,
    ObserveChangePublicationPullRequest,
    PublicationCheckObservationReceipt,
    PublicationPullRequestObservationReceipt,
    PullRequestDraftReceipt,
    PullRequestReadyReceipt,
    ReadChangePublicationHistory,
    ReturnChangePullRequestToDraft,
    SupersedeDraftPullRequest,
    UpdateGeneratedPullRequestSummary,
)
from owlbear_delivery.publication_provider import (
    CreateDraftPublicationPullRequest,
    FindPublicationPullRequest,
    ObservePublicationChecks,
    PublicationCheckSnapshot,
    PublicationProviderError,
    PublicationProviderFailureCode,
    PublicationPullRequest,
    PublicationRepository,
    SetPublicationPullRequestDraftState,
    UpdatePublicationPullRequest,
)

_HEAD = "1" * 40


@dataclass
class _Provider:
    lose_create_response: bool = False
    fail_create_before_write_once: bool = False
    create_started: Event | None = None
    allow_create: Event | None = None
    update_started: Event | None = None
    allow_update: Event | None = None
    pull_requests: list[PublicationPullRequest] = field(default_factory=list)
    create_calls: int = 0
    update_calls: int = 0
    observed_requests: list[ObservePublicationChecks] = field(default_factory=list)
    observed_head: str | None = None
    move_pull_request_during_observation: bool = False
    lose_update_response: bool = False
    fail_update_before_write_once: bool = False
    draft_state_calls: int = 0
    lose_draft_state_response: bool = False

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
        if self.fail_create_before_write_once:
            self.fail_create_before_write_once = False
            raise PublicationProviderError(
                PublicationProviderFailureCode.UNAVAILABLE,
                "create_draft_pull_request",
                "provider unavailable",
                retry_safe=True,
            )
        if self.create_started is not None:
            self.create_started.set()
        if self.allow_create is not None and not self.allow_create.wait(timeout=5):
            msg = "test provider create remained blocked"
            raise TimeoutError(msg)
        pull_request = PublicationPullRequest(
            repository=request.repository,
            number=7 + len(self.pull_requests),
            node_id=f"PR_node_{7 + len(self.pull_requests)}",
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

    def read_pull_request(self, repository: str, number: int) -> PublicationPullRequest:
        return next(
            pull_request
            for pull_request in self.pull_requests
            if pull_request.repository == repository and pull_request.number == number
        )

    def update_pull_request(self, request: UpdatePublicationPullRequest) -> PublicationPullRequest:
        current = self.read_pull_request(request.repository, request.number)
        if (
            current.head_sha != request.expected_head_sha
            or current.title != request.expected_title
            or current.body != request.expected_body
        ):
            raise PublicationProviderError(
                PublicationProviderFailureCode.CONFLICT,
                "update_pull_request",
                "pull request differs from the update fence",
                retry_safe=False,
            )
        if self.fail_update_before_write_once:
            self.fail_update_before_write_once = False
            raise PublicationProviderError(
                PublicationProviderFailureCode.UNAVAILABLE,
                "update_pull_request",
                "provider unavailable",
                retry_safe=True,
            )
        self.update_calls += 1
        if self.update_started is not None:
            self.update_started.set()
        if self.allow_update is not None and not self.allow_update.wait(timeout=5):
            msg = "test provider update remained blocked"
            raise TimeoutError(msg)
        updated = current.model_copy(update={"title": request.title, "body": request.body})
        self.pull_requests[self.pull_requests.index(current)] = updated
        if self.lose_update_response:
            raise PublicationProviderError(
                PublicationProviderFailureCode.RESPONSE_UNKNOWN,
                "update_pull_request",
                "response lost",
                retry_safe=False,
            )
        return updated

    def observe_checks(self, request: ObservePublicationChecks) -> PublicationCheckSnapshot:
        self.observed_requests.append(request)
        if self.move_pull_request_during_observation:
            current = self.read_pull_request(request.repository, request.number)
            self.pull_requests[self.pull_requests.index(current)] = current.model_copy(
                update={"base_branch": "different-target"}
            )
        return PublicationCheckSnapshot(
            repository=request.repository,
            number=request.number,
            head_sha=self.observed_head or request.expected_head_sha,
            rollup_state="success",
            checks=(),
        )

    def set_pull_request_draft_state(
        self,
        request: SetPublicationPullRequestDraftState,
    ) -> PublicationPullRequest:
        current = self.read_pull_request(request.repository, request.number)
        self.draft_state_calls += 1
        updated = current.model_copy(update={"draft": request.draft})
        self.pull_requests[self.pull_requests.index(current)] = updated
        if self.lose_draft_state_response:
            raise PublicationProviderError(
                PublicationProviderFailureCode.RESPONSE_UNKNOWN,
                "set_pull_request_draft_state",
                "response lost",
                retry_safe=False,
            )
        return updated


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
        clock=lambda: datetime(2026, 8, 11, 12, tzinfo=UTC),
    )


def _summary_request(**updates: object) -> UpdateGeneratedPullRequestSummary:
    values = {
        "change_id": "change-a",
        "operation_id": "summary-operation",
        "published_head": _HEAD,
        "generated_summary": "Second reviewed checkpoint.",
    }
    values.update(updates)
    return UpdateGeneratedPullRequestSummary.model_validate(values)


def _checks_request(**updates: object) -> ObserveChangePublicationChecks:
    values = {"change_id": "change-a", "published_head": _HEAD}
    values.update(updates)
    return ObserveChangePublicationChecks.model_validate(values)


def _supersede_request(
    predecessor: DraftPullRequestPublicationReceipt,
    **updates: object,
) -> SupersedeDraftPullRequest:
    predecessor_receipt = predecessor
    values = {
        "change_id": "change-a",
        "operation_id": "supersession-operation",
        "expected_predecessor_receipt_id": predecessor_receipt.receipt_id,
        "predecessor_branch": predecessor_receipt.head_branch,
        "predecessor_head": predecessor_receipt.head_sha,
        "successor_branch": "owlbear/change/change-a+s1",
        "superseding_head": "2" * 40,
        "title": "Change A corrected",
        "generated_summary": "Corrected reviewed checkpoint.",
    }
    values.update(updates)
    return SupersedeDraftPullRequest.model_validate(values)


def _ready_request(**updates: object) -> MarkChangePullRequestReady:
    values = {
        "change_id": "change-a",
        "operation_id": "ready-operation",
        "finalization_id": "a" * 64,
        "exact_head": _HEAD,
    }
    values.update(updates)
    return MarkChangePullRequestReady.model_validate(values)


def _draft_request(**updates: object) -> ReturnChangePullRequestToDraft:
    values = _ready_request().model_dump()
    values["operation_id"] = "draft-operation"
    values.update(updates)
    return ReturnChangePullRequestToDraft.model_validate(values)


def test_creates_one_marked_draft_pr_and_replays_local_receipt(tmp_path: Path) -> None:
    provider = _Provider()
    publisher = _publisher(tmp_path, provider)

    first = publisher.publish(_request())
    replayed = publisher.publish(_request())

    assert replayed == first
    assert first.number == 7
    assert provider.create_calls == 1


def test_creation_retries_at_new_head_after_prior_operation_failed(tmp_path: Path) -> None:
    provider = _Provider(fail_create_before_write_once=True)
    publisher = _publisher(tmp_path, provider)

    with pytest.raises(PublicationProviderError) as exc_info:
        publisher.publish(_request())

    assert exc_info.value.code is PublicationProviderFailureCode.UNAVAILABLE
    newer_head = "2" * 40
    receipt = publisher.publish(_request(operation_id="operation-2", published_head=newer_head))

    assert receipt.head_sha == newer_head
    assert provider.create_calls == 2


def test_existing_publication_reconciles_after_branch_head_advances(tmp_path: Path) -> None:
    provider = _Provider()
    publisher = _publisher(tmp_path, provider)
    original = publisher.publish(_request())
    newer_head = "2" * 40
    provider.pull_requests[0] = provider.pull_requests[0].model_copy(update={"head_sha": newer_head})

    replayed = publisher.publish(_request(operation_id="operation-2", published_head=newer_head))

    assert replayed == original
    assert provider.create_calls == 1
    assert provider.pull_requests[0].body.count("<!-- owlbear-change:change-a -->") == 1
    assert (tmp_path / "pull-requests/receipts/change-a.json").is_file()


def test_reconciles_lost_create_response_without_creating_second_pr(tmp_path: Path) -> None:
    provider = _Provider(lose_create_response=True)
    publisher = _publisher(tmp_path, provider)

    receipt = publisher.publish(_request())

    assert receipt.number == 7
    assert provider.create_calls == 2
    assert len(provider.pull_requests) == 1


def test_supersedes_publication_and_replays_ordered_successor_history(tmp_path: Path) -> None:
    provider = _Provider()
    publisher = _publisher(tmp_path, provider)
    predecessor = publisher.publish(_request())
    request = _supersede_request(predecessor)

    first = publisher.supersede(request)
    replayed = publisher.supersede(request)
    history = publisher.read_publication_history(ReadChangePublicationHistory(change_id="change-a"))

    assert replayed == first
    assert first.predecessor_receipt_id == predecessor.receipt_id
    assert first.successor_publication.head_branch == "owlbear/change/change-a+s1"
    assert first.successor_publication.head_sha == "2" * 40
    assert history is not None
    assert history.publications == (predecessor, first.successor_publication)
    assert history.current_receipt_id == first.successor_receipt_id
    assert provider.create_calls == 2
    assert len(provider.pull_requests) == 2
    assert provider.pull_requests[0].head_branch == predecessor.head_branch

    summary = publisher.update_generated_summary(
        _summary_request(
            operation_id="successor-summary-operation",
            published_head="2" * 40,
            generated_summary="Successor summary.",
        )
    )

    assert summary.head_sha == "2" * 40
    assert "Successor summary." in provider.pull_requests[1].body
    assert "Second reviewed checkpoint." not in provider.pull_requests[1].body


def test_chained_supersession_preserves_every_predecessor(tmp_path: Path) -> None:
    provider = _Provider()
    publisher = _publisher(tmp_path, provider)
    first_publication = publisher.publish(_request())
    first = publisher.supersede(_supersede_request(first_publication))

    second = publisher.supersede(
        _supersede_request(
            first.successor_publication,
            operation_id="supersession-operation-2",
            successor_branch="owlbear/change/change-a+s2",
            superseding_head="3" * 40,
        )
    )
    history = publisher.read_publication_history(ReadChangePublicationHistory(change_id="change-a"))

    assert history is not None
    assert history.publications == (
        first_publication,
        first.successor_publication,
        second.successor_publication,
    )
    assert second.predecessor_receipt_id == first.successor_receipt_id
    assert second.successor_branch == "owlbear/change/change-a+s2"
    assert len(provider.pull_requests) == 3


def test_reconciles_lost_successor_create_response(tmp_path: Path) -> None:
    provider = _Provider(lose_create_response=True)
    publisher = _publisher(tmp_path, provider)
    predecessor = publisher.publish(_request())

    receipt = publisher.supersede(_supersede_request(predecessor))

    assert receipt.successor_number == 8
    assert provider.create_calls == 2
    assert len(provider.pull_requests) == 2


def test_rejects_predecessor_branch_from_another_change_before_provider_write(tmp_path: Path) -> None:
    provider = _Provider()
    publisher = _publisher(tmp_path, provider)
    predecessor = publisher.publish(_request())

    with pytest.raises(ValueError, match="predecessor branch does not belong"):
        _supersede_request(predecessor, predecessor_branch="owlbear/change/other-change")

    assert provider.create_calls == 1


def test_replays_original_publish_operation_after_supersession(tmp_path: Path) -> None:
    provider = _Provider()
    publisher = _publisher(tmp_path, provider)
    predecessor = publisher.publish(_request())
    publisher.supersede(_supersede_request(predecessor))

    replayed = publisher.publish(_request())

    assert replayed == predecessor
    assert provider.create_calls == 2


def test_rejects_stale_predecessor_receipt_identity_before_successor_creation(tmp_path: Path) -> None:
    provider = _Provider()
    publisher = _publisher(tmp_path, provider)
    predecessor = publisher.publish(_request())

    with pytest.raises(PublicationProviderError) as exc_info:
        publisher.supersede(_supersede_request(predecessor, expected_predecessor_receipt_id="f" * 64))

    assert exc_info.value.code is PublicationProviderFailureCode.CONFLICT
    assert provider.create_calls == 1


def test_rejects_merged_predecessor_before_successor_creation(tmp_path: Path) -> None:
    provider = _Provider()
    publisher = _publisher(tmp_path, provider)
    predecessor = publisher.publish(_request())
    provider.pull_requests[0] = provider.pull_requests[0].model_copy(
        update={
            "state": "closed",
            "merged": True,
            "merge_commit_sha": "3" * 40,
            "merged_at": datetime(2026, 8, 12, tzinfo=UTC),
        }
    )

    with pytest.raises(PublicationProviderError, match="merged predecessor"):
        publisher.supersede(_supersede_request(predecessor))

    assert provider.create_calls == 1
    assert len(provider.pull_requests) == 1


def test_rechecks_merged_predecessor_after_persisted_operation_retry(tmp_path: Path) -> None:
    provider = _Provider()
    publisher = _publisher(tmp_path, provider)
    predecessor = publisher.publish(_request())
    request = _supersede_request(predecessor)
    provider.fail_create_before_write_once = True

    with pytest.raises(PublicationProviderError, match="provider unavailable"):
        publisher.supersede(request)

    provider.pull_requests[0] = provider.pull_requests[0].model_copy(
        update={
            "state": "closed",
            "merged": True,
            "merge_commit_sha": "3" * 40,
            "merged_at": datetime(2026, 8, 12, tzinfo=UTC),
        }
    )

    with pytest.raises(PublicationProviderError, match="merged predecessor"):
        publisher.supersede(request)

    assert provider.create_calls == 2
    assert len(provider.pull_requests) == 1


def test_repairs_current_receipt_after_interrupted_history_append(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _Provider()
    publisher = _publisher(tmp_path, provider)
    predecessor = publisher.publish(_request())
    original_write = publisher._write_current_receipt  # noqa: SLF001

    def fail_once(
        _successor: DraftPullRequestPublicationReceipt,
        _supersession: object,
        _request: object,
    ) -> None:
        monkeypatch.setattr(publisher, "_write_current_receipt", original_write)
        message = "simulated receipt projection interruption"
        raise RuntimeError(message)

    monkeypatch.setattr(publisher, "_write_current_receipt", fail_once)
    with pytest.raises(RuntimeError, match="projection interruption"):
        publisher.supersede(_supersede_request(predecessor))

    history = publisher.read_publication_history(ReadChangePublicationHistory(change_id="change-a"))
    assert history is not None
    successor = history.publications[-1]
    second = publisher.supersede(
        _supersede_request(
            successor,
            operation_id="supersession-operation-2",
            successor_branch="owlbear/change/change-a+s2",
            superseding_head="3" * 40,
        )
    )

    assert second.successor_branch == "owlbear/change/change-a+s2"
    current_receipt = DraftPullRequestPublicationReceipt.model_validate_json(
        (tmp_path / "pull-requests/receipts/change-a.json").read_bytes()
    )
    assert current_receipt.receipt_id == second.successor_receipt_id


def test_mark_ready_reconciles_lost_response_and_replays_durable_receipt(tmp_path: Path) -> None:
    provider = _Provider(lose_draft_state_response=True)
    publisher = _publisher(tmp_path, provider)
    publisher.publish(_request())

    first = publisher.mark_ready(_ready_request())
    replayed = publisher.mark_ready(_ready_request())

    assert isinstance(first, PullRequestReadyReceipt)
    assert replayed == first
    assert first.finalization_id == "a" * 64
    assert first.head_sha == _HEAD
    assert provider.pull_requests[0].draft is False
    assert provider.draft_state_calls == 1

    provider.lose_draft_state_response = True
    drafted = publisher.return_to_draft(_draft_request())
    draft_replay = publisher.return_to_draft(_draft_request())

    assert isinstance(drafted, PullRequestDraftReceipt)
    assert draft_replay == drafted
    assert drafted.finalization_id == first.finalization_id
    assert provider.pull_requests[0].draft is True
    assert provider.draft_state_calls == 2


def test_observes_checks_from_change_bound_pull_request_identity(tmp_path: Path) -> None:
    provider = _Provider()
    publisher = _publisher(tmp_path, provider)
    publication = publisher.publish(_request())
    change_lock_root = tmp_path / "pull-requests" / "locks" / "change-a"
    (change_lock_root / ".storage.lock").unlink()
    change_lock_root.rmdir()

    receipt = publisher.observe_checks(_checks_request())

    assert isinstance(receipt, PublicationCheckObservationReceipt)
    assert receipt.repository == publication.repository
    assert receipt.number == publication.number
    assert receipt.exact_commit == publication.head_sha
    assert receipt.snapshot.head_sha == publication.head_sha
    assert receipt.observed_at == datetime(2026, 8, 11, 12, tzinfo=UTC)
    observation_path = (
        tmp_path / "pull-requests/check-observations/change-a" / f"{receipt.provider_evidence_digest}.json"
    )
    assert PublicationCheckObservationReceipt.model_validate_json(observation_path.read_bytes()) == receipt
    assert provider.observed_requests == [
        ObservePublicationChecks(
            repository=publication.repository,
            number=publication.number,
            expected_head_sha=publication.head_sha,
        )
    ]


def test_identical_check_observation_replays_durable_receipt(tmp_path: Path) -> None:
    provider = _Provider()
    publisher = _publisher(tmp_path, provider)
    publisher.publish(_request())

    first = publisher.observe_checks(_checks_request())
    replayed = publisher.observe_checks(_checks_request())

    assert replayed == first
    assert len(provider.observed_requests) == 2
    assert len(tuple((tmp_path / "pull-requests/check-observations/change-a").glob("*.json"))) == 1


def test_observes_and_persists_bound_pull_request_head_drift(tmp_path: Path) -> None:
    provider = _Provider()
    publisher = _publisher(tmp_path, provider)
    publisher.publish(_request())
    provider.pull_requests[0] = provider.pull_requests[0].model_copy(update={"head_sha": "2" * 40})
    request = ObserveChangePublicationPullRequest(change_id="change-a")

    receipt = publisher.observe_pull_request(request)
    replayed = publisher.observe_pull_request(request)

    assert isinstance(receipt, PublicationPullRequestObservationReceipt)
    assert replayed == receipt
    assert receipt.snapshot.head_sha == "2" * 40
    observation_path = (
        tmp_path / "pull-requests/pull-request-observations/change-a" / f"{receipt.provider_evidence_digest}.json"
    )
    assert PublicationPullRequestObservationReceipt.model_validate_json(observation_path.read_bytes()) == receipt


def test_rejects_moved_pull_request_before_check_observation(tmp_path: Path) -> None:
    provider = _Provider()
    publisher = _publisher(tmp_path, provider)
    publisher.publish(_request())
    current = provider.pull_requests[0]
    provider.pull_requests[0] = current.model_copy(update={"base_branch": "different-target"})

    with pytest.raises(PublicationProviderError) as exc_info:
        publisher.observe_checks(_checks_request())

    assert exc_info.value.code is PublicationProviderFailureCode.CONFLICT
    assert provider.observed_requests == []


def test_rejects_check_snapshot_for_different_head(tmp_path: Path) -> None:
    provider = _Provider(observed_head="2" * 40)
    publisher = _publisher(tmp_path, provider)
    publisher.publish(_request())

    with pytest.raises(PublicationProviderError) as exc_info:
        publisher.observe_checks(_checks_request())

    assert exc_info.value.code is PublicationProviderFailureCode.INVALID_RESPONSE
    assert len(provider.observed_requests) == 1


def test_rejects_pull_request_drift_during_check_observation(tmp_path: Path) -> None:
    provider = _Provider(move_pull_request_during_observation=True)
    publisher = _publisher(tmp_path, provider)
    publisher.publish(_request())

    with pytest.raises(PublicationProviderError) as exc_info:
        publisher.observe_checks(_checks_request())

    assert exc_info.value.code is PublicationProviderFailureCode.CONFLICT
    assert len(provider.observed_requests) == 1


def test_updates_only_generated_block_and_replays_receipt(tmp_path: Path) -> None:
    provider = _Provider()
    publisher = _publisher(tmp_path, provider)
    publisher.publish(_request())
    created = provider.pull_requests[0]
    provider.pull_requests[0] = created.model_copy(update={"body": f"User intro.\n\n{created.body}\nUser tail.\n"})

    first = publisher.update_generated_summary(_summary_request())
    replayed = publisher.update_generated_summary(_summary_request())

    assert replayed == first
    assert provider.update_calls == 1
    assert provider.pull_requests[0].body.startswith("User intro.\n\n")
    assert provider.pull_requests[0].body.endswith("\nUser tail.\n")
    assert "Second reviewed checkpoint." in provider.pull_requests[0].body
    assert "First reviewed checkpoint." not in provider.pull_requests[0].body


def test_reconciles_lost_summary_update_response_without_second_write(tmp_path: Path) -> None:
    provider = _Provider(lose_update_response=True)
    publisher = _publisher(tmp_path, provider)
    publisher.publish(_request())

    receipt = publisher.update_generated_summary(_summary_request())

    assert receipt.body_digest
    assert provider.update_calls == 1
    assert "Second reviewed checkpoint." in provider.pull_requests[0].body


def test_retries_summary_after_user_prose_changes(tmp_path: Path) -> None:
    provider = _Provider(fail_update_before_write_once=True)
    publisher = _publisher(tmp_path, provider)
    publisher.publish(_request())

    with pytest.raises(PublicationProviderError) as exc_info:
        publisher.update_generated_summary(_summary_request())

    assert exc_info.value.code is PublicationProviderFailureCode.UNAVAILABLE
    current = provider.pull_requests[0]
    provider.pull_requests[0] = current.model_copy(update={"body": f"User intro.\n\n{current.body}"})

    receipt = publisher.update_generated_summary(_summary_request())

    assert receipt.body_digest
    assert provider.update_calls == 1
    assert provider.pull_requests[0].body.startswith("User intro.\n\n")
    assert "Second reviewed checkpoint." in provider.pull_requests[0].body


def test_concurrent_summary_publishers_make_one_metadata_write(tmp_path: Path) -> None:
    update_started = Event()
    allow_update = Event()
    provider = _Provider(update_started=update_started, allow_update=allow_update)
    first_publisher = _publisher(tmp_path, provider)
    second_publisher = _publisher(tmp_path, provider)
    first_publisher.publish(_request())

    with ThreadPoolExecutor(max_workers=2) as executor:
        first_future = executor.submit(first_publisher.update_generated_summary, _summary_request())
        assert update_started.wait(timeout=5)
        second_future = executor.submit(second_publisher.update_generated_summary, _summary_request())
        allow_update.set()
        first = first_future.result(timeout=5)
        second = second_future.result(timeout=5)

    assert second == first
    assert provider.update_calls == 1


def test_rejects_invalid_generated_block_without_metadata_write(tmp_path: Path) -> None:
    provider = _Provider()
    publisher = _publisher(tmp_path, provider)
    publisher.publish(_request())
    created = provider.pull_requests[0]
    provider.pull_requests[0] = created.model_copy(
        update={"body": created.body.replace("<!-- owlbear-generated:end -->", "")}
    )

    with pytest.raises(PublicationProviderError) as exc_info:
        publisher.update_generated_summary(_summary_request())

    assert exc_info.value.code is PublicationProviderFailureCode.CONFLICT
    assert provider.update_calls == 0


def test_rejects_summary_input_drift_before_second_metadata_write(tmp_path: Path) -> None:
    provider = _Provider()
    publisher = _publisher(tmp_path, provider)
    publisher.publish(_request())
    publisher.update_generated_summary(_summary_request())

    with pytest.raises(PublicationProviderError) as exc_info:
        publisher.update_generated_summary(_summary_request(generated_summary="Different summary."))

    assert exc_info.value.code is PublicationProviderFailureCode.CONFLICT
    assert provider.update_calls == 1


def test_new_summary_operation_updates_from_latest_provider_body(tmp_path: Path) -> None:
    provider = _Provider()
    publisher = _publisher(tmp_path, provider)
    publisher.publish(_request())
    publisher.update_generated_summary(_summary_request())
    first_body = provider.pull_requests[0].body

    second = publisher.update_generated_summary(
        _summary_request(operation_id="summary-operation-2", generated_summary="Third reviewed checkpoint.")
    )

    assert second.operation_id == "summary-operation-2"
    assert provider.update_calls == 2
    assert "Third reviewed checkpoint." in provider.pull_requests[0].body
    assert "Second reviewed checkpoint." not in provider.pull_requests[0].body
    assert provider.pull_requests[0].body != first_body


@pytest.mark.parametrize(
    "reserved_token",
    ["<!-- owlbear-generated:start -->", "<!-- owlbear-generated:end -->", "<!-- owlbear-change:other -->"],
)
def test_rejects_reserved_generated_summary_tokens_before_provider_write(
    tmp_path: Path,
    reserved_token: str,
) -> None:
    provider = _Provider()
    publisher = _publisher(tmp_path, provider)
    publisher.publish(_request())

    with pytest.raises(ValueError, match="reserved ownership marker"):
        _summary_request(generated_summary=f"Summary\n{reserved_token}")

    assert provider.update_calls == 0


def test_rejects_reserved_summary_tokens_before_draft_pr_creation() -> None:
    provider = _Provider()

    with pytest.raises(ValueError, match="reserved ownership marker"):
        _request(generated_summary="Summary\n<!-- owlbear-generated:end -->")

    assert provider.create_calls == 0


@pytest.mark.parametrize("kind", ["summary-operations", "summary-receipts"])
def test_rejects_symlinked_summary_state_before_metadata_write(tmp_path: Path, kind: str) -> None:
    provider = _Provider()
    publisher = _publisher(tmp_path, provider)
    publisher.publish(_request())
    state_root = tmp_path / "pull-requests"
    leaf_root = state_root / kind
    leaf_root.mkdir(parents=True)
    target = tmp_path / f"{kind}.json"
    target.write_text("{}\n", encoding="utf-8")
    (leaf_root / "change-a--summary-operation.json").symlink_to(target)

    with pytest.raises(PublicationProviderError) as exc_info:
        publisher.update_generated_summary(_summary_request())

    assert exc_info.value.code is PublicationProviderFailureCode.INVALID_RESPONSE
    assert provider.update_calls == 0


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
    leaf_name = "change-a--operation-1.json" if kind == "operations" else "change-a.json"
    (leaf_root / leaf_name).symlink_to(target)

    with pytest.raises(PublicationProviderError) as exc_info:
        _publisher(tmp_path, provider).publish(_request())

    assert exc_info.value.code is PublicationProviderFailureCode.INVALID_RESPONSE
    assert provider.create_calls == 0
