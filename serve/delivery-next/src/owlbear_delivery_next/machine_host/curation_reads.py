"""Pending memory and current read diagnostics, separate from curation's run history."""

from __future__ import annotations

from typing import TYPE_CHECKING

from owlbear_memory import MemoryEntry, MemoryState, selection

from owlbear_delivery_next.git.command_failure import failure

if TYPE_CHECKING:
    from pathlib import Path


def pending(store: Path, *, read_errors: dict[str, str] | None = None) -> list[MemoryEntry]:
    """Keep the readable pending entries; a current page read also reports skipped files."""
    try:
        read = selection.stored(store)
    except (OSError, ValueError) as exc:
        if read_errors is None:
            raise
        read_errors[str(store)] = failure(exc)
        return []
    if read_errors is not None:
        read_errors.update(read.read_errors)
    return [entry for entry in read.entries if entry.state == MemoryState.PENDING]
