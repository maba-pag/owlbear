"""Fixed-operation GitHub CLI publication provider."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from typing import cast
from urllib.parse import quote, urlencode

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from owlbear_delivery import (
    CreateDraftPublicationPullRequest,
    FindPublicationPullRequest,
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
        response = self._validate(_RepositoryResponse, payload, "read_repository")
        if response.full_name.casefold() != repository.casefold():
            self._invalid_response("read_repository", "GitHub returned another repository identity")
        return PublicationRepository(repository=response.full_name, default_branch=response.default_branch)

    def read_pull_request(self, repository: str, number: int) -> PublicationPullRequest:
        """Read one exact GitHub pull request."""
        operation = "read_pull_request"
        payload = self._rest(operation, "GET", f"{_repository_endpoint(repository)}/pulls/{number}")
        pull_request = self._pull_request(repository, payload, operation)
        if pull_request.number != number:
            self._invalid_response(operation, "GitHub returned another pull request identity")
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
            self._invalid_response(operation, "GitHub returned an invalid pull request list", cause=exc)
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
        self._require_open_head(request.repository, request.number, request.expected_head_sha, "update_pull_request")
        payload = self._rest(
            "update_pull_request",
            "PATCH",
            f"{_repository_endpoint(request.repository)}/pulls/{request.number}",
            body={"title": request.title, "body": request.body},
            write=True,
        )
        updated = self._pull_request(request.repository, payload, "update_pull_request")
        self._require_matching_head(updated, request.expected_head_sha, "update_pull_request")
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
                retry_safe=False,
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
        elif "http 404" in normalized or "not found" in normalized:
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

    def _pull_request(self, repository: str, payload: _JsonValue, operation: str) -> PublicationPullRequest:
        response = self._validate(_PullResponse, payload, operation)
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
            self._invalid_response(operation, "GitHub returned invalid pull request state", cause=exc)

    def _validate[Model: _GitHubModel](
        self,
        model: type[Model],
        payload: _JsonValue,
        operation: str,
    ) -> Model:
        try:
            return model.model_validate(payload)
        except ValidationError as exc:
            self._invalid_response(operation, "GitHub returned an invalid response", cause=exc)

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
    def _invalid_response(operation: str, detail: str, *, cause: Exception | None = None) -> None:
        error = PublicationProviderError(
            PublicationProviderFailureCode.INVALID_RESPONSE,
            operation,
            detail,
            retry_safe=False,
        )
        raise error from cause

    @staticmethod
    def _conflict(operation: str, detail: str) -> None:
        raise PublicationProviderError(
            PublicationProviderFailureCode.CONFLICT,
            operation,
            detail,
            retry_safe=False,
        )


def _repository_endpoint(repository: str) -> str:
    owner, name = repository.split("/", maxsplit=1)
    return f"repos/{quote(owner, safe='')}/{quote(name, safe='')}"
