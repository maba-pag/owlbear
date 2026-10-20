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

from owlbear_delivery_next.local_system import local_home, processes

LEASES = "leases"


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
