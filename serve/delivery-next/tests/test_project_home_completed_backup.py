"""A completed move fences its source at 999; the immutable 51aa opener refuses it, the current one admits the target.

The immutable opener is ``git archive`` of the audited commit, run in a child process with a temporary HOME, so
no live runtime or real HOME is touched. The source is never deleted: it stays where the move left it.
"""

import io
import os
import shutil
import subprocess
import sys
import tarfile
import threading
from pathlib import Path

import pytest

from owlbear_delivery_next.local_system import local_home
from owlbear_delivery_next.state_store import fd_tree, project_home, project_move
from owlbear_delivery_next.state_store.database import StoreError

AUDITED = "51aa0e1c60b3f8a1b15faf57d6ab4a84d4ac20a3"
OPEN_51AA = (
    "import sys\n"
    "from pathlib import Path\n"
    "from owlbear_delivery_next.state_store.store import Store\n"
    "Store.open(Path(sys.argv[1]))\n"
)


@pytest.fixture
def immutable_51aa(tmp_path):
    """The audited 51aa source tree, extracted from git and importable on its own."""
    root = tmp_path / "audited"
    root.mkdir()
    archive = subprocess.run(  # noqa: S603
        ["git", "archive", AUDITED, "serve/delivery-next/src"],  # noqa: S607
        cwd=Path(__file__).resolve().parents[3],
        check=True,
        capture_output=True,
    ).stdout
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(root, filter="data")
    return root / "serve" / "delivery-next" / "src"


def run_51aa(src: Path, repo: Path, home: Path) -> subprocess.CompletedProcess:
    env = {"PATH": "/usr/bin:/bin", "HOME": str(home), "PYTHONPATH": str(src)}
    return subprocess.run(  # noqa: S603
        [sys.executable, "-c", OPEN_51AA, str(repo)],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def receipt_bytes(folder: Path) -> bytes | None:
    path = folder / project_move.MOVE_RECORD
    return path.read_bytes() if path.exists() else None


def test_the_completed_source_is_fenced_at_999_and_the_immutable_opener_refuses_it(
    legacy_project_clone, offline_move, immutable_51aa, tmp_path
):
    repo, folder = legacy_project_clone
    offline_move(repo)
    assert (folder / project_home.MARKER).read_text().strip() == project_move.FENCE
    before = receipt_bytes(folder)

    result = run_51aa(immutable_51aa, repo, tmp_path / "home")

    assert result.returncode != 0, result.stdout
    assert "newer" in result.stderr, result.stderr
    assert (folder / project_home.MARKER).read_text().strip() == project_move.FENCE
    assert receipt_bytes(folder) == before
    assert (folder / "changes" / "c1" / "runner.log").read_text() == "ran\n"


def test_a_missing_target_refuses_and_keeps_the_source_and_receipt(legacy_project_clone, offline_move):
    repo, folder = legacy_project_clone
    offline_move(repo)
    target = project_home.located(repo)
    before = receipt_bytes(folder)
    shutil.rmtree(target)

    with pytest.raises(StoreError):
        project_home.located(repo)

    assert receipt_bytes(folder) == before
    assert (folder / "changes" / "c1" / "runner.log").read_text() == "ran\n"


def test_a_replaced_target_refuses_and_keeps_the_source_and_receipt(legacy_project_clone, offline_move):
    repo, folder = legacy_project_clone
    offline_move(repo)
    target = project_home.located(repo)
    before = receipt_bytes(folder)
    shutil.rmtree(target)
    target.mkdir()
    (target / "impostor").write_text("foreign\n")

    with pytest.raises(StoreError):
        project_home.located(repo)

    assert receipt_bytes(folder) == before
    assert (folder / "changes" / "c1" / "runner.log").read_text() == "ran\n"
    assert (target / "impostor").read_text() == "foreign\n"


def test_a_replaced_target_with_the_same_identity_refuses_and_keeps_the_impostor(
    legacy_project_clone, offline_move, monkeypatch
):
    """A freed folder can come back with the same device and inode (Linux reuses them); identity alone is not proof."""
    repo, folder = legacy_project_clone
    # project_move holds its own alias of fd_tree.ident; project_switch and switched_authority call the module.
    monkeypatch.setattr(project_move, "_ident", lambda _st: [0, 0])
    monkeypatch.setattr(fd_tree, "ident", lambda _st: [0, 0])
    offline_move(repo)
    target = project_home.located(repo)
    before = receipt_bytes(folder)
    shutil.rmtree(target)
    target.mkdir()
    (target / "impostor").write_text("foreign\n")

    with pytest.raises(StoreError):
        project_home.located(repo)

    assert receipt_bytes(folder) == before
    assert (folder / "changes" / "c1" / "runner.log").read_text() == "ran\n"
    assert (target / "impostor").read_text() == "foreign\n"


def test_a_malformed_receipt_refuses_and_is_not_rewritten(legacy_project_clone, offline_move):
    repo, folder = legacy_project_clone
    offline_move(repo)
    garbage = b"{not json"
    (folder / project_move.MOVE_RECORD).write_bytes(garbage)

    with pytest.raises(StoreError):
        project_home.located(repo)

    assert receipt_bytes(folder) == garbage
    assert (folder / project_home.MARKER).read_text().strip() == project_move.FENCE


def _replace_after_create(monkeypatch, replacement):
    """Swap the move's proof for *replacement* right after it is created, before it is read back."""
    real_create = fd_tree.create_at

    def create(dfd, name, text):
        real_create(dfd, name, text)
        if name == project_move.MOVE_PROOF:
            os.unlink(name, dir_fd=dfd)
            replacement(dfd, name)

    monkeypatch.setattr(fd_tree, "create_at", create)


def _foreign_regular(dfd, name):
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=dfd)
    with os.fdopen(fd, "wb") as fh:
        fh.write(b"previous-generation\n")


