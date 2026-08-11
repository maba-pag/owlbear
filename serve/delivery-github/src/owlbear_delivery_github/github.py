"""Fixed-operation GitHub CLI publication provider."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import NoReturn, cast
from urllib.parse import quote, urlencode

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from owlbear_delivery import (
    CreateDraftPublicationPullRequest,
    FindPublicationPullRequest,
    ObservePublicationChecks,
    PublicationCheck,
    PublicationCheckKind,
    PublicationCheckSnapshot,
    PublicationProviderError,
    PublicationProviderFailureCode,
    PublicationPullRequest,
    PublicationRepository,
    SetPublicationPullRequestDraftState,
    UpdatePublicationPullRequest,
)

_DEFAULT_TIMEOUT_SECONDS = 30.0
_API_VERSION = "2026-03-10"
_READY_MUTATION = """mutation MarkPullRequestReadyForReview($pullRequestId: ID!) {
  markPullRequestReadyForReview(input: {pullRequestId: $pullRequestId}) {
    pullRequest { id isDraft }
  }
}"""
_DRAFT_MUTATION = """mutation ConvertPullRequestToDraft($pullRequestId: ID!) {
  convertPullRequestToDraft(input: {pullRequestId: $pullRequestId}) {
    pullRequest { id isDraft }
  }
}"""
_OBSERVE_CHECKS_QUERY = """query ObservePublicationChecks(
    $owner: String!, $name: String!, $number: Int!, $cursor: String
) {
    repository(owner: $owner, name: $name) {
        nameWithOwner
        pullRequest(number: $number) {
            number
            headRefOid
            commits(last: 1) {
                nodes {
                    oid
                    statusCheckRollup {
                        state
                        contexts(first: 100, after: $cursor) {
                            totalCount
                            pageInfo { hasNextPage endCursor }
                            nodes {
                                __typename
                                ... on CheckRun {
                                    id name status conclusion startedAt completedAt detailsUrl
                                    isRequired(pullRequestNumber: $number)
                                }
                                ... on StatusContext {
                                    id context state createdAt updatedAt targetUrl
                                    isRequired(pullRequestNumber: $number)
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}"""
_MAX_OBSERVED_CHECKS = 1_000


@dataclass
class _CheckObservationState:
    checks: list[PublicationCheck] = field(default_factory=list)
    seen_check_ids: set[str] = field(default_factory=set)
    rollup_state: str | None = None
    total_count: int | None = None


_CommandRunner = Callable[[tuple[str, ...], bytes | None, float], subprocess.CompletedProcess[bytes]]
type _JsonValue = bool | int | float | str | list[_JsonValue] | dict[str, _JsonValue] | None
type _JsonObject = dict[str, _JsonValue]


class _GitHubModel(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)


class _RepositoryResponse(_GitHubModel):
    full_name: str
    default_branch: str


class _PullRef(_GitHubModel):
    ref: str
    sha: str


class _PullResponse(_GitHubModel):
    number: int = Field(gt=0)
    node_id: str = Field(min_length=1)
    head: _PullRef
    base: _PullRef
    title: str = Field(min_length=1)
    body: str | None
    draft: bool
    state: str
    merged: bool
    merge_commit_sha: str | None


class _PullListItem(_GitHubModel):
    number: int = Field(gt=0)


class _DraftStateResponse(_GitHubModel):
    id: str = Field(min_length=1)
    is_draft: bool = Field(alias="isDraft")


class _CheckPageInfo(_GitHubModel):
    has_next_page: bool = Field(alias="hasNextPage")
    end_cursor: str | None = Field(alias="endCursor")


class _CheckContextsResponse(_GitHubModel):
    nodes: list[dict[str, _JsonValue] | None]
    page_info: _CheckPageInfo = Field(alias="pageInfo")
    total_count: int = Field(ge=0, alias="totalCount")


class _StatusRollupResponse(_GitHubModel):
    state: str = Field(min_length=1)
    contexts: _CheckContextsResponse


class _CheckCommitResponse(_GitHubModel):
    oid: str = Field(pattern=r"^[0-9a-f]{40}$")
    status_check_rollup: _StatusRollupResponse | None = Field(alias="statusCheckRollup")


class _CheckCommitConnection(_GitHubModel):
    nodes: list[_CheckCommitResponse | None]


class _CheckPullRequestResponse(_GitHubModel):
    number: int = Field(gt=0)
    head_ref_oid: str = Field(pattern=r"^[0-9a-f]{40}$", alias="headRefOid")
    commits: _CheckCommitConnection


class _CheckRepositoryResponse(_GitHubModel):
    name_with_owner: str = Field(min_length=3, alias="nameWithOwner")
    pull_request: _CheckPullRequestResponse | None = Field(alias="pullRequest")


class _CheckQueryData(_GitHubModel):
    repository: _CheckRepositoryResponse | None


class _CheckQueryResponse(_GitHubModel):
    data: _CheckQueryData


class _CheckRunResponse(_GitHubModel):
    node_id: str = Field(min_length=1, alias="id")
    name: str = Field(min_length=1)
    status: str = Field(min_length=1)
    conclusion: str | None
    started_at: str | None = Field(alias="startedAt")
    completed_at: str | None = Field(alias="completedAt")
    details_url: str | None = Field(alias="detailsUrl")
    required: bool = Field(alias="isRequired")


class _StatusContextResponse(_GitHubModel):
    node_id: str = Field(min_length=1, alias="id")
    context: str = Field(min_length=1)
    state: str = Field(min_length=1)
    created_at: str = Field(min_length=1, alias="createdAt")
    updated_at: str = Field(min_length=1, alias="updatedAt")
    target_url: str | None = Field(alias="targetUrl")
    required: bool = Field(alias="isRequired")


_PULL_LIST = TypeAdapter(list[_PullListItem])


def _subprocess_runner(
    arguments: tuple[str, ...],
    input_bytes: bytes | None,
    timeout_seconds: float,
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(  # noqa: S603 - fixed gh executable and code-owned argument vectors.
        arguments,
        check=False,
        capture_output=True,
        input=input_bytes,
        timeout=timeout_seconds,
    )


class GitHubCliPublicationProvider:
    """Execute only Delivery's fixed GitHub publication operations through ``gh api``."""

    def __init__(
        self,
        *,
        timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS,
        runner: _CommandRunner = _subprocess_runner,
    ) -> None:
        if timeout_seconds <= 0:
            message = "GitHub CLI timeout must be positive"
            raise ValueError(message)
        self._timeout_seconds = timeout_seconds
        self._runner = runner

    def read_repository(self, repository: str) -> PublicationRepository:
        """Read and verify one exact GitHub repository identity."""
        payload = self._rest("read_repository", "GET", _repository_endpoint(repository))
        response = self._validate(_RepositoryResponse, payload, "read_repository", retry_safe=True)
        if response.full_name.casefold() != repository.casefold():
            self._invalid_response(
                "read_repository",
                "GitHub returned another repository identity",
                retry_safe=True,
            )
        return PublicationRepository(repository=response.full_name, default_branch=response.default_branch)

    def read_pull_request(self, repository: str, number: int) -> PublicationPullRequest:
        """Read one exact GitHub pull request."""
        operation = "read_pull_request"
        payload = self._rest(operation, "GET", f"{_repository_endpoint(repository)}/pulls/{number}")
        pull_request = self._pull_request(repository, payload, operation, retry_safe=True)
        if pull_request.number != number:
            self._invalid_response(operation, "GitHub returned another pull request identity", retry_safe=True)
        return pull_request

    def find_pull_request(self, request: FindPublicationPullRequest) -> PublicationPullRequest | None:
        """Find the unique pull request for one exact head/base identity."""
        owner, _ = request.repository.split("/", maxsplit=1)
        query = urlencode(
            {
                "state": "all",
                "head": f"{owner}:{request.head_branch}",
                "base": request.base_branch,
                "per_page": 100,
            }
        )
        operation = "find_pull_request"
        payload = self._rest(operation, "GET", f"{_repository_endpoint(request.repository)}/pulls?{query}")
        try:
            matches = _PULL_LIST.validate_python(payload)
        except ValidationError as exc:
            self._invalid_response(
                operation,
                "GitHub returned an invalid pull request list",
                retry_safe=True,
                cause=exc,
            )
        if len(matches) > 1:
            raise PublicationProviderError(
                PublicationProviderFailureCode.CONFLICT,
                operation,
                "multiple pull requests match the publication identity",
                retry_safe=False,
            )
        return self.read_pull_request(request.repository, matches[0].number) if matches else None

    def create_draft_pull_request(self, request: CreateDraftPublicationPullRequest) -> PublicationPullRequest:
        """Create one draft pull request using a fixed REST payload."""
        operation = "create_draft_pull_request"
        payload = self._rest(
            operation,
            "POST",
            f"{_repository_endpoint(request.repository)}/pulls",
            body={
                "title": request.title,
                "body": request.body,
                "head": request.head_branch,
                "base": request.base_branch,
                "draft": True,
            },
            write=True,
        )
        pull_request = self._pull_request(request.repository, payload, operation)
        if (
            pull_request.head_branch != request.head_branch
            or pull_request.head_sha != request.head_sha
            or pull_request.base_branch != request.base_branch
            or not pull_request.draft
            or pull_request.state != "open"
            or pull_request.merged
        ):
            self._invalid_response(operation, "created pull request differs from the requested identity")
        return pull_request

    def update_pull_request(self, request: UpdatePublicationPullRequest) -> PublicationPullRequest:
        """Update fixed generated metadata after exact-head read fences."""
        current = self._require_open_head(
            request.repository,
            request.number,
            request.expected_head_sha,
            "update_pull_request",
        )
        if current.title != request.expected_title or current.body != request.expected_body:
            self._conflict("update_pull_request", "pull request metadata differs from the update fence")
        payload = self._rest(
            "update_pull_request",
            "PATCH",
            f"{_repository_endpoint(request.repository)}/pulls/{request.number}",
            body={"title": request.title, "body": request.body},
            write=True,
        )
        updated = self._pull_request(request.repository, payload, "update_pull_request")
        self._require_matching_head(updated, request.expected_head_sha, "update_pull_request")
        if updated.title != request.title or updated.body != request.body:
            self._invalid_response(
                "update_pull_request",
                "GitHub did not apply the requested pull request metadata",
            )
        return updated

    def set_pull_request_draft_state(
        self,
        request: SetPublicationPullRequestDraftState,
    ) -> PublicationPullRequest:
        """Run one code-owned draft-state mutation after exact identity fences."""
        operation = "set_pull_request_draft_state"
        current = self._require_open_head(request.repository, request.number, request.expected_head_sha, operation)
        if current.node_id != request.node_id:
            self._conflict(operation, "pull request node identity differs from the update fence")
        if current.draft == request.draft:
            return current
        mutation = _DRAFT_MUTATION if request.draft else _READY_MUTATION
        operation_name = "ConvertPullRequestToDraft" if request.draft else "MarkPullRequestReadyForReview"
        payload = self._graphql(
            operation,
            {
                "query": mutation,
                "operationName": operation_name,
                "variables": {"pullRequestId": request.node_id},
            },
        )
        state = self._draft_state(payload, operation_name, operation)
        if state.id != request.node_id or state.is_draft != request.draft:
            self._invalid_response(operation, "GitHub returned an inconsistent draft-state mutation result")
        updated = self.read_pull_request(request.repository, request.number)
        self._require_matching_head(updated, request.expected_head_sha, operation)
        if updated.draft != request.draft:
            self._invalid_response(operation, "GitHub did not apply the requested draft state")
        return updated

    def observe_checks(self, request: ObservePublicationChecks) -> PublicationCheckSnapshot:
        """Read a complete bounded check rollup for one exact pull-request head."""
        operation = "observe_checks"
        owner, name = request.repository.split("/", maxsplit=1)
        cursor: str | None = None
        seen_cursors: set[str] = set()
        state = _CheckObservationState()
        while True:
            rollup = self._observe_check_page(request, owner, name, cursor, operation)
            if rollup is None:
                if cursor is not None:
                    self._invalid_response(
                        operation,
                        "GitHub removed the check rollup during pagination",
                        retry_safe=True,
                    )
                break
            self._record_check_page(state, rollup, request.expected_head_sha, operation)
            next_cursor = self._next_check_cursor(state, rollup.contexts.page_info, seen_cursors, operation)
            if next_cursor is None:
                break
            seen_cursors.add(next_cursor)
            cursor = next_cursor
        if state.total_count is not None and len(state.checks) != state.total_count:
            self._invalid_response(operation, "GitHub returned an incomplete check observation", retry_safe=True)
        try:
            return PublicationCheckSnapshot(
                repository=request.repository,
                number=request.number,
                head_sha=request.expected_head_sha,
                rollup_state=state.rollup_state,
                checks=tuple(state.checks),
            )
        except ValidationError as exc:
            self._invalid_response(
                operation,
                "GitHub returned inconsistent check identities",
                retry_safe=False,
                cause=exc,
            )

    def _record_check_page(
        self,
        state: _CheckObservationState,
        rollup: _StatusRollupResponse,
        head_sha: str,
        operation: str,
    ) -> None:
        rollup_state = rollup.state.casefold()
        if state.rollup_state is not None and state.rollup_state != rollup_state:
            self._invalid_response(operation, "GitHub check rollup changed during pagination", retry_safe=True)
        if state.total_count is not None and state.total_count != rollup.contexts.total_count:
            self._invalid_response(operation, "GitHub check count changed during pagination", retry_safe=True)
        page_checks = self._publication_checks(rollup.contexts.nodes, head_sha, operation)
        page_check_ids = {check.check_id for check in page_checks}
        if len(page_check_ids) != len(page_checks) or state.seen_check_ids.intersection(page_check_ids):
            self._invalid_response(operation, "GitHub returned duplicate check identities", retry_safe=True)
        state.rollup_state = rollup_state
        state.total_count = rollup.contexts.total_count
        state.checks.extend(page_checks)
        state.seen_check_ids.update(page_check_ids)

    def _next_check_cursor(
        self,
        state: _CheckObservationState,
        page_info: _CheckPageInfo,
        seen_cursors: set[str],
        operation: str,
    ) -> str | None:
        if len(state.checks) > _MAX_OBSERVED_CHECKS or (
            len(state.checks) == _MAX_OBSERVED_CHECKS and page_info.has_next_page
        ):
            self._invalid_response(
                operation,
                "GitHub check observation exceeds the bounded limit",
                retry_safe=False,
            )
        if not page_info.has_next_page:
            return None
        next_cursor = page_info.end_cursor
        if not next_cursor or next_cursor in seen_cursors:
            self._invalid_response(operation, "GitHub returned an invalid check pagination cursor", retry_safe=True)
        return next_cursor

    def _observe_check_page(
        self,
        request: ObservePublicationChecks,
        owner: str,
        name: str,
        cursor: str | None,
        operation: str,
    ) -> _StatusRollupResponse | None:
        payload = self._graphql_query(
            operation,
            {
                "query": _OBSERVE_CHECKS_QUERY,
                "operationName": "ObservePublicationChecks",
                "variables": {"owner": owner, "name": name, "number": request.number, "cursor": cursor},
            },
        )
        response = self._validate(_CheckQueryResponse, payload, operation, retry_safe=True)
        commit = self._check_page_identity(response, request, operation)
        return commit.status_check_rollup

    def _check_page_identity(
        self,
        response: _CheckQueryResponse,
        request: ObservePublicationChecks,
        operation: str,
    ) -> _CheckCommitResponse:
        repository = response.data.repository
        if repository is None:
            raise PublicationProviderError(
                PublicationProviderFailureCode.NOT_FOUND,
                operation,
                "publication repository was not found",
                retry_safe=False,
            )
        if repository.name_with_owner.casefold() != request.repository.casefold():
            self._invalid_response(operation, "GitHub returned another repository identity", retry_safe=True)
        pull_request = repository.pull_request
        if pull_request is None:
            raise PublicationProviderError(
                PublicationProviderFailureCode.NOT_FOUND,
                operation,
                "publication pull request was not found",
                retry_safe=False,
            )
        if pull_request.number != request.number:
            self._invalid_response(operation, "GitHub returned another pull request identity", retry_safe=True)
        if pull_request.head_ref_oid != request.expected_head_sha:
            self._conflict(operation, "pull request head differs from the check observation fence")
        commits = tuple(commit for commit in pull_request.commits.nodes if commit is not None)
        if len(commits) != 1 or commits[0].oid != request.expected_head_sha:
            self._invalid_response(
                operation,
                "GitHub check rollup is not bound to the pull request head",
                retry_safe=True,
            )
        return commits[0]

    def _publication_checks(
        self,
        nodes: list[dict[str, _JsonValue] | None],
        head_sha: str,
        operation: str,
    ) -> tuple[PublicationCheck, ...]:
        checks: list[PublicationCheck] = []
        for node in nodes:
            if node is None:
                self._invalid_response(operation, "GitHub returned an empty check context", retry_safe=True)
            kind = node.get("__typename")
            if kind == "CheckRun":
                response = self._validate(_CheckRunResponse, node, operation, retry_safe=True)
                started_at = self._timestamp(response.started_at, operation)
                completed_at = self._timestamp(response.completed_at, operation)
                checks.append(
                    PublicationCheck(
                        check_id=response.node_id,
                        kind=PublicationCheckKind.CHECK_RUN,
                        name=response.name,
                        head_sha=head_sha,
                        status=response.status.casefold(),
                        conclusion=response.conclusion.casefold() if response.conclusion else None,
                        required=response.required,
                        started_at=started_at,
                        completed_at=completed_at,
                        duration_seconds=self._duration(started_at, completed_at, operation),
                        details_url=response.details_url,
                    )
                )
            elif kind == "StatusContext":
                response = self._validate(_StatusContextResponse, node, operation, retry_safe=True)
                created_at = self._timestamp(response.created_at, operation)
                state = response.state.casefold()
                completed_at = (
                    self._timestamp(response.updated_at, operation)
                    if state in {"error", "failure", "success"}
                    else None
                )
                checks.append(
                    PublicationCheck(
                        check_id=response.node_id,
                        kind=PublicationCheckKind.STATUS_CONTEXT,
                        name=response.context,
                        head_sha=head_sha,
                        status=state,
                        conclusion=state if completed_at is not None else None,
                        required=response.required,
                        started_at=created_at,
                        completed_at=completed_at,
                        duration_seconds=self._duration(created_at, completed_at, operation),
                        details_url=response.target_url,
                    )
                )
            else:
                self._invalid_response(operation, "GitHub returned an unknown check context type", retry_safe=True)
        return tuple(checks)

    def _timestamp(self, value: str | None, operation: str) -> datetime | None:
        if value is None:
            return None
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError as exc:
            self._invalid_response(operation, "GitHub returned an invalid check timestamp", retry_safe=True, cause=exc)
        if parsed.tzinfo is None:
            self._invalid_response(operation, "GitHub returned a timezone-naive check timestamp", retry_safe=True)
        return parsed

    def _duration(
        self,
        started_at: datetime | None,
        completed_at: datetime | None,
        operation: str,
    ) -> float | None:
        if started_at is None or completed_at is None:
            return None
        duration = (completed_at - started_at).total_seconds()
        if duration < 0:
            self._invalid_response(operation, "GitHub returned an invalid check duration", retry_safe=True)
        return duration

    def _require_open_head(
        self,
        repository: str,
        number: int,
        expected_head_sha: str,
        operation: str,
    ) -> PublicationPullRequest:
        pull_request = self.read_pull_request(repository, number)
        self._require_matching_head(pull_request, expected_head_sha, operation)
        if pull_request.state != "open" or pull_request.merged:
            self._conflict(operation, "pull request is not open for publication updates")
        return pull_request

    def _require_matching_head(
        self,
        pull_request: PublicationPullRequest,
        expected_head_sha: str,
        operation: str,
    ) -> None:
        if pull_request.head_sha != expected_head_sha:
            self._conflict(operation, "pull request head differs from the update fence")

    def _rest(
        self,
        operation: str,
        method: str,
        endpoint: str,
        *,
        body: _JsonObject | None = None,
        write: bool = False,
    ) -> _JsonValue:
        arguments = (
            "gh",
            "api",
            "--method",
            method,
            "--header",
            "Accept: application/vnd.github+json",
            "--header",
            f"X-GitHub-Api-Version: {_API_VERSION}",
            endpoint,
        )
        if body is not None:
            arguments = (*arguments, "--input", "-")
        return self._execute(operation, arguments, body, write=write)

    def _graphql(self, operation: str, body: _JsonObject) -> _JsonValue:
        arguments = ("gh", "api", "graphql", "--method", "POST", "--input", "-")
        return self._execute(operation, arguments, body, write=True)

    def _graphql_query(self, operation: str, body: _JsonObject) -> _JsonValue:
        arguments = ("gh", "api", "graphql", "--method", "POST", "--input", "-")
        payload = self._execute(operation, arguments, body, write=False)
        if not isinstance(payload, dict) or "errors" in payload:
            self._invalid_response(operation, "GitHub returned a failed GraphQL query", retry_safe=True)
        return payload

    def _execute(
        self,
        operation: str,
        arguments: tuple[str, ...],
        body: _JsonObject | None,
        *,
        write: bool,
    ) -> _JsonValue:
        input_bytes = None if body is None else json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        try:
            completed = self._runner(arguments, input_bytes, self._timeout_seconds)
        except FileNotFoundError as exc:
            raise PublicationProviderError(
                PublicationProviderFailureCode.UNAVAILABLE,
                operation,
                "GitHub CLI executable is unavailable",
                retry_safe=False,
            ) from exc
        except subprocess.TimeoutExpired as exc:
            code = PublicationProviderFailureCode.RESPONSE_UNKNOWN if write else PublicationProviderFailureCode.TIMEOUT
            raise PublicationProviderError(
                code,
                operation,
                "GitHub CLI operation timed out",
                retry_safe=not write,
            ) from exc
        if completed.returncode != 0:
            self._raise_command_failure(operation, completed.stderr.decode(errors="replace"), write=write)
        try:
            return cast("_JsonValue", json.loads(completed.stdout))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            code = (
                PublicationProviderFailureCode.RESPONSE_UNKNOWN
                if write
                else PublicationProviderFailureCode.INVALID_RESPONSE
            )
            raise PublicationProviderError(
                code,
                operation,
                "GitHub CLI returned invalid JSON",
                retry_safe=not write,
            ) from exc

    @staticmethod
    def _raise_command_failure(operation: str, stderr: str, *, write: bool) -> None:
        normalized = stderr.casefold()
        if "rate limit" in normalized or "http 429" in normalized:
            code = PublicationProviderFailureCode.RATE_LIMITED
            retry_safe = True
        elif "gh auth login" in normalized or "http 401" in normalized or "bad credentials" in normalized:
            code = PublicationProviderFailureCode.AUTHENTICATION_REQUIRED
            retry_safe = False
        elif "http 404" in normalized or "not found" in normalized or "could not resolve to" in normalized:
            code = PublicationProviderFailureCode.NOT_FOUND
            retry_safe = False
        elif "http 409" in normalized or "http 422" in normalized or "already exists" in normalized:
            code = PublicationProviderFailureCode.CONFLICT
            retry_safe = False
        elif write:
            code = PublicationProviderFailureCode.RESPONSE_UNKNOWN
            retry_safe = False
        else:
            code = PublicationProviderFailureCode.UNAVAILABLE
            retry_safe = True
        raise PublicationProviderError(
            code,
            operation,
            "GitHub CLI operation failed",
            retry_safe=retry_safe,
        )

    def _pull_request(
        self,
        repository: str,
        payload: _JsonValue,
        operation: str,
        *,
        retry_safe: bool = False,
    ) -> PublicationPullRequest:
        response = self._validate(_PullResponse, payload, operation, retry_safe=retry_safe)
        try:
            return PublicationPullRequest(
                repository=repository,
                number=response.number,
                node_id=response.node_id,
                head_branch=response.head.ref,
                head_sha=response.head.sha,
                base_branch=response.base.ref,
                title=response.title,
                body=response.body or "",
                draft=response.draft,
                state=response.state,
                merged=response.merged,
                merge_commit_sha=response.merge_commit_sha,
            )
        except ValidationError as exc:
            self._invalid_response(
                operation,
                "GitHub returned invalid pull request state",
                retry_safe=retry_safe,
                cause=exc,
            )

    def _validate[Model: _GitHubModel](
        self,
        model: type[Model],
        payload: _JsonValue,
        operation: str,
        *,
        retry_safe: bool = False,
    ) -> Model:
        try:
            return model.model_validate(payload)
        except ValidationError as exc:
            self._invalid_response(
                operation,
                "GitHub returned an invalid response",
                retry_safe=retry_safe,
                cause=exc,
            )

    def _draft_state(
        self,
        payload: _JsonValue,
        operation_name: str,
        operation: str,
    ) -> _DraftStateResponse:
        if not isinstance(payload, dict) or "errors" in payload:
            self._invalid_response(operation, "GitHub returned a failed GraphQL mutation")
        data = payload.get("data")
        if not isinstance(data, dict):
            self._invalid_response(operation, "GitHub omitted GraphQL mutation data")
        mutation = data.get(operation_name[0].lower() + operation_name[1:])
        if not isinstance(mutation, dict):
            self._invalid_response(operation, "GitHub omitted the draft-state mutation result")
        return self._validate(_DraftStateResponse, mutation.get("pullRequest"), operation)

    @staticmethod
    def _invalid_response(
        operation: str,
        detail: str,
        *,
        retry_safe: bool = False,
        cause: Exception | None = None,
    ) -> NoReturn:
        error = PublicationProviderError(
            PublicationProviderFailureCode.INVALID_RESPONSE,
            operation,
            detail,
            retry_safe=retry_safe,
        )
        raise error from cause

    @staticmethod
    def _conflict(operation: str, detail: str) -> NoReturn:
        raise PublicationProviderError(
            PublicationProviderFailureCode.CONFLICT,
            operation,
            detail,
            retry_safe=False,
        )


def _repository_endpoint(repository: str) -> str:
    owner, name = repository.split("/", maxsplit=1)
    return f"repos/{quote(owner, safe='')}/{quote(name, safe='')}"
