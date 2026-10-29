"""A project host's share of the machine's session slots (TD-336, TD-105).

A step's agent sessions are reserved before its runner launches and given back once its processes are confirmed
gone. A step reserves none when it never starts an agent session (publish, follow, merge, cleanup) and one once its
decision pick waits for a session; up to the project's limit for a visual check that captures and judges (its judges
run in waves of the grant), else one. The grant is written with the runner's record, so a restarted machine host
counts it again before granting anything. An Impeccable update takes one slot for each of its sessions while it runs.
"""

from __future__ import annotations

import dataclasses
import subprocess
import threading
import uuid
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.change_contracts.failures import cause_key
from owlbear_delivery_next.change_contracts.models import ErrorKind, StepKind
from owlbear_delivery_next.impeccable import pack_files
from owlbear_delivery_next.impeccable_runs import pack_job, pack_replay, pack_run, pack_state
from owlbear_delivery_next.local_system.slots import PACK
from owlbear_delivery_next.runtimes import maintained
from owlbear_delivery_next.state_store import project_home
from owlbear_delivery_next.state_store.store import StoreError
from owlbear_delivery_next.workflow_steps import check, pick

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import datetime
    from pathlib import Path

    from owlbear_delivery_next.change_contracts.models import Change, Step
    from owlbear_delivery_next.impeccable.calibration import Replay
    from owlbear_delivery_next.impeccable_runs.pack_candidate import Candidate
    from owlbear_delivery_next.impeccable_runs.pack_job import Job, Live
    from owlbear_delivery_next.local_system.maintenance import Maintenance
    from owlbear_delivery_next.project_host.host import Host
    from owlbear_delivery_next.runtimes.sdk_adapter import Session
    from owlbear_delivery_next.runtimes.session_result import Run
    from owlbear_delivery_next.state_store.store import Store

NO_AGENT = frozenset({StepKind.PUBLISH, StepKind.FOLLOW, StepKind.MERGE, StepKind.CLEANUP})
ALL = 1_000  # as many as the project's limit and the machine's free slots allow
WAIT = 2.0  # seconds between a pack session's checks for a stop while it waits


def wanted(c: Change, step: Step | None) -> int:
    """The sessions a runner for *step* may run at once: 0 without an agent, all its judges may use, else 1.

    A step without an agent whose decision pick waits for a session (`decisions_gate`) gets one for it.
    """
    if step is None:
        return 0
    if step.kind in NO_AGENT:
        o = c.outcome
        return int(o is not None and o.cause == cause_key(ErrorKind.NETWORK, step.kind, pick.LABEL))
    return ALL if check.capturing(c) or step.kind == StepKind.TESTS else 1


def project(host: Host) -> str:
    """The project's key among the machine's slots: its id on the machine host, else its store."""
    return host.record.project or str(host.store.root)


def limit(host: Host) -> int:
    """The project's sessions at once; 1 while its settings do not read, which stops its runners anyway.

    While no layer sets it, none: code ships no defaults, and the Settings page shows it unset (2026-10-23).
    """
    try:
        return host.store.settings().sessions or 0
    except StoreError:
        return 1


def reserve(host: Host, slug: str) -> int | None:
    """The sessions *slug*'s runner may run at once, reserved now; None while it waits for its turn."""
    want = host.wants.pop(slug, 1)
    granted = host.slots.take(project(host), slug, want, limit(host)) if want else 0
    if want and not granted:
        host.asked.add(slug)  # its wait is shown, and kept, once the pass ends
        return None
    return granted


def release(host: Host, slug: str) -> None:
    """Give back what *slug*'s ended runner held."""
    host.slots.give(project(host), slug)


def join(host: Host) -> None:
    """Take part in the machine's slots: be woken for a free slot, and hold again what live runners reserved."""
    host.slots.waker(project(host), host.wake.set)
    host.slots.restore(project(host), {s: r.sessions for s in host.store.slugs() if (r := host.runner(s))})


def leave(host: Host) -> None:
    """A stopped project waits for nothing; what its runners hold stays counted until it loads again."""
    host.slots.leave(project(host))


