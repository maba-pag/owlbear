"""JSONL-based audit logger for orchestrator dispatch tracking."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from owlbear.audit.models import CompletionEvent, DispatchEvent, audit_adapter

if TYPE_CHECKING:
    from pathlib import Path


class AuditLog:
    """Append-only JSONL audit log; one file per session under audit_dir."""

    def __init__(self, audit_dir: Path) -> None:
        """Store audit directory path; does not create the directory eagerly."""
        self._audit_dir = audit_dir

    def _session_file(self, session_id: str) -> Path:
        return self._audit_dir / f"{session_id}.jsonl"

    def _ensure_dir(self) -> None:
        self._audit_dir.mkdir(parents=True, exist_ok=True)

    def log_dispatch(self, event: DispatchEvent, session_id: str) -> None:
        """Append a dispatch event as a JSON line to the session file."""
        self._ensure_dir()
        with self._session_file(session_id).open("a", encoding="utf-8") as f:
            f.write(event.model_dump_json() + "\n")

    def log_completion(self, event: CompletionEvent, session_id: str) -> None:
        """Append a completion event as a JSON line to the session file."""
        self._ensure_dir()
        with self._session_file(session_id).open("a", encoding="utf-8") as f:
            f.write(event.model_dump_json() + "\n")

    def query(
        self,
        *,
        date_range: tuple[str, str] | None = None,
        agent: str | None = None,
        outcome: str | None = None,
        cycle_id: str | None = None,
    ) -> list[DispatchEvent | CompletionEvent]:
        """Return all events from audit_dir, filtered by optional parameters."""
        if not self._audit_dir.exists():
            return []

        events: list[DispatchEvent | CompletionEvent] = []
        for jsonl_file in self._audit_dir.glob("*.jsonl"):
            for raw_line in jsonl_file.read_text(encoding="utf-8").splitlines():
                stripped = raw_line.strip()
                if not stripped:
                    continue
                events.append(audit_adapter.validate_json(stripped))

        if agent is not None:
            events = [e for e in events if e.agent == agent]

        if outcome is not None:
            events = [e for e in events if isinstance(e, CompletionEvent) and e.outcome == outcome]

        if cycle_id is not None:
            events = [e for e in events if hasattr(e, "cycle_id") and e.cycle_id == cycle_id]

        if date_range is not None:
            start_dt = _parse_ts(date_range[0])
            end_dt = _parse_ts(date_range[1])
            events = [e for e in events if start_dt <= _parse_ts(e.timestamp) <= end_dt]

        return events


def _parse_ts(ts: str) -> datetime:
    """Parse an ISO-8601 timestamp string."""
    return datetime.fromisoformat(ts)
