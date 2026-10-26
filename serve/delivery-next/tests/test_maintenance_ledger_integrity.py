"""Review on 8ad: the ledger is read only whole, and a session whose caller a reboot ended stays the owner's to recover.

A persisted ledger always carries every field it is written with, so one without them is a fault, never an empty
ledger; only a missing file is. A running lease from before a reboot proves its caller ended, never its SDK session: it
is held, listed and recoverable by the owner, not released. One of this boot whose caller cannot be inspected stays
running.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import psutil
import pytest
from fastapi.testclient import TestClient

from owlbear_delivery_next.change_contracts import tools
from owlbear_delivery_next.change_contracts.models import StepKind
from owlbear_delivery_next.change_contracts.permissions import Policy
from owlbear_delivery_next.local_system import codebase, maintenance, processes
from owlbear_delivery_next.local_system.slots import Slots
from owlbear_delivery_next.machine_host import app, project
from owlbear_delivery_next.machine_host.machine import Machine
from owlbear_delivery_next.project_host.host import Host, HostRecord
from owlbear_delivery_next.runtimes import maintained, sdk_adapter

AT = datetime(2026, 10, 25, tzinfo=UTC)
FIELDS = ("format", "sessions", "imported")


def uninspectable(*_args: object) -> None:
    """A process whose identity cannot be read: neither alive nor gone."""


def held_ledger(tmp_path: Path) -> maintenance.Maintenance:
    """A ledger with one uncertain pack session holding its slot, written whole."""
    owner = maintenance.Maintenance(Slots(lambda: 2), boot=lambda: 10.0, observe=lambda *_a: False)
    assert owner.slots.take("p", "pack:one", 1, 1) == 1
    owner.failed(owner.begin("p", "pack:one", "pack", str(tmp_path), now=AT), RuntimeError("no Run returned"))
    return owner


def session(root: Path) -> sdk_adapter.Session:
    return sdk_adapter.Session(
        kind=StepKind.REVIEW, worktree=root, session_id="synthetic", message="Synthetic work", resume=False,
        policy=Policy(root), observe=lambda: tools.Worktree("", ""), checks=(), model="synthetic-model",
    )  # fmt: skip


@pytest.mark.parametrize("missing", FIELDS)
def test_a_persisted_ledger_without_a_field_it_is_always_written_with_is_a_visible_fault_not_empty(tmp_path, missing):
    owner = held_ledger(tmp_path)
    whole = json.loads(owner.path.read_text())
    del whole[missing]
    owner.path.write_text(json.dumps(whole))
    before = owner.path.read_bytes()

    with pytest.raises(maintenance.MaintenanceError, match=f"fields {missing} are missing"):
        maintenance.Maintenance(Slots(lambda: 1), boot=lambda: 10.0)  # a restart reads it: no empty ledger, no grant

    entered: list[str] = []
    assert owner.slots.take("p", "pack:two", 1, 2) == 1
    with pytest.raises(maintenance.MaintenanceError, match="could not be read"):
        maintained.run_owned(owner, session(tmp_path), lambda cfg: entered.append(cfg.session_id), project="p",
                             slot="pack:two", kind="pack")  # fmt: skip
    with pytest.raises(maintenance.MaintenanceError), owner.workspace("synthetic-maintenance-") as kept:
        pass  # whether a lease retains it cannot be read, so it is not removed
    assert (entered, owner.slots.counts("p")[2], kept.is_dir(), owner.path.read_bytes()) == ([], 1, True, before)
    kept.rmdir()


def test_the_exact_reviewed_ledger_with_only_format_and_imported_is_refused():
    path = maintenance.Maintenance(Slots(lambda: 1), boot=lambda: 10.0).path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{"format":1,"imported":[]}')
    with pytest.raises(maintenance.MaintenanceError, match="fields sessions are missing"):
        maintenance.Maintenance(Slots(lambda: 1), boot=lambda: 10.0)
    assert path.read_text() == '{"format":1,"imported":[]}'


def test_a_whole_empty_ledger_and_a_lease_written_before_observed_existed_are_still_read(tmp_path):
    """Controls: a missing file and a whole empty ledger are empty; a lease field added later keeps its default."""
    owner = maintenance.Maintenance(Slots(lambda: 1), boot=lambda: 10.0)
    assert owner.read() == {"sessions": []}
    owner.path.parent.mkdir(parents=True, exist_ok=True)
    owner.path.write_text(maintenance.Ledger().model_dump_json())
    assert maintenance.Maintenance(Slots(lambda: 1), boot=lambda: 10.0).read() == {"sessions": []}
    held_ledger(tmp_path)
    older = json.loads(owner.path.read_text())
    del older["sessions"][0]["observed"]
    owner.path.write_text(json.dumps(older))
    slots = Slots(lambda: 1)
    [lease] = maintenance.Maintenance(slots, boot=lambda: 10.0).read()["sessions"]
    assert (lease["state"], slots.counts("p")[2]) == ("held", 1)


def running_lease(boot: float) -> maintenance.Maintenance:
    """A session admitted under *boot* whose caller never wrote its end."""
    owner = maintenance.Maintenance(Slots(lambda: 1), boot=lambda: boot, observe=uninspectable)
    assert owner.slots.take("p", "pack:one", 1, 1) == 1
    owner.begin("p", "pack:one", "pack", "", now=AT)
    return owner


def test_a_running_lease_from_before_a_reboot_is_held_for_recovery_even_when_its_caller_cannot_be_inspected():
    running_lease(10.0)
    slots = Slots(lambda: 1)
    after = maintenance.Maintenance(slots, boot=lambda: 20.0, observe=uninspectable)
    [lease] = after.read()["sessions"]
    assert (lease["state"], lease["recoverable"], slots.counts("p")[2], after.pending("pack")) == (
        "held", True, 1, True,
    )  # fmt: skip
    after.sweep()  # nothing positively proves its session ended: it is not released
    assert after.read()["sessions"][0]["state"] == "held"
    after.recover(lease["id"], rebooted=True)
    ended = (after.read()["sessions"][0]["state"], slots.counts("p")[2], after.pending("pack"))
    assert ended == ("recovered", 0, False)


def test_a_running_lease_of_this_boot_whose_caller_cannot_be_inspected_stays_running_and_owned():
    running_lease(10.0)
    slots = Slots(lambda: 1)
    same = maintenance.Maintenance(slots, boot=lambda: 10.0, observe=uninspectable)
    [lease] = same.read()["sessions"]
    assert (lease["state"], lease["recoverable"], slots.counts("p")[2]) == ("running", False, 1)
    with pytest.raises(ValueError, match="reboot"):
        same.recover(lease["id"], rebooted=True)  # only a held session from an earlier boot is the owner's to recover


def test_an_unreadable_boot_proves_nothing_and_changes_nothing():
    running_lease(10.0)
    path = maintenance.Maintenance(Slots(lambda: 1), boot=lambda: 10.0, observe=uninspectable).path
    before = path.read_bytes()

    def unknown() -> float:
        msg = "synthetic: the boot time cannot be read"
        raise OSError(msg)

    with pytest.raises(OSError, match="boot time cannot be read"):
        maintenance.Maintenance(Slots(lambda: 1), boot=unknown, observe=uninspectable)
    assert path.read_bytes() == before


@pytest.mark.parametrize("rebooted", [True, False], ids=["older-boot", "this-boot"])
def test_the_machine_lists_and_recovers_a_session_whose_caller_a_reboot_ended(monkeypatch, rebooted):
    """The machine's own page API: held and recoverable after a reboot, owned and running on the same boot."""
    running_lease(psutil.boot_time() - (100 if rebooted else 0))
    monkeypatch.setattr(processes, "alive", uninspectable)  # the former caller's PID is now an uninspectable process
    monkeypatch.setattr(project.readiness, "ready", lambda _store, _repo: [])
    monkeypatch.setattr(Host, "_spawn", lambda _self, slug: pytest.fail(f"no runner starts in these tests ({slug})"))
    now = datetime.now(UTC)
    machine = Machine(HostRecord(url="http://127.0.0.1:9/", token="t", pid=1, started_at=now, code=codebase.CURRENT))  # noqa: S106
    try:
        served = app.create(machine)
        http = TestClient(served, base_url="http://127.0.0.1", headers={"authorization": served.expected.decode()})
        [listed] = http.get("/api/next/maintenance/sessions").json()["sessions"]
        assert (listed["state"], listed["recoverable"], machine.slots.counts("p")[2]) == (
            ("held", True, 1) if rebooted else ("running", False, 1)
        )
        answer = http.post(f"/api/next/maintenance/sessions/{listed['id']}/recover", json={"rebooted": True})
        assert answer.status_code == (200 if rebooted else 409), answer.text
        assert machine.slots.counts("p")[2] == (0 if rebooted else 1)
    finally:
        machine.stop_all()
