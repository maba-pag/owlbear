"""Publication distinguishes failed probes from missing paths and unpublished work (FND-05)."""

import subprocess
from pathlib import Path

import pytest

from owlbear_delivery_next.local_system import data_repo
from owlbear_delivery_next.local_system.data_repo import DataRepo


def git(cwd: Path, *args: str) -> str:
    if (cwd / "HEAD").is_file():  # a bare repository: safe.bareRepository=explicit wants it named
        args = ("--git-dir=.", *args)
    who = ["-c", "user.name=t", "-c", "user.email=t@example.com"]
    return subprocess.run(["git", *who, *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()  # noqa: S603, S607


@pytest.fixture
def shared(shared_repo) -> tuple[DataRepo, Path]:
    root, remote = shared_repo
    return DataRepo(root), remote


def publish(repo: DataRepo, path: Path, message: str) -> str:
    with repo.locked():
        return repo.publish(path, message)


def tracked(repo: DataRepo) -> Path:
    path = repo.root / "config.json"
    path.write_text('{"v": 1}\n')
    assert publish(repo, path, "settings: save") == ""
    return path


def test_a_healthy_tracked_deletion_is_committed_and_pushed(shared) -> None:
    repo, remote = shared
    path = tracked(repo)
    assert git(remote, "show", "main:config.json") == '{"v": 1}'
    assert git(remote, "rev-parse", "main") == git(repo.root, "rev-parse", "HEAD")
    assert repo.pending() == ""
    (repo.root / "owner.txt").write_text("owner's staged work\n")
    git(repo.root, "add", "--", "owner.txt")
    staged = git(repo.root, "diff", "--cached", "--binary")
    git(repo.root, "commit", "-q", "--allow-empty", "--only", "-m", "earlier unchanged save")
    assert "1 commit(s)" in repo.pending()
    assert publish(repo, path, "settings: save") == ""
    assert git(remote, "rev-parse", "main") == git(repo.root, "rev-parse", "HEAD")
    assert git(repo.root, "diff", "--cached", "--binary") == staged
    path.unlink()
    assert publish(repo, path, "settings: delete") == ""
    assert git(remote, "rev-parse", "main") == git(repo.root, "rev-parse", "HEAD")
    assert git(repo.root, "ls-files", "--", "config.json") == ""
    assert git(repo.root, "diff", "--cached", "--binary") == staged
    assert git(repo.root, "ls-tree", "HEAD", "--", "owner.txt") == ""
    git(repo.root, "commit", "-q", "--allow-empty", "--only", "-m", "earlier missing-path save")
    assert publish(repo, repo.root / "ghost.json", "settings: save") == ""
    assert git(remote, "rev-parse", "main") == git(repo.root, "rev-parse", "HEAD")
    assert git(repo.root, "diff", "--cached", "--binary") == staged
    assert repo.pending() == f"unpublished in {repo.root}: 1 file(s) not committed; the next save retries"


@pytest.mark.parametrize("failure", ["corrupt-index", "timeout", "oserror"])
def test_a_local_tracking_failure_cannot_report_a_deletion_published(shared, monkeypatch, failure) -> None:
    repo, remote = shared
    path = tracked(repo)
    published = git(remote, "rev-parse", "main")
    path.unlink()
    (repo.root / "owner.txt").write_text("owner's staged work\n")
    git(repo.root, "add", "--", "owner.txt")
    staged = git(repo.root, "diff", "--cached", "--binary")
    if failure == "corrupt-index":
        (repo.root / ".git" / "index").write_bytes(b"synthetic broken index")
    run = subprocess.run

    def fail_tracking(args, **kwargs):
        if "ls-files" in args and failure != "corrupt-index":
            if failure == "timeout":
                raise subprocess.TimeoutExpired(args, 10)
            msg = "synthetic execution failure"
            raise OSError(msg)
        return run(args, **kwargs)

    monkeypatch.setattr(data_repo.subprocess, "run", fail_tracking)
    assert publish(repo, path, "settings: delete")
    assert git(remote, "rev-parse", "main") == published
    assert git(repo.root, "show", "HEAD:config.json") == '{"v": 1}'
    if failure != "corrupt-index":
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


@pytest.mark.parametrize("name", [" ", "\n"])
def test_tracking_preserves_whitespace_in_deleted_paths(shared, name) -> None:
    repo, remote = shared
    path = repo.root / name
    path.write_text("tracked data\n")
    assert publish(repo, path, "save whitespace path") == ""
    before = git(repo.root, "rev-parse", "HEAD")
    assert git(repo.root, "ls-tree", "-z", "--name-only", "HEAD", "--", name)
    path.unlink()
    assert publish(repo, path, "delete whitespace path") == ""
    assert git(repo.root, "ls-tree", "-z", "--name-only", "HEAD", "--", name) == ""
    assert git(repo.root, "rev-parse", "HEAD") != before
    assert git(remote, "rev-parse", "main") == git(repo.root, "rev-parse", "HEAD")


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
