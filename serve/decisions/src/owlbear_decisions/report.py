"""Render the migration preview's `REPORT.md` for the owner's review."""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from owlbear_decisions.migrate import Clause, Preview

_EXPLAINED = {
    "statement-length": "listed under unclear clauses; the wording is kept, never cut",
    "owner-words": "listed under unclear clauses (a decided row without owner's words in the record)",
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


def _scope(result: Preview, project: str) -> list[str]:
    per_topic = Counter(c.topic.heading for c in result.clauses)
    lines = [
        "## Proposed scope",
        "",
        (
            f"Every entry is proposed for `{project}`. Mark a topic `global` to make it apply to every project; "
            "the owner decides this in his review (TD-437)."
        ),
        "",
        "| Topic | Entries | Proposed | Owner's mark |",
        "| --- | --- | --- | --- |",
    ]
    lines.extend(f"| {_cell(topic)} | {n} | {project} | |" for topic, n in per_topic.items())
    return [*lines, ""]


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
            f"`{project}/decisions/`, one per in-force bullet."
        ),
        "",
    ]
    sections = (
        _counts(result),
        _unclear(result),
        _orphans(result),
        _scope(result, project),
        _findings(result, out),
        _concordance(result),
    )
    return "\n".join([*head, *(line for section in sections for line in section)]).rstrip() + "\n"
