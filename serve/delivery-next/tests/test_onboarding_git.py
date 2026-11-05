"""Onboarding's local Git steps (#723): folder state, identity by target remote, starter files, the first commit
from an emptied index, and push, clone and pull through local bare remotes."""

import os
import subprocess

import pytest

from owlbear_delivery_next.git.access import Access
from owlbear_delivery_next.git.command_failure import failure
from owlbear_delivery_next.git.remote_git import RemoteGitFailed
from owlbear_delivery_next.local_system import onboarding_git as og
from owlbear_delivery_next.runtimes import readiness

BOECHT = "https://github.com/boecht/new"


def _git(cwd, *args):
    return subprocess.run(("git", "-C", str(cwd), *args), capture_output=True, text=True, check=True).stdout.strip()  # noqa: S603, S607


def _bare(path):
    _git(path.parent, "init", "-q", "--bare", "-b", "main", str(path))
    return path


def _first(path, origin, *, ci=False):
    """A new project as E5 makes it: init, origin, author, starter files, first commit."""
    og.init(path)
    og.set_origin(path, str(origin))
    og.write_author(path, "t", "t@example.com")
    og.starter_files(path, path.name, ci)
    return og.first_commit(path, "Start")


def test_folder_state_tells_absent_empty_files_unborn_and_commits_apart(tmp_path):
    absent = og.folder_state(tmp_path / "absent")
    assert (absent.exists, absent.empty, absent.has_files, absent.git, absent.enclosing) == (
        False, False, False, "none", None,
    )  # fmt: skip
    (tmp_path / "empty").mkdir()
    assert og.folder_state(tmp_path / "empty").empty
    (tmp_path / "files").mkdir()
    (tmp_path / "files" / "a.txt").write_text("a")
    files = og.folder_state(tmp_path / "files")
    assert (files.empty, files.has_files, files.git) == (False, True, "none")
    og.init(tmp_path / "unborn")
    unborn = og.folder_state(tmp_path / "unborn")
    assert (unborn.empty, unborn.has_files, unborn.git, unborn.origin) == (True, False, "unborn", None)
    sha = _first(tmp_path / "made", _bare(tmp_path / "r.git"), ci=True)
    made = og.folder_state(tmp_path / "made")
    assert (made.empty, made.git, made.origin, made.has_workflows) == (False, "commits", str(tmp_path / "r.git"), True)
    assert _git(tmp_path / "made", "rev-parse", "HEAD") == sha
    assert not og.folder_state(tmp_path / "files").has_workflows


def test_a_folder_inside_another_repository_names_it_as_enclosing(tmp_path):
    outer = tmp_path / "outer"
    og.init(outer)
    (outer / "sub").mkdir()
    for inside in (outer / "sub", outer / "new" / "deep"):
        state = og.folder_state(inside)
        assert (state.git, state.origin, state.enclosing) == ("none", None, outer.resolve())
    assert og.folder_state(outer).enclosing is None


def test_the_first_commit_leaves_out_a_file_staged_before_it_was_ignored(tmp_path):
    path = tmp_path / "p"
    og.init(path)
    og.write_author(path, "t", "t@example.com")
    (path / "secret.txt").write_text("token")
    _git(path, "add", "secret.txt")
    (path / ".gitignore").write_text("secret.txt\n")
    (path / "a.txt").write_text("a")
    sha = og.first_commit(path, "Start")
    assert _git(path, "ls-tree", "-r", "--name-only", sha).split() == [".gitignore", "a.txt"]
    assert (path / "secret.txt").read_text() == "token"
    assert (path / ".gitignore").read_text() == "secret.txt\n"
    with pytest.raises(og.LocalGitError, match="already has commits"):
        og.first_commit(path, "Again")


def test_starter_files_are_a_readme_and_the_ci_workflow_only_when_asked(tmp_path):
    plain, ci, only = tmp_path / "plain", tmp_path / "ci", tmp_path / "only"
    for path in (plain, ci, only):
        path.mkdir()
    assert og.starter_files(plain, "Plain", ci=False) == ["README.md"]
    assert (plain / "README.md").read_text() == "# Plain\n"
    assert not (plain / ".github").exists()
    assert og.starter_files(ci, "Ci", ci=True) == ["README.md", ".github/workflows/ci.yml"]
    workflow = (ci / og.CI_PATH).read_text()
    assert "on:\n  push:\n  pull_request:\n" in workflow
    assert "jobs:\n  CI:\n" in workflow
    assert og.starter_files(only, "Only", ci=True, readme=False) == [".github/workflows/ci.yml"]
    assert sorted(p.name for p in only.iterdir()) == [".github"]
    assert not any(p.name == ".gitignore" for p in tmp_path.rglob("*"))


