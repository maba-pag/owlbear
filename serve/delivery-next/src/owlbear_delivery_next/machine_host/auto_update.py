"""Updating by itself when idle (self-update build §7; TD-301, TD-288, TD-352).

Idle is no agent step, check environment, design pack update or admitted work in any project, and no use for 15
minutes. Use is any request other than a read, a page's word that the owner is at it (at most once a minute) and every
chat tool call; polls never count. When a newer version of the machine's channel is there and the machine is idle,
every open page announces the update 2 minutes ahead with Postpone; Postpone is use, and any use cancels it. A clock
jump such as a sleep restarts the announcement. Update when idle off, or paused with Update while paused off, leaves
only Run updates now.
"""

from __future__ import annotations

import threading
import time
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.machine_host import registry, versions

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_delivery_next.machine_host.machine import Machine

IDLE_FOR = 900.0  # seconds without use before an update may be announced (TD-301)
ANNOUNCE = 120.0  # seconds the pages announce it ahead
LOOK = 600.0  # seconds between looks for a newer version: each one fetches
TICK = 5.0  # seconds between the loop's looks at the machine
JUMP = 30.0  # seconds the wall clock may run ahead of the monotonic one before it counts as a sleep


class Auto:
    """The machine's idle time, its announcement and the automatic update it leads to."""

    def __init__(
        self, machine: Machine, wall: Callable[[], float] = time.time, mono: Callable[[], float] = time.monotonic
    ) -> None:
        """Count idle time from now; nothing is announced yet."""
        self.machine, self.wall, self.mono = machine, wall, mono
        self.lock = threading.Lock()
        self.last_use = mono()
        self.deadline: float | None = None
        self.target, self.next_look = "", 0.0
        self.clocks = (wall(), mono())

    def use(self) -> None:
        """The owner is at it: idle time starts again and an announcement is cancelled (Postpone too)."""
        with self.lock:
            self.last_use, self.deadline = self.mono(), None

    def read(self) -> dict[str, Any] | None:
        """The announcement the pages show: the version and the seconds left; None while none runs."""
        with self.lock:
            if self.deadline is None:
                return None
            return {"version": self.target, "left": max(0, round(self.deadline - self.mono()))}

    def _allowed(self) -> bool:
        try:
            settings = registry.load().settings
        except registry.RegistryError:
            return False
        m = self.machine
        if m.stopping.is_set() or m.ending or m.updating or m.handover is not None:
            return False
        return settings.update_when_idle and (not m.paused or settings.update_while_paused)

    def _looked(self, now: float) -> str:
        if now >= self.next_look:
            self.next_look = now + LOOK
            try:
                choice = versions.target()
            except versions.VersionError, registry.RegistryError:
                choice = None
            self.target = choice.tag if choice else ""
        return self.target

    def tick(self) -> None:
        """One look: announce when due, run the update when the announcement ends with the machine still idle."""
        wall, now = self.wall(), self.mono()
        jumped = (wall - self.clocks[0]) - (now - self.clocks[1]) > JUMP
        self.clocks = (wall, now)
        busy = self.machine.updater.thread is not None and self.machine.updater.thread.is_alive()
        if busy or not self._allowed() or not self._looked(now):
            with self.lock:
                self.deadline = None
            return
        with self.lock:
            idle = now - self.last_use >= IDLE_FOR and not self.machine.busy()
            if not idle:
                self.deadline = None
                return
            if self.deadline is None or jumped:  # a sleep restarts the announcement: the owner may be back
                self.deadline = now + ANNOUNCE
                self.machine.say(f"update: announced {self.target} in {ANNOUNCE:.0f} s")
                return
            if now < self.deadline:
                return
            self.deadline = None
        self.machine.updater.run_now()

    def loop(self) -> None:
        """Thread: look every ``TICK`` seconds until the machine stops."""
        while not self.machine.stopping.wait(TICK):
            try:
                self.tick()
            except Exception as exc:  # noqa: BLE001 - the loop outlives one failed look
                self.machine.say(f"looking whether to update failed: {type(exc).__name__}: {exc}")
