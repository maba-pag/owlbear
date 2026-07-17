"""Pydantic response model for the cockpit GET /api/board endpoint."""

from __future__ import annotations

from pydantic import BaseModel, Field


class BoardOut(BaseModel):
    """Board configuration response model."""

    statuses: list[dict]
    priorities: list[str]
    valid_transitions: dict[str, list[str]]


class HealthModule(BaseModel):
    """Typed health evidence for one Cockpit workspace module."""

    status: str
    findings: list[dict] = Field(default_factory=list)
    checked_paths: list[str] = Field(default_factory=list)


class IdeasHealth(BaseModel):
    """Integrity evidence for the shared ideas markdown file."""

    status: str
    path: str
    detail: str | None = None


class WorkspaceHealth(BaseModel):
    """Aggregate workspace health response."""

    status: str
    modules: dict[str, HealthModule | IdeasHealth]
