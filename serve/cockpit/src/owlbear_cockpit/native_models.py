"""Typed Cockpit response models for native change authority."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class NativeDiagnosticResponse(BaseModel):
    """Expose stable loader diagnostics without source filesystem paths."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str
    detail: str
    target: str | None = None


class ChangeListEntryResponse(BaseModel):
    """Summarize one discoverable native change package."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    change_id: str
    state: Literal["loaded", "invalid"]
    delivery_digest: str | None = None
    diagnostics: tuple[NativeDiagnosticResponse, ...] = ()


class ChangeListResponse(BaseModel):
    """Contain identity-ordered native change summaries."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    changes: tuple[ChangeListEntryResponse, ...]


class ChangeDetailResponse(BaseModel):
    """Expose joined native authority for one admitted revision."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    change_id: str
    delivery_digest: str
    intent: str
    design: str
    decisions: dict[str, Any]
    graph: dict[str, Any]


class ChangeGraphResponse(BaseModel):
    """Expose the delivery graph with current isolated node plans."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    change_id: str
    delivery_digest: str
    graph: dict[str, Any]
    plans: dict[str, dict[str, Any]]


__all__ = [
    "ChangeDetailResponse",
    "ChangeGraphResponse",
    "ChangeListEntryResponse",
    "ChangeListResponse",
    "NativeDiagnosticResponse",
]
