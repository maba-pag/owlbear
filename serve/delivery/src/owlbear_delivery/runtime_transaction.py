"""Durable publication of a bounded set of contained runtime records."""

from __future__ import annotations

import contextlib
import hashlib
import os
import re
import secrets
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Never

import yaml

from owlbear_delivery.storage_io import locked_roots

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

_MAX_CONTAINED_MANIFEST_BYTES = 131_072
_MAX_CONTAINED_MANIFESTS = 256
_MAX_CONTAINED_PARTICIPANTS = 2
_MAX_CONTAINED_TEMPORARIES = 256
_MAX_CONTAINED_TEMPORARY_BYTES = _MAX_CONTAINED_MANIFEST_BYTES * _MAX_CONTAINED_TEMPORARIES
_CONTAINED_TEMPORARY_PATTERN = re.compile(r"^\.tmp-[0-9a-f]{24}$")
_CONTAINED_TEMPORARY_MODE = stat.S_IRUSR | stat.S_IWUSR


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

    def abort(self) -> None:
        """Restore prepared participant bytes after a handled publication failure."""
        with locked_roots(self._locked_roots()):
            if not self._manifest_path.exists():
                return
            if self._abort_snapshot is None:
                raise TransactionConflictError
            for path, content in reversed(self._abort_snapshot.items()):
                _restore_path(path, content)
            self._cleanup()

    def _locked_roots(self) -> tuple[Path, ...]:
        return (self._manifest_root, *(participant.root for participant in self._participants))

    def commit_contained(self, root_fd: int, *, failure: Callable[[str], None] | None = None) -> None:
        """Publish report participants under a caller-held descriptor-backed lock."""
        self._require_contained_root(root_fd)
        manifest = self._contained_manifest()
        path = Path("transactions") / f"{self._transaction_id}.yaml"
        content = yaml.safe_dump(manifest, sort_keys=True).encode()
        if len(content) > _MAX_CONTAINED_MANIFEST_BYTES:
            raise TransactionManifestError
        for participant in self._participants:
            self._check_contained_participant(root_fd, participant)
        write_contained(root_fd, path, content)
        if failure:
            failure("before-publication")
        self._publish_contained(root_fd, failure)
        if failure:
            failure("before-manifest-cleanup")
        self._require_contained_root(root_fd)
        with contained_directory(root_fd, Path("transactions")) as directory_fd:
            os.unlink(path.name, dir_fd=directory_fd)
            os.fsync(directory_fd)

    def _require_contained_root(self, root_fd: int) -> None:
        observed = self._manifest_root.lstat()
        pinned = os.fstat(root_fd)
        if (
            self._manifest_root.resolve() != self._manifest_root
            or not stat.S_ISDIR(observed.st_mode)
            or (observed.st_dev, observed.st_ino) != (pinned.st_dev, pinned.st_ino)
        ):
            raise TransactionPathError

    def _contained_manifest(self) -> dict[str, object]:
        if Path(self._transaction_id).name != self._transaction_id or self._transaction_id in (".", ".."):
            raise TransactionPathError
        for participant in self._participants:
            if isinstance(participant, MoveTransactionParticipant) or participant.root != self._manifest_root:
                raise TransactionPathError
            _relative_parts(participant.relative_path)
        manifest = self._manifest()
        if any(entry["root"] != str(self._manifest_root) for entry in manifest["participants"]):
            raise TransactionPathError
        return manifest

    @staticmethod
    def _check_contained_participant(
        root_fd: int, participant: TransactionParticipant | ReplacementTransactionParticipant
    ) -> None:
        current = read_contained(root_fd, participant.relative_path, limit=16_384)
        allowed = (
            (participant.expected_content, participant.replacement_content)
            if isinstance(participant, ReplacementTransactionParticipant)
            else (None, participant.content)
        )
        if current not in allowed:
            raise TransactionConflictError

    def _publish_contained(self, root_fd: int, failure: Callable[[str], None] | None) -> None:
        for index, participant in enumerate(self._participants):
            self._require_contained_root(root_fd)
            if isinstance(participant, MoveTransactionParticipant):
                raise TransactionPathError
            self._check_contained_participant(root_fd, participant)
            replacement = isinstance(participant, ReplacementTransactionParticipant)
            content = participant.replacement_content if replacement else participant.content
            expected = participant.expected_content if replacement else None
            write_contained(root_fd, participant.relative_path, content, expected=expected)
            if failure and index == 0:
                failure("after-first-publication")

    @classmethod
    def recover_contained(cls, root: Path, root_fd: int) -> None:
        """Recover only report transactions whose participants share the explicit root."""
        try:
            with (
                contained_directory(root_fd, Path("transactions")) as directory_fd,
                os.scandir(directory_fd) as entries,
            ):
                _contained_temporary_usage(directory_fd, additional_bytes=0)
                names = []
                for entry in entries:
                    if _CONTAINED_TEMPORARY_PATTERN.fullmatch(entry.name):
                        continue
                    names.append(entry.name)
        except FileNotFoundError:
            return
        names = tuple(sorted(names))
        if len(names) > _MAX_CONTAINED_MANIFESTS:
            raise TransactionManifestError
        for name in names:
            if not name.endswith(".yaml"):
                raise TransactionManifestError
            content = read_contained(root_fd, Path("transactions") / name, limit=_MAX_CONTAINED_MANIFEST_BYTES)
            try:
                manifest = yaml.safe_load(content)
            except yaml.YAMLError as exc:
                raise TransactionManifestError from exc
            if not isinstance(manifest, dict) or manifest.get("schema_version") not in (1, 2):
                raise TransactionManifestError
            entries = manifest.get("participants")
            if not isinstance(entries, list) or not entries or len(entries) > _MAX_CONTAINED_PARTICIPANTS:
                raise TransactionManifestError
            participants = tuple(_participant_from_manifest(entry, (root,)) for entry in entries)
            transaction = cls(root, Path(name).stem, participants)
            if transaction._contained_manifest() != manifest:
                raise TransactionManifestError
            transaction._publish_contained(root_fd, None)
            with contained_directory(root_fd, Path("transactions")) as directory_fd:
                os.unlink(name, dir_fd=directory_fd)
                os.fsync(directory_fd)

    @classmethod
    def recover_all(cls, manifest_root: Path, *, roots: tuple[Path, ...] | None = None) -> None:
        """Complete every valid pending transaction rooted at ``manifest_root``."""
        resolved_root = manifest_root.resolve()
        allowed_roots = tuple(root.resolve() for root in (roots or (resolved_root,)))
        directory = resolved_root / "transactions"
        manifest_paths = tuple(sorted(directory.glob("*.yaml"))) if directory.is_dir() else ()
        for manifest_path in manifest_paths:
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


