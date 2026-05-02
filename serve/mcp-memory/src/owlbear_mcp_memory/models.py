"""Pydantic models for owlbear-mcp-memory."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MemoryCategory = Literal[
    "knowledge",
    "behaviour",
    "pitfall",
    "process",
    "tool",
    "goal",
    "personality",
    "preference",
    "context",
]
MemoryState = Literal["pending", "curated", "approved", "deleted"]


class MemoryEntry(BaseModel):
    """A single markdown-backed memory entry."""

    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    categories: list[MemoryCategory]
    confidence: float = Field(ge=0.7, le=1.0)
    state: MemoryState = "pending"
    content: str
    scope_agents: list[str] | None = None
    created_at: str
    updated_at: str
