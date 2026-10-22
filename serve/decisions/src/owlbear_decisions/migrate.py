"""Preview the record's migration: one proposed decision per in-force bullet, plus a report for the owner.

The record itself is never changed; it stays authoritative until the owner has reviewed the preview (TD-437). Each
entry is inherited: its recorded authority, never read back, and none of the owner's words (TD-449, TD-454). An
overlay rewords lines that only make sense beside their neighbours (TD-462) and names the Global ones (TD-442).
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

from pydantic import BaseModel, ConfigDict, Field, model_validator

from owlbear_decisions.models import STATEMENT_LIMIT, Decision, Origin, Scope, State, new_id
from owlbear_decisions.record import UNKNOWN, Bullet, Topic, parse_record
from owlbear_decisions.report import orphans, render
from owlbear_decisions.storage import DECISIONS_DIR, write
from owlbear_decisions.validate import Finding, validate_repo

if TYPE_CHECKING:
    from collections.abc import Sequence

_RANK = {Origin.AUTONOMOUS: 0, Origin.APPROVED: 1, Origin.DECIDED: 2}
_TITLE_WORDS = 8


class GlobalEntry(BaseModel):
    """A record line TD-442 makes Global, keyed by its exact statement."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    topic: str
    original: str


class Rewording(BaseModel):
    """A record line reworded to stand alone, for the owner's review (TD-462)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    topic: str
    original: str
    statement: str = Field(min_length=1)
    note: str = ""

    @property
    def uncertain(self) -> bool:
        """The rewording's author doubts it."""
        return self.note.startswith("uncertain")


