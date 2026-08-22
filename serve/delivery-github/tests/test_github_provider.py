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
    ObservePublicationChecks,
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


@dataclass(frozen=True)
class _CheckResponseOptions:
    head: str = _HEAD
    has_next_page: bool = False
    end_cursor: str | None = None
    rollup: bool = True
    rollup_state: str = "SUCCESS"
    total_count: int | None = None
    repository: object = ...


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
        "merged_at": None,
        "merged_by": None,
    }


def _check_response(
    nodes: list[object],
    *,
    options: _CheckResponseOptions | None = None,
) -> dict[str, object]:
    options = options or _CheckResponseOptions()
    status_check_rollup: object = None
    if options.rollup:
        status_check_rollup = {
            "state": options.rollup_state,
            "contexts": {
                "totalCount": len(nodes) if options.total_count is None else options.total_count,
                "pageInfo": {"hasNextPage": options.has_next_page, "endCursor": options.end_cursor},
                "nodes": nodes,
            },
        }
    repository_response = (
        {
            "nameWithOwner": _REPOSITORY,
            "pullRequest": {
                "number": 7,
                "headRefOid": options.head,
                "commits": {"nodes": [{"commit": {"oid": options.head, "statusCheckRollup": status_check_rollup}}]},
            },
        }
        if options.repository is ...
        else options.repository
    )
    return {
        "data": {
            "repository": repository_response,
        }
    }


