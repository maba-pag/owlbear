"""A switched store needs its retained source's receipt and the target's proof at every public admission.

Real Prepare and Finish establish the valid control before damage to the receipt or target. Registration,
self-check, Store.open and current lookup must refuse explicitly without changing the source or target. A failed
public project load must retain uncertain ownership rather than mistake an unproven target's absent record for none.
"""

import fcntl
import inspect
import json
import os
import stat
import subprocess
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import pytest

from owlbear_delivery_next.commands import cli
from owlbear_delivery_next.local_system import codebase, local_home, maintenance
from owlbear_delivery_next.machine_host import selfcheck
from owlbear_delivery_next.machine_host.machine import Machine, MachineError
from owlbear_delivery_next.pack_runs import pack_run, pack_state
from owlbear_delivery_next.project_host.host import HostRecord
from owlbear_delivery_next.state_store import fd_tree, offline_protocol, project_home, project_move, registry
from owlbear_delivery_next.state_store.database import MARKER, FormatTooNewError, StoreError
from owlbear_delivery_next.state_store.store import Store

BEFORE = "AAAAAAAA-0000-4000-8000-000000000001"
AFTER = "BBBBBBBB-0000-4000-8000-000000000002"
FOREIGN = "/elsewhere/not-the-project-store"


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    path = tmp_path / "shop"
    subprocess.run(["git", "init", "-q", "-b", "main", str(path)], check=True, capture_output=True)  # noqa: S603, S607
    folder = project_home.clone_dir(path)
    folder.mkdir(parents=True)
    (folder / MARKER).write_text("7")
    (folder / "config.json").write_text(json.dumps({"format": 1, "widths": [1600]}))
    return path


@pytest.fixture
def boot(monkeypatch) -> dict:
    state = {"id": BEFORE}
    monkeypatch.setattr(offline_protocol, "boot_session", lambda: state["id"])
    monkeypatch.setattr(maintenance.psutil, "boot_time", lambda: 10.0)
    return state


def _source(repo: Path) -> Path:
    return project_home.clone_dir(repo)


def _snapshot(folder: Path) -> dict[str, bytes | str]:
    state: dict[str, bytes | str] = {}
    for entry in sorted(folder.rglob("*")):
        rel = str(entry.relative_to(folder))
        if rel == project_move.MOVE_LOCK:  # startup creates the move lock on purpose; it holds no state
            continue
        mode = os.lstat(entry).st_mode
        if stat.S_ISREG(mode):
            state[rel] = entry.read_bytes()
        else:
            state[rel] = "dir" if stat.S_ISDIR(mode) else "other"
    return state


def _finished_move(repo: Path, boot: dict) -> Path:
    """A real Prepare, a modeled reboot and a real Finish; returns the active store's root."""
    assert cli.main(["--repo", str(repo), "prepare"]) == 0
    boot["id"] = AFTER
    assert cli.main(["--repo", str(repo), "finish"]) == 0
    return Store.open(repo).root


def _with(**changes: object) -> Callable[[dict], str]:
    return lambda record: json.dumps({**record, **changes})


# Each corruption replaces the receipt text; the untampered receipt is the valid control.
CORRUPTIONS = [
    pytest.param(lambda _record: '{"target": "', id="malformed-json"),
    pytest.param(_with(future={"owner": "a later OwlBear"}), id="unknown-future-field"),
    pytest.param(_with(target=FOREIGN), id="mismatched-target-ownership"),
    pytest.param(_with(proof="0" * 32), id="mismatched-proof"),
]


@pytest.mark.usefixtures("current_binding")
def test_a_valid_switched_receipt_is_accepted_by_every_public_consumer(repo, boot) -> None:
    target = _finished_move(repo, boot)
    pid = registry.clone_id(_source(repo))
    assert pid is not None

    assert selfcheck._project(pid, repo) == []  # noqa: SLF001
    assert registry.canonical(repo) == (repo, _source(repo))
    assert registry.register(repo).id == pid
    assert Store.open(repo).root == target


@pytest.mark.usefixtures("current_binding")
def test_an_unreadable_switched_source_marker_refuses_store_open_without_writes(repo, boot):
    target = _finished_move(repo, boot)
    source = _source(repo)
    (source / MARKER).write_bytes(b"\xff\n")
    source_before, target_before = _snapshot(source), _snapshot(target)

    with pytest.raises(StoreError, match=r"switched source.*unreadable"):
        Store.open(repo)

    assert _snapshot(source) == source_before
    assert _snapshot(target) == target_before


