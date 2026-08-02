"""Receipt-gated transition from bootstrap stores to the target runtime."""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import shutil
import stat
from base64 import b64decode, b64encode
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Literal, Never

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from owlbear_kanban.snapshot import (
    LegacyDisposition,
    LegacySnapshotResult,
    create_legacy_snapshot,
    inventory_legacy_source,
    verify_legacy_snapshot,
)
from owlbear_kanban.storage_io import locked_roots
from owlbear_kanban.target_authority import AuthorityStatus, CommitmentClass, TargetAuthority
from owlbear_kanban.target_runtime import TargetRuntimeState

_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_PROTECTED_COMMITMENT_CLASSES = {
    CommitmentClass.DEALBREAKER,
    CommitmentClass.PROTECTED_REQUEST,
    CommitmentClass.IMPORTANT_REVIEWED,
}


class TargetCutoverError(RuntimeError):
    """Base class for typed target cutover failures."""

    code = "ERR_TARGET_CUTOVER"


class TargetCutoverReadinessError(TargetCutoverError):
    """One named readiness or currentness identity blocks cutover."""

    def __init__(self, code: str, detail: str, blocking_identity: str) -> None:
        self.code = code
        self.blocking_identity = blocking_identity
        super().__init__(f"{detail}: {blocking_identity}")


class TargetCutoverPathError(TargetCutoverError):
    """A cutover path is unsafe, absent, or aliases another path."""

    code = "ERR_TARGET_CUTOVER_PATH_UNSAFE"


class TargetCutoverPublicationError(TargetCutoverError):
    """A pre-receipt cutover stage failed and was rolled back."""

    code = "ERR_TARGET_CUTOVER_PUBLICATION"


class TargetCutoverReceiptError(TargetCutoverError):
    """A pending intent or published receipt is invalid or conflicting."""

    code = "ERR_TARGET_CUTOVER_RECEIPT"


class TargetMutationGateError(TargetCutoverError):
    """Target mutation lacks a valid cutover boundary."""

    def __init__(self, code: str, detail: str, required_actions: tuple[str, ...] = ()) -> None:
        self.code = code
        self.required_actions = required_actions
        super().__init__(detail)


class _CutoverModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class TargetCutoverSubjectKind(StrEnum):
    """Semantic identity kinds requiring explicit cutover disposition."""

    CHANGE = "change"
    OUTCOME = "outcome"
    COMMITMENT = "commitment"


class TargetCutoverClassification(_CutoverModel):
    """Explicit disposition for one unfinished semantic identity."""

    change_id: str = Field(min_length=1)
    subject_kind: TargetCutoverSubjectKind
    subject_id: str = Field(min_length=1)
    disposition: LegacyDisposition


class TargetCutoverSource(_CutoverModel):
    """One current authority or runtime store requiring immutable snapshot."""

    source_path: str
    snapshot_name: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    expected_source_digest: str

    @field_validator("source_path")
    @classmethod
    def validate_source_path(cls, value: str) -> str:
        """Require one canonical workspace-relative path."""
        return _relative_path(value)

    @field_validator("expected_source_digest")
    @classmethod
    def validate_source_digest(cls, value: str) -> str:
        """Require one lowercase SHA-256 identity."""
        return _digest(value)


class TargetAdapterRef(_CutoverModel):
    """One adapter registry or source ref staged during cutover."""

    relative_path: str
    target: str = Field(min_length=1)

    @field_validator("relative_path")
    @classmethod
    def validate_relative_path(cls, value: str) -> str:
        """Require one canonical workspace-relative path."""
        return _relative_path(value)


class TargetCutoverReadiness(_CutoverModel):
    """Current bootstrap identities that must be absent before cutover."""

    current_request_ids: tuple[str, ...] = ()
    active_claim_ids: tuple[str, ...] = ()
    active_writer_ids: tuple[str, ...] = ()


