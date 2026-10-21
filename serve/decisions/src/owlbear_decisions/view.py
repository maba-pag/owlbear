"""Generate OwlBear's read-only decisions view: the Global and one project's decisions, rules apart from history.

GitHub's agents and CodeRabbit read the view in OwlBear's repository; only the generator reads owlbear-data (TD-425).
Pull-request CI checks the view's own hash; a workflow with a read-only data token checks it is fresh (TD-436).
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING

from owlbear_decisions.models import LinkType, Scope, State
from owlbear_decisions.snapshot import CONFLICT, Snapshot, snapshot

if TYPE_CHECKING:
    from collections.abc import Sequence

    from owlbear_decisions.models import Decision
    from owlbear_decisions.validate import Entry

RECORD = ".owlbear/research/delivery-liveness-first-rebuild.md"
OUT = Path(".owlbear/decisions.md")
COMMIT_PREFIX = "Data commit: "
NO_COMMIT = "none"
HASH_LINE = re.compile(r"<!-- decisions-view sha256:([0-9a-f]{64}) -->")
_COMMIT = re.compile(r"[0-9a-f]{7,40}")
_COMMIT_LINE = re.compile(re.escape(COMMIT_PREFIX) + r"(`[0-9a-f]{7,40}`|none \(no decisions migrated yet\))")
_COMMIT_AT = 6  # the data commit's line in a rendered view: after the marker, the title and the two-line note
_HISTORY = (State.REPLACED, State.WITHDRAWN, State.SPENT)


def _line(text: str) -> str:
    return " ".join(text.split())


def _scope(d: Decision) -> str:
    if d.scope is Scope.GLOBAL:
        return "Global"
    return f"project `{d.project}`" if d.scope is Scope.PROJECT else f"Change `{d.project}/{d.change}`"


def _names(seen: Snapshot) -> dict[str, str]:
    return {
        e.decision.id: f"`{e.decision.id}`" + (f" ({', '.join(e.decision.aliases)})" if e.decision.aliases else "")
        for e in seen.entries
    }


def _name(names: dict[str, str], decision_id: str) -> str:
    return names.get(decision_id, f"`{decision_id}`")


def _rule(entry: Entry, seen: Snapshot, names: dict[str, str]) -> list[str]:
    d = entry.decision
    source = f", {_line(d.source)}" if d.source else ""
    lines = [
        f"- **{_name(names, d.id)}** {_line(d.title)}",
        f"  - Statement: {_line(d.statement)}",
        f"  - Origin: {d.origin} by {_line(d.actor)}{source}, {d.created_at.date()}; scope: {_scope(d)}",
    ]
    a = d.applies_to
    selectors = [
        f"{kind} {', '.join(f'`{v}`' for v in values)}"
        for kind, values in (("paths", a.paths), ("roles", a.roles), ("steps", a.steps))
        if values
    ]
    if selectors:
        lines.append(f"  - Applies to: {'; '.join(selectors)}")
    lines.extend(
        f'  - Owner\'s words ({w.date}{f", {w.alias}" if w.alias else ""}): "{_line(w.text)}"' for w in d.owner_words
    )
    if d.links:
        lines.append(f"  - Links: {'; '.join(f'{link.type} {_name(names, link.target)}' for link in d.links)}")
    rules = sorted({f.rule for f in seen.findings_for(d.id)})
    if d.conflict or CONFLICT in rules:
        lines.append("  - **Conflict:** not active until the owner resolves it")
    if others := [rule for rule in rules if rule != CONFLICT]:
        lines.append(f"  - **Findings:** {', '.join(others)} (see Findings); not active")
    return lines


def _rank(entry: Entry) -> tuple[int, str, str]:
    order = {Scope.GLOBAL: 0, Scope.PROJECT: 1, Scope.CHANGE: 2}
    return order[entry.layer.scope], entry.layer.change, entry.decision.id


def _rules(seen: Snapshot, names: dict[str, str]) -> list[str]:
    lines = ["## Rules in force", ""]
    in_force = [e for e in seen.entries if e.decision.state is State.IN_FORCE]
    for heading, scopes in (("Global", {Scope.GLOBAL}), (f"`{seen.project}`", {Scope.PROJECT, Scope.CHANGE})):
        lines += [f"### {heading}", ""]
        topics: dict[str, list[Entry]] = defaultdict(list)
        for entry in (e for e in in_force if e.layer.scope in scopes):
            topics[_line(entry.decision.topic)].append(entry)
        if not topics:
            lines += ["None.", ""]
        for topic in sorted(topics, key=lambda t: (not t, t)):
            lines += [f"#### {topic or 'No topic'}", ""]
            for entry in sorted(topics[topic], key=_rank):
                lines += _rule(entry, seen, names)
            lines.append("")
    return lines


def _history(seen: Snapshot, names: dict[str, str]) -> list[str]:
    successors: dict[str, list[str]] = defaultdict(list)
    for entry in seen.entries:
        for link in entry.decision.links:
            if link.type in {LinkType.REPLACES, LinkType.PROMOTED_FROM}:  # a promotion succeeds its source too
                successors[link.target].append(entry.decision.id)
    lines = ["## History", "", "Replaced, withdrawn and spent decisions; none of them is in force.", ""]
    retired = sorted((e for e in seen.entries if e.decision.state in _HISTORY), key=_rank)
    for entry in retired:
        d = entry.decision
        by = ""
        if d.state is State.REPLACED:
            found = sorted(set(successors[d.id]))
            by = f" by {', '.join(_name(names, s) for s in found)}" if found else " (no successor in this view)"
        lines.append(f"- {_name(names, d.id)} {d.state}{by}: {_line(d.title)} ({_scope(d)})")
    return [*lines, *([] if retired else ["None."]), ""]


def _findings(seen: Snapshot) -> list[str]:
    if not seen.findings:
        return []
    lines = ["## Findings", "", "The validator's findings over these decisions; no decision involved is active.", ""]
    if not seen.complete:
        lines += ["Some decision files did not load: the rules they hold are unknown.", ""]
    for finding in seen.findings:
        path = Path(finding.path)
        shown = path.relative_to(seen.root).as_posix() if path.is_relative_to(seen.root) else finding.path
        lines.append(f"- `{shown}`: {finding.rule}: {_line(finding.message)}")
    return [*lines, ""]


def render(seen: Snapshot, commit: str) -> str:
    """The view's text; *commit* is the data commit, or `none` for a data repository without decisions."""
    if commit == NO_COMMIT and (seen.entries or seen.findings):
        msg = "a view with decisions or findings names the data commit it came from"
        raise ValueError(msg)
    if commit != NO_COMMIT and not _COMMIT.fullmatch(commit):
        msg = f"{commit!r} is not a commit hash"
        raise ValueError(msg)
    drafts = sum(1 for e in seen.entries if e.decision.state is State.DRAFT)
    names = _names(seen)
    lines = [
        "<!-- markdownlint-disable -->",
        f"# Decisions: Global and `{seen.project}`",
        "",
        "Generated by `uv run decisions-view` from owlbear-data; do not edit. Pull-request CI checks the hash on the",
        "last line; a workflow on pushes to main and a daily schedule fails when owlbear-data's decisions differ.",
        "",
        COMMIT_PREFIX + (f"`{commit}`" if commit != NO_COMMIT else "none (no decisions migrated yet)"),
        "",
        f"The decision record `{RECORD}` stays authoritative until the owner has reviewed the migration",
        "(TD-437): where this view and the record differ, follow the record.",
        "",
        *([f"Drafts (proposed, not in force) are not listed: {drafts}.", ""] if drafts else []),
        *_rules(seen, names),
        *_history(seen, names),
        *_findings(seen),
    ]
    body = "\n".join(lines).rstrip("\n") + "\n\n"
    return f"{body}<!-- decisions-view sha256:{hashlib.sha256(body.encode()).hexdigest()} -->\n"


