"""The account a project's GitHub writes are made by (TD-402): the resolver, the origin and each launch's credentials.

D-01M6G9YYZHNDM3J6F0TYM9TWDK: the token goes only into the child's environment and Git's helpers are reset per launch;
the active ``gh`` account is never switched; an SSH push destination stops the write.
"""

import contextlib
import os
import subprocess
import time
from pathlib import Path

import pytest

from owlbear_delivery_next.git import access as access_module
from owlbear_delivery_next.git import remote_git
from owlbear_delivery_next.git.access import Access, PushRefused
from owlbear_delivery_next.git.remote_git import RemoteGitWriteUnknown
from owlbear_delivery_next.github import account
from owlbear_delivery_next.github.account import AccountMissing, Origin, Writer, resolve
from owlbear_delivery_next.github.gh import GhProvider
from owlbear_delivery_next.github.provider import (
    ConversationItem,
    MergeMethod,
    MergeRequest,
    ProviderError,
    PullRequest,
)
from owlbear_delivery_next.local_system import git_run

BOTH = {"github.com": {"maba-pag": "success", "boecht": "success"}}


def _git(cwd, *args):
    return subprocess.run(("git", "-C", str(cwd), *args), capture_output=True, text=True, check=True).stdout  # noqa: S603, S607


@pytest.fixture
def repo(tmp_path):
    path = tmp_path / "repo"
    path.mkdir()
    _git(path, "init", "-q")
    return path


@pytest.mark.parametrize(
    ("url", "origin"),
    [
        ("https://github.com/boecht/owlbear-sandbox.git", Origin("github.com", "boecht", "owlbear-sandbox")),
        ("https://x-access-token@GitHub.com/boecht/sandbox/", Origin("github.com", "boecht", "sandbox")),
        ("git@github.com:boecht/sandbox.git", Origin("github.com", "boecht", "sandbox")),
        ("ssh://git@ghe.acme.test:2222/Platform/tools.git", Origin("ghe.acme.test", "Platform", "tools")),
        ("https://ghe.acme.test/platform/tools", Origin("ghe.acme.test", "platform", "tools")),
        ("/srv/git/tools.git", Origin.LOCAL),
        ("../tools.git", Origin.LOCAL),
        ("file:///srv/git/tools.git", Origin.LOCAL),
    ],
)
def test_an_origin_names_its_host_owner_and_repository_or_is_local(url, origin):
    assert Origin.url(url) == origin


@pytest.mark.parametrize("url", ["https://github.com/boecht", "github.com:", "https:///boecht/x"])
def test_an_origin_that_names_no_repository_is_the_owners_question(url):
    with pytest.raises(AccountMissing, match="names no GitHub repository"):
        Origin.url(url)


def test_the_origin_is_read_as_written_so_a_url_the_tests_rewrite_still_names_github(repo):
    _git(repo, "remote", "add", "origin", "https://github.com/boecht/sandbox.git")
    assert Origin.of(repo) == Origin("github.com", "boecht", "sandbox")
    assert _git(repo, "remote", "get-url", "origin").startswith("/nonexistent/offline-in-tests/")
    assert account.host_of(repo) == "github.com"
    _git(repo, "remote", "set-url", "origin", "git@ghe.acme.test:platform/tools.git")
    assert account.host_of(repo) == "ghe.acme.test"
    _git(repo, "remote", "remove", "origin")
    with pytest.raises(AccountMissing, match="has no URL for the remote origin"):
        Origin.of(repo)
    assert account.host_of(repo) == "github.com"  # never raises: the launch fails, inside its caller's handling


