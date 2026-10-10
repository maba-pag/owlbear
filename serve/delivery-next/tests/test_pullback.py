import subprocess
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from owlbear_delivery_next import api
from owlbear_delivery_next.git.remote_git import RemoteGitTimeout
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


def worktrees(repo):
    return [line for line in git(repo, "worktree", "list", "--porcelain").splitlines() if line.startswith("worktree")]


def full(repo):
    """HEAD, branch, status, index and every non-ignored working file."""
    files = {p: (repo / p).read_bytes() for p in git(repo, "ls-files", "-co", "--exclude-standard").splitlines()}
    return (*state(repo), git(repo, "ls-files", "-s"), files)


def test_local_commits_are_replayed_and_unrelated_local_changes_kept(repos):
    repo, other = repos
    (repo / "local.txt").write_text("x\n")
    git(repo, "add", "local.txt")
    git(repo, "commit", "-q", "-m", "my message", "--author", "Ann <ann@a>")
    (repo / ".gitignore").write_text("edited\n")
    (repo / "new.txt").write_text("untracked\n")
    head, wts = merged(other), worktrees(repo)
    result = pullback.run(repo, "main", NOW)
    assert (result.state, result.reason) == ("updated", "replayed 1 local commits onto the merged change")
    assert git(repo, "rev-parse", "HEAD~1") == head
    assert git(repo, "log", "-1", "--format=%s|%an <%ae>") == "my message|Ann <ann@a>"
    assert ((repo / ".gitignore").read_text(), (repo / "new.txt").read_text()) == ("edited\n", "untracked\n")
    assert (git(repo, "stash", "list"), git(repo, "status", "--porcelain")) == ("", "M .gitignore\n?? new.txt")
    assert worktrees(repo) == wts


@pytest.mark.parametrize(
    ("diverged", "reason"), [(False, "fast-forwarded"), (True, "replayed 1 local commits onto the merged change")]
)
def test_a_partially_staged_file_keeps_its_index_entry_and_content(repos, diverged, reason):
    repo, other = repos
    commit(repo, "part.txt", "head\n")
    git(repo, "push", "-q", "origin", "main")
    git(other, "pull", "-q")
    if diverged:
        commit(repo, "local.txt")
    (repo / "part.txt").write_text("staged\n")
    git(repo, "add", "part.txt")
    (repo / "part.txt").write_text("working\n")
    entry, cached = git(repo, "ls-files", "-s", "part.txt"), git(repo, "diff", "--cached")
    merged(other)
    result = pullback.run(repo, "main", NOW)
    assert (result.state, result.reason) == ("updated", reason)
    assert (git(repo, "ls-files", "-s", "part.txt"), git(repo, "diff", "--cached")) == (entry, cached)
    assert (repo / "part.txt").read_text() == "working\n"


def test_a_conflicting_replay_leaves_the_local_copy_and_worktrees_as_before(repos):
    repo, other = repos
    commit(repo, "b.txt", "local commit\n")
    (repo / ".gitignore").write_text("edited\n")
    before, wts = full(repo), worktrees(repo)
    merged(other)
    result = pullback.run(repo, "main", NOW)
    assert (result.state, result.reason) == (
        "behind",
        "local main is behind: your local commits conflict with the merged change",
    )
    assert (full(repo), worktrees(repo), git(repo, "stash", "list")) == (before, wts, "")


def test_a_failing_signature_leaves_the_local_copy_untouched(repos):
    repo, other = repos
    commit(repo, "local.txt")
    git(repo, "config", "commit.gpgSign", "true")
    git(repo, "config", "gpg.program", "false")
    before, wts = full(repo), worktrees(repo)
    merged(other)
    result = pullback.run(repo, "main", NOW)
    assert result.state == "behind"
    assert (full(repo), worktrees(repo)) == (before, wts)


def test_a_local_merge_commit_leaves_the_target_behind(repos):
    repo, other = repos
    git(repo, "switch", "-q", "-c", "side")
    commit(repo, "side.txt")
    git(repo, "switch", "-q", "main")
    commit(repo, "local.txt")
    git(repo, "merge", "-q", "--no-ff", "-m", "merge side", "side")
    before = full(repo)
    merged(other)
    result = pullback.run(repo, "main", NOW)
    assert (result.state, result.reason) == ("behind", "local main is behind: local merge commits; pull manually")
    assert full(repo) == before


