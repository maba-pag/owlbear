"""The persisted design-pack run vocabulary and read-only ownership evidence."""

from __future__ import annotations

import fcntl
import json
import os
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.local_system import local_home

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear_delivery_next.design_packs import pack_git
    from owlbear_delivery_next.pack_runs import pack_candidate
    from owlbear_delivery_next.state_store.store import Store

FILE = "design-pack-update.json"  # the last run, under the store
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
OPEN = frozenset({"pending", "running", "waiting"})


def now() -> str:
    """The timestamp recorded for a run's stages and log entries."""
    return datetime.now(UTC).isoformat(timespec="seconds")


def blank() -> dict[str, Any]:
    """The unchanged initial shape used by every persisted job record."""
    stages = [{"name": n, "label": label, "result": "pending", "detail": ""} for n, label in STAGES]
    return {"state": "idle", "stage": "", "stages": stages, "started_at": None, "ended_at": None, "reason": "",
            "log": [], "published": None, "run": "", "loop": None, "questions": [], "context": None}  # fmt: skip


def describe(src: pack_git.Source, c: pack_candidate.Candidate) -> str:
    """The candidate and source identity shown in the job's stage result."""
    up = c.pins["upstream"]
    return f"{c.pins['pack']}: upstream {c.tag} at {up['commit'][:12]}, engine {up['engine']}; from {src.base[:12]}"


def read_fd(fd: int) -> tuple[dict[str, Any], str]:
    """The run *fd* holds and that file's version, both from the one open descriptor.

    The version is the file's identity and metadata as opened, so a replacement made after the open is not mixed
    into what was read. Raises OSError or ValueError when the record cannot be read as a run.
    """
    with os.fdopen(fd, encoding="utf-8") as f:
        st = os.fstat(f.fileno())
        kept = json.load(f)
    if not isinstance(kept, dict):
        msg = f"{FILE} is not a run"
        raise ValueError(msg)  # noqa: TRY004 - callers treat a damaged record as a ValueError
    return kept, f"{st.st_dev}:{st.st_ino}:{st.st_size}:{st.st_mtime_ns}"


def observed(root: Path) -> tuple[dict[str, Any], str] | None:
    """The last run as *root* holds it with its file version; None when it has no record. Reads without writing."""
    try:
        fd = os.open(root / FILE, os.O_RDONLY | os.O_NOFOLLOW)
    except FileNotFoundError:
        return None
    return read_fd(fd)


def read_only(root: Path) -> dict[str, Any] | None:
    """The last run as *root* holds it, read without following a link or writing; None when it has no record.

    Raises OSError or ValueError when the record exists but cannot be read as a run: that is not an empty record.
    """
    got = observed(root)
    return None if got is None else got[0]


def legacy_uncertain(kept: dict[str, Any]) -> bool:
    """A failed record an older host wrote while its updater or replay judge may still run; it has no workspace."""
    return (
        kept.get("state") == "failed"
        and "workspace" not in kept
        and "may still be running" in str(kept.get("reason", ""))
    )


def last(store: Store) -> dict[str, Any] | None:
    """The last run's state, ending and times, for the Maintenance page; None when it never ran."""
    try:
        kept = json.loads((store.root / FILE).read_text(encoding="utf-8"))
    except OSError, ValueError:
        return None
    if not isinstance(kept, dict) or not kept.get("started_at"):
        return None
    return {k: kept.get(k) for k in ("state", "started_at", "ended_at", "reason")}


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
