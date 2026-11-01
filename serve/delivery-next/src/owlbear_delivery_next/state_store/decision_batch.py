"""The journal of a decision batch in flight: written before its first file, cleared once published or put back.

A save of several decision files writes them, commits them as one commit and reads them back. Before the first file,
the journal records the project, Git's head, the decision ids and each file's bytes before and after the batch, under
a fresh generation. A pending journal is a batch in flight: while its writer holds the repository-wide lock, a read of
the decisions says a save is in progress (`decision_errors.settled`). One that stays once no writer holds the lock is
an interrupted batch: `decision_store` then refuses every read and write of the decisions until the owner finishes or
abandons it by that generation (`decision_recovery`).
Completing a batch records its generation in a list that is never pruned, so a copy of an old journal cannot be
replayed (ABA).
"""

from __future__ import annotations

import base64
import functools
import json
import os
import time
import uuid
from contextlib import suppress
from contextvars import ContextVar
from typing import TYPE_CHECKING

from owlbear_decisions.storage import bound, install, own_temporary
from owlbear_delivery_next.local_system import storage_io
from owlbear_delivery_next.local_system.batch_journal import (  # noqa: F401 - the store's journal API, read below it
    COMPLETED,
    GENERATION,
    JOURNAL,
    LOCK,
    Batch,
    JournalError,
    pending,
)
from owlbear_delivery_next.local_system.batch_journal import admin as _admin
from owlbear_delivery_next.local_system.batch_journal import decode as _decode
from owlbear_delivery_next.local_system.batch_journal import generations as _generations
from owlbear_delivery_next.local_system.batch_journal import inside as _inside
from owlbear_delivery_next.local_system.batch_journal import locked as _locked
from owlbear_delivery_next.local_system.batch_journal import paired as _paired
from owlbear_delivery_next.local_system.batch_journal import read as _read
from owlbear_delivery_next.local_system.storage_io import fsync_dir

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Sequence
    from pathlib import Path

    from owlbear_delivery_next.local_system.data_repo import DataRepo


# A chat's deadline for its save to start (`CLOCK_MONOTONIC`, the machine's, so the chat server and the host compare
# it): a save that would begin its batch later is refused before its journal, so a chat whose answer was lost and that
# finds nothing once the deadline passed knows nothing was written (#846). Set by the route for its one request.
ADMIT_BY: ContextVar[float | None] = ContextVar("admit_by", default=None)
_now = functools.partial(time.clock_gettime, time.CLOCK_MONOTONIC)


class Late(Exception):  # noqa: N818 - says what the save was
    """The save's batch would begin after its chat's deadline: nothing is journalled or written."""


def journal_path(shared: DataRepo) -> Path:
    """The journal's place in the Git admin folder, where Git never tracks it."""
    return _admin(shared) / JOURNAL


def replace_file(
    path: Path, data: bytes | None, fence: Callable[[], None] | None = None, root: Path | None = None
) -> None:
    """Make *path* hold *data* atomically, or no file at all when *data* is None; the rename or unlink is fsynced.

    *fence*, when given, runs last before the rename or unlink, after the new bytes are durable in their temporary
    file: a slow fsync cannot outlast the caller's proof that the file is still its to change. The folder is held open
    before *fence* runs; the rename or unlink and its fsync are made in that folder, and only while *path*'s folder
    still leads to it and, with *root* (the checkout), every folder up to *root* is still a plain folder (`bound`), so
    a folder moved aside or linked away during *fence*, at any level, changes nothing. The temporary file is made,
    checked and renamed held open throughout (`own_temporary`, `install`); it is removed only while its name still
    holds it, and *path* is then left as it is. A folder that does not exist holds no file to remove, and none is made
    to find out.
    """
    if data is None:
        try:
            folder = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        except FileNotFoundError:
            return
        try:
            if fence is not None:
                fence()
            bound(folder, path.parent, root)
            with suppress(FileNotFoundError):
                os.unlink(path.name, dir_fd=folder)
            os.fsync(folder)
        finally:
            os.close(folder)
        return
    folder = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        with own_temporary(folder, data) as temporary:
            if fence is not None:
                fence()
            install(temporary, path.name, path.parent, root)
    finally:
        os.close(folder)


def _held(path: Path) -> bytes | None:
    """*path*'s bytes as a proof reads them (`storage_io.read_regular`): a pipe or a link there raises `OSError`."""
    return storage_io.read_regular(path)


def plain_in_checkout(root: Path, path: Path) -> bool:
    """Whether *path* is a plain file or absent, under plain folders all the way up to the checkout *root*.

    Every folder between them is checked, so a linked folder holding a `.git` of its own cannot end the walk early.
    """
    if path.is_symlink() or (path.exists() and not path.is_file()):
        return False
    for folder in path.parents:
        if folder == root:
            return True
        if folder.is_symlink() or not folder.is_dir():
            return False
    return False