@pytest.mark.parametrize(
    ("setting", "owner", "active", "login", "why"),
    [
        ("boecht", "acme", "maba-pag", "boecht", "the setting names it"),
        ("repository-owner", "boecht", "maba-pag", "boecht", "the repository owner"),
        ("repository-owner", "Boecht", "maba-pag", "boecht", "the repository owner"),
        ("repository-owner", "acme", "boecht", "maba-pag", "gh has no account for the owner acme"),
        ("BOECHT", "acme", "maba-pag", "boecht", "the setting names it"),
    ],
)
def test_the_setting_the_owner_or_maba_pag_is_resolved_whatever_account_is_active(  # noqa: PLR0913, PLR0917 - one case
    fake_gh, setting, owner, active, login, why
):
    states = {"maba-pag": "success", "boecht": "error"}  # validation failed (offline): still an account gh holds
    fake_gh.set({"github.com": states}, {"github.com": active})
    got = resolve(setting, Origin("github.com", owner, "tools"))
    assert (got.login, got.why, got.host, got.token, got.gh) == (
        login,
        why,
        "github.com",
        f"tok-{login}",
        fake_gh.path.as_posix(),
    )
    assert "tok-" not in repr(got)
    assert all(call["argv"][:2] in (["auth", "token"], ["auth", "status"]) for call in fake_gh.calls())
    assert not any(call["GH_TOKEN"] for call in fake_gh.calls())


def test_the_usual_resolution_is_one_offline_gh_call(fake_gh):
    resolve("repository-owner", Origin("github.com", "boecht", "tools"))
    assert [c["argv"] for c in fake_gh.calls()] == [["auth", "token", "--hostname", "github.com", "--user", "boecht"]]


def test_a_token_in_the_hosts_environment_never_answers_for_an_account(fake_gh, monkeypatch):
    monkeypatch.setenv("GH_TOKEN", "tok-inherited")
    monkeypatch.setenv("GITHUB_TOKEN", "tok-inherited")
    assert resolve("boecht", Origin("github.com", "acme", "tools")).token == "tok-boecht"  # noqa: S105 - a fake token
    assert {(c["GH_TOKEN"], c["GITHUB_TOKEN"]) for c in fake_gh.calls()} == {(None, None)}


@pytest.mark.parametrize(
    ("setting", "owner", "wanted"),
    [("octo-writer", "acme", "octo-writer"), ("repository-owner", "acme", "acme or maba-pag")],
)
def test_an_account_gh_lacks_is_the_owners_question_naming_the_accounts_and_the_fix(fake_gh, setting, owner, wanted):
    fake_gh.set({"github.com": {"boecht": "success"}}, {"github.com": "boecht"})
    with pytest.raises(AccountMissing) as raised:
        resolve(setting, Origin("github.com", owner, "tools"))
    said = str(raised.value)
    assert f"gh holds no account {wanted} on github.com" in said
    assert "github.com/acme/tools" in said
    assert "gh's accounts there: boecht" in said
    assert "gh auth login --hostname github.com" in said
    assert "tok-" not in said
    assert (raised.value.retry_safe, raised.value.code) == (False, "authentication_required")


def test_a_local_origin_needs_no_account_and_asks_gh_nothing(fake_gh):
    got = Writer("octo-writer", Origin.url("file:///srv/tools.git")).access()
    assert got is Access.LOCAL
    assert (got.environment({"GH_TOKEN": "kept"}), got.options()) == ({"GH_TOKEN": "kept"}, ())
    assert fake_gh.calls() == []


def test_the_writer_resolves_at_its_first_use_and_keeps_it(fake_gh, repo):
    _git(repo, "remote", "add", "origin", "https://github.com/boecht/sandbox.git")
    read = []
    writer = Writer(lambda: read.append(1) or "repository-owner", repo)
    assert (read, fake_gh.calls()) == ([], [])
    assert writer.access().login == writer.access().login == "boecht"
    assert (read, len(fake_gh.calls())) == ([1], 1)


def test_an_expired_deadline_starts_no_gh_call(fake_gh):
    with pytest.raises(AccountMissing, match="no time was left"):
        resolve("boecht", Origin("github.com", "acme", "tools"), until=time.monotonic() - 1)
    assert fake_gh.calls() == []