def _relative_parts(path: Path) -> tuple[str, ...]:
    if path.is_absolute() or not path.parts or any(part in (".", "..") for part in path.parts):
        raise TransactionPathError
    return path.parts


@contextlib.contextmanager
def contained_directory(root_fd: int, path: Path, *, create: bool = False) -> Iterator[int]:
    """Open each relative directory component without following links."""
    descriptor = os.dup(root_fd)
    try:
        for part in _relative_parts(path):
            if create:
                with contextlib.suppress(FileExistsError):
                    os.mkdir(part, mode=0o700, dir_fd=descriptor)
                    os.fsync(descriptor)
            successor = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = successor
        yield descriptor
    finally:
        os.close(descriptor)


@contextlib.contextmanager
def _contained_parent(root_fd: int, path: Path, *, create: bool = False) -> Iterator[int]:
    parts = _relative_parts(path)
    if len(parts) == 1:
        yield root_fd
    else:
        with contained_directory(root_fd, Path(*parts[:-1]), create=create) as descriptor:
            yield descriptor


def read_contained(root_fd: int, path: Path, *, limit: int) -> bytes | None:
    """Read a bounded regular file using only pinned directory descriptors."""
    try:
        with _contained_parent(root_fd, path) as parent_fd:
            descriptor = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent_fd)
    except FileNotFoundError:
        return None
    with os.fdopen(descriptor, "rb") as handle:
        metadata = os.fstat(handle.fileno())
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > limit:
            raise TransactionPathError
        content = handle.read(limit + 1)
        if len(content) > limit:
            raise TransactionPathError
        return content


def _contained_temporary_usage(directory_fd: int, *, additional_bytes: int) -> tuple[int, int]:
    if additional_bytes < 0 or additional_bytes > _MAX_CONTAINED_MANIFEST_BYTES:
        raise TransactionManifestError
    temporary_count = 0
    temporary_bytes = 0
    try:
        with os.scandir(directory_fd) as entries:
            for entry in entries:
                if _CONTAINED_TEMPORARY_PATTERN.fullmatch(entry.name) is None:
                    continue
                try:
                    metadata = entry.stat(follow_symlinks=False)
                except OSError as exc:
                    raise TransactionManifestError from exc
                if (
                    not stat.S_ISREG(metadata.st_mode)
                    or metadata.st_nlink != 1
                    or stat.S_IMODE(metadata.st_mode) != _CONTAINED_TEMPORARY_MODE
                    or metadata.st_size < 0
                    or metadata.st_size > _MAX_CONTAINED_MANIFEST_BYTES
                ):
                    raise TransactionManifestError
                temporary_count += 1
                temporary_bytes += metadata.st_size
    except OSError as exc:
        raise TransactionManifestError from exc
    if (
        temporary_count + (1 if additional_bytes else 0) > _MAX_CONTAINED_TEMPORARIES
        or temporary_bytes + additional_bytes > _MAX_CONTAINED_TEMPORARY_BYTES
    ):
        raise TransactionManifestError
    return temporary_count, temporary_bytes


def write_contained(root_fd: int, path: Path, content: bytes, *, expected: bytes | None = None) -> None:
    """Atomically publish exact bytes without following directory or file links."""
    with _contained_parent(root_fd, path, create=True) as parent_fd:
        current = read_contained(parent_fd, Path(path.name), limit=max(len(content), len(expected or b"")))
        if current == content:
            return
        if current != expected:
            raise TransactionConflictError
        _contained_temporary_usage(parent_fd, additional_bytes=len(content))
        temporary = f".tmp-{secrets.token_hex(12)}"
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent_fd)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            if expected is None:
                os.link(temporary, path.name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd, follow_symlinks=False)
            else:
                os.replace(temporary, path.name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
            os.fsync(parent_fd)
        finally:
            with contextlib.suppress(FileNotFoundError):
                os.unlink(temporary, dir_fd=parent_fd)


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
