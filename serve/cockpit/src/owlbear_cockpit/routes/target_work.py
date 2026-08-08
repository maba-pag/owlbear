"""Delivery work-item and operator HTTP adapter."""

from __future__ import annotations

import logging
import threading
import uuid
from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from owlbear_cockpit.deps import get_target_context
from owlbear_cockpit.target_models import (
    ActivityCounts,
    AnswerRequestBody,
    BackwardMoveBody,
    BackwardMovePreviewBody,
    ClearBlockBody,
    ConfirmLostClaimBody,
    DesignWorkDetailResponse,
    NeedsCounts,
    WorkItemDetailResponse,
    WorkItemPortfolioResponse,
    WorkItemPortfolioTotals,
)
from owlbear_delivery.change_workspace import CoordinationConflictError
from owlbear_delivery.completed_history import CompletedHistoryError, CompletedHistoryMissingError
from owlbear_delivery.delivery_runtime import (
    AdministrativeDeliveryMove,
    DeliveryIntegrationAttentionDisposition,
    DeliveryRequestResolution,
    DeliveryRuntimeConflictError,
    DeliveryRuntimeReferenceError,
    DeliveryStage,
    integration_attention_disposition,
)
from owlbear_delivery.design_package import DesignPackageConflictError
from owlbear_delivery.portfolio_application import PortfolioApplication, PortfolioApplicationError
from owlbear_delivery.work_items import (
    ChangeGroupView,
    WorkItemActivityState,
    WorkItemNeed,
    WorkItemScope,
    WorkItemStage,
)

if TYPE_CHECKING:
    from collections.abc import Callable

_LOGGER = logging.getLogger(__name__)
_REGISTRY_INITIALIZATION_LOCK = threading.Lock()


class _IntegrationAttemptRegistry:
    """App-scoped single-flight ownership for long Integration attempts."""

    def __init__(self) -> None:
        self._active: set[str] = set()
        self._lock = threading.Lock()

    def begin(self, change_id: str) -> bool:
        with self._lock:
            if change_id in self._active:
                return False
            self._active.add(change_id)
            return True

    def finish(self, change_id: str) -> None:
        with self._lock:
            self._active.discard(change_id)


def _integration_attempts(request: Request) -> _IntegrationAttemptRegistry:
    registry = getattr(request.app.state, "delivery_integration_attempts", None)
    if registry is not None:
        return registry
    with _REGISTRY_INITIALIZATION_LOCK:
        registry = getattr(request.app.state, "delivery_integration_attempts", None)
        if registry is None:
            registry = _IntegrationAttemptRegistry()
            request.app.state.delivery_integration_attempts = registry
    return registry


