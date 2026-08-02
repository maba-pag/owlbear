"""Receipt-gated transition from bootstrap stores to the target runtime."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import tempfile
from base64 import b64decode, b64encode
from collections.abc import Callable
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
    authorities: tuple[TargetAuthority, ...] = Field(min_length=1)
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
    fingerprint = _request_fingerprint(request)
    if paths.receipt.exists():
        return _replay_completed(paths, request, fingerprint)
    _recover_pending(paths, request, fingerprint)
    _require_sources(paths.sources)
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
        _remove_sources(paths.sources)
        receipt = _build_receipt(request, fingerprint, manifest, snapshots)
        _publish_receipt(paths.receipt, receipt, failure)
    except Exception as exc:
        _rollback(paths, request, pending)
        if isinstance(exc, TargetCutoverError):
            raise
        raise TargetCutoverPublicationError(str(exc)) from exc
    paths.pending.unlink(missing_ok=True)
    return TargetCutoverResult(receipt=receipt, authorities=request.authorities, replayed=False)


def authorize_target_mutation(
    workspace_root: Path,
    request: TargetCutoverRequest,
) -> TargetMutationAuthority:
    """Require a valid receipt and reject reappearing current-schema jobs."""
    paths = _resolve_paths(workspace_root, request)
    if not paths.receipt.exists():
        actions = (
            "snapshot current authority and runtime stores",
            "classify unfinished changes, outcomes, and C1-C3 commitments",
        )
        detail = "target mutation requires a cutover receipt; snapshot and classification are required"
        _fail_gate("ERR_TARGET_CUTOVER_REQUIRED", detail, actions)
    for source in paths.sources:
        legacy_job = next(source.glob("jobs/**/*.md"), None) if source.is_dir() else None
        if legacy_job is not None:
            detail = f"current-schema job cannot become active target work: {legacy_job.relative_to(paths.root)}"
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
    receipt = _read_receipt(paths.receipt)
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


def _require_sources(sources: tuple[Path, ...]) -> None:
    absent = tuple(str(source) for source in sources if not source.is_dir())
    if absent:
        _fail_path(f"cutover source is absent: {absent}")


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
        _RefBackup(relative_path=str(path.relative_to(paths.root)), content_base64=_backup(path))
        for path in paths.adapter_refs
    )
    pending = _PendingCutover(request_fingerprint=fingerprint, refs=refs)
    _publish_file(paths.pending, _model_content(pending), immutable=True)
    return pending


def _recover_pending(paths: _CutoverPaths, request: TargetCutoverRequest, fingerprint: str) -> None:
    if not paths.pending.exists():
        if paths.snapshot.exists() or paths.target.exists():
            _fail_receipt("unowned target cutover state exists without a receipt")
        return
    try:
        pending = _PendingCutover.model_validate_json(paths.pending.read_bytes())
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
    if paths.target.exists():
        _fail_path("target store already exists")
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
        _publish_file(paths.target / authority_path, _model_content(authority), immutable=True)
        _publish_file(paths.target / runtime_path, _model_content(TargetRuntimeState()), immutable=True)
    _publish_file(paths.target / "manifest.json", _model_content(manifest), immutable=True)
    return manifest


def _stage_adapter_refs(paths: _CutoverPaths, request: TargetCutoverRequest) -> None:
    for path, reference in zip(paths.adapter_refs, request.adapter_refs, strict=True):
        _publish_file(path, reference.target.encode() + b"\n", immutable=False)


def _verify_staging(
    paths: _CutoverPaths,
    request: TargetCutoverRequest,
    manifest: TargetStoreManifest,
    snapshots: tuple[TargetCutoverSnapshot, ...],
) -> None:
    if TargetStoreManifest.model_validate_json((paths.target / "manifest.json").read_bytes()) != manifest:
        _fail_publication("target manifest verification failed")
    if _read_target_authorities(paths, manifest) != request.authorities:
        _fail_publication("target authority verification failed")
    for relative_path in manifest.runtime_paths:
        TargetRuntimeState.model_validate_json((paths.target / relative_path).read_bytes())
    for snapshot in snapshots:
        if verify_legacy_snapshot(paths.root / snapshot.snapshot_path).manifest_sha256 != snapshot.manifest_sha256:
            _fail_publication(f"snapshot verification failed: {snapshot.snapshot_name}")
    for path, reference in zip(paths.adapter_refs, request.adapter_refs, strict=True):
        if path.read_bytes() != reference.target.encode() + b"\n":
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
    path: Path,
    receipt: TargetCutoverReceipt,
    failure: TargetCutoverFailureHook | None,
) -> None:
    _invoke_failure(failure, "receipt-publication", path)
    _publish_file(path, _model_content(receipt), immutable=True)
    try:
        _invoke_failure(failure, "receipt-publication-linked", path)
    except Exception:
        path.unlink(missing_ok=True)
        raise


def _replay_completed(
    paths: _CutoverPaths,
    request: TargetCutoverRequest,
    fingerprint: str,
) -> TargetCutoverResult:
    receipt = _read_receipt(paths.receipt)
    if receipt.request_fingerprint != fingerprint:
        _fail_receipt("target cutover receipt belongs to another request")
    manifest = TargetStoreManifest.model_validate_json((paths.target / "manifest.json").read_bytes())
    if hashlib.sha256(_model_content(manifest)).hexdigest() != receipt.target_manifest_sha256:
        _fail_receipt("target store differs from its cutover receipt")
    authorities = _read_target_authorities(paths, manifest)
    if authorities != request.authorities:
        _fail_receipt("reintroduced authority differs from the cutover request")
    for snapshot in receipt.snapshots:
        query_target_snapshot(paths.root, request, snapshot.snapshot_name)
    _verify_source_absence(paths.sources)
    _verify_adapter_refs(paths, receipt.adapter_refs)
    paths.pending.unlink(missing_ok=True)
    return TargetCutoverResult(receipt=receipt, authorities=authorities, replayed=True)


def _read_receipt(path: Path) -> TargetCutoverReceipt:
    try:
        return TargetCutoverReceipt.model_validate_json(path.read_bytes())
    except (OSError, ValueError) as exc:
        message = "target cutover receipt is absent or invalid"
        raise TargetCutoverReceiptError(message) from exc


def _read_target_authorities(
    paths: _CutoverPaths,
    manifest: TargetStoreManifest,
) -> tuple[TargetAuthority, ...]:
    try:
        return tuple(
            TargetAuthority.model_validate_json((paths.target / relative).read_bytes())
            for relative in manifest.authority_paths
        )
    except (OSError, ValueError) as exc:
        message = "target authority store is invalid"
        raise TargetCutoverReceiptError(message) from exc


def _verify_adapter_refs(paths: _CutoverPaths, refs: tuple[TargetAdapterRef, ...]) -> None:
    for path, reference in zip(paths.adapter_refs, refs, strict=True):
        if path.read_bytes() != reference.target.encode() + b"\n":
            _fail_receipt(f"adapter ref differs from receipt: {reference.relative_path}")


def _verify_source_absence(sources: tuple[Path, ...]) -> None:
    remaining = tuple(str(path) for path in sources if os.path.lexists(path))
    if remaining:
        _fail_receipt(f"bootstrap source paths remain active: {remaining}")


def _remove_sources(sources: tuple[Path, ...]) -> None:
    for source in sources:
        if source.is_symlink() or not source.is_dir():
            raise TargetCutoverPathError(source)
        shutil.rmtree(source)


def _rollback(paths: _CutoverPaths, request: TargetCutoverRequest, pending: _PendingCutover) -> None:
    paths.receipt.unlink(missing_ok=True)
    _restore_refs(paths, pending)
    _restore_sources(paths, request)
    _remove_path(paths.target)
    _remove_path(paths.snapshot)
    paths.pending.unlink(missing_ok=True)


def _restore_refs(paths: _CutoverPaths, pending: _PendingCutover) -> None:
    backups = {item.relative_path: item.content_base64 for item in pending.refs}
    for path in paths.adapter_refs:
        content = backups[str(path.relative_to(paths.root))]
        if content is None:
            path.unlink(missing_ok=True)
        else:
            _publish_file(path, b64decode(content), immutable=False)


def _restore_sources(paths: _CutoverPaths, request: TargetCutoverRequest) -> None:
    for source, specification in zip(paths.sources, request.sources, strict=True):
        snapshot = paths.snapshot / specification.snapshot_name
        if not snapshot.exists():
            continue
        verified = verify_legacy_snapshot(snapshot)
        if verified.manifest.source_digest != specification.expected_source_digest:
            _fail_receipt(f"rollback snapshot changed: {specification.snapshot_name}")
        _remove_path(source)
        source.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(snapshot / "content", source)


def _remove_path(path: Path) -> None:
    if path.is_symlink():
        raise TargetCutoverPathError(path)
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def _backup(path: Path) -> str | None:
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(metadata.st_mode):
        raise TargetCutoverPathError(path)
    return b64encode(path.read_bytes()).decode("ascii")


def _publish_file(path: Path, content: bytes, *, immutable: bool) -> None:
    _prepare_parent(path.parent)
    if immutable and path.exists():
        if path.read_bytes() == content:
            return
        _fail_receipt(f"cutover destination already exists: {path}")
    descriptor, temporary = tempfile.mkstemp(prefix=".tmp-cutover-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        if immutable:
            try:
                os.link(temporary, path, follow_symlinks=False)
            except FileExistsError:
                if path.read_bytes() != content:
                    _fail_receipt(f"cutover destination already exists: {path}")
        else:
            Path(temporary).replace(path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def _prepare_parent(path: Path) -> None:
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        if current.is_symlink():
            raise TargetCutoverPathError(current)
        current.mkdir(exist_ok=True)
        if not current.is_dir():
            raise TargetCutoverPathError(current)


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
