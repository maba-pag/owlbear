"""Regression tests for exact checkpoint publication authority."""

# ruff: noqa: SLF001

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from serve.delivery.tests.test_portfolio_application import (
    _canonical,
    _finalization_request,
    _portfolio,
    _set_checkpoint,
)

from owlbear_delivery import (
    DeliveryCheckpointTrigger,
    DeliveryCheckpointTriggerKind,
    DeliveryFrontier,
    DeliveryPendingCheckpoint,
    DeliveryStage,
)
from owlbear_delivery.portfolio_application import DeliveryRuntimeReconciliationError


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
    frontier = DeliveryFrontier.model_validate_json(frontier_path.read_bytes())
    frontier_path.write_bytes(
        _canonical(frontier.model_copy(update={"published_head": "2" * 40, "pending_checkpoint": None}))
    )
    application._change_branch_publisher = Mock()
    application._draft_pull_request_publisher = Mock()

    with pytest.raises(DeliveryRuntimeReconciliationError, match="published checkpoint does not match"):
        application.reconcile_change_checkpoint("change-a")
