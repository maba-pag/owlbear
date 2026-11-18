"""Refused pinned copies published through the audits' per-finding custody."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import datetime
from typing import TYPE_CHECKING

from owlbear_quality import ledger

from owlbear_delivery_next.audit_runs import publish, record, suppression_items
from owlbear_delivery_next.state_store import backlog

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_delivery_next.state_store.store import Store


DETAIL_CHARS = 15_000  # at most 60,000 UTF-8 bytes, below GitHub's comment limit


def prepare(store: Store, state: dict) -> None:
    """Build findings from the complete ledger, including refusals from earlier runs and Changes."""
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for item in suppression_items.joined(store.root, state["inventory"]):
        row = item["judgment"]
        if row and row["verdict"] == "refused" and not row["backlog"]:
            groups[(item["directive"], suppression_items.place(item))].append(item)
    state["findings"], state["suppression_members"], state["suppression_details"] = [], [], []
    for (rule, place), items in sorted(groups.items()):
        key = hashlib.sha256(json.dumps([rule, place]).encode()).hexdigest()[:16]
        state["findings"].append(
            {
                "title": f"Review {rule[:80]} in {place[:60]} [{key}]",
                "type": "improvement",
                "severity": "low",
                "where": "Pinned inventory; full places in this entry's comments.",
                "evidence": f"{len(items)} refused copies. The directive, every place and the judge's reasons "
                "follow in this entry's comments.",
                "recommendation": "Fix the code, or accept the suppression on the Maintenance page.",
                "number": None,
                "url": "",
                "pending": None,
            }
        )
        state["suppression_members"].append(
            [{"identity": i["identity"], "index": i["judgment"]["index"]} for i in items]
        )
        detail = f"Directive: {rule}\nPlace: {place}\n\n" + "\n\n".join(
            f"{i['place']}: {i['judgment']['reason']}" for i in items
        )
        state["suppression_details"].append(
            [
                record.SummaryPart(body=detail[offset : offset + DETAIL_CHARS]).model_dump(mode="json")
                for offset in range(0, len(detail), DETAIL_CHARS)
            ]
        )


def findings(store: Store, state: dict, save: Callable[[], None]) -> None:
    """Keep issue and detail-comment custody before receipting every member in the ledger."""
    publish.findings(store, state, save, audit="suppressions")
    book = backlog.Backlog.of(store)
    for index, (finding, members, parts) in enumerate(
        zip(
            state["findings"],
            state["suppression_members"],
            state["suppression_details"],
            strict=True,
        ),
        1,
    ):
        for part_index, part in enumerate(parts, 1):
            if part["url"]:
                continue
            marker = f"audit:{state['id']}:{index}:part:{part_index}"
            previous = datetime.fromisoformat(part["pending"]) if part["pending"] else None
            part["pending"] = record.now()
            save()
            book.issues.private()
            part["url"] = book.issues.marked_comment(
                book.repository,
                finding["number"],
                part["body"] + f"\n\n<!-- {marker} -->\n",
                marker=marker,
                pending_since=previous,
            )
            part["pending"] = None
            save()
        ledger.published(store.root, members, finding["number"])


def links(store: Store, state: dict) -> list[dict]:
    """All pinned counting refusals' receipts, not only the latest run's new findings."""
    numbers = sorted(
        {
            int(i["judgment"]["backlog"])
            for i in suppression_items.joined(store.root, state.get("inventory", []))
            if i["judgment"] and i["judgment"]["backlog"]
        }
    )
    if not numbers:
        return []
    book = backlog.Backlog.of(store)
    return [{"number": n, "url": f"https://{book.issues.host}/{book.repository}/issues/{n}"} for n in numbers]
