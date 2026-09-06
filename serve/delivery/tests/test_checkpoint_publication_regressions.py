"""Regression tests for exact checkpoint publication authority."""

# ruff: noqa: SLF001

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from serve.delivery.tests.test_portfolio_application import (
    _canonical,
    _draft_receipt,
    _finalization_request,
    _portfolio,
    _requested_branch_receipt,
    _set_checkpoint,
    _summary_receipt,
)

from owlbear_delivery import (
    ChangeBranchPublicationReceipt,
    DeliveryCheckpointTrigger,
    DeliveryCheckpointTriggerKind,
    DeliveryFrontier,
    DeliveryPendingCheckpoint,
    DeliveryStage,
    PublishChangeBranch,
)
from owlbear_delivery.portfolio_application import DeliveryRuntimeReconciliationError


def test_checkpoint_snapshot_replays_after_publication_failure(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
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

    result = application.reconcile_change_checkpoint("change-a")

    assert result.reconciled
    assert result.state.pending_checkpoint is None
    assert result.state.published_head == snapshot.snapshot_head
    assert branch_publisher.publish.call_count == 2
    assert pull_request_publisher.publish.call_count == 1
    assert pull_request_publisher.update_generated_summary.call_count == 1


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
    frontier = DeliveryFrontier.model_validate_json(frontier_path.read_bytes(), strict=False)
    frontier_path.write_bytes(
        _canonical(frontier.model_copy(update={"published_head": "2" * 40, "pending_checkpoint": None}))
    )
    application._change_branch_publisher = Mock()
    application._draft_pull_request_publisher = Mock()

    with pytest.raises(DeliveryRuntimeReconciliationError, match="published checkpoint does not match"):
        application.reconcile_change_checkpoint("change-a")
