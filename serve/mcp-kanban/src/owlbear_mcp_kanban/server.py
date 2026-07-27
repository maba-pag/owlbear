"""OwlBear MCP server for the native delivery control plane."""

from __future__ import annotations

import asyncio
import json
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Literal
from uuid import UUID

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import BeforeValidator
from pydantic import ValidationError as PydanticValidationError

from owlbear_kanban import (
    AdmissionEvidence,
    AdmissionTransaction,
    ChangeDiagnosticCode,
    ChangeRevision,
    DispatchRuntime,
    Finding,
    FinishAcceptRequest,
    FinishJobRequest,
    FinishPlanRequest,
    GitRepositoryHistory,
    InvalidationRequest,
    NativeRuntime,
    NativeWorkspace,
    ProofCheckoutManager,
    RecoverExpiredClaimsRequest,
    RejectAcceptRequest,
    RejectAuditRequest,
    ReleaseJobRequest,
    StartJobRequest,
    evaluate_admission,
    load_change,
    parse_claim_expiry,
    parse_impact_closure,
    project_job,
)
from owlbear_kanban import (
    change_health as get_change_health,
)
from owlbear_kanban.admission_transaction import (
    AdmissionConflictError,
    AdmissionPublicationError,
    AdmissionValidationError,
)
from owlbear_kanban.runtime_requests import (
    NativeRequest,
    NativeRequestRuntime,
    RequestConflictError,
    RequestNotFoundError,
    RequestOption,
    RequestReferenceError,
    RequestStatus,
)
from owlbear_mcp_kanban.models import (
    FinishAcceptParams,
    FinishJobParams,
    FinishPlanParams,
    InvalidationParams,
    ListActivityParams,
    ListAttemptsParams,
    ListFindingsParams,
    ListJobsParams,
    PickJobsParams,
    RecoverExpiredClaimsParams,
    RejectAcceptParams,
    RejectAuditParams,
    ReleaseJobParams,
    ShowFindingParams,
    ShowJobParams,
    ShowReceiptParams,
    StartJobParams,
    WorkHealthParams,
)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


def _coerce_to_str(v: str | int) -> str:
    """Accept int values for str parameters (Pydantic v2 refuses int→str).

    MCP clients may send JSON numbers for parameters that were recently
    widened from int to str, because VS Code caches tool schemas per chat
    session and only refreshes on a fresh session start.
    """
    return str(v) if isinstance(v, int) else v


StrId = Annotated[str, BeforeValidator(_coerce_to_str)]

__all__ = [
    "AppContext",
    "StrId",
    "_apply_tool_exclusions",
    "admit_change",
    "app_lifespan",
    "change_health",
    "create_request",
    "finish_accept",
    "finish_audit",
    "finish_build",
    "finish_plan",
    "list_activity",
    "list_attempts",
    "list_changes",
    "list_findings",
    "list_jobs",
    "list_requests",
    "mcp",
    "pick_jobs",
    "recover_expired_claims",
    "reject_accept",
    "reject_audit",
    "release_job",
    "show_change",
    "show_finding",
    "show_job",
    "show_receipt",
    "show_request",
    "start_job",
    "validate_change",
    "work_health",
]

_DEFAULT_WORK_ROOT = Path(".owlbear/kanban")
_DEFAULT_CLAIM_EXPIRY = "1h"
_UUID4_VERSION = 4
_NORM_GUIDANCE = (
    "Literal \\n sequences were normalized to actual newlines. "
    "To keep a literal \\n in files, send \\\\n in JSON input."
)


def _resolve_work_root() -> Path:
    """Resolve the native work root from process configuration."""
    raw_value = os.environ.get("OWLBEAR_WORK_ROOT", "").strip()
    selected = Path(raw_value) if raw_value else _DEFAULT_WORK_ROOT
    return selected.resolve()


def _normalize_escaped_newlines(text: str) -> tuple[str, bool]:
    r"""Protect ``\\n``, normalize ``\n`` to newlines, then restore ``\n``."""
    sentinel = "\x00OBK_NL_SENTINEL\x00"
    protected = text.replace("\\\\n", sentinel)
    normalized = protected.replace("\\n", "\n")
    restored = normalized.replace(sentinel, "\\n")
    return restored, restored != text


def _sanitize_agent_strings(kwargs: dict[str, object]) -> None:
    """Normalize common LLM string-encoding mistakes in-place.

    Detects literal ``""`` or ``''`` (two quote characters intended as empty
    string by the agent) and replaces with actual empty string so downstream
    truthiness checks work correctly.
    """
    for key, value in kwargs.items():
        if isinstance(value, str) and value in ('""', "''"):
            kwargs[key] = ""


