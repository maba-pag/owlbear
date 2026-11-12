"""Publication, admission and resource findings from review 5647653877, through the public offline path.

Each relocation case runs the real ``cli.main`` Prepare, a modeled reboot and Finish. Test hooks only inject the
gap between two checks; the bytes and the refusal are asserted on the real filesystem. A ``os.open`` spy refuses a
blocking FIFO open, so a regression fails instead of hanging the run.
"""

import errno
import json
import os
import shutil
import stat
from pathlib import Path

import pytest
from tests import publication_offline
from tests.publication_offline import AFTER, PAYLOAD_FILE
from tests.publication_offline import prepare as _prepared
from tests.publication_offline import record as _record
from tests.publication_offline import source as _source
from tests.publication_offline import switched_store as _switched_store

from owlbear_delivery_next.commands import cli
from owlbear_delivery_next.machine_host import selfcheck
from owlbear_delivery_next.state_store import fd_tree, offline_protocol, project_home, project_move, registry
from owlbear_delivery_next.state_store.database import MARKER, STORE_FORMAT, FormatTooNewError, StoreError
from owlbear_delivery_next.state_store.store import Store


@pytest.fixture
def repo(tmp_path):
    return publication_offline.repo(tmp_path)


@pytest.fixture
def boot(monkeypatch):
    return publication_offline.boot(monkeypatch)


def _is_fifo_at(path: str) -> bool:
    try:
        return stat.S_ISFIFO(os.lstat(path).st_mode)
    except OSError:
        return False


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


@pytest.mark.usefixtures("current_binding")
def test_a_payload_edited_after_the_first_staging_check_is_refused_and_not_switched(repo, boot, monkeypatch):
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
    assert edited, "the payload edit hook never ran"
    assert code in (None, 1)
    assert _record(repo)["phase"] != project_move.SWITCHED
    assert (_source(repo) / PAYLOAD_FILE).read_text() == "regular payload\n", (
        "the source payload was altered or removed"
    )


@pytest.mark.usefixtures("current_binding")
def test_a_source_edit_during_the_retry_sync_is_refused_and_keeps_both_copies(repo, boot, monkeypatch):
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
    assert _record(repo)["phase"] != project_move.SWITCHED

    try:
        code = cli.main(["--repo", str(repo), "finish"])
    except StoreError as exc:
        code, err = None, str(exc)
    else:
        err = ""
    assert len(calls) == 2, "the retry never reached the sync"
    assert code in (None, 1), err
    assert _record(repo)["phase"] != project_move.SWITCHED, "a stale copy was switched after the source changed"
    assert (_source(repo) / PAYLOAD_FILE).read_bytes() == b"edited during the retry sync\n"
    target = Path(_record(repo)["target"])
    assert (target / PAYLOAD_FILE).exists(), "the published copy was removed"


def test_a_destination_open_failure_closes_the_source_descriptor_for_copy(tmp_path: Path, monkeypatch) -> None:
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    (src / "sub").mkdir(parents=True)
    (src / "sub" / "f.txt").write_text("x")
    dst.mkdir()
    (tmp_path / "elsewhere").mkdir()
    real_mkdir, real_open = os.mkdir, fd_tree.open_dir
    opened = []
    sfd = os.open(src, os.O_RDONLY | os.O_DIRECTORY)
    dfd = os.open(dst, os.O_RDONLY | os.O_DIRECTORY)

    def replace_created(name, mode=0o777, *, dir_fd=None):
        real_mkdir(name, mode, dir_fd=dir_fd)
        if name == "sub" and dir_fd == dfd:
            (dst / "sub").rmdir()
            (dst / "sub").symlink_to(tmp_path / "elsewhere")

    def capture(parent, name):
        fd = real_open(parent, name)
        if parent == sfd:
            opened.append(fd)
        return fd

    monkeypatch.setattr(os, "mkdir", replace_created)
    monkeypatch.setattr(fd_tree, "open_dir", capture)
    try:
        with pytest.raises(StoreError, match="holds a link or is not a folder"):
            fd_tree.copy(sfd, "sub", dfd)
        assert len(opened) == 1
        with pytest.raises(OSError, match="Bad file descriptor") as closed:
            os.fstat(opened[0])
        assert closed.value.errno == errno.EBADF
    finally:
        os.close(sfd)
        os.close(dfd)


