"""A search index over the decisions (TD-424): one SQLite file in OwlBear's folder, rebuilt from the files.

The files stay the truth. Every search loads the project's snapshot first (a store that cannot be read, or a
project view with an unusable file, raises instead of searching a partial set) and rebuilds that project's rows when
the data commit or the revisions of its decision files differ from what they were built from, so an uncommitted file
counts too. Creating, rebuilding or replacing the file happens under an exclusive lock on a sibling lock file, with
the file rechecked once the lock is held. Only a file SQLite reports corrupt, or of another format, is deleted and
rebuilt; a busy or locked database is retried briefly, then reported as `IndexBusy`. FTS5 ranks the words when the
bundled SQLite has it; else every word must appear in the title or statement.
"""

from __future__ import annotations

import contextlib
import fcntl
import hashlib
import os
import re
import sqlite3
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from owlbear_decisions import State
from owlbear_delivery_next.local_system import data_repo, local_home
from owlbear_delivery_next.state_store import decision_store
from owlbear_delivery_next.state_store.database import BUSY_MS, StoreError

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from owlbear_delivery_next.state_store.decision_store import DataView

FILE, FORMAT = "decisions.sqlite", 1
HIDDEN = (State.REPLACED, State.WITHDRAWN, State.SPENT)
TRIES, PAUSE = 4, 0.05
_BUSY, _CORRUPT = {5, 6}, {11, 26}  # SQLITE_BUSY, SQLITE_LOCKED; SQLITE_CORRUPT, SQLITE_NOTADB
_WORD = re.compile(r"\w+")


def _fts5() -> bool:
    connection = sqlite3.connect(":memory:")
    try:
        connection.execute("CREATE VIRTUAL TABLE probe USING fts5(text)")
    except sqlite3.OperationalError:
        return False
    finally:
        connection.close()
    return True


FTS = _fts5()


@dataclass(frozen=True)
class Hit:
    """One decision found."""

    id: str
    title: str
    statement: str
    scope: str
    project: str
    state: str
    origin: str


class IndexBusy(StoreError):  # noqa: N818 - says what it is
    """Another process kept the index busy; the same search shortly after succeeds."""

    action = "Search again in a moment"
    resume = "The decision index is free"


class _Unusable(Exception):  # noqa: N818 - private
    """The index file is corrupt or of another format."""


def path() -> Path:
    """The index file: rebuilt from the decision files whenever it is missing, stale or unreadable."""
    return local_home.root() / FILE


def search(
    text: str, project: str, *, include_retired: bool = False, limit: int = 20, view: DataView | None = None
) -> list[Hit]:
    """Decisions of *project* and Global whose title or statement holds every word of *text*; all for no words.

    Replaced, withdrawn and spent decisions are hidden unless *include_retired*. Raises `DecisionsUnavailable` when
    the decisions cannot be read in full: an unreadable store never searches as an empty or partial one. Raises
    `IndexBusy` when the index stays busy. A *view* the caller loaded already is searched as it is.
    """
    if view is None:
        try:
            shared = data_repo.locate()
        except data_repo.DataRepoError as exc:
            raise decision_store.DecisionsUnavailable(str(exc), decision_store.SET_UP) from exc
        view = decision_store.load(shared, project)
    words, file = _WORD.findall(text), path()
    file.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(TRIES):
        seen = _identity(file)
        try:
            return _search(file, view, words, include_retired=include_retired, limit=limit)
        except _Unusable:
            _rebuild(file, seen)
        except sqlite3.OperationalError as exc:
            if _code(exc) not in _BUSY:
                raise
            time.sleep(PAUSE * (attempt + 1))
    msg = f"the decision index {file} stayed busy or could not be rebuilt"
    raise IndexBusy(msg)


def _code(exc: sqlite3.Error) -> int:
    return (getattr(exc, "sqlite_errorcode", None) or 0) & 0xFF  # the primary result code


def _search(file: Path, view: DataView, words: list[str], *, include_retired: bool, limit: int) -> list[Hit]:
    try:
        connection = _open(file)
        try:
            context = f"{view.snapshot.root}\n{view.snapshot.project}"
            _fresh(connection, context, view)
            return _query(connection, context, words, include_retired=include_retired, limit=limit)
        finally:
            connection.close()
    except sqlite3.DatabaseError as exc:
        if _code(exc) in _CORRUPT:
            raise _Unusable(str(exc)) from exc
        raise


def _identity(file: Path) -> tuple[int, int, int] | None:
    try:
        found = file.stat()
    except FileNotFoundError:
        return None
    return found.st_dev, found.st_ino, found.st_ctime_ns


