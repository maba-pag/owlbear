"""The design pack job's persisted run vocabulary: stages, the blank record and the Job's reads of its run record."""

from __future__ import annotations

import fcntl
import json
import os
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.local_system import local_home
from owlbear_delivery_next.state_store import pack_run_record

# The run record's evidence is owned by the store (pack_run_record); these names stay importable from here for the Job.
from owlbear_delivery_next.state_store.pack_run_record import (
    FILE,  # noqa: F401
    HOST_STOPPED,  # noqa: F401
    REWRITTEN,
    STATES,  # noqa: F401
    digest,  # noqa: F401
    ended,  # noqa: F401
    generation,
    last,  # noqa: F401
    legacy_uncertain,  # noqa: F401
    now,  # noqa: F401
    observed,  # noqa: F401
    read_only,  # noqa: F401
    resolved,  # noqa: F401
    version_of,  # noqa: F401
)

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear_delivery_next.design_packs import pack_git
    from owlbear_delivery_next.pack_runs import pack_candidate

RUNS = "design-pack-runs"  # each run's own updater repository, under the store; never reused after a run
STAGES = (
    ("notice", "Notice: newer upstream release"),
    ("candidate", "Candidate: detector pins and skills"),
    ("diff", "Diff: rules and skill files"),
    ("golden", "Golden pages"),
    ("update", "Updater: skills against upstream and the findings"),
    ("replay", "Calibration replay"),
    ("challenger", "Challenger on the whole pack"),
    ("commit", "Commit: one commit on a pack branch"),
    ("push", "Push the branch"),
    ("pull-request", "Pull request to main"),
    ("merge", "CI and merge"),
)
LOG = 200  # lines kept of the last run's log
MACHINE_LOCK = "design-pack.lock"  # one running update per machine, whichever project started it (TD-242)


def blank() -> dict[str, Any]:
    """The unchanged initial shape used by every persisted job record."""
    stages = [{"name": n, "label": label, "result": "pending", "detail": ""} for n, label in STAGES]
    return {"state": "idle", "stage": "", "stages": stages, "started_at": None, "ended_at": None, "reason": "",
            "log": [], "published": None, "run": "", "loop": None, "questions": [], "context": None}  # fmt: skip


def describe(src: pack_git.Source, c: pack_candidate.Candidate) -> str:
    """The candidate and source identity shown in the job's stage result."""
    up = c.pins["upstream"]
    return f"{c.pins['pack']}: upstream {c.tag} at {up['commit'][:12]}, engine {up['engine']}; from {src.base[:12]}"


def read_version(path: Path) -> tuple[dict[str, Any], str]:
    """The last run at *path* as a Job reads it, and its version: "absent" when there is no file, "" when unreadable."""
    try:
        fd = pack_run_record.open_record(path)
    except FileNotFoundError:
        return blank(), "absent"
    except OSError, ValueError:
        return blank(), ""
    try:
        kept, version = pack_run_record.read_fd(fd)
    except OSError, ValueError:
        return blank(), ""
    return blank() | kept, version


def holds(seen: tuple[dict[str, Any], str], record: dict[str, Any], version: str) -> bool:
    """Whether *seen*, the run file as ``read_version`` read it whole and stable, is *record* at *version*.

    A writer's own version can describe another run's bytes, written over the published file before the writer read
    its descriptor, so only this read's agreement on both proves the version is the rewrite's. "absent" and ""
    (unreadable) match only themselves: a record the Job found absent or unreadable says nothing of a run read now.
    """
    return seen[1] == version and seen[0] == json.loads(json.dumps(record))


def interrupted(record: dict[str, Any], version: str) -> dict[str, str]:
    """A run an older host left running, as its record names it, with its generation taken before it is rewritten.

    A record without a workspace carries that generation into the rewrite made from it, under REWRITTEN, so the run
    keeps its identity even when no ledger write follows the rewrite.
    """
    identity = generation(record, version)[0]
    if "workspace" not in record:
        record[REWRITTEN] = identity
    return {
        "run": str(record.get("run") or ""),
        "started_at": str(record.get("started_at") or ""),
        "workspace": str(record.get("workspace") or ""),
        "generation": identity,
    }


def running_for() -> str | None:
    """The project whose design pack update runs on this machine now, by its name; None while none runs (TD-290)."""
    path = local_home.root() / MACHINE_LOCK
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    except OSError:
        return None
    try:
        fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)  # a running update holds it exclusively
    except BlockingIOError:
        return path.read_text(encoding="utf-8").strip() or "another project"
    finally:
        os.close(fd)  # closing releases a shared lock taken here
    return None
