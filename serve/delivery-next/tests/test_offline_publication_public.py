"""Publication, admission and resource findings from review 5647653877, through the public offline path.

Each relocation case runs the real ``cli.main`` Prepare, a modeled reboot and Finish. Test hooks only inject the
gap between two checks; the bytes and the refusal are asserted on the real filesystem. A ``os.open`` spy refuses a
blocking FIFO open, so a regression fails instead of hanging the run.
"""

import errno
import json
import os
import stat
import subprocess
from pathlib import Path

import pytest

from owlbear_delivery_next.commands import cli
from owlbear_delivery_next.state_store import fd_tree, offline_protocol, project_home, project_move, registry
from owlbear_delivery_next.state_store.database import MARKER, STORE_FORMAT, StoreError
from owlbear_delivery_next.state_store.store import Store

BEFORE = "AAAAAAAA-0000-4000-8000-000000000001"
AFTER = "BBBBBBBB-0000-4000-8000-000000000002"
PAYLOAD_FILE = Path("changes/c1/notes.txt")
PAYLOAD_FIFO = Path("changes/c1/output.pipe")


def _is_fifo_at(path: str) -> bool:
    try:
        return stat.S_ISFIFO(os.lstat(path).st_mode)
    except OSError:
        return False


def _open_fds() -> int:
    return len(list(Path("/dev/fd").iterdir()))


@pytest.fixture
def blocking_opens(monkeypatch) -> list[str]:
    real_open = os.open
    attempts: list[str] = []

    def guarded(path, flags, mode=0o777, *, dir_fd=None):
        if not flags & os.O_NONBLOCK and isinstance(path, str) and _is_fifo_at(path) and dir_fd is None:
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


def _prepared(repo: Path, boot: dict) -> None:
    assert cli.main(["--repo", str(repo), "prepare"]) == 0
    boot["id"] = AFTER


def _switched_store(repo: Path, boot: dict, capsys) -> Path:
    _prepared(repo, boot)
    assert cli.main(["--repo", str(repo), "finish"]) == 0
    capsys.readouterr()
    target = Store.open(repo).root
    (target / MARKER).unlink()
    return target


@pytest.mark.usefixtures("current_binding")
def test_a_payload_edited_after_the_first_staging_check_is_refused_and_not_switched(repo, boot, capsys, monkeypatch):
    _prepared(repo, boot)
    real_owned = project_move._owned  # noqa: SLF001 - the gap hook wraps the real staging check
    edited: list[Path] = []

    def edit_after_owned(pfd, stage_name, rec, *, complete):
        real_owned(pfd, stage_name, rec, complete=complete)
        staged = Path(rec["stage"]) / PAYLOAD_FILE
        if not edited and staged.exists():
            staged.write_bytes(b"edited after the staging check\n")
            edited.append(staged)

    monkeypatch.setattr(project_move, "_owned", edit_after_owned)

    try:
        code = cli.main(["--repo", str(repo), "finish"])
    except StoreError:
        code = None
    capsys.readouterr()

    assert edited, "the payload edit hook never ran"
    assert code in (None, 1)
    assert _record(repo)["phase"] != project_move.SWITCHED
    assert (_source(repo) / PAYLOAD_FILE).read_text() == "regular payload\n", (
        "the source payload was altered or removed"
    )


@pytest.mark.usefixtures("current_binding")
def test_a_source_edit_during_the_retry_sync_is_refused_and_keeps_both_copies(repo, boot, capsys, monkeypatch):
    _prepared(repo, boot)
    real_sync = project_move._sync_published  # noqa: SLF001 - the first attempt fails, the retry edits the source
    calls: list[int] = []

    def fail_then_edit_during_sync(pfd, target, tfd):
        calls.append(1)
        if len(calls) == 1:
            msg = "injected first-attempt sync failure"
            raise OSError(errno.EIO, msg)
        (_source(repo) / PAYLOAD_FILE).write_bytes(b"edited during the retry sync\n")
        real_sync(pfd, target, tfd)

    monkeypatch.setattr(project_move, "_sync_published", fail_then_edit_during_sync)

    with pytest.raises((OSError, StoreError)):
        cli.main(["--repo", str(repo), "finish"])
    capsys.readouterr()
    assert _record(repo)["phase"] != project_move.SWITCHED

    try:
        code = cli.main(["--repo", str(repo), "finish"])
    except StoreError as exc:
        code, err = None, str(exc)
    else:
        err = ""
    capsys.readouterr()

    assert len(calls) == 2, "the retry never reached the sync"
    assert code in (None, 1), err
    assert _record(repo)["phase"] != project_move.SWITCHED, "a stale copy was switched after the source changed"
    assert (_source(repo) / PAYLOAD_FILE).read_bytes() == b"edited during the retry sync\n"
    target = Path(_record(repo)["target"])
    assert (target / PAYLOAD_FILE).exists(), "the published copy was removed"