class TargetCutoverRequest(_CutoverModel):
    """Complete immutable input to one target cutover transaction."""

    sources: tuple[TargetCutoverSource, ...] = Field(min_length=1)
    snapshot_path: str
    target_path: str
    receipt_path: str
    adapter_refs: tuple[TargetAdapterRef, ...] = Field(min_length=1)
    authorities: tuple[TargetAuthority, ...]
    classifications: tuple[TargetCutoverClassification, ...]
    expected_authority_digest: str
    actual_code_revision: str
    expected_code_revision: str
    readiness: TargetCutoverReadiness
    approval: Literal["ACTIVATE_TARGET_RUNTIME"]

    @field_validator("snapshot_path", "target_path", "receipt_path")
    @classmethod
    def validate_relative_path(cls, value: str) -> str:
        """Require canonical workspace-relative transaction paths."""
        return _relative_path(value)

    @field_validator("expected_authority_digest", "actual_code_revision", "expected_code_revision")
    @classmethod
    def validate_digest(cls, value: str) -> str:
        """Require lowercase SHA-256 revision identities."""
        return _digest(value)


class TargetCutoverSnapshot(_CutoverModel):
    """One source snapshot bound into the activation receipt."""

    snapshot_name: str
    source_path: str
    snapshot_path: str
    source_digest: str
    manifest_sha256: str


class TargetStoreManifest(_CutoverModel):
    """Canonical target authority and empty runtime inventory."""

    schema_version: Literal[1] = 1
    authority_digest: str
    authority_paths: tuple[str, ...]
    runtime_paths: tuple[str, ...]


class TargetCutoverReceipt(_CutoverModel):
    """Immutable boundary activating target mutation."""

    schema_version: Literal[1] = 1
    receipt_id: str
    request_fingerprint: str
    authority_digest: str
    code_revision: str
    target_manifest_sha256: str
    snapshots: tuple[TargetCutoverSnapshot, ...]
    adapter_refs: tuple[TargetAdapterRef, ...]
    approval: Literal["ACTIVATE_TARGET_RUNTIME"]

    @model_validator(mode="after")
    def validate_receipt_id(self) -> TargetCutoverReceipt:
        """Bind the receipt identity to all immutable receipt content."""
        payload = self.model_dump(mode="json", exclude={"receipt_id"})
        if self.receipt_id != hashlib.sha256(_canonical_json(payload)).hexdigest():
            message = "target cutover receipt identity does not match its content"
            raise ValueError(message)
        return self


class TargetCutoverResult(_CutoverModel):
    """Published target activation result."""

    receipt: TargetCutoverReceipt
    authorities: tuple[TargetAuthority, ...]
    replayed: bool


class TargetMutationAuthority(_CutoverModel):
    """Receipt-verified semantic authority admitted for target mutation."""

    receipt: TargetCutoverReceipt
    authorities: tuple[TargetAuthority, ...]


class _RefBackup(_CutoverModel):
    relative_path: str
    content_base64: str | None


class _PendingCutover(_CutoverModel):
    request_fingerprint: str
    refs: tuple[_RefBackup, ...]


@dataclass(frozen=True)
class _CutoverPaths:
    root: Path
    sources: tuple[Path, ...]
    snapshot: Path
    target: Path
    receipt: Path
    pending: Path
    adapter_refs: tuple[Path, ...]


type TargetCutoverFailureHook = Callable[[str, Path], None]
type TargetCutoverSmokeCheck = Callable[[Path, TargetCutoverRequest], None]


def target_authority_digest(authorities: tuple[TargetAuthority, ...]) -> str:
    """Return the aggregate identity of sorted reintroduced authority."""
    payload = [item.model_dump(mode="json") for item in sorted(authorities, key=lambda item: item.change_id)]
    return hashlib.sha256(_canonical_json(payload)).hexdigest()


def validate_target_cutover_readiness(request: TargetCutoverRequest) -> None:
    """Reject every semantic or runtime blocker before filesystem mutation."""
    missing = _required_classifications(request.authorities) - _classification_keys(request.classifications)
    if missing:
        _fail_readiness("ERR_TARGET_CUTOVER_UNCLASSIFIED", "classification is required", min(missing))
    readiness = request.readiness
    if readiness.current_request_ids:
        _fail_readiness(
            "ERR_TARGET_CUTOVER_CURRENT_REQUEST",
            "current-digest request blocks cutover",
            readiness.current_request_ids[0],
        )
    if readiness.active_claim_ids:
        _fail_readiness(
            "ERR_TARGET_CUTOVER_ACTIVE_CLAIM",
            "active claim blocks cutover",
            readiness.active_claim_ids[0],
        )
    if readiness.active_writer_ids:
        _fail_readiness(
            "ERR_TARGET_CUTOVER_ACTIVE_WRITER",
            "active writer blocks cutover",
            readiness.active_writer_ids[0],
        )
    actual_authority_digest = target_authority_digest(request.authorities)
    if request.expected_authority_digest != actual_authority_digest:
        _fail_readiness("ERR_TARGET_CUTOVER_AUTHORITY_STALE", "authority revision is stale", actual_authority_digest)
    if request.expected_code_revision != request.actual_code_revision:
        _fail_readiness("ERR_TARGET_CUTOVER_CODE_STALE", "code revision is stale", request.actual_code_revision)


