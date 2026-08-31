"""Memory batch commit attribution contracts."""

from __future__ import annotations

import subprocess
from pathlib import Path
from uuid import uuid4

import pytest
from owlbear_memory import MemoryCategory, MemoryEntry, MemoryState, storage

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
    relative_path = str(reviewed_path.relative_to(tmp_path))
    _git(tmp_path, "add", "--", relative_path)
    _git(tmp_path, "commit", "-m", "initial memory")
    reviewed_path.unlink()

    with pytest.raises(ValueError, match="physical deletion is only allowed"):
        commit_batch(memory_dir, session_type="curation")

    assert _git(tmp_path, "status", "--porcelain", "--", ".owlbear/memory") == f"D {relative_path}"
