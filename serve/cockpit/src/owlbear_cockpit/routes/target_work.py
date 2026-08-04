"""Delivery work-item and operator HTTP adapter."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request
from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from owlbear_cockpit.deps import get_target_context
from owlbear_cockpit.target_models import (
    AnswerRequestBody,
    AttentionCounts,
    BackwardMoveBody,
    ClearBlockBody,
    ConfirmLostClaimBody,
    WorkItemDetailResponse,
    WorkItemLinks,
    WorkItemPortfolioResponse,
    WorkItemSummaryResponse,
)
from owlbear_kanban.change_workspace import CoordinationConflictError
from owlbear_kanban.completed_history import CompletedHistoryError, CompletedHistoryMissingError
from owlbear_kanban.delivery_runtime import (
    AdministrativeDeliveryMove,
    DeliveryRequestResolution,
    DeliveryRuntimeConflictError,
    DeliveryRuntimeReferenceError,
    DeliveryStage,
)
from owlbear_kanban.portfolio_application import PortfolioApplication, PortfolioApplicationError
from owlbear_kanban.work_items import WorkItemAttention, WorkItemProjection, WorkItemStage

if TYPE_CHECKING:
    from collections.abc import Callable


class TargetCockpitService:
    """Translate strict HTTP contracts to one Delivery application operation."""

    def __init__(self, application: PortfolioApplication) -> None:
        self._application = application

    def list_items(
        self,
        change_id: str | None,
        stage: WorkItemStage | None,
        attention: WorkItemAttention | None,
    ) -> WorkItemPortfolioResponse:
        """Return filtered current cards from one live portfolio projection."""
        items = self._invoke(self._application.list_work_items)
        filtered = tuple(
            item
            for item in items
            if (change_id is None or item.change_id == change_id)
            and (stage is None or item.stage == stage)
            and (attention is None or item.attention == attention)
        )
        return WorkItemPortfolioResponse(
            items=tuple(
                WorkItemSummaryResponse(card=item, links=_work_item_links(item.change_id, item.work_item_id))
                for item in filtered
            ),
            attention_counts=_attention_counts(filtered),
        )

    def show_item(self, change_id: str, outcome_id: str) -> WorkItemDetailResponse:
        """Return one exact bounded operator context and typed resources."""
        operator = self._invoke(lambda: self._application.show_operator_context(change_id, outcome_id))
        return WorkItemDetailResponse(operator=operator, links=_work_item_links(change_id, outcome_id))

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
        )
        return self._invoke(lambda: self._application.administrative_move(change_id, request))

    def show_integration_attention(self, change_id: str) -> object:
        """Return current typed Integration attention."""
        return self._invoke(lambda: self._application.show_integration_attention(change_id))

    def retry_integration(self, change_id: str) -> object:
        """Retry one Integration-ready or attention-bearing change."""
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


def _get_target_service(
    application: Annotated[PortfolioApplication, Depends(get_target_context)],
) -> TargetCockpitService:
    return TargetCockpitService(application)


_TargetService = Annotated[TargetCockpitService, Depends(_get_target_service)]


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
        change_id: str | None = None,
        stage: WorkItemStage | None = None,
        attention: WorkItemAttention | None = None,
    ) -> WorkItemPortfolioResponse:
        return service.list_items(change_id, stage, attention)

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

    @router.get("/changes/{change_id}/outcomes/{outcome_id}", response_model=WorkItemDetailResponse)
    def show_work_item(change_id: str, outcome_id: str, service: _TargetService) -> WorkItemDetailResponse:
        return service.show_item(change_id, outcome_id)


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

    @router.get("/changes/{change_id}/integration-attention")
    def show_integration_attention(change_id: str, service: _TargetService) -> object:
        return service.show_integration_attention(change_id)

    @router.post("/changes/{change_id}/integration/retry")
    def retry_integration(change_id: str, service: _TargetService) -> object:
        return service.retry_integration(change_id)


def _attention_counts(items: tuple[WorkItemProjection, ...]) -> AttentionCounts:
    values = [item.attention for item in items]
    return AttentionCounts(
        user=values.count(WorkItemAttention.USER),
        agent=values.count(WorkItemAttention.AGENT),
        waiting=values.count(WorkItemAttention.WAITING),
        none=values.count(WorkItemAttention.NONE),
    )


def _work_item_links(change_id: str, outcome_id: str) -> WorkItemLinks:
    base = f"/api/changes/{change_id}"
    outcome = f"{base}/outcomes/{outcome_id}"
    return WorkItemLinks(
        self=outcome,
        answer_request=f"{base}/requests/{{request_id}}/answer",
        clear_block=f"{outcome}/blocks/{{block_id}}/clear",
        recover_claim=f"{outcome}/claims/recover",
        move_backward=f"{outcome}/move-backward",
        integration_attention=f"{base}/integration-attention",
        integration_retry=f"{base}/integration/retry",
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
