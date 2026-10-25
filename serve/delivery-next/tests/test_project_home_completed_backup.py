"""A completed move fences its source at 999; the immutable 51aa opener refuses it, the current one admits the target.

The immutable opener is ``git archive`` of the audited commit, run in a child process with a temporary HOME, so
no live runtime or real HOME is touched. The source is never deleted: it stays where the move left it.
"""

import io
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

from owlbear_delivery_next.state_store import offline_protocol, project_home, project_move
from owlbear_delivery_next.state_store.database import StoreError

SOURCE_ID = "abc123"
BEFORE, AFTER = "AAAAAAAA-0000-4000-8000-000000000001", "BBBBBBBB-0000-4000-8000-000000000002"
AUDITED = "51aa0e1c60b3f8a1b15faf57d6ab4a84d4ac20a3"
OPEN_51AA = (
    "import sys\n"
    "from pathlib import Path\n"
    "from owlbear_delivery_next.state_store.store import Store\n"
    "Store.open(Path(sys.argv[1]))\n"
)


@pytest.fixture
def clone(tmp_path):
    """A clone whose store folder holds one run log and a clone id, as the post-switch tests build it."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True, capture_output=True)  # noqa: S607
    folder = repo / ".git" / "owlbear-delivery"
    (folder / "changes" / "c1").mkdir(parents=True)
    (folder / "changes" / "c1" / "runner.log").write_text("ran\n")
    (folder / "clone-id").write_text(f"{SOURCE_ID}\n")
    return repo, folder


def move(repo, monkeypatch):
    """Prepare before a boot session, then finish after a different one: the production sequence."""
    monkeypatch.setattr(offline_protocol, "boot_session", lambda: BEFORE)
    offline_protocol.prepare_clone(repo, gaps=lambda: ())
    monkeypatch.setattr(offline_protocol, "boot_session", lambda: AFTER)
    return offline_protocol.finish_clone(repo, gaps=lambda: ())


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
    clone, monkeypatch, immutable_51aa, tmp_path
):
    repo, folder = clone
    move(repo, monkeypatch)
    assert (folder / project_home.MARKER).read_text().strip() == project_move.FENCE
    before = receipt_bytes(folder)

    result = run_51aa(immutable_51aa, repo, tmp_path / "home")

    assert result.returncode != 0, result.stdout
    assert "newer" in result.stderr, result.stderr
    assert (folder / project_home.MARKER).read_text().strip() == project_move.FENCE
    assert receipt_bytes(folder) == before
    assert (folder / "changes" / "c1" / "runner.log").read_text() == "ran\n"


def test_the_current_opener_admits_the_proved_target_after_the_completed_move(clone, monkeypatch):
    repo, folder = clone
    move(repo, monkeypatch)
    target = project_home.located(repo)

    assert (target / "changes" / "c1" / "runner.log").read_text() == "ran\n"
    assert (folder / project_home.MARKER).read_text().strip() == project_move.FENCE


def test_a_missing_target_refuses_and_keeps_the_source_and_receipt(clone, monkeypatch):
    repo, folder = clone
    move(repo, monkeypatch)
    target = project_home.located(repo)
    before = receipt_bytes(folder)
    shutil.rmtree(target)

    with pytest.raises(StoreError):
        project_home.located(repo)

    assert receipt_bytes(folder) == before
    assert (folder / "changes" / "c1" / "runner.log").read_text() == "ran\n"


def test_a_replaced_target_refuses_and_keeps_the_source_and_receipt(clone, monkeypatch):
    repo, folder = clone
    move(repo, monkeypatch)
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


def test_a_malformed_receipt_refuses_and_is_not_rewritten(clone, monkeypatch):
    repo, folder = clone
    move(repo, monkeypatch)
    garbage = b"{not json"
    (folder / project_move.MOVE_RECORD).write_bytes(garbage)

    with pytest.raises(StoreError):
        project_home.located(repo)

    assert receipt_bytes(folder) == garbage
    assert (folder / project_home.MARKER).read_text().strip() == project_move.FENCE
