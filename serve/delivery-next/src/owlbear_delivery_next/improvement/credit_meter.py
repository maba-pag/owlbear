"""Credit limits (D-01M5XCD49YHHR1NQKKY8TQD0C3): each look, Retro run and paid replay run stops at its own limit.

There is no daily budget and no SDK credit cap. A ``Meter`` adds what the runtime reports each billed call cost, as it
reports it, and closes once its spend reaches its limit or becomes unknown: cooperative stopping on reported spend. A
call's cost is reported only after the call, and an abort reaches the runtime later still, so the spend may pass the
limit: the limit stops what follows, it is no hard ceiling. Once closed, a meter stays closed, whatever later
corrections say, and nothing new starts on it: no session, retry or extension.

A look's meter may sit in a run's (``parent``): every charge reaches both at once under one lock, and a closed run
closes its looks. A run's looks run one at a time: one already running learns of its run's closing at its next charge.
Each SDK session charges through its own ``Part``, which reconciles only that session's share with the session's
reported total, idempotently: sessions of 0.2 and then 0.1 credits leave 0.3. A share is unknown once a billed call
reports no usable cost or its session ends unconfirmed, until a confirmed total settles it.

The record of a look or run carries ``Meter.report()`` (the shape the other Improvement slices read):

- ``id`` (str): the look's or run's own identity, the same as its record's ``id``; each SDK session it runs notes it
  in the chatlogs manifest's ``started`` line (``look``), so a session's usage joins its look without timestamps;
- ``sdk_sessions`` (list of str): the SDK session ids charged to this meter itself, in order (a retry adds one);
  a run lists none of its looks' sessions, which its looks' records hold;
- ``credits`` (float): the known spend, the sum of what was reported;
- ``credits_known`` (bool): every billed call reported its cost and every session's end was confirmed. A record without
  this key is from before 2026-10-27: its ``credits`` may be the old 0.5 estimate, so it counts as unmeasured;
- ``limit`` (float): the configured limit;
- ``stopped`` (str): "" while within the limit, "reached" once the spend reached a limit, "unknown" once a spend could
  not be known;
- ``stopped_by`` (str): the scope of the meter whose limit or unknown spend stopped it ("look", "replay-run",
  "retro-run"); "" when not stopped.
"""

from __future__ import annotations

import math
import threading
import uuid
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterator

type Report = dict[str, Any]
NANO = 10**9  # nano-credits a credit: the runtime bills in whole ones (``total_nano_aiu``), and a meter counts them


def amount(value: object) -> float | None:
    """*value* as billed credits; None when unknown: missing, not a number, negative or not finite."""
    if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value) or value < 0:
        return None
    return float(value)


def nano(value: object) -> int | None:
    """*value* in credits as whole nano-credits, the precision the runtime bills at; None when unknown."""
    whole = amount(value)
    return None if whole is None else round(whole * NANO)


