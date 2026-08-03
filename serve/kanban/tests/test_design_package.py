from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from owlbear_kanban import DesignPackageConflictError, DesignPackageManifest, DesignPackageStore

_GIT = "/usr/bin/git"
_PACKAGE_FILES = ("authority.json", "design.md", "intent.md", "manifest.json")


def _git(repository: Path, *arguments: str, input_bytes: bytes | None = None) -> str:
    result = subprocess.run(
        (_GIT, "-C", str(repository), *arguments),
        check=True,
        capture_output=True,
        input=input_bytes,
        text=input_bytes is None,
    )
    output = result.stdout
    return output.strip() if isinstance(output, str) else output.decode().strip()


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    path = tmp_path / "repository"
    path.mkdir()
    _git(path, "init", "-b", "product")
    _git(path, "config", "user.name", "Design Package Test")
    _git(path, "config", "user.email", "design-package@example.invalid")
    (path / "product.txt").write_text("product\n", encoding="utf-8")
    _git(path, "add", "product.txt")
    _git(path, "commit", "-m", "product baseline")
    return path


def _package_bytes(package_root: Path) -> dict[str, bytes]:
    return {name: (package_root / "sample-change" / name).read_bytes() for name in _PACKAGE_FILES}


def test_create_replays_identity_and_rejects_divergence_or_drift(repository: Path, tmp_path: Path) -> None:
    active_root = tmp_path / "active-packages"
    store = DesignPackageStore(active_root, repository)

    created = store.create("sample-change", b"# Intent\n", b"# Design\n")
    original = _package_bytes(active_root)
    replayed = store.create("sample-change", b"# Intent\n", b"# Design\n")

    assert replayed.package_id == created.package_id
    assert replayed.replayed is True
    assert original["authority.json"] == b""
    with pytest.raises(DesignPackageConflictError):
        store.create("sample-change", b"changed\n", b"# Design\n")
    assert _package_bytes(active_root) == original

    (active_root / "sample-change/design.md").write_bytes(b"drift\n")
    with pytest.raises(DesignPackageConflictError):
        store.create("sample-change", b"# Intent\n", b"# Design\n")
    assert (active_root / "sample-change/intent.md").read_bytes() == original["intent.md"]
    assert (active_root / "sample-change/design.md").read_bytes() == b"drift\n"

    for unsafe in ("Uppercase", "leading-", "../escape", "two--hyphens"):
        with pytest.raises(ValueError):
            store.create(unsafe, b"intent", b"design")


def test_previsibility_failure_leaves_no_package_and_clean_replay_succeeds(repository: Path, tmp_path: Path) -> None:
    active_root = tmp_path / "active-packages"

    def interrupt(stage: str) -> None:
        if stage == "before-publication":
            message = "injected failure"
            raise RuntimeError(message)

    failing_store = DesignPackageStore(active_root, repository, failure=interrupt)
    with pytest.raises(RuntimeError, match="injected failure"):
        failing_store.create("sample-change", b"intent\n", b"design\n")

    assert not (active_root / "sample-change").exists()
    assert not list((active_root / ".runtime-transactions").glob("*.yaml"))

    created = DesignPackageStore(active_root, repository).create("sample-change", b"intent\n", b"design\n")
    assert created.replayed is False
    assert _package_bytes(active_root)["authority.json"] == b""


def test_checkpoint_updates_only_package_history_and_replays_identical_content(
    repository: Path,
    tmp_path: Path,
) -> None:
    active_root = tmp_path / "active-packages"
    store = DesignPackageStore(active_root, repository)
    store.create("sample-change", b"intent\n", b"design\n")
    before = {
        "branch": _git(repository, "branch", "--show-current"),
        "head": _git(repository, "rev-parse", "HEAD"),
        "index": _git(repository, "write-tree"),
        "status": _git(repository, "status", "--porcelain"),
        "worktree": (repository / "product.txt").read_bytes(),
    }
    package_ref = "refs/owlbear/packages/sample-change"
    assert _git(repository, "for-each-ref", "--format=%(objectname)", package_ref) == ""

    first = store.checkpoint("sample-change")
    replayed = store.checkpoint("sample-change")

    assert replayed.commit == first.commit
    assert replayed.replayed is True
    assert _git(repository, "rev-parse", package_ref) == first.commit
    assert tuple(_git(repository, "ls-tree", "--name-only", first.commit).splitlines()) == _PACKAGE_FILES
    assert _git(repository, "rev-list", "--parents", "-n", "1", first.commit).split() == [first.commit]

    (active_root / "sample-change/design.md").write_bytes(b"revised design\n")
    manifest = DesignPackageManifest.from_content("sample-change", b"intent\n", b"revised design\n")
    (active_root / "sample-change/manifest.json").write_bytes(manifest.canonical_bytes())
    second = store.checkpoint("sample-change")

    assert second.commit != first.commit
    assert _git(repository, "rev-list", "--parents", "-n", "1", second.commit).split() == [second.commit, first.commit]
    assert _git(repository, "show", f"{second.commit}:design.md") == "revised design"
    assert {
        "branch": _git(repository, "branch", "--show-current"),
        "head": _git(repository, "rev-parse", "HEAD"),
        "index": _git(repository, "write-tree"),
        "status": _git(repository, "status", "--porcelain"),
        "worktree": (repository / "product.txt").read_bytes(),
    } == before
