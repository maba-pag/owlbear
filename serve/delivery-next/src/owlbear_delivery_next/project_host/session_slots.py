"""A project host's share of the machine's session slots (TD-336, TD-105).

A step's agent sessions are reserved before its runner launches and given back once its processes are confirmed
gone. A step reserves none when it never starts an agent session (publish, follow, merge, cleanup), up to the
project's limit for a visual check that captures and judges (its judges run in waves of the grant), else one. The
grant is written with the runner's record, so a restarted machine host counts it again before granting anything. A
design pack update takes one slot for each of its sessions while it runs.
"""

from __future__ import annotations

import contextlib
import dataclasses
import threading
import uuid
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.change_contracts.models import StepKind
from owlbear_delivery_next.design_packs import design_pack
from owlbear_delivery_next.local_system.slots import PACK
from owlbear_delivery_next.state_store.store import StoreError
from owlbear_delivery_next.workflow_steps import check

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from owlbear_delivery_next.change_contracts.models import Change, Step
    from owlbear_delivery_next.pack_runs.pack_job import Job, Live
    from owlbear_delivery_next.project_host.host import Host

NO_AGENT = frozenset({StepKind.PUBLISH, StepKind.FOLLOW, StepKind.MERGE, StepKind.CLEANUP})
ALL = 1_000  # as many as the project's limit and the machine's free slots allow
WAIT = 2.0  # seconds between a pack session's checks for a stop while it waits


def wanted(c: Change, step: Step | None) -> int:
    """The sessions a runner for *step* may run at once: 0 without an agent, all its judges may use, else 1."""
    if step is None or step.kind in NO_AGENT:
        return 0
    return ALL if check.capturing(c) or step.kind == StepKind.TESTS else 1


def project(host: Host) -> str:
    """The project's key among the machine's slots: its id on the machine host, else its store."""
    return host.record.project or str(host.store.root)


def limit(host: Host) -> int:
    """The project's sessions at once; 1 while its settings do not read, which stops its runners anyway."""
    try:
        return host.store.settings().sessions
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
    return f"this machine {used} of {total}, this project {mine} of {limit(host)}"


@contextlib.contextmanager
def one(host: Host, note: Callable[[str], None]) -> Iterator[None]:
    """Hold one slot of the project for a pack update's session, waiting for it in the job's thread."""
    key = f"{PACK}{uuid.uuid4().hex[:8]}"
    try:
        _queued(host, key, note)
    except BaseException:
        host.slots.cancel(project(host), key)
        raise
    try:
        yield
    finally:
        host.slots.give(project(host), key)


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


def packed(host: Host, job: Job) -> Job:
    """*job* whose updater, challenger and replay sessions each hold one of the project's slots; its wait is logged."""
    job.live = pack_live(host, job.live, job.log)
    return job


def pack_live(host: Host, live: Live, note: Callable[[str], None]) -> Live:
    """*live* whose updater, challenger and replay sessions each hold one of the project's slots."""

    def gated[**P](work: Callable[P, Any]) -> Callable[P, Any]:
        def run(*args: P.args, **kwargs: P.kwargs) -> Any:  # noqa: ANN401 - whatever the session returns
            with one(host, note):
                return work(*args, **kwargs)

        return run

    held = {"update": gated(live.update), "challenge": gated(live.challenge), "replay": gated(live.replay)}
    return dataclasses.replace(live, **held)
