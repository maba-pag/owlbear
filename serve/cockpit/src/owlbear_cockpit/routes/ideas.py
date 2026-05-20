"""Ideas API routes for reading and persisting shared markdown content."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel, ConfigDict

from owlbear_cockpit.deps import get_ideas_path
from owlbear_kanban.storage_io import atomic_write

router = APIRouter()

_IdeasPath = Annotated[Path, Depends(get_ideas_path)]


class IdeasResponse(BaseModel):
    """Response payload for GET /ideas."""

    content: str


class IdeasUpdateRequest(BaseModel):
    """Request payload for PUT /ideas."""

    model_config = ConfigDict(extra="forbid")

    content: str


@router.get("/ideas", response_model=IdeasResponse)
def get_ideas(ideas_path: _IdeasPath) -> IdeasResponse:
    """Return the current shared ideas markdown, or empty content when absent."""
    try:
        content = ideas_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        content = ""
    return IdeasResponse(content=content)


@router.put("/ideas", status_code=status.HTTP_204_NO_CONTENT)
def put_ideas(req: IdeasUpdateRequest, ideas_path: _IdeasPath) -> Response:
    """Persist shared ideas markdown using atomic write semantics."""
    atomic_write(ideas_path, req.content)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
