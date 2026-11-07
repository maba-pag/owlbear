"""GitHub pull request identity comes from a validated response, not an unchecked request label."""

import json
import subprocess

import pytest

from owlbear_delivery_next.github.gh import GhProvider
from owlbear_delivery_next.github.gh_client import Missing
from owlbear_delivery_next.github.provider import FailureCode, ProviderError


def response(action):
    return {
        "number": 7,
        "node_id": "PR_synthetic",
        "html_url": "https://github.com/o/r/pull/7",
        "head": {"ref": "owlbear/c1", "sha": "a" * 40, "repo": {"full_name": "fork/r"}},
        "base": {"ref": "main", "repo": {"full_name": "o/r"}},
        "draft": action == "create",
        "state": "closed" if action == "read" else "open",
        "merged": action == "read",
        "merge_commit_sha": "b" * 40 if action == "read" else None,
    }


def request(root, payload, action):
    calls = []

    def server(argv, _body, _timeout, cwd, _env):
        assert cwd == root
        assert "api" in argv
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, json.dumps(payload).encode(), b"")

    gh = GhProvider(root, writer=None, runner=server)
    result = (
        gh.read_pull_request("o/r", 7)
        if action == "read"
        else gh.create_pull_request("o/r", "owlbear/c1", "main", "Synthetic change", "Synthetic proof")
    )
    assert len(calls) == 1
    return result


@pytest.mark.parametrize("action", ["read", "create"])
@pytest.mark.parametrize("repository", ["o/r", "O/R"])
def test_response_repository_matches_case_insensitively_and_allows_a_fork_head(tmp_path, action, repository):
    payload = response(action)
    payload["base"]["repo"]["full_name"] = repository
    found = request(tmp_path, payload, action)
    assert found.repository.casefold() == "o/r"
    assert found.number == 7


@pytest.mark.parametrize("action", ["read", "create"])
@pytest.mark.parametrize(
    "repository",
    [
        pytest.param({"full_name": "other/r"}, id="different"),
        pytest.param(None, id="null"),
        pytest.param({}, id="unnamed"),
        pytest.param({"full_name": ""}, id="empty"),
        pytest.param({"full_name": 5}, id="wrong-type"),
        pytest.param("absent", id="absent"),
    ],
)
def test_unproven_response_repository_is_not_relabelled_as_the_requested_one(tmp_path, action, repository):
    payload = response(action)
    if repository == "absent":
        payload["base"].pop("repo")
    else:
        payload["base"]["repo"] = repository
    with pytest.raises(ProviderError) as failed:
        request(tmp_path, payload, action)
    assert failed.value.code is FailureCode.INVALID_RESPONSE


def test_a_gh_failure_keeps_its_whole_stderr_and_an_expected_status_its_last_line(tmp_path, whole_error):
    """#971: a failed gh keeps its whole stderr as the detail its code is read from, then the command and the error
    body `gh api` printed on stdout; an expected status keeps gh's last line."""
    ran = []
    body = '{\n  "message": "BODY-MARK",\n  "documentation_url": "https://docs.github.com/rest"\n}'

    def failing(argv, _body, _timeout, _cwd, _env):
        ran.append(argv)
        return subprocess.CompletedProcess(argv, 1, f"{body}\n".encode(), f"gh: {whole_error}\n".encode())

    def forbidden(argv, _body, _timeout, _cwd, _env):
        stderr = f"{whole_error}\ngh: Resource not accessible (HTTP 403)\n"
        return subprocess.CompletedProcess(argv, 1, b"", stderr.encode())

    with pytest.raises(ProviderError) as failed:
        GhProvider(tmp_path, writer=None, runner=failing).read_pull_request("o/r", 7)
    note = f"CalledProcessError: Command '{ran[0]}' returned non-zero exit status 1.\nstdout:\n{body}"
    assert (failed.value.code, failed.value.retry_safe, str(failed.value), getattr(failed.value, "__notes__", [])) == (
        FailureCode.UNAVAILABLE, True, f"read_pull_request: {whole_error}", [note]
    )  # fmt: skip
    found = GhProvider(tmp_path, writer=None, runner=forbidden)._gh("read_protection", ("api", "x"), absent={403})  # noqa: SLF001
    assert found == Missing(403, "Resource not accessible (HTTP 403)")  # an expected status keeps gh's last line


@pytest.mark.parametrize("fails", ["missing", "slow", "garbled"])
def test_a_gh_that_cannot_answer_keeps_its_whole_cause_in_a_note(tmp_path, whole_error, fails):
    """#971: the OS error (gh, or a working folder that is gone), what gh printed before its timeout, or the JSON it
    could not parse follows the provider's detail, which its code and classification read as before."""
    said = f"{whole_error}\n"

    def broken(argv, _body, _timeout, _cwd, _env):
        if fails == "missing":
            raise FileNotFoundError(2, "No such file or directory", str(tmp_path / "gone"))
        if fails == "slow":
            raise subprocess.TimeoutExpired(argv, 30, output=said.encode())
        return subprocess.CompletedProcess(argv, 0, said.encode(), b"")

    with pytest.raises(ProviderError) as failed:
        GhProvider(tmp_path, writer=None, runner=broken).read_pull_request("o/r", 7)
    exc = failed.value
    cause = exc.__cause__
    if fails == "missing":
        code, detail = FailureCode.UNAVAILABLE, "gh is not installed"
        note = f"FileNotFoundError: [Errno 2] No such file or directory: '{tmp_path / 'gone'}'"
    elif fails == "slow":
        code, detail = FailureCode.TIMEOUT, "gh timed out"
        note = f"TimeoutExpired: Command '{cause.cmd}' timed out after 30 seconds\n{whole_error}"
    else:
        code, detail = FailureCode.INVALID_RESPONSE, "gh returned invalid JSON"
        note = f"JSONDecodeError: {cause}\nstdout:\n{whole_error}"
    assert (exc.code, str(exc), exc.__notes__) == (code, f"read_pull_request: {detail}", [note])