def owned(root: Path, images: dict[Path, tuple[bytes | None, bytes | None]]) -> bool:
    """Whether every file is plain and holds its before or after image; an owner's other content is never overwritten.

    A symlink or a path outside *root* is refused before anything is read, so a matching referent is never followed,
    and every path is checked again after all reads (`still_plain`), so a folder swapped for a link meanwhile refuses.
    A file that is absent may lie under folders that do not exist yet, as a new project's first decision does.
    """
    try:
        if not still_plain(root, images):
            return False
        held = all(_held(path) in (before, after) for path, (before, after) in images.items())
        return held and still_plain(root, images)
    except OSError:
        return False


def still_plain(root: Path, paths: Iterable[Path]) -> bool:
    """Whether every path still lies under plain folders of *root*, checked after the reads it guards.

    A proof reads bytes through a path's folders; checked only before, a folder swapped for a link during the read
    would lend it a foreign file's bytes. A path under folders that never existed counts up to its first missing name
    (`_anchor`); any error other than a missing name raises.
    """
    return all(plain_in_checkout(root, _anchor(root, path)) for path in paths)


def restored(root: Path, before: dict[Path, bytes | None]) -> bool:
    """Whether every file is plain under *root* and holds exactly its before image (absent for none), once durable.

    Two phases, so no fsync can hide a change to a row already read. First every folder the proof rests on is fsynced:
    each file's own folder, or for a file that had no before image, the nearest existing folder above its first missing
    name (`_anchor`). Then the whole batch is read again with no fsync: every anchor must be the one fsynced, each file
    exactly its before image or absent, and each folder chain plain up to *root*, checked after the read it guards.
    """
    try:
        anchors = {path: _anchor(root, path) for path, text in before.items() if text is None}
        folders = {first.parent for first in anchors.values()}
        folders |= {path.parent for path, text in before.items() if text is not None and path.parent.exists()}
        for folder in folders:
            fsync_dir(folder)
        return _exactly(root, before, anchors)
    except OSError:
        return False


def holds_before(root: Path, before: dict[Path, bytes | None]) -> bool:
    """Whether every file still holds exactly its before image, read again with no fsync (`restored` made it durable).

    A completion re-reads this after its blocking Git and index probes and before its final HEAD read, so a file put
    back and then changed again during a probe keeps the batch.
    """
    try:
        return _exactly(root, before, {path: _anchor(root, path) for path, text in before.items() if text is None})
    except OSError:
        return False


def _exactly(root: Path, before: dict[Path, bytes | None], anchors: dict[Path, Path]) -> bool:
    return all(
        _absent(root, path, anchors[path]) if text is None else _held(path) == text and plain_in_checkout(root, path)
        for path, text in before.items()
    ) and still_plain(root, before)


def _anchor(root: Path, path: Path) -> Path:
    """*path*'s first missing name from the top, or *path* itself when its folder exists; its folder exists.

    Only a missing name walks further up: any other error (no permission, a file where a folder belongs) raises.
    """
    first = path
    while first.parent != root and not _exists(first.parent):
        first = first.parent
    return first


def _absent(root: Path, path: Path, first: Path) -> bool:
    """Whether *path* is still absent from the same first missing name, below plain folders read after that name.

    The folder chain is checked after the last read of the name, so a folder swapped for a link during it refuses.
    Nothing is created to prove it.
    """
    return _anchor(root, path) == first and not _exists(first) and plain_in_checkout(root, first)


def _exists(path: Path) -> bool:
    """Whether *path* names anything, a symlink included; only a missing name is False, other errors raise."""
    try:
        os.lstat(path)
    except FileNotFoundError:
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


def begin(  # noqa: PLR0913, PLR0917 - a batch is its project, head, message, decisions and files together
    shared: DataRepo,
    project: str,
    head: str,
    message: str,
    ids: Sequence[str],
    files: Sequence[tuple[str, bytes | None, bytes]],
    admit_by: float | None = None,
) -> str:
    """Record a batch in flight before any of its files is written; return its new generation.

    The batch is checked as a reader decodes it, so a journal that could not be read back is never written. Past
    *admit_by* it raises `Late` instead: the check and the journal share one hold of the lock every reader's `stamp`
    takes, so a read after the deadline sees this batch's journal or its outcome, or no batch ever begins.
    """
    generation = uuid.uuid4().hex
    batch = Batch(generation, project, head, message, tuple(ids), tuple(files))
    try:
        _paired(batch.ids, tuple((_inside(rel), before, after) for rel, before, after in batch.files))
    except ValueError as exc:
        msg = f"the decision batch cannot be journalled: {exc}"
        raise JournalError(msg) from exc
    with _locked(shared):
        if admit_by is not None and _now() > admit_by:
            raise Late
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
    done = _generations(listed)  # checked even with no journal: an unreadable list leaves the read unknown
    if journal is not None and _decode(journal).generation not in done:
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