def test_a_destination_open_failure_closes_the_source_descriptor_for_partial_dir(tmp_path: Path, monkeypatch) -> None:
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    (src / "sub").mkdir(parents=True)
    dst.mkdir()
    (tmp_path / "elsewhere").mkdir()
    (dst / "sub").symlink_to(tmp_path / "elsewhere")

    sfd = os.open(src, os.O_RDONLY | os.O_DIRECTORY)
    dfd = os.open(dst, os.O_RDONLY | os.O_DIRECTORY)
    real_open, opened = fd_tree.open_dir, []

    def capture(parent, name):
        fd = real_open(parent, name)
        if parent == sfd:
            opened.append(fd)
        return fd

    monkeypatch.setattr(fd_tree, "open_dir", capture)
    try:
        with pytest.raises(StoreError, match="holds a link or is not a folder"):
            fd_tree._partial_dir(sfd, dfd, "sub")  # noqa: SLF001 - the second partial-copy path
        assert len(opened) == 1
        with pytest.raises(OSError, match="Bad file descriptor") as closed:
            os.fstat(opened[0])
        assert closed.value.errno == errno.EBADF
    finally:
        os.close(sfd)
        os.close(dfd)


@pytest.mark.usefixtures("current_binding")
def test_a_crash_between_the_marker_and_the_switch_leaves_a_durable_marker_and_resumes(repo, boot, monkeypatch):
    _prepared(repo, boot)
    real_save = project_move._save  # noqa: SLF001 - the crash is injected at the SWITCHED record write
    real_sync, synced = os.fsync, []

    def sync(fd):
        identity = fd_tree.ident(os.fstat(fd))
        real_sync(fd)
        synced.append(identity)

    def crash_before_switched(folder, folder_fd, rec, **kwargs):
        if rec.get("phase") == project_move.SWITCHED:
            target = Path(rec["target"])
            marker_sync = fd_tree.ident((target / MARKER).stat())
            assert marker_sync in synced
            assert fd_tree.ident(target.stat()) in synced[synced.index(marker_sync) + 1 :]
            msg = "injected crash before the SWITCHED record"
            raise OSError(errno.EIO, msg)
        real_save(folder, folder_fd, rec, **kwargs)

    monkeypatch.setattr(project_move, "_save", crash_before_switched)
    monkeypatch.setattr(os, "fsync", sync)
    with pytest.raises((OSError, StoreError)):
        cli.main(["--repo", str(repo), "finish"])
    record = _record(repo)
    assert record["phase"] != project_move.SWITCHED
    target = Path(record["target"])
    assert (target / MARKER).read_text().strip() == str(STORE_FORMAT), "the marker was not durable before the switch"

    monkeypatch.setattr(project_move, "_save", real_save)
    assert cli.main(["--repo", str(repo), "finish"]) == 0
    assert _record(repo)["phase"] == project_move.SWITCHED
    assert Store.open(repo).root == target
    assert registry.canonical(repo) == (repo.resolve(), _source(repo).resolve())
    retained, problem = selfcheck._receipt(project_home.clone_id(_source(repo)), _source(repo))  # noqa: SLF001
    assert (retained, problem) == (target, None)


@pytest.mark.usefixtures("current_binding")
@pytest.mark.parametrize("missing", ["corrupt-receipt", "target"])
def test_a_missing_target_marker_with_a_corrupt_receipt_is_refused_by_registration(repo, boot, missing):
    target = _switched_store(repo, boot)
    (target / MARKER).unlink()
    if missing == "corrupt-receipt":
        (_source(repo) / MARKER).unlink()
        (_source(repo) / project_move.MOVE_RECORD).write_text("{not json")
    else:
        (target / "config.json").unlink(missing_ok=True)
        target.rename(target.with_name(target.name + ".gone"))
    with pytest.raises(registry.RegistryError):
        registry.canonical(repo)
    assert not (target / MARKER).exists()


@pytest.mark.usefixtures("current_binding")
def test_a_target_marker_fifo_is_refused_without_a_blocking_open(repo, boot, blocking_opens):
    target = _switched_store(repo, boot)
    (target / MARKER).unlink()
    os.mkfifo(target / MARKER)

    with pytest.raises(StoreError):
        Store.open(repo)
    assert blocking_opens == [], "the target marker FIFO was opened for a blocking read"
    assert _is_fifo_at(str(target / MARKER)), "the foreign FIFO was removed or replaced"