def cut_over_target_runtime(
    workspace_root: Path,
    request: TargetCutoverRequest,
    *,
    smoke: TargetCutoverSmokeCheck,
    failure: TargetCutoverFailureHook | None = None,
) -> TargetCutoverResult:
    """Snapshot bootstrap stores and activate reintroduced target authority."""
    validate_target_cutover_readiness(request)
    paths = _resolve_paths(workspace_root, request)
    with locked_roots((paths.root,)):
        return _cut_over_locked(paths, request, smoke=smoke, failure=failure)


def _cut_over_locked(
    paths: _CutoverPaths,
    request: TargetCutoverRequest,
    *,
    smoke: TargetCutoverSmokeCheck,
    failure: TargetCutoverFailureHook | None,
) -> TargetCutoverResult:
    fingerprint = _request_fingerprint(request)
    if _workspace_path_kind(paths.root, paths.receipt) != "missing":
        return _replay_completed(paths, request, fingerprint)
    _recover_pending(paths, request, fingerprint)
    _validate_source_currentness(paths, request)
    pending = _create_pending(paths, fingerprint)
    try:
        snapshots = _snapshot_sources(paths, request)
        _invoke_failure(failure, "snapshot", paths.snapshot)
        manifest = _initialize_target(paths, request)
        _invoke_failure(failure, "initialization", paths.target)
        _stage_adapter_refs(paths, request)
        _invoke_failure(failure, "adapter-staging", paths.root)
        _verify_staging(paths, request, manifest, snapshots)
        smoke(paths.root, request)
        _invoke_failure(failure, "smoke-verification", paths.target)
        _retire_sources(paths, request)
        _invoke_failure(failure, "source-retirement", paths.snapshot)
        receipt = _build_receipt(request, fingerprint, manifest, snapshots)
        _publish_receipt(paths, receipt, failure)
    except Exception as exc:
        _rollback(paths, request, pending)
        if isinstance(exc, TargetCutoverError):
            raise
        raise TargetCutoverPublicationError(str(exc)) from exc
    _remove_retired_sources(paths, request)
    _remove_path(paths.root, paths.pending)
    return TargetCutoverResult(receipt=receipt, authorities=request.authorities, replayed=False)


def _validate_source_currentness(
    paths: _CutoverPaths,
    request: TargetCutoverRequest,
) -> None:
    for source, specification in zip(paths.sources, request.sources, strict=True):
        if _workspace_path_kind(paths.root, source) != "directory":
            _fail_path(f"cutover source is absent: {source}")
        actual = inventory_legacy_source(source, (), {}).source_digest
        if actual != specification.expected_source_digest:
            _fail_readiness("ERR_TARGET_CUTOVER_SOURCE_STALE", "source inventory is stale", specification.source_path)


def authorize_target_mutation(
    workspace_root: Path,
    request: TargetCutoverRequest,
) -> TargetMutationAuthority:
    """Require a valid receipt and reject reappearing current-schema jobs."""
    paths = _resolve_paths(workspace_root, request)
    with locked_roots((paths.root,)):
        return _authorize_target_mutation_locked(paths, request)


def _authorize_target_mutation_locked(
    paths: _CutoverPaths,
    request: TargetCutoverRequest,
) -> TargetMutationAuthority:
    if _workspace_path_kind(paths.root, paths.receipt) == "missing":
        actions = (
            "snapshot current authority and runtime stores",
            "classify unfinished changes, outcomes, and C1-C3 commitments",
        )
        detail = "target mutation requires a cutover receipt; snapshot and classification are required"
        _fail_gate("ERR_TARGET_CUTOVER_REQUIRED", detail, actions)
    for source in paths.sources:
        legacy_job = _find_current_job(paths.root, source)
        if legacy_job is not None:
            detail = f"current-schema job cannot become active target work: {legacy_job}"
            _fail_gate("ERR_TARGET_CUTOVER_LEGACY_ACTIVE_WORK", detail)
    result = _replay_completed(paths, request, _request_fingerprint(request))
    return TargetMutationAuthority(receipt=result.receipt, authorities=result.authorities)


