"""A FIFO at a metadata entry refuses through the real public Prepare, Finish and Store.open, without blocking.

Each case runs the real ``cli.main`` Prepare and Finish across a modeled reboot, then the real ``Store.open``. A
``os.open`` spy records and refuses any blocking open of a FIFO before the kernel can block on it, so a regression
fails the assertion instead of hanging the run. Each FIFO is left in place and every other byte is unchanged, apart
from the move lock that startup creates on purpose.
"""

import errno
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from owlbear_delivery_next.commands import cli
from owlbear_delivery_next.state_store import database, offline_protocol, project_home, project_move
from owlbear_delivery_next.state_store.database import MARKER, STORE_FORMAT, StoreError
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


def _fifo_at(path: str, dir_fd: int | None) -> bool:
    try:
        st = os.stat(path, dir_fd=dir_fd, follow_symlinks=False) if dir_fd is not None else os.lstat(path)
    except OSError:
        return False
    return stat.S_ISFIFO(st.st_mode)


@pytest.fixture
def blocking_opens(monkeypatch) -> list[str]:
    """Records each blocking open of a FIFO and refuses it; the real open is never reached for such a FIFO."""
    real_open = os.open
    attempts: list[str] = []

    def guarded(path, flags, mode=0o777, *, dir_fd=None):
        if not flags & os.O_NONBLOCK and isinstance(path, str) and _fifo_at(path, dir_fd):
            attempts.append(path)
            raise OSError(errno.EWOULDBLOCK, "blocking open of a FIFO refused by the test")
        return real_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(os, "open", guarded)
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


MARKER_CHILD = r"""
import json, os, sys
from pathlib import Path
from owlbear_delivery_next.machine_host import selfcheck
from owlbear_delivery_next.state_store import project_home, registry
from owlbear_delivery_next.state_store.database import Database, MARKER, STORE_FORMAT, StoreError
repo, target, action = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
_, source = registry.canonical(repo)
pid = project_home.clone_id(source)
assert pid is not None
assert Database(target).marker() == STORE_FORMAT
assert selfcheck._project(pid, repo) == []
marker = (source if action == "registry" else target) / MARKER
fired = []
def plant():
    marker.unlink()
    os.mkfifo(marker)
    fired.append(True)
if action == "selfcheck":
    assert selfcheck._receipt(pid, source) == (target, None)
    real = selfcheck.read_regular
    def read_marker(path):
        if path == marker and not fired:
            plant()
        return real(path)
    selfcheck.read_regular = read_marker
    problems = selfcheck._project(pid, repo)
    outcome, said = ("refused" if problems else "accepted"), "; ".join(problems)
else:
    plant()
    try:
        registry.canonical(repo) if action == "registry" else Database(target).marker()
    except (registry.RegistryError, StoreError) as error:
        outcome, said = "refused", str(error)
    else:
        outcome, said = "accepted", ""
print(json.dumps({"fired": fired, "outcome": outcome, "said": said}))
"""


@pytest.mark.usefixtures("current_binding")
@pytest.mark.parametrize("action", ["registry", "selfcheck", "database"])
def test_marker_readers_refuse_a_fifo_without_waiting_or_treating_it_as_absent(repo, boot, action):
    target = _move_to_next_boot(repo, boot)
    source = _source(repo)
    source_before, target_before = _snapshot(source), _snapshot(target)
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(p for p in sys.path if p)}
    done = subprocess.run(  # noqa: S603 - fixed diagnostic, this interpreter and disposable stores only
        [sys.executable, "-c", MARKER_CHILD, str(repo), str(target), action],
        capture_output=True,
        text=True,
        timeout=5,
        env=env,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    said = json.loads(done.stdout.strip().splitlines()[-1])
    assert said["fired"] == [True]
    assert said["outcome"] == "refused", said
    assert "unreadable" in said["said"], said
    expected_source = source_before | ({MARKER: "fifo"} if action == "registry" else {})
    expected_target = target_before | ({MARKER: "fifo"} if action != "registry" else {})
    assert _snapshot(source) == expected_source
    assert _snapshot(target) == expected_target
