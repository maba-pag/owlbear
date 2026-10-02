"""Route-level contracts for the Delivery Cockpit application."""

from __future__ import annotations

import json
import subprocess
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import cast
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient
from serve.delivery.tests.test_portfolio_application import (
    _assert_checkpoint_branch_operation,
    _assert_loader_observation_only,
    _assert_loader_retry_recording,
    _canonical,
    _engine_action,
    _failure_request,
    _git,
    _loader_activation_state_snapshot,
    _loader_composed_engine_fixture,
    _loader_engine_state_snapshot,
    _loader_registered_engine_action_fixture,
    _make_provider_readback_unavailable,
    _seed_loader_composed_completed_change,
    _startup_config,
    _workspace_mutation_snapshot,
    acceptance_budget_case,
    builder_transition_case,
)
from serve.delivery.tests.test_recovery import (
    absent_host_process_case,
    completed_recovery_restart_case,
    recovery_case,
    recovery_journal_snapshot,
)

from owlbear_cockpit.deps import get_target_context
from owlbear_cockpit.routes.target_work import assemble_target_app
from owlbear_cockpit.target_context import load_target_context
from owlbear_cockpit.target_models import PublicationChecksObservationResponse
from owlbear_delivery import (
    ChangeContinuationAction,
    DeliveryAcceptanceReconciliationOutcome,
    DeliveryAcceptanceReconciliationStatus,
    DeliveryAcquisitionFailure,
    DeliveryActionBusyError,
    DeliveryAnswer,
    DeliveryAnswerKind,
    DeliveryChangeIntent,
    DeliveryChangeIntentKind,
    DeliveryCheckpointPublicationState,
    DeliveryCheckpointReconciliationResult,
    DeliveryContinuationRequest,
    DeliveryContinuationResult,
    DeliveryEngineActionResult,
    DeliveryReadiness,
    DeliveryReadinessBasis,
    DeliveryRuntime,
    DeliveryStage,
    DeliveryUnavailableChangeView,
    ExecuteDeliveryChangeAction,
    PortfolioApplication,
    PortfolioCoordinator,
    PublicationCheckKind,
    PublicationProviderError,
    PublicationProviderFailureCode,
    RetryDelivery,
)
from owlbear_delivery.acceptance import CompletionPullRequestIdentity, CompletionReceiptConflictError
from owlbear_delivery.change_workspace import (
    ChangeTargetSyncAbortReceipt,
    ChangeTargetSyncConflictError,
    ChangeTargetSyncReceipt,
    ChangeWorktreeAttentionCode,
    ChangeWorktreeAttentionError,
)
from owlbear_delivery.completed_history import (
    CompletedChangePage,
    ReceiptCompletedChangeRecord,
)
from owlbear_delivery.delivery_application_loader import (
    DeliveryApplicationLoadError,
    DeliveryStartupConfig,
)
from owlbear_delivery.delivery_application_loader import (
    load_delivery_application as load_core_delivery_application,
)
from owlbear_delivery.delivery_runtime import (
    DeliveryAcceptanceWaitingError,
    DeliveryChangeDispositionBusyError,
    DeliveryChangeDispositionConflictError,
    DeliveryChangeStage,
)
from owlbear_delivery.finalization_reports import FinalizationFailureCode
from owlbear_delivery.portfolio_operating import (
    DeliveryHealthDiagnostic,
    DeliveryHealthStatus,
    DeliveryHealthView,
    PortfolioChangeAdmission,
    PortfolioChangeLifecycleStatus,
    PortfolioGuidance,
    PortfolioGuidanceKind,
    PortfolioOperatingView,
    PortfolioWorkReference,
    PortfolioWorkScope,
)
from owlbear_delivery.recovery import DeliveryWorkerExclusionRequiredError
from owlbear_delivery.storage_io import locked_roots
from owlbear_delivery.work_items import (
    ChangeGroupView,
    WorkItemAction,
    WorkItemActionKind,
    WorkItemActivity,
    WorkItemActivityState,
    WorkItemCardView,
    WorkItemChangeLifecycle,
    WorkItemDetailView,
    WorkItemNeed,
    WorkItemNextActor,
    WorkItemProgress,
    WorkItemProgressKind,
    WorkItemPublicationPhase,
    WorkItemPublicationView,
    WorkItemScope,
    WorkItemStage,
    WorkItemTargetSyncView,
)
from owlbear_delivery_github import GitHubCliPublicationProvider


class _LockOnlyPortfolioApplication(PortfolioApplication):
    def __init__(self, target_root: Path) -> None:
        self._target_root = target_root.resolve()
        self._coordinator = PortfolioCoordinator(self._target_root)
        self._clock = lambda: "2026-08-11T16:00:00Z"

    def _runtime(self, _change_id: str, *, for_mutation: bool = False) -> DeliveryRuntime:
        del for_mutation
        return cast(DeliveryRuntime, object())


def _card(change_id: str, outcome_id: str, needs: WorkItemNeed) -> WorkItemCardView:
    next_actor = WorkItemNextActor.YOU if needs == WorkItemNeed.YOU else WorkItemNextActor.AGENT
    next_step = "Your attention is required" if needs == WorkItemNeed.YOU else "Ready for Orchestration"
    return WorkItemCardView(
        item_key=f"outcome:{outcome_id}",
        work_item_id=outcome_id,
        change_id=change_id,
        scope=WorkItemScope.OUTCOME,
        title=f"Outcome {outcome_id}",
        stage=WorkItemStage.PLANNING,
        needs=needs,
        next_actor=next_actor,
        next_step=next_step,
        activity=WorkItemActivity(state=WorkItemActivityState.READY),
        progress=WorkItemProgress(kind=WorkItemProgressKind.PLAN, label="Task plan not published"),
        action=WorkItemAction(),
    )


CONTINUATION_ID = f"continue-{'c' * 64}"


def _continuation_action(change_id: str) -> ChangeContinuationAction:
    return ChangeContinuationAction(
        operation_id=CONTINUATION_ID,
        change_id=change_id,
        kind="sync-target",
        contract_digest="a" * 64,
        frontier_digest="b" * 64,
        exact_head="d" * 40,
        target_head="e" * 40,
        host_id="cockpit-host",
        session_id="cockpit-session",
        acquired_at="2026-09-13T00:00:00Z",
    )


def _continuation_readiness() -> DeliveryReadiness:
    return DeliveryReadiness(
        status="ready",
        operation=WorkItemActionKind.SYNC_TARGET,
        next_actor=WorkItemNextActor.AGENT,
        reason_code="target-sync-required",
        basis=DeliveryReadinessBasis(
            contract_digest="a" * 64,
            frontier_digest="b" * 64,
            source_head="d" * 40,
            target_head="e" * 40,
            continuation_id=CONTINUATION_ID,
        ),
    )


# Non-acquired dispositions the HTTP boundary must forward unchanged, keyed by selected Change.
CONTINUATION_DISPOSITIONS = {
    "waiting-change": ("waiting", "host-capability-unavailable"),
    "stale-change": ("stale", "readiness-changed"),
    "human-change": ("human", "merge-approval-required"),
}


def _engine_action_result(change_id: str, *, kind: str) -> DeliveryEngineActionResult:
    action = _continuation_action(change_id)
    if kind == "blocked":
        return DeliveryEngineActionResult(
            action=action,
            kind="blocked",
            reason_code="engine-action-interrupted",
            failure=DeliveryAcquisitionFailure(
                change_id=change_id,
                outcome_id="OUT-001",
                attempt_id=CONTINUATION_ID,
                code="ERR_DELIVERY_ACTION_INTERRUPTED",
                detail="The engine action did not report an outcome.",
                retry_condition="Recover the retained engine action custody.",
            ),
        )
    return DeliveryEngineActionResult(
        action=action,
        kind="completed",
        reason_code="engine-action-completed",
        target_sync=ChangeTargetSyncReceipt.create(
            operation_id=CONTINUATION_ID,
            change_id=change_id,
            integration_target="main",
            expected_target="e" * 40,
            target_head="e" * 40,
            change_head_before="d" * 40,
            merged_head="f" * 40,
            merge_commit=True,
        ),
    )