def waiting(host: Host, slug: str) -> str:
    """How full the slots are, while *slug* waits for one; else empty."""
    if slug not in host.waiting:
        return ""
    used, total, mine = host.slots.counts(project(host))
    try:
        unset = host.store.settings().sessions is None
    except StoreError:
        unset = False
    said = " (sessions at once is unset: set it on the Settings page)" if unset else ""
    return f"this machine {used} of {total}, this project {mine} of {limit(host)}{said}"


def admit(host: Host, note: Callable[[str], None]) -> str:
    """Wait for one of the project's slots for a pack update's session and return its key.

    The slot is given back only by the maintenance ownership, which keeps it while the session's processes are unproven.
    """
    key = f"{PACK}{uuid.uuid4().hex[:8]}"
    try:
        _queued(host, key, note)
    except BaseException:
        host.slots.cancel(project(host), key)
        raise
    return key


def _still_admitted(host: Host) -> None:
    """Refuse a session whose slot was granted while a stop began: nothing enters the SDK once the stop has begun.

    Checked under the launch lock, so a stop either finds the session already counted or refuses it here.
    """
    with host.launching:
        if host.closed() or host.draining():
            msg = "OwlBear stops; Impeccable's session did not start"
            raise pack_files.PackError(msg)


def _queued(host: Host, key: str, note: Callable[[str], None]) -> None:
    said, turn = False, threading.Event()
    while not host.slots.take(project(host), key, 1, limit(host), turn.set):
        if host.closed() or host.stopped.is_set() or host.draining():
            msg = "OwlBear stops; the update did not get a session slot"
            raise pack_files.PackError(msg)
        if not said:
            note("waiting for a session slot")
            said = True
        turn.wait(WAIT)
        turn.clear()


def packed(host: Host | None, job: Job) -> Job:
    """*job* whose updater, challenger and replay sessions each hold one of the project's slots; its wait is logged.

    A run the last host left open, or a legacy updater repository no ledger lease covers, is adopted as unknown work
    so it is never removed. Without a running host there is no maintenance to own a session, so the sessions refuse.
    """
    job.live = pack_live(host, job.live, job.log)
    job.maintenance = host.maintenance if host is not None else None
    if host is not None and job.maintenance is not None:
        interrupted(job, project(host))
    return job


def interrupted(job: Job, key: str) -> None:
    """Hold the uncertain pack work a last host left running, whether or not it has PIDs or a directory.

    Whatever the Job's startup did with the record, kept it as read, ended an interrupted run or set a stopped
    publication waiting, only the file still holding that very record at that version is what the Job saw: anything
    written over it is restored as it stands, held before any admission, and never receipted to the Job's run.
    """
    maintenance, legacy = job.maintenance, job.store.root / pack_run.UPDATER
    if maintenance is None:
        return
    seen = pack_state.read_version(job.store.root / pack_state.FILE)  # one read, compared and restored alike
    current = pack_state.holds(seen, job.state, job.version)
    if job.interrupted is not None:
        run = job.interrupted
        if not (run["workspace"] and maintenance.owns(run["workspace"])):  # owned: importing it again holds it twice
            notes: tuple[str, ...] = ()
            if current and not run["workspace"]:  # the file holds its own rewrite at that version: receipted to it
                notes = (maintenance.receipt_note(key, pack_state.digest(job.version), run["generation"]),)
            _hold(maintenance, key, run["workspace"] or str(legacy), run["generation"], notes=notes)  # one save
    elif job.version == "":
        maintenance.adopt_uncertain(f"{key}:unreadable", key, "pack", workspace=str(legacy))
    elif "workspace" not in job.state and (legacy.is_dir() or pack_job.legacy_uncertain(job.state)):
        _adopt_legacy(maintenance, key, legacy, job.state, job.version)
    if not current:
        restore(maintenance, key, job.store.root, seen)


def _identity(
    maintenance: Maintenance, key: str, record: dict[str, object], version: str
) -> tuple[str, datetime | None]:
    """A legacy record's generation: the one an older host's rewrite of this file version was given, else its own."""
    return pack_state.resolved(record, version, lambda found: maintenance.receipted(key, found))


