"""Bounded native work, evidence, invalidation, and health resources."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from owlbear_cockpit.deps import NativeChangeContext, NativeContextCache, get_engine, get_native_context_cache
from owlbear_cockpit.native_models import ChangeHealthPageResponse, InvalidationResponse, JobDetailResponse
from owlbear_cockpit.routes.native_changes import get_native_context
from owlbear_kanban import (
    AttemptEvent,
    ChangeHealthResult,
    Finding,
    FindingStore,
    JobStore,
    KanbanEngine,
    ReceiptRecord,
    ReceiptStore,
    RuntimeHistoryEntry,
    RuntimeJobProjection,
    RuntimePage,
    WorkHealthResult,
    change_health,
    project_job,
)
from owlbear_kanban.runtime_requests import NativeRequestRuntime, RequestNotFoundError, StoredRequest

if TYPE_CHECKING:
    from collections.abc import Callable

router = APIRouter(prefix="/changes/{change_id}", tags=["native-work"])
_Engine = Annotated[KanbanEngine, Depends(get_engine)]
_NativeCache = Annotated[NativeContextCache, Depends(get_native_context_cache)]
_Cursor = Annotated[str | None, Query()]
_Limit = Annotated[int, Query(ge=1, le=100)]


def _context(change_id: str, engine: KanbanEngine, cache: NativeContextCache) -> NativeChangeContext:
    return get_native_context(change_id, engine, cache)


def _work_root(engine: KanbanEngine) -> Path:
    return Path(engine.kanban_dir)


def _page[PageT](call: Callable[[], PageT]) -> PageT:
    try:
        return call()
    except ValueError as exc:
        if "cursor is not current" not in str(exc):
            raise
        raise HTTPException(
            status_code=409,
            detail={"code": "ERR_CURSOR_STALE", "message": "page cursor is not current"},
        ) from exc


def _change_health_page(
    result: ChangeHealthResult,
    cursor: str | None,
    limit: int,
) -> ChangeHealthPageResponse:
    paths = result.checked_paths
    start = 0
    if cursor is not None:
        try:
            start = paths.index(cursor) + 1
        except ValueError as exc:
            raise HTTPException(
                status_code=409,
                detail={"code": "ERR_CURSOR_STALE", "message": "page cursor is not current"},
            ) from exc
    stop = min(start + limit, len(paths))
    checked_paths = paths[start:stop]
    selected = set(checked_paths)
    findings = tuple(item for item in result.findings if item.path in selected or (item.path is None and start == 0))
    return ChangeHealthPageResponse(
        findings=findings,
        checked_paths=checked_paths,
        next_cursor=paths[stop - 1] if stop < len(paths) else None,
    )


def _not_found(code: str, message: str) -> HTTPException:
    return HTTPException(status_code=404, detail={"code": code, "message": message})


def _strings(value: object) -> tuple[str, ...]:
    if not isinstance(value, tuple | list):
        return ()
    return tuple(item for item in value if isinstance(item, str))


def _integers(value: object) -> tuple[int, ...]:
    if not isinstance(value, tuple | list):
        return ()
    return tuple(item for item in value if isinstance(item, int) and not isinstance(item, bool))


@router.get("/jobs", response_model=RuntimePage[RuntimeJobProjection])
def list_jobs(  # noqa: PLR0913, PLR0917 - FastAPI exposes each query and dependency explicitly.
    change_id: str,
    engine: _Engine,
    cache: _NativeCache,
    candidate_revision: str,
    cursor: _Cursor = None,
    limit: _Limit = 100,
) -> RuntimePage[RuntimeJobProjection]:
    """Return one bounded page of authority-composed native jobs."""
    runtime = _context(change_id, engine, cache).runtime
    return _page(lambda: runtime.list_jobs(candidate_revision=candidate_revision, cursor=cursor, limit=limit))


@router.get("/jobs/{job_id}", response_model=JobDetailResponse)
def show_job(change_id: str, job_id: int, engine: _Engine, cache: _NativeCache) -> JobDetailResponse:
    """Return one immutable job composed with current authority."""
    context = _context(change_id, engine, cache)
    store = JobStore(_work_root(engine))
    try:
        stored = store.read(job_id)
    except FileNotFoundError:
        try:
            stored = store.read(job_id, archived=True)
        except FileNotFoundError as exc:
            error = _not_found("ERR_JOB_NOT_FOUND", f"job {job_id} not found")
            raise error from exc
    projection = project_job(stored.job, context.revision)
    return JobDetailResponse(
        job=stored.job,
        title=projection.title,
        outcome=projection.outcome,
        acceptance=projection.acceptance,
        modules=projection.modules,
        interfaces=projection.interfaces,
        proof=projection.proof,
    )


@router.get("/attempts", response_model=RuntimePage[AttemptEvent])
def list_attempts(
    change_id: str,
    engine: _Engine,
    cache: _NativeCache,
    cursor: _Cursor = None,
    limit: _Limit = 100,
) -> RuntimePage[AttemptEvent]:
    """Return one bounded page of immutable attempt events."""
    runtime = _context(change_id, engine, cache).runtime
    return _page(lambda: runtime.list_attempts(cursor=cursor, limit=limit))


@router.get("/findings", response_model=RuntimePage[Finding])
def list_findings(
    change_id: str,
    engine: _Engine,
    cache: _NativeCache,
    cursor: _Cursor = None,
    limit: _Limit = 100,
) -> RuntimePage[Finding]:
    """Return one bounded page of corrective findings."""
    runtime = _context(change_id, engine, cache).runtime
    return _page(lambda: runtime.list_findings(cursor=cursor, limit=limit))


@router.get("/findings/{finding_id}", response_model=Finding)
def show_finding(change_id: str, finding_id: str, engine: _Engine, cache: _NativeCache) -> Finding:
    """Return one immutable corrective finding."""
    _context(change_id, engine, cache)
    result = FindingStore(_work_root(engine)).read(finding_id)
    if result.finding is not None:
        return result.finding
    diagnostic = result.diagnostics[0]
    if diagnostic.code.value == "ERR_FINDING_FILE_MISSING":
        error = _not_found("ERR_FINDING_MISSING", "finding not found")
        raise error
    raise HTTPException(status_code=422, detail={"code": diagnostic.code.value, "message": diagnostic.detail})


@router.get("/receipts", response_model=RuntimePage[ReceiptRecord])
def list_receipts(
    change_id: str,
    engine: _Engine,
    cache: _NativeCache,
    cursor: _Cursor = None,
    limit: _Limit = 100,
) -> RuntimePage[ReceiptRecord]:
    """Return one bounded page of immutable receipts."""
    runtime = _context(change_id, engine, cache).runtime
    return _page(lambda: runtime.list_receipts(cursor=cursor, limit=limit))


@router.get("/receipts/{receipt_id}", response_model=ReceiptRecord)
def show_receipt(change_id: str, receipt_id: str, engine: _Engine, cache: _NativeCache) -> ReceiptRecord:
    """Return one immutable native receipt."""
    context = _context(change_id, engine, cache)
    result = ReceiptStore(context.revision).read(receipt_id)
    if result.receipt is not None:
        return result.receipt
    diagnostic = result.diagnostics[0]
    if diagnostic.code.value == "ERR_RECEIPT_FILE_MISSING":
        error = _not_found("ERR_RECEIPT_MISSING", "receipt not found")
        raise error
    raise HTTPException(status_code=422, detail={"code": diagnostic.code.value, "message": diagnostic.detail})


@router.get("/requests", response_model=RuntimePage[StoredRequest])
def list_requests(
    change_id: str,
    engine: _Engine,
    cache: _NativeCache,
    cursor: _Cursor = None,
    limit: _Limit = 100,
) -> RuntimePage[StoredRequest]:
    """Return one bounded page of native requests."""
    runtime = _context(change_id, engine, cache).runtime
    return _page(lambda: runtime.list_requests(cursor=cursor, limit=limit))


@router.get("/requests/{request_id}", response_model=StoredRequest)
def show_request(change_id: str, request_id: str, engine: _Engine, cache: _NativeCache) -> StoredRequest:
    """Return one native request with its optional resolution."""
    context = _context(change_id, engine, cache)
    try:
        return NativeRequestRuntime(context.revision, _work_root(engine)).show_request(request_id)
    except RequestNotFoundError as exc:
        error = _not_found("ERR_NATIVE_REQUEST_NOT_FOUND", "request not found")
        raise error from exc


@router.get("/activity", response_model=RuntimePage[RuntimeHistoryEntry])
def list_activity(
    change_id: str,
    engine: _Engine,
    cache: _NativeCache,
    cursor: _Cursor = None,
    limit: _Limit = 100,
) -> RuntimePage[RuntimeHistoryEntry]:
    """Return one bounded chronological native history page."""
    runtime = _context(change_id, engine, cache).runtime
    return _page(lambda: runtime.list_history(cursor=cursor, limit=limit))


@router.get("/invalidations/{receipt_id}", response_model=InvalidationResponse)
def show_invalidation(
    change_id: str,
    receipt_id: str,
    engine: _Engine,
    cache: _NativeCache,
) -> InvalidationResponse:
    """Return one persisted supersession and its job closure."""
    context = _context(change_id, engine, cache)
    result = ReceiptStore(context.revision).read(receipt_id)
    receipt = result.receipt
    if receipt is None or receipt.kind != "supersession" or receipt.impact_closure is None:
        error = _not_found("ERR_INVALIDATION_NOT_FOUND", "invalidation not found")
        raise error
    return InvalidationResponse(
        invalidation_id=str(receipt.payload.get("invalidation_id", "")),
        supersession_receipt_id=receipt.receipt_id,
        issued_at=receipt.issued_at,
        impact_closure=receipt.impact_closure,
        affected_receipt_ids=_strings(receipt.payload.get("invalidated_receipt_ids")),
        corrective_finding_ids=_strings(receipt.payload.get("corrective_finding_ids")),
        corrective_job_ids=_integers(receipt.payload.get("corrective_job_ids")),
        receipt=receipt,
    )


@router.get("/health/work", response_model=WorkHealthResult)
def work_health(
    change_id: str,
    engine: _Engine,
    cache: _NativeCache,
    cursor: _Cursor = None,
    limit: _Limit = 100,
) -> WorkHealthResult:
    """Return one bounded non-mutating native work health page."""
    runtime = _context(change_id, engine, cache).runtime
    return _page(lambda: runtime.work_health(cursor=cursor, limit=limit))


@router.get("/health/change", response_model=ChangeHealthPageResponse)
def show_change_health(
    change_id: str,
    engine: _Engine,
    cache: _NativeCache,
    cursor: _Cursor = None,
    limit: _Limit = 100,
) -> ChangeHealthPageResponse:
    """Return canonical authority and receipt currentness health."""
    _context(change_id, engine, cache)
    result = change_health(_work_root(engine).parent / "changes", change_id)
    return _change_health_page(result, cursor, limit)


__all__ = ["router"]