@pytest.mark.usefixtures("fake_gh")
def test_a_deadline_bounds_each_gh_call(monkeypatch):
    seen = []
    real = subprocess.run

    def run(argv, **kw):
        seen.append(kw["timeout"])
        return real(argv, **kw)

    monkeypatch.setattr(account.subprocess, "run", run)
    resolve("repository-owner", Origin("github.com", "acme", "tools"), until=time.monotonic() + 7)
    assert len(seen) == 3  # owner, listing, then maba-pag
    assert all(0 < t <= 7 for t in seen)
    assert seen == sorted(seen, reverse=True)


@pytest.mark.parametrize(("host", "name"), [("github.com", "GH_TOKEN"), ("ghe.acme.test", "GH_ENTERPRISE_TOKEN")])
def test_the_token_is_the_childs_only_github_token_and_the_parent_keeps_its_own(host, name, monkeypatch):
    for each in access_module.TOKENS:
        monkeypatch.setenv(each, "tok-inherited")
    chosen = Access("boecht", "the setting names it", host, "tok-boecht", "/usr/bin/gh")
    child = chosen.environment()
    assert {k: child.get(k) for k in access_module.TOKENS} == {
        k: "tok-boecht" if k == name else None for k in access_module.TOKENS
    }
    assert all(os.environ[k] == "tok-inherited" for k in access_module.TOKENS)


def _fill(repo, options, environment, host="github.com"):
    asked = f"protocol=https\nhost={host}\npath=boecht/sandbox.git\n"
    done = subprocess.run(  # noqa: S603
        ("git", "-C", str(repo), *options, "credential", "fill"),  # noqa: S607
        input=asked, capture_output=True, text=True, env=environment, check=True,
    )  # fmt: skip
    return dict(line.split("=", 1) for line in done.stdout.splitlines())["password"]


@pytest.mark.parametrize("host", ["github.com", "ghe.acme.test"])
def test_git_asks_only_gh_and_gets_the_chosen_token_not_the_configured_helpers(fake_gh, repo, host):
    fake_gh.set({host: {"maba-pag": "success", "boecht": "success"}}, {host: "maba-pag"})
    got = resolve("boecht", Origin(host, "acme", "tools"))
    if host == "github.com":
        assert _fill(repo, (), {**os.environ, "GIT_TERMINAL_PROMPT": "0"}) == "tok-active"  # without the reset
    assert _fill(repo, got.options(), got.environment(), host) == "tok-boecht"
    assert "tok-boecht" not in " ".join(got.options())


@pytest.mark.parametrize(
    "setup",
    [
        ("remote", "set-url", "--add", "--push", "origin", "git@github.com:boecht/sandbox.git"),
        ("config", "url.git@github.com:boecht/.pushInsteadOf", "https://github.com/boecht/"),
        ("config", "url.ssh://git@github.com/boecht/.insteadOf", "https://github.com/boecht/"),
    ],
)
def test_a_push_that_would_leave_over_ssh_is_refused_naming_the_fix(repo, setup):
    _git(repo, "remote", "add", "origin", "https://github.com/boecht/sandbox.git")
    if setup[0] == "remote":  # an SSH push URL listed second, after an HTTPS one
        _git(repo, "remote", "set-url", "--push", "origin", "https://github.com/boecht/sandbox.git")
    _git(repo, *setup)  # longer than the tests' offline rewrite of https://github.com/, so it wins
    chosen = Access("boecht", "the setting names it", "github.com", "tok-boecht", "/usr/bin/gh")
    with pytest.raises(PushRefused) as raised:
        chosen.destinations(repo, "origin", 10)
    said = str(raised.value)
    assert "over SSH" in said
    assert "instead of boecht" in said
    assert "remote set-url --push origin https://" in said


def test_https_and_local_push_destinations_pass(repo, tmp_path):
    _git(repo, "remote", "add", "origin", "https://github.com/boecht/sandbox.git")
    _git(repo, "remote", "add", "data", str(tmp_path / "data.git"))
    chosen = Access("boecht", "the setting names it", "github.com", "tok-boecht", "/usr/bin/gh")
    assert chosen.destinations(repo, "data", 10) == [str(tmp_path / "data.git")]
    assert chosen.destinations(repo, "origin", 10) == ["/nonexistent/offline-in-tests/boecht/sandbox.git"]


