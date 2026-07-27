"""Fail-closed finalization of the external bootstrap carrier."""

from __future__ import annotations

import json
import os
import re
import shutil
import stat
import tempfile
from collections.abc import Mapping
from contextlib import suppress
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Literal, Never

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from owlbear_kanban.snapshot import (
    LegacyActiveItem,
    LegacyDisposition,
    LegacySnapshotDestinationError,
    LegacySnapshotError,
    LegacySnapshotManifest,
    LegacySnapshotResult,
    LegacySnapshotVerificationError,
    SnapshotFailureHook,
    create_legacy_snapshot,
    inventory_legacy_source,
    verify_legacy_snapshot,
)

_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class BootstrapFinalizationError(RuntimeError):
    """Base class for typed bootstrap finalization failures."""

    code = "ERR_BOOTSTRAP_FINALIZATION"


class BootstrapFinalizationPreconditionError(BootstrapFinalizationError):
    """Finalization readiness or currentness is not satisfied."""

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        super().__init__(detail)


class BootstrapFinalizationPathError(BootstrapFinalizationError):
    """A finalization path escapes or aliases another transaction path."""

    code = "ERR_BOOTSTRAP_FINALIZATION_PATH_UNSAFE"


class BootstrapFinalizationCurrentnessError(BootstrapFinalizationError):
    """The authority, code revision, or source inventory is stale."""

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        super().__init__(detail)


class BootstrapFinalizationPublicationError(BootstrapFinalizationError):
    """Snapshot, removal, or receipt publication was interrupted."""

    code = "ERR_BOOTSTRAP_FINALIZATION_PUBLICATION"


class BootstrapFinalizationAbsenceError(BootstrapFinalizationError):
    """An active carrier path remains after attempted removal."""

    code = "ERR_BOOTSTRAP_FINALIZATION_ABSENCE"


class BootstrapFinalizationReceiptError(BootstrapFinalizationError):
    """Persisted finalization intent or receipt conflicts with this request."""

    code = "ERR_BOOTSTRAP_FINALIZATION_RECEIPT"


class _FinalizationModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class BootstrapFinalizationReadiness(_FinalizationModel):
    """Caller-observed terminal state required before destructive cutover."""

    terminal: bool
    proof_verified: bool = True
    active_claim_ids: tuple[str, ...] = ()
    active_writer_ids: tuple[str, ...] = ()
    pending_request_ids: tuple[str, ...] = ()
    unclassified_record_ids: tuple[str, ...] = ()


class BootstrapFinalizationRequest(_FinalizationModel):
    """Complete immutable input to one bootstrap finalization attempt."""

    source_path: str
    sibling_carrier_path: str
    snapshot_path: str
    receipt_path: str
    active_items: tuple[LegacyActiveItem, ...]
    dispositions: Mapping[str, LegacyDisposition]
    expected_source_digest: str
    expected_delivery_digest: str
    actual_delivery_digest: str
    expected_code_revision: str
    actual_code_revision: str
    approval: Literal["FINALIZE_BOOTSTRAP_CARRIER"]
    readiness: BootstrapFinalizationReadiness

    @field_validator("source_path", "sibling_carrier_path", "snapshot_path", "receipt_path")
    @classmethod
    def validate_relative_path(cls, value: str) -> str:
        """Require one canonical workspace-relative POSIX path."""
        path = PurePosixPath(value)
        if (
            path.is_absolute()
            or PureWindowsPath(value).is_absolute()
            or any(part in {"", ".", ".."} for part in path.parts)
            or path.as_posix() != value
        ):
            message = "finalization paths must be canonical and workspace-relative"
            raise ValueError(message)
        return value

    @field_validator(
        "expected_source_digest",
        "expected_delivery_digest",
        "actual_delivery_digest",
        "expected_code_revision",
        "actual_code_revision",
    )
    @classmethod
    def validate_digest(cls, value: str) -> str:
        """Require lowercase SHA-256 identities."""
        if not _DIGEST_PATTERN.fullmatch(value):
            message = "revision identities must be lowercase SHA-256 digests"
            raise ValueError(message)
        return value


