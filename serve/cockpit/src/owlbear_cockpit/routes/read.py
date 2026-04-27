"""Cockpit read-only API routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from owlbear_cockpit.cache import MtimeScanCache
from owlbear_cockpit.deps import get_cache, get_engine, get_view
from owlbear_cockpit.models import (
    BoardOut,
)
from owlbear_kanban import KanbanEngine
from owlbear_kanban.engine import CockpitView
from owlbear_kanban.errors import NotFoundError
from owlbear_kanban.models import ActivityEvent, ListTasksResponse, SessionRecord, ShowTaskResponse

router = APIRouter()

_Engine = Annotated[KanbanEngine, Depends(get_engine)]
_Cache = Annotated[MtimeScanCache, Depends(get_cache)]
_View = Annotated[CockpitView, Depends(get_view)]


class CockpitListTasksResponse(ListTasksResponse):
    """Cockpit envelope for GET /api/tasks with tasks-dir mtime metadata."""

    mtime: int


@router.get("/board", response_model=BoardOut)
def get_board(engine: _Engine) -> BoardOut:
    """Return board config: statuses, priorities, and valid_transitions map."""
    config = engine.board_config()
    status_names = config.status_names
    valid_transitions = {
        name: sorted(engine.valid_transitions(name)) for name in status_names
    }
    return BoardOut(
        statuses=[{"name": s} for s in status_names],
        priorities=config.priorities,
        valid_transitions=valid_transitions,
    )


@router.get("/tasks", response_model=CockpitListTasksResponse)
def list_tasks(  # noqa: PLR0913
    view: _View,
    cache: _Cache,
    status: str = "",
    priority: str = "",
    tag: str = "",
    blocked: bool | None = None,  # noqa: FBT001
) -> CockpitListTasksResponse:
    """Return canonical list-tasks envelope for cockpit clients."""
    envelope = view.list_tasks(
        status=status,
        priority=priority,
        tag=tag,
        blocked=blocked,
    )
    payload = envelope.model_dump()
    payload["mtime"] = cache.scan()
    return CockpitListTasksResponse.model_validate(payload)


@router.get("/tasks/{task_id}", response_model=ShowTaskResponse)
def get_task(task_id: int, view: _View) -> ShowTaskResponse:
    """Return full task detail for the given task ID, or 404 if not found."""
    try:
        return view.show_task(task_id)
    except NotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Task {task_id!r} not found"
        ) from None


@router.get("/activity", response_model=list[ActivityEvent])
def list_activity(  # noqa: PLR0913
    view: _View,
    task_id: int | None = None,
    action: str | None = None,
    source: str | None = None,
    since: str | None = None,
    until: str | None = None,
    limit: int | None = None,
) -> list[ActivityEvent]:
    """Return activity events with optional filters."""
    return view.list_activity(
        task_id=task_id,
        action=action,
        source=source,
        since=since,
        until=until,
        limit=limit,
    )


@router.get("/sessions", response_model=list[SessionRecord])
def list_sessions(view: _View, filter: str = "active") -> list[SessionRecord]:  # noqa: A002
    """Return work sessions, filtered by state."""
    return view.list_sessions(filter=filter)
