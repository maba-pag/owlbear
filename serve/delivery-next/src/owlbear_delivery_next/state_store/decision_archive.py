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

import time
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from owlbear_decisions import DecisionError, LinkType, Scope, State, check_write, decision_path, new_id, read
from owlbear_decisions.models import Decision
from owlbear_decisions.snapshot import read_repo
from owlbear_decisions.storage import serialize
from owlbear_decisions.validate import Entry, Layer, check
from owlbear_delivery_next.change_contracts import decision_wording
from owlbear_delivery_next.change_contracts.decision_wording import WHOLE, whole  # noqa: F401 - existing consumer API
from owlbear_delivery_next.local_system.data_repo import SAVE_SECONDS, DataRepo
from owlbear_delivery_next.state_store import decision_store, decision_sync, decision_transaction

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import datetime
    from pathlib import Path

    from owlbear_delivery_next.change_contracts.models import BriefDecision, Change
    from owlbear_delivery_next.state_store.decision_store import Placed

CHANGES = "changes"
TITLE = 120
APPROVED = "approved"  # the brief's approval publishes its project decisions (TD-453)
_STATES = {  # (lasting, the Change's work stays) -> state
    (False, True): State.SPENT,
    (False, False): State.WITHDRAWN,
    (True, True): State.IN_FORCE,
    (True, False): State.DRAFT,
}


def plan(root: Path, project: str, c: Change, stem: str, outcome: str) -> tuple[list[Placed], list[str]]:
    """The finished *c*'s decisions, built and checked, and what kept any from being written; nothing is written."""
    planned, problems = _planned(root, project, c, stem, outcome)
    return planned, problems or _graph(root, project, c, planned)


def _selected(planned: list[Placed]) -> list[Placed]:
    """The planned decisions whose files change: the only ones journalled, written and published."""
    return [(d, layer, rev) for d, layer, rev in planned if rev != d.revision]


def batch_files(planned: list[Placed]) -> list[tuple[Path, bytes]]:
    """The files `write_plan` writes, with their bytes after: what a journal records before the first of them."""
    return [(decision_path(d, layer), serialize(d).encode("utf-8")) for d, layer, _ in _selected(planned)]


def write_plan(
    planned: list[Placed],
    problems: list[str],
    slug: str,
    fence: Callable[[], None] | None = None,
    root: Path | None = None,
) -> tuple[list[Path], list[str]]:
    """Write the planned decisions unless *problems* keep them all out; the files to publish, and what kept them out.

    Only the files that change are written and returned, the same ones `batch_files` journals: a decision left as it
    is was never journalled, so it is never published either, whatever its file holds by then. *fence* is the
    transaction's proof each write runs before its folder is made and immediately before its rename; *root*, the
    checkout, bounds the folders each rename checks are still plain (`decision_store.write_batch`).
    """
    writes = _selected(planned)
    if not problems:
        try:
            refused = decision_store.write_batch(writes, fence, root)
        except OSError as exc:
            refused = {"files": f"cannot be written: {exc}"}
        problems = [f"decision {key} of {slug}: {' '.join(why.split())}"[:240] for key, why in refused.items()]
    if problems:
        return [], [f"no decision of {slug} was archived", *problems]
    return [decision_path(decision, layer) for decision, layer, _ in writes], []


def archive(root: Path, project: str, c: Change, stem: str, outcome: str) -> tuple[list[Path], list[str]]:
    """Write and publish the decisions of the finished *c*; the files published, and what kept them from being written.

    The writes and their publication are one journaled batch: readers stay blocked from the first write until the
    commit is proven, and a publication whose outcome is unknown stays interrupted for the owner. Production writes go
    through `change_record`, which runs the same transaction around its record; nothing nests here.
    """
    shared = DataRepo(root)
    with shared.locked():
        decision_transaction.guard(shared)
        head, behind = decision_sync.prepare(shared, time.monotonic() + SAVE_SECONDS)
        if not head:
            return [], [behind]
        planned, problems = plan(root, project, c, stem, outcome)
        files = batch_files(planned) if not problems else []
        if not files:
            written, left = write_plan(planned, problems, c.slug)
            return written, [n for n in (*left, behind) if n]
        done: dict[str, tuple[list[Path], list[str]]] = {}

        def step(head: str, fence: Callable[[], None]) -> decision_transaction.Step:
            written, left = write_plan(planned, problems, c.slug, fence, root)
            done["result"] = (written, left)
            if not written:
                return decision_transaction.Step("", refused=True)
            sent = decision_sync.publish(shared, written, f"archive {c.slug}", time.monotonic() + SAVE_SECONDS, head)
            return decision_transaction.Step(
                sent.notice, unknown=sent.stale or sent.ambiguous, refused=sent.uncommitted
            )

        notice = decision_transaction.transaction(shared, project, f"archive {c.slug}", files, step, head)
    written, left = done["result"]
    return written, [n for n in (*left, notice, behind) if n]


