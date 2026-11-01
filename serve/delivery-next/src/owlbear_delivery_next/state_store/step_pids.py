"""The processes a Change's runner recorded, kept beside its capped activity log so none is evicted (#752).

The host finds a step's processes that run in sessions of their own (remote Git, installs) only by these records.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

FILE = "pids"


def kept(folder: Path, event: dict[str, Any]) -> None:
    """Append a ``pids`` event to the Change's file, which the activity log's cap never trims."""
    with (folder / FILE).open("a", encoding="utf-8") as out:
        out.write(json.dumps(event, default=str, sort_keys=True) + "\n")


def recorded(folder: Path, since: datetime) -> dict[int, float | None]:
    """Each PID recorded from a second before *since* on, with its start time.

    Raises:
        OSError: The file exists but cannot be read.
        ValueError: A line is not a ``pids`` event.
    """
    try:
        text = (folder / FILE).read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
    pids: dict[int, float | None] = {}
    for line in text.splitlines():
        try:
            event = json.loads(line)
            if datetime.fromisoformat(event["at"]) >= since - timedelta(seconds=1):
                pids |= {int(p): t for p, t in event["pids"].items()}
        except (KeyError, TypeError, AttributeError) as exc:
            msg = f"a line of {FILE} is not a pids event: {exc!r}"
            raise ValueError(msg) from exc
    return pids
