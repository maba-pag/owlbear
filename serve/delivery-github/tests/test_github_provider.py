"""Behavioral tests for the fixed GitHub CLI publication provider."""

from __future__ import annotations

import json
import subprocess
from collections import deque
from dataclasses import dataclass, field

import pytest

from owlbear_delivery import (
    CreateDraftPublicationPullRequest,
    FindPublicationPullRequest,
    PublicationProvider,
    PublicationProviderError,
    PublicationProviderFailureCode,
    SetPublicationPullRequestDraftState,
    UpdatePublicationPullRequest,
)
from owlbear_delivery_github import GitHubCliPublicationProvider

_REPOSITORY = "example/project"
_HEAD = "a" * 40
_OTHER_HEAD = "b" * 40


def _pull_response(*, draft: bool = True, head: str = _HEAD) -> dict[str, object]:
    return {
        "number": 7,
        "node_id": "PR_node_7",
        "head": {"ref": "owlbear/change/example", "sha": head},
        "base": {"ref": "main", "sha": _OTHER_HEAD},
        "title": "Example change",
        "body": "Generated summary",
        "draft": draft,
        "state": "open",
        "merged": False,
        "merge_commit_sha": _OTHER_HEAD,
    }


def _completed(
    payload: object,
    *,
    returncode: int = 0,
    stderr: bytes = b"",
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.CompletedProcess(
        args=(),
        returncode=returncode,
        stdout=json.dumps(payload).encode(),
        stderr=stderr,
    )


@dataclass
class _QueuedRunner:
    results: deque[subprocess.CompletedProcess[bytes] | BaseException]
    calls: list[tuple[tuple[str, ...], bytes | None, float]] = field(default_factory=list)

    def __call__(
        self,
        arguments: tuple[str, ...],
        input_bytes: bytes | None,
        timeout_seconds: float,
    ) -> subprocess.CompletedProcess[bytes]:
        self.calls.append((arguments, input_bytes, timeout_seconds))
        result = self.results.popleft()
        if isinstance(result, BaseException):
            raise result
        return result


def _provider(
    *results: subprocess.CompletedProcess[bytes] | BaseException,
) -> tuple[GitHubCliPublicationProvider, _QueuedRunner]:
    runner = _QueuedRunner(deque(results))
    return GitHubCliPublicationProvider(timeout_seconds=12.5, runner=runner), runner


def test_reads_repository_and_unique_pull_request_through_fixed_get_vectors() -> None:
    provider, runner = _provider(
        _completed({"full_name": _REPOSITORY, "default_branch": "main"}),
        _completed([{"number": 7}]),
        _completed(_pull_response()),
    )
    assert isinstance(provider, PublicationProvider)

    repository = provider.read_repository(_REPOSITORY)
    pull_request = provider.find_pull_request(
        FindPublicationPullRequest(
            repository=_REPOSITORY,
            head_branch="owlbear/change/example",
            base_branch="main",
        )
    )

    assert repository.repository == _REPOSITORY
    assert pull_request is not None
    assert pull_request.number == 7
    assert runner.calls[0][0][-1] == "repos/example/project"
    assert runner.calls[1][0][-1] == (
        "repos/example/project/pulls?state=all&head=example%3Aowlbear%2Fchange%2Fexample&base=main&per_page=100"
    )
    assert runner.calls[2][0][-1] == "repos/example/project/pulls/7"
    assert all(call[1] is None and call[2] == 12.5 for call in runner.calls)


def test_pull_request_lookup_distinguishes_missing_and_ambiguous_identity() -> None:
    request = FindPublicationPullRequest(
        repository=_REPOSITORY,
        head_branch="owlbear/change/example",
        base_branch="main",
    )
    provider, _ = _provider(_completed([]))
    assert provider.find_pull_request(request) is None

    provider, _ = _provider(_completed([{"number": 7}, {"number": 8}]))
    with pytest.raises(PublicationProviderError) as exc_info:
        provider.find_pull_request(request)
    assert exc_info.value.code is PublicationProviderFailureCode.CONFLICT


def test_creates_draft_pull_request_with_fixed_json_payload() -> None:
    provider, runner = _provider(_completed(_pull_response()))

    created = provider.create_draft_pull_request(
        CreateDraftPublicationPullRequest(
            repository=_REPOSITORY,
            head_branch="owlbear/change/example",
            head_sha=_HEAD,
            base_branch="main",
            title="Example change",
            body="Generated summary",
        )
    )

    arguments, input_bytes, _ = runner.calls[0]
    assert created.draft is True
    assert arguments[-3:] == ("repos/example/project/pulls", "--input", "-")
    assert json.loads(input_bytes or b"") == {
        "base": "main",
        "body": "Generated summary",
        "draft": True,
        "head": "owlbear/change/example",
        "title": "Example change",
    }
    assert not hasattr(provider, "merge_pull_request")
    assert not hasattr(provider, "request")


@pytest.mark.parametrize(
    "response",
    [
        {**_pull_response(), "draft": False},
        {
            **_pull_response(),
            "head": {"ref": "owlbear/change/example", "sha": _OTHER_HEAD},
        },
        {**_pull_response(), "state": "closed", "merged": True},
    ],
)
def test_create_rejects_provider_response_outside_requested_identity(response: dict[str, object]) -> None:
    provider, _ = _provider(_completed(response))

    with pytest.raises(PublicationProviderError) as exc_info:
        provider.create_draft_pull_request(
            CreateDraftPublicationPullRequest(
                repository=_REPOSITORY,
                head_branch="owlbear/change/example",
                head_sha=_HEAD,
                base_branch="main",
                title="Example change",
                body="Generated summary",
            )
        )

    assert exc_info.value.code is PublicationProviderFailureCode.INVALID_RESPONSE


def test_updates_metadata_only_after_exact_head_read_and_write_fences() -> None:
    updated_response = {**_pull_response(), "title": "Updated", "body": "Updated body"}
    provider, runner = _provider(
        _completed(_pull_response()),
        _completed(updated_response),
    )

    updated = provider.update_pull_request(
        UpdatePublicationPullRequest(
            repository=_REPOSITORY,
            number=7,
            expected_head_sha=_HEAD,
            expected_title="Example change",
            expected_body="Generated summary",
            title="Updated",
            body="Updated body",
        )
    )

    assert updated.title == "Updated"
    assert runner.calls[0][0][-1] == "repos/example/project/pulls/7"
    assert runner.calls[1][0][-3:] == ("repos/example/project/pulls/7", "--input", "-")
    assert json.loads(runner.calls[1][1] or b"") == {"body": "Updated body", "title": "Updated"}


def test_wrong_head_blocks_metadata_write_before_patch() -> None:
    provider, runner = _provider(_completed(_pull_response()))

    with pytest.raises(PublicationProviderError) as exc_info:
        provider.update_pull_request(
            UpdatePublicationPullRequest(
                repository=_REPOSITORY,
                number=7,
                expected_head_sha=_OTHER_HEAD,
                expected_title="Example change",
                expected_body="Generated summary",
                title="Updated",
                body="Updated body",
            )
        )

    assert exc_info.value.code is PublicationProviderFailureCode.CONFLICT
    assert len(runner.calls) == 1


def test_changed_metadata_blocks_update_before_patch() -> None:
    provider, runner = _provider(_completed({**_pull_response(), "body": "User-edited body"}))

    with pytest.raises(PublicationProviderError) as exc_info:
        provider.update_pull_request(
            UpdatePublicationPullRequest(
                repository=_REPOSITORY,
                number=7,
                expected_head_sha=_HEAD,
                expected_title="Example change",
                expected_body="Generated summary",
                title="Updated",
                body="Updated body",
            )
        )

    assert exc_info.value.code is PublicationProviderFailureCode.CONFLICT
    assert len(runner.calls) == 1


def test_ready_transition_uses_only_named_graphql_document_and_reads_back() -> None:
    mutation_response = {
        "data": {"markPullRequestReadyForReview": {"pullRequest": {"id": "PR_node_7", "isDraft": False}}}
    }
    provider, runner = _provider(
        _completed(_pull_response()),
        _completed(mutation_response),
        _completed(_pull_response(draft=False)),
    )

    ready = provider.set_pull_request_draft_state(
        SetPublicationPullRequestDraftState(
            repository=_REPOSITORY,
            number=7,
            node_id="PR_node_7",
            expected_head_sha=_HEAD,
            draft=False,
        )
    )

    arguments, input_bytes, _ = runner.calls[1]
    payload = json.loads(input_bytes or b"")
    assert ready.draft is False
    assert arguments == ("gh", "api", "graphql", "--method", "POST", "--input", "-")
    assert payload["operationName"] == "MarkPullRequestReadyForReview"
    assert "markPullRequestReadyForReview" in payload["query"]
    assert "mergePullRequest" not in payload["query"]
    assert payload["variables"] == {"pullRequestId": "PR_node_7"}


def test_draft_transition_uses_only_named_graphql_document_and_reads_back() -> None:
    mutation_response = {"data": {"convertPullRequestToDraft": {"pullRequest": {"id": "PR_node_7", "isDraft": True}}}}
    provider, runner = _provider(
        _completed(_pull_response(draft=False)),
        _completed(mutation_response),
        _completed(_pull_response()),
    )

    draft = provider.set_pull_request_draft_state(
        SetPublicationPullRequestDraftState(
            repository=_REPOSITORY,
            number=7,
            node_id="PR_node_7",
            expected_head_sha=_HEAD,
            draft=True,
        )
    )

    arguments, input_bytes, _ = runner.calls[1]
    payload = json.loads(input_bytes or b"")
    assert draft.draft is True
    assert arguments == ("gh", "api", "graphql", "--method", "POST", "--input", "-")
    assert payload["operationName"] == "ConvertPullRequestToDraft"
    assert "convertPullRequestToDraft" in payload["query"]
    assert "mergePullRequest" not in payload["query"]
    assert payload["variables"] == {"pullRequestId": "PR_node_7"}


def test_wrong_node_id_blocks_draft_state_mutation() -> None:
    provider, runner = _provider(_completed(_pull_response()))

    with pytest.raises(PublicationProviderError) as exc_info:
        provider.set_pull_request_draft_state(
            SetPublicationPullRequestDraftState(
                repository=_REPOSITORY,
                number=7,
                node_id="PR_wrong",
                expected_head_sha=_HEAD,
                draft=False,
            )
        )

    assert exc_info.value.code is PublicationProviderFailureCode.CONFLICT
    assert len(runner.calls) == 1


@pytest.mark.parametrize(
    ("stderr", "expected_code", "retry_safe"),
    [
        (b"HTTP 401: Bad credentials", PublicationProviderFailureCode.AUTHENTICATION_REQUIRED, False),
        (b"HTTP 429: rate limit exceeded", PublicationProviderFailureCode.RATE_LIMITED, True),
        (b"HTTP 422: pull request already exists", PublicationProviderFailureCode.CONFLICT, False),
    ],
)
def test_command_failures_map_to_typed_provider_failures(
    stderr: bytes,
    expected_code: PublicationProviderFailureCode,
    *,
    retry_safe: bool,
) -> None:
    provider, _ = _provider(_completed({}, returncode=1, stderr=stderr))

    with pytest.raises(PublicationProviderError) as exc_info:
        provider.create_draft_pull_request(
            CreateDraftPublicationPullRequest(
                repository=_REPOSITORY,
                head_branch="owlbear/change/example",
                head_sha=_HEAD,
                base_branch="main",
                title="Example change",
                body="Generated summary",
            )
        )

    assert exc_info.value.code is expected_code
    assert exc_info.value.retry_safe is retry_safe


def test_write_timeout_and_invalid_success_are_response_unknown() -> None:
    timeout = subprocess.TimeoutExpired(cmd=("gh", "api"), timeout=12.5)
    provider, _ = _provider(timeout)
    request = CreateDraftPublicationPullRequest(
        repository=_REPOSITORY,
        head_branch="owlbear/change/example",
        head_sha=_HEAD,
        base_branch="main",
        title="Example change",
        body="Generated summary",
    )

    with pytest.raises(PublicationProviderError) as timeout_info:
        provider.create_draft_pull_request(request)
    assert timeout_info.value.code is PublicationProviderFailureCode.RESPONSE_UNKNOWN
    assert timeout_info.value.retry_safe is False

    invalid = subprocess.CompletedProcess(args=(), returncode=0, stdout=b"not-json", stderr=b"")
    provider, _ = _provider(invalid)
    with pytest.raises(PublicationProviderError) as invalid_info:
        provider.create_draft_pull_request(request)
    assert invalid_info.value.code is PublicationProviderFailureCode.RESPONSE_UNKNOWN


def test_read_timeout_and_malformed_response_are_safe_typed_failures() -> None:
    timeout = subprocess.TimeoutExpired(cmd=("gh", "api"), timeout=12.5)
    provider, _ = _provider(timeout)
    with pytest.raises(PublicationProviderError) as timeout_info:
        provider.read_repository(_REPOSITORY)
    assert timeout_info.value.code is PublicationProviderFailureCode.TIMEOUT
    assert timeout_info.value.retry_safe is True

    provider, _ = _provider(_completed({"full_name": _REPOSITORY}))
    with pytest.raises(PublicationProviderError) as invalid_info:
        provider.read_repository(_REPOSITORY)
    assert invalid_info.value.code is PublicationProviderFailureCode.INVALID_RESPONSE
    assert invalid_info.value.retry_safe is True

    invalid_json = subprocess.CompletedProcess(args=(), returncode=0, stdout=b"not-json", stderr=b"")
    provider, _ = _provider(invalid_json)
    with pytest.raises(PublicationProviderError) as invalid_json_info:
        provider.read_repository(_REPOSITORY)
    assert invalid_json_info.value.code is PublicationProviderFailureCode.INVALID_RESPONSE
    assert invalid_json_info.value.retry_safe is True
