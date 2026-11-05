"""#921 D4: a failed readiness check keeps what failed whole, with its type, on Projects and in the host's log."""

import subprocess
import time
import urllib.error
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from owlbear_delivery_next.change_contracts.profile_record import Profile
from owlbear_delivery_next.git.access import Access
from owlbear_delivery_next.github.account import AccountMissing
from owlbear_delivery_next.local_system import codebase, git_files
from owlbear_delivery_next.local_system.data_repo import DataRepoError
from owlbear_delivery_next.machine_host import app, project
from owlbear_delivery_next.machine_host.machine import Machine
from owlbear_delivery_next.project_host.host import Host, HostRecord
from owlbear_delivery_next.runtimes import copilot_cli, readiness
from owlbear_delivery_next.state_store import prefs_import, profile_share
from owlbear_delivery_next.state_store.database import StoreError
from owlbear_delivery_next.state_store.store import Store

REPO_VIEW = f"gh repo view --json {readiness.REPO_FIELDS}"
HEAD = "git rev-parse --verify --quiet HEAD"
ON_MAIN = (
    '{"nameWithOwner": "o/r", "viewerPermission": "ADMIN", "isEmpty": false, "defaultBranchRef": {"name": "main"}}'
)
READY = {
    "gh --version": (0, "gh version 2.102.0"),
    REPO_VIEW: (0, ON_MAIN),
    "copilot --version": (0, "1.0.95"),
    "git config user.name": (0, "Ada"),
    "git config user.email": (0, "ada@example.com"),
}
OUT = "OUT begins\nwhat gh printed on stdout, in the middle\nOUT ends"
SIGN_IN = readiness.SIGN_IN.format(host="github.com")
GPG_FIX = "Unlock your GPG key (`echo test | gpg --clearsign`), then run setup again"
SIGNED = SimpleNamespace(
    access=lambda: Access("ada", "the setting names it", "github.com", "tok-ada", "gh"), unset=False
)


def missing(reason: str, error: type[Exception] = AccountMissing) -> SimpleNamespace:
    """A writer whose account can't be had: *reason* is *error*'s whole text."""

    def access() -> Access:
        raise error(reason)

    return SimpleNamespace(access=access, unset=False)


def failed(table: dict[str, tuple[int, str]], writer: SimpleNamespace = SIGNED) -> list[tuple[str, str]]:
    said = READY | table
    probe = lambda argv, _env=None: said.get(" ".join(argv), (0, ""))  # noqa: E731
    checks = readiness.readiness("github.com", probe, None, "copilot", writer)
    return [(c.name, c.detail) for c in checks if not c.ok]


@pytest.mark.parametrize(
    ("table", "name", "detail"),
    [
        pytest.param({"gh --version": (127, "{W}")}, "github cli", "{W}", id="gh-cli"),
        pytest.param({REPO_VIEW: (1, "{W}")}, "repository", "{W}", id="repository"),
        pytest.param({"copilot --version": (1, "{W}")}, "copilot cli", "copilot: {W}", id="copilot-cli"),
        pytest.param({"git config user.name": (128, "{W}")}, "git identity", "{W}", id="identity-unread"),
        pytest.param(
            {"git config --bool commit.gpgsign": (0, "true"), "git config user.signingkey": (-15, "{W}")},
            "commit signing",
            "{W}",
            id="signing-key-unread",
        ),
    ],
)
def test_a_failed_command_s_whole_output_is_its_check_s_detail(table, name, detail, whole_error):
    filled = {argv: (code, said.format(W=whole_error)) for argv, (code, said) in table.items()}
    assert failed(filled) == [(name, detail.format(W=whole_error))]


# `gh repo view` of an empty repository, as gh answered it on 2026-11-04
EMPTY = '{"defaultBranchRef":{"name":""},"isEmpty":true,"nameWithOwner":"o/r","viewerPermission":"ADMIN"}'
READS = {"gh --version", REPO_VIEW, HEAD, "copilot --version"}


@pytest.mark.parametrize(
    ("remote", "local", "detail", "command"),
    [
        pytest.param(
            EMPTY,
            (1, ""),
            "o/r has no commits yet, and neither has this clone",
            'git add <file> && git commit -m "First commit" && git push -u origin HEAD',
            id="both-empty",
        ),
        pytest.param(
            ON_MAIN,
            (1, ""),
            "o/r has commits on main, but this clone has none",
            "git pull --set-upstream origin main",
            id="clone-empty",
        ),
        pytest.param(
            ON_MAIN.replace('"main"', '"release/$USER;x"'),
            (1, ""),
            "o/r has commits on release/$USER;x, but this clone has none",
            "git pull --set-upstream origin 'release/$USER;x'",
            id="clone-empty-shell-branch",
        ),
        pytest.param(
            EMPTY,
            (0, "abc123"),
            "o/r has no commits yet, but this clone has",
            "git push -u origin HEAD",
            id="github-empty",
        ),
    ],
)
def test_a_repository_or_clone_without_commits_fails_first_commit_with_the_commands_that_end_it(
    remote, local, detail, command
):
    ran: list[str] = []
    said = READY | {REPO_VIEW: (0, remote), HEAD: local}

    def probe(argv: list[str], _env: object = None) -> tuple[int, str]:
        ran.append(" ".join(argv))
        return said.get(ran[-1], (0, ""))

    checks = readiness.readiness("github.com", probe, None, "copilot", SIGNED)
    assert [(c.name, c.detail) for c in checks if not c.ok] == [("first commit", detail)]
    assert f"`{command}`" in next(c.fix for c in checks if not c.ok)
    assert {c for c in ran if not c.startswith("git config ")} <= READS  # each probe only reads


