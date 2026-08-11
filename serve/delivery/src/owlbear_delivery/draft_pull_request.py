"""Idempotent draft pull-request creation for published Change branches."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Literal, Never

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from owlbear_delivery.publication_provider import (
    CreateDraftPublicationPullRequest,
    FindPublicationPullRequest,
    ObservePublicationChecks,
    PublicationCheckSnapshot,
    PublicationProvider,
    PublicationProviderError,
    PublicationProviderFailureCode,
    PublicationPullRequest,
    UpdatePublicationPullRequest,
)
from owlbear_delivery.storage_io import atomic_write, locked_roots

if TYPE_CHECKING:
    from pathlib import Path

_CHANGE_ID_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
_OPERATION_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$"
_SHA_PATTERN = r"^[0-9a-f]{40}$"
_GENERATED_START = "<!-- owlbear-generated:start -->"
_GENERATED_END = "<!-- owlbear-generated:end -->"
_MAX_PULL_REQUEST_BODY_LENGTH = 65_536


class _DraftPullRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class CreateOrReconcileDraftPullRequest(_DraftPullRequestModel):
    """Bind one stable operation to the first published Change checkpoint."""

    change_id: str = Field(pattern=_CHANGE_ID_PATTERN)
    operation_id: str = Field(pattern=_OPERATION_ID_PATTERN)
    published_head: str = Field(pattern=_SHA_PATTERN)
    title: str = Field(min_length=1, max_length=256)
    generated_summary: str = Field(min_length=1, max_length=50_000)

    @model_validator(mode="after")
    def _validate_generated_summary(self) -> CreateOrReconcileDraftPullRequest:
        _require_safe_generated_summary(self.generated_summary)
        return self


class UpdateGeneratedPullRequestSummary(_DraftPullRequestModel):
    """Replace only OwlBear's generated block at one published Change head."""

    change_id: str = Field(pattern=_CHANGE_ID_PATTERN)
    operation_id: str = Field(pattern=_OPERATION_ID_PATTERN)
    published_head: str = Field(pattern=_SHA_PATTERN)
    generated_summary: str = Field(min_length=1, max_length=50_000)

    @model_validator(mode="after")
    def _validate_generated_summary(self) -> UpdateGeneratedPullRequestSummary:
        _require_safe_generated_summary(self.generated_summary)
        return self


class ObserveChangePublicationChecks(_DraftPullRequestModel):
    """Observe provider checks for one Change-bound published head."""

    change_id: str = Field(pattern=_CHANGE_ID_PATTERN)
    published_head: str = Field(pattern=_SHA_PATTERN)


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


class GeneratedPullRequestSummaryReceipt(_DraftPullRequestModel):
    """Immutable evidence of one exact generated-block update."""

    schema_version: Literal[1] = 1
    receipt_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    operation_id: str = Field(pattern=_OPERATION_ID_PATTERN)
    change_id: str = Field(pattern=_CHANGE_ID_PATTERN)
    repository: str = Field(min_length=3, pattern=r"^[^\s/]+/[^\s/]+$")
    number: int = Field(gt=0)
    head_sha: str = Field(pattern=_SHA_PATTERN)
    body_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    provider_evidence_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _validate_receipt_id(self) -> GeneratedPullRequestSummaryReceipt:
        payload = self.model_dump(mode="json", exclude={"receipt_id"})
        if self.receipt_id != _digest(payload):
            msg = "generated pull-request summary receipt identity is invalid"
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
    body: str = Field(min_length=1, max_length=_MAX_PULL_REQUEST_BODY_LENGTH)


class _GeneratedSummaryOperation(_DraftPullRequestModel):
    schema_version: Literal[1] = 1
    operation_id: str = Field(pattern=_OPERATION_ID_PATTERN)
    change_id: str = Field(pattern=_CHANGE_ID_PATTERN)
    repository: str = Field(min_length=3, pattern=r"^[^\s/]+/[^\s/]+$")
    number: int = Field(gt=0)
    node_id: str = Field(min_length=1)
    head_branch: str = Field(min_length=1)
    head_sha: str = Field(pattern=_SHA_PATTERN)
    base_branch: str = Field(min_length=1)
    expected_title: str = Field(min_length=1)
    expected_body: str
    desired_body: str = Field(max_length=_MAX_PULL_REQUEST_BODY_LENGTH)
    generated_summary_digest: str = Field(pattern=r"^[0-9a-f]{64}$")


