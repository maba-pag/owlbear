"""Pydantic event models for orchestrator audit log."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter


class DispatchEvent(BaseModel):
    """Audit event recorded when a task is dispatched to an agent."""

    model_config = ConfigDict(frozen=True)

    type: Literal["dispatch"] = "dispatch"
    timestamp: str
    task_id: int
    agent: str
    prompt_summary: str = Field(max_length=100)
    session_id: str
    cycle_id: str = ""


class CompletionEvent(BaseModel):
    """Audit event recorded when an agent completes a task."""

    model_config = ConfigDict(frozen=True)

    type: Literal["completion"] = "completion"
    timestamp: str
    task_id: int
    agent: str
    outcome: Literal["success", "failure"]
    duration_ms: int
    files_changed: list[str]
    error: str | None = None
    cycle_id: str = ""


AuditEvent = Annotated[DispatchEvent | CompletionEvent, Field(discriminator="type")]

audit_adapter: TypeAdapter[DispatchEvent | CompletionEvent] = TypeAdapter(AuditEvent)
