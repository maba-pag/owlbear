"""A finished Change's decisions as decision files beside its record (TD-419 slice 2, TD-148).

Change-scope decisions go to `<project>/changes/<record stem>/decisions/`: spent once the Change merged or ended
unchanged, withdrawn when it was abandoned. Project-scope ones go to `<project>/decisions/`: in force once merged or
unchanged (the owner's brief approval activated them), a draft the owner may still activate when abandoned. An
approved project decision a later approved version narrowed to the Change is withdrawn, and its successor relates to
it: a `replaces` link may not narrow a layer. A project decision replacing one of the Change's own carries no link:
its approval publishes it (TD-453, `lasting`) while the one it replaces waits for the Change's end, which withdraws
it. A project decision the approval published is left as it is: the Change's end never writes over or demotes it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from owlbear_decisions import DecisionError, LinkType, Scope, State, check_write, decision_path, new_id, read
from owlbear_decisions.models import STATEMENT_LIMIT, Decision
from owlbear_decisions.snapshot import read_repo
from owlbear_decisions.validate import Entry, Layer, check
from owlbear_delivery_next.state_store import decision_store

if TYPE_CHECKING:
    from datetime import datetime
    from pathlib import Path

    from owlbear_delivery_next.change_contracts.models import BriefDecision, Change
    from owlbear_delivery_next.state_store.decision_store import Placed

CHANGES = "changes"
TITLE = 120
WHOLE = "Whole wording: "  # a cut statement's whole text in the rationale
APPROVED = "approved"  # the brief's approval publishes its project decisions (TD-453)
_STATES = {  # (lasting, the Change's work stays) -> state
    (False, True): State.SPENT,
    (False, False): State.WITHDRAWN,
    (True, True): State.IN_FORCE,
    (True, False): State.DRAFT,
}


def archive(root: Path, project: str, c: Change, stem: str, outcome: str) -> tuple[list[Path], list[str]]:
    """Write the decisions of the finished *c*; the files to publish, and what kept them from being written.

    Every decision is built and checked against its file and, with the decisions already in the data repository,
    against the graph's rules first; one that cannot be written keeps all of them out, so a published record never
    comes with part of its decisions, and a write failing midway puts every file back as it was. A file that already
    holds the same decision stays untouched, so a cleanup run again writes nothing new and publishes the same files.
    The caller holds the data repository's lock.
    """
    planned, problems = _planned(root, project, c, stem, outcome)
    problems = problems or _graph(root, project, c, planned)
    if not problems:
        try:
            refused = decision_store.write_batch([(d, layer, rev) for d, layer, rev in planned if rev != d.revision])
        except OSError as exc:
            refused = {"files": f"cannot be written, all put back: {exc}"}
        problems = [f"decision {key} of {c.slug}: {' '.join(why.split())}"[:240] for key, why in refused.items()]
    if problems:
        return [], [f"no decision of {c.slug} was archived", *problems]
    return [decision_path(decision, layer) for decision, layer, _ in planned], []


def lasting(project: str, c: Change, stem: str) -> list[Decision]:
    """The approved brief's project decisions as its approval puts them in force, retired ones by a later version.

    Built from the approvals alone, so a retry or a restart builds the same files. Genuinely legacy ID-less decisions
    remain for the archive. An invalid ID-bearing project decision refuses the whole approval, never a subset.
    """
    ids = {d.id for d, _ in _approved(c) if d.id}
    found = []
    for fields in _brief(project, c, stem, APPROVED):
        if fields["scope"] is Scope.PROJECT and fields["id"] in ids:
            try:
                found.append(Decision.model_validate(fields))
            except ValidationError as exc:
                msg = f"decision {fields['id']} of {c.slug} cannot be published: {' '.join(str(exc).split())}"[:240]
                raise DecisionError(msg) from exc
    return found


def _planned(root: Path, project: str, c: Change, stem: str, outcome: str) -> tuple[list[Placed], list[str]]:
    """Each decision of *c* with its layer and its file's revision, and why any cannot be written over its file."""
    planned: list[Placed] = []
    problems: list[str] = []
    published = {p.id for p in c.decisions_published if p.saved}
    for fields in [*_brief(project, c, stem, outcome), *_changed(project, c, stem, outcome)]:
        if fields["scope"] is Scope.PROJECT and fields["id"] in published:
            continue
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
    return planned, problems


def _graph(root: Path, project: str, c: Change, planned: list[Placed]) -> list[str]:
    """The validator's findings involving a planned decision, judged with every decision already in the repository."""
    try:
        found = read_repo(root, project)
    except OSError as exc:
        return [f"the decisions of {c.slug} cannot be checked against {root}: {exc}"[:240]]
    placed = [Entry(decision_path(d, layer), Layer(layer, d.scope, d.project, d.change), d) for d, layer, _ in planned]
    paths = {e.path for e in placed}
    entries = [e for e in found.entries if e.path not in paths] + placed
    ids = {d.id for d, _, _ in planned}
    return [
        f"decision {', '.join(f.involves)} of {c.slug}: {f.rule}: {' '.join(f.message.split())}"[:240]
        for f in check(entries)
        if ids.intersection(f.involves)
    ]


