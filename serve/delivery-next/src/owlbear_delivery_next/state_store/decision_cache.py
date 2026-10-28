"""The decision snapshots this process read (owlbear-data#16): one validated snapshot and search index per view.

The files in ``owlbear-data`` stay the authority. `decision_store` collects its files through `files`, inside its
settled-read checks, so every journal, rebase and HEAD guard still runs on every read; only the parse is reused. A
view's entry is kept for the data commit and a fingerprint of everything the loader reads (`lstat` records and
folder listings of the root, the Global layer and every project's layers), so a commit, a rebase after a fetch or an
uncommitted edit rebuilds it on the next read. A read is not kept when the fingerprint cannot be taken, moved while
it was read (a folder's times catch a file added and removed again), or holds a file or folder time within
`RACY_NS` of the read's start (a coarse clock hides a same-size rewrite in the same tick); a read that raised, or
holds a file or folder that did not load, keeps nothing.
"""

from __future__ import annotations

import stat
import threading
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from owlbear_decisions.storage import DECISIONS_DIR
from owlbear_decisions.validate import CHANGES_DIR
from owlbear_delivery_next.state_store import decision_search

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from owlbear_decisions import Snapshot
    from owlbear_delivery_next.local_system.data_repo import DataRepo

    type Mark = tuple[tuple[object, ...], ...]

RACY_NS = 2_000_000_000
_now = time.time_ns


@dataclass(frozen=True)
class _Entry:
    commit: str
    mark: Mark
    snapshot: Snapshot
    index: decision_search.Index


_entries: dict[tuple[str, str], _Entry] = {}
_locks: dict[tuple[str, str], threading.Lock] = {}
_guard = threading.Lock()


def files(shared: DataRepo, project: str, commit: str, read: Callable[[DataRepo, str], Snapshot]) -> Snapshot:
    """*project*'s snapshot at *commit*: the kept one while its files are unchanged, else *read*'s, kept if settled."""
    cutoff = _now() - RACY_NS  # fixed before the first look, so a slow read cannot age a young file into the cache
    key = (str(shared.root), project)
    if (first := fingerprint(shared.root, project)) is None:
        return read(shared, project)
    mark, newest = first
    if (kept := _kept(key, commit, mark)) is not None:
        return kept.snapshot
    with _lock(key):
        if (kept := _kept(key, commit, mark)) is not None:
            return kept.snapshot
        seen = read(shared, project)
        again = fingerprint(shared.root, project)
        if again is not None and again[0] == mark and newest < cutoff and _whole(seen):
            _entries[key] = _Entry(commit, mark, seen, decision_search.Index(seen))
    return seen


def _whole(seen: Snapshot) -> bool:
    """Every file and folder loaded: a read error may pass while the files' records stay as they were."""
    return seen.complete and not seen.outside


def search(snapshot: Snapshot, text: str, *, include_retired: bool) -> frozenset[str]:
    """The ids of *snapshot* matching *text* (`decision_search`), from its kept index when it is the kept one."""
    kept = _entries.get((str(snapshot.root), snapshot.project))
    index = kept.index if kept is not None and kept.snapshot is snapshot else decision_search.Index(snapshot)
    return index.matching(text, include_retired=include_retired)


def clear() -> None:
    """Forget every kept snapshot; the next read of each view parses its files."""
    with _guard:
        _entries.clear()


def _kept(key: tuple[str, str], commit: str, mark: Mark) -> _Entry | None:
    kept = _entries.get(key)
    return kept if kept is not None and (kept.commit, kept.mark) == (commit, mark) else None


def _lock(key: tuple[str, str]) -> threading.Lock:
    with _guard:
        return _locks.setdefault(key, threading.Lock())


def fingerprint(root: Path, project: str) -> tuple[Mark, int] | None:
    """What `snapshot(root, project)` reads, and its newest file time; None when any of it cannot be looked at.

    It follows `snapshot.read_repo`: the root's names (a dot-named folder by name only: it is never read, and Git's
    own folder changes on every call), the Global layer, *project*'s folder whatever its name, and every other
    folder's layers (`validate.change_folders`, `storage.load_folder`). Folders give their kind, owner, times and
    listing, files their full `lstat` record; every entry of a decisions folder counts.
    """
    walk = _Walk()
    try:
        names = sorted(child.name for child in root.iterdir())
        walk.folder(root)
        walk.records.append(("", *names))
        walk.layer(root)
        for name in names:
            if name == project or not (name.startswith(".") or name == DECISIONS_DIR):
                walk.project(root / name)
    except OSError:
        return None
    return tuple(walk.records), walk.newest


class _Walk:
    def __init__(self) -> None:
        self.records: list[tuple[object, ...]] = []
        self.newest = 0

    def project(self, folder: Path) -> None:
        if not self.folder(folder):
            return
        self.layer(folder)
        if not self.folder(changes := folder / CHANGES_DIR):
            return
        for name in self.listing(changes):
            if self.folder(held := changes / name):
                self.layer(held)

    def layer(self, folder: Path) -> None:
        if self.folder(directory := folder / DECISIONS_DIR):
            for name in self.listing(directory):
                self.file(directory / name)

    def folder(self, path: Path) -> bool:
        """Record *path*'s kind, owner and times; True when it is a real folder."""
        try:
            found = path.lstat()
        except FileNotFoundError, NotADirectoryError:
            self.records.append((str(path),))
            return False
        times = (found.st_mtime_ns, found.st_ctime_ns)
        self.records.append((str(path), found.st_mode, found.st_dev, found.st_ino, found.st_uid, found.st_gid, *times))
        self.newest = max(self.newest, *times)
        return stat.S_ISDIR(found.st_mode)

    def listing(self, folder: Path) -> list[str]:
        names = sorted(child.name for child in folder.iterdir())
        self.records.append((str(folder), *names))
        return names

    def file(self, path: Path) -> None:
        found = path.lstat()
        times = (found.st_mtime_ns, found.st_ctime_ns)
        self.records.append(
            (str(path), found.st_mode, found.st_dev, found.st_ino, found.st_size, *times, found.st_uid, found.st_gid)
        )
        self.newest = max(self.newest, *times)