def query_target_snapshot(
    workspace_root: Path,
    request: TargetCutoverRequest,
    snapshot_name: str,
) -> LegacySnapshotResult:
    """Verify and return one receipt-retained bootstrap snapshot."""
    paths = _resolve_paths(workspace_root, request)
    receipt = _read_receipt(paths.root, paths.receipt)
    if receipt.request_fingerprint != _request_fingerprint(request):
        _fail_receipt("target cutover receipt belongs to another request")
    snapshot = next((item for item in receipt.snapshots if item.snapshot_name == snapshot_name), None)
    if snapshot is None:
        _fail_receipt(f"cutover snapshot is absent: {snapshot_name}")
    result = verify_legacy_snapshot(paths.root / snapshot.snapshot_path)
    if result.manifest_sha256 != snapshot.manifest_sha256:
        _fail_receipt(f"cutover snapshot changed: {snapshot_name}")
    return result


def _resolve_paths(
    workspace_root: Path,
    request: TargetCutoverRequest,
) -> _CutoverPaths:
    if workspace_root.is_symlink() or not workspace_root.is_dir():
        raise TargetCutoverPathError(workspace_root)
    root = workspace_root.resolve()
    sources = tuple(_resolve_workspace_path(root, item.source_path) for item in request.sources)
    snapshot = _resolve_workspace_path(root, request.snapshot_path)
    target = _resolve_workspace_path(root, request.target_path)
    receipt = _resolve_workspace_path(root, request.receipt_path)
    refs = tuple(_resolve_workspace_path(root, item.relative_path) for item in request.adapter_refs)
    paths = _CutoverPaths(root, sources, snapshot, target, receipt, receipt.with_suffix(".pending"), refs)
    _validate_distinct_paths(paths)
    return paths


def _resolve_workspace_path(root: Path, value: str) -> Path:
    path = root.joinpath(*PurePosixPath(value).parts)
    current = root
    for part in path.relative_to(root).parts:
        current /= part
        if current.is_symlink():
            raise TargetCutoverPathError(current)
        if current.exists() and current != path and not current.is_dir():
            raise TargetCutoverPathError(current)
    return path


def _validate_distinct_paths(paths: _CutoverPaths) -> None:
    roots = (*paths.sources, paths.snapshot, paths.target, paths.receipt, paths.pending, *paths.adapter_refs)
    for index, path in enumerate(roots):
        for other in roots[index + 1 :]:
            if path == other or path in other.parents or other in path.parents:
                _fail_path(f"overlapping cutover paths: {path}, {other}")


def _create_pending(paths: _CutoverPaths, fingerprint: str) -> _PendingCutover:
    refs = tuple(
        _RefBackup(relative_path=str(path.relative_to(paths.root)), content_base64=_backup(paths.root, path))
        for path in paths.adapter_refs
    )
    pending = _PendingCutover(request_fingerprint=fingerprint, refs=refs)
    _publish_file(paths.root, paths.pending, _model_content(pending), immutable=True)
    return pending


def _recover_pending(paths: _CutoverPaths, request: TargetCutoverRequest, fingerprint: str) -> None:
    if _workspace_path_kind(paths.root, paths.pending) == "missing":
        if (
            _workspace_path_kind(paths.root, paths.snapshot) != "missing"
            or _workspace_path_kind(paths.root, paths.target) != "missing"
        ):
            _fail_receipt("unowned target cutover state exists without a receipt")
        return
    try:
        pending = _PendingCutover.model_validate_json(_read_workspace_file(paths.root, paths.pending))
    except (OSError, ValueError) as exc:
        message = "pending target cutover intent is invalid"
        raise TargetCutoverReceiptError(message) from exc
    if pending.request_fingerprint != fingerprint:
        _fail_receipt("pending target cutover belongs to another request")
    _rollback(paths, request, pending)


