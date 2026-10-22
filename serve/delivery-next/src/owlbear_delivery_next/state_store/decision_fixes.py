"""Fixes for a change of mind (TD-428; decision system §9, slice 5b part 2): grouped backlog entries, kept code.

Scheduling is the owner's click, apart from activating the new rule and from the runner gate that stops affected
work (§7). It makes ordinary backlog entries: one group per project whose impact is confirmed or unknown, split by
top-level folder when its matching files are many and spread (at most five groups per project). A group's title holds
its identity (decision, project, area); a checklist longer than one entry's text takes several entries, `(part k of
n)`, so every item stays listed, up to PARTS. Each names the old and new decisions' exact revisions as evidence and
lists its Changes and files as a checklist, so partial coverage is ticked off; a Change ticks only what it verified:
its cleanup ticks the file items its merged pull request changed, or completes an entry that names no paths, which
no file can cover (`verified`). Scheduling again reconciles the same
entries: ticked items stay ticked, items no longer found stay listed, new ones are added unticked, and a project's
grouping stays as first scheduled (see `_route`). A wording-only change schedules
nothing. Keeping a project's existing code is the owner's `decided` project decision that refines the new rule (an
exception to a Global one): a durable record in the data repository that agents read too, saved only while the new
rule is still at the revision the report showed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from owlbear_decisions import Decision, Link, LinkType, Origin, Scope, State, new_id
from owlbear_decisions.models import STATEMENT_LIMIT
from owlbear_delivery_next.state_store import decision_impact, decision_store
from owlbear_delivery_next.state_store.backlog import EVIDENCE, Backlog, named
from owlbear_delivery_next.state_store.decision_actions import Refused
from owlbear_delivery_next.state_store.decision_impact import ACCEPTED, DIVERGENCE

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Sequence

    from owlbear_delivery_next.local_system.data_repo import DataRepo
    from owlbear_delivery_next.state_store.backlog import Entry
    from owlbear_delivery_next.state_store.decision_impact import Impact, Report
    from owlbear_delivery_next.state_store.decision_store import Receipt

SPLIT = 20  # matching files above which a project's entry splits by top-level folder
GROUPS = 5  # groups per project at most
PARTS = 20  # entries one group's checklist takes at most
TEXT = 3700  # room for the checklist under the backlog's 4000-character text, and for a "Verified by" line
TITLE = 200
LABEL = 40  # characters of a folder's name in a title
PRS = 10  # pull requests kept as evidence
OTHER = "other folders"
CHECK = re.compile(r"^- \[([ xX])\] (.+)$")
FIX = re.compile(r"^Apply decision \S+ in ")
WHOLE = "Check {} against the new rule"  # a project's item when the report names no paths
PATHLESS = re.compile(r"^(Change \S+|Check .+ against the new rule)")
LONGEST = 4000  # an entry's text
type Line = tuple[str, str, bool]  # an item's key, its text, and whether it is ticked


@dataclass(frozen=True)
class Part:
    """One entry of a fix group: its title, text head and checklist, and the entry holding it (None: a new one)."""

    project: str
    title: str
    head: str
    lines: tuple[Line, ...]
    entry: Entry | None
    added: int  # items this scheduling adds


def _current(report: Report, revision: str) -> Decision:
    """The new rule, unchanged since the page read it and in force."""
    new = report.new
    if new is None:
        msg = f"{report.old.id} was withdrawn without a successor: there is no new rule to apply"
        raise Refused(msg, 422)
    if new.revision != revision:
        msg = f"{new.id} changed since it was read (now {new.revision[:12]}); reload and decide again"
        raise Refused(msg)
    if new.state is not State.IN_FORCE:
        msg = f"{new.id} is {new.state}: activate it first; fixes follow a rule in force"
        raise Refused(msg)
    return new


def _short(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "\u2026"


def _area(path: str) -> str:
    return _short(f"{path.split('/', 1)[0]}/", LABEL) if "/" in path else "top-level files"


def areas(paths: Sequence[str]) -> list[tuple[str, list[str]]]:
    """The paths in groups one Change can take: all together, or by top-level folder when many and spread."""
    if len(paths) <= SPLIT:
        return [("", list(paths))]
    by: dict[str, list[str]] = {}
    for p in paths:
        by.setdefault(_area(p), []).append(p)
    if len(by) < 2:  # noqa: PLR2004 - one folder needs no split
        return [("", list(paths))]
    ranked = sorted(by.items(), key=lambda item: (-len(item[1]), item[0]))
    if len(ranked) > GROUPS:
        rest = [p for _, group in ranked[GROUPS - 1 :] for p in group]
        ranked = [*ranked[: GROUPS - 1], (OTHER, rest)]
    return ranked


def _item(change: dict[str, str]) -> str:
    said = f"Change {change['slug']}" + (f": {change['title']}" if change["title"] else "")
    return said + (f" ({change['pr']})" if change["pr"] else f" ({change['from']})")


def _key(item: str) -> str:
    """What makes two checklist items one: a Change by its slug (its PR or step changes), a file by its path."""
    return " ".join(item.split(" ", 2)[:2]) if item.startswith("Change ") else item


def checklist(text: str) -> list[Line]:
    """The checklist items of a text, ticked or not."""
    return [(_key(m[2]), m[2], m[1] != " ") for line in text.splitlines() if (m := CHECK.match(line))]


def _render(head: str, lines: Sequence[Line]) -> str:
    return "\n".join([head, *(f"- [{'x' if ticked else ' '}] {item}" for _, item, ticked in lines)])


def _head(report: Report, new: Decision, impact: Impact, area: str) -> str:
    old = report.old
    return "\n".join([
        f"The rule changed: {new.title}.", "",
        f"Old rule \u201c{old.title}\u201d: {old.statement}",
        f"New rule \u201c{new.title}\u201d: {new.statement}", "", DIVERGENCE[report.effect], "",
        f"Impact in {impact.project}{f' ({area})' if area else ''}: {impact.status}: {impact.why}", "",
        "Tick each item once a Change has verified that it follows the new rule; a Change ticks only what it verified:",
    ])  # fmt: skip


def _title(new: Decision, project: str, area: str, part: int, parts: int) -> str:
    """The fix group's identity (decision, project, area) first, then its part, then the rule's title."""
    lead = f"Apply decision {new.id} in {project}{f' ({area})' if area else ''}"
    lead += f" (part {part} of {parts}): " if parts > 1 else ": "
    return lead + _short(new.title, TITLE - len(lead))


def _existing(entries: Iterable[Entry], new: Decision, project: str) -> dict[str, list[Entry]]:
    """*project*'s fix entries for *new* by area ("" for the whole project's), oldest group first, in part order."""
    pattern = re.compile(
        rf"^Apply decision {re.escape(new.id)} in {re.escape(project)}"
        r"(?: \((?!part \d+ of \d+\))(?P<area>.+?)\))?(?: \(part (?P<part>\d+) of \d+\))?: "
    )
    found: dict[str, list[tuple[int, int, Entry]]] = {}
    for e in entries:
        if e.source == "owner" and named(e) == {project} and (m := pattern.match(e.title)):
            found.setdefault(m["area"] or "", []).append((int(m["part"] or 1), int(e.id), e))
    ranked = sorted(found.items(), key=lambda item: min(i for _, i, _ in item[1]))
    return {area: [e for *_, e in sorted(group, key=lambda t: t[:2])] for area, group in ranked}


def _route(impact: Impact, have: Sequence[str]) -> list[tuple[str, list[str]]]:
    """The items by area; once scheduled, a project's grouping stays.

    A whole-project entry takes every new item; else an item joins its folder's entry, else "other folders", else a
    new entry for its folder. Changes join the first area.
    """
    if not have:
        found = areas(impact.paths)
    elif "" in have:
        found = [("", list(impact.paths))]
    else:
        by: dict[str, list[str]] = {a: [] for a in have}
        for p in impact.paths:
            area = _area(p)
            by.setdefault(area if area in by or OTHER not in by else OTHER, []).append(p)
        found = list(by.items())
    (first, paths), changes = found[0], [_item(c) for c in impact.changes]
    if not changes and not paths and len(found) == 1:
        paths = [WHOLE.format(impact.project)]
    return [(first, [*changes, *paths]), *found[1:]]


def _checklists(held: Sequence[Entry], items: Sequence[str], known: set[str], room: int) -> list[list[Line]]:
    """The group's checklist by entry: each held one's items as they are, new items appended unticked, all fitting."""
    fresh = {_key(i): i for i in items}
    parts = [[(k, fresh.get(k, i), ticked) for k, i, ticked in checklist(e.text)] for e in held]
    for k, item in fresh.items():
        if k in known:
            continue
        if (size := len(item) + 7) > room:  # "- [ ] " and the newline
            msg = f"the checklist item {item[:80]!r} is too long for a backlog entry"
            raise Refused(msg, 422)
        if not parts or sum(len(i) + 7 for _, i, _ in parts[-1]) + size > room:
            parts.append([])
        parts[-1].append((k, item, False))
    return parts


def _plan(report: Report, new: Decision, impact: Impact, mine: dict[str, list[Entry]]) -> list[Part]:
    """The entries of one project, every item listed once across them; refused beyond PARTS for one group."""
    known = {k for held in mine.values() for e in held for k, _, _ in checklist(e.text)}
    out = []
    for area, items in _route(impact, list(mine)):
        held, head = mine.get(area, []), _head(report, new, impact, area)
        lists = _checklists(held, items, known, TEXT - len(head) - 1)
        if len(lists) > PARTS:
            where = impact.project + (f" ({area})" if area else "")
            msg = (f"{where}: its checklist needs {len(lists)} backlog entries, more than {PARTS}; narrow the rule's "
                   "paths or keep the existing code")  # fmt: skip
            raise Refused(msg, 422)
        for n, lines in enumerate(lists, 1):
            entry = held[n - 1] if n <= len(held) else None
            added = sum(k not in known for k, _, _ in lines)
            out.append(Part(impact.project, _title(new, impact.project, area, n, len(lists)), head, tuple(lines),
                            entry, added))  # fmt: skip
    return out


def _merge(part: Part, evidence: Sequence[str]) -> Callable[[Entry, str], dict[str, Any]]:
    """The part's fields over the entry as it is now: ticks made meanwhile, here or on GitHub, and added items kept."""

    def fields(entry: Entry, body: str) -> dict[str, Any]:
        held = checklist(entry.text)
        now, planned = {k for k, _, _ in held}, {k for k, _, _ in part.lines}
        ticked = {k for k, _, t in [*held, *checklist(body)] if t}
        lines = [(k, i, k in ticked or (t and k not in now)) for k, i, t in part.lines]
        lines += [line for line in held if line[0] not in planned]
        out = {"title": part.title, "text": _render(part.head, lines), "projects": [part.project],
               "evidence": list(dict.fromkeys([*entry.evidence, *evidence]))[-EVIDENCE:]}  # fmt: skip
        return out | ({"status": "open"} if planned - now and entry.status == "done" else {})

    return fields


