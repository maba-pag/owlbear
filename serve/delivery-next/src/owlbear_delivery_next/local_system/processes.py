"""Step processes: observed by PID and start time, found by hierarchy, signalled, and the termination verdict (F4)."""

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


class UnlistedError(RuntimeError):
    """The process table, or one process's group or session, could not be read; nothing can be ruled out."""


def members(ids: Pids) -> dict[int, str]:
    """Live, non-zombie processes whose pgid or sid is one of *ids*, each with its label.

    Each id maps to the latest time its leader may have started, or None if unknown. An id whose pid is now a
    process created more than 1 s after that time names a newer process, so it is dropped. Every pid is listed,
    but only its pgid and sid are read to decide (D-01M68YBR3M77X54K6R17F4ZHP4). Name, status and start time are
    read only for members.

    Raises:
        UnlistedError: the table could not be listed, or a pgid or sid could not be read.
    """
    if not ids:
        return {}
    found: dict[int, str] = {}
    for key, pids in _matches(ids).items():
        if key in pids and _newer(key, ids[key]):  # a recycled pid carries the id only by leading anew
            continue
        found |= {p: label for p in pids if (label := _label(p)) is not None}
    return found


def _matches(ids: Pids) -> dict[int, list[int]]:
    """Every listed pid filed under each id its pgid and its sid is; nothing else of it is read.

    Filed under both, a process whose group id turns out recycled still counts by its session.
    """
    try:
        table = psutil.pids()
    except (psutil.Error, OSError) as exc:
        msg = f"the process table could not be listed: {exc}"
        raise UnlistedError(msg) from exc
    matched: dict[int, list[int]] = {}
    for p in table:
        if p <= 0:  # 0 asks getpgid and getsid about the caller itself
            continue
        try:
            keys = {os.getpgid(p), os.getsid(p)}
        except ProcessLookupError:
            continue
        except OSError as exc:
            msg = f"process {p}: its group or session could not be read: {exc}"
            raise UnlistedError(msg) from exc
        for key in keys & ids.keys():
            matched.setdefault(key, []).append(p)
    return matched


def _newer(pid: int, bound: float | None) -> bool:
    """Whether *pid* is a process created after *bound*; unknown counts as not newer, so nothing is overlooked."""
    with contextlib.suppress(psutil.Error, OSError):
        return bound is not None and started(pid) > bound + 1.0
    return False


def _label(pid: int) -> str | None:
    """A member's name and any field that could not be read; None once it is gone or a zombie."""
    failed: list[str] = []

    def read[T](what: str, get: Callable[[], T]) -> T | None:
        try:
            return get()
        except psutil.NoSuchProcess:  # also a zombie's ZombieProcess
            raise
        except (psutil.Error, OSError) as exc:
            failed.append(f"{what} unreadable: {type(exc).__name__}: {exc}")
            return None

    try:
        p = psutil.Process(pid)
        name = read("name", p.name)
        if read("status", p.status) == psutil.STATUS_ZOMBIE:
            return None
        read("start time", p.create_time)
    except psutil.NoSuchProcess:
        return None
    return "; ".join(x for x in (name, *failed) if x)


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
