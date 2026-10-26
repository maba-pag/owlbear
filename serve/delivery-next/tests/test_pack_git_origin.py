"""Pack preflight uses the installed bare repository layout and a fetched main snapshot, never live providers."""

import subprocess
from pathlib import Path

import pytest

from owlbear_delivery_next.design_packs import design_pack, pack_git
from owlbear_delivery_next.local_system import codebase, local_home
from owlbear_delivery_next.machine_host import versions

GITHUB = "https://github.com/maba-pag/owlbear.git"


def git(cwd: Path, *args: str) -> str:
    if (cwd / "HEAD").is_file():  # a bare repository: safe.bareRepository=explicit wants it named
        args = ("--git-dir=.", *args)
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()  # noqa: S603, S607


@pytest.fixture
def origin(tmp_path, monkeypatch):
    config = tmp_path / "gitconfig"
    config.write_text("[init]\n\tdefaultBranch = main\n[user]\n\tname = t\n\temail = t@example.com\n")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(config))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setattr(local_home, "root", lambda: tmp_path / "home")
    monkeypatch.setattr(codebase, "URL", GITHUB)
    root = tmp_path / "origin"
    git(tmp_path, "init", "-q", str(root))
    git(root, "commit", "-q", "--allow-empty", "-m", "first")
    (root / "tracked.txt").write_text("second\n")
    git(root, "add", "tracked.txt")
    git(root, "commit", "-qm", "second")
    git(tmp_path, "config", "--file", str(config), f"url.{root}.insteadOf", GITHUB)
    return root


def installed(tmp_path, commit):
    bare = versions.repo()
    versions.fetch(bare)
    folder = tmp_path / "installed" / "v0.1"
    folder.parent.mkdir(parents=True)
    git(bare, "worktree", "add", "-q", "--detach", str(folder), commit)
    return folder


def assert_no_tracking_ref(bare):
    absent = subprocess.run(
        ["git", "--git-dir=.", "rev-parse", "--verify", "--quiet", "refs/remotes/origin/main"],  # noqa: S607
        cwd=bare,
        capture_output=True,
        check=False,
    )
    assert absent.returncode == 1


@pytest.mark.parametrize("rev", ["HEAD~1", "HEAD"])
def test_installed_detached_runtime_on_main_needs_no_tracking_reference(origin, tmp_path, rev):
    pinned = git(origin, "rev-parse", rev)
    runtime = installed(tmp_path, pinned)
    assert git(versions.repo(), "show-ref", "--verify", "refs/heads/main")
    assert_no_tracking_ref(versions.repo())
    before = git(runtime, "status", "--porcelain")

    source = pack_git.source(runtime)

    assert (source.repository, source.base, source.root) == (pack_git.REPOSITORY, pinned, runtime)
    assert git(runtime, "rev-parse", "HEAD") == pinned
    assert git(runtime, "status", "--porcelain") == before
    assert_no_tracking_ref(versions.repo())


def test_installed_runtime_off_main_is_refused(origin, tmp_path):
    runtime = installed(tmp_path, git(origin, "rev-parse", "HEAD"))
    git(runtime, "commit", "-q", "--allow-empty", "-m", "off main")
    with pytest.raises(design_pack.PackError):
        pack_git.source(runtime)


def test_installed_dirty_source_is_refused_before_provider_reads(origin, tmp_path):
    runtime = installed(tmp_path, git(origin, "rev-parse", "HEAD"))
    (runtime / "tracked.txt").write_text("uncommitted owner work\n")

    def guarded(cwd, args):
        if args[0] in {"fetch", "ls-remote"}:
            pytest.fail("Dirty source must be refused before provider reads")
        return pack_git.git(cwd, args)

    with pytest.raises(design_pack.PackError):
        pack_git.source(runtime, run=guarded)
    assert (runtime / "tracked.txt").read_text() == "uncommitted owner work\n"


def test_installed_wrong_identity_is_refused_before_provider_reads(origin, tmp_path):
    runtime = installed(tmp_path, git(origin, "rev-parse", "HEAD"))
    git(runtime, "remote", "set-url", "origin", "https://github.com/not-the-owner/not-owlbear.git")

    def guarded(cwd, args):
        if args[0] in {"fetch", "ls-remote"}:
            pytest.fail("No provider reads are allowed for an untrusted repository identity")
        return pack_git.git(cwd, args)

    with pytest.raises(design_pack.PackError):
        pack_git.source(runtime, run=guarded)


def test_a_failed_exact_fetch_remains_an_explicit_refusal(origin, tmp_path):
    runtime = installed(tmp_path, git(origin, "rev-parse", "HEAD"))
    attempted = []

    def failed(cwd, args):
        if args[0] == "fetch":
            attempted.append(args)
            msg = "synthetic fetch failure"
            raise design_pack.PackError(msg)
        return pack_git.git(cwd, args)

    with pytest.raises(design_pack.PackError):
        pack_git.source(runtime, run=failed)
    assert len(attempted) == 1


def test_normal_clone_still_works(origin, tmp_path):
    clone = tmp_path / "normal"
    git(tmp_path, "clone", "-q", GITHUB, str(clone))
    source = pack_git.source(clone)
    assert source.base == git(origin, "rev-parse", "HEAD")
    assert git(clone, "rev-parse", "origin/main") == source.base


def test_a_newer_main_after_fetch_cannot_replace_the_fetched_snapshot(origin, tmp_path):
    clone = tmp_path / "normal"
    git(tmp_path, "clone", "-q", GITHUB, str(clone))
    captured = git(origin, "rev-parse", "HEAD")
    advanced = []

    def advancing(cwd, args):
        result = pack_git.git(cwd, args)
        if args[0] == "fetch" and not advanced:
            git(origin, "commit", "-q", "--allow-empty", "-m", "new main after fetch")
            advanced.append(git(origin, "rev-parse", "HEAD"))
        return result

    source = pack_git.source(clone, run=advancing)

    assert advanced[0] != captured
    assert source.base == captured
    assert git(clone, "rev-parse", "HEAD") == captured


def test_bare_source_capture_stays_valid_when_main_advances_before_exact_fetch(origin, tmp_path):
    runtime = installed(tmp_path, git(origin, "rev-parse", "HEAD"))
    pinned = git(runtime, "rev-parse", "HEAD")
    advanced = []

    def advancing(cwd, args):
        if args[0] == "fetch" and not advanced:
            git(origin, "commit", "-q", "--allow-empty", "-m", "new main before fetch")
            advanced.append(git(origin, "rev-parse", "HEAD"))
        return pack_git.git(cwd, args)

    source = pack_git.source(runtime, run=advancing)

    assert source.base == pinned
    assert advanced[0] != pinned
    assert git(runtime, "rev-parse", "HEAD") == pinned


@pytest.mark.parametrize("reply", ["", "not-an-object refs/heads/main", "a" * 40 + "\trefs/heads/other"])
@pytest.mark.usefixtures("origin")
def test_missing_or_malformed_remote_main_is_refused_before_fetch(tmp_path, reply):
    clone = tmp_path / "normal"
    git(tmp_path, "clone", "-q", GITHUB, str(clone))

    def malformed(cwd, args):
        if args[0] == "ls-remote":
            return reply
        if args[0] == "fetch":
            pytest.fail("Unverified remote output cannot authorize a fetch")
        return pack_git.git(cwd, args)

    with pytest.raises(design_pack.PackError):
        pack_git.source(clone, run=malformed)
