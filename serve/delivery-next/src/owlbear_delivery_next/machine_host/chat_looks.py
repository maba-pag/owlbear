"""A chat look's admission and ownership (Improvement design §4): counted from admission, leased until its end.

A look is admitted (``Gate.admit``) under the machine's stop barrier, the one an update's fence, a stop and a stop when
idle take: none once one of them holds, and one admitted before is counted (``Gate.working``) before the barrier is let
go, from then until its task ends, so the fence and a stop when idle wait for it even before its session exists. One
chat look runs at a time.

Like a Spotter cases run (``machine_host.cases_job``), each chat look holds a lease in the maintenance ledger
(``local_system.maintenance``) from before its session is created until its runtime's end is confirmed. A runtime
whose end teardown could not confirm (``spotter_look.UNENDED``) keeps the lease, and with it a session slot, held
until the owner recovers it on the Maintenance page after a reboot: meanwhile no chat look starts, and a stop when idle
or an update waits for it. A restarted host restores the held lease. A lease that cannot be written starts no session,
and a ledger that cannot be read counts as held.
"""

from __future__ import annotations

import contextlib
import threading
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.improvement import spotter
from owlbear_delivery_next.local_system import maintenance, processes
from owlbear_delivery_next.runtimes import spotter_look

if TYPE_CHECKING:
    from collections.abc import Callable
    from contextlib import AbstractContextManager

    from owlbear_delivery_next.improvement.credit_meter import Meter

PROJECT = "spotter-chats"  # the leases' share of the machine's slots
KIND = "replay"  # the Spotter's lane of the ledger; the cases job's leases are told apart by their project
LINGERING = "Spotter chats: a look's runtime may still run (its end was not confirmed); see Maintenance"
LOOKS = 1  # chat looks at once on this machine
CAPACITY = "capacity: a chat look is already running"
HELD = "held: a chat look's runtime may still run; no chat look starts until Maintenance recovers it"
FENCED = "fenced: no chat look starts while OwlBear updates or stops"


@dataclass
class _Ended:
    """What a look's session left, as the maintenance ledger reads it; its runtime records no PIDs."""

    termination: processes.Termination
    pids: processes.Pids = field(default_factory=dict)
    runtime_pid: int | None = None


class Owned:
    """Chat looks under the machine's maintenance ledger *ownership*; *say* tells the owner of a held one."""

    def __init__(self, ownership: maintenance.Maintenance, say: Callable[[str], None]) -> None:
        self.ownership, self.say = ownership, say

    def lingering(self) -> bool:
        """Whether a look's lease is held, so its runtime may still run; an unreadable ledger counts as held."""
        try:
            return PROJECT in self.ownership.holding(KIND)
        except maintenance.MaintenanceError:
            return True

    async def judged(self, judge: spotter.Judge, the_card: dict[str, Any], ctx: spotter.Context, meter: Meter) -> str:
        """*judge*'s look under a lease begun before its session and ended with what its teardown confirmed."""
        key = f"look-{meter.id}"
        lease = await spotter.offload(self.ownership.begin, PROJECT, key, KIND, "")  # durable before any session
        unended: list[str] = []
        token = spotter_look.UNENDED.set(unended)  # its teardown runs within it, whatever cancels the look
        try:
            return await judge(the_card, ctx, meter)
        finally:
            spotter_look.UNENDED.reset(token)
            problems = (f"the end of a Spotter chat look's session was not confirmed: {', '.join(unended)}"[:300],)
            ended = _Ended(processes.Termination(not unended, problems=problems if unended else ()))
            if unended:
                self.ownership.slots.restore_one(PROJECT, key, 1)  # its runtime may still use a session
            await spotter.offload(self.ownership.finished, lease, ended)
            if unended:
                self.say(f"chats follower: {problems[0]}; no chat look starts until Maintenance recovers it")


class Gate:
    """Chat looks' admission: *fenced* says why none starts (an update, a stop), read under *admission*'s barrier."""

    def __init__(
        self,
        fenced: Callable[[], str],
        admission: Callable[[], AbstractContextManager[Any]] | None,
        owned: Owned | None,
    ) -> None:
        self.fenced, self.owned = fenced, owned
        self.admission = admission or contextlib.nullcontext
        self.lock = threading.Lock()
        self.admitted = 0  # looks admitted whose task has not ended

    def admit(self) -> str:
        """Admit one look (""), counted until ``left``, or say why none starts now."""
        with self.lock:
            if self.admitted >= LOOKS:
                return CAPACITY
        if self.owned is not None and self.owned.lingering():
            return HELD
        with self.admission():  # a fence or stop taken before this keeps it out; one taken after counts it
            if self.fenced():
                return FENCED
            with self.lock:
                if self.admitted >= LOOKS:
                    return CAPACITY
                self.admitted += 1
        return ""

    def left(self) -> None:
        """A look ``admit`` admitted ended."""
        with self.lock:
            self.admitted -= 1

    def working(self) -> list[str]:
        """What a stop when idle and an update wait for: an admitted look, or a look's runtime that may still run."""
        with self.lock:
            n = self.admitted
        running = [f"Spotter chats: {n} look running"] if n else []
        return running + ([LINGERING] if self.owned is not None and self.owned.lingering() else [])
