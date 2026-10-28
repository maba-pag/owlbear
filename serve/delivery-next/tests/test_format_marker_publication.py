"""A missing publication marker is created exclusively; an owner's collided marker stays authoritative."""

import errno
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from owlbear_delivery_next.commands import cli
from owlbear_delivery_next.state_store import fd_tree, format_marker, offline_protocol, project_home, project_move
from owlbear_delivery_next.state_store.database import MARKER, STORE_FORMAT, FormatTooNewError, StoreError
from owlbear_delivery_next.state_store.store import Store

BEFORE = "AAAAAAAA-0000-4000-8000-000000000001"
AFTER = "BBBBBBBB-0000-4000-8000-000000000002"


def _owner_after_absence(monkeypatch, target: Path, text: bytes) -> list[int]:
    real_read = fd_tree.read_at
    identity: list[int] = []

    def read(dfd, name):
        found = real_read(dfd, name)
        if (
            name == MARKER
            and found is None
            and not identity
            and target.exists()
            and fd_tree.ident(os.fstat(dfd)) == fd_tree.ident(target.stat())
        ):
            (target / MARKER).write_bytes(text)
            identity.extend(fd_tree.ident((target / MARKER).stat()))
        return found

    monkeypatch.setattr(fd_tree, "read_at", read)
    return identity


@pytest.mark.parametrize("value", [8, 998, 1000])
def test_a_future_marker_created_after_absence_is_never_overwritten(tmp_path, monkeypatch, value):
    target = tmp_path / "target"
    target.mkdir()
    text = f"{value}\n".encode()
    owner = _owner_after_absence(monkeypatch, target, text)
    tfd = os.open(target, fd_tree.DIR_FLAGS)
    try:
        with pytest.raises(FormatTooNewError, match=f"store format {value} is newer than 7"):
            format_marker.ensure_target(tfd, 7)
    finally:
        os.close(tfd)

    assert owner
    assert (target / MARKER).read_bytes() == text
    assert fd_tree.ident((target / MARKER).stat()) == owner
    assert sorted(p.name for p in target.iterdir()) == [MARKER]


def _observe_syncs(monkeypatch, target: Path) -> list[tuple[str, list[int]]]:
    real_sync = os.fsync
    events: list[tuple[str, list[int]]] = []

    def sync(fd):
        held = fd_tree.ident(os.fstat(fd))
        if target.exists() and held == fd_tree.ident(target.stat()):
            events.append(("directory", held))
        marker = target / MARKER
        if marker.is_file() and held == fd_tree.ident(marker.stat()):
            events.append(("marker", held))
        return real_sync(fd)

    monkeypatch.setattr(os, "fsync", sync)
    return events


def _assert_durable(events: list, target: Path) -> None:
    marker_sync = ("marker", fd_tree.ident((target / MARKER).stat()))
    folder_sync = ("directory", fd_tree.ident(target.stat()))
    assert marker_sync in events
    assert folder_sync in events[events.index(marker_sync) + 1 :]


@pytest.mark.parametrize("collision", [False, True], ids=["existing", "collided"])
@pytest.mark.parametrize("value", range(1, STORE_FORMAT + 1))
def test_a_supported_owner_marker_keeps_its_bytes_and_inode_and_is_synced(tmp_path, monkeypatch, collision, value):
    target = tmp_path / "target"
    target.mkdir()
    text = f" \t{value:02d}\r\n".encode()
    if collision:
        owner = _owner_after_absence(monkeypatch, target, text)
    else:
        (target / MARKER).write_bytes(text)
        owner = fd_tree.ident((target / MARKER).stat())
    events = _observe_syncs(monkeypatch, target)
    tfd = os.open(target, fd_tree.DIR_FLAGS)
    try:
        format_marker.ensure_target(tfd, 7)
    finally:
        os.close(tfd)

    assert owner
    assert (target / MARKER).read_bytes() == text
    assert fd_tree.ident((target / MARKER).stat()) == owner
    _assert_durable(events, target)
    assert sorted(p.name for p in target.iterdir()) == [MARKER]


