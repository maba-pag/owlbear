"""The project's Delivery database and the import of the file format (TD-265, machine-host-build §7)."""

from __future__ import annotations

import json
import subprocess
import sys
import threading
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from owlbear_delivery_next.change_contracts.inbox import BriefApproval, IntentItem
from owlbear_delivery_next.change_contracts.models import FORMAT, Brief, Change
from owlbear_delivery_next.commands.mcp_server import Chat
from owlbear_delivery_next.machine_host import registry
from owlbear_delivery_next.machine_host.project import ImportWaitingError, Project
from owlbear_delivery_next.project_host import config_routes
from owlbear_delivery_next.state_store import database
from owlbear_delivery_next.state_store.database import STORE_FORMAT, LateWriteError, NotImportedError, StoreError
from owlbear_delivery_next.state_store.store import Store

NOW = datetime(2026, 10, 18, 12, tzinfo=UTC)
FILE_ERA = 5  # the last Change format a runtime that reads Change files knew (TD-265)
WRITER = """
import sys
from pathlib import Path
from owlbear_delivery_next.change_contracts.models import Change
from owlbear_delivery_next.state_store.store import Store
store = Store(Path(sys.argv[1]))
with store.lock("c2") as lock:
    for n in range(60):
        store.write(lock, Change(slug="c2", profile_version=n))
        store.log(lock, "c2", {"event": "wrote", "n": n})
"""


def legacy(root: Path, *, acked: bool = False) -> Path:
    """A store as the file format left it: a Change with its previous record, an inbox, activity and handles."""
    folder = root / "changes" / "c1"
    (folder / "inbox").mkdir(parents=True)
    (root / "format").write_text(f"{FORMAT}\n")
    old = Change(slug="c1", brief=Brief(version=1, challenged=1))
    item = BriefApproval(at=NOW, version=1).model_dump_json()
    (folder / "inbox" / "00000000000000000001-aaaaaaaa.json").write_text(item)
    current = old.model_copy(update={"profile_version": 2, "inbox_acked": ["00000000000000000001-aaaaaaaa.json"]})
    (folder / "change.json").write_text((current if acked else old).model_dump_json())
    (folder / "change.json.prev").write_text(old.model_copy(update={"profile_version": 1}).model_dump_json())
    (folder / "activity.jsonl").write_text('{"event": "started", "at": "2026-10-18T11:00:00+00:00"}\n')
    (folder / "now.json").write_text('{"tool": "edit"}')
    (root / "handles.json").write_text('{"issued": 7}')
    return folder


def imported(root: Path) -> Store:
    store = Store(root)
    store.db.import_files()
    return Store(root)  # a fresh process's view


def test_a_store_of_the_file_format_is_refused_until_the_machine_host_imports_it(tmp_path) -> None:
    folder = legacy(tmp_path)
    with pytest.raises(NotImportedError) as refused:
        Store(tmp_path).slugs()
    assert "owlbear start" in refused.value.stop(NOW).action
    store = imported(tmp_path)

    assert (store.slugs(), store.issued(), store.now("c1"), [e["event"] for e in store.events("c1")]) == (
        ["c1"], 7, {"tool": "edit"}, ["started"]
    )  # fmt: skip
    with store.lock("c1") as lock:
        assert len(store.fold(lock, "c1", NOW)[0].brief.approved) == 1  # the inbox item, taken once
        store.restore(lock, "c1")
    assert store.read("c1").brief.approved == []  # the record before the fold
    assert (tmp_path / "format").read_text() == f"{STORE_FORMAT}\n"
    assert (list(folder.rglob("*.json")), (tmp_path / "handles.json").exists()) == ([], False)
    assert (folder / "change.json.imported").exists()


def test_an_item_folded_before_a_crash_kept_its_file_is_not_imported_again(tmp_path) -> None:
    legacy(tmp_path, acked=True)
    store = imported(tmp_path)
    with store.lock("c1") as lock:
        assert store.fold(lock, "c1", NOW)[0].brief.approved == []