def _put(backlog: Backlog, part: Part, evidence: list[str]) -> dict[str, Any]:
    entry, fresh = part.entry, False
    if entry is None:  # a match the listing did not show yet is found and counted up here, then reconciled
        entry, fresh = backlog.add(part.title, _render(part.head, part.lines), "owner", evidence)
    entry = backlog.revise(entry.id, _merge(part, evidence))
    return {"project": part.project, "id": entry.id, "title": entry.title, "new": fresh, "added": part.added}


def schedule(
    shared: DataRepo, report: Report, revision: str, clock: Callable[[], datetime] | None = None
) -> list[dict[str, Any]]:
    """The owner's fixes: the backlog entries made or reconciled, per project the change may still affect.

    Every entry is planned before any is written, so a group too large for PARTS entries writes nothing.
    """
    new = _current(report, revision)
    if report.effect == "wording":
        msg = "a wording-only change schedules no fixes: existing behaviour stays compliant"
        raise Refused(msg, 422)
    if not (due := decision_impact.due(report)):
        msg = "nothing to fix: every project is unaffected or keeps its existing code"
        raise Refused(msg)
    listed = list(Backlog(shared, "", clock).read(fresh=True)[0].values())
    plans = [(i, _plan(report, new, i, _existing(listed, new, i.project))) for i in due]
    made = []
    for impact, parts in plans:
        backlog, old = Backlog(shared, impact.project, clock), report.old
        evidence = [f"decision {old.id} revision {old.revision}", f"decision {new.id} revision {new.revision}"]
        evidence += [c["pr"] for c in impact.changes if c["pr"]][:PRS]
        made += [_put(backlog, part, evidence) for part in parts]
    return made


