"""The impact of a change of mind with built effect (TD-428; decision system §9, slice 5b part 2).

For a decision that replaced another, or was withdrawn, each project the old rule reached is `confirmed` (merge
history shows work built under it: a merged finished-Change record whose brief made it or whose baseline pinned it,
or a Change in the project's store whose baseline pinned it) or `unknown`, with why: decisions carry no path
selectors (TD-460), so code and tests alone cannot rule a project out, and records miss chat-built code. A Global rule
reaches every project the host knows and OwlBear's own folder; a project whose repository the host cannot read stays
unknown. Nothing here writes.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Any, Literal

from owlbear_decisions import LinkType, Scope, State
from owlbear_delivery_next.state_store import decision_actions, decision_store
from owlbear_delivery_next.state_store.decision_actions import EFFECT, EFFECTS, Refused
from owlbear_delivery_next.state_store.decision_archive import CHANGES
from owlbear_delivery_next.state_store.store import StoreError

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence
    from pathlib import Path

    from owlbear_decisions import Decision
    from owlbear_delivery_next.local_system.data_repo import DataRepo
    from owlbear_delivery_next.state_store.store import Store

type Status = Literal["confirmed", "unaffected", "unknown"]
OWLBEAR = "owlbear"  # OwlBear's own folder in owlbear-data (TD-435)
SHOWN = 50  # evidence paths listed per project; the rest are counted
WHOLE = "no Change recorded work under it, and code and tests cannot tell"
ACCEPTED = "the Decisions page: existing code accepted"  # the source of the owner's grandfathering decision
DIVERGENCE = {
    "forbids": "The new rule forbids existing behaviour: affected work, publication and merge pause until compliance "
    "is settled (a running Change it applies to stops at its next step and asks); keeping existing code is the "
    "owner's choice per project.",
    "unknown": "Not said whether the new rule forbids existing behaviour, so it is treated as forbidding it: affected "
    "work pauses until compliance is settled.",
    "wording": "Wording only: existing behaviour stays compliant, so no fixes are scheduled.",
    "withdrawn": "Withdrawn without a successor: no rule replaces it, so existing code needs no fix for it.",
}


@dataclass(frozen=True)
class Place:
    """A project the host knows: its data folder, its repository and store when it can read them, else why not."""

    name: str
    repo: Path | None = None
    store: Store | None = None
    why: str = ""


@dataclass(frozen=True)
class Impact:
    """One project's verdict, the Changes, files and incomplete records behind it, and the owner's acceptance."""

    project: str
    status: Status
    why: str
    changes: tuple[dict[str, str], ...] = ()
    paths: tuple[str, ...] = ()
    accepted: str = ""  # the id of the decision keeping its existing code
    incomplete: tuple[str, ...] = ()  # the finished-Change records that cannot rule the old rule out


@dataclass(frozen=True)
class Report:
    """The old rule, the new one (None: withdrawn), the owner's mark on the change and each project's impact."""

    old: Decision
    new: Decision | None
    effect: str  # forbids, wording, unknown or withdrawn
    projects: tuple[Impact, ...]


def _listed(record: dict[str, Any]) -> list[Any] | None:
    listed = record.get("decisions_applied")
    if not isinstance(listed, list | None):
        raise TypeError(listed)
    return listed


def pinning(store: Store, decision_id: str) -> list[dict[str, Any]]:
    """The Changes of *store* whose decision baseline pins *decision_id*, and whether it applied to them."""
    found = []
    for slug in store.slugs():
        try:
            c = store.read(slug)
        except StoreError:
            continue
        pin = c.decisions_baseline
        if pin and decision_id in pin.revisions:
            found.append({
                "slug": slug, "handle": c.handle, "title": c.brief.title, "step": str(c.step.kind),
                "applies": decision_id in pin.said, "revision": pin.revisions[decision_id],
            })  # fmt: skip
    return found


def built(root: Path, project: str, old: Decision) -> tuple[list[dict[str, str]], list[str]]:
    """The merged records of *project* that made or applied *old*, and the records that cannot rule it out.

    Those are unreadable records and merged ones that do not list the decisions they applied (older Changes).
    """
    found, incomplete = [], []
    for path in sorted((root / project / CHANGES).glob("*.json")):
        try:
            record = json.loads(path.read_text())
            brief = record.get("brief") or {}
            listed = _listed(record)
            made = {d.get("id") for d in brief.get("decisions", [])} | set(listed or [])
            merged, pr = record.get("outcome") == "merged", (record.get("pr") or {}).get("url") or ""
            slug, title = str(record.get("slug", path.stem)), str(brief.get("title", ""))
        except (OSError, ValueError, AttributeError, TypeError) as exc:
            incomplete.append(f"{path.name}: cannot be read ({type(exc).__name__})")
            continue
        if merged and (old.id in made or path.stem == old.change):
            found.append({"slug": slug, "title": title, "pr": str(pr), "from": "merged"})
        elif merged and listed is None:
            incomplete.append(f"{path.name}: merged, but records no decisions it applied")
    return found, incomplete


def applied(store: Store | None, decision_id: str) -> list[dict[str, str]]:
    """The Changes in *store* whose baseline applied the decision: built, or being built, under it."""
    if store is None:
        return []
    return [
        {"slug": c["slug"], "title": c["title"], "pr": "", "from": f"pinned, at {c['step']}"}
        for c in pinning(store, decision_id)
        if c["applies"]
    ]


def classify(changes: Sequence[dict[str, str]], unreadable: str = "") -> tuple[Status, str]:
    """One project's verdict on the old rule and why: confirmed by the Changes that built under it, else unknown."""
    if unreadable:
        return "unknown", unreadable
    if changes:
        return "confirmed", f"{len(changes)} Change(s) built or are building work under the old rule"
    return "unknown", WHOLE


