"""Cockpit read-only API routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from owlbear_cockpit.cache import MtimeScanCache
from owlbear_cockpit.deps import get_engine
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


@router.get("/board", response_model=BoardOut)
def get_board(engine: _Engine) -> BoardOut:
    """Return board config: statuses, priorities, and valid_transitions map."""
    config = engine.board_config()
    statuses = config.statuses
    status_names = [s["name"] for s in statuses]
    valid_transitions = {
        name: sorted(engine.valid_transitions(name)) for name in status_names
    }
    return BoardOut(
        statuses=statuses,
        priorities=config.priorities,
        valid_transitions=valid_transitions,
    )


@router.get("/tasks", response_model=TaskListOut)
def list_tasks(
    engine: _Engine,
    status: str = "",
    priority: str = "",
    tag: str = "",
    blocked: bool | None = None,  # noqa: FBT001
) -> TaskListOut:
    """Return task summaries list and max mtime_ns of the tasks directory."""
    cache = MtimeScanCache(engine._tasks_dir)  # noqa: SLF001
    mtime = cache.scan()
    summaries = engine.list_tasks(
        status=status,
        priority=priority,
        tag=tag,
        blocked=blocked,
    )
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
    return TaskListOut(tasks=tasks, mtime=mtime)


@router.get("/tasks/{task_id}", response_model=TaskDetailOut)
def get_task(task_id: str, engine: _Engine) -> TaskDetailOut:
    """Return full task detail for the given task ID, or 404 if not found."""
    try:
        task = engine.show_task(task_id)
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
    sessions = engine.list_sessions(filter=filter)
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
