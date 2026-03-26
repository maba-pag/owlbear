"""Append-only JSONL store for work-in-progress summaries.

Each agent + task pair gets its own file under
``{workspace}/.owlbear/wip/{agent}_{task_id}.jsonl``.
Files are short-lived and deleted via :meth:`WipStore.clear` when no longer needed.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel

from owlbear.core.jsonl_store import JsonlStore

if TYPE_CHECKING:
    from pathlib import Path

__all__ = ["WipEntry", "WipStore"]


class WipEntry(BaseModel):
    """A single WIP checkpoint record."""

    timestamp: str
    agent: str
    task_id: str
    summary: str


class WipStore:
    """Manages per-task JSONL files for WIP summaries.

    Args:
        workspace: Root workspace directory.  Files are stored under
            ``{workspace}/.owlbear/wip/``.
    """

    def __init__(self, workspace: Path) -> None:
        self._wip_dir = workspace / ".owlbear" / "wip"

    def save(self, *, agent: str, task_id: str, summary: str) -> None:
        """Append a WIP entry for the given agent/task."""
        entry = WipEntry(
            timestamp=datetime.now(UTC).isoformat(),
            agent=agent,
            task_id=task_id,
            summary=summary,
        )
        self._store_for(agent, task_id).append(entry)

    def load(self, *, agent: str, task_id: str) -> str | None:
        """Return the most recent summary for the agent/task, or ``None``."""
        entries = self._store_for(agent, task_id).load()
        if not entries:
            return None
        return entries[-1].summary

    def clear(self, *, agent: str, task_id: str) -> None:
        """Delete the JSONL file for the given agent/task."""
        self._task_path(agent, task_id).unlink(missing_ok=True)

    # -- internals -----------------------------------------------------------

    def _task_path(self, agent: str, task_id: str) -> Path:
        """Compute the file path for a given agent/task pair."""
        return self._wip_dir / f"{agent}_{task_id}.jsonl"

    def _store_for(self, agent: str, task_id: str) -> JsonlStore[WipEntry]:
        """Create a lightweight ``JsonlStore`` for a single task file."""
        return JsonlStore(self._task_path(agent, task_id), WipEntry)