def _append_norm_guidance(guidance: list[str] | None, *, changed: bool) -> list[str]:
    """Append normalization guidance only when newline normalization occurred."""
    merged = list(guidance or [])
    if changed:
        merged.append(_NORM_GUIDANCE)
    return merged


def _startup_error(work_root: Path, detail: str) -> RuntimeError:
    """Build a startup error with native work-root remediation guidance."""
    return RuntimeError(f"{detail}: {work_root}. Set OWLBEAR_WORK_ROOT to a valid native work directory.")


def _raise_tool_error(code: str, message: str) -> None:
    """Raise MCP ToolError with normalized JSON payload fields."""
    raise ToolError(json.dumps({"code": code, "message": message}))


def _raise_param_validation(message: str) -> None:
    """Raise parameter validation errors using the MCP error envelope format."""
    _raise_tool_error("ERR_PARAM_VALIDATION", message)


def _require_uuid4(value: str, *, field: str) -> str:
    """Validate value is UUID4 text and return the original value."""
    try:
        parsed = UUID(value)
    except (TypeError, ValueError) as exc:
        _raise_param_validation(f"{field} must be a valid UUID4")
        raise AssertionError from exc
    if parsed.version != _UUID4_VERSION:
        _raise_param_validation(f"{field} must be a valid UUID4")
    return value


@dataclass
class AppContext:
    """Runtime context passed through MCP lifespan to all tools."""

    workspace: NativeWorkspace
    dispatch_runtimes: dict[str, DispatchRuntime] = field(default_factory=dict)

    def __contains__(self, item: object) -> bool:
        """Allow membership tests without TypeError (returns False always)."""
        return False


def _apply_tool_exclusions(server: FastMCP) -> set[str]:
    """Read KANBAN_TOOLS_EXCLUDE and remove each listed tool from the server.

    Returns the set of tool names successfully removed.
    """
    excluded: set[str] = set()
    env_val = os.environ.get("KANBAN_TOOLS_EXCLUDE", "")
    if not env_val:
        return excluded
    for raw in env_val.split(","):
        tool_name = raw.strip()
        if not tool_name:
            continue
        try:
            server.remove_tool(tool_name)
            excluded.add(tool_name)
        except Exception:  # noqa: BLE001, S110
            pass
    return excluded


@asynccontextmanager
async def app_lifespan(_server: FastMCP) -> AsyncGenerator[AppContext]:
    """Instantiate the native workspace and yield the MCP session context."""
    work_root = _resolve_work_root()
    _apply_tool_exclusions(_server)

    try:
        claim_expiry = parse_claim_expiry(os.environ.get("OWLBEAR_CLAIM_EXPIRY", _DEFAULT_CLAIM_EXPIRY))
        workspace = NativeWorkspace(work_root, claim_expiry)
    except Exception as exc:
        raise _startup_error(work_root, "Failed to initialize native workspace") from exc
    yield AppContext(workspace=workspace)


def _dispatch_runtime(app_ctx: AppContext, change_id: str) -> DispatchRuntime:
    """Assemble and cache the native runtime for one admitted sibling change."""
    cached = app_ctx.dispatch_runtimes.get(change_id)
    if cached is not None:
        return cached
    workspace = app_ctx.workspace
    changes_dir = workspace.changes_dir
    loaded = load_change(changes_dir, change_id)
    if loaded.revision is None:
        _raise_tool_error("ERR_CHANGE_NOT_ADMITTED", "change is not admitted")
    proof_checkouts = ProofCheckoutManager(workspace.workspace_root, workspace.proof_root)
    runtime = DispatchRuntime(
        NativeRuntime(
            loaded.revision,
            workspace.work_root,
            GitRepositoryHistory(workspace.workspace_root),
            workspace.claim_expiry,
            proof_checkouts,
        ),
        workspace.work_root,
        proof_checkouts,
    )
    app_ctx.dispatch_runtimes[change_id] = runtime
    return runtime


