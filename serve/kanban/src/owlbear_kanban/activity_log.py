"""Append-only activity.jsonl logging for the native kanban engine."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def log_activity(log_path: Path, action: str, task_id: int, detail: str) -> None:
    """Append one JSON log entry to *log_path*.

    Creates the file if it does not already exist.

    Entry format::

        {"timestamp": "<ISO>", "action": "<verb>", "task_id": <int>, "detail": "<string>"}
    """
    entry = {
        "timestamp": datetime.now(tz=UTC).isoformat(),
        "action": action,
        "task_id": task_id,
        "detail": detail,
    }
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
