from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import NamedTuple
from unittest.mock import Mock, patch

import pytest

from owlbear_delivery import (
    AdvanceDelivery,
    BlockDelivery,
    ChangeBranchPublisher,
    ChangeDirectOperation,
    ChangePauseRequest,
    ChangePauseRequestedError,
    ChangeTargetSyncReceipt,
    DeliveryAcceptanceAttentionReason,
    DeliveryActiveClaim,
    DeliveryAdmissionReceipt,
    DeliveryAdmissionRequest,
    DeliveryBlock,
    DeliveryBuilderInvocationSettlement,
    DeliveryChangeCompletion,
    DeliveryChangeDisposition,
    DeliveryChangeDispositionKind,
    DeliveryChangeIntent,
    DeliveryChangeIntentKind,
    DeliveryChangeStage,
    DeliveryCommandResult,
    DeliveryCommitment,
    DeliveryCommitmentClass,
    DeliveryContract,
    DeliveryFinalization,
    DeliveryFinalizationInvalidation,
    DeliveryFinalizationInvalidationReceipt,
    DeliveryFinalizationReceipt,
    DeliveryFrontier,
    DeliveryHealthHeadRelation,
    DeliveryHealthReason,
    DeliveryLaunchPackage,
    DeliveryMergedPullRequestLatch,
    DeliveryObservation,
    DeliveryObservationReceipt,
    DeliveryOutcome,
    DeliveryPlanCandidate,
    DeliveryPlanningRetrySettlement,
    DeliveryPlanScope,
    DeliveryRequest,
    DeliveryRequestKind,
    DeliveryRequestOption,
    DeliveryRequestResolution,
    DeliveryRetryDiagnostic,
    DeliveryReview,
    DeliveryReviewReceipt,
    DeliveryRuntime,
    DeliveryRuntimeConflictError,
    DeliveryStage,
    DeliveryStateConflictError,
    DeliveryStatePublicationError,
    DeliveryStatePublisher,
    DeliveryStateQuarantineError,
    DeliveryStateResponseUnknownError,
    DeliveryStateSnapshot,
    DeliveryTaskDefinition,
    DeliveryTaskResult,
    DeliveryWorkerExclusionRequiredError,
    DeliveryWorkerRole,
    DesignPackageManifest,
    DesignPackageStore,
    OutcomeAuthorityBinding,
    PortfolioApplication,
    PortfolioCoordinator,
    PublishChangeBranch,
    PublishDeliveryPlan,
    PublishDeliveryResult,
    RetryDelivery,
    ReturnDelivery,
    SyncChangeWithTarget,
    WindowHostIdentity,
    remote_git,
    state_migration,
)
from owlbear_delivery.acceptance import (
    CompletionDisplayMetadata,
    CompletionEvidence,
    CompletionPullRequestIdentity,
    CompletionReceipt,
)
from owlbear_delivery.change_workspace import ChangeWorkspaceManager
from owlbear_delivery.delivery_admission import DeliveryRevisionError
from owlbear_delivery.delivery_application_loader import (
    DeliveryApplicationLoadError,
    DeliveryStartupConfig,
    DeliveryStateVersionError,
    _can_defer_remote_state_reconciliation,
    _DeferredRemoteStateReconciliationError,
    _fetch_snapshot_change_head,
    _is_unpublished_acceptance_attention_successor,
    _is_unpublished_claim_successor,
    _is_unpublished_target_sync_attention_successor,
    _RemoteChangeHeadMismatchError,
    _require_local_snapshot_branch,
    close_delivery_application,
    load_configured_delivery_application,
    load_delivery_application,
)
from owlbear_delivery.delivery_runtime import (
    _DeliveryBuilderPlanPromotionReceipt,
    _DeliveryPlanningPauseReplay,
    _model_content,
)
from owlbear_delivery.delivery_state import parse_delivery_state_snapshot
from owlbear_delivery.draft_pull_request import PullRequestReadyReceipt
from owlbear_delivery.git_executable import resolve_git_executable
from owlbear_delivery.state_formats import format_marker_bytes
from owlbear_delivery.target_contract import DeliverySourceBinding
from owlbear_delivery.workspace_models import (
    ChangeDesignPackageSnapshotReceipt,
    DesignPackageSnapshotEditedError,
    DirtyWorktreeQuarantineReceipt,
)

_GIT = resolve_git_executable()


