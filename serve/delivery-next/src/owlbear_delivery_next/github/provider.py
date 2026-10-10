# Adapted from serve/delivery/src/owlbear_delivery/publication_provider.py at ab9cfc6cb.
"""Transport-free GitHub contract: pull requests, checks, rules, comments and merge (D4 §3.1, §3.2)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

_SHA = r"^[0-9a-f]{40}$"
_REPOSITORY = r"^[^\s/]+/[^\s/]+$"
_MAX_MESSAGE = 500
SUCCESS = frozenset({"success", "neutral", "skipped"})


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class FailureCode(StrEnum):
    """Provider failures without transport-specific exceptions."""

    UNAVAILABLE = "unavailable"
    AUTHENTICATION_REQUIRED = "authentication_required"
    RATE_LIMITED = "rate_limited"
    TIMEOUT = "timeout"
    CONFLICT = "conflict"
    NOT_FOUND = "not_found"
    INVALID_RESPONSE = "invalid_response"
    RESPONSE_UNKNOWN = "response_unknown"


class ProviderError(RuntimeError):
    """Typed provider failure; ``retry_safe`` is False when a write may have taken effect."""

    def __init__(self, code: FailureCode, operation: str, detail: str, *, retry_safe: bool) -> None:
        super().__init__(f"{operation}: {detail}")
        self.code, self.operation, self.retry_safe = code, operation, retry_safe


def bounded(message: str | None) -> str | None:
    """Return a single-line provider message bounded for persisted diagnostics."""
    collapsed = " ".join((message or "").split())
    return collapsed[:_MAX_MESSAGE] or None


class MergeMethod(StrEnum):
    """Merge methods a merge request may name; no rule-bypass option exists."""

    MERGE = "merge"
    SQUASH = "squash"
    REBASE = "rebase"


class Repository(_Model):
    """Repository facts read by ``gh repo view``."""

    repository: str = Field(pattern=_REPOSITORY)
    url: str
    default_branch: str = Field(min_length=1)
    methods: tuple[MergeMethod, ...]
    can_push: bool
    delete_branch_on_merge: bool


class PullRequest(_Model):
    """Provider-observed pull request state; never stored, read at every step entry (DR5)."""

    repository: str = Field(pattern=_REPOSITORY)
    number: int = Field(gt=0)
    node_id: str = Field(min_length=1)
    url: str
    head_branch: str = Field(min_length=1)
    head_sha: str = Field(pattern=_SHA)
    base_branch: str = Field(min_length=1)
    draft: bool
    state: Literal["open", "closed"]
    merged: bool
    mergeable: bool | None = None
    merge_state: str | None = None
    merge_commit_sha: str | None = Field(default=None, pattern=_SHA)


class Check(_Model):
    """One check run or commit status at one head."""

    name: str = Field(min_length=1)
    status: str
    conclusion: str | None = None
    required: bool = False
    url: str | None = None
    job_id: int | None = None
    completed_at: datetime | None = None


class Rules(_Model):
    """Effective rules of one branch; an HTTP 403 makes them unknown, never "no rules"."""

    state: Literal["known", "unknown"]
    evidence: str
    types: tuple[str, ...] = ()
    required_checks: tuple[str, ...] = ()
    queue_required: bool = False  # detected only: the merge queue is not supported (TD-22)
    strict: bool = False
    conversation_resolution: bool = False


class ThreadComment(_Model):
    """One comment of a review thread."""

    id: str
    author: str
    body: str


class ConversationItem(_Model):
    """One issue comment, review body or review thread of a pull request; ``id`` is its node id.

    A thread's ``body`` is its comments in order, each prefixed with its author; ``state`` is a review's state.
    """

    id: str
    kind: Literal["comment", "review", "thread"]
    author: str
    body: str
    url: str = ""
    path: str | None = None
    state: str = ""
    resolved: bool = False
    outdated: bool = False
    comments: tuple[ThreadComment, ...] = ()


class MergeRequest(_Model):
    """One exact-head direct merge."""

    repository: str = Field(pattern=_REPOSITORY)
    number: int = Field(gt=0)
    expected_head_sha: str = Field(pattern=_SHA)
    method: MergeMethod


def merge_request_body(request: MergeRequest) -> bytes:
    """Return the JSON body: ``sha`` guards the head."""
    body: dict[str, object] = {"merge_method": request.method.value, "sha": request.expected_head_sha}
    return json.dumps(body, sort_keys=True, separators=(",", ":")).encode()


class MergeStatus(StrEnum):
    """Outcome of one merge submission."""

    MERGED = "merged"
    REFUSED = "refused"
    UNKNOWN = "unknown"


class Refusal(StrEnum):
    """Complete provider refusals of one merge submission."""

    HEAD_CHANGED = "head-changed"
    NOT_MERGEABLE = "not-mergeable"
    CLOSED_OR_DRAFT = "closed-or-draft"
    RULES_FAILED = "rules-failed"
    FORBIDDEN = "forbidden"
    VALIDATION = "validation"


class MergeResult(_Model):
    """Result of one merge submission; UNKNOWN needs a readback before any replay."""

    status: MergeStatus
    sha: str | None = Field(default=None, pattern=_SHA)
    refusal: Refusal | None = None
    message: str | None = Field(default=None, max_length=_MAX_MESSAGE)


@dataclass(frozen=True)
class CiState:
    """Checks at one head, by name: passed, failed, running and never started."""

    passed: tuple[str, ...] = ()
    failed: tuple[Check, ...] = ()
    running: tuple[str, ...] = ()
    missing: tuple[str, ...] = ()

    @property
    def expected(self) -> int:
        """Number of expected checks."""
        return len(self.passed) + len(self.failed) + len(self.running) + len(self.missing)


def classify_checks(checks: tuple[Check, ...], declared: tuple[str, ...], required: tuple[str, ...]) -> CiState:
    """Classify the head's checks against the declared CI and required checks; a missing one is never passed (P10).

    A check is expected when it ran at the head, is declared, or is required by the profile or GitHub: every
    observed check gates the automatic merge (TD-15). The latest run of a name wins.
    """
    latest = {c.name: c for c in sorted(checks, key=lambda c: c.completed_at.timestamp() if c.completed_at else 1e12)}
    expected = dict.fromkeys([*declared, *required, *latest])
    passed, failed, running, missing = [], [], [], []
    for name in expected:
        c = latest.get(name)
        if c is None:
            missing.append(name)
        elif c.conclusion is None and c.status != "completed":
            running.append(name)
        elif (c.conclusion or "").casefold() in SUCCESS:
            passed.append(name)
        else:
            failed.append(c)
    return CiState(tuple(passed), tuple(failed), tuple(running), tuple(missing))


class Provider(Protocol):
    """GitHub operations the engine steps use; reads never send a write."""

    def read_repository(self) -> Repository:
        """Read the repository of the working directory with ``gh repo view``."""
        ...

    def read_rules(self, repository: str, branch: str) -> Rules:
        """Read effective rules and required checks of one branch."""
        ...

    def find_pull_request(self, repository: str, head: str, base: str) -> PullRequest | None:
        """Return the unique open pull request for one head and base branch."""
        ...

    def read_pull_request(self, repository: str, number: int) -> PullRequest:
        """Read one exact pull request."""
        ...

    def create_pull_request(self, repository: str, head: str, base: str, title: str, body: str) -> PullRequest:
        """Create one draft pull request."""
        ...

    def mark_ready(self, pr: PullRequest) -> None:
        """Mark one draft pull request ready for review."""
        ...

    def close_pull_request(self, repository: str, number: int) -> None:
        """Close one pull request without merging it."""
        ...

    def reopen_pull_request(self, repository: str, number: int) -> None:
        """Reopen one closed pull request."""
        ...

    def observe_checks(self, repository: str, number: int, head: str) -> tuple[Check, ...]:
        """Observe check runs and commit statuses at one exact head."""
        ...

    def observe_commit_checks(self, repository: str, sha: str) -> tuple[Check, ...]:
        """Observe check runs and commit statuses on one commit outside any pull request."""
        ...

    def review_request(self, repository: str, number: int) -> tuple[str | None, tuple[str, ...]]:
        """GitHub's review decision for the PR (e.g. ``REVIEW_REQUIRED``) and its requested reviewers."""
        ...

    def viewer(self) -> str:
        """The login Delivery posts as; a credential that cannot read it raises ``AUTHENTICATION_REQUIRED``."""
        ...

    def read_conversation(self, repository: str, number: int) -> tuple[ConversationItem, ...]:
        """Read every issue comment, review body (non-empty or changes requested) and review thread."""
        ...

    def post_reply(self, repository: str, number: int, item: ConversationItem, body: str) -> str:
        """Reply in a thread, or post an issue comment quoting a comment or review; return the new comment id."""
        ...

    def resolve_thread(self, thread_id: str) -> bool:
        """Resolve one review thread; True only when the mutation acknowledges it resolved."""
        ...

    def job_log(self, repository: str, job_id: int, lines: int = 40) -> str:
        """Return the tail of one Actions job log."""
        ...

    def compare(self, repository: str, base: str, head: str) -> str:
        """Return a short delta: commits and changed files from *base* to *head*."""
        ...

    def request_merge(self, request: MergeRequest) -> MergeResult:
        """Send one merge submission guarded by the expected head."""
        ...

    def delete_branch(self, repository: str, branch: str) -> None:
        """Delete one remote branch."""
        ...