class BootstrapFinalizationReceipt(_FinalizationModel):
    """Immutable proof that both active carrier paths were retired."""

    schema_version: Literal[1] = 1
    receipt_id: str
    request_fingerprint: str
    delivery_digest: str
    code_revision: str
    source_digest: str
    snapshot_manifest_sha256: str
    approval: Literal["FINALIZE_BOOTSTRAP_CARRIER"]
    snapshot_path: str
    snapshot_manifest_path: str
    removed_paths: tuple[str, str]
    tracked_paths: tuple[str, str, str, str]

    @field_validator(
        "receipt_id",
        "request_fingerprint",
        "delivery_digest",
        "code_revision",
        "source_digest",
        "snapshot_manifest_sha256",
    )
    @classmethod
    def validate_digest(cls, value: str) -> str:
        """Require lowercase SHA-256 identities."""
        if not _DIGEST_PATTERN.fullmatch(value):
            message = "receipt identities must be lowercase SHA-256 digests"
            raise ValueError(message)
        return value

    @model_validator(mode="after")
    def validate_receipt_id(self) -> BootstrapFinalizationReceipt:
        """Bind the receipt ID to all other immutable receipt fields."""
        if self.receipt_id != _receipt_id(self.model_dump(mode="json", exclude={"receipt_id"})):
            message = "receipt_id does not match receipt content"
            raise ValueError(message)
        return self


class BootstrapFinalizationResult(_FinalizationModel):
    """Public finalization result containing exact caller commit paths."""

    receipt: BootstrapFinalizationReceipt
    snapshot_manifest_path: str
    snapshot_manifest_sha256: str
    removed_paths: tuple[str, str]
    tracked_paths: tuple[str, str, str, str]
    replayed: bool


type FinalizationFailureHook = SnapshotFailureHook
type _ReceiptPayload = dict[str, object]


@dataclass(frozen=True)
class _FinalizationPaths:
    root: Path
    source: Path
    carrier: Path
    snapshot: Path
    receipt: Path
    pending: Path


def finalize_bootstrap_carrier(
    workspace_root: Path,
    request: BootstrapFinalizationRequest,
    *,
    failure: FinalizationFailureHook | None = None,
) -> BootstrapFinalizationResult:
    """Finalize one external bootstrap carrier or replay its exact result."""
    _validate_preconditions(request)
    paths = _resolve_paths(workspace_root, request)
    request_fingerprint = _request_fingerprint(request)
    if paths.receipt.exists():
        return _replay_completed(paths, request, request_fingerprint)
    source_manifest = _preflight_source(paths, request)
    pending_exists = _validate_pending(paths.pending, request_fingerprint)
    snapshot_exists = paths.snapshot.exists()
    if snapshot_exists and not pending_exists:
        raise LegacySnapshotDestinationError(paths.snapshot)
    if not snapshot_exists and not paths.carrier.exists():
        raise BootstrapFinalizationPathError(paths.carrier)
    _ensure_pending(paths, request_fingerprint)
    snapshot = _prepare_snapshot(paths, request, source_manifest, failure)
    try:
        _invoke_failure(failure, "after-snapshot", paths.snapshot)
        snapshot = verify_legacy_snapshot(paths.snapshot)
    except LegacySnapshotVerificationError:
        if paths.source.exists():
            _remove_snapshot(paths.snapshot)
            _remove_file(paths.pending)
        raise
    except Exception as exc:
        raise BootstrapFinalizationPublicationError(str(exc)) from exc
    try:
        _remove_active_path(paths.source)
        _invoke_failure(failure, "after-source-removal", paths.source)
        _remove_active_path(paths.carrier)
        _invoke_failure(failure, "before-absence-verification", paths.root)
        _verify_absence(paths)
        receipt = _build_receipt(request, request_fingerprint, snapshot)
        _invoke_failure(failure, "before-receipt-publication", paths.receipt)
        _publish_json(paths.receipt, receipt.model_dump(mode="json"), failure=failure)
    except BootstrapFinalizationError, LegacySnapshotError:
        raise
    except Exception as exc:
        raise BootstrapFinalizationPublicationError(str(exc)) from exc
    _best_effort_remove_file(paths.pending)
    return _result(receipt, replayed=False)


