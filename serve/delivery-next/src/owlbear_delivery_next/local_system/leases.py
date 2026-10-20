"""Leases on installed versions (self-update build §3): an OwlBear process running from ``versions/<tag>`` holds one.

A lease is a file ``versions/<tag>/leases/<pid>-<start time>``, made when the process starts and removed when it
ends; one whose process is gone counts for nothing. A version is removed only while no live lease holds it, so no
process ever loses the code it runs. The legacy runtime holds none: the owner removes it.
"""

from __future__ import annotations

import atexit
import contextlib
import os
import sys
from pathlib import Path

import psutil

from owlbear_delivery_next.local_system import local_home, processes

LEASES = "leases"


def physical(executable: Path) -> Path:
    """*executable* named by its own version's folder rather than through the alias.

    So a later switch never changes the code a running process loads (§3); the file itself may be a link (a venv's
    python), so only its folder is resolved.
    """
    return executable.parent.resolve() / executable.name


def pinned(argv: list[str]) -> None:
    """Run on from the version's own folder when started through the alias, before any lease or code is taken.

    The process is replaced, so its lease and the code it loads name the same version.
    """
    exe = Path(sys.executable)
    if (own := physical(exe)) != exe and own.exists():
        os.execv(own, [str(own), "-m", "owlbear_delivery_next", *argv])  # noqa: S606 - this interpreter, re-pinned


def unpinned() -> list[int]:
    """This user's processes started through the alias and never pinned: what still runs the kept legacy runtime.

    Every process since leases existed runs on from its version's own folder, so one whose command still names the
    alias was started before, from the runtime the first update put away; it holds no lease.
    """
    alias, found = str(local_home.root() / local_home.RUNTIME) + os.sep, []
    for proc in psutil.process_iter(["cmdline", "uids"]):
        with contextlib.suppress(psutil.Error, OSError):
            if proc.pid == os.getpid() or (proc.info["uids"] and proc.info["uids"].real != os.getuid()):
                continue
            if any(part.startswith(alias) for part in (proc.info["cmdline"] or [])[:2]):
                found.append(proc.pid)
    return found


def version_of(executable: Path) -> Path | None:
    """The installed version's folder *executable* runs from, or None for any other interpreter."""
    folder = executable.parent.resolve()  # the file itself may be a link (a venv's python)
    versions = (local_home.root() / local_home.VERSIONS).resolve()
    return next((p for p in [folder, *folder.parents] if p.parent == versions), None)


def take(executable: Path | None = None) -> Path | None:
    """Hold a lease on this process's version until it ends; None when it runs from no installed version."""
    version = version_of(executable or Path(sys.executable))
    if version is None:
        return None
    pid = os.getpid()
    with contextlib.suppress(OSError):
        path = version / LEASES / f"{pid}-{processes.started(pid)!r}"
        path.parent.mkdir(mode=0o700, exist_ok=True)
        path.touch(mode=0o600)
        atexit.register(path.unlink, missing_ok=True)
        return path
    return None


def held(version: Path) -> list[int]:
    """The processes whose live leases hold *version*; a lease whose process is gone is removed."""
    found = []
    for lease in sorted((version / LEASES).glob("*")):
        pid, _, start = lease.name.partition("-")
        try:
            state = processes.alive(int(pid), float(start))
        except ValueError:
            state = False
        if state is False:
            lease.unlink(missing_ok=True)
        else:
            found.append(int(pid))
    return found
