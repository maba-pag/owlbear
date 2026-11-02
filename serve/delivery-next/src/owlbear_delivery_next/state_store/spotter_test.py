"""The Spotter's steered-versus-silent test record (design §4): declared, started with its inputs frozen, ended.

One file, ``test.json`` in the Spotter's owner-only folder (``~/.owlbear/spotter/``), holds the newest test as plain
values: its ``id``, ``declared`` (the primary outcome, the start threshold and the promotion threshold, as the owner
gives them), ``frozen`` (the Spotter role's model, effort and context, the prompt's text and hash, the cases' version)
with ``started_at``, and ``ended_at``. A declaration may be replaced until the test starts and is refused from then on,
left as it was; a test starts only once declared, and ends once. After its end a new declaration begins the next test.
Every change is made under the file's lock and written atomically; a read takes the file as it was last replaced.
What the thresholds admit or promote is the test's runner's (item 25), never this record's.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.local_system import local_home, storage_io

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from pathlib import Path

FILE, LOCK = "test.json", "test.lock"


class Refused(Exception):  # noqa: N818 - says what happened
    """A change of the test record its state does not allow, said as the owner should read it."""


def path() -> Path:
    """Where the record is kept; nothing is created."""
    return local_home.root() / "spotter" / FILE


def current() -> dict[str, Any] | None:
    """The newest test, whatever its state; None before the first declaration.

    Raises:
        ValueError: The record cannot be read as JSON (its path and the parser's error say where).
    """
    raw = storage_io.read_regular(path())
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except ValueError as exc:
        msg = f"the Spotter's test record {path()} cannot be read: {exc}"
        raise ValueError(msg) from exc


def active() -> dict[str, Any] | None:
    """The test running now (started, not ended), with its ``frozen`` values; else None."""
    test = current()
    return test if test is not None and test.get("started_at") and not test.get("ended_at") else None


def name(test: Mapping[str, Any]) -> str:
    """How an error names *test*: its id and declared outcome."""
    return f"the Spotter test {test['id']} ({test['declared']['outcome']!r})"


def declare(outcome: str, start_threshold: str, promote_threshold: str) -> dict[str, Any]:
    """Declare the next test, or replace the declaration of one not started; the record.

    Raises:
        Refused: A test has started and not ended: its declaration is fixed.
    """

    def change(test: dict[str, Any] | None) -> dict[str, Any]:
        if test is not None and test.get("started_at") and not test.get("ended_at"):
            msg = f"{name(test)} started at {test['started_at']}: its declaration is fixed until it ends"
            raise Refused(msg)
        declared = {"outcome": outcome, "start_threshold": start_threshold, "promote_threshold": promote_threshold}
        tid = test["id"] if test is not None and not test.get("started_at") else f"t-{uuid.uuid4().hex[:8]}"
        return {"id": tid, "declared_at": _now(), "declared": declared, "frozen": None, "started_at": "",
                "ended_at": ""}  # fmt: skip

    return _changed(change)


def start(frozen: Mapping[str, Any]) -> dict[str, Any]:
    """Start the declared test with *frozen* kept for every look while it runs; the record.

    Raises:
        Refused: No test is declared, or the declared one has started already.
    """

    def change(test: dict[str, Any] | None) -> dict[str, Any]:
        if test is None or test.get("ended_at"):
            msg = "no Spotter test is declared: declare its outcome and thresholds first"
            raise Refused(msg)
        if test.get("started_at"):
            msg = f"{name(test)} started already, at {test['started_at']}"
            raise Refused(msg)
        return {**test, "frozen": dict(frozen), "started_at": _now()}

    return _changed(change)


def end() -> dict[str, Any]:
    """End the running test; the record.

    Raises:
        Refused: No test is running.
    """

    def change(test: dict[str, Any] | None) -> dict[str, Any]:
        if test is None or not test.get("started_at") or test.get("ended_at"):
            msg = "no Spotter test is running" + (f": {name(test)} is {state(test)}" if test else "")
            raise Refused(msg)
        return {**test, "ended_at": _now()}

    return _changed(change)


def state(test: Mapping[str, Any] | None) -> str:
    """``none``, ``declared``, ``started`` or ``ended``."""
    if test is None:
        return "none"
    return "ended" if test.get("ended_at") else "started" if test.get("started_at") else "declared"


def _changed(change: Callable[[dict[str, Any] | None], dict[str, Any]]) -> dict[str, Any]:
    folder = path().parent
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(folder, os.O_RDONLY | os.O_DIRECTORY)
    try:
        lock = storage_io.open_lock(fd, blocking=True, name=LOCK)
        try:
            test = change(current())
            storage_io.atomic_write(path(), json.dumps(test, indent=1, sort_keys=True) + "\n")
            return test
        finally:
            os.close(lock)
    finally:
        os.close(fd)


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")