@pytest.mark.parametrize("boundary", ["fill", "publish", "wal", "retire"])
def test_a_crash_at_each_import_boundary_resumes_without_loss_or_repeat(tmp_path, monkeypatch, boundary) -> None:
    legacy(tmp_path)
    where = {"fill": "_fill", "publish": "_fsync", "wal": "_wal", "retire": "_retire"}[boundary]
    owner = database if boundary == "publish" else database.Database

    def crashed(*_args) -> None:
        msg = f"crashed at {boundary}"
        raise OSError(msg)

    with monkeypatch.context() as patched:
        patched.setattr(owner, where, crashed)
        with pytest.raises((OSError, StoreError), match="crashed"):
            Store(tmp_path).db.import_files()
    if boundary == "fill":  # the fence: an older runtime refuses a marker above its format before reading a file
        assert int((tmp_path / "format").read_text()) > FILE_ERA  # what the older Store.open compares
        assert ((tmp_path / database.DB).exists(), (tmp_path / "changes" / "c1" / "change.json").exists()) == (
            False,
            True,
        )
        with pytest.raises(NotImportedError):
            Store(tmp_path).read("c1")
    if boundary in {"wal", "retire"}:  # published: the next open sets WAL and retires the files the ledger names
        assert ((tmp_path / database.DB).exists(), (tmp_path / "changes" / "c1" / "change.json").exists()) == (
            True,
            True,
        )
        store = Store(tmp_path)
        assert store.slugs() == ["c1"]
    else:  # the files are still authoritative and the import runs again
        store = imported(tmp_path)
    assert not (tmp_path / "changes" / "c1" / "change.json").exists()
    with store.db.read() as db:
        assert db.execute("PRAGMA journal_mode").fetchone() == ("wal",)
    with store.lock("c1") as lock:
        assert len(store.fold(lock, "c1", NOW)[0].brief.approved) == 1
        assert len(store.fold(lock, "c1", NOW)[0].brief.approved) == 1


def test_an_inbox_file_an_older_process_drops_after_the_import_is_applied_once(tmp_path, monkeypatch) -> None:
    """Including a crash between taking the file into the database and retiring it."""
    folder = legacy(tmp_path, acked=True)
    store = imported(tmp_path)
    late = folder / "inbox" / "00000000000000000002-bbbbbbbb.json"
    late.write_text(BriefApproval(at=NOW, version=1).model_dump_json())  # an older chat server, open all along
    real = Path.rename

    def lost(self, target):
        if self == late:
            msg = "crashed before retiring"
            raise OSError(msg)
        return real(self, target)

    with monkeypatch.context() as patched, store.lock("c1") as lock:
        patched.setattr(Path, "rename", lost)
        with pytest.raises(OSError, match="before retiring"):
            store.fold(lock, "c1", NOW)
    with store.lock("c1") as lock:
        assert len(store.fold(lock, "c1", NOW)[0].brief.approved) == 1
        assert len(store.fold(lock, "c1", NOW)[0].brief.approved) == 1
    assert not late.exists()


def test_a_chat_server_open_across_the_import_reads_the_database_after_it(tmp_path) -> None:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)  # noqa: S603, S607
    root = tmp_path / ".git" / "owlbear-delivery"
    legacy(root)
    chat = Chat(tmp_path)  # opened while the files were current
    with pytest.raises(NotImportedError):
        chat.show_status()
    root_store = Store(root)
    root_store.db.import_files()
    assert [row["slug"] for row in chat.show_status()["changes"]] == ["c1"]


def test_a_runner_and_the_host_write_at_once(tmp_path) -> None:
    store = Store(tmp_path)
    with store.lock("c1") as lock:
        store.write(lock, Change(slug="c1"))
    runner = subprocess.Popen([sys.executable, "-c", WRITER, str(tmp_path)])  # noqa: S603
    for n in range(60):
        store.put_inbox("c1", IntentItem(at=NOW, intent="pause" if n % 2 else "resume"))
        with store.lock("c1") as lock:
            store.log(lock, "c1", {"event": "host", "n": n})
    assert runner.wait(60) == 0
    assert (store.read("c2").profile_version, len(store.events("c2")), len(store.events("c1"))) == (59, 60, 60)
    with store.db.read() as db:
        assert db.execute("SELECT count(*) FROM inbox").fetchone() == (60,)


def test_a_fold_whose_barrier_waits_does_not_hold_another_changes_write(tmp_path) -> None:
    store = Store(tmp_path)
    for slug in ("c1", "c2"):
        with store.lock(slug) as lock:
            store.write(lock, Change(slug=slug))
    entered, release = threading.Event(), threading.Event()

    def barrier(_before, after):
        entered.set()
        release.wait(10)
        return after

    def fold() -> None:
        with store.lock("c1") as lock:
            store.fold(lock, "c1", NOW, leave=barrier)

    folding = threading.Thread(target=fold)
    folding.start()
    assert entered.wait(10)
    try:
        writer = Store(tmp_path)  # another connection, as the runner's or a route's
        with writer.lock("c2") as lock:
            writer.write(lock, Change(slug="c2", profile_version=3))
        assert writer.read("c2").profile_version == 3
    finally:
        release.set()
        folding.join(10)


