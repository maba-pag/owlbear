"""Strict MCPServer adapter for the Delivery portfolio application."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Never, cast

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import BaseModel, ValidationError

from owlbear_delivery.acceptance import CompletionReceiptConflictError
from owlbear_delivery.change_workspace import (
    ChangeExternalHeadAdoptionReceipt,
    ChangeTargetSyncAbortReceipt,
    ChangeTargetSyncConflictError,
    ChangeTargetSyncReceipt,
    ChangeWorktreeAttentionError,
    CoordinationConflictError,
)
from owlbear_delivery.completed_history import CompletedHistoryError, CompletedHistoryStaleError
from owlbear_delivery.delivery_runtime import (
    DeliveryPlanCandidate,
    DeliveryResultCandidate,
    DeliveryRuntimeConflictError,
    DeliveryRuntimeReferenceError,
)
from owlbear_delivery.design_package import DesignPackageConflictError
from owlbear_delivery.portfolio_application import (
    DeliveryChangePublicationSupersessionReceipt,
    DeliveryChangeWorktreeCleanup,
    DeliveryChangeWorktreeRecovery,
    PortfolioApplication,
    PortfolioApplicationError,
)
from owlbear_delivery.publication_provider import PublicationProviderError
from owlbear_delivery.runtime_transaction import (
    TransactionConflictError,
    TransactionManifestError,
    TransactionPathError,
)
from owlbear_delivery.target_admission import TargetAdmissionError
from owlbear_delivery_mcp.target_models import (
    AbandonChangeParams,
    AbandonChangeRequest,
    AdmitDeliveryChangeParams,
    AdmitDeliveryChangeRequest,
    ChangeExternalHeadAdoptionResponse,
    ChangeParams,
    ChangeRequest,
    ChangeTargetSyncAbortResponse,
    ChangeTargetSyncResponse,
    ChangeWorktreeCleanupResponse,
    ChangeWorktreeRecoveryResponse,
    ClaimContextParams,
    ClaimContextRequest,
    CleanupAbandonedChangeParams,
    CleanupAbandonedChangeRequest,
    CleanupCompletedChangeParams,
    CleanupCompletedChangeRequest,
    CompletedPageParams,
    CompletedPageRequest,
    CreateDesignSessionParams,
    CreateDesignSessionRequest,
    DeferChangeParams,
    DeferChangeRequest,
    DeliveryPlanPublication,
    DeliveryPublicationSupersessionResponse,
    DeliveryResultPublication,
    EmptyParams,
    EmptyRequest,
    ExternalHeadAdoptionParams,
    ExternalHeadAdoptionRequest,
    FinalizeDeliveryChangeParams,
    FinalizeDeliveryChangeRequest,
    MarkChangeReadyParams,
    MarkChangeReadyRequest,
    PublishDeliveryPlanParams,
    PublishDeliveryPlanRequest,
    PublishDeliveryResultParams,
    PublishDeliveryResultRequest,
    RecoverChangeWorktreeParams,
    RecoverChangeWorktreeRequest,
    RepairClaimContextParams,
    RepairClaimContextRequest,
    ResolveChangeDispositionParams,
    ResolveChangeDispositionRequest,
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
    TargetSyncRequest,
    TransitionDeliveryParams,
    TransitionDeliveryRequest,
    WorkItemParams,
    WorkItemRequest,
)

_READ = ToolAnnotations(read_only_hint=True, idempotent_hint=True, destructive_hint=False)
_WRITE = ToolAnnotations(read_only_hint=False, idempotent_hint=True, destructive_hint=False)
_CLEANUP = ToolAnnotations(read_only_hint=False, idempotent_hint=True, destructive_hint=True)
_ACQUIRE = ToolAnnotations(read_only_hint=False, idempotent_hint=False, destructive_hint=False)

DELIVERY_OPERATION_NAMES = (
    "create_design_session",
    "read_design_session",
    "revise_design_session",
    "publish_design_checkpoint",
    "derive_delivery_contract",
    "validate_delivery_contract",
    "admit_delivery_change",
    "list_work_items",
    "list_retained_change_worktrees",
    "show_work_item",
    "acquire_frontier_work",
    "show_plan_context",
    "show_build_context",
    "show_finalization_context",
    "publish_delivery_plan",
    "publish_delivery_result",
    "finalize_change",
    "mark_change_ready",
    "reconcile_finalization_head",
    "reconcile_change_checkpoint",
    "sync_change_with_target",
    "adopt_external_head",
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
    "cleanup_completed_change_worktree",
    "recover_change_worktree",
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
        "validate_delivery_contract",
        "list_work_items",
        "list_retained_change_worktrees",
        "show_work_item",
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
DELIVERY_OPERATION_ANNOTATIONS = {
    name: _READ
    if name in _DELIVERY_READS
    else _ACQUIRE
    if name == "acquire_frontier_work"
    else _CLEANUP
    if name in {"cleanup_abandoned_change_worktree", "cleanup_completed_change_worktree"}
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
    """Validate and delegate the strict Delivery transport contract."""

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

    async def validate_delivery_contract(self, request: ChangeRequest) -> dict[str, object]:
        """Validate one derived Delivery contract."""
        params = self._validate(ChangeParams, request)
        return self._call(params, lambda: self._application.validate_delivery_contract(params.change_id))

    async def admit_delivery_change(self, request: AdmitDeliveryChangeRequest) -> dict[str, object]:
        """Admit one source-bound Delivery change."""
        params = self._validate(AdmitDeliveryChangeParams, request)
        return self._call(params, lambda: self._application.admit_delivery_change(params.request))

    async def list_work_items(self, request: EmptyRequest) -> list[object]:
        """List bounded work-item projections."""
        params = self._validate(EmptyParams, request)
        return self._call(params, self._application.list_work_items)

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

    async def acquire_frontier_work(self, request: EmptyRequest) -> dict[str, object]:
        """Acquire currently available frontier work."""
        params = self._validate(EmptyParams, request)
        return self._call(params, self._application.acquire_frontier_work)

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
            lambda: self._application.publish_delivery_plan(params.change_id, params.request),
            DeliveryPlanCandidate,
        )
        return DeliveryPlanPublication.from_candidate(candidate)

    async def publish_delivery_result(self, request: PublishDeliveryResultRequest) -> DeliveryResultPublication:
        """Publish one claim-scoped Delivery result."""
        params = self._validate(PublishDeliveryResultParams, request)
        candidate = self._call_model(
            params,
            lambda: self._application.publish_delivery_result(params.change_id, params.request),
            DeliveryResultCandidate,
        )
        return DeliveryResultPublication.from_candidate(candidate)

    async def finalize_change(self, request: FinalizeDeliveryChangeRequest) -> dict[str, object]:
        """Finalize one exact clean reviewed Change head with persisted evidence."""
        params = self._validate(FinalizeDeliveryChangeParams, request)
        return await asyncio.to_thread(
            self._call,
            params,
            lambda: self._application.finalize_change(params.change_id, params.request),
        )

    async def mark_change_ready(self, request: MarkChangeReadyRequest) -> dict[str, object]:
        """Mark one exact finalized and fully published Change pull request ready."""
        params = self._validate(MarkChangeReadyParams, request)
        return await asyncio.to_thread(
            self._call,
            params,
            lambda: self._application.mark_change_ready(params.request.change_id, params.request),
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

    async def transition_delivery(self, request: TransitionDeliveryRequest) -> dict[str, object]:
        """Apply one worker-owned Delivery transition."""
        params = self._validate(TransitionDeliveryParams, request)
        return self._call(params, lambda: self._application.transition_delivery(params.change_id, params.request))

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
            return model.model_validate_json(json.dumps(payload))
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
        except CompletedHistoryError as exc:
            authority = exc.diagnostic.change_id or exc.diagnostic.completion_id or self._authority(params)
            self._raise(
                exc.diagnostic.code.value,
                exc.diagnostic.detail,
                authority,
                retry_safe=isinstance(exc, CompletedHistoryStaleError),
            )
        except PublicationProviderError as exc:
            self._raise(
                exc.code.value,
                str(exc) or exc.code.value,
                self._authority(params),
                retry_safe=exc.retry_safe,
            )
        except _NAMED_DELIVERY_ERRORS as exc:
            self._raise(
                exc.code,
                str(exc) or exc.code,
                self._authority(params),
                retry_safe=getattr(exc, "retry_safe", isinstance(exc, _RETRY_SAFE_ERRORS)),
            )

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


_NAMED_DELIVERY_ERRORS = (
    CompletionReceiptConflictError,
    ChangeTargetSyncConflictError,
    ChangeWorktreeAttentionError,
    CoordinationConflictError,
    DeliveryRuntimeConflictError,
    DeliveryRuntimeReferenceError,
    DesignPackageConflictError,
    PortfolioApplicationError,
    TargetAdmissionError,
    TransactionConflictError,
    TransactionManifestError,
    TransactionPathError,
)
_RETRY_SAFE_ERRORS = (
    CoordinationConflictError,
    DeliveryRuntimeConflictError,
    DesignPackageConflictError,
    TransactionConflictError,
)


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
        server.tool(name=name, annotations=tool_annotations)(cast("Callable[..., object]", getattr(adapter, name)))


__all__ = [
    "DELIVERY_OPERATION_ANNOTATIONS",
    "DELIVERY_OPERATION_NAMES",
    "DeliveryAppContext",
    "TargetMCPAdapter",
    "assemble_target_server",
    "register_target_tools",
]
