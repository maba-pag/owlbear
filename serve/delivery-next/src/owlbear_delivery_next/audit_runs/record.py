"""Atomic last-run reports, also readable without a project host."""

from __future__ import annotations

import json
import threading
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from owlbear_delivery_next.audit_runs import suppression_items
from owlbear_delivery_next.change_contracts.project_audit_tools import (
    AuditFinding,
    AuditPart,
    AuditVerdict,
    ChangedDefault,
)
from owlbear_delivery_next.git.command_failure import failure
from owlbear_delivery_next.local_system.storage_io import atomic_write

if TYPE_CHECKING:
    from owlbear_delivery_next.state_store.store import Store

FILE = "audits.json"
NAMES = ("doc", "agent", "code", "suppressions")
OPTIONAL = {
    "verified",
    "verdicts",
    "verifier_session",
    "summary_issue",
    "summary_parts",
    "inventory",
    "counts",
    "suppression_members",
    "judging_reason",
    "suppression_details",
}
INTERRUPTED = "OwlBear stopped while the audit ran; start it again"
_guard = threading.RLock()
_live: set[tuple[str, str]] = set()


class Finding(AuditFinding):
    """A reported finding and its host-owned publication receipt."""

    number: int | None
    url: str
    pending: str | None


class SummaryIssue(BaseModel):
    """Host-owned creation intent, issue receipt and final summary-edit receipt."""

    model_config = ConfigDict(extra="forbid", strict=True)

    number: int | None = None
    url: str = ""
    pending: str | None = None
    complete: bool = False


class SummaryPart(BaseModel):
    """A continuation comment's host-owned creation intent and receipt."""

    model_config = ConfigDict(extra="forbid", strict=True)

    body: str
    url: str = ""
    pending: str | None = None


class Report(BaseModel):
    """The complete last-run record, never a partial success inferred from malformed JSON."""

    model_config = ConfigDict(extra="forbid", strict=True)

    id: str
    state: Literal["running", "publishing", "done", "failed"]
    phase: str
    started_at: str
    ended_at: str
    branch: str
    commit: str
    note: str
    changed_defaults: list[ChangedDefault]
    destination: str
    summary: str
    findings: list[Finding]
    parts: list[AuditPart]
    not_covered: list[str]
    subagents: list[dict[str, Any]]
    reason: str
    session: str = ""
    verified: bool = False
    verdicts: list[AuditVerdict] = Field(default_factory=list)
    verifier_session: str = ""
    summary_issue: SummaryIssue = Field(default_factory=SummaryIssue)
    summary_parts: list[SummaryPart] = Field(default_factory=list)
    inventory: list[dict[str, str]] = Field(default_factory=list)
    counts: dict[str, int] = Field(default_factory=dict)
    suppression_members: list[list[dict[str, Any]]] = Field(default_factory=list)
    judging_reason: str = ""
    suppression_details: list[list[SummaryPart]] = Field(default_factory=list)


REPORTS = TypeAdapter(dict[Literal["doc", "agent", "code", "suppressions"], Report])


def now() -> str:
    """A timezone-aware report timestamp."""
    return datetime.now(UTC).isoformat()


def active(store: Store, audit: str, *, running: bool) -> None:
    """Register a live host thread for passive report readers in this process."""
    with _guard:
        key = (str(store.root.resolve()), audit)
        if running:
            _live.add(key)
        else:
            _live.discard(key)


def load(store: Store) -> dict[str, Any]:
    """Read persisted reports strictly; malformed records must never be overwritten as empty."""
    path = store.root / FILE
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    try:
        validated = REPORTS.validate_python(data)
    except ValidationError as exc:
        exc.add_note(f"saved audit record: {path}")
        raise
    return {
        name: report.model_dump(mode="json", exclude=OPTIONAL - data[name].keys()) for name, report in validated.items()
    }


def shown(row: dict[str, Any] | None) -> dict[str, Any] | None:
    """A report for a page: the review's lists of thousands of rows stay behind their own routes."""
    hidden = {"inventory", "suppression_members", "suppression_details"}
    return row and {k: v for k, v in row.items() if k not in hidden}


def read(store: Store) -> dict[str, Any]:
    """Last reports; an interrupted session fails visibly, publication remains recoverable."""
    with _guard:
        try:
            rows = load(store)
        except (OSError, ValueError, TypeError) as exc:
            return {name: {"state": "failed", "reason": failure(exc), "findings": []} for name in NAMES}
        for name, row in rows.items():
            if name == "suppressions" and "inventory" in row:
                row["counts"] = suppression_items.counts(store.root, row["inventory"])
            if row["state"] == "running" and (str(store.root.resolve()), name) not in _live:
                rows[name] = {
                    **row,
                    "state": "failed",
                    "reason": INTERRUPTED + ("; completed verdicts remain recorded" if name == "suppressions" else ""),
                }
        return rows


def save(store: Store, audit: str, state: dict[str, Any]) -> None:
    """Replace one report, preserving the other audit's last report."""
    with _guard:
        rows = load(store)
        Report.model_validate(state)
        rows[audit] = state
        store.root.mkdir(parents=True, exist_ok=True)
        atomic_write(store.root / FILE, json.dumps(rows, indent=2) + "\n")


def unpublished(state: dict[str, Any]) -> int:
    """Unconfirmed finding receipts, and a verified run's unfinished summary publication."""
    findings = state.get("findings", [])
    if not state.get("verified", False):
        return sum(f.get("number") is None for f in findings) + sum(
            not p["url"] for parts in state.get("suppression_details", []) for p in parts
        )
    accepted = {v["finding"] for v in state["verdicts"] if v["verdict"] == "accepted"}
    return sum(f.get("number") is None for n, f in enumerate(findings, 1) if n in accepted) + int(
        not state.get("summary_issue", {}).get("complete", False)
    )
