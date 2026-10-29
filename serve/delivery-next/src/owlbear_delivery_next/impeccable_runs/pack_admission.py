"""Who may take the machine's one Impeccable claim (TD-242), checked while the machine lock is held.

A new update starts only when no project on this machine runs or waits for one and no pack pull request is open in
OwlBear's repository. A waiting run goes on only as itself: its own record as this host last read or wrote it, no other
run open on the machine, and no pack pull request open but on its own branch. Every project's run record is read
without writing, never through a Job, which could rewrite it. A record or a pull request list that cannot be read
refuses: unreadable is never idle. Only the open pull request reaches beyond this machine.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.impeccable import pack_git
from owlbear_delivery_next.state_store import pack_run_record, project_home, registry

if TYPE_CHECKING:
    from owlbear_delivery_next.github.provider import Provider, PullRequest

PREFIX = "pack/"  # every pack update's branch: pack/<run>
OPEN = frozenset({"running", "waiting"})


class Refused(Exception):  # noqa: N818 - the claim's answer, not a fault
    """The claim may not be taken now; the text says why, naming the project or pull request in the way."""


@dataclass(frozen=True)
class Seen:
    """One project's run record as read now: its name, its record (None when it has none) and the file's version."""

    name: str
    record: dict[str, Any] | None
    version: str

    @property
    def state(self) -> str:
        """The record's state; "idle" without a record."""
        return str((self.record or {}).get("state") or "idle")


def fresh(own: Path, name: str, github: Provider) -> None:
    """A new update: no project on this machine runs or waits for one, and no Impeccable pull request is open.

    Raises:
        Refused: A run is open, a record or the registry cannot be read, or a pack pull request is open or unread.
    """
    open_ = [s for s in records(own, name) if s.state in OPEN]
    waiting = [s.name for s in open_ if s.state == "waiting"]
    if len(waiting) > 1:
        msg = f"Impeccable updates wait in {', '.join(waiting)}; answer or discard them first"
        raise Refused(msg)
    if open_:
        doing = "waits for answers" if waiting else "runs"
        msg = f"an Impeccable update {doing} in {open_[0].name}; one is open at a time on this machine"
        raise Refused(msg)
    if found := pulls(github):
        msg = f"an Impeccable pull request is open: {found[0].url}; merge or close it before a new update"
        raise Refused(msg)


def resumed(  # noqa: PLR0913 - the run's project, its identity and its branch, and GitHub
    own: Path, name: str, *, run: str, version: str, branch: str, github: Provider
) -> None:
    """A waiting run goes on: it is still itself, alone on this machine, and any open pack pull request is its own.

    *version* is the run file as this host last read or wrote it; *branch* is its publication's, empty before one.

    Raises:
        Refused: Its record changed, another run is open, something cannot be read, or another pack PR is open.
    """
    mine, *others = records(own, name)
    record = mine.record or {}
    if (record.get("run"), record.get("state"), mine.version) != (run, "waiting", version):
        msg = "this update's record changed since the page loaded it; reload the page"
        raise Refused(msg)
    if competing := [s.name for s in others if s.state in OPEN]:
        msg = f"an Impeccable update is also open in {', '.join(competing)}; discard one so only one goes on"
        raise Refused(msg)
    found = pulls(github)
    if other := [p for p in found if p.head_branch != branch]:
        msg = f"another Impeccable pull request is open: {other[0].url}; merge or close it first"
        raise Refused(msg)
    if len(found) > 1:
        msg = f"{len(found)} open pull requests come from {branch}; close all but this update's own"
        raise Refused(msg)


def records(own: Path, name: str) -> list[Seen]:
    """This project's run record first, then each other registered project's, each read once and never written.

    Raises:
        Refused: The machine's registry or a project's record cannot be read.
    """
    try:
        projects = registry.load().projects
    except registry.RegistryError as exc:
        msg = f"the machine's registry cannot be read, so other projects' updates cannot be ruled out: {exc}"
        raise Refused(msg) from None
    roots = {os.path.realpath(own): (name, own)}
    for p in projects:
        root = project_home.home(p.id)
        roots.setdefault(os.path.realpath(root), (Path(p.path).name, root))
    return [_seen(n, root) for n, root in roots.values()]


def _seen(name: str, root: Path) -> Seen:
    try:
        got = pack_run_record.observed(root)
    except (OSError, ValueError) as exc:
        msg = f"the Impeccable run record of {name} cannot be read ({exc}); unreadable is never idle, repair it first"
        raise Refused(msg) from None
    return Seen(name, None, "absent") if got is None else Seen(name, *got)


def pulls(github: Provider) -> tuple[PullRequest, ...]:
    """OwlBear's open Impeccable pull requests, read whole.

    Raises:
        Refused: They could not be read whole: a failed or cut-short lookup is no evidence that none is open.
    """
    try:
        found = github.open_pull_requests(pack_git.REPOSITORY, PREFIX)
    except Exception as exc:  # noqa: BLE001 - whatever stopped the lookup, it proves nothing
        msg = f"OwlBear's open Impeccable pull requests could not be read ({type(exc).__name__}: {exc}); try again"
        raise Refused(msg) from None
    return tuple(p for p in found if p.head_branch.startswith(PREFIX))
