"""Ghost holds: a modern run whose workspace the ledger already owns is not imported again; a legacy hold still is."""

import json
from datetime import UTC, datetime
from types import SimpleNamespace

from owlbear_delivery_next.local_system import maintenance
from owlbear_delivery_next.local_system.slots import Slots
from owlbear_delivery_next.project_host import session_slots

AT = datetime(2026, 10, 25, tzinfo=UTC)
STARTED = "2026-10-25T00:00:00+00:00"


def owner_with_lease(workspace):
    owner = maintenance.Maintenance(Slots(lambda: 1), boot=lambda: 10.0)
    assert owner.slots.take("p", "pack:one", 1, 1) == 1
    owner.begin("p", "pack:one", "pack", str(workspace), now=AT)
    return owner


def job_for(owner, root, interrupted=None, state=None, version="1:2:3:4"):
    return SimpleNamespace(
        maintenance=owner,
        store=SimpleNamespace(root=root),
        interrupted=interrupted,
        state=state or {},
        version=version,
    )


def test_an_interrupted_modern_run_the_ledger_owns_is_not_held_twice(tmp_path):
    workspace = tmp_path / "runs" / "r1"
    owner = owner_with_lease(workspace)
    before = len(owner.read()["sessions"])
    run = {"run": "r1", "started_at": STARTED, "workspace": str(workspace), "generation": "r1"}
    session_slots.interrupted(job_for(owner, tmp_path, interrupted=run), "p")
    assert len(owner.read()["sessions"]) == before


def test_an_interrupted_modern_run_in_an_unowned_workspace_is_still_held(tmp_path):
    owner = owner_with_lease(tmp_path / "runs" / "r1")
    before = len(owner.read()["sessions"])
    run = {"run": "r2", "started_at": STARTED, "workspace": str(tmp_path / "runs" / "r2"), "generation": "r2"}
    session_slots.interrupted(job_for(owner, tmp_path, interrupted=run), "p")
    assert len(owner.read()["sessions"]) == before + 1


def test_an_unloaded_modern_run_the_ledger_owns_is_not_held_twice(tmp_path, monkeypatch):
    """Review 4378036761: the record reaches the ownership check through the reader the restoration really uses."""
    workspace = tmp_path / "runs" / "r1"
    owner = owner_with_lease(workspace)
    before = len(owner.read()["sessions"])
    kept = {"state": "running", "run": "r1", "started_at": STARTED, "workspace": str(workspace)}
    monkeypatch.setattr(session_slots.project_home, "current", lambda _repo: tmp_path)
    monkeypatch.setattr(session_slots.pack_job, "observed", lambda _root: (kept, "1:2:3:4:5"))
    asked: list[str] = []
    real_owns = owner.owns
    monkeypatch.setattr(owner, "owns", lambda path: asked.append(path) or real_owns(path))
    session_slots.unloaded(owner, "p", tmp_path)
    assert (asked, len(owner.read()["sessions"])) == ([str(workspace)], before)


def test_the_unloaded_ownership_check_is_what_keeps_a_modern_run_from_a_second_hold(tmp_path, monkeypatch):
    """Negative control: with the ownership check answering no, the same record is held again."""
    workspace = tmp_path / "runs" / "r1"
    owner = owner_with_lease(workspace)
    before = len(owner.read()["sessions"])
    kept = {"state": "running", "run": "r1", "started_at": STARTED, "workspace": str(workspace)}
    monkeypatch.setattr(session_slots.project_home, "current", lambda _repo: tmp_path)
    monkeypatch.setattr(session_slots.pack_job, "observed", lambda _root: (kept, "1:2:3:4:5"))
    monkeypatch.setattr(owner, "owns", lambda _path: False)
    session_slots.unloaded(owner, "p", tmp_path)
    assert len(owner.read()["sessions"]) == before + 1


def test_a_genuine_legacy_uncertain_run_is_still_held_with_its_generation(tmp_path):
    (tmp_path / session_slots.pack_run.UPDATER).mkdir()
    owner = maintenance.Maintenance(Slots(lambda: 1), boot=lambda: 10.0)
    record = session_slots.pack_state.blank() | {"state": "running", "run": "legacy-1", "started_at": STARTED}
    (tmp_path / session_slots.pack_state.FILE).write_text(json.dumps(record))  # the record the Job read, on disk
    state, version = session_slots.pack_state.read_version(tmp_path / session_slots.pack_state.FILE)
    session_slots.interrupted(job_for(owner, tmp_path, state=state, version=version), "p")
    (lease,) = owner.read()["sessions"]
    assert lease["state"] == "held"
    session_slots.interrupted(job_for(owner, tmp_path, state=state, version=version), "p")
    assert len(owner.read()["sessions"]) == 1
