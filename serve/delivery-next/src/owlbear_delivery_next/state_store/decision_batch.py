"""The journal of a decision batch in flight: written before its first file, cleared once published or put back.

A save of several decision files writes them, commits them as one commit and reads them back. Before the first file,
the journal records the project, Git's head, the decision ids and each file's bytes before and after the batch, under
a fresh generation. A journal that stays after a crash is an interrupted batch: `decision_store` then refuses every
read and write of the decisions until the owner finishes or abandons it by that generation (`decision_recovery`).
Completing a batch records its generation in a list that is never pruned, so a copy of an old journal cannot be
replayed (ABA).
"""

from __future__ import annotations

import base64
import binascii
import json
import os
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from tempfile import mkstemp
from typing import TYPE_CHECKING

from owlbear_delivery_next.local_system.storage_io import fsync_dir, open_lock

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

    from owlbear_delivery_next.local_system.data_repo import DataRepo

JOURNAL = "owlbear-decision-batch.json"
COMPLETED = "owlbear-decision-batches-completed.json"
LOCK = "owlbear-decision-batch.lock"


class JournalError(ValueError):
    """The journal or its list of completed batches cannot be read, so whether a batch is in flight is unknown."""


@dataclass(frozen=True)
class Batch:
    """One batch in flight: its files by path relative to the checkout, with their bytes before and after."""

    generation: str
    project: str
    head: str
    message: str
    ids: tuple[str, ...]
    files: tuple[tuple[str, bytes | None, bytes], ...]


def _admin(shared: DataRepo) -> Path:
    found = shared.git("rev-parse", "--absolute-git-dir")
    admin = found.stdout.strip()
    if found.returncode or not Path(admin).is_absolute():  # an empty answer is no folder: never the working directory
        msg = f"the git folder of {shared.root} cannot be found: {found.stderr.strip()[:200] or 'Git named none'}"
        raise JournalError(msg)
    return Path(admin)


@contextmanager
def _locked(shared: DataRepo) -> Iterator[None]:
    """Hold the batch lock while the journal and the completed list are read or changed together.

    Every transition and every stamp capture takes it, so a reader never pairs a journal and a list from different
    moments: the pair it reads is one that existed.
    """
    dir_fd = os.open(_admin(shared), os.O_RDONLY | os.O_DIRECTORY)
    try:
        lock_fd = open_lock(dir_fd, blocking=True, name=LOCK)
        try:
            yield
        finally:
            os.close(lock_fd)
    finally:
        os.close(dir_fd)


def journal_path(shared: DataRepo) -> Path:
    """The journal's place in the Git admin folder, where Git never tracks it."""
    return _admin(shared) / JOURNAL


def replace_file(path: Path, data: bytes | None) -> None:
    """Make *path* hold *data* atomically, or no file at all when *data* is None; the rename or unlink is fsynced."""
    if data is None:
        if not path.parent.exists():  # no folder means no file to remove, and nothing to make durable
            return
        path.unlink(missing_ok=True)
        fsync_dir(path.parent)
        return
    descriptor, temporary = mkstemp(dir=path.parent, prefix=".", suffix=".tmp")
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        Path(temporary).replace(path)
        fsync_dir(path.parent)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def _held(path: Path) -> bytes | None:
    try:
        return path.read_bytes()
    except FileNotFoundError:
        return None


def _plain_in_checkout(path: Path) -> bool:
    """Whether *path* is a plain file or absent, under plain folders up to the checkout holding its `.git`."""
    if path.is_symlink() or (path.exists() and not path.is_file()):
        return False
    for folder in path.parents:
        if folder.is_symlink() or not folder.is_dir():
            return False
        if (folder / ".git").exists():
            return True
    return False


def owned(images: dict[Path, tuple[bytes | None, bytes | None]]) -> bool:
    """Whether every file is plain and holds its before or after image; an owner's other content is never overwritten.

    A symlink or a path outside a checkout is refused before anything is read, so a matching referent is never followed.
    """
    if not all(_plain_in_checkout(path) for path in images):
        return False
    return all(_held(path) in (before, after) for path, (before, after) in images.items())


def restored(before: dict[Path, bytes | None]) -> bool:
    """Whether every file holds its before image and the folders holding them are fsynced after the restore."""
    try:
        if any(_held(path) != text for path, text in before.items()):
            return False
        for folder in {path.parent for path in before if path.parent.exists()}:
            fsync_dir(folder)
    except OSError:
        return False
    return True


def _encode(batch: Batch) -> bytes:
    def text(data: bytes | None) -> str | None:
        return None if data is None else base64.b64encode(data).decode("ascii")

    files = [{"path": rel, "before": text(before), "after": text(after)} for rel, before, after in batch.files]
    record = {
        "generation": batch.generation,
        "project": batch.project,
        "head": batch.head,
        "message": batch.message,
        "ids": list(batch.ids),
        "files": files,
    }
    return json.dumps(record, indent=1).encode("utf-8")


def _data(value: str | None) -> bytes | None:
    return None if value is None else base64.b64decode(value, validate=True)


