"""STAND-IN for feat/run-credit-limits' ``improvement.credits``: the rebase replaces this whole file with theirs.

A run's or a look's credit meter (D-01M5XCD49YHHR1NQKKY8TQD0C3): what it spent against its own limit; a child charges
its parent too, so a run stops when its looks together reach the run's limit. Unknown spend closes it.
"""

from __future__ import annotations

import threading
from typing import Any


class Meter:
    """Credits spent against *limit*; thread-safe. A child meter charges its *parent* as well."""

    def __init__(self, limit: float, parent: Meter | None = None) -> None:
        self.limit, self.parent, self.lock = float(limit), parent, threading.Lock()
        self.spent, self.calls, self.known, self.stopped = 0.0, 0, True, ""

    def left(self) -> float:
        """Credits left; a closed meter has none."""
        with self.lock:
            own = 0.0 if self.stopped else max(0.0, self.limit - self.spent)
        return min(own, self.parent.left()) if self.parent is not None else own

    def open(self) -> bool:
        """Whether another call may start."""
        return self.left() > 0

    def charge(self, credits: float | None) -> bool:  # noqa: A002 - the upstream interface's name
        """Book one call's *credits* (None: unknown, which closes the meter); whether the meter stays open."""
        with self.lock:
            self.calls += 1
            if credits is None:
                self.known, self.stopped = False, self.stopped or "unknown spend"
            else:
                self.spent += credits
                if self.spent >= self.limit and not self.stopped:
                    self.stopped = "credit limit reached"
        if self.parent is not None:
            self.parent.charge(credits)
        return self.open()

    def correct(self, delta: float) -> None:
        """Adjust the spend to a total read later."""
        with self.lock:
            self.spent += delta
        if self.parent is not None:
            self.parent.correct(delta)

    def unsure(self, why: str) -> None:
        """The spend is not known: no further call."""
        with self.lock:
            self.known, self.stopped = False, self.stopped or why
        if self.parent is not None:
            self.parent.unsure(why)

    def refuse(self, what: str) -> None:
        """Close the meter: *what* may not start."""
        with self.lock:
            self.stopped = self.stopped or what

    def report(self) -> dict[str, Any]:
        """What the meter holds, for a record."""
        with self.lock:
            return {
                "limit": self.limit,
                "credits": round(self.spent, 4),
                "credits_known": self.known,
                "calls": self.calls,
                "stopped": self.stopped,
            }
