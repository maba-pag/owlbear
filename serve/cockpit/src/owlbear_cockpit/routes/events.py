"""Cockpit SSE routes for task-list invalidation events."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sse_starlette import EventSourceResponse
from watchfiles import awatch

from owlbear_cockpit.deps import get_engine
from owlbear_kanban import KanbanEngine

router = APIRouter()

_Engine = Annotated[KanbanEngine, Depends(get_engine)]


def _watch_filter(_change: object, path: str) -> bool:
    """Accept only task markdown files and ignore temporary write artifacts."""
    name = Path(path).name
    return name.endswith(".md") and not name.startswith(".tmp-")


@router.get("/events")
async def events(request: Request, engine: _Engine) -> EventSourceResponse:
    """Stream task invalidation events to clients via SSE."""

    async def _stream() -> object:
        tasks_dir = Path(engine.tasks_dir)
        if not tasks_dir.exists():  # noqa: ASYNC240
            return

        async for changes in awatch(
            tasks_dir,
            watch_filter=_watch_filter,
            recursive=False,
            yield_on_timeout=True,
            rust_timeout=100,
        ):
            if await request.is_disconnected():
                break

            if not changes:
                break

            latest_mtime: int | None = None
            for _change, changed_path in changes:
                try:
                    mtime = Path(changed_path).stat().st_mtime_ns  # noqa: ASYNC240
                except FileNotFoundError:
                    continue
                latest_mtime = mtime if latest_mtime is None else max(latest_mtime, mtime)

            if latest_mtime is None:
                continue

            yield {
                "event": "tasks-changed",
                "data": json.dumps({"mtime": latest_mtime}),
            }

    return EventSourceResponse(_stream(), ping=1)