def _after(value: str | None) -> bytes:
    if value is None:  # a null after image would make the batch delete a decision file
        msg = "a decision file's after image is null"
        raise ValueError(msg)
    return base64.b64decode(value, validate=True)


def _listed(value: object) -> list:
    if not isinstance(value, list):  # a string or object here would decode as an empty batch
        msg = "a journal list is not a list"
        raise TypeError(msg)
    return value


def _record_of(value: object) -> dict:
    if not isinstance(value, dict) or not isinstance(value.get("path"), str):
        msg = "a journal file record has no string path"
        raise TypeError(msg)
    return value


def _inside(value: str) -> str:
    """Recovery joins this path to the checkout root, so it must stay under it and outside the Git folder."""
    parts = PurePosixPath(value).parts
    if not parts or PurePosixPath(value).is_absolute() or ".." in parts or any(p.lower() == ".git" for p in parts):
        msg = "a journal path is empty, absolute, escapes the checkout or names the Git folder"
        raise ValueError(msg)
    return value


def _paired(ids: tuple[str, ...], files: tuple[object, ...]) -> None:
    if len(ids) != len(files):  # each producer journals one id per file; a partial list would hide a replacement
        msg = "the journal's decision ids and files do not pair up"
        raise ValueError(msg)


def _decode(raw: bytes) -> Batch:
    try:
        record = json.loads(raw)
        files = tuple(
            (_inside(f["path"]), _data(f["before"]), _after(f["after"]))
            for f in map(_record_of, _listed(record["files"]))
        )
        ids = tuple(str(i) for i in _listed(record["ids"]))
        _paired(ids, files)
        return Batch(
            str(record["generation"]),
            str(record["project"]),
            str(record["head"]),
            str(record["message"]),
            ids,
            files,
        )
    except (KeyError, TypeError, ValueError, binascii.Error) as exc:
        msg = f"the interrupted-batch journal cannot be read: {exc}"
        raise JournalError(msg) from exc


def _generations(raw: bytes | None) -> set[str]:
    if raw is None:
        return set()
    try:
        listed = json.loads(raw)
    except ValueError as exc:
        msg = f"the list of completed decision batches cannot be read: {exc}"
        raise JournalError(msg) from exc
    if not isinstance(listed, list) or not all(isinstance(g, str) for g in listed):
        msg = "the list of completed decision batches is not a list of generations"
        raise JournalError(msg)
    return set(listed)


def _read(path: Path) -> bytes | None:
    try:
        return path.read_bytes()
    except FileNotFoundError:
        return None
    except OSError as exc:
        msg = f"the interrupted-batch journal cannot be read: {exc}"
        raise JournalError(msg) from exc


def pending(shared: DataRepo) -> Batch | None:
    """The batch in flight, if any; a journal whose generation completed is a stale copy and is ignored."""
    admin = _admin(shared)
    with _locked(shared):
        raw = _read(admin / JOURNAL)
        listed = _read(admin / COMPLETED)
    if raw is None:
        return None
    batch = _decode(raw)
    return None if batch.generation in _generations(listed) else batch


def begin(  # noqa: PLR0913, PLR0917 - a batch is its project, head, message, decisions and files together
    shared: DataRepo,
    project: str,
    head: str,
    message: str,
    ids: Sequence[str],
    files: Sequence[tuple[str, bytes | None, bytes]],
) -> str:
    """Record a batch in flight before any of its files is written; return its new generation."""
    generation = uuid.uuid4().hex
    batch = Batch(generation, project, head, message, tuple(ids), tuple(files))
    with _locked(shared):
        replace_file(_admin(shared) / JOURNAL, _encode(batch))
    return generation


def stamp(shared: DataRepo) -> tuple[bytes | None, bytes | None]:
    """The journal and the completed list as they are now; a batch in flight is refused, so a read never starts in one.

    Both bytes are read before the batch check: a batch that begins after the journal was read is seen at the next
    stamp, and one that completed meanwhile changes the list, which is never pruned, so its ABA cannot match.
    """
    admin = _admin(shared)
    with _locked(shared):
        journal = _read(admin / JOURNAL)
        listed = _read(admin / COMPLETED)
    if journal is not None and _decode(journal).generation not in _generations(listed):
        msg = f"the interrupted decision batch {_decode(journal).generation} is in flight"
        raise JournalError(msg)
    return journal, listed


def complete(shared: DataRepo, generation: str) -> None:
    """Record *generation* as completed for good, then clear the journal if it is still this batch's.

    A journal that cannot be read is refused before the completed list changes.
    """
    admin = _admin(shared)
    with _locked(shared):
        raw = _read(admin / JOURNAL)
        journal = None if raw is None else _decode(raw)
        listed = _generations(_read(admin / COMPLETED)) | {generation}
        replace_file(admin / COMPLETED, json.dumps(sorted(listed), indent=1).encode("utf-8"))
        if journal is not None and journal.generation == generation:
            replace_file(admin / JOURNAL, None)