class Overlay(BaseModel):
    """Rewordings and Global entries to apply to the record's lines (`.owlbear/migration/decisions-overlay.json`)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source: str = ""
    notes: tuple[str, ...] = ()
    global_: tuple[GlobalEntry, ...] = Field(default=(), alias="global")
    reworded: tuple[Rewording, ...] = ()

    @model_validator(mode="after")
    def _unique(self) -> Overlay:
        for name, entries in (("global", self.global_), ("reworded", self.reworded)):
            if twice := [o for o, n in Counter(e.original for e in entries).items() if n > 1]:
                msg = f"the overlay's {name} lists one original twice: {twice[0]}"
                raise ValueError(msg)
        return self


@dataclass
class Clause:
    """A proposed decision and why it may need the owner."""

    topic: Topic
    bullet: Bullet
    decision: Decision
    unclear: list[str] = field(default_factory=list)
    rewording: Rewording | None = None


@dataclass
class Preview:
    """The parsed record and its proposed decisions."""

    topics: list[Topic]
    clauses: list[Clause]
    rows: dict[str, tuple[str, Topic]]
    findings: list[Finding] = field(default_factory=list)
    overlay: Overlay | None = None
    stale: list[tuple[str, GlobalEntry | Rewording]] = field(default_factory=list)


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


def _clause(  # noqa: PLR0913 - the line, its rows and where its entry goes
    topic: Topic,
    bullet: Bullet,
    rows: dict[str, tuple[str, Topic]],
    *,
    project: str,
    minted: tuple[str, datetime],
    overlay: Overlay | None,
) -> Clause:
    origin, unclear = _origin(bullet, topic, rows)
    rewording = next((e for e in overlay.reworded if e.original == bullet.statement), None) if overlay else None
    is_global = bool(overlay) and any(e.original == bullet.statement for e in overlay.global_)
    statement = rewording.statement if rewording else bullet.statement
    if len(statement) > STATEMENT_LIMIT:
        unclear.append(f"statement has {len(statement)} characters, over {STATEMENT_LIMIT}")
    references = "; ".join(f"[{ref.raw}]" for ref in bullet.references) or "none"
    rationale = f"Migrated from the decision record, {topic.heading}, line {bullet.line}. References: {references}."
    decision = Decision(
        id=minted[0],
        aliases=bullet.cited,
        title=_title(statement),
        topic=topic.heading,
        statement=statement,
        rationale=rationale + (" Reworded to stand alone (TD-462)." if rewording else ""),
        scope=Scope.GLOBAL if is_global else Scope.PROJECT,
        project="" if is_global else project,
        origin=origin,
        actor="assistant" if origin is Origin.AUTONOMOUS else "owner",
        source=f"decision record line {bullet.line}",
        inherited=True,
        state=State.IN_FORCE,
        created_at=minted[1],
    )
    return Clause(topic, bullet, decision, unclear, rewording)


def preview(
    text: str, *, project: str = "owlbear", at: datetime | None = None, overlay: Overlay | None = None
) -> Preview:
    """Parse the record and propose one decision per in-force bullet, the overlay applied."""
    topics = parse_record(text)
    rows: dict[str, tuple[str, Topic]] = {}
    for topic in topics:
        for td, origin in topic.rows.items():
            rows.setdefault(td, (origin, topic))
    at = at or latest_words(topics)
    clauses: list[Clause] = []
    seen: Counter[tuple[str, str]] = Counter()  # equal statements in one topic (refs stripped) get distinct ids
    for topic in (t for t in topics if t.key != UNKNOWN):
        for bullet in topic.bullets:
            occurrence = seen[topic.heading, bullet.statement]
            seen[topic.heading, bullet.statement] += 1
            minted = (new_id(at, seed=f"{topic.heading}|{bullet.statement}|{occurrence}"), at)
            clauses.append(_clause(topic, bullet, rows, project=project, minted=minted, overlay=overlay))
    statements = {clause.bullet.statement for clause in clauses}
    entries = [("global", e) for e in overlay.global_] + [("reworded", e) for e in overlay.reworded] if overlay else []
    stale = [(kind, entry) for kind, entry in entries if entry.original not in statements]
    return Preview(topics, clauses, rows, overlay=overlay, stale=stale)


def latest_words(topics: list[Topic]) -> datetime:
    """The record's newest owner's-words date, midnight UTC: a reproducible creation time for the preview."""
    dates = [date.fromisoformat(w.date) for topic in topics for w in topic.words] or [date(2026, 1, 1)]
    newest = max(dates)
    return datetime(newest.year, newest.month, newest.day, tzinfo=UTC)


def write_preview(record: Path, out: Path, project: str = "owlbear", overlay: Path | None = None) -> Preview:
    """Write the proposed decisions to `<out>/<project>/decisions/`, validate them and write `REPORT.md`.

    Global ones go to `<out>/decisions/`, the Global layer at a data repository's root.
    """
    targets = (out / project / DECISIONS_DIR, out / DECISIONS_DIR)
    if any(t.exists() and any(t.iterdir()) for t in targets) or (out / "REPORT.md").exists():
        msg = f"{out} already holds a preview; choose an empty folder"
        raise FileExistsError(msg)
    applied = Overlay.model_validate_json(overlay.read_bytes()) if overlay else None
    raw = record.read_bytes()
    result = preview(raw.decode("utf-8"), project=project, overlay=applied)
    ids = [clause.decision.id for clause in result.clauses]
    if len(set(ids)) != len(ids):
        msg = "the preview minted one id twice; nothing was written"
        raise ValueError(msg)
    for clause in result.clauses:
        write(clause.decision, out if clause.decision.scope is Scope.GLOBAL else out / project)
    result.findings = validate_repo(out)
    digest = hashlib.sha256(raw).hexdigest()
    report = render(result, record=str(record), digest=digest, out=out, project=project)
    (out / "REPORT.md").write_text(report, encoding="utf-8")
    return result


def main(argv: Sequence[str] | None = None) -> int:
    """`decisions-migrate-preview <record.md> <out-dir> [--overlay PATH]`: write the preview, print its counts."""
    parser = argparse.ArgumentParser(prog="decisions-migrate-preview", description=__doc__)
    parser.add_argument("record", type=Path, help="the decision record (Markdown)")
    parser.add_argument("out", type=Path, help="an empty folder for the proposed entries and REPORT.md")
    parser.add_argument("--project", default="owlbear", help="the data-repository folder (default: owlbear)")
    parser.add_argument("--overlay", type=Path, help="rewordings and Global lines (JSON); none by default")
    args = parser.parse_args(argv)
    try:
        result = write_preview(args.record, args.out, args.project, args.overlay)
    except (OSError, ValueError) as exc:
        parser.exit(2, f"decisions-migrate-preview: {exc}\n")
    unclear = sum(1 for clause in result.clauses if clause.unclear)
    reworded = sum(1 for clause in result.clauses if clause.rewording)
    shared = sum(1 for clause in result.clauses if clause.decision.scope is Scope.GLOBAL)
    sys.stdout.write(
        f"{len(result.clauses)} entries, {unclear} unclear clauses, {len(orphans(result))} orphan rows, "
        f"{len(result.findings)} validator findings, {reworded} reworded, {shared} Global, "
        f"{len(result.stale)} stale overlay entries; see {args.out / 'REPORT.md'}\n"
    )
    return 0
