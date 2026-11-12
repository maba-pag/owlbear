"""Real offline movement preserves ownership, source bytes and the original workspace."""

import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

from owlbear_delivery_next.commands import cli
from owlbear_delivery_next.impeccable_runs import pack_run, pack_state
from owlbear_delivery_next.local_system import codebase, local_home, maintenance
from owlbear_delivery_next.local_system.slots import Slots
from owlbear_delivery_next.machine_host import project
from owlbear_delivery_next.machine_host.machine import Machine
from owlbear_delivery_next.project_host.host import Host, HostRecord
from owlbear_delivery_next.state_store import offline_protocol, pack_run_record, project_home, project_move, registry
from owlbear_delivery_next.state_store.database import MARKER
from owlbear_delivery_next.state_store.store import Store

BEFORE = "AAAAAAAA-0000-4000-8000-000000000011"
AFTER = "BBBBBBBB-0000-4000-8000-000000000012"
STARTED = "2026-01-01T00:00:00+00:00"


@pytest.fixture
def offline(tmp_path, monkeypatch):
    repo = tmp_path / "shop"
    for args in (
        ["init", "-q", "-b", "main", str(repo)],
        ["-C", str(repo), "commit", "-q", "--allow-empty", "-m", "initial"],
    ):
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], check=True)  # noqa: S603, S607
    source = project_home.clone_dir(repo)
    source.mkdir(parents=True)
    (source / MARKER).write_text("7")
    (source / "config.json").write_text(json.dumps({"format": 1, "widths": [1600]}))
    boot = {"id": BEFORE}
    monkeypatch.setattr(offline_protocol, "boot_session", lambda: boot["id"])
    return repo, source, boot


@pytest.fixture
def machines(monkeypatch):
    monkeypatch.setattr(project.readiness, "ready", lambda _store, _repo, **_kwargs: [])
    monkeypatch.setattr(Host, "_spawn", lambda _self, slug: pytest.fail(f"unexpected runner: {slug}"))
    made = []

    def make():
        record = HostRecord(
            url="http://127.0.0.1:9/",
            token="t",  # noqa: S106
            pid=1,
            started_at=datetime.now(UTC),
            code=codebase.CURRENT,
        )
        machine = Machine(record)
        machine.slots.total = lambda: 1
        made.append(machine)
        return machine

    yield make
    for machine in made:
        machine.stop_all()


def write_run(root: Path, fields: dict) -> None:
    record = pack_state.blank() | fields
    if record["state"] == "running":
        record["stage"] = "update"
        next(s for s in record["stages"] if s["name"] == "update")["result"] = "running"
    (root / pack_state.FILE).write_text(json.dumps(record, indent=1) + "\n")


def hold_legacy_run(repo, source, machines, recovered):
    """Import the legacy run through the real unloaded Machine, retaining its original workspace."""
    entry = registry.register(repo)
    (source / MARKER).write_text("99\n")
    write_run(source, {"state": "running"})
    workspace = source / pack_run.UPDATER
    workspace.mkdir()
    sentinel = workspace / "retained-sentinel.txt"
    sentinel.write_text("kept\n")
    first = machines()
    first.load_all()
    [lease] = [s for s in first.maintenance.read()["sessions"] if s["project"] == entry.id]
    [stored] = [s for s in json.loads(first.maintenance.path.read_bytes())["sessions"] if s["id"] == lease["id"]]
    if recovered:
        original_boot = first.maintenance.boot
        first.maintenance.boot = lambda: original_boot() + 1
        first.maintenance.recover(lease["id"], rebooted=True)
    first.stop_all()
    (source / MARKER).write_text("7")
    return entry, lease, stored, workspace, sentinel


