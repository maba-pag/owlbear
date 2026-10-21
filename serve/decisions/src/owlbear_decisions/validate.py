"""Validate the decisions of a data repository: the Global layer at its root, each project in its folder."""

from __future__ import annotations

import argparse
import stat
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from owlbear_decisions.models import STATEMENT_LIMIT, Decision, LinkType, Scope, State
from owlbear_decisions.storage import DECISIONS_DIR, is_folder, kind, load_folder

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

CHANGES_DIR = "changes"


@dataclass(frozen=True, order=True)
class Finding:
    """One rule a file breaks, and the decisions it involves: none for a file that did not load."""

    path: str
    rule: str
    message: str
    involves: tuple[str, ...] = ()


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
        found.extend(Layer(held, Scope.CHANGE, folder.name, held.name) for held in _change_folders(folder))
    return found


def _change_folders(project: Path) -> list[Path]:
    """The Change folders holding decisions; a `changes` path or Change folder that is not a real folder raises."""
    changes = project / CHANGES_DIR
    if (mode := kind(changes)) is None:
        return []
    if not stat.S_ISDIR(mode):
        msg = f"{changes} is not a real folder: its Change decisions cannot be read"
        raise NotADirectoryError(msg)
    found = []
    for held in sorted(changes.iterdir()):
        if stat.S_ISLNK(kind(held) or 0):
            msg = f"{held} is a symlink: a Change folder must be a real folder"
            raise NotADirectoryError(msg)
        if is_folder(held) and kind(held / DECISIONS_DIR) is not None:
            found.append(held)
    return found


