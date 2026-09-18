"""Route-level contracts for the Delivery Cockpit application."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import cast
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from serve.delivery.tests.test_portfolio_application import acceptance_budget_case
from serve.delivery.tests.test_recovery import completed_recovery_case, recovery_case

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
    DeliveryUnavailableChangeView,
    ExecuteDeliveryChangeAction,
    PortfolioApplication,
    PortfolioCoordinator,
    PublicationCheckKind,
    PublicationProviderError,
    PublicationProviderFailureCode,
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
from owlbear_delivery.delivery_application_loader import DeliveryApplicationLoadError, DeliveryStartupConfig
from owlbear_delivery.delivery_runtime import (
    DeliveryAcceptanceWaitingError,
    DeliveryChangeDispositionBusyError,
    DeliveryChangeDispositionConflictError,
    DeliveryChangeStage,
)
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


@pytest.mark.parametrize("exhausted", [False, True])
def test_http_explicit_acceptance_is_one_bounded_read(tmp_path: Path, *, exhausted: bool) -> None:
    application, provider, ledger, restart = acceptance_budget_case(tmp_path, exhausted=exhausted)
    calls = provider.read_pull_request.call_count
    with TestClient(assemble_target_app(application)) as client:
        first = client.post("/api/changes/change-a/acceptance/observe")
    with TestClient(assemble_target_app(restart())) as client:
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
    application, _operation, request, unchanged = completed_recovery_case(tmp_path, "claim")
    body = {key: value for key, value in request.items() if key not in {"change_id", "outcome_id"}}
    with TestClient(assemble_target_app(application)) as client:
        response = client.post("/api/changes/change-a/outcomes/OUT-001/claims/recover", json=body)
    assert response.status_code == 200
    assert response.json()["status"] == "recovered"
    unchanged()


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