@pytest.mark.usefixtures("current_binding")
@pytest.mark.parametrize("corrupt", CORRUPTIONS)
def test_a_corrupt_switched_receipt_is_refused_by_registration_adoption_selfcheck_and_open(repo, boot, corrupt):
    target = _finished_move(repo, boot)
    pid = registry.clone_id(_source(repo))
    assert pid is not None
    registry.register(repo)  # the legitimate registration exists before the receipt is damaged

    receipt = _source(repo) / project_move.MOVE_RECORD
    receipt.write_text(corrupt(json.loads(receipt.read_text())))
    bad = receipt.read_bytes()
    source_before, target_before = _snapshot(_source(repo)), _snapshot(target)

    with pytest.raises(registry.RegistryError):
        registry.adopt(pid)
    assert selfcheck._project(pid, repo) != []  # noqa: SLF001
    with pytest.raises(StoreError):
        Store.open(repo)

    assert receipt.read_bytes() == bad, "a consumer rewrote the corrupt receipt"
    assert _snapshot(_source(repo)) == source_before, "a consumer changed the retained source"
    assert _snapshot(target) == target_before, "a consumer changed the active store"


@pytest.mark.usefixtures("current_binding")
@pytest.mark.parametrize(
    "marker",
    [pytest.param("1000\n", id="future-1000"), pytest.param(None, id="missing"), pytest.param("x9\n", id="malformed")],
)
def test_a_valid_switched_receipt_with_an_unknown_source_marker_is_refused_and_nothing_is_written(repo, boot, marker):
    target = _finished_move(repo, boot)
    source = _source(repo)
    assert (source / MARKER).read_text() == f"{project_move.FENCE}\n"
    if marker is None:
        (source / MARKER).unlink()
    else:
        (source / MARKER).write_text(marker)
    source_before, target_before = _snapshot(source), _snapshot(target)

    with pytest.raises(StoreError):
        Store.open(repo)

    assert _snapshot(source) == source_before, "a refused open rewrote the switched source"
    assert _snapshot(target) == target_before, "a refused open changed the active store"


@pytest.mark.usefixtures("current_binding")
@pytest.mark.parametrize("corrupt", CORRUPTIONS)
def test_a_corrupt_switched_receipt_blocks_a_fresh_registration_without_a_new_move(repo, boot, corrupt):
    target = _finished_move(repo, boot)
    pid = registry.clone_id(_source(repo))
    assert pid is not None
    registry.register(repo)
    registry.remove(pid)  # a fresh registration is the path under test

    receipt = _source(repo) / project_move.MOVE_RECORD
    receipt.write_text(corrupt(json.loads(receipt.read_text())))
    bad = receipt.read_bytes()
    source_before, target_before = _snapshot(_source(repo)), _snapshot(target)

    with pytest.raises(registry.RegistryError):
        registry.register(repo)

    assert receipt.read_bytes() == bad
    assert _snapshot(_source(repo)) == source_before
    assert _snapshot(target) == target_before


TARGET_DAMAGE = [
    pytest.param("missing-proof", id="missing-proof"),
    pytest.param("wrong-proof", id="wrong-proof"),
    pytest.param("recreated-identity", id="recreated-identity"),
    pytest.param("utf8-proof", id="utf8-proof"),
    pytest.param("utf8-format", id="utf8-format"),
    pytest.param("future-format", id="future-format"),
    pytest.param("quarantined", id="quarantined"),
]


def _damage(target: Path, damage: str, monkeypatch) -> type[StoreError]:
    if damage == "missing-proof":
        (target / project_move.MOVE_PROOF).unlink()
    elif damage == "recreated-identity":
        original = fd_tree.ident(target.stat())
        target.rename(target.with_name(target.name + "-retained"))
        target.mkdir()
        replacement = fd_tree.ident(target.stat())
        assert replacement != original
        real_ident = fd_tree.ident
        monkeypatch.setattr(fd_tree, "ident", lambda st: original if real_ident(st) == replacement else real_ident(st))
        (target / project_move.MOVE_PROOF).write_text("another-move\n")
        (target / MARKER).write_text("7\n")
    elif damage == "quarantined":
        (target / f"{fd_tree.QUARANTINE}foreign").write_bytes(b"keep me")
    else:
        name = MARKER if damage in {"utf8-format", "future-format"} else project_move.MOVE_PROOF
        content = b"99\n" if damage == "future-format" else b"\xff" if "utf8" in damage else b"wrong\n"
        (target / name).write_bytes(content)
    return FormatTooNewError if damage == "future-format" else StoreError


