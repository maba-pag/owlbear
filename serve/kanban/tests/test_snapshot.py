"""Behavioral coverage for immutable legacy snapshot publication."""

from __future__ import annotations

from pathlib import Path

import pytest

from owlbear_kanban import (
    LegacyActiveItem,
    LegacyDisposition,
    LegacySnapshotDestinationError,
    LegacySnapshotDispositionError,
    LegacySnapshotPathError,
    LegacySnapshotPublicationError,
    LegacySnapshotSourceChangedError,
    LegacySnapshotVerificationError,
    create_legacy_snapshot,
    inventory_legacy_source,
    verify_legacy_snapshot,
)


def _legacy_root(tmp_path: Path) -> Path:
    root = tmp_path / "legacy"
    (root / "tasks").mkdir(parents=True)
    (root / "archive").mkdir()
    (root / "tasks" / "1-active.md").write_text("active\n", encoding="utf-8")
    (root / "archive" / "2-done.md").write_text("done\n", encoding="utf-8")
    return root


def _active_items() -> tuple[LegacyActiveItem, ...]:
    return (LegacyActiveItem(item_id="task:1", relative_path="tasks/1-active.md"),)


def _dispositions() -> dict[str, LegacyDisposition]:
    return {"task:1": LegacyDisposition.REINTRODUCE_NATIVE}


def test_snapshot_publishes_verified_copy_and_manifest(tmp_path: Path) -> None:
    source = _legacy_root(tmp_path)
    destination = tmp_path / "snapshots" / "legacy-v1"
    expected = inventory_legacy_source(source, _active_items(), _dispositions())

    result = create_legacy_snapshot(source, destination, _active_items(), _dispositions())
    verified = verify_legacy_snapshot(destination)

    assert result.manifest == expected
    assert verified == result
    assert result.destination == destination
    assert result.manifest.file_count == 2
    assert result.manifest.directory_count == 2
    assert result.manifest.total_bytes == len(b"active\n") + len(b"done\n")
    assert result.manifest.active_items[0].disposition is LegacyDisposition.REINTRODUCE_NATIVE
    assert (destination / "content/tasks/1-active.md").read_bytes() == b"active\n"
    assert result.manifest_path.read_bytes()
    assert (source / "tasks/1-active.md").read_bytes() == b"active\n"


def test_snapshot_requires_exact_active_item_dispositions(tmp_path: Path) -> None:
    source = _legacy_root(tmp_path)
    before = {path.relative_to(source): path.read_bytes() for path in source.rglob("*") if path.is_file()}

    with pytest.raises(LegacySnapshotDispositionError):
        create_legacy_snapshot(source, tmp_path / "snapshot", _active_items(), {})

    after = {path.relative_to(source): path.read_bytes() for path in source.rglob("*") if path.is_file()}
    assert after == before
    assert not (tmp_path / "snapshot").exists()


def test_snapshot_rejects_existing_destination_without_overwrite(tmp_path: Path) -> None:
    source = _legacy_root(tmp_path)
    destination = tmp_path / "snapshot"
    destination.mkdir()
    marker = destination / "owned.txt"
    marker.write_text("keep\n", encoding="utf-8")

    with pytest.raises(LegacySnapshotDestinationError):
        create_legacy_snapshot(source, destination, _active_items(), _dispositions())

    assert marker.read_text(encoding="utf-8") == "keep\n"


def test_snapshot_rejects_symlinked_source_entry(tmp_path: Path) -> None:
    source = _legacy_root(tmp_path)
    outside = tmp_path / "outside.txt"
    outside.write_text("outside\n", encoding="utf-8")
    (source / "tasks" / "escape.md").symlink_to(outside)

    with pytest.raises(LegacySnapshotPathError):
        create_legacy_snapshot(source, tmp_path / "snapshot", _active_items(), _dispositions())

    assert not (tmp_path / "snapshot").exists()


