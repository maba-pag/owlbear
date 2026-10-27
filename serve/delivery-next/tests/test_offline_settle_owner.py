"""An offline move settles the design pack run record through the store's own module, before anything is copied.

These controls are direct: no trust binding, no Prepare or Finish and no copy, so they do not depend on the catalog.
The gated move and its copy are covered by the public offline tests.
"""

import json
from pathlib import Path

import pytest

from owlbear_delivery_next.local_system import maintenance
from owlbear_delivery_next.pack_runs import pack_state
from owlbear_delivery_next.state_store import offline_protocol, pack_run_record, project_home, project_move
from owlbear_delivery_next.state_store.database import StoreError

RUN, STARTED = "run-a", "2026-10-15T10:00:00+00:00"
RECEIPTED = "receipted-gen-1"


def legacy_run(folder: Path) -> Path:
    """A run an older host left running, with no workspace and no generation: its settlement must carry one."""
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / pack_state.FILE
    path.write_text(json.dumps(pack_state.blank() | {"state": "running", "run": RUN, "started_at": STARTED}) + "\n")
    return path


def test_the_move_settles_the_record_through_the_store_owned_module(tmp_path, monkeypatch):
    folder = tmp_path / "store"
    path = legacy_run(folder)
    project_home.ensure_id(folder)
    settled = []
    real_settle = pack_run_record.settle

    def spy(root, *, receipted, **kwargs):
        settled.append(root)
        return real_settle(root, receipted=receipted, **kwargs)

    monkeypatch.setattr(pack_run_record, "settle", spy)
    monkeypatch.setattr(maintenance.Maintenance, "lookup_receipt", staticmethod(lambda _key, _digest: ""))
    offline_protocol._settle_pack_run(folder)  # noqa: SLF001
    assert settled == [folder], "the move did not settle the run record through the store's module"
    record = json.loads(path.read_text())
    assert (record["state"], record[pack_run_record.REWRITTEN] != "") == ("failed", True)


def test_a_receipted_legacy_run_keeps_its_receipted_generation_and_is_read_by_the_clone_id(tmp_path, monkeypatch):
    folder = tmp_path / "store"
    path = legacy_run(folder)
    clone_id = project_home.ensure_id(folder)
    digest = pack_run_record.digest(pack_run_record.observed(folder)[1])
    asked = []

    def receipt(key, found):
        asked.append((key, found))
        return RECEIPTED if found == digest else ""

    monkeypatch.setattr(maintenance.Maintenance, "lookup_receipt", staticmethod(receipt))
    offline_protocol._settle_pack_run(folder)  # noqa: SLF001
    assert asked == [(clone_id, digest)], "the receipt was not read by the clone's id for this file version"
    record = json.loads(path.read_text())
    assert (record["state"], record[pack_run_record.REWRITTEN], record["reason"]) == (
        "failed",
        RECEIPTED,
        pack_run_record.HOST_STOPPED,
    )


def test_an_unreadable_ledger_refuses_before_the_record_or_any_move_changes(tmp_path, monkeypatch):
    folder = tmp_path / "store"
    path = legacy_run(folder)
    project_home.ensure_id(folder)
    before = path.read_bytes()
    asked = []

    def unreadable(key, _digest):
        asked.append(key)
        msg = "ledger is unreadable"
        raise maintenance.MaintenanceError(msg)

    monkeypatch.setattr(maintenance.Maintenance, "lookup_receipt", staticmethod(unreadable))
    with pytest.raises(StoreError, match=r"could not be settled.*nothing was moved"):
        offline_protocol._settle_pack_run(folder)  # noqa: SLF001
    assert asked, "the receipt lookup never ran, so the refusal proves nothing"
    assert path.read_bytes() == before
    assert project_move.record(folder) is None


def test_a_folder_without_a_clone_id_is_refused_before_its_record_is_touched(tmp_path):
    folder = tmp_path / "store"
    path = legacy_run(folder)
    before = path.read_bytes()
    with pytest.raises(StoreError, match="no clone id"):
        offline_protocol._settle_pack_run(folder)  # noqa: SLF001
    assert path.read_bytes() == before


@pytest.mark.parametrize(
    "name",
    [
        "FILE",
        "HOST_STOPPED",
        "REWRITTEN",
        "STATES",
        "digest",
        "ended",
        "generation",
        "last",
        "legacy_uncertain",
        "now",
        "observed",
        "read_only",
        "resolved",
        "version_of",
    ],
)
def test_the_job_reads_the_run_record_through_the_owner_without_a_second_copy(name):
    assert getattr(pack_state, name) is getattr(pack_run_record, name)
