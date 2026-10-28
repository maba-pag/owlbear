"""Search over one decision snapshot (owlbear-data#16): an in-memory SQLite table, built once, never on disk.

FTS5 matches every word of the text as a prefix in the title or statement when the bundled SQLite has it; else every
word must appear in the title or statement. Replaced, withdrawn and spent decisions are left out unless asked for.
The answer is the set of matching ids, uncapped: the caller filters its own entries by it.
"""

from __future__ import annotations

import re
import sqlite3
import threading
import weakref
from typing import TYPE_CHECKING

from owlbear_decisions import State

if TYPE_CHECKING:
    from owlbear_decisions import Snapshot

HIDDEN = (State.REPLACED, State.WITHDRAWN, State.SPENT)
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


class Index:
    """The decisions of one snapshot, complete once built; any thread may ask, one at a time."""

    def __init__(self, snapshot: Snapshot) -> None:
        self.fts = FTS
        self._lock = threading.Lock()
        self._connection = sqlite3.connect(":memory:", check_same_thread=False, isolation_level=None)
        weakref.finalize(self, self._connection.close)
        table = "CREATE VIRTUAL TABLE entries USING fts5(id UNINDEXED, title, statement, state UNINDEXED)"
        self._connection.execute(table if self.fts else "CREATE TABLE entries(id, title, statement, state)")
        self._connection.executemany(
            "INSERT INTO entries(id, title, statement, state) VALUES (?, ?, ?, ?)",
            [(d.id, d.title, d.statement, str(d.state)) for d in (e.decision for e in snapshot.entries)],
        )

    def matching(self, text: str, *, include_retired: bool) -> frozenset[str]:
        """The ids whose title or statement holds every word of *text*; every id for no words."""
        words = _WORD.findall(text)
        with self._lock:
            if not words:
                rows = self._rows(_ALL, ())
            elif self.fts:
                rows = self._rows(_MATCH, (" ".join(f'"{w}"*' for w in words),))
            else:  # every word in the title or statement of the same row
                found = [self._rows(_LIKE, (_pattern(w), _pattern(w))) for w in words]
                rows = set.intersection(*found)
        hidden = {str(s) for s in HIDDEN}
        return frozenset(i for _, i, state in rows if include_retired or state not in hidden)

    def _rows(self, sql: str, params: tuple[str, ...]) -> set[tuple[int, str, str]]:
        return set(self._connection.execute(sql, params))


_ALL = "SELECT rowid, id, state FROM entries"
_MATCH = "SELECT rowid, id, state FROM entries WHERE entries MATCH ?"
_LIKE = "SELECT rowid, id, state FROM entries WHERE title LIKE ? ESCAPE '\\' OR statement LIKE ? ESCAPE '\\'"


def _pattern(word: str) -> str:
    return "%" + re.sub(r"([\\%_])", r"\\\1", word) + "%"