def _validate_preconditions(request: BootstrapFinalizationRequest) -> None:
    readiness = request.readiness
    if not readiness.proof_verified:
        _fail_precondition(
            "ERR_BOOTSTRAP_FINALIZATION_PROOF_STALE",
            "finalization proof is missing or stale",
        )
    if not readiness.terminal:
        _fail_precondition(
            "ERR_BOOTSTRAP_FINALIZATION_NONTERMINAL",
            "legacy projection is not terminal",
        )
    if readiness.active_claim_ids:
        _fail_precondition(
            "ERR_BOOTSTRAP_FINALIZATION_ACTIVE_CLAIMS",
            "active claims block bootstrap finalization",
        )
    if readiness.active_writer_ids:
        _fail_precondition(
            "ERR_BOOTSTRAP_FINALIZATION_ACTIVE_WRITERS",
            "active writers block bootstrap finalization",
        )
    if readiness.pending_request_ids:
        _fail_precondition(
            "ERR_BOOTSTRAP_FINALIZATION_PENDING_REQUESTS",
            "pending requests block bootstrap finalization",
        )
    if readiness.unclassified_record_ids:
        _fail_precondition(
            "ERR_BOOTSTRAP_FINALIZATION_UNCLASSIFIED",
            "unclassified records block bootstrap finalization",
        )
    if request.expected_delivery_digest != request.actual_delivery_digest:
        _fail_currentness(
            "ERR_BOOTSTRAP_FINALIZATION_AUTHORITY_STALE",
            "delivery authority does not match the expected revision",
        )
    if request.expected_code_revision != request.actual_code_revision:
        _fail_currentness(
            "ERR_BOOTSTRAP_FINALIZATION_CODE_STALE",
            "code does not match the expected revision",
        )


def _fail_precondition(code: str, detail: str) -> Never:
    raise BootstrapFinalizationPreconditionError(code, detail)


def _fail_currentness(code: str, detail: str) -> Never:
    raise BootstrapFinalizationCurrentnessError(code, detail)


def _fail_path(detail: object) -> Never:
    raise BootstrapFinalizationPathError(detail)


def _fail_receipt(detail: str) -> Never:
    raise BootstrapFinalizationReceiptError(detail)


def _fail_absence(detail: str) -> Never:
    raise BootstrapFinalizationAbsenceError(detail)


def _resolve_paths(workspace_root: Path, request: BootstrapFinalizationRequest) -> _FinalizationPaths:
    if workspace_root.is_symlink() or not workspace_root.is_dir():
        raise BootstrapFinalizationPathError(workspace_root)
    root = workspace_root.resolve()
    resolved = tuple(_resolve_workspace_path(root, value) for value in _request_paths(request))
    for index, path in enumerate(resolved):
        for other in resolved[index + 1 :]:
            if path == other or path in other.parents or other in path.parents:
                _fail_path(f"overlapping finalization paths: {path}, {other}")
    source, carrier, snapshot, receipt = resolved
    return _FinalizationPaths(
        root=root,
        source=source,
        carrier=carrier,
        snapshot=snapshot,
        receipt=receipt,
        pending=receipt.with_name(f".{receipt.name}.pending"),
    )


def _request_paths(request: BootstrapFinalizationRequest) -> tuple[str, str, str, str]:
    return request.source_path, request.sibling_carrier_path, request.snapshot_path, request.receipt_path