def _load_request_revision(app_ctx: AppContext, change_id: str, delivery_digest: str) -> ChangeRevision:
    """Load and validate the admitted revision named by a request tool call."""
    changes_dir = app_ctx.workspace.changes_dir
    try:
        loaded = load_change(changes_dir, change_id)
    except FileNotFoundError:
        _raise_tool_error("ERR_CHANGE_NOT_FOUND", f"change '{change_id}' not found")
    if loaded.revision is None:
        diagnostic = loaded.diagnostics[0] if loaded.diagnostics else None
        if (
            diagnostic is not None
            and diagnostic.code is ChangeDiagnosticCode.FILE_MISSING
            and diagnostic.detail == "change directory is missing"
        ):
            _raise_tool_error("ERR_CHANGE_NOT_FOUND", f"change '{change_id}' not found")
        _raise_tool_error("ERR_CHANGE_NOT_ADMITTED", "change is not admitted")
    if loaded.revision.delivery_digest != delivery_digest:
        digest_short = loaded.revision.delivery_digest[:16]
        _raise_tool_error("ERR_DIGEST_MISMATCH", f"digest mismatch: expected {digest_short}...")
    return loaded.revision


mcp = FastMCP("owlbear-kanban", lifespan=app_lifespan)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, idempotentHint=True, destructiveHint=False))
async def create_request(  # noqa: PLR0913, PLR0917
    ctx: Context,
    request_id: str,
    created_at: str,
    change_id: str,
    delivery_digest: str,
    kind: str,
    title: str,
    summary: str,
    agent: str,
    target_node_id: str | None = None,
    job_ids: list[int] | None = None,
    options: list[dict[str, object]] | None = None,
    body: str = "",
) -> dict[str, object]:
    """Create a pending request and return its structured payload."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    normalized_body, body_changed = _normalize_escaped_newlines(body)
    revision = _load_request_revision(app_ctx, change_id, delivery_digest)

    # Build native request
    try:
        parsed_options: tuple[RequestOption, ...] = ()
        if kind == "decision" and options:
            parsed_options = tuple(RequestOption.model_validate(opt) for opt in options)

        evidence: tuple[str, ...] = ()
        resume_condition: str | None = None
        if kind == "action":
            # Action requests require evidence and resume condition
            evidence = (body,) if body else ()
            resume_condition = "User resolution required"

        request = NativeRequest(
            request_id=request_id,
            kind=kind,  # type: ignore[arg-type]
            title=title,
            summary=summary,
            body=normalized_body,
            agent=agent,
            created_at=created_at,
            change_id=change_id,
            delivery_digest=delivery_digest,  # type: ignore[arg-type]
            target_node_id=target_node_id,
            job_ids=tuple(job_ids or ()),
            options=parsed_options,
            evidence=evidence,
            resume_condition=resume_condition,
        )
    except PydanticValidationError as exc:
        _raise_param_validation(str(exc))

    # Create via native runtime
    try:
        runtime = NativeRequestRuntime(revision, app_ctx.workspace.work_root)
        stored = await asyncio.to_thread(runtime.create_request, request)
    except RequestConflictError:
        _raise_tool_error("ERR_NATIVE_REQUEST_CONFLICT", "request identity already names different immutable content")
    except RequestReferenceError:
        _raise_tool_error("ERR_NATIVE_REQUEST_REFERENCE", "request references authority or work outside its revision")
    except PydanticValidationError as exc:
        _raise_param_validation(str(exc))

    payload = stored.model_dump()
    payload["guidance"] = _append_norm_guidance([], changed=body_changed)
    return payload


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True, destructiveHint=False))
async def list_requests(
    ctx: Context,
    change_id: str,
    delivery_digest: str,
    status: str = "pending",
) -> list[dict[str, object]]:
    """List request records by status and optional task filter."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    revision = _load_request_revision(app_ctx, change_id, delivery_digest)

    # Validate status parameter
    try:
        parsed_status: RequestStatus | None = None
        if status and status != "all":
            parsed_status = RequestStatus(status)
    except ValueError:
        _raise_param_validation(f"status must be 'pending', 'resolved', or 'all', got '{status}'")

    # List via native runtime
    try:
        runtime = NativeRequestRuntime(revision, app_ctx.workspace.work_root)
        if status == "all":
            records = await asyncio.to_thread(runtime.list_requests, None)
        else:
            records = await asyncio.to_thread(runtime.list_requests, parsed_status)
    except PydanticValidationError as exc:
        _raise_param_validation(str(exc))

    return [record.model_dump(exclude={"request": {"body"}}) for record in records]


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True, destructiveHint=False))
async def show_request(
    ctx: Context,
    change_id: str,
    delivery_digest: str,
    request_id: str,
) -> dict[str, object]:
    """Show a single request record with full detail."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    revision = _load_request_revision(app_ctx, change_id, delivery_digest)

    # Show via native runtime
    try:
        runtime = NativeRequestRuntime(revision, app_ctx.workspace.work_root)
        record = await asyncio.to_thread(runtime.show_request, request_id)  # type: ignore[arg-type]
    except RequestNotFoundError:
        _raise_tool_error("ERR_NATIVE_REQUEST_NOT_FOUND", f"request '{request_id}' not found")
    except PydanticValidationError as exc:
        _raise_param_validation(str(exc))

    return record.model_dump()


# ---------------------------------------------------------------------------
# Native dispatch bridge — bootstrap-only IF-015 work operations
# ---------------------------------------------------------------------------


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True, destructiveHint=False))
async def pick_jobs(
    ctx: Context,
    *,
    change_id: str,
    candidate_revision: str,
    wave_size: int,
) -> object:
    """Plan eligible native jobs for one admitted change revision."""
    try:
        params = PickJobsParams.model_validate(
            {
                "change_id": change_id,
                "candidate_revision": candidate_revision,
                "wave_size": wave_size,
            }
        )
        app_ctx: AppContext = ctx.request_context.lifespan_context
        return _dispatch_runtime(app_ctx, params.change_id).pick_waves(
            params.candidate_revision,
            params.wave_size,
        )
    except PydanticValidationError as exc:
        _raise_param_validation(str(exc))


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, idempotentHint=True, destructiveHint=False))
async def start_job(  # noqa: PLR0913
    ctx: Context,
    *,
    change_id: str,
    job_id: int,
    attempt_id: str,
    claim_id: str,
    actor_id: str,
    process_id: str,
    claimed_at: str,
    candidate_revision: str,
) -> object:
    """Claim one native job through the dispatch runtime."""
    try:
        params = StartJobParams.model_validate(
            {
                "change_id": change_id,
                "job_id": job_id,
                "attempt_id": attempt_id,
                "claim_id": claim_id,
                "actor_id": actor_id,
                "process_id": process_id,
                "claimed_at": claimed_at,
                "candidate_revision": candidate_revision,
            }
        )
        app_ctx: AppContext = ctx.request_context.lifespan_context
        started, checkout = _dispatch_runtime(app_ctx, params.change_id).start_with_checkout(
            StartJobRequest(**params.model_dump(exclude={"change_id"}))
        )
        if checkout is not None and hasattr(checkout, "checkout"):
            return {"start": started, "checkout": checkout}
        return started  # noqa: TRY300
    except PydanticValidationError as exc:
        _raise_param_validation(str(exc))


async def _finish_job(
    ctx: Context,
    params: FinishJobParams,
    purpose: Literal["build", "accept", "audit"],
) -> object:
    app_ctx: AppContext = ctx.request_context.lifespan_context
    runtime = _dispatch_runtime(app_ctx, params.change_id)
    request_data = params.model_dump(exclude={"change_id"})
    if params.impact_closure is not None:
        request_data["impact_closure"] = parse_impact_closure(params.impact_closure)
    request = FinishJobRequest(**request_data)
    return {
        "build": runtime.finish_build,
        "accept": runtime.finish_accept,
        "audit": runtime.finish_audit,
    }[purpose](request)


def _tool_params(values: dict[str, object]) -> dict[str, object]:
    """Remove the transport context before strict MCP parameter validation."""
    return {key: value for key, value in values.items() if key != "ctx"}


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, idempotentHint=True, destructiveHint=False))
async def finish_plan(  # noqa: PLR0913
    ctx: Context,
    *,
    change_id: str,
    job_id: int,
    attempt_id: str,
    claim_id: str,
    actor_id: str,
    process_id: str,
    finished_at: str,
    receipt_id: str,
    code_revision: str,
    evidence: dict[str, object],
    node_plan: dict[str, object],
    build_job_ids: tuple[int, ...],
    accept_job_id: int,
    evidence_ids: tuple[str, ...] = (),
    impact_closure: dict[str, object] | None = None,
) -> object:
    """Finalize a plan job through the native dispatch runtime."""
    try:
        params = FinishPlanParams.model_validate(_tool_params(locals()))
        app_ctx: AppContext = ctx.request_context.lifespan_context
        request_data = params.model_dump(exclude={"change_id"})
        if params.impact_closure is not None:
            request_data["impact_closure"] = parse_impact_closure(params.impact_closure)
        return _dispatch_runtime(app_ctx, params.change_id).finish_plan(FinishPlanRequest(**request_data))
    except PydanticValidationError as exc:
        _raise_param_validation(str(exc))


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, idempotentHint=True, destructiveHint=False))
async def finish_build(  # noqa: PLR0913
    ctx: Context,
    *,
    change_id: str,
    job_id: int,
    attempt_id: str,
    claim_id: str,
    actor_id: str,
    process_id: str,
    finished_at: str,
    receipt_id: str,
    code_revision: str,
    evidence: dict[str, object],
    evidence_ids: tuple[str, ...] = (),
    impact_closure: dict[str, object] | None = None,
) -> object:
    """Finalize a build job through the native dispatch runtime."""
    try:
        return await _finish_job(ctx, FinishJobParams.model_validate(_tool_params(locals())), "build")
    except PydanticValidationError as exc:
        _raise_param_validation(str(exc))


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, idempotentHint=True, destructiveHint=False))
async def finish_accept(  # noqa: PLR0913
    ctx: Context,
    *,
    change_id: str,
    job_id: int,
    attempt_id: str,
    claim_id: str,
    actor_id: str,
    process_id: str,
    finished_at: str,
    receipt_id: str,
    code_revision: str,
    evidence: dict[str, object],
    reconciliation_plan_job_ids: tuple[int, ...],
    evidence_ids: tuple[str, ...] = (),
    impact_closure: dict[str, object] | None = None,
) -> object:
    """Finalize an accept job through the native dispatch runtime."""
    try:
        params = FinishAcceptParams.model_validate(_tool_params(locals()))
        app_ctx: AppContext = ctx.request_context.lifespan_context
        request_data = params.model_dump(exclude={"change_id"})
        if params.impact_closure is not None:
            request_data["impact_closure"] = parse_impact_closure(params.impact_closure)
        return _dispatch_runtime(app_ctx, params.change_id).finish_accept(FinishAcceptRequest(**request_data))
    except PydanticValidationError as exc:
        _raise_param_validation(str(exc))


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, idempotentHint=True, destructiveHint=False))
async def reject_accept(  # noqa: PLR0913
    ctx: Context,
    *,
    change_id: str,
    job_id: int,
    attempt_id: str,
    claim_id: str,
    actor_id: str,
    process_id: str,
    rejected_at: str,
    detail: str,
    evidence_ids: tuple[str, ...],
    findings: tuple[Finding, ...],
    invalidation: InvalidationParams,
) -> object:
    """Reject an accept job and publish its minimum corrective work."""
    try:
        params = RejectAcceptParams.model_validate(_tool_params(locals()))
        app_ctx: AppContext = ctx.request_context.lifespan_context
        return _dispatch_runtime(app_ctx, params.change_id).reject_accept(
            RejectAcceptRequest(
                **params.model_dump(exclude={"change_id", "findings", "invalidation"}),
                findings=params.findings,
                invalidation=InvalidationRequest(**params.invalidation.model_dump()),
            )
        )
    except PydanticValidationError as exc:
        _raise_param_validation(str(exc))


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, idempotentHint=True, destructiveHint=False))
async def reject_audit(  # noqa: PLR0913
    ctx: Context,
    *,
    change_id: str,
    job_id: int,
    attempt_id: str,
    claim_id: str,
    actor_id: str,
    process_id: str,
    rejected_at: str,
    detail: str,
    evidence_ids: tuple[str, ...],
    findings: tuple[Finding, ...],
    invalidation: InvalidationParams,
) -> object:
    """Reject an audit job and publish its minimum corrective work."""
    try:
        params = RejectAuditParams.model_validate(_tool_params(locals()))
        app_ctx: AppContext = ctx.request_context.lifespan_context
        return _dispatch_runtime(app_ctx, params.change_id).reject_audit(
            RejectAuditRequest(
                **params.model_dump(exclude={"change_id", "findings", "invalidation"}),
                findings=params.findings,
                invalidation=InvalidationRequest(**params.invalidation.model_dump()),
            )
        )
    except PydanticValidationError as exc:
        _raise_param_validation(str(exc))


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, idempotentHint=True, destructiveHint=False))
async def finish_audit(  # noqa: PLR0913
    ctx: Context,
    *,
    change_id: str,
    job_id: int,
    attempt_id: str,
    claim_id: str,
    actor_id: str,
    process_id: str,
    finished_at: str,
    receipt_id: str,
    code_revision: str,
    evidence: dict[str, object],
    evidence_ids: tuple[str, ...] = (),
    impact_closure: dict[str, object] | None = None,
) -> object:
    """Finalize an audit job through the native dispatch runtime."""
    try:
        return await _finish_job(ctx, FinishJobParams.model_validate(_tool_params(locals())), "audit")
    except PydanticValidationError as exc:
        _raise_param_validation(str(exc))


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, idempotentHint=True, destructiveHint=False))
async def release_job(  # noqa: PLR0913
    ctx: Context,
    *,
    change_id: str,
    job_id: int,
    attempt_id: str,
    claim_id: str,
    actor_id: str,
    process_id: str,
    released_at: str,
) -> object:
    """Release one native job through the dispatch runtime."""
    try:
        params = ReleaseJobParams.model_validate(_tool_params(locals()))
        app_ctx: AppContext = ctx.request_context.lifespan_context
        return _dispatch_runtime(app_ctx, params.change_id).release(
            ReleaseJobRequest(**params.model_dump(exclude={"change_id"}))
        )
    except PydanticValidationError as exc:
        _raise_param_validation(str(exc))


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, idempotentHint=True, destructiveHint=False))
async def recover_expired_claims(
    ctx: Context,
    *,
    change_id: str,
    recovered_at: str,
    actor_id: str,
    process_id: str,
) -> object:
    """Recover strictly expired native claims through the dispatch runtime."""
    try:
        params = RecoverExpiredClaimsParams.model_validate(_tool_params(locals()))
        app_ctx: AppContext = ctx.request_context.lifespan_context
        return _dispatch_runtime(app_ctx, params.change_id).recover_expired_claims(
            RecoverExpiredClaimsRequest(**params.model_dump(exclude={"change_id"}))
        )
    except PydanticValidationError as exc:
        _raise_param_validation(str(exc))


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True, destructiveHint=False))
async def list_jobs(
    ctx: Context,
    *,
    change_id: str,
    candidate_revision: str,
    cursor: str | None = None,
    limit: int = 100,
) -> object:
    """List native jobs with bounded pagination."""
    try:
        params = ListJobsParams.model_validate(_tool_params(locals()))
        app_ctx: AppContext = ctx.request_context.lifespan_context
        runtime = _dispatch_runtime(app_ctx, params.change_id)
        try:
            return runtime._native.list_jobs(  # noqa: SLF001
                candidate_revision=params.candidate_revision,
                cursor=params.cursor,
                limit=params.limit,
            )
        except ValueError as exc:
            if "cursor is not current" in str(exc):
                _raise_tool_error("ERR_CURSOR_STALE", "page cursor is not current")
            raise
    except PydanticValidationError as exc:
        _raise_param_validation(str(exc))


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True, destructiveHint=False))
async def show_job(
    ctx: Context,
    *,
    change_id: str,
    job_id: int,
) -> object:
    """Show one native job composed from immutable record and authority projection."""
    try:
        params = ShowJobParams.model_validate(_tool_params(locals()))
        app_ctx: AppContext = ctx.request_context.lifespan_context
        runtime = _dispatch_runtime(app_ctx, params.change_id)
        try:
            stored = runtime._jobs.read(params.job_id)  # noqa: SLF001
        except FileNotFoundError:
            _raise_tool_error("ERR_JOB_NOT_FOUND", f"job {params.job_id} not found")
        else:
            projection = project_job(
                stored.job,
                runtime._native._revision,  # noqa: SLF001
            )
            return {
                "job": stored.job,
                "title": projection.title,
                "outcome": projection.outcome,
                "acceptance": projection.acceptance,
                "modules": projection.modules,
                "interfaces": projection.interfaces,
                "proof": projection.proof,
            }
    except PydanticValidationError as exc:
        _raise_param_validation(str(exc))


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True, destructiveHint=False))
async def list_attempts(
    ctx: Context,
    *,
    change_id: str,
    cursor: str | None = None,
    limit: int = 100,
) -> object:
    """List attempt history with bounded pagination."""
    try:
        params = ListAttemptsParams.model_validate(_tool_params(locals()))
        app_ctx: AppContext = ctx.request_context.lifespan_context
        runtime = _dispatch_runtime(app_ctx, params.change_id)
        try:
            return runtime._native.list_attempts(  # noqa: SLF001
                cursor=params.cursor,
                limit=params.limit,
            )
        except ValueError as exc:
            if "cursor is not current" in str(exc):
                _raise_tool_error("ERR_CURSOR_STALE", "page cursor is not current")
            raise
    except PydanticValidationError as exc:
        _raise_param_validation(str(exc))


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True, destructiveHint=False))
async def list_findings(
    ctx: Context,
    *,
    change_id: str,
    cursor: str | None = None,
    limit: int = 100,
) -> object:
    """List corrective findings with bounded pagination."""
    try:
        params = ListFindingsParams.model_validate(_tool_params(locals()))
        app_ctx: AppContext = ctx.request_context.lifespan_context
        runtime = _dispatch_runtime(app_ctx, params.change_id)
        try:
            return runtime._native.list_findings(  # noqa: SLF001
                cursor=params.cursor,
                limit=params.limit,
            )
        except ValueError as exc:
            if "cursor is not current" in str(exc):
                _raise_tool_error("ERR_CURSOR_STALE", "page cursor is not current")
            raise
    except PydanticValidationError as exc:
        _raise_param_validation(str(exc))


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True, destructiveHint=False))
async def list_activity(
    ctx: Context,
    *,
    change_id: str,
    cursor: str | None = None,
    limit: int = 100,
) -> object:
    """List chronological runtime activity history with bounded pagination."""
    try:
        params = ListActivityParams.model_validate(_tool_params(locals()))
        app_ctx: AppContext = ctx.request_context.lifespan_context
        runtime = _dispatch_runtime(app_ctx, params.change_id)
        try:
            return runtime._native.list_history(  # noqa: SLF001
                cursor=params.cursor,
                limit=params.limit,
            )
        except ValueError as exc:
            if "cursor is not current" in str(exc):
                _raise_tool_error("ERR_CURSOR_STALE", "page cursor is not current")
            raise
    except PydanticValidationError as exc:
        _raise_param_validation(str(exc))


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True, destructiveHint=False))
async def show_receipt(
    ctx: Context,
    *,
    change_id: str,
    receipt_id: str,
) -> object:
    """Show one immutable receipt by ID from the native receipt store."""
    try:
        params = ShowReceiptParams.model_validate(_tool_params(locals()))
        app_ctx: AppContext = ctx.request_context.lifespan_context
        runtime = _dispatch_runtime(app_ctx, params.change_id)
        result = runtime._native._receipts.read(params.receipt_id)  # noqa: SLF001
        if result.receipt is not None:
            return result.receipt
        # Return stable error for missing or malformed receipt
        diagnostic = result.diagnostics[0]
        code = diagnostic.code
        if code == "ERR_RECEIPT_FILE_MISSING":
            _raise_tool_error("ERR_RECEIPT_MISSING", diagnostic.detail)
        else:
            _raise_tool_error(code, diagnostic.detail)
    except PydanticValidationError as exc:
        _raise_param_validation(str(exc))


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True, destructiveHint=False))
async def show_finding(
    ctx: Context,
    *,
    change_id: str,
    finding_id: str,
) -> object:
    """Show one immutable corrective finding by ID."""
    try:
        params = ShowFindingParams.model_validate(_tool_params(locals()))
        app_ctx: AppContext = ctx.request_context.lifespan_context
        runtime = _dispatch_runtime(app_ctx, params.change_id)
        result = runtime._native._findings.read(params.finding_id)  # noqa: SLF001
        if result.finding is not None:
            return result.finding
        diagnostic = result.diagnostics[0]
        if diagnostic.code == "ERR_FINDING_FILE_MISSING":
            _raise_tool_error("ERR_FINDING_MISSING", diagnostic.detail)
        _raise_tool_error(diagnostic.code, diagnostic.detail)
    except PydanticValidationError as exc:
        _raise_param_validation(str(exc))


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True, destructiveHint=False))
async def work_health(
    ctx: Context,
    *,
    change_id: str,
    cursor: str | None = None,
    limit: int = 100,
) -> object:
    """Return bounded native work integrity findings without mutation."""
    try:
        params = WorkHealthParams.model_validate(_tool_params(locals()))
        app_ctx: AppContext = ctx.request_context.lifespan_context
        runtime = _dispatch_runtime(app_ctx, params.change_id)
        try:
            result = runtime._native.work_health(  # noqa: SLF001
                cursor=params.cursor,
                limit=params.limit,
            )
            return result.model_dump(mode="python")
        except ValueError as exc:
            if "cursor is not current" in str(exc):
                _raise_tool_error("ERR_CURSOR_STALE", "page cursor is not current")
            raise
    except PydanticValidationError as exc:
        _raise_param_validation(str(exc))


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True, destructiveHint=False))
async def list_changes(ctx: Context) -> list[dict[str, object]]:
    """List all change packages with load state and identity-ordered summaries."""
    app_ctx: AppContext = ctx.request_context.lifespan_context
    changes_dir = app_ctx.workspace.changes_dir

    if not changes_dir.is_dir():
        return []

    results: list[dict[str, object]] = []
    try:
        entries = sorted(changes_dir.iterdir())
    except OSError:
        return []

    for entry in entries:
        if not entry.is_dir():
            continue
        change_id = entry.name
        load_result = load_change(changes_dir, change_id)

        if load_result.revision is not None:
            results.append(
                {
                    "change_id": change_id,
                    "state": "loaded",
                    "digest": load_result.revision.delivery_digest,
                }
            )
        else:
            diagnostics = [
                {
                    "code": d.code.value,
                    "detail": d.detail,
                    "path": d.path,
                    "target": d.target,
                }
                for d in load_result.diagnostics
            ]
            results.append(
                {
                    "change_id": change_id,
                    "state": "malformed",
                    "diagnostics": diagnostics,
                }
            )

    return results


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True, destructiveHint=False))
async def show_change(ctx: Context, *, change_id: str) -> dict[str, object]:
    """Show one loaded change revision with canonical digest and graph."""
    if not change_id or not change_id.strip():
        _raise_param_validation("change_id must be non-empty")

    app_ctx: AppContext = ctx.request_context.lifespan_context
    changes_dir = app_ctx.workspace.changes_dir

    load_result = load_change(changes_dir, change_id)

    if load_result.revision is None:
        diagnostics = [
            {
                "code": d.code.value,
                "detail": d.detail,
                "path": d.path,
                "target": d.target,
            }
            for d in load_result.diagnostics
        ]
        _raise_tool_error("ERR_CHANGE_NOT_LOADED", json.dumps({"diagnostics": diagnostics}))

    revision = load_result.revision
    return {
        "change_id": revision.change_id,
        "delivery_digest": revision.delivery_digest,
        "intent": revision.intent,
        "design": revision.design,
        "decisions": revision.decisions.model_dump(mode="python"),
        "graph": revision.graph.model_dump(mode="python"),
    }


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True, destructiveHint=False))
async def validate_change(ctx: Context, *, change_id: str, evidence: dict[str, object]) -> dict[str, object]:
    """Validate change admission without writing receipt, job, request, or attempt paths."""
    if not change_id or not change_id.strip():
        _raise_param_validation("change_id must be non-empty")

    app_ctx: AppContext = ctx.request_context.lifespan_context
    changes_dir = app_ctx.workspace.changes_dir

    load_result = load_change(changes_dir, change_id)

    if load_result.revision is None:
        _raise_tool_error("ERR_CHANGE_NOT_LOADED", "change could not be loaded")

    try:
        admission_evidence = AdmissionEvidence.model_validate_json(json.dumps(evidence))
    except PydanticValidationError as exc:
        _raise_param_validation(f"invalid evidence: {exc}")

    assessment = evaluate_admission(load_result.revision, admission_evidence)
    return assessment.model_dump(mode="python")


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True, destructiveHint=False))
async def change_health(ctx: Context, *, change_id: str) -> dict[str, object]:
    """Return canonical change health result without mutating authority or work paths."""
    if not change_id or not change_id.strip():
        _raise_param_validation("change_id must be non-empty")

    app_ctx: AppContext = ctx.request_context.lifespan_context
    changes_dir = app_ctx.workspace.changes_dir

    result = get_change_health(changes_dir, change_id)
    return result.model_dump(mode="python")


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, idempotentHint=True, destructiveHint=False))
async def admit_change(
    ctx: Context,
    *,
    change_id: str,
    evidence: dict[str, object],
) -> dict[str, object]:
    """Admit change and atomically publish receipt and initial plan jobs."""
    if not change_id or not change_id.strip():
        _raise_param_validation("change_id must be non-empty")

    app_ctx: AppContext = ctx.request_context.lifespan_context
    changes_dir = app_ctx.workspace.changes_dir

    load_result = load_change(changes_dir, change_id)

    if load_result.revision is None:
        _raise_tool_error("ERR_CHANGE_NOT_LOADED", "change could not be loaded")

    try:
        admission_evidence = AdmissionEvidence.model_validate_json(json.dumps(evidence))
    except PydanticValidationError as exc:
        _raise_param_validation(f"invalid evidence: {exc}")

    try:
        transaction = AdmissionTransaction(load_result.revision, app_ctx.workspace.work_root)
        receipt, generation, assessment = transaction.validate_and_admit(admission_evidence)
    except AdmissionConflictError:
        _raise_tool_error("ERR_ADMISSION_CONFLICT", "admission conflict: incompatible identity already exists")
    except AdmissionValidationError:
        _raise_tool_error("ERR_ADMISSION_VALIDATION", "admission validation failed: invalid immutable identity")
    except AdmissionPublicationError as exc:
        cause_msg = str(getattr(exc, "cause", exc))
        _raise_tool_error("ERR_ADMISSION_PUBLICATION", f"admission publication failed: {cause_msg}")

    return {
        "receipt": receipt.model_dump(mode="python") if receipt else None,
        "generation": generation.model_dump(mode="python") if generation else None,
        "assessment": assessment.model_dump(mode="python"),
    }
