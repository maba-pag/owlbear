"""The project's Delivery database (TD-265): ``delivery.db`` in the store, beside the run locks and artifacts.

Change records, inbox items, activity, the now line and the issued handles live here; locks, runner records,
logs, screenshots and worktrees stay files. WAL, ``synchronous=FULL``, a 10 s busy timeout, one connection per
thread. Every operation holds ``migrate.lock`` shared for itself alone, so an import waits for running ones
while an idle client never blocks it.

A store of the file format is imported by the machine host alone, fenced and resumable: the format marker
becomes ``STORE_FORMAT`` first, so every older runtime refuses the store on open; the files are read into
``delivery.db.tmp`` with an ``imported`` ledger of every file taken, which is published by one rename; only
then are those files renamed ``*.imported``. Until the database exists, every operation here is refused.
"""

from __future__ import annotations

import contextlib
import json
import os
import sqlite3
import subprocess
import threading
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.change_contracts.models import ErrorKind, Stop
from owlbear_delivery_next.local_system.storage_io import atomic_write, open_lock

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from datetime import datetime
    from pathlib import Path

STORE_FORMAT = 6  # above every file-format marker, so an older runtime refuses the store (TD-265)
DB, TMP, MARKER, MIGRATE, RETIRED = "delivery.db", "delivery.db.tmp", "format", "migrate.lock", ".imported"
BUSY_MS = 10_000
NOT_IMPORTED = "this clone's Delivery state moves to its database when OwlBear loads it; run `owlbear start`"
SCHEMA = """
CREATE TABLE changes(slug TEXT PRIMARY KEY, rev INTEGER NOT NULL, record TEXT NOT NULL, prev TEXT);
CREATE TABLE inbox(id INTEGER PRIMARY KEY, slug TEXT NOT NULL, name TEXT NOT NULL, item TEXT NOT NULL,
  UNIQUE(slug, name));
CREATE TABLE activity(id INTEGER PRIMARY KEY, slug TEXT NOT NULL, at TEXT, event TEXT NOT NULL);
CREATE INDEX activity_slug ON activity(slug, id);
CREATE TABLE now(slug TEXT PRIMARY KEY, data TEXT NOT NULL);
CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE imported(slug TEXT NOT NULL, name TEXT NOT NULL, PRIMARY KEY(slug, name));
"""
_local_devices: set[int] = set()


class StoreError(Exception):
    """State that cannot be used; the loop shows it as a ``state`` stop."""

    action = "Restore the previous state"
    resume = "State loads"

    def stop(self, now: datetime) -> Stop:
        """Return the stop record for this error."""
        return Stop(kind=ErrorKind.STATE, reason=str(self), action=self.action, resume=self.resume, at=now)


class FormatTooNewError(StoreError):
    """The state was written by a newer OwlBear."""

    action = "Upgrade OwlBear"
    resume = "State loads on the newer OwlBear"


class NotImportedError(StoreError):
    """The store still holds the file format; the machine host imports it."""

    action = "Start OwlBear (owlbear start), which moves the state into its database"
    resume = "OwlBear loads the project"