class Meter:
    """The credits a look or run spent against its limit; thread-safe, its parent's lock shared.

    It counts whole nano-credits, as the runtime bills, so many small amounts reach a limit exactly.
    """

    def __init__(self, limit: float, scope: str = "look", parent: Meter | None = None, ident: str = "") -> None:
        if not (limit_nano := nano(limit)):
            msg = f"a credit limit is a finite number above zero, not {limit!r}"
            raise ValueError(msg)
        self.limit, self.limit_nano, self.scope, self.parent = float(limit), limit_nano, scope, parent
        self.lock: threading.RLock = parent.lock if parent else threading.RLock()
        self.spent_nano, self.calls, self.unresolved = 0, 0, 0  # unresolved: shares whose spend is not known
        self.stopped = self.stopped_by = ""
        self.id = ident or uuid.uuid4().hex[:12]  # the record's id: what its sessions are joined on
        self.sdk_sessions: list[str] = []

    def _chain(self) -> Iterator[Meter]:
        meter: Meter | None = self
        while meter is not None:
            yield meter
            meter = meter.parent

    def _latch(self) -> bool:
        """Close, from the root down, each meter a limit or unknown spend closed, and those below a closed one; open?"""
        cause: tuple[str, str] | None = None
        for meter in reversed(list(self._chain())):
            if not meter.stopped:
                if meter.unresolved:
                    meter.stopped, meter.stopped_by = "unknown", meter.scope
                elif meter.spent_nano >= meter.limit_nano:
                    meter.stopped, meter.stopped_by = "reached", meter.scope
                elif cause:
                    meter.stopped, meter.stopped_by = cause
            if meter.stopped and cause is None:
                cause = (meter.stopped, meter.stopped_by)
        return cause is None

    def admit(self) -> bool:
        """Whether a session, retry or extension may start: neither this meter nor any above it is closed."""
        with self.lock:
            return self._latch()

    def left(self) -> float:
        """The credits left before this meter or one above it reaches its limit; 0 once closed."""
        with self.lock:
            if not self._latch():
                return 0.0
            return max(0, min(m.limit_nano - m.spent_nano for m in self._chain())) / NANO

    def part(self) -> Part:
        """A new SDK session's share of this meter."""
        return Part(self)

    def report(self) -> Report:
        """What the record of this look or run keeps; see the module's description."""
        with self.lock:
            return {"id": self.id, "sdk_sessions": list(self.sdk_sessions), "credits": self.spent_nano / NANO,
                    "credits_known": not self.unresolved, "limit": self.limit,
                    "stopped": self.stopped, "stopped_by": self.stopped_by}  # fmt: skip


class Part:
    """One SDK session's share of a meter: its billed calls as reported, reconciled once with the session's total."""

    def __init__(self, meter: Meter) -> None:
        self.meter = meter
        self.share = self.calls_sum = 0  # nano-credits: what it adds to the meter; what its calls reported
        self.calls = 0  # billed calls reported
        self.unknown_call = False  # a billed call reported no usable cost
        self.unresolved = False

    def started(self, session: str) -> None:
        """The SDK session this share is charged from: its id joins the look's record (``Meter.sdk_sessions``)."""
        with self.meter.lock:
            if session and session not in self.meter.sdk_sessions:
                self.meter.sdk_sessions.append(session)

    def _add(self, delta: int) -> None:
        for meter in self.meter._chain():  # noqa: SLF001 - the share's own meters
            meter.spent_nano += delta
        self.share += delta

    def _resolved(self, *, resolved: bool) -> None:
        if self.unresolved == (not resolved):
            return
        self.unresolved = not resolved
        for meter in self.meter._chain():  # noqa: SLF001
            meter.unresolved += -1 if resolved else 1

    def call(self, reported: object) -> bool:
        """One billed call, its reported cost (unknown when unusable); whether the meter stays open: False, stop now."""
        cost = nano(reported)
        with self.meter.lock:
            self.calls += 1
            for meter in self.meter._chain():  # noqa: SLF001
                meter.calls += 1
            if cost is None:
                self.unknown_call = True
                self._resolved(resolved=False)
            else:
                self.calls_sum += cost
                self._add(cost)
            return self.meter._latch()  # noqa: SLF001

    def ended(self, total: object, *, confirmed: bool) -> None:
        """The session's end, with its reported total (None when unread); idempotent.

        Confirmed (the turn ended, never merely stopped waiting for), a known total replaces this share; without one
        the share stays its calls' sum, known when each call's cost was and at least one call was reported. Unconfirmed,
        a call may still be billed: the share takes the larger of the two and stays unknown. A session that sent no
        turn ends with a total of 0, confirmed.
        """
        reported = nano(total)
        with self.meter.lock:
            if confirmed and reported is not None:
                self._add(reported - self.share)
                self._resolved(resolved=True)
            elif confirmed and self.calls:
                self._add(self.calls_sum - self.share)
                self._resolved(resolved=not self.unknown_call)
            else:
                self._add(max(self.share, reported or 0) - self.share)
                self._resolved(resolved=False)
            self.meter._latch()  # noqa: SLF001
