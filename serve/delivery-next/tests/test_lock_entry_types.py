"""A special file where a metadata entry should be is refused without blocking; a regular entry still reads.

Each reader opens its entry without blocking and checks it is a regular file before reading or locking it. A FIFO
with no writer would block a plain read-only open forever, so every FIFO call runs in a thread with a timeout. The
FIFO is never removed or written: the refusal must leave it in place.
"""

import fcntl
import os
import stat
import subprocess
import threading
from collections.abc import Callable
from pathlib import Path

import pytest

from owlbear_delivery_next.project_host import host
from owlbear_delivery_next.state_store import project_home, project_move
from owlbear_delivery_next.state_store.database import StoreError
from owlbear_delivery_next.state_store.store import Store


def _within(seconds: float, call: Callable[[], object]) -> object:
    box: list[object] = []

    def run() -> None:
        try:
            box.append(call())
        except Exception as exc:  # noqa: BLE001 - the outcome is the assertion
            box.append(exc)

    worker = threading.Thread(target=run, daemon=True)
    worker.start()
    worker.join(seconds)
    assert not worker.is_alive(), "the reader blocked on a special file"
    return box[0]


def _is_fifo(path: Path) -> bool:
    return stat.S_ISFIFO(os.lstat(path).st_mode)


@pytest.fixture
def folder(tmp_path: Path) -> Path:
    folder = tmp_path / "store"
    folder.mkdir()
    return folder


def test_a_fifo_move_record_refuses_without_blocking(folder):
    os.mkfifo(folder / project_move.MOVE_RECORD)
    fd = os.open(folder, os.O_RDONLY)
    try:
        outcome = _within(10, lambda: project_move.record_at(folder, fd))
    finally:
        os.close(fd)

    assert isinstance(outcome, StoreError)
    assert _is_fifo(folder / project_move.MOVE_RECORD)


def test_an_absent_move_record_is_none(folder):
    fd = os.open(folder, os.O_RDONLY)
    try:
        assert project_move.record_at(folder, fd) is None
    finally:
        os.close(fd)


def test_a_fifo_clone_id_refuses_without_blocking(folder):
    os.mkfifo(folder / project_move.CLONE_ID)

    outcome = _within(10, lambda: project_home.clone_id(folder))

    assert isinstance(outcome, StoreError)
    assert _is_fifo(folder / project_move.CLONE_ID)


def test_a_regular_clone_id_is_read_back(folder):
    created = project_home.ensure_id(folder)

    assert project_home.clone_id(folder) == created


def test_a_fifo_host_lock_refuses_without_blocking(tmp_path):
    root = tmp_path / "home"
    root.mkdir()
    os.mkfifo(root / "host.lock")

    outcome = _within(10, lambda: host.running_at(root))

    assert isinstance(outcome, OSError)
    assert _is_fifo(root / "host.lock")


def test_a_held_regular_host_lock_reports_a_host(tmp_path):
    root = tmp_path / "home"
    root.mkdir()
    fd = os.open(root / "host.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

        assert host.running_at(root) is not None
    finally:
        os.close(fd)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=root, check=True, capture_output=True)  # noqa: S607
    subprocess.run(
        ["git", "commit", "-q", "--allow-empty", "-m", "init"],  # noqa: S607
        cwd=root,
        check=True,
        capture_output=True,
        env={
            **os.environ,
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@t",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@t",
        },
    )
    return root


def test_a_fifo_change_lock_refuses_without_blocking(repo):
    store = Store.open(repo)
    change_dir = store._dir("c1")  # noqa: SLF001 - the change folder is the entry under test
    change_dir.mkdir(parents=True, exist_ok=True)
    os.mkfifo(change_dir / "lock")

    outcome = _within(10, lambda: store.holder("c1"))

    assert isinstance(outcome, StoreError)
    assert _is_fifo(change_dir / "lock")


def test_a_held_change_lock_names_its_holder(repo):
    store = Store.open(repo)
    with store.lock("c1"):
        assert store.holder("c1").pid == os.getpid()