class _DeliveryApplicationFake:
    def __init__(
        self,
        failures: dict[str, Exception] | None = None,
        health: DeliveryHealthView | None = None,
        unavailable_changes: tuple[DeliveryUnavailableChangeView, ...] = (),
    ) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []
        self.failures = failures or {}
        self.health = health or DeliveryHealthView(status=DeliveryHealthStatus.HEALTHY)
        self.unavailable_changes = unavailable_changes

    def list_work_item_groups(self) -> tuple[ChangeGroupView, ...]:
        self.calls.append(("list", ()))
        return self._work_item_groups()

    def list_changes(self) -> SimpleNamespace:
        self.calls.append(("portfolio", ()))
        return SimpleNamespace(
            groups=self._work_item_groups(),
            operating=self._portfolio_operating_view(),
            health=self.health,
            unavailable_changes=self.unavailable_changes,
        )

    @staticmethod
    def _work_item_groups() -> tuple[ChangeGroupView, ...]:
        return (
            ChangeGroupView(
                change_id="change-a",
                title="Change A",
                snapshot_version="a" * 64,
                lifecycle=WorkItemChangeLifecycle.IN_DELIVERY,
                outcome_total=1,
                outcome_completed=0,
                items=(_card("change-a", "OUT-001", WorkItemNeed.YOU),),
            ),
            ChangeGroupView(
                change_id="change-b",
                title="Change B",
                snapshot_version="b" * 64,
                lifecycle=WorkItemChangeLifecycle.FINALIZATION,
                outcome_total=1,
                outcome_completed=1,
                items=(
                    _card("change-b", "OUT-002", WorkItemNeed.NONE).model_copy(
                        update={
                            "stage": WorkItemStage.COMPLETED,
                            "next_actor": WorkItemNextActor.NONE,
                            "next_step": "Complete — no action needed",
                        }
                    ),
                    WorkItemCardView(
                        item_key="publication",
                        work_item_id="change-b",
                        change_id="change-b",
                        scope=WorkItemScope.CHANGE_PUBLICATION,
                        title="Change publication",
                        stage=None,
                        needs=WorkItemNeed.NONE,
                        next_actor=WorkItemNextActor.AGENT,
                        next_step="Finalize the reviewed Change",
                        activity=WorkItemActivity(state=WorkItemActivityState.READY),
                        progress=WorkItemProgress(
                            kind=WorkItemProgressKind.PUBLICATION,
                            label="Ready for finalization",
                        ),
                        action=WorkItemAction(),
                    ),
                ),
            ),
        )

    def portfolio_operating_view(self) -> PortfolioOperatingView:
        self.calls.append(("operating", ()))
        return self._portfolio_operating_view()

    @staticmethod
    def _portfolio_operating_view() -> PortfolioOperatingView:
        return PortfolioOperatingView(
            unfinished_change_count=2,
            completed_change_count=0,
            statuses=(
                PortfolioChangeLifecycleStatus(
                    change_id="draft-change",
                    admission=PortfolioChangeAdmission.UNADMITTED,
                    stage=DeliveryChangeStage.DESIGN,
                    actionable_runtime=False,
                ),
                PortfolioChangeLifecycleStatus(
                    change_id="admitted-planning",
                    admission=PortfolioChangeAdmission.ADMITTED,
                    stage=DeliveryChangeStage.BUILDING,
                    actionable_runtime=True,
                ),
                PortfolioChangeLifecycleStatus(
                    change_id="design-reentry",
                    admission=PortfolioChangeAdmission.ADMITTED,
                    stage=DeliveryChangeStage.DESIGN,
                    actionable_runtime=True,
                ),
                PortfolioChangeLifecycleStatus(
                    change_id="unavailable-change",
                    admission=PortfolioChangeAdmission.ADMITTED,
                    stage=DeliveryChangeStage.BUILDING,
                    actionable_runtime=False,
                    diagnostic_code="runtime_unavailable",
                    diagnostic_detail="Delivery runtime is unavailable.",
                ),
            ),
            interventions=(
                PortfolioWorkReference(
                    change_id="change-a",
                    item_key="outcome:OUT-001",
                    scope=PortfolioWorkScope.OUTCOME,
                ),
            ),
            guidance=(
                PortfolioGuidance(
                    kind=PortfolioGuidanceKind.INTERVENE,
                    change_ids=("change-a",),
                    work_count=1,
                ),
            ),
        )

    def read_design_session(self, change_id: str) -> SimpleNamespace:
        self.calls.append(("show-design", (change_id,)))
        return SimpleNamespace(
            change_id=change_id,
            package_id="d" * 64,
            intent_bytes=b"# Design intent\n",
            design_bytes=b"# Design architecture\n",
        )

    def show_work_item_view(self, change_id: str, item_key: str) -> WorkItemDetailView | DeliveryUnavailableChangeView:
        self.calls.append(("show", (change_id, item_key)))
        unavailable = next((item for item in self.unavailable_changes if item.change_id == change_id), None)
        if unavailable is not None:
            return unavailable
        if item_key == "publication":
            card = WorkItemCardView(
                item_key="publication",
                work_item_id=change_id,
                change_id=change_id,
                scope=WorkItemScope.CHANGE_PUBLICATION,
                title="Change publication",
                stage=None,
                needs=WorkItemNeed.NONE,
                next_actor=WorkItemNextActor.AGENT,
                next_step="Finalize the reviewed Change",
                activity=WorkItemActivity(state=WorkItemActivityState.READY),
                progress=WorkItemProgress(
                    kind=WorkItemProgressKind.PUBLICATION,
                    label="Ready for finalization",
                ),
                action=WorkItemAction(),
            )
            return WorkItemDetailView(
                snapshot_version="a" * 64,
                change_title=f"Change {change_id}",
                card=card,
                promise="Publish the reviewed Change.",
                publication=WorkItemPublicationView(
                    phase=WorkItemPublicationPhase.READY_FOR_FINALIZATION,
                    target_sync=WorkItemTargetSyncView(
                        receipt_id="a" * 64,
                        operation_id="sync-cockpit-test",
                        target_branch="main",
                        expected_target="1" * 40,
                        target_head="1" * 40,
                        change_head_before="2" * 40,
                        merged_head="3" * 40,
                        merge_commit=True,
                    ),
                ),
            )
        return WorkItemDetailView(
            snapshot_version="a" * 64,
            change_title=f"Change {change_id}",
            card=_card(change_id, item_key.removeprefix("outcome:"), WorkItemNeed.NONE),
            promise="Deliver the Outcome.",
        )

    def resolve_request(self, *args: object) -> dict[str, object]:
        self.calls.append(("answer", args))
        return {"request_id": args[1], "resolved": True}

    def get_change(self, change_id: str) -> SimpleNamespace:
        self.calls.append(("get-change", (change_id,)))
        return SimpleNamespace(frontier_digest="a" * 64)

    def answer(self, answer: DeliveryAnswer) -> dict[str, object]:
        operation = {
            "request": "answer",
            "block": "clear",
            "disposition": "attention-resolve",
        }[answer.kind.value]
        self.calls.append((operation, (answer,)))
        failure = self.failures.get("answer")
        if failure is not None:
            raise failure
        return {"request_id": answer.request_id, "resolved": True}

    def clear_block(self, *args: object) -> dict[str, object]:
        self.calls.append(("clear", args))
        return {"block_id": args[2], "resolved": True}

    def recover_claim(self, *args: object, confirmed_lost: bool = False) -> dict[str, object]:
        self.calls.append(("recover", args))
        assert confirmed_lost
        return {"status": "recovered", "attempt_id": args[2], "claim_id": args[3]}

    def administrative_move(self, *args: object) -> dict[str, object]:
        self.calls.append(("move", args))
        return {"move": args[1]}

    def preview_administrative_move(self, *args: object) -> dict[str, object]:
        self.calls.append(("move-preview", args))
        return {
            "outcome_id": args[1],
            "target": args[2],
            "snapshot_version": "a" * 64,
            "invalidated_outcome_ids": [args[1]],
        }

    def reconcile_change_checkpoint(self, *args: object) -> dict[str, object]:
        self.calls.append(("publication-reconcile", args))
        return DeliveryCheckpointReconciliationResult(
            change_id=str(args[0]),
            state=DeliveryCheckpointPublicationState(change_id=str(args[0])),
            reconciled=True,
        )

    def mark_current_change_ready(self, *args: object) -> dict[str, object]:
        self.calls.append(("publication-ready", args))
        failure = self.failures.get("publication-ready")
        if failure is not None:
            raise failure
        return {"change_id": args[0], "draft": False}

    def observe_change_publication_checks(self, *args: object) -> SimpleNamespace:
        self.calls.append(("publication-checks-observe", args))
        failure = self.failures.get("publication-checks-observe")
        if failure is not None:
            raise failure
        head = "1" * 40
        return SimpleNamespace(
            observation_id="a" * 64,
            change_id=str(args[0]),
            repository="owlbear/example",
            number=42,
            exact_commit=head,
            observed_at=datetime(2026, 8, 11, 16, 0, tzinfo=UTC),
            snapshot=SimpleNamespace(
                rollup_state="failure",
                checks=(
                    SimpleNamespace(
                        check_id="optional-failure",
                        kind=PublicationCheckKind.CHECK_RUN,
                        name="Optional lint",
                        status="completed",
                        conclusion="failure",
                        required=False,
                    ),
                    SimpleNamespace(
                        check_id="required-pending",
                        kind=PublicationCheckKind.CHECK_RUN,
                        name="Integration tests",
                        status="queued",
                        conclusion=None,
                        required=True,
                    ),
                    SimpleNamespace(
                        check_id="required-failure",
                        kind=PublicationCheckKind.CHECK_RUN,
                        name="Unit tests",
                        status="completed",
                        conclusion="failure",
                        required=True,
                    ),
                ),
            ),
        )

    def observe_acceptance(self, *args: object) -> dict[str, object]:
        self.calls.append(("acceptance-observe", args))
        failure = self.failures.get("observe_acceptance")
        if failure is not None:
            raise failure
        return {"change_id": args[0], "completion_id": "f" * 64}

    def reconcile_awaiting_acceptance(self, *args: object) -> tuple[DeliveryAcceptanceReconciliationOutcome, ...]:
        self.calls.append(("acceptance-reconcile", args))
        return (
            DeliveryAcceptanceReconciliationOutcome(
                change_id="change-a",
                status=DeliveryAcceptanceReconciliationStatus.WAITING,
                detail="The pull request is open and not merged.",
            ),
            DeliveryAcceptanceReconciliationOutcome(
                change_id="change-b",
                status=DeliveryAcceptanceReconciliationStatus.COMPLETED,
                completion_id="f" * 64,
            ),
            DeliveryAcceptanceReconciliationOutcome(
                change_id="change-c",
                status=DeliveryAcceptanceReconciliationStatus.PROVIDER_UNAVAILABLE,
                code="unavailable",
                detail="Provider unavailable",
            ),
        )

    def resolve_change_disposition(self, *args: object) -> dict[str, object]:
        self.calls.append(("attention-resolve", args))
        failure = self.failures.get("resolve_change_disposition")
        if failure is not None:
            raise failure
        return {"change_id": args[0], "disposition_id": args[1]}

    def supersede_current_publication(self, *args: object) -> SimpleNamespace:
        self.calls.append(("publication-supersede", args))
        return SimpleNamespace(
            receipt_id="a" * 64,
            operation_id=str(args[1]),
            change_id=str(args[0]),
            predecessor_publication_id="b" * 64,
            successor_publication_id="c" * 64,
        )

    def sync_change_with_current_target(self, *args: object) -> ChangeTargetSyncReceipt:
        self.calls.append(("target-sync", args))
        failure = self.failures.get("target_sync")
        if failure is not None:
            raise failure
        return ChangeTargetSyncReceipt.create(
            operation_id=str(args[1]),
            change_id=str(args[0]),
            integration_target="main",
            expected_target="e" * 40,
            target_head="e" * 40,
            change_head_before="d" * 40,
            merged_head="f" * 40,
            merge_commit=True,
        )

    def abort_target_sync_conflict(self, *args: object) -> ChangeTargetSyncAbortReceipt:
        self.calls.append(("target-sync-abort", args))
        return ChangeTargetSyncAbortReceipt.create(
            operation_id=str(args[3]),
            change_id=str(args[0]),
            target_head=str(args[2]),
            restored_head="d" * 40,
        )

    def resolve_target_sync_conflict(self, *args: object) -> ChangeTargetSyncReceipt:
        self.calls.append(("target-sync-resolve", args))
        return ChangeTargetSyncReceipt.create(
            operation_id=str(args[3]),
            change_id=str(args[0]),
            integration_target="main",
            expected_target=str(args[2]),
            target_head=str(args[2]),
            change_head_before="d" * 40,
            merged_head="f" * 40,
            merge_commit=True,
        )

    def defer_change(self, *args: object) -> dict[str, object]:
        self.calls.append(("defer", args))
        return {"change_id": args[0], "state": "deferred", "reason": args[1]}

    def resume_change(self, *args: object) -> dict[str, object]:
        self.calls.append(("resume", args))
        return {"change_id": args[0], "state": "building"}

    def abandon_change(self, *args: object) -> dict[str, object]:
        self.calls.append(("abandon", args))
        return {"change_id": args[0], "state": "abandoned", "reason": args[1]}

    def set_change_intent(self, intent: DeliveryChangeIntent) -> dict[str, object]:
        self.calls.append(("intent", (intent,)))
        return {"change_id": intent.change_id, "state": intent.kind.value}

    def acquire_change_action(self, request: DeliveryContinuationRequest) -> DeliveryContinuationResult:
        self.calls.append(("continuation-acquire", (request,)))
        failure = self.failures.get("acquire_change_action")
        if failure is not None:
            raise failure
        disposition = CONTINUATION_DISPOSITIONS.get(request.change_id)
        if disposition is not None:
            kind, reason = disposition
            return DeliveryContinuationResult(
                change_id=request.change_id,
                kind=kind,  # type: ignore[arg-type]
                reason_code=reason,  # type: ignore[arg-type]
                readiness=_continuation_readiness(),
            )
        if request.change_id == "blocked-change":
            engine_result = _engine_action_result(request.change_id, kind="blocked")
            return DeliveryContinuationResult(
                change_id=request.change_id,
                kind="unavailable",
                reason_code=engine_result.reason_code,
                readiness=_continuation_readiness(),
                failure=engine_result.failure,
                engine_result=engine_result,
            )
        return DeliveryContinuationResult(
            change_id=request.change_id,
            kind="acquired",
            reason_code="ready",
            readiness=_continuation_readiness(),
            engine_action=_continuation_action(request.change_id),
        )

    def execute_change_action(self, request: ExecuteDeliveryChangeAction) -> DeliveryEngineActionResult:
        self.calls.append(("continuation-execute", (request,)))
        failure = self.failures.get("execute_change_action")
        if failure is not None:
            raise failure
        return _engine_action_result(request.change_id, kind="completed")

    @staticmethod
    def _cleanup_receipt() -> SimpleNamespace:
        return SimpleNamespace(
            cleanup_id="c" * 64,
            change_id="change-a",
            branch="owlbear/change/change-a",
            worktree_path=Path(".owlbear/delivery/worktrees/change-a"),
            branch_head="d" * 40,
        )

    def cleanup_abandoned_change_worktree(self, *args: object) -> SimpleNamespace:
        self.calls.append(("cleanup-abandoned", args))
        failure = self.failures.get("cleanup_abandoned")
        if failure is not None:
            raise failure
        return self._cleanup_receipt()

    def cleanup_abandoned_change_worktree_after_target_sync_discard(
        self,
        *args: object,
        confirmed_discard: bool,
        expected_target_head: str,
        expected_operation_id: str,
    ) -> SimpleNamespace:
        self.calls.append(
            (
                "cleanup-abandoned-target-sync",
                (*args, confirmed_discard, expected_target_head, expected_operation_id),
            )
        )
        return self._cleanup_receipt()

    def cleanup_completed_change_worktree(self, *args: object) -> SimpleNamespace:
        self.calls.append(("cleanup-completed", args))
        return self._cleanup_receipt()

    @staticmethod
    def _recovery_receipt() -> SimpleNamespace:
        return SimpleNamespace(
            change_id="change-a",
            branch="owlbear/change/change-a",
            worktree_path=Path(".owlbear/delivery/worktrees/change-a"),
            branch_head="d" * 40,
            recovery_reviewed_head="c" * 40,
        )

    def recover_change_worktree(
        self, change_id: str, reviewed_head: str, *, confirmed_recovery: bool
    ) -> SimpleNamespace:
        self.calls.append(("recover-worktree", (change_id, reviewed_head, confirmed_recovery)))
        failure = self.failures.get("recover_worktree")
        if failure is not None:
            raise failure
        return self._recovery_receipt()

    @staticmethod
    def _completed_history() -> CompletedChangePage:
        return CompletedChangePage(
            records=(
                ReceiptCompletedChangeRecord(
                    change_id="change-a",
                    completion_id="b" * 64,
                    title="Receipt completion",
                    semantic_summary="A merged pull request completion receipt.",
                    outcome_titles=("Accept the merged Change",),
                    outcome_promises=("Record the accepted Delivery result.",),
                    finalization_receipt_id="c" * 64,
                    finalized_change_head="d" * 40,
                    repository_identity="owlbear/example",
                    pull_request_identity=CompletionPullRequestIdentity(number=41, node_id="PR_example_41"),
                    accepted_target_ref="main",
                    accepted_merge_commit="e" * 40,
                    merged_at=datetime(2026, 8, 11, 11, tzinfo=UTC),
                    acceptance_observation_id="f" * 64,
                    check_observation_ids=("0" * 64,),
                    review_receipt_ids=("1" * 64,),
                    acceptance_evidence_digest="2" * 64,
                    completed_at=datetime(2026, 8, 11, 12, tzinfo=UTC),
                ),
                ReceiptCompletedChangeRecord(
                    change_id="change-b",
                    completion_id="1" * 64,
                    title="Receipt completion",
                    semantic_summary="A merged pull request completion receipt.",
                    outcome_titles=("Accept the merged Change",),
                    outcome_promises=("Record the accepted Delivery result.",),
                    finalization_receipt_id="2" * 64,
                    finalized_change_head="3" * 40,
                    repository_identity="owlbear/example",
                    pull_request_identity=CompletionPullRequestIdentity(number=42, node_id="PR_example_42"),
                    accepted_target_ref="main",
                    accepted_merge_commit="4" * 40,
                    merged_at=datetime(2026, 8, 11, 12, tzinfo=UTC),
                    acceptance_observation_id="5" * 64,
                    check_observation_ids=("6" * 64,),
                    review_receipt_ids=("7" * 64,),
                    acceptance_evidence_digest="8" * 64,
                    completed_at=datetime(2026, 8, 11, 13, tzinfo=UTC),
                ),
            ),
            total_count=2,
            next_cursor="completed-history-next",
        )

    def list_completed_changes(self, *args: object) -> CompletedChangePage:
        self.calls.append(("completed-list", args))
        return self._completed_history()

    def search_completed_changes(self, *args: object) -> CompletedChangePage:
        self.calls.append(("completed-search", args))
        return self._completed_history()

    def show_completed_change(self, *args: object) -> ReceiptCompletedChangeRecord:
        self.calls.append(("completed-show", args))
        records = self._completed_history().records
        return records[1] if args[1] == "1" * 64 else records[0]


@pytest.mark.parametrize("kind", ["planner", "builder"])
def test_real_core_claim_recovery_exclusion_required(tmp_path: Path, kind: str) -> None:
    application, _operation, request, unchanged = recovery_case(tmp_path, kind)
    body = {key: value for key, value in request.items() if key not in {"change_id", "outcome_id"}}
    with TestClient(assemble_target_app(application)) as client:
        response = client.post("/api/changes/change-a/outcomes/OUT-001/claims/recover", json=body)
    assert response.status_code == 409
    diagnostic = response.json()
    assert diagnostic["code"] == DeliveryWorkerExclusionRequiredError.code
    assert diagnostic["retry_safe"] is False
    assert "Custody and files are unchanged" in diagnostic["detail"]
    unchanged()


@pytest.mark.parametrize("action", ["block", "return"])
def test_http_builder_transition_diagnostic_is_blocked_without_active_request(tmp_path: Path, action: str) -> None:
    application, runtimes, coordinator, _state_root, launch, transition = builder_transition_case(tmp_path, action)
    before_workspace = _workspace_mutation_snapshot(launch.worktree_path)
    before_coordination = coordinator.show("change-a")
    with pytest.raises(DeliveryWorkerExclusionRequiredError):
        application.transition_delivery("change-a", transition)
    retained = runtimes["change-a"].frontier_bytes()
    with TestClient(assemble_target_app(application)) as client:
        detail_response = client.get("/api/changes/change-a/work-items/outcome:OUT-001")
        change_response = client.get("/api/work-items")
    assert detail_response.status_code == change_response.status_code == 200
    detail = detail_response.json()["item"]
    change = change_response.json()["groups"][0]["items"][0]
    assert detail["recovery_attention"]["diagnostic_transition"] == transition.model_dump(mode="json")
    assert detail["requests"] == []
    assert detail["block"] is None
    assert detail["return_context"] is None
    assert detail["card"]["needs"] == "none"
    assert detail["card"]["action"]["kind"] == "none"
    assert launch.claim.owner_id in detail["card"]["next_step"]
    for readiness in (change["readiness"], detail["readiness"]):
        assert readiness["status"] == "blocked"
        assert readiness["reason_code"] == "builder-transition-contained"
        assert readiness["executable"] is False
        assert readiness["action"] is None
        assert "read-only" in readiness["prompt"]
    prompt = detail["readiness"]["prompt"]
    assert change["readiness"]["prompt"] == prompt
    assert prompt.startswith("/repair-delivery Inspect only Change change-a")
    assert "`delivery-diagnose inspect --change-id change-a`" in prompt
    assert "preserve custody, stage, worktree, inspected files, and retry budget" in prompt
    assert "do not answer, unblock, restart, release, edit, repair, or dispatch a replacement" in prompt
    for unsupported_tool in ("get_change", "show_operator_context", "acquire_change_action", "transition_delivery"):
        assert unsupported_tool not in prompt
    assert runtimes["change-a"].frontier_bytes() == retained
    assert coordinator.show("change-a") == before_coordination
    assert _workspace_mutation_snapshot(launch.worktree_path) == before_workspace


@pytest.mark.parametrize("exhausted", [False, True])
def test_http_explicit_acceptance_is_one_bounded_read(tmp_path: Path, *, exhausted: bool) -> None:
    application, provider, ledger, restart = acceptance_budget_case(tmp_path, exhausted=exhausted)
    calls = provider.read_pull_request.call_count
    with TestClient(assemble_target_app(application)) as client:
        for _ in range(2):
            assert (
                client.post("/api/work-items/acceptance/reconcile", json={"change_ids": ["change-a"]}).status_code
                == 200
            )
        assert provider.read_pull_request.call_count == calls
        first = client.post("/api/changes/change-a/acceptance/observe")
    with TestClient(assemble_target_app(restart())) as client:
        assert client.post("/api/work-items/acceptance/reconcile", json={"change_ids": ["change-a"]}).status_code == 200
        second = client.post("/api/changes/change-a/acceptance/observe")
    assert first.status_code == second.status_code == 409
    assert first.json()["code"] == "ERR_DELIVERY_ACCEPTANCE_WAITING"
    assert second.json()["detail"] == ("acceptance-wait" if exhausted else "retry-backoff")
    assert provider.read_pull_request.call_count == calls + int(exhausted)
    episode = ledger.read().episodes[0]
    assert (episode.total_attempts, episode.explicit_observations, episode.reset_count) == (
        (3, 1, 0) if exhausted else (1, 0, 0)
    )


def test_http_verified_completed_recovery_replay(tmp_path: Path) -> None:
    application, _operation, request, unchanged, host = completed_recovery_restart_case(tmp_path, "claim")
    body = {key: value for key, value in request.items() if key not in {"change_id", "outcome_id"}}
    journals = recovery_journal_snapshot(application, "change-a")
    verifications = host.verifications
    with TestClient(assemble_target_app(application)) as client:
        first_read = client.get("/api/changes/change-a/work-items/outcome:OUT-001")
        repeated_read = client.get("/api/changes/change-a/work-items/outcome:OUT-001")
        assert first_read.status_code == repeated_read.status_code == 200
        assert first_read.json() == repeated_read.json()
        assert recovery_journal_snapshot(application, "change-a") == journals
        assert host.verifications == verifications
        first_replay = client.post("/api/changes/change-a/outcomes/OUT-001/claims/recover", json=body)
        second_replay = client.post("/api/changes/change-a/outcomes/OUT-001/claims/recover", json=body)
    assert first_replay.status_code == second_replay.status_code == 200
    assert first_replay.json() == second_replay.json()
    assert first_replay.json()["status"] == "recovered"
    assert host.verifications == verifications + 2
    assert recovery_journal_snapshot(application, "change-a") == journals
    unchanged()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("preservation_paths", ["../../outside"]),
        ("commands", ["terminate-worker"]),
        ("budget", {"attempts": 999}),
        ("effect_receipt", {"verified": True}),
        ("stop_assertion", {"all_descendants_stopped": True}),
    ],
)
def test_http_recovery_rejects_caller_authored_evidence_fields_before_mutation(
    tmp_path: Path,
    field: str,
    value: object,
) -> None:
    application, _operation, request, unchanged = recovery_case(tmp_path, "builder")
    body = {key: value for key, value in request.items() if key not in {"change_id", "outcome_id"}}
    body[field] = value
    with TestClient(assemble_target_app(application)) as client:
        response = client.post("/api/changes/change-a/outcomes/OUT-001/claims/recover", json=body)
    assert response.status_code == 422
    assert response.json()["code"] == "ERR_DELIVERY_HTTP_VALIDATION"
    assert response.json()["detail"] == "Delivery request input is malformed"
    unchanged()


def test_http_recovery_rejects_stale_claim_identity_before_mutation(tmp_path: Path) -> None:
    application, _operation, request, unchanged = recovery_case(tmp_path, "builder")
    body = {key: value for key, value in request.items() if key not in {"change_id", "outcome_id"}}
    body["attempt_id"] = "stale-attempt"
    with TestClient(assemble_target_app(application)) as client:
        response = client.post("/api/changes/change-a/outcomes/OUT-001/claims/recover", json=body)
    assert response.status_code == 409
    unchanged()


