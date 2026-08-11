"""Change-branch-only publication through fixed Git operations."""

from __future__ import annotations

import hashlib
import subprocess
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Literal, NoReturn

from pydantic import BaseModel, ConfigDict, Field

from owlbear_delivery.git_executable import resolve_git_executable
from owlbear_delivery.identities import ChangeId

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear_delivery.change_workspace import PortfolioCoordinator

_ZERO_COMMIT = "0" * 40
_LS_REMOTE_MISSING = 2
_LS_REMOTE_FIELD_COUNT = 2


class _PublicationModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class PublishChangeBranch(_PublicationModel):
    """Exact preconditions for one replayable Change-branch checkpoint."""

    change_id: ChangeId
    expected_remote_head: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    operation_id: str = Field(min_length=1)


class ChangeBranchPublicationReceipt(_PublicationModel):
    """Provider-independent evidence for one exact remote Change branch head."""

    schema_version: Literal[1] = 1
    receipt_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    operation_id: str = Field(min_length=1)
    change_id: ChangeId
    remote: str = Field(min_length=1)
    branch: str = Field(min_length=1)
    target_branch: str = Field(min_length=1)
    target_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    expected_remote_head: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    published_head: str = Field(pattern=r"^[0-9a-f]{40}$")


class ChangePublicationFailureCode(StrEnum):
    """Stable Change publication failure codes."""

    CONFLICT = "conflict"
    RESPONSE_UNKNOWN = "response_unknown"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class _ReceiptValues:
    branch: str
    target_head: str
    expected_remote_head: str | None
    published_head: str


class ChangePublicationError(RuntimeError):
    """Typed failure that never grants target or arbitrary-ref authority."""

    __slots__ = ("code", "operation_id", "retry_safe")

    def __init__(self, code: str, operation_id: str, detail: str, *, retry_safe: bool) -> None:
        self.code = code
        self.operation_id = operation_id
        self.retry_safe = retry_safe
        super().__init__(detail)


