"""The decision-batch journal as read: its place, format and damage checks, its lock, and the batch in flight.

The shared data repository's checkout reads this before any ordinary push or rebase (`data_repo`), so an incomplete
batch commit never reaches another clone, and `state_store.decision_batch`, which writes and completes batches, builds
on it. Nothing here writes the journal.
"""

from __future__ import annotations

import base64
import binascii
import json
import os
import re
import time
import unicodedata
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING

from owlbear_delivery_next.local_system.storage_io import NotRegularError, open_lock, read_regular

if TYPE_CHECKING:
    from collections.abc import Iterator

    from owlbear_delivery_next.local_system.data_repo import DataRepo

JOURNAL = "owlbear-decision-batch.json"
GENERATION = re.compile(r"[0-9a-f]{8,64}")  # as `begin` makes it (a UUID's hex) and the owner's recovery names it
COMMIT = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")  # a full SHA-1 or SHA-256 commit id, as `rev-parse` names HEAD
COMPLETED = "owlbear-decision-batches-completed.json"
LOCK = "owlbear-decision-batch.lock"
LOCK_POLL = 0.05  # seconds between tries of a held batch lock, within a caller's deadline


class JournalError(ValueError):
    """The journal or its list of completed batches cannot be read, so whether a batch is in flight is unknown."""


class JournalBusyError(JournalError):
    """By the caller's deadline whether a batch is in flight is not known.

    Another writer still held the batch lock, or the deadline passed before the journal could be asked.
    """


@dataclass(frozen=True)
class Batch:
    """One batch in flight: its files by path relative to the checkout, with their bytes before and after."""

    generation: str
    project: str
    head: str
    message: str
    ids: tuple[str, ...]
    files: tuple[tuple[str, bytes | None, bytes], ...]


def admin(shared: DataRepo, until: float | None = None) -> Path:
    """The checkout's Git folder, where the journal lies and Git never tracks it; Git is asked within *until*.

    Once *until* has passed, Git is not asked: that is `JournalBusyError`, not known yet, never a damaged checkout.
    """
    found = shared.git("rev-parse", "--absolute-git-dir", until=until)
    folder = found.stdout.strip()
    if found.returncode and until is not None and time.monotonic() >= until:
        msg = f"this save's deadline passed before the git folder of {shared.root} was found, so try again"
        raise JournalBusyError(msg)
    if found.returncode or not Path(folder).is_absolute():  # an empty answer is no folder: never the working directory
        msg = f"the git folder of {shared.root} cannot be found: {found.stderr.strip()[:200] or 'Git named none'}"
        raise JournalError(msg)
    return Path(folder)


@contextmanager
def locked(shared: DataRepo, until: float | None = None) -> Iterator[None]:
    """Hold the batch lock while the journal and the completed list are read or changed together.

    Every transition and every stamp capture takes it, so a reader never pairs a journal and a list from different
    moments: the pair it reads is one that existed. A lock that cannot be taken (a link, not a regular file, no
    permission) is a `JournalError` naming it, so whether a batch is in flight stays unknown, never "none"; only taking
    the lock is translated, never an error of the body it guards. With *until* (monotonic), the caller's own deadline,
    a lock another writer still holds then is `JournalBusyError`; without one it is waited for, as before.
    """
    folder = admin(shared, until)
    try:
        dir_fd = os.open(folder, os.O_RDONLY | os.O_DIRECTORY)
    except OSError as exc:
        msg = f"the git folder {folder} cannot be opened for the batch lock: {exc}"
        raise JournalError(msg) from exc
    try:
        try:
            lock_fd = _take(dir_fd, until)
        except BlockingIOError:
            msg = f"another save still holds the batch lock, so try again ({folder / LOCK})"
            raise JournalBusyError(msg) from None
        except (OSError, ValueError) as exc:
            msg = f"the batch lock {folder / LOCK} cannot be taken ({exc}); make it a plain file the owner can open"
            raise JournalError(msg) from exc
        try:
            yield
        finally:
            os.close(lock_fd)
    finally:
        os.close(dir_fd)


def _take(dir_fd: int, until: float | None) -> int:
    """The batch lock, waited for without end, or tried only while *until* is ahead; `BlockingIOError` after it.

    The clock is read before every try, also the first and the one after a wait: a lock that comes free only once the
    deadline passed is never taken as within it.
    """
    if until is None:
        return open_lock(dir_fd, blocking=True, name=LOCK)
    while (left := until - time.monotonic()) > 0:
        try:
            return open_lock(dir_fd, blocking=False, name=LOCK)
        except BlockingIOError:
            if (left := until - time.monotonic()) <= 0:
                raise
            time.sleep(min(LOCK_POLL, left))
    raise BlockingIOError


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


_IGNORED = dict.fromkeys([*range(0x200C, 0x2010), *range(0x202A, 0x202F), *range(0x206A, 0x2070), 0xFEFF])


