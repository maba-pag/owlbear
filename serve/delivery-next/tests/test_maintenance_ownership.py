"""Durable ownership before maintenance SDK entry, including failures without a returned process identity."""

from datetime import UTC, datetime

import pytest

from owlbear_delivery_next.change_contracts import tools
from owlbear_delivery_next.change_contracts.models import StepKind
from owlbear_delivery_next.change_contracts.permissions import Policy
from owlbear_delivery_next.local_system import maintenance, processes
from owlbear_delivery_next.local_system.slots import Slots
from owlbear_delivery_next.runtimes import maintained, sdk_adapter
from owlbear_delivery_next.runtimes.session_result import Run

AT = datetime(2026, 10, 25, tzinfo=UTC)


def manager(slots, *, boot=10.0, seen=lambda *_args: False):
    return maintenance.Maintenance(slots, boot=lambda: boot, observe=seen)


def begin(owner, root):
    assert owner.slots.take("p", "pack:one", 1, 1) == 1
    return owner.begin("p", "pack:one", "pack", str(root), now=AT)


def test_empty_identity_exception_retains_its_slot_across_restart_and_requires_a_real_reboot(tmp_path):
    owner = manager(Slots(lambda: 1))
    ident = begin(owner, tmp_path)
    owner.failed(ident, RuntimeError("no Run returned"))
    restarted = manager(Slots(lambda: 1, closed=True))
    restarted.slots.open()
    assert restarted.slots.counts("p") == (1, 1, 1)
    restarted.sweep()
    assert restarted.slots.take("other", "c1", 1, 1) == 0
    assert restarted.retained(str(tmp_path))
    with pytest.raises(ValueError, match="reboot"):
        restarted.recover(ident, rebooted=True)

    rebooted = manager(Slots(lambda: 1, closed=True), boot=20.0)
    rebooted.slots.open()
    with pytest.raises(ValueError, match="confirm"):
        rebooted.recover(ident, rebooted=False)
    result = rebooted.recover(ident, rebooted=True)
    assert result["sessions"][0]["state"] == "recovered"
    assert rebooted.slots.counts("p") == (0, 1, 0)
    assert rebooted.retained(str(tmp_path))
    assert tmp_path.exists()
    with pytest.raises(LookupError):
        rebooted.recover(ident, rebooted=True)


def test_unknown_termination_never_releases_merely_because_known_pids_are_gone(tmp_path):
    owner = manager(Slots(lambda: 1))
    ident = begin(owner, tmp_path)
    owner.record(ident, {4242: 1.0})
    run = Run("x", pids={4242: 1.0}, runtime_pid=4242,
              termination=processes.Termination(confirmed=False, problems=("request task pending",)))  # fmt: skip
    owner.finished(ident, run)
    owner.sweep()
    assert owner.slots.counts("p") == (1, 1, 1)
    assert owner.retained(str(tmp_path))


def test_identified_complete_session_sweeps_once_without_releasing_a_successor(tmp_path):
    alive = {4242: True}
    owner = manager(Slots(lambda: 1), seen=lambda pid, _created: alive.get(pid, False))
    ident = begin(owner, tmp_path)
    run = Run("x", pids={4242: 1.0}, runtime_pid=4242,
              termination=processes.Termination(confirmed=False, survivors=(4242,)))  # fmt: skip
    owner.finished(ident, run)
    owner.sweep()
    assert owner.slots.counts("p") == (1, 1, 1)
    alive[4242] = False
    owner.sweep()
    assert owner.slots.counts("p") == (0, 1, 0)
    assert not owner.retained(str(tmp_path))
    assert owner.slots.take("p", "c1", 1, 1) == 1
    owner.sweep()
    assert owner.slots.counts("p") == (1, 1, 1)


