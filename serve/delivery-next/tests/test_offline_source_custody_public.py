"""Public offline commands keep source custody across verification and blocking receipt reads."""

import json
import os
import shutil
import stat
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from owlbear_delivery_next.commands import cli
from owlbear_delivery_next.impeccable_runs import pack_state
from owlbear_delivery_next.local_system import local_home, maintenance
from owlbear_delivery_next.machine_host import selfcheck
from owlbear_delivery_next.state_store import (
    fd_tree,
    offline_protocol,
    pack_run_record,
    project_home,
    project_move,
    registry,
)
from owlbear_delivery_next.state_store.database import MARKER, StoreError
from owlbear_delivery_next.state_store.store import Store

BEFORE = "AAAAAAAA-0000-4000-8000-000000000001"
AFTER = "BBBBBBBB-0000-4000-8000-000000000002"
pytestmark = pytest.mark.usefixtures("current_binding")


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    repo = tmp_path / "shop"
    subprocess.run(["git", "init", "-q", str(repo)], check=True, capture_output=True)  # noqa: S603, S607
    folder = project_home.clone_dir(repo)
    folder.mkdir()
    (folder / MARKER).write_text("7\n")
    (folder / "config.json").write_text(json.dumps({"format": 1, "widths": [1600]}))
    run = pack_state.blank() | {"state": "running", "run": "a", "started_at": "2026-01-01T00:00:00+00:00"}
    (folder / pack_state.FILE).write_text(json.dumps(run))
    monkeypatch.setattr(offline_protocol, "boot_session", lambda: BEFORE)
    assert cli.main(["--repo", str(repo), "prepare"]) == 0
    monkeypatch.setattr(offline_protocol, "boot_session", lambda: AFTER)
    return repo, folder


def snapshot(folder):
    return {str(p.relative_to(folder)): p.read_bytes() if p.is_file() else None for p in folder.rglob("*")}


def refused(repo):
    try:
        return cli.main(["--repo", str(repo), "finish"]) == 1
    except StoreError:
        return True


@pytest.mark.parametrize("alias", [False, True], ids=["replacement", "directory-alias"])
def test_source_swapped_after_finish_verification_is_never_settled(prepared, monkeypatch, alias):
    repo, folder = prepared
    aside = folder.with_name("original")
    foreign = folder.with_name("foreign")
    shutil.copytree(folder, foreign)
    before, foreign_before = snapshot(folder), snapshot(foreign)
    target = project_home.home(project_home.clone_id(folder))
    real_finish = offline_protocol.finish
    fired = []

    def finish(*args, **kwargs):
        proof = real_finish(*args, **kwargs)
        folder.rename(aside)
        if alias:
            folder.symlink_to(foreign, target_is_directory=True)
        else:
            foreign.rename(folder)
        fired.append(True)
        return proof

    monkeypatch.setattr(offline_protocol, "finish", finish)
    assert refused(repo)
    assert fired == [True]
    assert snapshot(aside) == before
    assert snapshot(foreign if alias else folder) == foreign_before
    assert not target.exists()


@pytest.mark.parametrize(
    "change", ["replacement", "directory-alias", "preparation", "run-version", "run-in-place", "clone-id"]
)
def test_source_change_during_blocking_receipt_read_is_refused_before_any_mutation(prepared, monkeypatch, change):
    repo, folder = prepared
    aside, foreign = folder.with_name("original"), folder.with_name("foreign")
    shutil.copytree(folder, foreign)
    original, foreign_before = snapshot(folder), snapshot(foreign)
    target = project_home.home(project_home.clone_id(folder))
    ledger = local_home.root() / maintenance.FILE
    ledger.write_text('{"foreign": "unchanged"}')
    ledger_before = ledger.read_bytes()
    entered, release = threading.Event(), threading.Event()
    asked = []

    def lookup(key, digest):
        asked.append((key, digest))
        entered.set()
        assert release.wait(10), "the receipt lookup was never released"
        return ""

    monkeypatch.setattr(maintenance.Maintenance, "lookup_receipt", staticmethod(lookup))
    with ThreadPoolExecutor(max_workers=1) as pool:
        result = pool.submit(refused, repo)
        try:
            assert entered.wait(10), "the real settlement never reached its receipt lookup"
            if change in {"replacement", "directory-alias"}:
                folder.rename(aside)
                if change == "replacement":
                    foreign.rename(folder)
                else:
                    folder.symlink_to(foreign, target_is_directory=True)
                expected = original
            else:
                name = {"preparation": offline_protocol.PREPARED, "clone-id": project_home.CLONE_ID}.get(
                    change, pack_state.FILE
                )
                path = folder / name
                text = "FOREIGN\n" if change == "clone-id" else path.read_text() + " "
                if change != "run-in-place":
                    path.unlink()
                path.write_text(text)
                expected = snapshot(folder)
        finally:
            release.set()
        assert result.result(timeout=10), "Finish admitted a source changed during the blocking lookup"
    assert asked, "the race injection did not fire"
    assert snapshot(aside if aside.exists() else folder) == expected
    assert snapshot(foreign if foreign.exists() else folder) == foreign_before
    assert ledger.read_bytes() == ledger_before
    assert not target.exists()
    assert not (local_home.root() / project_home.PROJECTS).exists()


