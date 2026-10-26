"""The persisted design-pack run vocabulary and read-only ownership evidence."""

from __future__ import annotations

import contextlib
import fcntl
import hashlib
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
# every state Job writes; a record in any other state is damaged, not idle
STATES = frozenset({"idle", "running", "waiting", "failed", "discarded", "up-to-date", "passed"})


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
    state, stages, log = kept.get("state"), kept.get("stages"), kept.get("log")
    if not (isinstance(state, str) and state in STATES and isinstance(stages, list) and isinstance(log, list)):
        msg = f"{FILE} is missing or misshapen in its state, stages or log"  # not evidence of an idle run
        raise ValueError(msg)
    return kept, version_of(st)


def version_of(st: os.stat_result) -> str:
    """A file's identity and metadata as one string; ctime, unlike mtime, moves on every change to the inode."""
    return f"{st.st_dev}:{st.st_ino}:{st.st_size}:{st.st_mtime_ns}:{st.st_ctime_ns}"


def read_version(path: Path) -> tuple[dict[str, Any], str]:
    """The last run at *path* as a Job reads it, and its version: "absent" when there is no file, "" when unreadable."""
    try:
        fd = os.open(path, os.O_RDONLY)
    except FileNotFoundError:
        return blank(), "absent"
    except OSError:
        return blank(), ""
    try:
        kept, version = read_fd(fd)
    except OSError, ValueError:
        return blank(), ""
    return blank() | kept, version


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


HOST_STOPPED = "the host stopped during this run; check the package checkout before running again"
SESSIONS = ("update", "replay", "challenger")  # the stages whose work enters the SDK
RETURNED = (  # what an older host wrote once a stage's SDK session returned with its termination confirmed
    "update: PackError: the updater asks the owner: ",
    "update: PackError: the updater ended with ",
    "challenger: PackError: the challenger ended with ",
    "calibration replay: ",  # the judges' failed verdict, each judge's session confirmed gone
)


def legacy_uncertain(kept: dict[str, Any]) -> bool:
    """A failed record an older host wrote while its updater, replay judge or challenger may still run; no workspace.

    It wrote "may still be running" when a session returned unconfirmed, and HOST_STOPPED for a run it found running.
    Any other failure of a stage that enters the SDK, an exception raised from the session itself among them, proves
    nothing about the session's end, whether or not its folder survived: only a reason it wrote after the session
    returned confirmed does. A failure in any other stage happened with no session open.
    """
    reason = str(kept.get("reason", ""))
    if kept.get("state") != "failed" or "workspace" in kept:
        return False
    if "may still be running" in reason or reason == HOST_STOPPED:
        return True
    stages = kept.get("stages") if isinstance(kept.get("stages"), list) else []
    failed = {s.get("name") for s in stages if isinstance(s, dict) and s.get("result") == "failed"}
    in_session = bool(failed & set(SESSIONS)) or reason.startswith(tuple(f"{s}: " for s in SESSIONS))
    return in_session and not reason.startswith(RETURNED)


OBSERVED = ("state", "stage", "run", "started_at", "ended_at", "reason", "workspace")
REWRITTEN = "interrupted_generation"  # the generation this host's own rewrite of a running record carries forward


def generation(record: dict[str, Any], version: str) -> tuple[str, datetime | None]:
    """A legacy run's identity: its proven run and start time, else a fingerprint of its fields and its file.

    The fingerprint binds the observed fields and the file's identity and version, read from the one descriptor the
    record came from. A same-bytes replacement is then a different file, and an untouched file keeps its identity.
    This host's own rewrite of a running record carries that run's generation in the record itself, so it survives
    whether or not the ledger could note the rewrite; it counts only in the very shape that rewrite writes. An older
    host starts a later run afresh, without it.
    """
    carried = record.get(REWRITTEN)
    if (
        isinstance(carried, str)
        and carried
        and record.get("state") == "failed"
        and record.get("reason") == HOST_STOPPED
        and "workspace" not in record
    ):
        return carried, None
    run, started = str(record.get("run") or ""), str(record.get("started_at") or "")
    if run and started:
        with contextlib.suppress(ValueError):
            return f"{run}:{started}", datetime.fromisoformat(started)
    fields = {k: str(record.get(k) or "") for k in OBSERVED}
    body = json.dumps({"fields": fields, "file": version}, sort_keys=True)
    return "observed:" + hashlib.sha256(body.encode()).hexdigest(), None


def digest(version: str) -> str:
    """A file version as a stable key for a rewrite's receipt."""
    return hashlib.sha256(version.encode()).hexdigest()


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
