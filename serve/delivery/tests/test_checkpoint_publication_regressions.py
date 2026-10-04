"""Regression tests for exact checkpoint publication authority."""

# ruff: noqa: SLF001

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from serve.delivery.tests.test_delivery_state import (
    _admission,
    _canonical_payload,
    _commit_corrupt_snapshot,
    _contract,
    _publish,
    _repository,
    _runtime,
)
from serve.delivery.tests.test_portfolio_application import (
    _canonical,
    _draft_receipt,
    _finalization_request,
    _git,
    _legacy_task_result,
    _portfolio,
    _requested_branch_receipt,
    _seed_loader_composed_completed_change,
    _set_checkpoint,
    _summary_receipt,
)

from owlbear_delivery import (
    ChangeBranchPublicationReceipt,
    DeliveryChangeIntent,
    DeliveryChangeIntentKind,
    DeliveryCheckpointTrigger,
    DeliveryCheckpointTriggerKind,
    DeliveryFrontier,
    DeliveryPendingCheckpoint,
    DeliveryStage,
    DeliveryStartupConfig,
    DeliveryStatePublicationError,
    DeliveryStatePublisher,
    PublishChangeBranch,
)
from owlbear_delivery.delivery_application_loader import (
    _is_unpublished_checkpoint_successor,
    load_delivery_application,
)
from owlbear_delivery.portfolio_application import DeliveryRuntimeReconciliationError


def test_checkpoint_snapshot_replays_after_publication_failure(tmp_path: Path) -> None:
    now = ["2026-08-04T00:00:00Z"]
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
        clock=lambda: now[0],
    )
    initial_head = coordinator.show("change-a").last_reviewed_commit
    _set_checkpoint(
        runtimes["change-a"],
        state_root,
        DeliveryPendingCheckpoint(
            head=initial_head,
            triggers=(DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK),),
        ),
    )
    branch_publisher = Mock()
    branch_attempts = 0
    failure_message = "simulated publication failure"

    def publish_branch(request: PublishChangeBranch) -> ChangeBranchPublicationReceipt:
        nonlocal branch_attempts
        branch_attempts += 1
        if branch_attempts == 1:
            raise RuntimeError(failure_message)
        return _requested_branch_receipt(request)

    branch_publisher.publish.side_effect = publish_branch
    pull_request_publisher = Mock()
    pull_request_publisher.publish.side_effect = lambda request: _draft_receipt(request.published_head)
    pull_request_publisher.update_generated_summary.side_effect = lambda request: _summary_receipt(
        request.published_head
    )
    application._change_branch_publisher = branch_publisher
    application._draft_pull_request_publisher = pull_request_publisher

    with pytest.raises(RuntimeError, match=failure_message):
        application.reconcile_change_checkpoint("change-a")

    snapshot = coordinator.show("change-a").design_package_snapshot
    assert snapshot is not None
    assert snapshot.previous_head == initial_head
    assert snapshot.snapshot_head != initial_head
    failed = runtimes["change-a"].checkpoint_publication_state()
    assert failed.published_head is None
    assert failed.pending_checkpoint is not None
    assert failed.pending_checkpoint.head == snapshot.snapshot_head

    deferred = application.reconcile_change_checkpoint("change-a")

    assert not deferred.reconciled
    assert deferred.error_detail == failure_message
    assert branch_publisher.publish.call_count == 1

    now[0] = "2026-08-04T00:00:05Z"
    result = application.reconcile_change_checkpoint("change-a")

    assert result.reconciled
    assert result.state.pending_checkpoint is None
    assert result.state.published_head == snapshot.snapshot_head
    assert branch_publisher.publish.call_count == 2
    assert pull_request_publisher.publish.call_count == 1
    assert pull_request_publisher.update_generated_summary.call_count == 1


