"""Session slots (TD-336, TD-105): how many agent sessions run at once on this machine and in each project.

One arbiter serves the machine host's process: every project host and every design pack update in it. A project host
reserves a step's sessions before it launches the step's runner and gives them back once the runner's processes are
confirmed gone; a pack update takes one for each of its sessions. The machine's total and each project's limit hold
together. A free slot goes round-robin across projects (by project id), first-ready within one. A lowered limit
never stops what runs; it only shapes the next grant.
"""

from __future__ import annotations

import itertools
import threading
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

type Key = tuple[str, str]  # (project, what holds or waits: a Change's slug, or a pack update's session)
PACK = "pack:"  # the prefix of a pack update's keys, which a project host's pass never prunes


@dataclass
class _Waiting:
    seq: int  # first seen ready: the order within a project
    want: int
    limit: int  # its project's limit as last asked


class Slots:
    """The machine's session slots; thread-safe."""

    def __init__(self, total: Callable[[], int], *, closed: bool = False) -> None:
        """*total*: the machine's limit, read at each grant. *closed*: grant nothing until ``open()``."""
        self.total, self.lock = total, threading.Lock()
        self.held: dict[Key, int] = {}
        self.waiting: dict[Key, _Waiting] = {}
        self.wakers: dict[str, Callable[[], None]] = {}
        self.own: dict[Key, Callable[[], None]] = {}  # a waiter woken itself rather than its project's host
        self.last, self.closed, self._seq = "", closed, itertools.count()

    def open(self) -> None:
        """Start granting, once every running step's reservation is known (after a restart)."""
        with self.lock:
            self.closed = False
            turn = self._turn(self.total())
        self._wake(turn)

    def waker(self, project: str, wake: Callable[[], None]) -> None:
        """How to wake *project*'s host when a slot is its turn."""
        self.wakers[project] = wake

    def take(self, project: str, key: str, want: int, limit: int, wake: Callable[[], None] | None = None) -> int:
        """Reserve up to *want* sessions for *key* of *project* when it is its turn: how many, else 0 while it waits.

        A key that holds already gets what it holds. *wake* wakes this waiter for its turn instead of its project.
        """
        with self.lock:
            if (project, key) in self.held:
                return self.held[project, key]
            w = self.waiting.setdefault((project, key), _Waiting(next(self._seq), want, limit))
            w.want, w.limit = want, limit
            if wake:
                self.own[project, key] = wake
            total, granted = self.total(), 0
            if (turn := self._turn(total)) == (project, key):
                granted = min(want, total - sum(self.held.values()), limit - self._of(project))
                del self.waiting[project, key]
                self.own.pop((project, key), None)
                self.held[project, key], self.last = granted, project
                turn = self._turn(total)  # a slot still free goes on
        self._wake(turn)
        return granted

    def give(self, project: str, key: str) -> None:
        """Give back what *key* holds, or stop its wait; the next turn is woken."""
        with self.lock:
            self.waiting.pop((project, key), None)
            self.own.pop((project, key), None)
            self.held.pop((project, key), None)
            turn = self._turn(self.total())
        self._wake(turn)

    def restore(self, project: str, held: dict[str, int]) -> None:
        """What *project*'s live steps hold, as its host finds them on (re)starting; pack sessions keep theirs."""
        with self.lock:
            for k in [k for k in self.held if k[0] == project and not k[1].startswith(PACK)]:
                del self.held[k]
            self.held |= {(project, key): n for key, n in held.items() if n}

    def leave(self, project: str) -> None:
        """Forget a stopped project's waits and its host, so the next turn goes to a project that can take it."""
        with self.lock:
            for k in [k for k in self.waiting if k[0] == project]:
                del self.waiting[k]
                self.own.pop(k, None)
            self.wakers.pop(project, None)
            turn = self._turn(self.total())
        self._wake(turn)

    def keep(self, project: str, keys: set[str]) -> None:
        """Forget *project*'s waiting Changes not in *keys*: they are no longer ready; pack waits stay."""
        with self.lock:
            gone = [k for k in self.waiting if k[0] == project and k[1] not in keys and not k[1].startswith(PACK)]
            for k in gone:
                del self.waiting[k]
            turn = self._turn(self.total()) if gone else None
        self._wake(turn)

    def counts(self, project: str) -> tuple[int, int, int]:
        """Sessions held on this machine, its total, and those *project* holds."""
        with self.lock:
            return sum(self.held.values()), self.total(), self._of(project)

    def _of(self, project: str) -> int:
        return sum(n for (p, _), n in self.held.items() if p == project)

    def _turn(self, total: int) -> Key | None:
        """Whose turn a free slot is: the next project after the last served that may take one, its first-ready."""
        if self.closed or total - sum(self.held.values()) < 1:
            return None
        fits = [k for k, w in self.waiting.items() if w.limit - self._of(k[0]) >= 1]
        if not fits:
            return None
        projects = sorted({p for p, _ in fits})
        project = next((p for p in projects if p > self.last), projects[0])
        return min((k for k in fits if k[0] == project), key=lambda k: self.waiting[k].seq)

    def _wake(self, turn: Key | None) -> None:
        if turn and (wake := self.own.get(turn) or self.wakers.get(turn[0])):
            wake()