def test_http_absent_host_still_writing_descendant_stays_contained_across_restarts(tmp_path: Path) -> None:
    application, host, _worker, launch, restart, snapshot, signal = absent_host_process_case(tmp_path)

    def assert_contained(candidate) -> tuple[object, ...]:
        before = snapshot(candidate)
        with TestClient(assemble_target_app(candidate)) as client:
            first = client.get("/api/changes/change-a/work-items/outcome:OUT-001")
            repeated = client.get("/api/changes/change-a/work-items/outcome:OUT-001")
            assert first.status_code == repeated.status_code == 200
            assert first.json() == repeated.json()
            readiness = first.json()["item"]["readiness"]
            assert readiness["executable"] is False
            portfolio = client.get("/api/work-items")
            assert portfolio.status_code == 200
            claim_refusal = client.post(
                "/api/changes/change-a/outcomes/OUT-001/claims/recover",
                json={
                    "attempt_id": launch.claim.attempt_id,
                    "claim_id": launch.claim.claim_id,
                    "confirmed_lost": True,
                },
            )
            assert claim_refusal.status_code == 409
            assert claim_refusal.json()["code"] == DeliveryWorkerExclusionRequiredError.code
            assert claim_refusal.json()["retry_safe"] is False
            assert "Custody and files are unchanged" in claim_refusal.json()["detail"]
            assert "Timeout and caller confirmation are not evidence" in claim_refusal.json()["detail"]
            acquired = client.post(
                "/api/changes/change-a/continuation/acquire",
                json={
                    "expected_basis": readiness["basis"],
                    "capabilities": ["builder"],
                    "host_id": "synthetic-host",
                    "session_id": "absent-host-recovery",
                },
            )
            assert acquired.status_code == 200
            assert acquired.json()["kind"] == "unsupported"
            assert acquired.json()["reason_code"] == "repair-required"
            assert acquired.json()["readiness"]["reason_code"] == "active-custody"
            assert acquired.json()["engine_action"] is None
        assert host.verifications == 0
        assert launch.claim.claim_id not in host.closed
        assert snapshot(candidate) == before
        return before

    try:
        first_snapshot = assert_contained(application)
        signal("write-next", b"late old write after restart\n")
        after_signaled_write = snapshot(application)
        assert after_signaled_write[:3] == first_snapshot[:3]
        assert after_signaled_write[3] != first_snapshot[3]
        assert after_signaled_write[4:] == first_snapshot[4:]
        restarted = restart()
        assert snapshot(restarted) == after_signaled_write
        assert_contained(restarted)
    finally:
        host.close(launch.claim.claim_id)


def test_http_default_loader_replays_engine_action_after_restart(tmp_path: Path) -> None:
    repository, _runtime_root, remote, provider, application, _head_a, _head_b = _loader_composed_engine_fixture(
        tmp_path
    )
    basis = application.get_change("change-a").readiness.basis.model_dump(mode="json")
    with TestClient(assemble_target_app(application)) as client:
        acquired = client.post(
            "/api/changes/change-a/continuation/acquire",
            json={
                "expected_basis": basis,
                "capabilities": ["engine"],
                "host_id": "synthetic-host",
                "session_id": "synthetic-session",
            },
        )
        assert acquired.status_code == 200
        action = acquired.json()["engine_action"]
        executed = client.post(
            "/api/changes/change-a/continuation/execute",
            json={"operation_id": action["operation_id"]},
        )
        replayed = client.post(
            "/api/changes/change-a/continuation/execute",
            json={"operation_id": action["operation_id"]},
        )

    runtime = application._runtimes["change-a"]  # noqa: SLF001
    workspace_before_restart = _workspace_mutation_snapshot(
        application._coordinator.show("change-a").worktree_path  # noqa: SLF001
    )
    frontier_before_restart = runtime.frontier_bytes()
    ledger_before_restart = runtime.retry_ledger().read()
    remote_refs_before_restart = _remote_refs(remote)

    _git(repository, "remote", "set-url", "origin", "https://github.com/example/project.git")
    _git(repository, "config", f"url.{remote}.insteadOf", "https://github.com/example/project.git")
    reloaded = load_core_delivery_application(
        _startup_config(),
        workspace_root=repository,
        publication_provider=provider,
    )
    with TestClient(assemble_target_app(reloaded)) as client:
        restarted = client.post(
            "/api/changes/change-a/continuation/execute",
            json={"operation_id": action["operation_id"]},
        )

    assert action["kind"] == "mark-ready"
    assert executed.status_code == replayed.status_code == restarted.status_code == 200
    assert executed.json()["kind"] == "completed"
    assert executed.json() == replayed.json() == restarted.json()
    assert provider.draft_state_calls == 1
    assert reloaded._runtimes["change-a"].frontier_bytes() == frontier_before_restart  # noqa: SLF001
    assert reloaded._runtimes["change-a"].retry_ledger().read() == ledger_before_restart  # noqa: SLF001
    assert (
        _workspace_mutation_snapshot(
            reloaded._coordinator.show("change-a").worktree_path  # noqa: SLF001
        )
        == workspace_before_restart
    )
    assert _remote_refs(remote) == remote_refs_before_restart


def test_http_default_loader_contains_unknown_result_after_restart(tmp_path: Path) -> None:
    repository, _runtime_root, remote, provider, application, _head_a, _head_b = _loader_composed_engine_fixture(
        tmp_path
    )
    basis = application.get_change("change-a").readiness.basis.model_dump(mode="json")
    with TestClient(assemble_target_app(application)) as client:
        acquired = client.post(
            "/api/changes/change-a/continuation/acquire",
            json={
                "expected_basis": basis,
                "capabilities": ["engine"],
                "host_id": "synthetic-host",
                "session_id": "synthetic-session",
            },
        )
    assert acquired.status_code == 200
    action = acquired.json()["engine_action"]
    assert action["kind"] == "mark-ready"

    provider.lose_draft_state_response = False
    original_finish = application._coordinator.finish_continuation_action  # noqa: SLF001
    failure_message = "injected result publication crash"

    def crash_at_result_publication(
        action_record: ChangeContinuationAction,
        result: DeliveryEngineActionResult,
        finished_at: object,
        *,
        release: bool,
    ) -> None:
        if action_record.operation_id == action["operation_id"]:
            raise RuntimeError(failure_message)
        original_finish(action_record, result, finished_at, release=release)

    with (
        patch.object(
            application._coordinator,  # noqa: SLF001
            "finish_continuation_action",
            crash_at_result_publication,
        ),
        TestClient(assemble_target_app(application)) as client,
        pytest.raises(RuntimeError, match=failure_message),
    ):
        client.post(
            "/api/changes/change-a/continuation/execute",
            json={"operation_id": action["operation_id"]},
        )

    runtime = application._runtimes["change-a"]  # noqa: SLF001
    workspace_before_containment = _workspace_mutation_snapshot(
        application._coordinator.show("change-a").worktree_path  # noqa: SLF001
    )
    frontier_before_containment = runtime.frontier_bytes()
    ledger_before_containment = runtime.retry_ledger().read()
    coordination_before_containment = (
        application._coordinator.runtime_root  # noqa: SLF001
        / "coordination/changes/change-a.json"
    ).read_bytes()
    remote_refs_before_containment = _remote_refs(remote)
    _git(repository, "remote", "set-url", "origin", "https://github.com/example/project.git")
    _git(repository, "config", f"url.{remote}.insteadOf", "https://github.com/example/project.git")
    reloaded = load_core_delivery_application(
        _startup_config(),
        workspace_root=repository,
        publication_provider=provider,
    )
    with TestClient(assemble_target_app(reloaded)) as client:
        contained = client.post(
            "/api/changes/change-a/continuation/execute",
            json={"operation_id": action["operation_id"]},
        )

    assert contained.status_code == 200
    assert contained.json()["kind"] == "blocked"
    assert contained.json()["reason_code"] == "engine-action-interrupted"
    assert provider.draft_state_calls == 1
    assert reloaded._runtimes["change-a"].frontier_bytes() == frontier_before_containment  # noqa: SLF001
    assert reloaded._runtimes["change-a"].retry_ledger().read() == ledger_before_containment  # noqa: SLF001
    assert (
        _workspace_mutation_snapshot(
            reloaded._coordinator.show("change-a").worktree_path  # noqa: SLF001
        )
        == workspace_before_containment
    )
    assert (
        reloaded._coordinator.runtime_root  # noqa: SLF001
        / "coordination/changes/change-a.json"
    ).read_bytes() == coordination_before_containment
    retained = reloaded._coordinator.show("change-a").continuation_action  # noqa: SLF001
    assert retained is not None
    assert retained.operation_id == action["operation_id"]
    assert retained.finished_at is None
    assert _remote_refs(remote) == remote_refs_before_containment


@pytest.mark.parametrize(
    "journal_state",
    ["invalid-intent", "mismatched-intent", "invalid-result", "mismatched-result"],
)
def test_http_default_loader_contains_malformed_engine_journals_without_effects(
    tmp_path: Path,
    journal_state: str,
) -> None:
    repository, _runtime_root, remote, provider, application, _head_a, _head_b = _loader_composed_engine_fixture(
        tmp_path
    )
    action = _engine_action(application, "change-a")
    intent_path = application._coordinator.continuation_record_path(  # noqa: SLF001
        "change-a", action.operation_id
    )
    result_path = intent_path.with_name("result.json")
    if journal_state == "invalid-intent":
        intent_path.write_bytes(b"{")
    elif journal_state == "mismatched-intent":
        intent_path.write_bytes(_canonical(action.model_copy(update={"session_id": "foreign-session"})))
    elif journal_state == "invalid-result":
        result_path.mkdir()
    else:
        foreign_action = action.model_copy(update={"session_id": "foreign-session"})
        foreign_result = application._engine_action_failure(  # noqa: SLF001
            foreign_action,
            "engine-action-failed",
            "foreign operation result",
        )
        result_path.write_bytes(_canonical(foreign_result))

    _git(repository, "remote", "set-url", "origin", "https://github.com/example/project.git")
    _git(repository, "config", f"url.{remote}.insteadOf", "https://github.com/example/project.git")
    reloaded = load_core_delivery_application(
        _startup_config(),
        workspace_root=repository,
        publication_provider=provider,
    )
    provider.read_pull_request = Mock(wraps=provider.read_pull_request)
    provider.observe_checks = Mock(wraps=provider.observe_checks)
    before = _loader_engine_state_snapshot(
        reloaded,
        runtime_root=reloaded._coordinator.runtime_root,  # noqa: SLF001
        remote_refs=_remote_refs(remote),
        provider=provider,
        change_id="change-a",
        operation_id=action.operation_id,
    )
    with TestClient(assemble_target_app(reloaded)) as client:
        detail = client.get("/api/changes/change-a/work-items/outcome:OUT-001")
        repeated = client.get("/api/changes/change-a/work-items/outcome:OUT-001")
        portfolio = client.get("/api/work-items")
        assert detail.status_code == repeated.status_code == portfolio.status_code == 200
        assert detail.json() == repeated.json()
        readiness = detail.json()["item"]["readiness"]
        listed_readiness = next(
            item["readiness"]
            for group in portfolio.json()["groups"]
            for item in group["items"]
            if item["change_id"] == "change-a" and item["scope"] == "outcome"
        )
        assert listed_readiness == readiness
        assert readiness["reason_code"] == "engine-action-blocked"
        assert readiness["executable"] is False
        assert readiness["action"] is None
        assert readiness["prompt"].startswith("/repair-delivery")
        acquired = client.post(
            "/api/changes/change-a/continuation/acquire",
            json={
                "expected_basis": readiness["basis"],
                "capabilities": ["engine"],
                "host_id": "synthetic-host",
                "session_id": "must-not-retry",
            },
        )
    assert acquired.status_code == 200
    assert acquired.json()["engine_action"] is None
    after = _loader_engine_state_snapshot(
        reloaded,
        runtime_root=reloaded._coordinator.runtime_root,  # noqa: SLF001
        remote_refs=_remote_refs(remote),
        provider=provider,
        change_id="change-a",
        operation_id=action.operation_id,
    )
    _assert_loader_observation_only(before, after)
    assert provider.draft_state_calls == 0
    if journal_state == "invalid-result":
        assert not tuple(result_path.iterdir())
    assert result_path.is_dir() is (journal_state == "invalid-result")


def test_http_default_loader_contains_unavailable_provider_readback_without_repeating_effects(
    tmp_path: Path,
) -> None:
    repository, runtime_root, remote, provider, application, _head_a, _head_b = _loader_composed_engine_fixture(
        tmp_path
    )
    basis = application.get_change("change-b").readiness.basis.model_dump(mode="json")
    with TestClient(assemble_target_app(application)) as client:
        acquired = client.post(
            "/api/changes/change-b/continuation/acquire",
            json={
                "expected_basis": basis,
                "capabilities": ["engine"],
                "host_id": "synthetic-host",
                "session_id": "readback-session",
            },
        )
    assert acquired.status_code == 200
    action = acquired.json()["engine_action"]
    assert action["kind"] == "mark-ready"
    _make_provider_readback_unavailable(provider, 8)
    provider.read_pull_request = Mock(wraps=provider.read_pull_request)
    provider.observe_checks = Mock(wraps=provider.observe_checks)
    with TestClient(assemble_target_app(application)) as client:
        failed = client.post(
            "/api/changes/change-b/continuation/execute",
            json={"operation_id": action["operation_id"]},
        )
    assert failed.status_code == 200
    assert failed.json()["kind"] == "blocked"
    assert failed.json()["reason_code"] == "engine-action-failed"
    assert "provider readback unavailable" in failed.json()["failure"]["detail"]
    assert "release custody" in failed.json()["failure"]["retry_condition"]
    assert provider.draft_state_calls == 1

    before_restart = _loader_engine_state_snapshot(
        application,
        runtime_root=runtime_root,
        remote_refs=_remote_refs(remote),
        provider=provider,
        change_id="change-b",
        operation_id=action["operation_id"],
    )
    _git(repository, "remote", "set-url", "origin", "https://github.com/example/project.git")
    _git(repository, "config", f"url.{remote}.insteadOf", "https://github.com/example/project.git")
    reloaded = load_core_delivery_application(
        _startup_config(),
        workspace_root=repository,
        publication_provider=provider,
    )
    after_restart = _loader_engine_state_snapshot(
        reloaded,
        runtime_root=reloaded._coordinator.runtime_root,  # noqa: SLF001
        remote_refs=_remote_refs(remote),
        provider=provider,
        change_id="change-b",
        operation_id=action["operation_id"],
    )
    _assert_loader_observation_only(before_restart, after_restart)
    with TestClient(assemble_target_app(reloaded)) as client:
        first = client.get("/api/changes/change-b/work-items/outcome:OUT-001")
        repeated = client.get("/api/changes/change-b/work-items/outcome:OUT-001")
        listed = client.get("/api/work-items")
        replayed = client.post(
            "/api/changes/change-b/continuation/execute",
            json={"operation_id": action["operation_id"]},
        )
    assert first.status_code == repeated.status_code == listed.status_code == replayed.status_code == 200
    assert first.json() == repeated.json()
    readiness = first.json()["item"]["readiness"]
    assert readiness["reason_code"] == "engine-action-failed"
    assert readiness["prompt"].startswith("/repair-delivery")
    assert replayed.json() == failed.json()
    after_reads = _loader_engine_state_snapshot(
        reloaded,
        runtime_root=reloaded._coordinator.runtime_root,  # noqa: SLF001
        remote_refs=_remote_refs(remote),
        provider=provider,
        change_id="change-b",
        operation_id=action["operation_id"],
    )
    _assert_loader_observation_only(after_restart, after_reads)
    assert provider.draft_state_calls == 1


