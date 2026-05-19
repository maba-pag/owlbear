"""Memory management routes for cockpit API."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends
from owlbear_memory.models import MemoryCategory, MemoryEntry, MemoryState  # noqa: TC002
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from owlbear_cockpit.deps import get_memory_engine

if TYPE_CHECKING:
    from owlbear_memory.engine import EditPayload

router = APIRouter()


class MemoryEntryResponse(BaseModel):
    """Serialized memory entry returned by cockpit API."""

    id: str
    title: str
    content: str
    categories: list[MemoryCategory]
    confidence: float
    state: MemoryState
    scope_agents: list[str]
    source_agent: str
    created_at: str
    updated_at: str
    approved_at: str | None


class MemoriesResponse(BaseModel):
    """Response body for listing memory entries."""

    entries: list[MemoryEntryResponse]
    parse_errors: int


class MemoryEntryEnvelope(BaseModel):
    """Single-entry mutation response wrapper."""

    entry: MemoryEntryResponse


class ApproveRequest(BaseModel):
    """Request body for approving a memory entry with OCC."""

    model_config = ConfigDict(extra="forbid")

    expected_updated_at: str


class EditRequest(BaseModel):
    """Request body for editing allowed memory fields with OCC."""

    model_config = ConfigDict(extra="forbid")

    expected_updated_at: str
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] | None = None
    content: Annotated[str, Field(max_length=1024)] | None = None
    categories: Annotated[list[MemoryCategory], Field(min_length=1)] | None = None
    confidence: Annotated[float, Field(ge=0.7, le=1.0)] | None = None
    scope_agents: list[str] | None = None


class DeleteRequest(BaseModel):
    """Request body for deleting a memory entry with OCC."""

    model_config = ConfigDict(extra="forbid")

    expected_updated_at: str


class DeleteResponse(BaseModel):
    """Success response for delete mutation."""

    success: bool


def _to_response(entry: MemoryEntry) -> MemoryEntryResponse:
    return MemoryEntryResponse.model_validate(entry.model_dump())


@router.get("/memories", response_model=MemoriesResponse)
def list_memories(engine=Depends(get_memory_engine)) -> MemoriesResponse:  # noqa: ANN001, B008
    """Return memory entries and parse error count."""
    entries = [_to_response(entry) for entry in engine.get_entries()]
    return MemoriesResponse(entries=entries, parse_errors=engine.parse_errors)


@router.post("/memories/{entry_id}/approve", response_model=MemoryEntryEnvelope)
def approve_memory(
    entry_id: str,
    req: ApproveRequest,
    engine=Depends(get_memory_engine),  # noqa: ANN001, B008
) -> MemoryEntryEnvelope:
    """Approve one curated entry using optimistic concurrency token."""
    entry = engine.approve(entry_id, req.expected_updated_at)
    return MemoryEntryEnvelope(entry=_to_response(entry))


@router.post("/memories/{entry_id}/edit", response_model=MemoryEntryEnvelope)
def edit_memory(
    entry_id: str,
    req: EditRequest,
    engine=Depends(get_memory_engine),  # noqa: ANN001, B008
) -> MemoryEntryEnvelope:
    """Edit allowlisted fields on one entry using optimistic concurrency token."""
    fields: EditPayload = {}
    if "title" in req.model_fields_set and req.title is not None:
        fields["title"] = req.title
    if "content" in req.model_fields_set and req.content is not None:
        fields["content"] = req.content
    if "categories" in req.model_fields_set and req.categories is not None:
        fields["categories"] = req.categories
    if "confidence" in req.model_fields_set and req.confidence is not None:
        fields["confidence"] = req.confidence
    if "scope_agents" in req.model_fields_set and req.scope_agents is not None:
        fields["scope_agents"] = req.scope_agents

    entry = engine.edit(entry_id, fields, req.expected_updated_at)
    return MemoryEntryEnvelope(entry=_to_response(entry))


@router.post("/memories/{entry_id}/delete", response_model=DeleteResponse)
def delete_memory(
    entry_id: str,
    req: DeleteRequest,
    engine=Depends(get_memory_engine),  # noqa: ANN001, B008
) -> DeleteResponse:
    """Delete one entry using optimistic concurrency token."""
    engine.delete(entry_id, req.expected_updated_at)
    return DeleteResponse(success=True)