class TargetCockpitService:
    """Translate strict HTTP contracts to one Delivery application operation."""

    def __init__(self, application: PortfolioApplication) -> None:
        self._application = application

    def list_items(
        self,
    ) -> WorkItemPortfolioResponse:
        """Return Change-grouped current Work Items from exact snapshots."""
        view = self._invoke(self._application.portfolio_read_view)
        return WorkItemPortfolioResponse(
            groups=view.groups,
            totals=_portfolio_totals(view.groups),
            operating=view.operating,
        )

    def show_item(self, change_id: str, item_key: str) -> WorkItemDetailResponse:
        """Return semantic and operator detail from one exact snapshot."""
        item = self._invoke(lambda: self._application.show_work_item_view(change_id, item_key))
        return WorkItemDetailResponse(item=item)

    def show_design_work(self, change_id: str) -> DesignWorkDetailResponse:
        """Return verified authored sources for one pre-admission Design package."""
        package = self._invoke(lambda: self._application.read_design_session(change_id))
        return DesignWorkDetailResponse(
            change_id=package.change_id,
            package_id=package.package_id,
            intent_markdown=package.intent_bytes.decode(),
            design_markdown=package.design_bytes.decode(),
        )

    def answer_request(self, change_id: str, request_id: str, body: AnswerRequestBody) -> object:
        """Answer one exact pending Delivery request."""
        resolution = DeliveryRequestResolution(**body.model_dump())
        return self._invoke(lambda: self._application.resolve_request(change_id, request_id, resolution))

    def clear_block(
        self,
        change_id: str,
        outcome_id: str,
        block_id: str,
        body: ClearBlockBody,
    ) -> object:
        """Clear one exact requestless block with operator evidence."""
        return self._invoke(
            lambda: self._application.clear_block(
                change_id,
                outcome_id,
                block_id,
                body.operator_note,
                tuple(body.locators),
            )
        )

    def recover_claim(
        self,
        change_id: str,
        outcome_id: str,
        body: ConfirmLostClaimBody,
    ) -> object:
        """Recover one exact claim only after explicit lost confirmation."""
        return self._invoke(
            lambda: self._application.recover_claim(
                change_id,
                outcome_id,
                body.attempt_id,
                body.claim_id,
            )
        )

    def move_backward(self, change_id: str, outcome_id: str, body: BackwardMoveBody) -> object:
        """Apply one server-identified administrative backward move."""
        request = AdministrativeDeliveryMove(
            move_id=str(uuid.uuid4()),
            outcome_id=outcome_id,
            target=DeliveryStage(body.target),
            reason=body.reason,
            expected_version=body.snapshot_version,
        )
        return self._invoke(lambda: self._application.administrative_move(change_id, request))

    def preview_backward_move(
        self,
        change_id: str,
        outcome_id: str,
        body: BackwardMovePreviewBody,
    ) -> object:
        """Preview the exact invalidation closure without mutation."""
        return self._invoke(
            lambda: self._application.preview_administrative_move(
                change_id,
                outcome_id,
                DeliveryStage(body.target),
            )
        )

    def show_integration_attention(self, change_id: str) -> object:
        """Return current typed Integration attention."""
        return self._invoke(lambda: self._application.show_integration_attention(change_id))

    def authorize_integration_retry(self, change_id: str) -> None:
        """Reject Integration attempts that require a different operator route."""
        attention = self._invoke(lambda: self._application.show_integration_attention(change_id))
        detail = self._invoke(lambda: self._application.show_work_item_view(change_id, "integration"))
        if detail.integration is not None and detail.integration.repair_active:
            _http_error(
                409,
                "ERR_DELIVERY_INTEGRATION_ACTION_REQUIRED",
                "A reviewed Integration repair is already in progress.",
                retry_safe=False,
            )
        superseded = detail.integration is not None and detail.integration.superseded
        if (
            attention is not None
            and not superseded
            and integration_attention_disposition(attention.code) != DeliveryIntegrationAttentionDisposition.RETRYABLE
        ):
            _http_error(
                409,
                "ERR_DELIVERY_INTEGRATION_ACTION_REQUIRED",
                attention.retry_condition,
                retry_safe=False,
            )

    def run_integration(self, change_id: str) -> object:
        """Run one authorized Integration attempt."""
        return self._invoke(lambda: self._application.integrate_ready_change(change_id))

    def list_completed(self, cursor: str | None, limit: int) -> object:
        """List one bounded page of completed change history."""
        return self._invoke(lambda: self._application.list_completed_changes(cursor, limit))

    def search_completed(self, query: str, cursor: str | None, limit: int) -> object:
        """Search completed semantic history."""
        return self._invoke(lambda: self._application.search_completed_changes(query, cursor, limit))

    def show_completed(self, change_id: str, completion_id: str | None) -> object:
        """Return one exact completed change record."""
        return self._invoke(lambda: self._application.show_completed_change(change_id, completion_id))

    @staticmethod
    def _invoke(operation: Callable[[], object]):  # noqa: ANN205
        try:
            return operation()
        except CompletedHistoryError as exc:
            _http_error(
                404 if isinstance(exc, CompletedHistoryMissingError) else 409,
                exc.diagnostic.code,
                exc.diagnostic.detail,
                retry_safe=False,
            )
        except (DeliveryRuntimeConflictError, CoordinationConflictError) as exc:
            _http_error(409, getattr(exc, "code", "ERR_DELIVERY_CONFLICT"), str(exc), retry_safe=True)
        except (DeliveryRuntimeReferenceError, PortfolioApplicationError) as exc:
            _http_error(409, exc.code, str(exc), retry_safe=False)
        except DesignPackageConflictError as exc:
            _http_error(409, exc.code, str(exc), retry_safe=False)