def lasting(project: str, c: Change, stem: str, *, root: Path | None = None) -> list[Decision]:
    """The approved brief's project decisions as its approval puts them in force, retired ones by a later version.

    Current invalid ID-bearing rules refuse the whole approval. Old malformed rows omitted by the earlier software
    do not prevent correction, but published predecessors still retire from their authoritative files.
    """
    c, legacy = _history(root, project, c, stem)
    ids = {d.id for d, _ in _approved(c) if d.id}
    found = []
    for fields in _brief(project, c, stem, APPROVED):
        if fields["scope"] is Scope.PROJECT and fields["id"] in ids:
            try:
                found.append(_as_decision(fields, legacy))
            except ValidationError as exc:
                msg = f"decision {fields['id']} of {c.slug} cannot be published: {' '.join(str(exc).split())}"[:240]
                raise DecisionError(msg) from exc
    return found


def _planned(root: Path, project: str, c: Change, stem: str, outcome: str) -> tuple[list[Placed], list[str]]:
    """Each decision of *c* with its layer and its file's revision, and why any cannot be written over its file."""
    planned: list[Placed] = []
    problems: list[str] = []
    published = {p.id for p in c.decisions_published if p.saved}
    try:
        source, legacy = _history(root, project, c, stem)
    except (decision_store.DecisionsUnavailable, DecisionError, ValidationError, OSError) as exc:
        return [], [f"decision history of {c.slug}: {' '.join(str(exc).split())}"[:240]]
    for fields in [*_brief(project, source, stem, outcome), *_changed(project, c, stem, outcome)]:
        if fields["scope"] is Scope.PROJECT and fields["id"] in published:
            continue
        try:
            decision = _as_decision(fields, legacy)
            layer = root / project / CHANGES / stem if decision.scope is Scope.CHANGE else root / project
            path = decision_path(decision, layer)
            current = read(path) if path.exists() or path.is_symlink() else None
            if current is None or current.revision != decision.revision:
                check_write(current, decision, current.revision if current else None)
            planned.append((decision, layer, current.revision if current else None))
        except (DecisionError, ValidationError, OSError) as exc:
            problems.append(f"decision {fields['id']} of {c.slug}: {' '.join(str(exc).split())}"[:240])
    return planned, problems


def _as_decision(fields: dict[str, Any], legacy: dict[str, Decision]) -> Decision:
    if current := legacy.get(fields["id"]):
        return current.model_copy(update={"state": fields["state"]})
    return Decision.model_validate(fields)


def _invalid_history(project: str, c: Change, stem: str) -> list[dict[str, Any]]:
    current = c.brief.approved[-1] if c.brief.approved else c.brief
    current_ids = {d.id for d in current.decisions}
    known = {d.id for d, _ in _approved(c) if d.id}
    invalid = []
    for fields in _brief(project, c, stem, APPROVED):
        if fields["scope"] is not Scope.PROJECT or fields["id"] not in known - current_ids:
            continue
        try:
            Decision.model_validate(fields)
        except ValidationError:
            invalid.append(fields)
    return invalid


def _history(root: Path | None, project: str, c: Change, stem: str) -> tuple[Change, dict[str, Decision]]:
    invalid = _invalid_history(project, c, stem)
    if not invalid or root is None or not project:
        return c, {}
    seen = decision_store.file_snapshot(DataRepo(root), project)
    saved = {p.id for p in c.decisions_published if p.saved}
    parents = {d.id: d.replaces for d, _ in _approved(c)}
    omitted: dict[str, str | None] = {}
    legacy: dict[str, Decision] = {}
    for fields in invalid:
        ident = fields["id"]
        matches = [e.decision for e in seen.entries if e.decision.id == ident]
        if len(matches) > 1:
            msg = f"historical decision {ident} has ambiguous authoritative files"
            raise decision_store.DecisionsUnavailable(msg, decision_store.READ)
        if matches:
            current = matches[0]
            if (current.id, current.scope, current.project) != (ident, Scope.PROJECT, project):
                msg = f"historical decision {ident} does not match its authoritative file"
                raise DecisionError(msg)
            legacy[ident] = current
        elif ident not in saved:
            omitted[ident] = parents[ident]
    return _without(c, omitted) if omitted else c, legacy


def _without(c: Change, omitted: dict[str, str | None]) -> Change:
    """Project authority without never-published historical rows; the stored approval history stays intact."""
    source = c.model_copy(deep=True)
    for brief in [source.brief, *source.brief.approved]:
        brief.decisions = [d for d in brief.decisions if d.id not in omitted]
        for decision in brief.decisions:
            seen: set[str] = set()
            while decision.replaces is not None and decision.replaces in omitted:
                if decision.replaces in seen:
                    msg = "the omitted historical decisions have a replacement cycle"
                    raise DecisionError(msg)
                seen.add(decision.replaces)
                decision.replaces = omitted[decision.replaces]
    return source


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
    source = f"{decision_wording.CHANGE}{c.slug}, brief v{brief.version} approved {at.isoformat(timespec='seconds')}"
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
            "source": f"{decision_wording.CHANGE}{c.slug}, {d.at.isoformat(timespec='seconds')}",
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
    return {"statement": decision_wording.short(text), "rationale": decision_wording.rationale(text, note),
            "read_back": at.date().isoformat() if origin == "decided" else "none"}  # fmt: skip


def _short(text: str) -> str:
    text = " ".join(text.split())
    return text if len(text) <= TITLE else text[: TITLE - 1].rstrip() + "\u2026"
