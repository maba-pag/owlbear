"""Strict MCPServer adapter for the Delivery portfolio application."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Never, cast

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import BaseModel, ValidationError

from owlbear_delivery.change_workspace import CoordinationConflictError
from owlbear_delivery.completed_history import CompletedHistoryError, CompletedHistoryStaleError
from owlbear_delivery.delivery_runtime import (
    DeliveryPlanCandidate,
    DeliveryResultCandidate,
    DeliveryRuntimeConflictError,
    DeliveryRuntimeReferenceError,
)
from owlbear_delivery.design_package import DesignPackageConflictError
from owlbear_delivery.portfolio_application import PortfolioApplication, PortfolioApplicationError
from owlbear_delivery.runtime_transaction import (
    TransactionConflictError,
    TransactionManifestError,
    TransactionPathError,
)
from owlbear_delivery.target_admission import TargetAdmissionError
from owlbear_delivery_mcp.target_models import (
    AdmitDeliveryChangeParams,
    AdmitDeliveryChangeRequest,
    ChangeParams,
    ChangeRequest,
    ClaimContextParams,
    ClaimContextRequest,
    CompletedPageParams,
    CompletedPageRequest,
    CreateDesignSessionParams,
    CreateDesignSessionRequest,
    DeliveryPlanPublication,
    DeliveryResultPublication,
    EmptyParams,
    EmptyRequest,
    IntegrationRepairParams,
    IntegrationRepairRequest,
    PublishDeliveryPlanParams,
    PublishDeliveryPlanRequest,
    PublishDeliveryResultParams,
    PublishDeliveryResultRequest,
    RepairClaimContextParams,
    RepairClaimContextRequest,
    ReviseDesignSessionParams,
    ReviseDesignSessionRequest,
    SearchCompletedParams,
    SearchCompletedRequest,
    ShowCompletedParams,
    ShowCompletedRequest,
    TargetDiagnostic,
    TransitionDeliveryParams,
    TransitionDeliveryRequest,
    WorkItemParams,
    WorkItemRequest,
)

_READ = ToolAnnotations(read_only_hint=True, idempotent_hint=True, destructive_hint=False)
_WRITE = ToolAnnotations(read_only_hint=False, idempotent_hint=True, destructive_hint=False)
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
    "show_work_item",
    "acquire_frontier_work",
    "show_plan_context",
    "show_build_context",
    "show_integration_repair_context",
    "publish_delivery_plan",
    "publish_delivery_result",
    "transition_delivery",
    "recover_claim",
    "recover_integration_repair_claim",
    "list_integration_ready_changes",
    "show_integration_attention",
    "integrate_ready_change",
    "admit_reviewed_integration_repair",
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
        "show_work_item",
        "show_plan_context",
        "show_build_context",
        "show_integration_repair_context",
        "list_integration_ready_changes",
        "show_integration_attention",
        "list_completed_changes",
        "search_completed_changes",
        "show_completed_change",
    }
)
DELIVERY_OPERATION_ANNOTATIONS = {
    name: _READ if name in _DELIVERY_READS else _ACQUIRE if name == "acquire_frontier_work" else _WRITE
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

    async def show_integration_repair_context(self, request: RepairClaimContextRequest) -> dict[str, object]:
        """Show bounded Integration repair context for one claim."""
        params = self._validate(RepairClaimContextParams, request)
        return self._call(
            params,
            lambda: self._application.show_integration_repair_context(**params.model_dump()),
        )

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

    async def list_integration_ready_changes(self, request: EmptyRequest) -> list[object]:
        """List changes ready for Integration."""
        params = self._validate(EmptyParams, request)
        return self._call(params, self._application.list_integration_ready_changes)

    async def show_integration_attention(self, request: ChangeRequest) -> dict[str, object] | None:
        """Show current typed Integration attention."""
        params = self._validate(ChangeParams, request)
        return self._call(params, lambda: self._application.show_integration_attention(params.change_id))

    async def integrate_ready_change(self, request: ChangeRequest) -> dict[str, object]:
        """Integrate one ready Delivery change."""
        params = self._validate(ChangeParams, request)
        return self._call(params, lambda: self._application.integrate_ready_change(params.change_id))

    async def admit_reviewed_integration_repair(self, request: IntegrationRepairRequest) -> dict[str, object]:
        """Admit one independently reviewed Integration repair."""
        params = self._validate(IntegrationRepairParams, request)
        return self._call(
            params,
            lambda: self._application.admit_reviewed_integration_repair(
                params.attempt_id,
                params.claim_id,
                params.repair,
            ),
        )

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
        except _NAMED_DELIVERY_ERRORS as exc:
            self._raise(
                exc.code,
                str(exc) or exc.code,
                self._authority(params),
                retry_safe=isinstance(exc, _RETRY_SAFE_ERRORS),
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
