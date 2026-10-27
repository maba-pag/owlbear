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