def _approved(c: Change) -> list[tuple[BriefDecision, datetime | None]]:
    """Every approved decision with the approval of the latest version holding it, the last version's last.

    Earlier ones it dropped or replaced are included; a version without its own approval time takes the brief's.
    """
    versions = c.brief.approved or [c.brief]
    final = {d.id for d in versions[-1].decisions}
    earlier = {d.id: (d, b.approved_at or c.brief.approved_at) for b in versions[:-1] for d in b.decisions
               if d.id and d.id not in final}  # fmt: skip
    last = versions[-1].approved_at or c.brief.approved_at
    return [*earlier.values(), *((d, last) for d in versions[-1].decisions)]


def _brief(project: str, c: Change, stem: str, outcome: str) -> list[dict[str, Any]]:
    """The approved brief's decisions; the owner's approval is their source and time."""
    brief = c.brief.approved[-1] if c.brief.approved else c.brief
    at = c.brief.approved_at
    if at is None:
        return []
    source = f"Change {c.slug}, brief v{brief.version} approved {at.isoformat(timespec='seconds')}"
    final = {d.id for d in brief.decisions}
    approved = _approved(c)
    lasting = {d.id for d, _ in approved if d.id and d.scope == "project"}
    own = {d.id for d, _ in approved if d.id and d.scope != "project"}
    narrowing = {d.replaces for d, _ in approved if d.replaces in lasting and d.scope != "project"}
    unlinked = {d.replaces for d, _ in approved if d.replaces in own and d.scope == "project"}
    successors = {d.replaces for d, _ in approved if d.replaces} - narrowing - unlinked
    kept = outcome != "abandoned"
    found = []
    for i, (d, confirmed) in enumerate(approved):
        widened = d.scope == "project" and d.replaces in unlinked
        note = f"From Change {c.slug} ({outcome})."
        note += f" It replaces {d.replaces}, a decision for this Change alone in an earlier version." if widened else ""
        note += f"\n\n{d.reason.strip()}" if d.reason.strip() else ""  # an autonomous choice's reasons (TD-41)
        fields = _said(d.answer, d.origin, confirmed or at, note)
        fields |= _placed(project, stem, lasting=d.scope == "project", kept=kept)
        if d.id and d.id not in final:  # approved once, then replaced or dropped by a later approval
            fields["state"] = State.REPLACED if kept and d.id in successors else State.WITHDRAWN
        link = LinkType.RELATED_TO if d.replaces in narrowing and d.scope != "project" else LinkType.REPLACES
        fields |= {
            "id": d.id or new_id(at, seed=f"{project}\n{stem}\nbrief\n{i}\n{d.question}"),
            "title": _short(d.question),
            "topic": brief.title,
            "origin": d.origin,
            "actor": "owner" if d.origin == "decided" else "shaper",
            "source": source,
            "links": [{"type": link, "target": d.replaces}] if d.replaces and not widened else [],
            "created_at": at,
        }
        found.append(fields)
    return found


def _changed(project: str, c: Change, stem: str, outcome: str) -> list[dict[str, Any]]:
    """The decisions recorded on the Change itself, such as "Not a UI change" or a clarification; each for it alone."""
    title = (c.brief.approved[-1] if c.brief.approved else c.brief).title
    found = []
    for i, d in enumerate(c.decisions):
        fields = _said(d.text, d.origin, d.at, f"From Change {c.slug} ({outcome}).")
        fields |= _placed(project, stem, lasting=False, kept=outcome != "abandoned")
        fields |= {
            "id": d.id or new_id(d.at, seed=f"{project}\n{stem}\nchange\n{i}\n{d.text}"),
            "title": _short(d.title or d.text),
            "topic": title,
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


def _said(text: str, origin: str, at: datetime, note: str) -> dict[str, Any]:
    """Statement and rationale; a longer text keeps its whole wording in the rationale.

    A `decided` one was confirmed by the owner at *at* (the brief's approval, or the Change-level answer); his words
    are never stored (TD-449).
    """
    text = text.strip()
    long = len(text) > STATEMENT_LIMIT
    statement = text[: STATEMENT_LIMIT - 1].rstrip() + "\u2026" if long else text
    return {"statement": statement, "rationale": f"{note}\n\n{WHOLE}{text}" if long else note,
            "read_back": at.date().isoformat() if origin == "decided" else "none"}  # fmt: skip


def _short(text: str) -> str:
    text = " ".join(text.split())
    return text if len(text) <= TITLE else text[: TITLE - 1].rstrip() + "\u2026"
