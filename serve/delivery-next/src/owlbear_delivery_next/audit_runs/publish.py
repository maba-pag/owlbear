"""Per-finding publication custody, including lost responses and lagging GitHub listings."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.audit_runs import record
from owlbear_delivery_next.github.owlbear_issues import OwlbearIssues
from owlbear_delivery_next.state_store import backlog

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_delivery_next.state_store.store import Store

WAIT = "GitHub may still be listing the last entry; press again in two minutes"


def findings(store: Store, state: dict[str, Any], save: Callable[[], None]) -> None:
    """Persist intent before every issue write and each receipt before attempting the next finding."""
    destination = state["destination"]
    external = OwlbearIssues(destination, store.root) if destination else None
    book = None if external else backlog.Backlog.of(store)
    for index, finding in enumerate(state["findings"], 1):
        if finding.get("number") is not None:
            continue
        identity = f"audit:{state['id']}:{index}"
        pending = finding.get("pending")
        previous = datetime.fromisoformat(pending) if pending else None
        found = external.listed(identity) if external else _listed(book, identity)
        if found is not None and external:
            finding.update(number=found.number, url=found.url, pending=None)
            save()
            continue
        if found is None:
            if previous and (datetime.now(UTC) - previous).total_seconds() < backlog.RECENT_SECONDS:
                raise RuntimeError(WAIT)
            finding["pending"] = record.now()
            save()
        text = _text(state, finding)
        labels = (f"type:{finding['type']}", f"severity:{finding['severity']}")
        if external:
            text += f"\n\n<!-- {identity} -->\n"
            if previous:
                issue = external.retry_audit(
                    finding["title"], text, marker=identity, labels=labels, pending_since=previous
                )
            else:
                issue = external.create(finding["title"], text, marker=identity, labels=labels)
            number, url = issue.number, issue.url
        else:
            if book is None:
                msg = "the audit has no Backlog publication client"
                raise RuntimeError(msg)
            entry, _ = book.add(finding["title"], text, source="audit", evidence=[identity], labels=labels)
            number, url = int(entry.id), f"https://github.com/{book.repository}/issues/{entry.id}"
        finding.update(number=number, url=url, pending=None)
        save()


def _listed(book: backlog.Backlog | None, identity: str) -> tuple[int, str] | None:
    if book is None:
        msg = "the audit has no Backlog publication client"
        raise RuntimeError(msg)
    entries, invalid = book.read(fresh=True)
    if invalid:
        msg = "cannot establish publication custody; unreadable Backlog entries: " + ", ".join(invalid)
        raise ValueError(msg)
    for entry in entries.values():
        if identity in entry.evidence:
            return int(entry.id), f"https://github.com/{book.repository}/issues/{entry.id}"
    return None


def _text(state: dict[str, Any], finding: dict[str, Any]) -> str:
    return (
        f"Type: {finding['type']} · Severity: {finding['severity']}\n\n"
        f"Audit: {state['branch']} at {state['commit']}\n\n"
        f"Where: {finding['where']}\n\nEvidence:\n{finding['evidence']}\n\n"
        f"Recommendation:\n{finding['recommendation']}"
    )