def test_settlement_reads_the_original_descriptor_when_the_directory_name_is_replaced(prepared, monkeypatch):
    repo, folder = prepared
    aside, foreign = folder.with_name("original"), folder.with_name("foreign")
    shutil.copytree(folder, foreign)
    original, foreign_before = snapshot(folder), snapshot(foreign)
    target = project_home.home(project_home.clone_id(folder))
    real_open = pack_run_record.open_record
    fired = []

    def open_record(path, **kwargs):
        folder.rename(aside)
        foreign.rename(folder)
        fd = real_open(path, **kwargs)
        assert os.path.samestat(os.fstat(fd), (aside / pack_state.FILE).stat())
        assert not os.path.samestat(os.fstat(fd), (folder / pack_state.FILE).stat())
        fired.append(True)
        return fd

    monkeypatch.setattr(pack_run_record, "open_record", open_record)
    assert refused(repo)
    assert fired == [True], "the descriptor-bound read never ran"
    assert snapshot(aside) == original
    assert snapshot(folder) == foreign_before
    assert not target.exists()


@pytest.mark.parametrize("change", ["owner-run", "replacement", "preparation", "clone-id"])
def test_finish_refuses_changes_during_real_temporary_sync_before_publishing_the_run(prepared, monkeypatch, change):
    repo, folder = prepared
    aside, foreign = folder.with_name("original"), folder.with_name("foreign")
    shutil.copytree(folder, foreign)
    foreign_before = snapshot(foreign)
    target = project_home.home(project_home.clone_id(folder))
    ledger = local_home.root() / maintenance.FILE
    ledger_before = ledger.read_bytes() if ledger.exists() else None
    fired, expected = [], {}

    class SyncingOS:
        def __getattr__(self, name):
            return getattr(os, name)

        def fsync(self, fd):
            os.fsync(fd)
            if fired or not stat.S_ISREG(os.fstat(fd).st_mode):
                return
            temporary = next(folder.glob(f".tmp-{pack_state.FILE}-*"), None)
            if temporary is None:
                return
            assert os.path.samestat(os.fstat(fd), temporary.stat())
            fired.append(True)
            if change == "replacement":
                folder.rename(aside)
                foreign.rename(folder)
            elif change == "owner-run":
                owner = folder / "owner-b"
                owner.write_text(json.dumps(pack_state.blank() | {"state": "running", "run": "OWNER-B"}))
                owner.replace(folder / pack_state.FILE)
            else:
                name = offline_protocol.PREPARED if change == "preparation" else project_home.CLONE_ID
                path = folder / name
                path.write_text(path.read_text() + (" " if change == "preparation" else "FOREIGN\n"))
            expected.update(snapshot(aside if aside.exists() else folder))
            del expected[temporary.name]

    monkeypatch.setattr(fd_tree, "os", SyncingOS())
    was_refused = refused(repo)
    assert fired == [True], "the real temporary sync injection never ran"
    assert was_refused, "Finish overwrote a run after its temporary sync changed the source"
    held = aside if aside.exists() else folder
    kept = list(held.glob(fd_tree.QUARANTINE + "*"))
    assert len(kept) == 1
    assert json.loads(kept[0].read_text())[pack_state.REWRITTEN]
    assert snapshot(held) == expected | {kept[0].name: kept[0].read_bytes()}
    assert snapshot(foreign if foreign.exists() else folder) == foreign_before
    assert (ledger.read_bytes() if ledger.exists() else None) == ledger_before
    assert not target.exists()
    assert not (local_home.root() / project_home.PROJECTS).exists()
    before_retry = snapshot(held)
    assert refused(repo), "a quarantined candidate must not be retried automatically"
    assert snapshot(held) == before_retry, "a refused retry settled the owner's replacement run"
    assert (ledger.read_bytes() if ledger.exists() else None) == ledger_before
    assert not (local_home.root() / project_home.PROJECTS).exists()


