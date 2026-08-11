"""Idempotent draft pull-request creation for published Change branches."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from owlbear_delivery.publication_provider import (
    CreateDraftPublicationPullRequest,
    FindPublicationPullRequest,
    PublicationProvider,
    PublicationProviderError,
    PublicationProviderFailureCode,
    PublicationPullRequest,
)
from owlbear_delivery.storage_io import atomic_write, locked_roots

if TYPE_CHECKING:
    from pathlib import Path

_CHANGE_ID_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
_OPERATION_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$"
_SHA_PATTERN = r"^[0-9a-f]{40}$"
_GENERATED_START = "<!-- owlbear-generated:start -->"
_GENERATED_END = "<!-- owlbear-generated:end -->"


class _DraftPullRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class CreateOrReconcileDraftPullRequest(_DraftPullRequestModel):
    """Bind one stable operation to the first published Change checkpoint."""

    change_id: str = Field(pattern=_CHANGE_ID_PATTERN)
    operation_id: str = Field(pattern=_OPERATION_ID_PATTERN)
    published_head: str = Field(pattern=_SHA_PATTERN)
    title: str = Field(min_length=1, max_length=256)
    generated_summary: str = Field(min_length=1, max_length=50_000)


class DraftPullRequestPublicationReceipt(_DraftPullRequestModel):
    """Immutable local binding to one provider-observed draft pull request."""

    schema_version: Literal[1] = 1
    receipt_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    operation_id: str = Field(pattern=_OPERATION_ID_PATTERN)
    change_id: str = Field(pattern=_CHANGE_ID_PATTERN)
    repository: str = Field(min_length=3, pattern=r"^[^\s/]+/[^\s/]+$")
    number: int = Field(gt=0)
    node_id: str = Field(min_length=1)
    head_branch: str = Field(min_length=1)
    head_sha: str = Field(pattern=_SHA_PATTERN)
    base_branch: str = Field(min_length=1)
    provider_evidence_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _validate_receipt_id(self) -> DraftPullRequestPublicationReceipt:
        payload = self.model_dump(mode="json", exclude={"receipt_id"})
        if self.receipt_id != _digest(payload):
            msg = "draft pull-request receipt identity is invalid"
            raise ValueError(msg)
        return self


class _DraftPullRequestOperation(_DraftPullRequestModel):
    schema_version: Literal[1] = 1
    operation_id: str = Field(pattern=_OPERATION_ID_PATTERN)
    change_id: str = Field(pattern=_CHANGE_ID_PATTERN)
    repository: str = Field(min_length=3, pattern=r"^[^\s/]+/[^\s/]+$")
    head_branch: str = Field(min_length=1)
    head_sha: str = Field(pattern=_SHA_PATTERN)
    base_branch: str = Field(min_length=1)
    title: str = Field(min_length=1, max_length=256)
    body: str = Field(min_length=1, max_length=65_536)


class DraftPullRequestPublisher:
    """Create or reconcile one exact draft PR without provider transport knowledge."""

    def __init__(
        self,
        provider: PublicationProvider,
        *,
        repository: str,
        target_branch: str,
        state_root: Path,
    ) -> None:
        self._provider = provider
        self._repository = repository
        self._target_branch = target_branch
        self._state_root = state_root.resolve()
        if state_root.is_symlink():
            msg = "draft pull-request state root must not be a symlink"
            raise ValueError(msg)

    def publish(self, request: CreateOrReconcileDraftPullRequest) -> DraftPullRequestPublicationReceipt:
        """Create or recover the unique draft PR for one first checkpoint."""
        lock_root = self._state_root / "locks" / request.change_id
        with locked_roots((lock_root,)):
            return self._publish_locked(request)

    def _publish_locked(
        self,
        request: CreateOrReconcileDraftPullRequest,
    ) -> DraftPullRequestPublicationReceipt:
        operation = self._bind_operation(self._operation(request), request)
        existing = self._read_receipt(request)
        if existing is not None:
            self._validate_receipt(existing, operation, request)
            return existing

        repository = self._provider.read_repository(self._repository)
        if repository.repository != self._repository:
            self._invalid_response(request, "provider returned a different repository identity")
        pull_request = self._find(operation)
        if pull_request is None:
            pull_request = self._create_or_reconcile(operation)
        self._validate_pull_request(pull_request, operation, request)
        return self._bind_receipt(self._receipt(operation, pull_request), request)

    def _operation(self, request: CreateOrReconcileDraftPullRequest) -> _DraftPullRequestOperation:
        marker = _change_marker(request.change_id)
        summary = request.generated_summary.rstrip()
        body = f"{marker}\n\n{_GENERATED_START}\n{summary}\n{_GENERATED_END}\n"
        return _DraftPullRequestOperation(
            operation_id=request.operation_id,
            change_id=request.change_id,
            repository=self._repository,
            head_branch=f"owlbear/change/{request.change_id}",
            head_sha=request.published_head,
            base_branch=self._target_branch,
            title=request.title,
            body=body,
        )

    def _find(self, operation: _DraftPullRequestOperation) -> PublicationPullRequest | None:
        return self._provider.find_pull_request(
            FindPublicationPullRequest(
                repository=operation.repository,
                head_branch=operation.head_branch,
                base_branch=operation.base_branch,
            )
        )

    def _create_or_reconcile(
        self,
        operation: _DraftPullRequestOperation,
    ) -> PublicationPullRequest:
        try:
            return self._provider.create_draft_pull_request(
                CreateDraftPublicationPullRequest(
                    repository=operation.repository,
                    head_branch=operation.head_branch,
                    head_sha=operation.head_sha,
                    base_branch=operation.base_branch,
                    title=operation.title,
                    body=operation.body,
                )
            )
        except PublicationProviderError as exc:
            if exc.code not in {
                PublicationProviderFailureCode.CONFLICT,
                PublicationProviderFailureCode.RESPONSE_UNKNOWN,
            }:
                raise
            reconciled = self._find(operation)
            if reconciled is not None:
                return reconciled
            raise

    def _validate_pull_request(
        self,
        pull_request: PublicationPullRequest,
        operation: _DraftPullRequestOperation,
        request: CreateOrReconcileDraftPullRequest,
    ) -> None:
        if (
            pull_request.repository != operation.repository
            or pull_request.head_branch != operation.head_branch
            or pull_request.head_sha != operation.head_sha
            or pull_request.base_branch != operation.base_branch
            or pull_request.state != "open"
            or pull_request.merged
            or not pull_request.draft
        ):
            self._conflict(request, "provider pull request does not match the draft publication identity")
        marker = _change_marker(operation.change_id)
        if pull_request.body.count(marker) != 1:
            self._conflict(request, "provider pull request does not contain the exact Change marker")

    def _receipt(
        self,
        operation: _DraftPullRequestOperation,
        pull_request: PublicationPullRequest,
    ) -> DraftPullRequestPublicationReceipt:
        payload = {
            "schema_version": 1,
            "operation_id": operation.operation_id,
            "change_id": operation.change_id,
            "repository": pull_request.repository,
            "number": pull_request.number,
            "node_id": pull_request.node_id,
            "head_branch": pull_request.head_branch,
            "head_sha": pull_request.head_sha,
            "base_branch": pull_request.base_branch,
            "provider_evidence_digest": _digest(pull_request.model_dump(mode="json")),
        }
        return DraftPullRequestPublicationReceipt(receipt_id=_digest(payload), **payload)

    def _bind_operation(
        self,
        operation: _DraftPullRequestOperation,
        request: CreateOrReconcileDraftPullRequest,
    ) -> _DraftPullRequestOperation:
        path = self._path("operations", request.change_id)
        existing = self._publish_or_read(path, operation, _DraftPullRequestOperation, request)
        if existing != operation:
            self._conflict(request, "draft pull-request operation differs from the stored operation")
        return existing

    def _read_receipt(
        self,
        request: CreateOrReconcileDraftPullRequest,
    ) -> DraftPullRequestPublicationReceipt | None:
        path = self._path("receipts", request.change_id)
        with locked_roots((self._state_root,)):
            self._reject_symlink(path, request)
            try:
                content = path.read_bytes()
            except FileNotFoundError:
                return None
        try:
            return DraftPullRequestPublicationReceipt.model_validate_json(content)
        except ValidationError as exc:
            self._invalid_response(request, "stored draft pull-request receipt is invalid", cause=exc)

    def _bind_receipt(
        self,
        receipt: DraftPullRequestPublicationReceipt,
        request: CreateOrReconcileDraftPullRequest,
    ) -> DraftPullRequestPublicationReceipt:
        path = self._path("receipts", request.change_id)
        existing = self._publish_or_read(path, receipt, DraftPullRequestPublicationReceipt, request)
        if existing != receipt:
            self._conflict(request, "Change is already bound to a different pull request")
        return existing

    def _publish_or_read[ModelT: _DraftPullRequestModel](
        self,
        path: Path,
        model: ModelT,
        model_type: type[ModelT],
        request: CreateOrReconcileDraftPullRequest,
    ) -> ModelT:
        with locked_roots((self._state_root,)):
            self._require_directory(path.parent)
            self._reject_symlink(path, request)
            try:
                content = path.read_bytes()
            except FileNotFoundError:
                try:
                    atomic_write(path, model.model_dump_json(indent=2) + "\n")
                except OSError as exc:
                    self._unavailable(request, "draft pull-request state could not be persisted", cause=exc)
                return model
        try:
            return model_type.model_validate_json(content)
        except ValidationError as exc:
            self._invalid_response(request, "stored draft pull-request state is invalid", cause=exc)

    def _validate_receipt(
        self,
        receipt: DraftPullRequestPublicationReceipt,
        operation: _DraftPullRequestOperation,
        request: CreateOrReconcileDraftPullRequest,
    ) -> None:
        if (
            receipt.operation_id != operation.operation_id
            or receipt.change_id != operation.change_id
            or receipt.repository != operation.repository
            or receipt.head_branch != operation.head_branch
            or receipt.head_sha != operation.head_sha
            or receipt.base_branch != operation.base_branch
        ):
            self._conflict(request, "stored draft pull-request receipt differs from the operation")

    def _path(self, kind: str, change_id: str) -> Path:
        return self._state_root / kind / f"{change_id}.json"

    @staticmethod
    def _require_directory(path: Path) -> None:
        if path.is_symlink():
            msg = "draft pull-request state directory must not be a symlink"
            raise ValueError(msg)
        path.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _reject_symlink(path: Path, request: CreateOrReconcileDraftPullRequest) -> None:
        if path.is_symlink():
            DraftPullRequestPublisher._invalid_response(
                request,
                "draft pull-request state file must not be a symlink",
            )

    @staticmethod
    def _conflict(request: CreateOrReconcileDraftPullRequest, detail: str) -> None:
        raise PublicationProviderError(
            PublicationProviderFailureCode.CONFLICT,
            request.operation_id,
            detail,
            retry_safe=False,
        )

    @staticmethod
    def _invalid_response(
        request: CreateOrReconcileDraftPullRequest,
        detail: str,
        *,
        cause: Exception | None = None,
    ) -> None:
        error = PublicationProviderError(
            PublicationProviderFailureCode.INVALID_RESPONSE,
            request.operation_id,
            detail,
            retry_safe=False,
        )
        raise error from cause

    @staticmethod
    def _unavailable(
        request: CreateOrReconcileDraftPullRequest,
        detail: str,
        *,
        cause: Exception,
    ) -> None:
        error = PublicationProviderError(
            PublicationProviderFailureCode.UNAVAILABLE,
            request.operation_id,
            detail,
            retry_safe=True,
        )
        raise error from cause


def _change_marker(change_id: str) -> str:
    return f"<!-- owlbear-change:{change_id} -->"


def _digest(payload: object) -> str:
    content = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(content.encode()).hexdigest()
