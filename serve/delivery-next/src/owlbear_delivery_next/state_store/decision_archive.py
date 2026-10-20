"""A finished Change's decisions as decision files beside its record (TD-419 slice 2, TD-148).

Change-scope decisions go to `<project>/changes/<record stem>/decisions/`: spent once the Change merged or ended
unchanged, withdrawn when it was abandoned. Project-scope ones go to `<project>/decisions/`: in force once merged or
unchanged (the owner's brief approval activated them), a draft the owner may still activate when abandoned.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from owlbear_decisions import DecisionError, LinkType, Scope, State, check_write, decision_path, new_id, read, write
from owlbear_decisions.models import STATEMENT_LIMIT, Decision

if TYPE_CHECKING:
    from datetime import datetime
    from pathlib import Path

    from owlbear_delivery_next.change_contracts.models import BriefDecision, Change

CHANGES = "changes"
TITLE = 120
_STATES = {  # (lasting, the Change's work stays) -> state
    (False, True): State.SPENT,
    (False, False): State.WITHDRAWN,
    (True, True): State.IN_FORCE,
    (True, False): State.DRAFT,
}


def archive(root: Path, project: str, c: Change, stem: str, outcome: str) -> tuple[list[Path], list[str]]:
    """Write the decisions of the finished *c*; the files to publish, and what kept them from being written.

    Every decision is built and checked against its file first; one that cannot be written keeps all of them out,
    so a published record never comes with part of its decisions. A file that already holds the same decision stays
    untouched, so a cleanup run again writes nothing new and publishes the same files. The caller holds the data
    repository's lock.
    """
    planned: list[tuple[Decision, Path, str | None]] = []
    problems: list[str] = []
    for fields in [*_brief(project, c, stem, outcome), *_changed(project, c, stem, outcome)]:
        try:
            decision = Decision.model_validate(fields)
            layer = root / project / CHANGES / stem if decision.scope is Scope.CHANGE else root / project
            path = decision_path(decision, layer)
            current = read(path) if path.exists() or path.is_symlink() else None
            if current is None or current.revision != decision.revision:
                check_write(current, decision, current.revision if current else None)
            planned.append((decision, layer, current.revision if current else None))
        except (DecisionError, ValidationError, OSError) as exc:
            problems.append(f"decision {fields['id']} of {c.slug}: {' '.join(str(exc).split())}"[:240])
    if problems:
        return [], [f"no decision of {c.slug} was archived", *problems]
    paths = []
    for decision, layer, revision in planned:
        if revision != decision.revision:
            write(decision, layer, expected_revision=revision)
        paths.append(decision_path(decision, layer))
    return paths, []


def _approved(c: Change) -> list[BriefDecision]:
    """Every approved decision, the last approved version's last: earlier ones it dropped or replaced included."""
    versions = c.brief.approved or [c.brief]
    final = {d.id for d in versions[-1].decisions}
    earlier = {d.id: d for b in versions[:-1] for d in b.decisions if d.id and d.id not in final}
    return [*earlier.values(), *versions[-1].decisions]


def _brief(project: str, c: Change, stem: str, outcome: str) -> list[dict[str, Any]]:
    """The approved brief's decisions; the owner's approval is their source and time."""
    brief = c.brief.approved[-1] if c.brief.approved else c.brief
    at = c.brief.approved_at
    if at is None:
        return []
    source = f"Change {c.slug}, brief v{brief.version} approved {at.isoformat(timespec='seconds')}"
    final = {d.id for d in brief.decisions}
    successors = {d.replaces for d in _approved(c) if d.replaces}
    kept = outcome != "abandoned"
    found = []
    for i, d in enumerate(_approved(c)):
        lasting = d.scope == "project"
        fields = _said(d.answer, d.origin, at, f"From Change {c.slug} ({outcome}).")
        fields |= _placed(project, stem, lasting=lasting, kept=kept)
        if d.id and d.id not in final:  # approved once, then replaced or dropped by a later approval
            fields["state"] = State.REPLACED if kept and d.id in successors else State.WITHDRAWN
        fields |= {
            "id": d.id or new_id(at, seed=f"{project}\n{stem}\nbrief\n{i}\n{d.question}"),
            "title": _short(d.question),
            "topic": brief.title,
            "origin": d.origin,
            "actor": "owner" if d.origin == "decided" else "shaper",
            "source": source,
            "links": [{"type": LinkType.REPLACES, "target": d.replaces}] if d.replaces else [],
            "created_at": at,
        }
        found.append(fields)
    return found


def _changed(project: str, c: Change, stem: str, outcome: str) -> list[dict[str, Any]]:
    """The decisions Delivery recorded on the Change itself, such as "Not a UI change"; each holds for it alone."""
    title = (c.brief.approved[-1] if c.brief.approved else c.brief).title
    found = []
    for i, d in enumerate(c.decisions):
        fields = _said(d.text, d.origin, d.at, f"From Change {c.slug} ({outcome}).", words=d.words)
        fields |= _placed(project, stem, lasting=False, kept=outcome != "abandoned")
        fields |= {
            "id": d.id or new_id(d.at, seed=f"{project}\n{stem}\nchange\n{i}\n{d.text}"),
            "title": _short(d.text),
            "topic": title,
            "applies_to": {"paths": d.paths},
            "origin": d.origin,
            "actor": "owner" if d.origin == "decided" else "delivery",
            "source": f"Change {c.slug}, {d.at.isoformat(timespec='seconds')}",
            "created_at": d.at,
        }
        found.append(fields)
    return found


def _placed(project: str, stem: str, *, lasting: bool, kept: bool) -> dict[str, Any]:
    scope = Scope.PROJECT if lasting else Scope.CHANGE
    return {"scope": scope, "project": project, "change": "" if lasting else stem, "state": _STATES[lasting, kept]}


def _said(text: str, origin: str, at: datetime, note: str, words: str | None = None) -> dict[str, Any]:
    """Statement, rationale and the owner's words; a longer text keeps its whole wording in the rationale.

    A brief's decided answer is the owner's choice as the shaper recorded it; a Change-level decision brings the
    owner's own answer as *words* (empty before TD-419: then none are claimed).
    """
    text = text.strip()
    long = len(text) > STATEMENT_LIMIT
    statement = text[: STATEMENT_LIMIT - 1].rstrip() + "\u2026" if long else text
    said = text if words is None else words.strip()
    owned = [{"text": said, "date": at.date()}] if origin == "decided" and said else []
    return {"statement": statement, "rationale": f"{note}\n\nWhole wording: {text}" if long else note,
            "owner_words": owned}  # fmt: skip


def _short(text: str) -> str:
    text = " ".join(text.split())
    return text if len(text) <= TITLE else text[: TITLE - 1].rstrip() + "\u2026"