GIT_CASES = {  # the setting, the origin's owner, the active account, whose token Git gets
    "the setting names boecht": ("boecht", "acme", "maba-pag", "boecht"),
    "the repository owner's account": (account.REPOSITORY_OWNER, "boecht", "maba-pag", "boecht"),
    "maba-pag for an owner gh lacks": (account.REPOSITORY_OWNER, "acme", "boecht", "maba-pag"),
}


@pytest.mark.parametrize("case", GIT_CASES)
def test_each_remote_git_launch_answers_git_with_the_chosen_accounts_token(case, fake_gh, git_launches, repo):
    setting, owner, active, login = GIT_CASES[case]
    fake_gh.set(BOTH, {"github.com": active})
    _git(repo, "remote", "add", "origin", f"https://github.com/{owner}/sandbox.git")
    chosen = Writer(setting, repo).access()
    remote_git.run_remote_git(repo, ("fetch", "--quiet", "origin", "main"), kind="read", access=chosen)
    with pytest.raises(RemoteGitWriteUnknown):  # the tests' offline rewrite of github.com leaves nowhere to push
        remote_git.run_remote_git(repo, ("push", "--quiet", "origin", "HEAD:refs/heads/x"), kind="write", access=chosen)
    assert git_launches.verbs() == ["fetch", "push"]
    for argv, environment in git_launches.seen:
        options = git_launches.options(argv)
        assert options[:2] == ("-c", "credential.helper=")  # HOME's helper, answering tok-active, is reset
        assert _fill(repo, options, environment) == f"tok-{login}"
    assert not [c for c in fake_gh.calls() if c["argv"][:2] == ["auth", "switch"]]


def test_a_push_over_ssh_is_refused_before_git_starts(fake_gh, git_launches, repo):
    _git(repo, "remote", "add", "origin", "https://github.com/boecht/sandbox.git")
    _git(repo, "remote", "set-url", "--push", "origin", "https://github.com/boecht/sandbox.git")
    _git(repo, "remote", "set-url", "--add", "--push", "origin", "git@github.com:boecht/sandbox.git")
    chosen = Writer("boecht", repo).access()
    with pytest.raises(PushRefused):
        remote_git.run_remote_git(repo, ("push", "--quiet", "origin", "HEAD:refs/heads/x"), kind="write", access=chosen)
    assert git_launches.seen == []
    assert fake_gh.calls()  # the account was resolved; only the push was refused


def test_a_local_origin_launches_git_unchanged_and_asks_gh_nothing(fake_gh, git_launches, repo, tmp_path):
    bare = tmp_path / "origin.git"
    _git(tmp_path, "init", "-q", "--bare", str(bare))
    _git(repo, "remote", "add", "origin", str(bare))
    _git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "i")
    push = ("push", "--quiet", "origin", "HEAD:refs/heads/main")
    remote_git.run_remote_git(repo, push, kind="write", access=Writer.rule(repo).access())
    ((argv, _environment),) = git_launches.seen
    assert argv[1:] == ("-C", str(repo), *push)
    assert fake_gh.calls() == []


HEAD = "a" * 40
PR = PullRequest(
    repository="acme/x", number=7, node_id="n", url="https://github.com/acme/x/pull/7", head_branch="owlbear/c1",
    head_sha=HEAD, base_branch="main", draft=False, state="open", merged=False,
)  # fmt: skip
THREAD = ConversationItem(kind="thread", id="t1", url="https://github.com/acme/x/pull/7#t1", author="a", body="b")
WRITES = {
    "pull request": lambda gh: gh.create_pull_request("acme/x", "owlbear/c1", "main", "t", "b"),
    "labels": lambda gh: gh.add_labels("acme/x", 7, ["release:minor"]),
    "merge": lambda gh: gh.request_merge(MergeRequest(repository="acme/x", number=7, expected_head_sha=HEAD,
                                                      method=MergeMethod.MERGE)),
    "enqueue": lambda gh: gh.enqueue(PR, HEAD),
    "branch deletion": lambda gh: gh.delete_branch("acme/x", "owlbear/c1", HEAD),
    "reply": lambda gh: gh.post_reply("acme/x", 7, THREAD, "done"),
    "thread resolution": lambda gh: gh.resolve_thread("t1"),
}  # fmt: skip


