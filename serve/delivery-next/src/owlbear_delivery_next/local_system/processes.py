"""Recorded step processes: observing them by PID and start time, signalling them, and the termination verdict (F4)."""

from __future__ import annotations

import contextlib
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

import psutil

if TYPE_CHECKING:
    import signal
    from collections.abc import Callable, Mapping, Sequence

type Pids = Mapping[int, float | None]
type Observe = Callable[[int, float | None], bool | None]


@dataclass(frozen=True)
class Termination:
    """Whether every listed or recorded process of the step is gone; anything unobserved keeps it unverified."""

    confirmed: bool
    survivors: tuple[int, ...] = ()
    unknown: tuple[int, ...] = ()
    problems: tuple[str, ...] = ()


def verdict(recorded: Pids, alive: Observe, problems: Sequence[str] = ()) -> Termination:
    """Decide confirmed or unverified from one observation per recorded PID (True alive, None unknown)."""
    states = {pid: alive(pid, created) for pid, created in recorded.items()}
    survivors = tuple(sorted(p for p, s in states.items() if s))
    unknown = tuple(sorted(p for p, s in states.items() if s is None))
    return Termination(not (survivors or unknown or problems), survivors, unknown, tuple(problems))


def alive(pid: int, created: float | None) -> bool | None:
    """Observe one recorded process: a zombie or a reused PID is gone; an unreadable one is unknown."""
    try:
        p = psutil.Process(pid)
        if p.status() == psutil.STATUS_ZOMBIE:
            return False
        return created is None or abs(p.create_time() - created) < 1.0
    except psutil.NoSuchProcess:
        return False
    except psutil.Error, OSError:
        return None


def started(pid: int) -> float:
    """Return the process creation time that identifies pid."""
    return psutil.Process(pid).create_time()


def _pgid(pid: int) -> int:
    with contextlib.suppress(OSError):
        return os.getpgid(pid)
    return -1


def targets(recorded: Pids, seen: Observe, group: Callable[[int], int], own: int) -> tuple[list[int], list[int]]:
    """Return live PIDs whose start time proves identity, and groups they lead; an unknown start is never signalled."""
    live = sorted(p for p, c in recorded.items() if c is not None and seen(p, c))
    return live, [p for p in live if p != own and group(p) == p]


def kill(recorded: Pids, sig: signal.Signals) -> list[int]:
    """Signal recorded PIDs whose start time proves identity, and the groups they lead; return the live ones."""
    live, groups = targets(recorded, alive, _pgid, os.getpgrp())
    for g, send in [*((g, os.killpg) for g in groups), *((p, os.kill) for p in live)]:
        with contextlib.suppress(OSError):
            send(g, sig)
    return live
