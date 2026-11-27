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
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.improvement import spotter

if TYPE_CHECKING:
    from collections.abc import Iterable

    from owlbear_delivery_next.machine_host.chats import Chat

STATE = "chats.json"


def load() -> dict[str, Any] | None:
    """The last run's offsets by chat; None if there is no readable record of a previous run."""
    with contextlib.suppress(OSError, ValueError):
        got = json.loads((spotter.place() / STATE).read_text())
        if isinstance(got, dict):
            return {k: v for k, v in got.items() if isinstance(v, dict)}
    return None


def save(chats: Iterable[Chat], saved: dict[str, Any] | None) -> dict[str, Any] | None:
    """Keep each of *chats*' offset, including an empty set for a run that followed no chats.

    Return the offsets kept now. A failure leaves *saved* unchanged.
    """
    now = {c.id: {"offset": max(c.offset, c.history), "file": list(c.file)} for c in chats}
    if now == saved:
        return saved
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
        return now
    return saved


def missed(cid: str, old: dict[str, Any] | None, start: int, file: tuple[int, int]) -> None:
    """Record what chat *cid*'s log got while OwlBear was not following it as a gap.

    *old* is where the last run read it to (None for a newly found chat), *start* where following begins in *file*.
    """
    was = (0, file) if old is None else (int(old.get("offset") or 0), tuple(old.get("file") or (0, 0)))
    if was[1] != file:
        gap(cid, "the chat's log was replaced while OwlBear was not following it; read as context only")
    elif was[0] < start:
        read = f"bytes {was[0]}..{start} of the chat's log were read as context, never looked at"
        gap(cid, f"OwlBear was not following: {read}")


def gap(cid: str, why: str) -> None:
    """Record that chat *cid*'s bytes were not looked at, and *why*."""
    record = spotter.Record(
        id=uuid.uuid4().hex[:12], at=datetime.now(UTC).isoformat(timespec="seconds"), project="", change="",
        step="chat", session=cid, look="gap", call="", cutoff=0, probability=0.0, skipped=why,
    )  # fmt: skip
    spotter.WORK.submit(spotter.store, spotter.place(), record, None)
