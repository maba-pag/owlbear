"""Per-finding publication custody, including lost responses and lagging GitHub listings."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, override

from owlbear_delivery_next.audit_runs import record, report_publish
from owlbear_delivery_next.github.owlbear_issues import Issue, OwlbearIssues
from owlbear_delivery_next.state_store import backlog

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from owlbear_delivery_next.state_store.store import Store

WAIT = "GitHub may still be listing the last entry; press again in two minutes"


def findings(store: Store, state: dict[str, Any], save: Callable[[], None], *, audit: str = "code") -> None:
    """Persist intent before every issue write and each receipt before attempting the next finding."""
    if state.get("verified") is True:
        sink = (
            _RepositorySink(OwlbearIssues(state["destination"], store.root))
            if state["destination"]
            else _BacklogSink(backlog.Backlog.of(store), state["summary_issue"])
        )
        report_publish.publish(state, sink, save, project=store.name, audit=audit)
        return
    _legacy(store, state, save)


class _RepositorySink(report_publish.Sink):
    def __init__(self, issues: OwlbearIssues) -> None:
        self.issues = issues

    @override
    def find(self, marker: str) -> Issue | None:
        return self.issues.listed(marker)

    @override
    def open(
        self,
        title: str,
        body: str,
        *,
        labels: Iterable[str],
        marker: str,
        pending_since: datetime | None,
    ) -> Issue:
        if found := self.find(marker):
            return found
        if pending_since is not None:
            return self.issues.retry_audit(title, body, marker=marker, labels=labels, pending_since=pending_since)
        return self.issues.create(title, body, marker=marker, labels=labels)

    @override
    def edit(self, number: int, body: str) -> None:
        self.issues.edit(number, body)

    @override
    def comment(self, number: int, body: str, *, marker: str, pending_since: datetime | None) -> str:
        return self.issues.marked_comment(
            self.issues.repository, number, body, marker=marker, pending_since=pending_since
        )


class _BacklogSink(report_publish.Sink):
    def __init__(self, book: backlog.Backlog, summary: dict[str, Any]) -> None:
        self.book, self.summary = book, summary

    @override
    def find(self, marker: str) -> Issue | None:
        if marker.endswith(":summary"):
            found = self.book.issues.find(marker)
            return Issue(found["number"], found["html_url"], found["state"]) if found else None
        entry = _listed(self.book, marker)
        return self._issue(entry) if entry else None

    @override
    def open(
        self,
        title: str,
        body: str,
        *,
        labels: Iterable[str],
        marker: str,
        pending_since: datetime | None,
    ) -> Issue:
        if marker.endswith(":summary"):
            if found := self.find(marker):
                return found
            names = list(labels)
            self.book.issues.ensure_labels(names)
            made = self.book.issues.create(title, body, names)
            return Issue(made["number"], made["html_url"], made["state"])
        # A found marker can precede completion of Backlog.add's reciprocal repeat links.
        entry, _ = self.book.add(title, body, source="audit", evidence=[marker, self.summary["url"]], labels=labels)
        return self._issue(entry)

    @override
    def edit(self, number: int, body: str) -> None:
        self.book.issues.edit(number, {"body": body})

    @override
    def comment(self, number: int, body: str, *, marker: str, pending_since: datetime | None) -> str:
        self.book.issues.private()
        return self.book.issues.marked_comment(
            self.book.repository, number, body, marker=marker, pending_since=pending_since
        )

    def _issue(self, entry: backlog.Entry) -> Issue:
        url = f"https://{self.book.issues.host}/{self.book.repository}/issues/{entry.id}"
        return Issue(int(entry.id), url, "closed" if entry.status in {"done", "dropped"} else "open")


def _legacy(store: Store, state: dict[str, Any], save: Callable[[], None]) -> None:
    destination = state["destination"]
    book = OwlbearIssues(destination, store.root) if destination else backlog.Backlog.of(store)
    for index, finding in enumerate(state["findings"], 1):
        if finding.get("number") is not None:
            continue
        identity = f"audit:{state['id']}:{index}"
        pending = finding.get("pending")
        previous = datetime.fromisoformat(pending) if pending else None
        found = _listed(book, identity) if isinstance(book, backlog.Backlog) else book.listed(identity)
        if found is not None and not isinstance(book, backlog.Backlog):
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
        if isinstance(book, backlog.Backlog):
            entry, _ = book.add(finding["title"], text, source="audit", evidence=[identity], labels=labels)
            number, url = int(entry.id), f"https://{book.issues.host}/{book.repository}/issues/{entry.id}"
        else:
            text += f"\n\n<!-- {identity} -->\n"
            if previous:
                issue = book.retry_audit(finding["title"], text, marker=identity, labels=labels, pending_since=previous)
            else:
                issue = book.create(finding["title"], text, marker=identity, labels=labels)
            number, url = issue.number, issue.url
        finding.update(number=number, url=url, pending=None)
        save()


def _listed(book: backlog.Backlog, identity: str) -> backlog.Entry | None:
    entries, invalid = book.read(fresh=True)
    if invalid:
        msg = "cannot establish publication custody; unreadable Backlog entries: " + ", ".join(invalid)
        raise ValueError(msg)
    return next((entry for entry in entries.values() if identity in entry.evidence), None)


def _text(state: dict[str, Any], finding: dict[str, Any]) -> str:
    return (
        f"Type: {finding['type']} · Severity: {finding['severity']}\n\n"
        f"Audit: {state['branch']} at {state['commit']}\n\n"
        f"Where: {finding['where']}\n\nEvidence:\n{finding['evidence']}\n\n"
        f"Recommendation:\n{finding['recommendation']}"
    )