@pytest.mark.parametrize("previous", range(STORE_FORMAT + 1))
def test_a_genuinely_absent_marker_is_created_with_its_prior_format_and_synced(tmp_path, monkeypatch, previous):
    events = _observe_syncs(monkeypatch, tmp_path)
    tfd = os.open(tmp_path, fd_tree.DIR_FLAGS)
    try:
        format_marker.ensure_target(tfd, previous)
        format_marker.written_format(tfd, previous)
    finally:
        os.close(tfd)

    assert (tmp_path / MARKER).read_text() == f"{previous or STORE_FORMAT}\n"
    _assert_durable(events, tmp_path)
    assert sorted(p.name for p in tmp_path.iterdir()) == [MARKER]


@pytest.mark.parametrize("text", [b"", b" \n", b"0\n", b"x9\n", b"\xff\n"])
def test_an_invalid_regular_collision_is_not_absence_and_is_kept(tmp_path, monkeypatch, text):
    owner = _owner_after_absence(monkeypatch, tmp_path, text)
    tfd = os.open(tmp_path, fd_tree.DIR_FLAGS)
    try:
        with pytest.raises(StoreError):
            format_marker.ensure_target(tfd, 7)
    finally:
        os.close(tfd)

    assert owner
    assert (tmp_path / MARKER).read_bytes() == text
    assert fd_tree.ident((tmp_path / MARKER).stat()) == owner


class _MarkerIO:
    def __init__(self, open_file):
        self.open_file = open_file
        self.fd = None
        self.stream = None
        self.transferred = False
        self.released = False
        self.failure = None

    def __getattr__(self, name):
        return getattr(os, name)

    def acquire(self, dfd, name):
        assert self.fd is None
        self.fd = self.open_file(dfd, name)
        return self.fd

    def fdopen(self, fd, *args, **kwargs):
        assert fd == self.fd
        if self.failure is not None:
            raise self.failure
        self.stream = os.fdopen(fd, *args, **kwargs)
        self.transferred = kwargs.get("closefd", True)
        return self.stream

    def close(self, fd):
        assert fd == self.fd
        assert not self.released
        assert not self.transferred
        os.close(fd)
        self.released = True

    @property
    def closed(self):
        return self.released or (self.transferred and self.stream.closed)

    def cleanup(self):
        if self.stream is not None:
            self.stream.close()
        if self.fd is not None and not self.released and not self.transferred:
            self.close(self.fd)


@pytest.fixture
def marker_io(monkeypatch):
    probe = _MarkerIO(fd_tree.open_file)
    monkeypatch.setattr(fd_tree, "open_file", probe.acquire)
    monkeypatch.setattr(format_marker, "os", probe)
    try:
        yield probe
    finally:
        probe.cleanup()


@pytest.mark.parametrize("text", [b"8\n", b"\xff\n"])
def test_a_refused_collision_closes_the_descriptor_it_opened(tmp_path, monkeypatch, marker_io, text):
    owner = _owner_after_absence(monkeypatch, tmp_path, text)
    tfd = os.open(tmp_path, fd_tree.DIR_FLAGS)
    try:
        with pytest.raises(StoreError):
            format_marker.ensure_target(tfd, 7)
        assert marker_io.fd is not None
        assert marker_io.stream.closed
        assert marker_io.closed
    finally:
        os.close(tfd)

    assert (tmp_path / MARKER).read_bytes() == text
    assert fd_tree.ident((tmp_path / MARKER).stat()) == owner


class _HandoverError(BaseException):
    pass