def _git_alias(part: str) -> bool:
    """Whether a file system may resolve *part* to `.git`, as Git itself refuses such names.

    Any case counts, and so do HFS's ignored code points and NTFS's trailing dots, spaces and short name.
    """
    name = part.translate(_IGNORED).casefold().rstrip(". ")
    return name in {".git", "git~1"}


def inside(value: str) -> str:
    """Recovery joins this path to the checkout root, so it must stay under it and outside the Git folder.

    Only the canonical spelling is accepted: `./`, `//` or a trailing `/` would name a file another row names too.
    """
    path = PurePosixPath(value)
    parts = path.parts
    if not parts or path.is_absolute() or "\0" in value or ".." in parts or any(map(_git_alias, parts)):
        msg = "a journal path is empty, absolute, escapes the checkout or names the Git folder"
        raise ValueError(msg)
    if str(path) != value:
        msg = "a journal path is not written in its one canonical form"
        raise ValueError(msg)
    return value


def _physical(rel: str) -> str:
    """The file *rel* may land on where names ignore case, Unicode normalization and HFS's ignored code points."""
    return unicodedata.normalize("NFD", rel.translate(_IGNORED)).casefold()


def paired(ids: tuple[str, ...], files: tuple[tuple[str, bytes | None, bytes], ...]) -> None:
    """Every producer journals one id per file, the file's own name, each file once; anything else is damage.

    A journal naming no file is damage too: no producer writes one, and it would complete without proving any image.
    Two rows that one file system could put in one file are one file twice, with images that contradict.
    """
    paths = [rel for rel, _, _ in files]
    if not paths:
        msg = "the journal names no file, so nothing of the batch can be proved"
        raise ValueError(msg)
    if [PurePosixPath(rel).stem for rel in paths] != list(ids) or len({_physical(p) for p in paths}) != len(paths):
        msg = "the journal's decision ids and files do not pair up"
        raise ValueError(msg)


def decode(raw: bytes) -> Batch:
    """The journal's batch, every field checked; damage of any kind is a `JournalError`."""
    try:
        record = json.loads(raw)
        files = tuple(
            (inside(f["path"]), _data(f["before"]), _after(f["after"]))
            for f in map(_record_of, _listed(record["files"]))
        )
        ids = tuple(str(i) for i in _listed(record["ids"]))
        paired(ids, files)
        return Batch(
            _generation(record["generation"]),
            str(record["project"]),
            _commit(record["head"]),
            str(record["message"]),
            ids,
            files,
        )
    except (KeyError, TypeError, ValueError, binascii.Error) as exc:
        msg = f"the interrupted-batch journal cannot be read: {exc}"
        raise JournalError(msg) from exc


def generations(raw: bytes | None) -> set[str]:
    """The completed batches' generations; a list that is not one is a `JournalError`, a missing one is empty."""
    if raw is None:
        return set()
    try:
        listed = json.loads(raw)
    except ValueError as exc:
        msg = f"the list of completed decision batches cannot be read: {exc}"
        raise JournalError(msg) from exc
    if not isinstance(listed, list) or not all(isinstance(g, str) and GENERATION.fullmatch(g) for g in listed):
        msg = "the list of completed decision batches is not a list of generations"
        raise JournalError(msg)
    return set(listed)


def _generation(value: object) -> str:
    """A batch's generation as `begin` makes it and the owner's recovery names it; anything else is damage."""
    if not isinstance(value, str) or not GENERATION.fullmatch(value):
        msg = "the journal's generation is not 8 to 64 lowercase hexadecimal characters"
        raise ValueError(msg)
    return value


def _commit(value: object) -> str:
    """The batch's head as `begin` journals it, a full commit id; a ref name, a short id or anything else is damage."""
    if not isinstance(value, str) or not COMMIT.fullmatch(value):
        msg = "the journal's head is not a full commit id of 40 or 64 lowercase hexadecimal characters"
        raise ValueError(msg)
    return value


def read(path: Path) -> bytes | None:
    """A journal file's bytes; None only when no entry has its name, and a `JournalError` when it cannot be read.

    The entry is opened without following a link and without blocking, and must be a regular file: a link, even a
    dangling one, a pipe or a folder at its name is damage, never a missing journal that would clear the barrier.
    """
    try:
        return read_regular(path)
    except NotRegularError as exc:
        msg = f"the interrupted-batch journal {path.name} is not a regular file"
        raise JournalError(msg) from exc
    except OSError as exc:
        msg = f"the interrupted-batch journal {path.name} cannot be read: {exc}"
        raise JournalError(msg) from exc


def pending(shared: DataRepo, until: float | None = None) -> Batch | None:
    """The batch in flight, if any; a journal whose generation completed is a stale copy and is ignored.

    The completed list is read and checked first: one that cannot be read means whether a batch is in flight is
    unknown, so it refuses even when no journal is there, before any writer changes a file. With *until*, Git and the
    lock are asked within the caller's own deadline (`locked`).
    """
    folder = admin(shared, until)
    with locked(shared, until):
        raw = read(folder / JOURNAL)
        listed = read(folder / COMPLETED)
    done = generations(listed)
    if raw is None:
        return None
    batch = decode(raw)
    return None if batch.generation in done else batch