def test_state_publication_retains_checkpoint_until_pr_summary_reconciliation(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    head = coordinator.show("change-a").last_reviewed_commit
    runtime = runtimes["change-a"]
    _set_checkpoint(
        runtime,
        state_root,
        DeliveryPendingCheckpoint(
            head=head,
            triggers=(DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK),),
        ),
    )

    branch_publisher = Mock()
    branch_publisher.publish.side_effect = _requested_branch_receipt
    state_publisher = Mock()
    pull_request_publisher = Mock()
    pull_request_publisher.publish.side_effect = lambda request: _draft_receipt(request.published_head)
    pull_request_publisher.update_generated_summary.side_effect = lambda request: _summary_receipt(
        request.published_head
    )
    application._change_branch_publisher = branch_publisher
    application._delivery_state_publisher = state_publisher
    application._draft_pull_request_publisher = pull_request_publisher

    application._publish_delivery_state("change-a", runtime, "retain-checkpoint")

    pending = runtime.checkpoint_publication_state().pending_checkpoint
    assert pending is not None
    assert pending.head == head
    assert pull_request_publisher.publish.call_count == 0

    result = application.reconcile_change_checkpoint("change-a")

    assert result.reconciled
    assert runtime.checkpoint_publication_state().pending_checkpoint is None
    assert pull_request_publisher.publish.call_count == 1
    assert pull_request_publisher.update_generated_summary.call_count == 1


def test_state_publisher_rejects_unacknowledged_reviewed_change_head(tmp_path: Path) -> None:
    repository, remote, _initial = _repository(tmp_path)
    change_id = "unacknowledged-head"
    contract, _intent, _design = _contract(change_id)
    runtime, manager, _worktree = _runtime(tmp_path, repository, change_id, contract)
    frontier_path = tmp_path / "state" / "changes" / change_id / "frontier.json"
    frontier = DeliveryFrontier.model_validate_json(runtime.frontier_bytes(), strict=True)
    frontier_path.write_bytes(_canonical(frontier.model_copy(update={"published_head": "1" * 40})))

    publisher = DeliveryStatePublisher(repository, remote=str(remote), state_branch="owlbear/delivery-state")

    with pytest.raises(DeliveryStatePublicationError, match="acknowledged on its branch"):
        _publish(publisher, runtime, manager, change_id, "f" * 64, "unacknowledged-head")


def test_loader_accepts_retained_checkpoint_after_state_projection(tmp_path: Path) -> None:
    repository, runtime_root = _seed_loader_composed_completed_change(tmp_path)
    remote = tmp_path / "state-remote.git"
    _git(tmp_path, "init", "--bare", "-b", "main", str(remote))
    _git(repository, "config", f"url.{remote}.insteadOf", "https://github.com/example/project.git")
    _git(repository, "push", "origin", "HEAD:refs/heads/main")
    application = load_delivery_application(
        DeliveryStartupConfig(
            schema_version=2,
            remote="origin",
            target_branch="main",
            github_repository="example/project",
        ),
        workspace_root=repository,
    )
    runtime = application._runtimes["change-a"]
    coordination = application._workspace_manager.show("change-a")
    head = coordination.last_reviewed_commit
    _set_checkpoint(
        runtime,
        runtime_root,
        DeliveryPendingCheckpoint(
            head=head,
            triggers=(DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK),),
        ),
        published_head=head,
    )
    publisher = application._delivery_state_publisher
    assert publisher is not None
    publisher.publish(
        change_id="change-a",
        package_id=application._package_store.read_verified("change-a").package_id,
        coordination=coordination,
        runtime=runtime,
        admission=_admission(runtime, application._workspace_manager, "change-a"),
        operation_id="retained-checkpoint-state",
        captured_at=datetime(2026, 8, 4, tzinfo=UTC),
    )
    snapshot = publisher.read_snapshot("change-a")
    assert snapshot is not None
    local = DeliveryFrontier.model_validate_json(runtime.frontier_bytes(), strict=True)
    assert _is_unpublished_checkpoint_successor(snapshot.frontier, local)
    mismatched = local.pending_checkpoint.model_copy(update={"head": "0" * 40})
    assert not _is_unpublished_checkpoint_successor(
        snapshot.frontier,
        local.model_copy(update={"pending_checkpoint": mismatched}),
    )

    reloaded = load_delivery_application(
        DeliveryStartupConfig(
            schema_version=2,
            remote="origin",
            target_branch="main",
            github_repository="example/project",
            delivery_state_branch="owlbear/delivery-state",
        ),
        workspace_root=repository,
    )

    health = reloaded.delivery_health()
    assert health.diagnostics == ()
    pending = reloaded._runtimes["change-a"].checkpoint_publication_state().pending_checkpoint
    assert pending is not None
    assert pending.head == head


