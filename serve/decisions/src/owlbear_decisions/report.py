"""Render the migration preview's `REPORT.md` for the owner's review."""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import TYPE_CHECKING

from owlbear_decisions.models import Scope

if TYPE_CHECKING:
    from owlbear_decisions.migrate import Clause, Preview

_EXPLAINED = {
    "statement-length": "listed under unclear clauses; the wording is kept, never cut",
}


def orphans(result: Preview) -> list[str]:
    """TDs of a Rows line cited by no in-force bullet or Open item and not listed as replaced or spent."""
    cited = {td for clause in result.clauses for td in clause.bullet.cited}
    retired = {td for topic in result.topics for td in (*topic.replaced, *topic.spent, *topic.open)}
    return sorted((td for td in result.rows if td not in cited | retired), key=lambda td: int(td[3:]))


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def _short(text: str, limit: int = 90) -> str:
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _counts(result: Preview) -> list[str]:
    origins = Counter(str(c.decision.origin) for c in result.clauses)
    rules = Counter(f.rule for f in result.findings)
    lines = [
        "## Counts",
        "",
        "| What | Count |",
        "| --- | --- |",
        f"| Topics | {sum(1 for t in result.topics if t.bullets)} |",
        f"| In-force bullets = entries | {len(result.clauses)} |",
        *(f"| Entries `{origin}` | {n} |" for origin, n in sorted(origins.items())),
        f"| Unclear clauses | {sum(1 for c in result.clauses if c.unclear)} |",
        f"| Orphan rows | {len(orphans(result))} |",
        f"| Reworded (TD-462) | {sum(1 for c in result.clauses if c.rewording)} |",
        f"| Global (TD-442) | {sum(1 for c in result.clauses if c.decision.scope is Scope.GLOBAL)} |",
        f"| Overlay entries that match no line | {len(result.stale)} |",
        f"| Validator findings | {len(result.findings)} |",
        *(f"| Validator `{rule}` | {n} |" for rule, n in sorted(rules.items())),
    ]
    return [*lines, ""]


def _unclear(result: Preview) -> list[str]:
    lines = ["## Unclear clauses", "", "Each needs the owner's reading before the migration is final.", ""]
    for clause in (c for c in result.clauses if c.unclear):
        d = clause.decision
        lines.append(f"- {clause.topic.heading}, line {clause.bullet.line}, `{d.id}` ({d.origin}):")
        lines.extend(f"  - {reason}" for reason in clause.unclear)
        lines.append(f"  - statement: {_short(d.statement)}")
    unparsed = [(t, item) for t in result.topics for item in t.unparsed]
    if unparsed:
        lines += ["", "Record lines the parser could not place (not migrated):", ""]
        lines.extend(f"- {t.heading}, line {item.line}: {_short(item.text)}" for t, item in unparsed)
    return [*lines, ""]


def _orphans(result: Preview) -> list[str]:
    lines = [
        "## Orphan rows",
        "",
        "Rows a topic lists that no in-force line or Open item cites and no Replaced or Spent line retires.",
        "",
    ]
    found = orphans(result)
    lines.extend(f"- {td} ({result.rows[td][0]}, {result.rows[td][1].heading})" for td in found)
    return [*lines, *([] if found else ["None."]), ""]


def _global(result: Preview, project: str) -> list[str]:
    lines = ["## Global by TD-442", ""]
    if result.overlay is None:
        return [*lines, f"No overlay applied: every entry is proposed for `{project}`.", ""]
    lines += [
        (
            "These entries are in `decisions/`, the Global layer at the data repository's root; every other entry is "
            f"`{project}`'s. The overlay's notes:"
        ),
        "",
        *(f"- {note}" for note in result.overlay.notes),
        "",
        "| Topic | Entry | Statement |",
        "| --- | --- | --- |",
    ]
    found = [c for c in result.clauses if c.decision.scope is Scope.GLOBAL]
    lines.extend(f"| {_cell(c.topic.heading)} | `{c.decision.id}` | {_cell(c.decision.statement)} |" for c in found)
    return [*lines, *([] if found else ["None."]), ""]


