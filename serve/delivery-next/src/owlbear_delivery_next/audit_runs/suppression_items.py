"""Pinned suppression copies joined to counting verdicts."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from owlbear_quality import ledger
from owlbear_quality.inspect import configured, inventory

from owlbear_delivery_next.change_flow import worktree

FOR = "maintenance.review"  # a Change slug never holds a dot, so no Change's gate counts the review's verdicts

if TYPE_CHECKING:
    from pathlib import Path


def scan(root: Path, commands: tuple[tuple[str, ...], ...]) -> list[dict]:
    """Read tracked directives and the pinned tree's lint configuration."""
    paths = worktree.git(root, "ls-files", "-z").split("\0")
    items = [
        {"identity": d.identity, "place": f"{d.path}:{d.line}", "directive": d.directive, "code": d.code}
        for d in inventory(root, [p for p in paths if p])
    ]
    items.extend(
        {"identity": c.identity, "place": c.path, "directive": c.table or c.path, "code": c.content}
        for c in configured(root, commands)
    )
    return sorted(items, key=lambda i: (i["directive"], i["place"]))


def _matched(root: Path, items: list[dict]) -> tuple[list[dict], list[dict]]:
    """Each pinned copy takes the verdict given at its place, else the earliest left; the rest cover no copy."""
    copies: dict[str, list[dict]] = defaultdict(list)
    for item in items:
        copies[item["identity"]].append(item)
    found, spare, verdicts = [], [], ledger.current(root)
    for identity, places in copies.items():
        rows = list(verdicts.get(identity, []))
        taken = {}
        for item in places:
            if row := next((r for r in rows if r["place"] == item["place"]), None):
                rows.remove(row)
                taken[item["place"]] = row
        for item in places:
            row = taken.get(item["place"]) or (rows.pop(0) if rows else None)
            found.append(item | {"judgment": row})
        spare.extend({"identity": identity, "index": r["index"], "for": r["for"]} for r in rows)
    return sorted(found, key=lambda i: (i["directive"], i["place"])), spare


def joined(root: Path, items: list[dict]) -> list[dict]:
    """At most one counting verdict per pinned copy."""
    return _matched(root, items)[0]


def spare(root: Path, items: list[dict], identities: set[str]) -> list[dict]:
    """Counting verdicts of removed copies, which would otherwise take the place of one the owner changes."""
    return [m for m in _matched(root, items)[1] if m["identity"] in identities]


def counts(root: Path, items: list[dict]) -> dict[str, int]:
    """Counts always describe the pinned inventory, even after an interrupted batch."""
    rows = joined(root, items)
    accepted = sum(bool(r["judgment"] and r["judgment"]["verdict"] == "accepted") for r in rows)
    refused = sum(bool(r["judgment"] and r["judgment"]["verdict"] == "refused") for r in rows)
    return {"held": len(rows), "accepted": accepted, "refused": refused, "unjudged": len(rows) - accepted - refused}


def place(item: dict) -> str:
    """Package or top folder, distinguished by tests and source."""
    path = PurePosixPath(item["place"].split(":")[0])
    folders = path.parent.parts
    package = "/".join(folders[:2]) if folders and folders[0] == "serve" else folders[0] if folders else "."
    kind = "tests" if any(p in {"tests", "test"} or p.startswith("test_") for p in path.parts) else "source"
    return f"{package} ({kind})"


def groups(root: Path, items: list[dict]) -> list[dict]:
    """One owner action per rule, place, verdict and who ruled; each copy's whole reason stays with its place."""
    grouped: dict[tuple, list[dict]] = defaultdict(list)
    for item in joined(root, items):
        if row := item["judgment"]:
            by = "owner" if row["by"] == "owner" else "judge"
            grouped[(item["directive"], place(item), row["verdict"], by)].append(item)
    result = []
    for (directive, location, verdict, by), copies in sorted(grouped.items()):
        reasons = [i["judgment"]["reason"] for i in copies]
        members = [
            {"identity": i["identity"], "index": i["judgment"]["index"], "for": i["judgment"]["for"]} for i in copies
        ]
        token = hashlib.sha256(json.dumps(members, sort_keys=True).encode()).hexdigest()
        result.append(
            {
                "id": token,
                "directive": directive,
                "place": location,
                "verdict": verdict,
                "by": by,
                "reason": reasons[0] if len(set(reasons)) == 1 else "",
                "reasons": reasons,
                "count": len(copies),
                "places": [i["place"] for i in copies],
                "members": members,
            }
        )
    return result
