"""Pinned suppression copies joined to counting, non-chat verdicts."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from owlbear_quality import ledger
from owlbear_quality.inspect import configured, inventory

from owlbear_delivery_next.change_flow import worktree

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


def joined(root: Path, items: list[dict]) -> list[dict]:
    """At most one counting verdict per pinned copy; chat advice never covers a review."""
    copies: dict[str, list[dict]] = defaultdict(list)
    for item in items:
        copies[item["identity"]].append(item)
    found, verdicts = [], ledger.current(root)
    for identity, places in copies.items():
        rows = [r for r in verdicts.get(identity, []) if not r["for"].startswith("chat:")]
        found.extend(item | {"judgment": rows[n] if n < len(rows) else None} for n, item in enumerate(places))
    return sorted(found, key=lambda i: (i["directive"], i["place"]))


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
    """Whole reasons remain visible; only equivalent lines share an owner action."""
    grouped: dict[tuple, list[dict]] = defaultdict(list)
    for item in joined(root, items):
        if row := item["judgment"]:
            grouped[(item["directive"], place(item), row["verdict"], row["reason"])].append(item)
    result = []
    for (directive, location, verdict, reason), copies in sorted(grouped.items()):
        members = [{"identity": i["identity"], "index": i["judgment"]["index"]} for i in copies]
        token = hashlib.sha256(json.dumps(members, sort_keys=True).encode()).hexdigest()
        result.append(
            {
                "id": token,
                "directive": directive,
                "place": location,
                "verdict": verdict,
                "reason": reason,
                "count": len(copies),
                "members": members,
            }
        )
    return result