@pytest.mark.usefixtures("current_binding")
def test_a_foreign_target_found_on_resume_is_refused_before_any_write(repo, boot, capsys, monkeypatch):
    _prepared(repo, boot)

    def fail_sync(_pfd, _target, _tfd):
        raise OSError(errno.EIO, "injected first-attempt sync failure")

    with monkeypatch.context() as patch:
        patch.setattr(project_move, "_sync_published", fail_sync)
        with pytest.raises((OSError, StoreError)):
            cli.main(["--repo", str(repo), "finish"])
    capsys.readouterr()
    target = Path(_record(repo)["target"])
    assert target.exists()
    shutil.rmtree(target)
    target.mkdir()
    (target / "foreign.txt").write_text("owner bytes\n")
    assert cli.main(["--repo", str(repo), "finish"]) == 1
    assert capsys.readouterr().err == (
        f"{target} is not the copy this move published: nothing was removed; move it away, then start again\n"
    )
    assert sorted(p.name for p in target.iterdir()) == ["foreign.txt"]
    assert (target / "foreign.txt").read_text() == "owner bytes\n"
    assert (_source(repo) / PAYLOAD_FILE).read_text() == "regular payload\n"
    assert _record(repo)["phase"] != project_move.SWITCHED


def _rewrite_prior(repo: Path, prior: str) -> None:
    path = _source(repo) / project_move.PREPARED
    record = json.loads(path.read_text())
    record["marker"] = prior
    path.write_text(json.dumps(record) + "\n")


@pytest.mark.usefixtures("current_binding")
@pytest.mark.parametrize("authority", ["future-prior", "missing-preparation"])
def test_a_missing_target_marker_with_a_prepared_prior_8_is_refused_by_every_consumer(repo, boot, authority):
    target = _switched_store(repo, boot)
    (target / MARKER).unlink()
    if authority == "future-prior":
        _rewrite_prior(repo, "8")
    else:
        prepared = _source(repo) / project_move.PREPARED
        assert prepared.exists()
        prepared.unlink()
    with pytest.raises(registry.RegistryError):
        registry.canonical(repo)
    with pytest.raises(StoreError):
        Store.open(repo)
    assert not (target / MARKER).exists()
    clone = _source(repo)
    registry_pid = project_home.clone_id(clone)
    assert registry_pid is not None
    _, problem = selfcheck._receipt(registry_pid, clone)  # noqa: SLF001 - the selfcheck's own receipt verdict
    assert problem is not None


@pytest.mark.usefixtures("current_binding")
@pytest.mark.parametrize("prior", [6, STORE_FORMAT])
def test_a_prepared_prior_6_is_admitted_by_every_consumer(repo, boot, blocking_opens, prior):
    (_source(repo) / MARKER).write_text(str(prior))
    target = _switched_store(repo, boot)
    (target / MARKER).unlink()
    _rewrite_prior(repo, str(prior))
    assert Store.open(repo).root == target
    assert (target / MARKER).read_text().strip() == str(prior)
    assert registry.canonical(repo) == (repo.resolve(), _source(repo).resolve())
    clone = _source(repo)
    retained, problem = selfcheck._receipt(project_home.clone_id(clone), clone)  # noqa: SLF001
    assert (retained, problem) == (target, None)
    assert blocking_opens == []


@pytest.mark.usefixtures("current_binding")
def test_a_target_marker_from_a_newer_store_is_refused_as_an_upgrade_and_nothing_is_written(repo, boot, monkeypatch):
    _prepared(repo, boot)
    real_sync, planted = fd_tree.sync, []

    def sync(dfd, entry):
        real_sync(dfd, entry)
        if entry == project_home.clone_id(_source(repo)) and not planted:
            planted.append(entry)
            (project_home.home(entry) / MARKER).write_text("99\n")

    monkeypatch.setattr(fd_tree, "sync", sync)
    before = {name: (_source(repo) / name).read_bytes() for name in (MARKER, project_move.PREPARED)}
    boot["id"] = AFTER
    with pytest.raises(FormatTooNewError):
        offline_protocol.finish_clone(repo, gaps=lambda: ())
    assert planted
    assert project_home.home(planted[0]).joinpath(MARKER).read_text() == "99\n"
    assert {name: (_source(repo) / name).read_bytes() for name in before} == before
    with pytest.raises(FormatTooNewError):
        Store.open(repo)