def test_checkpoint_snapshot_invalidates_finalization_before_publication(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    initial_head = coordinator.show("change-a").last_reviewed_commit
    finalization = application.finalize_change("change-a", _finalization_request("change-a", initial_head))
    _set_checkpoint(
        runtimes["change-a"],
        state_root,
        DeliveryPendingCheckpoint(
            head=initial_head,
            triggers=(
                DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK),
                DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.FINALIZATION),
            ),
        ),
    )
    branch_publisher = Mock()
    pull_request_publisher = Mock()
    application._change_branch_publisher = branch_publisher
    application._draft_pull_request_publisher = pull_request_publisher

    with patch.object(application._workspace_manager, "repository_automation_paths", return_value=()):
        result = application.reconcile_change_checkpoint("change-a")

    assert not result.reconciled
    assert result.attempted_head is not None
    assert result.attempted_head != initial_head
    assert result.state.published_head is None
    assert result.state.pending_checkpoint is not None
    assert result.state.pending_checkpoint.head is None
    assert runtimes["change-a"].finalization() is None
    invalidation = runtimes["change-a"].finalization_invalidation()
    assert invalidation is not None
    assert invalidation.finalization_id == finalization.finalization_id
    assert invalidation.observed_head == result.attempted_head
    snapshot = coordinator.show("change-a").design_package_snapshot
    assert snapshot is not None
    assert snapshot.snapshot_head == result.attempted_head
    assert branch_publisher.publish.call_count == 0
    assert pull_request_publisher.publish.call_count == 0


def test_checkpoint_reconcile_rejects_mismatched_heads_without_pending_queue(tmp_path: Path) -> None:
    application, _runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    exact_head = coordinator.show("change-a").last_reviewed_commit
    application.finalize_change("change-a", _finalization_request("change-a", exact_head))
    frontier_path = state_root / "changes/change-a/frontier.json"
    frontier = DeliveryFrontier.model_validate_json(frontier_path.read_bytes(), strict=True)
    frontier_path.write_bytes(
        _canonical(frontier.model_copy(update={"published_head": "2" * 40, "pending_checkpoint": None}))
    )
    application._change_branch_publisher = Mock()
    application._draft_pull_request_publisher = Mock()

    with pytest.raises(DeliveryRuntimeReconciliationError, match="published checkpoint does not match"):
        application.reconcile_change_checkpoint("change-a")


# --- N03-A stored-byte contract: a stored v18 frontier over a remote snapshot 2 (section 1.7 P/N rows) ---

_STATE_BRANCH = "owlbear/delivery-state"
_SNAPSHOT_PATH = ".owlbear/delivery/state/change-a/snapshot.json"
_CONFIG = DeliveryStartupConfig(
    schema_version=2,
    remote="origin",
    target_branch="main",
    github_repository="example/project",
    delivery_state_branch=_STATE_BRANCH,
)


def _store_v18(frontier_path: Path) -> bytes:
    """Rewrite the local frontier as a D03-era record: schema 18 holding only schema-1 evidence."""
    frontier = DeliveryFrontier.model_validate_json(frontier_path.read_bytes(), strict=True)
    legacy = frontier.model_copy(
        update={
            "bindings": tuple(
                binding.model_copy(update={"results": tuple(_legacy_task_result(item) for item in binding.results)})
                for binding in frontier.bindings
            )
        }
    )
    content = _canonical_payload(legacy.model_dump(mode="json") | {"schema_version": 18})
    frontier_path.write_bytes(content)
    return content


