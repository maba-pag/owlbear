"""Cockpit SSE routes for kanban surface invalidation events."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sse_starlette import EventSourceResponse
from watchfiles import awatch

from owlbear_cockpit.deps import get_engine
from owlbear_kanban import KanbanEngine

router = APIRouter()

_Engine = Annotated[KanbanEngine, Depends(get_engine)]


def _resolve(path: Path | str) -> Path:
    """Normalize a path without requiring it to exist on disk."""
    return Path(path).resolve(strict=False)


def _is_direct_md(path: Path, parent_dir: Path) -> bool:
    """Return True for direct child markdown files only."""
    try:
        relative = path.relative_to(parent_dir)
    except ValueError:
        return False
    return len(relative.parts) == 1 and relative.suffix == ".md"


def _build_watch_filter(
    tasks_dir: Path,
    archive_dir: Path,
    decisions_pending_dir: Path,
    activity_path: Path,
) -> callable:
    """Build a board-specific watch filter for tasks, decisions, and activity."""
    tasks_dir_r = _resolve(tasks_dir)
    archive_dir_r = _resolve(archive_dir)
    decisions_pending_dir_r = _resolve(decisions_pending_dir)
    activity_path_r = _resolve(activity_path)

    def _watch_filter(_change: object, path: str) -> bool:
        candidate = _resolve(path)
        name = candidate.name
        if candidate == activity_path_r:
            return True
        if name.startswith(".tmp-"):
            return False
        return (
            _is_direct_md(candidate, tasks_dir_r)
            or _is_direct_md(candidate, archive_dir_r)
            or _is_direct_md(candidate, decisions_pending_dir_r)
        )

    return _watch_filter


def _classify_path(
    changed_path: Path,
    tasks_dir: Path,
    archive_dir: Path,
    decisions_pending_dir: Path,
    activity_path: Path,
) -> str | None:
    """Map a changed path to its typed SSE event or None."""
    if changed_path == activity_path:
        return "activity-changed"
    if _is_direct_md(changed_path, tasks_dir) or _is_direct_md(changed_path, archive_dir):
        return "tasks-changed"
    if _is_direct_md(changed_path, decisions_pending_dir):
        return "decisions-changed"
    return None


def _batch_latest_mtimes(
    changes: set[tuple[object, str]],
    *,
    tasks_dir: Path,
    archive_dir: Path,
    decisions_pending_dir: Path,
    activity_path: Path,
) -> dict[str, int]:
    """Return the latest mtime per event type from one watch batch."""
    latest_mtimes: dict[str, int] = {}
    for _change, changed_path in changes:
        changed_path_obj = _resolve(changed_path)
        event_name = _classify_path(
            changed_path_obj,
            tasks_dir,
            archive_dir,
            decisions_pending_dir,
            activity_path,
        )
        if event_name is None:
            continue

        try:
            mtime = changed_path_obj.stat().st_mtime_ns
        except FileNotFoundError:
            mtime = time.time_ns()
        latest_mtimes[event_name] = max(latest_mtimes.get(event_name, 0), mtime)
    return latest_mtimes


def _next_event_mtime(
    event_name: str,
    candidate_mtime: int,
    *,
    last_emitted_mtimes: dict[str, int],
) -> int:
    """Return an event mtime guaranteed to differ from the last emitted value."""
    previous = last_emitted_mtimes.get(event_name, 0)
    if candidate_mtime <= previous:
        return previous + 1
    return candidate_mtime


@router.get("/events")
async def events(request: Request, engine: _Engine) -> EventSourceResponse:
    """Stream typed kanban invalidation events to clients via SSE."""

    async def _stream() -> object:
        kanban_dir = _resolve(engine.kanban_dir)
        if not kanban_dir.exists():
            return

        tasks_dir = _resolve(engine.tasks_dir)
        archive_dir = _resolve(engine.archive_dir)
        decisions_pending_dir = _resolve(kanban_dir / "decisions" / "pending")
        activity_path = _resolve(kanban_dir / "activity.jsonl")
        watch_filter = _build_watch_filter(
            tasks_dir,
            archive_dir,
            decisions_pending_dir,
            activity_path,
        )
        last_emitted_mtimes: dict[str, int] = {}

        async for changes in awatch(
            kanban_dir,
            watch_filter=watch_filter,
            recursive=True,
            yield_on_timeout=True,
            rust_timeout=100,
        ):
            if await request.is_disconnected():
                break

            if not changes:
                continue

            latest_mtimes = _batch_latest_mtimes(
                changes,
                tasks_dir=tasks_dir,
                archive_dir=archive_dir,
                decisions_pending_dir=decisions_pending_dir,
                activity_path=activity_path,
            )

            for event_name, candidate_mtime in latest_mtimes.items():
                emitted_mtime = _next_event_mtime(
                    event_name,
                    candidate_mtime,
                    last_emitted_mtimes=last_emitted_mtimes,
                )
                last_emitted_mtimes[event_name] = emitted_mtime
                yield {
                    "event": event_name,
                    "data": json.dumps({"mtime": emitted_mtime}),
                }

    return EventSourceResponse(_stream(), ping=1)