def test_restoring_maintenance_does_not_prune_ordinary_runner_reservations(tmp_path):
    slots = Slots(lambda: 3)
    assert slots.take("p", "c1", 1, 3) == 1
    owner = manager(slots)
    assert slots.take("p", "pack:one", 1, 3) == 1
    ident = owner.begin("p", "pack:one", "pack", str(tmp_path), now=AT)
    owner.failed(ident, RuntimeError("unknown termination"))
    manager(slots)
    assert slots.counts("p") == (2, 3, 2)


@pytest.mark.parametrize("fails", [False, True])
def test_admitted_sdk_entry_is_durable_and_unknown_work_keeps_its_workspace(fails):
    owner = manager(Slots(lambda: 1))
    events = []
    with owner.workspace("synthetic-maintenance-") as root:
        cfg = sdk_adapter.Session(
            kind=StepKind.REVIEW,
            worktree=root,
            session_id="synthetic",
            message="Synthetic work",
            resume=False,
            policy=Policy(root),
            observe=lambda: tools.Worktree("", ""),
            checks=(),
            model="synthetic-model",
            journal=sdk_adapter.Journal(event=events.append),
        )

        def execute(bound):
            lease = owner.read()["sessions"][-1]
            assert lease["state"] == "running"
            assert lease["workspace"] == str(root)
            bound.journal.event({"event": "pids", "pids": {"4242": 1.0}})
            bound.journal.event({"event": "pids", "pids": {"4242": None}})
            if fails:
                msg = "synthetic runtime failure"
                raise RuntimeError(msg)
            return Run("synthetic", termination=processes.Termination(confirmed=True))

        assert owner.slots.take("p", "pack:one", 1, 1) == 1
        if fails:
            with pytest.raises(RuntimeError, match="synthetic runtime failure"):
                maintained.run_owned(owner, cfg, execute, project="p", slot="pack:one", kind="pack")
        else:
            maintained.run_owned(owner, cfg, execute, project="p", slot="pack:one", kind="pack")
        assert len(events) == 2
    assert root.exists() is fails
    assert owner.slots.counts("p") == ((1, 1, 1) if fails else (0, 1, 0))


def test_a_recovered_generation_does_not_suppress_a_later_unknown_legacy_run(tmp_path):
    first = manager(Slots(lambda: 1, closed=True)).adopt_uncertain(
        "legacy", "p", "pack", workspace=str(tmp_path), generation="run-a:t1"
    )
    rebooted = manager(Slots(lambda: 1, closed=True), boot=20.0)
    rebooted.slots.open()
    rebooted.recover(first.id, rebooted=True)
    later = rebooted.adopt_uncertain("legacy", "p", "pack", workspace=str(tmp_path), generation="run-b:t2")
    assert later.id != first.id
    assert later.state == "held"
    assert (
        rebooted.adopt_uncertain("legacy", "p", "pack", workspace=str(tmp_path), generation="run-a:t1").id == first.id
    )
    assert {s["id"] for s in rebooted.read()["sessions"]} == {first.id, later.id}


def test_an_unproven_generation_dedupes_only_against_a_held_lease(tmp_path):
    held = manager(Slots(lambda: 1, closed=True)).adopt_uncertain("legacy", "p", "pack", workspace=str(tmp_path))
    rebooted = manager(Slots(lambda: 1, closed=True), boot=20.0)
    rebooted.slots.open()
    assert rebooted.adopt_uncertain("legacy", "p", "pack", workspace=str(tmp_path)).id == held.id
    rebooted.recover(held.id, rebooted=True)
    fresh = rebooted.adopt_uncertain("legacy", "p", "pack", workspace=str(tmp_path))
    assert fresh.id != held.id
    assert fresh.state == "held"


def test_a_workspace_already_in_the_ledger_is_owned_and_not_imported_again(tmp_path):
    owner = manager(Slots(lambda: 1))
    ident = begin(owner, tmp_path)
    assert owner.owns(str(tmp_path))
    assert not owner.owns(str(tmp_path / "other"))
    assert owner.read()["sessions"][0]["id"] == ident
