"""A FIFO inside the payload refuses through the real public Finish without blocking; a regular payload still moves.

The payload is every entry under the source folder that the digest, sync and copy paths read. Each case runs the
real ``cli.main`` Prepare, a modeled reboot and the real ``cli.main`` Finish. A ``os.open`` spy refuses any blocking
open of a FIFO before the kernel can block, so a regression fails the assertion instead of hanging the run.
"""

import errno
import json
import os
import stat
import subprocess
from pathlib import Path

import pytest

from owlbear_delivery_next.commands import cli
from owlbear_delivery_next.state_store import offline_protocol, project_home, project_move
from owlbear_delivery_next.state_store.database import MARKER

BEFORE = "AAAAAAAA-0000-4000-8000-000000000001"
AFTER = "BBBBBBBB-0000-4000-8000-000000000002"
PAYLOAD_FILE = Path("changes/c1/notes.txt")
PAYLOAD_FIFO = Path("changes/c1/output.pipe")


def _is_fifo_at(path: str, dir_fd: int | None) -> bool:
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
        if not flags & os.O_NONBLOCK and isinstance(path, str) and _is_fifo_at(path, dir_fd):
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
    (folder / PAYLOAD_FILE.parent).mkdir(parents=True)
    (folder / PAYLOAD_FILE).write_text("regular payload\n")
    return path


@pytest.fixture
def boot(monkeypatch) -> dict:
    state = {"id": BEFORE}
    monkeypatch.setattr(offline_protocol, "boot_session", lambda: state["id"])
    return state


def _source(repo: Path) -> Path:
    return project_home.clone_dir(repo)


def _record(repo: Path) -> dict:
    return json.loads((_source(repo) / project_move.MOVE_RECORD).read_text())


@pytest.mark.usefixtures("current_binding")
def test_finish_refuses_a_fifo_in_the_payload_without_blocking_or_switching(repo, boot, capsys, blocking_opens):
    assert cli.main(["--repo", str(repo), "prepare"]) == 0
    folder = _source(repo)
    os.mkfifo(folder / PAYLOAD_FIFO)
    boot["id"] = AFTER

    try:
        code = cli.main(["--repo", str(repo), "finish"])
        err = capsys.readouterr().err
    except Exception as exc:  # noqa: BLE001 - the typed refusal is the assertion
        code, err = None, str(exc)
    finally:
        capsys.readouterr()

    assert blocking_opens == [], "Finish opened the payload FIFO for a blocking read"
    assert code in (None, 1), err
    assert "not a regular file" in err, err
    assert _is_fifo_at(str(folder / PAYLOAD_FIFO), None), "the payload FIFO was removed or replaced"
    record_path = _source(repo) / project_move.MOVE_RECORD
    assert not record_path.exists() or json.loads(record_path.read_text())["phase"] != project_move.SWITCHED


@pytest.mark.usefixtures("current_binding")
def test_a_regular_payload_file_still_prepares_finishes_and_opens(repo, boot, capsys, blocking_opens) -> None:
    assert cli.main(["--repo", str(repo), "prepare"]) == 0
    boot["id"] = AFTER

    assert cli.main(["--repo", str(repo), "finish"]) == 0
    capsys.readouterr()

    assert _record(repo)["phase"] == project_move.SWITCHED
    assert blocking_opens == []
