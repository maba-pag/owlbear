"""A FIFO inside the payload refuses through the real public Finish without blocking.

The payload is every entry under the source folder that the digest, sync and copy paths read. Each case runs the
real ``cli.main`` Prepare, a modeled reboot and the real ``cli.main`` Finish. A ``os.open`` spy refuses any blocking
open of a FIFO before the kernel can block, so a regression fails the assertion instead of hanging the run.
"""

import errno
import json
import os
import stat
from pathlib import Path

import pytest
from tests import publication_offline
from tests.publication_offline import AFTER
from tests.publication_offline import source as _source

from owlbear_delivery_next.commands import cli
from owlbear_delivery_next.state_store import project_move

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
    return publication_offline.repo(tmp_path)


@pytest.fixture
def boot(monkeypatch) -> dict:
    return publication_offline.boot(monkeypatch)


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