def _v18_loader_case(tmp_path: Path, *, retained_checkpoint: bool, stored: int) -> tuple[Path, Path, str, str]:
    """Return a loader workspace whose remote holds a snapshot 2 (frontier 18) for the stored local frontier."""
    repository, runtime_root = _seed_loader_composed_completed_change(tmp_path)
    remote = tmp_path / "state-remote.git"
    _git(tmp_path, "init", "--bare", "-b", "main", str(remote))
    _git(repository, "config", f"url.{remote}.insteadOf", "https://github.com/example/project.git")
    _git(repository, "push", "origin", "HEAD:refs/heads/main")
    application = load_delivery_application(
        DeliveryStartupConfig(
            schema_version=2, remote="origin", target_branch="main", github_repository="example/project"
        ),
        workspace_root=repository,
    )
    runtime = application._runtimes["change-a"]
    coordination = application._workspace_manager.show("change-a")
    head = coordination.last_reviewed_commit
    frontier_path = runtime_root / "changes/change-a/frontier.json"
    if retained_checkpoint:
        _set_checkpoint(
            runtime,
            runtime_root,
            DeliveryPendingCheckpoint(
                head=head,
                triggers=(DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK),),
            ),
            published_head=head,
        )
    if stored == 18:
        _store_v18(frontier_path)
    publisher = application._delivery_state_publisher
    assert publisher is not None
    published = publisher.publish(
        change_id="change-a",
        package_id=application._package_store.read_verified("change-a").package_id,
        coordination=coordination,
        runtime=runtime,
        admission=_admission(runtime, application._workspace_manager, "change-a"),
        operation_id="v18-baseline-state",
        captured_at=datetime(2026, 8, 4, tzinfo=UTC),
    )
    state_head = published.published_head
    if stored == 18:
        state_head = _relabel_as_snapshot_2(repository, state_head)
    return repository, frontier_path, head, state_head


def _relabel_as_snapshot_2(repository: Path, state_head: str, change_id: str = "change-a") -> str:
    """Rewrite the published snapshot as the pre-N03 snapshot 2 embedding the same frontier at 18."""
    path = f".owlbear/delivery/state/{change_id}/snapshot.json"
    payload = json.loads(_git(repository, "show", f"{state_head}:{path}"))
    payload["schema_version"] = 2
    payload["frontier"]["schema_version"] = 18
    payload["snapshot_id"] = ""
    payload["snapshot_id"] = hashlib.sha256(_canonical_payload(payload)).hexdigest()
    relabeled = _commit_corrupt_snapshot(repository, state_head, change_id, _canonical_payload(payload))
    _git(repository, "push", "origin", f"{relabeled}:refs/heads/{_STATE_BRANCH}", "--force")
    return relabeled


def _remote_snapshot(repository: Path) -> tuple[str, dict[str, object]]:
    _git(repository, "fetch", "origin", f"+refs/heads/{_STATE_BRANCH}:refs/remotes/origin/{_STATE_BRANCH}")
    head = _git(repository, "rev-parse", f"refs/remotes/origin/{_STATE_BRANCH}")
    return head, json.loads(_git(repository, "show", f"{head}:{_SNAPSHOT_PATH}"))


def _healthy(repository: Path, *, pending: bool = False) -> object:
    application = load_delivery_application(_CONFIG, workspace_root=repository)
    codes = [item.code for item in application.delivery_health().diagnostics]
    assert codes == (["state-publication-pending"] if pending else []), codes
    assert "change-a" in application._runtimes
    return application


