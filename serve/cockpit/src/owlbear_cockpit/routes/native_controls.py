"""Intent-specific native request resolution and claim release controls."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends

from owlbear_cockpit.deps import NativeContextCache, get_engine, get_native_context_cache
from owlbear_cockpit.native_http import conflict
from owlbear_cockpit.native_models import (
    CancelJobBody,
    JobAdminConflictEnvelope,
    ReleaseJobBody,
    ResolveRequestBody,
    SetJobPriorityBody,
)
from owlbear_cockpit.routes.native_changes import get_native_context
from owlbear_kanban import (
    CancelJobRequest,
    CancelJobResult,
    DispatchDiagnostic,
    JobAdminDiagnostic,
    JobAdminDiagnosticCode,
    JobStore,
    KanbanEngine,
    ReleaseJobRequest,
    ReleaseJobResult,
    SetJobPriorityRequest,
    SetJobPriorityResult,
)
from owlbear_kanban.runtime_requests import (
    RequestConflictError,
    RequestNotFoundError,
    RequestReferenceError,
    RequestResolution,
    ResolveRequestResult,
)
from owlbear_kanban.runtime_transaction import TransactionConflictError

router = APIRouter(prefix="/changes/{change_id}", tags=["native-controls"])
_Engine = Annotated[KanbanEngine, Depends(get_engine)]
_NativeCache = Annotated[NativeContextCache, Depends(get_native_context_cache)]


def _work_root(engine: KanbanEngine) -> Path:
    return Path(engine.kanban_dir)


def _attach_current_job(error, engine: KanbanEngine, job_id: int) -> None:  # noqa: ANN001 - FastAPI HTTPException
    current = _current_job(engine, job_id)
    if current is not None:
        error.detail["current"] = current.model_dump(mode="json")


@router.post("/requests/{request_id}/resolve", response_model=ResolveRequestResult)
def resolve_request(
    change_id: str,
    request_id: str,
    body: ResolveRequestBody,
    engine: _Engine,
    cache: _NativeCache,
) -> ResolveRequestResult:
    """Resolve one pending native request through its immutable identity."""
    context = get_native_context(change_id, engine, cache)
    if body.delivery_digest != context.revision.delivery_digest:
        error = conflict(
            code="ERR_CHANGE_REVISION_CONFLICT",
            detail="request revision is not current",
            current_delivery_digest=context.revision.delivery_digest,
            target=request_id,
        )
        raise error
    resolution = RequestResolution(
        request_id=request_id,
        **body.model_dump(exclude={"delivery_digest"}),
    )
    runtime = context.runtime
    try:
        return runtime.resolve_request(resolution)
    except RequestNotFoundError as exc:
        error = conflict(
            code=exc.code,
            detail="request not found",
            current_delivery_digest=context.revision.delivery_digest,
            target=request_id,
        )
        raise error from exc
    except RequestReferenceError as exc:
        error = conflict(
            code=exc.code,
            detail="request resolution references stale authority",
            current_delivery_digest=context.revision.delivery_digest,
            target=request_id,
        )
        raise error from exc
    except RequestConflictError as exc:
        current = runtime.show_request(request_id)
        error = conflict(
            code=exc.code,
            detail="request resolution identity conflicts with persisted authority",
            current_delivery_digest=context.revision.delivery_digest,
            target=request_id,
        )
        error.detail["current"] = current.model_dump(mode="json")
        raise error from exc


@router.post(
    "/jobs/{job_id}/release",
    response_model=ReleaseJobResult,
    responses={409: {"model": JobAdminConflictEnvelope}},
)
def release_job(
    change_id: str,
    job_id: int,
    body: ReleaseJobBody,
    engine: _Engine,
    cache: _NativeCache,
) -> ReleaseJobResult:
    """Release one claim only when its complete immutable identity matches."""
    context = get_native_context(change_id, engine, cache)
    if body.delivery_digest != context.revision.delivery_digest:
        error = conflict(
            code="ERR_CHANGE_REVISION_CONFLICT",
            detail="release revision is not current",
            current_delivery_digest=context.revision.delivery_digest,
            target=str(job_id),
        )
        _attach_current_job(error, engine, job_id)
        raise error
    request = ReleaseJobRequest(job_id=job_id, **body.model_dump(exclude={"delivery_digest"}))
    try:
        result = context.dispatch.release(request)
    except TransactionConflictError as exc:
        error = conflict(
            code="ERR_CONTROL_TRANSACTION_CONFLICT",
            detail="release transaction did not commit",
            current_delivery_digest=context.revision.delivery_digest,
            lower_code=exc.code,
            target=str(job_id),
        )
        _attach_current_job(error, engine, job_id)
        raise error from exc
    except OSError as exc:
        error = conflict(
            code="ERR_CONTROL_STORAGE_FAILURE",
            detail="release storage could not be read or committed",
            current_delivery_digest=context.revision.delivery_digest,
            lower_code="ERR_STORAGE_IO",
            target=str(job_id),
        )
        _attach_current_job(error, engine, job_id)
        raise error from exc
    if isinstance(result, DispatchDiagnostic):
        error = conflict(
            code=result.code.value,
            detail=result.detail,
            current_delivery_digest=context.revision.delivery_digest,
            diagnostic=result,
            target=str(job_id),
        )
        _attach_current_job(error, engine, job_id)
        raise error
    if result.diagnostic is not None:
        error = conflict(
            code=result.diagnostic.code.value,
            detail=result.diagnostic.detail,
            current_delivery_digest=context.revision.delivery_digest,
            diagnostic=result.diagnostic,
            target=str(job_id),
        )
        _attach_current_job(error, engine, job_id)
        raise error
    return result


def _admin_conflict(diagnostic: JobAdminDiagnostic, delivery_digest: str) -> None:
    error = conflict(
        code=diagnostic.code.value,
        detail=diagnostic.detail,
        current_delivery_digest=delivery_digest,
        diagnostic=diagnostic,
        lower_code=diagnostic.lower_code,
        target=diagnostic.target,
    )
    raise error


def _current_job(engine: KanbanEngine, job_id: int):  # noqa: ANN202 - inferred StoredJob | None
    store = JobStore(_work_root(engine))
    try:
        return store.read(job_id)
    except FileNotFoundError:
        try:
            return store.read(job_id, archived=True)
        except FileNotFoundError:
            return None


def _require_current_digest(
    body_digest: str,
    current_digest: str,
    engine: KanbanEngine,
    job_id: int,
) -> None:
    if body_digest == current_digest:
        return
    diagnostic = JobAdminDiagnostic(
        code=JobAdminDiagnosticCode.AUTHORITY_STALE,
        detail="administrative request delivery digest is not current",
        target=str(job_id),
        current=_current_job(engine, job_id),
    )
    _admin_conflict(diagnostic, current_digest)


def _require_job_identity(path_job_id: int, body_job_id: int, delivery_digest: str) -> None:
    if path_job_id == body_job_id:
        return
    error = conflict(
        code="ERR_JOB_ID_CONFLICT",
        detail="job path and payload identities differ",
        current_delivery_digest=delivery_digest,
        target=str(path_job_id),
    )
    raise error


@router.post(
    "/jobs/{job_id}/priority",
    response_model=SetJobPriorityResult,
    responses={409: {"model": JobAdminConflictEnvelope}},
)
def set_job_priority(
    change_id: str,
    job_id: int,
    body: SetJobPriorityBody,
    engine: _Engine,
    cache: _NativeCache,
) -> SetJobPriorityResult:
    """Update one pending unclaimed job through complete OCC identity."""
    context = get_native_context(change_id, engine, cache)
    _require_job_identity(job_id, body.job_id, context.revision.delivery_digest)
    _require_current_digest(body.delivery_digest, context.revision.delivery_digest, engine, job_id)
    request = SetJobPriorityRequest(change_id=change_id, **body.model_dump())
    result = context.runtime.set_job_priority(request)
    if result.diagnostic is not None:
        _admin_conflict(result.diagnostic, context.revision.delivery_digest)
    return result


@router.post(
    "/jobs/{job_id}/cancel",
    response_model=CancelJobResult,
    responses={409: {"model": JobAdminConflictEnvelope}},
)
def cancel_job(
    change_id: str,
    job_id: int,
    body: CancelJobBody,
    engine: _Engine,
    cache: _NativeCache,
) -> CancelJobResult:
    """Cancel one pending unclaimed job through complete OCC identity."""
    context = get_native_context(change_id, engine, cache)
    _require_job_identity(job_id, body.job_id, context.revision.delivery_digest)
    _require_current_digest(body.delivery_digest, context.revision.delivery_digest, engine, job_id)
    request = CancelJobRequest(change_id=change_id, **body.model_dump())
    result = context.runtime.cancel_job(request)
    if result.diagnostic is not None:
        _admin_conflict(result.diagnostic, context.revision.delivery_digest)
    return result


__all__ = ["router"]
