"""A FIFO at a metadata entry refuses through the real public Prepare, Finish and Store.open, without blocking.

Each case runs the real ``cli.main`` Prepare and Finish across a modeled reboot, then the real ``Store.open``. A
spy records and refuses any blocking open of a FIFO before the kernel can block on it, so a regression
fails the assertion instead of hanging the run. Each FIFO is left in place and every other byte is unchanged, apart
from the move lock that startup creates on purpose.
"""

import builtins
import errno
import io
import json
import os
import stat
import subprocess
from pathlib import Path

import pytest

from owlbear_delivery_next.commands import cli
from owlbear_delivery_next.machine_host import selfcheck
from owlbear_delivery_next.state_store import (
    database,
    offline_protocol,
    project_home,
    project_move,
    registry,
    switched_authority,
)
from owlbear_delivery_next.state_store.database import MARKER, STORE_FORMAT, Database, StoreError
from owlbear_delivery_next.state_store.store import Store

BEFORE = "AAAAAAAA-0000-4000-8000-000000000001"
AFTER = "BBBBBBBB-0000-4000-8000-000000000002"


def _chain(exc: BaseException) -> str:
    parts: list[str] = []
    cur: BaseException | None = exc
    while cur is not None:
        parts.append(str(cur))
        cur = cur.__cause__ or cur.__context__
    return " | ".join(parts)


def _is_fifo(path: Path) -> bool:
    return stat.S_ISFIFO(os.lstat(path).st_mode)


def _fifo_at(path: str | os.PathLike, dir_fd: int | None) -> bool:
    try:
        st = os.stat(path, dir_fd=dir_fd, follow_symlinks=False) if dir_fd is not None else os.lstat(path)
    except OSError:
        return False
    return stat.S_ISFIFO(st.st_mode)


@pytest.fixture
def blocking_opens(monkeypatch) -> list[str]:
    """Records each blocking open of a FIFO and refuses it; the real open is never reached for such a FIFO."""
    real_open = os.open
    real_file_open = builtins.open
    attempts: list[str] = []

    def guarded(path, flags, mode=0o777, *, dir_fd=None):
        if not flags & os.O_NONBLOCK and isinstance(path, (str, os.PathLike)) and _fifo_at(path, dir_fd):
            attempts.append(os.fsdecode(path))
            raise OSError(errno.EWOULDBLOCK, "blocking open of a FIFO refused by the test")
        return real_open(path, flags, mode, dir_fd=dir_fd)

    def guarded_file(file, *args, **kwargs):
        if isinstance(file, (str, os.PathLike)) and _fifo_at(file, None):
            attempts.append(os.fsdecode(file))
            raise OSError(errno.EWOULDBLOCK, "blocking open of a FIFO refused by the test")
        return real_file_open(file, *args, **kwargs)

    monkeypatch.setattr(os, "open", guarded)
    monkeypatch.setattr(builtins, "open", guarded_file)
    monkeypatch.setattr(io, "open", guarded_file)
    return attempts


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
    """Every entry of a store folder, by name: regular bytes, or the kind of a special file.

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


def _plant(folder: Path, rel: str) -> None:
    path = folder / rel
    if path.is_symlink() or path.exists():
        path.unlink()
    path.parent.mkdir(parents=True, exist_ok=True)
    os.mkfifo(path)


def _cli(repo: Path, command: str, capsys) -> tuple[int | None, str]:
    """The real ``cli.main`` outcome: its exit code and stderr, or the exception it let escape."""
    try:
        code = cli.main(["--repo", str(repo), command])
    except Exception as exc:  # noqa: BLE001 - the refusal is the assertion
        capsys.readouterr()
        return None, _chain(exc)
    return code, capsys.readouterr().err


def _open(repo: Path) -> tuple[Path | None, str]:
    """The real ``Store.open`` outcome: the active store's root, or the refusal text."""
    try:
        return Store.open(repo).root, ""
    except Exception as exc:  # noqa: BLE001 - the refusal is the assertion
        return None, _chain(exc)


def _move_to_next_boot(repo: Path, boot: dict) -> Path:
    """Real Prepare, a modeled reboot, real Finish and a positive Store.open; returns the active store's root."""
    assert cli.main(["--repo", str(repo), "prepare"]) == 0
    boot["id"] = AFTER
    assert cli.main(["--repo", str(repo), "finish"]) == 0
    return Store.open(repo).root


# A FIFO at a metadata entry of the source while the move is pending: Finish must refuse it before anything moves.
SOURCE_ENTRIES = [
    pytest.param(project_move.MOVE_RECORD, id="move-json"),
    pytest.param(project_move.CLONE_ID, id="clone-id"),
    pytest.param(project_move.MOVE_LOCK, id="move-lock"),
    pytest.param("host.lock", id="host-lock"),
    pytest.param("c1/lock", id="change-c1-lock"),
]


@pytest.mark.usefixtures("current_binding")
@pytest.mark.parametrize("rel", SOURCE_ENTRIES)
def test_finish_refuses_a_fifo_metadata_entry_with_a_nonregular_diagnostic(repo, boot, capsys, blocking_opens, rel):
    assert cli.main(["--repo", str(repo), "prepare"]) == 0
    folder = _source(repo)
    _plant(folder, rel)
    before = _snapshot(folder)
    boot["id"] = AFTER

    code, text = _cli(repo, "finish", capsys)

    assert blocking_opens == [], "Finish opened a FIFO for blocking reads"
    assert code in (None, 1), text
    assert "regular file" in text, text
    assert _snapshot(folder) == before, "Finish changed the source while refusing"
    assert _is_fifo(folder / rel)


