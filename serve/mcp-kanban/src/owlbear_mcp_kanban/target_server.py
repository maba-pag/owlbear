"""Dormant FastMCP adapter for the target delivery runtime."""

from __future__ import annotations

import base64
import hashlib
import json
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Never

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import ValidationError

from owlbear_kanban.target_runtime import (
    ArbitrateTargetAttemptRequest,
    FinishTargetJobRequest,
    RecoverInterruptedTaskRequest,
    RespondToReviewRequest,
    StartTargetJobRequest,
    TargetRecoveryError,
    TargetRequest,
    TargetRuntimeConflictError,
    TargetRuntimeReferenceError,
)
from owlbear_kanban.work_items import WorkItemAttention, WorkItemProjector, WorkItemStage
from owlbear_mcp_kanban.target_models import TargetCursor, TargetDiagnostic, TargetRequestParams, WorkItemPage

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Callable

    from pydantic import BaseModel

    from owlbear_kanban.target_authority import TargetAuthority
    from owlbear_kanban.target_runtime import TargetRuntime

_READ = ToolAnnotations(readOnlyHint=True, idempotentHint=True, destructiveHint=False)
_WRITE = ToolAnnotations(readOnlyHint=False, idempotentHint=True, destructiveHint=False)


@dataclass(frozen=True)
class TargetChangeBinding:
    """Bind one admitted semantic authority to its target runtime."""

    authority: TargetAuthority
    runtime: TargetRuntime


@dataclass(frozen=True)
class TargetAppContext:
    """Resolved dependencies shared by every target MCP tool."""

    changes: dict[str, TargetChangeBinding]
    process_is_alive: Callable[[str], bool]
    work_item_activity: Callable[[str, str], tuple[dict[str, object], ...]]

    @property
    def authority_identity(self) -> str:
        """Return one stable identity for the loaded portfolio authority."""
        entries = sorted((change_id, binding.runtime.authority_digest) for change_id, binding in self.changes.items())
        return hashlib.sha256(json.dumps(entries, separators=(",", ":")).encode()).hexdigest()


