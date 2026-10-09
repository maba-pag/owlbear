"""Deterministic in-memory publication provider for Delivery tests."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from owlbear_delivery.publication_provider import (
    CreateDraftPublicationPullRequest,
    FindPublicationPullRequest,
    ObservePublicationChecks,
    PendingMergeRequest,
    PublicationBranchHead,
    PublicationCheckSnapshot,
    PublicationMergeEvidence,
    PublicationMergeMethod,
    PublicationMergeRefusal,
    PublicationMergeRefusalReason,
    PublicationMergeRequestResult,
    PublicationMergeRequestStatus,
    PublicationMergeSettings,
    PublicationMergeStack,
    PublicationProviderError,
    PublicationProviderFailureCode,
    PublicationPullRequest,
    PublicationRepository,
    RequestPublicationMerge,
    SetPublicationPullRequestDraftState,
    UpdatePublicationPullRequest,
    merge_request_body,
)
from owlbear_delivery_github.effect_launcher import FrozenBodyMismatchError

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

_MEMORY_MERGED_AT = datetime(2026, 1, 1, tzinfo=UTC)


@dataclass(slots=True)
class _MemoryMergeRequest:
    repository: str
    number: int
    pending: PendingMergeRequest
    base_branch: str
    target_head: str | None
    stacked: bool
    status: PublicationMergeRequestStatus = PublicationMergeRequestStatus.PENDING
    merge_commit_sha: str | None = None
    refusal: PublicationMergeRefusal | None = None
    expired: bool = False

    def result(self, *, existing_request: bool = False) -> PublicationMergeRequestResult:
        if self.status is PublicationMergeRequestStatus.PENDING:
            return PublicationMergeRequestResult(
                status=self.status,
                pending=self.pending,
                existing_request=existing_request,
            )
        return PublicationMergeRequestResult(
            status=self.status,
            merge_commit_sha=self.merge_commit_sha,
            refusal=self.refusal,
        )


@dataclass(slots=True)
class InMemoryPublicationProvider:
    """Implement fixed publication operations without network or subprocess effects.

    Merge requests are accepted as pending and execute only when a test calls
    ``execute_pending_merges``; fault fields model lost responses and complete refusals.
    """

    repositories: dict[str, PublicationRepository] = field(default_factory=dict)
    pull_requests: dict[tuple[str, int], PublicationPullRequest] = field(default_factory=dict)
    check_snapshots: dict[tuple[str, int, str], PublicationCheckSnapshot] = field(default_factory=dict)
    merge_settings: dict[tuple[str, str], PublicationMergeSettings] = field(default_factory=dict)
    branch_heads: dict[tuple[str, str], str] = field(default_factory=dict)
    stacks: dict[tuple[str, int], PublicationMergeStack] = field(default_factory=dict)
    downstack: dict[tuple[str, int], tuple[int, ...]] = field(default_factory=dict)
    merge_commit_parents: dict[tuple[str, int], tuple[str, ...]] = field(default_factory=dict)
    merge_requests: dict[str, _MemoryMergeRequest] = field(default_factory=dict)
    merge_request_bodies: list[bytes] = field(default_factory=list)
    rules_failures: dict[tuple[str, int], str] = field(default_factory=dict)
    lose_next_merge_response: bool = False
    next_merge_refusal: PublicationMergeRefusal | None = None
    effect_groups: int = 0

    def add_repository(self, repository: PublicationRepository) -> None:
        """Register one exact provider repository identity."""
        self.repositories[repository.repository] = repository

    def read_repository(self, repository: str) -> PublicationRepository:
        """Read one registered repository."""
        try:
            return self.repositories[repository]
        except KeyError as exc:
            raise PublicationProviderError(
                PublicationProviderFailureCode.NOT_FOUND,
                "read_repository",
                "publication repository was not found",
                retry_safe=False,
            ) from exc

    def read_pull_request(self, repository: str, number: int) -> PublicationPullRequest:
        """Read one registered pull request."""
        try:
            return self.pull_requests[(repository, number)]
        except KeyError as exc:
            raise PublicationProviderError(
                PublicationProviderFailureCode.NOT_FOUND,
                "read_pull_request",
                "publication pull request was not found",
                retry_safe=False,
            ) from exc

    def find_pull_request(self, request: FindPublicationPullRequest) -> PublicationPullRequest | None:
        """Find the unique open pull request for one head/base identity."""
        matches = tuple(
            pull_request
            for pull_request in self.pull_requests.values()
            if pull_request.repository == request.repository
            and pull_request.head_branch == request.head_branch
            and pull_request.base_branch == request.base_branch
            and pull_request.state == "open"
        )
        if len(matches) > 1:
            raise PublicationProviderError(
                PublicationProviderFailureCode.CONFLICT,
                "find_pull_request",
                "multiple pull requests match the publication identity",
                retry_safe=False,
            )
        return matches[0] if matches else None

    def create_draft_pull_request(self, request: CreateDraftPublicationPullRequest) -> PublicationPullRequest:
        """Create one draft pull request after rejecting duplicate head/base identity."""
        self.read_repository(request.repository)
        existing = self.find_pull_request(
            FindPublicationPullRequest(
                repository=request.repository,
                head_branch=request.head_branch,
                base_branch=request.base_branch,
            )
        )
        if existing is not None:
            raise PublicationProviderError(
                PublicationProviderFailureCode.CONFLICT,
                "create_draft_pull_request",
                "publication pull request already exists",
                retry_safe=False,
            )
        next_number = (
            max(
                (number for repository, number in self.pull_requests if repository == request.repository),
                default=0,
            )
            + 1
        )
        pull_request = PublicationPullRequest(
            repository=request.repository,
            number=next_number,
            node_id=f"PR_{request.repository}_{next_number}",
            head_branch=request.head_branch,
            head_sha=request.head_sha,
            base_branch=request.base_branch,
            title=request.title,
            body=request.body,
            draft=True,
            state="open",
            merged=False,
        )
        self.pull_requests[(request.repository, next_number)] = pull_request
        return pull_request

    def update_pull_request(self, request: UpdatePublicationPullRequest) -> PublicationPullRequest:
        """Update fixed generated fields after exact-head fencing."""
        current = self.read_pull_request(request.repository, request.number)
        if (
            current.head_sha != request.expected_head_sha
            or current.title != request.expected_title
            or current.body != request.expected_body
            or current.state != "open"
            or current.merged
        ):
            raise PublicationProviderError(
                PublicationProviderFailureCode.CONFLICT,
                "update_pull_request",
                "publication pull request state does not match the update fence",
                retry_safe=False,
            )
        updated = current.model_copy(
            update={
                "title": request.title,
                "body": request.body,
            }
        )
        self.pull_requests[(request.repository, request.number)] = updated
        return updated

    def set_pull_request_draft_state(
        self,
        request: SetPublicationPullRequestDraftState,
    ) -> PublicationPullRequest:
        """Transition draft state after exact node and head fencing."""
        current = self.read_pull_request(request.repository, request.number)
        if (
            current.node_id != request.node_id
            or current.head_sha != request.expected_head_sha
            or current.state != "open"
            or current.merged
        ):
            raise PublicationProviderError(
                PublicationProviderFailureCode.CONFLICT,
                "set_pull_request_draft_state",
                "publication pull request state does not match the draft-state fence",
                retry_safe=False,
            )
        updated = current.model_copy(update={"draft": request.draft})
        self.pull_requests[(request.repository, request.number)] = updated
        return updated

    def add_check_snapshot(self, snapshot: PublicationCheckSnapshot) -> None:
        """Register one exact deterministic provider check observation."""
        self.check_snapshots[(snapshot.repository, snapshot.number, snapshot.head_sha)] = snapshot

    def observe_checks(self, request: ObservePublicationChecks) -> PublicationCheckSnapshot:
        """Read registered checks only when the pull-request head still matches."""
        pull_request = self.read_pull_request(request.repository, request.number)
        if pull_request.head_sha != request.expected_head_sha:
            raise PublicationProviderError(
                PublicationProviderFailureCode.CONFLICT,
                "observe_checks",
                "publication pull request head differs from the check observation fence",
                retry_safe=False,
            )
        return self.check_snapshots.get(
            (request.repository, request.number, request.expected_head_sha),
            PublicationCheckSnapshot(
                repository=request.repository,
                number=request.number,
                head_sha=request.expected_head_sha,
                checks=(),
            ),
        )

    def set_merge_settings(self, settings: PublicationMergeSettings) -> None:
        """Configure merge settings, including execution-scope enforcement, for one target branch."""
        self.merge_settings[(settings.repository, settings.branch)] = settings

    def set_branch_head(self, repository: str, branch: str, head_sha: str) -> None:
        """Set or advance one branch head, for example a target advance after the final read."""
        self.branch_heads[(repository, branch)] = head_sha

    def set_stack(
        self,
        repository: str,
        number: int,
        stack: PublicationMergeStack | None,
        *,
        downstack: tuple[int, ...] = (),
    ) -> None:
        """Join or leave a stack; an unenforced merge of this PR also merges ``downstack``."""
        if stack is None:
            self.stacks.pop((repository, number), None)
            self.downstack.pop((repository, number), None)
            return
        self.stacks[(repository, number)] = stack
        self.downstack[(repository, number)] = downstack

    def add_foreign_merge_request(self, repository: str, number: int, pending: PendingMergeRequest) -> None:
        """Register a pending merge request that Delivery did not send."""
        pull_request = self.read_pull_request(repository, number)
        self.merge_requests[pending.request_id] = _MemoryMergeRequest(
            repository=repository,
            number=number,
            pending=pending,
            base_branch=pull_request.base_branch,
            target_head=self.branch_heads.get((repository, pull_request.base_branch)),
            stacked=self._stacked(repository, number),
        )

    def expire_merge_request(self, request_id: str) -> None:
        """Expire one request's readback while the request itself stays live."""
        self.merge_requests[request_id].expired = True

    def read_merge_settings(self, repository: str, branch: str) -> PublicationMergeSettings:
        """Read configured merge settings or permissive defaults without scope enforcement."""
        self.read_repository(repository)
        return self.merge_settings.get(
            (repository, branch),
            PublicationMergeSettings(
                repository=repository,
                branch=branch,
                allowed_methods=tuple(PublicationMergeMethod),
                viewer_can_push=True,
                rule_types=(),
                queue_required=False,
                strict_up_to_date_required=False,
                execution_scope_enforced=False,
            ),
        )

    def read_branch_head(self, repository: str, branch: str) -> PublicationBranchHead:
        """Read one registered branch head."""
        try:
            head_sha = self.branch_heads[(repository, branch)]
        except KeyError as exc:
            raise PublicationProviderError(
                PublicationProviderFailureCode.NOT_FOUND,
                "read_branch_head",
                "publication branch was not found",
                retry_safe=False,
            ) from exc
        return PublicationBranchHead(repository=repository, branch=branch, head_sha=head_sha)

    def request_merge(
        self,
        request: RequestPublicationMerge,
        *,
        body_path: Path,
        release: Callable[[int, str], None],
    ) -> PublicationMergeRequestResult:
        """Accept one frozen merge body after ``release``; a raised ``release`` sends nothing."""
        body = merge_request_body(request)
        if body_path.read_bytes() != body:
            message = "frozen merge body differs from the approved request"
            raise FrozenBodyMismatchError(message)
        self.effect_groups += 1
        release(self.effect_groups, f"memory:{self.effect_groups}")
        self.merge_request_bodies.append(body)
        result = self._submit_merge(request)
        if self.lose_next_merge_response:
            self.lose_next_merge_response = False
            raise PublicationProviderError(
                PublicationProviderFailureCode.RESPONSE_UNKNOWN,
                "request_merge",
                "merge request response was lost",
                retry_safe=False,
            )
        return result

    def read_merge_request(self, repository: str, number: int, request_id: str) -> PublicationMergeRequestResult:
        """Read one merge request; an unknown or expired identity is unavailable."""
        record = self.merge_requests.get(request_id)
        if record is None or record.expired or (record.repository, record.number) != (repository, number):
            return PublicationMergeRequestResult(status=PublicationMergeRequestStatus.UNAVAILABLE)
        return record.result()

    def read_merge_evidence(self, repository: str, number: int) -> PublicationMergeEvidence:
        """Read the pull request's merge facts, stack and merge-commit parents."""
        pull_request = self.read_pull_request(repository, number)
        return PublicationMergeEvidence(
            repository=repository,
            number=number,
            node_id=pull_request.node_id,
            state=pull_request.state,
            draft=pull_request.draft,
            merged=pull_request.merged,
            head_sha=pull_request.head_sha,
            base_branch=pull_request.base_branch,
            stack=self.stacks.get((repository, number)),
            merge_commit_sha=pull_request.merge_commit_sha if pull_request.merged else None,
            merge_commit_parents=self.merge_commit_parents.get((repository, number), ()),
            merged_at=pull_request.merged_at if pull_request.merged else None,
        )

    def execute_pending_merges(self) -> tuple[str, ...]:
        """Run every pending request the way GitHub's background merge would; return their IDs."""
        executed = [
            request_id
            for request_id, record in tuple(self.merge_requests.items())
            if record.status is PublicationMergeRequestStatus.PENDING
        ]
        for request_id in executed:
            self._execute_merge(self.merge_requests[request_id])
        return tuple(executed)

    def merge_manually(
        self,
        repository: str,
        number: int,
        *,
        merge_method: PublicationMergeMethod = PublicationMergeMethod.MERGE,
    ) -> str:
        """Merge one open pull request at its current head as a user would in GitHub."""
        pull_request = self.read_pull_request(repository, number)
        if pull_request.merged or pull_request.state != "open":
            message = "only open pull requests can be merged manually"
            raise ValueError(message)
        target_head = self.branch_heads[(repository, pull_request.base_branch)]
        return self._record_merge(pull_request, target_head, merge_method, merged_by="user")

    def _submit_merge(self, request: RequestPublicationMerge) -> PublicationMergeRequestResult:
        if self.next_merge_refusal is not None:
            refusal, self.next_merge_refusal = self.next_merge_refusal, None
            return PublicationMergeRequestResult(status=PublicationMergeRequestStatus.REFUSED, refusal=refusal)
        pull_request = self.pull_requests.get((request.repository, request.number))
        if pull_request is None:
            raise PublicationProviderError(
                PublicationProviderFailureCode.RESPONSE_UNKNOWN,
                "request_merge",
                "merge request outcome is unknown",
                retry_safe=False,
            )
        if pull_request.merged:
            return PublicationMergeRequestResult(
                status=PublicationMergeRequestStatus.MERGED,
                merge_commit_sha=pull_request.merge_commit_sha,
            )
        if pull_request.state != "open" or pull_request.draft:
            return PublicationMergeRequestResult(
                status=PublicationMergeRequestStatus.REFUSED,
                refusal=PublicationMergeRefusal(
                    reason=PublicationMergeRefusalReason.CLOSED_OR_DRAFT,
                    http_status=400,
                    message="Pull request is not mergeable",
                ),
            )
        existing = next(
            (
                record
                for record in self.merge_requests.values()
                if (record.repository, record.number) == (request.repository, request.number)
                and record.status is PublicationMergeRequestStatus.PENDING
            ),
            None,
        )
        if existing is not None:
            return existing.result(existing_request=True)
        pending = PendingMergeRequest(
            request_id=f"merge-request-{len(self.merge_requests) + 1}",
            expected_head_sha=request.expected_head_sha,
            merge_method=request.merge_method.value,
            merge_action="direct_merge",
            bypass_rules=False,
        )
        self.add_foreign_merge_request(request.repository, request.number, pending)
        return self.merge_requests[pending.request_id].result()

    def _execute_merge(self, record: _MemoryMergeRequest) -> None:
        pull_request = self.read_pull_request(record.repository, record.number)
        settings = self.read_merge_settings(record.repository, record.base_branch)
        target_head = self.branch_heads.get((record.repository, pull_request.base_branch))
        failure = self._merge_failure(record, pull_request, settings, target_head)
        if failure is not None:
            record.status = PublicationMergeRequestStatus.REFUSED
            record.refusal = failure
            return
        if target_head is None:
            message = "memory merge requires a registered target head"
            raise ValueError(message)
        merge_method = PublicationMergeMethod(record.pending.merge_method)
        record.merge_commit_sha = self._record_merge(pull_request, target_head, merge_method, merged_by="owlbear")
        record.status = PublicationMergeRequestStatus.MERGED
        for number in self.downstack.get((record.repository, record.number), ()):
            downstack = self.read_pull_request(record.repository, number)
            if not downstack.merged:
                self._record_merge(downstack, record.merge_commit_sha, merge_method, merged_by="owlbear")

    def _merge_failure(
        self,
        record: _MemoryMergeRequest,
        pull_request: PublicationPullRequest,
        settings: PublicationMergeSettings,
        target_head: str | None,
    ) -> PublicationMergeRefusal | None:
        rules = PublicationMergeRefusalReason.RULES_FAILED
        if pull_request.merged:
            return PublicationMergeRefusal(reason=rules, message="Pull request is already merged")
        if pull_request.head_sha != record.pending.expected_head_sha:
            return PublicationMergeRefusal(
                reason=PublicationMergeRefusalReason.HEAD_CHANGED,
                message="Head branch was modified",
            )
        if pull_request.state != "open" or pull_request.draft:
            return PublicationMergeRefusal(reason=PublicationMergeRefusalReason.CLOSED_OR_DRAFT)
        if target_head is None:
            return PublicationMergeRefusal(reason=rules, message="Base branch was not found")
        return self._rules_failure(record, pull_request, settings, target_head)

    def _rules_failure(
        self,
        record: _MemoryMergeRequest,
        pull_request: PublicationPullRequest,
        settings: PublicationMergeSettings,
        target_head: str,
    ) -> PublicationMergeRefusal | None:
        rules = PublicationMergeRefusalReason.RULES_FAILED
        rules_message = self.rules_failures.get((record.repository, record.number))
        if rules_message is not None:
            return PublicationMergeRefusal(reason=rules, message=rules_message)
        if settings.strict_up_to_date_required and target_head != record.target_head:
            return PublicationMergeRefusal(reason=rules, message="Head branch is not up to date with the base branch")
        scope_changed = pull_request.base_branch != record.base_branch or (
            self._stacked(record.repository, record.number) and not record.stacked
        )
        if settings.execution_scope_enforced and scope_changed:
            return PublicationMergeRefusal(reason=rules, message="Merge scope changed after the request")
        return None

    def _record_merge(
        self,
        pull_request: PublicationPullRequest,
        target_head: str,
        merge_method: PublicationMergeMethod,
        *,
        merged_by: str,
    ) -> str:
        key = (pull_request.repository, pull_request.number)
        identity = f"{pull_request.repository}#{pull_request.number}:{pull_request.head_sha}:{target_head}"
        merge_commit_sha = hashlib.sha1(identity.encode(), usedforsecurity=False).hexdigest()
        parents = (
            (target_head, pull_request.head_sha) if merge_method is PublicationMergeMethod.MERGE else (target_head,)
        )
        self.merge_commit_parents[key] = parents
        self.branch_heads[(pull_request.repository, pull_request.base_branch)] = merge_commit_sha
        self.pull_requests[key] = pull_request.model_copy(
            update={
                "state": "closed",
                "merged": True,
                "draft": False,
                "merge_commit_sha": merge_commit_sha,
                "merged_at": _MEMORY_MERGED_AT,
                "merged_by_login": merged_by,
            }
        )
        return merge_commit_sha

    def _stacked(self, repository: str, number: int) -> bool:
        stack = self.stacks.get((repository, number))
        return stack is not None and stack.size > 1