def _git(repository: Path, *arguments: str, check: bool = True) -> str:
    result = subprocess.run(  # noqa: S603
        (_GIT, "-C", str(repository), *arguments),
        check=check,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _repository(tmp_path: Path) -> tuple[Path, Path, str]:
    remote = tmp_path / "remote.git"
    _git(tmp_path, "init", "--bare", "-b", "main", str(remote))
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.name", "Delivery State Test")
    _git(repository, "config", "user.email", "delivery-state@example.invalid")
    (repository / "product.txt").write_text("baseline\n", encoding="utf-8")
    _git(repository, "add", "product.txt")
    _git(repository, "commit", "-m", "baseline")
    initial = _git(repository, "rev-parse", "HEAD")
    _git(repository, "remote", "add", "origin", str(remote))
    _git(repository, "push", "origin", "HEAD:refs/heads/main")
    _git(repository, "fetch", "origin", "refs/heads/main:refs/remotes/origin/main")
    return repository, remote, initial


def _contract(change_id: str) -> tuple[DeliveryContract, bytes, bytes]:
    intent = f"# Intent {change_id}\n".encode()
    design = f"# Design {change_id}\n".encode()
    contract = DeliveryContract(
        change_id=change_id,
        title=f"Delivery {change_id}",
        commitments=(
            DeliveryCommitment(
                commitment_id="COM-001",
                commitment_class=DeliveryCommitmentClass.AGREED_PATH,
                provenance="test",
                statement="Preserve state.",
            ),
        ),
        outcomes=(
            DeliveryOutcome(
                outcome_id="OUT-001",
                title="State",
                promise="Persist state.",
                acceptance=("State persists.",),
                commitment_ids=("COM-001",),
                dependency_ids=(),
            ),
        ),
        plan_scopes=(DeliveryPlanScope(scope_id="SCOPE-001", outcome_id="OUT-001"),),
        source_bindings=(
            DeliverySourceBinding(source_name="intent.md", sha256=hashlib.sha256(intent).hexdigest()),
            DeliverySourceBinding(source_name="design.md", sha256=hashlib.sha256(design).hexdigest()),
        ),
    )
    return contract, intent, design


def _runtime(
    tmp_path: Path,
    repository: Path,
    change_id: str,
    contract: DeliveryContract,
) -> tuple[DeliveryRuntime, ChangeWorkspaceManager, Path]:
    state_root = tmp_path / "state"
    coordinator = PortfolioCoordinator(state_root)
    manager = ChangeWorkspaceManager(repository, tmp_path / "worktrees", coordinator, "main")
    coordination = manager.ensure(change_id)
    frontier_path = state_root / "changes" / change_id / "frontier.json"
    frontier_path.parent.mkdir(parents=True, exist_ok=True)
    frontier = DeliveryFrontier(
        bindings=(
            OutcomeAuthorityBinding(
                outcome_id="OUT-001",
                plan_scope_id="SCOPE-001",
            ),
        ),
    )
    frontier_path.write_bytes(
        (json.dumps(frontier.model_dump(mode="json"), sort_keys=True, separators=(",", ":")) + "\n").encode()
    )
    return DeliveryRuntime(state_root, contract, workspace_manager=manager), manager, coordination.worktree_path


def _publish(  # noqa: PLR0913, PLR0917 - helper binds the exact publisher inputs.
    publisher: DeliveryStatePublisher,
    runtime: DeliveryRuntime,
    manager: ChangeWorkspaceManager,
    change_id: str,
    package_id: str,
    operation_id: str,
    *,
    expected_remote_head: str | None = None,
):
    admission = _admission(runtime, manager, change_id)
    return publisher.publish(
        change_id=change_id,
        package_id=package_id,
        coordination=manager.show(change_id),
        runtime=runtime,
        admission=admission,
        operation_id=operation_id,
        captured_at=datetime(2026, 8, 23, tzinfo=UTC),
        expected_remote_head=expected_remote_head,
    )


def _admission(runtime: DeliveryRuntime, manager: ChangeWorkspaceManager, change_id: str) -> DeliveryAdmissionReceipt:
    frontier = DeliveryFrontier.model_validate_json(runtime.frontier_bytes(), strict=True)
    contract_bytes = (
        json.dumps(runtime.contract.model_dump(mode="json"), sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()
    source_bindings = [item.model_dump(mode="json") for item in runtime.contract.source_bindings]
    admission_values = {
        "schema_version": 1,
        "change_id": change_id,
        "contract_digest": hashlib.sha256(contract_bytes).hexdigest(),
        "source_bindings_digest": hashlib.sha256(
            json.dumps(source_bindings, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "integration_target": manager.show(change_id).integration_target,
        "checkpoint_commit": manager.show(change_id).last_reviewed_commit,
        "frontier_ids": tuple(binding.plan_scope_id for binding in frontier.bindings),
    }
    return DeliveryAdmissionReceipt(
        receipt_id=hashlib.sha256(
            json.dumps(admission_values, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        **admission_values,
    )


def _startup_config() -> DeliveryStartupConfig:
    return DeliveryStartupConfig(
        schema_version=2,
        remote="origin",
        target_branch="main",
        github_repository="example/project",
    )


def _snapshot(
    runtime: DeliveryRuntime,
    manager: ChangeWorkspaceManager,
    change_id: str,
) -> DeliveryStateSnapshot:
    return DeliveryStateSnapshot.create(
        operation_id=f"snapshot-{change_id}",
        change_id=change_id,
        package_id="f" * 64,
        coordination=manager.show(change_id),
        runtime=runtime,
        admission=_admission(runtime, manager, change_id),
        sequence=1,
        parent_snapshot_id=None,
        base_head=None,
        captured_at=datetime(2026, 8, 23, tzinfo=UTC),
    )


def _canonical_payload(payload: object) -> bytes:
    return (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _commit_descendant(worktree: Path, filename: str, message: str) -> str:
    (worktree / filename).write_text(f"{message}\n", encoding="utf-8")
    _git(worktree, "add", filename)
    _git(worktree, "commit", "-m", message)
    return _git(worktree, "rev-parse", "HEAD")


def _commit_corrupt_snapshot(repository: Path, base: str, change_id: str, raw: bytes) -> str:
    index_path = repository.parent / f"{change_id}-state-index"
    environment = {**os.environ, "GIT_INDEX_FILE": str(index_path)}
    try:
        subprocess.run(  # noqa: S603
            (_GIT, "-C", str(repository), "read-tree", base), check=True, env=environment
        )
        blob = (
            subprocess.run(  # noqa: S603
                (_GIT, "-C", str(repository), "hash-object", "-w", "--stdin"),
                check=True,
                capture_output=True,
                input=raw,
                env=environment,
            )
            .stdout.decode()
            .strip()
        )
        subprocess.run(  # noqa: S603
            (
                _GIT,
                "-C",
                str(repository),
                "update-index",
                "--add",
                "--cacheinfo",
                f"100644,{blob},.owlbear/delivery/state/{change_id}/snapshot.json",
            ),
            check=True,
            env=environment,
        )
        tree = subprocess.run(  # noqa: S603
            (_GIT, "-C", str(repository), "write-tree"),
            check=True,
            capture_output=True,
            text=True,
            env=environment,
        ).stdout.strip()
        return subprocess.run(  # noqa: S603
            (
                _GIT,
                "-C",
                str(repository),
                "commit-tree",
                tree,
                "-p",
                base,
                "-m",
                f"corrupt Delivery state ({change_id})",
            ),
            check=True,
            capture_output=True,
            text=True,
            env=environment,
        ).stdout.strip()
    finally:
        index_path.unlink(missing_ok=True)


def test_loader_defers_active_remote_descendant_drift(tmp_path: Path) -> None:
    repository, _remote, _initial = _repository(tmp_path)
    change_id = "state-descendant"
    contract, _intent, _design = _contract(change_id)
    runtime, manager, worktree = _runtime(tmp_path, repository, change_id, contract)
    snapshot = _snapshot(runtime, manager, change_id)
    descendant = _commit_descendant(worktree, "descendant.txt", "active descendant")

    assert _can_defer_remote_state_reconciliation(snapshot, repository, descendant)
    with (
        patch(
            "owlbear_delivery.delivery_application_loader._remote_branch_head",
            return_value=descendant,
        ),
        pytest.raises(_DeferredRemoteStateReconciliationError),
    ):
        _fetch_snapshot_change_head(snapshot, _startup_config(), repository)


def test_loader_accepts_local_descendant_when_active_remote_branch_was_deleted(tmp_path: Path) -> None:
    repository, _remote, _initial = _repository(tmp_path)
    change_id = "state-local-fallback"
    contract, _intent, _design = _contract(change_id)
    runtime, manager, _worktree = _runtime(tmp_path, repository, change_id, contract)
    snapshot = _snapshot(runtime, manager, change_id)
    _commit_descendant(manager.show(change_id).worktree_path, "descendant.txt", "local descendant")

    with pytest.raises(
        DeliveryApplicationLoadError,
        match="remote Change branch is missing for an active Delivery snapshot",
    ):
        _fetch_snapshot_change_head(snapshot, _startup_config(), repository)

    with pytest.raises(
        DeliveryApplicationLoadError,
        match="remote Change branch is missing for an active Delivery snapshot",
    ):
        _fetch_snapshot_change_head(snapshot, _startup_config(), repository, allow_local_branch=True)

    with pytest.raises(
        DeliveryApplicationLoadError,
        match="remote Change branch is missing for an active Delivery snapshot",
    ):
        _fetch_snapshot_change_head(snapshot, _startup_config(), repository, allow_local_branch=True)


def test_loader_accepts_unpublished_acceptance_attention_successor(tmp_path: Path) -> None:
    repository, _remote, _initial = _repository(tmp_path)
    change_id = "state-acceptance-attention-fallback"
    contract, _intent, _design = _contract(change_id)
    runtime, manager, worktree = _runtime(tmp_path, repository, change_id, contract)
    snapshot = _snapshot(runtime, manager, change_id)
    local_frontier = snapshot.frontier.model_copy(
        update={
            "change_disposition": DeliveryChangeDisposition.create(
                kind=DeliveryChangeDispositionKind.ACCEPTANCE_ATTENTION,
                change_id=change_id,
                entered_from=DeliveryChangeStage.AWAITING_MERGE,
                recorded_at=datetime(2026, 8, 23, 1, tzinfo=UTC),
                diagnostics=("provider acceptance evidence regressed",),
                acceptance_reason=DeliveryAcceptanceAttentionReason.LATCH_REGRESSION,
            ),
        }
    )
    _commit_descendant(worktree, "acceptance-attention.txt", "acceptance attention")

    assert _is_unpublished_acceptance_attention_successor(snapshot.frontier, local_frontier)
    with patch(
        "owlbear_delivery.delivery_application_loader._remote_branch_head",
        return_value=None,
    ):
        assert _fetch_snapshot_change_head(
            snapshot,
            _startup_config(),
            repository,
            allow_local_branch=True,
            allow_local_descendant=True,
        ) == (snapshot.change_head, False)


def test_loader_accepts_unpublished_target_sync_attention_successor() -> None:
    receipt = ChangeTargetSyncReceipt.create(
        operation_id="sync-previous",
        change_id="state-target-sync-attention-fallback",
        integration_target="main",
        expected_target="4" * 40,
        target_head="4" * 40,
        change_head_before="1" * 40,
        merged_head="5" * 40,
        merge_commit=True,
    )
    snapshot_frontier = DeliveryFrontier(bindings=(), target_sync_receipt=receipt)
    disposition = DeliveryChangeDisposition.create(
        kind=DeliveryChangeDispositionKind.PUBLICATION_ATTENTION,
        change_id=receipt.change_id,
        entered_from=DeliveryChangeStage.FINALIZED,
        recorded_at=datetime(2026, 8, 23, 1, tzinfo=UTC),
        diagnostics=("target-sync-operation:sync-current", "target synchronization merge conflict"),
    )
    local_frontier = snapshot_frontier.model_copy(
        update={"target_sync_receipt": None, "change_disposition": disposition}
    )

    assert _is_unpublished_target_sync_attention_successor(snapshot_frontier, local_frontier)
    assert not _is_unpublished_target_sync_attention_successor(
        snapshot_frontier,
        local_frontier.model_copy(update={"target_sync_receipt": receipt}),
    )


def test_loader_accepts_unpublished_head_moved_acceptance_successor(tmp_path: Path) -> None:
    repository, _remote, initial = _repository(tmp_path)
    change_id = "state-head-moved-fallback"
    contract, _intent, _design = _contract(change_id)
    runtime, manager, worktree = _runtime(tmp_path, repository, change_id, contract)
    snapshot = _snapshot(runtime, manager, change_id)
    observed_at = datetime(2026, 8, 23, 1, tzinfo=UTC)
    operation_id = "finalize-state-head-moved-fallback"
    observation = DeliveryObservationReceipt.create(
        DeliveryObservation(
            change_id=change_id,
            task_or_finalization_id=operation_id,
            exact_commit=initial,
            observation_kind="snapshot-test",
            procedure="head moved acceptance fallback",
            result=DeliveryCommandResult(exit_status=0),
            observer_or_runner_identity="pytest",
            observed_at=observed_at,
        )
    )
    review = DeliveryReviewReceipt.create(
        DeliveryReview(
            review_mode="finalization",
            basis_digest="e" * 64,
            observation_ids=(observation.observation_id,),
            exact_commit=initial,
            author_id="snapshot-head-moved-author",
            reviewer_id="snapshot-head-moved-reviewer",
            evidence=("The head-moved successor retains its invalidation authority.",),
            reviewed_at=observed_at,
        )
    )
    finalization = DeliveryFinalizationReceipt.create(
        DeliveryFinalization(
            operation_id=operation_id,
            change_id=change_id,
            exact_head=initial,
            authority_digest=runtime.authority_digest,
            result_digests=("a" * 64,),
            observations=(observation,),
            review=review,
            finalized_at=observed_at,
        )
    )
    snapshot_frontier = snapshot.frontier.model_copy(update={"finalization": finalization, "published_head": initial})
    local_frontier = snapshot_frontier.model_copy(
        update={
            "finalization": None,
            "finalization_invalidation": DeliveryFinalizationInvalidationReceipt.create(
                DeliveryFinalizationInvalidation(
                    change_id=change_id,
                    finalization_id=finalization.finalization_id,
                    expected_head=finalization.exact_head,
                    observed_head="c" * 40,
                    invalidated_at=observed_at,
                )
            ),
            "change_disposition": DeliveryChangeDisposition.create(
                kind=DeliveryChangeDispositionKind.ACCEPTANCE_ATTENTION,
                change_id=change_id,
                entered_from=DeliveryChangeStage.AWAITING_MERGE,
                recorded_at=datetime(2026, 8, 23, 1, tzinfo=UTC),
                diagnostics=("provider pull request head differs from finalized Change head",),
                acceptance_reason=DeliveryAcceptanceAttentionReason.HEAD_MOVED,
            ),
        }
    )
    _commit_descendant(worktree, "head-moved.txt", "head moved")

    assert _is_unpublished_acceptance_attention_successor(snapshot_frontier, local_frontier)
    assert not _is_unpublished_acceptance_attention_successor(
        snapshot_frontier,
        local_frontier.model_copy(update={"finalization": finalization}),
    )
    with patch(
        "owlbear_delivery.delivery_application_loader._remote_branch_head",
        return_value=None,
    ):
        assert _fetch_snapshot_change_head(
            snapshot,
            _startup_config(),
            repository,
            allow_local_branch=True,
            allow_local_descendant=True,
        ) == (snapshot.change_head, False)


def test_loader_accepts_finalized_snapshot_when_remote_change_branch_was_deleted(tmp_path: Path) -> None:
    repository, _remote, initial = _repository(tmp_path)
    change_id = "state-finalized-fallback"
    contract, _intent, _design = _contract(change_id)
    runtime, manager, _worktree = _runtime(tmp_path, repository, change_id, contract)
    snapshot = _snapshot(runtime, manager, change_id)
    observed_at = datetime(2026, 8, 23, 12, tzinfo=UTC)
    operation_id = "finalize-state-finalized-fallback"
    observation = DeliveryObservationReceipt.create(
        DeliveryObservation(
            change_id=change_id,
            task_or_finalization_id=operation_id,
            exact_commit=initial,
            observation_kind="snapshot-test",
            procedure="finalized snapshot target fallback",
            result=DeliveryCommandResult(exit_status=0),
            observer_or_runner_identity="pytest",
            observed_at=observed_at,
        )
    )
    review = DeliveryReviewReceipt.create(
        DeliveryReview(
            review_mode="finalization",
            basis_digest="e" * 64,
            observation_ids=(observation.observation_id,),
            exact_commit=initial,
            author_id="snapshot-finalization-author",
            reviewer_id="snapshot-finalization-reviewer",
            evidence=("The finalized snapshot exact head is present on the target.",),
            reviewed_at=observed_at,
        )
    )
    finalization = DeliveryFinalizationReceipt.create(
        DeliveryFinalization(
            operation_id=operation_id,
            change_id=change_id,
            exact_head=initial,
            authority_digest=runtime.authority_digest,
            result_digests=("a" * 64,),
            observations=(observation,),
            review=review,
            finalized_at=observed_at,
        )
    )
    finalized_frontier = snapshot.frontier.model_copy(
        update={
            "bindings": (
                OutcomeAuthorityBinding(
                    outcome_id="OUT-001",
                    plan_scope_id="SCOPE-001",
                    stage=DeliveryStage.COMPLETED,
                ),
            ),
            "finalization": finalization,
        }
    )
    finalized_snapshot = snapshot.model_copy(update={"frontier": finalized_frontier})

    with patch(
        "owlbear_delivery.delivery_application_loader._remote_branch_head",
        return_value=None,
    ):
        assert _fetch_snapshot_change_head(finalized_snapshot, _startup_config(), repository) == (initial, False)

    assert finalized_snapshot.frontier.ready is None
    assert finalized_snapshot.frontier.change_completion is None


def test_loader_does_not_defer_completed_remote_descendant_drift(tmp_path: Path) -> None:
    repository, _remote, _initial = _repository(tmp_path)
    change_id = "state-completed"
    contract, _intent, _design = _contract(change_id)
    runtime, manager, worktree = _runtime(tmp_path, repository, change_id, contract)
    snapshot = _snapshot(runtime, manager, change_id)
    completed = snapshot.model_copy(
        update={
            "frontier": snapshot.frontier.model_copy(
                update={
                    "change_completion": DeliveryChangeCompletion(
                        completion_id="a" * 64,
                        completed_at=datetime(2026, 8, 23, tzinfo=UTC),
                    )
                }
            )
        }
    )
    descendant = _commit_descendant(worktree, "completed-descendant.txt", "completed descendant")

    assert not _can_defer_remote_state_reconciliation(completed, repository, descendant)
    with (
        patch(
            "owlbear_delivery.delivery_application_loader._remote_branch_head",
            return_value=descendant,
        ),
        pytest.raises(
            DeliveryApplicationLoadError,
            match="remote Change branch differs from Delivery-state snapshot: state-completed",
        ),
    ):
        _fetch_snapshot_change_head(completed, _startup_config(), repository)


def test_loader_rejects_divergent_remote_branch_drift(tmp_path: Path) -> None:
    repository, _remote, initial = _repository(tmp_path)
    change_id = "state-divergent"
    contract, _intent, _design = _contract(change_id)
    runtime, manager, worktree = _runtime(tmp_path, repository, change_id, contract)
    reviewed = _commit_descendant(worktree, "reviewed.txt", "reviewed state")
    manager.record_reviewed(change_id, reviewed)
    snapshot = _snapshot(runtime, manager, change_id)
    divergent = _commit_descendant(repository, "divergent.txt", "divergent state")

    assert initial != divergent
    assert not _can_defer_remote_state_reconciliation(snapshot, repository, divergent)
    with (
        patch(
            "owlbear_delivery.delivery_application_loader._remote_branch_head",
            return_value=divergent,
        ),
        pytest.raises(
            DeliveryApplicationLoadError,
            match="remote Change branch differs from Delivery-state snapshot: state-divergent",
        ),
    ):
        _fetch_snapshot_change_head(snapshot, _startup_config(), repository)


def test_loader_remote_head_mismatch_retains_typed_head_evidence(tmp_path: Path) -> None:
    repository, _remote, initial = _repository(tmp_path)
    change_id = "state-head-evidence"
    contract, _intent, _design = _contract(change_id)
    runtime, manager, worktree = _runtime(tmp_path, repository, change_id, contract)
    reviewed = _commit_descendant(worktree, "reviewed.txt", "reviewed state")
    manager.record_reviewed(change_id, reviewed)
    snapshot = _snapshot(runtime, manager, change_id)

    with (
        patch(
            "owlbear_delivery.delivery_application_loader._remote_branch_head",
            return_value=initial,
        ),
        pytest.raises(_RemoteChangeHeadMismatchError) as exc_info,
    ):
        _fetch_snapshot_change_head(snapshot, _startup_config(), repository)

    error = exc_info.value
    assert error.expected_head == reviewed
    assert error.observed_head == initial
    assert error.observed_local_head == reviewed
    assert error.head_relation is DeliveryHealthHeadRelation.ANCESTOR
    assert error.reason is DeliveryHealthReason.REMOTE_CHANGE_HEAD_MISMATCH


def test_state_publisher_round_trips_and_replays_without_primary_checkout_changes(tmp_path: Path) -> None:
    repository, remote, initial = _repository(tmp_path)
    contract, _intent, _design = _contract("state-change")
    runtime, manager, _worktree = _runtime(tmp_path, repository, "state-change", contract)
    publisher = DeliveryStatePublisher(repository, remote=str(remote), state_branch="owlbear/delivery-state")
    before = (_git(repository, "rev-parse", "HEAD"), _git(repository, "status", "--porcelain"))

    report = tmp_path / "state/finalization-reports/state-change/reports/host-only.json"
    report.parent.mkdir(parents=True)
    report.write_bytes(b"host-local diagnostic sentinel")

    receipt = _publish(publisher, runtime, manager, "state-change", "a" * 64, "state-one")
    replayed = _publish(publisher, runtime, manager, "state-change", "a" * 64, "state-one")
    snapshots = publisher.read_snapshots()

    assert replayed == receipt
    assert len(snapshots) == 1
    assert snapshots[0].snapshot_id == receipt.snapshot_id
    assert snapshots[0].change_id == "state-change"
    assert snapshots[0].contract == contract
    assert snapshots[0].frontier == DeliveryFrontier.model_validate_json(runtime.frontier_bytes(), strict=True)
    assert "finalization-reports" not in _git(
        remote, "ls-tree", "-r", "--name-only", "refs/heads/owlbear/delivery-state"
    )
    assert b"host-local diagnostic sentinel" not in snapshots[0].model_dump_json().encode()
    assert report.read_bytes() == b"host-local diagnostic sentinel"
    assert _git(repository, "rev-parse", "HEAD") == before[0] == initial
    assert _git(repository, "status", "--porcelain") == before[1]


def test_state_publisher_repairs_quarantined_snapshot_with_exact_fences(tmp_path: Path) -> None:
    repository, remote, _initial = _repository(tmp_path)
    contract, _intent, _design = _contract("state-repair")
    runtime, manager, _worktree = _runtime(tmp_path, repository, "state-repair", contract)
    publisher = DeliveryStatePublisher(repository, remote=str(remote), state_branch="owlbear/delivery-state")
    first = _publish(publisher, runtime, manager, "state-repair", "a" * 64, "state-repair-one")
    snapshot_path = ".owlbear/delivery/state/state-repair/snapshot.json"
    original = publisher._git_blob(first.published_head, snapshot_path)  # noqa: SLF001
    corrupted_payload = json.loads(original)
    corrupted_payload["snapshot_id"] = "0" * 64
    corrupted = (json.dumps(corrupted_payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
    corrupted_head = _commit_corrupt_snapshot(repository, first.published_head, "state-repair", corrupted)
    _git(repository, "push", "origin", f"{corrupted_head}:refs/heads/owlbear/delivery-state", "--force")
    corrupted_digest = hashlib.sha256(corrupted).hexdigest()

    inventory = publisher.read_snapshot_inventory()
    diagnostic = next(item for item in inventory.diagnostics if item.change_id == "state-repair")
    assert inventory.remote_head == corrupted_head
    assert diagnostic.code == "snapshot-identity-invalid"
    assert diagnostic.raw_digest == corrupted_digest
    with pytest.raises(DeliveryStateQuarantineError, match="quarantined") as conflict:
        _publish(publisher, runtime, manager, "state-repair", "b" * 64, "state-repair-two")
    assert conflict.value.retry_safe is False
    assert conflict.value.diagnostic_code == "snapshot-identity-invalid"

    with pytest.raises(DeliveryStateConflictError, match="diagnostic changed"):
        publisher.repair_quarantined_snapshot(
            change_id="state-repair",
            package_id="b" * 64,
            coordination=manager.show("state-repair"),
            runtime=runtime,
            admission=_admission(runtime, manager, "state-repair"),
            operation_id="state-repair-two",
            captured_at=datetime(2026, 8, 23, tzinfo=UTC),
            expected_remote_head=corrupted_head,
            expected_snapshot_digest=corrupted_digest,
            expected_diagnostic_code="snapshot-invalid",
        )

    repaired = publisher.repair_quarantined_snapshot(
        change_id="state-repair",
        package_id="b" * 64,
        coordination=manager.show("state-repair"),
        runtime=runtime,
        admission=_admission(runtime, manager, "state-repair"),
        operation_id="state-repair-two",
        captured_at=datetime(2026, 8, 23, tzinfo=UTC),
        expected_remote_head=corrupted_head,
        expected_snapshot_digest=corrupted_digest,
        expected_diagnostic_code="snapshot-identity-invalid",
    )

    snapshot = publisher.read_snapshot("state-repair")
    assert snapshot is not None
    assert snapshot.repaired_predecessor_digest == corrupted_digest
    assert snapshot.base_head == corrupted_head
    assert repaired.snapshot_id == snapshot.snapshot_id
    assert (
        publisher.repair_quarantined_snapshot(
            change_id="state-repair",
            package_id="b" * 64,
            coordination=manager.show("state-repair"),
            runtime=runtime,
            admission=_admission(runtime, manager, "state-repair"),
            operation_id="state-repair-two",
            captured_at=datetime(2026, 8, 23, tzinfo=UTC),
            expected_remote_head=corrupted_head,
            expected_snapshot_digest=corrupted_digest,
            expected_diagnostic_code="snapshot-identity-invalid",
        )
        == repaired
    )
    assert publisher._git_blob(corrupted_head, snapshot_path) == corrupted  # noqa: SLF001


def test_state_snapshot_migrates_schema_1_and_retains_predecessor_identity(tmp_path: Path) -> None:
    repository, _remote, _initial = _repository(tmp_path)
    contract, _intent, _design = _contract("legacy-state")
    runtime, manager, _worktree = _runtime(tmp_path, repository, "legacy-state", contract)
    current = _snapshot(runtime, manager, "legacy-state").model_dump(mode="json")
    current.pop("migrated_from_snapshot_id")
    current.pop("repaired_predecessor_digest")
    current["schema_version"] = 1
    current["frontier"]["schema_version"] = 17
    for binding in current["frontier"]["bindings"]:
        binding.pop("retry_count")
        binding.pop("retry_fingerprint")
    current["snapshot_id"] = ""
    legacy_snapshot_id = hashlib.sha256(_canonical_payload(current)).hexdigest()
    current["snapshot_id"] = legacy_snapshot_id
    raw = _canonical_payload(current)

    migrated = parse_delivery_state_snapshot(raw)

    assert migrated.schema_version == 3
    assert migrated.migrated_from_snapshot_id == legacy_snapshot_id
    assert migrated.frontier.schema_version == 18
    assert migrated.frontier.bindings[0].retry_count == 0


def test_state_snapshot_published_before_optional_binding_fields_keeps_identity(tmp_path: Path) -> None:
    repository, _remote, _initial = _repository(tmp_path)
    contract, _intent, _design = _contract("pre-d03-state")
    runtime, manager, _worktree = _runtime(tmp_path, repository, "pre-d03-state", contract)
    published = _snapshot(runtime, manager, "pre-d03-state").model_dump(mode="json")
    for binding in published["frontier"]["bindings"]:
        binding.pop("builder_handoff_context", None)
        binding.pop("retry_diagnostic", None)
    published["snapshot_id"] = ""
    published["snapshot_id"] = hashlib.sha256(_canonical_payload(published)).hexdigest()
    raw = _canonical_payload(published)

    parsed = parse_delivery_state_snapshot(raw)

    assert parsed.snapshot_id == published["snapshot_id"]
    assert parsed.migrated_from_snapshot_id is None
    assert _canonical_payload(parsed.model_dump(mode="json")) == raw


def test_state_publisher_rewrites_migrated_snapshot_to_current_schema(tmp_path: Path) -> None:
    repository, remote, _initial = _repository(tmp_path)
    contract, _intent, _design = _contract("legacy-publish")
    runtime, manager, _worktree = _runtime(tmp_path, repository, "legacy-publish", contract)
    publisher = DeliveryStatePublisher(repository, remote=str(remote), state_branch="owlbear/delivery-state")
    first = _publish(publisher, runtime, manager, "legacy-publish", "a" * 64, "legacy-publish-one")
    snapshot_path = ".owlbear/delivery/state/legacy-publish/snapshot.json"
    legacy_payload = json.loads(publisher._git_blob(first.published_head, snapshot_path))  # noqa: SLF001
    legacy_payload.pop("migrated_from_snapshot_id")
    legacy_payload.pop("repaired_predecessor_digest")
    legacy_payload["schema_version"] = 1
    legacy_payload["frontier"]["schema_version"] = 17
    for binding in legacy_payload["frontier"]["bindings"]:
        binding.pop("retry_count")
        binding.pop("retry_fingerprint")
    legacy_payload["snapshot_id"] = ""
    legacy_payload["snapshot_id"] = hashlib.sha256(_canonical_payload(legacy_payload)).hexdigest()
    legacy_raw = _canonical_payload(legacy_payload)
    legacy_head = _commit_corrupt_snapshot(repository, first.published_head, "legacy-publish", legacy_raw)
    _git(repository, "push", "origin", f"{legacy_head}:refs/heads/owlbear/delivery-state", "--force")

    rewritten = _publish(publisher, runtime, manager, "legacy-publish", "b" * 64, "legacy-publish-two")

    assert rewritten.published_head != legacy_head
    current = publisher.read_snapshot("legacy-publish")
    assert current is not None
    assert current.schema_version == 3
    assert current.migrated_from_snapshot_id is None
    assert current.parent_snapshot_id is not None
    assert publisher._git_blob(legacy_head, snapshot_path) == legacy_raw  # noqa: SLF001


def test_schema_1_remote_snapshot_reads_as_pure_upcast_with_verified_stored_identity(tmp_path: Path) -> None:
    repository, remote, _initial = _repository(tmp_path)
    contract, _intent, _design = _contract("legacy-read")
    runtime, manager, _worktree = _runtime(tmp_path, repository, "legacy-read", contract)
    publisher = DeliveryStatePublisher(repository, remote=str(remote), state_branch="owlbear/delivery-state")
    first = _publish(publisher, runtime, manager, "legacy-read", "a" * 64, "legacy-read-one")
    snapshot_path = ".owlbear/delivery/state/legacy-read/snapshot.json"
    legacy_payload = json.loads(publisher._git_blob(first.published_head, snapshot_path))  # noqa: SLF001
    legacy_payload.pop("migrated_from_snapshot_id")
    legacy_payload.pop("repaired_predecessor_digest")
    legacy_payload["schema_version"] = 1
    legacy_payload["frontier"]["schema_version"] = 17
    for binding in legacy_payload["frontier"]["bindings"]:
        binding.pop("retry_count")
        binding.pop("retry_fingerprint")
    legacy_payload["snapshot_id"] = ""
    stored_id = hashlib.sha256(_canonical_payload(legacy_payload)).hexdigest()
    legacy_payload["snapshot_id"] = stored_id
    legacy_raw = _canonical_payload(legacy_payload)
    legacy_head = _commit_corrupt_snapshot(repository, first.published_head, "legacy-read", legacy_raw)
    _git(repository, "push", "origin", f"{legacy_head}:refs/heads/owlbear/delivery-state", "--force")

    inventory = publisher.read_snapshot_inventory()
    tampered = json.loads(legacy_raw)
    tampered["sequence"] += 1

    assert inventory.diagnostics == ()
    assert inventory.remote_head == legacy_head
    snapshot = inventory.snapshots[0]
    assert snapshot.schema_version == 3
    assert snapshot.migrated_from_snapshot_id == stored_id
    assert snapshot.snapshot_id != stored_id
    assert snapshot.frontier.schema_version == 18
    assert _git(remote, "cat-file", "-p", f"{legacy_head}:{snapshot_path}").encode() + b"\n" == legacy_raw
    assert _git(remote, "rev-parse", "refs/heads/owlbear/delivery-state") == legacy_head
    with pytest.raises(ValueError, match="snapshot identity is invalid"):
        parse_delivery_state_snapshot(_canonical_payload(tampered))


def test_newer_remote_snapshot_is_unsupported_never_restored_published_over_or_repaired(tmp_path: Path) -> None:
    repository, remote, _initial = _repository(tmp_path)
    change_id = "newer-state"
    contract, _intent, _design = _contract(change_id)
    runtime, manager, _worktree = _runtime(tmp_path, repository, change_id, contract)
    publisher = DeliveryStatePublisher(repository, remote=str(remote), state_branch="owlbear/delivery-state")
    package_id = "a" * 64
    first = _publish(publisher, runtime, manager, change_id, package_id, "newer-state-one")
    snapshot_path = f".owlbear/delivery/state/{change_id}/snapshot.json"
    newer_payload = json.loads(publisher._git_blob(first.published_head, snapshot_path))  # noqa: SLF001
    newer_payload["schema_version"] = 4
    newer_payload["future_field"] = {"written": "by a newer controller"}
    newer_raw = _canonical_payload(newer_payload)
    newer_head = _commit_corrupt_snapshot(repository, first.published_head, change_id, newer_raw)
    _git(repository, "push", "origin", f"{newer_head}:refs/heads/owlbear/delivery-state", "--force")
    newer_digest = hashlib.sha256(newer_raw).hexdigest()

    inventory = publisher.read_snapshot_inventory()
    diagnostic = next(item for item in inventory.diagnostics if item.change_id == change_id)
    with pytest.raises(DeliveryStateQuarantineError) as refused:
        _publish(publisher, runtime, manager, change_id, package_id, "newer-state-two")
    repairs = []
    for expected_code in ("snapshot-invalid", "snapshot-identity-invalid"):
        with pytest.raises(DeliveryStateConflictError) as repair:
            publisher.repair_quarantined_snapshot(
                change_id=change_id,
                package_id=package_id,
                coordination=manager.show(change_id),
                runtime=runtime,
                admission=_admission(runtime, manager, change_id),
                operation_id="newer-state-repair",
                captured_at=datetime(2026, 8, 23, tzinfo=UTC),
                expected_remote_head=newer_head,
                expected_snapshot_digest=newer_digest,
                expected_diagnostic_code=expected_code,  # type: ignore[arg-type]
            )
        repairs.append(str(repair.value))

    assert inventory.snapshots == ()
    assert diagnostic.code == "remote-state-version-unsupported"
    assert diagnostic.raw_digest == newer_digest
    assert "newer than this controller supports" in diagnostic.detail
    assert refused.value.diagnostic_code == "remote-state-version-unsupported"
    assert all("newer controller" in message for message in repairs)
    assert _git(remote, "rev-parse", "refs/heads/owlbear/delivery-state") == newer_head

    fresh = tmp_path / "fresh"
    _git(tmp_path, "clone", str(remote), str(fresh))
    _git(fresh, "config", "url." + str(remote) + ".insteadOf", "https://github.com/example/project.git")
    _git(fresh, "remote", "set-url", "origin", "https://github.com/example/project.git")
    config = DeliveryStartupConfig(
        schema_version=2,
        remote="origin",
        target_branch="main",
        github_repository="example/project",
        delivery_state_branch="owlbear/delivery-state",
    )
    application = load_delivery_application(config, workspace_root=fresh)
    health = application.delivery_health()

    assert [
        (item.change_id, item.code, item.reason) for item in health.diagnostics if item.source == "remote-state"
    ] == [(change_id, "remote-state-version-unsupported", DeliveryHealthReason.REMOTE_STATE_VERSION_UNSUPPORTED)]
    assert not (fresh / ".owlbear/delivery/runtime/changes" / change_id).exists()
    assert not (fresh / ".owlbear/delivery/packages" / change_id).exists()
    assert _git(remote, "rev-parse", "refs/heads/owlbear/delivery-state") == newer_head


def test_state_snapshot_accepts_terminal_completion_projection(tmp_path: Path) -> None:
    repository, _remote, initial = _repository(tmp_path)
    change_id = "state-complete"
    contract, _intent, _design = _contract(change_id)
    state_root = tmp_path / "state"
    coordinator = PortfolioCoordinator(state_root)
    manager = ChangeWorkspaceManager(repository, tmp_path / "worktrees", coordinator, "main")
    coordination = manager.ensure(change_id)
    frontier_path = state_root / "changes" / change_id / "frontier.json"
    frontier_path.parent.mkdir(parents=True, exist_ok=True)
    frontier_path.write_bytes(
        (
            json.dumps(
                DeliveryFrontier(
                    bindings=(OutcomeAuthorityBinding(outcome_id="OUT-001", plan_scope_id="SCOPE-001"),),
                ).model_dump(mode="json"),
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        ).encode()
    )
    runtime = DeliveryRuntime(state_root, contract, workspace_manager=manager)
    observed_at = datetime(2026, 8, 23, 12, tzinfo=UTC)
    observation = DeliveryObservationReceipt.create(
        DeliveryObservation(
            change_id=change_id,
            task_or_finalization_id="finalize-state-complete",
            exact_commit=initial,
            observation_kind="snapshot-test",
            procedure="terminal snapshot construction",
            result=DeliveryCommandResult(exit_status=0),
            observer_or_runner_identity="pytest",
            observed_at=observed_at,
        )
    )
    review = DeliveryReviewReceipt.create(
        DeliveryReview(
            review_mode="finalization",
            basis_digest="e" * 64,
            observation_ids=(observation.observation_id,),
            exact_commit=initial,
            author_id="snapshot-author",
            reviewer_id="snapshot-reviewer",
            evidence=("The terminal snapshot authority is internally consistent.",),
            reviewed_at=observed_at,
        )
    )
    finalization = DeliveryFinalizationReceipt.create(
        DeliveryFinalization(
            operation_id="finalize-state-complete",
            change_id=change_id,
            exact_head=initial,
            authority_digest=runtime.authority_digest,
            result_digests=("a" * 64,),
            observations=(observation,),
            review=review,
            finalized_at=observed_at,
        )
    )
    ready_values = {
        "schema_version": 1,
        "operation_id": "ready-state-complete",
        "change_id": change_id,
        "finalization_id": finalization.finalization_id,
        "repository": "example/project",
        "number": 1,
        "node_id": "PR_node_complete",
        "head_sha": initial,
        "draft": False,
        "observed_at": observed_at,
        "provider_evidence_digest": "b" * 64,
    }
    ready_candidate = PullRequestReadyReceipt.model_construct(receipt_id="0" * 64, **ready_values)
    ready = PullRequestReadyReceipt(
        receipt_id=hashlib.sha256(
            json.dumps(
                ready_candidate.model_dump(mode="json", exclude={"receipt_id"}),
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest(),
        **ready_values,
    )
    merged_at = datetime(2026, 8, 23, 12, 1, tzinfo=UTC)
    latch = DeliveryMergedPullRequestLatch(
        change_id=change_id,
        finalization_id=finalization.finalization_id,
        ready_receipt_id=ready.receipt_id,
        acceptance_observation_id="c" * 64,
        provider_evidence_digest="d" * 64,
        repository="example/project",
        number=1,
        node_id="PR_node_complete",
        base_branch="main",
        head_sha=initial,
        accepted_merge_commit="e" * 40,
        merged_at=merged_at,
    )
    completion = CompletionReceipt.create(
        CompletionEvidence(
            change_id=change_id,
            finalization_receipt_id=finalization.finalization_id,
            finalized_change_head=initial,
            repository_identity="example/project",
            pull_request_identity=CompletionPullRequestIdentity(number=1, node_id="PR_node_complete"),
            accepted_target_ref="main",
            accepted_merge_commit=latch.accepted_merge_commit,
            merged_at=merged_at,
            acceptance_observation_id=latch.acceptance_observation_id,
            review_receipt_ids=(review.review_id,),
            completed_at=datetime(2026, 8, 23, 12, 2, tzinfo=UTC),
        )
    )
    display = CompletionDisplayMetadata.create(
        change_id=change_id,
        completion_id=completion.completion_id,
        title=contract.title,
        outcome_titles=tuple(outcome.title for outcome in contract.outcomes),
        outcome_promises=tuple(outcome.promise for outcome in contract.outcomes),
    )
    completion_root = state_root / "completions" / change_id
    completion_root.mkdir(parents=True)
    (completion_root / f"{completion.completion_id}.json").write_text(
        completion.model_dump_json(),
        encoding="utf-8",
    )
    (completion_root / "display.json").write_text(display.model_dump_json(), encoding="utf-8")
    frontier = DeliveryFrontier(
        bindings=(
            OutcomeAuthorityBinding(
                outcome_id="OUT-001",
                plan_scope_id="SCOPE-001",
                stage=DeliveryStage.COMPLETED,
            ),
        ),
        published_head=initial,
        finalization=finalization,
        ready=ready,
        merged_pull_request_latch=latch,
        change_completion=DeliveryChangeCompletion(
            completion_id=completion.completion_id,
            completed_at=completion.completed_at,
        ),
    )
    frontier_path.write_bytes(
        (json.dumps(frontier.model_dump(mode="json"), sort_keys=True, separators=(",", ":")) + "\n").encode()
    )
    snapshot = DeliveryStateSnapshot.create(
        operation_id="snapshot-state-complete",
        change_id=change_id,
        package_id="f" * 64,
        coordination=coordination,
        runtime=runtime,
        admission=_admission(runtime, manager, change_id),
        sequence=1,
        parent_snapshot_id=None,
        base_head=None,
        captured_at=observed_at,
    )

    assert snapshot.frontier.change_completion is not None
    assert snapshot.completion is not None
    assert snapshot.completion.receipt.change_id == change_id
    assert snapshot.completion.receipt.completion_id == snapshot.frontier.change_completion.completion_id


def test_state_publisher_rejects_active_claims_and_stale_remote_head(tmp_path: Path) -> None:
    repository, remote, _initial = _repository(tmp_path)
    contract, _intent, _design = _contract("state-reject")
    runtime, manager, _worktree = _runtime(tmp_path, repository, "state-reject", contract)
    publisher = DeliveryStatePublisher(repository, remote=str(remote), state_branch="owlbear/delivery-state")
    frontier_path = runtime._frontier_path  # noqa: SLF001
    frontier = DeliveryFrontier.model_validate_json(runtime.frontier_bytes(), strict=True)
    active = DeliveryActiveClaim(
        attempt_id="attempt",
        claim_id="claim",
        owner_id="owner",
        process_id="process",
        started_at="2026-08-23T00:00:00Z",
        worker_role=DeliveryWorkerRole.PLANNER,
    )
    frontier_path.write_bytes(
        (
            json.dumps(
                frontier.model_copy(
                    update={
                        "bindings": (
                            frontier.bindings[0].model_copy(
                                update={"active_claim": active, "stage": DeliveryStage.PLANNING}
                            ),
                        )
                    }
                ).model_dump(mode="json"),
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        ).encode()
    )

    with pytest.raises(DeliveryStatePublicationError, match="active Outcome claim"):
        _publish(publisher, runtime, manager, "state-reject", "b" * 64, "state-reject-one")

    frontier_path.write_bytes(
        (json.dumps(frontier.model_dump(mode="json"), sort_keys=True, separators=(",", ":")) + "\n").encode()
    )
    first = _publish(publisher, runtime, manager, "state-reject", "b" * 64, "state-reject-one")

    with pytest.raises(DeliveryStateConflictError, match="branch changed"):
        _publish(
            publisher,
            runtime,
            manager,
            "state-reject",
            "c" * 64,
            "state-reject-two",
            expected_remote_head="0" * 40,
        )

    assert first.published_head != "0" * 40
    assert isinstance(publisher.read_snapshot("state-reject"), DeliveryStateSnapshot)


def test_state_publisher_rejects_unreachable_result_commit(tmp_path: Path) -> None:
    repository, remote, _initial = _repository(tmp_path)
    contract, _intent, _design = _contract("state-unreachable-result")
    runtime, manager, _worktree = _runtime(tmp_path, repository, "state-unreachable-result", contract)
    task = DeliveryTaskDefinition(
        task_id="TASK-001",
        outcome_id="OUT-001",
        plan_scope_id="SCOPE-001",
        title="Persist result",
        result="Persist the result.",
        commitment_ids=("COM-001",),
        dependency_ids=(),
        required_outputs=("Result",),
        maintained_surfaces=("serve/delivery",),
        constraints=("Use the reviewed branch.",),
        exclusions=("Do not rewrite target history.",),
        acceptance_observations=("The result is persisted.",),
        proof_boundaries=("DeliveryStatePublisher.publish",),
    )
    completed_commit = "1" * 40
    observed_at = datetime(2026, 8, 23, tzinfo=UTC)
    observation = DeliveryObservationReceipt.create(
        DeliveryObservation(
            change_id="state-unreachable-result",
            task_or_finalization_id=task.task_id,
            exact_commit=completed_commit,
            observation_kind="snapshot-test",
            procedure="unreachable result fixture",
            result=DeliveryCommandResult(exit_status=0),
            observer_or_runner_identity="pytest",
            observed_at=observed_at,
        )
    )
    review = DeliveryReviewReceipt.create(
        DeliveryReview(
            review_mode="task",
            exact_commit=completed_commit,
            author_id="result-author",
            reviewer_id="result-reviewer",
            evidence=("The result evidence is bound to the fixture commit.",),
            reviewed_at=observed_at,
        )
    )
    result = DeliveryTaskResult(
        result_id="RESULT-001",
        change_id="state-unreachable-result",
        authority_digest=runtime.authority_digest,
        task_id=task.task_id,
        task_digest=task.digest,
        completed_commit=completed_commit,
        observations=(observation,),
        review=review,
    )
    frontier_path = tmp_path / "state/changes/state-unreachable-result/frontier.json"
    frontier = DeliveryFrontier(
        bindings=(
            OutcomeAuthorityBinding(
                outcome_id="OUT-001",
                plan_scope_id="SCOPE-001",
                stage=DeliveryStage.COMPLETED,
                tasks=(task,),
                results=(result,),
            ),
        ),
    )
    frontier_path.write_bytes(_canonical_payload(frontier.model_dump(mode="json")))
    publisher = DeliveryStatePublisher(repository, remote=str(remote), state_branch="owlbear/delivery-state")

    with pytest.raises(DeliveryStatePublicationError, match="result commit absent"):
        _publish(
            publisher,
            runtime,
            manager,
            "state-unreachable-result",
            "f" * 64,
            "state-unreachable-result",
        )


@pytest.mark.parametrize("refused_retry", [False, True])
def test_loader_accepts_claim_only_local_frontier_successor(*, refused_retry: bool) -> None:
    snapshot_frontier = DeliveryFrontier(
        bindings=(
            OutcomeAuthorityBinding(outcome_id="OUT-001", plan_scope_id="SCOPE-001"),
            OutcomeAuthorityBinding(outcome_id="OUT-002", plan_scope_id="SCOPE-002"),
        )
    )
    local_frontier = snapshot_frontier.model_copy(
        update={
            "bindings": (
                snapshot_frontier.bindings[0].model_copy(
                    update={
                        "active_claim": DeliveryActiveClaim(
                            attempt_id="attempt",
                            claim_id="claim",
                            owner_id="owner",
                            process_id="process",
                            started_at="2026-08-23T00:00:00Z",
                            worker_role=DeliveryWorkerRole.PLANNER,
                        ),
                        "stage": DeliveryStage.PLANNING,
                    }
                ),
                snapshot_frontier.bindings[1],
            )
        }
    )
    if refused_retry:
        local_binding = local_frontier.bindings[0]
        diagnostic = DeliveryRetryDiagnostic(
            attempt_id="attempt",
            transition=RetryDelivery(
                action="retry",
                outcome_id="OUT-001",
                claim_id="claim",
                failure_code="planner-failed",
            ),
        )
        diagnosed = OutcomeAuthorityBinding.model_validate(
            {**local_binding.model_dump(), "retry_diagnostic": diagnostic}
        )
        local_frontier = local_frontier.model_copy(update={"bindings": (diagnosed, local_frontier.bindings[1])})

    assert _is_unpublished_claim_successor(snapshot_frontier, local_frontier)


def test_loader_accepts_claim_successor_with_published_plan_candidate() -> None:
    snapshot_frontier = DeliveryFrontier(
        bindings=(OutcomeAuthorityBinding(outcome_id="OUT-001", plan_scope_id="SCOPE-001"),)
    )
    claim = DeliveryActiveClaim(
        attempt_id="attempt",
        claim_id="claim",
        owner_id="owner",
        process_id="process",
        started_at="2026-08-23T00:00:00Z",
        worker_role=DeliveryWorkerRole.PLANNER,
    )
    candidate = DeliveryPlanCandidate.model_construct(
        candidate_id="plan",
        claim_id="claim",
        digest="a" * 64,
        tasks=(),
    )
    local_frontier = snapshot_frontier.model_copy(
        update={
            "bindings": (
                snapshot_frontier.bindings[0].model_copy(
                    update={
                        "active_claim": claim,
                        "candidate": candidate,
                        "output": candidate.output,
                    }
                ),
            )
        }
    )

    assert _is_unpublished_claim_successor(snapshot_frontier, local_frontier)


@pytest.mark.parametrize(
    "update",
    [
        {"published_head": "1" * 40},
        {"operator_moves": ("unexpected",)},
    ],
)
def test_loader_rejects_claim_successor_with_unrelated_frontier_drift(
    update: dict[str, object],
) -> None:
    snapshot_frontier = DeliveryFrontier(
        bindings=(OutcomeAuthorityBinding(outcome_id="OUT-001", plan_scope_id="SCOPE-001"),)
    )
    claim = DeliveryActiveClaim(
        attempt_id="attempt",
        claim_id="claim",
        owner_id="owner",
        process_id="process",
        started_at="2026-08-23T00:00:00Z",
        worker_role=DeliveryWorkerRole.PLANNER,
    )
    local_frontier = snapshot_frontier.model_copy(
        update={
            **update,
            "bindings": (snapshot_frontier.bindings[0].model_copy(update={"active_claim": claim}),),
        }
    )

    assert not _is_unpublished_claim_successor(snapshot_frontier, local_frontier)


def test_loader_claim_successor_never_allows_advanced_branch(tmp_path: Path) -> None:
    repository, _remote, _snapshot_head = _repository(tmp_path)
    contract, _intent, _design = _contract("claim-successor")
    runtime, manager, worktree = _runtime(tmp_path, repository, "claim-successor", contract)
    snapshot = _snapshot(runtime, manager, "claim-successor")
    claim = DeliveryActiveClaim(
        attempt_id="attempt",
        claim_id="claim",
        owner_id="owner",
        process_id="process",
        started_at="2026-08-23T00:00:00Z",
        worker_role=DeliveryWorkerRole.PLANNER,
    )
    local_frontier = snapshot.frontier.model_copy(
        update={"bindings": (snapshot.frontier.bindings[0].model_copy(update={"active_claim": claim}),)}
    )

    assert _is_unpublished_claim_successor(snapshot.frontier, local_frontier)
    _git(repository, "push", "origin", f"{snapshot.change_head}:refs/heads/{snapshot.branch}")
    _git(worktree, "commit", "--allow-empty", "-m", "advanced")
    with pytest.raises(
        DeliveryApplicationLoadError,
        match="local Change branch differs from Delivery-state snapshot",
    ):
        _require_local_snapshot_branch(snapshot, repository)


def test_state_publisher_exposes_response_unknown_and_replays_after_remote_push(tmp_path: Path) -> None:
    repository, remote, _initial = _repository(tmp_path)
    contract, _intent, _design = _contract("state-response-unknown")
    runtime, manager, _worktree = _runtime(tmp_path, repository, "state-response-unknown", contract)
    publisher = DeliveryStatePublisher(repository, remote=str(remote), state_branch="owlbear/delivery-state")

    with (
        patch.object(
            publisher,
            "_remote_head",
            side_effect=[None, DeliveryStatePublicationError("remote observation failed", retry_safe=True)],
        ),
        pytest.raises(DeliveryStateResponseUnknownError, match="could not be verified"),
    ):
        _publish(publisher, runtime, manager, "state-response-unknown", "d" * 64, "state-unknown")

    replayed = _publish(publisher, runtime, manager, "state-response-unknown", "d" * 64, "state-unknown")

    assert replayed.snapshot_id == publisher.read_snapshot("state-response-unknown").snapshot_id


def _state_branch_head(remote: Path) -> str | None:
    head = _git(remote, "rev-parse", "--verify", "--quiet", "refs/heads/owlbear/delivery-state", check=False)
    return head or None


def test_state_push_accepted_after_its_lost_response_reads_back_success_without_a_second_push(
    tmp_path: Path,
    ext_remote,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, remote, _initial = _repository(tmp_path)
    contract, _intent, _design = _contract("state-slow-accept")
    runtime, manager, _worktree = _runtime(tmp_path, repository, "state-slow-accept", contract)
    transport = ext_remote(remote)
    transport.use(repository)
    transport.slow_accepting_receive(2)
    transport.modes("receive-pack", "detach")
    monkeypatch.setattr(remote_git, "WRITE_TIMEOUT_SECONDS", 1.0)
    publisher = DeliveryStatePublisher(repository, remote="origin", state_branch="owlbear/delivery-state")

    try:
        receipt = _publish(publisher, runtime, manager, "state-slow-accept", "a" * 64, "state-slow-accept-1")
    finally:
        transport.assert_exited("receive-pack", timeout=30)

    assert receipt.expected_remote_head is None
    assert receipt.published_head == _state_branch_head(remote)
    assert len(transport.pids("receive-pack")) == 1
    assert publisher.read_snapshot("state-slow-accept").snapshot_id == receipt.snapshot_id


def test_hung_state_push_reads_back_an_unchanged_remote_as_retry_safe_without_a_second_push(
    tmp_path: Path,
    ext_remote,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, remote, _initial = _repository(tmp_path)
    contract, _intent, _design = _contract("state-hung-push")
    runtime, manager, _worktree = _runtime(tmp_path, repository, "state-hung-push", contract)
    transport = ext_remote(remote)
    transport.use(repository)
    transport.modes("receive-pack", "hang", "pass")
    monkeypatch.setattr(remote_git, "WRITE_TIMEOUT_SECONDS", 1.0)
    publisher = DeliveryStatePublisher(repository, remote="origin", state_branch="owlbear/delivery-state")

    started = time.monotonic()
    with pytest.raises(DeliveryStatePublicationError, match="push failed") as raised:
        _publish(publisher, runtime, manager, "state-hung-push", "b" * 64, "state-hung-push-1")

    assert time.monotonic() - started < 15
    assert type(raised.value) is DeliveryStatePublicationError
    assert raised.value.retry_safe
    assert len(transport.pids("receive-pack")) == 1
    transport.assert_exited("receive-pack")
    assert _state_branch_head(remote) is None

    receipt = _publish(publisher, runtime, manager, "state-hung-push", "b" * 64, "state-hung-push-1")

    assert receipt.published_head == _state_branch_head(remote)


def test_state_push_readback_failure_is_response_unknown_and_keeps_the_pending_intent(
    tmp_path: Path,
    ext_remote,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, remote, _initial = _repository(tmp_path)
    change_id = "state-readback-lost"
    contract, intent, design = _contract(change_id)
    state_root = tmp_path / "state"
    package_store = DesignPackageStore(repository / ".owlbear/delivery/packages", repository)
    package = package_store.create(change_id, intent, design)
    contract_bytes = (
        json.dumps(contract.model_dump(mode="json"), sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()
    package_store.publish_contract(change_id, package.package_id, contract_bytes, lambda *_content: None)
    package = package_store.read_verified(change_id)
    manager = ChangeWorkspaceManager(repository, tmp_path / "worktrees", PortfolioCoordinator(state_root), "main")
    coordination = manager.ensure(change_id)
    frontier_path = state_root / "changes" / change_id / "frontier.json"
    frontier_path.parent.mkdir(parents=True, exist_ok=True)
    frontier = DeliveryFrontier(bindings=(OutcomeAuthorityBinding(outcome_id="OUT-001", plan_scope_id="SCOPE-001"),))
    frontier_path.write_bytes(_canonical_payload(frontier.model_dump(mode="json")))
    runtime = DeliveryRuntime(state_root, contract, workspace_manager=manager)
    snapshot = manager.snapshot_design_package(
        change_id,
        package.package_id,
        {
            "authority.json": package.authority_bytes,
            "design.md": package.design_bytes,
            "intent.md": package.intent_bytes,
            "manifest.json": package.manifest.canonical_bytes(),
        },
        "readback-package",
    )
    _git(repository, "push", "origin", f"{snapshot.snapshot_head}:refs/heads/{coordination.branch}")
    DeliveryStatePublisher(repository, remote=str(remote), state_branch="owlbear/delivery-state").publish(
        change_id=change_id,
        package_id=package.package_id,
        coordination=manager.show(change_id),
        runtime=runtime,
        admission=_admission(runtime, manager, change_id),
        operation_id="readback-state",
        captured_at=datetime(2026, 8, 23, tzinfo=UTC),
    )
    fresh = tmp_path / "fresh"
    _git(tmp_path, "clone", str(remote), str(fresh))
    _git(fresh, "config", "url." + str(remote) + ".insteadOf", "https://github.com/example/project.git")
    _git(fresh, "remote", "set-url", "origin", "https://github.com/example/project.git")
    config = DeliveryStartupConfig(
        schema_version=2,
        remote="origin",
        target_branch="main",
        github_repository="example/project",
        delivery_state_branch="owlbear/delivery-state",
    )
    application = load_delivery_application(config, workspace_root=fresh)
    launch = application.acquire_frontier_work().launch_packages[0]
    published_before = _state_branch_head(remote)
    transport = ext_remote(remote)
    _git(fresh, "config", "--unset", "url." + str(remote) + ".insteadOf")
    _git(fresh, "config", "protocol.ext.allow", "always")
    _git(fresh, "config", "url." + transport.url + ".insteadOf", "https://github.com/example/project.git")
    transport.modes("receive-pack", "arm-hang")
    monkeypatch.setattr(remote_git, "WRITE_TIMEOUT_SECONDS", 1.0)
    monkeypatch.setattr(remote_git, "READ_TIMEOUT_SECONDS", 1.0)

    with pytest.raises(DeliveryStateResponseUnknownError, match="could not be observed") as raised:
        application.transition_delivery(
            change_id,
            BlockDelivery(
                action="block",
                outcome_id=launch.outcome_id,
                claim_id=launch.claim.claim_id,
                block_id="readback-lost-block",
                reason="The state push response and its readback are lost.",
                unblock_condition="The remote state branch can be read back.",
                expected_evidence=("Published state",),
                locators=("test_delivery_state.py",),
            ),
        )

    assert not raised.value.retry_safe
    assert len(transport.pids("receive-pack")) == 1
    transport.assert_exited("receive-pack")
    transport.assert_exited("upload-pack")
    pending_path = fresh / ".owlbear/delivery/runtime/changes" / change_id / "state-publication.json"
    assert json.loads(pending_path.read_bytes())["status"] == "pending"
    assert _state_branch_head(remote) == published_before

    (transport.root / "armed").unlink()
    transport.modes("receive-pack", "arm-hang", "pass")
    restarted = load_delivery_application(config, workspace_root=fresh)
    assert restarted.acquire_frontier_work().failures == ()
    assert restarted.show_operator_context(change_id, "OUT-001").block is not None
    assert _state_branch_head(remote) != published_before


def test_loader_bootstrap_with_a_hung_remote_reports_retryable_unavailable_state_within_bound(
    tmp_path: Path,
    ext_remote,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _repository_path, remote, _initial = _repository(tmp_path)
    fresh = tmp_path / "fresh"
    _git(tmp_path, "clone", str(remote), str(fresh))
    transport = ext_remote(remote)
    transport.modes("upload-pack", "hang")
    _git(fresh, "config", "protocol.ext.allow", "always")
    _git(fresh, "config", "url." + transport.url + ".insteadOf", "https://github.com/example/project.git")
    _git(fresh, "remote", "set-url", "origin", "https://github.com/example/project.git")
    monkeypatch.setattr(remote_git, "READ_TIMEOUT_SECONDS", 1.0)

    started = time.monotonic()
    application = load_delivery_application(
        DeliveryStartupConfig(
            schema_version=2,
            remote="origin",
            target_branch="main",
            github_repository="example/project",
            delivery_state_branch="owlbear/delivery-state",
        ),
        workspace_root=fresh,
    )

    assert time.monotonic() - started < 15
    assert len(transport.pids("upload-pack")) == 1
    transport.assert_exited("upload-pack")
    diagnostics = application.delivery_health().diagnostics
    assert any(
        item.code == "remote-state-unavailable"
        and item.retry_safe
        and item.reason is DeliveryHealthReason.REMOTE_STATE_UNAVAILABLE
        for item in diagnostics
    ), diagnostics


def test_loader_change_branch_observation_is_bounded(
    tmp_path: Path,
    ext_remote,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, remote, _initial = _repository(tmp_path)
    contract, _intent, _design = _contract("loader-hung-branch")
    runtime, manager, _worktree = _runtime(tmp_path, repository, "loader-hung-branch", contract)
    snapshot = _snapshot(runtime, manager, "loader-hung-branch")
    transport = ext_remote(remote)
    transport.use(repository)
    transport.modes("upload-pack", "hang")
    monkeypatch.setattr(remote_git, "READ_TIMEOUT_SECONDS", 1.0)

    started = time.monotonic()
    with pytest.raises(DeliveryApplicationLoadError, match="remote Change branch could not be observed"):
        _fetch_snapshot_change_head(snapshot, _startup_config(), repository)

    assert time.monotonic() - started < 10
    transport.assert_exited("upload-pack")


def test_remote_state_bootstrap_reconstructs_fresh_clone(tmp_path: Path) -> None:  # noqa: PLR0915 - assembled restart proof.
    repository, remote, _initial = _repository(tmp_path)
    change_id = "bootstrap-change"
    contract, intent, design = _contract(change_id)
    state_root = tmp_path / "state"
    package_root = repository / ".owlbear/delivery/packages"
    package_store = DesignPackageStore(package_root, repository)
    package = package_store.create(change_id, intent, design)
    contract_bytes = (
        json.dumps(contract.model_dump(mode="json"), sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()
    package_store.publish_contract(change_id, package.package_id, contract_bytes, lambda *_content: None)
    package = package_store.read_verified(change_id)
    coordinator = PortfolioCoordinator(state_root)
    manager = ChangeWorkspaceManager(repository, tmp_path / "worktrees", coordinator, "main")
    coordination = manager.ensure(change_id)
    frontier_path = state_root / "changes" / change_id / "frontier.json"
    frontier_path.parent.mkdir(parents=True, exist_ok=True)
    frontier = DeliveryFrontier(bindings=(OutcomeAuthorityBinding(outcome_id="OUT-001", plan_scope_id="SCOPE-001"),))
    frontier_path.write_bytes(
        (json.dumps(frontier.model_dump(mode="json"), sort_keys=True, separators=(",", ":")) + "\n").encode()
    )
    runtime = DeliveryRuntime(state_root, contract, workspace_manager=manager)
    snapshot = manager.snapshot_design_package(
        change_id,
        package.package_id,
        {
            "authority.json": package.authority_bytes,
            "design.md": package.design_bytes,
            "intent.md": package.intent_bytes,
            "manifest.json": package.manifest.canonical_bytes(),
        },
        "bootstrap-package",
    )
    _git(repository, "push", "origin", f"{snapshot.snapshot_head}:refs/heads/{coordination.branch}")
    publisher = DeliveryStatePublisher(repository, remote=str(remote), state_branch="owlbear/delivery-state")
    state_receipt = publisher.publish(
        change_id=change_id,
        package_id=package.package_id,
        coordination=manager.show(change_id),
        runtime=runtime,
        admission=_admission(runtime, manager, change_id),
        operation_id="bootstrap-state",
        captured_at=datetime(2026, 8, 23, tzinfo=UTC),
    )

    fresh = tmp_path / "fresh"
    _git(tmp_path, "clone", str(remote), str(fresh))
    _git(fresh, "config", "url." + str(remote) + ".insteadOf", "https://github.com/example/project.git")
    _git(fresh, "remote", "set-url", "origin", "https://github.com/example/project.git")
    config = DeliveryStartupConfig(
        schema_version=2,
        remote="origin",
        target_branch="main",
        github_repository="example/project",
        delivery_state_branch="owlbear/delivery-state",
    )
    application = load_delivery_application(config, workspace_root=fresh)

    restored = application.read_design_session(change_id)
    assert restored.package_id == package.package_id
    runtime_root = fresh / ".owlbear/delivery/runtime"
    assert (runtime_root / "changes" / change_id / "contract.json").is_file()
    assert (runtime_root / "changes" / change_id / "frontier.json").is_file()
    assert (runtime_root / "changes" / change_id / "admission.json").is_file()
    assert _git(fresh, "rev-parse", f"refs/heads/owlbear/change/{change_id}") == snapshot.snapshot_head
    assert state_receipt.published_head != "0" * 40
    assert _git(fresh / ".owlbear/delivery/worktrees" / change_id, "status", "--porcelain") == ""
    assert application.list_work_items()

    launch = application.acquire_frontier_work().launch_packages[0]
    failing_publisher = Mock()
    failing_publisher.publish.side_effect = DeliveryStatePublicationError("state unavailable", retry_safe=True)
    application._delivery_state_publisher = failing_publisher  # noqa: SLF001 - inject provider failure.
    with pytest.raises(DeliveryStatePublicationError, match="state unavailable"):
        application.transition_delivery(
            change_id,
            BlockDelivery(
                action="block",
                outcome_id=launch.outcome_id,
                claim_id=launch.claim.claim_id,
                block_id="restart-replay-block",
                reason="Remote state publication is temporarily unavailable.",
                unblock_condition="Remote state publication succeeds.",
                expected_evidence=("Published state",),
                locators=("test_delivery_state.py",),
            ),
        )

    restarted_after_failure = load_delivery_application(config, workspace_root=fresh)
    assert restarted_after_failure.delivery_health().status.value == "attention"
    replayed = restarted_after_failure.acquire_frontier_work()
    assert replayed.launch_packages == ()
    assert replayed.failures == ()
    assert restarted_after_failure.delivery_health().status.value == "healthy"
    assert restarted_after_failure.show_operator_context(change_id, "OUT-001").block is not None

    frontier_path = runtime_root / "changes" / change_id / "frontier.json"
    frontier = DeliveryFrontier.model_validate_json(frontier_path.read_bytes(), strict=True)
    frontier_path.write_bytes(
        (
            json.dumps(
                frontier.model_copy(update={"published_head": "1" * 40}).model_dump(mode="json"),
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        ).encode()
    )
    degraded = load_delivery_application(config, workspace_root=fresh)
    health = degraded.delivery_health()
    assert health.status.value == "attention"
    assert any(
        diagnostic.change_id == change_id and diagnostic.code == "remote-state-reconciliation-required"
        for diagnostic in health.diagnostics
    )
    assert degraded.list_work_items() == ()


def _tamper_builder_handoff_frontier(
    fresh: Path,
    change_id: str,
    outcome_id: str,
    task_id: str,
    scenario: str,
) -> None:
    frontier_path = fresh / ".owlbear/delivery/runtime/changes" / change_id / "frontier.json"
    frontier = DeliveryFrontier.model_validate_json(frontier_path.read_bytes(), strict=True)
    binding = next(item for item in frontier.bindings if item.outcome_id == outcome_id)
    if scenario == "forged-context":
        context = binding.builder_handoff_context
        assert context is not None
        changed_binding = binding.model_copy(
            update={"builder_handoff_context": context.model_copy(update={"metadata_fingerprint": "0" * 64})}
        )
    elif scenario == "task-drift":
        tasks = tuple(
            task.model_copy(update={"title": f"{task.title} drifted"}) if task.task_id == task_id else task
            for task in binding.tasks
        )
        changed_binding = binding.model_copy(update={"tasks": tasks})
    elif scenario == "history-drift":
        changed_binding = binding.model_copy(update={"retry_count": binding.retry_count + 1})
    else:
        pytest.fail("unsupported Builder frontier tampering scenario")
    updated = frontier.model_copy(
        update={
            "bindings": tuple(changed_binding if item.outcome_id == outcome_id else item for item in frontier.bindings)
        }
    )
    frontier_path.write_bytes(_canonical_payload(updated.model_dump(mode="json")))


def _tamper_builder_handoff_host_state(
    fresh: Path,
    change_id: str,
    branch: str,
    attempt_id: str,
    scenario: str,
) -> None:
    if scenario == "missing-receipt":
        attempt_digest = hashlib.sha256(attempt_id.encode("utf-8")).hexdigest()
        receipt_path = (
            fresh
            / ".owlbear/delivery/runtime/changes"
            / change_id
            / "builder-invocation-receipts"
            / f"{attempt_digest}.json"
        )
        receipt_path.unlink()
    elif scenario == "wrong-coordination":
        local_coordinator = PortfolioCoordinator(fresh / ".owlbear/delivery/runtime")
        coordination = local_coordinator.show(change_id)
        assert coordination.builder_handoff is not None
        bad_handoff = coordination.builder_handoff.model_copy(update={"settlement_id": "0" * 64})
        coordination_path = fresh / ".owlbear/delivery/runtime/coordination/changes" / f"{change_id}.json"
        coordination_path.write_bytes(
            _canonical_payload(coordination.model_copy(update={"builder_handoff": bad_handoff}).model_dump(mode="json"))
        )
    elif scenario == "foreign-branch":
        tree = _git(fresh, "rev-parse", "HEAD^{tree}")
        foreign_head = _git(fresh, "commit-tree", tree, "-m", "foreign Builder handoff branch")
        _git(fresh, "update-ref", f"refs/heads/{branch}", foreign_head)
    else:
        pytest.fail("unsupported Builder coordination tampering scenario")


def _workspace_git_state(repository: Path, worktree: Path) -> tuple[str, str, str, str, bytes]:
    index_path = Path(_git(worktree, "rev-parse", "--path-format=absolute", "--git-path", "index"))
    status = subprocess.run(  # noqa: S603 - fixed Git executable and argument vector.
        (
            _GIT,
            "-C",
            str(worktree),
            "--no-optional-locks",
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
        ),
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return (
        _git(repository, "for-each-ref", "--format=%(refname) %(objectname)"),
        _git(repository, "worktree", "list", "--porcelain", "-z"),
        _git(worktree, "rev-parse", "HEAD"),
        status,
        index_path.read_bytes(),
    )


class _BuilderReturnRestartFixture(NamedTuple):
    fresh: Path
    remote: Path
    config: DeliveryStartupConfig
    application: PortfolioApplication
    completed_task: DeliveryTaskDefinition
    original_task: DeliveryTaskDefinition
    historical_result: DeliveryTaskResult
    remote_state_head: str
    remote_snapshot_path: str
    remote_snapshot: bytes


def _builder_return_restart_fixture(tmp_path: Path, change_id: str) -> _BuilderReturnRestartFixture:
    repository, remote, initial = _repository(tmp_path)
    contract, intent, design = _contract(change_id)
    state_root = tmp_path / "state"
    package_store = DesignPackageStore(repository / ".owlbear/delivery/packages", repository)
    package = package_store.create(change_id, intent, design)
    package_store.publish_contract(
        change_id,
        package.package_id,
        _canonical_payload(contract.model_dump(mode="json")),
        lambda *_content: None,
    )
    package = package_store.read_verified(change_id)
    coordinator = PortfolioCoordinator(state_root)
    manager = ChangeWorkspaceManager(repository, tmp_path / "worktrees", coordinator, "main")
    coordination = manager.ensure(change_id)
    completed_task = DeliveryTaskDefinition(
        task_id="TASK-001",
        outcome_id="OUT-001",
        plan_scope_id="SCOPE-001",
        title="Persist the first result",
        result="Persist the first result.",
        commitment_ids=("COM-001",),
        dependency_ids=(),
        required_outputs=("Result",),
        maintained_surfaces=("serve/delivery",),
        constraints=("Use the reviewed branch.",),
        exclusions=("Do not rewrite target history.",),
        acceptance_observations=("The first result is persisted.",),
        proof_boundaries=("DeliveryStatePublisher.publish",),
    )
    original_task = DeliveryTaskDefinition(
        task_id="TASK-002",
        outcome_id="OUT-001",
        plan_scope_id="SCOPE-001",
        title="Implement the remaining task",
        result="Complete the remaining implementation task.",
        commitment_ids=("COM-001",),
        dependency_ids=("TASK-001",),
        required_outputs=("Updated implementation",),
        maintained_surfaces=("serve/delivery",),
        constraints=("Preserve the current worktree.",),
        exclusions=("Do not rewrite target history.",),
        acceptance_observations=("The implementation is verifiable.",),
        proof_boundaries=("DeliveryRuntime.transition",),
    )
    frontier_path = state_root / "changes" / change_id / "frontier.json"
    frontier_path.parent.mkdir(parents=True, exist_ok=True)
    frontier = DeliveryFrontier(
        bindings=(
            OutcomeAuthorityBinding(
                outcome_id="OUT-001",
                plan_scope_id="SCOPE-001",
                stage=DeliveryStage.IMPLEMENTATION,
                tasks=(completed_task, original_task),
            ),
        ),
    )
    frontier_path.write_bytes(_canonical_payload(frontier.model_dump(mode="json")))
    runtime = DeliveryRuntime(state_root, contract, workspace_manager=manager)
    observed_at = datetime(2026, 8, 23, tzinfo=UTC)
    observation = DeliveryObservationReceipt.create(
        DeliveryObservation(
            change_id=change_id,
            task_or_finalization_id=completed_task.task_id,
            exact_commit=initial,
            observation_kind="snapshot-test",
            procedure="initial completed task fixture",
            result=DeliveryCommandResult(exit_status=0),
            observer_or_runner_identity="pytest",
            observed_at=observed_at,
        )
    )
    review = DeliveryReviewReceipt.create(
        DeliveryReview(
            review_mode="task",
            exact_commit=initial,
            author_id="task-author",
            reviewer_id="task-reviewer",
            evidence=("The historical result is bound to the initial reviewed commit.",),
            reviewed_at=observed_at,
        )
    )
    historical_result = DeliveryTaskResult(
        result_id="RESULT-001",
        change_id=change_id,
        authority_digest=runtime.authority_digest,
        task_id=completed_task.task_id,
        task_digest=completed_task.digest,
        completed_commit=initial,
        observations=(observation,),
        review=review,
    )
    frontier_path.write_bytes(
        _canonical_payload(
            frontier.model_copy(
                update={"bindings": (frontier.bindings[0].model_copy(update={"results": (historical_result,)}),)}
            ).model_dump(mode="json")
        )
    )
    snapshot = manager.snapshot_design_package(
        change_id,
        package.package_id,
        {
            "authority.json": package.authority_bytes,
            "design.md": package.design_bytes,
            "intent.md": package.intent_bytes,
            "manifest.json": package.manifest.canonical_bytes(),
        },
        "bootstrap-package",
    )
    _git(repository, "push", "origin", f"{snapshot.snapshot_head}:refs/heads/{coordination.branch}")
    publisher = DeliveryStatePublisher(repository, remote=str(remote), state_branch="owlbear/delivery-state")
    publisher.publish(
        change_id=change_id,
        package_id=package.package_id,
        coordination=manager.show(change_id),
        runtime=runtime,
        admission=_admission(runtime, manager, change_id),
        operation_id="bootstrap-state",
        captured_at=observed_at,
    )

    remote_state_head = _git(remote, "rev-parse", "refs/heads/owlbear/delivery-state")
    remote_snapshot_path = f".owlbear/delivery/state/{change_id}/snapshot.json"
    remote_snapshot = subprocess.run(  # noqa: S603 - fixed local Git executable and argument vector.
        (_GIT, "-C", str(remote), "show", f"{remote_state_head}:{remote_snapshot_path}"),
        check=True,
        capture_output=True,
    ).stdout
    fresh = tmp_path / "fresh"
    _git(tmp_path, "clone", str(remote), str(fresh))
    _git(fresh, "config", "url." + str(remote) + ".insteadOf", "https://github.com/example/project.git")
    _git(fresh, "remote", "set-url", "origin", "https://github.com/example/project.git")
    config = DeliveryStartupConfig(
        schema_version=2,
        remote="origin",
        target_branch="main",
        github_repository="example/project",
        delivery_state_branch="owlbear/delivery-state",
    )
    return _BuilderReturnRestartFixture(
        fresh=fresh,
        remote=remote,
        config=config,
        application=load_delivery_application(config, workspace_root=fresh),
        completed_task=completed_task,
        original_task=original_task,
        historical_result=historical_result,
        remote_state_head=remote_state_head,
        remote_snapshot_path=remote_snapshot_path,
        remote_snapshot=remote_snapshot,
    )


@pytest.mark.parametrize(
    ("promotion_fault", "return_target"),
    [
        (None, DeliveryStage.PLANNING),
        ("missing-receipt", DeliveryStage.PLANNING),
        ("forged-receipt", DeliveryStage.PLANNING),
        ("dropped-task", DeliveryStage.PLANNING),
        ("dropped-history", DeliveryStage.PLANNING),
        ("original-scope-drift", DeliveryStage.PLANNING),
        (None, DeliveryStage.DESIGN),
    ],
)
def test_builder_return_handoff_survives_default_loader_restart(  # noqa: PLR0915
    tmp_path: Path,
    promotion_fault: str | None,
    return_target: DeliveryStage,
) -> None:
    change_id = "return-planning-promotion"
    restart = _builder_return_restart_fixture(tmp_path, change_id)
    fresh, config, application = restart.fresh, restart.config, restart.application
    remote, remote_state_head = restart.remote, restart.remote_state_head
    remote_snapshot_path, remote_snapshot = restart.remote_snapshot_path, restart.remote_snapshot
    completed_task, original_task = restart.completed_task, restart.original_task
    historical_result = restart.historical_result
    builder_launch = application.acquire_frontier_work().launch_packages[0]
    assert builder_launch.claim.worker_role is DeliveryWorkerRole.BUILDER
    assert builder_launch.task_id == original_task.task_id

    staged_product = builder_launch.worktree_path / "product.txt"
    staged_product.write_text("staged return-planning work\n", encoding="utf-8")
    _git(builder_launch.worktree_path, "add", staged_product.name)
    staged_product.write_text("staged return-planning work\nplus an unstaged edit\n", encoding="utf-8")
    staged_file = builder_launch.worktree_path / "staged-return-planning.txt"
    staged_file.write_text("staged task bytes\n", encoding="utf-8")
    _git(builder_launch.worktree_path, "add", staged_file.name)
    untracked_file = builder_launch.worktree_path / "untracked-return-planning.txt"
    untracked_file.write_text("untracked task bytes\n", encoding="utf-8")
    worktree_state = _workspace_git_state(fresh, builder_launch.worktree_path)
    task_bytes = {path.name: path.read_bytes() for path in (staged_product, staged_file, untracked_file)}
    return_request = ReturnDelivery(
        action="return",
        outcome_id=builder_launch.outcome_id,
        claim_id=builder_launch.claim.claim_id,
        target=return_target,
        reason=(
            "The admitted Design lacks the premise for the retained task."
            if return_target is DeliveryStage.DESIGN
            else "Clarify the remaining implementation task."
        ),
        locators=("design.md",) if return_target is DeliveryStage.DESIGN else (original_task.task_id,),
        preserved_commit=builder_launch.last_reviewed_commit,
        attempt_id=builder_launch.claim.attempt_id,
    )
    settled = application.settle_worker_invocation(
        DeliveryBuilderInvocationSettlement(
            change_id=change_id,
            outcome_id=builder_launch.outcome_id,
            claim_id=builder_launch.claim.claim_id,
            attempt_id=builder_launch.claim.attempt_id,
            task_id=builder_launch.task_id,
            expected_last_reviewed_commit=builder_launch.last_reviewed_commit,
            disposition="normal-return",
            request=return_request,
        ),
        host_id=builder_launch.claim.owner_id,
        session_id=builder_launch.claim.process_id,
    )
    assert settled.stage == return_target
    assert settled.tasks == (completed_task, original_task)
    assert settled.results == (historical_result,)
    assert settled.builder_handoff_context is not None
    assert settled.builder_handoff_context.route == (
        "same-outcome-design" if return_target is DeliveryStage.DESIGN else "same-outcome-planner"
    )
    coordination_path = fresh / ".owlbear/delivery/runtime/coordination/changes" / f"{change_id}.json"
    retained_handoff_custody = coordination_path.read_bytes()

    if return_target is DeliveryStage.DESIGN:
        assert _workspace_git_state(fresh, builder_launch.worktree_path) == worktree_state
        assert {path.name: path.read_bytes() for path in (staged_product, staged_file, untracked_file)} == task_bytes
        design_application = load_delivery_application(config, workspace_root=fresh)
        design_health = design_application.delivery_health()
        assert design_health.status.value == "healthy", design_health.diagnostics
        design_view = design_application.show_work_item_view(change_id, "outcome:OUT-001")
        assert design_view.return_context == settled.return_context
        design_readiness = design_view.readiness
        assert design_readiness is not None
        assert design_readiness.status == "blocked"
        assert design_readiness.reason_code == "design-attention"
        assert design_readiness.next_actor.value == "you"
        assert not design_readiness.executable
        assert design_readiness.prompt is not None
        assert "The admitted Design lacks the premise for the retained task." in design_readiness.prompt
        assert "design.md" in design_readiness.prompt
        assert design_application.acquire_frontier_work().launch_packages == ()
        design_runtime = design_application._runtimes[change_id]  # noqa: SLF001
        assert design_runtime.active_claims() == ()
        assert design_runtime.claimable_outcome_ids() == ()
        design_writer = design_application._coordinator.show(change_id).writer  # noqa: SLF001
        assert design_writer is not None
        assert design_writer.kind == "handoff"
        assert coordination_path.read_bytes() == retained_handoff_custody
        return

    planner_application = load_delivery_application(config, workspace_root=fresh)
    health = planner_application.delivery_health()
    assert health.status.value == "healthy", health.diagnostics
    planner_readiness = planner_application.show_work_item_view(change_id, "outcome:OUT-001").readiness
    assert planner_readiness is not None
    assert planner_readiness.status == "ready"
    assert planner_readiness.next_actor.value == "agent"
    assert planner_readiness.executable is True
    assert planner_readiness.operation.value == "start-orchestration"
    assert planner_readiness.action is not None
    assert planner_readiness.action.kind.value == "start-orchestration"
    planner_launch = planner_application.acquire_frontier_work().launch_packages[0]
    assert planner_launch.claim.worker_role is DeliveryWorkerRole.PLANNER
    assert planner_launch.task_id is None
    plan_context = planner_application.show_plan_context(
        change_id,
        planner_launch.outcome_id,
        planner_launch.claim.attempt_id,
        planner_launch.claim.claim_id,
    )
    assert plan_context.launch.builder_handoff_context == settled.builder_handoff_context

    revised_task = original_task.model_copy(
        update={
            "title": "Implement the clarified remaining task",
            "result": "Complete the clarified implementation task.",
        }
    )
    follow_up_task = DeliveryTaskDefinition(
        task_id="TASK-003",
        outcome_id="OUT-001",
        plan_scope_id="SCOPE-001",
        title="Verify the completed implementation",
        result="Verify the completed implementation.",
        commitment_ids=("COM-001",),
        dependency_ids=("TASK-002",),
        required_outputs=("Verification evidence",),
        maintained_surfaces=("serve/delivery",),
        constraints=("Use the reviewed task result.",),
        exclusions=("Do not rewrite target history.",),
        acceptance_observations=("The implementation evidence is recorded.",),
        proof_boundaries=("DeliveryRuntime.transition",),
    )
    plan_candidate = planner_application.publish_delivery_plan(
        change_id,
        PublishDeliveryPlan(
            outcome_id=planner_launch.outcome_id,
            claim_id=planner_launch.claim.claim_id,
            tasks=(completed_task, revised_task, follow_up_task),
        ),
    )
    candidate_application = load_delivery_application(config, workspace_root=fresh)
    candidate_health = candidate_application.delivery_health()
    assert candidate_health.status.value == "healthy", candidate_health.diagnostics
    assert coordination_path.read_bytes() == retained_handoff_custody
    candidate_context = candidate_application.show_plan_context(
        change_id,
        planner_launch.outcome_id,
        planner_launch.claim.attempt_id,
        planner_launch.claim.claim_id,
    )
    assert candidate_context.launch.claim.claim_id == planner_launch.claim.claim_id
    assert candidate_application._runtimes[change_id].show_binding("OUT-001").candidate == plan_candidate  # noqa: SLF001
    advanced = candidate_application.transition_delivery(
        change_id,
        AdvanceDelivery(
            action="advance",
            outcome_id=planner_launch.outcome_id,
            claim_id=planner_launch.claim.claim_id,
            output=plan_candidate.output,
        ),
    )
    assert advanced.stage == DeliveryStage.IMPLEMENTATION
    assert advanced.tasks == plan_candidate.tasks
    assert advanced.tasks[0] == completed_task
    assert advanced.results == (historical_result,)
    assert advanced.builder_handoff_context is not None
    assert advanced.builder_handoff_context.route == "same-task"
    assert advanced.builder_handoff_context.original_task_id == original_task.task_id
    assert advanced.tasks[1].task_id == original_task.task_id
    assert advanced.tasks[1].plan_scope_id == original_task.plan_scope_id
    assert advanced.tasks[1].commitment_ids == original_task.commitment_ids
    assert coordination_path.read_bytes() == retained_handoff_custody

    promotion_path = (
        fresh
        / ".owlbear/delivery/runtime/changes"
        / change_id
        / "builder-plan-promotion-receipts"
        / f"{settled.builder_handoff_context.settlement_id}.json"
    )
    promotion_bytes = promotion_path.read_bytes()
    promotion = _DeliveryBuilderPlanPromotionReceipt.model_validate_json(promotion_bytes, strict=True)
    assert promotion.settlement_id == settled.builder_handoff_context.settlement_id
    assert promotion.planner_claim.claim_id == planner_launch.claim.claim_id
    assert promotion.planner_claim.attempt_id == planner_launch.claim.attempt_id
    assert promotion.candidate == plan_candidate
    assert promotion.source_binding.tasks == settled.tasks
    assert promotion.source_binding.results == settled.results
    assert promotion.result_binding == advanced

    builder_ledger = application._runtimes[change_id].retry_ledger()  # noqa: SLF001
    builder_ledger.reconcile_owner_results()
    builder_episode = builder_ledger.episode_for_attempt(builder_launch.claim.attempt_id)
    assert builder_episode is not None
    assert builder_episode.total_attempts == 1
    assert builder_episode.reset_count == 0
    builder_retry_budget = (builder_episode.episode_id, builder_episode.total_attempts, builder_episode.reset_count)

    assert _git(remote, "rev-parse", "refs/heads/owlbear/delivery-state") == remote_state_head
    assert (
        subprocess.run(  # noqa: S603 - fixed local Git executable and argument vector.
            (_GIT, "-C", str(remote), "show", f"{remote_state_head}:{remote_snapshot_path}"),
            check=True,
            capture_output=True,
        ).stdout
        == remote_snapshot
    )

    frontier_path = fresh / ".owlbear/delivery/runtime/changes" / change_id / "frontier.json"
    if promotion_fault == "missing-receipt":
        promotion_path.unlink()
    elif promotion_fault == "forged-receipt":
        payload = json.loads(promotion_bytes)
        payload["promotion_id"] = "0" * 64
        promotion_path.write_bytes(_canonical_payload(payload))
    elif promotion_fault in {"dropped-task", "dropped-history", "original-scope-drift"}:
        local_frontier = DeliveryFrontier.model_validate_json(frontier_path.read_bytes(), strict=True)
        local_binding = local_frontier.bindings[0]
        if promotion_fault == "dropped-task":
            changed_binding = local_binding.model_copy(update={"tasks": local_binding.tasks[:-1]})
        elif promotion_fault == "dropped-history":
            changed_binding = local_binding.model_copy(update={"results": ()})
        else:
            changed_binding = local_binding.model_copy(
                update={
                    "tasks": tuple(
                        task.model_copy(update={"plan_scope_id": "SCOPE-002"})
                        if task.task_id == original_task.task_id
                        else task
                        for task in local_binding.tasks
                    )
                }
            )
        frontier_path.write_bytes(
            _canonical_payload(
                local_frontier.model_copy(update={"bindings": (changed_binding,)}).model_dump(mode="json")
            )
        )

    frontier_bytes_before_reload = frontier_path.read_bytes()
    coordination_bytes_before_reload = coordination_path.read_bytes()
    worktree_before_reload = _workspace_git_state(fresh, builder_launch.worktree_path)
    promotion_bytes_before_reload = promotion_path.read_bytes() if promotion_path.exists() else None
    resumed_application = load_delivery_application(config, workspace_root=fresh)
    resumed_health = resumed_application.delivery_health()
    if promotion_fault is not None:
        assert resumed_health.status.value == "attention"
        assert any(
            diagnostic.code == "remote-state-reconciliation-required" for diagnostic in resumed_health.diagnostics
        )
        assert frontier_path.read_bytes() == frontier_bytes_before_reload
        assert coordination_path.read_bytes() == coordination_bytes_before_reload
        assert _workspace_git_state(fresh, builder_launch.worktree_path) == worktree_before_reload
        assert _git(remote, "rev-parse", "refs/heads/owlbear/delivery-state") == remote_state_head
        assert (
            subprocess.run(  # noqa: S603 - fixed local Git executable and argument vector.
                (_GIT, "-C", str(remote), "show", f"{remote_state_head}:{remote_snapshot_path}"),
                check=True,
                capture_output=True,
            ).stdout
            == remote_snapshot
        )
        if promotion_bytes_before_reload is None:
            assert not promotion_path.exists()
        else:
            assert promotion_path.read_bytes() == promotion_bytes_before_reload
        return
    assert resumed_health.status.value == "healthy", resumed_health.diagnostics
    promoted_readiness = resumed_application.show_work_item_view(change_id, "outcome:OUT-001").readiness
    assert promoted_readiness is not None
    assert promoted_readiness.status == "ready"
    assert promoted_readiness.next_actor.value == "agent"
    assert promoted_readiness.executable is True
    assert promoted_readiness.operation.value == "start-orchestration"
    resumed_ledger = resumed_application._runtimes[change_id].retry_ledger()  # noqa: SLF001
    resumed_ledger.reconcile_owner_results()
    resumed_episode = resumed_ledger.episode_for_attempt(builder_launch.claim.attempt_id)
    assert resumed_episode is not None
    assert (
        resumed_episode.episode_id,
        resumed_episode.total_attempts,
        resumed_episode.reset_count,
    ) == builder_retry_budget
    builder_resume = resumed_application.acquire_frontier_work().launch_packages[0]
    assert builder_resume.claim.worker_role is DeliveryWorkerRole.BUILDER
    assert builder_resume.task_id == original_task.task_id
    assert builder_resume.builder_handoff_context == advanced.builder_handoff_context
    assert _workspace_git_state(fresh, builder_resume.worktree_path) == worktree_state
    assert {path.name: path.read_bytes() for path in (staged_product, staged_file, untracked_file)} == task_bytes
    active_builder_application = load_delivery_application(config, workspace_root=fresh)
    active_builder_health = active_builder_application.delivery_health()
    assert active_builder_health.status.value == "healthy", active_builder_health.diagnostics
    active_build_context = active_builder_application.show_build_context(
        change_id,
        builder_resume.outcome_id,
        builder_resume.claim.attempt_id,
        builder_resume.claim.claim_id,
    )
    assert active_build_context.task == revised_task
    assert active_build_context.launch.builder_handoff_context == advanced.builder_handoff_context
    acquired_ledger = resumed_application._runtimes[change_id].retry_ledger()  # noqa: SLF001
    acquired_ledger.reconcile_owner_results()
    acquired_episode = acquired_ledger.episode_for_attempt(builder_launch.claim.attempt_id)
    assert acquired_episode is not None
    assert acquired_episode.episode_id == builder_retry_budget[0]
    assert acquired_episode.total_attempts == builder_retry_budget[1] + 1
    assert acquired_episode.reset_count == builder_retry_budget[2] == 0


def _settle_default_loader_planning_return(
    restart: _BuilderReturnRestartFixture,
    change_id: str,
) -> OutcomeAuthorityBinding:
    builder_launch = restart.application.acquire_frontier_work().launch_packages[0]
    assert builder_launch.claim.worker_role is DeliveryWorkerRole.BUILDER
    settled = restart.application.settle_worker_invocation(
        DeliveryBuilderInvocationSettlement(
            change_id=change_id,
            outcome_id=builder_launch.outcome_id,
            claim_id=builder_launch.claim.claim_id,
            attempt_id=builder_launch.claim.attempt_id,
            task_id=builder_launch.task_id,
            expected_last_reviewed_commit=builder_launch.last_reviewed_commit,
            disposition="normal-return",
            request=ReturnDelivery(
                action="return",
                outcome_id=builder_launch.outcome_id,
                claim_id=builder_launch.claim.claim_id,
                target=DeliveryStage.PLANNING,
                reason="Clarify the remaining implementation task.",
                locators=(restart.original_task.task_id,),
                preserved_commit=builder_launch.last_reviewed_commit,
                attempt_id=builder_launch.claim.attempt_id,
            ),
        ),
        host_id=builder_launch.claim.owner_id,
        session_id=builder_launch.claim.process_id,
    )
    assert settled.builder_handoff_context is not None
    assert settled.builder_handoff_context.route == "same-outcome-planner"
    return settled


def _planner_return_pause(
    outcome_id: str,
    claim_id: str,
    *,
    request_bearing: bool,
    ordinal: int = 1,
) -> BlockDelivery:
    suffix = "" if ordinal == 1 else f"-{ordinal}"
    request = (
        DeliveryRequest(
            request_id=f"planner-return-request{suffix}",
            kind=DeliveryRequestKind.DECISION,
            outcome_id=outcome_id,
            summary="Choose the boundary for the returned task.",
            options=(
                DeliveryRequestOption(option_id="narrow", label="Narrow the task"),
                DeliveryRequestOption(option_id="split", label="Split the task"),
            ),
        )
        if request_bearing
        else None
    )
    return BlockDelivery(
        action="block",
        outcome_id=outcome_id,
        claim_id=claim_id,
        block_id=f"planner-return-block{suffix}",
        reason="The returned task boundary needs a decision.",
        unblock_condition="The boundary decision is recorded.",
        expected_evidence=("Boundary decision",),
        locators=("TASK-002",),
        request=request,
    )


def _answer_planner_return_pause(
    application: PortfolioApplication,
    change_id: str,
    pause: BlockDelivery,
    option_id: str = "narrow",
) -> None:
    if pause.request is not None:
        application.resolve_request(
            change_id,
            pause.request.request_id,
            DeliveryRequestResolution(selected_option_id=option_id, provenance="user-confirmed"),
        )
    else:
        application.clear_block(
            change_id,
            pause.outcome_id,
            pause.block_id,
            "Boundary verified by operator.",
            ("TASK-002",),
        )


def _healthy_restart(restart: _BuilderReturnRestartFixture) -> PortfolioApplication:
    application = load_delivery_application(restart.config, workspace_root=restart.fresh)
    health = application.delivery_health()
    assert health.status.value == "healthy", health.diagnostics
    return application


# N09-A2 §3.3: a Pause request and an unfinished direct marker survive the real configured loader.
def test_pause_request_and_unfinished_direct_marker_survive_default_loader_restart(tmp_path: Path) -> None:
    change_id = "pause-restart"
    restart = _builder_return_restart_fixture(tmp_path, change_id)
    application = restart.application
    launch = application.acquire_frontier_work().launch_packages[0]
    direct = ChangeDirectOperation(
        change_id=change_id, kind="mark-ready", operation_id="ready-before-restart", request_digest="a" * 64
    )
    assert application._coordinator.start_direct_operation(direct) is True  # noqa: SLF001
    runtime = application._runtimes[change_id]  # noqa: SLF001
    requested = application.set_change_intent(
        DeliveryChangeIntent(
            change_id=change_id,
            kind=DeliveryChangeIntentKind.DEFER,
            expected_frontier_digest=hashlib.sha256(runtime.frontier_bytes()).hexdigest(),
            reason="Hold for review",
        )
    )
    assert isinstance(requested.receipt, ChangePauseRequest)
    close_delivery_application(application)

    restarted = load_configured_delivery_application(restart.fresh, lambda _path: restart.config)
    coordinator = restarted._coordinator  # noqa: SLF001

    assert restarted.delivery_health().status.value == "healthy"
    assert coordinator.pause_request(change_id) == requested.receipt
    assert coordinator.direct_operation_state(direct) == "started"
    assert restarted.get_change(change_id).pause_requested is True
    assert restarted.acquire_frontier_work().launch_packages == ()
    restarted_runtime = restarted._runtimes[change_id]  # noqa: SLF001
    assert restarted_runtime.show_binding(launch.outcome_id).active_claim == launch.claim
    assert restarted_runtime.change_deferral() is None
    with pytest.raises(ChangePauseRequestedError):
        coordinator.start_direct_operation(direct.model_copy(update={"operation_id": "ready-after-restart"}))
    close_delivery_application(restarted)


def _acquire_planner_after_pause(application: PortfolioApplication, minutes: int) -> DeliveryLaunchPackage:
    # A Planner block ends its attempt with a retry backoff before reacquisition.
    eligible_at = (datetime.now(UTC) + timedelta(minutes=minutes)).isoformat()
    application._clock = lambda: eligible_at  # noqa: SLF001
    launch = application.acquire_frontier_work().launch_packages[0]
    assert launch.claim.worker_role is DeliveryWorkerRole.PLANNER
    return launch


def _pause_second_planner_return(
    restart: _BuilderReturnRestartFixture,
    change_id: str,
    *,
    first_request_bearing: bool,
    second_request_bearing: bool,
) -> tuple[BlockDelivery, BlockDelivery, OutcomeAuthorityBinding]:
    application = _healthy_restart(restart)
    first_launch = application.acquire_frontier_work().launch_packages[0]
    first_pause = _planner_return_pause(
        first_launch.outcome_id,
        first_launch.claim.claim_id,
        request_bearing=first_request_bearing,
    )
    application.transition_delivery(change_id, first_pause)
    _answer_planner_return_pause(_healthy_restart(restart), change_id, first_pause)
    second_launch = _acquire_planner_after_pause(_healthy_restart(restart), minutes=5)
    second_pause = _planner_return_pause(
        second_launch.outcome_id,
        second_launch.claim.claim_id,
        request_bearing=second_request_bearing,
        ordinal=2,
    )
    second_blocked = _healthy_restart(restart).transition_delivery(change_id, second_pause)
    return first_pause, second_pause, second_blocked


@pytest.mark.parametrize("request_bearing", [True, False])
def test_planner_pause_on_builder_planning_return_survives_default_loader_restart(
    tmp_path: Path,
    *,
    request_bearing: bool,
) -> None:
    change_id = "return-planning-pause"
    restart = _builder_return_restart_fixture(tmp_path, change_id)
    settled = _settle_default_loader_planning_return(restart, change_id)
    planner_application = _healthy_restart(restart)
    planner_launch = planner_application.acquire_frontier_work().launch_packages[0]
    assert planner_launch.claim.worker_role is DeliveryWorkerRole.PLANNER
    pause = _planner_return_pause(
        planner_launch.outcome_id,
        planner_launch.claim.claim_id,
        request_bearing=request_bearing,
    )
    blocked = planner_application.transition_delivery(change_id, pause)
    assert blocked.block is not None
    assert blocked.return_context is None

    blocked_application = _healthy_restart(restart)
    assert blocked_application.show_operator_context(change_id, "OUT-001").block == blocked.block
    assert blocked_application.acquire_frontier_work().launch_packages == ()
    _answer_planner_return_pause(blocked_application, change_id, pause)

    answered_application = _healthy_restart(restart)
    answered = answered_application._runtimes[change_id].show_binding("OUT-001")  # noqa: SLF001
    assert answered.block is not None
    assert answered.block.resolved
    assert answered.return_context == settled.return_context
    assert answered.builder_handoff_context == settled.builder_handoff_context
    # A requestless block ends the Planner attempt with a short retry backoff.
    eligible_at = (datetime.now(UTC) + timedelta(minutes=1)).isoformat()
    answered_application._clock = lambda: eligible_at  # noqa: SLF001
    replan_launch = answered_application.acquire_frontier_work().launch_packages[0]
    assert replan_launch.claim.worker_role is DeliveryWorkerRole.PLANNER
    assert replan_launch.claim.claim_id != planner_launch.claim.claim_id

    claimed_application = _healthy_restart(restart)
    candidate = claimed_application.publish_delivery_plan(
        change_id,
        PublishDeliveryPlan(
            outcome_id=replan_launch.outcome_id,
            claim_id=replan_launch.claim.claim_id,
            tasks=settled.tasks,
        ),
    )
    candidate_application = _healthy_restart(restart)
    advanced = candidate_application.transition_delivery(
        change_id,
        AdvanceDelivery(
            action="advance",
            outcome_id=replan_launch.outcome_id,
            claim_id=replan_launch.claim.claim_id,
            output=candidate.output,
        ),
    )
    assert advanced.stage == DeliveryStage.IMPLEMENTATION
    assert advanced.builder_handoff_context is not None
    assert advanced.builder_handoff_context.route == "same-task"

    promoted_application = _healthy_restart(restart)
    builder_resume = promoted_application.acquire_frontier_work().launch_packages[0]
    assert builder_resume.claim.worker_role is DeliveryWorkerRole.BUILDER
    assert builder_resume.task_id == restart.original_task.task_id


@pytest.mark.parametrize(
    ("scenario", "expected_detail"),
    [
        ("missing-pause-receipt", "local Planner pause differs from its exact Planning pause receipt"),
        ("drifted-request", "local Delivery frontier differs from its exact Builder return promotion"),
        ("early-return-context", "local Delivery frontier differs from its exact Builder return promotion"),
        ("forged-return-context", "local Delivery frontier differs from its exact Builder return promotion"),
        ("unlocated-requestless-clear", "local Planner requestless clearance lacks operator evidence"),
        ("promotion-without-pause-receipt", "local Planner pause differs from its exact Planning pause receipt"),
    ],
)
def test_default_loader_rejects_unrecorded_planner_pause_on_builder_planning_return(
    tmp_path: Path,
    scenario: str,
    expected_detail: str,
) -> None:
    change_id = "return-planning-pause-forgery"
    restart = _builder_return_restart_fixture(tmp_path, change_id)
    settled = _settle_default_loader_planning_return(restart, change_id)
    application = restart.application
    launch = application.acquire_frontier_work().launch_packages[0]
    pause = _planner_return_pause(
        launch.outcome_id,
        launch.claim.claim_id,
        request_bearing=scenario not in {"early-return-context", "unlocated-requestless-clear"},
    )
    application.transition_delivery(change_id, pause)
    if scenario in {"forged-return-context", "promotion-without-pause-receipt"}:
        _answer_planner_return_pause(application, change_id, pause)
    if scenario == "promotion-without-pause-receipt":
        replan = application.acquire_frontier_work().launch_packages[0]
        candidate = application.publish_delivery_plan(
            change_id,
            PublishDeliveryPlan(outcome_id=replan.outcome_id, claim_id=replan.claim.claim_id, tasks=settled.tasks),
        )
        application.transition_delivery(
            change_id,
            AdvanceDelivery(
                action="advance",
                outcome_id=replan.outcome_id,
                claim_id=replan.claim.claim_id,
                output=candidate.output,
            ),
        )

    change_root = restart.fresh / ".owlbear/delivery/runtime/changes" / change_id
    frontier_path = change_root / "frontier.json"
    if scenario in {"missing-pause-receipt", "promotion-without-pause-receipt"}:
        receipts = tuple((change_root / "planning-pause-receipts" / "OUT-001").glob("*.json"))
        assert len(receipts) == 1
        receipts[0].unlink()
    else:
        frontier = DeliveryFrontier.model_validate_json(frontier_path.read_bytes(), strict=True)
        binding = frontier.bindings[0]
        assert binding.block is not None
        assert settled.return_context is not None
        if scenario == "drifted-request":
            changed = binding.model_copy(
                update={
                    "requests": (
                        *binding.requests[:-1],
                        binding.requests[-1].model_copy(update={"summary": "An unrecorded Planner question."}),
                    )
                }
            )
        elif scenario == "early-return-context":
            changed = binding.model_copy(update={"return_context": settled.return_context})
        elif scenario == "forged-return-context":
            assert binding.return_context == settled.return_context
            changed = binding.model_copy(
                update={"return_context": settled.return_context.model_copy(update={"reason": "Forged context."})}
            )
        else:
            changed = binding.model_copy(
                update={
                    "block": binding.block.model_copy(update={"resolution_note": "Unlocated operator note."}),
                    "return_context": settled.return_context,
                }
            )
        frontier_path.write_bytes(
            _canonical_payload(frontier.model_copy(update={"bindings": (changed,)}).model_dump(mode="json"))
        )

    frontier_before = frontier_path.read_bytes()
    rejected = load_delivery_application(restart.config, workspace_root=restart.fresh)
    health = rejected.delivery_health()
    assert health.status.value == "attention"
    assert any(
        diagnostic.change_id == change_id
        and diagnostic.code == "remote-state-reconciliation-required"
        and expected_detail in diagnostic.detail
        for diagnostic in health.diagnostics
    ), health.diagnostics
    assert frontier_path.read_bytes() == frontier_before


@pytest.mark.parametrize(
    ("first_request_bearing", "second_request_bearing"),
    [(True, True), (True, False), (False, True)],
)
def test_repeated_planner_pauses_on_builder_planning_return_survive_default_loader_restart(
    tmp_path: Path,
    *,
    first_request_bearing: bool,
    second_request_bearing: bool,
) -> None:
    change_id = "return-planning-repeated-pause"
    restart = _builder_return_restart_fixture(tmp_path, change_id)
    settled = _settle_default_loader_planning_return(restart, change_id)
    first_pause, second_pause, second_blocked = _pause_second_planner_return(
        restart,
        change_id,
        first_request_bearing=first_request_bearing,
        second_request_bearing=second_request_bearing,
    )
    planner_requests = tuple(pause.request for pause in (first_pause, second_pause) if pause.request is not None)
    assert second_blocked.return_context is None
    assert tuple(item.request_id for item in second_blocked.requests[len(settled.requests) :]) == tuple(
        item.request_id for item in planner_requests
    )
    if first_pause.request is not None:
        assert second_blocked.requests[len(settled.requests)].resolution is not None

    blocked_application = _healthy_restart(restart)
    assert blocked_application.show_operator_context(change_id, "OUT-001").block == second_blocked.block
    assert blocked_application.acquire_frontier_work().launch_packages == ()
    _answer_planner_return_pause(blocked_application, change_id, second_pause, option_id="split")

    answered_application = _healthy_restart(restart)
    answered = answered_application._runtimes[change_id].show_binding("OUT-001")  # noqa: SLF001
    assert answered.block is not None
    assert answered.block.resolved
    assert answered.block.block_id == second_pause.block_id
    assert answered.return_context == settled.return_context
    assert answered.requests[: len(settled.requests)] == settled.requests
    assert tuple(item.request_id for item in answered.requests[len(settled.requests) :]) == tuple(
        item.request_id for item in planner_requests
    )
    assert all(item.resolution is not None for item in answered.requests[len(settled.requests) :])
    replan_launch = _acquire_planner_after_pause(answered_application, minutes=30)

    claimed_application = _healthy_restart(restart)
    candidate = claimed_application.publish_delivery_plan(
        change_id,
        PublishDeliveryPlan(
            outcome_id=replan_launch.outcome_id,
            claim_id=replan_launch.claim.claim_id,
            tasks=settled.tasks,
        ),
    )
    advanced = _healthy_restart(restart).transition_delivery(
        change_id,
        AdvanceDelivery(
            action="advance",
            outcome_id=replan_launch.outcome_id,
            claim_id=replan_launch.claim.claim_id,
            output=candidate.output,
        ),
    )
    assert advanced.stage == DeliveryStage.IMPLEMENTATION
    assert advanced.builder_handoff_context is not None
    assert advanced.builder_handoff_context.route == "same-task"

    builder_resume = _healthy_restart(restart).acquire_frontier_work().launch_packages[0]
    assert builder_resume.claim.worker_role is DeliveryWorkerRole.BUILDER
    assert builder_resume.task_id == restart.original_task.task_id


def _change_intent(
    application: PortfolioApplication, change_id: str, kind: DeliveryChangeIntentKind, reason: str | None = None
) -> object:
    runtime = application._runtimes[change_id]  # noqa: SLF001
    return application.set_change_intent(
        DeliveryChangeIntent(
            change_id=change_id,
            kind=kind,
            expected_frontier_digest=hashlib.sha256(runtime.frontier_bytes()).hexdigest(),
            reason=reason,
        )
    ).receipt


def _assert_change_intent_restarts(
    restart: _BuilderReturnRestartFixture,
    change_id: str,
    *,
    abandon: bool,
) -> PortfolioApplication:
    application = _healthy_restart(restart)
    expected = application._runtimes[change_id].show_binding("OUT-001")  # noqa: SLF001
    _change_intent(application, change_id, DeliveryChangeIntentKind.DEFER, "Wait while the Planner pause is reviewed.")
    deferred_application = _healthy_restart(restart)
    assert deferred_application.acquire_frontier_work().launch_packages == ()
    _change_intent(deferred_application, change_id, DeliveryChangeIntentKind.RESUME)
    resumed_application = _healthy_restart(restart)
    assert resumed_application._runtimes[change_id].show_binding("OUT-001") == expected  # noqa: SLF001
    if not abandon:
        return resumed_application
    resumed_application.abandon_change(change_id, "The user abandoned this paused Planning return.")
    abandoned_application = _healthy_restart(restart)
    assert abandoned_application.show_completed_change(change_id).record_kind == "abandoned-change"
    assert abandoned_application.acquire_frontier_work().launch_packages == ()
    assert abandoned_application._runtimes[change_id].show_binding("OUT-001") == expected  # noqa: SLF001
    return abandoned_application


@pytest.mark.parametrize(
    ("scenario", "request_bearing"),
    [
        ("paused", True),
        ("paused", False),
        ("answered", True),
        ("answered", False),
        ("historical", True),
        ("historical", False),
    ],
)
def test_change_intents_on_planner_pause_of_builder_planning_return_survive_default_loader_restart(
    tmp_path: Path,
    scenario: str,
    *,
    request_bearing: bool,
) -> None:
    change_id = "return-planning-pause-intent"
    restart = _builder_return_restart_fixture(tmp_path, change_id)
    settled = _settle_default_loader_planning_return(restart, change_id)
    application = _healthy_restart(restart)
    launch = application.acquire_frontier_work().launch_packages[0]
    pause = _planner_return_pause(launch.outcome_id, launch.claim.claim_id, request_bearing=request_bearing)
    application.transition_delivery(change_id, pause)
    if scenario == "paused":
        _assert_change_intent_restarts(restart, change_id, abandon=True)
        return
    if scenario == "historical":
        application = _assert_change_intent_restarts(restart, change_id, abandon=False)
    else:
        application = _healthy_restart(restart)
    _answer_planner_return_pause(application, change_id, pause)
    if scenario == "answered":
        _assert_change_intent_restarts(restart, change_id, abandon=True)
        return

    application = _assert_change_intent_restarts(restart, change_id, abandon=False)
    second_launch = _acquire_planner_after_pause(application, minutes=5)
    second_pause = _planner_return_pause(
        second_launch.outcome_id,
        second_launch.claim.claim_id,
        request_bearing=True,
        ordinal=2,
    )
    _healthy_restart(restart).transition_delivery(change_id, second_pause)
    _assert_change_intent_restarts(restart, change_id, abandon=False)
    _answer_planner_return_pause(_healthy_restart(restart), change_id, second_pause, option_id="split")
    answered = _assert_change_intent_restarts(restart, change_id, abandon=True)
    binding = answered._runtimes[change_id].show_binding("OUT-001")  # noqa: SLF001
    assert binding.return_context == settled.return_context


def _exhaust_default_loader_planning_return(
    restart: _BuilderReturnRestartFixture,
    change_id: str,
) -> OutcomeAuthorityBinding:
    application = restart.application
    for minutes in (5, 10):
        launch = application.acquire_frontier_work().launch_packages[0]
        assert launch.claim.worker_role is DeliveryWorkerRole.BUILDER
        application.settle_worker_invocation(
            DeliveryBuilderInvocationSettlement(
                change_id=change_id,
                outcome_id=launch.outcome_id,
                claim_id=launch.claim.claim_id,
                attempt_id=launch.claim.attempt_id,
                task_id=launch.task_id,
                expected_last_reviewed_commit=launch.last_reviewed_commit,
                disposition="normal-return",
                request=RetryDelivery(
                    action="retry",
                    outcome_id=launch.outcome_id,
                    claim_id=launch.claim.claim_id,
                    attempt_id=launch.claim.attempt_id,
                    abandoned_commit=launch.source_head,
                    failure_code="builder-failed",
                ),
            ),
            host_id=launch.claim.owner_id,
            session_id=launch.claim.process_id,
        )
        # Each Builder retry ends with a durable backoff before reacquisition.
        eligible_at = (datetime.now(UTC) + timedelta(minutes=minutes)).isoformat()
        application._clock = lambda eligible_at=eligible_at: eligible_at  # noqa: SLF001
    settled = _settle_default_loader_planning_return(restart, change_id)
    assert settled.stage == DeliveryStage.PLANNING
    assert settled.block is not None
    assert settled.block.block_id.startswith("builder-planning-route-")
    assert settled.block.request_id is None
    assert not settled.block.resolved
    assert settled.return_context is not None
    return settled


def _assert_exhausted_planning_return_readiness(application: PortfolioApplication, change_id: str) -> None:
    readiness = application.show_work_item_view(change_id, "outcome:OUT-001").readiness
    assert readiness is not None
    assert readiness.reason_code == "retry-exhausted"
    assert readiness.operation is None
    assert not readiness.executable
    assert application.acquire_frontier_work().launch_packages == ()


def test_exhausted_builder_planning_return_survives_default_loader_restart(tmp_path: Path) -> None:
    change_id = "return-planning-exhausted"
    restart = _builder_return_restart_fixture(tmp_path, change_id)
    settled = _exhaust_default_loader_planning_return(restart, change_id)

    restarted = _healthy_restart(restart)
    assert restarted._runtimes[change_id].show_binding("OUT-001") == settled  # noqa: SLF001
    _assert_exhausted_planning_return_readiness(restarted, change_id)

    resumed = _assert_change_intent_restarts(restart, change_id, abandon=False)
    _assert_exhausted_planning_return_readiness(resumed, change_id)
    abandoned = _assert_change_intent_restarts(restart, change_id, abandon=True)
    assert abandoned._runtimes[change_id].show_binding("OUT-001") == settled  # noqa: SLF001


@pytest.mark.parametrize(
    ("tamper", "expected_detail"),
    [
        ("planner-pause-shape", "local Delivery frontier differs from its exact Builder return promotion"),
        ("cleared-exhaustion", "local exhausted Builder return differs from its exact settlement"),
    ],
)
def test_default_loader_rejects_planner_pause_over_exhausted_builder_planning_return(
    tmp_path: Path,
    tamper: str,
    expected_detail: str,
) -> None:
    change_id = "return-planning-exhausted-forgery"
    restart = _builder_return_restart_fixture(tmp_path, change_id)
    settled = _exhaust_default_loader_planning_return(restart, change_id)
    assert settled.block is not None
    frontier_path = restart.fresh / ".owlbear/delivery/runtime/changes" / change_id / "frontier.json"
    frontier = DeliveryFrontier.model_validate_json(frontier_path.read_bytes(), strict=True)
    binding = frontier.bindings[0]
    changed = (
        binding.model_copy(update={"return_context": None})
        if tamper == "planner-pause-shape"
        else binding.model_copy(
            update={
                "block": settled.block.model_copy(
                    update={"resolution_note": "Forged operator clearance.", "resolution_locators": ("TASK-002",)}
                )
            }
        )
    )
    frontier_path.write_bytes(
        _canonical_payload(frontier.model_copy(update={"bindings": (changed,)}).model_dump(mode="json"))
    )

    frontier_before = frontier_path.read_bytes()
    health = load_delivery_application(restart.config, workspace_root=restart.fresh).delivery_health()
    assert health.status.value == "attention"
    assert any(
        diagnostic.change_id == change_id
        and diagnostic.code == "remote-state-reconciliation-required"
        and expected_detail in diagnostic.detail
        for diagnostic in health.diagnostics
    ), health.diagnostics
    assert frontier_path.read_bytes() == frontier_before


def test_default_loader_rejects_planner_pause_intent_chain_after_rolled_back_answer(tmp_path: Path) -> None:
    change_id = "return-planning-intent-rollback"
    restart = _builder_return_restart_fixture(tmp_path, change_id)
    _settle_default_loader_planning_return(restart, change_id)
    application = _healthy_restart(restart)
    launch = application.acquire_frontier_work().launch_packages[0]
    pause = _planner_return_pause(launch.outcome_id, launch.claim.claim_id, request_bearing=True)
    application.transition_delivery(change_id, pause)
    frontier_path = restart.fresh / ".owlbear/delivery/runtime/changes" / change_id / "frontier.json"
    paused_frontier = frontier_path.read_bytes()
    _answer_planner_return_pause(_healthy_restart(restart), change_id, pause)
    _assert_change_intent_restarts(restart, change_id, abandon=False)
    frontier_path.write_bytes(paused_frontier)

    rejected = load_delivery_application(restart.config, workspace_root=restart.fresh)
    health = rejected.delivery_health()
    assert health.status.value == "attention"
    assert any(
        diagnostic.change_id == change_id
        and diagnostic.code == "remote-state-reconciliation-required"
        and "local Builder lifecycle intent is not anchored to its exact settlement or answer" in diagnostic.detail
        for diagnostic in health.diagnostics
    ), health.diagnostics
    assert frontier_path.read_bytes() == paused_frontier


@pytest.mark.parametrize(
    ("scenario", "expected_detail"),
    [
        ("tampered-second-receipt", "local Planner pause differs from its exact Planning pause receipt"),
        ("foreign-second-receipt", "local Planner pause differs from its exact Planning pause receipt"),
        ("missing-first-receipt", "local Planner pause differs from its exact Planning pause receipt"),
        ("reordered-requests", "local Planner pause differs from its exact Planning pause receipt"),
        ("orphan-receipt", "local Planning pause receipt is outside its exact Planner pause sequence"),
    ],
)
def test_default_loader_rejects_unrecorded_repeated_planner_pause_on_builder_planning_return(
    tmp_path: Path,
    scenario: str,
    expected_detail: str,
) -> None:
    change_id = "return-planning-repeated-forgery"
    restart = _builder_return_restart_fixture(tmp_path, change_id)
    _settle_default_loader_planning_return(restart, change_id)
    first_pause, second_pause, _ = _pause_second_planner_return(
        restart,
        change_id,
        first_request_bearing=True,
        second_request_bearing=True,
    )
    assert first_pause.request is not None
    assert second_pause.request is not None
    change_root = restart.fresh / ".owlbear/delivery/runtime/changes" / change_id
    frontier_path = change_root / "frontier.json"
    receipts: dict[str, Path] = {}
    for path in (change_root / "planning-pause-receipts" / "OUT-001").glob("*.json"):
        receipt_request = _DeliveryPlanningPauseReplay.model_validate_json(path.read_bytes(), strict=True).request
        assert receipt_request.request is not None
        receipts[receipt_request.request.request_id] = path
    assert set(receipts) == {first_pause.request.request_id, second_pause.request.request_id}
    second_path = receipts[second_pause.request.request_id]
    second = _DeliveryPlanningPauseReplay.model_validate_json(second_path.read_bytes(), strict=True)
    if scenario == "tampered-second-receipt":
        payload = json.loads(second_path.read_bytes())
        payload["result"]["requests"][-2]["resolution"]["selected_option_id"] = "split"
        second_path.write_bytes(_canonical_payload(payload))
    elif scenario == "foreign-second-receipt":
        payload = json.loads(second_path.read_bytes())
        payload["change_id"] = "another-change"
        second_path.write_bytes(_canonical_payload(payload))
    elif scenario == "missing-first-receipt":
        receipts[first_pause.request.request_id].unlink()
    elif scenario == "reordered-requests":
        frontier = DeliveryFrontier.model_validate_json(frontier_path.read_bytes(), strict=True)
        binding = frontier.bindings[0]
        reordered = (*binding.requests[:-2], binding.requests[-1], binding.requests[-2])
        frontier_path.write_bytes(
            _canonical_payload(
                frontier.model_copy(
                    update={"bindings": (binding.model_copy(update={"requests": reordered}),)}
                ).model_dump(mode="json")
            )
        )
    else:
        assert second.request.request is not None
        orphan_request = second.request.request.model_copy(update={"request_id": "planner-return-orphan"})
        orphan_transition = second.request.model_copy(update={"request": orphan_request})
        assert second.result.block is not None
        orphan_result = second.result.model_copy(
            update={
                "block": second.result.block.model_copy(update={"request_id": "planner-return-orphan"}),
                "requests": (*second.result.requests[:-1], orphan_request),
            }
        )
        orphan_digest = hashlib.sha256(_model_content(orphan_transition)).hexdigest()
        orphan = second.model_copy(
            update={"request": orphan_transition, "result": orphan_result, "request_digest": orphan_digest}
        )
        _DeliveryPlanningPauseReplay.model_validate_json(_model_content(orphan), strict=True)
        (second_path.parent / f"{orphan_digest}.json").write_bytes(_model_content(orphan))

    frontier_before = frontier_path.read_bytes()
    rejected = load_delivery_application(restart.config, workspace_root=restart.fresh)
    health = rejected.delivery_health()
    assert health.status.value == "attention"
    assert any(
        diagnostic.change_id == change_id
        and diagnostic.code == "remote-state-reconciliation-required"
        and expected_detail in diagnostic.detail
        for diagnostic in health.diagnostics
    ), health.diagnostics
    assert frontier_path.read_bytes() == frontier_before


@pytest.mark.parametrize(
    "scenario",
    [
        "refused",
        "settled",
        "completed-timeout",
        "ended-without-result",
        "host-lost",
        "released-stuck",
        "deferred",
        "forged-context",
        "missing-receipt",
        "wrong-coordination",
        "foreign-branch",
        "task-drift",
        "history-drift",
        "active-edited",
        "active-foreign-head",
        "active-result",
        "active-candidate-wrong-claim",
        "active-accepted-result-drift",
    ],
)
def test_remote_state_bootstrap_preserves_builder_retry_state(  # noqa: PLR0915, C901, PLR0912
    tmp_path: Path,
    *,
    scenario: str,
) -> None:
    repository, remote, _initial = _repository(tmp_path)
    change_id = "bootstrap-refused-retry"
    contract, intent, design = _contract(change_id)
    state_root = tmp_path / "state"
    package_store = DesignPackageStore(repository / ".owlbear/delivery/packages", repository)
    package = package_store.create(change_id, intent, design)
    package_store.publish_contract(
        change_id,
        package.package_id,
        _canonical_payload(contract.model_dump(mode="json")),
        lambda *_content: None,
    )
    package = package_store.read_verified(change_id)
    coordinator = PortfolioCoordinator(state_root)
    manager = ChangeWorkspaceManager(repository, tmp_path / "worktrees", coordinator, "main")
    coordination = manager.ensure(change_id)
    task = DeliveryTaskDefinition(
        task_id="TASK-001",
        outcome_id="OUT-001",
        plan_scope_id="SCOPE-001",
        title="Persist result",
        result="Persist the result.",
        commitment_ids=("COM-001",),
        dependency_ids=(),
        required_outputs=("Result",),
        maintained_surfaces=("serve/delivery",),
        constraints=("Use the reviewed branch.",),
        exclusions=("Do not rewrite target history.",),
        acceptance_observations=("The result is persisted.",),
        proof_boundaries=("PortfolioApplication.acquire_frontier_work",),
    )
    frontier = DeliveryFrontier(
        bindings=(
            OutcomeAuthorityBinding(
                outcome_id="OUT-001",
                plan_scope_id="SCOPE-001",
                stage=DeliveryStage.IMPLEMENTATION,
                tasks=(task,),
            ),
        ),
    )
    frontier_path = state_root / "changes" / change_id / "frontier.json"
    frontier_path.parent.mkdir(parents=True, exist_ok=True)
    frontier_path.write_bytes(_canonical_payload(frontier.model_dump(mode="json")))
    runtime = DeliveryRuntime(state_root, contract, workspace_manager=manager)
    snapshot = manager.snapshot_design_package(
        change_id,
        package.package_id,
        {
            "authority.json": package.authority_bytes,
            "design.md": package.design_bytes,
            "intent.md": package.intent_bytes,
            "manifest.json": package.manifest.canonical_bytes(),
        },
        "bootstrap-package",
    )
    _git(repository, "push", "origin", f"{snapshot.snapshot_head}:refs/heads/{coordination.branch}")
    publisher = DeliveryStatePublisher(repository, remote=str(remote), state_branch="owlbear/delivery-state")
    publisher.publish(
        change_id=change_id,
        package_id=package.package_id,
        coordination=manager.show(change_id),
        runtime=runtime,
        admission=_admission(runtime, manager, change_id),
        operation_id="bootstrap-state",
        captured_at=datetime(2026, 8, 23, tzinfo=UTC),
    )

    fresh = tmp_path / "fresh"
    _git(tmp_path, "clone", str(remote), str(fresh))
    _git(fresh, "config", "url." + str(remote) + ".insteadOf", "https://github.com/example/project.git")
    _git(fresh, "remote", "set-url", "origin", "https://github.com/example/project.git")
    config = DeliveryStartupConfig(
        schema_version=2,
        remote="origin",
        target_branch="main",
        github_repository="example/project",
        delivery_state_branch="owlbear/delivery-state",
    )
    application = load_delivery_application(config, workspace_root=fresh, issuer_host=_TEST_WINDOW)
    launch = application.acquire_frontier_work().launch_packages[0]
    assert launch.claim.worker_role is DeliveryWorkerRole.BUILDER
    handoff_context = None
    if scenario != "refused":
        _git(fresh, "config", "user.name", "Delivery State Test")
        _git(fresh, "config", "user.email", "delivery-state@example.invalid")
        retry_file = launch.worktree_path / "committed-retry.txt"
        retry_file.write_text("preserved retry work\n", encoding="utf-8")
        _git(launch.worktree_path, "add", retry_file.name)
        _git(launch.worktree_path, "commit", "-m", "preserve Builder retry work")
        branch_head = _git(launch.worktree_path, "rev-parse", "HEAD")
        retry = RetryDelivery(
            action="retry",
            outcome_id=launch.outcome_id,
            claim_id=launch.claim.claim_id,
            abandoned_commit=branch_head,
            attempt_id=launch.claim.attempt_id,
            failure_code="builder-failed",
        )
        requestless = scenario in {"completed-timeout", "ended-without-result"}
        settlement = DeliveryBuilderInvocationSettlement(
            change_id=change_id,
            outcome_id=launch.outcome_id,
            claim_id=launch.claim.claim_id,
            attempt_id=launch.claim.attempt_id,
            task_id=launch.task_id,
            expected_last_reviewed_commit=launch.last_reviewed_commit,
            disposition=scenario if requestless else "normal-return",
            request=None if requestless else retry,
        )
        if scenario in {"host-lost", "released-stuck"}:
            settled = _settle_engine_worker_ending(application, launch, scenario)
        else:
            with patch.object(application, "_clock", return_value="1970-01-02T00:00:00Z"):
                settled = application.settle_worker_invocation(
                    settlement,
                    host_id=launch.claim.owner_id,
                    session_id=launch.claim.process_id,
                )
        handoff_context = settled.builder_handoff_context
        assert handoff_context is not None
    else:
        transition = RetryDelivery(
            action="retry",
            outcome_id="OUT-001",
            claim_id=launch.claim.claim_id,
            abandoned_commit=launch.last_reviewed_commit,
            attempt_id=launch.claim.attempt_id,
        )
        with pytest.raises(DeliveryWorkerExclusionRequiredError):
            application.transition_delivery(change_id, transition)
        refused = application.show_operator_context(change_id, "OUT-001")
        assert refused.active_claim is not None
        assert refused.retry_diagnostic is not None

    if scenario == "deferred":
        retry_runtime = application._runtimes[change_id]  # noqa: SLF001
        retry_git_state = _workspace_git_state(fresh, launch.worktree_path)
        remote_snapshot_ref = "refs/heads/owlbear/delivery-state"
        remote_snapshot_head = _git(remote, "rev-parse", remote_snapshot_ref)
        snapshot_path = f".owlbear/delivery/state/{change_id}/snapshot.json"
        remote_snapshot = subprocess.run(  # noqa: S603 - fixed Git executable and argument vector.
            (_GIT, "-C", str(remote), "show", f"{remote_snapshot_head}:{snapshot_path}"),
            check=True,
            capture_output=True,
        ).stdout
        retry_runtime.defer_change(
            "Waiting before retrying the retained Builder task.",
            datetime(2026, 8, 23, 1, tzinfo=UTC),
        )
        deferred_frontier_bytes = retry_runtime.frontier_bytes()

    negative_scenarios = {
        "forged-context",
        "missing-receipt",
        "wrong-coordination",
        "foreign-branch",
        "task-drift",
        "history-drift",
    }
    if scenario in {"forged-context", "task-drift", "history-drift"}:
        _tamper_builder_handoff_frontier(
            fresh,
            change_id,
            launch.outcome_id,
            launch.task_id,
            scenario,
        )
    elif scenario in {"missing-receipt", "wrong-coordination", "foreign-branch"}:
        _tamper_builder_handoff_host_state(
            fresh,
            change_id,
            coordination.branch,
            launch.claim.attempt_id,
            scenario,
        )
    git_state_before = _workspace_git_state(fresh, launch.worktree_path) if scenario in negative_scenarios else None

    reloaded = load_delivery_application(config, workspace_root=fresh)
    health = reloaded.delivery_health()
    if scenario not in negative_scenarios:
        assert health.status.value == "healthy"
        assert not any(item.change_id == change_id for item in health.diagnostics)
    persisted_frontier = DeliveryFrontier.model_validate_json(
        (fresh / ".owlbear/delivery/runtime/changes" / change_id / "frontier.json").read_bytes(), strict=True
    )
    binding = next(item for item in persisted_frontier.bindings if item.outcome_id == "OUT-001")
    if scenario in {"settled", "completed-timeout", "ended-without-result", "host-lost", "released-stuck"}:
        assert binding.active_claim is None
        assert binding.builder_handoff_context == handoff_context
        resumed = reloaded.acquire_frontier_work().launch_packages[0]
        assert resumed.claim.task_id == launch.task_id
        assert resumed.claim.claim_id != launch.claim.claim_id
        assert resumed.builder_handoff_context == handoff_context
        build_context = reloaded.show_build_context(
            change_id,
            resumed.outcome_id,
            resumed.claim.attempt_id,
            resumed.claim.claim_id,
        )
        assert build_context.launch.builder_handoff_context == handoff_context
        restarted = load_delivery_application(config, workspace_root=fresh)
        assert restarted.delivery_health().status.value == "healthy"
        restarted_build_context = restarted.show_build_context(
            change_id,
            resumed.outcome_id,
            resumed.claim.attempt_id,
            resumed.claim.claim_id,
        )
        assert restarted_build_context.launch.builder_handoff_context == handoff_context
    elif scenario == "deferred":
        assert health.status.value == "healthy"
        assert binding.active_claim is None
        assert binding.builder_handoff_context == handoff_context
        assert persisted_frontier.change_deferral is not None
        assert (
            fresh / ".owlbear/delivery/runtime/changes" / change_id / "frontier.json"
        ).read_bytes() == deferred_frontier_bytes
        assert reloaded.acquire_frontier_work().launch_packages == ()
        assert _workspace_git_state(fresh, launch.worktree_path) == retry_git_state
        assert _git(remote, "rev-parse", remote_snapshot_ref) == remote_snapshot_head
        assert (
            subprocess.run(  # noqa: S603 - fixed Git executable and argument vector.
                (_GIT, "-C", str(remote), "show", f"{remote_snapshot_head}:{snapshot_path}"),
                check=True,
                capture_output=True,
            ).stdout
            == remote_snapshot
        )
    elif scenario == "refused":
        assert binding.active_claim == launch.claim
        assert binding.retry_diagnostic == refused.retry_diagnostic
        operator = reloaded.show_operator_context(change_id, "OUT-001")
        assert operator.active_claim == refused.active_claim
        assert operator.retry_diagnostic == refused.retry_diagnostic
        readiness = reloaded.show_work_item_view(change_id, "outcome:OUT-001").readiness
        assert readiness.status == "blocked"
        assert readiness.reason_code == "retry-transition-contained"
        assert readiness.next_actor.value == "none"
        assert readiness.executable is False
        assert readiness.operation is None
        assert readiness.action is None
        assert readiness.prompt is not None
        assert "/repair-delivery" in readiness.prompt
        assert "delivery-diagnose inspect --change-id" in readiness.prompt
        assert "Make no MCP calls" in readiness.prompt
    elif scenario in {"active-edited", "active-foreign-head"}:
        assert binding.active_claim is None
        assert binding.builder_handoff_context == handoff_context
        resumed = reloaded.acquire_frontier_work().launch_packages[0]
        assert resumed.task_id == launch.task_id
        assert resumed.claim.claim_id != launch.claim.claim_id
        assert resumed.builder_handoff_context == handoff_context

        if scenario == "active-edited":
            committed = resumed.worktree_path / "committed-after-reacquisition.txt"
            committed.write_text("same-claim descendant\n", encoding="utf-8")
            _git(resumed.worktree_path, "add", committed.name)
            _git(resumed.worktree_path, "commit", "-m", "continue same Builder claim")
            branch_head = _git(resumed.worktree_path, "rev-parse", "HEAD")
            (resumed.worktree_path / "product.txt").write_text("dirty tracked work\n", encoding="utf-8")
            staged = resumed.worktree_path / "staged-after-reacquisition.txt"
            staged.write_text("staged same-claim work\n", encoding="utf-8")
            _git(resumed.worktree_path, "add", staged.name)
            untracked = resumed.worktree_path / "untracked-after-reacquisition.txt"
            untracked.write_text("untracked same-claim work\n", encoding="utf-8")
        else:
            tree = _git(fresh, "rev-parse", "HEAD^{tree}")
            foreign_head = _git(fresh, "commit-tree", tree, "-m", "foreign active Builder head")
            _git(fresh, "update-ref", f"refs/heads/{coordination.branch}", foreign_head)
        git_state_before_restart = _workspace_git_state(fresh, resumed.worktree_path)

        restarted = load_delivery_application(config, workspace_root=fresh)
        assert _workspace_git_state(fresh, resumed.worktree_path) == git_state_before_restart
        restart_health = restarted.delivery_health()
        if scenario == "active-edited":
            assert restart_health.status.value == "healthy"
            restarted_frontier = DeliveryFrontier.model_validate_json(
                (fresh / ".owlbear/delivery/runtime/changes" / change_id / "frontier.json").read_bytes(),
                strict=True,
            )
            restarted_binding = next(item for item in restarted_frontier.bindings if item.outcome_id == "OUT-001")
            assert restarted_binding.active_claim == resumed.claim
            assert restarted_binding.builder_handoff_context == handoff_context
            assert restarted_binding.result_candidate is None
            build_context = restarted.show_build_context(
                change_id,
                resumed.outcome_id,
                resumed.claim.attempt_id,
                resumed.claim.claim_id,
            )
            assert build_context.task.task_id == launch.task_id
            assert build_context.launch.source_head == branch_head
        else:
            assert restart_health.status.value == "attention"
            assert any(
                diagnostic.change_id == change_id and diagnostic.code == "remote-state-reconciliation-required"
                for diagnostic in restart_health.diagnostics
            )
    elif scenario in {"active-result", "active-candidate-wrong-claim", "active-accepted-result-drift"}:
        assert binding.active_claim is None
        assert binding.builder_handoff_context == handoff_context
        resumed = reloaded.acquire_frontier_work().launch_packages[0]
        assert resumed.task_id == launch.task_id
        assert resumed.claim.claim_id != launch.claim.claim_id
        active_runtime = reloaded._runtimes[change_id]  # noqa: SLF001 - exercise the loaded unpublished-result path.
        completed_commit = _git(resumed.worktree_path, "rev-parse", "HEAD")
        observed_at = datetime(2026, 8, 23, tzinfo=UTC)
        observation = DeliveryObservationReceipt.create(
            DeliveryObservation(
                change_id=change_id,
                task_or_finalization_id=task.task_id,
                exact_commit=completed_commit,
                observation_kind="pytest",
                procedure="active Builder result restart fixture",
                result=DeliveryCommandResult(exit_status=0),
                observer_or_runner_identity="pytest",
                observed_at=observed_at,
            )
        )
        review = DeliveryReviewReceipt.create(
            DeliveryReview(
                review_mode="task",
                exact_commit=completed_commit,
                author_id="Builder fixture author",
                reviewer_id="Builder fixture reviewer",
                evidence=("The result is bound to the active task commit.",),
                reviewed_at=observed_at,
            )
        )
        result = DeliveryTaskResult(
            result_id="RESULT-ACTIVE-001",
            change_id=change_id,
            authority_digest=active_runtime.authority_digest,
            task_id=task.task_id,
            task_digest=task.digest,
            completed_commit=completed_commit,
            observations=(observation,),
            review=review,
        )
        candidate = active_runtime.publish_result(
            PublishDeliveryResult(
                outcome_id="OUT-001",
                claim_id=resumed.claim.claim_id,
                result=result,
            )
        )
        assert candidate.claim_id == resumed.claim.claim_id
        frontier_before_late_publish = active_runtime.frontier_bytes()
        with pytest.raises(DeliveryRuntimeConflictError):
            active_runtime.publish_result(
                PublishDeliveryResult(
                    outcome_id="OUT-001",
                    claim_id=launch.claim.claim_id,
                    result=result,
                )
            )
        assert active_runtime.frontier_bytes() == frontier_before_late_publish
        if scenario == "active-candidate-wrong-claim":
            persisted_frontier = DeliveryFrontier.model_validate_json(active_runtime.frontier_bytes(), strict=True)
            persisted_binding = next(item for item in persisted_frontier.bindings if item.outcome_id == "OUT-001")
            foreign_candidate = candidate.model_copy(update={"claim_id": launch.claim.claim_id})
            tampered_binding = persisted_binding.model_copy(
                update={"result_candidate": foreign_candidate, "output": foreign_candidate.output}
            )
            frontier_path = fresh / ".owlbear/delivery/runtime/changes" / change_id / "frontier.json"
            frontier_path.write_bytes(
                _canonical_payload(
                    persisted_frontier.model_copy(
                        update={
                            "bindings": tuple(
                                tampered_binding if item.outcome_id == "OUT-001" else item
                                for item in persisted_frontier.bindings
                            )
                        }
                    ).model_dump(mode="json")
                )
            )
        elif scenario == "active-accepted-result-drift":
            persisted_frontier = DeliveryFrontier.model_validate_json(active_runtime.frontier_bytes(), strict=True)
            persisted_binding = next(item for item in persisted_frontier.bindings if item.outcome_id == "OUT-001")
            tampered_binding = persisted_binding.model_copy(update={"results": (result,)})
            frontier_path = fresh / ".owlbear/delivery/runtime/changes" / change_id / "frontier.json"
            frontier_path.write_bytes(
                _canonical_payload(
                    persisted_frontier.model_copy(
                        update={
                            "bindings": tuple(
                                tampered_binding if item.outcome_id == "OUT-001" else item
                                for item in persisted_frontier.bindings
                            )
                        }
                    ).model_dump(mode="json")
                )
            )
        git_state_before_restart = _workspace_git_state(fresh, resumed.worktree_path)

        restarted = load_delivery_application(config, workspace_root=fresh)
        assert _workspace_git_state(fresh, resumed.worktree_path) == git_state_before_restart
        restart_health = restarted.delivery_health()
        if scenario == "active-result":
            assert restart_health.status.value == "healthy"
            restarted_frontier = DeliveryFrontier.model_validate_json(
                (fresh / ".owlbear/delivery/runtime/changes" / change_id / "frontier.json").read_bytes(),
                strict=True,
            )
            restarted_binding = next(item for item in restarted_frontier.bindings if item.outcome_id == "OUT-001")
            assert restarted_binding.stage == DeliveryStage.IMPLEMENTATION
            assert restarted_binding.active_claim == resumed.claim
            assert restarted_binding.builder_handoff_context == handoff_context
            assert restarted_binding.results == ()
            assert restarted_binding.result_candidate == candidate
            assert restarted_binding.output == candidate.output
            build_context = restarted.show_build_context(
                change_id,
                resumed.outcome_id,
                resumed.claim.attempt_id,
                resumed.claim.claim_id,
            )
            assert build_context.task.task_id == task.task_id
            assert build_context.launch.source_head == completed_commit
        else:
            assert restart_health.status.value == "attention"
            assert any(
                diagnostic.change_id == change_id and diagnostic.code == "remote-state-reconciliation-required"
                for diagnostic in restart_health.diagnostics
            )
    else:
        attention = next(item for item in health.diagnostics if item.change_id == change_id)
        assert attention.code == "remote-state-reconciliation-required"
        assert len(attention.detail) <= 512
        assert git_state_before is not None
        assert git_state_before == _workspace_git_state(fresh, launch.worktree_path)


_TEST_WINDOW = WindowHostIdentity(pid=4242, create_time=1_700_000_000.5, name="Code Helper (Plugin)")


class _ClosedWindowWithoutLeftovers:
    def window_state(self, _window: WindowHostIdentity) -> str:
        return "gone"

    def active_processes(self, _roots: tuple[Path, ...], *, issued_after: datetime | None) -> tuple[str, ...]:  # noqa: ARG002
        return ()


def _settle_engine_worker_ending(application, launch, disposition: str) -> OutcomeAuthorityBinding:
    """Settle through the engine owner with a quiet observation; quiescence itself is proven elsewhere."""
    quiet_activity = datetime(1970, 1, 1, tzinfo=UTC)
    environment = _ClosedWindowWithoutLeftovers()
    with (
        patch.object(application, "_clock", return_value="1970-01-02T00:00:00Z"),
        patch.object(application._workspace_manager, "observe_worktree_activity", return_value=quiet_activity),  # noqa: SLF001
        patch.object(application, "_worktree_process_probe", environment),
    ):
        if disposition == "released-stuck":
            return application.release_stuck_worker(
                launch.change_id, launch.outcome_id, launch.claim.attempt_id, launch.claim.claim_id
            )
        issuer = application._read_claim_issuer(launch.change_id, launch.claim.attempt_id)  # noqa: SLF001
        assert issuer is not None
        assert issuer.window == _TEST_WINDOW
        with patch.object(application, "_window_liveness_probe", environment):
            application.acquire_frontier_work()
    return application._runtimes[launch.change_id].show_binding(launch.outcome_id)  # noqa: SLF001


@pytest.mark.parametrize("disposition", ["completed-timeout", "ended-without-result", "host-lost", "released-stuck"])
def test_remote_state_bootstrap_preserves_requestless_planner_settlement(tmp_path: Path, disposition: str) -> None:
    repository, remote, _initial = _repository(tmp_path)
    change_id = "bootstrap-planner-settlement"
    contract, intent, design = _contract(change_id)
    state_root = tmp_path / "state"
    package_store = DesignPackageStore(repository / ".owlbear/delivery/packages", repository)
    package = package_store.create(change_id, intent, design)
    package_store.publish_contract(
        change_id,
        package.package_id,
        _canonical_payload(contract.model_dump(mode="json")),
        lambda *_content: None,
    )
    package = package_store.read_verified(change_id)
    coordinator = PortfolioCoordinator(state_root)
    manager = ChangeWorkspaceManager(repository, tmp_path / "worktrees", coordinator, "main")
    coordination = manager.ensure(change_id)
    frontier = DeliveryFrontier(
        bindings=(
            OutcomeAuthorityBinding(outcome_id="OUT-001", plan_scope_id="SCOPE-001", stage=DeliveryStage.PLANNING),
        ),
    )
    frontier_path = state_root / "changes" / change_id / "frontier.json"
    frontier_path.parent.mkdir(parents=True, exist_ok=True)
    frontier_path.write_bytes(_canonical_payload(frontier.model_dump(mode="json")))
    runtime = DeliveryRuntime(state_root, contract, workspace_manager=manager)
    snapshot = manager.snapshot_design_package(
        change_id,
        package.package_id,
        {
            "authority.json": package.authority_bytes,
            "design.md": package.design_bytes,
            "intent.md": package.intent_bytes,
            "manifest.json": package.manifest.canonical_bytes(),
        },
        "bootstrap-package",
    )
    _git(repository, "push", "origin", f"{snapshot.snapshot_head}:refs/heads/{coordination.branch}")
    publisher = DeliveryStatePublisher(repository, remote=str(remote), state_branch="owlbear/delivery-state")
    publisher.publish(
        change_id=change_id,
        package_id=package.package_id,
        coordination=manager.show(change_id),
        runtime=runtime,
        admission=_admission(runtime, manager, change_id),
        operation_id="bootstrap-state",
        captured_at=datetime(2026, 8, 23, tzinfo=UTC),
    )
    fresh = tmp_path / "fresh"
    _git(tmp_path, "clone", str(remote), str(fresh))
    _git(fresh, "config", "url." + str(remote) + ".insteadOf", "https://github.com/example/project.git")
    _git(fresh, "remote", "set-url", "origin", "https://github.com/example/project.git")
    config = DeliveryStartupConfig(
        schema_version=2,
        remote="origin",
        target_branch="main",
        github_repository="example/project",
        delivery_state_branch="owlbear/delivery-state",
    )
    application = load_delivery_application(config, workspace_root=fresh, issuer_host=_TEST_WINDOW)
    launch = application.acquire_frontier_work().launch_packages[0]
    assert launch.claim.worker_role is DeliveryWorkerRole.PLANNER
    if disposition in {"host-lost", "released-stuck"}:
        settled = _settle_engine_worker_ending(application, launch, disposition)
    else:
        settlement = DeliveryPlanningRetrySettlement(
            change_id=change_id,
            outcome_id=launch.outcome_id,
            claim_id=launch.claim.claim_id,
            attempt_id=launch.claim.attempt_id,
            disposition=disposition,
        )
        with patch.object(application, "_clock", return_value="1970-01-02T00:00:00Z"):
            settled = application.settle_worker_invocation(
                settlement,
                host_id=launch.claim.owner_id,
                session_id=launch.claim.process_id,
            )
    assert settled.active_claim is None

    reloaded = load_delivery_application(config, workspace_root=fresh)

    health = reloaded.delivery_health()
    assert health.status.value == "healthy"
    assert not any(item.change_id == change_id for item in health.diagnostics)
    runtime_root = fresh / ".owlbear/delivery/runtime/changes" / change_id
    persisted = DeliveryFrontier.model_validate_json((runtime_root / "frontier.json").read_bytes(), strict=True)
    assert persisted.bindings[0].active_claim is None
    owner_result = json.loads(
        (runtime_root / "retry-ledger/owner-results" / f"{launch.claim.attempt_id}.json").read_bytes()
    )
    assert (
        owner_result["failure_code"]
        == {
            "completed-timeout": "worker-timeout",
            "ended-without-result": "worker-ended-without-result",
            "host-lost": "worker-host-lost",
            "released-stuck": "worker-released-stuck",
        }[disposition]
    )
    resumed = reloaded.acquire_frontier_work().launch_packages[0]
    assert resumed.claim.worker_role is DeliveryWorkerRole.PLANNER
    assert resumed.outcome_id == launch.outcome_id
    assert resumed.claim.attempt_id != launch.claim.attempt_id
    assert load_delivery_application(config, workspace_root=fresh).delivery_health().status.value == "healthy"


@pytest.mark.parametrize(
    "lifecycle",
    [
        "resume",
        "abandon",
        "corrupt-head",
        "missing-chain",
        "reordered-chain",
        "foreign-settlement",
    ],
)
def test_loader_preserves_builder_pause_lifecycle_handoff(  # noqa: C901, PLR0915
    tmp_path: Path,
    *,
    lifecycle: str,
) -> None:
    repository, remote, _initial = _repository(tmp_path)
    change_id = "bootstrap-refused-retry"
    contract, intent, design = _contract(change_id)
    state_root = tmp_path / "state"
    package_store = DesignPackageStore(repository / ".owlbear/delivery/packages", repository)
    package = package_store.create(change_id, intent, design)
    package_store.publish_contract(
        change_id,
        package.package_id,
        _canonical_payload(contract.model_dump(mode="json")),
        lambda *_content: None,
    )
    package = package_store.read_verified(change_id)
    coordinator = PortfolioCoordinator(state_root)
    manager = ChangeWorkspaceManager(repository, tmp_path / "worktrees", coordinator, "main")
    coordination = manager.ensure(change_id)
    task = DeliveryTaskDefinition(
        task_id="TASK-001",
        outcome_id="OUT-001",
        plan_scope_id="SCOPE-001",
        title="Persist result",
        result="Persist the result.",
        commitment_ids=("COM-001",),
        dependency_ids=(),
        required_outputs=("Result",),
        maintained_surfaces=("serve/delivery",),
        constraints=("Use the reviewed branch.",),
        exclusions=("Do not rewrite target history.",),
        acceptance_observations=("The result is persisted.",),
        proof_boundaries=("PortfolioApplication.acquire_frontier_work",),
    )
    frontier = DeliveryFrontier(
        bindings=(
            OutcomeAuthorityBinding(
                outcome_id="OUT-001",
                plan_scope_id="SCOPE-001",
                stage=DeliveryStage.IMPLEMENTATION,
                tasks=(task,),
            ),
        ),
    )
    frontier_path = state_root / "changes" / change_id / "frontier.json"
    frontier_path.parent.mkdir(parents=True, exist_ok=True)
    frontier_path.write_bytes(_canonical_payload(frontier.model_dump(mode="json")))
    runtime = DeliveryRuntime(state_root, contract, workspace_manager=manager)
    snapshot = manager.snapshot_design_package(
        change_id,
        package.package_id,
        {
            "authority.json": package.authority_bytes,
            "design.md": package.design_bytes,
            "intent.md": package.intent_bytes,
            "manifest.json": package.manifest.canonical_bytes(),
        },
        "bootstrap-package",
    )
    _git(repository, "push", "origin", f"{snapshot.snapshot_head}:refs/heads/{coordination.branch}")
    publisher = DeliveryStatePublisher(repository, remote=str(remote), state_branch="owlbear/delivery-state")
    publisher.publish(
        change_id=change_id,
        package_id=package.package_id,
        coordination=manager.show(change_id),
        runtime=runtime,
        admission=_admission(runtime, manager, change_id),
        operation_id="bootstrap-state",
        captured_at=datetime(2026, 8, 23, tzinfo=UTC),
    )

    remote_snapshot_ref = "refs/heads/owlbear/delivery-state"
    remote_snapshot_head = _git(remote, "rev-parse", remote_snapshot_ref)
    snapshot_path = f".owlbear/delivery/state/{change_id}/snapshot.json"
    remote_snapshot = subprocess.run(  # noqa: S603 - fixed Git executable and argument vector.
        (_GIT, "-C", str(remote), "show", f"{remote_snapshot_head}:{snapshot_path}"),
        check=True,
        capture_output=True,
    ).stdout

    def assert_remote_snapshot_unchanged() -> None:
        assert _git(remote, "rev-parse", remote_snapshot_ref) == remote_snapshot_head
        current_snapshot = subprocess.run(  # noqa: S603 - fixed Git executable and argument vector.
            (_GIT, "-C", str(remote), "show", f"{remote_snapshot_head}:{snapshot_path}"),
            check=True,
            capture_output=True,
        )
        assert current_snapshot.stdout == remote_snapshot

    fresh = tmp_path / "fresh"
    _git(tmp_path, "clone", str(remote), str(fresh))
    _git(fresh, "config", "url." + str(remote) + ".insteadOf", "https://github.com/example/project.git")
    _git(fresh, "remote", "set-url", "origin", "https://github.com/example/project.git")
    config = DeliveryStartupConfig(
        schema_version=2,
        remote="origin",
        target_branch="main",
        github_repository="example/project",
        delivery_state_branch="owlbear/delivery-state",
    )
    application = load_delivery_application(config, workspace_root=fresh)
    initial_acquisition = application.acquire_frontier_work()
    assert initial_acquisition.launch_packages, (initial_acquisition, application.list_work_items())
    launch = initial_acquisition.launch_packages[0]
    assert launch.claim.worker_role is DeliveryWorkerRole.BUILDER

    _git(fresh, "config", "user.name", "Delivery State Test")
    _git(fresh, "config", "user.email", "delivery-state@example.invalid")
    committed = launch.worktree_path / "committed-pause.txt"
    committed.write_text("preserved Builder pause work\n", encoding="utf-8")
    _git(launch.worktree_path, "add", committed.name)
    _git(launch.worktree_path, "commit", "-m", "preserve Builder pause work")
    branch_head = _git(launch.worktree_path, "rev-parse", "HEAD")
    active_workspace_manager = ChangeWorkspaceManager(
        fresh,
        fresh / ".owlbear/delivery/worktrees",
        PortfolioCoordinator(fresh / ".owlbear/delivery/runtime"),
        "main",
    )
    pre_settlement_metadata = active_workspace_manager._capture_builder_handoff_metadata(  # noqa: SLF001
        active_workspace_manager.show(change_id)
    )
    request = DeliveryRequest(
        request_id="builder-pause-decision",
        kind=DeliveryRequestKind.DECISION,
        outcome_id=launch.outcome_id,
        summary="Choose the evidence source for the retained Builder task.",
        options=(
            DeliveryRequestOption(option_id="local", label="Use local evidence"),
            DeliveryRequestOption(option_id="remote", label="Wait for remote evidence"),
        ),
    )
    block_request = BlockDelivery(
        action="block",
        outcome_id=launch.outcome_id,
        claim_id=launch.claim.claim_id,
        block_id="builder-pause-decision-block",
        reason="A bounded evidence-source decision is required.",
        unblock_condition="The user selects an evidence source.",
        expected_evidence=("Selected evidence source",),
        locators=(launch.task_id,),
        request=request,
        resume_commit=branch_head,
    )
    paused = application.settle_worker_invocation(
        DeliveryBuilderInvocationSettlement(
            change_id=change_id,
            outcome_id=launch.outcome_id,
            claim_id=launch.claim.claim_id,
            attempt_id=launch.claim.attempt_id,
            task_id=launch.task_id,
            expected_last_reviewed_commit=launch.last_reviewed_commit,
            disposition="normal-return",
            request=block_request,
        ),
        host_id=launch.claim.owner_id,
        session_id=launch.claim.process_id,
    )
    handoff_context = paused.builder_handoff_context
    assert handoff_context is not None
    assert pre_settlement_metadata.fingerprint == handoff_context.metadata_fingerprint
    assert paused.block is not None
    assert not paused.block.resolved
    assert paused.requests[-1] == request

    runtime_root = fresh / ".owlbear/delivery/runtime"
    local_frontier_path = runtime_root / "changes" / change_id / "frontier.json"
    coordination_path = runtime_root / "coordination/changes" / f"{change_id}.json"
    attempt_digest = hashlib.sha256(launch.claim.attempt_id.encode("utf-8")).hexdigest()
    settlement_receipt_path = (
        runtime_root / "changes" / change_id / "builder-invocation-receipts" / f"{attempt_digest}.json"
    )
    assert paused.builder_handoff_context is not None
    resolution_receipt_path = (
        runtime_root
        / "changes"
        / change_id
        / "builder-request-resolution-receipts"
        / f"{paused.builder_handoff_context.settlement_id}.json"
    )
    unresolved_frontier_bytes = local_frontier_path.read_bytes()
    settlement_receipt_bytes = settlement_receipt_path.read_bytes()
    coordination_bytes = coordination_path.read_bytes()
    unresolved_frontier = DeliveryFrontier.model_validate_json(unresolved_frontier_bytes, strict=True)
    unresolved_binding = next(item for item in unresolved_frontier.bindings if item.outcome_id == "OUT-001")
    assert unresolved_binding == paused
    assert not resolution_receipt_path.exists()
    pause_git_state = _workspace_git_state(fresh, launch.worktree_path)
    intent_directory = (
        runtime_root / "changes" / change_id / "builder-handoff-change-intent-receipts" / handoff_context.settlement_id
    )
    intent_head_path = intent_directory / "head.json"

    def read_lifecycle_intent_files() -> dict[str, bytes]:
        return {path.name: path.read_bytes() for path in intent_directory.iterdir() if path.is_file()}

    def assert_lifecycle_chain_quarantined(
        expected_frontier_bytes: bytes,
        expected_intent_files: dict[str, bytes],
    ) -> None:
        rejected = load_delivery_application(config, workspace_root=fresh)
        health = rejected.delivery_health()
        assert health.status.value == "attention"
        assert any(
            diagnostic.change_id == change_id and diagnostic.code == "remote-state-reconciliation-required"
            for diagnostic in health.diagnostics
        )
        assert local_frontier_path.read_bytes() == expected_frontier_bytes
        assert settlement_receipt_path.read_bytes() == settlement_receipt_bytes
        assert coordination_path.read_bytes() == coordination_bytes
        assert not resolution_receipt_path.exists()
        assert read_lifecycle_intent_files() == expected_intent_files
        assert _workspace_git_state(fresh, launch.worktree_path) == pause_git_state
        assert_remote_snapshot_unchanged()

    fresh_workspace_manager = ChangeWorkspaceManager(
        fresh,
        fresh / ".owlbear/delivery/worktrees",
        PortfolioCoordinator(runtime_root),
        "main",
    )
    fresh_coordination = fresh_workspace_manager.show(change_id)
    assert fresh_coordination.builder_handoff is not None
    captured_handoff_metadata = fresh_workspace_manager._capture_builder_handoff_metadata(  # noqa: SLF001
        fresh_coordination
    )
    assert captured_handoff_metadata == pre_settlement_metadata
    unanswered_application = load_delivery_application(config, workspace_root=fresh)
    unanswered_health = unanswered_application.delivery_health()
    assert unanswered_health.status.value == "healthy", tuple(item.detail for item in unanswered_health.diagnostics)
    assert local_frontier_path.read_bytes() == unresolved_frontier_bytes
    assert settlement_receipt_path.read_bytes() == settlement_receipt_bytes
    assert not resolution_receipt_path.exists()
    unanswered_acquisition = unanswered_application.acquire_frontier_work()
    assert unanswered_acquisition.launch_packages == ()
    assert unanswered_acquisition.failures == ()
    assert _workspace_git_state(fresh, launch.worktree_path) == pause_git_state

    unanswered_application._runtimes[change_id].defer_change(  # noqa: SLF001
        "Waiting for the bounded Builder request to be answered.",
        datetime(2026, 8, 23, 2, tzinfo=UTC),
    )
    if lifecycle == "reordered-chain":
        unanswered_application._runtimes[change_id].resume_change()  # noqa: SLF001
        intent_head = json.loads(intent_head_path.read_bytes())
        intent_head["sequence"] = 1
        intent_head_path.write_bytes(_canonical_payload(intent_head))
    elif lifecycle == "corrupt-head":
        intent_head = json.loads(intent_head_path.read_bytes())
        intent_head["latest_receipt_id"] = "0" * 64
        intent_head_path.write_bytes(_canonical_payload(intent_head))
    elif lifecycle == "missing-chain":
        intent_head_path.unlink()
    elif lifecycle == "foreign-settlement":
        intent_head = json.loads(intent_head_path.read_bytes())
        intent_head["settlement_id"] = "0" * 64
        intent_head_path.write_bytes(_canonical_payload(intent_head))

    lifecycle_frontier_bytes = local_frontier_path.read_bytes()
    lifecycle_frontier = DeliveryFrontier.model_validate_json(lifecycle_frontier_bytes, strict=True)
    if lifecycle in {"corrupt-head", "missing-chain", "reordered-chain", "foreign-settlement"}:
        assert_lifecycle_chain_quarantined(lifecycle_frontier_bytes, read_lifecycle_intent_files())
        return

    assert lifecycle_frontier.change_deferral is not None
    deferred_application = load_delivery_application(config, workspace_root=fresh)
    deferred_health = deferred_application.delivery_health()
    assert deferred_health.status.value == "healthy", deferred_health.diagnostics
    deferred_acquisition = deferred_application.acquire_frontier_work()
    assert deferred_acquisition.launch_packages == ()
    assert deferred_acquisition.failures == ()
    assert _workspace_git_state(fresh, launch.worktree_path) == pause_git_state

    if lifecycle == "abandon":
        deferred_application._runtimes[change_id].abandon_change(  # noqa: SLF001
            "The user abandoned this paused Change.",
            datetime(2026, 8, 23, 3, tzinfo=UTC),
        )
        abandoned_frontier_bytes = local_frontier_path.read_bytes()
        abandoned_frontier = DeliveryFrontier.model_validate_json(abandoned_frontier_bytes, strict=True)
        abandoned_application = load_delivery_application(config, workspace_root=fresh)
        abandoned_health = abandoned_application.delivery_health()
        assert abandoned_health.status.value == "healthy", abandoned_health.diagnostics
        abandoned_history = abandoned_application.show_completed_change(change_id)
        assert abandoned_history.record_kind == "abandoned-change"
        assert abandoned_history.cleanup_available is False
        assert abandoned_frontier.change_deferral is None
        assert abandoned_frontier.change_abandonment is not None
        assert abandoned_frontier.bindings[0] == unresolved_binding
        abandoned_acquisition = abandoned_application.acquire_frontier_work()
        assert abandoned_acquisition.launch_packages == ()
        assert abandoned_acquisition.failures == ()
        assert coordination_path.read_bytes() == coordination_bytes
        assert PortfolioCoordinator(runtime_root).show(change_id).builder_handoff is not None
        assert launch.worktree_path.is_dir()
        assert local_frontier_path.read_bytes() == abandoned_frontier_bytes
        assert _workspace_git_state(fresh, launch.worktree_path) == pause_git_state
        assert_remote_snapshot_unchanged()
        return

    deferred_application._runtimes[change_id].resume_change()  # noqa: SLF001
    resumed_frontier = DeliveryFrontier.model_validate_json(local_frontier_path.read_bytes(), strict=True)
    assert resumed_frontier == unresolved_frontier
    resumed_application = load_delivery_application(config, workspace_root=fresh)
    resumed_health = resumed_application.delivery_health()
    assert resumed_health.status.value == "healthy", resumed_health.diagnostics
    resumed_acquisition = resumed_application.acquire_frontier_work()
    assert resumed_acquisition.launch_packages == ()
    assert resumed_acquisition.failures == ()
    assert _workspace_git_state(fresh, launch.worktree_path) == pause_git_state
    application = resumed_application

    def assert_quarantined(
        expected_frontier_bytes: bytes,
        expected_resolution_receipt_bytes: bytes | None,
        expected_git_state: tuple[str, str, str, str, bytes],
    ) -> None:
        expected_intent_files = read_lifecycle_intent_files()
        rejected = load_delivery_application(config, workspace_root=fresh)
        health = rejected.delivery_health()
        assert health.status.value == "attention"
        assert any(
            diagnostic.change_id == change_id and diagnostic.code == "remote-state-reconciliation-required"
            for diagnostic in health.diagnostics
        )
        assert local_frontier_path.read_bytes() == expected_frontier_bytes
        assert settlement_receipt_path.read_bytes() == settlement_receipt_bytes
        assert coordination_path.read_bytes() == coordination_bytes
        if expected_resolution_receipt_bytes is None:
            assert not resolution_receipt_path.exists()
        else:
            assert resolution_receipt_path.read_bytes() == expected_resolution_receipt_bytes
        assert read_lifecycle_intent_files() == expected_intent_files
        assert _workspace_git_state(fresh, launch.worktree_path) == expected_git_state

    changed_request = request.model_copy(
        update={
            "options": tuple(
                option.model_copy(update={"label": f"{option.label} changed"}) for option in request.options
            )
        }
    )
    changed_requests = tuple(
        changed_request if item.request_id == request.request_id else item for item in unresolved_binding.requests
    )
    changed_binding = unresolved_binding.model_copy(update={"requests": changed_requests})
    changed_frontier = unresolved_frontier.model_copy(
        update={
            "bindings": tuple(
                changed_binding if item.outcome_id == "OUT-001" else item for item in unresolved_frontier.bindings
            )
        }
    )
    changed_frontier_bytes = _canonical_payload(changed_frontier.model_dump(mode="json"))
    local_frontier_path.write_bytes(changed_frontier_bytes)
    assert_quarantined(changed_frontier_bytes, None, pause_git_state)
    local_frontier_path.write_bytes(unresolved_frontier_bytes)

    drifted_binding = unresolved_binding.model_copy(update={"retry_count": unresolved_binding.retry_count + 1})
    drifted_frontier = unresolved_frontier.model_copy(
        update={
            "bindings": tuple(
                drifted_binding if item.outcome_id == "OUT-001" else item for item in unresolved_frontier.bindings
            )
        }
    )
    drifted_frontier_bytes = _canonical_payload(drifted_frontier.model_dump(mode="json"))
    local_frontier_path.write_bytes(drifted_frontier_bytes)
    assert_quarantined(drifted_frontier_bytes, None, pause_git_state)
    local_frontier_path.write_bytes(unresolved_frontier_bytes)

    forged_resolution = DeliveryRequestResolution(selected_option_id="local", provenance="user-confirmed")
    forged_request = request.model_copy(update={"resolution": forged_resolution})
    assert unresolved_binding.block is not None
    forged_binding = unresolved_binding.model_copy(
        update={
            "requests": tuple(
                forged_request if item.request_id == request.request_id else item
                for item in unresolved_binding.requests
            ),
            "block": unresolved_binding.block.model_copy(
                update={"resolution_note": "local", "resolution_locators": (request.request_id,)}
            ),
        }
    )
    forged_frontier = unresolved_frontier.model_copy(
        update={
            "bindings": tuple(
                forged_binding if item.outcome_id == "OUT-001" else item for item in unresolved_frontier.bindings
            )
        }
    )
    forged_frontier_bytes = _canonical_payload(forged_frontier.model_dump(mode="json"))
    local_frontier_path.write_bytes(forged_frontier_bytes)
    assert_quarantined(forged_frontier_bytes, None, pause_git_state)
    local_frontier_path.write_bytes(unresolved_frontier_bytes)

    answer = DeliveryRequestResolution(
        selected_option_id="local",
        response_text="Use the verified local evidence.",
        provenance="user-confirmed",
    )
    resolved_request = application.resolve_request(change_id, request.request_id, answer)
    assert resolved_request == request.model_copy(update={"resolution": answer})
    answered_frontier_bytes = local_frontier_path.read_bytes()
    resolution_receipt_bytes = resolution_receipt_path.read_bytes()
    answered_frontier = DeliveryFrontier.model_validate_json(answered_frontier_bytes, strict=True)
    answered_binding = next(item for item in answered_frontier.bindings if item.outcome_id == "OUT-001")
    assert (
        answered_binding.model_copy(update={"requests": unresolved_binding.requests, "block": unresolved_binding.block})
        == unresolved_binding
    )
    answered_git_state = _workspace_git_state(fresh, launch.worktree_path)

    resolution_receipt_path.unlink()
    assert_quarantined(answered_frontier_bytes, None, answered_git_state)
    resolution_receipt_path.write_bytes(resolution_receipt_bytes)

    forged_receipt = json.loads(resolution_receipt_bytes)
    forged_receipt["resolved_request"]["options"][0]["label"] = "Unreviewed evidence source"
    forged_receipt_bytes = _canonical_payload(forged_receipt)
    resolution_receipt_path.write_bytes(forged_receipt_bytes)
    assert_quarantined(answered_frontier_bytes, forged_receipt_bytes, answered_git_state)
    resolution_receipt_path.write_bytes(resolution_receipt_bytes)

    answered_drifted_binding = answered_binding.model_copy(update={"retry_count": answered_binding.retry_count + 1})
    answered_drifted_frontier = answered_frontier.model_copy(
        update={
            "bindings": tuple(
                answered_drifted_binding if item.outcome_id == "OUT-001" else item
                for item in answered_frontier.bindings
            )
        }
    )
    answered_drifted_bytes = _canonical_payload(answered_drifted_frontier.model_dump(mode="json"))
    local_frontier_path.write_bytes(answered_drifted_bytes)
    assert_quarantined(answered_drifted_bytes, resolution_receipt_bytes, answered_git_state)
    local_frontier_path.write_bytes(answered_frontier_bytes)

    drifted_task_binding = answered_binding.model_copy(
        update={
            "tasks": tuple(
                task.model_copy(update={"title": f"{task.title} changed"}) if task.task_id == launch.task_id else task
                for task in answered_binding.tasks
            )
        }
    )
    task_drifted_frontier = answered_frontier.model_copy(
        update={
            "bindings": tuple(
                drifted_task_binding if item.outcome_id == "OUT-001" else item for item in answered_frontier.bindings
            )
        }
    )
    task_drifted_bytes = _canonical_payload(task_drifted_frontier.model_dump(mode="json"))
    local_frontier_path.write_bytes(task_drifted_bytes)
    assert_quarantined(task_drifted_bytes, resolution_receipt_bytes, answered_git_state)
    local_frontier_path.write_bytes(answered_frontier_bytes)

    answered_application = load_delivery_application(config, workspace_root=fresh)
    answered_health = answered_application.delivery_health()
    assert answered_health.status.value == "healthy", answered_health.diagnostics
    assert local_frontier_path.read_bytes() == answered_frontier_bytes
    assert resolution_receipt_path.read_bytes() == resolution_receipt_bytes
    assert PortfolioCoordinator(runtime_root).show(change_id).builder_handoff is not None
    retry_episodes = answered_application._runtimes[change_id].retry_ledger().read().episodes  # noqa: SLF001
    assert len(retry_episodes) == 1
    next_eligible_at = retry_episodes[0].next_eligible_at
    assert next_eligible_at is not None
    retry_eligible_at = datetime.fromisoformat(next_eligible_at)
    resume_time = (retry_eligible_at + timedelta(seconds=1)).isoformat().replace("+00:00", "Z")
    answered_application._clock = lambda: resume_time  # noqa: SLF001
    resumed_acquisition = answered_application.acquire_frontier_work()
    assert resumed_acquisition.launch_packages, (
        tuple(
            (failure.code, failure.detail, failure.retry_condition, failure.pre_effect_retryable)
            for failure in resumed_acquisition.failures
        ),
        retry_episodes,
    )
    resumed = resumed_acquisition.launch_packages[0]
    assert resumed.task_id == launch.task_id
    assert resumed.claim.claim_id != launch.claim.claim_id
    assert resumed.builder_handoff_context == handoff_context

    active_frontier_bytes = local_frontier_path.read_bytes()
    active_frontier = DeliveryFrontier.model_validate_json(active_frontier_bytes, strict=True)
    active_binding = next(item for item in active_frontier.bindings if item.outcome_id == "OUT-001")
    assert active_binding.model_copy(update={"active_claim": None}) == answered_binding
    active_git_state = _workspace_git_state(fresh, resumed.worktree_path)
    active_restart = load_delivery_application(config, workspace_root=fresh)
    assert active_restart.delivery_health().status.value == "healthy"
    restarted_frontier = DeliveryFrontier.model_validate_json(local_frontier_path.read_bytes(), strict=True)
    restarted_binding = next(item for item in restarted_frontier.bindings if item.outcome_id == "OUT-001")
    assert restarted_binding == active_binding
    assert restarted_binding.active_claim == resumed.claim
    assert restarted_binding.builder_handoff_context == handoff_context
    assert (
        active_restart.show_build_context(
            change_id,
            resumed.outcome_id,
            resumed.claim.attempt_id,
            resumed.claim.claim_id,
        ).task.task_id
        == launch.task_id
    )
    assert _workspace_git_state(fresh, resumed.worktree_path) == active_git_state
    assert settlement_receipt_path.read_bytes() == settlement_receipt_bytes
    assert resolution_receipt_path.read_bytes() == resolution_receipt_bytes
    assert_remote_snapshot_unchanged()

    reachable_objects = _git(fresh, "rev-list", "--objects", "--all").splitlines()
    reachable_object_ids = {item.split(maxsplit=1)[0] for item in reachable_objects}
    reachable_object_text = "\n".join(reachable_objects)
    for artifact_path in (
        local_frontier_path,
        settlement_receipt_path,
        resolution_receipt_path,
        coordination_path,
    ):
        assert artifact_path.relative_to(fresh).as_posix() not in reachable_object_text
        artifact_object_id = (
            subprocess.run(  # noqa: S603 - fixed Git executable and argument vector.
                (_GIT, "-C", str(fresh), "hash-object", "--stdin"),
                check=True,
                capture_output=True,
                input=artifact_path.read_bytes(),
            )
            .stdout.decode()
            .strip()
        )
        assert artifact_object_id not in reachable_object_ids
    index_object_id = (
        subprocess.run(  # noqa: S603 - fixed Git executable and argument vector.
            (_GIT, "-C", str(fresh), "hash-object", "--stdin"),
            check=True,
            capture_output=True,
            input=active_git_state[-1],
        )
        .stdout.decode()
        .strip()
    )
    assert index_object_id not in reachable_object_ids


def test_delivery_state_snapshot_repair_reconciles_confirmed_block_successor(tmp_path: Path) -> None:
    repository, remote, _initial = _repository(tmp_path)
    _git(repository, "config", "url." + str(remote) + ".insteadOf", "https://github.com/example/project.git")
    _git(repository, "remote", "set-url", "origin", "https://github.com/example/project.git")
    change_id = "repair-state"
    contract, intent, design = _contract(change_id)
    runtime_root = repository / ".owlbear/delivery/runtime"
    package_root = repository / ".owlbear/delivery/packages"
    worktree_root = repository / ".owlbear/delivery/worktrees"
    package_store = DesignPackageStore(package_root, repository, transaction_root=runtime_root)
    package = package_store.create(change_id, intent, design)
    contract_bytes = (
        json.dumps(contract.model_dump(mode="json"), sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()
    package_store.publish_contract(change_id, package.package_id, contract_bytes, lambda *_content: None)
    package = package_store.read_verified(change_id)
    (runtime_root / "changes" / change_id).mkdir(parents=True, exist_ok=True)
    (runtime_root / "changes" / change_id / "contract.json").write_bytes(contract_bytes)
    coordinator = PortfolioCoordinator(runtime_root)
    manager = ChangeWorkspaceManager(repository, worktree_root, coordinator, "main", "origin")
    coordination = manager.ensure(change_id)
    frontier_path = runtime_root / "changes" / change_id / "frontier.json"
    frontier_path.parent.mkdir(parents=True, exist_ok=True)
    frontier = DeliveryFrontier(bindings=(OutcomeAuthorityBinding(outcome_id="OUT-001", plan_scope_id="SCOPE-001"),))
    frontier_path.write_bytes(
        (json.dumps(frontier.model_dump(mode="json"), sort_keys=True, separators=(",", ":")) + "\n").encode()
    )
    runtime = DeliveryRuntime(runtime_root, contract, workspace_manager=manager)
    (runtime_root / "changes" / change_id / "admission.json").write_bytes(
        _canonical_payload(_admission(runtime, manager, change_id).model_dump(mode="json"))
    )
    snapshot = manager.snapshot_design_package(
        change_id,
        package.package_id,
        {
            "authority.json": package.authority_bytes,
            "design.md": package.design_bytes,
            "intent.md": package.intent_bytes,
            "manifest.json": package.manifest.canonical_bytes(),
        },
        "repair-state-package",
    )
    _git(repository, "push", "origin", f"{snapshot.snapshot_head}:refs/heads/{coordination.branch}")
    publisher = DeliveryStatePublisher(repository, remote="origin", state_branch="owlbear/delivery-state")
    publisher.publish(
        change_id=change_id,
        package_id=package.package_id,
        coordination=manager.show(change_id),
        runtime=runtime,
        admission=_admission(runtime, manager, change_id),
        operation_id="repair-state-initial",
        captured_at=datetime(2026, 8, 23, tzinfo=UTC),
    )
    config = DeliveryStartupConfig(
        schema_version=2,
        remote="origin",
        target_branch="main",
        github_repository="example/project",
        delivery_state_branch="owlbear/delivery-state",
    )
    local_block = DeliveryBlock(
        block_id="repair-block",
        reason="The planner reviewer was unavailable.",
        unblock_condition="The reviewer is dispatchable.",
        expected_evidence=("Reviewer dispatch evidence",),
        locators=("planner-challenger",),
    )
    local_frontier = frontier.model_copy(
        update={"bindings": (frontier.bindings[0].model_copy(update={"block": local_block}),)}
    )
    frontier_path.write_bytes(
        (json.dumps(local_frontier.model_dump(mode="json"), sort_keys=True, separators=(",", ":")) + "\n").encode()
    )
    (runtime_root / "format.json").write_bytes(format_marker_bytes())

    degraded = load_delivery_application(config, workspace_root=repository)
    assert degraded.delivery_health().status.value == "attention"
    repaired = degraded.repair_delivery_state_snapshot(
        change_id,
        "repair-state-operation",
        confirmed_repair=True,
    )

    assert repaired.change_id == change_id
    assert degraded.delivery_health().status.value == "healthy"

    restarted = load_delivery_application(config, workspace_root=repository)
    assert restarted.delivery_health().status.value == "healthy"
    assert restarted.show_operator_context(change_id, "OUT-001").block == local_block


def _migrate_local_legacy_frontier(
    repository: Path, config: DeliveryStartupConfig, change_id: str, legacy_frontier: bytes
) -> bytes:
    """Write a legacy local frontier, see it refused, then run the fenced migration and return the result."""
    frontier_path = repository / ".owlbear/delivery/runtime/changes" / change_id / "frontier.json"
    frontier_path.write_bytes(legacy_frontier)
    with pytest.raises(DeliveryStateVersionError) as refusal:
        load_delivery_application(config, workspace_root=repository)
    assert refusal.value.code == "state-migration-required"
    (repository / ".owlbear/delivery/config.json").write_text(config.model_dump_json(), encoding="utf-8")
    proposal = state_migration.propose(repository)
    assert [entry.locator for entry in proposal.entries] == [
        f"runtime/changes/{change_id}/frontier.json",
        "runtime/format.json",
    ]
    state_migration.apply(repository, proposal.migration_id)
    state_migration.verify(repository, proposal.migration_id)
    migrated = frontier_path.read_bytes()
    assert json.loads(migrated)["schema_version"] == 18
    return migrated


def test_loader_reconciles_a_legacy_local_frontier_with_its_legacy_remote_snapshot(tmp_path: Path) -> None:
    repository, remote, _initial = _repository(tmp_path)
    _git(repository, "config", "url." + str(remote) + ".insteadOf", "https://github.com/example/project.git")
    _git(repository, "remote", "set-url", "origin", "https://github.com/example/project.git")
    change_id = "legacy-reconcile"
    contract, intent, design = _contract(change_id)
    runtime_root = repository / ".owlbear/delivery/runtime"
    package_store = DesignPackageStore(
        repository / ".owlbear/delivery/packages", repository, transaction_root=runtime_root
    )
    package = package_store.create(change_id, intent, design)
    contract_bytes = _canonical_payload(contract.model_dump(mode="json"))
    package_store.publish_contract(change_id, package.package_id, contract_bytes, lambda *_content: None)
    package = package_store.read_verified(change_id)
    change_root = runtime_root / "changes" / change_id
    change_root.mkdir(parents=True)
    (change_root / "contract.json").write_bytes(contract_bytes)
    manager = ChangeWorkspaceManager(
        repository, repository / ".owlbear/delivery/worktrees", PortfolioCoordinator(runtime_root), "main", "origin"
    )
    coordination = manager.ensure(change_id)
    frontier = DeliveryFrontier(bindings=(OutcomeAuthorityBinding(outcome_id="OUT-001", plan_scope_id="SCOPE-001"),))
    frontier_path = change_root / "frontier.json"
    frontier_path.write_bytes(_canonical_payload(frontier.model_dump(mode="json")))
    runtime = DeliveryRuntime(runtime_root, contract, workspace_manager=manager)
    package_snapshot = manager.snapshot_design_package(
        change_id,
        package.package_id,
        {
            "authority.json": package.authority_bytes,
            "design.md": package.design_bytes,
            "intent.md": package.intent_bytes,
            "manifest.json": package.manifest.canonical_bytes(),
        },
        "legacy-reconcile-package",
    )
    _git(repository, "push", "origin", f"{package_snapshot.snapshot_head}:refs/heads/{coordination.branch}")
    admission = _admission(runtime, manager, change_id)
    (change_root / "admission.json").write_bytes(_canonical_payload(admission.model_dump(mode="json")))
    publisher = DeliveryStatePublisher(repository, remote="origin", state_branch="owlbear/delivery-state")
    published = publisher.publish(
        change_id=change_id,
        package_id=package.package_id,
        coordination=manager.show(change_id),
        runtime=runtime,
        admission=admission,
        operation_id="legacy-reconcile-initial",
        captured_at=datetime(2026, 8, 23, tzinfo=UTC),
    )
    snapshot_path = f".owlbear/delivery/state/{change_id}/snapshot.json"
    legacy = json.loads(publisher._git_blob(published.published_head, snapshot_path))  # noqa: SLF001
    legacy.pop("migrated_from_snapshot_id")
    legacy.pop("repaired_predecessor_digest")
    legacy["schema_version"] = 1
    legacy["frontier"]["schema_version"] = 17
    for binding in legacy["frontier"]["bindings"]:
        binding.pop("retry_count")
        binding.pop("retry_fingerprint")
    legacy["snapshot_id"] = ""
    legacy["snapshot_id"] = hashlib.sha256(_canonical_payload(legacy)).hexdigest()
    legacy_head = _commit_corrupt_snapshot(repository, published.published_head, change_id, _canonical_payload(legacy))
    _git(repository, "push", "origin", f"{legacy_head}:refs/heads/owlbear/delivery-state", "--force")
    config = DeliveryStartupConfig(
        schema_version=2,
        remote="origin",
        target_branch="main",
        github_repository="example/project",
        delivery_state_branch="owlbear/delivery-state",
    )

    def remote_state_reasons() -> list[DeliveryHealthReason]:
        health = load_delivery_application(config, workspace_root=repository).delivery_health()
        return [item.reason for item in health.diagnostics if item.source == "remote-state"]

    # A local schema-17 frontier needs the registered fenced rewrite before any controller reads it (N02-B).
    migrated = _migrate_local_legacy_frontier(repository, config, change_id, _canonical_payload(legacy["frontier"]))
    assert remote_state_reasons() == []

    diverged = json.loads(migrated)
    diverged["bindings"][0]["plan_scope_id"] = "SCOPE-002"
    frontier_path.write_bytes(_canonical_payload(diverged))
    assert remote_state_reasons() == [DeliveryHealthReason.LOCAL_FRONTIER_MISMATCH]

    frontier_path.write_bytes(migrated)
    assert remote_state_reasons() == []
    assert _git(remote, "rev-parse", "refs/heads/owlbear/delivery-state") == legacy_head


def test_target_sync_state_snapshot_is_restartable_after_branch_publication(tmp_path: Path) -> None:
    repository, remote, _initial = _repository(tmp_path)
    change_id = "state-target-sync"
    contract, intent, design = _contract(change_id)
    state_root = tmp_path / "state"
    package_root = repository / ".owlbear/delivery/packages"
    package_store = DesignPackageStore(package_root, repository)
    package = package_store.create(change_id, intent, design)
    contract_bytes = (
        json.dumps(contract.model_dump(mode="json"), sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()
    package_store.publish_contract(change_id, package.package_id, contract_bytes, lambda *_content: None)
    package = package_store.read_verified(change_id)
    coordinator = PortfolioCoordinator(state_root)
    manager = ChangeWorkspaceManager(repository, tmp_path / "worktrees", coordinator, "main", "origin")
    manager.ensure(change_id)
    frontier_path = state_root / "changes" / change_id / "frontier.json"
    frontier_path.parent.mkdir(parents=True, exist_ok=True)
    frontier = DeliveryFrontier(bindings=(OutcomeAuthorityBinding(outcome_id="OUT-001", plan_scope_id="SCOPE-001"),))
    frontier_path.write_bytes(
        (json.dumps(frontier.model_dump(mode="json"), sort_keys=True, separators=(",", ":")) + "\n").encode()
    )
    runtime = DeliveryRuntime(state_root, contract, workspace_manager=manager)
    snapshot = manager.snapshot_design_package(
        change_id,
        package.package_id,
        {
            "authority.json": package.authority_bytes,
            "design.md": package.design_bytes,
            "intent.md": package.intent_bytes,
            "manifest.json": package.manifest.canonical_bytes(),
        },
        "target-sync-package",
    )
    branch_publisher = ChangeBranchPublisher(
        repository,
        coordinator,
        remote="origin",
        target_branch="main",
        operation_root=state_root / "publications/change-branches/operations",
    )
    branch_publisher.publish(
        PublishChangeBranch(
            change_id=change_id,
            expected_remote_head=None,
            expected_published_head=snapshot.snapshot_head,
            operation_id="target-sync-initial-branch",
        )
    )

    target_repository = tmp_path / "target-repository"
    _git(tmp_path, "clone", str(remote), str(target_repository))
    _git(target_repository, "config", "user.name", "Target User")
    _git(target_repository, "config", "user.email", "target@example.invalid")
    (target_repository / "target.txt").write_text("target\n", encoding="utf-8")
    _git(target_repository, "add", "target.txt")
    _git(target_repository, "commit", "-m", "advance target")
    target_head = _git(target_repository, "rev-parse", "HEAD")
    _git(target_repository, "push", "origin", "HEAD:refs/heads/main")

    sync_receipt = manager.sync_with_target(
        SyncChangeWithTarget(
            change_id=change_id,
            expected_target=target_head,
            operation_id="target-sync-restart",
        )
    )
    runtime.record_target_sync(sync_receipt, datetime(2026, 8, 23, tzinfo=UTC))
    checkpoint = runtime.checkpoint_publication_state()
    branch_publisher.publish(
        PublishChangeBranch(
            change_id=change_id,
            expected_remote_head=snapshot.snapshot_head,
            expected_published_head=sync_receipt.merged_head,
            operation_id="target-sync-restart-branch",
        )
    )
    runtime.record_checkpoint_branch_publication(checkpoint, sync_receipt.merged_head)
    state_publisher = DeliveryStatePublisher(repository, remote="origin", state_branch="owlbear/delivery-state")
    state_receipt = state_publisher.publish(
        change_id=change_id,
        package_id=package.package_id,
        coordination=manager.show(change_id),
        runtime=runtime,
        admission=_admission(runtime, manager, change_id),
        operation_id="target-sync-restart-state",
        captured_at=datetime(2026, 8, 23, tzinfo=UTC),
    )

    fresh = tmp_path / "fresh-target-sync"
    _git(tmp_path, "clone", str(remote), str(fresh))
    _git(fresh, "config", "url." + str(remote) + ".insteadOf", "https://github.com/example/project.git")
    _git(fresh, "remote", "set-url", "origin", "https://github.com/example/project.git")
    config = DeliveryStartupConfig(
        schema_version=2,
        remote="origin",
        target_branch="main",
        github_repository="example/project",
        delivery_state_branch="owlbear/delivery-state",
    )
    application = load_delivery_application(config, workspace_root=fresh)

    assert application.delivery_health().status.value == "healthy"
    assert application.list_work_items()
    assert _git(fresh, "rev-parse", f"refs/heads/owlbear/change/{change_id}") == sync_receipt.merged_head
    assert state_receipt.published_head == _git(fresh, "rev-parse", "refs/remotes/origin/owlbear/delivery-state")
    assert application.show_finalization_context(change_id).ready_for_finalization is False


class _Crash(BaseException):
    """A process death at one durable boundary; product handlers never catch it."""


def _revision_sources(second: str) -> bytes:
    blocks = (
        "kind: commitment\nid: COM-001\nclass: agreed-path\nprovenance: restart test\nstatement: Keep launches.",
        (
            "kind: outcome\nid: OUT-001\ntitle: Launch\npromise: Make the launch observable.\n"
            f'acceptance: ["AC-001: The launch is observable.", "{second}"]\ncommitments: [COM-001]\ndependencies: []'
        ),
    )
    return (
        "# Revision restart\n\n" + "".join(f"```yaml target-contract\n{block}\n```\n\n" for block in blocks)
    ).encode()


def _published_paused_revision(tmp_path: Path) -> tuple[PortfolioApplication, DeliveryStartupConfig, Path, object, str]:
    """Admit, publish and Pause one Change through the default loader, then revise its package."""
    repository, remote, _initial = _repository(tmp_path)
    _git(repository, "config", "url." + str(remote) + ".insteadOf", "https://github.com/example/project.git")
    _git(repository, "remote", "set-url", "origin", "https://github.com/example/project.git")
    config = DeliveryStartupConfig(
        schema_version=2,
        remote="origin",
        target_branch="main",
        github_repository="example/project",
        delivery_state_branch="owlbear/delivery-state",
    )
    application = load_delivery_application(config, workspace_root=repository)
    change_id = "revision-restart"

    def authored_id() -> str:
        package = application.read_design_session(change_id)
        manifest = DesignPackageManifest.from_content(change_id, package.intent_bytes, package.design_bytes)
        return hashlib.sha256(manifest.canonical_bytes()).hexdigest()

    application.create_design_session(change_id, _revision_sources("AC-002: Retained."), b"# Architecture\n")
    application.admit_delivery_change(
        DeliveryAdmissionRequest(change_id=change_id, expected_package_id=authored_id(), active_claim_ids=())
    )
    runtime = application._runtimes[change_id]  # noqa: SLF001
    application._publish_delivery_state(change_id, runtime, "revision-restart-first-state")  # noqa: SLF001
    application.set_change_intent(
        DeliveryChangeIntent(
            change_id=change_id,
            kind=DeliveryChangeIntentKind.DEFER,
            expected_frontier_digest=hashlib.sha256(runtime.frontier_bytes()).hexdigest(),
            reason="Revise requirements",
        )
    )
    assert runtime.change_deferral() is not None
    assert runtime.pending_state_publication() is None
    current = application.read_design_session(change_id)
    application.revise_design_session(
        change_id, current.package_id, _revision_sources("AC-002: Revised."), b"# Architecture\n"
    )
    coordination = application._coordinator.show(change_id)  # noqa: SLF001
    request = DeliveryAdmissionRequest(
        change_id=change_id,
        expected_package_id=authored_id(),
        active_claim_ids=(),
        expected_frontier_digest=hashlib.sha256(runtime.frontier_bytes()).hexdigest(),
        expected_design_package_snapshot_receipt_id=coordination.design_package_snapshot.receipt_id,
    )
    return application, config, repository, request, coordination.last_reviewed_commit


@pytest.mark.parametrize(
    "boundary",
    [
        "after-contract",
        "staged",
        "committed",
        "after-snapshot",
        "after-activation",
        "branch-pushed",
        "branch-recorded",
        "state-pushed",
    ],
)
def test_revision_activation_crash_reloads_and_replays_to_one_snapshot(tmp_path: Path, boundary: str) -> None:
    application, config, repository, request, reviewed = _published_paused_revision(tmp_path)
    manager = application._workspace_manager  # noqa: SLF001
    run_git = manager._run_git  # noqa: SLF001

    def crash_before_snapshot_commit(*arguments: str, **options: object) -> object:
        if arguments[:2] == ("commit", "--only"):
            raise _Crash
        return run_git(*arguments, **options)

    crash = {
        "after-contract": patch.object(manager, "snapshot_design_package", side_effect=_Crash),
        "staged": patch.object(manager, "_run_git", side_effect=crash_before_snapshot_commit),
        "committed": patch.object(ChangeDesignPackageSnapshotReceipt, "create", side_effect=_Crash),
        "after-snapshot": patch("owlbear_delivery.delivery_admission._delivery_frontier", side_effect=_Crash),
        "after-activation": patch.object(application, "_publish_delivery_state", side_effect=_Crash),
        "branch-pushed": patch.object(DeliveryRuntime, "record_checkpoint_branch_publication", side_effect=_Crash),
        "branch-recorded": patch.object(DeliveryStatePublisher, "publish", side_effect=_Crash),
        "state-pushed": patch.object(DeliveryRuntime, "acknowledge_pending_publication", side_effect=_Crash),
    }[boundary]
    with crash, pytest.raises(_Crash):
        application.admit_change(request)
    close_delivery_application(application)

    restarted = load_delivery_application(config, workspace_root=repository)
    health = restarted.delivery_health()
    assert {diagnostic.code for diagnostic in health.diagnostics} <= {"state-publication-pending"}, health
    replayed = restarted.admit_change(request)
    restarted.acquire_frontier_work()

    head = restarted._coordinator.show(request.change_id).last_reviewed_commit  # noqa: SLF001
    runtime = restarted._runtimes[request.change_id]  # noqa: SLF001
    assert replayed.replayed is True
    assert replayed.frontier.change_deferral is None
    assert _git(repository, "rev-list", "--parents", "-n", "1", head).split()[1:] == [reviewed]
    assert runtime.pending_state_publication() is None
    assert restarted.delivery_health().status.value == "healthy"
    close_delivery_application(restarted)


@pytest.mark.parametrize("staged", [False, True])
def test_revision_snapshot_replay_refuses_package_edits_made_after_interruption(
    tmp_path: Path,
    staged: bool,  # noqa: FBT001 - pytest parameter.
) -> None:
    application, config, repository, request, _reviewed = _published_paused_revision(tmp_path)
    manager = application._workspace_manager  # noqa: SLF001
    run_git = manager._run_git  # noqa: SLF001

    def crash_before_snapshot_commit(*arguments: str, **options: object) -> object:
        if arguments[:2] == ("commit", "--only"):
            raise _Crash
        return run_git(*arguments, **options)

    with patch.object(manager, "_run_git", side_effect=crash_before_snapshot_commit), pytest.raises(_Crash):
        application.admit_change(request)
    worktree = application._coordinator.show(request.change_id).worktree_path  # noqa: SLF001
    close_delivery_application(application)
    relative = f".owlbear/delivery/packages/{request.change_id}/design.md"
    (worktree / relative).write_bytes(b"# Designer edit\n")
    if staged:
        _git(worktree, "add", "-f", relative)

    restarted = load_delivery_application(config, workspace_root=repository)
    with pytest.raises(DesignPackageSnapshotEditedError) as refused:
        restarted.admit_change(request)

    assert refused.value.paths == (relative,)
    assert (worktree / relative).read_bytes() == b"# Designer edit\n"
    assert (_git(worktree, "show", f":{relative}") == "# Designer edit") is staged
    close_delivery_application(restarted)


def test_non_ascii_first_admission_replays_after_restart_and_publishes(tmp_path: Path) -> None:
    repository, remote, _initial = _repository(tmp_path)
    _git(repository, "config", "url." + str(remote) + ".insteadOf", "https://github.com/example/project.git")
    _git(repository, "remote", "set-url", "origin", "https://github.com/example/project.git")
    config = DeliveryStartupConfig(
        schema_version=2,
        remote="origin",
        target_branch="main",
        github_repository="example/project",
        delivery_state_branch="owlbear/delivery-state",
    )
    application = load_delivery_application(config, workspace_root=repository)
    change_id = "slug-rules"
    sources = _revision_sources("AC-002: Straße → strasse, Café → cafe.")
    application.create_design_session(change_id, sources, b"# Architecture\n")
    request = DeliveryAdmissionRequest(
        change_id=change_id, expected_package_id=_authored_package_id(application, change_id), active_claim_ids=()
    )
    # N10-H: the package authority check refused after the admission authority was written.
    with patch.object(application, "_validate_package_authority", side_effect=_Crash), pytest.raises(_Crash):
        application.admit_change(request)
    assert application._coordinator.show(change_id).design_package_snapshot is None  # noqa: SLF001
    close_delivery_application(application)

    restarted = load_delivery_application(config, workspace_root=repository)
    assert restarted.admit_change(request).replayed is True
    assert not restarted.read_design_session(change_id).authority_bytes.isascii()
    runtime = restarted._runtimes[change_id]  # noqa: SLF001
    restarted._publish_delivery_state(change_id, runtime, "non-ascii-first-state")  # noqa: SLF001
    assert runtime.pending_state_publication() is None
    close_delivery_application(restarted)

    reloaded = load_delivery_application(config, workspace_root=repository)
    health = reloaded.delivery_health()
    assert health.status.value == "healthy", health.model_dump_json()
    assert reloaded._coordinator.show(change_id).design_package_snapshot is not None  # noqa: SLF001
    close_delivery_application(reloaded)


def _authored_package_id(application: PortfolioApplication, change_id: str) -> str:
    package = application.read_design_session(change_id)
    manifest = DesignPackageManifest.from_content(change_id, package.intent_bytes, package.design_bytes)
    return hashlib.sha256(manifest.canonical_bytes()).hexdigest()


def _published_design_return(
    tmp_path: Path, variant: str = "mixed"
) -> tuple[PortfolioApplication, DeliveryStartupConfig, Path, object, str]:
    """Publish one authored Change, return its Builder to Design with committed and ``variant`` work, then Pause it.

    ``mixed``: staged, unstaged and untracked; ``staged-only``: staged bytes over unchanged worktree bytes (plus an
    untracked file in ``staged-only-untracked``).
    """
    repository, remote, _initial = _repository(tmp_path)
    _git(repository, "config", "url." + str(remote) + ".insteadOf", "https://github.com/example/project.git")
    _git(repository, "remote", "set-url", "origin", "https://github.com/example/project.git")
    config = DeliveryStartupConfig(
        schema_version=2,
        remote="origin",
        target_branch="main",
        github_repository="example/project",
        delivery_state_branch="owlbear/delivery-state",
    )
    application = load_delivery_application(config, workspace_root=repository)
    change_id = "design-return"
    application.create_design_session(change_id, _revision_sources("AC-002: Retained."), b"# Architecture\n")
    admitted = application.admit_delivery_change(
        DeliveryAdmissionRequest(
            change_id=change_id, expected_package_id=_authored_package_id(application, change_id), active_claim_ids=()
        )
    )
    runtime = application._runtimes[change_id]  # noqa: SLF001
    application._publish_delivery_state(change_id, runtime, "design-return-first-state")  # noqa: SLF001
    task = DeliveryTaskDefinition(
        task_id="TASK-001",
        outcome_id="OUT-001",
        plan_scope_id=admitted.frontier.bindings[0].plan_scope_id,
        title="Implement the launch",
        result="Make the launch observable.",
        commitment_ids=("COM-001",),
        dependency_ids=(),
        required_outputs=("Launch implementation",),
        maintained_surfaces=("serve/delivery",),
        constraints=("Use the reviewed branch.",),
        exclusions=("Do not rewrite target history.",),
        acceptance_observations=("The launch is observable.",),
        proof_boundaries=("DeliveryRuntime.transition",),
    )
    # Seed the planned outcome through the runtime writer so its publication marker stays exact.
    frontier = DeliveryFrontier.model_validate_json(runtime.frontier_bytes(), strict=True)
    seeded = frontier.model_copy(
        update={
            "bindings": (
                frontier.bindings[0].model_copy(update={"stage": DeliveryStage.IMPLEMENTATION, "tasks": (task,)}),
            ),
            "pending_checkpoint": None,
            "published_head": application._coordinator.show(change_id).last_reviewed_commit,  # noqa: SLF001
        }
    )
    runtime._replace_content(runtime.frontier_bytes(), _model_content(seeded))  # noqa: SLF001
    application._publish_delivery_state(change_id, runtime, "design-return-seeded-state")  # noqa: SLF001
    assert runtime.pending_state_publication() is None
    builder = application.acquire_frontier_work().launch_packages[0]
    worktree = builder.worktree_path
    (worktree / "committed.txt").write_text("committed Builder bytes\n", encoding="utf-8")
    _git(worktree, "add", "committed.txt")
    _git(worktree, "commit", "-m", "Builder work")
    branch_head = _git(worktree, "rev-parse", "HEAD")
    if variant == "mixed":
        (worktree / "staged.txt").write_text("staged Builder bytes\n", encoding="utf-8")
        _git(worktree, "add", "staged.txt")
        (worktree / "staged.txt").write_text("unstaged Builder bytes\n", encoding="utf-8")
    if variant.startswith("staged-only"):
        (worktree / "product.txt").write_text("staged Builder bytes\n", encoding="utf-8")
        _git(worktree, "add", "product.txt")
        (worktree / "product.txt").write_text("baseline\n", encoding="utf-8")
    if variant != "staged-only":
        (worktree / "untracked.txt").write_text("untracked Builder bytes\n", encoding="utf-8")
    application.settle_worker_invocation(
        DeliveryBuilderInvocationSettlement(
            change_id=change_id,
            outcome_id="OUT-001",
            claim_id=builder.claim.claim_id,
            attempt_id=builder.claim.attempt_id,
            task_id=builder.task_id,
            expected_last_reviewed_commit=builder.last_reviewed_commit,
            disposition="normal-return",
            request=ReturnDelivery(
                action="return",
                outcome_id="OUT-001",
                claim_id=builder.claim.claim_id,
                target=DeliveryStage.DESIGN,
                reason="The admitted Design lacks the launch premise.",
                locators=("design.md",),
                preserved_commit=branch_head,
                attempt_id=builder.claim.attempt_id,
            ),
        ),
        host_id=builder.claim.owner_id,
        session_id=builder.claim.process_id,
    )
    application.set_change_intent(
        DeliveryChangeIntent(
            change_id=change_id,
            kind=DeliveryChangeIntentKind.DEFER,
            expected_frontier_digest=hashlib.sha256(runtime.frontier_bytes()).hexdigest(),
            reason="Revise requirements",
        )
    )
    assert runtime.change_deferral() is not None
    return application, config, repository, builder, branch_head


@pytest.mark.parametrize(
    ("variant", "boundary"),
    [
        *(("mixed", boundary) for boundary in (None, "before-quarantine-ref", "before-receipt")),
        *(("mixed", boundary) for boundary in ("after-capture", "after-reset", "before-release")),
        ("staged-only", None),
        ("staged-only-untracked", "before-receipt"),
    ],
)
def test_design_return_readmission_preserves_builder_work_across_restart(
    tmp_path: Path, variant: str, boundary: str | None
) -> None:
    application, config, repository, builder, branch_head = _published_design_return(tmp_path, variant)
    change_id, worktree, attempt_id = builder.change_id, builder.worktree_path, builder.claim.attempt_id
    revised = _revision_sources("AC-002: Revised.")
    if boundary is not None:
        with _design_return_crash(application, boundary), pytest.raises(_Crash):
            application.revise_design_session(
                change_id, application.read_design_session(change_id).package_id, revised, b"# Architecture\n"
            )
        close_delivery_application(application)
        application = load_delivery_application(config, workspace_root=repository)
        health = application.delivery_health()
        assert health.status.value == "healthy", health

    application.revise_design_session(
        change_id, application.read_design_session(change_id).package_id, revised, b"# Architecture\n"
    )

    runtime = application._runtimes[change_id]  # noqa: SLF001
    coordination = application._coordinator.show(change_id)  # noqa: SLF001
    released = runtime.show_binding("OUT-001")
    assert (released.stage, released.tasks, released.results) == (DeliveryStage.DESIGN, (), ())
    assert released.builder_handoff_context is None
    assert released.return_context is not None
    assert released.return_context.preserved_commit == branch_head
    assert (coordination.writer, coordination.builder_handoff) == (None, None)
    assert runtime.pending_state_publication() is None
    assert _git(worktree, "rev-parse", "HEAD") == builder.last_reviewed_commit
    assert _git(worktree, "status", "--porcelain", "--untracked-files=all") == ""
    attempt, index, quarantine = (
        f"refs/owlbear/{kind}/{change_id}/{attempt_id}" for kind in ("attempts", "quarantine-index", "quarantine")
    )
    assert _git(repository, "rev-parse", attempt) == branch_head
    assert _git(repository, "show", f"{attempt}:committed.txt") == "committed Builder bytes"
    if variant == "mixed":
        assert _git(repository, "show", f"{index}:staged.txt") == "staged Builder bytes"
        assert _git(repository, "show", f"{quarantine}:staged.txt") == "unstaged Builder bytes"
    else:
        assert _git(repository, "show", f"{index}:product.txt") == "staged Builder bytes"
    if variant != "staged-only":
        assert _git(repository, "show", f"{quarantine}:untracked.txt") == "untracked Builder bytes"
    close_delivery_application(application)
    application = load_delivery_application(config, workspace_root=repository)
    health = application.delivery_health()
    assert health.status.value == "healthy", health
    runtime = application._runtimes[change_id]  # noqa: SLF001

    activated = application.admit_change(
        DeliveryAdmissionRequest(
            change_id=change_id,
            expected_package_id=_authored_package_id(application, change_id),
            active_claim_ids=(),
            expected_frontier_digest=hashlib.sha256(runtime.frontier_bytes()).hexdigest(),
            expected_design_package_snapshot_receipt_id=coordination.design_package_snapshot.receipt_id,
        )
    )

    replanned = activated.frontier.bindings[0]
    assert replanned.stage is DeliveryStage.PLANNING
    assert replanned.return_context is not None
    assert replanned.return_context.preserved_commit == branch_head
    launches = application.acquire_frontier_work().launch_packages
    assert [(launch.outcome_id, launch.claim.worker_role) for launch in launches] == [
        ("OUT-001", DeliveryWorkerRole.PLANNER)
    ]
    close_delivery_application(application)


def _design_return_crash(application: PortfolioApplication, boundary: str) -> object:
    manager = application._workspace_manager  # noqa: SLF001
    run_git = manager._run_git  # noqa: SLF001

    def crash_at(command: tuple[str, ...]) -> object:
        def run(*arguments: str, **options: object) -> object:
            if arguments[: len(command)] == command:
                raise _Crash
            return run_git(*arguments, **options)

        return patch.object(manager, "_run_git", side_effect=run)

    return {
        "before-quarantine-ref": crash_at(("commit-tree",)),
        "before-receipt": patch.object(DirtyWorktreeQuarantineReceipt, "create", side_effect=_Crash),
        "after-capture": crash_at(("-c", "submodule.recurse=false", "reset", "--hard")),
        "after-reset": crash_at(("clean",)),
        "before-release": patch.object(PortfolioCoordinator, "_prepare_design_return_release", side_effect=_Crash),
    }[boundary]


def _revise_design_return(application: PortfolioApplication, change_id: str) -> object:
    package_id = application.read_design_session(change_id).package_id
    return application.revise_design_session(
        change_id, package_id, _revision_sources("AC-002: Revised."), b"# Architecture\n"
    )


def _design_return_custody(application: PortfolioApplication, repository: Path, worktree: Path) -> tuple[object, ...]:
    change_id = "design-return"
    return (
        _git(worktree, "ls-files", "--stage"),
        _git(repository, "for-each-ref", "refs/owlbear"),
        application._coordinator.show(change_id),  # noqa: SLF001
        application._runtimes[change_id].frontier_bytes(),  # noqa: SLF001
    )


def test_design_return_replay_refuses_an_index_restaged_after_capture(tmp_path: Path) -> None:
    application, config, repository, builder, _branch_head = _published_design_return(tmp_path)
    change_id, worktree = builder.change_id, builder.worktree_path
    with _design_return_crash(application, "after-capture"), pytest.raises(_Crash):
        _revise_design_return(application, change_id)
    (worktree / "staged.txt").write_text("restaged bytes\n", encoding="utf-8")
    _git(worktree, "add", "staged.txt")
    (worktree / "staged.txt").write_text("unstaged Builder bytes\n", encoding="utf-8")
    close_delivery_application(application)
    application = load_delivery_application(config, workspace_root=repository)
    health = application.delivery_health()
    changed = "the Design-return worktree differs from its handoff or capture"
    assert [(item.change_id, item.detail) for item in health.diagnostics] == [(change_id, changed)]
    before = _design_return_custody(application, repository, worktree)

    with pytest.raises(DeliveryRevisionError, match="design-return-workspace-changed"):
        _revise_design_return(application, change_id)

    assert _design_return_custody(application, repository, worktree) == before
    assert _git(worktree, "show", ":staged.txt") == "restaged bytes"
    close_delivery_application(application)


def test_design_return_revision_waits_for_its_release_publication(tmp_path: Path) -> None:
    application, config, repository, builder, branch_head = _published_design_return(tmp_path)
    change_id = builder.change_id

    def package() -> tuple[str, bytes]:
        current = application.read_design_session(change_id)
        return current.package_id, current.authority_bytes

    before = package()
    unavailable = patch.object(DeliveryStatePublisher, "publish", side_effect=RuntimeError("provider unavailable"))
    with unavailable, pytest.raises(DeliveryRevisionError, match="publication-pending"):
        _revise_design_return(application, change_id)
    runtime = application._runtimes[change_id]  # noqa: SLF001
    assert runtime.show_binding("OUT-001").builder_handoff_context is None
    assert runtime.pending_state_publication() is not None
    assert package() == before
    close_delivery_application(application)
    with unavailable:
        application = load_delivery_application(config, workspace_root=repository)
        with pytest.raises(DeliveryRevisionError, match="publication-pending"):
            _revise_design_return(application, change_id)
    assert package() == before

    _revise_design_return(application, change_id)

    runtime = application._runtimes[change_id]  # noqa: SLF001
    assert runtime.pending_state_publication() is None
    coordination = application._coordinator.show(change_id)  # noqa: SLF001
    activated = application.admit_change(
        DeliveryAdmissionRequest(
            change_id=change_id,
            expected_package_id=_authored_package_id(application, change_id),
            active_claim_ids=(),
            expected_frontier_digest=hashlib.sha256(runtime.frontier_bytes()).hexdigest(),
            expected_design_package_snapshot_receipt_id=coordination.design_package_snapshot.receipt_id,
        )
    )
    assert activated.frontier.bindings[0].return_context.preserved_commit == branch_head
    assert [launch.outcome_id for launch in application.acquire_frontier_work().launch_packages] == ["OUT-001"]
    close_delivery_application(application)
