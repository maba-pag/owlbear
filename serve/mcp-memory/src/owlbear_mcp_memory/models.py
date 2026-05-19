"""Pydantic models for owlbear-mcp-memory."""

from __future__ import annotations

import enum
import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class MemoryCategory(enum.StrEnum):
    """Supported memory categories."""

    DOMAIN_KNOWLEDGE = "domain-knowledge"
    BEHAVIOUR = "behaviour"
    PITFALL = "pitfall"
    PROCESS = "process"
    TOOL_USAGE = "tool-usage"
    GOAL = "goal"
    PERSONALITY = "personality"
    PREFERENCE = "preference"
    ENV_CONTEXT = "env-context"


class MemoryState(enum.StrEnum):
    """Lifecycle state of a memory entry."""

    PENDING = "pending"
    CURATED = "curated"
    APPROVED = "approved"
    DELETED = "deleted"


class MemoryEntry(BaseModel):
    """A single markdown-backed memory entry."""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        use_enum_values=True,
    )

    id: str
    title: str
    categories: list[MemoryCategory] = Field(min_length=1)
    confidence: float = Field(ge=0.7, le=1.0)
    state: MemoryState = MemoryState.PENDING
    content: str
    scope_agents: list[str] = Field(default_factory=list)
    source_agent: str = Field(frozen=True)
    created_at: str
    updated_at: str
    approved_at: str | None = None

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

    @field_validator("source_agent")
    @classmethod
    def _validate_source_agent_not_blank(cls, value: str) -> str:
        if not value.strip():
            msg = "source_agent must not be empty"
            raise ValueError(msg)
        return value

    @field_validator("id")
    @classmethod
    def _validate_id_uuid_v4(cls, value: str) -> str:
        # Enforce canonical UUIDv4 string format (8-4-4-4-12 with hyphens).
        pattern = (
            r"^[0-9a-fA-F]{8}-"
            r"[0-9a-fA-F]{4}-"
            r"4[0-9a-fA-F]{3}-"
            r"[89abAB][0-9a-fA-F]{3}-"
            r"[0-9a-fA-F]{12}$"
        )
        if re.fullmatch(pattern, value) is None:
            msg = "id must be a canonical UUIDv4 string"
            raise ValueError(msg)
        return value

    @field_validator("created_at", "updated_at", "approved_at")
    @classmethod
    def _validate_iso_datetime(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if "T" not in value and "t" not in value:
            msg = "timestamp must include date and time"
            raise ValueError(msg)

        normalized = value.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError as exc:
            msg = "timestamp must be a valid ISO 8601 datetime"
            raise ValueError(msg) from exc

        if parsed.tzinfo is None or parsed.utcoffset() is None:
            msg = "timestamp must include timezone information"
            raise ValueError(msg)

        return value
