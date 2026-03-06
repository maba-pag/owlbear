"""Append-only JSONL error journal with rotation.

Captures every error and resolution as a single JSON line in
``{workspace}/.owlbear/error_journal.jsonl``.  Agents query past
failures via :meth:`ErrorJournal.query` to learn from history.

Rotation: when the entry count exceeds :attr:`max_entries` after a
:meth:`log` call, the file is truncated to the most recent
``max_entries`` entries.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, TypeAdapter

from owlbear.core.jsonl_store import JsonlStore

if TYPE_CHECKING:
    from pathlib import Path

__all__ = ["ErrorEntry", "ErrorJournal"]

_DEFAULT_MAX_ENTRIES: int = 10_000


class ErrorEntry(BaseModel):
    """A single error journal record."""

    timestamp: str
    error_type: str
    tool_name: str
    exception_message: str
    action_taken: str
    attempt_number: int
    resolved: bool
    session_id: str


class ErrorJournal(JsonlStore[ErrorEntry]):
    """Append-only JSONL error log with query and rotation.

    Args:
        workspace: Root workspace directory.  The journal file is placed at
            ``{workspace}/.owlbear/error_journal.jsonl``.
        max_entries: Maximum entries before rotation (default 10 000).
    """

    def __init__(self, workspace: Path, *, max_entries: int = _DEFAULT_MAX_ENTRIES) -> None:
        super().__init__(workspace / ".owlbear" / "error_journal.jsonl", ErrorEntry)
        self._max_entries = max_entries

    # -- properties ----------------------------------------------------------

    @property
    def max_entries(self) -> int:
        """Maximum entries before rotation triggers."""
        return self._max_entries

    # -- write ---------------------------------------------------------------

    def log(  # noqa: PLR0913
        self,
        *,
        ts: str,
        error_type: str,
        tool_name: str,
        exc_message: str,
        action_taken: str,
        attempt: int,
        resolved: bool,
        session_id: str,
    ) -> None:
        """Append an error entry, rotating if the cap is exceeded."""
        self.append(
            ErrorEntry(
                timestamp=ts,
                error_type=error_type,
                tool_name=tool_name,
                exception_message=exc_message,
                action_taken=action_taken,
                attempt_number=attempt,
                resolved=resolved,
                session_id=session_id,
            )
        )
        self._maybe_rotate()

    # -- read ----------------------------------------------------------------

    def query(
        self,
        *,
        tool_name: str | None = None,
        error_type: str | None = None,
        last_n: int | None = None,
    ) -> list[ErrorEntry]:
        """Return filtered journal entries.

        All filters are optional; when omitted, all entries are returned.
        ``last_n`` is applied **after** filtering — it returns the last *n*
        matching entries (most recent).
        """
        entries = self.load()
        if tool_name is not None:
            entries = [e for e in entries if e.tool_name == tool_name]
        if error_type is not None:
            entries = [e for e in entries if e.error_type == error_type]
        if last_n is not None:
            entries = entries[-last_n:]
        return entries

    # -- internals -----------------------------------------------------------

    def _maybe_rotate(self) -> None:
        """If entry count exceeds the cap, keep only the last *max_entries*."""
        entries = self.load()
        if len(entries) <= self._max_entries:
            return
        trimmed = entries[-self._max_entries :]
        adapter: TypeAdapter[ErrorEntry] = TypeAdapter(ErrorEntry)
        with self._path.open("w", encoding="utf-8") as fh:
            for entry in trimmed:
                fh.write(adapter.dump_json(entry).decode("utf-8") + "\n")