@pytest.mark.parametrize("failure", ["oserror", "baseexception"])
def test_a_failed_marker_fdopen_handover_closes_its_owned_descriptor(tmp_path, marker_io, failure):
    marker = tmp_path / MARKER
    marker.write_bytes(b"7\n")
    owner = fd_tree.ident(marker.stat())
    error = OSError(errno.ENOMEM, "injected fdopen failure") if failure == "oserror" else _HandoverError("interrupted")
    marker_io.failure = error
    expected = StoreError if failure == "oserror" else _HandoverError
    tfd = os.open(tmp_path, fd_tree.DIR_FLAGS)
    try:
        with pytest.raises(expected) as caught:
            format_marker.ensure_target(tfd, 7)
        assert caught.value.__cause__ is error if failure == "oserror" else caught.value is error
        assert marker_io.fd is not None
        assert marker_io.stream is None
        assert marker_io.closed, "the failed handover left the caller-owned marker descriptor live"
    finally:
        os.close(tfd)

    assert marker.read_bytes() == b"7\n"
    assert fd_tree.ident(marker.stat()) == owner


class _CreatingMarkerIO(_MarkerIO):
    def __init__(self):
        super().__init__(None)
        self.created = None
        self.syncs = []

    def open(self, name, flags, mode=0o777, *, dir_fd=None):
        fd = os.open(name, flags, mode, dir_fd=dir_fd)
        if flags & os.O_CREAT:
            assert flags & os.O_EXCL
            assert self.fd is None
            self.fd = fd
            self.created = fd_tree.ident(os.fstat(fd))
        return fd

    def close(self, fd):
        if fd == self.fd and not self.released and not self.transferred:
            super().close(fd)
        else:
            os.close(fd)

    def fsync(self, fd):
        self.syncs.append("marker" if fd == self.fd and not self.released else "directory")
        os.fsync(fd)


@pytest.fixture
def creation_io(monkeypatch):
    probe = _CreatingMarkerIO()
    monkeypatch.setattr(fd_tree, "os", probe)
    try:
        yield probe
    finally:
        probe.cleanup()


def _create_marker(tfd: int, entrypoint: str) -> None:
    if entrypoint == "create":
        fd_tree.create_at(tfd, MARKER, "7\n")
    else:
        format_marker.ensure_target(tfd, 7)


@pytest.mark.parametrize("entrypoint", ["create", "ensure"])
@pytest.mark.parametrize("failure", ["oserror", "baseexception"])
def test_a_failed_creation_fdopen_handover_closes_its_owned_descriptor(tmp_path, creation_io, failure, entrypoint):
    error = (
        OSError(errno.ENOMEM, "injected creation fdopen failure") if failure == "oserror" else _HandoverError("stopped")
    )
    creation_io.failure = error
    expected = StoreError if failure == "oserror" else _HandoverError
    tfd = os.open(tmp_path, fd_tree.DIR_FLAGS)
    try:
        with pytest.raises(expected) as caught:
            _create_marker(tfd, entrypoint)
        assert caught.value.__cause__ is error if failure == "oserror" else caught.value is error
        assert creation_io.fd is not None
        assert creation_io.stream is None
        assert creation_io.closed, "the failed creation handover left the caller-owned descriptor live"
        assert creation_io.syncs == []
    finally:
        os.close(tfd)

    assert (tmp_path / MARKER).read_bytes() == b""
    assert fd_tree.ident((tmp_path / MARKER).stat()) == creation_io.created
    assert sorted(p.name for p in tmp_path.iterdir()) == [MARKER]


@pytest.mark.parametrize("entrypoint", ["create", "ensure"])
def test_a_successful_creation_handover_closes_and_syncs_its_marker(tmp_path, creation_io, entrypoint):
    tfd = os.open(tmp_path, fd_tree.DIR_FLAGS)
    try:
        _create_marker(tfd, entrypoint)
        assert creation_io.stream.closed
        assert creation_io.closed
        assert creation_io.syncs == ["marker", "directory"]
    finally:
        os.close(tfd)

    assert (tmp_path / MARKER).read_bytes() == b"7\n"
    assert fd_tree.ident((tmp_path / MARKER).stat()) == creation_io.created
    assert sorted(p.name for p in tmp_path.iterdir()) == [MARKER]


