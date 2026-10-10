"""Person-only check environments: the host launches the Builder's recipe, verifies readiness and disposes of it."""

from __future__ import annotations

import contextlib
import shlex
import signal
import subprocess
import time
import urllib.request
from typing import TYPE_CHECKING, Literal

import psutil

from owlbear_delivery_next import loop, sdk_adapter
from owlbear_delivery_next.models import ErrorKind, Exit, StepKind, Task, Waiting

if TYPE_CHECKING:
    from datetime import datetime
    from pathlib import Path

    from owlbear_delivery_next.models import Change, Environment

READY_WITHIN = 60.0
GRACE = 5.0
type Action = Literal["launch", "keep", "dispose", "settle"]
type Pids = dict[int, float | None]
_LOCAL = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # loopback never goes through a proxy


def action(c: Change, *, live: bool) -> Action | None:
    """What the host does with the Change's environment; dispose and settle come before any other writer."""
    e = c.env
    if e is None:
        return None
    person = next((p for p in c.checks if p.id == e.check), None)
    if c.finished_at or person is None or (c.step.kind, c.step.task) != (StepKind.CHECK, e.check):
        return "dispose"
    if person.answer and e.ready_at and person.answer.at >= e.ready_at:
        return "settle"
    return "keep" if live else "launch"


def answers(url: str) -> bool:
    """Whether the local readiness URL answers without an error status."""
    try:
        with _LOCAL.open(url, timeout=2) as response:
            return response.status < 400  # noqa: PLR2004 - HTTP error range
    except OSError, ValueError:
        return False


def dispose(pids: Pids) -> tuple[int, ...]:
    """End the recorded processes and the groups they lead; return those still present."""
    sdk_adapter.kill(pids, signal.SIGTERM)
    end = time.monotonic() + GRACE
    while not (t := sdk_adapter.verdict(pids, sdk_adapter.alive)).confirmed and time.monotonic() < end:
        time.sleep(0.2)
    if not t.confirmed:
        sdk_adapter.kill(pids, signal.SIGKILL)
        time.sleep(0.5)
        t = sdk_adapter.verdict(pids, sdk_adapter.alive)
    return (*t.survivors, *t.unknown)


def launch(e: Environment, root: Path, log: Path) -> Pids | None:
    """Start the recipe in its own process group; return its PIDs once the URL answers, else end it and None."""
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
        pids: Pids = {proc.pid: psutil.Process(proc.pid).create_time()}
    except OSError, ValueError, psutil.Error:
        return None
    end = time.monotonic() + READY_WITHIN
    while time.monotonic() < end and proc.poll() is None:
        if answers(e.ready_url):
            kids = psutil.Process(proc.pid).children(recursive=True)
            return pids | {k.pid: k.create_time() for k in kids}
        time.sleep(0.5)
    dispose(pids)
    with contextlib.suppress(subprocess.TimeoutExpired):
        proc.wait(GRACE)
    return None


def pending(c: Change, e: Environment) -> loop.StepResult:
    """The check waits on the owner once its environment answers."""
    person = next(p for p in c.checks if p.id == e.check)
    reason = f"{'; '.join(person.steps) or person.id} · {e.ready_url}"
    return loop.StepResult(exit=Exit.PENDING, waiting=Waiting.PERSON_CHECK, who="you", reason=reason)


def failed(reason: str) -> loop.StepResult:
    """Preparation or readiness failed: the check is prepared again."""
    cause = loop.cause_key(ErrorKind.PROJECT_ENV, StepKind.CHECK, "environment")
    return loop.StepResult(exit=Exit.RETRY, cause=cause, reason=reason)


def settle(c: Change, now: datetime) -> loop.StepResult:
    """A pass moves on; a fail goes back to build with the owner's note as a fix task (H2)."""
    person = next(p for p in c.checks if p.id == c.step.task)
    answer = person.answer
    if answer is None or answer.passed:
        return loop.StepResult(exit=Exit.DONE, reason=f"{person.id} passed for you at {now:%H:%M}")
    tasks = c.plan.tasks if c.plan else []
    last = tasks[-1] if tasks else Task(id="t0", title="")
    title = f"Fix: the check {person.id} failed for the owner: {answer.text}"
    fix = Task(id=f"t{len(tasks) + 1}", title=title, scope=last.scope, checks=last.checks, origin="person-check")
    cause = loop.cause_key(ErrorKind.CHECKS, StepKind.CHECK, person.id)
    return loop.StepResult(
        exit=Exit.BACK, back_to=StepKind.BUILD, cause=cause, reason=f"{person.id} failed for you", fix_task=fix
    )
