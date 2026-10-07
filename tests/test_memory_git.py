"""Memory batch commit attribution contracts."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import pytest
from owlbear_memory import MemoryCategory, MemoryEngine, MemoryEntry, MemoryState, storage

from owlbear_memory_mcp.git import commit_batch


def _git(repository: Path, *args: str) -> str:
    result = subprocess.run(  # noqa: S603
        ["git", *args],  # noqa: S607
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _write_entry(memory_dir: Path, *, state: MemoryState) -> Path:
    entry_id = str(uuid4())
    path = memory_dir / f"{entry_id}.md"
    entry = MemoryEntry(
        id=entry_id,
        title=f"{state} entry",
        content="Memory content.",
        categories=[MemoryCategory.PROCESS],
        confidence=0.8,
        state=state,
        source_agent="test-agent",
        created_at="2026-08-29T00:00:00+00:00",
        updated_at="2026-08-29T00:00:00+00:00",
        approved_at="2026-08-29T00:00:00+00:00" if state != MemoryState.PENDING else None,
    )
    storage.write_entry(path, entry, memory_dir=memory_dir)
    return path


def _save_engine_entry(
    engine: MemoryEngine,
    *,
    title: str,
    scope_agents: list[str],
) -> MemoryEntry:
    return engine.save(
        title=title,
        content="Memory content.",
        categories=[MemoryCategory.PROCESS],
        confidence=0.8,
        source_agent="test-agent",
        scope_agents=scope_agents,
    )


def _save_approved_entry(engine: MemoryEngine, *, title: str, scope_agents: list[str]) -> MemoryEntry:
    pending = _save_engine_entry(engine, title=title, scope_agents=[])
    curated = engine.edit(pending.id, {"scope_agents": scope_agents}, pending.updated_at)
    return engine.approve(curated.id, curated.updated_at)


def _read_head_entry(repository: Path, relative_path: str) -> MemoryEntry:
    raw = _git(repository, "show", f"HEAD:{relative_path}")
    return storage.read_entry_bytes_strict(raw.encode())


def _init_memory_repository(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.name", "OwlBear Test")
    _git(tmp_path, "config", "user.email", "test@example.invalid")
    memory_dir = tmp_path / ".owlbear/memory"
    memory_dir.mkdir(parents=True)
    return memory_dir


def test_review_batch_commit_uses_memory_reviewer_actor(tmp_path: Path) -> None:
    memory_dir = _init_memory_repository(tmp_path)
    _write_entry(memory_dir, state=MemoryState.APPROVED)

    commit_sha = commit_batch(memory_dir, session_type="review")

    assert commit_sha == _git(tmp_path, "rev-parse", "HEAD")
    assert _git(tmp_path, "log", "-1", "--format=%s") == "chore: memory review batch (memory-mcp, memory-reviewer)"


def test_batch_rejects_invalid_entry_before_staging(tmp_path: Path) -> None:
    memory_dir = _init_memory_repository(tmp_path)
    _write_entry(memory_dir, state=MemoryState.APPROVED)
    (memory_dir / "invalid.md").write_text("---\nstate: approved\n---\n\nBroken\n", encoding="utf-8")
    (memory_dir / "unknown-state.md").write_text(
        "---\nstate: reviewed\n---\n\nUnknown state.\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="memory batch validation failed") as raised:
        commit_batch(memory_dir, session_type="curation")

    assert "invalid.md" in str(raised.value)
    assert "unknown-state.md" in str(raised.value)
    assert _git(tmp_path, "diff", "--cached", "--name-only") == ""


def test_batch_rejects_staged_pending_entry(tmp_path: Path) -> None:
    memory_dir = _init_memory_repository(tmp_path)
    pending_path = _write_entry(memory_dir, state=MemoryState.PENDING)
    relative_path = str(pending_path.relative_to(tmp_path))
    _git(tmp_path, "add", "--", relative_path)

    with pytest.raises(ValueError, match="pending entry is staged"):
        commit_batch(memory_dir, session_type="curation")

    assert _git(tmp_path, "diff", "--cached", "--name-only") == relative_path


def test_batch_rejects_pending_index_snapshot_when_worktree_is_approved(tmp_path: Path) -> None:
    memory_dir = _init_memory_repository(tmp_path)
    pending_path = _write_entry(memory_dir, state=MemoryState.PENDING)
    pending = storage.read_entry_strict(pending_path)
    relative_path = str(pending_path.relative_to(tmp_path))
    _git(tmp_path, "add", "--", relative_path)
    storage.write_entry(
        pending_path,
        pending.model_copy(
            update={
                "state": MemoryState.APPROVED,
                "approved_at": "2026-08-29T00:00:00+00:00",
            }
        ),
        memory_dir=memory_dir,
    )

    with pytest.raises(ValueError, match="pending entry is staged"):
        commit_batch(memory_dir, session_type="curation")

    assert _git(tmp_path, "diff", "--cached", "--name-only") == relative_path


def test_batch_leaves_untracked_pending_entry_untouched(tmp_path: Path) -> None:
    memory_dir = _init_memory_repository(tmp_path)
    reviewed_path = _write_entry(memory_dir, state=MemoryState.APPROVED)
    pending_path = _write_entry(memory_dir, state=MemoryState.PENDING)

    commit_batch(memory_dir, session_type="curation")

    reviewed_relative = str(reviewed_path.relative_to(tmp_path))
    pending_relative = str(pending_path.relative_to(tmp_path))
    assert _git(tmp_path, "ls-tree", "-r", "--name-only", "HEAD", "--", ".owlbear/memory") == reviewed_relative
    assert _git(tmp_path, "status", "--porcelain", "--", ".owlbear/memory") == f"?? {pending_relative}"


def test_batch_commits_tracked_pending_deletion(tmp_path: Path) -> None:
    memory_dir = _init_memory_repository(tmp_path)
    pending_path = _write_entry(memory_dir, state=MemoryState.PENDING)
    relative_path = str(pending_path.relative_to(tmp_path))
    _git(tmp_path, "add", "--", relative_path)
    _git(tmp_path, "commit", "-m", "initial memory")
    initial_sha = _git(tmp_path, "rev-parse", "HEAD")
    pending_path.unlink()

    commit_sha = commit_batch(memory_dir, session_type="curation")

    assert commit_sha != initial_sha
    assert _git(tmp_path, "status", "--porcelain", "--", ".owlbear/memory") == ""
    assert _git(tmp_path, "ls-tree", "-r", "--name-only", "HEAD", "--", ".owlbear/memory") == ""


def test_batch_rejects_physical_deletion_of_live_reviewed_entry(tmp_path: Path) -> None:
    memory_dir = _init_memory_repository(tmp_path)
    reviewed_path = _write_entry(memory_dir, state=MemoryState.APPROVED)
    untracked_path = _write_entry(memory_dir, state=MemoryState.APPROVED)
    relative_path = str(reviewed_path.relative_to(tmp_path))
    untracked_relative = str(untracked_path.relative_to(tmp_path))
    _git(tmp_path, "add", "--", relative_path)
    _git(tmp_path, "commit", "-m", "initial memory")
    reviewed_path.unlink()

    with pytest.raises(ValueError, match="physical deletion is only allowed"):
        commit_batch(memory_dir, session_type="curation")

    assert _git(tmp_path, "diff", "--cached", "--name-only") == ""
    status = _git(tmp_path, "status", "--porcelain", "--", ".owlbear/memory")
    assert f"D {relative_path}" in status
    assert f"?? {untracked_relative}" in status


def test_retiring_last_audience_commits_tombstone_then_purge(tmp_path: Path) -> None:
    memory_dir = _init_memory_repository(tmp_path)
    engine = MemoryEngine(memory_dir)
    orphaned = _save_approved_entry(engine, title="Orphaned", scope_agents=["retired"])
    shared = _save_approved_entry(engine, title="Shared", scope_agents=["retired", "builder"])
    pending = _save_engine_entry(engine, title="Pending", scope_agents=["retired"])
    orphaned_path = memory_dir / f"{orphaned.id}.md"
    shared_path = memory_dir / f"{shared.id}.md"
    pending_path = memory_dir / f"{pending.id}.md"
    orphaned_relative = str(orphaned_path.relative_to(tmp_path))
    shared_relative = str(shared_path.relative_to(tmp_path))
    pending_relative = str(pending_path.relative_to(tmp_path))

    initial_sha = commit_batch(memory_dir, session_type="curation")

    assert initial_sha == _git(tmp_path, "rev-parse", "HEAD")
    assert set(_git(tmp_path, "ls-tree", "-r", "--name-only", "HEAD", "--", ".owlbear/memory").splitlines()) == {
        orphaned_relative,
        shared_relative,
    }
    assert pending_path.exists()
    assert pending_relative not in _git(tmp_path, "ls-tree", "-r", "--name-only", "HEAD", "--", ".owlbear/memory")

    (tmp_path / "notes.txt").write_text("Unrelated staged change.\n", encoding="utf-8")
    _git(tmp_path, "add", "--", "notes.txt")

    with patch.object(engine, "_now_iso", return_value="2000-01-01T00:00:00+00:00"):
        result = engine.delete_agent("retired")

    assert result == {"entries_deleted": 2, "scopes_updated": 1}
    assert orphaned_path.exists()
    assert not pending_path.exists()
    orphaned_after_retirement = engine.get_entry(orphaned.id)
    assert orphaned_after_retirement.state == MemoryState.DELETED
    assert orphaned_after_retirement.scope_agents == []
    shared_after_retirement = engine.get_entry(shared.id)
    assert shared_after_retirement.state == MemoryState.APPROVED
    assert shared_after_retirement.scope_agents == ["builder"]
    assert _git(tmp_path, "diff", "--cached", "--name-only") == "notes.txt"

    tombstone_sha = commit_batch(memory_dir, session_type="curation")

    assert tombstone_sha == _git(tmp_path, "rev-parse", "HEAD")
    assert _git(tmp_path, "diff", "--cached", "--name-only") == "notes.txt"
    committed_orphaned = _read_head_entry(tmp_path, orphaned_relative)
    assert committed_orphaned.state == MemoryState.DELETED
    assert committed_orphaned.scope_agents == []
    committed_shared = _read_head_entry(tmp_path, shared_relative)
    assert committed_shared.state == MemoryState.APPROVED
    assert committed_shared.scope_agents == ["builder"]

    purge_result = engine.purge(min_age_days=0)

    assert purge_result.purged == 1
    assert not orphaned_path.exists()
    purge_sha = commit_batch(memory_dir, session_type="curation")

    assert purge_sha == _git(tmp_path, "rev-parse", "HEAD")
    assert _git(tmp_path, "ls-tree", "-r", "--name-only", "HEAD", "--", ".owlbear/memory") == shared_relative
    assert _git(tmp_path, "diff", "--cached", "--name-only") == "notes.txt"


def test_purge_before_tombstone_checkpoint_is_rejected_without_staging(tmp_path: Path) -> None:
    memory_dir = _init_memory_repository(tmp_path)
    engine = MemoryEngine(memory_dir)
    orphaned = _save_approved_entry(engine, title="Orphaned", scope_agents=["retired"])
    shared = _save_approved_entry(engine, title="Shared", scope_agents=["retired", "builder"])
    orphaned_path = memory_dir / f"{orphaned.id}.md"
    orphaned_relative = str(orphaned_path.relative_to(tmp_path))
    shared_relative = str((memory_dir / f"{shared.id}.md").relative_to(tmp_path))
    commit_batch(memory_dir, session_type="curation")

    with patch.object(engine, "_now_iso", return_value="2000-01-01T00:00:00+00:00"):
        engine.delete_agent("retired")
    assert engine.get_entry(shared.id).state == MemoryState.APPROVED
    assert engine.purge(min_age_days=0).purged == 1

    with pytest.raises(ValueError, match="physical deletion is only allowed") as raised:
        commit_batch(memory_dir, session_type="curation")

    message = str(raised.value)
    assert f"physical deletion is only allowed for pending or deleted entries {orphaned_relative}" in message
    assert "HEAD state is approved" in message
    assert f"`git restore --source=HEAD -- {orphaned_relative}`" in message
    assert "soft-delete it, commit the batch, then purge" in message
    assert _git(tmp_path, "diff", "--cached", "--name-only") == ""
    assert shared_relative in _git(tmp_path, "diff", "--name-only", "--", ".owlbear/memory")
    assert _read_head_entry(tmp_path, orphaned_relative).state == MemoryState.APPROVED

    (tmp_path / "notes.txt").write_text("Unrelated staged change.\n", encoding="utf-8")
    _git(tmp_path, "add", "--", "notes.txt")
    with pytest.raises(ValueError, match="physical deletion is only allowed"):
        commit_batch(memory_dir, session_type="curation")

    assert _git(tmp_path, "diff", "--cached", "--name-only") == "notes.txt"