def project_folders(root: Path) -> list[Path]:
    """The folders under a data repository's *root* that hold project or Change decisions.

    A folder that cannot be looked into raises `OSError`: it is never taken for one without decisions.
    """
    return [
        child
        for child in sorted(root.iterdir())
        if not child.name.startswith(".")
        and child.name != DECISIONS_DIR
        and is_folder(child)
        and (kind(child / DECISIONS_DIR) is not None or _change_folders(child))
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
    return found  # a decided decision chosen without a quote has none (TD-388): its words are not required


def _visible(source: Entry, target: Entry, link: LinkType) -> bool:
    if link is LinkType.PROMOTED_FROM or target.decision.scope is Scope.GLOBAL:
        return True
    return source.decision.scope is not Scope.GLOBAL and source.decision.project == target.decision.project


def _same_or_narrower(source: Decision, target: Decision) -> bool:
    """Global replaces Global only; a project its own project's or Changes' decisions; a Change its own."""
    if source.scope is Scope.GLOBAL:
        return target.scope is Scope.GLOBAL
    if target.scope is Scope.GLOBAL or target.project != source.project:
        return False
    return source.scope is Scope.PROJECT or target.change == source.change


def _wider(source: Decision, target: Decision) -> bool:
    """A promotion widens: Global from a project or Change decision, a project from one of its own Changes'."""
    if source.scope is Scope.GLOBAL:
        return target.scope is not Scope.GLOBAL
    return source.scope is Scope.PROJECT and target.scope is Scope.CHANGE and target.project == source.project


def _succeeds(entry: Entry, target: str, link: LinkType, by_id: dict[str, Entry]) -> bool:
    """A `replaces` link, or a `promoted_from` link that widens: both make *entry* a successor of *target*."""
    if link is LinkType.REPLACES:
        return True
    found = by_id.get(target)
    return link is LinkType.PROMOTED_FROM and found is not None and _wider(entry.decision, found.decision)


def _links(entry: Entry, by_id: dict[str, Entry]) -> list[Finding]:
    path, source = str(entry.path), entry.decision.id
    found: list[Finding] = []
    for link in entry.decision.links:
        target = by_id.get(link.target)
        if link.target == source:
            found.append(Finding(path, "link-target", f"{link.type} links to itself", (source,)))
        elif target is None or not _visible(entry, target, link.type):
            message = f"{link.type} target {link.target} is missing or out of reach"
            found.append(Finding(path, "link-target", message, (source,)))
        elif link.type is LinkType.EXCEPTION_TO and target.decision.scope is not Scope.GLOBAL:
            message = f"exception_to {link.target}, which is not a Global decision"
            found.append(Finding(path, "exception-target", message, (source,)))
        elif link.type is LinkType.REPLACES and not _same_or_narrower(entry.decision, target.decision):
            message = (
                f"replaces {link.target}, a {target.decision.scope} decision of a wider or other layer; "
                "widen by promoted_from, depart from Global by exception_to"
            )
            found.append(Finding(path, "replace-scope", message, (source, link.target)))
        elif link.type is LinkType.PROMOTED_FROM and not _wider(entry.decision, target.decision):
            message = (
                f"promoted_from {link.target}, a {target.decision.scope} decision of a layer not narrower; a "
                "promotion widens: Global from a project or Change, a project from its own Change"
            )
            found.append(Finding(path, "promote-scope", message, (source, link.target)))
    return found


def _successors(entries: list[Entry], by_id: dict[str, Entry]) -> list[Finding]:
    """Two in-force successors of one decision, and a replaced one without any; a widening promotion counts (TD-426)."""
    successors: dict[str, dict[str, Entry]] = defaultdict(dict)
    for entry in entries:
        for link in entry.decision.links:
            if _succeeds(entry, link.target, link.type, by_id):
                successors[link.target][entry.decision.id] = entry  # a repeated link is still one successor
    findings = []
    for target, by_source in successors.items():
        active = sorted((str(e.path), e.decision.id) for e in by_source.values() if e.decision.state is State.IN_FORCE)
        if len(active) > 1:
            message = f"{len(active)} in-force decisions replace or promote {target}"
            findings.extend(Finding(p, "two-successors", message, (i, target)) for p, i in active)
    for entry in entries:
        named = [e for e in successors.get(entry.decision.id, {}).values() if e.decision.state is not State.DRAFT]
        if entry.decision.state is State.REPLACED and not named:
            message = "replaced, but no decision replaces it"
            findings.append(Finding(str(entry.path), "no-successor", message, (entry.decision.id,)))
    return findings


def _duplicates(entries: list[Entry]) -> list[Finding]:
    # an alias may name several entries: one record row split into clauses keeps its TD number on each
    ids: dict[str, list[Entry]] = defaultdict(list)
    for entry in entries:
        ids[entry.decision.id].append(entry)
    return [
        Finding(str(e.path), "duplicate-id", f"id {key} is used by {len(group)} files", (key,))
        for key, group in ids.items()
        if len(group) > 1
        for e in group
    ]


def check(entries: list[Entry]) -> list[Finding]:
    """Every rule over loaded entries."""
    by_id = {e.decision.id: e for e in entries}
    findings = [Finding(str(e.path), rule, m, (e.decision.id,)) for e in entries for rule, m in _single(e)]
    findings += [f for e in entries for f in _links(e, by_id)]
    return sorted([*findings, *_duplicates(entries), *_successors(entries, by_id)])


def read_layers(found: Iterable[Layer]) -> tuple[list[Entry], list[tuple[Layer, Finding]]]:
    """The decisions of *found* layers, and each file that did not load as a finding with its layer."""
    entries: list[Entry] = []
    failed: list[tuple[Layer, Finding]] = []
    for layer in found:
        loaded = load_folder(layer.folder)
        for error in loaded.errors:
            rule = "link-type" if any(_is_link_type(loc) for loc in error.locations) else "schema"
            failed.append((layer, Finding(str(error.path), rule, error.message)))
        entries.extend(Entry(path, layer, decision) for path, decision in loaded.decisions.items())
    return entries, failed


def collect(found: Iterable[Layer]) -> tuple[list[Entry], list[Finding]]:
    """The decisions of *found* layers and every finding over them, unreadable files included."""
    entries, failed = read_layers(found)
    return entries, sorted([*(f for _, f in failed), *check(entries)])


def validate(global_folder: Path | None, project_folders: Iterable[Path]) -> list[Finding]:
    """Findings for the Global folder and the project folders, unreadable files included."""
    return collect(layers(global_folder, project_folders))[1]


def _is_link_type(location: str) -> bool:
    parts = location.split(".")
    return len(parts) == 3 and parts[0] == "links" and parts[2] == "type"  # noqa: PLR2004 - links.<n>.type


def validate_repo(root: Path) -> list[Finding]:
    """Findings for a data repository: Global at `root`, every project folder holding decisions."""
    return validate(root, project_folders(root))


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
