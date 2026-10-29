"""An OwlBear update's ten steps as the pages show them, kept across the switch (D-01M63CCHPB2W34NM7K9NHEXFY3).

Each step has a state, its start and end time and its line; a capped log keeps the lines in the order they came,
written by OwlBear itself, never a tool's raw output. The current update's steps live in
``~/.owlbear/update-steps.json``, rewritten on every change and overwritten by the next update: no history. The
version that takes over reads the record its old host wrote for it and adds its own last step; with no such record it
shows its own step alone.
"""

from __future__ import annotations

import contextlib
import json
import threading
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.local_system import local_home
from owlbear_delivery_next.local_system.storage_io import atomic_write

if TYPE_CHECKING:
    from collections.abc import Callable

STEPS = (
    ("looking", "Looking for a newer version"),
    ("getting", "Getting the version"),
    ("building", "Building its environment"),
    ("selfcheck", "Self-check"),
    ("impeccable", "Installing its Impeccable"),
    ("waiting", "Waiting for running steps"),
    ("standby", "Starting the standby"),
    ("health", "Health check"),
    ("switching", "Switching"),
    ("handover", "Handing over"),
)
LABELS = dict(STEPS)
RECORD = "update-steps.json"
SHAPE = 1  # the record's format; any other one, or none, is read as absent
LOG = 100  # log lines kept
LINE = 240  # characters a line keeps


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def line_of(text: str) -> str:
    """*text* as one capped line: its last non-empty line, spaces folded."""
    lines = [s for s in text.splitlines() if s.strip()]
    return " ".join(lines[-1].split())[:LINE] if lines else ""


class Steps:
    """The current update's steps and log, and their record under ``~/.owlbear``."""

    def __init__(self, say: Callable[[str], None]) -> None:
        """No update's steps yet."""
        self.say, self.lock = say, threading.Lock()
        self.version, self.steps, self.log = "", [], []
        self.unwritten = ""  # the last write's failure, said once

    def begin(self) -> None:
        """A new update: every step waits, the log is empty and the record is overwritten."""
        with self.lock:
            self.version, self.log = "", []
            self.steps = [{"key": k, "label": label, "state": "pending", "started_at": None, "ended_at": None,
                           "line": ""} for k, label in STEPS]  # fmt: skip
            self._write()

    def about(self, version: str) -> None:
        """The version this update takes."""
        with self.lock:
            self.version = version
            self._write()

    def mark(self, key: str, state: str, line: str = "") -> None:
        """Step *key* is now *state* (running, done, failed or stopped) with *line*.

        A step started again resets the ones after it.
        """
        with self.lock:
            self._mark(key, state, line_of(line))
            self._write()

    def end(self, state: str, line: str) -> None:
        """The update ended: each running step takes *state* and *line*."""
        with self.lock:
            for step in [s for s in self.steps if s["state"] == "running"]:
                self._mark(step["key"], state, line_of(line))
            self._write()

    def read(self) -> dict[str, Any]:
        """The steps and the log, as the pages read them."""
        with self.lock:
            return {"steps": [dict(s) for s in self.steps], "log": [dict(e) for e in self.log]}

    def took_over(self, version: str, state: str, line: str) -> None:
        """This host is *version*, taken over from its old host; it ends the handover, the update's last step.

        The steps before come from the old host's record of *version*; without one this host's step stands alone.
        """
        with self.lock:
            found = _record()
            if found.get("version") == version:
                self.steps, self.log = found["steps"], found["log"]
            else:
                self.steps, self.log = [], []
            self.version = version
            self._mark("handover", state, line_of(line))
            self._write()

    def _mark(self, key: str, state: str, line: str) -> None:
        at = _now()
        step = next((s for s in self.steps if s["key"] == key), None)
        if step is None:  # a step this host has no record of: its own, alone
            step = {"key": key, "label": LABELS[key], "state": "pending", "started_at": None, "ended_at": None,
                    "line": ""}  # fmt: skip
            self.steps.append(step)
        if state == "running" and step["state"] != "running":
            step["started_at"], step["ended_at"] = at, None
            for later in self.steps[self.steps.index(step) + 1 :]:
                later.update(state="pending", started_at=None, ended_at=None, line="")
        elif state != "running":
            step["started_at"] = step["started_at"] or at
            step["ended_at"] = at
        if line and line != step["line"]:
            self.log = [*self.log, {"at": at, "step": key, "line": line}][-LOG:]
        step["state"], step["line"] = state, line or step["line"]

    def _write(self) -> None:
        path = local_home.root() / RECORD
        body = {"shape": SHAPE, "version": self.version, "steps": self.steps, "log": self.log}
        try:
            atomic_write(path, json.dumps(body))
            path.chmod(0o600)
        except OSError as exc:  # the update goes on; only the pages after a switch lose the steps before it
            if str(exc) != self.unwritten:
                self.say(f"update: its steps could not be kept in {path}: {exc}")
            self.unwritten = str(exc)
        else:
            self.unwritten = ""


def _step(s: object) -> bool:
    return (
        isinstance(s, dict) and set(s) == {"key", "label", "state", "started_at", "ended_at", "line"}
        and all(isinstance(s[k], str) for k in ("key", "label", "state", "line")) and s["key"] in LABELS
        and all(s[k] is None or isinstance(s[k], str) for k in ("started_at", "ended_at"))
    )  # fmt: skip


def _entry(e: object) -> bool:
    return (
        isinstance(e, dict) and set(e) == {"at", "step", "line"} and all(isinstance(v, str) for v in e.values())
        and e["step"] in LABELS
    )  # fmt: skip


def _record() -> dict[str, Any]:
    """The record an update kept; empty when it is missing, unreadable, damaged or from another producer."""
    with contextlib.suppress(OSError, ValueError):
        found = json.loads((local_home.root() / RECORD).read_text())
        if (
            isinstance(found, dict) and found.get("shape") == SHAPE and isinstance(found.get("version"), str)
            and isinstance(found.get("steps"), list) and isinstance(found.get("log"), list)
            and all(map(_step, found["steps"])) and all(map(_entry, found["log"]))
        ):  # fmt: skip
            return found
    return {}