def test_a_store_on_a_network_disk_is_refused_before_anything_is_written(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(database, "_local_devices", set())
    monkeypatch.setattr(database.subprocess, "run", lambda *_a, **_k: SimpleNamespace(returncode=1, stdout=""))
    with pytest.raises(StoreError, match="not on a local disk"):
        Store(tmp_path / "fresh").slugs()
    legacy(tmp_path / "old")
    with pytest.raises(StoreError, match="not on a local disk"):
        Store(tmp_path / "old").db.import_files()
    assert ((tmp_path / "old" / "format").read_text(), (tmp_path / "fresh" / database.DB).exists()) == (
        f"{FORMAT}\n", False
    )  # fmt: skip


def test_a_change_file_an_older_process_writes_after_the_import_is_never_silently_ignored(tmp_path) -> None:
    folder = legacy(tmp_path, acked=True)
    store = imported(tmp_path)
    (folder / "change.json").write_text(Change(slug="c1", profile_version=9).model_dump_json())
    (tmp_path / "changes" / "c7").mkdir()
    (tmp_path / "changes" / "c7" / "change.json").write_text(Change(slug="c7").model_dump_json())
    assert store.slugs() == ["c1", "c7"]
    for slug in ("c1", "c7"):
        with pytest.raises(LateWriteError) as late:
            store.read(slug)
        assert "Compare the file" in late.value.stop(NOW).action


def test_files_that_are_not_utf8_stay_unreadable_after_the_import(tmp_path) -> None:
    folder = legacy(tmp_path)
    (folder / "change.json").write_bytes(Change(slug="c1").model_dump_json().encode().replace(b"c1", b"c\xff1", 1))
    with pytest.raises(StoreError, match="unreadable"):
        imported(tmp_path).read("c1")
    folder = legacy(tmp_path / "answer")
    item = BriefApproval(at=NOW, version=1).model_dump_json().encode().replace(b"version", b"versi\xffon")
    (folder / "inbox" / "00000000000000000001-aaaaaaaa.json").write_bytes(item)
    store = imported(tmp_path / "answer")
    with store.lock("c1") as lock:
        assert store.fold(lock, "c1", NOW)[0].brief.approved == []
    assert [e["event"] for e in store.events("c1")] == ["started", "inbox-rejected"]


class Probe:
    """The machine host's view of the runners an older OwlBear left."""

    def __init__(self, live: set[str]) -> None:
        self.live, self.said = live, []

    def runner(self, slug: str):
        return SimpleNamespace(pid=4242, created=None) if slug in self.live else None

    def alive(self, _pid, _created) -> bool:
        return True

    def say(self, text: str) -> None:
        self.said.append(text)

    record = SimpleNamespace(pid=0)


def test_an_unimported_clone_with_an_older_runner_is_neither_removed_nor_renamed_beside(tmp_path) -> None:
    legacy(tmp_path)
    project = Project(registry.Project(id="a" * 16, path=str(tmp_path), added_at=NOW))
    project.store, project.host = Store(tmp_path), Probe({"c1"})
    assert project.working() == ["c1: a running step (process 4242)"]
    assert config_routes._working(project.store, Probe({"c1"})) == ["c1"]  # noqa: SLF001 - the rename's own check


def test_the_machine_host_imports_once_no_older_runner_is_alive_and_no_change_is_locked(tmp_path) -> None:
    legacy(tmp_path)
    store = Store(tmp_path)
    with pytest.raises(ImportWaitingError, match="running steps of c1 end"):
        Project.import_state(store, Probe({"c1"}))
    holder = subprocess.Popen(  # noqa: S603
        [sys.executable, "-c", HOLD, str(tmp_path)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True
    )
    try:
        assert holder.stdout.readline().strip() == "held"
        with pytest.raises(ImportWaitingError, match=f"process {holder.pid} ends its step"):
            Project.import_state(store, Probe(set()))
    finally:
        holder.kill()
        holder.wait()
    assert store.db.waiting()
    probe = Probe(set())
    Project.import_state(store, probe)
    assert (store.slugs(), probe.said) == (["c1"], ["moved the state of 1 Change into the database"])
    assert json.loads((tmp_path / "format").read_text()) == STORE_FORMAT


HOLD = """
import sys
from pathlib import Path
from owlbear_delivery_next.state_store.store import Store
with Store(Path(sys.argv[1])).lock("c1"):
    print("held", flush=True)
    sys.stdin.read()
"""