def test_a_destination_open_failure_closes_the_source_descriptor_for_copy(tmp_path: Path) -> None:
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    (src / "sub").mkdir(parents=True)
    (src / "sub" / "f.txt").write_text("x")
    dst.mkdir()
    (tmp_path / "elsewhere").mkdir()
    (dst / "sub").symlink_to(tmp_path / "elsewhere")  # the destination child is a symlink: its open must fail

    sfd = os.open(src, os.O_RDONLY | os.O_DIRECTORY)
    dfd = os.open(dst, os.O_RDONLY | os.O_DIRECTORY)
    try:
        before = _open_fds()
        with pytest.raises(OSError):  # noqa: PT011 - the typed open failure is the assertion
            fd_tree.copy(sfd, "sub", dfd)
        assert _open_fds() == before, "the source child descriptor leaked after the destination open failed"
    finally:
        os.close(sfd)
        os.close(dfd)


def test_a_destination_open_failure_closes_the_source_descriptor_for_partial_dir(tmp_path: Path) -> None:
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    (src / "sub").mkdir(parents=True)
    dst.mkdir()
    (tmp_path / "elsewhere").mkdir()
    (dst / "sub").symlink_to(tmp_path / "elsewhere")

    sfd = os.open(src, os.O_RDONLY | os.O_DIRECTORY)
    dfd = os.open(dst, os.O_RDONLY | os.O_DIRECTORY)
    try:
        before = _open_fds()
        with pytest.raises(StoreError, match="holds a link or is not a folder"):
            fd_tree._partial_dir(sfd, dfd, "sub")  # noqa: SLF001 - the second partial-copy path
        assert _open_fds() == before, "the source child descriptor leaked after the destination open failed"
    finally:
        os.close(sfd)
        os.close(dfd)


@pytest.mark.usefixtures("current_binding")
def test_a_crash_between_the_marker_and_the_switch_leaves_a_durable_marker_and_resumes(repo, boot, capsys, monkeypatch):
    _prepared(repo, boot)
    real_save = project_move._save  # noqa: SLF001 - the crash is injected at the SWITCHED record write

    def crash_before_switched(folder, folder_fd, rec, **kwargs):
        if rec.get("phase") == project_move.SWITCHED:
            msg = "injected crash before the SWITCHED record"
            raise OSError(errno.EIO, msg)
        real_save(folder, folder_fd, rec, **kwargs)

    monkeypatch.setattr(project_move, "_save", crash_before_switched)
    with pytest.raises((OSError, StoreError)):
        cli.main(["--repo", str(repo), "finish"])
    capsys.readouterr()

    record = _record(repo)
    assert record["phase"] != project_move.SWITCHED
    target = Path(record["target"])
    assert (target / MARKER).read_text().strip() == str(STORE_FORMAT), "the marker was not durable before the switch"

    monkeypatch.setattr(project_move, "_save", real_save)
    assert cli.main(["--repo", str(repo), "finish"]) == 0
    capsys.readouterr()
    assert _record(repo)["phase"] == project_move.SWITCHED
    assert Store.open(repo).root == target


@pytest.mark.usefixtures("current_binding")
def test_a_switched_store_with_a_healthy_marker_is_admitted_without_blocking(repo, boot, capsys, blocking_opens):
    _switched_store_healthy(repo, boot, capsys)
    assert Store.open(repo).root.is_dir()
    assert blocking_opens == []


def _switched_store_healthy(repo: Path, boot: dict, capsys) -> None:
    _prepared(repo, boot)
    assert cli.main(["--repo", str(repo), "finish"]) == 0
    capsys.readouterr()


@pytest.mark.usefixtures("current_binding")
def test_a_missing_target_marker_with_a_corrupt_receipt_is_refused_by_registration(repo, boot, capsys):
    target = _switched_store(repo, boot, capsys)
    (_source(repo) / MARKER).unlink()
    (_source(repo) / project_move.MOVE_RECORD).write_text("{not json")

    with pytest.raises(registry.RegistryError):
        registry.canonical(repo)
    assert not (target / MARKER).exists(), "a marker was minted over a corrupt receipt"


@pytest.mark.usefixtures("current_binding")
def test_a_source_marker_of_7_with_a_missing_target_is_refused_by_registration(repo, boot, capsys):
    target = _switched_store(repo, boot, capsys)
    (target / "config.json").unlink(missing_ok=True)
    target.rename(target.with_name(target.name + ".gone"))

    with pytest.raises(registry.RegistryError):
        registry.canonical(repo)


@pytest.mark.usefixtures("current_binding")
def test_a_target_marker_fifo_is_refused_without_a_blocking_open(repo, boot, capsys, blocking_opens):
    target = _switched_store(repo, boot, capsys)
    os.mkfifo(target / MARKER)

    with pytest.raises(StoreError):
        Store.open(repo)
    assert blocking_opens == [], "the target marker FIFO was opened for a blocking read"
    assert _is_fifo_at(str(target / MARKER)), "the foreign FIFO was removed or replaced"


@pytest.mark.usefixtures("current_binding")
def test_a_healthy_target_marker_6_or_7_is_still_admitted_after_the_fifo_guard(repo, boot, capsys, blocking_opens):
    target = _switched_store(repo, boot, capsys)
    (target / MARKER).write_text(str(STORE_FORMAT))
    assert Store.open(repo).root == target
    assert blocking_opens == []
