import subprocess
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from owlbear_delivery_next import api
from owlbear_delivery_next.host import Host
from owlbear_delivery_next.models import Change, Names, Step, StepKind
from owlbear_delivery_next.status import Activity
from owlbear_delivery_next.steps import pullback
from owlbear_delivery_next.store import Lock, Store

NOW = datetime(2026, 10, 10, 12, tzinfo=UTC)


def git(cwd, *args):
    done = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)  # noqa: S603, S607
    return done.stdout.strip()


def commit(cwd, name, text="x\n"):
    (cwd / name).write_text(text)
    git(cwd, "add", name)
    git(cwd, "commit", "-q", "-m", name)


@pytest.fixture(autouse=True)
def git_env(tmp_path, monkeypatch):
    (tmp_path / "gitconfig").write_text("")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(tmp_path / "gitconfig"))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    for who in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{who}_NAME", "t")
        monkeypatch.setenv(f"GIT_{who}_EMAIL", "t@t")


@pytest.fixture
def repos(tmp_path):
    """A clone with ``main`` checked out, and another clone that merges into the same origin."""
    origin, repo, other = tmp_path / "origin.git", tmp_path / "repo", tmp_path / "other"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    git(tmp_path, "clone", "-q", str(origin), str(repo))
    commit(repo, ".gitignore", "*.log\n")
    git(repo, "push", "-q", "origin", "HEAD:refs/heads/main")
    git(tmp_path, "clone", "-q", str(origin), str(other))
    return repo, other


def merged(other, name="b.txt"):
    commit(other, name)
    git(other, "push", "-q", "origin", "main")
    return git(other, "rev-parse", "HEAD")


def test_a_clean_checked_out_target_is_fast_forwarded(repos):
    repo, other = repos
    head = merged(other)
    result = pullback.run(repo, "main", NOW)
    assert (result.state, result.worktree, git(repo, "rev-parse", "HEAD")) == ("updated", str(repo), head)
    assert pullback.run(repo, "main", NOW).reason == "already up to date"


def test_a_target_not_checked_out_has_only_its_ref_fast_forwarded(repos):
    repo, other = repos
    git(repo, "switch", "-q", "-c", "work")
    (repo / "w.txt").write_text("mine\n")
    head = merged(other)
    result = pullback.run(repo, "main", NOW)
    assert (result.state, result.worktree, git(repo, "rev-parse", "main")) == ("updated", "", head)
    assert (git(repo, "branch", "--show-current"), (repo / "w.txt").read_text()) == ("work", "mine\n")


def test_a_dirty_target_is_behind_and_untouched_even_with_autostash(repos):
    repo, other = repos
    git(repo, "config", "merge.autostash", "true")
    before = git(repo, "rev-parse", "HEAD")
    (repo / ".gitignore").write_text("edited\n")
    merged(other)
    result = pullback.run(repo, "main", NOW)
    assert (result.state, result.reason) == ("behind", "local main is behind: dirty")
    assert (git(repo, "rev-parse", "HEAD"), (repo / ".gitignore").read_text()) == (before, "edited\n")
    assert git(repo, "stash", "list") == ""


def test_a_diverged_target_is_behind(repos):
    repo, other = repos
    commit(repo, "local.txt")
    mine = git(repo, "rev-parse", "HEAD")
    merged(other)
    result = pullback.run(repo, "main", NOW)
    assert (result.state, result.reason, git(repo, "rev-parse", "HEAD")) == (
        "behind",
        "local main is behind: diverged",
        mine,
    )


def test_an_ignored_file_the_merge_would_overwrite_is_kept_and_the_target_is_behind(repos):
    repo, other = repos
    before = git(repo, "rev-parse", "HEAD")
    (repo / "keep.log").write_text("local log\n")
    commit(other, "placeholder")
    (other / "keep.log").write_text("remote\n")
    git(other, "add", "-f", "keep.log")
    git(other, "commit", "-q", "-m", "log")
    git(other, "push", "-q", "origin", "main")
    result = pullback.run(repo, "main", NOW)
    assert (result.state, result.reason.startswith("local main is behind: ")) == ("behind", True)
    assert ((repo / "keep.log").read_text(), git(repo, "rev-parse", "HEAD")) == ("local log\n", before)


def test_a_gitlink_change_is_reported(repos):
    repo, other = repos
    sha = git(other, "rev-parse", "HEAD")
    git(other, "update-index", "--add", "--cacheinfo", f"160000,{sha},sub")
    git(other, "commit", "-q", "-m", "submodule")
    git(other, "push", "-q", "origin", "main")
    result = pullback.run(repo, "main", NOW)
    assert "submodules changed" in result.reason


def test_the_pull_action_is_queued_by_the_api_and_rerun_by_the_host(repos):
    repo, other = repos
    store = Store.open(repo)
    c = Change(slug="c1", step=Step(kind=StepKind.CLEANUP), names=Names(target="main"))
    store.write(Lock("c1"), c)

    class Fake:
        wake = type("W", (), {"set": lambda _self: None})()
        record = None

        def activity(self, _slug):
            return Activity(host_up=True)

    client = TestClient(
        api.create_app(store, "t", Fake()), base_url="http://127.0.0.1", headers={"authorization": "Bearer t"}
    )
    assert client.post("/api/next/changes/c1/pull", json={}).status_code == 200
    head = merged(other)
    h = Host(store, repo, spawn=None)
    with store.lock("c1") as lock:
        c, _ = store.fold(lock, "c1", NOW)
        assert c.pull_requested is not None
        c = h._pull(lock, c, NOW)  # noqa: SLF001 - the host's pull-back seam
    assert (c.pullback.state, c.pull_requested, git(repo, "rev-parse", "HEAD")) == ("updated", None, head)
    assert store.events("c1")[-1]["event"] == "pullback"
    assert h._pull(Lock("c1"), c, NOW) is c  # noqa: SLF001 - no request: nothing runs