def _get_target_service(
    application: Annotated[PortfolioApplication, Depends(get_target_context)],
) -> TargetCockpitService:
    return TargetCockpitService(application)


_TargetService = Annotated[TargetCockpitService, Depends(_get_target_service)]


def _run_integration_attempt(
    service: TargetCockpitService,
    registry: _IntegrationAttemptRegistry,
    change_id: str,
) -> None:
    try:
        service.run_integration(change_id)
    except Exception:
        _LOGGER.exception("Cockpit Integration attempt failed for %s", change_id)
    finally:
        registry.finish(change_id)


def assemble_target_app(application: PortfolioApplication) -> FastAPI:
    """Assemble the Delivery router with an explicit test application."""
    app = FastAPI(title="OwlBear Cockpit Delivery")
    app.add_exception_handler(HTTPException, handle_target_http_error)
    app.add_exception_handler(RequestValidationError, handle_target_validation_error)
    app.dependency_overrides[get_target_context] = lambda: application
    app.include_router(router, prefix="/api")
    return app


def _target_router() -> APIRouter:
    router = APIRouter(tags=["delivery-work-items"])
    _register_queries(router)
    _register_controls(router)
    return router


def _register_queries(router: APIRouter) -> None:

    @router.get("/work-items", response_model=WorkItemPortfolioResponse)
    def list_work_items(
        service: _TargetService,
    ) -> WorkItemPortfolioResponse:
        return service.list_items()

    @router.get("/work-items/completed")
    def list_completed_changes(
        service: _TargetService,
        cursor: str | None = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 100,
    ) -> object:
        return service.list_completed(cursor, limit)

    @router.get("/work-items/completed/search")
    def search_completed_changes(
        service: _TargetService,
        query: Annotated[str, Query(min_length=1)],
        cursor: str | None = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 100,
    ) -> object:
        return service.search_completed(query, cursor, limit)

    @router.get("/work-items/completed/{change_id}")
    def show_completed_change(
        change_id: str,
        service: _TargetService,
        completion_id: str | None = None,
    ) -> object:
        return service.show_completed(change_id, completion_id)

    @router.get("/design-work/{change_id}", response_model=DesignWorkDetailResponse)
    def show_design_work(change_id: str, service: _TargetService) -> DesignWorkDetailResponse:
        return service.show_design_work(change_id)

    @router.get("/changes/{change_id}/work-items/{item_key}", response_model=WorkItemDetailResponse)
    def show_work_item(change_id: str, item_key: str, service: _TargetService) -> WorkItemDetailResponse:
        return service.show_item(change_id, item_key)