def test_a_repository_and_clone_with_commits_pass_first_commit_naming_the_default_branch():
    probe = lambda argv, _env=None: READY.get(" ".join(argv), (0, ""))  # noqa: E731
    checks = readiness.readiness("github.com", probe, None, "copilot", SIGNED)
    assert [(c.ok, c.detail) for c in checks if c.name == "first commit"] == [(True, "default branch main")]


def test_a_failing_head_probe_fails_first_commit_with_gits_error_whole():
    fatal = "fatal: detected dubious ownership in repository at '/p'\nTo add an exception for this directory, call:"
    probe = lambda argv, _env=None: (READY | {HEAD: (128, fatal)}).get(" ".join(argv), (0, ""))  # noqa: E731
    checks = readiness.readiness("github.com", probe, None, "copilot", SIGNED)
    assert [(c.name, c.detail) for c in checks if not c.ok] == [("first commit", fatal)]


@pytest.mark.parametrize("error", [AccountMissing, StoreError])  # gh lacks it; the settings naming it can't be read
def test_an_account_that_can_t_be_had_keeps_its_whole_reason_as_the_sign_in_detail(whole_error, error):
    assert failed({}, missing(whole_error, error)) == [("github sign-in", str(error(whole_error)))]


def test_an_unreached_host_s_whole_error_and_type_are_the_network_check_s_detail(monkeypatch, whole_error):
    def refused(*_args: object, **_kwargs: object) -> None:
        raise urllib.error.URLError(OSError(whole_error))

    monkeypatch.setattr(readiness.urllib.request, "build_opener", lambda *_a: SimpleNamespace(open=refused))
    [network] = readiness.publishing(
        "github.com", lambda argv, _env=None: READY.get(" ".join(argv), (0, "")), readiness.reach("github.com"), SIGNED
    )[:1]
    assert (network.ok, network.detail) == (False, f"https://github.com: OSError: {whole_error}")


def test_an_unreadable_ssh_key_file_names_its_error_s_type(tmp_path):
    pub = tmp_path / ("a-key-file-whose-name-is-long-enough-that-its-error-says-more-than-two-hundred-characters" * 2)
    signing = {"git config --bool commit.gpgsign": (0, "true"), "git config gpg.format": (0, "ssh")}
    said = f"ssh key {pub}.pub: FileNotFoundError: [Errno 2] No such file or directory: '{pub}.pub'"
    assert failed(signing | {"git config user.signingkey": (0, str(pub))}) == [("commit signing", said)]


def test_a_timed_out_probe_keeps_both_streams_in_its_check_s_detail(tmp_path, monkeypatch, whole_error):
    def timed_out(argv: list[str], **_kwargs: object) -> None:
        raise subprocess.TimeoutExpired(argv, 30, output=OUT, stderr=whole_error)

    monkeypatch.setattr(git_files.subprocess, "run", timed_out)
    [gh] = [c for c in readiness.publishing("github.com", git_files.probe_in(tmp_path), None, SIGNED) if not c.ok]
    timeout = "TimeoutExpired: Command '['gh', '--version']' timed out after 30 seconds"
    said = f"{timeout}\nstderr:\n{whole_error}\nstdout:\n{OUT}"
    assert (gh.name, gh.detail) == ("github cli", said)


