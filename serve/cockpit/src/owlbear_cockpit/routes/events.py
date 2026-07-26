"""Cockpit SSE invalidation events for canonical native resources."""

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
_AUTHORITY_RESOURCES = {
    "delivery": "changes",
    "plans": "graphs",
    "receipts": "receipts",
}
_WORK_RESOURCES = {
    "jobs": "jobs",
    "attempts": "attempts",
    "findings": "findings",
    "requests": "requests",
}
_CHANGE_FILE_DEPTH = 2
_CHANGE_RESOURCE_DEPTH = 3


def _resolve(path: Path | str) -> Path:
    """Normalize a path without requiring it to exist on disk."""
    return Path(path).resolve(strict=False)


def _relative(path: Path, root: Path) -> Path | None:
    try:
        return path.relative_to(root)
    except ValueError:
        return None


def _is_temporary(relative: Path) -> bool:
    return any(part.startswith(".") for part in relative.parts) or relative.name.endswith((".tmp", "~"))


def _classify_native_path(changed_path: Path, changes_root: Path, work_root: Path) -> str | None:
    """Map one canonical authority or work path to its resource class."""
    authority = _relative(changed_path, changes_root)
    if authority is not None and authority.parts and not _is_temporary(authority):
        if len(authority.parts) >= _CHANGE_RESOURCE_DEPTH and authority.parts[1] in _AUTHORITY_RESOURCES:
            return _AUTHORITY_RESOURCES[authority.parts[1]]
        if len(authority.parts) == _CHANGE_FILE_DEPTH and authority.suffix in {".md", ".yaml"}:
            return "changes"

    work = _relative(changed_path, work_root)
    if work is not None and work.parts and not _is_temporary(work):
        return _WORK_RESOURCES.get(work.parts[0])
    return None


def _build_watch_filter(
    changes_root: Path,
    work_root: Path,
) -> callable:
    """Build a filter that suppresses legacy stores and transaction noise."""
    changes_root = _resolve(changes_root)
    work_root = _resolve(work_root)

    def _watch_filter(_change: object, path: str) -> bool:
        return _classify_native_path(_resolve(path), changes_root, work_root) is not None

    return _watch_filter


def _batch_resources(
    changes: set[tuple[object, str]],
    changes_root: Path,
    work_root: Path,
) -> tuple[str, ...]:
    """Return sorted unique resource classes affected by one watch batch."""
    resources = {
        resource
        for _change, path in changes
        if (resource := _classify_native_path(_resolve(path), changes_root, work_root)) is not None
    }
    return tuple(sorted(resources))


def _next_token(previous: int) -> int:
    """Return a process-local token that is strictly monotonic."""
    return max(time.time_ns(), previous + 1)


@router.get("/events")
async def events(request: Request, engine: _Engine) -> EventSourceResponse:
    """Stream one native invalidation event for each canonical watch batch."""

    async def _stream() -> object:
        work_root = _resolve(engine.kanban_dir)
        ops_root = work_root.parent
        changes_root = _resolve(ops_root / "changes")
        if not ops_root.is_dir() or not work_root.is_dir() or not changes_root.is_dir():
            return

        token = 0

        async for changes in awatch(
            ops_root,
            watch_filter=_build_watch_filter(changes_root, work_root),
            recursive=True,
            yield_on_timeout=True,
            rust_timeout=100,
        ):
            if await request.is_disconnected():
                break

            resources = _batch_resources(changes, changes_root, work_root)
            if not resources:
                continue
            token = _next_token(token)
            yield {
                "event": "native-changed",
                "data": json.dumps({"resources": resources, "token": str(token)}),
            }

    return EventSourceResponse(_stream(), ping=1)


__all__ = ["router"]
