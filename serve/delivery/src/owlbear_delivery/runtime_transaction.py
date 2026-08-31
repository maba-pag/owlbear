"""Durable publication of a bounded set of contained runtime records."""

from __future__ import annotations

import contextlib
import hashlib
import os
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Never

import yaml

from owlbear_delivery.storage_io import locked_roots

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
        """Return the participant destination after enforcing root containment."""
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
        """Return the replacement destination after enforcing root containment."""
        root = self.root.resolve()
        destination = (root / self.relative_path).resolve()
        if not self.relative_path.parts or self.relative_path.is_absolute() or root not in destination.parents:
            raise TransactionPathError
        return destination


@dataclass(frozen=True)
class MoveTransactionParticipant:
    """One contained move guarded by immutable source bytes."""

    root: Path
    source_path: Path
    destination_path: Path
    expected_content: bytes
    destination_content: bytes

    def source(self) -> Path:
        """Return the move source after enforcing root containment."""
        return _contained_path(self.root, self.source_path)

    def destination(self) -> Path:
        """Return the move destination after enforcing root containment."""
        return _contained_path(self.root, self.destination_path)


def _contained_path(root: Path, relative_path: Path) -> Path:
    resolved_root = root.resolve()
    path = (resolved_root / relative_path).resolve()
    if not relative_path.parts or relative_path.is_absolute() or resolved_root not in path.parents:
        raise TransactionPathError
    return path


class RuntimeTransaction:
    """Publish immutable participants with a recoverable commit manifest."""

    def __init__(
        self,
        manifest_root: Path,
        transaction_id: str,
        participants: tuple[
            TransactionParticipant | ReplacementTransactionParticipant | MoveTransactionParticipant, ...
        ],
    ) -> None:
        if not transaction_id or not participants:
            msg = "transaction needs an ID and participants"
            raise ValueError(msg)
        self._manifest_root = manifest_root.resolve()
        self._transaction_id = transaction_id
        self._participants = participants
        self._abort_snapshot: dict[Path, bytes | None] | None = None

    @property
    def _directory(self) -> Path:
        return self._manifest_root / "transactions"

    @property
    def _manifest_path(self) -> Path:
        return self._directory / f"{self._transaction_id}.yaml"

    def commit(self, *, failure: Callable[[str], None] | None = None) -> None:
        """Stage, record, and publish all participants exactly once."""
        with locked_roots(self._locked_roots()):
            self._migrate_legacy_directory(self._manifest_root)
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
            self._migrate_legacy_directory(self._manifest_root)
            if self._manifest_path.exists():
                self._publish(None)
                self._cleanup()

    def abort(self) -> None:
        """Restore prepared participant bytes after a handled publication failure."""
        with locked_roots(self._locked_roots()):
            self._migrate_legacy_directory(self._manifest_root)
            if not self._manifest_path.exists():
                return
            if self._abort_snapshot is None:
                raise TransactionConflictError
            for path, content in reversed(self._abort_snapshot.items()):
                _restore_path(path, content)
            self._cleanup()

    def _locked_roots(self) -> tuple[Path, ...]:
        return (self._manifest_root, *(participant.root for participant in self._participants))

    @classmethod
    def recover_all(cls, manifest_root: Path, *, roots: tuple[Path, ...] | None = None) -> None:
        """Complete every valid pending transaction rooted at ``manifest_root``."""
        resolved_root = manifest_root.resolve()
        allowed_roots = tuple(root.resolve() for root in (roots or (resolved_root,)))
        cls._migrate_legacy_directory(resolved_root)
        directory = resolved_root / "transactions"
        manifest_paths = tuple(sorted(directory.glob("*.yaml"))) if directory.is_dir() else ()
        for manifest_path in manifest_paths:
            transaction = cls._from_manifest(resolved_root, manifest_path, allowed_roots)
            transaction.recover()

    @classmethod
    def _migrate_legacy_directory(cls, manifest_root: Path) -> None:
        # Transitional input only; current recovery uses transactions/.
        directory = manifest_root / "transactions"
        legacy_directory = manifest_root / ".runtime-transactions"
        canonical_present = directory.exists() or directory.is_symlink()
        legacy_present = legacy_directory.exists() or legacy_directory.is_symlink()
        if canonical_present:
            if legacy_present:
                _manifest_error("both transaction directories are present")
            if directory.is_symlink() or not directory.is_dir():
                _manifest_error("transaction directory is unsafe")
            return
        if not legacy_present:
            return
        if legacy_directory.is_symlink() or not legacy_directory.is_dir():
            _manifest_error("legacy transaction directory is unsafe")
        try:
            legacy_directory.rename(directory)
        except OSError as exc:
            if directory.is_dir() and not legacy_directory.exists():
                return
            try:
                _manifest_error("legacy transaction directory could not be migrated")
            except TransactionManifestError as error:
                raise error from exc

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
            if isinstance(participant, MoveTransactionParticipant):
                source = participant.source()
                source_matches = source.exists() and source.read_bytes() == participant.expected_content
                destination_matches = (
                    destination.exists() and destination.read_bytes() == participant.destination_content
                )
                if not source_matches or destination_matches:
                    raise TransactionConflictError
            elif isinstance(participant, ReplacementTransactionParticipant):
                if not destination.exists() or destination.read_bytes() not in (
                    participant.expected_content,
                    participant.replacement_content,
                ):
                    raise TransactionConflictError
            elif destination.exists() and destination.read_bytes() != participant.content:
                raise TransactionConflictError
        self._abort_snapshot = {
            path: path.read_bytes() if path.exists() else None for path in self._participant_paths()
        }
        _atomic_write_yaml(self._manifest_path, manifest)

    def _participant_paths(self) -> tuple[Path, ...]:
        paths: list[Path] = []
        for participant in self._participants:
            if isinstance(participant, MoveTransactionParticipant):
                candidates = (participant.source(), participant.destination())
            else:
                candidates = (participant.destination(),)
            for path in candidates:
                if path not in paths:
                    paths.append(path)
        return tuple(paths)

    def _manifest(self) -> dict[str, object]:
        has_replacements = any(
            isinstance(participant, ReplacementTransactionParticipant | MoveTransactionParticipant)
            for participant in self._participants
        )
        schema_version = 2 if has_replacements else 1
        return {
            "schema_version": schema_version,
            "participants": [_participant_manifest(participant) for participant in self._participants],
        }

    def _publish(self, failure: Callable[[str], None] | None) -> None:
        for index, participant in enumerate(self._participants):
            destination = participant.destination()
            if isinstance(participant, MoveTransactionParticipant):
                _publish_move(
                    participant.source(),
                    destination,
                    participant.expected_content,
                    participant.destination_content,
                )
                if failure and index == 0:
                    failure("after-first-publication")
                continue
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
        self._abort_snapshot = None


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