def _snapshot_sources(
    paths: _CutoverPaths,
    request: TargetCutoverRequest,
) -> tuple[TargetCutoverSnapshot, ...]:
    snapshots = []
    for source, specification in zip(paths.sources, request.sources, strict=True):
        manifest = inventory_legacy_source(source, (), {})
        if manifest.source_digest != specification.expected_source_digest:
            _fail_readiness("ERR_TARGET_CUTOVER_SOURCE_STALE", "source inventory is stale", specification.source_path)
        destination = paths.snapshot / specification.snapshot_name
        result = create_legacy_snapshot(source, destination, (), {})
        snapshots.append(_snapshot_record(paths, specification, result))
    return tuple(snapshots)


def _snapshot_record(
    paths: _CutoverPaths,
    source: TargetCutoverSource,
    result: LegacySnapshotResult,
) -> TargetCutoverSnapshot:
    return TargetCutoverSnapshot(
        snapshot_name=source.snapshot_name,
        source_path=source.source_path,
        snapshot_path=str(result.destination.relative_to(paths.root)),
        source_digest=result.manifest.source_digest,
        manifest_sha256=result.manifest_sha256,
    )


def _initialize_target(paths: _CutoverPaths, request: TargetCutoverRequest) -> TargetStoreManifest:
    if _workspace_path_kind(paths.root, paths.target) != "missing":
        _fail_path("target store already exists")
    (paths.target / "changes").mkdir(parents=True)
    authority_paths = tuple(f"changes/{item.change_id}/authority.json" for item in request.authorities)
    runtime_paths = tuple(f"changes/{item.change_id}/target-runtime/state.json" for item in request.authorities)
    manifest = TargetStoreManifest(
        authority_digest=target_authority_digest(request.authorities),
        authority_paths=authority_paths,
        runtime_paths=runtime_paths,
    )
    for authority, authority_path, runtime_path in zip(
        request.authorities, authority_paths, runtime_paths, strict=True
    ):
        _publish_file(paths.root, paths.target / authority_path, _model_content(authority), immutable=True)
        _publish_file(
            paths.root,
            paths.target / runtime_path,
            _model_content(TargetRuntimeState()),
            immutable=True,
        )
    _publish_file(paths.root, paths.target / "manifest.json", _model_content(manifest), immutable=True)
    return manifest


def _stage_adapter_refs(paths: _CutoverPaths, request: TargetCutoverRequest) -> None:
    for path, reference in zip(paths.adapter_refs, request.adapter_refs, strict=True):
        _publish_file(paths.root, path, reference.target.encode() + b"\n", immutable=False)


def _verify_staging(
    paths: _CutoverPaths,
    request: TargetCutoverRequest,
    manifest: TargetStoreManifest,
    snapshots: tuple[TargetCutoverSnapshot, ...],
) -> None:
    manifest_content = _read_workspace_file(paths.root, paths.target / "manifest.json")
    if TargetStoreManifest.model_validate_json(manifest_content) != manifest:
        _fail_publication("target manifest verification failed")
    if _read_target_authorities(paths, manifest) != request.authorities:
        _fail_publication("target authority verification failed")
    for relative_path in manifest.runtime_paths:
        content = _read_workspace_file(paths.root, paths.target / relative_path)
        TargetRuntimeState.model_validate_json(content)
    for snapshot in snapshots:
        if verify_legacy_snapshot(paths.root / snapshot.snapshot_path).manifest_sha256 != snapshot.manifest_sha256:
            _fail_publication(f"snapshot verification failed: {snapshot.snapshot_name}")
    for path, reference in zip(paths.adapter_refs, request.adapter_refs, strict=True):
        if _read_workspace_file(paths.root, path) != reference.target.encode() + b"\n":
            _fail_publication(f"adapter ref verification failed: {reference.relative_path}")


def _build_receipt(
    request: TargetCutoverRequest,
    fingerprint: str,
    manifest: TargetStoreManifest,
    snapshots: tuple[TargetCutoverSnapshot, ...],
) -> TargetCutoverReceipt:
    payload = {
        "schema_version": 1,
        "request_fingerprint": fingerprint,
        "authority_digest": request.expected_authority_digest,
        "code_revision": request.actual_code_revision,
        "target_manifest_sha256": hashlib.sha256(_model_content(manifest)).hexdigest(),
        "snapshots": snapshots,
        "adapter_refs": request.adapter_refs,
        "approval": request.approval,
    }
    receipt_id = hashlib.sha256(_canonical_json(_json_payload(payload))).hexdigest()
    return TargetCutoverReceipt(receipt_id=receipt_id, **payload)


