"""The account a project's GitHub writes are made by (TD-402): the resolver, the origin and each launch's credentials.

D-01M6G9YYZHNDM3J6F0TYM9TWDK: the token goes only into the child's environment and Git's helpers are reset per launch;
the active ``gh`` account is never switched; an SSH push destination stops the write.
"""

import os
import subprocess
import time

import pytest

from owlbear_delivery_next.git import access as access_module
from owlbear_delivery_next.git.access import Access, PushRefused, destinations
from owlbear_delivery_next.github import account
from owlbear_delivery_next.github.account import AccountMissing, Origin, Writer, resolve

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
        destinations(repo, "origin", chosen, 10)
    said = str(raised.value)
    assert "over SSH" in said
    assert "instead of boecht" in said
    assert "remote set-url --push origin https://" in said


def test_https_and_local_push_destinations_pass(repo, tmp_path):
    _git(repo, "remote", "add", "origin", "https://github.com/boecht/sandbox.git")
    _git(repo, "remote", "add", "data", str(tmp_path / "data.git"))
    chosen = Access("boecht", "the setting names it", "github.com", "tok-boecht", "/usr/bin/gh")
    assert destinations(repo, "data", chosen, 10) == [str(tmp_path / "data.git")]
    assert destinations(repo, "origin", chosen, 10) == ["/nonexistent/offline-in-tests/boecht/sandbox.git"]