@pytest.mark.usefixtures("current_binding")
@pytest.mark.parametrize("damage", TARGET_DAMAGE)
def test_current_and_every_admission_refuse_an_unproven_target_without_writes(repo, boot, monkeypatch, damage):
    target = _finished_move(repo, boot)
    entry = registry.register(repo)
    error = _damage(target, damage, monkeypatch)
    source_before, target_before = _snapshot(_source(repo)), _snapshot(target.parent)

    with pytest.raises(error):
        project_home.current(repo)
    with pytest.raises(error):
        Store.open(repo)
    with pytest.raises(registry.RegistryError, match=r"nothing was|newer than"):
        registry.adopt(entry.id)
    diagnostics = selfcheck.problems()
    assert diagnostics
    assert all(isinstance(item, str) for item in diagnostics)
    assert any(str(repo) in item for item in diagnostics)
    registry.remove(entry.id)
    with pytest.raises(registry.RegistryError, match=r"nothing was|newer than"):
        registry.register(repo)

    assert _snapshot(_source(repo)) == source_before
    assert _snapshot(target.parent) == target_before


@pytest.mark.usefixtures("current_binding")
def test_read_only_current_registration_and_selfcheck_leave_a_missing_target_marker_for_store_open(repo, boot):
    target = _finished_move(repo, boot)
    entry = registry.register(repo)
    (target / MARKER).unlink()
    source_before, target_before = _snapshot(_source(repo)), _snapshot(target)

    assert project_home.current(repo) == target
    assert registry.canonical(repo) == (repo, _source(repo))
    assert registry.adopt(entry.id).id == entry.id
    registry.remove(entry.id)
    assert registry.register(repo).id == entry.id
    assert selfcheck.problems() == []
    assert _snapshot(_source(repo)) == source_before
    assert _snapshot(target) == target_before
    assert not (target / MARKER).exists()

    assert Store.open(repo).root == target
    assert (target / MARKER).read_text() == "7\n"


def _machine() -> Machine:
    record = HostRecord(
        url="http://127.0.0.1:9/",
        token=BEFORE,
        pid=1,
        started_at=datetime.now(UTC),
        code=codebase.CURRENT,
    )
    machine = Machine(record)
    machine.slots.total = lambda: 1
    machine.maintenance.boot = lambda: 10.0
    return machine


@pytest.mark.usefixtures("current_binding")
@pytest.mark.parametrize("switched", [False, True], ids=["legacy", "switched"])
def test_an_unreadable_clone_id_refuses_registration_and_adoption_with_an_actionable_status(repo, boot, switched):
    if switched:
        _finished_move(repo, boot)
    entry = registry.register(repo)
    source = _source(repo)
    target = project_home.home(entry.id)
    (source / project_home.CLONE_ID).write_text("replacement\n")
    machine = _machine()
    try:
        machine.load_all()
        assert machine.projects[entry.id].state == "replaced"
        (source / project_home.CLONE_ID).write_bytes(b"\xff\n")
        source_before = _snapshot(source)
        target_before = target.exists(), _snapshot(target)
        registry_path = local_home.root() / registry.MACHINE
        registry_before = registry_path.read_bytes()

        for action in (lambda: machine.register(repo), lambda: machine.adopt(entry.id)):
            with pytest.raises(MachineError, match=r"clone-id.*unreadable") as refused:
                action()
            assert refused.value.status == 409
        for action in (lambda: registry.register(repo), lambda: registry.adopt(entry.id)):
            with pytest.raises(registry.RegistryError, match=r"clone-id.*unreadable"):
                action()
        if switched:
            with pytest.raises(StoreError, match=r"clone-id.*unreadable"):
                project_home.current(repo)
        else:
            assert project_home.current(repo) == source
        assert _snapshot(source) == source_before
        assert (target.exists(), _snapshot(target)) == target_before
        assert registry_path.read_bytes() == registry_before
    finally:
        machine.stop_all()