@pytest.mark.parametrize("action_kind", ["reconcile-checkpoint", "sync-target", "observe-acceptance"])
def test_http_loader_replays_and_contains_interrupted_engine_rows(  # noqa: PLR0915
    tmp_path: Path,
    action_kind: str,
) -> None:
    """Every non-mark-ready owner row preserves exact effects across the HTTP boundary."""
    repository, runtime_root, remote, provider, application = _loader_registered_engine_action_fixture(
        tmp_path,
        action_kind,  # type: ignore[arg-type]
    )
    basis = application.get_change("change-a").readiness.basis.model_dump(mode="json")
    if action_kind == "observe-acceptance":
        with TestClient(assemble_target_app(application)) as client:
            prepared = client.post(
                "/api/changes/change-a/continuation/acquire",
                json={
                    "expected_basis": basis,
                    "capabilities": ["planner", "builder", "finalizer", "engine"],
                    "host_id": "synthetic-host",
                    "session_id": "preparation-session",
                },
            )
            assert prepared.status_code == 200
            prepared_action = ChangeContinuationAction.model_validate(prepared.json()["engine_action"])
            assert prepared_action.kind == "mark-ready"
            prepared_result = client.post(
                "/api/changes/change-a/continuation/execute",
                json={"operation_id": prepared_action.operation_id},
            )
        assert prepared_result.status_code == 200
        assert prepared_result.json()["kind"] == "completed", prepared_result.json()
        provider.pull_requests[0] = provider.pull_requests[0].model_copy(
            update={
                "state": "closed",
                "merged": True,
                "merge_commit_sha": prepared_action.exact_head,
                "merged_at": datetime(2026, 8, 4, tzinfo=UTC),
            }
        )
        basis = application.get_change("change-a").readiness.basis.model_dump(mode="json")
    runtime = application._runtimes["change-a"]  # noqa: SLF001
    sibling_frontier = application._runtimes["change-c"].frontier_bytes()  # noqa: SLF001
    sibling_publication = application._runtimes["change-c"].checkpoint_publication_state()  # noqa: SLF001
    with TestClient(assemble_target_app(application)) as client:
        acquired = client.post(
            "/api/changes/change-a/continuation/acquire",
            json={
                "expected_basis": basis,
                "capabilities": ["planner", "builder", "finalizer", "engine"],
                "host_id": "synthetic-host",
                "session_id": "synthetic-session",
            },
        )
        assert acquired.status_code == 200
        action = ChangeContinuationAction.model_validate(acquired.json()["engine_action"])
        assert action.kind == action_kind
        before_owner_execution = _loader_engine_state_snapshot(
            application,
            runtime_root=runtime_root,
            remote_refs=_remote_refs(remote),
            provider=provider,
            change_id="change-a",
            operation_id=action.operation_id,
        )
        executed = client.post(
            "/api/changes/change-a/continuation/execute",
            json={"operation_id": action.operation_id},
        )
        before_immediate_replay = _loader_engine_state_snapshot(
            application,
            runtime_root=runtime_root,
            remote_refs=_remote_refs(remote),
            provider=provider,
            change_id="change-a",
            operation_id=action.operation_id,
        )
        replayed = client.post(
            "/api/changes/change-a/continuation/execute",
            json={"operation_id": action.operation_id},
        )
    after_immediate_replay = _loader_engine_state_snapshot(
        application,
        runtime_root=runtime_root,
        remote_refs=_remote_refs(remote),
        provider=provider,
        change_id="change-a",
        operation_id=action.operation_id,
    )
    assert executed.status_code == replayed.status_code == 200
    assert executed.json() == replayed.json()
    assert executed.json()["kind"] == "completed"
    assert after_immediate_replay == before_immediate_replay
    assert after_immediate_replay["provider_mutations"] == before_immediate_replay["provider_mutations"]
    assert after_immediate_replay["provider_reads"] == before_immediate_replay["provider_reads"]
    engine_result = executed.json()
    operation_journal = before_immediate_replay["continuation_operation_journal"]
    assert operation_journal["intent"]
    assert operation_journal["started"]
    assert operation_journal["result"]
    completed_record = json.loads(operation_journal["result"])
    assert completed_record["kind"] == "completed"
    assert completed_record["action"]["operation_id"] == action.operation_id
    if action_kind in {"reconcile-checkpoint", "sync-target"}:
        published_head = (
            action.exact_head if action_kind == "reconcile-checkpoint" else engine_result["target_sync"]["merged_head"]
        )
        _assert_checkpoint_branch_operation(
            before_owner_execution,
            before_immediate_replay,
            change_id=action.change_id,
            published_head=published_head,
            expected_remote_head=before_owner_execution["checkpoint_publication"].published_head,
        )
    else:
        assert any(
            path.startswith(f"{action.change_id}/") and path != f"{action.change_id}/display.json" and content
            for path, content in before_immediate_replay["completion_journal"]
        )
    assert engine_result["action"]["operation_id"] == action.operation_id
    assert engine_result["action"]["kind"] == action.kind
    if action_kind == "reconcile-checkpoint":
        checkpoint = engine_result["checkpoint"]
        assert checkpoint["change_id"] == action.change_id
        assert checkpoint["attempted_head"] == action.exact_head
        assert checkpoint["reconciled"] is True
    elif action_kind == "sync-target":
        target_sync = engine_result["target_sync"]
        assert target_sync["change_id"] == action.change_id
        assert target_sync["expected_target"] == action.target_head
        assert target_sync["target_head"] == action.target_head
        assert target_sync["merged_head"]
    else:
        acceptance = engine_result["acceptance"]
        assert acceptance["completion_id"]
        assert acceptance["acceptance_observation_id"]
    effects_after_completion = (
        provider.create_calls,
        provider.update_calls,
        provider.draft_state_calls,
    )
    frontier_after_completion = runtime.frontier_bytes()
    retry_after_completion = runtime.retry_ledger().read()
    workspace_after_completion = _workspace_mutation_snapshot(
        application._coordinator.show("change-a").worktree_path  # noqa: SLF001
    )
    remote_after_completion = _remote_refs(remote)

    _git(repository, "remote", "set-url", "origin", "https://github.com/example/project.git")
    _git(repository, "config", f"url.{remote}.insteadOf", "https://github.com/example/project.git")
    reloaded = load_core_delivery_application(
        _startup_config(),
        workspace_root=repository,
        publication_provider=provider,
    )
    after_loader_before_replay = _loader_engine_state_snapshot(
        reloaded,
        runtime_root=runtime_root,
        remote_refs=_remote_refs(remote),
        provider=provider,
        change_id="change-a",
        operation_id=action.operation_id,
    )
    assert after_loader_before_replay == after_immediate_replay
    with TestClient(assemble_target_app(reloaded)) as client:
        restarted = client.post(
            "/api/changes/change-a/continuation/execute",
            json={"operation_id": action.operation_id},
        )
    after_loader_replay = _loader_engine_state_snapshot(
        reloaded,
        runtime_root=runtime_root,
        remote_refs=_remote_refs(remote),
        provider=provider,
        change_id="change-a",
        operation_id=action.operation_id,
    )
    assert restarted.status_code == 200
    assert restarted.json() == executed.json()
    assert after_loader_replay == after_loader_before_replay
    retained = reloaded.get_change("change-a").continuation_action
    assert retained is not None
    assert retained.model_copy(update={"finished_at": None}) == action
    assert (
        provider.create_calls,
        provider.update_calls,
        provider.draft_state_calls,
    ) == effects_after_completion
    assert reloaded._runtimes["change-a"].frontier_bytes() == frontier_after_completion  # noqa: SLF001
    assert reloaded._runtimes["change-a"].retry_ledger().read() == retry_after_completion  # noqa: SLF001
    assert (
        _workspace_mutation_snapshot(
            reloaded._coordinator.show("change-a").worktree_path  # noqa: SLF001
        )
        == workspace_after_completion
    )
    assert _remote_refs(remote) == remote_after_completion
    assert reloaded._runtimes["change-c"].frontier_bytes() == sibling_frontier  # noqa: SLF001
    assert reloaded._runtimes["change-c"].checkpoint_publication_state() == sibling_publication  # noqa: SLF001
    if action_kind != "observe-acceptance":
        next_basis = reloaded.get_change("change-a").readiness.basis.model_dump(mode="json")
        with TestClient(assemble_target_app(reloaded)) as client:
            next_acquired = client.post(
                "/api/changes/change-a/continuation/acquire",
                json={
                    "expected_basis": next_basis,
                    "capabilities": ["planner", "builder", "finalizer", "engine"],
                    "host_id": "synthetic-host",
                    "session_id": "fresh-session",
                },
            )
        assert next_acquired.status_code == 200
        assert next_acquired.json()["kind"] == "acquired"
        next_engine_action = next_acquired.json()["engine_action"]
        if next_engine_action is not None:
            next_action = ChangeContinuationAction.model_validate(next_engine_action)
            assert next_action.change_id == action.change_id
            assert next_action.operation_id != action.operation_id
        else:
            next_finalization = next_acquired.json()["finalization"]
            next_launch = next_acquired.json()["launch"]
            assert next_finalization is not None or next_launch is not None
            next_owner_id = (
                next_finalization["attempt"]["writer"]["attempt_id"]
                if next_finalization is not None
                else next_launch["claim"]["attempt_id"]
            )
            assert next_owner_id != action.operation_id

    sibling = reloaded.get_change("change-c")
    with TestClient(assemble_target_app(reloaded)) as client:
        subsequent = client.post(
            "/api/changes/change-c/continuation/acquire",
            json={
                "expected_basis": sibling.readiness.basis.model_dump(mode="json"),
                "capabilities": ["planner", "builder", "finalizer", "engine"],
                "host_id": "synthetic-host",
                "session_id": "synthetic-session",
            },
        )
    assert subsequent.status_code == 200
    assert subsequent.json()["kind"] == "acquired"


@pytest.mark.parametrize("action_kind", ["reconcile-checkpoint", "sync-target", "observe-acceptance"])
def test_http_loader_contains_unknown_custody_without_repeating_effects(  # noqa: PLR0915
    tmp_path: Path,
    action_kind: str,
) -> None:
    """A result-publication interruption remains blocked and retains its exact action."""
    repository, runtime_root, remote, provider, application = _loader_registered_engine_action_fixture(
        tmp_path,
        action_kind,  # type: ignore[arg-type]
    )
    basis = application.get_change("change-a").readiness.basis.model_dump(mode="json")
    if action_kind == "observe-acceptance":
        with TestClient(assemble_target_app(application)) as client:
            prepared = client.post(
                "/api/changes/change-a/continuation/acquire",
                json={
                    "expected_basis": basis,
                    "capabilities": ["planner", "builder", "finalizer", "engine"],
                    "host_id": "synthetic-host",
                    "session_id": "preparation-session",
                },
            )
            assert prepared.status_code == 200
            prepared_action = ChangeContinuationAction.model_validate(prepared.json()["engine_action"])
            assert prepared_action.kind == "mark-ready"
            prepared_result = client.post(
                "/api/changes/change-a/continuation/execute",
                json={"operation_id": prepared_action.operation_id},
            )
        assert prepared_result.status_code == 200
        assert prepared_result.json()["kind"] == "completed"
        provider.pull_requests[0] = provider.pull_requests[0].model_copy(
            update={
                "state": "closed",
                "merged": True,
                "merge_commit_sha": prepared_action.exact_head,
                "merged_at": datetime(2026, 8, 4, tzinfo=UTC),
            }
        )
        basis = application.get_change("change-a").readiness.basis.model_dump(mode="json")
    sibling_frontier = application._runtimes["change-c"].frontier_bytes()  # noqa: SLF001
    sibling_publication = application._runtimes["change-c"].checkpoint_publication_state()  # noqa: SLF001
    with TestClient(assemble_target_app(application)) as client:
        acquired = client.post(
            "/api/changes/change-a/continuation/acquire",
            json={
                "expected_basis": basis,
                "capabilities": ["planner", "builder", "finalizer", "engine"],
                "host_id": "synthetic-host",
                "session_id": "synthetic-session",
            },
        )
    assert acquired.status_code == 200
    action = ChangeContinuationAction.model_validate(acquired.json()["engine_action"])
    assert action.kind == action_kind
    original_finish = application._coordinator.finish_continuation_action  # noqa: SLF001
    failure_message = "HTTP result publication interruption"
    provider.read_pull_request = Mock(wraps=provider.read_pull_request)
    provider.observe_checks = Mock(wraps=provider.observe_checks)
    before_owner_execution = _loader_engine_state_snapshot(
        application,
        runtime_root=runtime_root,
        remote_refs=_remote_refs(remote),
        provider=provider,
        change_id="change-a",
        operation_id=action.operation_id,
    )

    def interrupt_finish(action_record, result, finished_at, *, release):
        if action_record.operation_id == action.operation_id:
            raise RuntimeError(failure_message)
        return original_finish(action_record, result, finished_at, release=release)

    with (
        patch.object(
            application._coordinator,  # noqa: SLF001
            "finish_continuation_action",
            interrupt_finish,
        ),
        TestClient(assemble_target_app(application)) as client,
        pytest.raises(RuntimeError, match="HTTP result publication interruption"),
    ):
        client.post(
            "/api/changes/change-a/continuation/execute",
            json={"operation_id": action.operation_id},
        )
    before_reload = _loader_engine_state_snapshot(
        application,
        runtime_root=runtime_root,
        remote_refs=_remote_refs(remote),
        provider=provider,
        change_id="change-a",
        operation_id=action.operation_id,
    )
    operation_journal_before_reload = before_reload["continuation_operation_journal"]
    assert operation_journal_before_reload["intent"]
    assert operation_journal_before_reload["started"]
    assert operation_journal_before_reload["result"] is None
    assert any(action.operation_id in episode.attempt_ids for episode in before_reload["retry_ledger"].episodes)
    if action_kind in {"reconcile-checkpoint", "sync-target"}:
        if action_kind == "reconcile-checkpoint":
            published_head = action.exact_head
        else:
            target_sync = application._runtimes["change-a"].target_sync_receipt()  # noqa: SLF001
            assert target_sync is not None
            published_head = target_sync.merged_head
        _assert_checkpoint_branch_operation(
            before_owner_execution,
            before_reload,
            change_id=action.change_id,
            published_head=published_head,
            expected_remote_head=before_owner_execution["checkpoint_publication"].published_head,
        )
    else:
        assert any(
            path.startswith(f"{action.change_id}/") and path != f"{action.change_id}/display.json" and content
            for path, content in before_reload["completion_journal"]
        )
    _git(repository, "remote", "set-url", "origin", "https://github.com/example/project.git")
    _git(repository, "config", f"url.{remote}.insteadOf", "https://github.com/example/project.git")
    reloaded = load_core_delivery_application(
        _startup_config(),
        workspace_root=repository,
        publication_provider=provider,
    )
    after_loader = _loader_engine_state_snapshot(
        reloaded,
        runtime_root=runtime_root,
        remote_refs=_remote_refs(remote),
        provider=provider,
        change_id="change-a",
        operation_id=action.operation_id,
    )
    expected_after_loader = dict(before_reload)
    if action_kind == "observe-acceptance":
        _assert_loader_retry_recording(
            before_reload,
            after_loader,
            action_id=action.operation_id,
            accepted_progress=True,
        )
        expected_after_loader["retry_ledger"] = after_loader["retry_ledger"]
        expected_after_loader["retry_journal"] = after_loader["retry_journal"]
    else:
        _assert_loader_retry_recording(
            before_reload,
            after_loader,
            action_id=action.operation_id,
            accepted_progress=False,
        )
    assert after_loader == expected_after_loader
    with TestClient(assemble_target_app(reloaded)) as client:
        before_containment = _loader_engine_state_snapshot(
            reloaded,
            runtime_root=runtime_root,
            remote_refs=_remote_refs(remote),
            provider=provider,
            change_id="change-a",
            operation_id=action.operation_id,
        )
        _assert_loader_observation_only(after_loader, before_containment)
        contained = client.post(
            "/api/changes/change-a/continuation/execute",
            json={"operation_id": action.operation_id},
        )
        assert contained.status_code == 200
        assert contained.json()["kind"] == "blocked"
        assert contained.json()["reason_code"] == "engine-action-interrupted"
        after_containment = _loader_engine_state_snapshot(
            reloaded,
            runtime_root=runtime_root,
            remote_refs=_remote_refs(remote),
            provider=provider,
            change_id="change-a",
            operation_id=action.operation_id,
        )
        contained_replay = client.post(
            "/api/changes/change-a/continuation/execute",
            json={"operation_id": action.operation_id},
        )
        after_replay_execution = _loader_engine_state_snapshot(
            reloaded,
            runtime_root=runtime_root,
            remote_refs=_remote_refs(remote),
            provider=provider,
            change_id="change-a",
            operation_id=action.operation_id,
        )
        guidance = client.get("/api/work-items")
        listed = client.get("/api/work-items")
        shown = client.get("/api/changes/change-a/work-items/publication")
        repeated_guidance = client.get("/api/work-items")
        repeated_listed = client.get("/api/work-items")
        repeated_shown = client.get("/api/changes/change-a/work-items/publication")
    assert contained_replay.status_code == 200
    assert contained_replay.json() == contained.json()
    operation_journal_after_containment = after_containment["continuation_operation_journal"]
    assert operation_journal_after_containment["intent"] == operation_journal_before_reload["intent"]
    assert operation_journal_after_containment["started"] == operation_journal_before_reload["started"]
    assert operation_journal_after_containment["result"]
    containment_record = json.loads(operation_journal_after_containment["result"])
    assert containment_record["kind"] == "blocked"
    assert containment_record["reason_code"] == "engine-action-interrupted"
    assert containment_record["action"]["operation_id"] == action.operation_id
    expected_containment = dict(before_containment)
    expected_containment["continuation_operation_journal"] = operation_journal_after_containment
    assert after_containment == expected_containment
    assert after_containment["retry_ledger"] == before_containment["retry_ledger"]
    assert after_replay_execution == after_containment
    assert guidance.status_code == listed.status_code == shown.status_code == 200
    assert guidance.json()["groups"]
    assert listed.json()["totals"]
    assert shown.json()["item"]["acceptance"] == []
    assert shown.json()["item"]["card"]["change_id"] == "change-a"
    assert shown.json()["item"]["readiness"]["basis"]["continuation_id"] == action.operation_id
    readiness = shown.json()["item"]["readiness"]
    assert readiness["reason_code"] == "engine-action-interrupted"
    assert readiness["status"] == "blocked"
    assert readiness["checks_state"] == reloaded.get_change("change-a").readiness.checks_state
    assert readiness["executable"] is False
    assert readiness["action"] is None
    assert readiness["prompt"] == (
        "/continue-change change-a only after the Delivery engine owner verifies host/worker closure and settles "
        "all descendant writers and jobs; preserve custody and journals, and do not retry or infer termination."
    )
    next_step = shown.json()["item"]["card"]["next_step"]
    assert "Delivery engine owner" in next_step
    assert "Preserve custody and journals" in next_step
    assert "all descendant writers and jobs" in next_step
    assert "do not retry" in next_step
    assert shown.json()["item"]["card"]["next_actor"] == "agent"
    assert guidance.json() == repeated_guidance.json()
    assert listed.json() == repeated_listed.json()
    assert shown.json() == repeated_shown.json()
    assert reloaded.get_change("change-a").continuation_action == action
    assert reloaded.get_change("change-a").continuation_action.finished_at is None
    assert reloaded._runtimes["change-c"].frontier_bytes() == sibling_frontier  # noqa: SLF001
    assert reloaded._runtimes["change-c"].checkpoint_publication_state() == sibling_publication  # noqa: SLF001
    after_read_only_views = _loader_engine_state_snapshot(
        reloaded,
        runtime_root=runtime_root,
        remote_refs=_remote_refs(remote),
        provider=provider,
        change_id="change-a",
        operation_id=action.operation_id,
    )
    _assert_loader_observation_only(after_containment, after_read_only_views)


