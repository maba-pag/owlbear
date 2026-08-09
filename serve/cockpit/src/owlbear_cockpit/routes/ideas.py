"""Ideas API routes for reading and persisting shared markdown content."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from owlbear_cockpit.deps import get_ideas_path
from owlbear_delivery.storage_io import atomic_write

router = APIRouter()

_IdeasPath = Annotated[Path, Depends(get_ideas_path)]


class IdeasResponse(BaseModel):
    """Response payload for GET /ideas."""

    content: str
    updated_at: str | None = None


class IdeasUpdateRequest(BaseModel):
    """Request payload for PUT /ideas."""

    model_config = ConfigDict(extra="forbid")

    content: str
    expected_updated_at: str | None = None
    force: bool = False


def _ideas_updated_at(ideas_path: Path) -> str | None:
    try:
        mtime = ideas_path.stat().st_mtime
    except FileNotFoundError:
        return None
    return datetime.fromtimestamp(mtime, tz=UTC).isoformat()


@router.get("/ideas", response_model=IdeasResponse)
def get_ideas(ideas_path: _IdeasPath) -> IdeasResponse:
    """Return the current shared ideas markdown, or empty content when absent."""
    try:
        content = ideas_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        content = ""
    return IdeasResponse(content=content, updated_at=_ideas_updated_at(ideas_path))


def _read_ideas_content(ideas_path: Path) -> str:
    try:
        return ideas_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


@router.put("/ideas", status_code=status.HTTP_204_NO_CONTENT)
def put_ideas(req: IdeasUpdateRequest, ideas_path: _IdeasPath) -> Response:
    """Persist shared ideas markdown using atomic write semantics."""
    current_updated_at = _ideas_updated_at(ideas_path)
    if (
        not req.force
        and "expected_updated_at" in req.model_fields_set
        and req.expected_updated_at != current_updated_at
    ):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "code": "IDEAS_CONFLICT",
                "message": "Ideas file changed on disk.",
                "content": _read_ideas_content(ideas_path),
                "updated_at": current_updated_at,
            },
        )

    atomic_write(ideas_path, req.content)
    updated_at = _ideas_updated_at(ideas_path)
    headers = {"X-Ideas-Updated-At": updated_at} if updated_at else None
    return Response(status_code=status.HTTP_204_NO_CONTENT, headers=headers)
