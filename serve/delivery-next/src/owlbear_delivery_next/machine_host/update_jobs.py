"""The machine's update jobs and their common admission barrier."""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING

from owlbear_delivery_next.impeccable import pack_files
from owlbear_delivery_next.impeccable_runs import pack_job
from owlbear_delivery_next.local_system import data_repo
from owlbear_delivery_next.machine_host import cases_job
from owlbear_delivery_next.project_host import decision_routes, session_slots
from owlbear_delivery_next.state_store import update_home

if TYPE_CHECKING:
    from collections.abc import Iterator

    from owlbear_delivery_next.machine_host.machine import Machine


class Source:
    """Machine settings and OwlBear's shared memory and calibration."""

    name = decision_routes.OWLBEAR
    settings = staticmethod(cases_job.settings)

    def __init__(self) -> None:
        self.root = update_home.root()

    @property
    def shared(self) -> data_repo.DataRepo | None:
        """Find the shared repository in its current location."""
        return data_repo.locate()


class Updates:
    """One of each update and one hand audit, bound to the machine's slots."""

    def __init__(self, machine: Machine) -> None:
        self.machine = machine
        store = Source()
        owner = session_slots.SlotOwner(
            update_home.KEY, machine.slots, machine.maintenance, lambda: 1,
            self.admitted, lambda: bool(self.refusal()),
        )  # fmt: skip
        self.pack = session_slots.packed(owner, pack_job.Job(store))
        self.hand, self.pds = session_slots.pds(owner, store)

    def refusal(self) -> str:
        """Why no update work may start, even while Delivery otherwise runs."""
        m = self.machine
        if m.stopping.is_set():
            return "OwlBear is stopping"
        return m.updating or ("OwlBear stops once nothing runs" if m.ending else "")

    @contextmanager
    def admitted(self) -> Iterator[None]:
        """Start under the same barrier as stop when idle and OwlBear's update fence."""
        with self.machine.lock:
            if why := self.refusal():
                raise pack_files.PackError(why)
            yield

    def working(self) -> list[str]:
        """The updates, replay and audit that have not finished running."""
        return session_slots.busy(self.pack, self.hand, self.pds)