@pytest.mark.parametrize("writer_recorded", [False, True])
def test_http_default_loader_contains_failed_claim_activation(  # noqa: PLR0915 - verify persisted activation and independent restart progress.
    tmp_path: Path,
    *,
    writer_recorded: bool,
) -> None:
    repository, _runtime_root = _seed_loader_composed_completed_change(
        tmp_path,
        (("change-a", DeliveryStage.IMPLEMENTATION), ("change-b", DeliveryStage.IMPLEMENTATION)),
    )
    application = load_core_delivery_application(_startup_config(), workspace_root=repository)
    coordinator = application._coordinator  # noqa: SLF001
    acquire = coordinator.acquire

    def fail(change_id: str, writer: object, **kwargs: object) -> None:
        if writer_recorded:
            acquire(change_id, writer, **kwargs)
        failure_message = "injected writer persistence failure"
        raise OSError(failure_message)

    basis = application.get_change("change-a").readiness.basis.model_dump(mode="json")
    with (
        patch.object(coordinator, "acquire", fail),
        TestClient(assemble_target_app(application)) as client,
    ):
        result = client.post(
            "/api/changes/change-a/continuation/acquire",
            json={
                "expected_basis": basis,
                "capabilities": ["builder"],
                "host_id": "synthetic-host",
                "session_id": "synthetic-session",
            },
        )
    assert result.status_code == 200
    payload = result.json()
    assert payload["kind"] == "unavailable"
    assert payload["reason_code"] == "claim-activation-failed"
    assert payload["launch"] is None
    assert payload["readiness"]["prompt"].startswith("/repair-delivery")
    assert "read-only" in payload["readiness"]["prompt"]
    assert payload["failure"]["claim_id"]
    assert payload["failure"]["attempt_id"]
    assert (coordinator.show("change-a").writer is not None) is writer_recorded
    failed_claim = application._runtimes["change-a"].show_binding("OUT-001").active_claim  # noqa: SLF001
    failed_episode = application._runtimes["change-a"].retry_ledger().read().episodes[0]  # noqa: SLF001
    assert failed_claim is not None
    assert (failed_claim.claim_id, failed_claim.attempt_id) == (
        payload["failure"]["claim_id"],
        payload["failure"]["attempt_id"],
    )
    assert failed_episode.attempt_ids == (failed_claim.attempt_id,)
    before_reload = _loader_activation_state_snapshot(application)
    reloaded = load_core_delivery_application(_startup_config(), workspace_root=repository)
    assert _loader_activation_state_snapshot(reloaded) == before_reload
    reloaded_coordinator = reloaded._coordinator  # noqa: SLF001
    reloaded_runtime = reloaded._runtimes["change-a"]  # noqa: SLF001
    assert reloaded_runtime.show_binding("OUT-001").active_claim == failed_claim
    assert reloaded_runtime.retry_ledger().read().episodes == (failed_episode,)
    assert (reloaded_coordinator.show("change-a").writer is not None) is writer_recorded
    coordination_path = reloaded_coordinator.runtime_root / "coordination/changes/change-a.json"
    coordination_before = coordination_path.read_bytes()
    with TestClient(assemble_target_app(reloaded)) as client:
        first_read = client.get("/api/work-items")
        second_read = client.get("/api/work-items")
        assert first_read.status_code == second_read.status_code == 200
        assert second_read.json() == first_read.json()
        first_readiness = next(
            item["readiness"]
            for group in first_read.json()["groups"]
            for item in group["items"]
            if item["change_id"] == "change-a" and item["scope"] == "outcome"
        )
        assert first_readiness["executable"] is False
        assert first_readiness["prompt"].startswith("/repair-delivery")
        assert "dispatch a replacement" in first_readiness["prompt"]
        blocked = client.post(
            "/api/changes/change-a/continuation/acquire",
            json={
                "expected_basis": first_readiness["basis"],
                "capabilities": ["builder"],
                "host_id": "synthetic-host",
                "session_id": "retry-after-restart",
            },
        )
    after_refusal = _loader_activation_state_snapshot(reloaded)
    assert after_refusal == before_reload
    with TestClient(assemble_target_app(reloaded)) as client:
        sibling_read = client.get("/api/work-items")
        assert sibling_read.status_code == 200
        sibling_readiness = next(
            item["readiness"]
            for group in sibling_read.json()["groups"]
            for item in group["items"]
            if item["change_id"] == "change-b" and item["scope"] == "outcome"
        )
        sibling_result = client.post(
            "/api/changes/change-b/continuation/acquire",
            json={
                "expected_basis": sibling_readiness["basis"],
                "capabilities": ["builder"],
                "host_id": "synthetic-host",
                "session_id": "sibling-after-restart",
            },
        )
    assert blocked.status_code == 200
    assert blocked.json()["launch"] is None
    assert blocked.json()["reason_code"] == ("active-custody" if writer_recorded else "claim-custody-unreconciled")
    assert coordination_path.read_bytes() == coordination_before
    assert reloaded_runtime.show_binding("OUT-001").active_claim == failed_claim
    assert reloaded_runtime.retry_ledger().read().episodes == (failed_episode,)
    assert sibling_result.status_code == 200
    assert sibling_result.json()["kind"] == "acquired"
    assert sibling_result.json()["launch"] is not None
    assert reloaded._runtimes["change-b"].show_binding("OUT-001").active_claim is not None  # noqa: SLF001
    after_sibling_progress = _loader_activation_state_snapshot(reloaded)
    before_changes = before_reload["changes"]
    after_changes = after_sibling_progress["changes"]
    assert after_changes["change-a"] == before_changes["change-a"]
    assert after_changes["change-b"]["frontier"] != before_changes["change-b"]["frontier"]
    assert after_changes["change-b"]["workspace"] == before_changes["change-b"]["workspace"]
    assert after_sibling_progress["repository_refs"] == before_reload["repository_refs"]


def test_http_finalizer_handoff_contains_failure_before_checks(tmp_path: Path) -> None:
    _repository, _runtime_root, _remote, _provider, application = _loader_registered_engine_action_fixture(
        tmp_path, "sync-target"
    )
    basis = application.get_change("change-a").readiness.basis.model_dump(mode="json")
    with TestClient(assemble_target_app(application)) as client:
        synchronized = client.post(
            "/api/changes/change-a/continuation/acquire",
            json={
                "expected_basis": basis,
                "capabilities": ["engine"],
                "host_id": "synthetic-host",
                "session_id": "sync-session",
            },
        )
        assert synchronized.status_code == 200
        sync_action = synchronized.json()["engine_action"]
        assert sync_action is not None
        assert sync_action["kind"] == "sync-target"
        executed_sync = client.post(
            "/api/changes/change-a/continuation/execute",
            json={"operation_id": sync_action["operation_id"]},
        )
        assert executed_sync.status_code == 200
        assert executed_sync.json()["kind"] == "completed"

        detail = client.get("/api/changes/change-a/work-items/publication")
        assert detail.status_code == 200
        finalizer_basis = detail.json()["item"]["readiness"]["basis"]
        acquired = client.post(
            "/api/changes/change-a/continuation/acquire",
            json={
                "expected_basis": finalizer_basis,
                "capabilities": ["finalizer"],
                "host_id": "synthetic-host",
                "session_id": "finalizer-session",
            },
        )
        assert acquired.status_code == 200
        finalization = acquired.json()["finalization"]
        assert finalization is not None
        (
            application._coordinator.show("change-a").worktree_path / "product.txt"  # noqa: SLF001
        ).write_text("dirty before checks\n", encoding="utf-8")
        finalization_basis = application.show_finalization_context("change-a").readiness.basis
        failure = _failure_request(
            application,
            attempt_key=finalization["attempt"]["writer"]["attempt_id"],
            category="custody-preflight",
            code=FinalizationFailureCode.WORKSPACE_DIRTY,
            checks_state="not-run",
            expected_workspace_fingerprint=finalization_basis.workspace_fingerprint,
            paths=("product.txt",),
        )
        retry_now = datetime.now(UTC).isoformat()
        application._clock = lambda: retry_now  # noqa: SLF001
        report = application.report_finalization_failure(failure)

        current = client.get("/api/changes/change-a/work-items/publication")
        assert current.status_code == 200
        current_readiness = current.json()["item"]["readiness"]
        stopped = client.post(
            "/api/changes/change-a/continuation/acquire",
            json={
                "expected_basis": current_readiness["basis"],
                "capabilities": ["finalizer"],
                "host_id": "synthetic-host",
                "session_id": "finalizer-session-2",
            },
        )
    assert stopped.status_code == 200
    assert stopped.json()["kind"] == "busy"
    assert stopped.json()["reason_code"] == "active-custody"
    assert stopped.json()["finalization"] is None
    assert stopped.json()["readiness"]["checks_state"] == "not-run"
    assert application.get_change("change-a").readiness.last_attempt.report == report
    assert application._coordinator.show("change-a").writer is not None  # noqa: SLF001


def test_http_finalizer_handoff_refusal_survives_restart_without_mutation(  # noqa: PLR0915 - restart safety proof.
    tmp_path: Path,
) -> None:
    repository, runtime_root, remote, provider, application = _loader_registered_engine_action_fixture(
        tmp_path, "sync-target"
    )
    basis = application.get_change("change-a").readiness.basis.model_dump(mode="json")
    with TestClient(assemble_target_app(application)) as client:
        acquired_sync = client.post(
            "/api/changes/change-a/continuation/acquire",
            json={
                "expected_basis": basis,
                "capabilities": ["engine"],
                "host_id": "synthetic-host",
                "session_id": "sync-session",
            },
        )
        assert acquired_sync.status_code == 200
        sync_action = acquired_sync.json()["engine_action"]
        assert sync_action is not None
        assert sync_action["kind"] == "sync-target"
        executed_sync = client.post(
            "/api/changes/change-a/continuation/execute",
            json={"operation_id": sync_action["operation_id"]},
        )
        assert executed_sync.status_code == 200
        publication = client.get("/api/changes/change-a/work-items/publication")
        assert publication.status_code == 200
        finalizer_basis = publication.json()["item"]["readiness"]["basis"]
        acquired_finalizer = client.post(
            "/api/changes/change-a/continuation/acquire",
            json={
                "expected_basis": finalizer_basis,
                "capabilities": ["finalizer"],
                "host_id": "synthetic-host",
                "session_id": "finalizer-session",
            },
        )
        assert acquired_finalizer.status_code == 200
        finalization = acquired_finalizer.json()["finalization"]
        assert finalization is not None
        worktree = application._coordinator.show("change-a").worktree_path  # noqa: SLF001
        (worktree / "product.txt").write_text("dirty before checks\n", encoding="utf-8")
        finalization_basis = application.show_finalization_context("change-a").readiness.basis
        failure = _failure_request(
            application,
            attempt_key=finalization["attempt"]["writer"]["attempt_id"],
            category="custody-preflight",
            code=FinalizationFailureCode.WORKSPACE_DIRTY,
            checks_state="not-run",
            expected_workspace_fingerprint=finalization_basis.workspace_fingerprint,
            paths=("product.txt",),
        )
        retry_now = datetime.now(UTC).isoformat()
        application._clock = lambda: retry_now  # noqa: SLF001
        report = application.report_finalization_failure(failure)

    report_root = runtime_root / "finalization-reports/change-a"

    def report_files() -> tuple[tuple[str, bytes], ...]:
        return tuple(
            (path.relative_to(report_root).as_posix(), path.read_bytes())
            for path in sorted(report_root.rglob("*.json"))
            if path.is_file()
        )

    assert report_files()
    _git(repository, "remote", "set-url", "origin", "https://github.com/example/project.git")
    _git(repository, "config", f"url.{remote}.insteadOf", "https://github.com/example/project.git")

    def state_snapshot(candidate: PortfolioApplication) -> dict[str, object]:
        candidate_coordinator = candidate._coordinator  # noqa: SLF001
        candidate_runtime = candidate._runtimes["change-a"]  # noqa: SLF001
        return {
            "coordination": (candidate_coordinator.runtime_root / "coordination/changes/change-a.json").read_bytes(),
            "frontier": candidate_runtime.frontier_bytes(),
            "retry_ledger": candidate_runtime.retry_ledger().read(),
            "workspace": _workspace_mutation_snapshot(candidate_coordinator.show("change-a").worktree_path),
            "remote_refs": _remote_refs(remote),
            "writer": candidate_coordinator.show("change-a").writer,
            "report_files": report_files(),
            "provider_mutations": (provider.create_calls, provider.update_calls, provider.draft_state_calls),
        }

    before_reload = state_snapshot(application)
    reloaded = load_core_delivery_application(
        _startup_config(),
        workspace_root=repository,
        publication_provider=provider,
    )
    reloaded._clock = lambda: retry_now  # noqa: SLF001
    after_reload = state_snapshot(reloaded)
    assert after_reload == before_reload
    with TestClient(assemble_target_app(reloaded)) as client:
        detail = client.get("/api/changes/change-a/work-items/publication")
        repeated = client.get("/api/changes/change-a/work-items/publication")
        assert detail.status_code == repeated.status_code == 200
        assert detail.json() == repeated.json()
        readiness = detail.json()["item"]["readiness"]
        assert readiness["checks_state"] == "not-run"
        assert readiness["last_attempt"]["report"] == report.model_dump(mode="json")
        refused = client.post(
            "/api/changes/change-a/continuation/acquire",
            json={
                "expected_basis": readiness["basis"],
                "capabilities": ["finalizer"],
                "host_id": "synthetic-host",
                "session_id": "finalizer-after-restart",
            },
        )
    assert refused.status_code == 200
    assert refused.json()["kind"] == "busy", refused.json()
    assert refused.json()["reason_code"] == "active-custody"
    assert refused.json()["finalization"] is None
    assert refused.json()["readiness"]["checks_state"] == "not-run"
    assert state_snapshot(reloaded) == after_reload


def test_http_default_loader_rejects_stale_basis_without_acquisition(tmp_path: Path) -> None:
    _repository, _runtime_root, _remote, provider, application, _head_a, _head_b = _loader_composed_engine_fixture(
        tmp_path
    )
    basis = application.get_change("change-a").readiness.basis.model_dump(mode="json")
    with TestClient(assemble_target_app(application)) as client:
        result = client.post(
            "/api/changes/change-a/continuation/acquire",
            json={
                "expected_basis": {**basis, "frontier_digest": "0" * 64},
                "capabilities": ["engine"],
                "host_id": "synthetic-host",
                "session_id": "synthetic-session",
            },
        )
    assert result.status_code == 200
    assert result.json()["kind"] == "stale"
    assert result.json()["reason_code"] == "readiness-changed"
    assert result.json()["launch"] is None
    assert provider.draft_state_calls == 0


