"""Improvement's marked assumptions (D-01M5XB9M1A1MNG0S54N367RC70): what fills an evidence gap until a decision does.

Each assumption has an id, what it assumes and since when it was first used; ``owlbear improvement reset`` retires
every one at once, used or not. A retired assumption stays retired: what needs it refuses until a decided replacement
(a new id, in code) exists, and nothing marks the same id again, so a rollback, a new seed or a restart never revives
it. Kept owner-only in ``~/.owlbear/improvement/assumptions.json``.
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
PLAN = "chat-plan-1"  # the chats follower's moments (``runtimes.chat_moments``)
HANDOFF = "chat-hand-off-1"
STATE_CHANGE = "chat-state-change-1"
KNOWN = {
    RELEASE: "A release of the Spotter cases is a frozen revision of the case corpus (each reviewed case's card, "
    "expected call and family) and its grading contract; choosing active examples alone makes none",
    SYNTHETIC: "Invented cases stand in for the finding categories no real moment shows yet (outside-state changes, "
    "irreversible harm); never in the reserve, never an example, never published",
    PLAN: "A chat's plan is its agent's first reply with content after a requester message, whatever it asks for "
    "besides",
    HANDOFF: "A chat's hand-off is at most one per requester turn: its final reply (content, no tool requests, its "
    "round ended) once the turn settled, by a checkpoint after it read to the log's end, the next requester message, "
    "the session's end or a quiet time with nothing of the agent open; a later round supersedes it, an abort drops it",
    STATE_CHANGE: "A chat's state change is a completed call of its agent that writes outside the chat's workspace "
    "folder, or publishes, deletes or changes settings by its shell command's words or its tool's name; a call whose "
    "effect is not known is a candidate too, and known read-only calls are none",
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
    """Every assumption ever marked, with its state; none when the file is missing.

    Raises:
        ValueError: The registry is no JSON object: it is unreadable, never taken as empty.
    """
    try:
        marks = json.loads(path().read_text())
    except FileNotFoundError:
        return {}
    if not isinstance(marks, dict):
        msg = "the marked assumptions' registry is not an object"
        raise ValueError(msg)  # noqa: TRY004 - unreadable state, as a file that is no JSON is
    return marks


def _mark(marks: dict[str, Any], name: str) -> dict[str, Any] | None:
    """*name*'s entry in *marks*; None when it was never marked.

    Raises:
        ValueError: Its entry is no object: whether it was retired is unknown.
    """
    if name not in marks:
        return None
    if not isinstance(mark := marks[name], dict):
        msg = f"the marked assumption {name}'s entry is not an object"
        raise ValueError(msg)  # noqa: TRY004 - unreadable state, as a file that is no JSON is
    return mark


def _save(marks: dict[str, dict[str, Any]]) -> None:
    atomic_write(path(), json.dumps(marks, indent=2) + "\n")
    path().chmod(0o600)


def active(name: str) -> bool:
    """Whether *name* is marked and not retired."""
    mark = _mark(listed(), name)
    return mark is not None and not mark.get("retired")


def ensure(name: str) -> bool:
    """Mark *name* when it never was; whether it holds now (False once retired: only a decision replaces it)."""
    with _locked():
        marks = listed()
        if (mark := _mark(marks, name)) is None:
            now = datetime.now(UTC).isoformat(timespec="seconds")
            marks[name] = mark = {"what": KNOWN[name], "since": now, "retired": None}
            _save(marks)
        return not mark.get("retired")


def reset() -> list[str]:
    """Retire every assumption; the ids retired now.

    One never used is listed retired too, so ``ensure`` never marks it later and nothing that rests on it holds.
    """
    with _locked():
        marks, now, done = listed(), datetime.now(UTC).isoformat(timespec="seconds"), []
        read = {name: _mark(marks, name) for name in marks}  # every entry readable before any is changed
        for name, mark in read.items():
            if mark is not None and not mark.get("retired"):
                mark["retired"] = now
                done.append(name)
        for name in sorted(KNOWN.keys() - marks.keys()):
            marks[name] = {"what": KNOWN[name], "since": None, "retired": now}
            done.append(name)
        if done:
            _save(marks)
        return done
