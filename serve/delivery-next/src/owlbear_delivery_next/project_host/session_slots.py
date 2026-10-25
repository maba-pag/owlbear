"""A project host's share of the machine's session slots (TD-336, TD-105).

A step's agent sessions are reserved before its runner launches and given back once its processes are confirmed
gone. A step reserves none when it never starts an agent session (publish, follow, merge, cleanup) and one once its
decision pick waits for a session; up to the project's limit for a visual check that captures and judges (its judges
run in waves of the grant), else one. The grant is written with the runner's record, so a restarted machine host
counts it again before granting anything. A design pack update takes one slot for each of its sessions while it runs.
"""

from __future__ import annotations

import dataclasses
import subprocess
import threading
import uuid
from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts.failures import cause_key
from owlbear_delivery_next.change_contracts.models import ErrorKind, StepKind
from owlbear_delivery_next.design_packs import design_pack
from owlbear_delivery_next.local_system.slots import PACK
from owlbear_delivery_next.pack_runs import pack_job, pack_replay, pack_run
from owlbear_delivery_next.state_store import project_home
from owlbear_delivery_next.state_store.store import StoreError
from owlbear_delivery_next.workflow_steps import check, pick

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from owlbear_delivery_next.change_contracts.models import Change, Step
    from owlbear_delivery_next.design_packs.calibration import Replay
    from owlbear_delivery_next.local_system.maintenance import Maintenance
    from owlbear_delivery_next.pack_runs.pack_candidate import Candidate
    from owlbear_delivery_next.pack_runs.pack_job import Job, Live
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


def _queued(host: Host, key: str, note: Callable[[str], None]) -> None:
    said, turn = False, threading.Event()
    while not host.slots.take(project(host), key, 1, limit(host), turn.set):
        if host.closed() or host.stopped.is_set():
            msg = "OwlBear stops; the update did not get a session slot"
            raise design_pack.PackError(msg)
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
    """Hold the uncertain pack work a last host left running, whether or not it has PIDs or a directory."""
    maintenance, legacy = job.maintenance, job.store.root / pack_run.UPDATER
    if maintenance is None:
        return
    if job.interrupted is not None:
        run = job.interrupted
        source = f"{key}:run:{run['run']}:{run['started_at']}"  # the same run adopted once, wherever its folder lies
        maintenance.adopt(source, key, "pack", {}, interrupted=True, workspace=run["workspace"] or str(legacy))
    elif "workspace" not in job.state and (legacy.is_dir() or pack_job.legacy_uncertain(job.state)):
        maintenance.adopt_uncertain(f"{key}:legacy", key, "pack", workspace=str(legacy))


def unloaded(maintenance: Maintenance, key: str, repo: Path) -> None:
    """Hold the uncertain pack work of a project whose store did not open, read from its folder without opening it.

    A record that cannot be read is held too: unreadable ownership is never taken for none (TD-242).
    """
    try:
        root = project_home.current(repo)
    except OSError, subprocess.CalledProcessError, StoreError:
        maintenance.adopt(f"{key}:unlocated", key, "pack", {}, interrupted=True)  # its folder cannot be told
        return
    if root is None:
        return
    legacy = root / pack_run.UPDATER
    try:
        kept = pack_job.read_only(root)
    except OSError, ValueError:
        maintenance.adopt(f"{key}:unreadable", key, "pack", {}, interrupted=True, workspace=str(legacy))
        return
    if kept is None:
        if legacy.is_dir():
            maintenance.adopt_uncertain(f"{key}:legacy", key, "pack", workspace=str(legacy))
    elif kept.get("state") == "running":
        run, started = str(kept.get("run") or ""), str(kept.get("started_at") or "")
        workspace = str(kept.get("workspace") or legacy)
        maintenance.adopt(f"{key}:run:{run}:{started}", key, "pack", {}, interrupted=True, workspace=workspace)
    elif "workspace" not in kept and (legacy.is_dir() or pack_job.legacy_uncertain(kept)):
        maintenance.adopt_uncertain(f"{key}:legacy", key, "pack", workspace=str(legacy))


def pack_live(host: Host | None, live: Live, note: Callable[[str], None]) -> Live:
    """*live* whose updater, challenger and replay sessions enter the SDK only as maintenance owning a project slot."""

    def owned(work: Callable[[Session], Run]) -> Callable[[Session], Run]:
        def run(cfg: Session) -> Run:
            if host is None or host.maintenance is None:
                msg = "the machine's maintenance ownership is not bound; the design pack's sessions cannot start"
                raise design_pack.PackError(msg)
            return host.maintenance.run(cfg, work, project=project(host), slot=admit(host, note), kind="pack")

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
