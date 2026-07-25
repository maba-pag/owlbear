"""Cockpit read-only API routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from owlbear_cockpit.cache import MtimeScanCache
from owlbear_cockpit.deps import get_cache, get_engine, get_view
from owlbear_cockpit.models import (
    BoardOut,
)
from owlbear_cockpit.view import CockpitView
from owlbear_kanban import KanbanEngine
from owlbear_kanban.models import (
    ActivityEvent,
    ListTasksResponse,
    SessionRecord,
    ShowTaskResponse,
)

router = APIRouter()

_Engine = Annotated[KanbanEngine, Depends(get_engine)]
_Cache = Annotated[MtimeScanCache, Depends(get_cache)]
_View = Annotated[CockpitView, Depends(get_view)]


class CockpitListTasksResponse(ListTasksResponse):
    """Cockpit envelope for GET /api/tasks with tasks-dir signature metadata."""

    mtime: int


class SessionsResponse(BaseModel):
    """Cockpit envelope for GET /api/sessions."""

    sessions: list[SessionRecord]


def _filter_cached_tasks(
    tasks: list,
    *,
    status: str,
    priority: str,
    tag: str,
    blocked: bool | None,
) -> list:
    """Apply the subset of list filters supported on the cache-hit path."""
    filtered = tasks
    if status:
        filtered = [task for task in filtered if task.status == status]
    if priority:
        filtered = [task for task in filtered if task.priority == priority]
    if tag:
        filtered = [task for task in filtered if tag in task.tags]
    if blocked is not None:
        filtered = [task for task in filtered if task.blocked is blocked]
    return filtered


@router.get("/board", response_model=BoardOut)
def get_board(engine: _Engine) -> BoardOut:
    """Return board config: statuses, priorities, and valid_transitions map."""
    config = engine.board_config()
    status_names = config.status_names
    valid_transitions = {name: sorted(engine.valid_transitions(name)) for name in status_names}
    return BoardOut(
        statuses=[{"name": s} for s in status_names],
        priorities=config.priorities,
        valid_transitions=valid_transitions,
    )


@router.get("/tasks", response_model=CockpitListTasksResponse)
def list_tasks(  # noqa: PLR0913, PLR0917
    view: _View,
    cache: _Cache,
    status: str = "",
    priority: str = "",
    tag: str = "",
    blocked: bool | None = None,  # noqa: FBT001
) -> CockpitListTasksResponse:
    """Return canonical list-tasks envelope for cockpit clients."""
    mtime = cache.scan()

    if cache.changed_since(mtime) or not cache.has_cached_tasks:
        envelope = view.list_tasks()
        cache.tasks = envelope.tasks
        cache.commit_signature(mtime)
        tasks = _filter_cached_tasks(
            cache.tasks,
            status=status,
            priority=priority,
            tag=tag,
            blocked=blocked,
        )
        return CockpitListTasksResponse(
            tasks=tasks,
            guidance=envelope.guidance,
            missing_ids=envelope.missing_ids,
            mtime=mtime,
        )

    tasks = _filter_cached_tasks(
        cache.tasks,
        status=status,
        priority=priority,
        tag=tag,
        blocked=blocked,
    )
    return CockpitListTasksResponse(
        tasks=tasks,
        guidance=[],
        missing_ids=None,
        mtime=mtime,
    )


@router.get("/tasks/{task_id}", response_model=ShowTaskResponse)
def get_task(task_id: int, view: _View) -> ShowTaskResponse:
    """Return full task detail for the given task ID, or 404 if not found."""
    return view.show_task(task_id)


@router.get("/activity", response_model=list[ActivityEvent])
def list_activity(  # noqa: PLR0913, PLR0917
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


@router.get("/sessions", response_model=SessionsResponse)
def list_sessions(view: _View, filter: str = "active") -> SessionsResponse:  # noqa: A002
    """Return work sessions, filtered by state."""
    return SessionsResponse(sessions=view.list_sessions(filter=filter))
