"""The chats follower's offsets (Improvement design §4): where each chat was read to, for the next run's gap record.

A restart records each chat's bytes written while OwlBear was not following them as a gap, never looked at
(D-01M5XCE8ZA4FGYYY45YP44M8RD), from the offsets the last run left in ``~/.owlbear/spotter/chats.json``.
"""

from __future__ import annotations

import contextlib
import json
import os
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from owlbear_delivery_next.improvement import spotter

STATE = "chats.json"


def load() -> dict[str, Any]:
    """The last run's offsets by chat; none when unreadable."""
    with contextlib.suppress(OSError, ValueError):
        got = json.loads((spotter.place() / STATE).read_text())
        if isinstance(got, dict):
            return {k: v for k, v in got.items() if isinstance(v, dict)}
    return {}


def save(now: dict[str, Any]) -> bool:
    """Replace the offsets with *now*; whether they were written. A failure loses only the next gap record's bounds."""
    with contextlib.suppress(OSError):
        folder = spotter.root()
        fd, tmp = tempfile.mkstemp(dir=folder, prefix=".chats-")
        try:
            with os.fdopen(fd, "w") as out:
                json.dump(now, out)
            Path(tmp).replace(folder / STATE)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise
        return True
    return False


def gap(cid: str, why: str) -> None:
    """Record that chat *cid*'s bytes were not looked at, and *why*."""
    record = spotter.Record(
        id=uuid.uuid4().hex[:12], at=datetime.now(UTC).isoformat(timespec="seconds"), project="", change="",
        step="chat", session=cid, look="gap", call="", cutoff=0, probability=0.0, skipped=why,
    )  # fmt: skip
    spotter.WORK.submit(spotter.store, spotter.place(), record, None)