SPECIAL_ENTRY_PROBE = """
import os
import stat
import sys
from pathlib import Path
from owlbear_delivery_next.state_store import fd_tree, format_marker
from owlbear_delivery_next.state_store.database import MARKER, StoreError

target, kind, when = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
marker = target / MARKER
outside = target / "outside"
outside.write_text("owner outside bytes\\n")
owner = []
real_read = fd_tree.read_at

def create():
    if kind == "symlink":
        marker.symlink_to(outside)
    elif kind == "dangling":
        marker.symlink_to(target / "missing")
    elif kind == "fifo":
        os.mkfifo(marker)
    else:
        marker.mkdir()
    owner.extend(fd_tree.ident(marker.lstat()))

def read(dfd, name):
    text = real_read(dfd, name)
    if name == MARKER and text is None and not owner:
        create()
    return text

if when == "existing":
    create()
fd_tree.read_at = read
tfd = os.open(target, fd_tree.DIR_FLAGS)
try:
    try:
        format_marker.ensure_target(tfd, 7)
    except StoreError:
        pass
    else:
        raise AssertionError("a special entry was admitted")
finally:
    os.close(tfd)
assert owner == fd_tree.ident(marker.lstat())
assert outside.read_text() == "owner outside bytes\\n"
assert sorted(p.name for p in target.iterdir()) == sorted([MARKER, "outside"])
if kind in ("symlink", "dangling"):
    assert marker.is_symlink()
    assert marker.readlink() == (outside if kind == "symlink" else target / "missing")
elif kind == "fifo":
    assert stat.S_ISFIFO(marker.lstat().st_mode)
else:
    assert marker.is_dir()
print("refused and preserved")
"""


@pytest.mark.parametrize("kind", ["symlink", "dangling", "fifo", "directory"])
@pytest.mark.parametrize("when", ["existing", "collision"])
def test_a_special_marker_is_refused_without_following_replacing_or_blocking(tmp_path, kind, when):
    result = subprocess.run(  # noqa: S603 - a bounded child probes potentially blocking filesystem operations
        [sys.executable, "-c", SPECIAL_ENTRY_PROBE, str(tmp_path), kind, when],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == "refused and preserved"


@pytest.mark.parametrize("where", ["marker", "directory"])
@pytest.mark.parametrize("when", ["missing", "existing", "collision"])
def test_a_sync_error_never_cleans_up_an_owner_replacement(tmp_path, monkeypatch, where, when):
    if when == "existing":
        (tmp_path / MARKER).write_text("7\n")
    elif when == "collision":
        _owner_after_absence(monkeypatch, tmp_path, b"7\n")
    real_sync = os.fsync
    owner: list[int] = []

    def sync(fd):
        kind = "directory" if stat.S_ISDIR(os.fstat(fd).st_mode) else "marker"
        if kind == where and not owner:
            replacement = tmp_path / "owner"
            replacement.write_bytes(b"8\n")
            replacement.replace(tmp_path / MARKER)
            owner.extend(fd_tree.ident((tmp_path / MARKER).stat()))
            raise OSError(errno.EIO, "injected marker durability failure")
        return real_sync(fd)

    monkeypatch.setattr(os, "fsync", sync)
    tfd = os.open(tmp_path, fd_tree.DIR_FLAGS)
    try:
        with pytest.raises(StoreError, match=r"not finished|could not be made durable"):
            format_marker.ensure_target(tfd, 7)
    finally:
        os.close(tfd)

    assert owner
    assert (tmp_path / MARKER).read_bytes() == b"8\n"
    assert fd_tree.ident((tmp_path / MARKER).stat()) == owner
    assert sorted(p.name for p in tmp_path.iterdir()) == [MARKER]


@pytest.mark.parametrize("change", ["replace", "edit", "remove"])
def test_a_marker_changed_during_its_sync_is_not_admitted(tmp_path, monkeypatch, change):
    marker = tmp_path / MARKER
    marker.write_bytes(b"7\n")
    old = fd_tree.ident(marker.stat())
    real_sync = os.fsync
    changed = []

    def sync(fd):
        real_sync(fd)
        if fd_tree.ident(os.fstat(fd)) == old and not changed:
            changed.append(change)
            if change == "replace":
                replacement = tmp_path / "owner"
                replacement.write_bytes(b"7\n")
                replacement.replace(marker)
            elif change == "edit":
                marker.write_bytes(b"6\n")
            else:
                marker.unlink()

    monkeypatch.setattr(os, "fsync", sync)
    tfd = os.open(tmp_path, fd_tree.DIR_FLAGS)
    try:
        with pytest.raises(StoreError, match="changed while it was made durable"):
            format_marker.ensure_target(tfd, 7)
    finally:
        os.close(tfd)
    assert changed == [change]
    if change != "remove":
        assert marker.read_bytes() == (b"6\n" if change == "edit" else b"7\n")
    else:
        assert not marker.exists()


@pytest.fixture
def prepared_repo(tmp_path, monkeypatch, current_binding):
    assert current_binding.interpreter == Path(sys.executable)
    repo = tmp_path / "shop"
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True, capture_output=True)  # noqa: S603, S607
    source = project_home.clone_dir(repo)
    source.mkdir(parents=True)
    (source / MARKER).write_text("7\n")
    (source / "config.json").write_text(json.dumps({"format": 1, "widths": [1600]}))
    monkeypatch.setattr(offline_protocol, "boot_session", lambda: BEFORE)
    assert cli.main(["--repo", str(repo), "prepare"]) == 0
    monkeypatch.setattr(offline_protocol, "boot_session", lambda: AFTER)
    return repo, source, project_home.home(project_home.clone_id(source))