def _resolve_workspace_path(root: Path, value: str) -> Path:
    path = root.joinpath(*PurePosixPath(value).parts)
    current = root
    for part in path.relative_to(root).parts:
        current /= part
        if current.is_symlink():
            raise BootstrapFinalizationPathError(current)
        if current.exists() and current != path and not current.is_dir():
            raise BootstrapFinalizationPathError(current)
    return path


def _preflight_source(
    paths: _FinalizationPaths,
    request: BootstrapFinalizationRequest,
) -> LegacySnapshotManifest | None:
    if not paths.source.exists():
        if paths.snapshot.exists() or paths.receipt.exists():
            return None
        raise BootstrapFinalizationPathError(paths.source)
    manifest = inventory_legacy_source(paths.source, request.active_items, request.dispositions)
    if manifest.source_digest != request.expected_source_digest:
        _fail_currentness(
            "ERR_BOOTSTRAP_FINALIZATION_SOURCE_CHANGED",
            "legacy source does not match the verified inventory",
        )
    return manifest


def _prepare_snapshot(
    paths: _FinalizationPaths,
    request: BootstrapFinalizationRequest,
    source_manifest: LegacySnapshotManifest | None,
    failure: FinalizationFailureHook | None,
) -> LegacySnapshotResult:
    if paths.snapshot.exists():
        snapshot = verify_legacy_snapshot(paths.snapshot)
    else:
        try:
            snapshot = create_legacy_snapshot(
                paths.source,
                paths.snapshot,
                request.active_items,
                request.dispositions,
                failure=failure,
            )
        except LegacySnapshotError:
            if not paths.snapshot.exists():
                _remove_file(paths.pending)
            raise
    if snapshot.manifest.source_digest != request.expected_source_digest:
        if paths.source.exists():
            _remove_snapshot(paths.snapshot)
            _remove_file(paths.pending)
        _fail_currentness(
            "ERR_BOOTSTRAP_FINALIZATION_SOURCE_CHANGED",
            "published snapshot does not match the verified inventory",
        )
    if source_manifest is not None and snapshot.manifest != source_manifest:
        _fail_currentness(
            "ERR_BOOTSTRAP_FINALIZATION_SOURCE_CHANGED",
            "legacy source changed during finalization",
        )
    return snapshot


def _request_fingerprint(request: BootstrapFinalizationRequest) -> str:
    return sha256(_canonical_json(request.model_dump(mode="json"))).hexdigest()


def _validate_pending(path: Path, request_fingerprint: str) -> bool:
    if not path.exists():
        return False
    try:
        payload = json.loads(_read_regular_file(path))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        message = "pending finalization intent is invalid"
        raise BootstrapFinalizationReceiptError(message) from exc
    if payload != {"request_fingerprint": request_fingerprint}:
        _fail_receipt("pending finalization belongs to a different request")
    return True


def _ensure_pending(paths: _FinalizationPaths, request_fingerprint: str) -> None:
    if _validate_pending(paths.pending, request_fingerprint):
        return
    _publish_json(paths.pending, {"request_fingerprint": request_fingerprint})


def _build_receipt(
    request: BootstrapFinalizationRequest,
    request_fingerprint: str,
    snapshot: LegacySnapshotResult,
) -> BootstrapFinalizationReceipt:
    removed_paths = (request.source_path, request.sibling_carrier_path)
    tracked_paths = (*removed_paths, request.snapshot_path, request.receipt_path)
    payload: _ReceiptPayload = {
        "schema_version": 1,
        "request_fingerprint": request_fingerprint,
        "delivery_digest": request.actual_delivery_digest,
        "code_revision": request.actual_code_revision,
        "source_digest": snapshot.manifest.source_digest,
        "snapshot_manifest_sha256": snapshot.manifest_sha256,
        "approval": request.approval,
        "snapshot_path": request.snapshot_path,
        "snapshot_manifest_path": f"{request.snapshot_path}/manifest.json",
        "removed_paths": removed_paths,
        "tracked_paths": tracked_paths,
    }
    return BootstrapFinalizationReceipt(receipt_id=_receipt_id(payload), **payload)