def _publish_receipt(
    paths: _CutoverPaths,
    receipt: TargetCutoverReceipt,
    failure: TargetCutoverFailureHook | None,
) -> None:
    _invoke_failure(failure, "receipt-publication", paths.receipt)
    _publish_file(paths.root, paths.receipt, _model_content(receipt), immutable=True)
    try:
        _invoke_failure(failure, "receipt-publication-linked", paths.receipt)
    except Exception:
        _remove_path(paths.root, paths.receipt)
        raise


def _replay_completed(
    paths: _CutoverPaths,
    request: TargetCutoverRequest,
    fingerprint: str,
) -> TargetCutoverResult:
    receipt = _read_receipt(paths.root, paths.receipt)
    if receipt.request_fingerprint != fingerprint:
        _fail_receipt("target cutover receipt belongs to another request")
    manifest_content = _read_workspace_file(paths.root, paths.target / "manifest.json")
    manifest = TargetStoreManifest.model_validate_json(manifest_content)
    if hashlib.sha256(_model_content(manifest)).hexdigest() != receipt.target_manifest_sha256:
        _fail_receipt("target store differs from its cutover receipt")
    authorities = _read_target_authorities(paths, manifest)
    if authorities != request.authorities:
        _fail_receipt("reintroduced authority differs from the cutover request")
    for snapshot in receipt.snapshots:
        query_target_snapshot(paths.root, request, snapshot.snapshot_name)
    _verify_source_absence(paths.root, paths.sources)
    _verify_adapter_refs(paths, receipt.adapter_refs)
    _remove_retired_sources(paths, request)
    _remove_path(paths.root, paths.pending)
    return TargetCutoverResult(receipt=receipt, authorities=authorities, replayed=True)


def _read_receipt(root: Path, path: Path) -> TargetCutoverReceipt:
    try:
        return TargetCutoverReceipt.model_validate_json(_read_workspace_file(root, path))
    except (OSError, ValueError) as exc:
        message = "target cutover receipt is absent or invalid"
        raise TargetCutoverReceiptError(message) from exc


def _read_target_authorities(
    paths: _CutoverPaths,
    manifest: TargetStoreManifest,
) -> tuple[TargetAuthority, ...]:
    try:
        return tuple(
            TargetAuthority.model_validate_json(_read_workspace_file(paths.root, paths.target / relative))
            for relative in manifest.authority_paths
        )
    except (OSError, ValueError) as exc:
        message = "target authority store is invalid"
        raise TargetCutoverReceiptError(message) from exc


def _verify_adapter_refs(paths: _CutoverPaths, refs: tuple[TargetAdapterRef, ...]) -> None:
    for path, reference in zip(paths.adapter_refs, refs, strict=True):
        if _read_workspace_file(paths.root, path) != reference.target.encode() + b"\n":
            _fail_receipt(f"adapter ref differs from receipt: {reference.relative_path}")


def _verify_source_absence(root: Path, sources: tuple[Path, ...]) -> None:
    remaining = tuple(str(path) for path in sources if _workspace_path_kind(root, path) != "missing")
    if remaining:
        _fail_receipt(f"bootstrap source paths remain active: {remaining}")


def _retire_sources(paths: _CutoverPaths, request: TargetCutoverRequest) -> None:
    for source, retired in zip(paths.sources, _retired_paths(paths, request), strict=True):
        _rename_directory(paths.root, source, retired)


def _remove_retired_sources(paths: _CutoverPaths, request: TargetCutoverRequest) -> None:
    for retired in _retired_paths(paths, request):
        _remove_path(paths.root, retired)


def _retired_paths(paths: _CutoverPaths, request: TargetCutoverRequest) -> tuple[Path, ...]:
    return tuple(paths.snapshot / ".retired" / item.snapshot_name for item in request.sources)


def _rollback(paths: _CutoverPaths, request: TargetCutoverRequest, pending: _PendingCutover) -> None:
    _remove_path(paths.root, paths.receipt)
    _restore_refs(paths, pending)
    _restore_sources(paths, request)
    _remove_path(paths.root, paths.target)
    _remove_path(paths.root, paths.snapshot)
    _remove_path(paths.root, paths.pending)


