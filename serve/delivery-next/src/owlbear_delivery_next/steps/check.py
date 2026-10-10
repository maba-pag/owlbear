"""Person-only check environments: the host launches the Builder's recipe, verifies readiness and disposes of it."""

from __future__ import annotations

import contextlib
import os
import shlex
import signal
import subprocess
import threading
import time
import urllib.request
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import psutil

from owlbear_delivery_next import loop, sdk_adapter
from owlbear_delivery_next.models import ErrorKind, Exit, StepKind, Task, Waiting
from owlbear_delivery_next.steps import worktree

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from datetime import datetime

    from owlbear_delivery_next.models import Change, Environment, PersonCheck

READY_WITHIN = 60.0
GRACE = 5.0
type Action = Literal["launch", "keep", "dispose", "settle"]
type Pids = dict[int, float | None]
type Found = dict[int, str]
_LOCAL = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # loopback never goes through a proxy


def action(c: Change, *, live: bool, paths: Mapping[str, str]) -> Action | None:
    """What the host does with the Change's environment; dispose and settle come before any other writer."""
    e = c.env
    if e is None:
        return None
    person = next((p for p in c.checks if p.id == e.check), None)
    if c.finished_at or person is None or (c.step.kind, c.step.task) != (StepKind.CHECK, e.check):
        return "dispose"
    a = person.answer
    if a and a.inputs and loop.inputs_valid(a.inputs, loop.check_inputs(c, person, paths)):
        return "settle"  # by the result's recorded inputs (P5), whichever launch it was given for
    return "keep" if live and e.ready_at else "launch"


def fingerprints(c: Change, person: PersonCheck) -> dict[str, str]:
    """Current fingerprints of the paths one person-only check depends on."""
    root = Path(c.names.worktree)
    return worktree.fingerprints(root, person.paths) if person.paths and c.names.worktree and root.is_dir() else {}


def declared(c: Change) -> dict[str, str]:
    """Current fingerprints of every declared check's paths, against which a recorded answer stays valid."""
    return {k: v for p in c.checks for k, v in fingerprints(c, p).items()}


def answers(url: str) -> bool:
    """Whether the local readiness URL answers without an error status."""
    try:
        with _LOCAL.open(url, timeout=2) as response:
            return response.status < 400  # noqa: PLR2004 - HTTP error range
    except OSError, ValueError:
        return False


def created(pid: int) -> float | None:
    """Start time of a live process, None when unreadable; an unknown start is never signalled."""
    with contextlib.suppress(psutil.Error):
        return psutil.Process(pid).create_time()
    return None


def members(pgid: int, leader: float | None = None) -> Found:
    """Live members of one recorded group; none once its id names a newer process, as then the group ended."""
    found: Found = {}
    for p in psutil.process_iter(["name", "status", "create_time"]):
        with contextlib.suppress(OSError, psutil.Error):
            if p.info["status"] == psutil.STATUS_ZOMBIE or os.getpgid(p.pid) != pgid:
                continue
            if p.pid == pgid and leader is not None and abs(p.info["create_time"] - leader) >= 1.0:
                return {}
            found[p.pid] = p.info["name"] or ""
    return found


def remaining(
    e: Environment, alive: sdk_adapter.Observe = sdk_adapter.alive, group: Callable[..., Found] = members
) -> Found:
    """Recorded PIDs alive or unobservable, and every live member of the recorded group."""
    found: Found = {p: "" for p, t in e.pids.items() if alive(p, t) is not False}
    return found | (group(e.pgid, e.pids.get(e.pgid)) if e.pgid else {})


def dispose(e: Environment) -> Found:
    """Signal the whole group, even without its leader, and the recorded PIDs, TERM then KILL; return what remains."""
    left: Found = {}
    for sig, wait in ((signal.SIGTERM, GRACE), (signal.SIGKILL, 2.0)):
        if not (left := remaining(e)):
            return {}
        sdk_adapter.kill(e.pids, sig)
        if e.pgid and e.pgid != os.getpgrp() and members(e.pgid, e.pids.get(e.pgid)):
            with contextlib.suppress(OSError):
                os.killpg(e.pgid, sig)
        end = time.monotonic() + wait
        while (left := remaining(e)) and time.monotonic() < end:
            time.sleep(0.2)
    return left


def start(e: Environment, root: Path, log: Path) -> subprocess.Popen[bytes] | None:
    """Spawn the recipe as leader of its own session and group; the caller records it before waiting."""
    try:
        with log.open("ab") as out:
            proc = subprocess.Popen(  # noqa: S603 - argument vector of an allow-listed launch command
                shlex.split(e.command),
                cwd=root / e.directory,
                stdin=subprocess.DEVNULL,
                stdout=out,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
    except OSError, ValueError:
        return None
    threading.Thread(target=proc.wait, daemon=True).start()  # reaps the leader whenever it ends
    return proc


def ready(e: Environment, proc: subprocess.Popen[bytes]) -> Pids | None:
    """Wait for the readiness URL; return the group's PIDs once it answers, else None."""
    end = time.monotonic() + READY_WITHIN
    while time.monotonic() < end and proc.returncode is None:
        if answers(e.ready_url):
            return e.pids | {p: created(p) for p in members(proc.pid, e.pids.get(proc.pid))}
        time.sleep(0.5)
    return None


def pending(c: Change, e: Environment) -> loop.StepResult:
    """The check waits on the owner once its environment answers."""
    person = next(p for p in c.checks if p.id == e.check)
    reason = f"{'; '.join(person.steps) or person.id} · {e.ready_url}"
    a = person.answer
    if a and a.inputs and (what := loop.changed(a.inputs, loop.check_inputs(c, person, declared(c)))):
        reason += f" · asked again: changed {', '.join(what)}"
    return loop.StepResult(exit=Exit.PENDING, waiting=Waiting.PERSON_CHECK, who="you", reason=reason)


def failed(reason: str) -> loop.StepResult:
    """Preparation or readiness failed: the check is prepared again."""
    cause = loop.cause_key(ErrorKind.PROJECT_ENV, StepKind.CHECK, "environment")
    return loop.StepResult(exit=Exit.RETRY, cause=cause, reason=reason)


def settle(c: Change, now: datetime, paths: Mapping[str, str]) -> Change:
    """A pass moves on, judged against the current *paths*; a fail goes back to build with the owner's note (H2)."""
    person = next(p for p in c.checks if p.id == c.step.task)
    answer = person.answer
    if answer is None or answer.passed:
        reason = f"{person.id} passed for you at {now:%H:%M}"
        return loop.apply(c, loop.StepResult(exit=Exit.DONE, reason=reason, paths=dict(paths)), now)
    tasks = c.plan.tasks if c.plan else []
    last = tasks[-1] if tasks else Task(id="t0", title="")
    title = f"Fix: the check {person.id} failed for the owner: {answer.text}"
    fix = Task(id=f"t{len(tasks) + 1}", title=title, scope=last.scope, checks=last.checks, origin="person-check")
    cause = loop.cause_key(ErrorKind.CHECKS, StepKind.CHECK, person.id)
    result = loop.StepResult(
        exit=Exit.BACK, back_to=StepKind.BUILD, cause=cause, reason=f"{person.id} failed for you", fix_task=fix
    )
    after = loop.apply(c, result, now)
    for p in after.checks:
        if p.id == person.id and p.answer:
            p.answer.inputs = None  # a settled failure settles no later round
    return after
