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
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

import psutil

from owlbear_delivery_next.change_contracts import evidence, failures
from owlbear_delivery_next.change_contracts.models import VISUAL, ErrorKind, Exit, StepKind, Task, Waiting
from owlbear_delivery_next.change_flow import loop, worktree
from owlbear_delivery_next.local_system import processes

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from owlbear_delivery_next.change_contracts.models import Change, Environment, PersonCheck

READY_WITHIN = 60.0
GRACE = 5.0
WITHIN = 600.0  # seconds per install or preparation command
SHOWN = 80  # characters of a command a note quotes, so a long path never pushes out why it failed
PIDFILE = "env.pid"  # the launched recipe's pid, written by its wrapper before the recipe runs
CAUSE = 160  # characters of its last output line; a whole note then fits a caller's 300 behind a 45-character prefix
type Action = Literal["launch", "keep", "dispose", "settle"]
type Pids = dict[int, float | None]
type Found = dict[int, str]
_LOCAL = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # loopback never goes through a proxy


def journal(log: Callable[[dict[str, Any]], None], pids: Pids) -> None:
    """Persist started PIDs first, so the host finds them if this runner dies."""
    log({"event": "pids", "at": datetime.now(UTC).isoformat(), "pids": {str(p): t for p, t in pids.items()}})


def shown(argv: list[str]) -> str:
    """The command as a note quotes it: its start and its end, which name the program, script and arguments."""
    text = shlex.join(argv)
    return text if len(text) <= SHOWN else f"{text[: SHOWN // 3]}…{text[-(SHOWN - SHOWN // 3 - 1) :]}"


def run(argv: list[str], cwd: Path, log: Callable[[dict[str, Any]], None], env: Mapping[str, str] | None = None) -> str:
    """Run one command the owner made known in its own group, within ``WITHIN``; a note if it failed, else empty."""
    within, cmd = WITHIN, shown(argv)
    try:
        proc = subprocess.Popen(  # noqa: S603 - argument vector of a command the owner made known
            argv, cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            start_new_session=True, env=env,
        )  # fmt: skip
    except OSError as exc:
        return f"`{cmd}` did not start: {exc}"
    born = created(proc.pid)
    try:
        journal(log, {proc.pid: born})
        out, _ = proc.communicate(timeout=within)
    except subprocess.TimeoutExpired:
        return f"`{cmd}` took over {within:.0f} s"
    finally:  # timed out, interrupted or done: nothing of its group outlives the command
        if members(proc.pid, born):  # not once its id names a newer group
            with contextlib.suppress(OSError):
                os.killpg(proc.pid, signal.SIGKILL)
        with contextlib.suppress(subprocess.TimeoutExpired):
            proc.communicate(timeout=5)  # an escaped child may hold the pipe open
    if proc.returncode:
        last = next((x for x in reversed(out.decode(errors="replace").splitlines()) if x.strip()), "")
        return f"`{cmd}` failed: {last.strip()[:CAUSE]}"
    return ""


def action(c: Change, *, live: bool, paths: Mapping[str, str]) -> Action | None:
    """What the host does with the Change's environment; dispose and settle come before any other writer."""
    e = c.env
    if e is None:
        return None
    person = next((p for p in c.checks if p.id == e.check), None)
    known = person is not None or e.check == VISUAL
    stale = (c.step.kind, c.step.task) != (StepKind.CHECK, e.check)
    if c.finished_at or not known or stale or loop.owner_gated(c):  # a gated check relaunches on its rerun
        return "dispose"
    if person is None:
        if c.intent.abandoned_at or c.stop is not None:
            return "dispose"  # a terminal exit of the visual task; done moves the step on
        return "keep" if live and e.ready_at else "launch"  # the runner captures and settles the visual check
    a = person.answer
    if a and a.inputs and evidence.check_valid(a.inputs, evidence.check_inputs(c, person, paths)):
        return "settle"  # by the result's recorded inputs (P5), whichever launch it was given for
    return "keep" if live and e.ready_at else "launch"


def owned(e: Environment, pid: int) -> bool:
    """The process belongs to the host-started check environment, which the host disposes of itself."""
    if pid in e.pids:
        return True
    try:
        return e.pgid is not None and os.getpgid(pid) == e.pgid
    except OSError:
        return False


def capturing(c: Change) -> bool:
    """The visual check's environment answers and the runner captures and judges it."""
    e = c.env
    return bool(e and e.check == VISUAL and e.ready_at) and (c.step.kind, c.step.task) == (StepKind.CHECK, VISUAL)