@pytest.mark.usefixtures("current_binding")
@pytest.mark.parametrize("damage", TARGET_DAMAGE)
def test_a_failed_public_project_load_holds_unlocated_instead_of_reading_the_unproven_target(
    repo, boot, monkeypatch, damage
):
    target = _finished_move(repo, boot)
    entry = registry.register(repo)
    _damage(target, damage, monkeypatch)
    assert not (target / pack_state.FILE).exists()
    source_before, target_before = _snapshot(_source(repo)), _snapshot(target.parent)
    machine = _machine()
    try:
        machine.load_all()
        assert machine.projects[entry.id].state == "failed"
        (lease,) = machine.maintenance.read()["sessions"]
        assert (lease["state"], lease["project"], lease["workspace"]) == ("held", entry.id, str(repo))
        ledger = json.loads((local_home.root() / maintenance.FILE).read_text())
        assert ledger["imported"] == [f"{entry.id}:unlocated"]
        assert machine.slots.counts(entry.id) == (1, 1, 1)
        machine.retry()
        assert machine.maintenance.read()["sessions"] == [lease]
        assert machine.slots.take("another-project", "work", 1, 1) == 0
    finally:
        machine.stop_all()
    assert machine.maintenance.read()["sessions"] == [lease]
    assert machine.slots.counts(entry.id) == (1, 1, 1)
    assert _snapshot(_source(repo)) == source_before
    assert _snapshot(target.parent) == target_before


