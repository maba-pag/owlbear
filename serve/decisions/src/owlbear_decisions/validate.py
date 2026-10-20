"""Validate the decisions of a data repository: the Global layer at its root, each project in its folder."""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from owlbear_decisions.models import STATEMENT_LIMIT, Decision, LinkType, Origin, Scope, State
from owlbear_decisions.storage import DECISIONS_DIR, load_folder

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

CHANGES_DIR = "changes"


@dataclass(frozen=True, order=True)
class Finding:
    """One rule a file breaks."""

    path: str
    rule: str
    message: str


@dataclass(frozen=True)
class Layer:
    """A folder holding a `decisions/` folder, and the scope its decisions must carry."""

    folder: Path
    scope: Scope
    project: str = ""
    change: str = ""


@dataclass(frozen=True)
class Entry:
    """A loaded decision with the layer it was found in."""

    path: Path
    layer: Layer
    decision: Decision


def layers(global_folder: Path | None, project_folders: Iterable[Path]) -> list[Layer]:
    """The Global layer, each project's layer and its Changes' layers (`<project>/changes/<slug>/`)."""
    found = [Layer(global_folder, Scope.GLOBAL)] if global_folder else []
    for folder in sorted(project_folders):
        found.append(Layer(folder, Scope.PROJECT, folder.name))
        found.extend(
            Layer(held.parent, Scope.CHANGE, folder.name, held.parent.name)
            for held in sorted((folder / CHANGES_DIR).glob(f"*/{DECISIONS_DIR}"))
        )
    return found


def _project_folders(root: Path) -> list[Path]:
    return [
        child
        for child in sorted(root.iterdir())
        if child.is_dir()
        and not child.name.startswith(".")
        and child.name != DECISIONS_DIR
        and ((child / DECISIONS_DIR).is_dir() or any((child / CHANGES_DIR).glob(f"*/{DECISIONS_DIR}")))
    ]


def _placement(entry: Entry) -> str:
    d, layer = entry.decision, entry.layer
    if d.scope is Scope.CHANGE and layer.scope is not Scope.CHANGE:
        return f"a change decision ({d.project}/{d.change}) outside a change folder"
    if (d.scope, d.project, d.change) != (layer.scope, layer.project, layer.change):
        where = "/".join(p for p in (layer.project, layer.change) if p) or "the Global layer"
        return f"a {d.scope} decision ({d.project or '-'}/{d.change or '-'}) in {where}"
    return ""


def _single(entry: Entry) -> list[tuple[str, str]]:
    d = entry.decision
    found: list[tuple[str, str]] = []
    if message := _placement(entry):
        found.append(("placement", message))
    if len(d.statement) > STATEMENT_LIMIT:
        found.append(("statement-length", f"statement has {len(d.statement)} characters, at most {STATEMENT_LIMIT}"))
    if d.origin is Origin.DECIDED and not d.owner_words:
        found.append(("owner-words", "a decided decision needs the owner's words"))
    return found


def _visible(source: Entry, target: Entry, link: LinkType) -> bool:
    if link is LinkType.PROMOTED_FROM or target.decision.scope is Scope.GLOBAL:
        return True
    return source.decision.scope is not Scope.GLOBAL and source.decision.project == target.decision.project


def _links(entry: Entry, by_id: dict[str, Entry]) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for link in entry.decision.links:
        target = by_id.get(link.target)
        if link.target == entry.decision.id:
            found.append(("link-target", f"{link.type} links to itself"))
        elif target is None or not _visible(entry, target, link.type):
            found.append(("link-target", f"{link.type} target {link.target} is missing or out of reach"))
        elif link.type is LinkType.EXCEPTION_TO and target.decision.scope is not Scope.GLOBAL:
            found.append(("exception-target", f"exception_to {link.target}, which is not a Global decision"))
    return found


def _successors(entries: list[Entry]) -> list[Finding]:
    successors: dict[str, dict[str, Entry]] = defaultdict(dict)
    for entry in entries:
        for link in entry.decision.links:
            if link.type is LinkType.REPLACES:
                successors[link.target][entry.decision.id] = entry  # a repeated link is still one successor
    findings = []
    for target, by_source in successors.items():
        active = sorted(str(e.path) for e in by_source.values() if e.decision.state is State.IN_FORCE)
        if len(active) > 1:
            findings.extend(
                Finding(p, "two-successors", f"{len(active)} in-force decisions replace {target}") for p in active
            )
    for entry in entries:
        named = [e for e in successors.get(entry.decision.id, {}).values() if e.decision.state is not State.DRAFT]
        if entry.decision.state is State.REPLACED and not named:
            findings.append(Finding(str(entry.path), "no-successor", "replaced, but no decision replaces it"))
    return findings


def _duplicates(entries: list[Entry]) -> list[Finding]:
    # an alias may name several entries: one record row split into clauses keeps its TD number on each
    ids: dict[str, list[Entry]] = defaultdict(list)
    for entry in entries:
        ids[entry.decision.id].append(entry)
    return [
        Finding(str(e.path), "duplicate-id", f"id {key} is used by {len(group)} files")
        for key, group in ids.items()
        if len(group) > 1
        for e in group
    ]


def check(entries: list[Entry]) -> list[Finding]:
    """Every rule over loaded entries."""
    by_id = {e.decision.id: e for e in entries}
    findings = [Finding(str(e.path), rule, m) for e in entries for rule, m in (*_single(e), *_links(e, by_id))]
    return sorted([*findings, *_duplicates(entries), *_successors(entries)])


def validate(global_folder: Path | None, project_folders: Iterable[Path]) -> list[Finding]:
    """Findings for the Global folder and the project folders, unreadable files included."""
    entries: list[Entry] = []
    findings: list[Finding] = []
    for layer in layers(global_folder, project_folders):
        loaded = load_folder(layer.folder)
        for error in loaded.errors:
            rule = "link-type" if any(_is_link_type(loc) for loc in error.locations) else "schema"
            findings.append(Finding(str(error.path), rule, error.message))
        entries.extend(Entry(path, layer, decision) for path, decision in loaded.decisions.items())
    return sorted([*findings, *check(entries)])


def _is_link_type(location: str) -> bool:
    parts = location.split(".")
    return len(parts) == 3 and parts[0] == "links" and parts[2] == "type"  # noqa: PLR2004 - links.<n>.type


def validate_repo(root: Path) -> list[Finding]:
    """Findings for a data repository: Global at `root`, every project folder holding decisions."""
    return validate(root, _project_folders(root))


def main(argv: Sequence[str] | None = None) -> int:
    """`decisions-validate <data-repo-root>`: print findings, exit 1 on any."""
    parser = argparse.ArgumentParser(prog="decisions-validate", description=__doc__)
    parser.add_argument("root", type=Path, help="the data repository's root (the Global layer)")
    args = parser.parse_args(argv)
    if not args.root.is_dir():
        parser.error(f"{args.root} is not a folder")
    findings = validate_repo(args.root)
    for finding in findings:
        sys.stdout.write(f"{finding.path}: {finding.rule}: {finding.message}\n")
    sys.stdout.write(f"{len(findings)} finding(s)\n")
    return 1 if findings else 0
