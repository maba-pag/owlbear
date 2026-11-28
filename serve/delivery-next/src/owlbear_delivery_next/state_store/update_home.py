"""The machine's update records and the checkouts they still need."""

from __future__ import annotations

from pathlib import Path

from owlbear_delivery_next.local_system import local_home
from owlbear_delivery_next.state_store import pack_run_record, pds_run_record

KEY = "updates"


def root() -> Path:
    """Where the machine keeps its update records and workspaces."""
    return local_home.root() / KEY


def checkouts() -> set[Path]:
    """Keep both the working checkout and the publication checkout of every open update."""
    kept = set()
    for read in (pack_run_record.read_only, pds_run_record.read_only):
        record = read(root())
        if record and record["state"] in {"running", "waiting"}:
            context = record.get("context") or {}
            for key in ("checkout", "publication"):
                if path := (context.get(key) or {}).get("root"):
                    kept.add(Path(path).resolve())
    return kept
