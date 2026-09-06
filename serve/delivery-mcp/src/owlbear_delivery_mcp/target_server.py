"""Strict MCPServer adapter for the Delivery portfolio application."""

from __future__ import annotations

import asyncio
import inspect
import json
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from functools import partial
from typing import Annotated, Never, cast, get_args, get_origin, get_type_hints

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import BaseModel, BeforeValidator, ConfigDict, TypeAdapter, ValidationError, create_model

from owlbear_delivery.change_workspace import (
    ChangeExternalHeadAdoptionReceipt,
    ChangeExternalHeadPromotionReceipt,
    ChangeTargetSyncAbortReceipt,
    ChangeTargetSyncReceipt,
    PublicationBaselineRecoveryReceipt,
)
from owlbear_delivery.completed_history import CompletedHistoryError
from owlbear_delivery.delivery_admission import DeliveryAdmissionRequest
from owlbear_delivery.delivery_runtime import (
    AdministrativeDeliveryMove,
    AdministrativeDeliveryMovePreview,
    AdministrativeDeliveryMoveResult,
    DeliveryPlanCandidate,
    DeliveryRequest,
    DeliveryResultCandidate,
    OutcomeAuthorityBinding,
)
from owlbear_delivery.diagnostics import classify_delivery_failure
from owlbear_delivery.draft_pull_request import MarkChangePullRequestReady
from owlbear_delivery.portfolio_application import (
    DeliveryChangePublicationSupersessionReceipt,
    DeliveryChangeWorktreeCleanup,
    DeliveryChangeWorktreeRecovery,
    DeliveryOperatorContext,
    DeliveryTargetSyncRepairReceipt,
    PortfolioApplication,
)
from owlbear_delivery.portfolio_operating import DeliveryHealthView
from owlbear_delivery_mcp.target_models import (
    AbandonChangeParams,
    AbandonChangeRequest,
    AdministrativeMoveParams,
    AdministrativeMovePreviewResponse,
    AdministrativeMoveRequest,
    AdministrativeMoveResponse,
    AdmitDeliveryChangeRequest,
    ChangeExternalHeadAdoptionResponse,
    ChangeExternalHeadPromotionResponse,
    ChangeParams,
    ChangePublicationBaselineRecoveryResponse,
    ChangeRequest,
    ChangeTargetSyncAbortResponse,
    ChangeTargetSyncResponse,
    ChangeWorktreeCleanupResponse,
    ChangeWorktreeRecoveryResponse,
    ClaimContextParams,
    ClaimContextRequest,
    CleanupAbandonedChangeParams,
    CleanupAbandonedChangeRequest,
    CleanupAbandonedTargetSyncParams,
    CleanupAbandonedTargetSyncRequest,
    CleanupCompletedChangeParams,
    CleanupCompletedChangeRequest,
    ClearBlockParams,
    ClearBlockRequest,
    ClearedDeliveryBlockResponse,
    CompletedPageParams,
    CompletedPageRequest,
    CreateDesignSessionParams,
    CreateDesignSessionRequest,
    DeferChangeParams,
    DeferChangeRequest,
    DeliveryHealthResponse,
    DeliveryOperatorContextResponse,
    DeliveryPlanPublication,
    DeliveryPublicationSupersessionResponse,
    DeliveryResultPublication,
    EmptyParams,
    EmptyRequest,
    ExternalHeadAdoptionParams,
    ExternalHeadAdoptionRequest,
    ExternalHeadPromotionParams,
    ExternalHeadPromotionRequest,
    FinalizeDeliveryChangeParams,
    FinalizeDeliveryChangeRequest,
    MarkChangeReadyRequest,
    OperatorContextParams,
    OperatorContextRequest,
    PreviewAdministrativeMoveParams,
    PreviewAdministrativeMoveRequest,
    PublishDeliveryPlanParams,
    PublishDeliveryPlanRequest,
    PublishDeliveryResultParams,
    PublishDeliveryResultRequest,
    RecoverChangeWorktreeParams,
    RecoverChangeWorktreeRequest,
    RecoverPublicationBaselineParams,
    RecoverPublicationBaselineRequest,
    RepairClaimContextParams,
    RepairClaimContextRequest,
    RepairTargetSyncPublicationParams,
    RepairTargetSyncPublicationRequest,
    ResolveChangeDispositionParams,
    ResolveChangeDispositionRequest,
    ResolvedDeliveryRequestResponse,
    ResolveRequestParams,
    ResolveRequestRequest,
    RetainedChangeWorktreeResponse,
    ReviseDesignSessionParams,
    ReviseDesignSessionRequest,
    SearchCompletedParams,
    SearchCompletedRequest,
    ShowCompletedParams,
    ShowCompletedRequest,
    SupersedePublicationParams,
    SupersedePublicationRequest,
    TargetDiagnostic,
    TargetSyncConflictParams,
    TargetSyncConflictRequest,
    TargetSyncParams,
    TargetSyncPublicationRepairResponse,
    TargetSyncRequest,
    TransitionDeliveryParams,
    TransitionDeliveryRequest,
    WorkItemParams,
    WorkItemRequest,
    WorkItemViewParams,
    WorkItemViewRequest,
)

