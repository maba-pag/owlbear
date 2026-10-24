"""Publication distinguishes failed probes from missing paths and unpublished work (FND-05)."""

import subprocess
from pathlib import Path

import pytest

from owlbear_delivery_next.local_system import data_repo
from owlbear_delivery_next.local_system.data_repo import DataRepo


def git(cwd: Path, *args: str) -> str:
    who = ["-c", "user.name=t", "-c", "user.email=t@example.com"]
    return subprocess.run(["git", *who, *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()  # noqa: S603, S607


@pytest.fixture
def shared(tmp_path: Path) -> tuple[DataRepo, Path]:
    remote, root = tmp_path / "remote.git", tmp_path / "owlbear-data"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(remote))
    git(tmp_path, "clone", "-q", str(remote), str(root))
    for key, value in (("user.name", "t"), ("user.email", "t@example.com")):
        git(root, "config", key, value)
    git(root, "commit", "-q", "--allow-empty", "-m", "start")
    git(root, "push", "-q", "origin", "HEAD")
    return DataRepo(root), remote


def publish(repo: DataRepo, path: Path, message: str) -> str:
    with repo.locked():
        return repo.publish(path, message)


def tracked(repo: DataRepo) -> Path:
    path = repo.root / "config.json"
    path.write_text('{"v": 1}\n')
    assert publish(repo, path, "settings: save") == ""
    return path


def test_a_healthy_save_commits_and_pushes_an_existing_path(shared) -> None:
    repo, remote = shared
    tracked(repo)
    assert git(remote, "rev-parse", "main") == git(repo.root, "rev-parse", "HEAD")
    assert repo.pending() == ""


def test_a_healthy_tracked_deletion_is_committed_and_pushed(shared) -> None:
    repo, remote = shared
    path = tracked(repo)
    (repo.root / "owner.txt").write_text("owner's staged work\n")
    git(repo.root, "add", "--", "owner.txt")
    staged = git(repo.root, "diff", "--cached", "--binary")
    path.unlink()
    assert publish(repo, path, "settings: delete") == ""
    assert git(remote, "rev-parse", "main") == git(repo.root, "rev-parse", "HEAD")
    assert git(repo.root, "ls-files", "--", "config.json") == ""
    assert git(repo.root, "diff", "--cached", "--binary") == staged
    assert git(repo.root, "ls-tree", "HEAD", "--", "owner.txt") == ""


def test_a_corrupt_index_cannot_report_a_tracked_deletion_published(shared) -> None:
    repo, remote = shared
    path = tracked(repo)
    published = git(remote, "rev-parse", "main")
    path.unlink()
    (repo.root / ".git" / "index").write_bytes(b"synthetic broken index")

    assert publish(repo, path, "settings: delete")
    assert git(remote, "rev-parse", "main") == published
    assert git(repo.root, "show", "HEAD:config.json") == '{"v": 1}'


@pytest.mark.parametrize("failure", ["timeout", "oserror"])
def test_a_local_tracking_failure_cannot_report_a_deletion_published(shared, monkeypatch, failure) -> None:
    repo, remote = shared
    path = tracked(repo)
    published = git(remote, "rev-parse", "main")
    path.unlink()
    (repo.root / "owner.txt").write_text("owner's staged work\n")
    git(repo.root, "add", "--", "owner.txt")
    staged = git(repo.root, "diff", "--cached", "--binary")
    run = subprocess.run

    def fail_tracking(args, **kwargs):
        if "ls-files" in args:
            if failure == "timeout":
                raise subprocess.TimeoutExpired(args, 10)
            msg = "synthetic execution failure"
            raise OSError(msg)
        return run(args, **kwargs)

    monkeypatch.setattr(data_repo.subprocess, "run", fail_tracking)
    assert publish(repo, path, "settings: delete")
    assert git(remote, "rev-parse", "main") == published
    assert git(repo.root, "diff", "--cached", "--binary") == staged


def test_a_failed_staged_diff_does_not_commit_or_push(shared, monkeypatch) -> None:
    repo, remote = shared
    path = tracked(repo)
    published = git(remote, "rev-parse", "main")
    path.write_text('{"v": 2}\n')
    real = subprocess.run

    def fail_diff(args, **kwargs):
        if "diff" in args and "--cached" in args and "--quiet" in args:
            return subprocess.CompletedProcess(args, 128, "", "fatal: synthetic diff failure")
        return real(args, **kwargs)

    monkeypatch.setattr(data_repo.subprocess, "run", fail_diff)
    assert publish(repo, path, "settings: save")
    assert git(repo.root, "rev-parse", "HEAD") == published
    assert git(remote, "rev-parse", "main") == published


def test_a_missing_untracked_path_still_retries_earlier_unpushed_commits(shared) -> None:
    repo, remote = shared
    git(repo.root, "commit", "-q", "--allow-empty", "-m", "earlier")
    assert publish(repo, repo.root / "ghost.json", "settings: save") == ""
    assert git(remote, "rev-parse", "main") == git(repo.root, "rev-parse", "HEAD")


@pytest.mark.parametrize("name", [" ", "\n"])
def test_tracking_preserves_whitespace_in_deleted_paths(shared, name) -> None:
    repo, remote = shared
    path = repo.root / name
    path.write_text("tracked data\n")
    assert publish(repo, path, "save whitespace path") == ""
    path.unlink()
    assert publish(repo, path, "delete whitespace path") == ""
    assert git(repo.root, "ls-tree", "--name-only", "HEAD", "--", name) == ""
    assert git(remote, "rev-parse", "main") == git(repo.root, "rev-parse", "HEAD")


def test_an_unchanged_save_preserves_unrelated_staging_and_retries_publication(shared) -> None:
    repo, remote = shared
    path = tracked(repo)
    other = repo.root / "owner.txt"
    other.write_text("owner's staged work\n")
    git(repo.root, "add", "--", other.name)
    staged = git(repo.root, "diff", "--cached", "--binary")
    git(repo.root, "commit", "-q", "--allow-empty", "--only", "-m", "earlier")
    assert publish(repo, path, "settings: save") == ""
    assert git(repo.root, "diff", "--cached", "--binary") == staged
    assert git(remote, "rev-parse", "main") == git(repo.root, "rev-parse", "HEAD")
    assert git(repo.root, "ls-tree", "HEAD", "--", other.name) == ""


def test_pending_counts_the_commits_no_remote_has(shared) -> None:
    repo, _ = shared
    assert repo.pending() == ""
    git(repo.root, "commit", "-q", "--allow-empty", "-m", "earlier")
    assert "1 commit(s)" in repo.pending()


@pytest.mark.parametrize(("code", "output"), [(128, ""), (0, "not-a-count"), (0, "\u00b2")])
def test_a_failed_or_malformed_unpushed_count_is_not_read_as_zero(shared, monkeypatch, code, output) -> None:
    repo, _ = shared
    real = subprocess.run

    def fail_count(args, **kwargs):
        if "rev-list" in args:
            return subprocess.CompletedProcess(args, code, output, "synthetic count failure")
        return real(args, **kwargs)

    monkeypatch.setattr(data_repo.subprocess, "run", fail_count)
    assert repo.pending()


def test_an_unborn_checkout_reports_files_without_inventing_unpushed_commits(tmp_path: Path) -> None:
    root = tmp_path / "fresh"
    git(tmp_path, "init", "-q", "-b", "main", str(root))
    assert DataRepo(root).git("rev-parse", "--verify", "--quiet", "HEAD").returncode == 1
    (root / "config.json").write_text("{}\n")
    notice = DataRepo(root).pending()
    assert "1 file(s)" in notice
    assert "cannot be read" not in notice