def _restore_refs(paths: _CutoverPaths, pending: _PendingCutover) -> None:
    backups = {item.relative_path: item.content_base64 for item in pending.refs}
    for path in paths.adapter_refs:
        content = backups[str(path.relative_to(paths.root))]
        if content is None:
            _remove_path(paths.root, path)
        else:
            _publish_file(paths.root, path, b64decode(content), immutable=False)


def _restore_sources(paths: _CutoverPaths, request: TargetCutoverRequest) -> None:
    retired_paths = _retired_paths(paths, request)
    for source, retired in zip(paths.sources, retired_paths, strict=True):
        if _workspace_path_kind(paths.root, retired) != "missing":
            if _workspace_path_kind(paths.root, source) != "missing":
                _fail_receipt(f"source and retired source both exist: {source}")
            _rename_directory(paths.root, retired, source)


def _remove_path(root: Path, path: Path) -> None:
    try:
        parent_fd = _open_parent_descriptor(root, path, create=False)
    except FileNotFoundError:
        return
    try:
        try:
            metadata = os.stat(path.name, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            return
        if stat.S_ISLNK(metadata.st_mode):
            raise TargetCutoverPathError(path)
        if stat.S_ISDIR(metadata.st_mode):
            shutil.rmtree(path.name, dir_fd=parent_fd)
        elif stat.S_ISREG(metadata.st_mode):
            os.unlink(path.name, dir_fd=parent_fd)
        else:
            raise TargetCutoverPathError(path)
    finally:
        os.close(parent_fd)


def _rename_directory(root: Path, source: Path, destination: Path) -> None:
    source_parent_fd = _open_parent_descriptor(root, source, create=False)
    destination_parent_fd = _open_parent_descriptor(root, destination, create=True)
    try:
        metadata = os.stat(source.name, dir_fd=source_parent_fd, follow_symlinks=False)
        if not stat.S_ISDIR(metadata.st_mode):
            raise TargetCutoverPathError(source)
        os.rename(
            source.name,
            destination.name,
            src_dir_fd=source_parent_fd,
            dst_dir_fd=destination_parent_fd,
        )
    finally:
        os.close(destination_parent_fd)
        os.close(source_parent_fd)


def _backup(root: Path, path: Path) -> str | None:
    try:
        content = _read_workspace_file(root, path)
    except FileNotFoundError:
        return None
    return b64encode(content).decode("ascii")


def _publish_file(root: Path, path: Path, content: bytes, *, immutable: bool) -> None:
    parent_fd = _open_parent_descriptor(root, path, create=True)
    temporary = f".tmp-cutover-{secrets.token_hex(12)}-{path.name}"
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent_fd)
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        if immutable:
            try:
                os.link(temporary, path.name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd, follow_symlinks=False)
            except FileExistsError:
                if _read_descriptor_file(parent_fd, path.name) != content:
                    _fail_receipt(f"cutover destination already exists: {path}")
        else:
            os.replace(temporary, path.name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
        os.fsync(parent_fd)
    finally:
        with suppress(FileNotFoundError):
            os.unlink(temporary, dir_fd=parent_fd)
        os.close(parent_fd)


def _open_parent_descriptor(root: Path, path: Path, *, create: bool) -> int:
    try:
        parts = path.relative_to(root).parts[:-1]
    except ValueError as exc:
        raise TargetCutoverPathError(path) from exc
    descriptor = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in parts:
            try:
                child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
            except FileNotFoundError:
                if not create:
                    raise
                os.mkdir(part, mode=0o755, dir_fd=descriptor)
                child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
    except Exception:
        os.close(descriptor)
        raise
    return descriptor


def _read_descriptor_file(parent_fd: int, name: str) -> bytes:
    descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent_fd)
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise TargetCutoverPathError(name)
        with os.fdopen(descriptor, "rb") as source:
            descriptor = -1
            return source.read()
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _read_workspace_file(root: Path, path: Path) -> bytes:
    parent_fd = _open_parent_descriptor(root, path, create=False)
    try:
        return _read_descriptor_file(parent_fd, path.name)
    finally:
        os.close(parent_fd)