class TargetMCPAdapter:
    """Translate target MCP calls without duplicating runtime decisions."""

    def __init__(self, context: TargetAppContext) -> None:
        self._context = context

    async def list_work_items(
        self,
        change_id: str | None = None,
        stage: WorkItemStage | None = None,
        attention: WorkItemAttention | None = None,
        cursor: str | None = None,
        limit: int = 100,
    ) -> WorkItemPage:
        """List stable mixed-change semantic work-item pages."""
        if limit <= 0:
            self._raise_diagnostic(
                "ERR_TARGET_PARAM_VALIDATION",
                "limit must be positive",
                change_id,
                retry_safe=False,
            )
        items = self._portfolio(change_id, stage, attention)
        identity = self._context.authority_identity
        query_identity = self._query_identity(identity, items, change_id, stage, attention)
        offset = self._cursor_offset(cursor, query_identity, change_id)
        page = items[offset : offset + limit]
        next_offset = offset + len(page)
        next_cursor = self._encode_cursor(query_identity, next_offset) if next_offset < len(items) else None
        return WorkItemPage(items=page, authority_identity=identity, next_cursor=next_cursor)

    async def show_work_item(self, work_item_id: str, change_id: str | None = None) -> dict[str, object]:
        """Show one semantic item, requiring disambiguation across changes."""
        matches = self._matching_projectors(work_item_id, change_id)
        if len(matches) != 1:
            detail = "work item is missing" if not matches else "work item identity is ambiguous across changes"
            self._raise_diagnostic("ERR_TARGET_WORK_ITEM_REFERENCE", detail, change_id, retry_safe=False)
        return matches[0].show(work_item_id).model_dump(mode="json")

    async def list_semantic_updates(self, work_item_id: str, change_id: str | None = None) -> list[dict[str, object]]:
        """List non-blocking semantic updates for one exact work item."""
        projector = self._one_projector(work_item_id, change_id)
        return [item.model_dump(mode="json") for item in projector.list_semantic_updates(work_item_id)]

    async def list_work_item_activity(self, work_item_id: str, change_id: str | None = None) -> list[dict[str, object]]:
        """List correction and execution history for one exact work item."""
        _binding, resolved_change_id = self._one_binding(work_item_id, change_id)
        return list(self._context.work_item_activity(resolved_change_id, work_item_id))

    async def show_completion_summary(
        self, work_item_id: str, change_id: str | None = None
    ) -> dict[str, object] | None:
        """Show the commitment-level result for one completed work item."""
        summary = self._one_projector(work_item_id, change_id).show_completion_summary(work_item_id)
        return summary.model_dump(mode="json") if summary is not None else None

    async def list_frontier(self, change_id: str) -> list[dict[str, object]]:
        """List dependency-ready target jobs for one change."""
        return [item.model_dump(mode="json") for item in self._binding(change_id).runtime.list_frontier()]

    async def show_job(self, change_id: str, job_id: int) -> dict[str, object]:
        """Show one technical target job."""
        return self._invoke(change_id, lambda: self._binding(change_id).runtime.show_job(job_id))

    async def show_attempt(self, change_id: str, attempt_id: str) -> dict[str, object]:
        """Show one attempt with nested review and arbitration evidence."""
        return self._invoke(change_id, lambda: self._binding(change_id).runtime.show_attempt(attempt_id))

    async def show_receipt(self, change_id: str, receipt_id: str) -> dict[str, object]:
        """Show one immutable target receipt."""
        return self._invoke(change_id, lambda: self._binding(change_id).runtime.show_receipt(receipt_id))

    async def create_request(self, request: dict[str, object]) -> dict[str, object]:
        """Create one authority-scoped request."""
        params = self._validate(TargetRequestParams, request)
        target = TargetRequest.model_validate(params.model_dump())
        return self._invoke(target.change_id, lambda: self._binding(target.change_id).runtime.create_request(target))

    async def resolve_request(self, change_id: str, request_id: str, resolved_at: str) -> dict[str, object]:
        """Resolve one scoped request without erasing its immutable target."""
        return self._invoke(
            change_id,
            lambda: self._binding(change_id).runtime.resolve_request(request_id, resolved_at),
        )

    async def start_job(self, change_id: str, request: dict[str, object]) -> dict[str, object]:
        """Start one ready plan, build, or assembly transformation."""
        parsed = self._validate(StartTargetJobRequest, request)
        return self._invoke(change_id, lambda: self._binding(change_id).runtime.start_job(parsed))

    async def finish_plan(self, change_id: str, request: dict[str, object]) -> dict[str, object]:
        """Apply independent review evidence to one plan transformation."""
        return self._finish(change_id, request, "plan")

    async def finish_build(self, change_id: str, request: dict[str, object]) -> dict[str, object]:
        """Apply independent review evidence to one build transformation."""
        return self._finish(change_id, request, "build")

    async def finish_assembly(self, change_id: str, request: dict[str, object]) -> dict[str, object]:
        """Apply independent review evidence to one assembly transformation."""
        return self._finish(change_id, request, "assembly")

    async def respond_to_review(self, change_id: str, request: dict[str, object]) -> dict[str, object]:
        """Submit the owner's sole evidence response to a repair review."""
        parsed = self._validate(RespondToReviewRequest, request)
        return self._invoke(change_id, lambda: self._binding(change_id).runtime.respond_to_review(parsed))

    async def arbitrate_attempt(self, change_id: str, request: dict[str, object]) -> dict[str, object]:
        """Record the one final isolated arbiter decision."""
        parsed = self._validate(ArbitrateTargetAttemptRequest, request)
        return self._invoke(change_id, lambda: self._binding(change_id).runtime.arbitrate(parsed))

    async def recover_interrupted_task(self, change_id: str, request: dict[str, object]) -> dict[str, object]:
        """Recover one exact task only after proving its owner process dead."""
        parsed = self._validate(RecoverInterruptedTaskRequest, request)
        return self._invoke(
            change_id,
            lambda: self._binding(change_id).runtime.recover_interrupted_task(
                parsed,
                process_is_alive=self._context.process_is_alive,
            ),
        )

    def _finish(self, change_id: str, request: dict[str, object], expected_kind: str) -> dict[str, object]:
        parsed = self._validate(FinishTargetJobRequest, request)

        def operation() -> BaseModel:
            runtime = self._binding(change_id).runtime
            if runtime.show_job(parsed.job_id).kind != expected_kind:
                message = f"job is not a {expected_kind} transformation"
                raise TargetRuntimeReferenceError(message)
            return runtime.finish_job(parsed)

        return self._invoke(change_id, operation)

    def _portfolio(
        self,
        change_id: str | None,
        stage: WorkItemStage | None,
        attention: WorkItemAttention | None,
    ) -> tuple[Any, ...]:
        bindings = (
            ((change_id, self._binding(change_id)),) if change_id else tuple(sorted(self._context.changes.items()))
        )
        items = (
            item
            for _identity, binding in bindings
            for item in WorkItemProjector(binding.authority, binding.runtime.work_item_evidence()).list_items()
            if (stage is None or item.stage == stage) and (attention is None or item.attention == attention)
        )
        return tuple(sorted(items, key=lambda item: (item.change_id, item.work_item_id)))

    def _matching_projectors(self, work_item_id: str, change_id: str | None) -> list[WorkItemProjector]:
        bindings = (self._binding(change_id),) if change_id else tuple(self._context.changes.values())
        matches = []
        for binding in bindings:
            projector = WorkItemProjector(binding.authority, binding.runtime.work_item_evidence())
            if any(item.work_item_id == work_item_id for item in projector.list_items()):
                matches.append(projector)
        return matches

    def _one_projector(self, work_item_id: str, change_id: str | None) -> WorkItemProjector:
        matches = self._matching_projectors(work_item_id, change_id)
        if len(matches) != 1:
            detail = "work item is missing" if not matches else "work item identity is ambiguous across changes"
            self._raise_diagnostic("ERR_TARGET_WORK_ITEM_REFERENCE", detail, change_id, retry_safe=False)
        return matches[0]

    def _one_binding(self, work_item_id: str, change_id: str | None) -> tuple[TargetChangeBinding, str]:
        identities = (change_id,) if change_id is not None else tuple(sorted(self._context.changes))
        matches = []
        for identity in identities:
            binding = self._binding(identity)
            projector = WorkItemProjector(binding.authority, binding.runtime.work_item_evidence())
            if any(item.work_item_id == work_item_id for item in projector.list_items()):
                matches.append((binding, identity))
        if len(matches) != 1:
            detail = "work item is missing" if not matches else "work item identity is ambiguous across changes"
            self._raise_diagnostic("ERR_TARGET_WORK_ITEM_REFERENCE", detail, change_id, retry_safe=False)
        return matches[0]

    def _binding(self, change_id: str) -> TargetChangeBinding:
        try:
            return self._context.changes[change_id]
        except KeyError:
            self._raise_diagnostic(
                "ERR_TARGET_CHANGE_NOT_LOADED",
                "change is not loaded",
                change_id,
                retry_safe=False,
            )

    def _invoke(self, change_id: str, operation: Callable[[], BaseModel]) -> dict[str, object]:
        try:
            return operation().model_dump(mode="json")
        except (TargetRuntimeConflictError, TargetRuntimeReferenceError, TargetRecoveryError) as exc:
            retry_safe = isinstance(exc, TargetRuntimeConflictError)
            self._raise_diagnostic(exc.code, str(exc), change_id, retry_safe=retry_safe)

    def _validate[ModelT: BaseModel](self, model: type[ModelT], payload: dict[str, object]) -> ModelT:
        try:
            return model.model_validate_json(json.dumps(payload))
        except ValidationError as exc:
            self._raise_diagnostic("ERR_TARGET_PARAM_VALIDATION", str(exc), None, retry_safe=False)

    def _cursor_offset(self, cursor: str | None, query_identity: str, change_id: str | None) -> int:
        if cursor is None:
            return 0
        try:
            decoded = base64.urlsafe_b64decode(cursor.encode()).decode()
            parsed = TargetCursor.model_validate_json(decoded)
        except (ValueError, ValidationError) as exc:
            self._raise_diagnostic("ERR_TARGET_CURSOR_INVALID", str(exc), change_id, retry_safe=False)
        if parsed.query_identity != query_identity:
            self._raise_diagnostic(
                "ERR_TARGET_CURSOR_STALE",
                "portfolio projection changed",
                change_id,
                retry_safe=True,
            )
        return parsed.offset

    @staticmethod
    def _encode_cursor(query_identity: str, offset: int) -> str:
        payload = TargetCursor(query_identity=query_identity, offset=offset).model_dump_json()
        return base64.urlsafe_b64encode(payload.encode()).decode()

    @staticmethod
    def _query_identity(
        authority_identity: str,
        items: tuple[Any, ...],
        change_id: str | None,
        stage: WorkItemStage | None,
        attention: WorkItemAttention | None,
    ) -> str:
        payload = {
            "attention": attention.value if attention is not None else None,
            "authority_identity": authority_identity,
            "change_id": change_id,
            "items": [item.model_dump(mode="json") for item in items],
            "stage": stage.value if stage is not None else None,
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    def _raise_diagnostic(
        self,
        code: str,
        detail: str,
        change_id: str | None,
        *,
        retry_safe: bool,
    ) -> Never:
        binding = self._context.changes.get(change_id) if change_id is not None else None
        current = binding.runtime.authority_digest if binding is not None else self._context.authority_identity
        diagnostic = TargetDiagnostic(
            code=code,
            detail=detail,
            current_authority_identity=current,
            retry_safe=retry_safe,
        )
        raise ToolError(diagnostic.model_dump_json())


def assemble_target_server(context: TargetAppContext) -> FastMCP:
    """Assemble the isolated target registry without mutating the live MCP server."""

    @asynccontextmanager
    async def lifespan(_server: FastMCP) -> AsyncGenerator[TargetAppContext]:
        yield context

    server = FastMCP("owlbear-kanban-target", lifespan=lifespan)
    adapter = TargetMCPAdapter(context)
    _register_queries(server, adapter)
    _register_mutations(server, adapter)
    return server


def _register_queries(server: FastMCP, adapter: TargetMCPAdapter) -> None:
    for name in (
        "list_work_items",
        "show_work_item",
        "list_work_item_activity",
        "list_semantic_updates",
        "show_completion_summary",
        "list_frontier",
        "show_job",
        "show_attempt",
        "show_receipt",
    ):
        server.tool(name=name, annotations=_READ)(getattr(adapter, name))


def _register_mutations(server: FastMCP, adapter: TargetMCPAdapter) -> None:
    for name in (
        "create_request",
        "resolve_request",
        "start_job",
        "finish_plan",
        "finish_build",
        "finish_assembly",
        "respond_to_review",
        "arbitrate_attempt",
        "recover_interrupted_task",
    ):
        server.tool(name=name, annotations=_WRITE)(getattr(adapter, name))


__all__ = ["TargetAppContext", "TargetChangeBinding", "TargetMCPAdapter", "assemble_target_server"]
