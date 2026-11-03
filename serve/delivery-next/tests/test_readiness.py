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

READY = {
    "gh --version": (0, "gh version 2.102.0"),
    "gh repo view --json nameWithOwner,viewerPermission": (0, '{"nameWithOwner": "o/r", "viewerPermission": "ADMIN"}'),
    "copilot --version": (0, "1.0.95"),
    "git config user.name": (0, "Ada"),
    "git config user.email": (0, "ada@example.com"),
}
OUT = "OUT begins\nwhat gh printed on stdout, in the middle\nOUT ends"
SIGN_IN = readiness.SIGN_IN.format(host="github.com")
SIGNED = SimpleNamespace(
    access=lambda: Access("ada", "the setting names it", "github.com", "tok-ada", "gh"), unset=False
)


def missing(reason: str) -> SimpleNamespace:
    """A writer whose account ``gh`` lacks: *reason* is AccountMissing's whole text."""

    def access() -> Access:
        raise AccountMissing(reason)

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
        pytest.param(
            {"gh repo view --json nameWithOwner,viewerPermission": (1, "{W}")}, "repository", "{W}", id="repository"
        ),
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


def test_an_account_gh_lacks_keeps_its_whole_reason_as_the_sign_in_detail(whole_error):
    assert failed({}, missing(whole_error)) == [("github sign-in", str(AccountMissing(whole_error)))]


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
    command = f"CalledProcessError: Command '{['gh', 'repo', 'view', '--json', 'nameWithOwner,viewerPermission']}'"
    said = f"{command} returned non-zero exit status 1.\nstderr:\n{whole_error}\nstdout:\n{OUT}"
    assert (repo.name, repo.detail) == ("repository", said)


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
    probe = READY | {"copilot --version": (1, OUT)}
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
    ]
    assert ready == expected
    assert f"readiness: {'; '.join(expected)}\n" in capsys.readouterr().out
