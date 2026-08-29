"""Route-level contracts for the Delivery Cockpit application."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from owlbear_cockpit.deps import get_target_context
from owlbear_cockpit.routes.target_work import assemble_target_app
from owlbear_cockpit.target_context import load_target_context
from owlbear_cockpit.target_models import PublicationChecksObservationResponse
from owlbear_delivery import (
    DeliveryAcceptanceReconciliationOutcome,
    DeliveryAcceptanceReconciliationStatus,
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
    LegacyCompletedChangeRecord,
    ReceiptCompletedChangeRecord,
)
from owlbear_delivery.delivery_application_loader import DeliveryApplicationLoadError, DeliveryStartupConfig
from owlbear_delivery.delivery_runtime import (
    DeliveryAcceptanceWaitingError,
    DeliveryChangeDispositionConflictError,
    DeliveryChangeStage,
)
from owlbear_delivery.portfolio_operating import (
    PortfolioChangeAdmission,
    PortfolioChangeLifecycleStatus,
    PortfolioGuidance,
    PortfolioGuidanceKind,
    PortfolioOperatingView,
    PortfolioWorkReference,
    PortfolioWorkScope,
)
from owlbear_delivery.work_items import (
    ChangeGroupView,
    WorkItemAction,
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


class _DeliveryApplicationFake:
    def __init__(self, failures: dict[str, Exception] | None = None) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []
        self.failures = failures or {}

    def list_work_item_groups(self) -> tuple[ChangeGroupView, ...]:
        self.calls.append(("list", ()))
        return self._work_item_groups()

    def portfolio_read_view(self) -> SimpleNamespace:
        self.calls.append(("portfolio", ()))
        return SimpleNamespace(
            groups=self._work_item_groups(),
            operating=self._portfolio_operating_view(),
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

    def show_work_item_view(self, change_id: str, item_key: str) -> WorkItemDetailView:
        self.calls.append(("show", (change_id, item_key)))
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

    def clear_block(self, *args: object) -> dict[str, object]:
        self.calls.append(("clear", args))
        return {"block_id": args[2], "resolved": True}

    def recover_claim(self, *args: object) -> dict[str, object]:
        self.calls.append(("recover", args))
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
        return {"change_id": args[0], "reconciled": True}

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
                LegacyCompletedChangeRecord(
                    change_id="change-a",
                    completion_id="b" * 64,
                    title="Legacy completion",
                    semantic_summary="A migrated completion package.",
                    outcome_titles=("Migrate the completion package",),
                    outcome_promises=("Make historical completion evidence available.",),
                    completion_path=".owlbear/legacy/completed/change-a",
                    historical_completion_locator=".owlbear/completed/change-a",
                    package_id="c" * 64,
                    introducing_target_commit="d" * 40,
                    source_target_commit="e" * 40,
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

    def show_completed_change(self, *args: object) -> LegacyCompletedChangeRecord | ReceiptCompletedChangeRecord:
        self.calls.append(("completed-show", args))
        records = self._completed_history().records
        return records[1] if args[1] == "1" * 64 else records[0]


def _client(failures: dict[str, Exception] | None = None) -> tuple[TestClient, _DeliveryApplicationFake]:
    application = _DeliveryApplicationFake(failures)
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


def test_startup_reports_delivery_migration_blocker(tmp_path: Path) -> None:
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
    load_error = DeliveryApplicationLoadError("runtime_root", "legacy runtime state requires migration")

    with (
        patch("owlbear_cockpit.target_context.load_delivery_application", side_effect=load_error),
        pytest.raises(
            RuntimeError,
            match="Cockpit Delivery startup failed for runtime_root: legacy runtime state requires migration",
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
        json={"selected_option_id": "option-a"},
    )
    clear = client.post(
        "/api/changes/change-a/outcomes/OUT-001/blocks/block-one/clear",
        json={"operator_note": "Verified externally", "locators": ["request:REQ-001"]},
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
            json={"expected_disposition_id": "a" * 64},
        ),
        client.post(
            "/api/changes/change-a/defer",
            json={"reason": "Wait for user review"},
        ),
        client.post("/api/changes/change-a/resume"),
        client.post(
            "/api/changes/change-a/abandon",
            json={"confirmed_abandonment": True, "reason": "User stopped the Change"},
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
        ("attention-resolve", ("change-a", "a" * 64)),
        ("defer", ("change-a", "Wait for user review")),
        ("resume", ("change-a",)),
        ("abandon", ("change-a", "User stopped the Change")),
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
    client, application = _client(
        {"resolve_change_disposition": DeliveryChangeDispositionConflictError("attention identity is stale")}
    )

    response = client.post(
        "/api/changes/change-a/attention/resolve",
        json={"expected_disposition_id": "a" * 64},
    )

    assert response.status_code == 409
    assert response.json() == {
        "code": "ERR_DELIVERY_RUNTIME_CONFLICT",
        "detail": "attention identity is stale",
        "authority": "delivery",
        "retry_safe": False,
    }
    assert application.calls == [("attention-resolve", ("change-a", "a" * 64))]


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
        {"$ref": "#/components/schemas/LegacyCompletedChangeRecord"},
        {"$ref": "#/components/schemas/ReceiptCompletedChangeRecord"},
    ]
    assert record_schema["discriminator"] == {
        "propertyName": "record_kind",
        "mapping": {
            "legacy-package": "#/components/schemas/LegacyCompletedChangeRecord",
            "completion-receipt": "#/components/schemas/ReceiptCompletedChangeRecord",
        },
    }
