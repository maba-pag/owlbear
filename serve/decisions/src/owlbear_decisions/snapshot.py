"""What one project sees of a data repository: the Global layer, its own layers and every finding over them."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from owlbear_decisions.models import Scope, State
from owlbear_decisions.storage import is_folder
from owlbear_decisions.validate import Entry, Finding, Layer, check, layers, project_folders, read_layers

if TYPE_CHECKING:
    from pathlib import Path

CONFLICT = "two-successors"


@dataclass(frozen=True)
class Snapshot:
    """The decisions of the Global layer and one project's layers, and every finding involving one of them.

    A finding's `involves` names its decisions; a file that did not load involves none and is kept, in `unreadable`
    too, when it lies in one of these layers. A snapshot with such a file is not `complete`: the rules that file
    holds are unknown.
    """

    root: Path
    project: str
    layers: tuple[Layer, ...]
    entries: tuple[Entry, ...]
    findings: tuple[Finding, ...]
    unreadable: tuple[Finding, ...] = ()

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
    leaves that Global decision not active here too. Folders that cannot be read raise `OSError`.
    """
    own = root / project
    folders = sorted({*project_folders(root), *([own] if project and is_folder(own) else [])})
    every = layers(root, folders)
    entries, failed = read_layers(every)
    kept = [layer for layer in every if layer.scope is Scope.GLOBAL or layer.project == project]
    mine = [e for e in entries if e.layer in kept]
    ids = {e.decision.id for e in mine}
    unreadable = tuple(sorted(f for layer, f in failed if layer in kept))
    seen = sorted([*unreadable, *(f for f in check(entries) if ids.intersection(f.involves))])
    return Snapshot(root, project, tuple(kept), tuple(mine), tuple(seen), unreadable)
