"""GitHub pull request identity comes from a validated response, not an unchecked request label."""

import json
import subprocess

import pytest

from owlbear_delivery_next.github.gh import GhProvider
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

    def server(argv, _body, _timeout, cwd):
        assert cwd == root
        assert "api" in argv
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, json.dumps(payload).encode(), b"")

    gh = GhProvider(root, runner=server)
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
