"""Durable publication of a bounded set of contained runtime records."""

from __future__ import annotations

import contextlib
import hashlib
import os
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from owlbear_kanban.storage_io import locked_roots

if TYPE_CHECKING:
    from collections.abc import Callable


class TransactionConflictError(RuntimeError):
    """A transaction destination already contains different immutable bytes."""

    code = "ERR_TRANSACTION_CONFLICT"


class TransactionPathError(ValueError):
    """A transaction participant escapes its explicit root."""

    code = "ERR_TRANSACTION_PATH_UNSAFE"


class TransactionManifestError(ValueError):
    """A pending transaction manifest is malformed or has been altered."""

    code = "ERR_TRANSACTION_MANIFEST_INVALID"


@dataclass(frozen=True)
class TransactionParticipant:
    """One immutable file publication rooted at an explicit directory."""

    root: Path
    relative_path: Path
    content: bytes

    def destination(self) -> Path:
        root = self.root.resolve()
        destination = (root / self.relative_path).resolve()
        if not self.relative_path.parts or self.relative_path.is_absolute() or root not in destination.parents:
            raise TransactionPathError
        return destination


@dataclass(frozen=True)
class ReplacementTransactionParticipant:
    """One contained replacement guarded by its current destination bytes."""

    root: Path
    relative_path: Path
    expected_content: bytes
    replacement_content: bytes

    def destination(self) -> Path:
        root = self.root.resolve()
        destination = (root / self.relative_path).resolve()
        if not self.relative_path.parts or self.relative_path.is_absolute() or root not in destination.parents:
            raise TransactionPathError
        return destination


class RuntimeTransaction:
    """Publish immutable participants with a recoverable commit manifest."""

    def __init__(
        self,
        manifest_root: Path,
        transaction_id: str,
        participants: tuple[TransactionParticipant | ReplacementTransactionParticipant, ...],
    ) -> None:
        if not transaction_id or not participants:
            msg = "transaction needs an ID and participants"
            raise ValueError(msg)
        self._manifest_root = manifest_root.resolve()
        self._transaction_id = transaction_id
        self._participants = participants

    @property
    def _directory(self) -> Path:
        return self._manifest_root / ".runtime-transactions"

    @property
    def _manifest_path(self) -> Path:
        return self._directory / f"{self._transaction_id}.yaml"

    def commit(self, *, failure: Callable[[str], None] | None = None) -> None:
        """Stage, record, and publish all participants exactly once."""
        with locked_roots(self._locked_roots()):
            self._prepare_manifest()
            if failure:
                failure("before-publication")
            self._publish(failure)
            if failure:
                failure("before-manifest-cleanup")
            self._cleanup()

    def recover(self) -> None:
        """Deterministically complete a previously staged transaction."""
        with locked_roots(self._locked_roots()):
            if self._manifest_path.exists():
                self._publish(None)
                self._cleanup()

    def _locked_roots(self) -> tuple[Path, ...]:
        return (self._manifest_root, *(participant.root for participant in self._participants))

    @classmethod
    def recover_all(cls, manifest_root: Path, *, roots: tuple[Path, ...] | None = None) -> None:
        """Complete every valid pending transaction rooted at ``manifest_root``."""
        resolved_root = manifest_root.resolve()
        allowed_roots = tuple(root.resolve() for root in (roots or (resolved_root,)))
        directory = resolved_root / ".runtime-transactions"
        if not directory.is_dir():
            return
        for manifest_path in sorted(directory.glob("*.yaml")):
            transaction = cls._from_manifest(resolved_root, manifest_path, allowed_roots)
            transaction.recover()

    @classmethod
    def _from_manifest(
        cls,
        manifest_root: Path,
        manifest_path: Path,
        allowed_roots: tuple[Path, ...],
    ) -> RuntimeTransaction:
        manifest = _load_yaml(manifest_path)
        entries = manifest.get("participants")
        if manifest.get("schema_version") not in (1, 2) or not isinstance(entries, list):
            raise TransactionManifestError
        if manifest["schema_version"] == 1 and any(
            isinstance(entry, dict) and entry.get("kind") == "replacement" for entry in entries
        ):
            raise TransactionManifestError
        participants = tuple(_participant_from_manifest(entry, allowed_roots) for entry in entries)
        if not participants:
            raise TransactionManifestError
        return cls(manifest_root, manifest_path.stem, participants)

    def _prepare_manifest(self) -> None:
        self._directory.mkdir(parents=True, exist_ok=True)
        manifest = self._manifest()
        if self._manifest_path.exists():
            if _load_yaml(self._manifest_path) != manifest:
                raise TransactionConflictError
            return
        for participant in self._participants:
            destination = participant.destination()
            if isinstance(participant, ReplacementTransactionParticipant):
                if not destination.exists() or destination.read_bytes() not in (
                    participant.expected_content,
                    participant.replacement_content,
                ):
                    raise TransactionConflictError
            elif destination.exists() and destination.read_bytes() != participant.content:
                raise TransactionConflictError
        _atomic_write_yaml(self._manifest_path, manifest)

    def _manifest(self) -> dict[str, object]:
        has_replacements = any(
            isinstance(participant, ReplacementTransactionParticipant) for participant in self._participants
        )
        schema_version = 2 if has_replacements else 1
        return {
            "schema_version": schema_version,
            "participants": [_participant_manifest(participant) for participant in self._participants],
        }

    def _publish(self, failure: Callable[[str], None] | None) -> None:
        for index, participant in enumerate(self._participants):
            destination = participant.destination()
            destination.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(participant, ReplacementTransactionParticipant):
                _publish_replacement(destination, participant)
                if failure and index == 0:
                    failure("after-first-publication")
                continue
            if destination.exists():
                if destination.read_bytes() != participant.content:
                    raise TransactionConflictError
                continue
            temporary = destination.with_name(f".tmp-{secrets.token_hex(12)}-{destination.name}")
            try:
                with temporary.open("xb") as handle:
                    handle.write(participant.content)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.link(temporary, destination)
                _fsync_directory(destination.parent)
            finally:
                with contextlib.suppress(FileNotFoundError):
                    temporary.unlink()
            if failure and index == 0:
                failure("after-first-publication")

    def _cleanup(self) -> None:
        self._manifest_path.unlink(missing_ok=True)
        _fsync_directory(self._directory)


