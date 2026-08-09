"""Memory batch commit attribution contracts."""

from __future__ import annotations

from pathlib import Path
import subprocess

from owlbear_memory_mcp.git import commit_batch


def _git(repository: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def test_review_batch_commit_uses_memory_reviewer_actor(tmp_path: Path) -> None:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.name", "OwlBear Test")
    _git(tmp_path, "config", "user.email", "test@example.invalid")
    memory_dir = tmp_path / ".owlbear/memory"
    memory_dir.mkdir(parents=True)
    (memory_dir / "reviewed.md").write_text("---\nstate: approved\n---\n\n# Reviewed\n", encoding="utf-8")

    commit_sha = commit_batch(memory_dir, session_type="review")

    assert commit_sha == _git(tmp_path, "rev-parse", "HEAD")
    assert _git(tmp_path, "log", "-1", "--format=%s") == "chore: memory review batch (memory-mcp, memory-reviewer)"