def _replay_once_then_converge(repository: Path, snapshot_2_id: str, state_head: str) -> None:
    replaying = _healthy(repository, pending=True)
    assert replaying._replay_pending_state_publications() == ()
    published_head, snapshot = _remote_snapshot(repository)
    assert published_head != state_head
    assert _git(repository, "rev-list", "--count", f"{state_head}..{published_head}") == "1"
    assert snapshot["schema_version"] == 3
    assert snapshot["frontier"]["schema_version"] == 19
    assert snapshot["parent_snapshot_id"] == snapshot_2_id
    assert replaying._runtimes["change-a"].pending_state_publication() is None

    again = _healthy(repository)
    assert again._replay_pending_state_publications() == ()
    assert _remote_snapshot(repository)[0] == published_head
    assert again._runtimes["change-a"].pending_state_publication() is None


def test_first_mutation_of_a_stored_v18_frontier_records_one_marker_on_its_v18_base_and_replays(
    tmp_path: Path,
) -> None:
    repository, frontier_path, _head, state_head = _v18_loader_case(tmp_path, retained_checkpoint=False, stored=18)
    _state, snapshot_2 = _remote_snapshot(repository)
    stored = frontier_path.read_bytes()
    remote_frontier_digest = hashlib.sha256(_canonical_payload(snapshot_2["frontier"])).hexdigest()

    application = _healthy(repository)
    runtime = application._runtimes["change-a"]
    assert runtime.frontier_bytes() == stored
    assert runtime.publication_base_digest(stored) == remote_frontier_digest
    application._delivery_state_publisher = None
    application.set_change_intent(
        DeliveryChangeIntent(
            change_id="change-a",
            kind=DeliveryChangeIntentKind.DEFER,
            expected_frontier_digest=hashlib.sha256(stored).hexdigest(),
            reason="Hold the stored v18 Change",
        )
    )

    written = frontier_path.read_bytes()
    assert json.loads(written)["schema_version"] == 19
    marker = runtime.pending_state_publication()
    assert marker is not None
    assert marker.base_frontier_digest == remote_frontier_digest
    assert marker.frontier_digest == hashlib.sha256(written).hexdigest()
    reloaded = _healthy(repository, pending=True)
    assert reloaded._runtimes["change-a"].change_deferral() is not None
    assert frontier_path.read_bytes() == written

    _replay_once_then_converge(repository, str(snapshot_2["snapshot_id"]), state_head)
    assert _git(repository, "show", f"{state_head}:{_SNAPSHOT_PATH}").encode() + b"\n" == _canonical_payload(snapshot_2)


@pytest.mark.parametrize("stored", [18, 19])
def test_drained_acknowledgment_of_a_stored_frontier_records_a_marker_only_for_v18(tmp_path: Path, stored: int) -> None:
    repository, frontier_path, head, state_head = _v18_loader_case(tmp_path, retained_checkpoint=True, stored=stored)
    _state, snapshot = _remote_snapshot(repository)
    assert snapshot["schema_version"] == (2 if stored == 18 else 3)
    assert snapshot["frontier"].get("pending_checkpoint") is None
    before = frontier_path.read_bytes()

    application = _healthy(repository)
    runtime = application._runtimes["change-a"]
    assert frontier_path.read_bytes() == before
    pending = runtime.checkpoint_publication_state().pending_checkpoint
    assert pending is not None
    runtime.acknowledge_checkpoint_publication(pending, head)

    acknowledged = frontier_path.read_bytes()
    assert json.loads(acknowledged)["schema_version"] == 19
    assert json.loads(acknowledged).get("pending_checkpoint") is None
    marker = runtime.pending_state_publication()
    if stored == 19:
        assert marker is None
        return
    assert marker is not None
    assert marker.base_frontier_digest == hashlib.sha256(_canonical_payload(snapshot["frontier"])).hexdigest()
    assert marker.base_frontier_digest != runtime.publication_base_digest(before)
    assert _healthy(repository, pending=True)._runtimes["change-a"].frontier_bytes() == acknowledged

    _replay_once_then_converge(repository, str(snapshot["snapshot_id"]), state_head)
