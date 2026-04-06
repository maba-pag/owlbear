"""Pydantic models for owlbear-mcp-memory."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class MemoryEntry(BaseModel):
    """A single memory entry stored in the memory database."""

    model_config = ConfigDict()

    id: str
    content: str
    category: Literal["preference", "knowledge", "context", "behavior", "goal"]
    confidence: float
    created_at: str
    updated_at: str
    source: str
    scope_agent: str | None = None
    scope_project: str | None = None
    approval_state: Literal["pending", "approved", "deleted"] = "pending"
    deleted_at: str | None = None
