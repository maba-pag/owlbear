"""Improvement's marked assumptions (D-01M5XB9M1A1MNG0S54N367RC70): what fills an evidence gap until a decision does.

Each assumption has an id, what it assumes and since when; ``owlbear improvement reset`` retires every one at once.
A retired assumption stays retired: what needs it refuses until a decided replacement (a new id, in code) exists,
and nothing marks the same id again, so a rollback or a new seed never revives it. Kept owner-only in
``~/.owlbear/improvement/assumptions.json``.
"""

from __future__ import annotations

import contextlib
import fcntl
import json
import os
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.local_system import local_home
from owlbear_delivery_next.local_system.storage_io import atomic_write

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

RELEASE = "assumed-release-1"
SYNTHETIC = "synthetic-cases-1"
KNOWN = {
    RELEASE: "A release of the Spotter cases is a frozen revision of the case corpus (each reviewed case's card, "
    "expected call and family) and its grading contract; choosing active examples alone makes none",
    SYNTHETIC: "Invented cases stand in for the finding categories no real moment shows yet (outside-state changes, "
    "irreversible harm); never in the reserve, never an example, never published",
}


def path() -> Path:
    """The registry's file."""
    return local_home.root() / "improvement" / "assumptions.json"


@contextlib.contextmanager
def _locked() -> Iterator[None]:
    path().parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(path().with_suffix(".lock"), os.O_WRONLY | os.O_CREAT, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        os.close(fd)


def listed() -> dict[str, dict[str, Any]]:
    """Every assumption ever marked, with its state; none when the file is missing."""
    try:
        return json.loads(path().read_text())
    except FileNotFoundError:
        return {}


def _save(marks: dict[str, dict[str, Any]]) -> None:
    atomic_write(path(), json.dumps(marks, indent=2) + "\n")
    path().chmod(0o600)


def active(name: str) -> bool:
    """Whether *name* is marked and not retired."""
    mark = listed().get(name)
    return mark is not None and not mark.get("retired")


def ensure(name: str) -> bool:
    """Mark *name* when it never was; whether it holds now (False once retired: only a decision replaces it)."""
    with _locked():
        marks = listed()
        if name not in marks:
            now = datetime.now(UTC).isoformat(timespec="seconds")
            marks[name] = {"what": KNOWN[name], "since": now, "retired": None}
            _save(marks)
        return not marks[name].get("retired")


def reset() -> list[str]:
    """Retire every active assumption; the ids retired now."""
    with _locked():
        marks, now, done = listed(), datetime.now(UTC).isoformat(timespec="seconds"), []
        for name, mark in marks.items():
            if not mark.get("retired"):
                mark["retired"] = now
                done.append(name)
        if done:
            _save(marks)
        return done
