"""Cockpit read-only API routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from owlbear_cockpit import adapter
from owlbear_cockpit.cache import MtimeScanCache
from owlbear_cockpit.deps import get_cache, get_engine
from owlbear_cockpit.models import (
    BoardOut,
    SessionListOut,
    SessionOut,
    TaskDetailOut,
    TaskListOut,
    TaskSummaryOut,
)
from owlbear_kanban import KanbanEngine

router = APIRouter()

_Engine = Annotated[KanbanEngine, Depends(get_engine)]
_Cache = Annotated[MtimeScanCache, Depends(get_cache)]


@router.get("/board", response_model=BoardOut)
def get_board(engine: _Engine) -> BoardOut:
    """Return board config: statuses, priorities, and valid_transitions map."""
    config = adapter.board_config(engine)
    statuses = config.statuses
    status_names = [s["name"] for s in statuses]
    valid_transitions = {name: sorted(adapter.valid_transitions(engine, name)) for name in status_names}
    return BoardOut(
        statuses=statuses,
        priorities=config.priorities,
        valid_transitions=valid_transitions,
    )


@router.get("/tasks", response_model=TaskListOut)
def list_tasks(  # noqa: PLR0913
    engine: _Engine,
    cache: _Cache,
    status: str = "",
    priority: str = "",
    tag: str = "",
    blocked: bool | None = None,  # noqa: FBT001
) -> TaskListOut:
    """Return task summaries list and max mtime_ns of the tasks directory.

    Uses a per-engine mtime cache: engine.list_tasks() is only called when the
    tasks directory has changed since the last request (cache miss).  On a cache
    hit the previously fetched task list is returned without touching the engine.
    Filtering is applied in Python after the cache look-up so that different
    filter combinations still benefit from the same cached full task list.
    """
    if cache.has_changed():
        cache.tasks = adapter.list_tasks(engine)

    summaries = cache.tasks
    if status:
        summaries = [s for s in summaries if s.status == status]
    if priority:
        summaries = [s for s in summaries if s.priority == priority]
    if tag:
        summaries = [s for s in summaries if tag in (s.tags or [])]
    if blocked is not None:
        summaries = [s for s in summaries if s.blocked == blocked]

    tasks = [
        TaskSummaryOut(
            id=s.id,
            title=s.title,
            status=s.status,
            priority=s.priority,
            tags=s.tags,
            blocked=s.blocked,
        )
        for s in summaries
    ]
    return TaskListOut(tasks=tasks, mtime=cache.last_mtime)


@router.get("/tasks/{task_id}", response_model=TaskDetailOut)
def get_task(task_id: str, engine: _Engine) -> TaskDetailOut:
    """Return full task detail for the given task ID, or 404 if not found."""
    try:
        task = adapter.show_task(engine, task_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Task {task_id!r} not found") from None
    return TaskDetailOut(
        id=task.id,
        title=task.title,
        status=task.status,
        priority=task.priority,
        body=task.body,
        updated=task.updated,
        created=task.created,
        tags=task.tags,
        blocked=task.blocked,
        block_reason=task.block_reason,
        parent=task.parent,
        depends_on=task.depends_on,
    )


@router.get("/sessions", response_model=SessionListOut)
def list_sessions(engine: _Engine, filter: str = "active") -> SessionListOut:  # noqa: A002
    """Return work sessions, filtered by state."""
    sessions = adapter.list_sessions(engine, filter=filter)
    return SessionListOut(
        sessions=[
            SessionOut(
                task_id=s.task_id,
                state=s.state,
                agent=s.agent,
                started_at=s.started_at,
                duration=s.duration,
                outcome=s.outcome,
            )
            for s in sessions
        ]
    )