def test_push_clone_and_pull_through_local_remotes(tmp_path):
    bare = _bare(tmp_path / "r.git")
    project = tmp_path / "project"
    og.init(project)
    og.set_origin(project, "https://github.com/o/elsewhere")
    sha = _first(project, bare)  # set_origin again: set-url this time
    og.push_first(project, Access.LOCAL)
    assert _git(bare, "rev-parse", "main") == sha
    assert _git(project, "rev-parse", "--abbrev-ref", "@{u}") == "origin/main"

    cloned = og.clone(tmp_path / "clones", str(bare), "c", Access.LOCAL)
    assert cloned == tmp_path / "clones" / "c"
    assert _git(cloned, "rev-parse", "HEAD") == sha

    empty = _bare(tmp_path / "empty.git")
    unborn = og.clone(tmp_path / "clones", str(empty), "u", Access.LOCAL)
    assert og.folder_state(unborn).git == "unborn"
    _git(project, "push", "-q", str(empty), "main")
    og.pull_default(unborn, "main", Access.LOCAL)
    assert _git(unborn, "rev-parse", "HEAD") == sha
    assert _git(unborn, "rev-parse", "--abbrev-ref", "@{u}") == "origin/main"

    with pytest.raises(RemoteGitFailed) as raised:
        og.clone(tmp_path / "clones", str(tmp_path / "missing.git"), "m", Access.LOCAL)
    assert "exit 128" in str(raised.value)
    assert "missing.git' does not exist" in str(raised.value)  # git's own stderr
    assert "'clone'" in failure(raised.value)  # the command, in its note


def _clean_home(tmp_path, monkeypatch, gitconfig):
    home = tmp_path / "home"
    home.mkdir()
    (home / ".gitconfig").write_text(gitconfig)
    monkeypatch.setenv("HOME", str(home))
    for name in [n for n in os.environ if n.startswith("GIT_CONFIG")] + ["XDG_CONFIG_HOME"]:
        monkeypatch.delenv(name, raising=False)
    return home


def test_push_urls_are_read_after_rewrites_and_must_name_the_target(tmp_path, monkeypatch):
    _clean_home(tmp_path, monkeypatch, "")
    path = tmp_path / "p"
    og.init(path)
    og.set_origin(path, "https://github.com/Boecht/Sandbox.git")
    _git(path, "config", "url.https://github.com/other/.pushInsteadOf", "https://github.com/Boecht/")
    assert og.push_urls_name(path, "origin", "https://github.com/boecht/sandbox", 10) == [
        "https://github.com/other/Sandbox.git"
    ]
    _git(path, "config", "--unset", "url.https://github.com/other/.pushInsteadOf")
    for url in ("git@github.com:boecht/sandbox", "ssh://git@github.com/BOECHT/sandbox.git", "/srv/sandbox.git"):
        _git(path, "remote", "set-url", "--add", "--push", "origin", url)
    assert og.push_urls(path) == [
        "git@github.com:boecht/sandbox", "ssh://git@github.com/BOECHT/sandbox.git", "/srv/sandbox.git",
    ]  # fmt: skip
    assert og.push_urls_name(path, "origin", "https://github.com/boecht/sandbox", 10) == ["/srv/sandbox.git"]
    assert og.foreign_urls(
        ["https://ghe.acme.test/boecht/sandbox", "https://github.com/boecht/sandbox2", "https://github.com/boecht"],
        "https://github.com/boecht/sandbox.git",
    ) == ["https://ghe.acme.test/boecht/sandbox", "https://github.com/boecht/sandbox2", "https://github.com/boecht"]


def test_identity_and_signing_are_read_with_the_target_remote(tmp_path, monkeypatch):
    home = _clean_home(
        tmp_path,
        monkeypatch,
        "[user]\n\tname = maba\n\temail = m@example.com\n"
        '[includeIf "hasconfig:remote.*.url:https://github.com/boecht/**"]\n\tpath = identity-boecht\n',
    )
    (home / "identity-boecht").write_text(
        "[user]\n\tname = boecht\n\temail = b@example.com\n\tsigningkey = boecht-key\n"
        "[commit]\n\tgpgsign = yes\n[gpg]\n\tformat = x509\n"
    )
    (tmp_path / "Projects").mkdir()
    folder = tmp_path / "Projects" / "new"  # still to be made: read from its parent
    assert readiness.identity(og.target_probe(folder, BOECHT)).detail == "boecht <b@example.com>"
    assert readiness.signing(og.target_probe(folder, BOECHT)).detail == "x509: not verified by setup"
    assert readiness.identity(og.target_probe(folder, "")).detail == "maba <m@example.com>"
    assert readiness.signing(og.target_probe(folder, "")).detail == "not required"

    og.init(folder)
    og.set_origin(folder, BOECHT)  # before the first commit, so Git picks boecht's identity
    _git(folder, "config", "--local", "commit.gpgsign", "false")  # the fixture has no x509 key to sign with
    og.starter_files(folder, "new", ci=False)
    sha = og.first_commit(folder, "Start")
    assert (
        _git(folder, "log", "-1", "--format=%an <%ae> %cn <%ce>", sha)
        == "boecht <b@example.com> boecht <b@example.com>"
    )