def _fsync(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _local(root: Path) -> None:
    """Refuse a store on a network file system, where SQLite's locks do not hold (``df -l``)."""
    device = root.stat().st_dev
    if device in _local_devices:
        return
    said = subprocess.run(["df", "-l", str(root)], capture_output=True, text=True, check=False, timeout=30)  # noqa: S603, S607
    if said.returncode or len(said.stdout.splitlines()) < 2:  # noqa: PLR2004 - the header and the file system
        msg = f"{root} is not on a local disk, so Delivery cannot keep its database there"
        raise StoreError(msg)
    _local_devices.add(device)


class Database:
    """One store's database: its connections, the operation fence and the import of the file format."""

    def __init__(self, root: Path) -> None:
        self.root, self.path = root, root / DB
        self._threads = threading.local()
        self._ready = False

    def marker(self) -> int:
        """The store's format marker; 0 when there is none."""
        try:
            path = self.root / MARKER
            return int(path.read_text()) if path.exists() else 0
        except (OSError, ValueError) as exc:
            msg = "store format marker is unreadable"
            raise StoreError(msg) from exc

    def legacy_slugs(self) -> list[str]:
        """The Changes the file format holds."""
        return sorted(p.parent.name for p in (self.root / "changes").glob("*/change.json"))

    def waiting(self) -> bool:
        """Whether file-format state waits for its import."""
        return not self.path.exists() and (bool(self.legacy_slugs()) or (self.root / "handles.json").exists())

    def check(self) -> None:
        """Make the database usable or say why not; a store without file-format state starts empty."""
        if self._ready:
            return
        if (found := self.marker()) > STORE_FORMAT:
            msg = f"store format {found} is newer than {STORE_FORMAT}"
            raise FormatTooNewError(msg)
        if not self.path.exists():
            if self.waiting():
                raise NotImportedError(NOT_IMPORTED)
            self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
            with self.fenced():
                if not self.path.exists():
                    self._build(None)
        _local(self.root)
        with self._shared():
            wal = self._connection().execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        if not wal:  # a crash came between publishing the database and setting WAL: set it with no operation running
            with self.fenced():
                self._wal()
        with self._shared():
            connection = self._connection()
            if not connection.execute("SELECT 1 FROM meta WHERE key = 'retired'").fetchone():
                self._retire(connection)
        self._ready = True

    @contextlib.contextmanager
    def fenced(self) -> Iterator[None]:
        """Hold ``migrate.lock`` exclusively, once every running operation has ended."""
        fd = self._lock(shared=False)
        try:
            yield
        finally:
            os.close(fd)

    @contextlib.contextmanager
    def _shared(self) -> Iterator[None]:
        fd = self._lock(shared=True)
        try:
            yield
        finally:
            os.close(fd)

    def _lock(self, *, shared: bool) -> int:
        dir_fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            return open_lock(dir_fd, blocking=True, shared=shared, name=MIGRATE)
        finally:
            os.close(dir_fd)

    def _connection(self) -> sqlite3.Connection:
        connection = getattr(self._threads, "connection", None)
        if connection is None:
            connection = sqlite3.connect(self.path, timeout=BUSY_MS / 1000, isolation_level=None)
            connection.execute(f"PRAGMA busy_timeout={BUSY_MS}")
            connection.execute("PRAGMA synchronous=FULL")
            self._threads.connection = connection
        return connection

    @contextlib.contextmanager
    def read(self) -> Iterator[sqlite3.Connection]:
        """One reading operation."""
        self.check()
        with self._shared():
            try:
                yield self._connection()
            except sqlite3.Error as exc:
                msg = f"the Delivery database failed: {exc}"
                raise StoreError(msg) from exc

    @contextlib.contextmanager
    def write(self) -> Iterator[sqlite3.Connection]:
        """One writing operation in one transaction, committed when the block ends without an error."""
        self.check()
        with self._shared():
            connection = self._connection()
            try:
                connection.execute("BEGIN IMMEDIATE")
                try:
                    yield connection
                except BaseException:
                    connection.execute("ROLLBACK")
                    raise
                connection.execute("COMMIT")
            except sqlite3.Error as exc:
                msg = f"the Delivery database failed: {exc}"
                raise StoreError(msg) from exc

    def import_files(self) -> None:
        """Move the file format into the database; the caller holds the host lock and every Change lock.

        Resumable: a crash before the database is published leaves the files authoritative and this runs
        again; after it, the retirement of the files the ledger names repeats on the next open.
        """
        with self.fenced():
            if not self.path.exists():
                self._build(self._fill)
        self.check()

    def _build(self, fill: Callable[[sqlite3.Connection], None] | None) -> None:
        atomic_write(self.root / MARKER, f"{STORE_FORMAT}\n")  # every older runtime refuses the store from now on
        tmp = self.root / TMP
        tmp.unlink(missing_ok=True)
        connection = sqlite3.connect(tmp, isolation_level=None)
        try:
            connection.execute("PRAGMA journal_mode=DELETE")
            connection.execute("PRAGMA synchronous=FULL")
            connection.execute("BEGIN")
            for statement in SCHEMA.split(";"):
                if statement.strip():
                    connection.execute(statement)
            if fill is not None:
                fill(connection)
            else:
                connection.execute("INSERT INTO meta VALUES ('retired', '1')")  # nothing to retire
            connection.execute("COMMIT")
        finally:
            connection.close()
        tmp.chmod(0o600)
        _fsync(tmp)
        tmp.replace(self.path)
        _fsync(self.root)
        self._wal()  # the caller holds the fence, so no operation has the database open in a transaction

    def _wal(self) -> None:
        connection = sqlite3.connect(self.path, timeout=BUSY_MS / 1000, isolation_level=None)
        try:
            connection.execute("PRAGMA journal_mode=WAL")
        finally:
            connection.close()

    def _fill(self, connection: sqlite3.Connection) -> None:
        """Read every file-format record into the database, each file named in the ledger."""
        taken: list[tuple[str, str]] = []
        for folder in sorted(p for p in (self.root / "changes").glob("*") if p.is_dir()):
            taken += _fill_change(connection, folder)
        if (handles := self.root / "handles.json").exists():
            with contextlib.suppress(AttributeError, ValueError):
                if isinstance(issued := json.loads(handles.read_text()).get("issued"), int):
                    connection.execute("INSERT INTO meta VALUES ('issued', ?)", (str(issued),))
            taken.append(("", handles.name))
        connection.executemany("INSERT INTO imported VALUES (?, ?)", taken)

    def file(self, slug: str, name: str) -> Path:
        """The file a ledger entry names."""
        return self.root / name if not slug else self.root / "changes" / slug / name

    def _retire(self, connection: sqlite3.Connection) -> None:
        for slug, name in connection.execute("SELECT slug, name FROM imported").fetchall():
            path = self.file(slug, name)
            with contextlib.suppress(FileNotFoundError):
                path.rename(path.with_name(path.name + RETIRED))
        connection.execute("INSERT OR IGNORE INTO meta VALUES ('retired', '1')")

    def ingest(self, slug: str, folder: Path) -> None:
        """Take the inbox files an older process dropped after the import, once each, then retire them."""
        files = sorted(folder.glob("*.json"))
        if not files:
            return
        with self.write() as connection:
            for path in files:
                name = f"inbox/{path.name}"
                if connection.execute("SELECT 1 FROM imported WHERE slug = ? AND name = ?", (slug, name)).fetchone():
                    continue  # taken before a crash kept it from being retired
                text = path.read_bytes().decode(errors="replace")
                connection.execute("INSERT INTO inbox(slug, name, item) VALUES (?, ?, ?)", (slug, path.name, text))
                connection.execute("INSERT INTO imported VALUES (?, ?)", (slug, name))
        for path in files:
            with contextlib.suppress(FileNotFoundError):
                path.rename(path.with_name(path.name + RETIRED))


def _text(path: Path) -> str:
    return path.read_bytes().decode(errors="replace")  # a damaged file stays damaged: reading it reports that


def _fill_change(connection: sqlite3.Connection, folder: Path) -> list[tuple[str, str]]:
    """One Change's record, inbox, activity and now line; the ledger names of the files taken."""
    slug, acked, taken = folder.name, set[str](), []
    if (record := folder / "change.json").exists():
        text, prev = _text(record), folder / "change.json.prev"
        with contextlib.suppress(AttributeError, TypeError, ValueError):
            acked = set(json.loads(text).get("inbox_acked") or [])
        old = _text(prev) if prev.exists() else None
        connection.execute("INSERT INTO changes VALUES (?, 1, ?, ?)", (slug, text, old))
        taken += [(slug, "change.json")] + ([(slug, "change.json.prev")] if old is not None else [])
    for item in sorted((folder / "inbox").glob("*.json")):
        if item.name not in acked:  # an acknowledged item was folded before a crash left its file
            connection.execute("INSERT INTO inbox(slug, name, item) VALUES (?, ?, ?)", (slug, item.name, _text(item)))
        taken.append((slug, f"inbox/{item.name}"))
    if (log := folder / "activity.jsonl").exists():
        for line in _text(log).splitlines():
            if line.strip():
                append_activity(connection, slug, line)
        taken.append((slug, log.name))
    if (now := folder / "now.json").exists():
        connection.execute("INSERT INTO now VALUES (?, ?)", (slug, _text(now)))
        taken.append((slug, now.name))
    return taken


def put_record(connection: sqlite3.Connection, slug: str, text: str) -> None:
    """Write one Change record in the open transaction, keeping the one before as ``prev``; unchanged writes nothing."""
    row = connection.execute("SELECT record FROM changes WHERE slug = ?", (slug,)).fetchone()
    if row is None:
        connection.execute("INSERT INTO changes VALUES (?, 1, ?, NULL)", (slug, text))
    elif row[0] != text:
        connection.execute("UPDATE changes SET prev = record, record = ?, rev = rev + 1 WHERE slug = ?", (text, slug))


def append_activity(connection: sqlite3.Connection, slug: str, line: str, keep: int | None = None) -> None:
    """Append one activity event (a JSON line) in the open transaction; with *keep*, drop all but the last ones."""
    at: Any = None
    with contextlib.suppress(AttributeError, ValueError):
        at = json.loads(line).get("at")
    connection.execute("INSERT INTO activity(slug, at, event) VALUES (?, ?, ?)", (slug, str(at) if at else None, line))
    if keep is not None:
        connection.execute(
            "DELETE FROM activity WHERE slug = ? AND id NOT IN "
            "(SELECT id FROM activity WHERE slug = ? ORDER BY id DESC LIMIT ?)",
            (slug, slug, keep),
        )
