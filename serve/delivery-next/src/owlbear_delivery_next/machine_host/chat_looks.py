"""A chat look's ownership (Improvement design §4): a maintenance lease from before its session to its confirmed end.

Like a Spotter cases run (``machine_host.cases_job``), each chat look holds a lease in the maintenance ledger
(``local_system.maintenance``) from before its session is created until its runtime's end is confirmed. A runtime
whose end teardown could not confirm (``spotter_look.UNENDED``) keeps the lease, and with it a session slot, held
until the owner recovers it on the Maintenance page after a reboot: meanwhile no chat look starts, and a stop when idle
or an update waits for it. A restarted host restores the held lease. A lease that cannot be written starts no session,
and a ledger that cannot be read counts as held.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.improvement import spotter
from owlbear_delivery_next.local_system import maintenance, processes
from owlbear_delivery_next.runtimes import spotter_look

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_delivery_next.improvement.credit_meter import Meter

PROJECT = "spotter-chats"  # the leases' share of the machine's slots
KIND = "replay"  # the Spotter's lane of the ledger; the cases job's leases are told apart by their project
LINGERING = "Spotter chats: a look's runtime may still run (its end was not confirmed); see Maintenance"


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
