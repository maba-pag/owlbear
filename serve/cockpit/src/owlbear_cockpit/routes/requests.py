"""Cockpit requests API routes."""

from __future__ import annotations

import logging
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict

from owlbear_cockpit.deps import get_engine

router = APIRouter()
_LOG = logging.getLogger(__name__)
_Engine = Annotated[object, Depends(get_engine)]
_UUID4_VERSION = 4


class RequestOptionResponse(BaseModel):
    """Public API shape for one decision option."""

    model_config = ConfigDict(extra="forbid")

    option_id: str
    label: str
    confidence: float
    recommended: bool
    rationale: str


class PendingRequestResponse(BaseModel):
    """Public API shape for one pending request record."""

    model_config = ConfigDict(extra="forbid")

    request_id: str
    task_id: int
    kind: Literal["decision", "action"]
    title: str
    summary: str
    agent: str
    created_at: str
    options: list[RequestOptionResponse]
    body: str


class ResolveRequestBody(BaseModel):
    """Request body for resolving a structured request."""

    model_config = ConfigDict(extra="forbid")

    selected_option_id: str | None = None
    free_text: str | None = None
    kind: Literal["decision", "action"] | None = None


class ResolveResponse(BaseModel):
    """Public API shape returned after a successful resolve."""

    model_config = ConfigDict(extra="forbid")

    request_id: str
    task_id: int
    kind: Literal["decision", "action"]
    title: str
    resolved_at: str | None


def _validate_request_id(request_id: str) -> None:
    try:
        parsed = UUID(request_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid request id") from exc

    if parsed.version != _UUID4_VERSION or str(parsed) != request_id.lower():
        raise HTTPException(status_code=422, detail="Invalid request id")


def _to_pending_response(record: object) -> PendingRequestResponse:
    return PendingRequestResponse.model_validate(
        {
            "request_id": record.request_id,
            "task_id": record.task_id,
            "kind": record.kind,
            "title": record.title,
            "summary": record.summary,
            "agent": record.agent,
            "created_at": record.created_at,
            "options": [
                {
                    "option_id": option.option_id,
                    "label": option.label,
                    "confidence": option.confidence,
                    "recommended": option.recommended,
                    "rationale": option.rationale,
                }
                for option in record.options
            ],
            "body": record.body,
        }
    )


@router.get("/requests/pending", response_model=list[PendingRequestResponse])
def list_pending_requests(engine: _Engine) -> list[PendingRequestResponse]:
    """List all pending structured requests for Cockpit."""
    try:
        engine.sweep_requests()
    except Exception:  # noqa: BLE001 - AC requires broad catch around sweep
        _LOG.warning("Request sweep failed before pending listing", exc_info=True)

    records = engine.list_requests(status="pending")
    return [_to_pending_response(record) for record in records]


@router.post("/requests/{request_id}/resolve", response_model=ResolveResponse)
def resolve_request(
    request_id: str,
    req: ResolveRequestBody,
    engine: _Engine,
) -> ResolveResponse:
    """Resolve a request by id."""
    _validate_request_id(request_id)

    selected_option_id = req.selected_option_id
    free_text = req.free_text

    if selected_option_id is None and free_text is None:
        if req.kind == "action":
            free_text = ""
        else:
            raise HTTPException(
                status_code=422,
                detail="decision requests require selected_option_id or free_text",
            )

    resolved = engine.resolve_request(request_id, selected_option_id, free_text)
    return ResolveResponse(
        request_id=resolved.request_id,
        task_id=resolved.task_id,
        kind=resolved.kind,
        title=resolved.title,
        resolved_at=resolved.resolution.resolved_at,
    )
