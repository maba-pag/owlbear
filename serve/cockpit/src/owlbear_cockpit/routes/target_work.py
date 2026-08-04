"""Target work-item HTTP adapter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, FastAPI, HTTPException

from owlbear_cockpit.deps import get_target_context
from owlbear_cockpit.target_models import (
    AttentionCounts,
    CompletionSummaryResponse,
    CreateWorkItemRequestBody,
    RecoverWorkItemBody,
    ResolveWorkItemRequestBody,
    ResumeDesignResponse,
    SemanticUpdatesResponse,
    WorkItemDetailResponse,
    WorkItemPortfolioResponse,
    WorkItemRequestsResponse,
    WorkItemTraceLinks,
    WorkItemTraceResponse,
)
from owlbear_kanban.target_runtime import (
    RecoverInterruptedTaskRequest,
    TargetRecoveryError,
    TargetRequest,
    TargetRuntimeConflictError,
    TargetRuntimeReferenceError,
)
from owlbear_kanban.work_items import WorkItemAttention, WorkItemProjector, WorkItemStage

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_kanban.target_authority import TargetAuthority
    from owlbear_kanban.target_runtime import TargetRuntime
    from owlbear_kanban.work_items import WorkItemProjection


@dataclass(frozen=True)
class TargetCockpitBinding:
    """Bind one admitted target authority to its runtime."""

    authority: TargetAuthority
    runtime: TargetRuntime


@dataclass(frozen=True)
class TargetCockpitContext:
    """Supply target bindings and read-side technical projections."""

    changes: dict[str, TargetCockpitBinding]
    work_item_activity: Callable[[str, str], tuple[dict[str, object], ...]]
    work_item_trace: Callable[[str, str], tuple[dict[str, object], ...]]
    work_item_requests: Callable[[str, str], tuple[dict[str, object], ...]]
    process_is_alive: Callable[[str], bool]
    refresh: Callable[[], None] = lambda: None


class TargetCockpitService:
    """Compose target HTTP projections without duplicating runtime mutation rules."""

    def __init__(self, context: TargetCockpitContext) -> None:
        self._context = context

    def list_items(
        self,
        change_id: str | None,
        stage: WorkItemStage | None,
        attention: WorkItemAttention | None,
    ) -> WorkItemPortfolioResponse:
        """Return filtered mixed-change cards and counts for the filtered result."""
        self._context.refresh()
        bindings = (
            ((change_id, self._binding(change_id)),) if change_id else tuple(sorted(self._context.changes.items()))
        )
        items = tuple(
            sorted(
                (
                    item
                    for _identity, binding in bindings
                    for item in self._projector(binding).list_items()
                    if (stage is None or item.stage == stage) and (attention is None or item.attention == attention)
                ),
                key=lambda item: (item.change_id, item.work_item_id),
            )
        )
        return WorkItemPortfolioResponse(items=items, attention_counts=_attention_counts(items))

    def show_item(self, work_item_id: str, change_id: str | None) -> WorkItemDetailResponse:
        """Compose semantic detail while keeping operational IDs in trace resources."""
        resolved_change_id, binding, projector = self._resolve(work_item_id, change_id)
        detail = projector.show(work_item_id)
        evidence = binding.runtime.work_item_evidence()
        scope_ids = {scope.scope_id for scope in binding.authority.task_plan_scopes if scope.target_id == work_item_id}
        commitments = tuple(
            item for item in binding.authority.commitments if item.commitment_id in detail.projection.commitment_ids
        )
        return WorkItemDetailResponse(
            card=detail.projection,
            authority_identity=binding.runtime.authority_digest,
            commitments=commitments,
            acceptance=detail.acceptance,
            task_progress=tuple(item for item in evidence.task_progress if item.scope_id in scope_ids),
            correction_history=self._context.work_item_activity(resolved_change_id, work_item_id),
            semantic_updates=tuple(
                item for item in binding.authority.semantic_updates if item.work_item_id == work_item_id
            ),
            completion_summary=next(
                (item for item in binding.authority.completion_summaries if item.work_item_id == work_item_id),
                None,
            ),
            trace_links=_trace_links(resolved_change_id, work_item_id),
        )

    def resume_design(self, work_item_id: str, change_id: str | None) -> ResumeDesignResponse:
        """Return persisted briefing without changing the admitted semantic revision."""
        _resolved_change_id, _binding, projector = self._resolve(work_item_id, change_id)
        detail = projector.show(work_item_id)
        if detail.briefing is None or detail.projection.stage != WorkItemStage.DESIGN:
            _http_error(409, "ERR_TARGET_DESIGN_NOT_PENDING", "work item has no persisted design briefing")
        return ResumeDesignResponse(work_item_id=work_item_id, briefing=detail.briefing)

    def trace(self, work_item_id: str, change_id: str | None) -> WorkItemTraceResponse:
        """Return correction history and technical evidence on explicit request."""
        resolved_change_id, _binding, _projector = self._resolve(work_item_id, change_id)
        return WorkItemTraceResponse(
            activity=self._context.work_item_activity(resolved_change_id, work_item_id),
            evidence=self._context.work_item_trace(resolved_change_id, work_item_id),
        )

    def updates(self, work_item_id: str, change_id: str | None) -> SemanticUpdatesResponse:
        """Return non-blocking semantic revisions for one work item."""
        _resolved_change_id, _binding, projector = self._resolve(work_item_id, change_id)
        return SemanticUpdatesResponse(updates=projector.list_semantic_updates(work_item_id))

    def completion(self, work_item_id: str, change_id: str | None) -> CompletionSummaryResponse:
        """Return the commitment-level completion summary when present."""
        _resolved_change_id, _binding, projector = self._resolve(work_item_id, change_id)
        return CompletionSummaryResponse(completion_summary=projector.show_completion_summary(work_item_id))

    def requests(self, work_item_id: str, change_id: str | None) -> WorkItemRequestsResponse:
        """Return requests scoped to one semantic work item."""
        resolved_change_id, _binding, _projector = self._resolve(work_item_id, change_id)
        return WorkItemRequestsResponse(requests=self._context.work_item_requests(resolved_change_id, work_item_id))

    def create_request(
        self,
        work_item_id: str,
        body: CreateWorkItemRequestBody,
        change_id: str | None,
    ) -> dict[str, object]:
        """Create one request under the selected semantic work item."""
        resolved_change_id, binding, _projector = self._resolve(work_item_id, change_id)
        request = TargetRequest(
            **body.model_dump(),
            change_id=resolved_change_id,
            work_item_id=work_item_id,
        )
        return self._invoke(binding, lambda: binding.runtime.create_request(request))

    def resolve_request(
        self,
        work_item_id: str,
        request_id: str,
        body: ResolveWorkItemRequestBody,
        change_id: str | None,
    ) -> dict[str, object]:
        """Resolve one scoped request while retaining its target identity."""
        _resolved_change_id, binding, _projector = self._resolve(work_item_id, change_id)
        return self._invoke(binding, lambda: binding.runtime.resolve_request(request_id, body.resolved_at))

    def recover(
        self,
        work_item_id: str,
        body: RecoverWorkItemBody,
        change_id: str | None,
    ) -> dict[str, object]:
        """Delegate guarded interrupted-task recovery to the target runtime."""
        _resolved_change_id, binding, _projector = self._resolve(work_item_id, change_id)
        request = RecoverInterruptedTaskRequest(**body.model_dump())
        return self._invoke(
            binding,
            lambda: binding.runtime.recover_interrupted_task(
                request,
                process_is_alive=self._context.process_is_alive,
            ),
        )

    def _resolve(self, work_item_id: str, change_id: str | None) -> tuple[str, TargetCockpitBinding, WorkItemProjector]:
        self._context.refresh()
        identities = (change_id,) if change_id else tuple(sorted(self._context.changes))
        matches = []
        for identity in identities:
            binding = self._binding(identity)
            projector = self._projector(binding)
            if any(item.work_item_id == work_item_id for item in projector.list_items()):
                matches.append((identity, binding, projector))
        if len(matches) != 1:
            detail = "work item is missing" if not matches else "work item identity is ambiguous across changes"
            _http_error(404 if not matches else 409, "ERR_TARGET_WORK_ITEM_REFERENCE", detail)
        return matches[0]

    def _binding(self, change_id: str) -> TargetCockpitBinding:
        try:
            return self._context.changes[change_id]
        except KeyError:
            _http_error(404, "ERR_TARGET_CHANGE_NOT_LOADED", "change is not loaded")

    @staticmethod
    def _projector(binding: TargetCockpitBinding) -> WorkItemProjector:
        return WorkItemProjector(binding.authority, binding.runtime.work_item_evidence())

    @staticmethod
    def _invoke(binding: TargetCockpitBinding, operation: Callable[[], object]) -> dict[str, object]:
        try:
            result = operation()
        except (TargetRuntimeConflictError, TargetRuntimeReferenceError, TargetRecoveryError) as exc:
            _http_error(
                409,
                exc.code,
                str(exc),
                current_authority_identity=binding.runtime.authority_digest,
                retry_safe=isinstance(exc, TargetRuntimeConflictError),
            )
        return result.model_dump(mode="json")


def _get_target_service(
    context: Annotated[TargetCockpitContext, Depends(get_target_context)],
) -> TargetCockpitService:
    return TargetCockpitService(context)


_TargetService = Annotated[TargetCockpitService, Depends(_get_target_service)]


def assemble_target_app(context: TargetCockpitContext) -> FastAPI:
    """Assemble the target router with an explicit test context."""
    app = FastAPI(title="OwlBear Cockpit Target")
    app.dependency_overrides[get_target_context] = lambda: context
    app.include_router(router, prefix="/api")
    return app


def _target_router() -> APIRouter:
    router = APIRouter(prefix="/work-items", tags=["target-work-items"])
    _register_target_queries(router)
    _register_target_mutations(router)
    return router


def _register_target_queries(router: APIRouter) -> None:

    @router.get("", response_model=WorkItemPortfolioResponse)
    def list_work_items(
        service: _TargetService,
        change_id: str | None = None,
        stage: WorkItemStage | None = None,
        attention: WorkItemAttention | None = None,
    ) -> WorkItemPortfolioResponse:
        return service.list_items(change_id, stage, attention)

    @router.get("/{work_item_id}", response_model=WorkItemDetailResponse)
    def show_work_item(
        work_item_id: str,
        service: _TargetService,
        change_id: str | None = None,
    ) -> WorkItemDetailResponse:
        return service.show_item(work_item_id, change_id)

    @router.get("/{work_item_id}/resume-design", response_model=ResumeDesignResponse)
    def resume_design(
        work_item_id: str,
        service: _TargetService,
        change_id: str | None = None,
    ) -> ResumeDesignResponse:
        return service.resume_design(work_item_id, change_id)

    @router.get("/{work_item_id}/trace", response_model=WorkItemTraceResponse)
    def show_trace(
        work_item_id: str,
        service: _TargetService,
        change_id: str | None = None,
    ) -> WorkItemTraceResponse:
        return service.trace(work_item_id, change_id)

    @router.get("/{work_item_id}/updates", response_model=SemanticUpdatesResponse)
    def list_updates(
        work_item_id: str,
        service: _TargetService,
        change_id: str | None = None,
    ) -> SemanticUpdatesResponse:
        return service.updates(work_item_id, change_id)

    @router.get("/{work_item_id}/completion", response_model=CompletionSummaryResponse)
    def show_completion(
        work_item_id: str,
        service: _TargetService,
        change_id: str | None = None,
    ) -> CompletionSummaryResponse:
        return service.completion(work_item_id, change_id)

    @router.get("/{work_item_id}/requests", response_model=WorkItemRequestsResponse)
    def list_requests(
        work_item_id: str,
        service: _TargetService,
        change_id: str | None = None,
    ) -> WorkItemRequestsResponse:
        return service.requests(work_item_id, change_id)


def _register_target_mutations(router: APIRouter) -> None:
    @router.post("/{work_item_id}/requests")
    def create_request(
        work_item_id: str,
        body: CreateWorkItemRequestBody,
        service: _TargetService,
        change_id: str | None = None,
    ) -> dict[str, object]:
        return service.create_request(work_item_id, body, change_id)

    @router.post("/{work_item_id}/requests/{request_id}/resolve")
    def resolve_request(
        work_item_id: str,
        request_id: str,
        body: ResolveWorkItemRequestBody,
        service: _TargetService,
        change_id: str | None = None,
    ) -> dict[str, object]:
        return service.resolve_request(work_item_id, request_id, body, change_id)

    @router.post("/{work_item_id}/recover")
    def recover_task(
        work_item_id: str,
        body: RecoverWorkItemBody,
        service: _TargetService,
        change_id: str | None = None,
    ) -> dict[str, object]:
        return service.recover(work_item_id, body, change_id)


def _attention_counts(items: tuple[WorkItemProjection, ...]) -> AttentionCounts:
    values = [item.attention for item in items]
    return AttentionCounts(
        user=values.count(WorkItemAttention.USER),
        agent=values.count(WorkItemAttention.AGENT),
        waiting=values.count(WorkItemAttention.WAITING),
        none=values.count(WorkItemAttention.NONE),
    )


def _trace_links(change_id: str, work_item_id: str) -> WorkItemTraceLinks:
    query = urlencode({"change_id": change_id})
    base = f"/api/work-items/{work_item_id}"
    return WorkItemTraceLinks(
        activity=f"{base}/trace?{query}",
        evidence=f"{base}/trace?{query}",
        requests=f"{base}/requests?{query}",
    )


def _http_error(
    status_code: int,
    code: str,
    detail: str,
    *,
    current_authority_identity: str | None = None,
    retry_safe: bool | None = None,
) -> None:
    payload: dict[str, object] = {"code": code, "detail": detail}
    if current_authority_identity is not None:
        payload["current_authority_identity"] = current_authority_identity
    if retry_safe is not None:
        payload["retry_safe"] = retry_safe
    raise HTTPException(status_code=status_code, detail=payload)


router = _target_router()


__all__ = ["TargetCockpitBinding", "TargetCockpitContext", "assemble_target_app", "router"]
