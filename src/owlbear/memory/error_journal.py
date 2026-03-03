"""Append-only JSONL error journal with rotation.

Captures every error and resolution as a single JSON line in
``{workspace}/.owlbear/error_journal.jsonl``.  Agents query past
failures via :meth:`ErrorJournal.query` to learn from history.

Rotation: when the entry count exceeds :attr:`max_entries` after a
:meth:`log` call, the file is truncated to the most recent
``max_entries`` entries.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

__all__ = ["ErrorJournal"]

_DEFAULT_MAX_ENTRIES: int = 10_000


class ErrorJournal:
    """Append-only JSONL error log with query and rotation.

    Args:
        workspace: Root workspace directory.  The journal file is placed at
            ``{workspace}/.owlbear/error_journal.jsonl``.
        max_entries: Maximum entries before rotation (default 10 000).
    """

    def __init__(self, workspace: Path, *, max_entries: int = _DEFAULT_MAX_ENTRIES) -> None:
        self._path = workspace / ".owlbear" / "error_journal.jsonl"
        self._max_entries = max_entries

    # -- properties ----------------------------------------------------------

    @property
    def path(self) -> Path:
        """Location of the JSONL file."""
        return self._path

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
        entry = {
            "timestamp": ts,
            "error_type": error_type,
            "tool_name": tool_name,
            "exception_message": exc_message,
            "action_taken": action_taken,
            "attempt_number": attempt,
            "resolved": resolved,
            "session_id": session_id,
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
        self._maybe_rotate()

    # -- read ----------------------------------------------------------------

    def query(
        self,
        *,
        tool_name: str | None = None,
        error_type: str | None = None,
        last_n: int | None = None,
    ) -> list[dict[str, object]]:
        """Return filtered journal entries.

        All filters are optional; when omitted, all entries are returned.
        ``last_n`` is applied **after** filtering — it returns the last *n*
        matching entries (most recent).
        """
        entries = self._load_all()
        if tool_name is not None:
            entries = [e for e in entries if e["tool_name"] == tool_name]
        if error_type is not None:
            entries = [e for e in entries if e["error_type"] == error_type]
        if last_n is not None:
            entries = entries[-last_n:]
        return entries

    # -- internals -----------------------------------------------------------

    def _load_all(self) -> list[dict[str, object]]:
        """Deserialize every entry from the JSONL file."""
        if not self._path.exists():
            return []
        lines = self._path.read_text(encoding="utf-8").strip().splitlines()
        return [json.loads(line) for line in lines if line]

    def _maybe_rotate(self) -> None:
        """If entry count exceeds the cap, keep only the last *max_entries*."""
        entries = self._load_all()
        if len(entries) <= self._max_entries:
            return
        trimmed = entries[-self._max_entries :]
        with self._path.open("w", encoding="utf-8") as fh:
            for entry in trimmed:
                fh.write(json.dumps(entry) + "\n")