@pytest.mark.parametrize("alias", [False, True], ids=["replacement", "directory-alias"])
def test_descriptor_write_cannot_follow_a_source_swap_after_its_final_guard(prepared, monkeypatch, alias):
    """The residual check-to-I/O window can write the original only, never the replacement folder."""
    repo, folder = prepared
    aside, foreign = folder.with_name("original"), folder.with_name("foreign")
    shutil.copytree(folder, foreign)
    original, foreign_before = snapshot(folder), snapshot(foreign)
    target = project_home.home(project_home.clone_id(folder))
    fired = []

    class RenamingOS:
        def __getattr__(self, name):
            return getattr(os, name)

        def rename(self, src, dst, *, src_dir_fd, dst_dir_fd):
            if dst == pack_state.FILE:
                assert os.path.samestat(os.fstat(dst_dir_fd), folder.stat())
                folder.rename(aside)
                if alias:
                    folder.symlink_to(foreign, target_is_directory=True)
                else:
                    foreign.rename(folder)
                assert os.path.samestat(os.fstat(dst_dir_fd), aside.stat())
                fired.append(True)
            return os.rename(src, dst, src_dir_fd=src_dir_fd, dst_dir_fd=dst_dir_fd)

    monkeypatch.setattr(fd_tree, "os", RenamingOS())
    assert refused(repo)
    assert fired == [True], "the descriptor-bound write never ran"
    settled = json.loads((aside / pack_state.FILE).read_text())
    assert settled["state"] == "failed"
    assert settled[pack_state.REWRITTEN]
    assert snapshot(aside) == original | {pack_state.FILE: (aside / pack_state.FILE).read_bytes()}
    assert snapshot(foreign if alias else folder) == foreign_before
    assert not target.exists()


def completed(prepared):
    repo, folder = prepared
    assert cli.main(["--repo", str(repo), "finish"]) == 0
    target = Store.open(repo).root
    pid = project_home.clone_id(folder)
    registry.register(repo)
    return repo, folder, target, pid


@pytest.mark.parametrize(
    "damage", ["truncated", "boot-type", "boot-uuid", "extra-key", "missing-key", "folder-type", "folder-id", "copied"]
)
def test_all_switched_consumers_refuse_incomplete_or_foreign_preparation_before_marker_repair(prepared, damage):
    repo, folder, target, pid = completed(prepared)
    aside = folder.with_name("original")
    path = folder / offline_protocol.PREPARED
    record = json.loads(path.read_text())
    if damage == "copied":
        folder.rename(aside)
        shutil.copytree(aside, folder)
        assert not os.path.samestat(folder.stat(), aside.stat())
    elif damage == "truncated":
        path.write_text("{")
    else:
        if damage == "boot-type":
            record["boot"] = 7
        elif damage == "boot-uuid":
            record["boot"] = "not-a-uuid"
        elif damage == "extra-key":
            record["extra"] = True
        elif damage == "missing-key":
            del record["boot"]
        elif damage == "folder-type":
            record["folder"] = [True, record["folder"][1]]
        elif damage == "folder-id":
            record["folder"][1] += 1
        path.write_text(json.dumps(record))
    (target / MARKER).unlink()
    before, target_before = snapshot(folder), snapshot(target)
    old_before = snapshot(aside) if aside.exists() else None
    ledger_before = snapshot(local_home.root())

    with pytest.raises(StoreError):
        Store.open(repo)
    with pytest.raises(StoreError):
        project_home.current(repo)
    with pytest.raises(registry.RegistryError):
        registry.register(repo)
    with pytest.raises(registry.RegistryError):
        registry.adopt(pid)
    assert selfcheck._project(pid, repo)  # noqa: SLF001
    assert snapshot(folder) == before
    assert snapshot(target) == target_before
    assert snapshot(local_home.root()) == ledger_before
    if old_before is not None:
        assert snapshot(aside) == old_before


@pytest.mark.parametrize("receipt", ["switched", "null", "{", "[]"])
def test_repeated_prepare_reads_receipt_before_retained_payload_and_writes_nothing(prepared, receipt):
    repo, folder, target, _pid = completed(prepared)
    if receipt != "switched":
        (folder / project_move.MOVE_RECORD).write_text(receipt)
    assert (folder / pack_state.FILE).exists(), "the completed source payload must be retained"
    before, target_before = snapshot(folder), snapshot(target)
    assert cli.main(["--repo", str(repo), "prepare"]) == 1
    assert snapshot(folder) == before
    assert snapshot(target) == target_before


def test_repeated_prepare_preserves_its_boot_prior_and_generation(prepared):
    repo, folder = prepared
    before = snapshot(folder)
    assert cli.main(["--repo", str(repo), "prepare"]) == 0
    assert snapshot(folder) == before
    assert cli.main(["--repo", str(repo), "finish"]) == 0