def test_snapshot_rejects_symlinked_destination_ancestor(tmp_path: Path) -> None:
    source = _legacy_root(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    linked = tmp_path / "linked"
    linked.symlink_to(outside, target_is_directory=True)

    with pytest.raises(LegacySnapshotPathError):
        create_legacy_snapshot(source, linked / "nested/snapshot", _active_items(), _dispositions())

    assert not (outside / "nested").exists()


def test_snapshot_rejects_destination_ancestor_swap_before_publication(tmp_path: Path) -> None:
    source = _legacy_root(tmp_path)
    parent = tmp_path / "snapshots"
    parent.mkdir()
    moved_parent = tmp_path / "moved-snapshots"
    outside = tmp_path / "outside"
    outside.mkdir()
    destination = parent / "snapshot"

    def swap_parent(stage: str, _staging: Path) -> None:
        if stage == "before-publication":
            parent.rename(moved_parent)
            parent.symlink_to(outside, target_is_directory=True)

    with pytest.raises(LegacySnapshotPathError):
        create_legacy_snapshot(source, destination, _active_items(), _dispositions(), failure=swap_parent)

    assert not (outside / "snapshot").exists()
    assert not (moved_parent / "snapshot").exists()
    assert not list(moved_parent.glob(".tmp-snapshot-*"))


def test_snapshot_rolls_back_destination_ancestor_swap_after_publication(tmp_path: Path) -> None:
    source = _legacy_root(tmp_path)
    parent = tmp_path / "snapshots"
    parent.mkdir()
    moved_parent = tmp_path / "moved-snapshots"
    outside = tmp_path / "outside"
    outside.mkdir()
    destination = parent / "snapshot"

    def swap_parent(stage: str, _published: Path) -> None:
        if stage == "after-publication":
            parent.rename(moved_parent)
            parent.symlink_to(outside, target_is_directory=True)

    with pytest.raises(LegacySnapshotPathError):
        create_legacy_snapshot(source, destination, _active_items(), _dispositions(), failure=swap_parent)

    assert not (outside / "snapshot").exists()
    assert not (moved_parent / "snapshot").exists()


def test_snapshot_rejects_source_change_before_publication(tmp_path: Path) -> None:
    source = _legacy_root(tmp_path)
    destination = tmp_path / "snapshot"

    def mutate_source(stage: str, _staging: Path) -> None:
        if stage == "before-publication":
            (source / "tasks" / "1-active.md").write_text("changed\n", encoding="utf-8")

    with pytest.raises(LegacySnapshotSourceChangedError):
        create_legacy_snapshot(source, destination, _active_items(), _dispositions(), failure=mutate_source)

    assert not destination.exists()


def test_snapshot_rolls_back_source_change_after_publication(tmp_path: Path) -> None:
    source = _legacy_root(tmp_path)
    destination = tmp_path / "snapshot"

    def mutate_source(stage: str, _published: Path) -> None:
        if stage == "after-publication":
            (source / "tasks" / "1-active.md").write_text("changed\n", encoding="utf-8")

    with pytest.raises(LegacySnapshotSourceChangedError):
        create_legacy_snapshot(source, destination, _active_items(), _dispositions(), failure=mutate_source)

    assert not destination.exists()


def test_snapshot_rejects_staged_hash_mismatch_and_replays(tmp_path: Path) -> None:
    source = _legacy_root(tmp_path)
    destination = tmp_path / "snapshot"

    def corrupt_staging(stage: str, staging: Path) -> None:
        if stage == "after-staging":
            (staging / "content/tasks/1-active.md").write_text("corrupt\n", encoding="utf-8")

    with pytest.raises(LegacySnapshotVerificationError):
        create_legacy_snapshot(source, destination, _active_items(), _dispositions(), failure=corrupt_staging)

    result = create_legacy_snapshot(source, destination, _active_items(), _dispositions())
    assert result.manifest.file_count == 2
    assert (destination / "content/tasks/1-active.md").read_bytes() == b"active\n"


def test_snapshot_publication_failure_cleans_staging_and_replays(tmp_path: Path) -> None:
    source = _legacy_root(tmp_path)
    destination = tmp_path / "snapshot"

    def interrupt(stage: str, _staging: Path) -> None:
        if stage == "before-publication":
            message = "injected publication interruption"
            raise OSError(message)

    with pytest.raises(LegacySnapshotPublicationError, match="injected publication interruption"):
        create_legacy_snapshot(source, destination, _active_items(), _dispositions(), failure=interrupt)

    assert not destination.exists()
    assert not list(tmp_path.glob(".tmp-snapshot-*"))
    result = create_legacy_snapshot(source, destination, _active_items(), _dispositions())
    assert result.manifest_path.is_file()
