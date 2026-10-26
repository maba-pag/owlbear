"""What an older curation host's record proves about the snapshot of PIDs it left (R04, #608).

A restart reads that record before it holds anything. The snapshot is the producer's ``left`` PIDs; its session evidence
is every row but a refusal the producer is known to write before any session. Such a refusal proves no session, so the
same snapshot under refusals stays the one generation its lease already holds or recovered.
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
REFUSALS = frozenset({  # the fixed reasons main's ``_one`` writes when it refuses before any session
    "no shared repository is set up, so there is no memory to curate",
    "the last curation's processes may still run; stop them before curating again",
    "the machine is paused, and this automatic trigger does not curate while paused; it waits for a later trigger",
    "this automatic trigger is off in the machine settings; it waits until it is turned on",
    "stopping",
    "OwlBear stops once nothing runs: no memory curation starts",
    "OwlBear is updating; try again in a minute",
})  # fmt: skip
SUBAGENTS_UNSET = "agents.curator.subagents is unset"  # main's ``_unset`` reasons, before any session and SDK call
UNSET = ("settings unset: ", "; fill them in on the Settings page")


def observed(runs: Runs) -> str:
    """The snapshot a producer left: its PIDs and their births, never this host's key."""
    return hashlib.sha256(json.dumps(sorted(runs.left.items())).encode()).hexdigest()  # each PID once


def sessions(runs: Runs) -> tuple[str, ...]:
    """The producer's session evidence on file: each row's folder and times, never this host's keys or reasons.

    Only a refusal main is known to write before any session is left out (see ``refused``). It may overwrite a
    session's row, which takes evidence away and adds none. Every other dated row counts, a generic failure even when
    the clock gave its start and end one value, and a row in a state the producer never writes is never taken for the
    snapshot's own.
    """
    found = (
        f"{name}|{r.state if r.state not in STATES else ''}|{_at(r.started_at)}|{_at(r.ended_at)}"
        for name, r in runs.folders.items()
        if r.state not in STATES or ((r.started_at or r.ended_at) and not refused(r))
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


def refused(run: FolderRun) -> bool:
    """Whether a failed row, or its waiting copy, is a refusal main writes only before any session and SDK call.

    A fixed refusal ends as it starts; an unset setting may also be found in the session's own check, later. Equal
    times alone prove nothing: a generic failure gets them when the clock gives one value.
    """
    if run.state not in {"failed", "waiting"} or run.started_at is None or run.ended_at is None:
        return False
    if run.reason in REFUSALS:
        return run.ended_at == run.started_at
    unset = run.reason == SUBAGENTS_UNSET or (run.reason.startswith(UNSET[0]) and run.reason.endswith(UNSET[1]))
    return unset and run.ended_at >= run.started_at


def _at(when: datetime | None) -> str:
    return when.isoformat() if when else ""
