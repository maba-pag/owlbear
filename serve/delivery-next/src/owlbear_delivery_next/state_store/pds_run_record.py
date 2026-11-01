"""A project's last PDS update run record (#777), read without writing, as ``pack_run_record`` reads Impeccable's."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.state_store.pack_run_record import open_record, read_fd

if TYPE_CHECKING:
    from pathlib import Path

FILE = "pds-update.json"
RUNS = "pds-runs"  # each run's own workspace, under the store


def observed(root: Path) -> tuple[dict[str, Any], str] | None:
    """The last PDS run as *root* holds it with its file version; None when it has no record. Reads without writing."""
    try:
        fd = open_record(root / FILE)
    except FileNotFoundError:
        return None
    return read_fd(fd)


def read_only(root: Path) -> dict[str, Any] | None:
    """The last PDS run as *root* holds it; None when it has no record.

    Raises OSError or ValueError when the record exists but cannot be read as a run: that is not an empty record.
    """
    got = observed(root)
    return None if got is None else got[0]
