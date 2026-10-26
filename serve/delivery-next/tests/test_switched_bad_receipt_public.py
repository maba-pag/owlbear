"""A corrupt SWITCHED receipt in a finished move's retained source is refused by every public consumer.

The receipt is the source's ``move.json``. Each case first proves the untampered move is accepted by registration,
self-check and ``Store.open``, then corrupts only that file and drives the real ``registry.adopt``,
``registry.register``, ``selfcheck._project`` and ``Store.open``. Every refusal must be explicit: the source
(fence 999), the active target's config and payload, and the receipt bytes stay as they were, and no new move is made.
"""

import json
import os
import stat
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

from owlbear_delivery_next.commands import cli
from owlbear_delivery_next.machine_host import registry, selfcheck
from owlbear_delivery_next.state_store import offline_protocol, project_home, project_move
from owlbear_delivery_next.state_store.database import MARKER, StoreError
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