def _check_run(check_id: str = "CR_1") -> dict[str, object]:
    return {
        "__typename": "CheckRun",
        "id": check_id,
        "name": "test",
        "status": "COMPLETED",
        "conclusion": "SUCCESS",
        "startedAt": "2026-08-11T10:00:00Z",
        "completedAt": "2026-08-11T10:02:00Z",
        "detailsUrl": None,
        "isRequired": True,
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


def test_reads_merged_pull_request_evidence_from_one_response() -> None:
    response = {
        **_pull_response(draft=False),
        "state": "closed",
        "merged": True,
        "merged_at": "2026-08-11T10:02:00Z",
        "merged_by": {"login": "octocat"},
    }
    provider, _ = _provider(_completed(response))

    pull_request = provider.read_pull_request(_REPOSITORY, 7)

    assert pull_request.merged_at is not None
    assert pull_request.merged_at.isoformat() == "2026-08-11T10:02:00+00:00"
    assert pull_request.merged_by_login == "octocat"


@pytest.mark.parametrize("missing_key", ["merged_at", "merged_by"])
def test_pull_request_read_rejects_missing_merge_evidence_key(missing_key: str) -> None:
    response = _pull_response()
    del response[missing_key]
    provider, _ = _provider(_completed(response))

    with pytest.raises(PublicationProviderError) as exc_info:
        provider.read_pull_request(_REPOSITORY, 7)

    assert exc_info.value.code is PublicationProviderFailureCode.INVALID_RESPONSE


def test_pull_request_read_accepts_open_response_without_merge_commit_sha() -> None:
    response = _pull_response()
    del response["merge_commit_sha"]
    provider, _ = _provider(_completed(response))

    pull_request = provider.read_pull_request(_REPOSITORY, 7)

    assert pull_request.merge_commit_sha is None


@pytest.mark.parametrize(
    ("merged_at", "merge_commit_sha"),
    [
        (None, _OTHER_HEAD),
        ("2026-08-11T10:02:00Z", None),
        ("2026-08-11T10:02:00", _OTHER_HEAD),
    ],
)
def test_pull_request_read_rejects_invalid_merged_evidence(
    merged_at: str | None,
    merge_commit_sha: str | None,
) -> None:
    response = {
        **_pull_response(draft=False),
        "state": "closed",
        "merged": True,
        "merged_at": merged_at,
        "merge_commit_sha": merge_commit_sha,
    }
    provider, _ = _provider(_completed(response))

    with pytest.raises(PublicationProviderError) as exc_info:
        provider.read_pull_request(_REPOSITORY, 7)

    assert exc_info.value.code is PublicationProviderFailureCode.INVALID_RESPONSE


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


def test_update_rejects_response_without_requested_metadata() -> None:
    provider, runner = _provider(
        _completed(_pull_response()),
        _completed(_pull_response()),
    )

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

    assert exc_info.value.code is PublicationProviderFailureCode.INVALID_RESPONSE
    assert len(runner.calls) == 2


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


def test_observes_paginated_check_runs_and_status_contexts_with_fixed_query() -> None:
    provider, runner = _provider(
        _completed(
            _check_response(
                [
                    {
                        "__typename": "CheckRun",
                        "id": "CR_1",
                        "name": "test",
                        "status": "COMPLETED",
                        "conclusion": "SUCCESS",
                        "startedAt": "2026-08-11T10:00:00Z",
                        "completedAt": "2026-08-11T10:02:00Z",
                        "detailsUrl": "https://example.test/checks/1",
                        "isRequired": True,
                    }
                ],
                options=_CheckResponseOptions(has_next_page=True, end_cursor="cursor-1", total_count=2),
            )
        ),
        _completed(
            _check_response(
                [
                    {
                        "__typename": "StatusContext",
                        "id": "SC_1",
                        "context": "deployment",
                        "state": "PENDING",
                        "createdAt": "2026-08-11T10:03:00Z",
                        "updatedAt": "2026-08-11T10:03:30Z",
                        "targetUrl": None,
                        "isRequired": False,
                    }
                ],
                options=_CheckResponseOptions(total_count=2),
            )
        ),
    )

    snapshot = provider.observe_checks(
        ObservePublicationChecks(repository=_REPOSITORY, number=7, expected_head_sha=_HEAD)
    )

    assert snapshot.rollup_state == "success"
    assert [(check.kind.value, check.name) for check in snapshot.checks] == [
        ("check_run", "test"),
        ("status_context", "deployment"),
    ]
    assert snapshot.checks[0].status == "completed"
    assert {check.head_sha for check in snapshot.checks} == {_HEAD}
    assert snapshot.checks[0].conclusion == "success"
    assert snapshot.checks[0].duration_seconds == 120
    assert snapshot.checks[1].status == "pending"
    assert snapshot.checks[1].conclusion is None
    assert snapshot.checks[1].completed_at is None
    assert snapshot.checks[1].duration_seconds is None
    assert all(call[0] == ("gh", "api", "graphql", "--method", "POST", "--input", "-") for call in runner.calls)
    payloads = [json.loads(call[1] or b"") for call in runner.calls]
    assert [payload["operationName"] for payload in payloads] == [
        "ObservePublicationChecks",
        "ObservePublicationChecks",
    ]
    assert payloads[0]["variables"] == {
        "owner": "example",
        "name": "project",
        "number": 7,
        "cursor": None,
    }
    assert payloads[1]["variables"]["cursor"] == "cursor-1"
    query = payloads[0]["query"]
    assert "commit {" in query
    assert "isRequired(pullRequestNumber: $number)" in query
    assert "mutation" not in query
    assert "workflowDispatch" not in query
    assert "rerequestCheckSuite" not in query


def test_observes_no_rollup_as_an_empty_snapshot() -> None:
    provider, _ = _provider(_completed(_check_response([], options=_CheckResponseOptions(rollup=False))))

    snapshot = provider.observe_checks(
        ObservePublicationChecks(repository=_REPOSITORY, number=7, expected_head_sha=_HEAD)
    )

    assert snapshot.rollup_state is None
    assert snapshot.checks == ()


def test_check_observation_rejects_head_drift_between_pages() -> None:
    provider, runner = _provider(
        _completed(
            _check_response(
                [_check_run()],
                options=_CheckResponseOptions(has_next_page=True, end_cursor="cursor-1", total_count=1),
            )
        ),
        _completed(_check_response([], options=_CheckResponseOptions(head=_OTHER_HEAD))),
    )

    with pytest.raises(PublicationProviderError) as exc_info:
        provider.observe_checks(ObservePublicationChecks(repository=_REPOSITORY, number=7, expected_head_sha=_HEAD))

    assert exc_info.value.code is PublicationProviderFailureCode.CONFLICT
    assert exc_info.value.retry_safe is False
    assert len(runner.calls) == 2


def test_check_observation_rejects_empty_interior_page_before_another_call() -> None:
    provider, runner = _provider(
        _completed(
            _check_response(
                [],
                options=_CheckResponseOptions(has_next_page=True, end_cursor="cursor-1", total_count=0),
            )
        ),
        _completed(_check_response([])),
    )

    with pytest.raises(PublicationProviderError) as exc_info:
        provider.observe_checks(ObservePublicationChecks(repository=_REPOSITORY, number=7, expected_head_sha=_HEAD))

    assert exc_info.value.code is PublicationProviderFailureCode.INVALID_RESPONSE
    assert exc_info.value.retry_safe is True
    assert "empty check page" in str(exc_info.value)
    assert len(runner.calls) == 1


@pytest.mark.parametrize(
    ("second_response", "detail"),
    [
        (
            _check_response([], options=_CheckResponseOptions(rollup_state="FAILURE", total_count=1)),
            "rollup changed",
        ),
        (_check_response([], options=_CheckResponseOptions(total_count=2)), "count changed"),
    ],
)
def test_check_observation_treats_paginated_rollup_drift_as_retry_safe(
    second_response: dict[str, object],
    detail: str,
) -> None:
    provider, _ = _provider(
        _completed(
            _check_response(
                [_check_run()],
                options=_CheckResponseOptions(has_next_page=True, end_cursor="cursor-1", total_count=1),
            )
        ),
        _completed(second_response),
    )

    with pytest.raises(PublicationProviderError) as exc_info:
        provider.observe_checks(ObservePublicationChecks(repository=_REPOSITORY, number=7, expected_head_sha=_HEAD))

    assert exc_info.value.code is PublicationProviderFailureCode.INVALID_RESPONSE
    assert exc_info.value.retry_safe is True
    assert detail in str(exc_info.value)


def test_check_observation_rejects_incomplete_and_duplicate_pages_as_retry_safe() -> None:
    duplicate = {
        "__typename": "StatusContext",
        "id": "SC_1",
        "context": "deployment",
        "state": "SUCCESS",
        "createdAt": "2026-08-11T10:03:00Z",
        "updatedAt": "2026-08-11T10:03:30Z",
        "targetUrl": None,
        "isRequired": True,
    }
    provider, _ = _provider(_completed(_check_response([], options=_CheckResponseOptions(total_count=1))))
    with pytest.raises(PublicationProviderError) as incomplete_info:
        provider.observe_checks(ObservePublicationChecks(repository=_REPOSITORY, number=7, expected_head_sha=_HEAD))
    assert incomplete_info.value.code is PublicationProviderFailureCode.INVALID_RESPONSE
    assert incomplete_info.value.retry_safe is True

    provider, _ = _provider(
        _completed(_check_response([duplicate, duplicate], options=_CheckResponseOptions(total_count=2)))
    )
    with pytest.raises(PublicationProviderError) as duplicate_info:
        provider.observe_checks(ObservePublicationChecks(repository=_REPOSITORY, number=7, expected_head_sha=_HEAD))
    assert duplicate_info.value.code is PublicationProviderFailureCode.INVALID_RESPONSE
    assert duplicate_info.value.retry_safe is True


@pytest.mark.parametrize("nodes", [[None], [{"__typename": "UnknownCheck", "id": "unknown"}]])
def test_check_observation_rejects_malformed_union_nodes_as_retry_safe(nodes: list[object]) -> None:
    provider, _ = _provider(_completed(_check_response(nodes)))

    with pytest.raises(PublicationProviderError) as exc_info:
        provider.observe_checks(ObservePublicationChecks(repository=_REPOSITORY, number=7, expected_head_sha=_HEAD))

    assert exc_info.value.code is PublicationProviderFailureCode.INVALID_RESPONSE
    assert exc_info.value.retry_safe is True


def test_check_observation_rejects_missing_pagination_cursor_as_retry_safe() -> None:
    provider, _ = _provider(
        _completed(_check_response([], options=_CheckResponseOptions(has_next_page=True, total_count=1)))
    )

    with pytest.raises(PublicationProviderError) as exc_info:
        provider.observe_checks(ObservePublicationChecks(repository=_REPOSITORY, number=7, expected_head_sha=_HEAD))

    assert exc_info.value.code is PublicationProviderFailureCode.INVALID_RESPONSE
    assert exc_info.value.retry_safe is True


def test_status_context_terminal_state_exposes_conclusion_and_duration() -> None:
    status_context = {
        "__typename": "StatusContext",
        "id": "SC_1",
        "context": "deployment",
        "state": "SUCCESS",
        "createdAt": "2026-08-11T10:03:00Z",
        "updatedAt": "2026-08-11T10:03:30Z",
        "targetUrl": None,
        "isRequired": True,
    }
    provider, _ = _provider(_completed(_check_response([status_context])))

    snapshot = provider.observe_checks(
        ObservePublicationChecks(repository=_REPOSITORY, number=7, expected_head_sha=_HEAD)
    )

    assert snapshot.checks[0].status == "success"
    assert snapshot.checks[0].conclusion == "success"
    assert snapshot.checks[0].duration_seconds == 30


def test_check_observation_rejects_invalid_timestamp_as_retry_safe() -> None:
    check_run = {
        "__typename": "CheckRun",
        "id": "CR_1",
        "name": "test",
        "status": "COMPLETED",
        "conclusion": "SUCCESS",
        "startedAt": "not-a-timestamp",
        "completedAt": "2026-08-11T10:02:00Z",
        "detailsUrl": None,
        "isRequired": True,
    }
    provider, _ = _provider(_completed(_check_response([check_run])))

    with pytest.raises(PublicationProviderError) as exc_info:
        provider.observe_checks(ObservePublicationChecks(repository=_REPOSITORY, number=7, expected_head_sha=_HEAD))

    assert exc_info.value.code is PublicationProviderFailureCode.INVALID_RESPONSE
    assert exc_info.value.retry_safe is True


def test_check_observation_rejects_missing_repository_as_terminal_not_found() -> None:
    provider, _ = _provider(_completed(_check_response([], options=_CheckResponseOptions(repository=None))))

    with pytest.raises(PublicationProviderError) as exc_info:
        provider.observe_checks(ObservePublicationChecks(repository=_REPOSITORY, number=7, expected_head_sha=_HEAD))

    assert exc_info.value.code is PublicationProviderFailureCode.NOT_FOUND
    assert exc_info.value.retry_safe is False


def test_graphql_repository_resolution_failure_is_terminal_not_found() -> None:
    provider, _ = _provider(
        _completed(
            {},
            returncode=1,
            stderr=b"Could not resolve to a Repository with the name 'example/project'.",
        )
    )

    with pytest.raises(PublicationProviderError) as exc_info:
        provider.observe_checks(ObservePublicationChecks(repository=_REPOSITORY, number=7, expected_head_sha=_HEAD))

    assert exc_info.value.code is PublicationProviderFailureCode.NOT_FOUND
    assert exc_info.value.retry_safe is False


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