def _register_controls(router: APIRouter) -> None:
    @router.post("/changes/{change_id}/requests/{request_id}/answer")
    def answer_request(
        change_id: str,
        request_id: str,
        body: AnswerRequestBody,
        service: _TargetService,
    ) -> object:
        return service.answer_request(change_id, request_id, body)

    @router.post("/changes/{change_id}/outcomes/{outcome_id}/blocks/{block_id}/clear")
    def clear_block(
        change_id: str,
        outcome_id: str,
        block_id: str,
        body: ClearBlockBody,
        service: _TargetService,
    ) -> object:
        return service.clear_block(change_id, outcome_id, block_id, body)

    @router.post("/changes/{change_id}/outcomes/{outcome_id}/claims/recover")
    def recover_claim(
        change_id: str,
        outcome_id: str,
        body: ConfirmLostClaimBody,
        service: _TargetService,
    ) -> object:
        return service.recover_claim(change_id, outcome_id, body)

    @router.post("/changes/{change_id}/outcomes/{outcome_id}/move-backward")
    def move_backward(
        change_id: str,
        outcome_id: str,
        body: BackwardMoveBody,
        service: _TargetService,
    ) -> object:
        return service.move_backward(change_id, outcome_id, body)

    @router.post("/changes/{change_id}/outcomes/{outcome_id}/move-backward/preview")
    def preview_backward_move(
        change_id: str,
        outcome_id: str,
        body: BackwardMovePreviewBody,
        service: _TargetService,
    ) -> object:
        return service.preview_backward_move(change_id, outcome_id, body)

    @router.get("/changes/{change_id}/integration-attention")
    def show_integration_attention(change_id: str, service: _TargetService) -> object:
        return service.show_integration_attention(change_id)

    @router.post("/changes/{change_id}/integration/retry", status_code=status.HTTP_202_ACCEPTED)
    def retry_integration(
        change_id: str,
        request: Request,
        background_tasks: BackgroundTasks,
        service: _TargetService,
    ) -> dict[str, str]:
        service.authorize_integration_retry(change_id)
        registry = _integration_attempts(request)
        if not registry.begin(change_id):
            return {"status": "running"}
        background_tasks.add_task(_run_integration_attempt, service, registry, change_id)
        return {"status": "started"}


def _portfolio_totals(groups: tuple[ChangeGroupView, ...]) -> WorkItemPortfolioTotals:
    items = tuple(item for group in groups for item in group.items)
    needs = [item.needs for item in items]
    activity = [item.activity.state for item in items]
    return WorkItemPortfolioTotals(
        total=len(items),
        complete=sum(item.scope == WorkItemScope.OUTCOME and item.stage == WorkItemStage.COMPLETED for item in items),
        needs=NeedsCounts(
            you=needs.count(WorkItemNeed.YOU),
            dependency=needs.count(WorkItemNeed.DEPENDENCY),
            repair=needs.count(WorkItemNeed.REPAIR),
            none=needs.count(WorkItemNeed.NONE),
        ),
        activity=ActivityCounts(
            idle=activity.count(WorkItemActivityState.IDLE),
            ready=activity.count(WorkItemActivityState.READY),
            working=activity.count(WorkItemActivityState.WORKING),
            repairing=activity.count(WorkItemActivityState.REPAIRING),
        ),
    )


def _http_error(status_code: int, code: object, detail: str, *, retry_safe: bool) -> None:
    raise HTTPException(
        status_code=status_code,
        detail={
            "code": str(code),
            "detail": detail,
            "authority": "delivery",
            "retry_safe": retry_safe,
        },
    )


async def handle_target_http_error(request: Request, exc: Exception) -> JSONResponse:
    """Expose typed Delivery diagnostics while retaining FastAPI defaults elsewhere."""
    if isinstance(exc, HTTPException) and isinstance(exc.detail, dict) and exc.detail.get("authority") == "delivery":
        return JSONResponse(status_code=exc.status_code, content=exc.detail, headers=exc.headers)
    return await http_exception_handler(request, exc)  # type: ignore[arg-type]


async def handle_target_validation_error(request: Request, exc: Exception) -> JSONResponse:
    """Reject malformed Delivery input with one stable non-retryable diagnostic."""
    if isinstance(exc, RequestValidationError) and request.url.path.startswith(("/api/work-items", "/api/changes")):
        return JSONResponse(
            status_code=422,
            content={
                "code": "ERR_DELIVERY_HTTP_VALIDATION",
                "detail": "Delivery request input is malformed",
                "authority": "delivery",
                "retry_safe": False,
            },
        )
    return await request_validation_exception_handler(request, exc)  # type: ignore[arg-type]


router = _target_router()


__all__ = ["assemble_target_app", "handle_target_http_error", "handle_target_validation_error", "router"]
