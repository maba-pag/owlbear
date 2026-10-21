"""What one project sees of a data repository: the Global layer, its own layers and every finding over them."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from owlbear_decisions.models import Scope, State
from owlbear_decisions.storage import is_folder
from owlbear_decisions.validate import Entry, Finding, Layer, check, holds_decisions, layers, read_layers

if TYPE_CHECKING:
    from pathlib import Path

CONFLICT = "two-successors"
UNREADABLE = "unreadable"


@dataclass(frozen=True)
class Read:
    """Every layer of a data repository as one project reads it; *outside*: other projects' unreadable folders."""

    layers: list[Layer]
    entries: list[Entry]
    failed: list[tuple[Layer, Finding]]
    outside: list[tuple[Layer, Finding]]


def read_repo(root: Path, project: str) -> Read:
    """The Global layer and every project's layers, as *project* reads them.

    A folder of another project that cannot be read is an `unreadable` finding of its layer in `outside`; the root,
    the Global layer and *project*'s own folder raise `OSError`.
    """
    own = root / project if project else None
    every = [Layer(root, Scope.GLOBAL)]
    entries, failed = read_layers(every)
    outside: list[tuple[Layer, Finding]] = []
    for child in sorted(root.iterdir()):
        try:
            if not (is_folder(child) if child == own else holds_decisions(child)):
                continue
            found = layers(None, [child])
            got, lost = read_layers(found)
        except OSError as exc:
            if child == own:
                raise
            finding = Finding(str(child), UNREADABLE, f"cannot be read: {exc}")
            outside.append((Layer(child, Scope.PROJECT, child.name), finding))
            continue
        every += found
        entries += got
        failed += lost
    return Read(every, entries, failed, outside)


@dataclass(frozen=True)
class Snapshot:
    """The decisions of the Global layer and one project's layers, and every finding involving one of them.

    A finding's `involves` names its decisions; a file that did not load involves none and is kept, in `unreadable`
    too, when it lies in one of these layers. A snapshot with such a file is not `complete`: the rules that file
    holds are unknown. Another project's folder that cannot be read is kept in `outside`, never in this view.
    """

    root: Path
    project: str
    layers: tuple[Layer, ...]
    entries: tuple[Entry, ...]
    findings: tuple[Finding, ...]
    unreadable: tuple[Finding, ...] = ()
    outside: tuple[tuple[Layer, Finding], ...] = ()

    @property
    def complete(self) -> bool:
        """Every file in these layers loaded as a decision."""
        return not self.unreadable

    def get(self, decision_id: str) -> Entry | None:
        """The entry holding *decision_id*; the first by path when a duplicate id is reported."""
        return next((e for e in self.entries if e.decision.id == decision_id), None)

    def findings_for(self, decision_id: str) -> list[Finding]:
        """Every finding involving *decision_id*."""
        return [f for f in self.findings if decision_id in f.involves]

    def active(self, decision_id: str) -> bool:
        """In force, not flagged `conflict` and involved in no finding; only the owner clears a flag."""
        entry = self.get(decision_id)
        if entry is None or entry.decision.state is not State.IN_FORCE or entry.decision.conflict:
            return False
        return not self.findings_for(decision_id)


def snapshot(root: Path, project: str) -> Snapshot:
    """Load the Global layer at *root* and the layers of *project* (`<root>/<project>/`, its Changes' folders).

    An empty *project* loads the Global layer alone. Validation runs over every project's folder, so a finding is
    kept by the decisions it involves, wherever its file lies: another project's decision replacing a Global one
    leaves that Global decision not active here too. The root's, the Global layer's and *project*'s folders that
    cannot be read raise `OSError`; another project's is kept in `outside` (`read_repo`), so a conflict over a
    Global rule that only its unreadable files hold stays unseen until it can be read.
    """
    read = read_repo(root, project)
    kept = [layer for layer in read.layers if layer.scope is Scope.GLOBAL or layer.project == project]
    mine = [e for e in read.entries if e.layer in kept]
    ids = {e.decision.id for e in mine}
    unreadable = tuple(sorted(f for layer, f in read.failed if layer in kept))
    seen = sorted([*unreadable, *(f for f in check(read.entries) if ids.intersection(f.involves))])
    return Snapshot(root, project, tuple(kept), tuple(mine), tuple(seen), unreadable, tuple(read.outside))
