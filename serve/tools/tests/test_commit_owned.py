"""Tests for scoped Git commit handling."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from owlbear_tools.commit_owned import CommitOwnedError, commit_owned_paths


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=check,
        text=True,
        capture_output=True,
    )


@pytest.fixture()
def git_repo(tmp_path: Path) -> Path:
    """Create a repository with an initial commit."""
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test User")
    (tmp_path / "baseline.txt").write_text("baseline\n", encoding="utf-8")
    (tmp_path / "owned.txt").write_text("baseline owned\n", encoding="utf-8")
    _git(tmp_path, "add", "baseline.txt", "owned.txt")
    _git(tmp_path, "commit", "-m", "initial")
    return tmp_path


def test_commits_owned_path_without_including_unrelated_staged_path(git_repo: Path) -> None:
    """An unrelated staged path stays staged while the owned path is committed."""
    (git_repo / "owned.txt").write_text("owned\n", encoding="utf-8")
    (git_repo / "unrelated.txt").write_text("unrelated\n", encoding="utf-8")
    _git(git_repo, "add", "unrelated.txt")

    commit_owned_paths(cwd=git_repo, message="feat: owned change (#1, builder)", paths=["owned.txt"])

    assert _git(git_repo, "show", "--format=", "--name-only", "HEAD").stdout.splitlines() == ["owned.txt"]
    assert _git(git_repo, "diff", "--cached", "--name-only").stdout.splitlines() == ["unrelated.txt"]


def test_commits_advanced_task_with_all_unrelated_dirt_preserved(git_repo: Path) -> None:
    """An ordinary pipeline commit includes final task state and excludes unrelated dirt."""
    task_path = git_repo / ".owlbear/kanban/tasks/1-task.md"
    task_path.parent.mkdir(parents=True)
    task_path.write_text("status: build\n", encoding="utf-8")
    _git(git_repo, "add", task_path.relative_to(git_repo).as_posix())
    _git(git_repo, "commit", "-m", "add task")

    (git_repo / "owned.txt").write_text("implemented\n", encoding="utf-8")
    task_path.write_text("status: verify\n", encoding="utf-8")
    (git_repo / "baseline.txt").write_text("unrelated tracked\n", encoding="utf-8")
    (git_repo / "unrelated-staged.txt").write_text("staged\n", encoding="utf-8")
    (git_repo / "unrelated-untracked.txt").write_text("untracked\n", encoding="utf-8")
    _git(git_repo, "add", "unrelated-staged.txt")

    commit_owned_paths(
        cwd=git_repo,
        message="feat: advance task (#1, builder)",
        paths=["owned.txt", task_path.relative_to(git_repo).as_posix()],
    )

    assert _git(git_repo, "show", "--format=", "--name-only", "HEAD").stdout.splitlines() == [
        ".owlbear/kanban/tasks/1-task.md",
        "owned.txt",
    ]
    assert _git(git_repo, "diff", "--name-only").stdout.splitlines() == ["baseline.txt"]
    assert _git(git_repo, "diff", "--cached", "--name-only").stdout.splitlines() == ["unrelated-staged.txt"]
    assert (git_repo / "unrelated-untracked.txt").exists()


def test_commits_archive_move_without_including_unrelated_dirt(git_repo: Path) -> None:
    """A collector can commit both sides of an archive move in a dirty worktree."""
    task_path = git_repo / ".owlbear/kanban/tasks/1-task.md"
    archive_path = git_repo / ".owlbear/kanban/archive/1-task.md"
    task_path.parent.mkdir(parents=True)
    archive_path.parent.mkdir(parents=True)
    task_path.write_text("status: collect\n", encoding="utf-8")
    _git(git_repo, "add", task_path.relative_to(git_repo).as_posix())
    _git(git_repo, "commit", "-m", "add task")

    task_path.rename(archive_path)
    (git_repo / "unrelated-staged.txt").write_text("staged\n", encoding="utf-8")
    (git_repo / "unrelated-untracked.txt").write_text("untracked\n", encoding="utf-8")
    _git(git_repo, "add", "unrelated-staged.txt")

    commit_owned_paths(
        cwd=git_repo,
        message="chore: archive task (#1, collector)",
        paths=[
            task_path.relative_to(git_repo).as_posix(),
            archive_path.relative_to(git_repo).as_posix(),
        ],
    )

    committed = _git(git_repo, "diff-tree", "--no-commit-id", "--name-status", "-r", "-M", "HEAD").stdout
    assert committed.splitlines() == ["R100\t.owlbear/kanban/tasks/1-task.md\t.owlbear/kanban/archive/1-task.md"]
    assert _git(git_repo, "diff", "--cached", "--name-only").stdout.splitlines() == ["unrelated-staged.txt"]
    assert (git_repo / "unrelated-untracked.txt").exists()


def test_rejects_owned_path_that_was_already_staged(git_repo: Path) -> None:
    """The helper cannot establish ownership of pre-staged changes in one path."""
    (git_repo / "owned.txt").write_text("owned\n", encoding="utf-8")
    _git(git_repo, "add", "owned.txt")

    with pytest.raises(CommitOwnedError, match="already have staged changes"):
        commit_owned_paths(cwd=git_repo, message="feat: owned change (#1, builder)", paths=["owned.txt"])

    assert _git(git_repo, "diff", "--cached", "--name-only").stdout.splitlines() == ["owned.txt"]


def test_unstages_owned_paths_after_commit_failure(git_repo: Path) -> None:
    """A failing commit keeps the worktree edit while restoring the index."""
    (git_repo / "owned.txt").write_text("owned\n", encoding="utf-8")
    hooks = git_repo / ".git" / "hooks"
    hook = hooks / "pre-commit"
    hook.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    hook.chmod(0o755)

    with pytest.raises(CommitOwnedError, match="were unstaged"):
        commit_owned_paths(cwd=git_repo, message="feat: owned change (#1, builder)", paths=["owned.txt"])

    assert _git(git_repo, "diff", "--cached", "--name-only").stdout == ""
    assert _git(git_repo, "diff", "--name-only").stdout.splitlines() == ["owned.txt"]