@contextlib.contextmanager
def _locked(file: Path) -> Iterator[None]:
    """Hold the exclusive lock on the sibling lock file that serializes creating and replacing *file*."""
    descriptor = os.open(file.with_name(f"{file.name}.lock"), os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        end = time.monotonic() + BUSY_MS / 1000
        while True:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() > end:
                    msg = f"another process kept the decision index {file} locked"
                    raise IndexBusy(msg) from None
                time.sleep(PAUSE)
        yield
    finally:
        os.close(descriptor)


def _rebuild(file: Path, seen: tuple[int, int, int] | None) -> None:
    """Delete the unusable *file*, unless another process replaced it since it was found unusable."""
    with _locked(file):
        if _identity(file) == seen:
            _discard(file)


def _connect(file: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(file, timeout=BUSY_MS / 1000, isolation_level=None)
    connection.execute(f"PRAGMA busy_timeout={BUSY_MS}")
    return connection


def _open(file: Path) -> sqlite3.Connection:
    connection = _connect(file)
    try:
        if (found := _format(connection)) == 0:
            _initialise(file)
            found = _format(connection)
    except BaseException:
        connection.close()
        raise
    if found != FORMAT:
        connection.close()
        msg = f"index format {found}, not {FORMAT}"
        raise _Unusable(msg)
    return connection


def _initialise(file: Path) -> None:
    """Create the tables under the lock, unless another process did once it was held."""
    with _locked(file):
        connection = _connect(file)
        try:
            if _format(connection) == 0:
                _create(connection)
        finally:
            connection.close()


def _format(connection: sqlite3.Connection) -> int:
    """The file's format: 0 for a new, empty file; -1 for tables without a format."""
    found = connection.execute("PRAGMA user_version").fetchone()[0]
    if found == 0 and connection.execute("SELECT 1 FROM sqlite_master").fetchone():
        return -1
    return found


def _create(connection: sqlite3.Connection) -> None:
    rows = "CREATE VIRTUAL TABLE entries USING fts5(context UNINDEXED, id UNINDEXED, title, statement, "
    rows += "scope UNINDEXED, project UNINDEXED, state UNINDEXED, origin UNINDEXED)"
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("BEGIN IMMEDIATE")
    connection.execute("CREATE TABLE built(context TEXT PRIMARY KEY, data_commit TEXT NOT NULL, digest TEXT NOT NULL)")
    connection.execute(
        rows if FTS else "CREATE TABLE entries(context, id, title, statement, scope, project, state, origin)"
    )
    connection.execute(f"PRAGMA user_version={FORMAT}")
    connection.execute("COMMIT")


def _discard(file: Path) -> None:
    for suffix in ("", "-wal", "-shm"):
        with contextlib.suppress(FileNotFoundError):
            file.with_name(file.name + suffix).unlink()


def _digest(view: DataView) -> str:
    root = view.snapshot.root
    lines = sorted(f"{e.path.relative_to(root).as_posix()} {e.decision.revision}" for e in view.snapshot.entries)
    return hashlib.sha256("\n".join(lines).encode()).hexdigest()


def _fresh(connection: sqlite3.Connection, context: str, view: DataView) -> None:
    source = (view.commit, _digest(view))
    connection.execute("BEGIN IMMEDIATE")
    try:
        built = connection.execute("SELECT data_commit, digest FROM built WHERE context = ?", (context,)).fetchone()
        if built != source:
            connection.execute("DELETE FROM entries WHERE context = ?", (context,))
            connection.executemany(
                "INSERT INTO entries(context, id, title, statement, scope, project, state, origin) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (context, d.id, d.title, d.statement, str(d.scope), d.project, str(d.state), str(d.origin))
                    for d in (e.decision for e in view.snapshot.entries)
                ],
            )
            connection.execute("INSERT OR REPLACE INTO built VALUES (?, ?, ?)", (context, *source))
    except BaseException:
        connection.execute("ROLLBACK")
        raise
    connection.execute("COMMIT")


def _query(
    connection: sqlite3.Connection, context: str, words: list[str], *, include_retired: bool, limit: int
) -> list[Hit]:
    where, params = ["context = ?"], [context]
    if not include_retired:
        where.append(f"state NOT IN ({', '.join('?' * len(HIDDEN))})")
        params += [str(s) for s in HIDDEN]
    order = "id"
    if words and FTS:
        where.append("entries MATCH ?")
        params.append(" ".join(f'"{w}"*' for w in words))
        order = "rank, id"
    elif words:
        for word in words:
            where.append("(title LIKE ? ESCAPE '\\' OR statement LIKE ? ESCAPE '\\')")
            pattern = "%" + re.sub(r"([\\%_])", r"\\\1", word) + "%"
            params += [pattern, pattern]
    columns = "id, title, statement, scope, project, state, origin"
    sql = f"SELECT {columns} FROM entries WHERE {' AND '.join(where)}"  # noqa: S608 - fixed clauses, values bound
    rows = connection.execute(f"{sql} ORDER BY {order} LIMIT ?", (*params, limit)).fetchall()
    return [Hit(*row) for row in rows]
