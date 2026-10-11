"""Processes a VS Code step left working in its worktree: what the agent's shells started, never the editor's own."""

from __future__ import annotations

import contextlib
import os
import signal
import time
from typing import TYPE_CHECKING

import psutil

from owlbear_delivery_next.process_probe import SHELL_PROCESS_NAMES, ProcessTableWorktreeProbe, WorktreeProcessScanError
from owlbear_delivery_next.processes import Termination

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import datetime
    from pathlib import Path

EDITOR = ("/Visual Studio Code", "/.vscode/extensions/", "/.vscode-insiders/")  # the app, its harness, extensions
SYSTEM = ("/System/", "/usr/", "/bin/", "/sbin/", "/Library/Apple/")
GRACE = 5.0


def _exe(p: psutil.Process) -> str:
    with contextlib.suppress(psutil.Error, OSError):
        return p.exe() or ""
    return ""


def agent_started(pid: int) -> bool:
    """A shell started ``pid`` before any editor process did, or a shell left it detached."""
    try:
        proc = psutil.Process(pid)
        chain = [proc, *proc.parents()]
        detached = proc.ppid() == 1
    except psutil.Error, OSError:
        return False
    for p in chain:
        if any(mark in _exe(p) for mark in EDITOR):
            return False
        with contextlib.suppress(psutil.Error, OSError):
            if p.name().lower().lstrip("-") in SHELL_PROCESS_NAMES:
                return True
    exe = _exe(proc)
    return detached and bool(exe) and not exe.startswith(SYSTEM)


def scan(root: Path, since: datetime) -> list[int]:
    """The agent-started processes still working in ``root`` that began after ``since``."""
    found = ProcessTableWorktreeProbe().active_processes((root,), started_after=since)
    return sorted(pid for pid, _ in found if agent_started(pid))


def settle(
    root: Path,
    since: datetime,
    find: Callable[[Path, datetime], list[int]] = scan,
    wait: Callable[[float], None] = time.sleep,
) -> Termination:
    """End what the step left running: terminate, then kill; confirmed only when a scan finds nothing."""
    try:
        pids = find(root, since)
        for sig in (signal.SIGTERM, signal.SIGKILL):
            if not pids:
                break
            for pid in pids:
                with contextlib.suppress(OSError):
                    os.kill(pid, sig)
            wait(GRACE)
            pids = find(root, since)
    except WorktreeProcessScanError as exc:
        return Termination(confirmed=False, problems=(str(exc),))
    return Termination(confirmed=not pids, survivors=tuple(pids))
