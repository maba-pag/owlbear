"""Workspace-scoped security audit log store."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field, TypeAdapter

from owlbear.core.jsonl_store import JsonlStore

if TYPE_CHECKING:
    from pathlib import Path

_DEFAULT_MAX_ENTRIES = 500_000


class SecurityEvent(BaseModel):
    """A single security-relevant runtime event."""

    timestamp: str
    event_type: str
    severity: str
    actor: str
    session_id: str
    tool_name: str | None = None
    detail: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class SecurityAuditLog(JsonlStore[SecurityEvent]):
    """Append-only JSONL store for :class:`SecurityEvent` records.

    Args:
        workspace: Root workspace path for storing the audit file.
        max_entries: Maximum number of events retained.
    """

    def __init__(self, workspace: Path, *, max_entries: int = _DEFAULT_MAX_ENTRIES) -> None:
        super().__init__(workspace / ".owlbear" / "security_audit.jsonl", SecurityEvent)
        self._max_entries = max_entries

    @property
    def max_entries(self) -> int:
        """Maximum number of events retained by the store."""
        return self._max_entries

    def log(  # noqa: PLR0913
        self,
        *,
        event_type: str,
        severity: str,
        actor: str,
        session_id: str,
        tool_name: str | None,
        detail: str,
        metadata: dict[str, Any],
        timestamp: str | None = None,
    ) -> None:
        """Append one security event and trim overflow.

        Args:
            event_type: Event category identifier.
            severity: Severity level.
            actor: Actor that triggered the event.
            session_id: Session identifier.
            tool_name: Tool name if applicable.
            detail: Human-readable event detail.
            metadata: Additional event context.
            timestamp: Optional ISO-8601 timestamp override.
        """
        self.append(
            SecurityEvent(
                timestamp=timestamp or datetime.now(UTC).isoformat(),
                event_type=event_type,
                severity=severity,
                actor=actor,
                session_id=session_id,
                tool_name=tool_name,
                detail=detail,
                metadata=metadata,
            )
        )
        self._maybe_trim()

    def _maybe_trim(self) -> None:
        """Trim overflow by keeping only the newest *max_entries* records."""
        entries = self.load()
        if len(entries) <= self._max_entries:
            return

        trimmed = entries[-self._max_entries :]
        adapter: TypeAdapter[SecurityEvent] = TypeAdapter(SecurityEvent)
        with self.path.open("w", encoding="utf-8") as fh:
            for entry in trimmed:
                fh.write(adapter.dump_json(entry).decode("utf-8") + "\n")
