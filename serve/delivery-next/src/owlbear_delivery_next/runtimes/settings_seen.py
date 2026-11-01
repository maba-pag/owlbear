"""What the last reads of outside data found, kept machine-wide in ``~/.owlbear/settings-read.json`` (#810).

The file holds when the last read ran and when the last one succeeded in full, the last read's failures, Global's set
values as that read found them, and a notice for each Global value changed elsewhere since the read before, kept until
the owner dismisses it. A save from this machine's Settings page updates the values seen, so the owner's own change is
never noticed.
"""

from __future__ import annotations

import json
import secrets
import threading
from datetime import datetime
from functools import partial
from typing import TYPE_CHECKING

from pydantic import Field, ValidationError

from owlbear_delivery_next.change_contracts.models import Record
from owlbear_delivery_next.local_system.storage_io import atomic_write

if TYPE_CHECKING:
    from collections.abc import Callable, Collection
    from pathlib import Path

    from owlbear_delivery_next.settings.config import Layer

NAME = "settings-read.json"
STATE = "read state"  # the source an unreadable file is a failure of


class Notice(Record):
    """One Global value changed elsewhere: its key, the value before and after as JSON text, ``None`` for unset."""

    id: str
    key: str
    old: str | None
    new: str | None
    at: datetime


class Failure(Record):
    """One source a read could not read, and why."""

    source: str
    at: datetime
    error: str


class Seen(Record):
    """The reads' record; ``seen`` is ``None`` before the first read that found Global."""

    succeeded_at: datetime | None = None  # the last read in which every source succeeded
    read_at: datetime | None = None  # the last completed read, partial or not
    failures: list[Failure] = Field(default_factory=list)  # the last read's only
    unshared: bool = False  # no shared repository is set up: said, not a failure
    seen: dict[str, str] | None = None
    notices: list[Notice] = Field(default_factory=list)


_text = partial(json.dumps, separators=(",", ":"), sort_keys=True)


def flatten(layer: Layer | None) -> dict[str, str]:
    """A layer's set values, keyed as the Settings page names them (``agents.builder.model``, ``machine.channel``)."""
    out: dict[str, str] = {}
    for key, value in (layer.model_dump(mode="json", exclude_none=True) if layer else {}).items():
        if key in {"format", "prefs_imported", "roles_moved", "machine_moved"}:  # receipts, not settings
            continue
        if key == "agents":
            out |= {f"agents.{role}.{field}": _text(v) for role, agent in value.items() for field, v in agent.items()}
        elif key in {"prefs", "final_review", "spotter", "machine"}:  # one key per field, as Settings names them
            out |= {f"{key}.{field}": _text(v) for field, v in value.items()}
        else:
            out[key] = _text(value)
    return out


def changed(before: dict[str, str], after: dict[str, str]) -> list[str]:
    """The keys whose values differ, a key missing on one side being unset there."""
    return sorted(k for k in before.keys() | after.keys() if before.get(k) != after.get(k))


class Ledger:
    """The read state file, every change under one lock."""

    def __init__(self, path: Path, say: Callable[[str], None]) -> None:
        self.path, self.say, self._lock = path, say, threading.Lock()
        self._owned: dict[str, str | None] = {}  # this machine's saves of Global during a read, by key

    def _read(self) -> tuple[Seen, str]:
        """The state, and why it could not be read; an absent file is the state before any read."""
        try:
            return Seen.model_validate_json(self.path.read_bytes()), ""
        except FileNotFoundError:
            return Seen(), ""
        except (OSError, ValidationError) as exc:
            return Seen(), f"{type(exc).__name__}: {exc}"[:300]

    def _write(self, seen: Seen) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write(self.path, seen.model_dump_json(indent=1) + "\n")

    def load(self) -> Seen:
        """The state; an unreadable file shows as a failure of the read state until the next read rebuilds it."""
        seen, broken = self._read()
        if broken:
            seen.failures = [Failure(source=STATE, at=datetime.now().astimezone(), error=broken)]
        return seen

    def begin(self) -> None:
        """Start a read: a save made before it ends is taken over the Global it found, which may be older."""
        with self._lock:
            self._owned = {}

    def finish(self, glob: dict[str, str] | None, failures: list[Failure], *, unshared: bool, at: datetime) -> Seen:
        """Record a completed read: Global's values as found (*glob*, ``None`` when it did not read) and its failures.

        Each value that differs from the last read's gets its own notice; the first read only records.
        """
        with self._lock:
            if glob is not None:
                glob = {k: v for k, v in (glob | self._owned).items() if v is not None}
            seen, broken = self._read()
            if broken:
                self.say(f"settings read: {STATE} failed at {self.path}: {broken}; it is rebuilt")
                failures = [Failure(source=STATE, at=at, error=broken), *failures]
            if glob is not None and seen.seen is not None:
                seen.notices += [
                    Notice(id=secrets.token_hex(8), key=k, old=seen.seen.get(k), new=glob.get(k), at=at)
                    for k in changed(seen.seen, glob)
                ]
            seen.succeeded_at = seen.succeeded_at if failures else at
            seen.read_at, seen.failures, seen.unshared = at, failures, unshared
            seen.seen = glob if glob is not None else seen.seen
            self._write(seen)
            return seen

    def own(self, before: Layer | None, after: Layer) -> None:
        """Take this machine's own save of Global as seen, so only changes made elsewhere are noticed.

        It runs right after the save's write; a failure to record it is said, never the save's failure.
        """
        old, new = flatten(before), flatten(after)
        with self._lock:
            updates = {key: new.get(key) for key in changed(old, new)}
            self._owned |= updates
            seen = self._read()[0]
            if seen.seen is None:
                return
            seen.seen = {k: v for k, v in (seen.seen | updates).items() if v is not None}
            try:
                self._write(seen)
            except OSError as exc:
                self.say(f"settings read: the saved Global values could not be recorded as seen: {exc}")

    def dismiss(self, ids: Collection[str]) -> None:
        """Remove the notices with these ids; unknown ids are ignored."""
        with self._lock:
            seen = self._read()[0]
            if not any(n.id in ids for n in seen.notices):
                return
            seen.notices = [n for n in seen.notices if n.id not in ids]
            self._write(seen)