def fingerprints(c: Change, person: PersonCheck) -> dict[str, str]:
    """Current fingerprints of the paths one person-only check depends on; the tree id when it declares none."""
    root = Path(c.names.worktree)
    if not (c.names.worktree and root.is_dir()):
        return {}
    return worktree.fingerprints(root, person.paths) if person.paths else {evidence.TREE: worktree.tree(root)}


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
    return processes.members({pgid: leader}, sessions=False)


def remaining(
    e: Environment, alive: processes.Observe = processes.alive, group: Callable[..., Found] = members
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
        processes.kill(e.pids, sig)
        if e.pgid and e.pgid != os.getpgrp() and members(e.pgid, e.pids.get(e.pgid)):
            with contextlib.suppress(OSError):
                os.killpg(e.pgid, sig)
        end = time.monotonic() + wait
        while (left := remaining(e)) and time.monotonic() < end:
            time.sleep(0.2)
    return left


def start(
    e: Environment, root: Path, log: Path, env: Mapping[str, str] | None = None, pidfile: Path | None = None
) -> subprocess.Popen[bytes] | None:
    """Spawn the recipe as leader of its own session and group; *env* is a test copy's isolated environment.

    With *pidfile*, a shell writes its pid there and then becomes the recipe, so a host that stops before it records
    the group can still find it (``recovered``).
    """
    try:
        argv = shlex.split(e.command)
        if pidfile is not None:
            pidfile.unlink(missing_ok=True)
            argv = ["/bin/sh", "-c", 'echo $$ > "$0"; exec "$@"', str(pidfile), *argv]
        with log.open("ab") as out:
            proc = subprocess.Popen(  # noqa: S603 - argument vector of the Builder's launch recipe
                argv,
                cwd=root / e.directory,
                stdin=subprocess.DEVNULL,
                stdout=out,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                env=env,
            )
    except OSError, ValueError:
        return None
    threading.Thread(target=proc.wait, daemon=True).start()  # reaps the leader whenever it ends
    return proc


def recovered(e: Environment, pidfile: Path) -> Environment:
    """A launch whose group was never recorded, with its leader's pid from *pidfile* and the file's time as its start.

    No file, or one older than the launch, leaves *e* unchanged. The time bounds the leader's start, so disposal never
    signals a pid that a newer process took over.
    """
    try:
        st = pidfile.stat()
    except FileNotFoundError:
        return e
    if e.launched_at is None or st.st_mtime < e.launched_at.timestamp() - 1:
        return e
    text = pidfile.read_text().strip()
    if not (text.isascii() and text.isdigit()) or int(text) <= 0:
        msg = f"{pidfile} holds {text!r}, not a process id"
        raise ValueError(msg)
    pid = int(text)
    return e.model_copy(update={"pgid": pid, "pids": e.pids | {pid: st.st_mtime}})


def ready(e: Environment, proc: subprocess.Popen[bytes]) -> Pids | None:
    """Wait for the readiness URL; return the group's PIDs once it answers, else None."""
    end = time.monotonic() + READY_WITHIN
    while time.monotonic() < end and proc.returncode is None:
        if answers(e.ready_url):
            return e.pids | {p: created(p) for p in members(proc.pid, e.pids.get(proc.pid))}
        time.sleep(0.5)
    return None


def pending(c: Change, e: Environment) -> loop.StepResult:
    """The check waits on the owner once its environment answers; the visual check waits on its capture."""
    if e.check == VISUAL:
        reason = f"capturing {len(c.brief.visual)} visual states at {e.ready_url}"
        return loop.StepResult(exit=Exit.PENDING, waiting=Waiting.REVIEWER, reason=reason)
    person = next(p for p in c.checks if p.id == e.check)
    reason = f"{'; '.join(person.steps) or person.id} · {e.ready_url}"
    a = person.answer
    if a and a.inputs and (what := evidence.changed(a.inputs, evidence.check_inputs(c, person, declared(c)))):
        reason += f" · asked again: changed {', '.join(what)}"
    return loop.StepResult(exit=Exit.PENDING, waiting=Waiting.PERSON_CHECK, who="you", reason=reason)


def failed(reason: str) -> loop.StepResult:
    """Preparation or readiness failed: the check is prepared again."""
    cause = failures.cause_key(ErrorKind.PROJECT_ENV, StepKind.CHECK, "environment")
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
    cause = failures.cause_key(ErrorKind.CHECKS, StepKind.CHECK, person.id)
    result = loop.StepResult(
        exit=Exit.BACK, back_to=StepKind.BUILD, cause=cause, reason=f"{person.id} failed for you", fix_task=fix
    )
    after = loop.apply(c, result, now)
    for p in after.checks:
        if p.id == person.id and p.answer:
            p.answer.inputs = None  # a settled failure settles no later round
    return after
