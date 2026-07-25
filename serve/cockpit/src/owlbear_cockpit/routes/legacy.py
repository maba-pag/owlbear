"""Bounded read-only inventory of pre-native Cockpit stores."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict

from owlbear_cockpit.deps import get_engine
from owlbear_kanban import KanbanEngine
from owlbear_kanban.models import ActivityEvent, TaskSummary
from owlbear_kanban.request_models import RequestRecord

router = APIRouter(tags=["legacy-inventory"])
_Engine = Annotated[KanbanEngine, Depends(get_engine)]
_Limit = Annotated[int, Query(ge=1, le=100)]


class LegacyTaskEntry(BaseModel):
    """One legacy task summary with its source-store provenance."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    provenance: Literal["tasks", "archive"]
    task: TaskSummary


class LegacyRequestEntry(BaseModel):
    """One legacy request with its source-store provenance."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    provenance: Literal["decisions/pending", "decisions/resolved"]
    request: RequestRecord


class LegacyActivityEntry(BaseModel):
    """One legacy activity event with its source-store provenance."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    provenance: Literal["activity.jsonl"] = "activity.jsonl"
    event: ActivityEvent


class LegacyInventoryResponse(BaseModel):
    """Bounded inventory with explicit truncation state and no mutation links."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    tasks: tuple[LegacyTaskEntry, ...]
    requests: tuple[LegacyRequestEntry, ...]
    activity: tuple[LegacyActivityEntry, ...]
    truncated: dict[Literal["tasks", "requests", "activity"], bool]


@router.get("/legacy", response_model=LegacyInventoryResponse)
def legacy_inventory(engine: _Engine, limit: _Limit = 100) -> LegacyInventoryResponse:
    """Return capped legacy task, request, and activity records without mutation affordances."""
    active = engine.list_tasks(sort="id")
    archived = engine.list_tasks(archived=True, sort="id")
    pending = engine.list_requests(status="pending")
    resolved = engine.list_requests(status="resolved")
    activity = engine.list_activity()
    tasks = tuple(
        [
            *(LegacyTaskEntry(provenance="tasks", task=item) for item in active),
            *(LegacyTaskEntry(provenance="archive", task=item) for item in archived),
        ][:limit]
    )
    requests = tuple(
        [
            *(LegacyRequestEntry(provenance="decisions/pending", request=item) for item in pending),
            *(LegacyRequestEntry(provenance="decisions/resolved", request=item) for item in resolved),
        ][:limit]
    )
    return LegacyInventoryResponse(
        tasks=tasks,
        requests=requests,
        activity=tuple(LegacyActivityEntry(event=item) for item in activity[-limit:]),
        truncated={
            "tasks": len(active) + len(archived) > limit,
            "requests": len(pending) + len(resolved) > limit,
            "activity": len(activity) > limit,
        },
    )


__all__ = ["router"]