def _covered(item: str, files: frozenset[str]) -> bool:
    """Whether a merged file is the item's path or lies under the folder it names; a Change item never is."""
    if PATHLESS.match(item):
        return False
    path = item.rstrip("/")
    return path in files or any(f.startswith(f"{path}/") for f in files)


def _verify(
    files: frozenset[str] | None, changes: set[str], project: str, said: tuple[str, str]
) -> Callable[[Entry, str], dict[str, Any]]:
    """Tick the items *files* cover over the entry as it is now, ticks made meanwhile kept; done when none is left.

    An entry that names no paths has nothing a merge's files can cover: the merged Change launched from it (*files*
    not None) completes it, said so without claiming any file. The entry is checked again under the lock: one
    reassigned to another Change meanwhile is left as it is.
    """
    change, pr = said

    def fields(entry: Entry, body: str) -> dict[str, Any]:
        if entry.status in {"done", "dropped"} or not _mine(entry, changes, project):
            return {}
        items = checklist(entry.text)
        whole = bool(files) and bool(items) and all(PATHLESS.match(i) for _, i, _ in items)
        owner = {k for k, _, t in checklist(body) if t}  # ticked on GitHub
        lines, covered = [], 0
        for line in entry.text.splitlines():
            m = CHECK.match(line)
            hit = bool(m) and (whole or _covered(m[2], files or frozenset()))
            if m and (hit or (m[1] == " " and _key(m[2]) in owner)):
                covered += hit
                line = f"- [x] {m[2]}"  # noqa: PLW2901 - the ticked line replaces it
            lines.append(line)
        text = "\n".join(lines)
        by = f"Verified by Change {change}{f' ({pr})' if pr else ''}"
        said = f"{by}, merged: its checklist names no files." if whole else f"{by}: {covered} item(s) ticked."
        if covered and said not in text and len(text) + len(said) + 2 <= LONGEST:
            text += f"\n\n{said}"
        left = any(not t for _, _, t in checklist(text))
        refs = [*entry.evidence, pr] if covered and pr and pr not in entry.evidence else entry.evidence
        return {"text": text, "status": "open" if left else "done", "evidence": refs[-EVIDENCE:]}

    return fields