@pytest.mark.parametrize("write", WRITES)
@pytest.mark.parametrize(
    ("setting", "owner", "active", "login"),
    [
        ("boecht", "acme", "maba-pag", "boecht"),
        ("repository-owner", "boecht", "maba-pag", "boecht"),
        ("repository-owner", "acme", "boecht", "maba-pag"),
    ],
)
def test_each_gh_write_is_launched_with_only_the_chosen_accounts_token(  # noqa: PLR0913, PLR0917 - one case
    fake_gh, monkeypatch, write, setting, owner, active, login
):
    for each in access_module.TOKENS:
        monkeypatch.setenv(each, "tok-inherited")
    fake_gh.set(BOTH, {"github.com": active})
    gh = GhProvider(Path(), writer=Writer(setting, Origin("github.com", owner, "x")))
    with contextlib.suppress(ProviderError):  # the fake answers ``{}``; the launch is what is checked
        WRITES[write](gh)
    launches = [c for c in fake_gh.calls() if c["argv"][0] != "auth"]
    assert launches
    assert {(c["GH_TOKEN"], c["GITHUB_TOKEN"], c["GH_ENTERPRISE_TOKEN"]) for c in launches} == {
        (f"tok-{login}", None, None)
    }
    assert all(os.environ[k] == "tok-inherited" for k in access_module.TOKENS)
    assert not any(f"tok-{login}" in " ".join(c["argv"]) for c in fake_gh.calls())


def test_an_enterprise_gh_write_gets_the_enterprise_token_alone(fake_gh, monkeypatch):
    for each in access_module.TOKENS:
        monkeypatch.setenv(each, "tok-inherited")
    fake_gh.set({"ghe.acme.test": {"maba-pag": "success", "boecht": "success"}}, {"ghe.acme.test": "maba-pag"})
    gh = GhProvider(Path(), writer=Writer("boecht", Origin("ghe.acme.test", "acme", "x")), host="ghe.acme.test")
    with contextlib.suppress(ProviderError):
        WRITES["labels"](gh)
    (launch,) = [c for c in fake_gh.calls() if c["argv"][0] != "auth"]
    assert (launch["GH_TOKEN"], launch["GITHUB_TOKEN"], launch["GH_ENTERPRISE_TOKEN"]) == (None, None, "tok-boecht")


def test_an_account_gh_lacks_launches_no_gh_write(fake_gh):
    gh = GhProvider(Path(), writer=Writer("octo-writer", Origin("github.com", "acme", "x")))
    with pytest.raises(AccountMissing) as raised:
        WRITES["labels"](gh)
    assert "octo-writer" in str(raised.value)
    assert all(c["argv"][0] == "auth" for c in fake_gh.calls())


class _Clock:
    """``time.monotonic`` for git_run and the resolver: each launch takes two seconds; each launch's timeout is kept."""

    def __init__(self, monkeypatch) -> None:
        self.now, self.seen, real = 1000.0, [], subprocess.run

        def run(argv, **kw):
            self.seen.append((Path(argv[0]).name, kw["timeout"]))
            self.now += 2
            return real(argv, **kw)

        monkeypatch.setattr(time, "monotonic", lambda: self.now)
        monkeypatch.setattr(subprocess, "run", run)