@pytest.mark.parametrize("coordination_state", ["malformed", "missing"])
def test_http_default_loader_reports_unavailable_custody(tmp_path: Path, coordination_state: str) -> None:  # noqa: PLR0915
    repository, _runtime_root, remote, provider, application, _head_a, _head_b = _loader_composed_engine_fixture(
        tmp_path
    )
    coordination = application._coordinator.runtime_root / "coordination/changes/change-a.json"  # noqa: SLF001
    malformed_marker = b"PRIVATE-MALFORMED-COORDINATION-CONTENT"
    if coordination_state == "malformed":
        coordination.write_bytes(malformed_marker)
    else:
        coordination.unlink()
    _git(repository, "remote", "set-url", "origin", "https://github.com/example/project.git")
    _git(repository, "config", f"url.{remote}.insteadOf", "https://github.com/example/project.git")
    reloaded = load_core_delivery_application(
        _startup_config(),
        workspace_root=repository,
        publication_provider=provider,
    )
    coordination_before = coordination.read_bytes() if coordination.exists() else None
    remote_refs_before = _remote_refs(remote)
    with TestClient(assemble_target_app(reloaded)) as client:
        result = client.post(
            "/api/changes/change-a/continuation/acquire",
            json={
                "expected_basis": {"contract_digest": "a" * 64, "frontier_digest": "b" * 64},
                "capabilities": ["engine"],
                "host_id": "synthetic-host",
                "session_id": "synthetic-session",
            },
        )
        repeated = client.post(
            "/api/changes/change-a/continuation/acquire",
            json={
                "expected_basis": {"contract_digest": "a" * 64, "frontier_digest": "b" * 64},
                "capabilities": ["engine"],
                "host_id": "synthetic-host",
                "session_id": "repeated-read",
            },
        )
        portfolio = client.get("/api/work-items")
        repeated_portfolio = client.get("/api/work-items")
        detail = client.get("/api/changes/change-a/work-items/publication")
    assert result.status_code == 200
    assert repeated.status_code == 200
    assert result.json() == repeated.json()
    assert result.json()["kind"] == "unavailable"
    assert result.json()["reason_code"] == "coordination-unavailable"
    assert result.json()["engine_action"] is None
    assert portfolio.status_code == repeated_portfolio.status_code == 200
    assert portfolio.json() == repeated_portfolio.json()
    assert detail.status_code == 200
    readiness = detail.json()["item"]["readiness"]
    assert readiness["status"] == "unavailable"
    assert readiness["checks_state"] == "unknown"
    assert readiness["prompt"] == (
        "Do not release, retry, or redispatch Change change-a: canonical Delivery authority is unavailable "
        "(coordination-unavailable); checks are unknown. Preserve existing custody and journals. Use "
        "/repair-delivery Diagnose Change change-a read-only; preserve existing custody and journals. This does "
        "not repair authority or prove host/worker closure; the responsible owner must resolve the condition "
        "separately before Delivery rereads it."
    )
    assert (coordination.read_bytes() if coordination.exists() else None) == coordination_before
    assert _remote_refs(remote) == remote_refs_before
    assert provider.draft_state_calls == 0

    def tree_snapshot(root: Path) -> tuple[tuple[str, str, bytes | str | None], ...]:
        entries = []
        for path in (root, *sorted(root.rglob("*"))):
            relative = path.relative_to(root.parent).as_posix()
            if path.is_symlink():
                entries.append((relative, "symlink", path.readlink().as_posix()))
            elif path.is_dir():
                entries.append((relative, "directory", None))
            elif path.is_file():
                entries.append((relative, "file", path.read_bytes()))
            else:
                entries.append((relative, "other", None))
        return tuple(entries)

    repository_before_cli = tree_snapshot(repository)
    diagnostics_cli = subprocess.run(  # noqa: S603
        (
            sys.executable,
            "-B",
            str(Path(__file__).resolve().parents[1] / "serve/tools/src/owlbear_tools/delivery_diagnostics.py"),
            "inspect",
            "--project-root",
            str(repository),
            "--change-id",
            "change-a",
            "--format",
            "json",
        ),
        cwd=repository,
        check=False,
        capture_output=True,
        text=True,
    )
    assert diagnostics_cli.returncode == 1
    diagnostics = json.loads(diagnostics_cli.stdout)
    assert diagnostics["status"] == "degraded"
    assert diagnostics["change_scope"] == "selected"
    expected_coordination_diagnostic = (
        "COORDINATION_MALFORMED" if coordination_state == "malformed" else "COORDINATION_MISSING"
    )
    assert expected_coordination_diagnostic in diagnostics["diagnostic_codes"]
    if coordination_state == "missing":
        assert diagnostics["inspection_complete"] is False
        assert "PENDING_EFFECTS_UNKNOWN" in diagnostics["diagnostic_codes"]
        assert diagnostics["pending_effects"] == "unknown"
    assert diagnostics["writes_performed"] is False
    if coordination_state == "malformed":
        assert malformed_marker.decode() not in diagnostics_cli.stdout + diagnostics_cli.stderr
    assert tree_snapshot(repository) == repository_before_cli
    assert _remote_refs(remote) == remote_refs_before
    assert provider.draft_state_calls == 0


def test_http_and_offline_diagnostics_bound_an_unknown_change_without_mutation(tmp_path: Path) -> None:
    repository, _runtime_root, remote, provider, _application, _head_a, _head_b = _loader_composed_engine_fixture(
        tmp_path
    )
    _git(repository, "remote", "set-url", "origin", "https://github.com/example/project.git")
    _git(repository, "config", f"url.{remote}.insteadOf", "https://github.com/example/project.git")
    reloaded = load_core_delivery_application(
        _startup_config(),
        workspace_root=repository,
        publication_provider=provider,
    )

    def tree_snapshot(root: Path) -> tuple[tuple[str, str, bytes | str | None], ...]:
        entries = []
        for path in (root, *sorted(root.rglob("*"))):
            relative = path.relative_to(root.parent).as_posix()
            if path.is_symlink():
                entries.append((relative, "symlink", path.readlink().as_posix()))
            elif path.is_dir():
                entries.append((relative, "directory", None))
            elif path.is_file():
                entries.append((relative, "file", path.read_bytes()))
            else:
                entries.append((relative, "other", None))
        return tuple(entries)

    repository_before = tree_snapshot(repository)
    remote_refs_before = _remote_refs(remote)
    provider_calls_before = provider.draft_state_calls
    with TestClient(assemble_target_app(reloaded)) as client:
        first = client.get("/api/changes/change-missing/work-items/publication")
        repeated = client.get("/api/changes/change-missing/work-items/publication")
    assert first.status_code == repeated.status_code == 409
    assert first.json() == repeated.json()
    assert first.json()["code"] == "ERR_DELIVERY_PORTFOLIO"
    diagnostics_cli = subprocess.run(  # noqa: S603
        (
            sys.executable,
            "-B",
            str(Path(__file__).resolve().parents[1] / "serve/tools/src/owlbear_tools/delivery_diagnostics.py"),
            "inspect",
            "--project-root",
            str(repository),
            "--change-id",
            "change-missing",
            "--format",
            "json",
        ),
        cwd=repository,
        check=False,
        capture_output=True,
        text=True,
    )
    assert diagnostics_cli.returncode == 1
    diagnostics = json.loads(diagnostics_cli.stdout)
    assert diagnostics["status"] == "degraded"
    assert diagnostics["change_scope"] == "selected"
    assert "CHANGE_NOT_FOUND" not in diagnostics["diagnostic_codes"]
    assert "CONFIG_MISSING" in diagnostics["diagnostic_codes"]
    assert diagnostics["pending_effects"] is False
    assert diagnostics["inspection_complete"] is False
    assert diagnostics["writes_performed"] is False
    assert repository_before == tree_snapshot(repository)
    assert _remote_refs(remote) == remote_refs_before
    assert provider.draft_state_calls == provider_calls_before


def _remote_refs(repository: Path) -> str:
    result = subprocess.run(  # noqa: S603
        (  # noqa: S607
            "git",
            "-c",
            "safe.bareRepository=all",
            "-C",
            str(repository),
            "for-each-ref",
            "--format=%(refname) %(objectname)",
        ),
        check=False,
        capture_output=True,
        text=True,
    )
    return f"{result.returncode}\n{result.stdout}\n{result.stderr}"


def _client(
    failures: dict[str, Exception] | None = None,
    health: DeliveryHealthView | None = None,
    unavailable_changes: tuple[DeliveryUnavailableChangeView, ...] = (),
) -> tuple[TestClient, _DeliveryApplicationFake]:
    application = _DeliveryApplicationFake(failures, health, unavailable_changes)
    return TestClient(assemble_target_app(application)), application  # type: ignore[arg-type]


def test_startup_loads_shared_delivery_configuration(
    tmp_path: Path,
) -> None:
    workspace_root = tmp_path / "workspace"
    config = DeliveryStartupConfig(
        schema_version=2,
        remote="origin",
        target_branch="dev",
        github_repository="example/project",
    )
    config_path = workspace_root / ".owlbear/delivery/config.json"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(config.model_dump_json(by_alias=True), encoding="utf-8")
    application = object()

    with patch(
        "owlbear_cockpit.target_context.load_delivery_application",
        return_value=application,
    ) as load:
        result = load_target_context(workspace_root)

    assert result is application
    load.assert_called_once()
    call = load.call_args
    assert call.args == (config,)
    assert call.kwargs["workspace_root"] == workspace_root
    assert isinstance(call.kwargs["publication_provider"], GitHubCliPublicationProvider)


def test_startup_discovers_workspace_delivery_configuration(
    tmp_path: Path,
) -> None:
    workspace_root = tmp_path / "workspace"
    config = DeliveryStartupConfig(
        schema_version=2,
        remote="origin",
        target_branch="dev",
        github_repository="example/project",
    )
    config_path = workspace_root / ".owlbear/delivery/config.json"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(config.model_dump_json(by_alias=True), encoding="utf-8")
    application = object()
    with patch(
        "owlbear_cockpit.target_context.load_delivery_application",
        return_value=application,
    ) as load:
        result = load_target_context(workspace_root)

    assert result is application
    load.assert_called_once()
    call = load.call_args
    assert call.args == (config,)
    assert call.kwargs["workspace_root"] == workspace_root
    assert isinstance(call.kwargs["publication_provider"], GitHubCliPublicationProvider)


