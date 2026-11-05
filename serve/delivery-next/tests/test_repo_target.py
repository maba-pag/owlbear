"""Onboarding's GitHub repository reads and creation (#723), through a fake ``gh`` runner."""

import json
import subprocess

import pytest

from owlbear_delivery_next.github import repo_target
from owlbear_delivery_next.github.gh_client import GhClient
from owlbear_delivery_next.github.provider import MergeMethod, ProviderError

EMPTY = {  # an empty repository's real `gh repo view` answer before its first push
    "defaultBranchRef": {"name": ""},
    "id": "R_kgDOabc",
    "isEmpty": True,
    "mergeCommitAllowed": True,
    "nameWithOwner": "o/r",
    "rebaseMergeAllowed": True,
    "squashMergeAllowed": False,
    "viewerPermission": "ADMIN",
    "visibility": "PRIVATE",
}
UNRESOLVED = "GraphQL: Could not resolve to a Repository with the name 'o/r'. (repository)\n"


class Gh:
    """Answers each launch in turn with ``(exit, stdout, stderr)`` and records its arguments."""

    def __init__(self, *answers):
        self.answers, self.calls = list(answers), []

    def __call__(self, argv, _data, _timeout, _cwd, _env):
        self.calls.append(argv)
        code, out, err = self.answers.pop(0)
        return subprocess.CompletedProcess(argv, code, out.encode(), err.encode())


def _client(tmp_path, *answers):
    gh = Gh(*answers)
    return GhClient(tmp_path, writer=None, runner=gh), gh


def test_an_empty_repository_is_read_with_its_merge_settings(tmp_path):
    client, gh = _client(tmp_path, (0, json.dumps(EMPTY), ""))
    assert repo_target.view(client, "o/r") == repo_target.RepoState(
        repository="o/r", id="R_kgDOabc", empty=True, default_branch="", visibility="private",
        methods=frozenset({MergeMethod.MERGE, MergeMethod.REBASE}),
    )  # fmt: skip
    assert gh.calls == [("gh", "repo", "view", "o/r", "--json", repo_target.FIELDS)]


def test_a_missing_repository_is_none_and_any_other_failure_raises_whole(tmp_path):
    client, _ = _client(tmp_path, (1, "", UNRESOLVED))
    assert repo_target.view(client, "o/r") is None
    client, _ = _client(tmp_path, (1, "", "error connecting to api.github.com\ncheck your internet connection\n"))
    with pytest.raises(ProviderError) as raised:
        repo_target.view(client, "o/r")
    assert "error connecting to api.github.com\ncheck your internet connection" in str(raised.value)


def test_a_name_is_free_only_when_github_answers_404(tmp_path):
    client, gh = _client(tmp_path, (1, '{"message":"Not Found"}', "gh: Not Found (HTTP 404)\n"))
    assert repo_target.name_free(client, "o", "r")
    assert "repos/o/r" in gh.calls[0]
    client, _ = _client(tmp_path, (0, '{"full_name":"o/r"}', ""))
    assert not repo_target.name_free(client, "o", "r")


def test_create_names_the_visibility_and_reads_the_repository_back(tmp_path):
    client, gh = _client(tmp_path, (0, "https://github.com/o/r\n", ""), (0, json.dumps(EMPTY), ""))
    created = repo_target.create(client, "o", "r", "private")
    assert (created.id, created.visibility, created.empty) == ("R_kgDOabc", "private", True)
    assert gh.calls[0] == ("gh", "repo", "create", "o/r", "--private")
    client, _ = _client(tmp_path, (0, "https://github.com/o/r\n", ""), (1, "", UNRESOLVED))
    with pytest.raises(ProviderError, match="doesn't show it"):
        repo_target.create(client, "o", "r", "public")


@pytest.mark.parametrize(
    ("runs", "status"),
    [
        ([], "missing"),
        ([{"name": "CI", "status": "in_progress", "conclusion": None}], "in_progress"),
        ([{"name": "CI", "status": "completed", "conclusion": "failure"}], "failure"),
    ],
)
def test_ci_status_reads_the_ci_check_run_on_the_commit(tmp_path, runs, status):
    client, gh = _client(tmp_path, (0, json.dumps({"total_count": len(runs), "check_runs": runs}), ""))
    assert repo_target.ci_status(client, "o/r", "abc123") == status
    assert "repos/o/r/commits/abc123/check-runs?check_name=CI" in gh.calls[0]