@pytest.fixture
def switched_repo(prepared_repo):
    repo, source, target = prepared_repo
    assert cli.main(["--repo", str(repo), "finish"]) == 0
    assert Store.open(repo).root == target
    assert json.loads((source / project_move.MOVE_RECORD).read_text())["phase"] == project_move.SWITCHED
    return repo, source, target


def test_public_switched_store_repair_refuses_a_future_collision_without_fallback(switched_repo, monkeypatch):
    repo, source, target = switched_repo
    (target / MARKER).unlink()
    saved = {name: (source / name).read_bytes() for name in (MARKER, project_move.MOVE_RECORD, project_move.PREPARED)}
    owner = _owner_after_absence(monkeypatch, target, b"8\n")

    def no_fallback(*_args, **_kwargs):
        pytest.fail("a refused switched marker started a fresh preparation or relocation")

    monkeypatch.setattr(offline_protocol, "prepare_clone", no_fallback)
    monkeypatch.setattr(offline_protocol, "finish_clone", no_fallback)
    monkeypatch.setattr(project_move, "relocate", no_fallback)
    with pytest.raises(FormatTooNewError, match="store format 8 is newer than 7"):
        Store.open(repo)

    assert owner
    assert (target / MARKER).read_bytes() == b"8\n"
    assert fd_tree.ident((target / MARKER).stat()) == owner
    assert {name: (source / name).read_bytes() for name in saved} == saved
    assert (target / "config.json").exists()


@pytest.mark.parametrize("collision", [False, True], ids=["existing", "collided"])
def test_public_switched_store_makes_an_owner_marker_durable_without_replacement(switched_repo, monkeypatch, collision):
    repo, _, target = switched_repo
    if collision:
        (target / MARKER).unlink()
        owner = _owner_after_absence(monkeypatch, target, b"7\n")
    else:
        owner = fd_tree.ident((target / MARKER).stat())
    before = (target / "config.json").read_bytes()
    events = _observe_syncs(monkeypatch, target)

    assert Store.open(repo).root == target

    assert (target / MARKER).read_bytes() == b"7\n"
    assert fd_tree.ident((target / MARKER).stat()) == owner
    assert (target / "config.json").read_bytes() == before
    _assert_durable(events, target)