def hash_problem(text: str) -> str:
    """Why *text* is not an unedited view, or "" when its last line's hash matches everything above it."""
    body, _, last = text.removesuffix("\n").rpartition("\n")
    match = HASH_LINE.fullmatch(last)
    if not text.endswith("\n") or match is None:
        return "its last line is not the view's hash comment"
    if hashlib.sha256(f"{body}\n".encode()).hexdigest() != match[1]:
        return "it was edited by hand: its content does not match the hash on its last line"
    return ""


def _comparable(text: str) -> list[str]:
    """The view's lines without its one data-commit line and its hash: a new data commit alone never makes it stale.

    Only the line where the generator writes the commit, in its exact form, is left out; any other line counts.
    """
    lines = text.splitlines()
    if lines and HASH_LINE.fullmatch(lines[-1]):
        lines = lines[:-1]
    if len(lines) > _COMMIT_AT and _COMMIT_LINE.fullmatch(lines[_COMMIT_AT]):
        del lines[_COMMIT_AT]
    return lines


def _head(root: Path) -> str:
    done = subprocess.run(  # noqa: S603 - fixed git argument vector
        ["git", "-C", str(root), "rev-parse", "HEAD"],  # noqa: S607 - git from PATH
        capture_output=True,
        text=True,
        check=False,
    )
    if done.returncode or not _COMMIT.fullmatch(commit := done.stdout.strip()):
        msg = f"{root} is not a Git checkout with a commit; pass --commit"
        raise ValueError(msg)
    return commit