def test_a_dirty_rename_target_refused_by_reset_keep_is_untouched(repos):
    repo, other = repos
    commit(repo, "a.txt", "one\ntwo\nthree\nfour\n")
    git(repo, "push", "-q", "origin", "main")
    git(other, "pull", "-q")
    git(repo, "mv", "a.txt", "b.txt")
    git(repo, "commit", "-q", "-m", "rename")
    (repo / "b.txt").write_text("one\ntwo\nthree\nfour\nmine\n")
    before = full(repo)
    commit(other, "a.txt", "ONE\ntwo\nthree\nfour\n")
    git(other, "push", "-q", "origin", "main")
    result = pullback.run(repo, "main", NOW)
    assert result.state == "behind"
    assert full(repo) == before
    assert "<<<<<<<" not in (repo / "b.txt").read_text()


def test_a_staged_rename_whose_source_the_merge_edits_is_a_collision(repos):
    repo, other = repos
    commit(repo, "a.txt", "one\n")
    git(repo, "push", "-q", "origin", "main")
    git(other, "pull", "-q")
    git(repo, "mv", "a.txt", "b.txt")
    (repo / "b.txt").write_text("mine\n")
    before = full(repo)
    commit(other, "a.txt", "ONE\n")
    git(other, "push", "-q", "origin", "main")
    result = pullback.run(repo, "main", NOW)
    assert (result.state, "a.txt overlap" in result.reason) == ("behind", True)
    assert full(repo) == before


def test_two_worktrees_holding_the_target_leave_it_behind(repos, tmp_path):
    repo, other = repos
    git(repo, "worktree", "add", "-q", "--force", str(tmp_path / "second"), "main")
    before = full(repo)
    merged(other)
    result = pullback.run(repo, "main", NOW)
    assert (result.state, result.reason) == ("behind", "local main is behind: main is checked out in 2 worktrees")
    assert full(repo) == before


def test_a_case_only_untracked_collision_counts_when_git_ignores_case(repos):
    repo, other = repos
    git(repo, "config", "core.ignorecase", "true")
    (repo / "B.TXT").write_text("mine\n")
    before = full(repo)
    merged(other)
    result = pullback.run(repo, "main", NOW)
    assert result.state == "behind"
    assert (full(repo), (repo / "B.TXT").read_text()) == (before, "mine\n")


def test_an_untracked_file_where_the_merge_needs_a_directory_is_a_collision(repos):
    repo, other = repos
    (repo / "d").write_text("mine\n")
    before = full(repo)
    (other / "d").mkdir()
    commit(other, "d/f.txt")
    git(other, "push", "-q", "origin", "main")
    result = pullback.run(repo, "main", NOW)
    assert (result.state, "d/f.txt overlap" in result.reason) == ("behind", True)
    assert full(repo) == before


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


@pytest.mark.parametrize("diverged", [False, True])
def test_an_ignored_file_the_merge_would_overwrite_is_kept_and_the_target_is_behind(repos, diverged):
    repo, other = repos
    if diverged:
        commit(repo, "local.txt")
    before = git(repo, "rev-parse", "HEAD")
    (repo / "keep.log").write_text("local log\n")
    commit(other, "placeholder")
    (other / "keep.log").write_text("remote\n")
    git(other, "add", "-f", "keep.log")
    git(other, "commit", "-q", "-m", "log")
    git(other, "push", "-q", "origin", "main")
    result = pullback.run(repo, "main", NOW)
    assert (result.state, "keep.log overlap" in result.reason) == ("behind", True)
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


def test_a_path_the_replay_moves_into_an_ignored_file_is_a_collision(repos):
    repo, other = repos
    (repo / "old").mkdir()
    commit(repo, "old/a.txt", "one\ntwo\nthree\n")
    git(repo, "push", "-q", "origin", "main")
    git(other, "pull", "-q")
    (repo / "old" / "local.log").write_text("committed\n")
    git(repo, "add", "-f", "old/local.log")
    git(repo, "commit", "-q", "-m", "local log")
    git(repo, "config", "merge.directoryRenames", "true")
    git(other, "mv", "old", "new")
    git(other, "commit", "-q", "-m", "rename")
    git(other, "push", "-q", "origin", "main")
    (repo / "new").mkdir()
    (repo / "new" / "local.log").write_text("mine\n")
    head = git(repo, "rev-parse", "HEAD")
    result = pullback.run(repo, "main", NOW)
    assert (result.state, "new/local.log overlap" in result.reason) == ("behind", True)
    assert ((repo / "new" / "local.log").read_text(), git(repo, "rev-parse", "HEAD")) == ("mine\n", head)


