"""Pending memory and current read diagnostics, separate from curation's run history."""

from __future__ import annotations

from stat import S_ISDIR, S_ISLNK
from typing import TYPE_CHECKING

from owlbear_memory import MemoryEntry, MemoryState, selection

from owlbear_delivery_next.git.command_failure import failure

if TYPE_CHECKING:
    from pathlib import Path


def folders(root: Path, *, include_invalid: bool = False) -> list[str]:
    """Nonlinked project memory paths; the page also reports existing paths of the wrong type."""
    found = (p for p in root.iterdir() if p.is_dir() and not p.is_symlink() and not p.name.startswith("."))
    own = []
    for project in found:
        if project.name == "memory":
            continue
        try:
            mode = (project / "memory").lstat().st_mode
        except FileNotFoundError:
            continue
        if not S_ISLNK(mode) and (include_invalid or S_ISDIR(mode)):
            own.append(project.name)
    return sorted(own)


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
