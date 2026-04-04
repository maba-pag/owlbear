"""Pydantic models for kanban-md task data at the MCP protocol boundary."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class KanbanTask(BaseModel):
    """Represents a single kanban task as returned by kanban-md --json."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    # Required fields
    id: int
    title: str
    status: str
    priority: str
    created: str
    updated: str

    # Optional fields
    claimed: bool = False
    tags: list[str] = Field(default_factory=list)
    parent: int | None = None
    depends_on: list[int] = Field(default_factory=list)
    blocked: bool = False
    block_reason: str | None = None
    body: str | None = None
    file: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _coerce_claimed(cls, data: dict[str, object]) -> dict[str, object]:
        """Convert kanban-md's claimed_by string to a boolean claimed flag."""
        if isinstance(data, dict) and "claimed_by" in data:
            data["claimed"] = data.pop("claimed_by") is not None
        return data
