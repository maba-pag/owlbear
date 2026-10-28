"""Retro's job in the machine host (#715): leases per paid call, recovery, triggers, eligibility and pruning."""

from owlbear_delivery_next.local_system import maintenance, processes
from owlbear_delivery_next.local_system.slots import Slots
from owlbear_delivery_next.runtimes.session_result import Run


def _owner(*, closed=False):
    return maintenance.Maintenance(Slots(lambda: 2, closed=closed), boot=lambda: 10.0, observe=lambda *_: False)


def test_a_retro_lease_is_begun_persisted_finished_and_reloaded_under_its_own_kind(tmp_path):
    owner = _owner()
    assert owner.slots.take("retro", "retro:b-1", 1, 1) == 1
    lease = owner.begin("retro", "retro:b-1", "retro", "")
    assert owner.holding("retro") == ["retro"]
    owner.finished(lease, Run("x", termination=processes.Termination(confirmed=True)))
    again = _owner(closed=True)
    assert again.holding("retro") == []
    assert [(s["kind"], s["state"]) for s in again.read()["sessions"]] == [("retro", "released")]


def test_a_dead_owners_retro_lease_reloads_held_with_its_slot(tmp_path):
    owner = _owner()
    assert owner.slots.take("retro", "retro:b-2", 1, 1) == 1
    owner.begin("retro", "retro:b-2", "retro", "")
    restarted = _owner(closed=True)
    restarted.slots.open()
    assert restarted.holding("retro") == ["retro"]
    assert restarted.slots.take("retro", "retro:b-3", 1, 1) == 0
