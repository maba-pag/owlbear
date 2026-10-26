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
import unicodedata
import uuid
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING

from owlbear_decisions.storage import bound, install, own_temporary
from owlbear_delivery_next.local_system.storage_io import fsync_dir, open_lock

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Iterator, Sequence

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


def replace_file(path: Path, data: bytes | None, fence: Callable[[], None] | None = None) -> None:
    """Make *path* hold *data* atomically, or no file at all when *data* is None; the rename or unlink is fsynced.

    *fence*, when given, runs last before the rename or unlink, after the new bytes are durable in their temporary
    file: a slow fsync cannot outlast the caller's proof that the file is still its to change. The folder is held open
    before *fence* runs; the rename or unlink and its fsync are made in that folder, and only while *path*'s folder
    still leads to it (`bound`), so a folder moved aside or linked away during *fence* changes nothing. The temporary
    file is made, checked and renamed held open throughout (`own_temporary`, `install`); it is removed only while its
    name still holds it, and *path* is then left as it is. A folder that does not exist holds no file to remove, and
    none is made to find out.
    """
    if data is None:
        try:
            folder = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        except FileNotFoundError:
            return
        try:
            if fence is not None:
                fence()
            bound(folder, path.parent)
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
            install(temporary, path.name, path.parent)
    finally:
        os.close(folder)


def _held(path: Path) -> bytes | None:
    try:
        return path.read_bytes()
    except FileNotFoundError:
        return None


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
        return all(
            _absent(root, path, anchors[path])
            if text is None
            else _held(path) == text and plain_in_checkout(root, path)
            for path, text in before.items()
        ) and still_plain(root, before)
    except OSError:
        return False


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


def _inside(value: str) -> str:
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


def _paired(ids: tuple[str, ...], files: tuple[tuple[str, bytes | None, bytes], ...]) -> None:
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
    """Record a batch in flight before any of its files is written; return its new generation.

    The batch is checked as a reader decodes it, so a journal that could not be read back is never written.
    """
    generation = uuid.uuid4().hex
    batch = Batch(generation, project, head, message, tuple(ids), tuple(files))
    try:
        _paired(batch.ids, tuple((_inside(rel), before, after) for rel, before, after in batch.files))
    except ValueError as exc:
        msg = f"the decision batch cannot be journalled: {exc}"
        raise JournalError(msg) from exc
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