@pytest.mark.usefixtures("current_binding")
def test_prepare_then_finish_and_the_next_open_complete_healthy(repo, boot, capsys, blocking_opens) -> None:
    assert cli.main(["--repo", str(repo), "prepare"]) == 0
    boot["id"] = AFTER

    assert cli.main(["--repo", str(repo), "finish"]) == 0
    assert "moved: authoritative store" in capsys.readouterr().out

    target = Store.open(repo).root
    record = json.loads((_source(repo) / project_move.MOVE_RECORD).read_text())
    assert record["phase"] == project_move.SWITCHED
    assert Path(record["target"]) == target
    assert (target / MARKER).read_text().strip() == str(STORE_FORMAT)
    assert (target / project_move.MOVE_PROOF).read_text() == f"{record['proof']}\n"
    assert (_source(repo) / MARKER).read_text().strip() == project_move.FENCE
    assert blocking_opens == []


# A FIFO planted into the retained source of a previously valid SWITCHED store, after a real Finish and Store.open.
RETAINED_SOURCE_ENTRIES = [
    pytest.param(project_move.MOVE_RECORD, id="source-move-json"),
    pytest.param(project_move.CLONE_ID, id="source-clone-id"),
    pytest.param(project_move.MOVE_LOCK, id="source-move-lock"),
]


@pytest.mark.usefixtures("current_binding")
@pytest.mark.parametrize("rel", RETAINED_SOURCE_ENTRIES)
def test_a_previously_valid_switched_store_refuses_a_fifo_in_its_retained_source(repo, boot, blocking_opens, rel):
    target = _move_to_next_boot(repo, boot)
    assert _open(repo)[0] == target  # the valid SWITCHED store opens before the tamper
    _plant(_source(repo), rel)
    source_before, target_before = _snapshot(_source(repo)), _snapshot(target)
    fds_before = len(list(Path("/dev/fd").iterdir()))

    root, text = _open(repo)

    assert blocking_opens == [], "Store.open opened a FIFO for blocking reads"
    assert root is None, "Store.open accepted a FIFO entry"
    assert "regular file" in text, text
    assert _snapshot(_source(repo)) == source_before, "Store.open changed the source while refusing"
    assert _snapshot(target) == target_before, "Store.open changed the active store while refusing"
    assert _is_fifo(_source(repo) / rel)
    assert len(list(Path("/dev/fd").iterdir())) == fds_before, "Store.open leaked a file descriptor"


@pytest.mark.usefixtures("current_binding")
def test_the_active_stores_migrate_lock_refuses_a_fifo_on_its_first_database_read(repo, boot, blocking_opens):
    target = _move_to_next_boot(repo, boot)
    _plant(target, database.MIGRATE)
    before = _snapshot(target)

    store = Store.open(repo)  # the format marker is read without the lock: startup itself takes no migrate lock
    assert store.root == target
    with pytest.raises((ValueError, StoreError)) as caught:
        store.slugs()  # the first database operation takes migrate.lock

    assert blocking_opens == [], "the database opened a FIFO for blocking reads"
    assert "regular file" in _chain(caught.value), _chain(caught.value)
    assert _snapshot(target) == before, "the database changed the active store while refusing"
    assert _is_fifo(target / database.MIGRATE)


@pytest.mark.usefixtures("current_binding")
def test_the_active_store_startup_does_not_read_the_machine_host_lock(repo, boot, blocking_opens):
    target = _move_to_next_boot(repo, boot)
    assert Store.open(repo).slugs() == []  # first database read creates WAL state: warm up before the baseline
    _plant(target, "host.lock")
    before = _snapshot(target)

    store = Store.open(repo)  # the machine host takes host.lock when it starts a project, not Store.open
    assert store.root == target
    assert store.slugs() == []

    assert blocking_opens == []
    assert _snapshot(target) == before
    assert _is_fifo(target / "host.lock")


@pytest.mark.usefixtures("current_binding")
@pytest.mark.parametrize("action", ["registry", "selfcheck", "database"])
def test_marker_readers_refuse_a_fifo_without_waiting_or_treating_it_as_absent(
    repo, boot, action, monkeypatch, blocking_opens
):
    target = _move_to_next_boot(repo, boot)
    _, source = registry.canonical(repo)
    pid = project_home.clone_id(source)
    assert pid is not None
    assert registry.register(repo).id == pid
    assert Database(target).marker() == STORE_FORMAT
    assert selfcheck.problems() == []
    source_before, target_before = _snapshot(source), _snapshot(target)
    marker = (source if action == "registry" else target) / MARKER
    fired = []

    def plant():
        marker.unlink()
        os.mkfifo(marker)
        fired.append(True)

    if action == "selfcheck":
        assert switched_authority.retained_target(source, pid) == target
        real = selfcheck.read_regular

        def read_marker(path):
            if path == marker and not fired:
                plant()
            return real(path)

        monkeypatch.setattr(selfcheck, "read_regular", read_marker)
        problems = selfcheck.problems()
        assert problems, "selfcheck accepted a FIFO marker"
        said = "; ".join(problems)
    else:
        plant()
        with pytest.raises((registry.RegistryError, StoreError)) as caught:
            registry.canonical(repo) if action == "registry" else Database(target).marker()
        said = str(caught.value)

    assert blocking_opens == [], "a marker reader tried to open a FIFO without O_NONBLOCK"
    assert fired == [True]
    assert "unreadable" in said, said
    expected_source = source_before | ({MARKER: "fifo"} if action == "registry" else {})
    expected_target = target_before | ({MARKER: "fifo"} if action != "registry" else {})
    assert _snapshot(source) == expected_source
    assert _snapshot(target) == expected_target