def test_startup_surfaces_delivery_load_failure(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    config = DeliveryStartupConfig(
        schema_version=2,
        remote="origin",
        target_branch="dev",
        github_repository="example/project",
    )
    config_path = workspace_root / ".owlbear/delivery/config.json"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(config.model_dump_json(by_alias=True), encoding="utf-8")
    load_error = DeliveryApplicationLoadError("runtime_root", "legacy runtime state is unsupported")

    with (
        patch("owlbear_cockpit.target_context.load_delivery_application", side_effect=load_error),
        pytest.raises(
            RuntimeError,
            match="Cockpit Delivery startup failed for runtime_root: legacy runtime state is unsupported",
        ),
    ):
        load_target_context(workspace_root)


def test_list_and_detail_expose_current_bounded_delivery_state() -> None:
    client, application = _client()

    portfolio = client.get("/api/work-items")
    detail = client.get("/api/changes/change-a/work-items/outcome:OUT-001")

    assert portfolio.status_code == 200
    assert portfolio.json()["totals"] == {
        "total": 3,
        "complete": 1,
        "needs": {"you": 1, "dependency": 0, "none": 2},
        "activity": {"idle": 0, "ready": 3, "working": 0},
    }
    assert portfolio.json()["operating"] == {
        "unfinished_change_count": 2,
        "completed_change_count": 0,
        "statuses": [
            {
                "change_id": "draft-change",
                "admission": "unadmitted",
                "stage": "design",
                "actionable_runtime": False,
                "diagnostic_code": None,
                "diagnostic_detail": None,
            },
            {
                "change_id": "admitted-planning",
                "admission": "admitted",
                "stage": "building",
                "actionable_runtime": True,
                "diagnostic_code": None,
                "diagnostic_detail": None,
            },
            {
                "change_id": "design-reentry",
                "admission": "admitted",
                "stage": "design",
                "actionable_runtime": True,
                "diagnostic_code": None,
                "diagnostic_detail": None,
            },
            {
                "change_id": "unavailable-change",
                "admission": "admitted",
                "stage": "building",
                "actionable_runtime": False,
                "diagnostic_code": "runtime_unavailable",
                "diagnostic_detail": "Delivery runtime is unavailable.",
            },
        ],
        "draft_design_change_ids": [],
        "design_required_change_ids": [],
        "claimed": [],
        "queued_for_orchestration": [],
        "interventions": [{"change_id": "change-a", "item_key": "outcome:OUT-001", "scope": "outcome"}],
        "dependency_waits": [],
        "guidance": [
            {"kind": "intervene", "change_ids": ["change-a"], "work_count": 1},
        ],
    }
    first = portfolio.json()["groups"][0]["items"][0]
    assert first["stage"] == "planning"
    assert first["needs"] == "you"
    assert detail.status_code == 200
    assert detail.json()["item"]["acceptance"] == []
    assert detail.json()["item"]["block"] is None
    assert detail.json()["item"]["requests"] == []
    assert "process_id" not in json.dumps((portfolio.json(), detail.json()))
    assert application.calls == [
        ("portfolio", ()),
        ("show", ("change-a", "outcome:OUT-001")),
    ]


def test_list_and_detail_preserve_known_unavailable_change_projection() -> None:
    unavailable = DeliveryUnavailableChangeView(
        change_id="unavailable-change",
        title="Unreadable Change",
        readiness=DeliveryReadiness(
            status="unavailable",
            next_actor=WorkItemNextActor.NONE,
            reason_code="runtime-unavailable",
            checks_state="unknown",
            basis=DeliveryReadinessBasis(contract_digest="a" * 64),
        ),
    )
    client, application = _client(unavailable_changes=(unavailable,))

    portfolio = client.get("/api/work-items")
    detail = client.get("/api/changes/unavailable-change/work-items/outcome:OUT-001")

    assert portfolio.status_code == 200
    assert portfolio.json()["groups"]
    assert portfolio.json()["unavailable_changes"] == [
        {
            "kind": "unavailable",
            "change_id": "unavailable-change",
            "title": "Unreadable Change",
            "diagnostics": ["runtime-unavailable"],
            "coordination_status": None,
            "readiness": {
                "status": "unavailable",
                "operation": None,
                "executable": False,
                "next_actor": "none",
                "reason_code": "runtime-unavailable",
                "checks_state": "unknown",
                "basis": {
                    "contract_digest": "a" * 64,
                    "frontier_digest": None,
                    "source_head": None,
                    "target_head": None,
                    "continuation_id": None,
                    "candidate_head": None,
                    "reviewed_head": None,
                    "workspace_fingerprint": None,
                    "diagnostic_sequence": None,
                },
                "action": None,
                "last_attempt": None,
                "attempts": 0,
                "next_eligible_at": None,
                "stop_reason": None,
                "retry_history": [],
                "prompt": None,
            },
        },
    ]
    assert detail.status_code == 200
    assert detail.json() == portfolio.json()["unavailable_changes"][0]
    assert application.calls == [
        ("portfolio", ()),
        ("show", ("unavailable-change", "outcome:OUT-001")),
    ]


def test_unavailable_projection_preserves_coordination_evidence() -> None:
    unavailable = DeliveryUnavailableChangeView(
        change_id="unavailable-change",
        title="Unreadable Change",
        diagnostics=("runtime-unavailable", "coordination-unavailable"),
        coordination_status="unreadable",
        readiness=DeliveryReadiness(
            status="unavailable",
            next_actor=WorkItemNextActor.NONE,
            reason_code="coordination-unavailable",
            checks_state="unknown",
            basis=DeliveryReadinessBasis(),
        ),
    )
    client, _application = _client(unavailable_changes=(unavailable,))

    portfolio = client.get("/api/work-items").json()["unavailable_changes"][0]
    detail = client.get("/api/changes/unavailable-change/work-items/outcome:OUT-001").json()

    assert portfolio["diagnostics"] == ["runtime-unavailable", "coordination-unavailable"]
    assert portfolio["coordination_status"] == "unreadable"
    assert portfolio["readiness"]["reason_code"] == "coordination-unavailable"
    assert detail == portfolio


def _acquisition_body() -> dict[str, object]:
    return {
        "expected_basis": {
            "contract_digest": "a" * 64,
            "frontier_digest": "b" * 64,
            "source_head": "d" * 40,
            "target_head": "e" * 40,
        },
        "capabilities": ["builder", "engine"],
        "host_id": "cockpit-host",
        "session_id": "cockpit-session",
    }


def test_continuation_acquisition_forwards_selected_change_and_preserves_launch() -> None:
    client, application = _client()

    response = client.post("/api/changes/change-a/continuation/acquire", json=_acquisition_body())

    assert response.status_code == 200
    payload = response.json()
    assert payload["kind"] == "acquired"
    assert payload["reason_code"] == "ready"
    assert payload["launch"] is None
    assert payload["finalization"] is None
    assert payload["engine_action"] == {
        "operation_id": CONTINUATION_ID,
        "change_id": "change-a",
        "kind": "sync-target",
        "contract_digest": "a" * 64,
        "frontier_digest": "b" * 64,
        "exact_head": "d" * 40,
        "target_head": "e" * 40,
        "finalization_id": None,
        "host_id": "cockpit-host",
        "session_id": "cockpit-session",
        "acquired_at": "2026-09-13T00:00:00Z",
        "finished_at": None,
    }
    assert payload["readiness"]["basis"]["continuation_id"] == CONTINUATION_ID
    assert payload["readiness"]["basis"]["target_head"] == "e" * 40
    request = application.calls[0][1][0]
    assert isinstance(request, DeliveryContinuationRequest)
    assert request.change_id == "change-a"
    assert request.capabilities == ("builder", "engine")
    assert request.host_id == "cockpit-host"
    assert request.expected_basis.target_head == "e" * 40


def test_continuation_acquisition_preserves_blocked_engine_evidence() -> None:
    client, _application = _client()

    response = client.post("/api/changes/blocked-change/continuation/acquire", json=_acquisition_body())

    assert response.status_code == 200
    payload = response.json()
    assert payload["kind"] == "unavailable"
    assert payload["reason_code"] == "engine-action-interrupted"
    assert payload["engine_result"]["kind"] == "blocked"
    assert payload["engine_result"]["action"]["operation_id"] == CONTINUATION_ID
    assert payload["failure"] == payload["engine_result"]["failure"]
    assert payload["failure"]["retry_condition"] == "Recover the retained engine action custody."


@pytest.mark.parametrize(
    ("change_id", "kind", "reason_code"),
    [
        ("waiting-change", "waiting", "host-capability-unavailable"),
        ("stale-change", "stale", "readiness-changed"),
        ("human-change", "human", "merge-approval-required"),
    ],
)
def test_continuation_acquisition_forwards_non_acquired_envelopes_exactly(
    change_id: str,
    kind: str,
    reason_code: str,
) -> None:
    client, application = _client()

    response = client.post(f"/api/changes/{change_id}/continuation/acquire", json=_acquisition_body())

    assert response.status_code == 200
    payload = response.json()
    assert payload["change_id"] == change_id
    assert payload["kind"] == kind
    assert payload["reason_code"] == reason_code
    assert payload["launch"] is None
    assert payload["finalization"] is None
    assert payload["engine_action"] is None
    assert payload["engine_result"] is None
    assert payload["failure"] is None
    assert payload["readiness"]["basis"]["continuation_id"] == CONTINUATION_ID
    assert [call[0] for call in application.calls] == ["continuation-acquire"]


@pytest.mark.parametrize(
    "body",
    [
        {**_acquisition_body(), "change_id": "change-b"},
        {**_acquisition_body(), "kind": "acquired"},
        {**_acquisition_body(), "engine_action": {"operation_id": CONTINUATION_ID}},
        {**_acquisition_body(), "capabilities": ["merger"]},
        {key: value for key, value in _acquisition_body().items() if key != "host_id"},
    ],
)
def test_continuation_acquisition_rejects_caller_authored_effects(body: dict[str, object]) -> None:
    client, application = _client()

    response = client.post("/api/changes/change-a/continuation/acquire", json=body)

    assert response.status_code == 422
    assert application.calls == []


def test_continuation_execution_forwards_only_the_retained_operation() -> None:
    client, application = _client()

    response = client.post(
        "/api/changes/change-a/continuation/execute",
        json={"operation_id": CONTINUATION_ID},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["kind"] == "completed"
    assert payload["reason_code"] == "engine-action-completed"
    assert payload["failure"] is None
    assert payload["target_sync"]["merged_head"] == "f" * 40
    assert payload["checkpoint"] is None
    assert payload["checkpoint_snapshot"] is None
    request = application.calls[0][1][0]
    assert isinstance(request, ExecuteDeliveryChangeAction)
    assert request.change_id == "change-a"
    assert request.operation_id == CONTINUATION_ID


@pytest.mark.parametrize(
    "body",
    [
        {"operation_id": CONTINUATION_ID, "change_id": "change-b"},
        {"operation_id": CONTINUATION_ID, "confirmed_lost": True},
        {"operation_id": CONTINUATION_ID, "kind": "completed"},
        {"operation_id": CONTINUATION_ID, "commands": ["git status"]},
        {"operation_id": CONTINUATION_ID, "budget": 1},
        {"operation_id": CONTINUATION_ID, "receipt": {"success": True}},
        {"operation_id": CONTINUATION_ID, "stop_assertion": True},
        {"operation_id": "sync-change-a"},
        {},
    ],
)
def test_continuation_execution_rejects_caller_authored_effects(body: dict[str, object]) -> None:
    client, application = _client()

    response = client.post("/api/changes/change-a/continuation/execute", json=body)

    assert response.status_code == 422
    assert application.calls == []


def test_continuation_execution_preserves_typed_busy_failure() -> None:
    client, _application = _client(
        failures={"execute_change_action": DeliveryActionBusyError("change-a is locked by another operation")},
    )

    response = client.post(
        "/api/changes/change-a/continuation/execute",
        json={"operation_id": CONTINUATION_ID},
    )

    assert response.status_code == 409
    assert response.json()["code"] == "ERR_DELIVERY_ACTION_BUSY"
    assert response.json()["retry_safe"] is True


def test_list_exposes_bounded_delivery_health_diagnostics() -> None:
    client, _application = _client(
        health=DeliveryHealthView(
            status=DeliveryHealthStatus.ATTENTION,
            diagnostics=(
                DeliveryHealthDiagnostic(
                    source="local-runtime",
                    code="contract-identity-invalid",
                    detail="Persisted Change contract identity is invalid",
                    change_id="quarantined-change",
                    path=".owlbear/delivery/runtime/changes/quarantined-change",
                ),
            ),
        ),
    )

    response = client.get("/api/work-items")

    assert response.status_code == 200
    assert response.json()["health"] == {
        "status": "attention",
        "diagnostics": [
            {
                "source": "local-runtime",
                "code": "contract-identity-invalid",
                "detail": "Persisted Change contract identity is invalid",
                "change_id": "quarantined-change",
                "path": ".owlbear/delivery/runtime/changes/quarantined-change",
                "retry_safe": False,
                "reason": "unknown",
                "resolution": "authority-gap",
                "expected_head": None,
                "observed_head": None,
                "observed_local_head": None,
                "head_relation": None,
            },
        ],
    }


def test_detail_target_sync_uses_target_branch_wire_contract() -> None:
    client, _application = _client()

    detail = client.get("/api/changes/change-a/work-items/publication")

    assert detail.status_code == 200
    assert detail.json()["item"]["publication"]["target_sync"] == {
        "receipt_id": "a" * 64,
        "operation_id": "sync-cockpit-test",
        "target_branch": "main",
        "expected_target": "1" * 40,
        "target_head": "1" * 40,
        "change_head_before": "2" * 40,
        "merged_head": "3" * 40,
        "merge_commit": True,
        "review_required": False,
    }


def test_design_work_detail_exposes_verified_authored_sources() -> None:
    client, application = _client()

    detail = client.get("/api/design-work/design-draft")

    assert detail.status_code == 200
    assert detail.json() == {
        "change_id": "design-draft",
        "package_id": "d" * 64,
        "intent_markdown": "# Design intent\n",
        "design_markdown": "# Design architecture\n",
    }
    assert application.calls == [("show-design", ("design-draft",))]


def test_controls_require_exact_confirmation_and_delegate_once() -> None:
    client, application = _client()

    answer = client.post(
        "/api/changes/change-a/requests/request-one/answer",
        json={"selected_option_id": "option-a", "expected_frontier_digest": "a" * 64},
    )
    clear = client.post(
        "/api/changes/change-a/outcomes/OUT-001/blocks/block-one/clear",
        json={
            "operator_note": "Verified externally",
            "locators": ["request:REQ-001"],
            "expected_frontier_digest": "a" * 64,
        },
    )
    rejected_recovery = client.post(
        "/api/changes/change-a/outcomes/OUT-001/claims/recover",
        json={"confirmed_lost": False, "attempt_id": "attempt-one", "claim_id": "claim-one"},
    )
    recovery = client.post(
        "/api/changes/change-a/outcomes/OUT-001/claims/recover",
        json={"confirmed_lost": True, "attempt_id": "attempt-one", "claim_id": "claim-one"},
    )
    preview = client.post(
        "/api/changes/change-a/outcomes/OUT-001/move-backward/preview",
        json={"target": "design"},
    )
    move = client.post(
        "/api/changes/change-a/outcomes/OUT-001/move-backward",
        json={"target": "design", "reason": "Authority changed", "snapshot_version": "a" * 64},
    )

    assert (answer.status_code, clear.status_code, recovery.status_code, preview.status_code, move.status_code) == (
        200,
        200,
        200,
        200,
        200,
    )
    assert rejected_recovery.status_code == 422
    assert [name for name, _args in application.calls] == ["answer", "clear", "recover", "move-preview", "move"]
    answer_request = application.calls[0][1][0]
    assert isinstance(answer_request, DeliveryAnswer)
    assert answer_request.expected_frontier_digest == "a" * 64
    move_request = application.calls[-1][1][1]
    assert uuid.UUID(move_request.move_id).version == 4  # type: ignore[attr-defined]
    assert move_request.outcome_id == "OUT-001"  # type: ignore[attr-defined]
    assert move_request.expected_version == "a" * 64  # type: ignore[attr-defined]


def test_bulk_expired_claim_recovery_route_is_removed_without_delivery_call() -> None:
    client, application = _client()

    response = client.post("/api/work-items/claims/recover-expired")

    assert response.status_code in {404, 405}
    assert application.calls == []


def test_publication_and_completed_history_routes_delegate_exactly_once() -> None:
    client, application = _client()

    responses = (
        client.post("/api/changes/change-a/publication/reconcile"),
        client.post(
            "/api/changes/change-a/target/sync",
            json={"operation_id": "cockpit-target-sync-test"},
        ),
        client.post("/api/changes/change-a/publication/ready"),
        client.post("/api/changes/change-a/acceptance/observe"),
        client.post(
            "/api/changes/change-a/attention/resolve",
            json={
                "expected_disposition_id": "a" * 64,
                "expected_frontier_digest": "a" * 64,
            },
        ),
        client.post(
            "/api/changes/change-a/defer",
            json={"reason": "Wait for user review", "expected_frontier_digest": "a" * 64},
        ),
        client.post("/api/changes/change-a/resume", json={"expected_frontier_digest": "a" * 64}),
        client.post(
            "/api/changes/change-a/abandon",
            json={
                "confirmed_abandonment": True,
                "reason": "User stopped the Change",
                "expected_frontier_digest": "a" * 64,
            },
        ),
        client.post("/api/changes/change-a/worktree/cleanup/abandoned"),
        client.post(
            "/api/changes/change-a/worktree/cleanup/completed",
            json={"completion_id": "e" * 64},
        ),
        client.get("/api/work-items/completed", params={"limit": 25}),
        client.get("/api/work-items/completed/search", params={"query": "delivery", "limit": 5}),
        client.get("/api/work-items/completed/change-a", params={"completion_id": "a" * 64}),
    )

    assert [response.status_code for response in responses] == [200] * 13
    history = _DeliveryApplicationFake._completed_history()  # noqa: SLF001
    assert responses[10].json() == history.model_dump(mode="json")
    assert responses[11].json() == history.model_dump(mode="json")
    assert responses[12].json() == history.records[0].model_dump(mode="json")
    target_sync_call = application.calls[1]
    target_sync_operation_id = target_sync_call[1][1]
    assert isinstance(target_sync_operation_id, str)
    assert target_sync_operation_id == "cockpit-target-sync-test"
    target_sync_receipt = ChangeTargetSyncReceipt.create(
        operation_id=target_sync_operation_id,
        change_id="change-a",
        integration_target="main",
        expected_target="e" * 40,
        target_head="e" * 40,
        change_head_before="d" * 40,
        merged_head="f" * 40,
        merge_commit=True,
    )
    assert responses[1].json() == {
        "schema_version": 1,
        "receipt_id": target_sync_receipt.receipt_id,
        "operation_id": target_sync_operation_id,
        "change_id": "change-a",
        "target_branch": "main",
        "expected_target": "e" * 40,
        "target_head": "e" * 40,
        "change_head_before": "d" * 40,
        "merged_head": "f" * 40,
        "merge_commit": True,
        "review_required": False,
    }
    assert responses[8].json() == {
        "cleanup_id": "c" * 64,
        "change_id": "change-a",
        "branch": "owlbear/change/change-a",
        "worktree_path": ".owlbear/delivery/worktrees/change-a",
        "branch_head": "d" * 40,
    }
    assert responses[9].json() == responses[8].json()
    assert application.calls == [
        ("publication-reconcile", ("change-a",)),
        target_sync_call,
        ("publication-ready", ("change-a",)),
        ("acceptance-observe", ("change-a",)),
        (
            "attention-resolve",
            (
                DeliveryAnswer(
                    change_id="change-a",
                    kind=DeliveryAnswerKind.DISPOSITION,
                    expected_frontier_digest="a" * 64,
                    expected_disposition_id="a" * 64,
                ),
            ),
        ),
        (
            "intent",
            (
                DeliveryChangeIntent(
                    change_id="change-a",
                    kind=DeliveryChangeIntentKind.DEFER,
                    expected_frontier_digest="a" * 64,
                    reason="Wait for user review",
                ),
            ),
        ),
        (
            "intent",
            (
                DeliveryChangeIntent(
                    change_id="change-a",
                    kind=DeliveryChangeIntentKind.RESUME,
                    expected_frontier_digest="a" * 64,
                ),
            ),
        ),
        (
            "intent",
            (
                DeliveryChangeIntent(
                    change_id="change-a",
                    kind=DeliveryChangeIntentKind.ABANDON,
                    expected_frontier_digest="a" * 64,
                    reason="User stopped the Change",
                ),
            ),
        ),
        ("cleanup-abandoned", ("change-a",)),
        ("cleanup-completed", ("change-a", "e" * 64)),
        ("completed-list", (None, 25)),
        ("completed-search", ("delivery", None, 5)),
        ("completed-show", ("change-a", "a" * 64)),
    ]


def test_publication_check_observation_is_bounded_and_classified() -> None:
    client, application = _client()

    response = client.post("/api/changes/change-a/publication/checks/observe")
    method_rejected = client.get("/api/changes/change-a/publication/checks/observe")

    assert response.status_code == 200
    assert response.json() == {
        "schema_version": 1,
        "observation_id": "a" * 64,
        "change_id": "change-a",
        "repository": "owlbear/example",
        "pull_request_number": 42,
        "exact_commit": "1" * 40,
        "observed_at": "2026-08-11T16:00:00Z",
        "rollup_state": "failure",
        "checks": [
            {
                "check_id": "required-failure",
                "kind": "check_run",
                "name": "Unit tests",
                "status": "completed",
                "conclusion": "failure",
                "required": True,
                "blocking_state": "blocking",
            },
            {
                "check_id": "required-pending",
                "kind": "check_run",
                "name": "Integration tests",
                "status": "queued",
                "conclusion": None,
                "required": True,
                "blocking_state": "required-pending",
            },
            {
                "check_id": "optional-failure",
                "kind": "check_run",
                "name": "Optional lint",
                "status": "completed",
                "conclusion": "failure",
                "required": False,
                "blocking_state": "not-blocking",
            },
        ],
        "required_failure_count": 1,
        "truncated_count": 0,
    }
    assert method_rejected.status_code == 405
    assert application.calls == [("publication-checks-observe", ("change-a",))]


def test_publication_provider_failure_is_typed_and_retry_safe() -> None:
    failure = PublicationProviderError(
        PublicationProviderFailureCode.UNAVAILABLE,
        "observe_checks",
        "GitHub is unavailable",
        retry_safe=True,
    )
    client, application = _client({"publication-checks-observe": failure})

    response = client.post("/api/changes/change-a/publication/checks/observe")

    assert response.status_code == 502
    assert response.json() == {
        "code": "ERR_DELIVERY_PROVIDER_UNAVAILABLE",
        "detail": "GitHub is unavailable",
        "authority": "delivery",
        "retry_safe": True,
    }
    assert application.calls == [("publication-checks-observe", ("change-a",))]


def test_publication_provider_failure_mapping_is_shared_by_ready_route() -> None:
    failure = PublicationProviderError(
        PublicationProviderFailureCode.AUTHENTICATION_REQUIRED,
        "set_pull_request_draft_state",
        "GitHub credentials are required",
        retry_safe=False,
    )
    client, application = _client({"publication-ready": failure})

    response = client.post("/api/changes/change-a/publication/ready")

    assert response.status_code == 502
    assert response.json() == {
        "code": "ERR_DELIVERY_PROVIDER_AUTHENTICATION_REQUIRED",
        "detail": "GitHub credentials are required",
        "authority": "delivery",
        "retry_safe": False,
    }
    assert application.calls == [("publication-ready", ("change-a",))]


def test_publication_check_response_retains_blockers_before_bounded_truncation() -> None:
    head = "1" * 40
    checks = (
        SimpleNamespace(
            check_id="blocking-check",
            kind=PublicationCheckKind.CHECK_RUN,
            name="Blocking check",
            status="completed",
            conclusion="failure",
            required=True,
        ),
        *(
            SimpleNamespace(
                check_id=f"optional-{index}",
                kind=PublicationCheckKind.CHECK_RUN,
                name=f"Optional check {index}",
                status="completed",
                conclusion="success",
                required=False,
            )
            for index in range(200)
        ),
    )
    receipt = SimpleNamespace(
        observation_id="a" * 64,
        change_id="change-a",
        repository="owlbear/example",
        number=42,
        exact_commit=head,
        observed_at=datetime(2026, 8, 11, 16, 0, tzinfo=UTC),
        snapshot=SimpleNamespace(rollup_state="success", checks=checks),
    )

    response = PublicationChecksObservationResponse.from_receipt(receipt)

    assert len(response.checks) == 200
    assert response.checks[0].check_id == "blocking-check"
    assert response.required_failure_count == 1
    assert response.truncated_count == 1


def test_completed_history_routes_serialize_both_record_kinds() -> None:
    client, application = _client()
    history = _DeliveryApplicationFake._completed_history()  # noqa: SLF001

    legacy = client.get(
        "/api/work-items/completed/change-a",
        params={"completion_id": history.records[0].completion_id},
    )
    receipt = client.get(
        "/api/work-items/completed/change-b",
        params={"completion_id": history.records[1].completion_id},
    )

    assert legacy.status_code == receipt.status_code == 200
    assert legacy.json() == history.records[0].model_dump(mode="json")
    assert receipt.json() == history.records[1].model_dump(mode="json")
    assert application.calls == [
        ("completed-show", ("change-a", history.records[0].completion_id)),
        ("completed-show", ("change-b", history.records[1].completion_id)),
    ]


def test_open_acceptance_waiting_route_is_retry_safe() -> None:
    client, application = _client(
        {"observe_acceptance": DeliveryAcceptanceWaitingError("pull request is still open and unmerged")}
    )

    response = client.post("/api/changes/change-a/acceptance/observe")

    assert response.status_code == 409
    assert response.json() == {
        "code": "ERR_DELIVERY_ACCEPTANCE_WAITING",
        "detail": "pull request is still open and unmerged",
        "authority": "delivery",
        "retry_safe": True,
    }
    assert application.calls == [("acceptance-observe", ("change-a",))]


def test_acceptance_reconciliation_route_returns_isolated_mixed_outcomes() -> None:
    client, application = _client()

    response = client.post(
        "/api/work-items/acceptance/reconcile",
        json={"change_ids": ["change-a", "change-b"]},
    )

    assert response.status_code == 200
    assert response.json() == {
        "outcomes": [
            {
                "change_id": "change-a",
                "status": "waiting",
                "code": None,
                "detail": "The pull request is open and not merged.",
                "completion_id": None,
            },
            {
                "change_id": "change-b",
                "status": "completed",
                "code": None,
                "detail": None,
                "completion_id": "f" * 64,
            },
            {
                "change_id": "change-c",
                "status": "provider-unavailable",
                "code": "unavailable",
                "detail": "Provider unavailable",
                "completion_id": None,
            },
        ]
    }
    assert application.calls == [("acceptance-reconcile", (("change-a", "change-b"),))]


def test_acceptance_reconciliation_route_rejects_malformed_ids() -> None:
    client, application = _client()

    response = client.post(
        "/api/work-items/acceptance/reconcile",
        json={"change_ids": "change-a"},
    )

    assert response.status_code == 422
    assert response.json() == {
        "code": "ERR_DELIVERY_HTTP_VALIDATION",
        "detail": "Delivery request input is malformed",
        "authority": "delivery",
        "retry_safe": False,
    }
    assert application.calls == []


def test_target_sync_conflict_route_preserves_typed_delivery_error() -> None:
    client, application = _client(
        {
            "target_sync": ChangeTargetSyncConflictError(
                "change-a",
                "cockpit-target-sync-test",
                "e" * 40,
                ("product.txt",),
            )
        }
    )

    response = client.post(
        "/api/changes/change-a/target/sync",
        json={"operation_id": "cockpit-target-sync-test"},
    )

    assert response.status_code == 409
    assert response.json() == {
        "code": "ERR_TARGET_SYNC_CONFLICT",
        "detail": "target synchronization requires conflict resolution: product.txt",
        "authority": "delivery",
        "retry_safe": False,
    }
    assert application.calls == [("target-sync", ("change-a", "cockpit-target-sync-test"))]


def test_target_sync_conflict_exit_routes_delegate_exactly_once() -> None:
    client, application = _client()
    body = {
        "expected_disposition_id": "a" * 64,
        "target_head": "e" * 40,
        "operation_id": "cockpit-target-sync-test",
    }

    abort = client.post("/api/changes/change-a/target/conflict/abort", json=body)
    resolve = client.post("/api/changes/change-a/target/conflict/resolve", json=body)

    assert abort.status_code == 200
    assert resolve.status_code == 200
    assert abort.json()["restored_head"] == "d" * 40
    assert resolve.json()["target_head"] == "e" * 40
    assert application.calls == [
        (
            "target-sync-abort",
            ("change-a", "a" * 64, "e" * 40, "cockpit-target-sync-test"),
        ),
        (
            "target-sync-resolve",
            ("change-a", "a" * 64, "e" * 40, "cockpit-target-sync-test"),
        ),
    ]


def test_abandoned_target_sync_discard_cleanup_route_requires_confirmation() -> None:
    client, application = _client()

    response = client.post(
        "/api/changes/change-a/worktree/cleanup/abandoned/target-sync-discard",
        json={
            "confirmed_discard": True,
            "expected_target_head": "e" * 40,
            "expected_operation_id": "cockpit-target-sync-test",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "cleanup_id": "c" * 64,
        "change_id": "change-a",
        "branch": "owlbear/change/change-a",
        "worktree_path": ".owlbear/delivery/worktrees/change-a",
        "branch_head": "d" * 40,
    }
    assert application.calls == [
        (
            "cleanup-abandoned-target-sync",
            ("change-a", True, "e" * 40, "cockpit-target-sync-test"),
        )
    ]

    rejected = client.post(
        "/api/changes/change-a/worktree/cleanup/abandoned/target-sync-discard",
        json={
            "confirmed_discard": False,
            "expected_target_head": "e" * 40,
            "expected_operation_id": "cockpit-target-sync-test",
        },
    )

    assert rejected.status_code == 422
    assert application.calls == [
        (
            "cleanup-abandoned-target-sync",
            ("change-a", True, "e" * 40, "cockpit-target-sync-test"),
        )
    ]


def test_publication_supersession_route_delegates_current_identity_exactly_once() -> None:
    client, application = _client()

    response = client.post(
        "/api/changes/change-a/publication/supersede",
        json={"operation_id": "cockpit-publication-supersede"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "schema_version": 1,
        "receipt_id": "a" * 64,
        "operation_id": "cockpit-publication-supersede",
        "change_id": "change-a",
        "predecessor_publication_id": "b" * 64,
        "successor_publication_id": "c" * 64,
    }
    assert application.calls == [
        ("publication-supersede", ("change-a", "cockpit-publication-supersede")),
    ]


def test_stale_attention_resolution_route_is_not_retry_safe() -> None:
    client, application = _client({"answer": DeliveryChangeDispositionConflictError("attention identity is stale")})

    response = client.post(
        "/api/changes/change-a/attention/resolve",
        json={"expected_disposition_id": "a" * 64, "expected_frontier_digest": "a" * 64},
    )

    assert response.status_code == 409
    assert response.json() == {
        "code": "ERR_DELIVERY_RUNTIME_CONFLICT",
        "detail": "attention identity is stale",
        "authority": "delivery",
        "retry_safe": False,
    }
    assert application.calls == [
        (
            "attention-resolve",
            (
                DeliveryAnswer(
                    change_id="change-a",
                    kind=DeliveryAnswerKind.DISPOSITION,
                    expected_frontier_digest="a" * 64,
                    expected_disposition_id="a" * 64,
                ),
            ),
        ),
    ]


def test_busy_attention_resolution_route_is_retryable_conflict() -> None:
    client, application = _client({"answer": DeliveryChangeDispositionBusyError("attention is already in progress")})

    response = client.post(
        "/api/changes/change-a/attention/resolve",
        json={"expected_disposition_id": "a" * 64, "expected_frontier_digest": "a" * 64},
    )

    assert response.status_code == 409
    assert response.json() == {
        "code": "ERR_DELIVERY_ATTENTION_RESOLVE_BUSY",
        "detail": "attention is already in progress",
        "authority": "delivery",
        "retry_safe": True,
    }
    assert application.calls == [
        (
            "attention-resolve",
            (
                DeliveryAnswer(
                    change_id="change-a",
                    kind=DeliveryAnswerKind.DISPOSITION,
                    expected_frontier_digest="a" * 64,
                    expected_disposition_id="a" * 64,
                ),
            ),
        ),
    ]


def test_real_attention_resolution_route_fails_fast_on_held_checkpoint_lock(tmp_path: Path) -> None:
    application = _LockOnlyPortfolioApplication(tmp_path)
    lock_root = tmp_path / "publications/checkpoints/locks/change-a"

    with (
        patch("owlbear_delivery.portfolio_application._ATTENTION_RESOLUTION_LOCK_TIMEOUT_SECONDS", 0.0),
        locked_roots((lock_root,)),
        TestClient(assemble_target_app(application)) as client,
    ):
        response = client.post(
            "/api/changes/change-a/attention/resolve",
            json={"expected_disposition_id": "a" * 64, "expected_frontier_digest": "a" * 64},
        )

    assert response.status_code == 409
    assert response.json() == {
        "code": "ERR_DELIVERY_ATTENTION_RESOLVE_BUSY",
        "detail": "Change attention resolution is already in progress; retry after the active mutation finishes",
        "authority": "delivery",
        "retry_safe": True,
    }


def test_malformed_body_fails_before_application_mutation() -> None:
    client, application = _client()

    response = client.post(
        "/api/changes/change-a/outcomes/OUT-001/move-backward",
        json={"move_id": "caller-owned", "target": "design", "reason": "Authority changed"},
    )

    assert response.status_code == 422
    assert response.json() == {
        "code": "ERR_DELIVERY_HTTP_VALIDATION",
        "detail": "Delivery request input is malformed",
        "authority": "delivery",
        "retry_safe": False,
    }
    assert application.calls == []


def test_completed_cleanup_requires_exact_completion_identity() -> None:
    client, application = _client()

    response = client.post(
        "/api/changes/change-a/worktree/cleanup/completed",
        json={"completion_id": "not-a-completion-id"},
    )

    assert response.status_code == 422
    assert response.json() == {
        "code": "ERR_DELIVERY_HTTP_VALIDATION",
        "detail": "Delivery request input is malformed",
        "authority": "delivery",
        "retry_safe": False,
    }
    assert application.calls == []


def test_worktree_attention_cleanup_route_returns_typed_delivery_error() -> None:
    attention = ChangeWorktreeAttentionError(
        "change-a",
        (ChangeWorktreeAttentionCode.WORKTREE_DIRTY,),
    )
    client, application = _client({"cleanup_abandoned": attention})

    response = client.post("/api/changes/change-a/worktree/cleanup/abandoned")

    assert response.status_code == 409
    assert response.json() == {
        "code": "ERR_TARGET_WORKTREE_ATTENTION",
        "detail": "Change worktree requires attention: worktree-dirty",
        "authority": "delivery",
        "retry_safe": False,
    }
    assert application.calls == [("cleanup-abandoned", ("change-a",))]


def test_worktree_recovery_route_forwards_exact_confirmation_and_head() -> None:
    client, application = _client()

    response = client.post(
        "/api/changes/change-a/worktree/recover",
        json={"confirmed_recovery": True, "recovery_reviewed_head": "c" * 40},
    )

    assert response.status_code == 200
    assert response.json() == {
        "change_id": "change-a",
        "branch": "owlbear/change/change-a",
        "worktree_path": ".owlbear/delivery/worktrees/change-a",
        "branch_head": "d" * 40,
        "recovery_reviewed_head": "c" * 40,
    }
    assert application.calls == [("recover-worktree", ("change-a", "c" * 40, True))]


def test_malformed_worktree_recovery_body_fails_before_application_mutation() -> None:
    client, application = _client()

    response = client.post(
        "/api/changes/change-a/worktree/recover",
        json={"confirmed_recovery": False, "recovery_reviewed_head": "c" * 40},
    )

    assert response.status_code == 422
    assert response.json() == {
        "code": "ERR_DELIVERY_HTTP_VALIDATION",
        "detail": "Delivery request input is malformed",
        "authority": "delivery",
        "retry_safe": False,
    }
    assert application.calls == []


def test_worktree_attention_recovery_route_returns_typed_delivery_error() -> None:
    attention = ChangeWorktreeAttentionError(
        "change-a",
        (ChangeWorktreeAttentionCode.OWNERSHIP_AMBIGUOUS,),
    )
    client, application = _client({"recover_worktree": attention})

    response = client.post(
        "/api/changes/change-a/worktree/recover",
        json={"confirmed_recovery": True, "recovery_reviewed_head": "c" * 40},
    )

    assert response.status_code == 409
    assert response.json() == {
        "code": "ERR_TARGET_WORKTREE_ATTENTION",
        "detail": "Change worktree requires attention: ownership-ambiguous",
        "authority": "delivery",
        "retry_safe": False,
    }
    assert application.calls == [("recover-worktree", ("change-a", "c" * 40, True))]


def test_live_cockpit_app_surfaces_known_delivery_failure() -> None:
    from owlbear_cockpit.main import app  # noqa: PLC0415

    application = _DeliveryApplicationFake(
        {"observe_acceptance": CompletionReceiptConflictError("completion receipt is inconsistent")}
    )
    app.dependency_overrides[get_target_context] = lambda: application
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post("/api/changes/change-a/acceptance/observe")
    finally:
        app.dependency_overrides.pop(get_target_context, None)

    assert response.status_code == 409
    assert response.json() == {
        "code": "ERR_COMPLETION_RECEIPT_CONFLICT",
        "detail": "completion receipt is inconsistent",
        "authority": "delivery",
        "retry_safe": False,
    }
    assert application.calls == [("acceptance-observe", ("change-a",))]


def test_live_cockpit_app_keeps_unknown_failure_on_generic_backstop() -> None:
    from owlbear_cockpit.main import app  # noqa: PLC0415

    application = _DeliveryApplicationFake({"observe_acceptance": RuntimeError("unexpected failure")})
    app.dependency_overrides[get_target_context] = lambda: application
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post("/api/changes/change-a/acceptance/observe")
    finally:
        app.dependency_overrides.pop(get_target_context, None)

    assert response.status_code == 500
    assert response.json() == {
        "code": "COCKPIT_INTERNAL_ERROR",
        "message": "An unexpected error occurred.",
    }
    assert application.calls == [("acceptance-observe", ("change-a",))]


def test_target_routes_are_mounted_on_live_app() -> None:
    from owlbear_cockpit.main import app  # noqa: PLC0415

    paths = app.openapi()["paths"]
    assert "/api/work-items" in paths
    assert "/api/changes/{change_id}/work-items/{item_key}" in paths


def test_completed_history_routes_publish_versioned_discriminated_schema() -> None:
    client, _application = _client()
    schema = client.app.openapi()
    paths = schema["paths"]
    components = schema["components"]["schemas"]

    for path in ("/api/work-items/completed", "/api/work-items/completed/search"):
        response_schema = paths[path]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
        assert response_schema == {"$ref": "#/components/schemas/CompletedChangePage"}
    show_schema = paths["/api/work-items/completed/{change_id}"]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]
    assert show_schema == {"$ref": "#/components/schemas/CompletedChangeRecord"}

    record_schema = components["CompletedChangeRecord"]
    assert record_schema["oneOf"] == [
        {"$ref": "#/components/schemas/ReceiptCompletedChangeRecord"},
        {"$ref": "#/components/schemas/AbandonedChangeRecord"},
    ]
    assert record_schema["discriminator"] == {
        "propertyName": "record_kind",
        "mapping": {
            "completion-receipt": "#/components/schemas/ReceiptCompletedChangeRecord",
            "abandoned-change": "#/components/schemas/AbandonedChangeRecord",
        },
    }


def test_http_retry_diagnostic_is_blocked_and_projected(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root, launch, _transition = builder_transition_case(tmp_path, "block")
    transition = RetryDelivery(
        action="retry",
        outcome_id=launch.outcome_id,
        claim_id=launch.claim.claim_id,
        abandoned_commit=_git(launch.worktree_path, "rev-parse", "HEAD"),
        attempt_id=launch.claim.attempt_id,
        failure_code="builder-failed",
    )
    before_frontier = runtimes["change-a"].frontier_bytes()
    before_payload = json.loads(before_frontier)
    before_coordination = coordinator.show("change-a")
    before_workspace = _workspace_mutation_snapshot(launch.worktree_path)

    with pytest.raises(DeliveryWorkerExclusionRequiredError):
        application.transition_delivery("change-a", transition)

    with TestClient(assemble_target_app(application)) as client:
        detail_response = client.get("/api/changes/change-a/work-items/outcome:OUT-001")
        change_response = client.get("/api/work-items")
    assert detail_response.status_code == change_response.status_code == 200
    detail = detail_response.json()["item"]
    change = change_response.json()["groups"][0]["items"][0]
    assert detail["retry_diagnostic"] == {
        "code": "ERR_DELIVERY_WORKER_EXCLUSION_REQUIRED",
        "attempt_id": launch.claim.attempt_id,
        "transition": transition.model_dump(mode="json"),
    }
    assert detail["recovery_attention"] is None
    assert detail["active_claim"]["attempt_id"] == launch.claim.attempt_id
    assert detail["card"]["needs"] == "none"
    assert detail["card"]["next_actor"] == "none"
    assert detail["card"]["activity"]["state"] == "idle"
    assert detail["card"]["action"]["kind"] == "none"
    assert launch.claim.owner_id in detail["card"]["next_step"]
    prompt = detail["readiness"]["prompt"]
    for readiness in (change["readiness"], detail["readiness"]):
        assert readiness["status"] == "blocked"
        assert readiness["reason_code"] == "retry-transition-contained"
        assert readiness["executable"] is False
        assert readiness["next_actor"] == "none"
        assert readiness["operation"] is None
        assert readiness["action"] is None
        assert readiness["prompt"] == prompt
    assert prompt.startswith("/repair-delivery Inspect only Change change-a")
    assert "`delivery-diagnose inspect --change-id change-a`" in prompt
    assert "Make no MCP calls" in prompt
    assert "do not retry" in prompt
    assert "retry budget" in prompt
    for unsupported_tool in ("get_change", "show_operator_context", "acquire_change_action", "transition_delivery"):
        assert unsupported_tool not in prompt

    after_payload = json.loads(runtimes["change-a"].frontier_bytes())
    assert after_payload["bindings"][0]["retry_diagnostic"] == detail["retry_diagnostic"]
    after_payload["bindings"][0]["retry_diagnostic"] = before_payload["bindings"][0]["retry_diagnostic"]
    assert after_payload == before_payload
    assert coordinator.show("change-a") == before_coordination
    assert _workspace_mutation_snapshot(launch.worktree_path) == before_workspace