def verified(backlog: Backlog, slug: str, clone: str | None, files: frozenset[str] | None, pr: str = "") -> list[Entry]:
    """Settle the project's fix entries that went into the finished Change *slug* of the clone *clone*.

    A merged Change ticks the items its merged *files* cover, never a Change item, and names itself and *pr* in the
    text, or completes an entry that names no paths; None (abandoned or unchanged) ticks nothing. Each entry is then
    done when nothing is left, else open again.
    """
    changes = {slug, f"{clone}/{slug}"} if clone else {slug}  # as `backlog_routes.named` stores it
    found, _ = backlog.read(fresh=True)
    mine = sorted((e.id for e in found.values() if _mine(e, changes, backlog.project)
                   and e.status not in {"done", "dropped"}), key=int)  # fmt: skip
    settle = _verify(files, changes, backlog.project, (slug, pr))
    return [backlog.revise(i, settle) for i in mine]


def _mine(entry: Entry, changes: set[str], project: str) -> bool:
    """*entry* is a decision fix of *project* that went into one of *changes*."""
    return entry.change in changes and bool(FIX.match(entry.title)) and project in named(entry)


def accept(shared: DataRepo, report: Report, project: str, revision: str, reason: str) -> Receipt:
    """The owner keeps *project*'s existing code as it is under the new rule; new work follows it."""
    new = _current(report, revision)
    if not (why := reason.strip()):
        msg = "say why: keeping existing code needs a reason, recorded with it"
        raise Refused(msg, 422)
    impact = next((i for i in report.projects if i.project == project), None)
    if impact is None:
        msg = f"{project} is not among the projects {new.id} reaches"
        raise Refused(msg, 404)
    if impact.accepted or impact.status == "unaffected" or new.scope is Scope.CHANGE:
        said = f"keeps its existing code already ({impact.accepted})" if impact.accepted else "has none to keep"
        msg = f"{project} {said} under {new.id}"
        raise Refused(msg)
    now = datetime.now(UTC)
    kept = Decision(
        id=new_id(), title=_short(f"{project} keeps existing code under: {new.title}", TITLE), topic=new.topic,
        statement=_short(f"Code in {project} built before \u201c{new.title}\u201d stays as it is; new work follows it.",
                         STATEMENT_LIMIT),
        rationale=f"Why: {why}\n\nImpact when kept: {impact.status}: {impact.why}",
        scope=Scope.PROJECT, project=project, origin=Origin.DECIDED, actor="owner", source=ACCEPTED,
        read_back=now.date().isoformat(), state=State.IN_FORCE, created_at=now,
        links=(Link(type=LinkType.EXCEPTION_TO if new.scope is Scope.GLOBAL else LinkType.REFINES, target=new.id),),
    )  # fmt: skip
    said = f"decisions: accept-existing {new.id} ({project})"
    # the rule rides along unchanged: under the lock, after catching up, a rule replaced or withdrawn meanwhile refuses
    rule, done = decision_store.save_all(shared, [(new, new.revision), (kept, None)], message=said)
    if not rule.saved:
        msg = f"not kept: {new.id} is no longer the rule in force the report showed ({rule.notice}); reload it"
        raise Refused(msg)
    return done