def _reworded(result: Preview) -> list[str]:
    lines = [
        "## Reworded for your review (TD-462)",
        "",
        (
            "Lines that only made sense beside their neighbours, reworded to stand alone; the entry holds the "
            "rewording only. Accept or correct each in the last column; `uncertain` ones come first."
        ),
        "",
    ]
    found = sorted(((c, r) for c in result.clauses if (r := c.rewording)), key=lambda pair: not pair[1].uncertain)
    if result.overlay is None or not found:
        return [*lines, "None.", ""]
    lines += [
        f"Overlay: {result.overlay.source}.",
        "",
        "| Topic | Entry | Original | Reworded | Note | Your mark |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for c, r in found:
        cells = (c.topic.heading, f"`{c.decision.id}`", r.original, c.decision.statement, r.note)
        lines.append("| " + " | ".join(_cell(cell) for cell in cells) + " | |")
    return [*lines, ""]


def _stale(result: Preview) -> list[str]:
    lines = [
        "## Overlay entries that match no line",
        "",
        "Overlay entries whose original is no in-force line of the record: the record changed since the overlay.",
        "",
    ]
    lines.extend(f"- {kind}, {entry.topic}: {entry.original}" for kind, entry in result.stale)
    return [*lines, *([] if result.stale else ["None."]), ""]


def _findings(result: Preview, out: Path) -> list[str]:
    lines = ["## Validator findings", "", "`decisions-validate` on this preview, by rule.", ""]
    if not result.findings:
        return [*lines, "None.", ""]
    by_rule: dict[str, list[str]] = defaultdict(list)
    for finding in result.findings:
        path = Path(finding.path)
        where = path.relative_to(out) if path.is_relative_to(out) else path
        by_rule[finding.rule].append(f"- `{where}`: {_cell(finding.message)}")
    for rule, found in sorted(by_rule.items()):
        why = _EXPLAINED.get(rule, "not expected from the migration: a defect to fix before migrating")
        lines += [f"### `{rule}` ({len(found)})", "", f"Why: {why}.", "", *found, ""]
    return lines


def _concordance(result: Preview) -> list[str]:
    entries: dict[str, list[Clause]] = defaultdict(list)
    for clause in result.clauses:
        for td in clause.bullet.cited:
            entries[td].append(clause)
    lines = [
        "## Concordance",
        "",
        "Each cited row and the entries that carry it (topic and record line in brackets).",
        "",
        "| Row | Origin | Rows line | Entries |",
        "| --- | --- | --- | --- |",
    ]
    for td in sorted(entries, key=lambda td: int(td[3:])):
        origin, home = result.rows.get(td, ("?", None))
        cells = ", ".join(f"`{c.decision.id}` ({c.topic.key} l.{c.bullet.line})" for c in entries[td])
        lines.append(f"| {td} | {origin} | {_cell(home.heading) if home else 'none'} | {cells} |")
    return [*lines, ""]


def render(result: Preview, *, record: str, digest: str, out: Path, project: str) -> str:
    """The whole report as Markdown."""
    head = [
        "# Decision migration preview",
        "",
        (
            f"Source: `{record}` (sha256 `{digest[:16]}`). The record is unchanged and stays authoritative until "
            "the owner has reviewed this preview (TD-437). Entries are in "
            f"`{project}/decisions/` and Global ones in `decisions/`, one per in-force bullet."
        ),
        "",
    ]
    sections = (
        _counts(result),
        _unclear(result),
        _orphans(result),
        _global(result, project),
        _reworded(result),
        _stale(result),
        _findings(result, out),
        _concordance(result),
    )
    return "\n".join([*head, *(line for section in sections for line in section)]).rstrip() + "\n"
