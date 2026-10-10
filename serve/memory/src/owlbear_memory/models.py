"""Pydantic data models for memory entries."""

from __future__ import annotations

import enum
import hashlib
import json
import re
from datetime import datetime
from typing import Literal

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
    CONTESTED = "contested"
    DISPUTED = "disputed"
    STALE = "stale"
    DELETED = "deleted"


class MemoryHealth(BaseModel):
    """Read-only diagnostics for markdown-backed memory storage."""

    unreadable_paths: list[str] = Field(default_factory=list)
    duplicate_paths: dict[str, list[str]] = Field(default_factory=dict)

    @property
    def healthy(self) -> bool:
        """Return whether all records are readable and UUIDs are unique."""
        return not self.unreadable_paths and not self.duplicate_paths


def validate_scope_agents(value: list[str]) -> list[str]:
    """Validate that every relevance-scope member is a nonblank string."""
    if any(not isinstance(agent, str) or not agent.strip() for agent in value):
        msg = "scope_agents must contain only non-empty strings"
        raise ValueError(msg)
    return value


class PurgePreview(BaseModel):
    """Counts from classifying deleted memories for purge."""

    deleted_total: int
    eligible: int
    too_recent: int


class PurgeResult(BaseModel):
    """Counts from a completed best-effort tombstone purge."""

    purged: int
    skipped: int
    failed: int


AssessmentBucket = Literal["outstanding", "unremarkable", "didnt_use", "factually_wrong"]


class AssessmentReceipt(BaseModel):
    """Persist the first assessment bucket for one task and content revision."""

    model_config = ConfigDict(extra="forbid")

    task_id: str = Field(pattern=r"^[\x21-\x7e]{1,128}$")
    revision: str = Field(pattern=r"^[0-9a-f]{16}$")
    bucket: AssessmentBucket


class ChallengeRecord(BaseModel):
    """Record one task's challenge to a memory revision."""

    model_config = ConfigDict(extra="forbid")

    # New task IDs are validated on write; legacy contested_by_task values were unrestricted.
    task_id: str
    revision: str = Field(pattern=r"^[0-9a-f]{16}$")
    recorded_at: str

    @field_validator("recorded_at")
    @classmethod
    def _validate_recorded_at(cls, value: str) -> str:
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


class MemoryEntry(BaseModel):
    """A single markdown-backed memory entry."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True, use_enum_values=True)

    id: str
    title: str
    content: str = Field(max_length=1024)
    categories: list[MemoryCategory] = Field(min_length=1)
    confidence: float = Field(ge=0.7, le=1.0)
    state: MemoryState = MemoryState.PENDING
    outstanding_count: int = 0
    unremarkable_count: int = 0
    didnt_use_count: int = 0
    score: float = 0.0
    scope_agents: list[str] = Field(default_factory=list)
    source_agent: str = Field(frozen=True)
    created_at: str
    updated_at: str
    approved_at: str | None = None
    challenges: list[ChallengeRecord] = Field(default_factory=list, max_length=2)
    assessment_receipts: list[AssessmentReceipt] = Field(default_factory=list)

    @property
    def revision(self) -> str:
        """Return a stable, unpersisted token for the entry's editable content."""
        serialized = json.dumps(
            {
                "title": self.title,
                "content": self.content,
                "categories": self.categories,
                "confidence": self.confidence,
                "scope_agents": self.scope_agents,
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        return hashlib.sha256(serialized).hexdigest()[:16]

    @field_validator("scope_agents")
    @classmethod
    def _validate_scope_agents(cls, value: list[str]) -> list[str]:
        return validate_scope_agents(value)

    @model_validator(mode="before")
    @classmethod
    def _drop_legacy_approval_state(cls, data: object) -> object:
        if isinstance(data, dict):
            data = dict(data)
            data.pop("approval_state", None)
            legacy_task_id = data.pop("contested_by_task", None)
            if legacy_task_id is not None and "challenges" not in data:
                legacy_entry = cls.model_validate(data)
                data["challenges"] = [
                    {
                        "task_id": legacy_task_id,
                        "revision": legacy_entry.revision,
                        "recorded_at": legacy_entry.updated_at,
                    }
                ]
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


class AssessmentResult(BaseModel):
    """Describe an applied assessment or its previously recorded receipt."""

    model_config = ConfigDict(extra="forbid")

    entry: MemoryEntry
    already_applied: bool
    recorded_bucket: AssessmentBucket