@pytest.mark.parametrize("when", ["missing", "existing", "collision"])
def test_public_finish_syncs_the_marker_and_directory_before_switched(prepared_repo, monkeypatch, when):
    repo, source, target = prepared_repo
    real_ensure, real_save = format_marker.ensure_target, project_move._save  # noqa: SLF001 - publication boundary
    owner: list[int] = []
    events = _observe_syncs(monkeypatch, target)
    switches = []

    def ensure(tfd, previous, **kwargs):
        if not owner and when == "existing":
            (target / MARKER).write_text("7\n")
            owner.extend(fd_tree.ident((target / MARKER).stat()))
        real_ensure(tfd, previous, **kwargs)

    if when == "collision":
        owner = _owner_after_absence(monkeypatch, target, b"7\n")

    def save(folder, folder_fd, rec, **kwargs):
        if rec["phase"] == project_move.SWITCHED:
            _assert_durable(events, target)
            if owner:
                assert fd_tree.ident((target / MARKER).stat()) == owner
            switches.append(rec["phase"])
        real_save(folder, folder_fd, rec, **kwargs)

    monkeypatch.setattr(format_marker, "ensure_target", ensure)
    monkeypatch.setattr(project_move, "_save", save)

    assert cli.main(["--repo", str(repo), "finish"]) == 0
    assert switches == [project_move.SWITCHED]
    assert json.loads((source / project_move.MOVE_RECORD).read_text())["phase"] == project_move.SWITCHED
    assert (target / MARKER).read_text() == "7\n"


def test_public_finish_refuses_a_future_collision_before_switched(prepared_repo, monkeypatch, capsys):
    repo, source, target = prepared_repo
    owner = _owner_after_absence(monkeypatch, target, b"8\n")

    assert cli.main(["--repo", str(repo), "finish"]) == 1

    assert "store format 8 is newer than 7" in capsys.readouterr().err
    assert owner
    assert (target / MARKER).read_bytes() == b"8\n"
    assert fd_tree.ident((target / MARKER).stat()) == owner
    assert json.loads((source / project_move.MOVE_RECORD).read_text())["phase"] == project_move.COPYING


@pytest.mark.parametrize("where", ["marker", "directory"])
def test_public_finish_refuses_a_collided_marker_whose_sync_failed(prepared_repo, monkeypatch, capsys, where):
    repo, source, target = prepared_repo
    owner = _owner_after_absence(monkeypatch, target, b"7\n")
    real_sync = os.fsync
    failures = []

    def sync(fd):
        if owner and not failures:
            want = owner if where == "marker" else fd_tree.ident(target.stat())
            if fd_tree.ident(os.fstat(fd)) == want:
                failures.append(where)
                raise OSError(errno.EIO, "injected collided marker sync failure")
        real_sync(fd)

    monkeypatch.setattr(os, "fsync", sync)

    assert cli.main(["--repo", str(repo), "finish"]) == 1

    assert "could not be made durable" in capsys.readouterr().err
    assert failures == [where]
    assert (target / MARKER).read_bytes() == b"7\n"
    assert fd_tree.ident((target / MARKER).stat()) == owner
    assert json.loads((source / project_move.MOVE_RECORD).read_text())["phase"] == project_move.COPYING


@pytest.mark.parametrize(
    ("marker", "message"),
    [(b"8\n", "store format 8 is newer than 7"), (b"\xff\n", "format marker is not a regular file")],
)
def test_public_finish_still_validates_the_marker_after_the_publication_sync(
    prepared_repo, monkeypatch, capsys, marker, message
):
    repo, source, target = prepared_repo
    real_sync = project_move._sync_published  # noqa: SLF001 - the final publication-sync boundary
    owner: list[int] = []

    def sync(pfd, published, tfd):
        replacement = target / "owner"
        replacement.write_bytes(marker)
        replacement.replace(target / MARKER)
        owner.extend(fd_tree.ident((target / MARKER).stat()))
        real_sync(pfd, published, tfd)

    monkeypatch.setattr(project_move, "_sync_published", sync)
    assert cli.main(["--repo", str(repo), "finish"]) == 1
    assert message in capsys.readouterr().err

    assert owner
    assert (target / MARKER).read_bytes() == marker
    assert fd_tree.ident((target / MARKER).stat()) == owner
    assert json.loads((source / project_move.MOVE_RECORD).read_text())["phase"] == project_move.COPYING