type _PublicationRequest = (
    CreateOrReconcileDraftPullRequest | ObserveChangePublicationChecks | UpdateGeneratedPullRequestSummary
)


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

    def update_generated_summary(
        self,
        request: UpdateGeneratedPullRequestSummary,
    ) -> GeneratedPullRequestSummaryReceipt:
        """Replace or reconcile one generated PR summary without changing user prose."""
        lock_root = self._state_root / "locks" / request.change_id
        with locked_roots((lock_root,)):
            return self._update_generated_summary_locked(request)

    def observe_checks(self, request: ObserveChangePublicationChecks) -> PublicationCheckSnapshot:
        """Observe checks for the exact PR and head bound to one Change."""
        publication = self._read_receipt(request)
        if publication is None:
            self._conflict(request, "Change has no draft pull-request publication receipt")
        current = self._provider.read_pull_request(publication.repository, publication.number)
        self._validate_publication_identity(current, publication, request)
        snapshot = self._provider.observe_checks(
            ObservePublicationChecks(
                repository=publication.repository,
                number=publication.number,
                expected_head_sha=request.published_head,
            )
        )
        if (
            snapshot.repository != publication.repository
            or snapshot.number != publication.number
            or snapshot.head_sha != request.published_head
        ):
            self._invalid_response(request, "provider returned checks for a different publication identity")
        observed = self._provider.read_pull_request(publication.repository, publication.number)
        self._validate_publication_identity(observed, publication, request)
        return snapshot

    def _update_generated_summary_locked(
        self,
        request: UpdateGeneratedPullRequestSummary,
    ) -> GeneratedPullRequestSummaryReceipt:
        operation = self._read_summary_operation(request)
        if operation is None:
            operation = self._bind_summary_operation(self._summary_operation(request), request)
        else:
            self._validate_summary_request(operation, request)

        existing = self._read_summary_receipt(request)
        if existing is not None:
            self._validate_summary_receipt(existing, operation, request)
            return existing

        current = self._provider.read_pull_request(operation.repository, operation.number)
        self._validate_summary_pull_request(current, operation, request)
        if current.title == operation.expected_title and current.body == operation.desired_body:
            return self._bind_summary_receipt(self._summary_receipt(operation, current), request)
        if current.title != operation.expected_title or current.body != operation.expected_body:
            self._conflict(request, "pull request metadata differs from the generated-summary operation")

        try:
            updated = self._provider.update_pull_request(
                UpdatePublicationPullRequest(
                    repository=operation.repository,
                    number=operation.number,
                    expected_head_sha=operation.head_sha,
                    expected_title=operation.expected_title,
                    expected_body=operation.expected_body,
                    title=operation.expected_title,
                    body=operation.desired_body,
                )
            )
        except PublicationProviderError as exc:
            if exc.code is not PublicationProviderFailureCode.RESPONSE_UNKNOWN:
                raise
            reconciled = self._provider.read_pull_request(operation.repository, operation.number)
            self._validate_summary_pull_request(reconciled, operation, request)
            if reconciled.title == operation.expected_title and reconciled.body == operation.desired_body:
                return self._bind_summary_receipt(self._summary_receipt(operation, reconciled), request)
            raise

        self._validate_summary_pull_request(updated, operation, request)
        if updated.title != operation.expected_title or updated.body != operation.desired_body:
            self._invalid_response(request, "provider did not apply the generated pull-request summary")
        return self._bind_summary_receipt(self._summary_receipt(operation, updated), request)

    def _summary_operation(self, request: UpdateGeneratedPullRequestSummary) -> _GeneratedSummaryOperation:
        publication = self._read_receipt(request)
        if publication is None:
            self._conflict(request, "Change has no draft pull-request publication receipt")
        current = self._provider.read_pull_request(publication.repository, publication.number)
        self._validate_publication_identity(current, publication, request)
        desired_body = _replace_generated_block(current.body, request.generated_summary, request)
        return _GeneratedSummaryOperation(
            operation_id=request.operation_id,
            change_id=request.change_id,
            repository=publication.repository,
            number=publication.number,
            node_id=publication.node_id,
            head_branch=publication.head_branch,
            head_sha=request.published_head,
            base_branch=publication.base_branch,
            expected_title=current.title,
            expected_body=current.body,
            desired_body=desired_body,
            generated_summary_digest=_digest(request.generated_summary),
        )

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
        request: _PublicationRequest,
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

    def _read_summary_operation(
        self,
        request: UpdateGeneratedPullRequestSummary,
    ) -> _GeneratedSummaryOperation | None:
        return self._read_state(
            self._summary_path("summary-operations", request),
            _GeneratedSummaryOperation,
            request,
        )

    def _bind_summary_operation(
        self,
        operation: _GeneratedSummaryOperation,
        request: UpdateGeneratedPullRequestSummary,
    ) -> _GeneratedSummaryOperation:
        path = self._summary_path("summary-operations", request)
        existing = self._publish_or_read(path, operation, _GeneratedSummaryOperation, request)
        if existing != operation:
            self._conflict(request, "generated-summary operation differs from the stored operation")
        return existing

    def _read_summary_receipt(
        self,
        request: UpdateGeneratedPullRequestSummary,
    ) -> GeneratedPullRequestSummaryReceipt | None:
        return self._read_state(
            self._summary_path("summary-receipts", request),
            GeneratedPullRequestSummaryReceipt,
            request,
        )

    def _bind_summary_receipt(
        self,
        receipt: GeneratedPullRequestSummaryReceipt,
        request: UpdateGeneratedPullRequestSummary,
    ) -> GeneratedPullRequestSummaryReceipt:
        path = self._summary_path("summary-receipts", request)
        existing = self._publish_or_read(path, receipt, GeneratedPullRequestSummaryReceipt, request)
        if existing != receipt:
            self._conflict(request, "generated-summary receipt differs from the provider result")
        return existing

    def _read_state[ModelT: _DraftPullRequestModel](
        self,
        path: Path,
        model_type: type[ModelT],
        request: _PublicationRequest,
    ) -> ModelT | None:
        with locked_roots((self._state_root,)):
            self._reject_symlink(path, request)
            try:
                content = path.read_bytes()
            except FileNotFoundError:
                return None
        try:
            return model_type.model_validate_json(content)
        except ValidationError as exc:
            self._invalid_response(request, "stored draft pull-request state is invalid", cause=exc)

    def _validate_summary_request(
        self,
        operation: _GeneratedSummaryOperation,
        request: UpdateGeneratedPullRequestSummary,
    ) -> None:
        if (
            operation.operation_id != request.operation_id
            or operation.change_id != request.change_id
            or operation.head_sha != request.published_head
            or operation.generated_summary_digest != _digest(request.generated_summary)
        ):
            self._conflict(request, "generated-summary request differs from the stored operation")

    def _validate_summary_receipt(
        self,
        receipt: GeneratedPullRequestSummaryReceipt,
        operation: _GeneratedSummaryOperation,
        request: UpdateGeneratedPullRequestSummary,
    ) -> None:
        if (
            receipt.operation_id != operation.operation_id
            or receipt.change_id != operation.change_id
            or receipt.repository != operation.repository
            or receipt.number != operation.number
            or receipt.head_sha != operation.head_sha
            or receipt.body_digest != _digest(operation.desired_body)
        ):
            self._conflict(request, "stored generated-summary receipt differs from the operation")

    def _validate_publication_identity(
        self,
        pull_request: PublicationPullRequest,
        publication: DraftPullRequestPublicationReceipt,
        request: ObserveChangePublicationChecks | UpdateGeneratedPullRequestSummary,
    ) -> None:
        if (
            pull_request.repository != publication.repository
            or pull_request.number != publication.number
            or pull_request.node_id != publication.node_id
            or pull_request.head_branch != publication.head_branch
            or pull_request.head_sha != request.published_head
            or pull_request.base_branch != publication.base_branch
            or pull_request.state != "open"
            or pull_request.merged
        ):
            self._conflict(request, "provider pull request does not match the bound publication identity")

    def _validate_summary_pull_request(
        self,
        pull_request: PublicationPullRequest,
        operation: _GeneratedSummaryOperation,
        request: UpdateGeneratedPullRequestSummary,
    ) -> None:
        if (
            pull_request.repository != operation.repository
            or pull_request.number != operation.number
            or pull_request.node_id != operation.node_id
            or pull_request.head_branch != operation.head_branch
            or pull_request.head_sha != operation.head_sha
            or pull_request.base_branch != operation.base_branch
            or pull_request.state != "open"
            or pull_request.merged
        ):
            self._conflict(request, "provider pull request moved outside the generated-summary fence")
        _generated_block_bounds(pull_request.body, request)

    @staticmethod
    def _summary_receipt(
        operation: _GeneratedSummaryOperation,
        pull_request: PublicationPullRequest,
    ) -> GeneratedPullRequestSummaryReceipt:
        payload = {
            "schema_version": 1,
            "operation_id": operation.operation_id,
            "change_id": operation.change_id,
            "repository": operation.repository,
            "number": operation.number,
            "head_sha": operation.head_sha,
            "body_digest": _digest(operation.desired_body),
            "provider_evidence_digest": _digest(pull_request.model_dump(mode="json")),
        }
        return GeneratedPullRequestSummaryReceipt(receipt_id=_digest(payload), **payload)

    def _publish_or_read[ModelT: _DraftPullRequestModel](
        self,
        path: Path,
        model: ModelT,
        model_type: type[ModelT],
        request: _PublicationRequest,
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

    def _summary_path(self, kind: str, request: UpdateGeneratedPullRequestSummary) -> Path:
        return self._state_root / kind / f"{request.change_id}--{request.operation_id}.json"

    @staticmethod
    def _require_directory(path: Path) -> None:
        if path.is_symlink():
            msg = "draft pull-request state directory must not be a symlink"
            raise ValueError(msg)
        path.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _reject_symlink(path: Path, request: _PublicationRequest) -> None:
        if path.is_symlink():
            DraftPullRequestPublisher._invalid_response(
                request,
                "draft pull-request state file must not be a symlink",
            )

    @staticmethod
    def _conflict(request: _PublicationRequest, detail: str) -> Never:
        _raise_conflict(request, detail)

    @staticmethod
    def _invalid_response(
        request: _PublicationRequest,
        detail: str,
        *,
        cause: Exception | None = None,
    ) -> Never:
        error = PublicationProviderError(
            PublicationProviderFailureCode.INVALID_RESPONSE,
            _request_operation(request),
            detail,
            retry_safe=False,
        )
        raise error from cause

    @staticmethod
    def _unavailable(
        request: _PublicationRequest,
        detail: str,
        *,
        cause: Exception,
    ) -> Never:
        error = PublicationProviderError(
            PublicationProviderFailureCode.UNAVAILABLE,
            _request_operation(request),
            detail,
            retry_safe=True,
        )
        raise error from cause


def _change_marker(change_id: str) -> str:
    return f"<!-- owlbear-change:{change_id} -->"


def _require_safe_generated_summary(generated_summary: str) -> None:
    reserved_tokens = (_GENERATED_START, _GENERATED_END, "<!-- owlbear-change:")
    if any(token in generated_summary for token in reserved_tokens):
        msg = "generated pull-request summary contains a reserved ownership marker"
        raise ValueError(msg)


def _raise_conflict(request: _PublicationRequest, detail: str) -> Never:
    raise PublicationProviderError(
        PublicationProviderFailureCode.CONFLICT,
        _request_operation(request),
        detail,
        retry_safe=False,
    )


def _request_operation(request: _PublicationRequest) -> str:
    if isinstance(request, ObserveChangePublicationChecks):
        return "observe_change_publication_checks"
    return request.operation_id


def _generated_block_bounds(body: str, request: _PublicationRequest) -> tuple[int, int]:
    if body.count(_change_marker(request.change_id)) != 1:
        _raise_conflict(request, "pull request body has an invalid Change marker")
    if body.count(_GENERATED_START) != 1 or body.count(_GENERATED_END) != 1:
        _raise_conflict(request, "pull request body has invalid generated-block delimiters")
    start = body.index(_GENERATED_START)
    end = body.index(_GENERATED_END)
    if start >= end:
        _raise_conflict(request, "pull request generated-block delimiters are out of order")
    return start, end


def _replace_generated_block(
    body: str,
    generated_summary: str,
    request: UpdateGeneratedPullRequestSummary,
) -> str:
    start, end = _generated_block_bounds(body, request)
    suffix_start = end + len(_GENERATED_END)
    generated_block = f"{_GENERATED_START}\n{generated_summary.rstrip()}\n{_GENERATED_END}"
    rendered = f"{body[:start]}{generated_block}{body[suffix_start:]}"
    if len(rendered) > _MAX_PULL_REQUEST_BODY_LENGTH:
        _raise_conflict(request, "generated pull-request body exceeds the provider limit")
    return rendered


def _digest(payload: object) -> str:
    content = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(content.encode()).hexdigest()
