"""Change-branch-only publication through fixed Git operations."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from typing import TYPE_CHECKING, Literal, NoReturn

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from owlbear_delivery.change_workspace import CoordinationConflictError
from owlbear_delivery.git_executable import resolve_git_executable
from owlbear_delivery.identities import ChangeId
from owlbear_delivery.publication_provider import (
    PublicationProviderError,
    PublicationProviderFailureCode,
)
from owlbear_delivery.storage_io import atomic_write, locked_roots

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear_delivery.change_workspace import ChangeCoordination, PortfolioCoordinator

_COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}")
_LS_REMOTE_MISSING = 2
_REMOTE_REF_FIELD_COUNT = 2


class _PublicationModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class PublishChangeBranch(_PublicationModel):
    """Exact preconditions for one replayable Change-branch checkpoint."""

    change_id: ChangeId
    expected_remote_head: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
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
    target_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    expected_remote_head: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    published_head: str = Field(pattern=r"^[0-9a-f]{40}$")


class _PublicationOperation(_PublicationModel):
    schema_version: Literal[1] = 1
    operation_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
    change_id: ChangeId
    remote: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")
    branch: str = Field(pattern=r"^owlbear/change/[a-z0-9]+(?:-[a-z0-9]+)*$")
    target_branch: str = Field(min_length=1)
    target_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    expected_remote_head: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    published_head: str = Field(pattern=r"^[0-9a-f]{40}$")


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
        self._operation_root = operation_root
        self._validate_configuration()

    def publish(self, request: PublishChangeBranch) -> ChangeBranchPublicationReceipt:
        """Publish or reconcile one exact reviewed Change branch checkpoint."""
        try:
            with locked_roots((self._operation_root,)):
                operation = self._read_operation(request)
                if operation is not None:
                    self._validate_replay(operation, request)
                    if self._remote_head(operation.branch, request) == operation.published_head:
                        return self._receipt(operation)
                else:
                    operation = self._prepare_operation(request)
                    self._write_operation(operation, request)

                self._validate_prepared_operation(operation, request)
                remote_head = self._remote_head(operation.branch, request)
                if remote_head != operation.expected_remote_head:
                    self._conflict(request, "remote Change branch differs from the expected head", retry_safe=True)
                if remote_head is not None and not self._is_ancestor(remote_head, operation.published_head, request):
                    self._conflict(request, "remote Change branch cannot fast-forward to the reviewed head")
                self._push_exact_head(operation, request)
                if self._remote_head(operation.branch, request) != operation.published_head:
                    self._failure(
                        PublicationProviderFailureCode.RESPONSE_UNKNOWN,
                        request,
                        "remote Change branch does not expose the published head",
                    )
                return self._receipt(operation)
        except PublicationProviderError:
            raise
        except (OSError, ValueError) as exc:
            error = PublicationProviderError(
                PublicationProviderFailureCode.UNAVAILABLE,
                request.operation_id,
                "Change publication state is unavailable",
                retry_safe=False,
            )
            raise error from exc

    def _prepare_operation(self, request: PublishChangeBranch) -> _PublicationOperation:
        coordination = self._coordination(request)
        expected_branch = f"owlbear/change/{request.change_id}"
        if coordination.branch != expected_branch or coordination.writer is not None:
            self._conflict(request, "Change branch publication requires one idle canonical workspace")
        branch_head = self._resolve_commit(f"refs/heads/{coordination.branch}", request)
        if branch_head != coordination.last_reviewed_commit:
            self._conflict(request, "Change branch head differs from the reviewed boundary")
        self._require_clean_worktree(coordination.worktree_path, request)
        target_head = self._fetch_target(request)
        if not self._is_ancestor(target_head, branch_head, request):
            self._conflict(request, "fresh remote target is not an ancestor of the reviewed Change head")
        return _PublicationOperation(
            operation_id=request.operation_id,
            change_id=request.change_id,
            remote=self._remote,
            branch=coordination.branch,
            target_branch=self._target_branch,
            target_head=target_head,
            expected_remote_head=request.expected_remote_head,
            published_head=branch_head,
        )

    def _validate_prepared_operation(
        self,
        operation: _PublicationOperation,
        request: PublishChangeBranch,
    ) -> None:
        coordination = self._coordination(request)
        if coordination.writer is not None or coordination.branch != operation.branch:
            self._conflict(request, "prepared publication requires one idle canonical workspace")
        branch_head = self._resolve_commit(f"refs/heads/{operation.branch}", request)
        if branch_head != operation.published_head or branch_head != coordination.last_reviewed_commit:
            self._conflict(request, "prepared publication no longer names the reviewed boundary")
        self._require_clean_worktree(coordination.worktree_path, request)
        if self._fetch_target(request) != operation.target_head:
            self._conflict(request, "remote target changed after publication preparation", retry_safe=True)

    def _fetch_target(self, request: PublishChangeBranch) -> str:
        target_ref = f"refs/heads/{self._target_branch}"
        target_head = self._remote_ref(target_ref, request)
        result = self._run_git(
            "fetch",
            "--no-tags",
            "--no-write-fetch-head",
            "--refmap=",
            self._remote,
            target_ref,
        )
        if result.returncode != 0:
            self._unavailable(request, "configured target could not be fetched")
        self._resolve_commit(target_head, request, invalid_response=True)
        if self._remote_ref(target_ref, request) != target_head:
            self._conflict(request, "remote target changed while it was fetched", retry_safe=True)
        return target_head

    def _remote_head(self, branch: str, request: PublishChangeBranch) -> str | None:
        result = self._run_git("ls-remote", "--exit-code", "--heads", self._remote, f"refs/heads/{branch}")
        if result.returncode == _LS_REMOTE_MISSING:
            return None
        if result.returncode != 0:
            self._unavailable(request, "remote Change branch could not be observed")
        return self._parse_remote_ref(result.stdout, f"refs/heads/{branch}", request)

    def _remote_ref(self, reference: str, request: PublishChangeBranch) -> str:
        result = self._run_git("ls-remote", "--exit-code", "--heads", self._remote, reference)
        if result.returncode == _LS_REMOTE_MISSING:
            self._failure(
                PublicationProviderFailureCode.NOT_FOUND,
                request,
                "required remote ref is unavailable",
            )
        if result.returncode != 0:
            self._unavailable(request, "remote ref could not be observed")
        return self._parse_remote_ref(result.stdout, reference, request)

    def _push_exact_head(
        self,
        operation: _PublicationOperation,
        request: PublishChangeBranch,
    ) -> None:
        destination = f"refs/heads/{operation.branch}"
        lease_head = operation.expected_remote_head or ""
        result = self._run_git(
            "push",
            "--porcelain",
            f"--force-with-lease={destination}:{lease_head}",
            self._remote,
            f"{operation.published_head}:{destination}",
        )
        if result.returncode == 0:
            return
        observed = self._remote_head(operation.branch, request)
        if observed == operation.published_head:
            return
        if observed != operation.expected_remote_head:
            self._conflict(request, "remote Change branch changed before publication", retry_safe=True)
        self._failure(
            PublicationProviderFailureCode.RESPONSE_UNKNOWN,
            request,
            "Change branch push failed without a matching remote read-back",
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

    def _operation_path(self, operation_id: str) -> Path:
        identity = hashlib.sha256(operation_id.encode()).hexdigest()
        return self._operation_root / f"{identity}.json"

    def _read_operation(self, request: PublishChangeBranch) -> _PublicationOperation | None:
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

    def _write_operation(self, operation: _PublicationOperation, request: PublishChangeBranch) -> None:
        try:
            atomic_write(
                self._operation_path(operation.operation_id),
                json.dumps(operation.model_dump(mode="json"), sort_keys=True, separators=(",", ":")) + "\n",
            )
        except OSError as exc:
            self._failure(
                PublicationProviderFailureCode.UNAVAILABLE,
                request,
                "publication operation could not be persisted",
                cause=exc,
            )

    def _validate_replay(self, operation: _PublicationOperation, request: PublishChangeBranch) -> None:
        if (
            operation.operation_id != request.operation_id
            or operation.change_id != request.change_id
            or operation.branch != f"owlbear/change/{operation.change_id}"
            or operation.expected_remote_head != request.expected_remote_head
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
            target_head=operation.target_head,
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