def _workspace_path_kind(root: Path, path: Path) -> Literal["missing", "file", "directory"]:
    try:
        parent_fd = _open_parent_descriptor(root, path, create=False)
    except FileNotFoundError:
        return "missing"
    try:
        try:
            metadata = os.stat(path.name, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            return "missing"
    finally:
        os.close(parent_fd)
    if stat.S_ISREG(metadata.st_mode):
        return "file"
    if stat.S_ISDIR(metadata.st_mode):
        return "directory"
    raise TargetCutoverPathError(path)


def _find_current_job(root: Path, source: Path) -> str | None:
    if _workspace_path_kind(root, source) == "missing":
        return None
    source_parent_fd = _open_parent_descriptor(root, source, create=False)
    source_fd = -1
    jobs_fd = -1
    try:
        source_fd = os.open(source.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=source_parent_fd)
        try:
            jobs_fd = os.open("jobs", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=source_fd)
        except FileNotFoundError:
            return None
        relative = _find_regular_file(jobs_fd, PurePosixPath("jobs"))
        if relative is None:
            return None
        return f"{source.relative_to(root).as_posix()}/{relative}"
    finally:
        if jobs_fd >= 0:
            os.close(jobs_fd)
        if source_fd >= 0:
            os.close(source_fd)
        os.close(source_parent_fd)


def _find_regular_file(directory_fd: int, prefix: PurePosixPath) -> str | None:
    for name in sorted(os.listdir(directory_fd)):
        metadata = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        relative = prefix / name
        if stat.S_ISREG(metadata.st_mode):
            return relative.as_posix()
        if not stat.S_ISDIR(metadata.st_mode):
            raise TargetCutoverPathError(relative.as_posix())
        child_fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory_fd)
        try:
            found = _find_regular_file(child_fd, relative)
        finally:
            os.close(child_fd)
        if found is not None:
            return found
    return None


def _request_fingerprint(request: TargetCutoverRequest) -> str:
    return hashlib.sha256(_canonical_json(request.model_dump(mode="json"))).hexdigest()


def _model_content(model: BaseModel) -> bytes:
    return json.dumps(model.model_dump(mode="json"), sort_keys=True, indent=2).encode() + b"\n"


def _json_payload(payload: object) -> object:
    return json.loads(json.dumps(payload, default=lambda item: item.model_dump(mode="json")))


def _invoke_failure(failure: TargetCutoverFailureHook | None, stage: str, path: Path) -> None:
    if failure is not None:
        failure(stage, path)


def _required_classifications(authorities: tuple[TargetAuthority, ...]) -> set[str]:
    required: set[str] = set()
    for authority in authorities:
        required.add(_classification_key(authority.change_id, TargetCutoverSubjectKind.CHANGE, authority.change_id))
        required.update(
            _classification_key(authority.change_id, TargetCutoverSubjectKind.OUTCOME, item.outcome_id)
            for item in authority.outcomes
            if item.status == AuthorityStatus.ACTIVE
        )
        required.update(
            _classification_key(authority.change_id, TargetCutoverSubjectKind.COMMITMENT, item.commitment_id)
            for item in authority.commitments
            if item.status == AuthorityStatus.ACTIVE and item.commitment_class in _PROTECTED_COMMITMENT_CLASSES
        )
    return required


def _classification_keys(classifications: tuple[TargetCutoverClassification, ...]) -> set[str]:
    return {_classification_key(item.change_id, item.subject_kind, item.subject_id) for item in classifications}


def _classification_key(change_id: str, kind: TargetCutoverSubjectKind, subject_id: str) -> str:
    return f"{change_id}:{kind}:{subject_id}"


def _fail_readiness(code: str, detail: str, identity: str) -> Never:
    raise TargetCutoverReadinessError(code, detail, identity)


def _fail_path(detail: str) -> Never:
    raise TargetCutoverPathError(detail)


def _fail_publication(detail: str) -> Never:
    raise TargetCutoverPublicationError(detail)


def _fail_receipt(detail: str) -> Never:
    raise TargetCutoverReceiptError(detail)


def _fail_gate(code: str, detail: str, actions: tuple[str, ...] = ()) -> Never:
    raise TargetMutationGateError(code, detail, actions)


def _relative_path(value: str) -> str:
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or PureWindowsPath(value).is_absolute()
        or any(part in {"", ".", ".."} for part in path.parts)
        or path.as_posix() != value
    ):
        message = "cutover paths must be canonical and workspace-relative"
        raise ValueError(message)
    return value


def _digest(value: str) -> str:
    if not _DIGEST_PATTERN.fullmatch(value):
        message = "cutover identities must be lowercase SHA-256 digests"
        raise ValueError(message)
    return value


def _canonical_json(payload: object) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
