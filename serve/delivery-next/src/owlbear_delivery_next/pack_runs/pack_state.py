"""The persisted design-pack run vocabulary and read-only ownership evidence."""

from __future__ import annotations

import contextlib
import fcntl
import hashlib
import json
import os
import stat
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.local_system import local_home
from owlbear_delivery_next.local_system.storage_io import atomic_write

if TYPE_CHECKING:
    from collections.abc import Callable
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


def open_record(path: Path) -> int:
    """A descriptor for the run file at *path*, opened without following a link or waiting on a pipe; regular only.

    Raises FileNotFoundError when there is no file, and OSError or ValueError when it is anything but a regular file
    that can be opened: no other kind is ever read, or taken for absent. The descriptor is closed on every failure.
    """
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        regular = stat.S_ISREG(os.fstat(fd).st_mode)
    except BaseException:
        os.close(fd)
        raise
    if not regular:
        os.close(fd)
        msg = f"{path} is not a regular file"
        raise ValueError(msg)
    return fd


def read_fd(fd: int) -> tuple[dict[str, Any], str]:
    """The run *fd* holds and that file's version, both from the one open descriptor, which this always closes.

    The version is the file's identity and metadata as opened, so a replacement made after the open is not mixed
    into what was read. Raises OSError or ValueError when the record cannot be read as a run.
    """
    try:
        source = os.fdopen(fd, encoding="utf-8")
    except BaseException:
        os.close(fd)
        raise
    with source as f:
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
        fd = open_record(path)
    except FileNotFoundError:
        return blank(), "absent"
    except OSError, ValueError:
        return blank(), ""
    try:
        kept, version = read_fd(fd)
    except OSError, ValueError:
        return blank(), ""
    return blank() | kept, version


def observed(root: Path) -> tuple[dict[str, Any], str] | None:
    """The last run as *root* holds it with its file version; None when it has no record. Reads without writing."""
    try:
        fd = open_record(root / FILE)
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
REWRITTEN = "interrupted_generation"  # the generation this host's own rewrite of a legacy record carries forward


def carried(record: dict[str, Any]) -> str:
    """The generation this host wrote into a legacy record, in the only shape it writes it.

    That shape is failed, uncertain and without a workspace. Any other record gets an empty answer, so a running or
    later record never borrows it.
    """
    kept = record.get(REWRITTEN)
    return kept if isinstance(kept, str) and kept and legacy_uncertain(record) else ""


def generation(record: dict[str, Any], version: str) -> tuple[str, datetime | None]:
    """A legacy run's identity: its proven run and start time, else a fingerprint of its fields and its file.

    The fingerprint binds the observed fields and the file's identity and version, read from the one descriptor the
    record came from. A same-bytes replacement is then a different file, and an untouched file keeps its identity.
    This host's own rewrite or settling of a legacy record carries that run's generation in the record itself, so it
    survives a ledger write that fails and a copy of the file; it counts only in the shape ``carried`` accepts. An
    older host starts a later run afresh, without it.
    """
    if kept := carried(record):
        return kept, None
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


def resolved(record: dict[str, Any], version: str, receipted: Callable[[str], str]) -> tuple[str, datetime | None]:
    """A legacy record's generation as every reader takes it, the receipt for its very version first.

    That is the run a rewrite of this very file version was receipted to, else the record's own: carried, proven or
    fingerprinted. *receipted* answers from the machine's ledger for a version's digest, empty when it holds no
    receipt, and raises when the ledger cannot be read: an unread receipt is never taken for none.
    """
    if version not in {"", "absent"} and (got := receipted(digest(version))):
        return got, None
    return generation(record, version)


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


def ended(record: dict[str, Any], state: str, reason: str) -> None:
    """End the run *record* names, as a Job writes it: its open stages failed or skipped, no question left open."""
    for s in record["stages"]:
        if s["result"] in OPEN:
            s["result"] = "failed" if s["result"] == "running" and state == "failed" else "skipped"
    record |= {"state": state, "stage": "", "ended_at": now(), "reason": reason, "questions": []}
    record["context"] = None


def settle(root: Path, *, receipted: Callable[[str], str]) -> bool:
    """Carry a legacy record's generation into the record itself, before its store is copied; whether it wrote.

    A copy is another file, so a fingerprint would name another run: the generation carried in the record names the
    one this host saw, resolved as every reader resolves it (see ``resolved``), so a rewrite an earlier host receipted
    keeps the run it was receipted to. A running record without a workspace is ended as the Job's own rewrite ends it,
    still uncertain; an uncertain failed one keeps every field. A run stopped while it was being published is left as
    it is: no session runs then, its run and start prove it, and the Job's own startup puts its publication back to
    the owner with its context whole. Nothing is held, recovered or released here, and a record already carrying its
    generation, a modern one or any other is left as it is. Raises OSError or ValueError when the record cannot be read
    or written, and whatever *receipted* raises: an unreadable record or ledger is never taken for a settled one.
    """
    got = observed(root)
    if got is None:
        return False
    record, version = got
    if "workspace" in record or carried(record):
        return False
    publishing = record["state"] == "running" and bool((record.get("context") or {}).get("publication"))
    if publishing or not (record["state"] == "running" or legacy_uncertain(record)):
        return False
    record[REWRITTEN] = resolved(record, version, receipted)[0]
    if record["state"] == "running":
        ended(record, "failed", HOST_STOPPED)  # as the Job's own rewrite ends it, carrying the generation it saw
    atomic_write(root / FILE, json.dumps(record, indent=1) + "\n")
    return True


def last(store: Store) -> dict[str, Any] | None:
    """The last run's state, ending and times, for the Maintenance page; None when it never ran or cannot be read."""
    try:
        fd = open_record(store.root / FILE)
    except OSError, ValueError:
        return None
    try:
        source = os.fdopen(fd, encoding="utf-8")
    except BaseException:
        os.close(fd)
        raise
    try:
        with source:
            kept = json.load(source)
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