def _impact(root: Path, place: Place, old: Decision, accepted: dict[str, str]) -> Impact:
    merged, incomplete = built(root, place.name, old)
    changes = [*merged, *applied(place.store, old.id)]
    unreadable = place.why or ("" if place.repo else f"{place.name}'s repository is not served by this host")
    status, why = classify(changes, unreadable)
    return Impact(place.name, status, why, tuple(changes), (), accepted.get(place.name, ""), tuple(incomplete))


def _reached(root: Path, old: Decision, places: Sequence[Place]) -> list[Place]:
    """The projects *old* reached: its own, or for a Global rule every known one and OwlBear's folder."""
    by_name = {p.name: p for p in places if p.name}
    if old.scope is Scope.GLOBAL:
        names = [*by_name, *([OWLBEAR] if (root / OWLBEAR).is_dir() and OWLBEAR not in by_name else [])]
    else:
        names = [old.project]
    absent = "is not a project this host serves"
    return [by_name.get(n) or Place(n, why=f"{'OwlBear' if n == OWLBEAR else n}'s repository {absent}") for n in names]


def effect(new: Decision | None) -> str:
    """The owner's mark on the replacement in its rationale: forbids, wording or unknown; withdrawn without one."""
    if new is None:
        return "withdrawn"
    marks = [p.removeprefix(EFFECT) for p in new.rationale.split("\n\n") if p.startswith(EFFECT)]
    named = {said: key for key, said in EFFECTS.items()}
    return named.get(marks[-1], "unknown") if marks else "unknown"


def _accepted(decisions: Iterable[Decision], new: Decision | None) -> dict[str, str]:
    """The projects whose existing code the owner kept under *new*, with the decision recording it."""
    if new is None:
        return {}
    return {
        d.project: d.id
        for d in decisions
        if d.source == ACCEPTED and d.state is State.IN_FORCE and any(link.target == new.id for link in d.links)
    }


def report(shared: DataRepo | None, folder: str, decision_id: str, places: Sequence[Place]) -> Report:
    """The impact of *decision_id* (in *folder*'s view): the rule it replaced, or itself when withdrawn."""
    view = decision_store.load(shared, folder)
    if shared is None or (entry := view.snapshot.get(decision_id)) is None:
        msg = f"there is no decision {decision_id} in this view"
        raise Refused(msg, 404)
    chosen, every = entry.decision, decision_actions.every(shared)
    target = next((link.target for link in chosen.links if link.type is LinkType.REPLACES), "")
    if target:
        old, new = every.get(target), chosen
        if old is None:
            msg = f"{target}, which {chosen.id} replaces, cannot be found"
            raise Refused(msg, 404)
    elif chosen.state is State.WITHDRAWN:
        old, new = chosen, None
    else:
        msg = f"{chosen.id} replaced no decision and is not withdrawn: it has no impact report"
        raise Refused(msg, 422)
    accepted = _accepted(every.values(), new)
    found = tuple(_impact(shared.root, p, old, accepted) for p in _reached(shared.root, old, places))
    return Report(old, new, effect(new), found)


def due(report: Report) -> list[Impact]:
    """The projects whose code may still follow the old rule: confirmed or unknown, and not kept by the owner."""
    if report.new is None or report.effect == "wording":
        return []
    return [i for i in report.projects if i.status != "unaffected" and not i.accepted]


def is_test(path: str) -> bool:
    """A test file: under a ``tests`` folder, or named ``test_*``."""
    parts = PurePosixPath(path).parts
    return "tests" in parts[:-1] or parts[-1].startswith("test_")


def _rule(d: Decision) -> dict[str, Any]:
    out = d.model_dump(mode="json", include={"id", "title", "statement", "scope", "project", "state", "origin"})
    return out | {"revision": d.revision}


def _project(i: Impact) -> dict[str, Any]:
    tests = [p for p in i.paths if is_test(p)]
    return {
        "project": i.project, "status": i.status, "why": i.why, "changes": list(i.changes), "accepted": i.accepted,
        "paths": list(i.paths[:SHOWN]), "more": max(0, len(i.paths) - SHOWN),
        "tests": tests[:SHOWN], "more_tests": max(0, len(tests) - SHOWN),
        "incomplete": list(i.incomplete[:SHOWN]), "more_incomplete": max(0, len(i.incomplete) - SHOWN),
    }  # fmt: skip


def shown(report: Report) -> dict[str, Any]:
    """The report as the page shows it, evidence paths capped."""
    return {
        "old": _rule(report.old), "new": _rule(report.new) if report.new else None, "effect": report.effect,
        "divergence": DIVERGENCE[report.effect], "projects": [_project(i) for i in report.projects],
        "fixes": bool(due(report)) and report.new is not None and report.new.state is State.IN_FORCE,
    }  # fmt: skip
