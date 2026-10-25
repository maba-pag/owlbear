"""Which memories an agent is given: recall's eligibility and the pre-flight selection (TD-70, TD-241).

Eligibility is recall's: approved, curated and contested entries whose ``scope_agents`` name the agent or ``*``.
The curator's threshold plays no part. The pre-flight selection, version ``VERSION``, ranks the eligible entries
of a project's memory folder and of Global memory, deduplicated by ID with the project's copy kept, by:

1. scope specificity: entries scoped to the agent itself before those only for every agent (``*``); within each,
   the project's before Global memory's;
2. score, higher first: the saver's confidence plus the assessments so far;
3. recency, the latest ``updated_at`` first;
4. the entry ID, so equal entries always come in the same order.

It keeps at most ``CAP`` whole entries. One that does not fit the space left is skipped, never cut, and a later,
smaller one may still fit; nothing fills a quota. Every eligible entry left out is named with its reason, the cap
or the budget. A read that skipped unreadable entry files is incomplete, and says so; only a folder that does not
exist reads as complete and empty.

Limits: the ranking knows nothing of the task, so a high-scoring lesson that does not apply can take a place a
relevant one needed; a long entry is skipped whole; a new lesson ranks by its saver's confidence alone, since
nobody has assessed it yet; recency follows the entry's last update, whatever changed.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from stat import S_ISDIR
from typing import TYPE_CHECKING, Literal

from owlbear_memory.engine import MemoryEngine
from owlbear_memory.models import MemoryEntry, MemoryState, Where

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable
    from pathlib import Path

VERSION = "preflight-1"
CAP = 5  # entries at most
BUDGET = 2000  # characters of the rendered lessons, wrappers included
RECALLED = frozenset({MemoryState.APPROVED, MemoryState.CURATED, MemoryState.CONTESTED})
EVERY = "*"  # the scope of a memory for every agent


def eligible(entry: MemoryEntry, agent: str | None) -> bool:
    """Whether recall gives *entry* to *agent*; an unrecognised caller, None, gets only entries for ``*``."""
    if entry.state not in RECALLED:
        return False
    return EVERY in entry.scope_agents or (bool(agent) and agent != EVERY and agent in entry.scope_agents)


@dataclass(frozen=True)
class Read:
    """A memory folder's readable entries and how many of its entry files could not be read."""

    entries: list[MemoryEntry]
    unreadable: int = 0

    @property
    def complete(self) -> bool:
        """Every entry file was read: an empty complete read means the folder holds none."""
        return not self.unreadable


def stored(folder: Path) -> Read:
    """A memory folder's entries, read as recall reads them; none, completely, while the folder does not exist.

    Raises:
        OSError: The folder exists but is no folder or cannot be listed, so its entries are unknown.
    """
    try:
        found = folder.stat()
    except FileNotFoundError:
        return Read([])
    if not S_ISDIR(found.st_mode):
        raise NotADirectoryError(str(folder))
    with os.scandir(folder):  # a folder the reader cannot list would otherwise read as empty
        pass
    engine = MemoryEngine(folder)
    entries = engine.load()
    return Read(entries, engine.parse_errors)


def readable(project: Iterable[MemoryEntry], shared: Iterable[MemoryEntry]) -> list[tuple[MemoryEntry, Where]]:
    """The project's entries, then Global memory's ones the project does not hold (TD-241)."""
    own: list[tuple[MemoryEntry, Where]] = [(entry, "project") for entry in project]
    ids = {entry.id for entry, _ in own}
    return own + [(entry, "global") for entry in shared if entry.id not in ids]


@dataclass(frozen=True)
class Candidate:
    """One eligible entry, where it is stored and whether its scope names the agent itself."""

    entry: MemoryEntry
    where: Where
    specific: bool


@dataclass(frozen=True)
class Skipped:
    """An eligible entry left out, and why: the cap was reached, or it did not fit the space left."""

    candidate: Candidate
    reason: Literal["cap", "budget"]


@dataclass(frozen=True)
class Selection:
    """The entries kept, in order, and every other eligible one with the reason it was left out."""

    chosen: tuple[Candidate, ...]
    omitted: tuple[Skipped, ...]


def _updated(entry: MemoryEntry) -> float:
    return datetime.fromisoformat(entry.updated_at).timestamp()


def ranked(entries: Iterable[tuple[MemoryEntry, Where]], agent: str) -> list[Candidate]:
    """The entries *agent* may recall, most specific first, then by score, recency and ID."""
    found = [
        Candidate(entry, where, specific=agent in entry.scope_agents)
        for entry, where in entries
        if eligible(entry, agent)
    ]
    return sorted(
        found,
        key=lambda c: (not c.specific, c.where != "project", -c.entry.score, -_updated(c.entry), c.entry.id),
    )


def select(
    entries: Iterable[tuple[MemoryEntry, Where]],
    agent: str,
    *,
    cost: Callable[[Candidate], int],
    room: int,
    cap: int = CAP,
) -> Selection:
    """Up to *cap* ranked entries whose *cost*, the size of each as rendered, fits *room* in total; the rest skipped."""
    chosen: list[Candidate] = []
    omitted: list[Skipped] = []
    for candidate in ranked(entries, agent):
        if len(chosen) >= cap:
            omitted.append(Skipped(candidate, "cap"))
            continue
        size = cost(candidate)
        if size > room:
            omitted.append(Skipped(candidate, "budget"))
            continue
        chosen.append(candidate)
        room -= size
    return Selection(tuple(chosen), tuple(omitted))