DEADLINES = {  # cap, until after now, the origin's owner: each launch's timeout, or None for a failed run
    "the cap bounds a later until": (10, 45, "boecht", [("git", 10), ("gh", 8), ("git", 6)]),
    "an until earlier than the cap": (10, 5, "boecht", [("git", 5), ("gh", 3), ("git", 1)]),
    "the cap alone": (10, None, "boecht", [("git", 10), ("gh", 8), ("git", 6)]),
    "resolution uses it all": (10, 4, "acme", [("git", 4), ("gh", 2)]),
}


@pytest.mark.parametrize("case", DEADLINES)
def test_one_deadline_bounds_choosing_the_account_and_git_gets_only_what_is_left(case, fake_gh, repo, monkeypatch):
    """The fetch reads its remote's URL (git), the account's token (gh), then runs; each gets what remains."""
    cap, after, owner, launches = DEADLINES[case]
    fake_gh.set(BOTH, {"github.com": "maba-pag"})
    _git(repo, "remote", "add", "origin", f"https://github.com/{owner}/data.git")
    clock = _Clock(monkeypatch)
    done = git_run.run(repo, "fetch", "-q", "origin", until=None if after is None else clock.now + after, cap=cap)
    assert clock.seen == launches
    if case == "resolution uses it all":  # no listing, no maba-pag token and no fetch once nothing is left
        assert (done.returncode, done.stdout) == (128, "")
        assert "no time was left" in done.stderr


def test_a_command_that_reaches_no_remote_keeps_its_whole_cap_and_resolves_nothing(fake_gh, repo, monkeypatch):
    clock = _Clock(monkeypatch)
    assert git_run.run(repo, "status", "--short", until=None, cap=10).returncode == 0
    assert clock.seen == [("git", 10)]
    assert fake_gh.calls() == []


def _authority(tmp_path):
    """A data checkout whose remote ``authority`` names boecht/data and reaches a local bare copy; ``origin`` names
    acme/other, whose account would be maba-pag's."""
    bare, root = tmp_path / "data.git", tmp_path / "data"
    _git(tmp_path, "init", "-q", "--bare", "-b", "main", str(bare))
    _git(tmp_path, "clone", "-q", str(bare), str(root))
    _git(root, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "i")
    _git(root, "push", "-q", "origin", "HEAD:refs/heads/main")
    _git(root, "remote", "rename", "origin", "authority")
    _git(root, "remote", "set-url", "authority", "https://github.com/boecht/data.git")
    _git(root, "config", f"url.{bare}.insteadOf", "https://github.com/boecht/data.git")  # outranks the offline rule
    _git(root, "remote", "add", "origin", "https://github.com/acme/other.git")
    _git(root, "config", "branch.main.pushRemote", "authority")
    _git(root, "config", "push.default", "current")
    return root


@pytest.mark.parametrize("args", [("push", "-q", "authority", "HEAD:refs/heads/main"), ("push", "-q"), ("fetch", "-q")])
def test_the_remote_git_uses_chooses_the_account(args, fake_gh, git_runs, tmp_path):
    fake_gh.set(BOTH, {"github.com": "maba-pag"})
    root = _authority(tmp_path)
    done = git_run.run(root, *args, until=None, cap=30)
    assert done.returncode == 0, done.stderr
    ((argv, environment, _),) = git_runs.seen
    assert argv[1:3] == ("-c", "credential.helper=")
    assert _fill(root, _options(argv), environment) == "tok-boecht"


def _options(argv):
    """The account's ``-c credential…`` options between ``git`` and the command's own arguments."""
    end = 1
    while argv[end] == "-c" and argv[end + 1].startswith("credential"):
        end += 2
    return argv[1:end]


def test_a_push_over_ssh_through_git_run_is_a_failed_run_and_starts_no_push(fake_gh, git_runs, tmp_path):
    root = _authority(tmp_path)
    _git(root, "remote", "set-url", "--push", "authority", "git@github.com:boecht/data.git")
    done = git_run.run(root, "push", "-q", until=None, cap=30)
    assert done.returncode == 128
    assert "over SSH" in done.stderr
    assert git_runs.seen == []
    assert fake_gh.calls()
