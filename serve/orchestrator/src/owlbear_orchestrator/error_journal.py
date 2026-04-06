"""ErrorJournal — JSONL-backed persistent error log for the orchestrator."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, TypeAdapter

if TYPE_CHECKING:
    from pathlib import Path


class ErrorEntry(BaseModel):
    """A single error event recorded by the orchestrator.

    All fields are plain strings so the model serialises cleanly to one JSONL line.
    The model is frozen to prevent accidental mutation after creation.
    """

    model_config = ConfigDict(frozen=True)

    timestamp: str
    category: str
    method: str
    message: str
    session_id: str


#: Module-level TypeAdapter for efficient JSONL serialisation / deserialisation.
entry_adapter: TypeAdapter[ErrorEntry] = TypeAdapter(ErrorEntry)


class ErrorJournal:
    """Append-only JSONL log with bounded rotation.

    Args:
        path: File path for the JSONL log.  The file is created lazily on the
            first :meth:`log` call — the constructor never touches the filesystem.
        max_entries: Maximum number of entries to retain.  When the file grows
            beyond this limit, the oldest entries are discarded.
    """

    def __init__(self, path: Path, *, max_entries: int = 5000) -> None:
        self._path = path
        self._max_entries = max_entries

    def log(
        self,
        *,
        category: str,
        method: str,
        message: str,
        session_id: str,
    ) -> None:
        """Append an entry to the journal, rotating if the limit is exceeded.

        All arguments are keyword-only.  The ISO-8601 timestamp is auto-generated.
        """
        entry = ErrorEntry(
            timestamp=datetime.now(tz=UTC).isoformat(),
            category=category,
            method=method,
            message=message,
            session_id=session_id,
        )
        line = entry_adapter.dump_json(entry).decode() + "\n"
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(line)
        self._rotate()

    def load(self) -> list[ErrorEntry]:
        """Return all entries in chronological order (oldest first).

        Returns an empty list when the file does not exist or is empty.
        """
        if not self._path.exists():
            return []
        text = self._path.read_text(encoding="utf-8").strip()
        if not text:
            return []
        return [entry_adapter.validate_json(line) for line in text.splitlines()]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _rotate(self) -> None:
        """Trim the file to the most recent *max_entries* lines if over the limit."""
        text = self._path.read_text(encoding="utf-8").strip()
        lines = text.splitlines()
        if len(lines) <= self._max_entries:
            return
        kept = lines[-self._max_entries :]
        self._path.write_text("\n".join(kept) + "\n", encoding="utf-8")


class ErrorLoggerAdapter:
    """Adapts ErrorJournal to the _ErrorLogger Protocol.

    Delegates log_error() calls to ErrorJournal.log() using the fixed
    'pre-session' sentinel as session_id — concurrency-safe because it
    is a class-level constant, not an instance attribute.
    """

    _SESSION_ID = "pre-session"

    def __init__(self, journal: ErrorJournal) -> None:
        self._journal = journal

    def log_error(self, *, category: object, method: str, message: str) -> None:
        """Delegate to ErrorJournal.log() with pre-session sentinel session_id."""
        self._journal.log(
            category=str(category),
            method=method,
            message=message,
            session_id=self._SESSION_ID,
        )
