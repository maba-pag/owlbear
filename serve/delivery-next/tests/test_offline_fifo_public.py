"""A special file at each metadata entry refuses through the public startup and Finish, without blocking.

Startup (``project_home.migrated`` without a proof, the switched-startup path) and ``offline_protocol.finish_clone``
both reach the entries below. Every call runs in a daemon thread with a timeout, so a regression that opens a FIFO
for reading blocks only that thread and fails the assertion instead of hanging the run. Each FIFO is left in place
and every other byte of the store is unchanged.
"""

import os
import stat
import subprocess
import threading
from collections.abc import Callable
from pathlib import Path

import pytest

from owlbear_delivery_next.state_store import offline_protocol, project_home, project_move
from owlbear_delivery_next.state_store.database import MARKER, StoreError

SECONDS = 10
Outcome = object


def _within(call: Callable[[], object]) -> Outcome:
    box: list[object] = []

    def run() -> None:
        try:
            box.append(call())
        except Exception as exc:  # noqa: BLE001 - the outcome is the assertion
            box.append(exc)

    worker = threading.Thread(target=run, daemon=True)
    worker.start()
    worker.join(SECONDS)
    assert not worker.is_alive(), "the public call blocked on a special file"
    return box[0]


def _is_fifo(path: Path) -> bool:
    return stat.S_ISFIFO(os.lstat(path).st_mode)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    path = tmp_path / "shop"
    subprocess.run(["git", "init", "-q", "-b", "main", str(path)], check=True, capture_output=True)  # noqa: S603, S607
    folder = project_home.clone_dir(path)
    folder.mkdir(parents=True)
    (folder / MARKER).write_text("7\n")
    (folder / project_move.CLONE_ID).write_text("0123abcd\n")
    return path


def _snapshot(folder: Path) -> dict[str, bytes | str]:
    """Every entry of the store folder, by name: regular bytes, or the kind of a special file.

    The move's own lock is left out: startup creates it on purpose and it holds no state.
    """
    state: dict[str, bytes | str] = {}
    for entry in sorted(folder.rglob("*")):
        rel = str(entry.relative_to(folder))
        if rel == project_move.MOVE_LOCK:
            continue
        mode = os.lstat(entry).st_mode
        if stat.S_ISFIFO(mode):
            state[rel] = "fifo"
        elif stat.S_ISREG(mode):
            state[rel] = entry.read_bytes()
        else:
            state[rel] = "dir" if stat.S_ISDIR(mode) else "other"
    return state


# Each entry is the path, relative to the clone's store folder, that gets the FIFO.
ENTRIES = [
    pytest.param(project_move.MOVE_RECORD, id="move-json"),
    pytest.param(project_move.CLONE_ID, id="clone-id"),
    pytest.param(project_move.MOVE_LOCK, id="move-lock"),
    pytest.param("host.lock", id="host-lock"),
    pytest.param("c1/lock", id="change-c1-lock"),
]


def _plant(folder: Path, rel: str) -> None:
    path = folder / rel
    if rel == project_move.CLONE_ID:
        path.unlink()
    path.parent.mkdir(parents=True, exist_ok=True)
    os.mkfifo(path)


@pytest.mark.parametrize("rel", ENTRIES)
def test_switched_startup_refuses_a_fifo_entry_without_blocking(repo, rel):
    folder = project_home.clone_dir(repo)
    _plant(folder, rel)
    before = _snapshot(folder)

    outcome = _within(lambda: project_home.migrated(repo, None))

    assert isinstance(outcome, (StoreError, ValueError, OSError)), outcome
    assert _snapshot(folder) == before, "startup changed the store while refusing"
    assert _is_fifo(folder / rel)


@pytest.mark.parametrize("rel", ENTRIES)
def test_finish_refuses_or_ignores_a_fifo_entry_without_blocking(repo, rel, monkeypatch):
    folder = project_home.clone_dir(repo)
    _plant(folder, rel)
    before = _snapshot(folder)
    monkeypatch.setattr(offline_protocol, "boot_session", lambda: "AAAAAAAA-0000-4000-8000-000000000001")

    outcome = _within(lambda: offline_protocol.finish_clone(repo, lambda: ()))

    assert isinstance(outcome, (StoreError, ValueError, OSError)), outcome
    assert _snapshot(folder) == before, "finish changed the store while refusing"
    assert _is_fifo(folder / rel)