def _hold(  # noqa: PLR0913 - one run's identity and what its hold records with it
    maintenance: Maintenance,
    key: str,
    workspace: str,
    generation: str,
    started: datetime | None = None,
    *,
    notes: tuple[str, ...] = (),
) -> None:
    """Hold one run's uncertain work once per generation; a recovered generation is not held again.

    *notes* are recorded in the same ledger save, so a rewrite's receipt never lands without its hold, or after it.
    """
    maintenance.adopt_uncertain(
        f"{key}:{workspace}:{generation}", key, "pack", workspace=workspace, generation=generation, started=started,
        notes=notes,
    )  # fmt: skip


def _adopt_legacy(maintenance: Maintenance, key: str, legacy: Path, record: dict[str, object], version: str) -> None:
    """Hold a legacy updater repository for the record that left it; a folder with no record has no generation."""
    if version == "absent":
        maintenance.adopt_uncertain(f"{key}:legacy", key, "pack", workspace=str(legacy))
        return
    generation, started = _identity(maintenance, key, record, version)
    maintenance.adopt_uncertain(
        f"{key}:legacy", key, "pack", workspace=str(legacy), generation=generation, started=started
    )


def unloaded(maintenance: Maintenance, key: str, repo: Path) -> None:
    """Hold the uncertain pack work of a project whose store did not open, read from its folder without opening it.

    A record that cannot be read is held too: unreadable ownership is never taken for none (TD-242).
    """
    try:
        root = project_home.current(repo)
    except OSError, subprocess.CalledProcessError, StoreError:
        maintenance.adopt_uncertain(f"{key}:unlocated", key, "pack", workspace=str(repo))  # its folder cannot be told
        return
    if root is None:
        return
    restore(maintenance, key, root)


def restore(maintenance: Maintenance, key: str, root: Path, seen: tuple[dict[str, Any], str] | None = None) -> None:
    """Hold the uncertain pack work the run file in *root* records, as *seen* read it, else as read now; never write.

    *seen* is a whole, stable read by ``pack_state.read_version``: "absent" when there was no file, "" when it could
    not be read. A record that cannot be read is held too: unreadable ownership is never taken for none (TD-242).
    """
    legacy = root / pack_run.UPDATER
    kept, version = seen if seen is not None else pack_state.read_version(root / pack_state.FILE)
    if version == "":
        maintenance.adopt_uncertain(f"{key}:unreadable", key, "pack", workspace=str(legacy))
        return
    if version == "absent":
        if legacy.is_dir():
            _adopt_legacy(maintenance, key, legacy, {}, "absent")
        return
    if kept.get("state") == "running":
        if kept.get("workspace") and maintenance.owns(str(kept["workspace"])):
            return  # a modern run the ledger already owns; the same record is not a second hold
        generation, started = _identity(maintenance, key, kept, version)
        _hold(maintenance, key, str(kept.get("workspace") or legacy), generation, started)
    elif "workspace" not in kept and (legacy.is_dir() or pack_job.legacy_uncertain(kept)):
        _adopt_legacy(maintenance, key, legacy, kept, version)


def pack_live(host: Host | None, live: Live, note: Callable[[str], None]) -> Live:
    """*live* whose updater, challenger and replay sessions enter the SDK only as maintenance owning a project slot."""

    def owned(work: Callable[[Session], Run]) -> Callable[[Session], Run]:
        def run(cfg: Session) -> Run:
            if host is None or host.maintenance is None:
                msg = "the machine's maintenance ownership is not bound; Impeccable's sessions cannot start"
                raise pack_files.PackError(msg)
            slot = admit(host, note)
            try:
                _still_admitted(host)
            except BaseException:
                release(host, slot)  # refused after its grant: the slot goes back before any SDK entry
                raise
            return maintained.run_owned(host.maintenance, cfg, work, project=project(host), slot=slot, kind="pack")

        return run

    def update(store: Store, cfg: Session) -> Run:
        return owned(lambda bound: live.update(store, bound))(cfg)

    def challenge(store: Store, cfg: Session) -> Run:
        return owned(lambda bound: live.challenge(store, bound))(cfg)

    def replay(
        store: Store,
        candidate: Candidate | None,
        run: Callable[[Session], Run] | None = None,
        *,
        keep: Callable[[Path], bool] | None = None,
    ) -> Replay:
        return live.replay(store, candidate, owned(run or pack_replay.sdk_run), keep=keep)

    return dataclasses.replace(live, update=update, challenge=challenge, replay=replay)
