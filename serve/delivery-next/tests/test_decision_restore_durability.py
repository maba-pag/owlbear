"""Durability and ownership regressions for the decision-batch restore: a failed parent fsync after a restore rename,
an owner edit during a refused commit, and the known-refusal and ambiguous-publication controls beside them.

Each test saves through the public store API on a real temporary repository. Only the Git publish outcome and the
directory fsync are injected.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from owlbear_decisions import Decision, Link, LinkType, Origin, Scope, State, new_id, read
from owlbear_delivery_next.change_contracts.models import Brief, Change
from owlbear_delivery_next.local_system import storage_io
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.state_store import (
    change_record,
    decision_batch,
    decision_recovery,
    decision_store,
    decision_sync,
)

PROJECT = "shop-site"
AT = datetime(2026, 10, 21, 9, tzinfo=UTC)
OWNER = b"an owner edit, not a decision\n"


def make(**changes) -> Decision:
    fields = {
        "id": new_id(), "title": "Notes live in SQLite", "statement": "Notes live in SQLite.",
        "scope": Scope.PROJECT, "project": PROJECT, "origin": Origin.AUTONOMOUS, "actor": "shaper",
        "state": State.IN_FORCE, "created_at": AT,
    }  # fmt: skip
    return Decision(**{**fields, **changes})


def _committed(picking) -> tuple[Decision, bytes]:
    """A decision already in HEAD, read back from its file so its revision is the one on disk, and its bytes."""
    old = make()
    assert decision_store.save(picking.shared, old, expected_revision=None, message="decisions: old").saved
    path = _file(picking, old)
    return read(path), path.read_bytes()


def _file(picking, decision: Decision) -> Path:
    return picking.shared.root / PROJECT / "decisions" / f"{decision.id}.md"


def _refused(*_args, **_kwargs) -> decision_sync.Sent:
    return decision_sync.Sent(uncommitted=True, notice="git refused the commit")


def _unknown(*_args, **_kwargs) -> decision_sync.Sent:
    return decision_sync.Sent(ambiguous=True, notice="the publication is unknown")


def _successor(old: Decision) -> Decision:
    """The new decision that replaces the committed one."""
    return make(links=(Link(type=LinkType.REPLACES, target=old.id),), statement="Notes live in Postgres.")


def _save_supersede(picking, old: Decision, successor: Decision, extra: list | None = None):
    retired = old.model_copy(update={"state": State.REPLACED})
    batch = [(successor, None), (retired, old.revision), *(extra or [])]
    return decision_store.save_all(picking.shared, batch, message="decisions: supersede")


def _head(picking) -> str:
    return picking.shared.git("rev-parse", "HEAD").stdout.strip()


def test_a_known_refusal_puts_the_before_image_back_and_completes(picking, monkeypatch):
    old, before = _committed(picking)
    path = _file(picking, old)
    successor = _successor(old)
    successor_path = _file(picking, successor)
    seen: dict[str, bytes] = {}

    def refused_after_write(*args, **kwargs):
        seen["during"] = successor_path.read_bytes()  # the new bytes are on disk when the refusal arrives
        return _refused(*args, **kwargs)

    monkeypatch.setattr(decision_sync, "publish", refused_after_write)

    _save_supersede(picking, old, successor)

    assert b"Notes live in Postgres." in seen["during"]
    assert path.read_bytes() == before
    assert not successor_path.exists()
    assert decision_batch.pending(picking.shared) is None


def test_an_ambiguous_publication_keeps_the_new_bytes_and_the_batch_interrupted(picking, monkeypatch):
    old, _ = _committed(picking)
    successor = _successor(old)
    successor_path = _file(picking, successor)
    monkeypatch.setattr(decision_sync, "publish", _unknown)

    _save_supersede(picking, old, successor)

    assert b"Notes live in Postgres." in successor_path.read_bytes()
    assert decision_batch.pending(picking.shared) is not None


def test_a_restore_whose_parent_fsync_fails_after_the_rename_stays_pending_and_then_abandons(picking, monkeypatch):
    old, before = _committed(picking)
    path = _file(picking, old)
    real_fsync, state = decision_batch.fsync_dir, {"armed": False, "failed": False}

    def fsync_once_fails(folder):
        # the fault is the parent fsync that follows the rename of the restored file, not the earlier unlink
        if state["armed"] and not state["failed"] and path.read_bytes() == before:
            state["failed"] = True
            msg = "the parent fsync failed after the rename"
            raise OSError(msg)
        real_fsync(folder)

    def refused_after_arming(*args, **kwargs):
        state["armed"] = True  # the fault belongs to the restore, not to the journal written before the commit
        return _refused(*args, **kwargs)

    monkeypatch.setattr(decision_batch, "fsync_dir", fsync_once_fails)
    monkeypatch.setattr(decision_sync, "publish", refused_after_arming)

    _save_supersede(picking, old, _successor(old))

    assert state["failed"]
    assert path.read_bytes() == before  # the rename landed before the parent fsync failed
    pending = decision_batch.pending(picking.shared)
    assert pending is not None  # the restore is not durable, so the batch is not completed
    decision_recovery.abandon(picking.shared, pending.generation)
    assert decision_batch.pending(picking.shared) is None
    assert path.read_bytes() == before


def test_an_owner_edit_during_a_refused_commit_keeps_the_owner_bytes_and_the_batch(picking, monkeypatch):
    old, _ = _committed(picking)
    path = _file(picking, old)
    head = _head(picking)

    def refused_after_owner_edit(*args, **kwargs):
        path.write_bytes(OWNER)
        return _refused(*args, **kwargs)

    monkeypatch.setattr(decision_sync, "publish", refused_after_owner_edit)

    _save_supersede(picking, old, _successor(old))

    assert path.read_bytes() == OWNER
    assert decision_batch.pending(picking.shared) is not None
    assert _head(picking) == head


def test_an_owner_edit_to_one_file_keeps_the_whole_batch_as_written(picking, monkeypatch):
    old, _ = _committed(picking)
    successor = _successor(old)
    second = make(title="Notes in A", statement="Notes are in A.")
    successor_path, second_path = _file(picking, successor), _file(picking, second)

    def refused_after_owner_edit(*args, **kwargs):
        second_path.write_bytes(OWNER)  # the owner edits one file of the batch during the refused commit
        return _refused(*args, **kwargs)

    monkeypatch.setattr(decision_sync, "publish", refused_after_owner_edit)

    _save_supersede(picking, old, successor, extra=[(second, None)])

    # not put back: the batch is not wholly the file's own
    assert b"Notes live in Postgres." in successor_path.read_bytes()
    assert second_path.read_bytes() == OWNER
    assert decision_batch.pending(picking.shared) is not None


def _finished_change() -> Change:
    brief = Brief(version=2, title="Notes", outcome="Owners keep notes", approved_at=AT)
    return Change(slug="notes", handle="c4", brief=Brief(version=2, approved_at=AT, approved=[brief]))


class _Store:
    def __init__(self, root: Path) -> None:
        self.shared, self.name = DataRepo(root), PROJECT


def _where(folder: Path, root: Path) -> str:
    """A synced folder's place under the data root; a folder outside it, such as the root's parent, is named outside."""
    if not Path(folder).is_relative_to(root):
        return "outside"
    return Path(folder).relative_to(root).as_posix() or "."


def test_a_new_project_folder_and_its_parent_are_fsynced_before_the_record_is_published(shared_repo, monkeypatch):
    root, _ = shared_repo
    store = _Store(root)
    events: list[str] = []
    real_fsync, real_publish = storage_io.fsync_dir, decision_sync.publish

    def traced_fsync(folder: Path) -> None:
        events.append(f"fsync {_where(folder, root)}")
        real_fsync(folder)

    def traced_publish(*args, **kwargs):
        events.append("publish")
        return real_publish(*args, **kwargs)

    assert not (root / PROJECT).exists()
    monkeypatch.setattr(storage_io, "fsync_dir", traced_fsync)
    monkeypatch.setattr(decision_sync, "publish", traced_publish)

    change_record.save(store, _finished_change(), None, AT)

    assert events.index("fsync .") < events.index("fsync " + PROJECT) < events.index("publish")
    assert (root / PROJECT / "changes").is_dir()


def test_an_existing_project_folder_publishes_without_refsyncing_the_root(shared_repo, monkeypatch):
    root, _ = shared_repo
    store = _Store(root)
    (root / PROJECT / "changes").mkdir(parents=True)
    events: list[str] = []
    real_fsync, real_publish = storage_io.fsync_dir, decision_sync.publish

    def traced_fsync(folder: Path) -> None:
        events.append(f"fsync {_where(folder, root)}")
        real_fsync(folder)

    def traced_publish(*args, **kwargs):
        events.append("publish")
        return real_publish(*args, **kwargs)

    monkeypatch.setattr(storage_io, "fsync_dir", traced_fsync)
    monkeypatch.setattr(decision_sync, "publish", traced_publish)

    assert change_record.save(store, _finished_change(), None, AT) == ""

    assert "fsync ." not in events
    assert "publish" in events


def test_a_symlink_leaf_with_matching_bytes_rejects_the_whole_batch_before_any_restore(picking, monkeypatch, tmp_path):
    old, before = _committed(picking)
    path = _file(picking, old)
    successor = _successor(old)
    successor_path = _file(picking, successor)
    outside = tmp_path / "outside.md"
    outside.write_bytes(before)
    head = _head(picking)

    def refused_after_swap(*args, **kwargs):
        path.unlink()
        path.symlink_to(outside)
        return _refused(*args, **kwargs)

    monkeypatch.setattr(decision_sync, "publish", refused_after_swap)

    _save_supersede(picking, old, successor)

    assert path.is_symlink()
    assert outside.read_bytes() == before
    assert successor_path.exists()
    assert _head(picking) == head
    assert decision_batch.pending(picking.shared) is not None


def test_a_symlink_parent_with_matching_bytes_rejects_the_whole_batch_before_any_restore(
    picking, monkeypatch, tmp_path
):
    old, before = _committed(picking)
    path = _file(picking, old)
    folder = path.parent
    successor = _successor(old)
    successor_path = _file(picking, successor)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / path.name).write_bytes(before)
    head = _head(picking)

    def refused_after_swap(*args, **kwargs):
        moved = tmp_path / "moved"
        folder.rename(moved)
        folder.symlink_to(outside, target_is_directory=True)
        return _refused(*args, **kwargs)

    monkeypatch.setattr(decision_sync, "publish", refused_after_swap)

    _save_supersede(picking, old, successor)

    assert folder.is_symlink()
    assert (outside / path.name).read_bytes() == before
    assert not (outside / successor_path.name).exists()
    assert (tmp_path / "moved" / successor_path.name).exists()
    assert _head(picking) == head
    assert decision_batch.pending(picking.shared) is not None
