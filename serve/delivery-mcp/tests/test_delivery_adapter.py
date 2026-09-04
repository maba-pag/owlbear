"""Contract tests for the strict Delivery MCP adapter."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import BaseModel, ConfigDict

from owlbear_delivery import (
    DeliveryAdmissionConflictError,
    DeliveryAdmissionValidationError,
    DeliveryChangeWorktreeCleanup,
    DeliveryChangeWorktreeRecovery,
    DeliveryRetainedChangeWorktree,
    PublicationBaselineRecoveryReceipt,
)
from owlbear_delivery.acceptance import CompletionReceiptConflictError
from owlbear_delivery.change_publication import ChangeBranchSupersessionReceipt
from owlbear_delivery.change_workspace import (
    ChangeExternalHeadAdoptionReceipt,
    ChangeExternalHeadPromotionReceipt,
    ChangeTargetSyncAbortReceipt,
    ChangeTargetSyncConflictError,
    ChangeTargetSyncReceipt,
    CoordinationConflictError,
    PublicationBaselineUnavailableError,
)
from owlbear_delivery.completed_history import (
    CompletedHistoryDiagnostic,
    CompletedHistoryDiagnosticCode,
    CompletedHistoryMissingError,
)
from owlbear_delivery.delivery_runtime import (
    AdministrativeDeliveryMovePreview,
    DeliveryAcceptanceWaitingError,
    DeliveryBlock,
    DeliveryChangeDispositionBusyError,
    DeliveryChangeDispositionConflictError,
    DeliveryChangePublicationHistory,
    DeliveryChangePublicationIdentity,
    DeliveryObservation,
    DeliveryObservationReceipt,
    DeliveryPlanCandidate,
    DeliveryRequest,
    DeliveryRequestKind,
    DeliveryRequestResolution,
    DeliveryResultCandidate,
    DeliveryReview,
    DeliveryReviewReceipt,
    DeliveryRuntimeReferenceError,
    DeliveryStage,
    DeliveryTaskDefinition,
    DeliveryTaskResult,
    FinalizeDeliveryChange,
    OutcomeAuthorityBinding,
)
from owlbear_delivery.delivery_state import DeliveryStatePublicationError
from owlbear_delivery.design_package import DesignPackageConflictError
from owlbear_delivery.draft_pull_request import (
    DraftPullRequestPublicationReceipt,
    DraftPullRequestSupersessionReceipt,
    MarkChangePullRequestReady,
)
from owlbear_delivery.portfolio_application import (
    DeliveryChangePublicationSupersessionReceipt,
    DeliveryOperatorContext,
)
from owlbear_delivery.portfolio_operating import (
    DeliveryHealthDiagnostic,
    DeliveryHealthStatus,
    DeliveryHealthView,
)
from owlbear_delivery.publication_provider import PublicationProviderError, PublicationProviderFailureCode
from owlbear_delivery_mcp.target_server import (
    DELIVERY_OPERATION_ANNOTATIONS,
    DELIVERY_OPERATION_NAMES,
    TargetMCPAdapter,
)

CHANGE = "change-a"
DIGEST = "a" * 64
COMMIT = "b" * 40
WORKTREE_PATH = Path(__file__).resolve().parent / "fixture-worktree" / CHANGE


def _receipt_id(payload: dict[str, object]) -> str:
    content = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(content.encode()).hexdigest()


def _supersession_receipt() -> DeliveryChangePublicationSupersessionReceipt:
    predecessor_head = COMMIT
    successor_head = "c" * 40
    predecessor_branch = "owlbear/change/change-a"
    successor_branch = "owlbear/change/change-a+s1"
    predecessor_payload = {
        "schema_version": 1,
        "operation_id": "pull-request-operation",
        "change_id": CHANGE,
        "repository": "example/project",
        "number": 7,
        "node_id": "PR_7",
        "head_branch": predecessor_branch,
        "head_sha": predecessor_head,
        "base_branch": "main",
        "provider_evidence_digest": "2" * 64,
    }
    successor_payload = {
        **predecessor_payload,
        "operation_id": "supersede-change-a",
        "number": 8,
        "node_id": "PR_8",
        "head_branch": successor_branch,
        "head_sha": successor_head,
        "provider_evidence_digest": "3" * 64,
    }
    predecessor = DraftPullRequestPublicationReceipt(
        receipt_id=_receipt_id(predecessor_payload),
        **predecessor_payload,
    )
    successor = DraftPullRequestPublicationReceipt(
        receipt_id=_receipt_id(successor_payload),
        **successor_payload,
    )
    provider_payload = {
        "schema_version": 1,
        "operation_id": "supersede-change-a",
        "change_id": CHANGE,
        "predecessor_receipt_id": predecessor.receipt_id,
        "predecessor_branch": predecessor_branch,
        "predecessor_head": predecessor_head,
        "successor_receipt_id": successor.receipt_id,
        "successor_branch": successor_branch,
        "superseding_head": successor_head,
        "repository": "example/project",
        "successor_number": 8,
        "successor_node_id": "PR_8",
        "base_branch": "main",
        "provider_evidence_digest": "3" * 64,
        "predecessor_publication": predecessor.model_dump(mode="json"),
        "successor_publication": successor.model_dump(mode="json"),
    }
    provider_receipt = DraftPullRequestSupersessionReceipt(
        receipt_id=_receipt_id(provider_payload),
        **provider_payload,
    )
    predecessor_identity = DeliveryChangePublicationIdentity(
        change_id=CHANGE,
        repository="example/project",
        number=7,
        node_id="PR_7",
        head_sha=predecessor_head,
    )
    successor_identity = DeliveryChangePublicationIdentity(
        change_id=CHANGE,
        repository="example/project",
        number=8,
        node_id="PR_8",
        head_sha=successor_head,
    )
    publication_history = DeliveryChangePublicationHistory.create(predecessor_identity).append(
        predecessor_identity,
        successor_identity,
    )
    git_receipt = ChangeBranchSupersessionReceipt(
        receipt_id="4" * 64,
        operation_id="supersede-change-a",
        change_id=CHANGE,
        remote="origin",
        predecessor_branch=predecessor_branch,
        predecessor_head=predecessor_head,
        successor_branch=successor_branch,
        superseding_head=successor_head,
        target_branch="main",
    )
    return DeliveryChangePublicationSupersessionReceipt.create(
        operation_id="supersede-change-a",
        predecessor_publication_id=predecessor.receipt_id,
        git_supersession=git_receipt,
        provider_supersession=provider_receipt,
        publication_history=publication_history,
    )


def _target_sync_receipt() -> ChangeTargetSyncReceipt:
    return ChangeTargetSyncReceipt.create(
        operation_id="sync-change-a",
        change_id=CHANGE,
        integration_target="main",
        expected_target="c" * 40,
        target_head="c" * 40,
        change_head_before=COMMIT,
        merged_head="d" * 40,
        merge_commit=True,
    )


def _target_sync_abort_receipt() -> ChangeTargetSyncAbortReceipt:
    return ChangeTargetSyncAbortReceipt.create(
        operation_id="sync-change-a",
        change_id=CHANGE,
        target_head="c" * 40,
        restored_head=COMMIT,
    )


def _external_head_adoption_receipt() -> ChangeExternalHeadAdoptionReceipt:
    return ChangeExternalHeadAdoptionReceipt.create(
        operation_id="adopt-change-a",
        change_id=CHANGE,
        branch="owlbear/change/change-a",
        expected_head=COMMIT,
        adopted_head="e" * 40,
    )


def _external_head_promotion_receipt() -> ChangeExternalHeadPromotionReceipt:
    adoption = _external_head_adoption_receipt()
    return ChangeExternalHeadPromotionReceipt.create(
        operation_id="promote-change-a",
        change_id=CHANGE,
        branch="owlbear/change/change-a",
        adoption_receipt_id=adoption.receipt_id,
        promoted_head=adoption.adopted_head,
        provenance="explicit",
    )


class _Result(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    operation: str


class _RecordingApplication:
    def __init__(self, failures: dict[str, Exception] | None = None) -> None:
        self.calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []
        self.failures = failures or {}

    def delivery_health(self) -> DeliveryHealthView:
        self.calls.append(("delivery_health", (), {}))
        return DeliveryHealthView(
            status=DeliveryHealthStatus.ATTENTION,
            diagnostics=(
                DeliveryHealthDiagnostic(
                    source="test",
                    code="runtime-unavailable",
                    detail="The fixture Change requires reconciliation.",
                    change_id=CHANGE,
                    retry_safe=True,
                ),
            ),
        )

    def __getattr__(self, name: str) -> Any:  # noqa: C901
        def operation(*args: object, **kwargs: object) -> object:  # noqa: C901, PLR0912
            self.calls.append((name, args, kwargs))
            failure = self.failures.get(name)
            if failure is not None:
                raise failure
            if name == "list_work_items":
                result: object = (_Result(operation=name),)
            elif name == "list_retained_change_worktrees":
                result = (
                    DeliveryRetainedChangeWorktree(
                        change_id=CHANGE,
                        worktree_path=WORKTREE_PATH,
                        branch="owlbear/change/change-a",
                        branch_head=COMMIT,
                        coordination_registered=True,
                        git_registered=True,
                        worktree_present=True,
                        worktree_head=COMMIT,
                        worktree_branch="owlbear/change/change-a",
                        lifecycle=None,
                        orphan=False,
                        cleanup_eligible=True,
                    ),
                )
            elif name in {
                "cleanup_abandoned_change_worktree",
                "cleanup_abandoned_change_worktree_after_target_sync_discard",
                "cleanup_completed_change_worktree",
            }:
                result = DeliveryChangeWorktreeCleanup(
                    cleanup_id=DIGEST,
                    change_id=CHANGE,
                    branch="owlbear/change/change-a",
                    worktree_path=WORKTREE_PATH,
                    branch_head=COMMIT,
                )
            elif name == "recover_change_worktree":
                result = DeliveryChangeWorktreeRecovery(
                    change_id=CHANGE,
                    branch="owlbear/change/change-a",
                    worktree_path=WORKTREE_PATH,
                    branch_head=COMMIT,
                    recovery_reviewed_head=COMMIT,
                )
            elif name == "recover_publication_baseline":
                result = PublicationBaselineRecoveryReceipt.create(
                    operation_id="recover-baseline",
                    change_id=CHANGE,
                    expected_change_head=COMMIT,
                    publication_base_head="a" * 40,
                )
            elif name == "show_operator_context":
                result = DeliveryOperatorContext(
                    change_id=CHANGE,
                    outcome_id="OUT-001",
                    stage=DeliveryStage.PLANNING,
                    block=DeliveryBlock(
                        block_id="block",
                        reason="Need user action",
                        unblock_condition="Action is complete",
                        expected_evidence=("completion evidence",),
                        locators=("request",),
                        request_id="request",
                    ),
                    requests=(
                        DeliveryRequest(
                            request_id="request",
                            kind=DeliveryRequestKind.ACTION,
                            outcome_id="OUT-001",
                            summary="Complete the action",
                        ),
                    ),
                )
            elif name == "resolve_request":
                result = DeliveryRequest(
                    request_id="request",
                    kind=DeliveryRequestKind.ACTION,
                    outcome_id="OUT-001",
                    summary="Complete the action",
                    resolution=DeliveryRequestResolution(response_text="Completed."),
                )
            elif name == "clear_block":
                result = OutcomeAuthorityBinding(
                    outcome_id="OUT-001",
                    plan_scope_id="SCOPE-001",
                    block=DeliveryBlock(
                        block_id="block",
                        reason="Need operator evidence",
                        unblock_condition="Evidence is recorded",
                        expected_evidence=("operator evidence",),
                        locators=("operator-note",),
                        resolution_note="Verified.",
                        resolution_locators=("operator-note",),
                    ),
                )
            elif name == "preview_administrative_move":
                result = AdministrativeDeliveryMovePreview(
                    outcome_id="OUT-001",
                    target=DeliveryStage.PLANNING,
                    snapshot_version=DIGEST,
                    invalidated_outcome_ids=("OUT-001",),
                )
            elif name == "publish_delivery_plan":
                request = args[1]
                assert hasattr(request, "tasks")
                tasks = request.tasks
                assert isinstance(tasks, tuple)
                assert all(isinstance(task, DeliveryTaskDefinition) for task in tasks)
                result = DeliveryPlanCandidate(candidate_id="plan", claim_id="claim", digest=DIGEST, tasks=tasks)
            elif name == "publish_delivery_result":
                request = args[1]
                assert hasattr(request, "result")
                result = request.result
                assert isinstance(result, DeliveryTaskResult)
                result = DeliveryResultCandidate(
                    candidate_id="result",
                    claim_id="claim",
                    digest=DIGEST,
                    result=result,
                )
            elif name in {
                "supersede_publication",
                "sync_change_with_target",
                "adopt_external_head",
                "promote_external_head",
                "resolve_target_sync_conflict",
                "abort_target_sync_conflict",
            }:
                result = {
                    "supersede_publication": _supersession_receipt,
                    "sync_change_with_target": _target_sync_receipt,
                    "adopt_external_head": _external_head_adoption_receipt,
                    "promote_external_head": _external_head_promotion_receipt,
                    "resolve_target_sync_conflict": _target_sync_receipt,
                    "abort_target_sync_conflict": _target_sync_abort_receipt,
                }[name]()
            else:
                result = _Result(operation=name)
            return result

        return operation


def _task() -> dict[str, object]:
    return {
        "task_id": "TASK-001",
        "outcome_id": "OUT-001",
        "plan_scope_id": "SCOPE-001",
        "title": "Implement result",
        "result": "Observable result",
        "commitment_ids": ["COM-001"],
        "dependency_ids": [],
        "required_outputs": ["result"],
        "maintained_surfaces": ["surface"],
        "constraints": [],
        "exclusions": [],
        "acceptance_observations": ["result observed"],
        "proof_boundaries": ["public adapter"],
    }


def _result() -> dict[str, object]:
    observed_at = datetime(2026, 8, 11, 12, tzinfo=UTC)
    observation = DeliveryObservationReceipt.create(
        DeliveryObservation(
            change_id=CHANGE,
            task_or_finalization_id="TASK-001",
            exact_commit=COMMIT,
            observation_kind="pytest",
            command_or_procedure="Delivery MCP adapter contract test",
            exit_status_or_artifact_locator="exit:0",
            observer_or_runner_identity="pytest",
            observed_at=observed_at,
        )
    )
    review = DeliveryReviewReceipt.create(
        DeliveryReview(
            exact_commit=COMMIT,
            author_id="MCP adapter test author",
            reviewer_id="MCP adapter test reviewer",
            evidence=("The exact fixture commit satisfies task authority.",),
            reviewed_at=observed_at,
        )
    )
    return {
        "result_id": "result-one",
        "change_id": CHANGE,
        "authority_digest": DIGEST,
        "task_id": "TASK-001",
        "task_digest": DIGEST,
        "completed_commit": COMMIT,
        "observations": [observation.model_dump(mode="json")],
        "review": review.model_dump(mode="json"),
    }


def _finalization() -> dict[str, object]:
    operation_id = "finalize-one"
    observed_at = datetime(2026, 8, 11, 13, tzinfo=UTC)
    observation = DeliveryObservationReceipt.create(
        DeliveryObservation(
            change_id=CHANGE,
            task_or_finalization_id=operation_id,
            exact_commit=COMMIT,
            observation_kind="pytest",
            command_or_procedure="Delivery MCP finalization contract test",
            exit_status_or_artifact_locator="exit:0",
            observer_or_runner_identity="pytest",
            observed_at=observed_at,
        )
    )
    review = DeliveryReviewReceipt.create(
        DeliveryReview(
            exact_commit=COMMIT,
            author_id="MCP finalization test author",
            reviewer_id="MCP finalization test reviewer",
            evidence=("The exact Change head satisfies finalization authority.",),
            reviewed_at=observed_at,
        )
    )
    return {
        "operation_id": operation_id,
        "exact_head": COMMIT,
        "observations": [observation.model_dump(mode="json")],
        "review": review.model_dump(mode="json"),
    }


def _requests() -> dict[str, dict[str, object]]:
    change = {"change_id": CHANGE}
    claim = {**change, "outcome_id": "OUT-001", "attempt_id": "attempt", "claim_id": "claim"}
    repair_claim = {**change, "attempt_id": "repair-attempt", "claim_id": "repair-claim"}
    return {
        "create_design_session": {**change, "intent_bytes": "intent", "design_bytes": "design"},
        "read_design_session": change,
        "revise_design_session": {
            **change,
            "expected_package_id": DIGEST,
            "intent_bytes": "intent",
            "design_bytes": "design",
        },
        "publish_design_checkpoint": change,
        "derive_delivery_contract": change,
        "validate_delivery_contract": change,
        "admit_delivery_change": {"request": {"change_id": CHANGE, "active_claim_ids": []}},
        "list_work_items": {},
        "delivery_health": {},
        "list_retained_change_worktrees": {},
        "show_work_item": {**change, "work_item_id": "OUT-001"},
        "show_work_item_view": {**change, "item_key": "publication"},
        "show_operator_context": {**change, "outcome_id": "OUT-001"},
        "resolve_request": {
            **change,
            "request_id": "request",
            "resolution": {"response_text": "Completed."},
        },
        "clear_block": {
            **change,
            "outcome_id": "OUT-001",
            "block_id": "block",
            "operator_note": "Verified.",
            "locators": ["operator-note"],
        },
        "preview_administrative_move": {
            **change,
            "outcome_id": "OUT-001",
            "target": "planning",
        },
        "acquire_frontier_work": {},
        "show_plan_context": claim,
        "show_build_context": claim,
        "show_finalization_context": change,
        "publish_delivery_plan": {
            **change,
            "request": {"outcome_id": "OUT-001", "claim_id": "claim", "tasks": [_task()]},
        },
        "publish_delivery_result": {
            **change,
            "request": {"outcome_id": "OUT-001", "claim_id": "claim", "result": _result()},
        },
        "finalize_change": {**change, "request": _finalization()},
        "mark_change_ready": {
            "request": {
                "change_id": CHANGE,
                "operation_id": "ready-change-a",
                "finalization_id": DIGEST,
                "exact_head": COMMIT,
            }
        },
        "prepare_review_repair": change,
        "reconcile_finalization_head": change,
        "reconcile_change_checkpoint": change,
        "sync_change_with_target": {
            **change,
            "expected_target": "c" * 40,
            "operation_id": "sync-change-a",
        },
        "adopt_external_head": {
            **change,
            "expected_head": COMMIT,
            "adopted_head": "e" * 40,
            "operation_id": "adopt-change-a",
        },
        "promote_external_head": {
            **change,
            "expected_head": "e" * 40,
            "operation_id": "promote-change-a",
        },
        "abort_target_sync_conflict": {
            **change,
            "expected_disposition_id": DIGEST,
            "target_head": "c" * 40,
            "operation_id": "sync-change-a",
        },
        "resolve_target_sync_conflict": {
            **change,
            "expected_disposition_id": DIGEST,
            "target_head": "c" * 40,
            "operation_id": "sync-change-a",
        },
        "supersede_publication": {
            **change,
            "expected_publication_id": DIGEST,
            "operation_id": "supersede-change-a",
        },
        "observe_change_publication_checks": change,
        "observe_acceptance": change,
        "resolve_change_disposition": {**change, "expected_disposition_id": DIGEST},
        "defer_change": {**change, "reason": "Wait for user review"},
        "resume_change": change,
        "abandon_change": {**change, "reason": "Stop this Change"},
        "cleanup_abandoned_change_worktree": change,
        "cleanup_abandoned_change_worktree_after_target_sync_discard": {
            **change,
            "confirmed_discard": True,
        },
        "cleanup_completed_change_worktree": {**change, "completion_id": DIGEST},
        "recover_change_worktree": {
            **change,
            "confirmed_recovery": True,
            "recovery_reviewed_head": COMMIT,
        },
        "recover_publication_baseline": {
            **change,
            "confirmed_recovery": True,
            "expected_change_head": COMMIT,
            "publication_base_head": "a" * 40,
            "operation_id": "recover-baseline",
        },
        "transition_delivery": {
            **change,
            "request": {
                "action": "block",
                "outcome_id": "OUT-001",
                "claim_id": "claim",
                "block_id": "block",
                "reason": "Need user action",
                "unblock_condition": "Action is complete",
                "expected_evidence": ["completion evidence"],
                "locators": ["request"],
                "request": {
                    "request_id": "request",
                    "kind": "action",
                    "outcome_id": "OUT-001",
                    "summary": "Complete the action",
                },
            },
        },
        "recover_claim": claim,
        "recover_integration_repair_claim": repair_claim,
        "show_integration_attention": change,
        "list_completed_changes": {"limit": 25},
        "search_completed_changes": {"query": "delivery", "limit": 25},
        "show_completed_change": {**change, "completion_id": DIGEST},
    }


def _assert_publication_result(operation_name: str, result: Any) -> None:
    assert result.change_id == CHANGE
    expected_operation_id = {
        "supersede_publication": "supersede-change-a",
        "sync_change_with_target": "sync-change-a",
        "adopt_external_head": "adopt-change-a",
        "promote_external_head": "promote-change-a",
        "resolve_target_sync_conflict": "sync-change-a",
        "abort_target_sync_conflict": "sync-change-a",
    }[operation_name]
    assert result.operation_id == expected_operation_id
    if operation_name == "supersede_publication":
        assert result.provider_supersession.successor_number == 8
    elif operation_name == "adopt_external_head":
        assert result.adopted_head == "e" * 40
        assert result.provenance == "fast-forward"
    elif operation_name == "promote_external_head":
        assert result.promoted_head == "e" * 40
    elif operation_name in {"sync_change_with_target", "resolve_target_sync_conflict"}:
        assert result.target_branch == "main"
        assert "integration_target" not in result.model_dump(mode="json")
    else:
        assert result.target_head == "c" * 40


@pytest.mark.asyncio
@pytest.mark.parametrize("operation_name", DELIVERY_OPERATION_NAMES)
async def test_each_delivery_operation_validates_delegates_once_and_serializes(  # noqa: C901, PLR0912, PLR0915
    operation_name: str,
) -> None:
    application = _RecordingApplication()
    adapter = TargetMCPAdapter(application)  # type: ignore[arg-type]

    result = await getattr(adapter, operation_name)(_requests()[operation_name])

    assert [call[0] for call in application.calls] == [operation_name]
    call_args = {
        "show_operator_context": (CHANGE, "OUT-001"),
        "resolve_request": (CHANGE, "request", DeliveryRequestResolution(response_text="Completed.")),
        "clear_block": (CHANGE, "OUT-001", "block", "Verified.", ("operator-note",)),
        "preview_administrative_move": (CHANGE, "OUT-001", DeliveryStage.PLANNING),
        "reconcile_finalization_head": (CHANGE,),
        "observe_acceptance": (CHANGE,),
        "supersede_publication": (CHANGE, DIGEST, "supersede-change-a"),
        "sync_change_with_target": (CHANGE, "c" * 40, "sync-change-a"),
        "adopt_external_head": (CHANGE, COMMIT, "e" * 40, "adopt-change-a"),
        "promote_external_head": (CHANGE, "e" * 40, "promote-change-a"),
        "abort_target_sync_conflict": (CHANGE, DIGEST, "c" * 40, "sync-change-a"),
        "resolve_target_sync_conflict": (CHANGE, DIGEST, "c" * 40, "sync-change-a"),
        "cleanup_abandoned_change_worktree": (CHANGE,),
        "cleanup_abandoned_change_worktree_after_target_sync_discard": (CHANGE,),
        "cleanup_completed_change_worktree": (CHANGE, DIGEST),
        "resolve_change_disposition": (CHANGE, DIGEST),
        "prepare_review_repair": (CHANGE,),
    }
    if operation_name in call_args:
        assert application.calls[0][1] == call_args[operation_name]
    if operation_name == "recover_change_worktree":
        assert application.calls[0][1] == (CHANGE, COMMIT)
        assert application.calls[0][2] == {"confirmed_recovery": True}
    if operation_name == "recover_publication_baseline":
        assert application.calls[0][1] == (CHANGE, COMMIT, "a" * 40, "recover-baseline")
        assert application.calls[0][2] == {"confirmed_recovery": True}
    if operation_name == "finalize_change":
        assert isinstance(application.calls[0][1][1], FinalizeDeliveryChange)
    if operation_name == "mark_change_ready":
        assert application.calls[0][1][0] == CHANGE
        assert isinstance(application.calls[0][1][1], MarkChangePullRequestReady)
    tuple_results = {"list_work_items", "list_retained_change_worktrees"}
    publication_results = {
        "publish_delivery_plan": {"candidate_id": "plan", "claim_id": "claim"},
        "publish_delivery_result": {"candidate_id": "result", "claim_id": "claim"},
    }
    receipt_results = {
        "cleanup_abandoned_change_worktree": {"cleanup_id": DIGEST, "worktree_path": str(WORKTREE_PATH)},
        "cleanup_abandoned_change_worktree_after_target_sync_discard": {
            "cleanup_id": DIGEST,
            "worktree_path": str(WORKTREE_PATH),
        },
        "cleanup_completed_change_worktree": {"cleanup_id": DIGEST, "worktree_path": str(WORKTREE_PATH)},
        "recover_change_worktree": {
            "change_id": CHANGE,
            "worktree_path": str(WORKTREE_PATH),
            "recovery_reviewed_head": COMMIT,
        },
        "recover_publication_baseline": {
            "change_id": CHANGE,
            "expected_change_head": COMMIT,
            "publication_base_head": "a" * 40,
        },
    }
    if operation_name == "list_retained_change_worktrees":
        assert len(result) == 1
        assert result[0]["change_id"] == CHANGE
        assert result[0]["worktree_path"] == str(WORKTREE_PATH)
    elif operation_name in {
        "supersede_publication",
        "sync_change_with_target",
        "adopt_external_head",
        "promote_external_head",
        "abort_target_sync_conflict",
        "resolve_target_sync_conflict",
    }:
        _assert_publication_result(operation_name, result)
    elif operation_name in receipt_results:
        for field, expected in receipt_results[operation_name].items():
            assert getattr(result, field) == expected
    elif operation_name in publication_results:
        assert result.candidate_id == publication_results[operation_name]["candidate_id"]
        assert result.claim_id == publication_results[operation_name]["claim_id"]
        assert result.output.output_id == result.candidate_id
    elif operation_name == "show_operator_context":
        assert result.change_id == CHANGE
        assert result.outcome_id == "OUT-001"
        assert result.block.block_id == "block"
        assert result.requests[0].request_id == "request"
    elif operation_name == "resolve_request":
        assert result.change_id == CHANGE
        assert result.request.request_id == "request"
        assert result.request.resolution.response_text == "Completed."
    elif operation_name == "clear_block":
        assert result.change_id == CHANGE
        assert result.outcome_id == "OUT-001"
        assert result.block.resolution_note == "Verified."
        assert "tasks" not in result.model_dump(mode="json")
        assert "results" not in result.model_dump(mode="json")
    elif operation_name == "preview_administrative_move":
        assert result.outcome_id == "OUT-001"
        assert result.target == DeliveryStage.PLANNING
        assert result.snapshot_version == DIGEST
    elif operation_name == "delivery_health":
        assert result.status is DeliveryHealthStatus.ATTENTION
        assert result.diagnostics[0].change_id == CHANGE
        assert result.diagnostics[0].retry_safe is True
    else:
        assert result == (
            [{"operation": operation_name}] if operation_name in tuple_results else {"operation": operation_name}
        )
    serialized = result.model_dump(mode="json") if isinstance(result, BaseModel) else result
    assert "intent_bytes" not in json.dumps(serialized)
    assert "design_bytes" not in json.dumps(serialized)


@pytest.mark.asyncio
@pytest.mark.parametrize("operation_name", DELIVERY_OPERATION_NAMES)
async def test_invalid_parameters_fail_before_application_delegation(operation_name: str) -> None:
    application = _RecordingApplication()
    adapter = TargetMCPAdapter(application)  # type: ignore[arg-type]

    with pytest.raises(ToolError) as exc_info:
        await getattr(adapter, operation_name)({"unexpected": True})

    diagnostic = json.loads(str(exc_info.value))
    assert diagnostic["code"] == "ERR_TARGET_PARAM_VALIDATION"
    assert diagnostic["retry_safe"] is False
    assert application.calls == []


@pytest.mark.asyncio
async def test_publication_baseline_recovery_requires_literal_confirmation_before_delegation() -> None:
    application = _RecordingApplication()
    adapter = TargetMCPAdapter(application)  # type: ignore[arg-type]
    request = {**_requests()["recover_publication_baseline"], "confirmed_recovery": False}

    with pytest.raises(ToolError) as exc_info:
        await adapter.recover_publication_baseline(request)

    diagnostic = json.loads(str(exc_info.value))
    assert diagnostic["code"] == "ERR_TARGET_PARAM_VALIDATION"
    assert application.calls == []


def test_delivery_operation_names_annotations_and_prohibited_methods_are_exact() -> None:
    reads = {
        "read_design_session",
        "derive_delivery_contract",
        "validate_delivery_contract",
        "list_work_items",
        "delivery_health",
        "list_retained_change_worktrees",
        "show_work_item",
        "show_work_item_view",
        "show_operator_context",
        "preview_administrative_move",
        "show_plan_context",
        "show_build_context",
        "show_finalization_context",
        "show_integration_attention",
        "observe_change_publication_checks",
        "list_completed_changes",
        "search_completed_changes",
        "show_completed_change",
    }
    prohibited = {
        "create_request",
        "unblock_delivery",
        "list_semantic_updates",
        "show_completion_summary",
        "respond_to_review",
        "arbitrate_attempt",
        "recover_interrupted_task",
        "start_job",
        "finish_plan",
        "finish_build",
        "finish_assembly",
        "return_delivery",
        "publish_change_branch",
        "create_or_reconcile_draft_pull_request",
        "update_generated_pull_request_summary",
    }

    assert tuple(DELIVERY_OPERATION_ANNOTATIONS) == DELIVERY_OPERATION_NAMES
    for name, tool_annotations in DELIVERY_OPERATION_ANNOTATIONS.items():
        assert tool_annotations.destructive_hint is (
            name
            in {
                "cleanup_abandoned_change_worktree",
                "cleanup_abandoned_change_worktree_after_target_sync_discard",
                "cleanup_completed_change_worktree",
            }
        )
        assert tool_annotations.read_only_hint is (name in reads)
        assert tool_annotations.idempotent_hint is (
            name not in {"acquire_frontier_work", "resolve_request", "clear_block"}
        )
    assert all(not hasattr(TargetMCPAdapter, name) for name in prohibited)


@pytest.mark.asyncio
async def test_revise_design_session_rejects_non_digest_identity_before_delegation() -> None:
    application = _RecordingApplication()
    adapter = TargetMCPAdapter(application)  # type: ignore[arg-type]
    request = {**_requests()["revise_design_session"], "expected_package_id": "not-a-digest"}

    with pytest.raises(ToolError) as exc_info:
        await adapter.revise_design_session(request)

    diagnostic = json.loads(str(exc_info.value))
    assert diagnostic["code"] == "ERR_TARGET_PARAM_VALIDATION"
    assert application.calls == []


@pytest.mark.asyncio
async def test_recovery_requires_literal_confirmation_before_delegation() -> None:
    application = _RecordingApplication()
    adapter = TargetMCPAdapter(application)  # type: ignore[arg-type]
    request = {**_requests()["recover_change_worktree"], "confirmed_recovery": False}

    with pytest.raises(ToolError) as exc_info:
        await adapter.recover_change_worktree(request)

    diagnostic = json.loads(str(exc_info.value))
    assert diagnostic["code"] == "ERR_TARGET_PARAM_VALIDATION"
    assert application.calls == []


@pytest.mark.asyncio
async def test_named_runtime_catalog_and_integration_failures_preserve_diagnostics() -> None:
    catalog_error = CompletedHistoryMissingError(
        CompletedHistoryDiagnostic(
            code=CompletedHistoryDiagnosticCode.MISSING,
            detail="completed change is absent",
            change_id=CHANGE,
        )
    )
    cases = (
        (
            "admit_delivery_change",
            DeliveryAdmissionConflictError("active claims block Delivery authority revision"),
            "ERR_DELIVERY_ADMISSION_CONFLICT",
            False,
        ),
        (
            "admit_delivery_change",
            DeliveryAdmissionValidationError("authored Specification does not compile"),
            "ERR_DELIVERY_ADMISSION_VALIDATION",
            False,
        ),
        (
            "transition_delivery",
            DeliveryRuntimeReferenceError("outcome is absent"),
            "ERR_DELIVERY_RUNTIME_REFERENCE",
            False,
        ),
        ("list_completed_changes", catalog_error, "completed-history-missing", False),
        (
            "revise_design_session",
            DesignPackageConflictError("package identity is stale"),
            "ERR_DESIGN_PACKAGE_CONFLICT",
            False,
        ),
        (
            "reconcile_change_checkpoint",
            PublicationProviderError(
                PublicationProviderFailureCode.RATE_LIMITED,
                "create_draft_pull_request",
                "provider rate limit reached",
                retry_safe=True,
            ),
            "ERR_DELIVERY_PROVIDER_RATE_LIMITED",
            True,
        ),
        (
            "observe_acceptance",
            CompletionReceiptConflictError("completion receipt is inconsistent"),
            "ERR_COMPLETION_RECEIPT_CONFLICT",
            False,
        ),
        (
            "observe_acceptance",
            DeliveryAcceptanceWaitingError("pull request is still open and unmerged"),
            "ERR_DELIVERY_ACCEPTANCE_WAITING",
            True,
        ),
        (
            "resolve_change_disposition",
            DeliveryChangeDispositionConflictError("attention identity is stale"),
            "ERR_DELIVERY_RUNTIME_CONFLICT",
            False,
        ),
        (
            "resolve_change_disposition",
            DeliveryChangeDispositionBusyError("attention resolution is already in progress"),
            "ERR_DELIVERY_ATTENTION_RESOLVE_BUSY",
            True,
        ),
        (
            "cleanup_abandoned_change_worktree",
            CoordinationConflictError("cleanup coordination changed"),
            "ERR_TARGET_COORDINATION_CONFLICT",
            True,
        ),
        (
            "sync_change_with_target",
            ChangeTargetSyncConflictError(
                CHANGE,
                "sync-change-a",
                "c" * 40,
                ("product.txt",),
            ),
            "ERR_TARGET_SYNC_CONFLICT",
            False,
        ),
        (
            "recover_publication_baseline",
            PublicationBaselineUnavailableError(CHANGE, "publication baseline is unavailable"),
            "ERR_PUBLICATION_BASELINE_UNAVAILABLE",
            False,
        ),
        (
            "observe_acceptance",
            DeliveryStatePublicationError("state publication failed", retry_safe=True),
            "ERR_DELIVERY_STATE_PUBLICATION",
            True,
        ),
    )
    for operation_name, failure, code, retry_safe in cases:
        application = _RecordingApplication({operation_name: failure})
        adapter = TargetMCPAdapter(application)  # type: ignore[arg-type]

        with pytest.raises(ToolError) as exc_info:
            await getattr(adapter, operation_name)(_requests()[operation_name])

        diagnostic = json.loads(str(exc_info.value))
        assert diagnostic["code"] == code
        assert diagnostic["detail"] == (str(failure) or code)
        assert diagnostic["current_authority_identity"] == CHANGE
        assert diagnostic["retry_safe"] is retry_safe
        assert [call[0] for call in application.calls] == [operation_name]
