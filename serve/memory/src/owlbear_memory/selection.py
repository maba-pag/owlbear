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
smaller one may still fit; nothing fills a quota.

Limits: the ranking knows nothing of the task, so a high-scoring lesson that does not apply can take a place a
relevant one needed; a long entry is skipped whole; a new lesson ranks by its saver's confidence alone, since
nobody has assessed it yet; recency follows the entry's last update, whatever changed.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

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


def stored(folder: Path) -> list[MemoryEntry]:
    """A memory folder's entries, read as recall reads them; none while the folder does not exist."""
    return MemoryEngine(folder).load() if folder.is_dir() else []


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
class Selection:
    """The entries kept, in order, and those skipped because they did not fit the space left."""

    chosen: tuple[Candidate, ...]
    omitted: tuple[Candidate, ...]


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
    """Up to *cap* ranked entries whose *cost*, the size of each as rendered, fits *room* in total."""
    chosen: list[Candidate] = []
    omitted: list[Candidate] = []
    for candidate in ranked(entries, agent):
        if len(chosen) >= cap:
            break
        size = cost(candidate)
        if size > room:
            omitted.append(candidate)
            continue
        chosen.append(candidate)
        room -= size
    return Selection(tuple(chosen), tuple(omitted))
