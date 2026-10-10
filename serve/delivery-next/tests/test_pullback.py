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


def test_without_a_local_target_branch_only_the_remote_ref_is_updated(repos):
    repo, other = repos
    git(repo, "switch", "-q", "-c", "work")
    git(repo, "branch", "-q", "-D", "main")
    head = merged(other)
    result = pullback.run(repo, "main", NOW)
    assert (result.state, result.reason) == ("updated", "no local main branch; origin/main updated")
    assert git(repo, "rev-parse", "origin/main") == head


def state(repo):
    status = git(repo, "status", "--porcelain=v1", "--untracked-files=all")
    return git(repo, "rev-parse", "HEAD"), git(repo, "rev-parse", "refs/heads/main"), status


def test_unrelated_local_changes_survive_a_fast_forward(repos):
    repo, other = repos
    (repo / ".gitignore").write_text("edited\n")
    (repo / "new.txt").write_text("untracked\n")
    head = merged(other)
    result = pullback.run(repo, "main", NOW)
    assert (result.state, git(repo, "rev-parse", "HEAD"), (repo / "b.txt").exists()) == ("updated", head, True)
    assert ((repo / ".gitignore").read_text(), (repo / "new.txt").read_text()) == ("edited\n", "untracked\n")
    assert git(repo, "stash", "list") == ""


@pytest.mark.parametrize("staged", [False, True])
def test_local_changes_to_an_incoming_path_leave_the_target_behind_and_untouched(repos, staged):
    repo, other = repos
    (repo / "b.txt").write_text("mine\n")
    if staged:
        git(repo, "add", "b.txt")
    before = state(repo)
    merged(other)
    result = pullback.run(repo, "main", NOW)
    assert (result.state, result.reason) == (
        "behind",
        "local main is behind: your local changes to b.txt overlap the merged change",
    )
    assert (state(repo), (repo / "b.txt").read_text()) == (before, "mine\n")


def test_local_commits_are_rebased_and_unrelated_local_changes_kept(repos):
    repo, other = repos
    commit(repo, "local.txt")
    (repo / ".gitignore").write_text("edited\n")
    (repo / "new.txt").write_text("untracked\n")
    head = merged(other)
    result = pullback.run(repo, "main", NOW)
    assert (result.state, result.reason) == ("updated", "rebased 1 local commits")
    assert (git(repo, "rev-parse", "HEAD~1"), git(repo, "log", "-1", "--format=%s")) == (head, "local.txt")
    assert ((repo / ".gitignore").read_text(), (repo / "new.txt").read_text()) == ("edited\n", "untracked\n")
    assert (git(repo, "stash", "list"), git(repo, "status", "--porcelain")) == ("", "M .gitignore\n?? new.txt")


def test_a_conflicting_rebase_is_aborted_and_everything_is_as_before(repos):
    repo, other = repos
    commit(repo, "b.txt", "local commit\n")
    (repo / ".gitignore").write_text("edited\n")
    before = state(repo)
    merged(other)
    result = pullback.run(repo, "main", NOW)
    assert (result.state, result.reason.startswith("local main is behind: rebase undone: ")) == ("behind", True)
    assert (state(repo), (repo / ".gitignore").read_text()) == (before, "edited\n")
    assert git(repo, "stash", "list") == ""


def test_an_untracked_file_at_an_incoming_path_leaves_the_target_behind(repos):
    repo, other = repos
    (repo / "b.txt").write_text("untracked\n")
    before = state(repo)
    merged(other)
    result = pullback.run(repo, "main", NOW)
    assert (result.state, "b.txt overlap" in result.reason) == ("behind", True)
    assert (state(repo), (repo / "b.txt").read_text()) == (before, "untracked\n")


@pytest.mark.parametrize("op", ["rebase", "bisect"])
def test_a_target_mid_rebase_or_bisect_is_behind(repos, op):
    repo, other = repos
    if op == "rebase":
        git(repo, "switch", "-q", "-c", "side", "HEAD")
        commit(repo, "c.txt", "side\n")
        git(repo, "switch", "-q", "main")
        commit(repo, "c.txt", "main\n")
        subprocess.run(["git", "rebase", "side"], cwd=repo, capture_output=True, check=False)  # noqa: S607
    else:
        git(repo, "bisect", "start")
    detached = git(repo, "rev-parse", "HEAD")
    merged(other)
    result = pullback.run(repo, "main", NOW)
    assert (result.state, result.reason, result.worktree) == ("behind", "local main is behind: in progress", str(repo))
    assert git(repo, "rev-parse", "HEAD") == detached


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