def _manifest_error(detail: str) -> Never:
    raise TransactionManifestError(detail)


def _participant_from_manifest(
    entry: object, allowed_roots: tuple[Path, ...]
) -> TransactionParticipant | ReplacementTransactionParticipant | MoveTransactionParticipant:
    if not isinstance(entry, dict):
        raise TransactionManifestError
    if entry.get("kind") == "move":
        return _move_participant_from_manifest(entry, allowed_roots)
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


def _participant_manifest(
    participant: TransactionParticipant | ReplacementTransactionParticipant | MoveTransactionParticipant,
) -> dict[str, str]:
    if isinstance(participant, MoveTransactionParticipant):
        return {
            "kind": "move",
            "root": str(participant.root.resolve()),
            "source_path": str(participant.source_path),
            "destination_path": str(participant.destination_path),
            "expected_sha256": hashlib.sha256(participant.expected_content).hexdigest(),
            "expected_content": participant.expected_content.hex(),
            "destination_sha256": hashlib.sha256(participant.destination_content).hexdigest(),
            "destination_content": participant.destination_content.hex(),
        }
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


def _move_participant_from_manifest(
    entry: dict[object, object], allowed_roots: tuple[Path, ...]
) -> MoveTransactionParticipant:
    root, source_path, destination_path, expected_digest, expected_content, destination_digest, destination_content = (
        entry.get(key)
        for key in (
            "root",
            "source_path",
            "destination_path",
            "expected_sha256",
            "expected_content",
            "destination_sha256",
            "destination_content",
        )
    )
    if not all(
        isinstance(value, str)
        for value in (
            root,
            source_path,
            destination_path,
            expected_digest,
            expected_content,
            destination_digest,
            destination_content,
        )
    ):
        raise TransactionManifestError
    participant_root = Path(root).resolve()
    if participant_root not in allowed_roots:
        raise TransactionPathError
    try:
        expected_bytes = bytes.fromhex(expected_content)
        destination_bytes = bytes.fromhex(destination_content)
    except ValueError as exc:
        raise TransactionManifestError from exc
    if (
        hashlib.sha256(expected_bytes).hexdigest() != expected_digest
        or hashlib.sha256(destination_bytes).hexdigest() != destination_digest
    ):
        raise TransactionManifestError
    participant = MoveTransactionParticipant(
        participant_root,
        Path(source_path),
        Path(destination_path),
        expected_bytes,
        destination_bytes,
    )
    participant.source()
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


def _publish_move(
    source: Path,
    destination: Path,
    expected_content: bytes,
    destination_content: bytes,
) -> None:
    if destination.exists():
        if destination.read_bytes() != destination_content:
            raise TransactionConflictError
        if source.exists():
            if source.read_bytes() != expected_content:
                raise TransactionConflictError
            source.unlink()
            _fsync_directory(source.parent)
        return
    if not source.exists() or source.read_bytes() != expected_content:
        raise TransactionConflictError
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".tmp-{secrets.token_hex(12)}-{destination.name}")
    try:
        with temporary.open("xb") as handle:
            handle.write(destination_content)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, destination)
        _fsync_directory(destination.parent)
    finally:
        with contextlib.suppress(FileNotFoundError):
            temporary.unlink()
    source.unlink()
    _fsync_directory(source.parent)


def _restore_path(path: Path, content: bytes | None) -> None:
    if content is None:
        if path.exists():
            path.unlink()
            _fsync_directory(path.parent)
        return
    if path.exists() and path.read_bytes() == content:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    _replace_bytes(path, content)


def _replace_bytes(destination: Path, content: bytes) -> None:
    temporary = destination.with_name(f".tmp-{secrets.token_hex(12)}-{destination.name}")
    try:
        with temporary.open("xb") as handle:
            handle.write(content)
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
    "MoveTransactionParticipant",
    "ReplacementTransactionParticipant",
    "RuntimeTransaction",
    "TransactionConflictError",
    "TransactionManifestError",
    "TransactionParticipant",
    "TransactionPathError",
]