@pytest.mark.usefixtures("current_binding")
@pytest.mark.parametrize("kind", ["modern", "legacy-identified", "legacy-unidentified"])
def test_a_valid_target_record_restores_exactly_one_lease_after_a_failed_public_load(repo, boot, kind):
    target = _finished_move(repo, boot)
    entry = registry.register(repo)
    workspace = target / pack_run.UPDATER
    workspace.mkdir()
    identity = {} if kind == "legacy-unidentified" else {"run": "kept", "started_at": "2026-10-25T00:00:00+00:00"}
    record = pack_state.blank() | {"state": "running"} | identity
    if kind == "modern":
        record["workspace"] = str(workspace)
    (target / pack_state.FILE).write_text(json.dumps(record))
    machine = _machine()
    if kind == "modern":
        assert machine.slots.take(entry.id, "pack:kept", 1, 1) == 0  # startup has not opened admission
        machine.maintenance.adopt_uncertain("kept", entry.id, "pack", workspace=str(workspace))
    lock = os.open(target / "host.lock", os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        source_before, target_before = _snapshot(_source(repo)), _snapshot(target)
        assert project_home.current(repo) == target
        machine.load_all()
        assert machine.projects[entry.id].state == "failed"
        assert "another Delivery host" in machine.projects[entry.id].reason
        (lease,) = machine.maintenance.read()["sessions"]
        assert lease["workspace"] == str(workspace)
        assert lease["state"] == "held"
        assert machine.slots.counts(entry.id) == (1, 1, 1)
        machine.retry()
        assert machine.maintenance.read()["sessions"] == [lease]
        assert _snapshot(_source(repo)) == source_before
        assert _snapshot(target) == target_before
    finally:
        os.close(lock)
        machine.stop_all()


def _replace_after_authority_read(repo, monkeypatch, changed, seam, *, current_only=False):
    source = _source(repo)
    pid = project_home.clone_id(source)
    assert pid
    target = project_home.home(pid)
    held_source, held_target = source.stat(), target.stat()
    real_read, real_proof = fd_tree.read_at, project_move._proof_ok  # noqa: SLF001 - real proof read boundary
    moved = (target if changed == "target" else source).with_name("retained-original")
    fired, expected = [], {}

    def replace():
        if fired or (current_only and not any(frame.function == "current" for frame in inspect.stack(context=0))):
            return
        folder = target if changed == "target" else source
        folder.rename(moved)
        folder.mkdir()
        (folder / MARKER).write_text("7\n" if changed == "target" else "8\n")
        (folder / project_home.CLONE_ID).write_text("foreign-owner\n")
        fired.append(True)
        expected.update(source=_snapshot(source), target=_snapshot(target), moved=_snapshot(moved))

    def read(dfd, name):
        text = real_read(dfd, name)
        if (
            seam == "preparation" and name == project_move.PREPARED and os.path.samestat(os.fstat(dfd), held_source)
        ) or (
            name == (MARKER if seam == "marker" else project_move.MOVE_PROOF)
            and os.path.samestat(os.fstat(dfd), held_target)
        ):
            replace()
        return text

    def proof(dfd, rec):
        valid = real_proof(dfd, rec)
        if seam == "proof" and os.path.samestat(os.fstat(dfd), held_target):
            replace()
        return valid

    monkeypatch.setattr(fd_tree, "read_at", read)
    monkeypatch.setattr(project_move, "_proof_ok", proof)
    return fired, expected, moved


@pytest.mark.usefixtures("current_binding")
@pytest.mark.parametrize("lookup", ["current", "register", "adopt", "selfcheck", "unloaded"])
@pytest.mark.parametrize("seam", ["proof", "marker"])
def test_target_replacement_during_authority_reads_refuses_and_keeps_uncertain_ownership(
    repo, boot, monkeypatch, lookup, seam
):
    target = _finished_move(repo, boot)
    entry = registry.register(repo)
    if lookup == "register":
        registry.remove(entry.id)
    machine, lock = None, None
    if lookup == "unloaded":
        machine = _machine()
        lock = os.open(target / "host.lock", os.O_CREAT | os.O_RDWR, 0o600)
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    fired, expected, moved = _replace_after_authority_read(
        repo, monkeypatch, "target", seam, current_only=lookup == "unloaded"
    )
    try:
        if machine is not None:
            machine.load_all()
            assert fired == [True]
            assert machine.projects[entry.id].state == "failed"
            (lease,) = machine.maintenance.read()["sessions"]
            assert (lease["state"], lease["project"], lease["workspace"]) == ("held", entry.id, str(repo))
            ledger = json.loads((local_home.root() / maintenance.FILE).read_text())
            assert ledger["imported"] == [f"{entry.id}:unlocated"]
            machine.retry()
            assert machine.maintenance.read()["sessions"] == [lease]
            assert machine.slots.take("another-project", "work", 1, 1) == 0
        elif lookup == "selfcheck":
            assert selfcheck.problems()
        else:
            error = StoreError if lookup == "current" else registry.RegistryError
            action = {
                "current": lambda: project_home.current(repo),
                "register": lambda: registry.register(repo),
                "adopt": lambda: registry.adopt(entry.id),
            }[lookup]
            with pytest.raises(error):
                action()
        assert fired == [True]
        assert _snapshot(_source(repo)) == expected["source"]
        assert _snapshot(target) == expected["target"]
        assert _snapshot(moved) == expected["moved"]
    finally:
        if lock is not None:
            os.close(lock)
        if machine is not None:
            machine.stop_all()


@pytest.mark.usefixtures("current_binding")
@pytest.mark.parametrize("lookup", ["current", "register", "adopt", "selfcheck", "open"])
@pytest.mark.parametrize("seam", ["preparation", "marker"])
def test_source_replacement_during_authority_reads_never_admits_the_replacement(repo, boot, monkeypatch, lookup, seam):
    target = _finished_move(repo, boot)
    entry = registry.register(repo)
    if lookup == "register":
        registry.remove(entry.id)
    fired, expected, moved = _replace_after_authority_read(repo, monkeypatch, "source", seam)

    if lookup == "selfcheck":
        assert selfcheck.problems()
    else:
        error = StoreError if lookup in {"current", "open"} else registry.RegistryError
        action = {
            "current": lambda: project_home.current(repo),
            "register": lambda: registry.register(repo),
            "adopt": lambda: registry.adopt(entry.id),
            "open": lambda: Store.open(repo),
        }[lookup]
        with pytest.raises(error):
            action()

    assert fired == [True]
    assert _snapshot(_source(repo)) == expected["source"]
    assert _snapshot(target) == expected["target"]
    assert _snapshot(moved) == expected["moved"]


@pytest.mark.usefixtures("current_binding")
@pytest.mark.parametrize(
    "change",
    [
        "target-proof",
        "source-preparation",
        "source-id",
        "source-fence",
        "source-path",
        "target-marker",
        "source-receipt",
        "source-other-receipt",
    ],
)
def test_store_open_revalidates_its_authority_after_the_source_fence_sync(repo, boot, monkeypatch, change):
    target = _finished_move(repo, boot)
    source = _source(repo)
    retained = source.with_name("retained-original")
    expected = {}
    real_sync = os.fsync
    fired = []

    def sync(fd):
        real_sync(fd)
        if fired or not stat.S_ISREG(os.fstat(fd).st_mode):
            return
        for path in source.glob(f".tmp-{MARKER}-*"):
            if os.path.samestat(path.stat(), os.fstat(fd)):
                fired.append(True)
                if change == "source-preparation":
                    record = json.loads((source / project_move.PREPARED).read_text())
                    record["boot"] = "CCCCCCCC-0000-4000-8000-000000000003"
                    (source / project_move.PREPARED).write_text(json.dumps(record))
                elif change == "source-path":
                    source.rename(retained)
                    source.mkdir()
                    (source / "owner").write_text("foreign source")
                else:
                    destination, text = {
                        "target-proof": (target / project_move.MOVE_PROOF, "foreign-proof\n"),
                        "source-id": (source / project_home.CLONE_ID, "foreign-owner\n"),
                        "source-fence": (source / MARKER, "8\n"),
                        "target-marker": (target / MARKER, "8\n"),
                        "source-receipt": (source / project_move.MOVE_RECORD, '{"owner":"unfinished repair"}\n'),
                        "source-other-receipt": (
                            source / project_move.MOVE_RECORD,
                            json.dumps(
                                json.loads((source / project_move.MOVE_RECORD).read_text())
                                | {"target": str(target.with_name("owner-target"))}
                            ),
                        ),
                    }[change]
                    destination.write_text(text)
                for label, folder in (("source", source), ("target", target), ("retained", retained)):
                    expected[label] = {
                        name: value
                        for name, value in _snapshot(folder).items()
                        if not name.startswith((f".tmp-{MARKER}-", fd_tree.QUARANTINE))
                    }

    monkeypatch.setattr(os, "fsync", sync)
    error = FormatTooNewError if change in {"source-fence", "target-marker"} else StoreError
    with pytest.raises(error):
        Store.open(repo)

    assert fired == [True]
    for label, folder in (("source", source), ("target", target), ("retained", retained)):
        assert {
            name: value
            for name, value in _snapshot(folder).items()
            if not name.startswith((f".tmp-{MARKER}-", fd_tree.QUARANTINE))
        } == expected[label]


@pytest.mark.usefixtures("current_binding")
def test_store_open_keeps_legitimate_active_payload_changes(repo, boot):
    target = _finished_move(repo, boot)
    edited = json.dumps({"format": 1, "widths": [987]})
    (target / "config.json").write_text(edited)

    assert Store.open(repo).root == target
    assert (target / "config.json").read_text() == edited


@pytest.mark.usefixtures("current_binding")
@pytest.mark.parametrize("marker", [b"8\n", b"\xff\n", b"", None], ids=["newer", "utf8", "blank", "missing"])
def test_an_unproven_source_fence_keeps_one_unlocated_reservation(repo, boot, marker):
    target = _finished_move(repo, boot)
    entry = registry.register(repo)
    source = _source(repo)
    if marker is None:
        (source / MARKER).unlink()
    else:
        (source / MARKER).write_bytes(marker)
    (source / pack_state.FILE).write_text(
        json.dumps(pack_state.blank() | {"state": "running", "run": "newer-source-run"})
    )
    workspace = source / pack_run.UPDATER
    workspace.mkdir()
    (workspace / "sentinel").write_text("keep original workspace")
    assert not (target / pack_state.FILE).exists()
    before = _snapshot(source)
    machine = _machine()
    try:
        machine.load_all()
        machine.retry()
        assert machine.projects[entry.id].state == "failed"
        (lease,) = machine.maintenance.read()["sessions"]
        assert (lease["state"], lease["project"], lease["workspace"]) == ("held", entry.id, str(repo))
        ledger = json.loads((local_home.root() / maintenance.FILE).read_text())
        assert ledger["imported"] == [f"{entry.id}:unlocated"]
        assert machine.slots.take("another-project", "work", 1, 1) == 0
        with pytest.raises(StoreError):
            project_home.current(repo)
        assert _snapshot(source) == before
    finally:
        machine.stop_all()
    assert machine.maintenance.read()["sessions"] == [lease]


@pytest.mark.usefixtures("current_binding")
@pytest.mark.parametrize("surface", ["register", "adopt"])
@pytest.mark.parametrize("when", ["target-read", "id-file-sync", "id-directory-sync"])
def test_registration_keeps_the_id_it_validated_through_its_durability_work(repo, boot, monkeypatch, surface, when):
    target = _finished_move(repo, boot)
    entry = registry.register(repo) if surface == "adopt" else None
    source = _source(repo)
    registry_path = local_home.root() / registry.MACHINE
    saved = registry_path.read_bytes() if registry_path.exists() else None
    real_read, real_sync = fd_tree.read_at, os.fsync
    target_identity, source_identity = target.stat(), source.stat()
    id_identity = (source / project_home.CLONE_ID).stat()
    fired = []

    def replace_id():
        if not fired:
            fired.append(True)
            (source / project_home.CLONE_ID).write_text("foreign-owner\n")

    def read(fd, name):
        text = real_read(fd, name)
        if when == "target-read" and name == MARKER and os.path.samestat(os.fstat(fd), target_identity):
            replace_id()
        return text

    def sync(fd):
        real_sync(fd)
        wanted = id_identity if when == "id-file-sync" else source_identity
        if when != "target-read" and os.path.samestat(os.fstat(fd), wanted):
            replace_id()

    monkeypatch.setattr(fd_tree, "read_at", read)
    monkeypatch.setattr(os, "fsync", sync)
    action = (lambda: registry.register(repo)) if entry is None else (lambda: registry.adopt(entry.id))
    with pytest.raises(registry.RegistryError):
        action()

    assert fired == [True]
    assert (source / project_home.CLONE_ID).read_text() == "foreign-owner\n"
    assert (registry_path.read_bytes() if registry_path.exists() else None) == saved
    assert not project_home.home("foreign-owner").exists()
    assert json.loads((source / project_move.MOVE_RECORD).read_text())["target"] == str(target)


@pytest.mark.usefixtures("current_binding")
def test_selfcheck_refuses_a_readable_clone_id_that_disagrees_with_its_registered_receipt(repo, boot):
    _finished_move(repo, boot)
    registry.register(repo)
    (_source(repo) / project_home.CLONE_ID).write_text("foreign-owner\n")

    with pytest.raises(StoreError):
        project_home.current(repo)
    problems = selfcheck.problems()
    assert problems
    assert any(str(repo) in problem for problem in problems)


@pytest.mark.usefixtures("current_binding")
@pytest.mark.parametrize("damage", ["valid", "missing-proof", "utf8-proof", "utf8-format", "future-format"])
@pytest.mark.parametrize("lookup", ["current", "adopt", "selfcheck"])
def test_lookup_closes_each_descriptor_it_acquires_on_success_and_typed_refusal(
    repo, boot, monkeypatch, damage, lookup
):
    target = _finished_move(repo, boot)
    entry = registry.register(repo)
    if damage != "valid":
        _damage(target, damage, monkeypatch)
    real_open, real_close = os.open, os.close
    acquired, closed, live = [], [], {}

    def opened(*args, **kwargs):
        fd = real_open(*args, **kwargs)
        caller = inspect.stack(context=0)[1].frame.f_globals["__name__"]
        if caller not in {
            f"owlbear_delivery_next.state_store.{name}"
            for name in ("fd_tree", "project_home", "project_move", "project_switch", "switched_authority")
        }:
            return fd
        token = len(acquired)
        acquired.append((token, str(args[0])))
        assert fd not in live
        live[fd] = token
        return fd

    def close(fd):
        if fd in live:
            os.fstat(fd)  # assert ownership while live, not a recycled descriptor number after close
            closed.append(live.pop(fd))
        return real_close(fd)

    monkeypatch.setattr(os, "open", opened)
    monkeypatch.setattr(os, "close", close)
    if lookup == "selfcheck":
        result = selfcheck.problems()
        assert bool(result) == (damage != "valid")
    elif damage == "valid":
        assert project_home.current(repo) if lookup == "current" else registry.adopt(entry.id)
    else:
        with pytest.raises(StoreError if lookup == "current" else registry.RegistryError):
            project_home.current(repo) if lookup == "current" else registry.adopt(entry.id)
    assert acquired
    assert not live
    assert sorted(closed) == list(range(len(acquired)))
    assert any(name in {str(target), target.name} for _, name in acquired)