def _atomic_write_yaml(path: Path, value: dict[str, object]) -> None:
    temporary = path.with_name(f".tmp-{secrets.token_hex(12)}-{path.name}")
    try:
        with temporary.open("x", encoding="utf-8") as handle:
            yaml.safe_dump(value, handle, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
        _fsync_directory(path.parent)
    finally:
        with contextlib.suppress(FileNotFoundError):
            temporary.unlink()


def _load_yaml(path: Path) -> dict[str, object]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise TransactionManifestError from exc
    return value if isinstance(value, dict) else {}


def _participant_from_manifest(
    entry: object, allowed_roots: tuple[Path, ...]
) -> TransactionParticipant | ReplacementTransactionParticipant:
    if not isinstance(entry, dict):
        raise TransactionManifestError
    if entry.get("kind") == "replacement":
        return _replacement_participant_from_manifest(entry, allowed_roots)
    root, path, digest, content = (entry.get(key) for key in ("root", "path", "sha256", "content"))
    if not all(isinstance(value, str) for value in (root, path, digest, content)):
        raise TransactionManifestError
    participant_root = Path(root).resolve()
    if participant_root not in allowed_roots:
        raise TransactionPathError
    try:
        participant_content = bytes.fromhex(content)
    except ValueError as exc:
        raise TransactionManifestError from exc
    if hashlib.sha256(participant_content).hexdigest() != digest:
        raise TransactionManifestError
    participant = TransactionParticipant(participant_root, Path(path), participant_content)
    participant.destination()
    return participant


def _participant_manifest(participant: TransactionParticipant | ReplacementTransactionParticipant) -> dict[str, str]:
    if isinstance(participant, ReplacementTransactionParticipant):
        return {
            "kind": "replacement",
            "root": str(participant.root.resolve()),
            "path": str(participant.relative_path),
            "expected_sha256": hashlib.sha256(participant.expected_content).hexdigest(),
            "expected_content": participant.expected_content.hex(),
            "replacement_sha256": hashlib.sha256(participant.replacement_content).hexdigest(),
            "replacement_content": participant.replacement_content.hex(),
        }
    return {
        "root": str(participant.root.resolve()),
        "path": str(participant.relative_path),
        "sha256": hashlib.sha256(participant.content).hexdigest(),
        "content": participant.content.hex(),
    }


def _replacement_participant_from_manifest(
    entry: dict[object, object], allowed_roots: tuple[Path, ...]
) -> ReplacementTransactionParticipant:
    root, path, expected_digest, expected_content, replacement_digest, replacement_content = (
        entry.get(key)
        for key in (
            "root",
            "path",
            "expected_sha256",
            "expected_content",
            "replacement_sha256",
            "replacement_content",
        )
    )
    if not all(
        isinstance(value, str)
        for value in (root, path, expected_digest, expected_content, replacement_digest, replacement_content)
    ):
        raise TransactionManifestError
    participant_root = Path(root).resolve()
    if participant_root not in allowed_roots:
        raise TransactionPathError
    try:
        expected_bytes = bytes.fromhex(expected_content)
        replacement_bytes = bytes.fromhex(replacement_content)
    except ValueError as exc:
        raise TransactionManifestError from exc
    if (
        hashlib.sha256(expected_bytes).hexdigest() != expected_digest
        or hashlib.sha256(replacement_bytes).hexdigest() != replacement_digest
    ):
        raise TransactionManifestError
    participant = ReplacementTransactionParticipant(participant_root, Path(path), expected_bytes, replacement_bytes)
    participant.destination()
    return participant


def _publish_replacement(destination: Path, participant: ReplacementTransactionParticipant) -> None:
    if not destination.exists() or destination.read_bytes() not in (
        participant.expected_content,
        participant.replacement_content,
    ):
        raise TransactionConflictError
    if destination.read_bytes() == participant.replacement_content:
        return
    temporary = destination.with_name(f".tmp-{secrets.token_hex(12)}-{destination.name}")
    try:
        with temporary.open("xb") as handle:
            handle.write(participant.replacement_content)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(destination)
        _fsync_directory(destination.parent)
    finally:
        with contextlib.suppress(FileNotFoundError):
            temporary.unlink()


def _fsync_directory(directory: Path) -> None:
    descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


__all__ = [
    "ReplacementTransactionParticipant",
    "RuntimeTransaction",
    "TransactionConflictError",
    "TransactionManifestError",
    "TransactionParticipant",
    "TransactionPathError",
]