def test_a_branch_switch_before_the_update_leaves_both_branches_alone(repos, monkeypatch):
    repo, other = repos
    head, guard = git(repo, "rev-parse", "HEAD"), pullback._guard  # noqa: SLF001 - the step before mutation

    def switch(wt, paths, *, fold):
        git(repo, "switch", "-q", "-c", "other")
        return guard(wt, paths, fold=fold)

    monkeypatch.setattr(pullback, "_guard", switch)
    merged(other)
    result = pullback.run(repo, "main", NOW)
    assert (result.state, "HEAD moved" in result.reason) == ("behind", True)
    assert (git(repo, "rev-parse", "other"), git(repo, "rev-parse", "main")) == (head, head)
    assert not (repo / "b.txt").exists()


def test_a_failing_checkout_filter_restores_the_local_copy_and_a_retry_succeeds(repos):
    repo, other = repos
    commit(repo, ".gitattributes", "*.x filter=x\n")
    git(repo, "push", "-q", "origin", "main")
    git(other, "pull", "-q")
    git(repo, "config", "filter.x.smudge", "false")
    git(repo, "config", "filter.x.required", "true")
    before = full(repo)
    commit(other, "a.txt")
    commit(other, "z.x")
    git(other, "push", "-q", "origin", "main")
    head = git(other, "rev-parse", "HEAD")
    result = pullback.run(repo, "main", NOW)
    assert (result.state, "external filter 'false' failed" in result.reason) == ("behind", True)
    assert "partial update" not in result.reason
    assert full(repo) == before
    git(repo, "config", "filter.x.smudge", "cat")
    result = pullback.run(repo, "main", NOW)
    assert (result.state, git(repo, "rev-parse", "HEAD"), (repo / "z.x").read_text()) == ("updated", head, "x\n")


GIT_TIMEOUT = subprocess.TimeoutExpired("git", 120)


def timeout(*_args, **_kwargs):
    raise GIT_TIMEOUT


@pytest.mark.parametrize(
    ("module", "name", "error"),
    [
        (pullback.engine, "fetch", RemoteGitTimeout("fetch exceeded 30 s")),
        (pullback, "holders", GIT_TIMEOUT),
        (pullback, "rev", GIT_TIMEOUT),
        (pullback, "_submodules", GIT_TIMEOUT),
    ],
)
def test_a_timeout_anywhere_leaves_the_target_behind(repos, monkeypatch, module, name, error):
    repo, other = repos
    before = full(repo)
    reason = "git timed out" if error is GIT_TIMEOUT else str(error)
    merged(other)

    def fail(*_args, **_kwargs):
        raise error

    monkeypatch.setattr(module, name, fail)
    result = pullback.run(repo, "main", NOW)
    assert (result.state, result.reason) == ("behind", f"local main is behind: {reason}")
    assert full(repo) == before


def test_an_intentionally_empty_local_commit_is_replayed_with_its_metadata(repos):
    repo, other = repos
    git(repo, "commit", "-q", "--allow-empty", "-m", "marker", "--author", "Ann <ann@a>")
    head = merged(other)
    result = pullback.run(repo, "main", NOW)
    assert (result.state, git(repo, "rev-parse", "HEAD~1")) == ("updated", head)
    assert git(repo, "log", "-1", "--format=%s|%an <%ae>") == "marker|Ann <ann@a>"


def test_a_local_commit_already_upstream_is_kept_as_an_empty_commit(repos):
    repo, other = repos
    (repo / "b.txt").write_text("x\n")
    git(repo, "add", "b.txt")
    git(repo, "commit", "-q", "-m", "same patch", "--author", "Ann <ann@a>")
    head = merged(other)
    result = pullback.run(repo, "main", NOW)
    assert (result.state, git(repo, "rev-parse", "HEAD~1")) == ("updated", head)
    assert git(repo, "log", "-1", "--format=%s|%an <%ae>") == "same patch|Ann <ann@a>"
    assert git(repo, "diff", "HEAD~1", "HEAD") == ""


def test_a_locked_temporary_worktree_is_removed_even_if_remove_times_out(repos, monkeypatch):
    repo, other = repos
    commit(repo, "local.txt")
    real, wts = pullback.pullback_replay.git, worktrees(repo)

    def flaky(path, *args):
        if args[:1] == ("cherry-pick",):
            real(path, "worktree", "lock", str(path))
        if args[:2] == ("worktree", "remove"):
            timeout()
        return real(path, *args)

    monkeypatch.setattr(pullback.pullback_replay, "git", flaky)
    merged(other)
    result = pullback.run(repo, "main", NOW)
    assert (result.state, worktrees(repo)) == ("updated", wts)
