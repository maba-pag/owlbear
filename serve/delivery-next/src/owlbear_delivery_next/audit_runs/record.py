"""Atomic last-run reports, also readable without a project host."""

from __future__ import annotations

import json
import threading
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, ConfigDict, TypeAdapter, ValidationError

from owlbear_delivery_next.change_contracts.project_audit_tools import AuditFinding, ChangedDefault
from owlbear_delivery_next.git.command_failure import failure
from owlbear_delivery_next.local_system import codebase, data_repo
from owlbear_delivery_next.local_system.storage_io import atomic_write

if TYPE_CHECKING:
    from owlbear_delivery_next.state_store.store import Store

FILE = "audits.json"
NAMES = ("doc", "agent")
INTERRUPTED = "OwlBear stopped while the audit ran; start it again"
_guard = threading.RLock()
_live: set[tuple[str, str]] = set()


class Finding(AuditFinding):
    """A reported finding and its host-owned publication receipt."""

    number: int | None
    url: str
    pending: str | None


class Report(BaseModel):
    """The complete last-run record, never a partial success inferred from malformed JSON."""

    model_config = ConfigDict(extra="forbid", strict=True)

    id: str
    audit: Literal["doc", "agent"]
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
    parts: list[str]
    not_covered: list[str]
    subagents: list[dict[str, Any]]
    reason: str
    session: str = ""


REPORTS = TypeAdapter(dict[Literal["doc", "agent"], Report])


def offered(store: Store) -> tuple[str, ...]:
    """Offer agent audits only to the canonical OwlBear repository, under any shared-folder name."""
    identity = data_repo.remote_identity(codebase.URL)
    return NAMES if store.shared is not None and store.shared.claimed(identity) == store.name else ("doc",)


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
    return {name: report.model_dump(mode="json") for name, report in validated.items()}


def read(store: Store) -> dict[str, Any]:
    """Last reports; an interrupted session fails visibly, publication remains recoverable."""
    with _guard:
        try:
            rows = load(store)
        except (OSError, ValueError, TypeError) as exc:
            return {name: {"state": "failed", "reason": failure(exc), "findings": []} for name in NAMES}
        for name, row in rows.items():
            if row["state"] == "running" and (str(store.root.resolve()), name) not in _live:
                rows[name] = {**row, "state": "failed", "reason": INTERRUPTED}
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
    """How many findings have no confirmed issue receipt."""
    return sum(f.get("number") is None for f in state.get("findings", []))