def check(path: Path, fresh: str) -> list[str]:
    """Why the view at *path* is not *fresh*: missing, edited by hand, or showing other decisions; [] when current."""
    try:
        current = path.read_bytes().decode()
    except FileNotFoundError:
        return [f"{path} is missing"]
    if problem := hash_problem(current):
        return [f"{path}: {problem}"]
    old, new = _comparable(current), _comparable(fresh)
    if old == new:
        return []
    diff = difflib.unified_diff(old, new, f"{path} (committed)", "owlbear-data (now)", lineterm="")
    return [f"{path} is stale: owlbear-data's decisions differ from it", *diff]


def main(argv: Sequence[str] | None = None) -> int:
    """`decisions-view <data-root>`: write the view, or with `--check` exit 1 when the committed one differs."""
    parser = argparse.ArgumentParser(prog="decisions-view", description=__doc__)
    parser.add_argument("root", type=Path, help="the owlbear-data checkout's root (the Global layer)")
    parser.add_argument("--project", default="owlbear", help="the project's data folder (default: owlbear)")
    parser.add_argument("--out", type=Path, default=OUT, help=f"the view (default: {OUT})")
    parser.add_argument("--commit", help="the data commit (default: the root's HEAD); `none` only without decisions")
    parser.add_argument("--check", action="store_true", help="exit 1 when --out is missing, edited or stale")
    args = parser.parse_args(argv)
    if not args.root.is_dir():
        parser.error(f"{args.root} is not a folder")
    try:
        seen = snapshot(args.root, args.project)
        commit = args.commit or _head(args.root)
        text = render(seen, commit)
    except (OSError, ValueError) as exc:
        parser.exit(2, f"decisions-view: {exc}\n")
    if args.check:
        if problems := check(args.out, text):
            sys.stderr.write("\n".join(problems) + "\n")
            sys.stderr.write(
                f"decisions-view: the lead chat regenerates the view from owlbear-data {commit} by pull request: "
                f"uv run decisions-view <owlbear-data> --project {args.project} --out {args.out}\n"
            )
            return 1
        sys.stdout.write(f"{args.out} matches owlbear-data {commit}\n")
        return 0
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8", newline="\n")
    in_force = sum(1 for e in seen.entries if e.decision.state is State.IN_FORCE)
    sys.stdout.write(f"wrote {args.out}: {in_force} in force, {len(seen.findings)} finding(s), data {commit}\n")
    return 0
