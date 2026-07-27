"""Immutable inventory and snapshot publication for legacy stores."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
from collections.abc import Callable, Mapping
from enum import StrEnum
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from owlbear_kanban.storage_io import locked_roots

_DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
_FILE_FLAGS = os.O_RDONLY | os.O_NOFOLLOW
_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class LegacyDisposition(StrEnum):
    """Explicit terminal treatment for one active legacy item."""

    REINTRODUCE_NATIVE = "reintroduce-native"
    COMPLETED_HISTORY = "completed-history"
    DROPPED = "dropped"
    SUPERSEDED = "superseded"


class LegacySnapshotError(RuntimeError):
    """Base class for fail-closed snapshot errors."""

    code = "ERR_LEGACY_SNAPSHOT"


class LegacySnapshotDispositionError(LegacySnapshotError):
    """Active-item dispositions are incomplete or invalid."""

    code = "ERR_LEGACY_SNAPSHOT_DISPOSITION"


class LegacySnapshotDestinationError(LegacySnapshotError):
    """The immutable destination already exists."""

    code = "ERR_LEGACY_SNAPSHOT_DESTINATION_EXISTS"


class LegacySnapshotPathError(LegacySnapshotError):
    """A source or destination path is unsafe."""

    code = "ERR_LEGACY_SNAPSHOT_PATH_UNSAFE"


class LegacySnapshotSourceChangedError(LegacySnapshotError):
    """The source changed while it was being captured."""

    code = "ERR_LEGACY_SNAPSHOT_SOURCE_CHANGED"


class LegacySnapshotVerificationError(LegacySnapshotError):
    """Staged counts or hashes differ from the source inventory."""

    code = "ERR_LEGACY_SNAPSHOT_VERIFICATION"


class LegacySnapshotPublicationError(LegacySnapshotError):
    """Snapshot staging or publication was interrupted."""

    code = "ERR_LEGACY_SNAPSHOT_PUBLICATION"


class _SnapshotModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class LegacyActiveItem(_SnapshotModel):
    """One caller-declared active legacy item requiring disposition."""

    item_id: str = Field(min_length=1)
    relative_path: str = Field(min_length=1)

    @field_validator("relative_path")
    @classmethod
    def validate_relative_path(cls, value: str) -> str:
        """Require one canonical relative POSIX path."""
        path = PurePosixPath(value)
        if (
            path.is_absolute()
            or PureWindowsPath(value).is_absolute()
            or any(part in {"", ".", ".."} for part in path.parts)
            or path.as_posix() != value
        ):
            message = "active item path must be canonical and relative"
            raise ValueError(message)
        return value


class LegacySnapshotFile(_SnapshotModel):
    """Hash and size for one regular legacy file."""

    relative_path: str
    sha256: str
    size: int = Field(ge=0)

    @field_validator("sha256")
    @classmethod
    def validate_digest(cls, value: str) -> str:
        """Require a lowercase SHA-256 digest."""
        if not _DIGEST_PATTERN.fullmatch(value):
            message = "sha256 must be a lowercase SHA-256 digest"
            raise ValueError(message)
        return value


class LegacySnapshotDisposition(_SnapshotModel):
    """Resolved disposition for one active item."""

    item_id: str
    relative_path: str
    disposition: LegacyDisposition


class LegacySnapshotManifest(_SnapshotModel):
    """Canonical immutable manifest for one captured legacy root."""

    schema_version: Literal[1] = 1
    source_digest: str
    directories: tuple[str, ...]
    files: tuple[LegacySnapshotFile, ...]
    active_items: tuple[LegacySnapshotDisposition, ...]
    directory_count: int = Field(ge=0)
    file_count: int = Field(ge=0)
    total_bytes: int = Field(ge=0)

    @field_validator("source_digest")
    @classmethod
    def validate_source_digest(cls, value: str) -> str:
        """Require a lowercase SHA-256 digest."""
        if not _DIGEST_PATTERN.fullmatch(value):
            message = "source_digest must be a lowercase SHA-256 digest"
            raise ValueError(message)
        return value

    @model_validator(mode="after")
    def validate_counts(self) -> LegacySnapshotManifest:
        """Keep aggregate counts bound to the recorded inventory."""
        if self.directory_count != len(self.directories):
            message = "directory_count does not match directories"
            raise ValueError(message)
        if self.file_count != len(self.files):
            message = "file_count does not match files"
            raise ValueError(message)
        if self.total_bytes != sum(item.size for item in self.files):
            message = "total_bytes does not match files"
            raise ValueError(message)
        return self


class LegacySnapshotResult(_SnapshotModel):
    """Published snapshot identity returned to a public adapter."""

    destination: Path
    manifest_path: Path
    manifest_sha256: str
    manifest: LegacySnapshotManifest

    @field_validator("manifest_sha256")
    @classmethod
    def validate_manifest_digest(cls, value: str) -> str:
        """Require a lowercase SHA-256 digest."""
        if not _DIGEST_PATTERN.fullmatch(value):
            message = "manifest_sha256 must be a lowercase SHA-256 digest"
            raise ValueError(message)
        return value


type SnapshotFailureHook = Callable[[str, Path], None]
type _Inventory = tuple[tuple[str, ...], tuple[LegacySnapshotFile, ...]]


def create_legacy_snapshot(
    source: Path,
    destination: Path,
    active_items: tuple[LegacyActiveItem, ...],
    dispositions: Mapping[str, LegacyDisposition],
    *,
    failure: SnapshotFailureHook | None = None,
) -> LegacySnapshotResult:
    """Publish a verified immutable copy of one caller-described legacy root."""
    source, destination = _validate_roots(source, destination)
    with locked_roots((destination.parent,)):
        if destination.exists() or destination.is_symlink():
            raise LegacySnapshotDestinationError(destination)
        inventory = _inventory(source)
        resolved_dispositions = _resolve_dispositions(active_items, dispositions, inventory)
        manifest = _build_manifest(inventory, resolved_dispositions)
        manifest_bytes = _manifest_bytes(manifest)
        staging = _staging_path(destination, manifest.source_digest)
        _remove_staging(staging)
        try:
            _materialize(source, staging, inventory, manifest_bytes)
            _invoke_failure(failure, "after-staging", staging)
            _verify_staging(staging, inventory, manifest_bytes)
            _ensure_source_stable(source, inventory)
            _invoke_failure(failure, "before-publication", staging)
            _ensure_destination_available(destination)
            staging.rename(destination)
            _fsync_directory(destination.parent)
        except LegacySnapshotError:
            _remove_staging(staging)
            raise
        except Exception as exc:
            _remove_staging(staging)
            raise LegacySnapshotPublicationError(str(exc)) from exc
    manifest_path = destination / "manifest.json"
    return LegacySnapshotResult(
        destination=destination,
        manifest_path=manifest_path,
        manifest_sha256=hashlib.sha256(manifest_bytes).hexdigest(),
        manifest=manifest,
    )


def _ensure_source_stable(source: Path, expected: _Inventory) -> None:
    if _inventory(source) != expected:
        raise LegacySnapshotSourceChangedError(source)


def _ensure_destination_available(destination: Path) -> None:
    if destination.exists() or destination.is_symlink():
        raise LegacySnapshotDestinationError(destination)


def _validate_roots(source: Path, destination: Path) -> tuple[Path, Path]:
    if source.is_symlink() or not source.is_dir():
        raise LegacySnapshotPathError(source)
    source = source.resolve()
    destination_parent = destination.parent
    if destination_parent.is_symlink():
        raise LegacySnapshotPathError(destination_parent)
    destination_parent.mkdir(parents=True, exist_ok=True)
    destination = destination_parent.resolve() / destination.name
    if not destination.name or source == destination or source in destination.parents or destination in source.parents:
        raise LegacySnapshotPathError(destination)
    return source, destination


def _inventory(source: Path) -> _Inventory:
    directories: list[str] = []
    files: list[LegacySnapshotFile] = []
    try:
        root_fd = os.open(source, _DIRECTORY_FLAGS)
    except OSError as exc:
        raise LegacySnapshotPathError(source) from exc
    try:
        _walk_directory(root_fd, PurePosixPath(), directories, files)
    finally:
        os.close(root_fd)
    return tuple(directories), tuple(files)


def _walk_directory(
    directory_fd: int,
    prefix: PurePosixPath,
    directories: list[str],
    files: list[LegacySnapshotFile],
) -> None:
    try:
        names = sorted(os.listdir(directory_fd))
    except OSError as exc:
        raise LegacySnapshotPathError(prefix.as_posix()) from exc
    for name in names:
        relative = prefix / name
        try:
            metadata = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        except OSError as exc:
            raise LegacySnapshotPathError(relative.as_posix()) from exc
        if stat.S_ISDIR(metadata.st_mode):
            directories.append(relative.as_posix())
            _walk_child_directory(directory_fd, name, relative, directories, files)
        elif stat.S_ISREG(metadata.st_mode):
            files.append(_read_file(directory_fd, name, relative, metadata))
        else:
            raise LegacySnapshotPathError(relative.as_posix())


def _walk_child_directory(
    parent_fd: int,
    name: str,
    relative: PurePosixPath,
    directories: list[str],
    files: list[LegacySnapshotFile],
) -> None:
    try:
        child_fd = os.open(name, _DIRECTORY_FLAGS, dir_fd=parent_fd)
    except OSError as exc:
        raise LegacySnapshotPathError(relative.as_posix()) from exc
    try:
        _walk_directory(child_fd, relative, directories, files)
    finally:
        os.close(child_fd)


def _read_file(
    directory_fd: int,
    name: str,
    relative: PurePosixPath,
    expected: os.stat_result,
) -> LegacySnapshotFile:
    content = _read_open_file(directory_fd, name, relative, expected)
    return LegacySnapshotFile(
        relative_path=relative.as_posix(),
        sha256=hashlib.sha256(content).hexdigest(),
        size=len(content),
    )


def _read_open_file(directory_fd: int, name: str, relative: PurePosixPath, expected: os.stat_result) -> bytes:
    try:
        file_fd = os.open(name, _FILE_FLAGS, dir_fd=directory_fd)
    except OSError as exc:
        raise LegacySnapshotPathError(relative.as_posix()) from exc
    try:
        opened = os.fstat(file_fd)
        if not stat.S_ISREG(opened.st_mode) or _identity(opened) != _identity(expected):
            raise LegacySnapshotSourceChangedError(relative.as_posix())
        with os.fdopen(file_fd, "rb") as handle:
            file_fd = -1
            return handle.read()
    finally:
        if file_fd >= 0:
            os.close(file_fd)


def _identity(metadata: os.stat_result) -> tuple[int, int, int, int]:
    return metadata.st_dev, metadata.st_ino, metadata.st_size, metadata.st_mtime_ns


def _resolve_dispositions(
    active_items: tuple[LegacyActiveItem, ...],
    dispositions: Mapping[str, LegacyDisposition],
    inventory: _Inventory,
) -> tuple[LegacySnapshotDisposition, ...]:
    item_ids = [item.item_id for item in active_items]
    item_paths = [item.relative_path for item in active_items]
    if len(set(item_ids)) != len(item_ids) or len(set(item_paths)) != len(item_paths):
        message = "active item IDs and paths must be unique"
        raise LegacySnapshotDispositionError(message)
    if set(dispositions) != set(item_ids):
        message = "dispositions must match active item IDs"
        raise LegacySnapshotDispositionError(message)
    known_paths = set(inventory[0]) | {item.relative_path for item in inventory[1]}
    resolved: list[LegacySnapshotDisposition] = []
    for item in active_items:
        if item.relative_path not in known_paths:
            message = f"active item path is not inventoried: {item.relative_path}"
            raise LegacySnapshotDispositionError(message)
        try:
            disposition = LegacyDisposition(dispositions[item.item_id])
        except ValueError as exc:
            raise LegacySnapshotDispositionError(item.item_id) from exc
        resolved.append(
            LegacySnapshotDisposition(
                item_id=item.item_id,
                relative_path=item.relative_path,
                disposition=disposition,
            )
        )
    return tuple(sorted(resolved, key=lambda item: item.item_id))


def _build_manifest(
    inventory: _Inventory,
    dispositions: tuple[LegacySnapshotDisposition, ...],
) -> LegacySnapshotManifest:
    directories, files = inventory
    envelope = {
        "directories": directories,
        "files": [item.model_dump(mode="json") for item in files],
    }
    canonical = json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode()
    return LegacySnapshotManifest(
        source_digest=hashlib.sha256(canonical).hexdigest(),
        directories=directories,
        files=files,
        active_items=dispositions,
        directory_count=len(directories),
        file_count=len(files),
        total_bytes=sum(item.size for item in files),
    )


def _manifest_bytes(manifest: LegacySnapshotManifest) -> bytes:
    return (json.dumps(manifest.model_dump(mode="json"), sort_keys=True, indent=2) + "\n").encode()


def _staging_path(destination: Path, source_digest: str) -> Path:
    return destination.with_name(f".tmp-snapshot-{destination.name}-{source_digest[:16]}")


def _remove_staging(path: Path) -> None:
    if path.is_symlink():
        raise LegacySnapshotPathError(path)
    if path.exists():
        if not path.is_dir():
            raise LegacySnapshotPathError(path)
        shutil.rmtree(path)
        _fsync_directory(path.parent)


def _materialize(source: Path, staging: Path, inventory: _Inventory, manifest_bytes: bytes) -> None:
    content_root = staging / "content"
    content_root.mkdir(parents=True)
    for relative in inventory[0]:
        (content_root / relative).mkdir(parents=True, exist_ok=True)
    for item in inventory[1]:
        target = content_root / item.relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        content = _read_relative_file(source, PurePosixPath(item.relative_path))
        if hashlib.sha256(content).hexdigest() != item.sha256 or len(content) != item.size:
            raise LegacySnapshotSourceChangedError(item.relative_path)
        _write_bytes(target, content)
    _write_bytes(staging / "manifest.json", manifest_bytes)
    _fsync_directory(staging)


def _read_relative_file(source: Path, relative: PurePosixPath) -> bytes:
    descriptors: list[int] = []
    try:
        current_fd = os.open(source, _DIRECTORY_FLAGS)
        descriptors.append(current_fd)
        for part in relative.parts[:-1]:
            current_fd = os.open(part, _DIRECTORY_FLAGS, dir_fd=current_fd)
            descriptors.append(current_fd)
        metadata = os.stat(relative.name, dir_fd=current_fd, follow_symlinks=False)
        return _read_open_file(current_fd, relative.name, relative, metadata)
    except LegacySnapshotError:
        raise
    except OSError as exc:
        raise LegacySnapshotPathError(relative.as_posix()) from exc
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def _write_bytes(path: Path, content: bytes) -> None:
    with path.open("xb") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
    _fsync_directory(path.parent)


def _verify_staging(staging: Path, inventory: _Inventory, manifest_bytes: bytes) -> None:
    if (staging / "manifest.json").read_bytes() != manifest_bytes:
        message = "manifest bytes differ"
        raise LegacySnapshotVerificationError(message)
    if _inventory(staging / "content") != inventory:
        message = "staged inventory differs"
        raise LegacySnapshotVerificationError(message)


def _invoke_failure(failure: SnapshotFailureHook | None, stage: str, staging: Path) -> None:
    if failure is not None:
        failure(stage, staging)


def _fsync_directory(directory: Path) -> None:
    descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
