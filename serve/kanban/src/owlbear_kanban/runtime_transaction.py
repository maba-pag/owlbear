"""Durable publication of a bounded set of contained runtime records."""

from __future__ import annotations

import contextlib
import fcntl
import hashlib
import os
import secrets
from dataclasses import dataclass
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from pathlib import Path


class TransactionConflictError(RuntimeError):
    """A transaction destination already contains different immutable bytes."""

    code = "ERR_TRANSACTION_CONFLICT"


class TransactionPathError(ValueError):
    """A transaction participant escapes its explicit root."""

    code = "ERR_TRANSACTION_PATH_UNSAFE"


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


class RuntimeTransaction:
    """Publish immutable participants with a recoverable commit manifest."""

    def __init__(
        self,
        manifest_root: Path,
        transaction_id: str,
        participants: tuple[TransactionParticipant, ...],
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
        with _transaction_lock(self._manifest_root):
            self._prepare_manifest()
            if failure:
                failure("before-publication")
            self._publish(failure)
            self._cleanup()

    def recover(self) -> None:
        """Deterministically complete a previously staged transaction."""
        with _transaction_lock(self._manifest_root):
            if self._manifest_path.exists():
                self._publish(None)
                self._cleanup()

    def _prepare_manifest(self) -> None:
        self._directory.mkdir(parents=True, exist_ok=True)
        manifest = self._manifest()
        if self._manifest_path.exists():
            if _load_yaml(self._manifest_path) != manifest:
                raise TransactionConflictError
            return
        for participant in self._participants:
            destination = participant.destination()
            if destination.exists() and destination.read_bytes() != participant.content:
                raise TransactionConflictError
        _atomic_write_yaml(self._manifest_path, manifest)

    def _manifest(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "participants": [
                {
                    "root": str(participant.root.resolve()),
                    "path": str(participant.relative_path),
                    "sha256": hashlib.sha256(participant.content).hexdigest(),
                    "content": participant.content.hex(),
                }
                for participant in self._participants
            ],
        }

    def _publish(self, failure: Callable[[str], None] | None) -> None:
        for index, participant in enumerate(self._participants):
            destination = participant.destination()
            destination.parent.mkdir(parents=True, exist_ok=True)
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


@contextlib.contextmanager
def _transaction_lock(root: Path) -> Iterator[None]:
    root.mkdir(parents=True, exist_ok=True)
    lock_path = root / ".runtime-transactions.lock"
    with lock_path.open("a+") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


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
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else {}


def _fsync_directory(directory: Path) -> None:
    descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


__all__ = ["RuntimeTransaction", "TransactionConflictError", "TransactionParticipant", "TransactionPathError"]
