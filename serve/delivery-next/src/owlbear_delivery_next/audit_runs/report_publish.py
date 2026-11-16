"""Summary-first audit publication shared by production sinks and fixture replay."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Protocol, override

from owlbear_delivery_next.audit_runs import record
from owlbear_delivery_next.github.owlbear_issues import AUDIT_RECENT_SECONDS, Issue

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

WAIT = "GitHub may still be listing the last entry; press again in two minutes"


class Sink(Protocol):
    """Issue operations, without choosing report text, ordering or durable receipts."""

    def find(self, marker: str) -> Issue | None:
        """List by exact marker; return None only after a complete, successful absence check."""
        ...

    def open(
        self,
        title: str,
        body: str,
        *,
        labels: Iterable[str],
        marker: str,
        pending_since: datetime | None,
    ) -> Issue:
        """Idempotently open or finish the marked issue, including a found Backlog entry's repeat links.

        Called even when find returned an issue: finding its marker does not establish completion.
        The report's refreshed intent is already saved; pending_since is the PREVIOUS attempt's time,
        suitable for OwlbearIssues.retry_audit. A found marker must never create another issue.
        """
        ...

    def edit(self, number: int, body: str) -> None:
        """Replace an issue body idempotently; keep any sink-owned metadata and selected writer."""
        ...


@dataclass(frozen=True)
class _Draft:
    title: str
    body: str
    labels: tuple[str, ...]
    marker: str


def publish(
    state: dict[str, Any],
    sink: Sink,
    save: Callable[[], None],
    *,
    project: str,
    audit: str = "code",
) -> None:
    """Publish only verified, accepted candidates, preserving their original one-based identities.

    The caller owns validation of the report and destination, and serializes publication attempts.
    No session is launched here. Every creation intent and receipt is saved independently; completing
    the summary means its reciprocal links were edited successfully, not merely that it exists.
    """
    if not state.get("verified"):
        msg = "audit findings must be verified before report publication"
        raise ValueError(msg)
    if state["summary_issue"]["complete"]:
        return
    verdicts = {row["finding"]: row for row in state["verdicts"]}
    accepted = [
        (index, finding)
        for index, finding in enumerate(state["findings"], 1)
        if verdicts[index]["verdict"] == "accepted"
    ]
    _open(
        state["summary_issue"],
        sink,
        save,
        _Draft(
            title=f"{project}: {audit} audit summary",
            body=_summary(state, project, audit, complete=False),
            labels=("audit:summary",),
            marker=f"audit:{state['id']}:summary",
        ),
    )
    for index, finding in accepted:
        _open(
            finding,
            sink,
            save,
            _Draft(
                title=finding["title"],
                body=_finding(state, finding),
                labels=(f"type:{finding['type']}", f"severity:{finding['severity']}"),
                marker=f"audit:{state['id']}:{index}",
            ),
        )
    sink.edit(state["summary_issue"]["number"], _summary(state, project, audit, complete=True))
    state["summary_issue"]["complete"] = True
    save()


def _open(
    receipt: dict[str, Any],
    sink: Sink,
    save: Callable[[], None],
    draft: _Draft,
) -> None:
    if receipt["number"] is not None:
        return
    pending = receipt["pending"]
    previous = datetime.fromisoformat(pending) if pending else None
    found = sink.find(draft.marker)
    if found is None and previous and (datetime.now(UTC) - previous).total_seconds() < AUDIT_RECENT_SECONDS:
        raise RuntimeError(WAIT)
    receipt["pending"] = record.now()
    save()
    issue = sink.open(
        draft.title,
        _marked(draft.body, draft.marker),
        labels=draft.labels,
        marker=draft.marker,
        pending_since=previous,
    )
    receipt.update(number=issue.number, url=issue.url, pending=None)
    save()


def _marked(body: str, marker: str) -> str:
    if body.rstrip().endswith(f"<!-- {marker} -->"):
        return body
    return f"{body.rstrip()}\n\n<!-- {marker} -->\n"


def _finding(state: dict[str, Any], finding: dict[str, Any]) -> str:
    summary = state["summary_issue"]["url"]
    return (
        f"Type: {finding['type']} | Severity: {finding['severity']}\n\n"
        f"Audit: {state['branch']} at {state['commit']}\n\n"
        f"Where: {finding['where']}\n\nEvidence:\n{finding['evidence']}\n\n"
        f"Audit summary: {summary}\n\nRecommendation:\n{finding['recommendation']}"
    )


def _summary(state: dict[str, Any], project: str, audit: str, *, complete: bool) -> str:
    verdicts = {row["finding"]: row for row in state["verdicts"]}
    counts = {
        outcome: sum(row["verdict"] == outcome for row in state["verdicts"])
        for outcome in ("accepted", "rejected", "unsure")
    }
    published = sum(
        finding["number"] is not None
        for index, finding in enumerate(state["findings"], 1)
        if verdicts[index]["verdict"] == "accepted"
    )
    destination = state["destination"] or "Backlog"
    lines = [
        f"Publication: {'complete' if complete else 'publishing'}",
        "",
        "## Scope",
        f"Project: {project}",
        f"Audit: {audit}",
        f"Branch: {state['branch']}",
        f"Commit: {state['commit']}",
        "",
        state["summary"],
        "",
        "## Note",
        state["note"] or "None.",
        "",
        "## Changed defaults",
    ]
    lines.extend(
        [f"- {row['default']}: {row['to']}. Reason: {row['reason']}" for row in state["changed_defaults"]] or ["None."]
    )
    lines.extend(["", "## Parts"])
    lines.extend(
        [f"- {row['part']}: {'ran' if row['ran'] else 'not run'}. {row['note']}" for row in state["parts"]]
        or ["None reported."]
    )
    lines.extend(["", "## Not covered"])
    lines.extend([f"- {gap}" for gap in state["not_covered"]] or ["None reported."])
    lines.extend(
        [
            "",
            "## Effects",
            "Code edits: none (read-only audit).",
            f"Auditor session: {state['session'] or 'not recorded'}",
            f"Verifier session: {state['verifier_session'] or 'not recorded'}",
            f"Subagents: {len(state['subagents'])}",
            "```json",
            json.dumps(state["subagents"], indent=2, ensure_ascii=False),
            "```",
            f"Destination: {destination}",
            (
                f"Candidates: {len(state['findings'])}; accepted: {counts['accepted']}; "
                f"rejected: {counts['rejected']}; unsure: {counts['unsure']}."
            ),
            (
                f"Published findings: {published}/{counts['accepted']}; summary issues: "
                f"{int(complete or state['summary_issue']['number'] is not None)}."
            ),
        ]
    )
    for outcome in ("accepted", "rejected", "unsure"):
        lines.extend(["", f"## {outcome.title()} findings"])
        rows = []
        for index, finding in enumerate(state["findings"], 1):
            verdict = verdicts[index]
            if verdict["verdict"] != outcome:
                continue
            title = finding["title"].replace("[", r"\[").replace("]", r"\]")
            link = f"[{title}]({finding['url']})" if finding["url"] else title
            rows.append(f"- {index}. {link} ({finding['type']}, {finding['severity']})")
            if outcome != "accepted":
                rows.extend(
                    [
                        f"  Reason: {verdict['reason']}",
                        f"  Decisions: {', '.join(verdict['decisions']) or 'none cited'}",
                        f"  Duplicate of: {verdict['duplicate_of'] or 'none'}",
                    ]
                )
        lines.extend(rows or ["None."])
    return _marked("\n\n".join(lines), f"audit:{state['id']}:summary")


class Recorder(Sink):
    """An in-memory sink; fixture URLs are references only and cause no external writes."""

    def __init__(self) -> None:
        self.issues: dict[int, dict[str, Any]] = {}
        self._markers: dict[str, int] = {}

    @override
    def find(self, marker: str) -> Issue | None:
        """Return the receipt for an issue previously opened with this exact marker."""
        number = self._markers.get(marker)
        return self._issue(number) if number is not None else None

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
        """Record a new issue, or return the existing receipt without duplicating it."""
        if found := self.find(marker):
            return found
        number = len(self.issues) + 1
        self.issues[number] = {
            "title": title,
            "body": body,
            "labels": list(labels),
            "url": f"https://audit.invalid/issues/{number}",
        }
        self._markers[marker] = number
        return self._issue(number)

    @override
    def edit(self, number: int, body: str) -> None:
        """Replace the recorded body, just as a successful issue edit would."""
        self.issues[number]["body"] = body

    def _issue(self, number: int) -> Issue:
        return Issue(number, self.issues[number]["url"], "open")
