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


def test_revise_cas_replaces_authored_bytes_and_clears_generated_authority(
    repository: Path,
    tmp_path: Path,
) -> None:
    active_root = tmp_path / "active-packages"
    store = DesignPackageStore(active_root, repository)
    created = store.create("sample-change", b"intent\n", b"design\n")

    replayed = store.revise("sample-change", created.package_id, b"intent\n", b"design\n")
    published = store.publish_contract(
        "sample-change",
        replayed.package_id,
        b'{"authority":true}\n',
        lambda *_content: None,
    )
    cleared = store.revise("sample-change", published.package_id, b"intent\n", b"design\n")
    republished = store.publish_contract(
        "sample-change",
        cleared.package_id,
        b'{"authority":true}\n',
        lambda *_content: None,
    )
    revised = store.revise("sample-change", republished.package_id, b"new intent\n", b"new design\n")

    assert replayed.package_id == created.package_id
    assert published.package_id != created.package_id
    assert cleared.package_id == created.package_id
    assert cleared.authority_bytes == b""
    assert revised.package_id not in {created.package_id, republished.package_id}
    assert revised.intent_bytes == b"new intent\n"
    assert revised.design_bytes == b"new design\n"
    assert revised.authority_bytes == b""
    assert store.read_verified("sample-change") == revised


def test_revise_rejects_stale_identity_without_mutation(repository: Path, tmp_path: Path) -> None:
    active_root = tmp_path / "active-packages"
    store = DesignPackageStore(active_root, repository)
    store.create("sample-change", b"intent\n", b"design\n")
    original = _package_bytes(active_root)

    with pytest.raises(DesignPackageConflictError, match="changed before authored revision"):
        store.revise("sample-change", "0" * 64, b"new intent\n", b"new design\n")

    assert _package_bytes(active_root) == original


@pytest.mark.parametrize("failure_stage", ["before-publication", "before-manifest-cleanup"])
def test_revise_handled_failure_restores_verified_old_package(
    failure_stage: str,
    repository: Path,
    tmp_path: Path,
) -> None:
    active_root = tmp_path / "active-packages"
    original_store = DesignPackageStore(active_root, repository)
    created = original_store.create("sample-change", b"intent\n", b"design\n")
    original = original_store.read_verified("sample-change")

    def interrupt(stage: str) -> None:
        if stage == failure_stage:
            message = "injected revision failure"
            raise RuntimeError(message)

    failing_store = DesignPackageStore(active_root, repository, failure=interrupt)
    with pytest.raises(RuntimeError, match="injected revision failure"):
        failing_store.revise("sample-change", created.package_id, b"new intent\n", b"new design\n")

    assert DesignPackageStore(active_root, repository).read_verified("sample-change") == original
    assert not list((active_root / ".runtime-transactions").glob("*.yaml"))


def test_revise_recovers_interrupted_publication_to_verified_new_package(
    repository: Path,
    tmp_path: Path,
) -> None:
    active_root = tmp_path / "active-packages"
    original_store = DesignPackageStore(active_root, repository)
    created = original_store.create("sample-change", b"intent\n", b"design\n")

    class SimulatedProcessExit(BaseException):
        pass

    def interrupt(stage: str) -> None:
        if stage == "after-first-publication":
            raise SimulatedProcessExit

    interrupted_store = DesignPackageStore(active_root, repository, failure=interrupt)
    with pytest.raises(SimulatedProcessExit):
        interrupted_store.revise("sample-change", created.package_id, b"new intent\n", b"new design\n")

    recovered = DesignPackageStore(active_root, repository).read_verified("sample-change")
    assert recovered.intent_bytes == b"new intent\n"
    assert recovered.design_bytes == b"new design\n"
    assert recovered.authority_bytes == b""
    assert not list((active_root / ".runtime-transactions").glob("*.yaml"))


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