def _receipt_id(payload: Mapping[str, object]) -> str:
    return sha256(_canonical_json(payload)).hexdigest()


def _canonical_json(payload: object) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def _publish_json(
    path: Path,
    payload: object,
    *,
    failure: FinalizationFailureHook | None = None,
) -> None:
    _prepare_parent(path.parent)
    content = json.dumps(payload, sort_keys=True, indent=2).encode() + b"\n"
    descriptor, temporary = tempfile.mkstemp(prefix=".tmp-finalization-", dir=path.parent)
    linked = False
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        try:
            os.link(temporary, path, follow_symlinks=False)
            linked = True
        except FileExistsError as exc:
            message = f"finalization file already exists: {path}"
            raise BootstrapFinalizationReceiptError(message) from exc
        _invoke_failure(failure, "after-receipt-link", path)
        directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except Exception:
        if linked:
            _remove_file(path)
        raise
    finally:
        Path(temporary).unlink(missing_ok=True)


def _prepare_parent(path: Path) -> None:
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        if current.is_symlink():
            raise BootstrapFinalizationPathError(current)
        current.mkdir(exist_ok=True)
        if not current.is_dir():
            raise BootstrapFinalizationPathError(current)


def _read_regular_file(path: Path) -> str:
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise BootstrapFinalizationPathError(path)
        with os.fdopen(descriptor, encoding="utf-8") as source:
            descriptor = -1
            return source.read()
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _remove_active_path(path: Path) -> None:
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return
    if stat.S_ISLNK(metadata.st_mode):
        raise BootstrapFinalizationPathError(path)
    if stat.S_ISDIR(metadata.st_mode):
        shutil.rmtree(path)
    elif stat.S_ISREG(metadata.st_mode):
        path.unlink()
    else:
        raise BootstrapFinalizationPathError(path)


def _verify_absence(paths: _FinalizationPaths) -> None:
    remaining = tuple(path for path in (paths.source, paths.carrier) if os.path.lexists(path))
    if remaining:
        _fail_absence(f"active carrier paths remain: {remaining}")


def _replay_completed(
    paths: _FinalizationPaths,
    request: BootstrapFinalizationRequest,
    request_fingerprint: str,
) -> BootstrapFinalizationResult:
    _verify_absence(paths)
    snapshot = verify_legacy_snapshot(paths.snapshot)
    expected = _build_receipt(request, request_fingerprint, snapshot)
    try:
        receipt = BootstrapFinalizationReceipt.model_validate_json(_read_regular_file(paths.receipt))
    except ValueError as exc:
        message = "finalization receipt is invalid"
        raise BootstrapFinalizationReceiptError(message) from exc
    if receipt != expected:
        _fail_receipt("finalization receipt does not match this request")
    _best_effort_remove_file(paths.pending)
    return _result(receipt, replayed=True)


def _result(receipt: BootstrapFinalizationReceipt, *, replayed: bool) -> BootstrapFinalizationResult:
    return BootstrapFinalizationResult(
        receipt=receipt,
        snapshot_manifest_path=receipt.snapshot_manifest_path,
        snapshot_manifest_sha256=receipt.snapshot_manifest_sha256,
        removed_paths=receipt.removed_paths,
        tracked_paths=receipt.tracked_paths,
        replayed=replayed,
    )


def _remove_snapshot(path: Path) -> None:
    if path.is_symlink() or not path.is_dir():
        raise BootstrapFinalizationPathError(path)
    shutil.rmtree(path)


def _remove_file(path: Path) -> None:
    with suppress(FileNotFoundError):
        path.unlink()


def _best_effort_remove_file(path: Path) -> None:
    with suppress(OSError):
        path.unlink()


def _invoke_failure(failure: FinalizationFailureHook | None, stage: str, path: Path) -> None:
    if failure is not None:
        failure(stage, path)
