"""Admit an update under the machine's lock, using its record and OwlBear's open pull requests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.git.command_failure import failure
from owlbear_delivery_next.impeccable import pack_git
from owlbear_delivery_next.state_store import pack_run_record

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from owlbear_delivery_next.github.provider import Provider, PullRequest

PREFIX = "pack/"  # every pack update's branch: pack/<run>
OPEN = frozenset({"running", "waiting"})


@dataclass(frozen=True)
class Kind:
    """One kind of update: its run record's reader, its branches' prefix and its name in a refusal."""

    reader: Callable[[Path], tuple[dict[str, Any], str] | None]
    prefix: str
    title: str

    @property
    def an(self) -> str:
        """The title with its article: "an Impeccable", "a PDS"."""
        return f"{'an' if self.title[0] in 'AEIOU' else 'a'} {self.title}"


IMPECCABLE = Kind(lambda root: pack_run_record.observed(root), PREFIX, "Impeccable")  # noqa: PLW0108 - read late


class Refused(Exception):  # noqa: N818 - the claim's answer, not a fault
    """The claim may not be taken now; the text says why."""


def fresh(root: Path, github: Provider, kind: Kind = IMPECCABLE) -> None:
    """Start only if this kind has no open update or pull request."""
    record, _ = _seen(root, kind)
    if (state := record.get("state")) in OPEN:
        doing = "waits for answers" if state == "waiting" else "runs"
        msg = f"{kind.an} update {doing}; one is open at a time on this machine"
        raise Refused(msg)
    if found := pulls(github, kind):
        msg = f"{kind.an} pull request is open: {found[0].url}; merge or close it before a new update"
        raise Refused(msg)


def resumed(  # noqa: PLR0913 - the run's project, its identity and its branch, GitHub and the kind
    root: Path, *, run: str, version: str, branch: str, github: Provider, kind: Kind = IMPECCABLE
) -> None:
    """A waiting run goes on: it is still itself and any open pull request of its kind is its own.

    *version* is the run file as this host last read or wrote it; *branch* is its publication's, empty before one.

    Raises:
        Refused: Its record changed, something cannot be read, or another pull request is open.
    """
    record, observed_version = _seen(root, kind)
    if (record.get("run"), record.get("state"), observed_version) != (run, "waiting", version):
        msg = "this update's record changed since the page loaded it; reload the page"
        raise Refused(msg)
    found = pulls(github, kind)
    if other := [p for p in found if p.head_branch != branch]:
        msg = f"another {kind.title} pull request is open: {other[0].url}; merge or close it first"
        raise Refused(msg)
    if len(found) > 1:
        msg = f"{len(found)} open pull requests come from {branch}; close all but this update's own"
        raise Refused(msg)


def _seen(root: Path, kind: Kind) -> tuple[dict[str, Any], str]:
    try:
        got = kind.reader(root)
    except (OSError, ValueError) as exc:
        why = failure(exc)
        msg = f"the machine's {kind.title} run record cannot be read ({why}); unreadable is never idle, repair it first"
        raise Refused(msg) from None
    return ({}, "absent") if got is None else got


def pulls(github: Provider, kind: Kind = IMPECCABLE) -> tuple[PullRequest, ...]:
    """OwlBear's open pull requests of *kind*, read whole.

    Raises:
        Refused: They could not be read whole: a failed or cut-short lookup is no evidence that none is open.
    """
    try:
        found = github.open_pull_requests(pack_git.REPOSITORY, kind.prefix)
    except Exception as exc:  # noqa: BLE001 - whatever stopped the lookup, it proves nothing
        msg = f"OwlBear's open {kind.title} pull requests could not be read ({failure(exc)}); try again"
        raise Refused(msg) from None
    return tuple(p for p in found if p.head_branch.startswith(kind.prefix))
