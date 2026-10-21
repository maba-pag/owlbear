"""Preview the record's migration: one proposed decision per in-force bullet, plus a report for the owner.

The record itself is never changed; it stays authoritative until the owner has reviewed the preview (TD-437).
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from owlbear_decisions.models import STATEMENT_LIMIT, Decision, Origin, OwnerWords, Scope, State, new_id
from owlbear_decisions.record import UNKNOWN, Bullet, Topic, Words, parse_record
from owlbear_decisions.report import orphans, render
from owlbear_decisions.storage import DECISIONS_DIR, write
from owlbear_decisions.validate import Finding, validate_repo

if TYPE_CHECKING:
    from collections.abc import Sequence

_RANK = {Origin.AUTONOMOUS: 0, Origin.APPROVED: 1, Origin.DECIDED: 2}
_TITLE_WORDS = 8


@dataclass
class Clause:
    """A proposed decision and why it may need the owner."""

    topic: Topic
    bullet: Bullet
    decision: Decision
    unclear: list[str] = field(default_factory=list)


@dataclass
class Preview:
    """The parsed record and its proposed decisions."""

    topics: list[Topic]
    clauses: list[Clause]
    rows: dict[str, tuple[str, Topic]]
    findings: list[Finding] = field(default_factory=list)


def _title(statement: str) -> str:
    head = re.split(r"[.;:](?:\s|$)| [-\u2013\u2014] ", statement, maxsplit=1)[0]
    words = head.split()
    return " ".join(words[:_TITLE_WORDS]).rstrip(",") + (" …" if len(words) > _TITLE_WORDS else "")


def _origin(bullet: Bullet, topic: Topic, rows: dict[str, tuple[str, Topic]]) -> tuple[Origin, list[str]]:
    # a line may cite another topic's row: its origin comes from the Rows line that lists it
    origins = {td: Origin(topic.rows.get(td) or rows[td][0]) for td in bullet.cited if td in topic.rows or td in rows}
    unclear = [f"{td} is in no Rows line" for td in bullet.cited if td not in origins]
    found = set(origins.values())
    if not bullet.cited:
        unclear.append("cites no TD row; origin autonomous by the best-effort rule")
    if len(found) > 1:
        mix = "; ".join(f"{o} {', '.join(td for td, of in origins.items() if of == o)}" for o in sorted(found))
        unclear.append(f"mixed origins ({mix}); the most protective one is proposed")
    unclear.extend(f"origin qualified as '{q}' in the record" for ref in bullet.references for q in ref.qualifiers)
    return (max(found, key=_RANK.__getitem__) if found else Origin.AUTONOMOUS), unclear


def _words(
    bullet: Bullet, topic: Topic, rows: dict[str, tuple[str, Topic]], every: dict[str, list[Words]]
) -> tuple[tuple[OwnerWords, ...], list[str]]:
    attached: list[OwnerWords] = []
    unclear: list[str] = []
    for td in bullet.cited:
        if topic.rows.get(td, rows.get(td, ("",))[0]) != Origin.DECIDED:
            continue
        found = [w for w in topic.words if w.alias == td] or every.get(td, [])
        # a row chosen without a quote has none (TD-388), and the record keeps quotes to one line (C-31), so a quote
        # cut with … is normal too: neither is unclear
        attached.extend(OwnerWords(text=w.text, date=date.fromisoformat(w.date), alias=td) for w in found)
    return tuple(attached), unclear


def _clause(
    topic: Topic, bullet: Bullet, context: tuple[dict, dict], *, project: str, minted: tuple[str, datetime]
) -> Clause:
    rows, every = context
    origin, unclear = _origin(bullet, topic, rows)
    words, missing = _words(bullet, topic, rows, every)
    if len(bullet.statement) > STATEMENT_LIMIT:
        unclear.append(f"statement has {len(bullet.statement)} characters, over {STATEMENT_LIMIT}")
    references = "; ".join(f"[{ref.raw}]" for ref in bullet.references) or "none"
    decision = Decision(
        id=minted[0],
        aliases=bullet.cited,
        title=_title(bullet.statement),
        topic=topic.heading,
        statement=bullet.statement,
        rationale=f"Migrated from the decision record, {topic.heading}, line {bullet.line}. References: {references}.",
        scope=Scope.PROJECT,
        project=project,
        origin=origin,
        actor="assistant" if origin is Origin.AUTONOMOUS else "owner",
        source=f"decision record line {bullet.line}",
        owner_words=words,
        state=State.IN_FORCE,
        created_at=minted[1],
    )
    return Clause(topic, bullet, decision, [*unclear, *missing])


def preview(text: str, *, project: str = "owlbear", at: datetime | None = None) -> Preview:
    """Parse the record and propose one decision per in-force bullet."""
    topics = parse_record(text)
    rows: dict[str, tuple[str, Topic]] = {}
    every: dict[str, list[Words]] = {}
    for topic in topics:
        for td, origin in topic.rows.items():
            rows.setdefault(td, (origin, topic))
        for words in topic.words:
            every.setdefault(words.alias, []).append(words)
    at = at or latest_words(topics)
    clauses: list[Clause] = []
    seen: Counter[tuple[str, str]] = Counter()  # equal statements in one topic (refs stripped) get distinct ids
    for topic in (t for t in topics if t.key != UNKNOWN):
        for bullet in topic.bullets:
            occurrence = seen[topic.heading, bullet.statement]
            seen[topic.heading, bullet.statement] += 1
            minted = (new_id(at, seed=f"{topic.heading}|{bullet.statement}|{occurrence}"), at)
            clauses.append(_clause(topic, bullet, (rows, every), project=project, minted=minted))
    return Preview(topics, clauses, rows)


def latest_words(topics: list[Topic]) -> datetime:
    """The record's newest owner's-words date, midnight UTC: a reproducible creation time for the preview."""
    dates = [date.fromisoformat(w.date) for topic in topics for w in topic.words] or [date(2026, 1, 1)]
    newest = max(dates)
    return datetime(newest.year, newest.month, newest.day, tzinfo=UTC)


def write_preview(record: Path, out: Path, project: str = "owlbear") -> Preview:
    """Write the proposed decisions to `<out>/<project>/decisions/`, validate them and write `REPORT.md`."""
    target = out / project / DECISIONS_DIR
    if (target.exists() and any(target.iterdir())) or (out / "REPORT.md").exists():
        msg = f"{out} already holds a preview; choose an empty folder"
        raise FileExistsError(msg)
    raw = record.read_bytes()
    result = preview(raw.decode("utf-8"), project=project)
    ids = [clause.decision.id for clause in result.clauses]
    if len(set(ids)) != len(ids):
        msg = "the preview minted one id twice; nothing was written"
        raise ValueError(msg)
    for clause in result.clauses:
        write(clause.decision, out / project)
    result.findings = validate_repo(out)
    digest = hashlib.sha256(raw).hexdigest()
    report = render(result, record=str(record), digest=digest, out=out, project=project)
    (out / "REPORT.md").write_text(report, encoding="utf-8")
    return result


def main(argv: Sequence[str] | None = None) -> int:
    """`decisions-migrate-preview <record.md> <out-dir>`: write the preview and print its counts."""
    parser = argparse.ArgumentParser(prog="decisions-migrate-preview", description=__doc__)
    parser.add_argument("record", type=Path, help="the decision record (Markdown)")
    parser.add_argument("out", type=Path, help="an empty folder for the proposed entries and REPORT.md")
    parser.add_argument("--project", default="owlbear", help="the data-repository folder (default: owlbear)")
    args = parser.parse_args(argv)
    try:
        result = write_preview(args.record, args.out, args.project)
    except (OSError, ValueError) as exc:
        parser.exit(2, f"decisions-migrate-preview: {exc}\n")
    unclear = sum(1 for clause in result.clauses if clause.unclear)
    sys.stdout.write(
        f"{len(result.clauses)} entries, {unclear} unclear clauses, {len(orphans(result))} orphan rows, "
        f"{len(result.findings)} validator findings; see {args.out / 'REPORT.md'}\n"
    )
    return 0
