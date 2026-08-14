"""Change-branch-only publication through fixed Git operations."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import uuid
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Literal, NoReturn

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from owlbear_delivery.change_workspace import CoordinationConflictError, PublicationLease
from owlbear_delivery.git_executable import resolve_git_executable
from owlbear_delivery.identities import ChangeId
from owlbear_delivery.publication_provider import (
    PublicationProviderError,
    PublicationProviderFailureCode,
)
from owlbear_delivery.storage_io import atomic_write, locked_roots

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from owlbear_delivery.change_workspace import (
        ChangeCoordination,
        PortfolioCoordinator,
        PublicationLock,
    )

_COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}")
_GIT_TIMEOUT_SECONDS = 30.0
_LS_REMOTE_MISSING = 2
_PUBLICATION_LEASE_DURATION = timedelta(minutes=10)
_REMOTE_REF_FIELD_COUNT = 2


class _PublicationModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class PublishChangeBranch(_PublicationModel):
    """Exact preconditions for one replayable Change-branch checkpoint."""

    change_id: ChangeId
    expected_remote_head: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    expected_published_head: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    operation_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class SupersedeChangeBranch(_PublicationModel):
    """Exact preconditions for one replayable published-history successor."""

    change_id: ChangeId
    expected_published_branch: str = Field(pattern=r"^owlbear/change/[a-z0-9]+(?:-[a-z0-9]+)*(?:\+s[1-9][0-9]*)?$")
    expected_published_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    superseding_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    operation_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class ChangeBranchPublicationReceipt(_PublicationModel):
    """Provider-independent evidence for one exact remote Change branch head."""

    schema_version: Literal[1] = 1
    receipt_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    operation_id: str = Field(min_length=1)
    change_id: ChangeId
    remote: str = Field(min_length=1)
    branch: str = Field(min_length=1)
    target_branch: str = Field(min_length=1)
    expected_remote_head: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    published_head: str = Field(pattern=r"^[0-9a-f]{40}$")


class ChangeBranchSupersessionReceipt(_PublicationModel):
    """Provider-independent evidence for one exact successor Change branch head."""

    schema_version: Literal[1] = 1
    receipt_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    operation_id: str = Field(min_length=1)
    change_id: ChangeId
    remote: str = Field(min_length=1)
    predecessor_branch: str = Field(pattern=r"^owlbear/change/[a-z0-9]+(?:-[a-z0-9]+)*(?:\+s[1-9][0-9]*)?$")
    predecessor_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    successor_branch: str = Field(pattern=r"^owlbear/change/[a-z0-9]+(?:-[a-z0-9]+)*\+s[1-9][0-9]*$")
    superseding_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    target_branch: str = Field(min_length=1)


class _PublicationOperation(_PublicationModel):
    schema_version: Literal[1] = 1
    operation_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
    change_id: ChangeId
    remote: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")
    branch: str = Field(pattern=r"^owlbear/change/[a-z0-9]+(?:-[a-z0-9]+)*(?:\+s[1-9][0-9]*)?$")
    target_branch: str = Field(min_length=1)
    expected_remote_head: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    published_head: str = Field(pattern=r"^[0-9a-f]{40}$")


class _SupersessionOperation(_PublicationModel):
    schema_version: Literal[1] = 1
    operation_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
    change_id: ChangeId
    remote: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")
    predecessor_branch: str = Field(pattern=r"^owlbear/change/[a-z0-9]+(?:-[a-z0-9]+)*(?:\+s[1-9][0-9]*)?$")
    predecessor_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    successor_branch: str = Field(pattern=r"^owlbear/change/[a-z0-9]+(?:-[a-z0-9]+)*\+s[1-9][0-9]*$")
    superseding_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    target_branch: str = Field(min_length=1)


@dataclass
class _PublicationAttempt:
    owner_id: str
    reservation: ChangeCoordination | None = None
    observed_remote_head: str | None = None
    write_started: bool = False
    write_outcome_ambiguous: bool = False
    reservation_released: bool = False


class ChangeBranchPublisher:
    """Publish one reviewed Change head to its same-named remote branch."""

    def __init__(
        self,
        repository: Path,
        coordinator: PortfolioCoordinator,
        *,
        remote: str,
        target_branch: str,
        operation_root: Path,
    ) -> None:
        self._repository = repository.resolve()
        self._git_executable = resolve_git_executable()
        self._coordinator = coordinator
        self._remote = remote
        self._target_branch = target_branch
        self._operation_root = operation_root.resolve()
        self._git_environment = os.environ.copy()
        self._git_environment["GIT_TERMINAL_PROMPT"] = "0"
        for variable in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
            self._git_environment.pop(variable, None)
        self._validate_configuration()

    def publish(self, request: PublishChangeBranch) -> ChangeBranchPublicationReceipt:
        """Publish or reconcile one exact reviewed Change branch checkpoint."""
        attempt = _PublicationAttempt(owner_id=str(uuid.uuid4()))
        with self._publication_lock(request) as lock:
            try:
                try:
                    return self._publish(request, attempt, lock)
                except subprocess.TimeoutExpired as exc:
                    code = (
                        PublicationProviderFailureCode.RESPONSE_UNKNOWN
                        if attempt.write_started
                        else PublicationProviderFailureCode.TIMEOUT
                    )
                    error = PublicationProviderError(
                        code,
                        request.operation_id,
                        "Git publication operation timed out",
                        retry_safe=not attempt.write_started,
                    )
                    raise error from exc
                except (OSError, ValueError) as exc:
                    error = PublicationProviderError(
                        PublicationProviderFailureCode.UNAVAILABLE,
                        request.operation_id,
                        "Change publication state is unavailable",
                        retry_safe=False,
                    )
                    raise error from exc
            finally:
                if (
                    attempt.reservation is not None
                    and not attempt.reservation_released
                    and not attempt.write_outcome_ambiguous
                ):
                    self._release_reserved_request(request, attempt.owner_id, lock)

    def supersede(self, request: SupersedeChangeBranch) -> ChangeBranchSupersessionReceipt:
        """Publish one successor branch without rewriting the predecessor publication."""
        branch_request = PublishChangeBranch(
            change_id=request.change_id,
            expected_remote_head=None,
            operation_id=request.operation_id,
        )
        attempt = _PublicationAttempt(owner_id=str(uuid.uuid4()))
        with self._publication_lock(branch_request) as lock:
            try:
                return self._supersede(request, branch_request, attempt, lock)
            except subprocess.TimeoutExpired as exc:
                code = (
                    PublicationProviderFailureCode.RESPONSE_UNKNOWN
                    if attempt.write_started
                    else PublicationProviderFailureCode.TIMEOUT
                )
                error = PublicationProviderError(
                    code,
                    request.operation_id,
                    "Git supersession operation timed out",
                    retry_safe=not attempt.write_started,
                )
                raise error from exc
            except (OSError, ValueError) as exc:
                error = PublicationProviderError(
                    PublicationProviderFailureCode.UNAVAILABLE,
                    request.operation_id,
                    "Change supersession state is unavailable",
                    retry_safe=False,
                )
                raise error from exc
            finally:
                if (
                    attempt.reservation is not None
                    and not attempt.reservation_released
                    and not attempt.write_outcome_ambiguous
                ):
                    self._release_reserved_request(branch_request, attempt.owner_id, lock)

    def _supersede(
        self,
        request: SupersedeChangeBranch,
        branch_request: PublishChangeBranch,
        attempt: _PublicationAttempt,
        lock: PublicationLock,
    ) -> ChangeBranchSupersessionReceipt:
        operation, receipt = self._load_or_prepare_supersession(request, branch_request, attempt, lock)
        if receipt is not None:
            return receipt
        self._validate_supersession_predecessor(operation, branch_request)
        self._publish_supersession_successor(operation, branch_request, attempt)
        attempt.reservation_released = True
        self._release_publication(operation, attempt.owner_id, lock)
        return self._supersession_receipt(operation)

    def _load_or_prepare_supersession(
        self,
        request: SupersedeChangeBranch,
        branch_request: PublishChangeBranch,
        attempt: _PublicationAttempt,
        lock: PublicationLock,
    ) -> tuple[_SupersessionOperation, ChangeBranchSupersessionReceipt | None]:
        operation = self._read_supersession_operation(request)
        if operation is not None:
            self._validate_supersession_replay(operation, request)
            self._validate_supersession_workspace(operation, branch_request)
            if self._remote_head(operation.successor_branch, branch_request) == operation.superseding_head:
                return operation, self._supersession_receipt(operation)

        reservation = self._reserve_publication(branch_request, attempt.owner_id, lock)
        attempt.reservation = reservation
        if operation is None:
            operation = self._prepare_supersession(request, reservation, attempt.owner_id, branch_request)
            operation = self._bind_supersession_operation(operation, branch_request)
            self._validate_supersession_replay(operation, request)
        self._validate_supersession_workspace(operation, branch_request, owner_id=attempt.owner_id)
        return operation, None

    def _validate_supersession_predecessor(
        self,
        operation: _SupersessionOperation,
        request: PublishChangeBranch,
    ) -> None:
        predecessor_head = self._remote_head(operation.predecessor_branch, request)
        if predecessor_head == operation.predecessor_head:
            self._fetch_change_head(operation.predecessor_branch, predecessor_head, request)
            return
        if predecessor_head is not None:
            self._conflict(
                request,
                "published predecessor branch changed before supersession",
                retry_safe=True,
            )
        self._conflict(request, "published predecessor branch is missing")

    def _publish_supersession_successor(
        self,
        operation: _SupersessionOperation,
        request: PublishChangeBranch,
        attempt: _PublicationAttempt,
    ) -> None:
        successor_head = self._remote_head(operation.successor_branch, request)
        if successor_head is not None:
            self._fetch_change_head(operation.successor_branch, successor_head, request)
            if not self._is_ancestor(successor_head, operation.superseding_head, request):
                self._conflict(
                    request,
                    "successor Change branch cannot fast-forward to the superseding head",
                )
        attempt.observed_remote_head = successor_head
        if successor_head == operation.superseding_head:
            return
        attempt.write_started = True
        attempt.write_outcome_ambiguous = True
        self._push_superseding_head(operation, request, attempt)
        if self._remote_head(operation.successor_branch, request) != operation.superseding_head:
            attempt.write_outcome_ambiguous = False
            self._failure(
                PublicationProviderFailureCode.RESPONSE_UNKNOWN,
                request,
                "remote successor branch does not expose the superseding head",
            )

    @contextmanager
    def _publication_lock(self, request: PublishChangeBranch) -> Iterator[PublicationLock]:
        stack = ExitStack()
        try:
            lock = stack.enter_context(self._coordinator.publication_lock(request.change_id, blocking=False))
        except BlockingIOError as exc:
            stack.close()
            error = PublicationProviderError(
                PublicationProviderFailureCode.CONFLICT,
                request.operation_id,
                "Change publication is already in progress",
                retry_safe=True,
            )
            raise error from exc
        with stack:
            yield lock

    def _publish(
        self,
        request: PublishChangeBranch,
        attempt: _PublicationAttempt,
        lock: PublicationLock,
    ) -> ChangeBranchPublicationReceipt:
        operation = self._read_operation(request)
        if operation is not None:
            self._validate_replay(operation, request)
            self._require_current_reviewed_boundary(operation, request)
            if self._remote_head(operation.branch, request) == operation.published_head:
                return self._receipt(operation)
        attempt.reservation = self._reserve_publication(request, attempt.owner_id, lock)
        if operation is not None:
            self._require_current_reviewed_boundary(operation, request)

        if operation is None:
            candidate = self._prepare_operation(request, attempt.reservation, attempt.owner_id)
            operation = self._bind_operation(candidate, request)
            self._validate_replay(operation, request)

        self._validate_prepared_operation(
            operation,
            request,
            owner_id=attempt.owner_id,
        )
        remote_head = self._remote_head(operation.branch, request)
        if remote_head == operation.published_head:
            attempt.reservation_released = True
            self._release_publication(operation, attempt.owner_id, lock)
            return self._receipt(operation)
        if remote_head is not None:
            self._fetch_change_head(operation.branch, remote_head, request)
        if operation.expected_remote_head is not None and (
            remote_head is None or not self._is_ancestor(operation.expected_remote_head, remote_head, request)
        ):
            self._conflict(request, "remote Change branch is behind or divergent from the expected head")
        if remote_head is not None and not self._is_ancestor(remote_head, operation.published_head, request):
            self._conflict(request, "remote Change branch cannot fast-forward to the reviewed head")
        attempt.observed_remote_head = remote_head
        attempt.write_started = True
        attempt.write_outcome_ambiguous = True
        self._push_exact_head(operation, request, attempt)
        observed_after_push = self._remote_head(operation.branch, request)
        if observed_after_push != operation.published_head:
            attempt.write_outcome_ambiguous = False
            self._failure(
                PublicationProviderFailureCode.RESPONSE_UNKNOWN,
                request,
                "remote Change branch does not expose the published head",
            )
        attempt.reservation_released = True
        self._release_publication(operation, attempt.owner_id, lock)
        return self._receipt(operation)

    def _prepare_operation(
        self,
        request: PublishChangeBranch,
        coordination: ChangeCoordination,
        owner_id: str,
    ) -> _PublicationOperation:
        expected_branch = f"owlbear/change/{request.change_id}"
        if (
            coordination.branch != expected_branch
            or coordination.writer is not None
            or coordination.publication_lease is None
            or coordination.publication_lease.operation_id != request.operation_id
            or coordination.publication_lease.owner_id != owner_id
        ):
            self._conflict(request, "Change branch publication requires one reserved canonical workspace")
        worktree = coordination.worktree_path.resolve()
        if self._operation_root == worktree or self._operation_root.is_relative_to(worktree):
            self._conflict(request, "publication operation storage cannot be inside the Change worktree")
        branch_head = self._resolve_commit(f"refs/heads/{coordination.branch}", request)
        if branch_head != coordination.last_reviewed_commit:
            self._conflict(request, "Change branch head differs from the reviewed boundary")
        if request.expected_published_head is not None and branch_head != request.expected_published_head:
            self._conflict(request, "Change branch head differs from the requested checkpoint")
        self._require_clean_worktree(coordination.worktree_path, request)
        return _PublicationOperation(
            operation_id=request.operation_id,
            change_id=request.change_id,
            remote=self._remote,
            branch=coordination.branch,
            target_branch=self._target_branch,
            expected_remote_head=request.expected_remote_head,
            published_head=branch_head,
        )

    def _prepare_supersession(
        self,
        request: SupersedeChangeBranch,
        coordination: ChangeCoordination,
        owner_id: str,
        branch_request: PublishChangeBranch,
    ) -> _SupersessionOperation:
        if (
            coordination.branch != f"owlbear/change/{request.change_id}"
            or coordination.writer is not None
            or coordination.publication_lease is None
            or coordination.publication_lease.operation_id != request.operation_id
            or coordination.publication_lease.owner_id != owner_id
        ):
            self._conflict(branch_request, "Change supersession requires one reserved canonical workspace")
        worktree = coordination.worktree_path.resolve()
        if self._operation_root == worktree or self._operation_root.is_relative_to(worktree):
            self._conflict(branch_request, "publication operation storage cannot be inside the Change worktree")
        branch_head = self._resolve_commit(f"refs/heads/{coordination.branch}", branch_request)
        if request.expected_published_head == request.superseding_head:
            self._conflict(branch_request, "supersession must advance beyond the published predecessor")
        if branch_head != request.superseding_head or coordination.last_reviewed_commit != request.superseding_head:
            self._conflict(branch_request, "supersession head differs from the reviewed boundary")
        self._require_clean_worktree(coordination.worktree_path, branch_request)
        successor_branch = self._next_successor_branch(request.change_id, branch_request)
        return _SupersessionOperation(
            operation_id=request.operation_id,
            change_id=request.change_id,
            remote=self._remote,
            predecessor_branch=request.expected_published_branch,
            predecessor_head=request.expected_published_head,
            successor_branch=successor_branch,
            superseding_head=request.superseding_head,
            target_branch=self._target_branch,
        )

    def _validate_supersession_workspace(
        self,
        operation: _SupersessionOperation,
        request: PublishChangeBranch,
        *,
        owner_id: str | None = None,
    ) -> None:
        coordination = self._coordination(request)
        if coordination.branch != f"owlbear/change/{operation.change_id}" or coordination.writer is not None:
            self._conflict(request, "supersession no longer owns the reviewed Change workspace")
        if owner_id is not None and (
            coordination.publication_lease is None
            or coordination.publication_lease.operation_id != operation.operation_id
            or coordination.publication_lease.owner_id != owner_id
        ):
            self._conflict(request, "supersession does not own the Change publication reservation")
        branch_head = self._resolve_commit(f"refs/heads/{coordination.branch}", request)
        if branch_head != operation.superseding_head or coordination.last_reviewed_commit != operation.superseding_head:
            self._conflict(request, "supersession no longer names the reviewed Change head")
        self._require_clean_worktree(coordination.worktree_path, request)

    def _push_superseding_head(
        self,
        operation: _SupersessionOperation,
        request: PublishChangeBranch,
        attempt: _PublicationAttempt,
    ) -> None:
        push_operation = _PublicationOperation(
            operation_id=operation.operation_id,
            change_id=operation.change_id,
            remote=operation.remote,
            branch=operation.successor_branch,
            target_branch=operation.target_branch,
            expected_remote_head=attempt.observed_remote_head,
            published_head=operation.superseding_head,
        )
        self._push_exact_head(push_operation, request, attempt)

    def _next_successor_branch(self, change_id: str, request: PublishChangeBranch) -> str:
        base = f"owlbear/change/{change_id}"
        references = self._run_git(
            "for-each-ref",
            "--format=%(refname)",
            "refs/heads/owlbear/change",
            f"refs/remotes/{self._remote}/owlbear/change",
        )
        if references.returncode != 0:
            self._unavailable(request, "local successor Change branches could not be observed")
        indexes = self._successor_indexes(references.stdout.decode(errors="replace"), base)
        remote_references = self._run_git("ls-remote", "--heads", self._remote)
        if remote_references.returncode != 0:
            self._unavailable(request, "remote successor Change branches could not be observed")
        indexes.update(self._successor_indexes(remote_references.stdout.decode(errors="replace"), base))
        next_index = max(indexes, default=0) + 1
        return f"{base}+s{next_index}"

    @staticmethod
    def _successor_indexes(output: str, base: str) -> set[int]:
        indexes: set[int] = set()
        pattern = re.compile(rf"^{re.escape(base)}\+s([1-9][0-9]*)$")
        for line in output.splitlines():
            fields = line.split("\t")
            reference = fields[-1]
            if reference.startswith("refs/heads/"):
                reference = reference.removeprefix("refs/heads/")
            elif reference.startswith("refs/remotes/"):
                reference = reference.removeprefix("refs/remotes/").partition("/")[2]
            else:
                continue
            match = pattern.search(reference)
            if match is None:
                continue
            indexes.add(int(match.group(1)))
        return indexes

    def _validate_prepared_operation(
        self,
        operation: _PublicationOperation,
        request: PublishChangeBranch,
        *,
        owner_id: str,
    ) -> None:
        coordination = self._coordination(request)
        if (
            coordination.writer is not None
            or coordination.branch != operation.branch
            or coordination.publication_lease is None
            or coordination.publication_lease.operation_id != operation.operation_id
            or coordination.publication_lease.owner_id != owner_id
        ):
            self._conflict(request, "prepared publication does not own the Change workspace")
        branch_head = self._resolve_commit(f"refs/heads/{operation.branch}", request)
        if branch_head != operation.published_head or branch_head != coordination.last_reviewed_commit:
            self._conflict(request, "prepared publication no longer names the reviewed boundary")
        self._require_clean_worktree(coordination.worktree_path, request)

    def _require_current_reviewed_boundary(
        self,
        operation: _PublicationOperation,
        request: PublishChangeBranch,
    ) -> None:
        coordination = self._coordination(request)
        if coordination.branch != operation.branch or coordination.last_reviewed_commit != operation.published_head:
            self._conflict(request, "published operation no longer names the reviewed boundary")

    def _fetch_change_head(
        self,
        branch: str,
        expected_head: str,
        request: PublishChangeBranch,
    ) -> None:
        branch_ref = f"refs/heads/{branch}"
        result = self._run_git(
            "fetch",
            "--no-tags",
            "--no-write-fetch-head",
            "--refmap=",
            self._remote,
            branch_ref,
        )
        if result.returncode != 0:
            if self._remote_head(branch, request) != expected_head:
                self._conflict(request, "remote Change branch changed while it was fetched", retry_safe=True)
            self._unavailable(request, "remote Change branch could not be fetched")
        if self._remote_head(branch, request) != expected_head:
            self._conflict(request, "remote Change branch changed while it was fetched", retry_safe=True)
        self._resolve_commit(expected_head, request, invalid_response=True)

    def _remote_head(self, branch: str, request: PublishChangeBranch) -> str | None:
        result = self._run_git("ls-remote", "--exit-code", "--heads", self._remote, f"refs/heads/{branch}")
        if result.returncode == _LS_REMOTE_MISSING:
            return None
        if result.returncode != 0:
            self._unavailable(request, "remote Change branch could not be observed")
        return self._parse_remote_ref(result.stdout, f"refs/heads/{branch}", request)

    def _push_exact_head(
        self,
        operation: _PublicationOperation,
        request: PublishChangeBranch,
        attempt: _PublicationAttempt,
    ) -> None:
        destination = f"refs/heads/{operation.branch}"
        try:
            result = self._run_git(
                "push",
                "--porcelain",
                self._remote,
                f"{operation.published_head}:{destination}",
            )
        except subprocess.TimeoutExpired:
            self._reconcile_failed_push(operation, request, attempt, timed_out=True, result=None)
            return
        if result.returncode == 0:
            return
        self._reconcile_failed_push(operation, request, attempt, timed_out=False, result=result)

    def _reconcile_failed_push(
        self,
        operation: _PublicationOperation,
        request: PublishChangeBranch,
        attempt: _PublicationAttempt,
        *,
        timed_out: bool,
        result: subprocess.CompletedProcess[bytes] | None,
    ) -> None:
        observed = self._remote_head(operation.branch, request)
        if observed == operation.published_head:
            return
        if observed != attempt.observed_remote_head:
            attempt.write_outcome_ambiguous = False
            self._conflict(request, "remote Change branch changed before publication", retry_safe=True)
        attempt.write_outcome_ambiguous = False
        if timed_out:
            self._failure(
                PublicationProviderFailureCode.TIMEOUT,
                request,
                "Change branch push timed out without changing the remote",
                retry_safe=True,
            )
        if result is None:
            self._failure(
                PublicationProviderFailureCode.RESPONSE_UNKNOWN,
                request,
                "Change branch push outcome could not be classified",
            )
        diagnostics = (result.stdout + result.stderr).decode(errors="replace").casefold()
        if "authentication failed" in diagnostics or "could not read username" in diagnostics:
            self._failure(
                PublicationProviderFailureCode.AUTHENTICATION_REQUIRED,
                request,
                "Change branch push requires authentication",
            )
        if "rate limit" in diagnostics or "too many requests" in diagnostics:
            self._failure(
                PublicationProviderFailureCode.RATE_LIMITED,
                request,
                "Change branch push was rate limited",
                retry_safe=True,
            )
        if "pre-receive hook declined" in diagnostics or "remote rejected" in diagnostics:
            self._conflict(request, "remote rejected the Change branch publication")
        self._failure(
            PublicationProviderFailureCode.UNAVAILABLE,
            request,
            "Change branch push failed without changing the remote",
            retry_safe=True,
        )

    def _require_clean_worktree(self, worktree: Path, request: PublishChangeBranch) -> None:
        result = subprocess.run(  # noqa: S603 - fixed Git executable and code-owned argument vector.
            (
                self._git_executable,
                "--no-optional-locks",
                "-C",
                str(worktree),
                "status",
                "--porcelain=v1",
                "-z",
                "--untracked-files=all",
            ),
            check=False,
            capture_output=True,
            env=self._git_environment,
            timeout=_GIT_TIMEOUT_SECONDS,
        )
        if result.returncode != 0:
            self._failure(
                PublicationProviderFailureCode.UNAVAILABLE,
                request,
                "Change worktree could not be inspected",
            )
        if result.stdout:
            self._conflict(request, "Change worktree must be clean before publication")

    def _is_ancestor(self, ancestor: str, descendant: str, request: PublishChangeBranch) -> bool:
        result = self._run_git("merge-base", "--is-ancestor", "--", ancestor, descendant)
        if result.returncode not in {0, 1}:
            self._failure(
                PublicationProviderFailureCode.UNAVAILABLE,
                request,
                "Git ancestry could not be inspected",
            )
        return result.returncode == 0

    def _resolve_commit(
        self,
        revision: str,
        request: PublishChangeBranch,
        *,
        invalid_response: bool = False,
    ) -> str:
        result = self._run_git("rev-parse", "--verify", "--end-of-options", f"{revision}^{{commit}}")
        if result.returncode != 0:
            code = (
                PublicationProviderFailureCode.INVALID_RESPONSE
                if invalid_response
                else PublicationProviderFailureCode.NOT_FOUND
            )
            self._failure(code, request, "required Git commit is unavailable")
        commit = result.stdout.decode(errors="replace").strip()
        if _COMMIT_PATTERN.fullmatch(commit) is None:
            self._failure(
                PublicationProviderFailureCode.INVALID_RESPONSE,
                request,
                "Git returned an invalid commit identity",
            )
        return commit

    def _run_git(self, *arguments: str) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(  # noqa: S603 - fixed Git executable and code-owned argument vectors.
            (self._git_executable, "-C", str(self._repository), *arguments),
            check=False,
            capture_output=True,
            env=self._git_environment,
            timeout=_GIT_TIMEOUT_SECONDS,
        )

    def _validate_configuration(self) -> None:
        if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]*", self._remote) is None:
            msg = "configured Git remote name is invalid"
            raise ValueError(msg)
        remotes = self._run_git("remote")
        if remotes.returncode != 0 or self._remote not in remotes.stdout.decode(errors="replace").splitlines():
            msg = "configured Git remote is unavailable"
            raise ValueError(msg)
        if self._run_git("check-ref-format", f"refs/heads/{self._target_branch}").returncode != 0:
            msg = "configured target branch is invalid"
            raise ValueError(msg)

    def _coordination(self, request: PublishChangeBranch) -> ChangeCoordination:
        try:
            return self._coordinator.show(request.change_id)
        except (CoordinationConflictError, OSError, ValueError) as exc:
            self._failure(
                PublicationProviderFailureCode.NOT_FOUND,
                request,
                "Change workspace is unavailable",
                cause=exc,
            )

    def _reserve_publication(
        self,
        request: PublishChangeBranch,
        owner_id: str,
        lock: PublicationLock,
    ) -> ChangeCoordination:
        now = datetime.now(UTC)
        expires_at = now + _PUBLICATION_LEASE_DURATION
        lease = PublicationLease(
            operation_id=request.operation_id,
            owner_id=owner_id,
            expires_at=expires_at.isoformat().replace("+00:00", "Z"),
        )
        try:
            return self._coordinator.reserve_publication(
                request.change_id,
                lease,
                lock,
                now=now.isoformat().replace("+00:00", "Z"),
            )
        except (CoordinationConflictError, OSError, ValueError) as exc:
            error = PublicationProviderError(
                PublicationProviderFailureCode.CONFLICT,
                request.operation_id,
                "Change workspace cannot be reserved for publication",
                retry_safe=False,
            )
            raise error from exc

    def _release_publication(
        self,
        operation: _PublicationOperation | _SupersessionOperation,
        owner_id: str,
        lock: PublicationLock,
    ) -> None:
        try:
            self._coordinator.release_publication(operation.change_id, operation.operation_id, owner_id, lock)
        except (CoordinationConflictError, OSError, ValueError) as exc:
            error = PublicationProviderError(
                PublicationProviderFailureCode.RESPONSE_UNKNOWN,
                operation.operation_id,
                "published Change branch ownership could not be released",
                retry_safe=False,
            )
            raise error from exc

    def _release_reserved_request(
        self,
        request: PublishChangeBranch,
        owner_id: str,
        lock: PublicationLock,
    ) -> None:
        try:
            self._coordinator.release_publication(request.change_id, request.operation_id, owner_id, lock)
        except (CoordinationConflictError, OSError, ValueError) as exc:
            error = PublicationProviderError(
                PublicationProviderFailureCode.RESPONSE_UNKNOWN,
                request.operation_id,
                "Change publication ownership could not be released",
                retry_safe=False,
            )
            raise error from exc

    def _operation_path(self, operation_id: str) -> Path:
        identity = hashlib.sha256(operation_id.encode()).hexdigest()
        return self._operation_root / f"{identity}.json"

    def _supersession_operation_path(self, operation_id: str) -> Path:
        identity = hashlib.sha256(f"supersession:{operation_id}".encode()).hexdigest()
        return self._operation_root / f"{identity}.json"

    def _read_operation(self, request: PublishChangeBranch) -> _PublicationOperation | None:
        if not self._operation_root.exists():
            return None
        with locked_roots((self._operation_root,)):
            try:
                content = self._operation_path(request.operation_id).read_bytes()
            except FileNotFoundError:
                return None
        try:
            return _PublicationOperation.model_validate_json(content)
        except ValidationError as exc:
            self._failure(
                PublicationProviderFailureCode.INVALID_RESPONSE,
                request,
                "stored publication operation is invalid",
                cause=exc,
            )

    def _bind_operation(
        self,
        operation: _PublicationOperation,
        request: PublishChangeBranch,
    ) -> _PublicationOperation:
        with locked_roots((self._operation_root,)):
            path = self._operation_path(operation.operation_id)
            try:
                content = path.read_bytes()
            except FileNotFoundError:
                try:
                    atomic_write(
                        path,
                        json.dumps(operation.model_dump(mode="json"), sort_keys=True, separators=(",", ":")) + "\n",
                    )
                except OSError as exc:
                    self._failure(
                        PublicationProviderFailureCode.UNAVAILABLE,
                        request,
                        "publication operation could not be persisted",
                        cause=exc,
                    )
                return operation
            try:
                return _PublicationOperation.model_validate_json(content)
            except ValidationError as exc:
                self._failure(
                    PublicationProviderFailureCode.INVALID_RESPONSE,
                    request,
                    "stored publication operation is invalid",
                    cause=exc,
                )

    def _read_supersession_operation(self, request: SupersedeChangeBranch) -> _SupersessionOperation | None:
        if not self._operation_root.exists():
            return None
        with locked_roots((self._operation_root,)):
            try:
                content = self._supersession_operation_path(request.operation_id).read_bytes()
            except FileNotFoundError:
                return None
        try:
            return _SupersessionOperation.model_validate_json(content)
        except ValidationError as exc:
            branch_request = PublishChangeBranch(
                change_id=request.change_id,
                expected_remote_head=None,
                operation_id=request.operation_id,
            )
            self._failure(
                PublicationProviderFailureCode.INVALID_RESPONSE,
                branch_request,
                "stored supersession operation is invalid",
                cause=exc,
            )

    def _bind_supersession_operation(
        self,
        operation: _SupersessionOperation,
        request: PublishChangeBranch,
    ) -> _SupersessionOperation:
        with locked_roots((self._operation_root,)):
            path = self._supersession_operation_path(operation.operation_id)
            try:
                content = path.read_bytes()
            except FileNotFoundError:
                try:
                    atomic_write(
                        path,
                        json.dumps(operation.model_dump(mode="json"), sort_keys=True, separators=(",", ":")) + "\n",
                    )
                except OSError as exc:
                    self._failure(
                        PublicationProviderFailureCode.UNAVAILABLE,
                        request,
                        "supersession operation could not be persisted",
                        cause=exc,
                    )
                return operation
            try:
                return _SupersessionOperation.model_validate_json(content)
            except ValidationError as exc:
                self._failure(
                    PublicationProviderFailureCode.INVALID_RESPONSE,
                    request,
                    "stored supersession operation is invalid",
                    cause=exc,
                )

    def _validate_supersession_replay(
        self,
        operation: _SupersessionOperation,
        request: SupersedeChangeBranch,
    ) -> None:
        if (
            operation.operation_id != request.operation_id
            or operation.change_id != request.change_id
            or operation.remote != self._remote
            or operation.target_branch != self._target_branch
            or operation.predecessor_branch != request.expected_published_branch
            or operation.predecessor_head != request.expected_published_head
            or operation.superseding_head != request.superseding_head
        ):
            branch_request = PublishChangeBranch(
                change_id=request.change_id,
                expected_remote_head=None,
                operation_id=request.operation_id,
            )
            self._conflict(branch_request, "supersession inputs differ from the stored operation")

    def _supersession_receipt(self, operation: _SupersessionOperation) -> ChangeBranchSupersessionReceipt:
        digest_input = json.dumps(
            operation.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
        )
        return ChangeBranchSupersessionReceipt(
            receipt_id=hashlib.sha256(digest_input.encode()).hexdigest(),
            operation_id=operation.operation_id,
            change_id=operation.change_id,
            remote=operation.remote,
            predecessor_branch=operation.predecessor_branch,
            predecessor_head=operation.predecessor_head,
            successor_branch=operation.successor_branch,
            superseding_head=operation.superseding_head,
            target_branch=operation.target_branch,
        )

    def _validate_replay(self, operation: _PublicationOperation, request: PublishChangeBranch) -> None:
        if (
            operation.operation_id != request.operation_id
            or operation.change_id != request.change_id
            or operation.branch != f"owlbear/change/{operation.change_id}"
            or request.expected_remote_head not in {operation.expected_remote_head, operation.published_head}
            or (
                request.expected_published_head is not None
                and operation.published_head != request.expected_published_head
            )
            or operation.remote != self._remote
            or operation.target_branch != self._target_branch
        ):
            self._conflict(request, "publication operation inputs differ from the stored operation")

    def _parse_remote_ref(self, output: bytes, reference: str, request: PublishChangeBranch) -> str:
        try:
            lines = output.decode().splitlines()
        except UnicodeDecodeError as exc:
            self._failure(
                PublicationProviderFailureCode.INVALID_RESPONSE,
                request,
                "remote returned invalid ref data",
                cause=exc,
            )
        if len(lines) != 1:
            self._failure(
                PublicationProviderFailureCode.INVALID_RESPONSE,
                request,
                "remote returned an ambiguous ref response",
            )
        fields = lines[0].split("\t")
        if (
            len(fields) != _REMOTE_REF_FIELD_COUNT
            or fields[1] != reference
            or _COMMIT_PATTERN.fullmatch(fields[0]) is None
        ):
            self._failure(
                PublicationProviderFailureCode.INVALID_RESPONSE,
                request,
                "remote returned an invalid ref response",
            )
        return fields[0]

    def _receipt(self, operation: _PublicationOperation) -> ChangeBranchPublicationReceipt:
        digest_input = json.dumps(
            operation.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
        )
        return ChangeBranchPublicationReceipt(
            receipt_id=hashlib.sha256(digest_input.encode()).hexdigest(),
            operation_id=operation.operation_id,
            change_id=operation.change_id,
            remote=operation.remote,
            branch=operation.branch,
            target_branch=operation.target_branch,
            expected_remote_head=operation.expected_remote_head,
            published_head=operation.published_head,
        )

    @staticmethod
    def _conflict(request: PublishChangeBranch, detail: str, *, retry_safe: bool = False) -> NoReturn:
        raise PublicationProviderError(
            PublicationProviderFailureCode.CONFLICT,
            request.operation_id,
            detail,
            retry_safe=retry_safe,
        )

    @staticmethod
    def _unavailable(request: PublishChangeBranch, detail: str) -> NoReturn:
        raise PublicationProviderError(
            PublicationProviderFailureCode.UNAVAILABLE,
            request.operation_id,
            detail,
            retry_safe=True,
        )

    @staticmethod
    def _failure(
        code: PublicationProviderFailureCode,
        request: PublishChangeBranch,
        detail: str,
        *,
        retry_safe: bool = False,
        cause: Exception | None = None,
    ) -> NoReturn:
        error = PublicationProviderError(code, request.operation_id, detail, retry_safe=retry_safe)
        raise error from cause
