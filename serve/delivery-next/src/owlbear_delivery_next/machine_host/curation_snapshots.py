"""What an older curation host's record proves about the snapshot of PIDs it left (R04, #608).

A restart reads that record before it holds anything. The snapshot is the producer's ``left`` PIDs; its session evidence
is every row a session wrote. A refusal before any session writes a row too, which proves no session, so the same
snapshot under refusals stays the one generation its lease already holds or recovered.
"""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import datetime

    from owlbear_delivery_next.local_system import maintenance
    from owlbear_delivery_next.machine_host.curation import FolderRun, Runs

STATES = frozenset({"never", "waiting", "running", "done", "failed"})  # every state a folder's row is written in


def observed(runs: Runs) -> str:
    """The snapshot a producer left: its PIDs and their births, never this host's key."""
    return hashlib.sha256(json.dumps(sorted(runs.left.items())).encode()).hexdigest()  # each PID once


def sessions(runs: Runs) -> tuple[str, ...]:
    """The producer's session evidence on file: each row's folder and times, never this host's keys or reasons.

    A refusal before any session is the producer's failed or waiting row that ends as it starts, so it is no session;
    it may overwrite a session's row, which takes evidence away and adds none. Every other dated row is a session's.
    A row in a state the producer never writes counts as evidence, so it is never taken for the snapshot's own.
    """
    found = (
        f"{name}|{r.state if r.state not in STATES else ''}|{_at(r.started_at)}|{_at(r.ended_at)}"
        for name, r in runs.folders.items()
        if r.state not in STATES or ((r.started_at or r.ended_at) and not _refusal(r))
    )
    return tuple(sorted(found))


def same_snapshot(project: str, snapshot: str, seen: tuple[str, ...]) -> Callable[[maintenance.Lease], bool]:
    """Whether a lease imported these very PIDs and saw every session row still on file, whatever its state."""

    def covers(lease: maintenance.Lease) -> bool:
        return (
            lease.project == project
            and lease.kind == "curation"
            and lease.workspace == ""
            and lease.generation == snapshot
            and set(seen) <= set(lease.observed)
        )

    return covers


def _refusal(run: FolderRun) -> bool:
    return run.state in {"failed", "waiting"} and run.started_at is not None and run.ended_at == run.started_at


def _at(when: datetime | None) -> str:
    return when.isoformat() if when else ""