@pytest.mark.parametrize("kind", ["regular", "symlink"])
def test_a_proof_replaced_after_creation_refuses_and_keeps_the_foreign_entry(
    legacy_project_clone, offline_move, monkeypatch, tmp_path, kind
):
    """The record must hold the nonce the move wrote; an entry put in its place is refused, never recorded."""
    repo, _ = legacy_project_clone
    foreign = tmp_path / "foreign-target"
    foreign.write_text("foreign\n")
    if kind == "regular":
        _replace_after_create(monkeypatch, _foreign_regular)
    else:
        _replace_after_create(monkeypatch, lambda dfd, name: os.symlink(foreign, name, dir_fd=dfd))

    with pytest.raises(StoreError) as caught:
        offline_move(repo)

    assert "was replaced while it was written" in str(caught.value), str(caught.value)
    assert foreign.read_text() == "foreign\n"
    kept = list(local_home.root().rglob(project_move.MOVE_PROOF))
    assert len(kept) == 1, [p.as_posix() for p in kept]
    if kind == "regular":
        assert kept[0].read_bytes() == b"previous-generation\n"
    else:
        assert kept[0].is_symlink()
    with pytest.raises(StoreError):
        project_home.located(repo)


def _outcome_within(seconds, call):
    """The exception or result of *call*, failing the test if it has not returned within *seconds*."""
    box = []

    def run():
        try:
            box.append(call())
        except Exception as exc:  # noqa: BLE001 - the outcome is the assertion
            box.append(exc)

    worker = threading.Thread(target=run, daemon=True)
    worker.start()
    worker.join(seconds)
    assert not worker.is_alive(), "the admission blocked on a special file"
    return box[0]


def test_a_fifo_committed_as_the_proof_refuses_without_blocking(legacy_project_clone, offline_move):
    repo, _ = legacy_project_clone
    offline_move(repo)
    target = project_home.located(repo)
    (target / project_move.MOVE_PROOF).unlink()
    os.mkfifo(target / project_move.MOVE_PROOF)

    assert isinstance(_outcome_within(10, lambda: project_home.located(repo)), StoreError)