class ChangeBranchPublisher:
    """Publish one reviewed Change head to its same-named remote branch."""

    def __init__(
        self,
        repository: Path,
        coordinator: PortfolioCoordinator,
        *,
        remote: str,
        target_branch: str,
    ) -> None:
        self._repository = repository.resolve()
        self._coordinator = coordinator
        self._remote = remote
        self._target_branch = target_branch
        self._git("check-ref-format", f"refs/remotes/{remote}/{target_branch}")

    def publish(self, request: PublishChangeBranch) -> ChangeBranchPublicationReceipt:
        """Publish or reconcile one exact reviewed Change branch checkpoint."""
        coordination = self._coordinator.show(request.change_id)
        expected_branch = f"owlbear/change/{request.change_id}"
        if coordination.branch != expected_branch or coordination.writer is not None:
            self._conflict(request, "Change branch publication requires one idle canonical workspace")
        branch_head = self._resolve(f"refs/heads/{coordination.branch}")
        if branch_head != coordination.last_reviewed_commit:
            self._conflict(request, "Change branch head differs from the reviewed boundary")
        self._require_clean_worktree(coordination.worktree_path, request)

        target_head = self._fetch_target(request)
        if not self._is_ancestor(target_head, branch_head):
            self._conflict(request, "fresh remote target is not an ancestor of the reviewed Change head")

        remote_head = self._remote_head(coordination.branch, request)
        if remote_head == branch_head:
            return self._receipt(
                request,
                _ReceiptValues(coordination.branch, target_head, request.expected_remote_head, branch_head),
            )
        if remote_head != request.expected_remote_head:
            self._conflict(request, "remote Change branch differs from the expected head")
        if remote_head is not None and not self._is_ancestor(remote_head, branch_head):
            self._conflict(request, "remote Change branch cannot fast-forward to the reviewed head")

        self._push_exact_head(coordination.branch, branch_head, remote_head, request)
        observed_head = self._remote_head(coordination.branch, request)
        if observed_head != branch_head:
            raise ChangePublicationError(
                ChangePublicationFailureCode.RESPONSE_UNKNOWN,
                request.operation_id,
                "remote Change branch does not expose the published head",
                retry_safe=False,
            )
        return self._receipt(
            request,
            _ReceiptValues(coordination.branch, target_head, request.expected_remote_head, branch_head),
        )

    def _fetch_target(self, request: PublishChangeBranch) -> str:
        result = self._run_git(
            "ls-remote",
            "--exit-code",
            "--heads",
            self._remote,
            f"refs/heads/{self._target_branch}",
        )
        if result.returncode != 0:
            self._unavailable(request, "configured target could not be observed")
        fields = result.stdout.decode().split()
        if len(fields) != _LS_REMOTE_FIELD_COUNT or fields[1] != f"refs/heads/{self._target_branch}":
            self._unavailable(request, "configured target response is malformed")
        target_head = fields[0]
        result = self._run_git(
            "fetch",
            "--no-tags",
            "--no-write-fetch-head",
            self._remote,
            target_head,
        )
        if result.returncode != 0:
            self._unavailable(request, "configured target could not be fetched")
        try:
            return self._resolve(target_head)
        except RuntimeError:
            self._unavailable(request, "configured target object is unavailable after fetch")

    def _remote_head(self, branch: str, request: PublishChangeBranch) -> str | None:
        result = self._run_git("ls-remote", "--exit-code", "--heads", self._remote, f"refs/heads/{branch}")
        if result.returncode == _LS_REMOTE_MISSING:
            return None
        if result.returncode != 0:
            self._unavailable(request, "remote Change branch could not be observed")
        fields = result.stdout.decode().split()
        if len(fields) != _LS_REMOTE_FIELD_COUNT or fields[1] != f"refs/heads/{branch}":
            self._unavailable(request, "remote Change branch response is malformed")
        return fields[0]

    def _push_exact_head(
        self,
        branch: str,
        head: str,
        expected_remote_head: str | None,
        request: PublishChangeBranch,
    ) -> None:
        destination = f"refs/heads/{branch}"
        lease_head = expected_remote_head or _ZERO_COMMIT
        result = self._run_git(
            "push",
            "--porcelain",
            f"--force-with-lease={destination}:{lease_head}",
            self._remote,
            f"{head}:{destination}",
        )
        if result.returncode == 0:
            return
        observed = self._remote_head(branch, request)
        if observed == head:
            return
        raise ChangePublicationError(
            ChangePublicationFailureCode.RESPONSE_UNKNOWN,
            request.operation_id,
            "Change branch push failed without a matching remote read-back",
            retry_safe=False,
        )

    def _require_clean_worktree(self, worktree: Path, request: PublishChangeBranch) -> None:
        if self._git("-C", str(worktree), "status", "--porcelain"):
            self._conflict(request, "Change worktree must be clean before publication")

    def _is_ancestor(self, ancestor: str, descendant: str) -> bool:
        return self._run_git("merge-base", "--is-ancestor", ancestor, descendant).returncode == 0

    def _resolve(self, revision: str) -> str:
        return self._git("rev-parse", "--verify", f"{revision}^{{commit}}")

    def _git(self, *arguments: str) -> str:
        result = self._run_git(*arguments)
        if result.returncode != 0:
            message = result.stderr.decode(errors="replace").strip() or "Git operation failed"
            raise RuntimeError(message)
        return result.stdout.decode().strip()

    def _run_git(self, *arguments: str) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(  # noqa: S603 - fixed Git executable and code-owned argument vectors.
            (resolve_git_executable(), "-C", str(self._repository), *arguments),
            check=False,
            capture_output=True,
        )

    def _receipt(
        self,
        request: PublishChangeBranch,
        values: _ReceiptValues,
    ) -> ChangeBranchPublicationReceipt:
        digest_input = "\0".join(
            (
                request.operation_id,
                request.change_id,
                self._remote,
                values.branch,
                self._target_branch,
                values.target_head,
                values.expected_remote_head or _ZERO_COMMIT,
                values.published_head,
            )
        )
        return ChangeBranchPublicationReceipt(
            receipt_id=hashlib.sha256(digest_input.encode()).hexdigest(),
            operation_id=request.operation_id,
            change_id=request.change_id,
            remote=self._remote,
            branch=values.branch,
            target_branch=self._target_branch,
            target_head=values.target_head,
            expected_remote_head=values.expected_remote_head,
            published_head=values.published_head,
        )

    @staticmethod
    def _conflict(request: PublishChangeBranch, detail: str) -> NoReturn:
        raise ChangePublicationError(
            ChangePublicationFailureCode.CONFLICT,
            request.operation_id,
            detail,
            retry_safe=False,
        )

    @staticmethod
    def _unavailable(request: PublishChangeBranch, detail: str) -> NoReturn:
        raise ChangePublicationError(
            ChangePublicationFailureCode.UNAVAILABLE,
            request.operation_id,
            detail,
            retry_safe=True,
        )
