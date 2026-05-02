"""Pydantic models for owlbear-mcp-memory."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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
    categories: list[MemoryCategory] = Field(min_length=1)
    confidence: float = Field(ge=0.7, le=1.0)
    state: MemoryState = "pending"
    content: str
    scope_agents: list[str] | None = None
    created_at: str
    updated_at: str

    @model_validator(mode="before")
    @classmethod
    def _drop_legacy_approval_state(cls, data: object) -> object:
        if isinstance(data, dict):
            data = dict(data)
            data.pop("approval_state", None)
        return data

    @field_validator("title")
    @classmethod
    def _validate_title_not_blank(cls, value: str) -> str:
        if not value.strip():
            msg = "title must not be empty"
            raise ValueError(msg)
        return value
