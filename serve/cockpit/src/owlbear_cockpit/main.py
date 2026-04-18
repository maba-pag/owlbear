"""Cockpit FastAPI application."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException

from owlbear_kanban import KanbanEngine

app = FastAPI(title="OwlBear Cockpit")


def get_engine() -> KanbanEngine:
    """FastAPI dependency — returns a board engine from OWLBEAR_KANBAN_DIR."""
    kanban_dir = Path(os.environ.get("OWLBEAR_KANBAN_DIR", "."))
    return KanbanEngine(kanban_dir)


_Engine = Annotated[KanbanEngine, Depends(get_engine)]


@app.get("/health")
def health() -> dict[str, str]:
    """Return service health status."""
    return {"status": "ok"}


@app.get("/api/board")
def board(engine: _Engine) -> dict:
    """Return board config: statuses, priorities, and valid_transitions map."""
    config = engine.board_config()
    valid_transitions = {
        s["name"]: sorted(engine.valid_transitions(s["name"]))
        for s in config.statuses
    }
    return {
        "statuses": config.statuses,
        "priorities": config.priorities,
        "valid_transitions": valid_transitions,
    }


@app.get("/api/tasks")
def list_tasks(
    engine: _Engine,
    status: str = "",
    priority: str = "",
    tag: str = "",
    blocked: str = "",
) -> dict:
    """Return TaskSummary list and tasks-dir mtime (nanoseconds)."""
    blocked_filter: bool | None = None
    if blocked.lower() == "true":
        blocked_filter = True
    elif blocked.lower() == "false":
        blocked_filter = False

    tasks = engine.list_tasks(
        status=status,
        priority=priority,
        tag=tag,
        blocked=blocked_filter,
    )

    tasks_dir: Path = engine._tasks_dir  # noqa: SLF001
    try:
        mtime = max(
            (f.stat().st_mtime_ns for f in tasks_dir.iterdir()),
            default=0,
        )
    except FileNotFoundError:
        mtime = 0

    return {"tasks": [t.model_dump() for t in tasks], "mtime": mtime}


@app.get("/api/tasks/{task_id}")
def get_task(task_id: str, engine: _Engine) -> dict:
    """Return full Task for task_id; 404 if not found."""
    try:
        task = engine.show_task(task_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Task {task_id!r} not found") from None
    return task.model_dump()


@app.get("/api/sessions")
def list_sessions(engine: _Engine, filter: str = "active") -> dict:  # noqa: A002
    """Return sessions list filtered by filter param (default: active)."""
    sessions = engine.list_sessions(filter=filter)
    return {"sessions": [{"task_id": s.task_id, "state": s.state} for s in sessions]}