def test_a_probe_that_exits_non_zero_names_its_command_status_and_both_streams(tmp_path, monkeypatch, whole_error):
    def refused(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess:
        code = 1 if argv[:2] == ["gh", "repo"] else 0
        return subprocess.CompletedProcess(argv, code, OUT, whole_error if code else "")

    monkeypatch.setattr(git_files.subprocess, "run", refused)
    [repo] = [c for c in readiness.publishing("github.com", git_files.probe_in(tmp_path), None, SIGNED) if not c.ok]
    command = f"CalledProcessError: Command '{['gh', 'repo', 'view', '--json', readiness.REPO_FIELDS]}'"
    said = f"{command} returned non-zero exit status 1.\nstderr:\n{whole_error}\nstdout:\n{OUT}"
    assert (repo.name, repo.detail) == ("repository", said)


GPG = "gpg --batch --yes --pinentry-mode error -u K --clearsign -o /dev/null /dev/null"


@pytest.mark.parametrize(
    "case",
    [
        pytest.param((GPG, 2, "gpg key K locked or missing: {said}"), id="gpg"),
        pytest.param(("ssh-add -L", 2, "ssh-agent not reachable: {said}"), id="ssh"),
        pytest.param(("ssh-add -L", 1, "ssh key not in the agent"), id="no-identities"),
    ],
)
def test_a_locked_gpg_key_or_an_unreachable_ssh_agent_keeps_the_probe_s_whole_failure(
    tmp_path, monkeypatch, whole_error, case
):
    failing, code, detail = case
    fmt = "" if failing == GPG else "ssh"
    key = "key::ssh-ed25519 AAAAKEY" if fmt else "K"
    said = {
        "git config --bool commit.gpgsign": "true",
        "git config gpg.format": fmt,
        "git config user.signingkey": key,
        **{argv: out for argv, (_code, out) in READY.items()},
    }

    def run(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess:
        joined = " ".join(argv)
        if joined == failing:
            return subprocess.CompletedProcess(argv, code, OUT, whole_error)
        return subprocess.CompletedProcess(argv, 0 if said.get(joined) else 1, said.get(joined, ""), "")

    monkeypatch.setattr(git_files.subprocess, "run", run)
    [signing] = [c for c in readiness.readiness("github.com", git_files.probe_in(tmp_path), None, "copilot", SIGNED)
                 if c.name == "commit signing"]  # fmt: skip
    command = f"CalledProcessError: Command '{failing.split()}' returned non-zero exit status {code}."
    whole = f"{command}\nstderr:\n{whole_error}\nstdout:\n{OUT}"
    assert (signing.ok, signing.detail) == (False, detail.format(said=whole))


@pytest.mark.parametrize("step", ["detection", "legacy"])
def test_a_failed_detection_or_legacy_import_names_its_error_s_type(tmp_path, monkeypatch, whole_error, step):
    def raised(*_args: object) -> None:
        raise (StoreError if step == "detection" else DataRepoError)(whole_error)

    monkeypatch.setattr(readiness, "check", lambda *_args: [])
    if step == "detection":
        monkeypatch.setattr(profile_share, "checked", raised)
        said = ("profile detection", f"StoreError: {whole_error}")
    else:
        monkeypatch.setattr(profile_share, "checked", lambda *_args: Profile())
        monkeypatch.setattr(prefs_import, "run", raised)
        said = ("legacy preferences", f"DataRepoError: {whole_error}")
    assert [(c.name, c.detail) for c in readiness.ready(Store(tmp_path / "s"), tmp_path, carry=True)] == [said]


def test_a_project_s_failed_checks_show_whole_in_its_entry_and_the_host_s_log(
    tmp_path, monkeypatch, capsys, whole_error
):
    """Two checks the producers fail, through the project's own readiness run, as Projects reads them."""
    signing = {
        "git config --bool commit.gpgsign": (0, "true"),
        "git config user.signingkey": (0, "K"),
        GPG: (2, whole_error),
    }
    probe = READY | signing | {"copilot --version": (1, OUT)}
    produced = readiness.readiness(
        "github.com", lambda argv, _env=None: probe.get(" ".join(argv), (0, "")), None, "copilot", missing(whole_error)
    )
    monkeypatch.setattr(project.readiness, "ready", lambda _store, _repo, **_kwargs: produced)
    monkeypatch.setattr(Host, "_spawn", lambda _self, slug: pytest.fail(f"no runner starts here ({slug})"))
    now = datetime.now(UTC)
    record = HostRecord(url="http://127.0.0.1:9/", token="t", pid=1, started_at=now, code=codebase.CURRENT)  # noqa: S106
    machine = Machine(record)
    folder = tmp_path / "shop"
    for args in (["init", "-q", str(folder)], ["-C", str(folder), "commit", "-q", "--allow-empty", "-m", "i"]):
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], check=True)  # noqa: S603, S607
    try:
        http = TestClient(app.create(machine), base_url="http://127.0.0.1", headers={"authorization": "Bearer t"})
        assert http.post("/api/next/projects", json={"path": str(folder)}).status_code == 200
        end = time.monotonic() + 10
        while (ready := http.get("/api/next/projects").json()["projects"][0].get("ready")) is None:
            assert time.monotonic() < end, "never checked"
            time.sleep(0.05)
    finally:
        machine.stop_all()
    expected = [
        f"github sign-in: {AccountMissing(whole_error)} · fix: {SIGN_IN}",
        f"copilot cli: copilot: {OUT} · fix: {copilot_cli.FIX}",
        f"commit signing: gpg key K locked or missing: {whole_error} · fix: {GPG_FIX}",
    ]
    assert ready == expected
    assert f"readiness: {'; '.join(expected)}\n" in capsys.readouterr().out