_READ = ToolAnnotations(read_only_hint=True, idempotent_hint=True, destructive_hint=False)
_WRITE = ToolAnnotations(read_only_hint=False, idempotent_hint=True, destructive_hint=False)
_OPERATOR_WRITE = ToolAnnotations(read_only_hint=False, idempotent_hint=False, destructive_hint=False)
_CLEANUP = ToolAnnotations(read_only_hint=False, idempotent_hint=True, destructive_hint=True)
_ACQUIRE = ToolAnnotations(read_only_hint=False, idempotent_hint=False, destructive_hint=False)

DELIVERY_OPERATION_NAMES = (
    "create_design_session",
    "read_design_session",
    "revise_design_session",
    "publish_design_checkpoint",
    "derive_delivery_contract",
    "admit_delivery_change",
    "list_work_items",
    "delivery_health",
    "repair_target_sync_publication",
    "list_retained_change_worktrees",
    "show_work_item",
    "show_work_item_view",
    "show_operator_context",
    "resolve_request",
    "clear_block",
    "preview_administrative_move",
    "administrative_move",
    "acquire_frontier_work",
    "show_plan_context",
    "show_build_context",
    "show_finalization_context",
    "publish_delivery_plan",
    "publish_delivery_result",
    "finalize_change",
    "mark_change_ready",
    "prepare_review_repair",
    "reconcile_finalization_head",
    "reconcile_change_checkpoint",
    "sync_change_with_target",
    "adopt_external_head",
    "promote_external_head",
    "abort_target_sync_conflict",
    "resolve_target_sync_conflict",
    "supersede_publication",
    "observe_change_publication_checks",
    "observe_acceptance",
    "resolve_change_disposition",
    "defer_change",
    "resume_change",
    "abandon_change",
    "cleanup_abandoned_change_worktree",
    "cleanup_abandoned_change_worktree_after_target_sync_discard",
    "cleanup_completed_change_worktree",
    "recover_change_worktree",
    "recover_publication_baseline",
    "transition_delivery",
    "recover_claim",
    "recover_integration_repair_claim",
    "show_integration_attention",
    "list_completed_changes",
    "search_completed_changes",
    "show_completed_change",
)
_DELIVERY_READS = frozenset(
    {
        "read_design_session",
        "derive_delivery_contract",
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
)
_DELIVERY_NON_IDEMPOTENT_WRITES = frozenset({"resolve_request", "clear_block", "administrative_move"})
DELIVERY_OPERATION_ANNOTATIONS = {
    name: _READ
    if name in _DELIVERY_READS
    else _ACQUIRE
    if name == "acquire_frontier_work"
    else _CLEANUP
    if name
    in {
        "cleanup_abandoned_change_worktree",
        "cleanup_abandoned_change_worktree_after_target_sync_discard",
        "cleanup_completed_change_worktree",
    }
    else _OPERATOR_WRITE
    if name in _DELIVERY_NON_IDEMPOTENT_WRITES
    else _WRITE
    for name in DELIVERY_OPERATION_NAMES
}

type StructuredOutput = dict[str, object] | list[object] | str | int | float | bool | None
type ApplicationProvider = Callable[[], PortfolioApplication]


@dataclass(frozen=True)
class DeliveryAppContext:
    """Resolved Delivery application shared by every live MCP tool."""

    application: PortfolioApplication


class TargetMCPAdapter:
    """Validate and delegate the strict Delivery transport contract.

    Synchronous application calls run in worker threads. Cancelling a handler only
    cancels the transport wait; an in-flight mutation may finish, so callers must
    reconcile durable state before retrying rather than blindly replaying it.
    """

    def __init__(
        self,
        application: PortfolioApplication | None = None,
        *,
        provider: ApplicationProvider | None = None,
    ) -> None:
        if provider is not None:
            self._application_provider = provider
        elif application is not None:
            self._application_provider = lambda: application
        else:
            message = "an application or provider is required"
            raise TypeError(message)

    @classmethod
    def from_provider(cls, provider: ApplicationProvider) -> TargetMCPAdapter:
        """Bind tools before lifespan while resolving one live application per call."""
        return cls(provider=provider)

    @property
    def _application(self) -> PortfolioApplication:
        return self._application_provider()

    async def create_design_session(self, request: CreateDesignSessionRequest) -> dict[str, object]:
        """Create one authored Design session."""
        params = self._validate(CreateDesignSessionParams, request)
        return self._call(
            params,
            lambda: self._application.create_design_session(
                params.change_id,
                params.intent_bytes,
                params.design_bytes,
            ),
        )

    async def read_design_session(self, request: ChangeRequest) -> dict[str, object]:
        """Read one verified authored Design session and its current identity."""
        params = self._validate(ChangeParams, request)
        return self._call(params, lambda: self._application.read_design_session(params.change_id))

    async def revise_design_session(self, request: ReviseDesignSessionRequest) -> dict[str, object]:
        """Replace authored Design bytes for one exact package identity."""
        params = self._validate(ReviseDesignSessionParams, request)
        return self._call(
            params,
            lambda: self._application.revise_design_session(
                params.change_id,
                params.expected_package_id,
                params.intent_bytes,
                params.design_bytes,
            ),
        )

    async def publish_design_checkpoint(self, request: ChangeRequest) -> dict[str, object]:
        """Publish one verified Design checkpoint."""
        params = self._validate(ChangeParams, request)
        return self._call(params, lambda: self._application.publish_design_checkpoint(params.change_id))

    async def derive_delivery_contract(self, request: ChangeRequest) -> dict[str, object]:
        """Derive one Delivery contract without publication."""
        params = self._validate(ChangeParams, request)
        return self._call(params, lambda: self._application.derive_delivery_contract(params.change_id))

    async def admit_delivery_change(self, request: AdmitDeliveryChangeRequest) -> dict[str, object]:
        """Admit one source-bound Delivery change."""
        params = self._validate(DeliveryAdmissionRequest, request)
        return await asyncio.to_thread(
            self._call,
            params,
            lambda: self._application.admit_delivery_change(params),
        )

    async def list_work_items(self, request: EmptyRequest) -> list[object]:
        """List bounded work-item projections."""
        params = self._validate(EmptyParams, request)
        return self._call(params, self._application.list_work_items)

    async def delivery_health(self, request: EmptyRequest) -> DeliveryHealthResponse:
        """Return bounded diagnostics for quarantined or unavailable Delivery state."""
        params = self._validate(EmptyParams, request)
        health = self._call_model(params, self._application.delivery_health, DeliveryHealthView)
        return DeliveryHealthResponse.from_view(health)

    async def repair_target_sync_publication(
        self,
        request: RepairTargetSyncPublicationRequest,
    ) -> TargetSyncPublicationRepairResponse:
        """Repair one exact quarantined target-sync publication after confirmation."""
        params = self._validate(RepairTargetSyncPublicationParams, request)
        receipt = await asyncio.to_thread(
            self._call_model,
            params,
            lambda: self._application.repair_target_sync_publication(
                params.change_id,
                params.expected_remote_head,
                params.expected_merged_head,
                params.target_sync_operation_id,
                params.operation_id,
                confirmed_repair=params.confirmed_repair,
            ),
            DeliveryTargetSyncRepairReceipt,
        )
        return TargetSyncPublicationRepairResponse.from_receipt(receipt)

    async def list_retained_change_worktrees(self, request: EmptyRequest) -> list[object]:
        """List retained Change worktrees and their cleanup eligibility."""
        params = self._validate(EmptyParams, request)

        def project() -> tuple[RetainedChangeWorktreeResponse, ...]:
            projections = self._application.list_retained_change_worktrees()
            return tuple(RetainedChangeWorktreeResponse.from_projection(item) for item in projections)

        return cast("list[object]", self._call(params, project))

    async def show_work_item(self, request: WorkItemRequest) -> dict[str, object]:
        """Show one exact bounded work item."""
        params = self._validate(WorkItemParams, request)
        return self._call(params, lambda: self._application.show_work_item(params.change_id, params.work_item_id))

    async def show_work_item_view(self, request: WorkItemViewRequest) -> dict[str, object]:
        """Show one exact detailed Work Item view."""
        params = self._validate(WorkItemViewParams, request)
        return self._call(
            params,
            lambda: self._application.show_work_item_view(params.change_id, params.item_key),
        )

    async def show_operator_context(self, request: OperatorContextRequest) -> DeliveryOperatorContextResponse:
        """Show bounded operator state for one exact outcome or Change."""
        params = self._validate(OperatorContextParams, request)
        context = await asyncio.to_thread(
            self._call_model,
            params,
            lambda: self._application.show_operator_context(params.change_id, params.outcome_id),
            DeliveryOperatorContext,
        )
        return DeliveryOperatorContextResponse.from_context(context)

    async def resolve_request(self, request: ResolveRequestRequest) -> ResolvedDeliveryRequestResponse:
        """Persist one user-owned answer for a retained Delivery request."""
        params = self._validate(ResolveRequestParams, request)
        resolved = await asyncio.to_thread(
            self._call_model,
            params,
            lambda: self._application.resolve_request(
                params.change_id,
                params.request_id,
                params.resolution,
            ),
            DeliveryRequest,
        )
        return ResolvedDeliveryRequestResponse(change_id=params.change_id, request=resolved)

    async def clear_block(self, request: ClearBlockRequest) -> ClearedDeliveryBlockResponse:
        """Clear one requestless block with explicit operator evidence."""
        params = self._validate(ClearBlockParams, request)
        binding = await asyncio.to_thread(
            self._call_model,
            params,
            lambda: self._application.clear_block(
                params.change_id,
                params.outcome_id,
                params.block_id,
                params.operator_note,
                params.locators,
            ),
            OutcomeAuthorityBinding,
        )
        if binding.block is None:
            message = "unsupported cleared block output: missing block"
            raise TypeError(message)
        return ClearedDeliveryBlockResponse(
            change_id=params.change_id,
            outcome_id=binding.outcome_id,
            block=binding.block,
        )

    async def preview_administrative_move(
        self,
        request: PreviewAdministrativeMoveRequest,
    ) -> AdministrativeMovePreviewResponse:
        """Preview one backward movement without changing Delivery state."""
        params = self._validate(PreviewAdministrativeMoveParams, request)
        preview = await asyncio.to_thread(
            self._call_model,
            params,
            lambda: self._application.preview_administrative_move(
                params.change_id,
                params.outcome_id,
                params.target,
            ),
            AdministrativeDeliveryMovePreview,
        )
        return AdministrativeMovePreviewResponse.from_preview(preview)

    async def administrative_move(self, request: AdministrativeMoveRequest) -> AdministrativeMoveResponse:
        """Apply one exact operator-directed backward movement."""
        params = self._validate(AdministrativeMoveParams, request)
        result = await asyncio.to_thread(
            self._call_model,
            params,
            lambda: self._application.administrative_move(
                params.change_id,
                AdministrativeDeliveryMove(
                    move_id=params.move_id,
                    outcome_id=params.outcome_id,
                    target=params.target,
                    reason=params.reason,
                    expected_version=params.expected_version,
                ),
            ),
            AdministrativeDeliveryMoveResult,
        )
        return AdministrativeMoveResponse.from_result(result)

    async def acquire_frontier_work(self, request: EmptyRequest) -> dict[str, object]:
        """Acquire currently available frontier work."""
        params = self._validate(EmptyParams, request)
        return await asyncio.to_thread(
            self._call,
            params,
            self._application.acquire_frontier_work,
        )

    async def show_plan_context(self, request: ClaimContextRequest) -> dict[str, object]:
        """Show bounded Planning context for one claim."""
        params = self._validate(ClaimContextParams, request)
        return self._call(params, lambda: self._application.show_plan_context(**params.model_dump()))

    async def show_build_context(self, request: ClaimContextRequest) -> dict[str, object]:
        """Show bounded Build context for one claim."""
        params = self._validate(ClaimContextParams, request)
        return self._call(params, lambda: self._application.show_build_context(**params.model_dump()))

    async def show_finalization_context(self, request: ChangeRequest) -> dict[str, object]:
        """Show engine-resolved context for one exact Change finalization."""
        params = self._validate(ChangeParams, request)
        return self._call(params, lambda: self._application.show_finalization_context(params.change_id))

    async def publish_delivery_plan(self, request: PublishDeliveryPlanRequest) -> DeliveryPlanPublication:
        """Publish one claim-scoped Delivery plan."""
        params = self._validate(PublishDeliveryPlanParams, request)
        candidate = self._call_model(
            params,
            lambda: self._application.publish_delivery_plan(params.change_id, params.plan),
            DeliveryPlanCandidate,
        )
        return DeliveryPlanPublication.from_candidate(candidate)

    async def publish_delivery_result(self, request: PublishDeliveryResultRequest) -> DeliveryResultPublication:
        """Publish one claim-scoped Delivery result."""
        params = self._validate(PublishDeliveryResultParams, request)
        candidate = self._call_model(
            params,
            lambda: self._application.publish_delivery_result(params.change_id, params.result),
            DeliveryResultCandidate,
        )
        return DeliveryResultPublication.from_candidate(candidate)

    async def finalize_change(self, request: FinalizeDeliveryChangeRequest) -> dict[str, object]:
        """Finalize one exact clean reviewed Change head with persisted evidence."""
        params = self._validate(FinalizeDeliveryChangeParams, request)
        return await asyncio.to_thread(
            self._call,
            params,
            lambda: self._application.finalize_change(params.change_id, params.finalization),
        )

    async def mark_change_ready(self, request: MarkChangeReadyRequest) -> dict[str, object]:
        """Mark one exact finalized and fully published Change pull request ready."""
        params = self._validate(MarkChangePullRequestReady, request)
        return await asyncio.to_thread(
            self._call,
            params,
            lambda: self._application.mark_change_ready(params.change_id, params),
        )

    async def prepare_review_repair(self, request: ChangeRequest) -> dict[str, object]:
        """Return one open Change pull request to draft before external review repair."""
        params = self._validate(ChangeParams, request)
        return await asyncio.to_thread(
            self._call,
            params,
            lambda: self._application.prepare_review_repair(params.change_id),
        )

    async def reconcile_finalization_head(self, request: ChangeRequest) -> dict[str, object] | None:
        """Retain or invalidate finalization from engine-derived local/provider head evidence."""
        params = self._validate(ChangeParams, request)
        return await asyncio.to_thread(
            self._call,
            params,
            lambda: self._application.reconcile_finalization_head(params.change_id),
        )

    async def reconcile_change_checkpoint(self, request: ChangeRequest) -> dict[str, object]:
        """Reconcile one durable checkpoint using only engine-derived external identities."""
        params = self._validate(ChangeParams, request)
        return await asyncio.to_thread(
            self._call,
            params,
            lambda: self._application.reconcile_change_checkpoint(params.change_id),
        )

    async def supersede_publication(
        self,
        request: SupersedePublicationRequest,
    ) -> DeliveryPublicationSupersessionResponse:
        """Publish one successor branch and pull request for exact publication attention."""
        params = self._validate(SupersedePublicationParams, request)
        receipt = await asyncio.to_thread(
            self._call_model,
            params,
            lambda: self._application.supersede_publication(
                params.change_id,
                params.expected_publication_id,
                params.operation_id,
            ),
            DeliveryChangePublicationSupersessionReceipt,
        )
        return DeliveryPublicationSupersessionResponse.from_receipt(receipt)

    async def sync_change_with_target(
        self,
        request: TargetSyncRequest,
    ) -> ChangeTargetSyncResponse:
        """Fetch and merge one exact target head through the managed Change worktree."""
        params = self._validate(TargetSyncParams, request)
        receipt = await asyncio.to_thread(
            self._call_model,
            params,
            lambda: self._application.sync_change_with_target(
                params.change_id,
                params.expected_target,
                params.operation_id,
            ),
            ChangeTargetSyncReceipt,
        )
        return ChangeTargetSyncResponse.from_receipt(receipt)

    async def adopt_external_head(
        self,
        request: ExternalHeadAdoptionRequest,
    ) -> ChangeExternalHeadAdoptionResponse:
        """Adopt one exact remote Change descendant through the managed Change worktree."""
        params = self._validate(ExternalHeadAdoptionParams, request)
        receipt = await asyncio.to_thread(
            self._call_model,
            params,
            lambda: self._application.adopt_external_head(
                params.change_id,
                params.expected_head,
                params.adopted_head,
                params.operation_id,
            ),
            ChangeExternalHeadAdoptionReceipt,
        )
        return ChangeExternalHeadAdoptionResponse.from_receipt(receipt)

    async def promote_external_head(self, request: ExternalHeadPromotionRequest) -> ChangeExternalHeadPromotionResponse:
        """Promote one exact adopted external Change head before Builder acquisition."""
        params = self._validate(ExternalHeadPromotionParams, request)
        receipt = await asyncio.to_thread(
            self._call_model,
            params,
            lambda: self._application.promote_external_head(
                params.change_id,
                params.expected_head,
                params.operation_id,
            ),
            ChangeExternalHeadPromotionReceipt,
        )
        return ChangeExternalHeadPromotionResponse.from_receipt(receipt)

    async def abort_target_sync_conflict(
        self,
        request: TargetSyncConflictRequest,
    ) -> ChangeTargetSyncAbortResponse:
        """Abort one exact preserved target-sync conflict."""
        params = self._validate(TargetSyncConflictParams, request)
        receipt = await asyncio.to_thread(
            self._call_model,
            params,
            lambda: self._application.abort_target_sync_conflict(
                params.change_id,
                params.expected_disposition_id,
                params.target_head,
                params.operation_id,
            ),
            ChangeTargetSyncAbortReceipt,
        )
        return ChangeTargetSyncAbortResponse.from_receipt(receipt)

    async def resolve_target_sync_conflict(
        self,
        request: TargetSyncConflictRequest,
    ) -> ChangeTargetSyncResponse:
        """Resolve one exact preserved target-sync conflict with a reviewed merge."""
        params = self._validate(TargetSyncConflictParams, request)
        receipt = await asyncio.to_thread(
            self._call_model,
            params,
            lambda: self._application.resolve_target_sync_conflict(
                params.change_id,
                params.expected_disposition_id,
                params.target_head,
                params.operation_id,
            ),
            ChangeTargetSyncReceipt,
        )
        return ChangeTargetSyncResponse.from_receipt(receipt)

    async def observe_change_publication_checks(
        self,
        request: ChangeRequest,
    ) -> dict[str, object]:
        """Observe checks at the engine-derived published Change head."""
        params = self._validate(ChangeParams, request)
        return await asyncio.to_thread(
            self._call,
            params,
            lambda: self._application.observe_change_publication_checks(params.change_id),
        )

    async def observe_acceptance(self, request: ChangeRequest) -> dict[str, object]:
        """Complete one Change from engine-derived merged pull-request evidence."""
        params = self._validate(ChangeParams, request)
        return await asyncio.to_thread(
            self._call,
            params,
            lambda: self._application.observe_acceptance(params.change_id),
        )

    async def resolve_change_disposition(self, request: ResolveChangeDispositionRequest) -> dict[str, object]:
        """Resolve one exact Change attention record without restoring provider authority."""
        params = self._validate(ResolveChangeDispositionParams, request)
        return await asyncio.to_thread(
            self._call,
            params,
            lambda: self._application.resolve_change_disposition(
                params.change_id,
                params.expected_disposition_id,
            ),
        )

    async def defer_change(self, request: DeferChangeRequest) -> dict[str, object]:
        """Retain one Change while pausing its claimable frontier."""
        params = self._validate(DeferChangeParams, request)
        return await asyncio.to_thread(
            self._call,
            params,
            lambda: self._application.defer_change(params.change_id, params.reason),
        )

    async def resume_change(self, request: ChangeRequest) -> dict[str, object]:
        """Resume one deferred Change from its retained prior state."""
        params = self._validate(ChangeParams, request)
        return await asyncio.to_thread(
            self._call,
            params,
            lambda: self._application.resume_change(params.change_id),
        )

    async def abandon_change(self, request: AbandonChangeRequest) -> dict[str, object]:
        """Terminate one uncompleted Change by explicit user disposition."""
        params = self._validate(AbandonChangeParams, request)
        return await asyncio.to_thread(
            self._call,
            params,
            lambda: self._application.abandon_change(params.change_id, params.reason),
        )

    async def cleanup_abandoned_change_worktree(
        self,
        request: CleanupAbandonedChangeRequest,
    ) -> ChangeWorktreeCleanupResponse:
        """Remove one exact abandoned Change worktree while retaining its branch."""
        params = self._validate(CleanupAbandonedChangeParams, request)
        receipt = await asyncio.to_thread(
            self._call_model,
            params,
            lambda: self._application.cleanup_abandoned_change_worktree(params.change_id),
            DeliveryChangeWorktreeCleanup,
        )
        return ChangeWorktreeCleanupResponse.from_receipt(receipt)

    async def cleanup_abandoned_change_worktree_after_target_sync_discard(
        self,
        request: CleanupAbandonedTargetSyncRequest,
    ) -> ChangeWorktreeCleanupResponse:
        """Discard one abandoned target merge and remove its exact worktree."""
        params = self._validate(CleanupAbandonedTargetSyncParams, request)
        receipt = await asyncio.to_thread(
            self._call_model,
            params,
            lambda: self._application.cleanup_abandoned_change_worktree_after_target_sync_discard(
                params.change_id,
                confirmed_discard=params.confirmed_discard,
                expected_target_head=params.expected_target_head,
                expected_operation_id=params.expected_operation_id,
            ),
            DeliveryChangeWorktreeCleanup,
        )
        return ChangeWorktreeCleanupResponse.from_receipt(receipt)

    async def cleanup_completed_change_worktree(
        self,
        request: CleanupCompletedChangeRequest,
    ) -> ChangeWorktreeCleanupResponse:
        """Remove one exact completed Change worktree after receipt validation."""
        params = self._validate(CleanupCompletedChangeParams, request)
        receipt = await asyncio.to_thread(
            self._call_model,
            params,
            lambda: self._application.cleanup_completed_change_worktree(
                params.change_id,
                params.completion_id,
            ),
            DeliveryChangeWorktreeCleanup,
        )
        return ChangeWorktreeCleanupResponse.from_receipt(receipt)

    async def recover_change_worktree(
        self,
        request: RecoverChangeWorktreeRequest,
    ) -> ChangeWorktreeRecoveryResponse:
        """Recreate one exact Change worktree after explicit reviewed-head confirmation."""
        params = self._validate(RecoverChangeWorktreeParams, request)
        receipt = await asyncio.to_thread(
            self._call_model,
            params,
            lambda: self._application.recover_change_worktree(
                params.change_id,
                params.recovery_reviewed_head,
                confirmed_recovery=params.confirmed_recovery,
            ),
            DeliveryChangeWorktreeRecovery,
        )
        return ChangeWorktreeRecoveryResponse.from_receipt(receipt)

    async def recover_publication_baseline(
        self,
        request: RecoverPublicationBaselineRequest,
    ) -> ChangePublicationBaselineRecoveryResponse:
        """Recover one unknown publication baseline after explicit confirmation."""
        params = self._validate(RecoverPublicationBaselineParams, request)
        receipt = await asyncio.to_thread(
            self._call_model,
            params,
            lambda: self._application.recover_publication_baseline(
                params.change_id,
                params.expected_change_head,
                params.publication_base_head,
                params.operation_id,
                confirmed_recovery=params.confirmed_recovery,
            ),
            PublicationBaselineRecoveryReceipt,
        )
        return ChangePublicationBaselineRecoveryResponse.from_receipt(receipt)

    async def transition_delivery(self, request: TransitionDeliveryRequest) -> dict[str, object]:
        """Apply one worker-owned Delivery transition."""
        params = self._validate(TransitionDeliveryParams, request)
        return self._call(params, lambda: self._application.transition_delivery(params.change_id, params.transition))

    async def recover_claim(self, request: ClaimContextRequest) -> dict[str, object]:
        """Recover one exact failed Delivery claim."""
        params = self._validate(ClaimContextParams, request)
        return self._call(params, lambda: self._application.recover_claim(**params.model_dump()))

    async def recover_integration_repair_claim(
        self,
        request: RepairClaimContextRequest,
    ) -> dict[str, object]:
        """Recover one exact failed Integration repair claim."""
        params = self._validate(RepairClaimContextParams, request)
        return self._call(
            params,
            lambda: self._application.recover_integration_repair_claim(**params.model_dump()),
        )

    async def show_integration_attention(self, request: ChangeRequest) -> dict[str, object] | None:
        """Show current typed Integration attention."""
        params = self._validate(ChangeParams, request)
        return self._call(params, lambda: self._application.show_integration_attention(params.change_id))

    async def list_completed_changes(self, request: CompletedPageRequest) -> dict[str, object]:
        """List one bounded completed-history page."""
        params = self._validate(CompletedPageParams, request)
        return self._call(params, lambda: self._application.list_completed_changes(params.cursor, params.limit))

    async def search_completed_changes(self, request: SearchCompletedRequest) -> dict[str, object]:
        """Search bounded completed-history summaries."""
        params = self._validate(SearchCompletedParams, request)
        return self._call(
            params,
            lambda: self._application.search_completed_changes(params.query, params.cursor, params.limit),
        )

    async def show_completed_change(self, request: ShowCompletedRequest) -> dict[str, object]:
        """Show one exact completed Delivery change."""
        params = self._validate(ShowCompletedParams, request)
        return self._call(
            params,
            lambda: self._application.show_completed_change(params.change_id, params.completion_id),
        )

    @staticmethod
    def _validate[ModelT: BaseModel](model: type[ModelT], payload: ModelT | dict[str, object]) -> ModelT:
        if isinstance(payload, model):
            return payload
        try:
            try:
                return model.model_validate(payload)
            except ValidationError:
                return model.model_validate_json(json.dumps(payload, default=_json_default))
        except (TypeError, ValueError, ValidationError) as exc:
            TargetMCPAdapter._raise(
                "ERR_TARGET_PARAM_VALIDATION",
                str(exc),
                TargetMCPAdapter._payload_authority(payload),
                retry_safe=False,
            )

    def _call_model[ModelT: BaseModel](
        self,
        params: BaseModel,
        operation: Callable[[], object],
        model: type[ModelT],
    ) -> ModelT:
        value = self._call_raw(params, operation)
        if not isinstance(value, model):
            message = f"unsupported structured output: {type(value).__name__}"
            raise TypeError(message)
        return value

    def _call(self, params: BaseModel, operation: Callable[[], object]) -> StructuredOutput:
        return self._serialize(self._call_raw(params, operation))

    def _call_raw(self, params: BaseModel, operation: Callable[[], object]) -> object:
        try:
            return operation()
        except Exception as exc:
            failure = classify_delivery_failure(exc)
            if failure is None:
                raise
            authority = self._authority(params)
            if isinstance(exc, CompletedHistoryError):
                authority = exc.diagnostic.change_id or exc.diagnostic.completion_id or authority
            self._raise(failure.code, failure.detail, authority, retry_safe=failure.retry_safe)

    @staticmethod
    def _serialize(value: object) -> StructuredOutput:
        if isinstance(value, BaseModel):
            return value.model_dump(mode="json")
        if isinstance(value, tuple):
            return [TargetMCPAdapter._serialize(item) for item in value]
        if value is None or isinstance(value, str | int | float | bool):
            return value
        message = f"unsupported structured output: {type(value).__name__}"
        raise TypeError(message)

    @classmethod
    def _authority(cls, params: BaseModel) -> str:
        return cls._payload_authority(params.model_dump(mode="json"))

    @classmethod
    def _payload_authority(cls, payload: dict[str, object]) -> str:
        for key in ("authority_digest", "change_id"):
            identity = cls._find_field(payload, key)
            if identity is not None:
                return identity
        return "portfolio"

    @staticmethod
    def _find_field(value: object, field: str) -> str | None:
        if isinstance(value, dict):
            candidate = value.get(field)
            if isinstance(candidate, str):
                return candidate
            return next(
                (found for item in value.values() if (found := TargetMCPAdapter._find_field(item, field))),
                None,
            )
        if isinstance(value, list | tuple):
            return next((found for item in value if (found := TargetMCPAdapter._find_field(item, field))), None)
        return None

    @staticmethod
    def _raise(code: str, detail: str, authority: str, *, retry_safe: bool) -> Never:
        diagnostic = TargetDiagnostic(
            code=code,
            detail=detail,
            current_authority_identity=authority,
            retry_safe=retry_safe,
        )
        raise ToolError(diagnostic.model_dump_json())


def assemble_target_server(application: PortfolioApplication) -> MCPServer:
    """Assemble the exact Delivery registry around one explicit application."""

    @asynccontextmanager
    async def lifespan(_server: MCPServer) -> AsyncIterator[DeliveryAppContext]:
        yield DeliveryAppContext(application=application)

    server = MCPServer("owlbear-delivery", lifespan=lifespan)
    register_target_tools(server, TargetMCPAdapter(application))
    return server


def register_target_tools(server: MCPServer, adapter: TargetMCPAdapter) -> None:
    """Register the exact Delivery operation contract."""
    for name, tool_annotations in DELIVERY_OPERATION_ANNOTATIONS.items():
        server.tool(name=name, annotations=tool_annotations)(_flatten_tool(adapter, name))
        _install_strict_argument_model(server, name)


def _install_strict_argument_model(server: MCPServer, name: str) -> None:
    """Replace MCP's permissive argument model with an extra-forbid variant."""
    tool_manager = getattr(server, "_tool_manager", None)
    tool = tool_manager.get_tool(name) if tool_manager is not None else None
    if tool is None:
        message = f"Delivery MCP operation {name} was not registered"
        raise RuntimeError(message)
    argument_model = create_model(
        f"Strict{name.title().replace('_', '')}Arguments",
        __base__=tool.fn_metadata.arg_model,
        __config__=ConfigDict(extra="forbid"),
    )
    tool.fn_metadata.arg_model = argument_model
    tool.parameters = argument_model.model_json_schema(by_alias=True)


def _flatten_tool(adapter: TargetMCPAdapter, name: str) -> Callable[..., object]:
    """Expose one adapter model as strict top-level MCP keyword arguments."""
    method = getattr(adapter, name)
    hints = get_type_hints(method, include_extras=True)
    request_annotation = hints["request"]
    while not isinstance(request_annotation, type):
        alias_value = getattr(request_annotation, "__value__", None)
        if alias_value is not None and alias_value is not request_annotation:
            request_annotation = alias_value
            continue
        if get_origin(request_annotation) is None:
            break
        arguments = get_args(request_annotation)
        if not arguments:
            break
        request_annotation = arguments[0]
    if not isinstance(request_annotation, type) or not issubclass(request_annotation, BaseModel):
        message = f"Delivery MCP operation {name} has no Pydantic request model"
        raise TypeError(message)

    parameters: list[inspect.Parameter] = []
    annotations: dict[str, object] = {}
    for field_name, field in request_annotation.model_fields.items():
        default = inspect.Parameter.empty
        if not field.is_required():
            default = field.default
            if field.default_factory is not None:
                default = field.default_factory()
        annotation = field.rebuild_annotation()
        annotation = Annotated[
            annotation,
            BeforeValidator(partial(_parse_flat_field, annotation)),
        ]
        annotations[field_name] = annotation
        parameters.append(
            inspect.Parameter(
                field_name,
                inspect.Parameter.KEYWORD_ONLY,
                default=default,
                annotation=annotation,
            )
        )

    async def flat_tool(**payload: object) -> object:
        params = request_annotation.model_validate(payload)
        return await method(params)

    flat_tool.__name__ = name
    flat_tool.__qualname__ = name
    flat_tool.__doc__ = method.__doc__
    annotations["return"] = hints.get("return", inspect.Signature.empty)
    flat_tool.__annotations__ = annotations
    flat_tool.__signature__ = inspect.Signature(
        parameters=parameters,
        return_annotation=annotations["return"],
    )
    return flat_tool


def _parse_flat_field(annotation: object, value: object) -> object:
    """Parse JSON-shaped MCP values before strict nested model validation."""
    if isinstance(value, BaseModel):
        return value
    return TypeAdapter(annotation).validate_json(json.dumps(value))


def _json_default(value: object) -> object:
    """Serialize nested Pydantic values when normalizing MCP arguments."""
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    message = f"Object of type {type(value).__name__} is not JSON serializable"
    raise TypeError(message)


__all__ = [
    "DELIVERY_OPERATION_ANNOTATIONS",
    "DELIVERY_OPERATION_NAMES",
    "DeliveryAppContext",
    "TargetMCPAdapter",
    "assemble_target_server",
    "register_target_tools",
]