@pytest.mark.usefixtures("current_binding")
@pytest.mark.parametrize("recovered", [False, True], ids=["held", "recovered"])
def test_held_generation_survives_prepare_finish_and_restart(offline, machines, recovered):
    repo, source, boot = offline
    entry, lease, stored, workspace, sentinel = hold_legacy_run(repo, source, machines, recovered)
    head = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"])  # noqa: S603, S607
    assert cli.main(["--repo", str(repo), "prepare"]) == 0
    boot["id"] = AFTER
    ledger = local_home.root() / maintenance.FILE
    ledger_bytes = ledger.read_bytes()

    assert cli.main(["--repo", str(repo), "finish"]) == 0
    target = Store.open(repo).root
    assert target != source
    original, carried = source / pack_state.FILE, target / pack_state.FILE
    assert not os.path.samestat(original.stat(), carried.stat())
    settled = original.read_bytes()
    assert carried.read_bytes() == settled
    record = json.loads(settled)
    assert (record["state"], record["reason"]) == ("failed", pack_state.HOST_STOPPED)
    assert record[pack_state.REWRITTEN] == stored["generation"]
    assert ledger.read_bytes() == ledger_bytes
    assert subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"]) == head  # noqa: S603, S607

    again = machines()
    again.load_all()
    [found] = [s for s in again.maintenance.read()["sessions"] if s["project"] == entry.id]
    assert (found["id"], found["state"], found["workspace"]) == (
        lease["id"],
        "recovered" if recovered else "held",
        lease["workspace"],
    )
    assert found["workspace"] == str(workspace)
    assert not workspace.is_relative_to(target)
    assert workspace.is_dir()
    assert sentinel.read_text() == "kept\n"
    assert original.read_bytes() == carried.read_bytes() == settled
    again.stop_all()

    other_repo = repo.parent / "other"
    subprocess.run(["git", "init", "-q", str(other_repo)], check=True, capture_output=True)  # noqa: S603, S607
    subprocess.run(  # noqa: S603
        [  # noqa: S607
            "git",
            "-c",
            "user.name=t",
            "-c",
            "user.email=t@t",
            "-C",
            str(other_repo),
            "commit",
            "-q",
            "--allow-empty",
            "-m",
            "other clone",
        ],
        check=True,
    )
    other = registry.register(other_repo)
    write_run(
        target,
        {
            "state": "failed",
            "run": "run-b",
            "started_at": STARTED,
            "ended_at": "2026-01-01T01:00:00+00:00",
            "reason": "update: RuntimeError: SDK failure",
            "stages": [{"name": "update", "label": "Update", "result": "failed", "detail": "SDK failure"}],
        },
    )
    later = machines()
    later.load_all()
    owned = [s for s in later.maintenance.read()["sessions"] if s["project"] == entry.id]
    assert [(s["id"], s["state"]) for s in owned[:1]] == [(lease["id"], found["state"])]
    [b] = owned[1:]
    assert b["id"] != lease["id"]
    assert b["state"] == "held"
    assert later.slots.take(other.id, "probe", 1, 1) == 0
    assert later.maintenance.pending("pack")
    assert sentinel.read_text() == "kept\n"


@pytest.mark.usefixtures("current_binding")
def test_finish_resumes_copy_without_resettling(offline, monkeypatch):
    repo, source, boot = offline
    assert cli.main(["--repo", str(repo), "prepare"]) == 0
    boot["id"] = AFTER
    write_run(source, {"state": "running", "run": "a", "started_at": STARTED})
    calls = []
    real_settle = pack_run_record.settle

    def counted(*args, **kwargs):
        calls.append(args)
        return real_settle(*args, **kwargs)

    def interrupted(*_args, **_kwargs):
        msg = "interrupted after the copy began"
        raise OSError(msg)

    monkeypatch.setattr(pack_run_record, "settle", counted)
    with monkeypatch.context() as patch:
        patch.setattr(project_move, "_copy_each", interrupted)
        with pytest.raises(OSError, match="interrupted after the copy began"):
            cli.main(["--repo", str(repo), "finish"])
    assert project_move.record(source) is not None
    assert len(calls) == 1
    before = {p.name: p.read_bytes() for p in source.iterdir() if p.is_file()}
    assert cli.main(["--repo", str(repo), "prepare"]) == 0
    assert {p.name: p.read_bytes() for p in source.iterdir() if p.is_file()} == before
    assert cli.main(["--repo", str(repo), "finish"]) == 0
    assert len(calls) == 1
    assert (source / pack_state.FILE).read_bytes() == before[pack_state.FILE]


@pytest.mark.usefixtures("current_binding")
@pytest.mark.parametrize("receipted", [False, True], ids=["absent-ledger", "unregistered-clone-receipt"])
def test_finish_uses_static_clone_receipt_without_a_host(offline, monkeypatch, receipted):
    repo, source, boot = offline
    write_run(source, {"state": "running", "run": "a", "started_at": STARTED})
    clone_id = project_home.ensure_id(source)
    ledger = local_home.root() / maintenance.FILE
    if receipted:
        owner = maintenance.Maintenance(Slots(lambda: 1), boot=lambda: 0.0, observe=lambda *_a: True)
        owner.receipt(clone_id, pack_state.digest(pack_state.observed(source)[1]), "receipt-a")
    before = ledger.read_bytes() if receipted else None
    assert cli.main(["--repo", str(repo), "prepare"]) == 0
    boot["id"] = AFTER
    monkeypatch.setattr(maintenance.Maintenance, "__init__", lambda *_a, **_kw: pytest.fail("Finish starts a manager"))
    assert cli.main(["--repo", str(repo), "finish"]) == 0
    assert (ledger.read_bytes() if ledger.exists() else None) == before
    kept = json.loads((Store.open(repo).root / pack_state.FILE).read_bytes())
    assert kept[pack_state.REWRITTEN] == ("receipt-a" if receipted else f"a:{STARTED}")
    assert (kept["run"], kept["started_at"]) == ("a", STARTED)
    retained = json.loads((source / pack_state.FILE).read_bytes())
    assert retained["run"] == "a"
    assert retained["started_at"] == STARTED
