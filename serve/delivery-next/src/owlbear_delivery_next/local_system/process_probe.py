# Adapted from serve/delivery/src/owlbear_delivery/worker_stall.py at ab9cfc6cb: claim issuer, window identity and
# release error dropped; processes report their PID; ``issued_after`` is the step's start.
"""Same-user processes still working in a step's worktree; a scan never proves a worker has ended."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

try:
    import psutil
except ImportError:  # pragma: no cover - psutil is a declared dependency; absence fails closed.
    psutil = None

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Iterator
    from datetime import datetime

SHELL_PROCESS_NAMES = frozenset({"sh", "bash", "zsh", "fish"})
# Same pid within this many seconds of its recorded start is the same process; errs toward "alive".
_CREATE_TIME_TOLERANCE_SECONDS = 1.0
# macOS's sealed, read-only system volume; /System/Volumes holds the writable data and other volumes.
_SEALED_SYSTEM_ROOT: Path | None = Path("/System") if sys.platform == "darwin" else None


class ProcessObservationError(RuntimeError):
    """One live process could not be observed; callers treat it as unknown."""


class ProcessVanishedError(ProcessObservationError):
    """The process exited or became a zombie while it was observed."""


class WorktreeProcessScanError(RuntimeError):
    """The process table as a whole could not be scanned; callers must treat the worker as active."""


class ProcessView(Protocol):
    """Lazy view of one same-user process.

    Methods raise ``ProcessVanishedError`` when it exits and ``ProcessObservationError`` when it is unreadable.
    """

    @property
    def pid(self) -> int:
        """Return the process id."""
        ...

    @property
    def name(self) -> str:
        """Return the process name only; never a path or command line."""
        ...

    @property
    def create_time(self) -> float | None:
        """Return the start time in epoch seconds, or ``None`` when it cannot be read."""
        ...

    def cwd(self) -> Path | None:
        """Return the working directory, if any."""
        ...

    def open_files(self) -> tuple[Path, ...]:
        """Return the regular files currently open by the process."""
        ...

    def executable(self) -> Path | None:
        """Return the executable path, if any."""
        ...

    def has_live_children(self) -> bool:
        """Return whether any non-zombie child process exists."""
        ...

    def has_terminal(self) -> bool:
        """Return whether the process is attached to a controlling terminal."""
        ...

    def cmdline(self) -> tuple[str, ...]:
        """Return the argument vector for local judgement only; never report it."""
        ...


type ProcessSource = Callable[[], Iterable[ProcessView]]


def _contains(path: Path, roots: tuple[Path, ...]) -> bool:
    return any(path.is_relative_to(root) for root in roots)


def _is_interactive_invocation(argv: tuple[str, ...]) -> bool:
    """Only options follow the shell name, and none runs a command string or script."""
    if not argv:
        return False
    for index, argument in enumerate(argv[1:], start=1):
        if argument in {"-", "--"}:
            return index == len(argv) - 1
        if argument[:1] not in {"-", "+"}:
            return False
        if argument.startswith("--"):
            if argument == "--command" or argument.startswith("--command="):
                return False
        elif {"c", "s"} & set(argument[1:]):  # A command string, or commands read from standard input.
            return False
    return True


def _is_idle_interactive_shell(process: ProcessView) -> bool:
    """Terminal-attached, childless, and started without a command string, script or unreadable arguments."""
    if not process.has_terminal() or process.has_live_children():
        return False
    try:
        argv = process.cmdline()
    except ProcessVanishedError:
        raise
    except ProcessObservationError:
        return False
    return _is_interactive_invocation(argv)


def _worktree_cwd_blocks(process: ProcessView, roots: tuple[Path, ...]) -> bool:
    """A process working in the worktree blocks unless it is a fully verified idle interactive shell."""
    if process.name.lower().lstrip("-") not in SHELL_PROCESS_NAMES:
        return True
    try:
        if any(_contains(path, roots) for path in process.open_files()):
            return True
        # Only an interactive prompt whose sole link is its working directory is idle.
        return not _is_idle_interactive_shell(process)
    except ProcessVanishedError:
        raise
    except ProcessObservationError:
        return True


def _is_sealed_system_binary(process: ProcessView) -> bool:
    """Whether the executable lies on the sealed system volume, which only OS updates can write."""
    if _SEALED_SYSTEM_ROOT is None:
        return False
    try:
        executable = process.executable()
    except ProcessVanishedError:
        raise
    except ProcessObservationError:
        return False
    return (
        executable is not None
        and executable.is_absolute()
        and ".." not in executable.parts
        and executable.is_relative_to(_SEALED_SYSTEM_ROOT)
        and not executable.is_relative_to(_SEALED_SYSTEM_ROOT / "Volumes")
    )


def _blocks(process: ProcessView, roots: tuple[Path, ...]) -> bool:
    """Judge readable evidence first; raise ``ProcessObservationError`` only when no worktree link is established."""
    unreadable: ProcessObservationError | None = None
    cwd: Path | None = None
    try:
        cwd = process.cwd()
    except ProcessVanishedError:
        raise
    except ProcessObservationError as exc:
        unreadable = exc
    if cwd is not None and _contains(cwd, roots):
        return _worktree_cwd_blocks(process, roots)
    try:
        if any(_contains(path, roots) for path in process.open_files()):
            return True
    except ProcessVanishedError:
        raise
    except ProcessObservationError as exc:
        unreadable = exc
    if unreadable is not None:
        # Hardened OS daemons deny open-file reads even to their owner; a readable outside cwd suffices.
        if cwd is not None and _is_sealed_system_binary(process):
            return False
        raise unreadable
    return False


def _observation_error(exc: BaseException) -> ProcessObservationError:
    if psutil is not None and isinstance(exc, psutil.NoSuchProcess):  # Includes zombies.
        return ProcessVanishedError(type(exc).__name__)
    return ProcessObservationError(type(exc).__name__)


class _PsutilProcessView:
    def __init__(
        self, process: psutil.Process, name: str, create_time: float | None, *, owner_known: bool = True
    ) -> None:
        self._process = process
        self._name = name
        self._create_time = create_time
        self._owner_known = owner_known

    @property
    def pid(self) -> int:
        return self._process.pid

    @property
    def name(self) -> str:
        return self._name

    @property
    def create_time(self) -> float | None:
        return self._create_time

    def _read[T](self, read: Callable[[], T], *, owner: bool = True) -> T:
        if owner and not self._owner_known:
            message = "process owner is unknown"
            raise ProcessObservationError(message)
        try:
            return read()
        except (psutil.Error, OSError) as exc:
            raise _observation_error(exc) from exc

    def cwd(self) -> Path | None:
        cwd = self._read(self._process.cwd)
        return Path(cwd) if cwd else None

    def open_files(self) -> tuple[Path, ...]:
        return tuple(Path(item.path) for item in self._read(self._process.open_files))

    def executable(self) -> Path | None:
        executable = self._read(self._process.exe)
        return Path(executable) if executable else None

    def has_terminal(self) -> bool:
        return self._read(self._process.terminal, owner=False) is not None

    def cmdline(self) -> tuple[str, ...]:
        return tuple(self._read(self._process.cmdline))

    def has_live_children(self) -> bool:
        for child in self._read(self._process.children, owner=False):
            try:
                if child.status() != psutil.STATUS_ZOMBIE:
                    return True
            except psutil.NoSuchProcess:
                continue
            except psutil.Error, OSError:
                return True
        return False


def _still_own_descendant(pid: int, create_time: float | None, own_pid: int) -> bool | None:
    """Return ``None`` when the process vanished; any other doubt means it is scanned like every process."""
    try:
        current = psutil.Process(pid)
        if create_time is None or current.create_time() != create_time:
            return False
        return any(parent.pid == own_pid for parent in current.parents())
    except psutil.NoSuchProcess:
        return None
    except psutil.Error, OSError:
        return False


def psutil_user_processes() -> Iterator[ProcessView]:
    """Yield every process owned, or possibly owned, by the current user except this one and its descendants."""
    if psutil is None:
        message = "process table is unavailable"
        raise WorktreeProcessScanError(message)
    own_pid, own_uid = os.getpid(), os.getuid()
    try:
        processes = tuple(psutil.process_iter(("pid", "name", "uids", "create_time")))
        # The scanner's own Git subprocesses run inside worktrees; they are never a stopped worker's leftovers.
        own_pids = {child.pid for child in psutil.Process(own_pid).children(recursive=True)}
    except (psutil.Error, OSError) as exc:
        message = "process table could not be scanned"
        raise WorktreeProcessScanError(message) from exc
    for process in processes:
        info = process.info
        pid, uids = info.get("pid"), info.get("uids")
        if pid == own_pid or (uids is not None and uids.real != own_uid):
            continue
        # A descendant orphaned since the snapshot is no longer the scanner's own work.
        if pid in own_pids and _still_own_descendant(pid, info.get("create_time"), own_pid) is not False:
            continue
        yield _PsutilProcessView(process, info.get("name") or "", info.get("create_time"), owner_known=uids is not None)


def _may_be_worker_leftover(process: ProcessView, started_after: datetime | None) -> bool:
    """A worker's leftover started after its step began; unknown times cannot rule that out."""
    created = process.create_time
    # A naive time depends on the host's local zone, so it cannot rule out a leftover either.
    if started_after is None or started_after.tzinfo is None or created is None:
        return True
    try:
        threshold = started_after.timestamp() - _CREATE_TIME_TOLERANCE_SECONDS
    except OverflowError, OSError, ValueError:
        return True
    return created >= threshold


class ProcessTableWorktreeProbe:
    """Find same-user processes whose working directory or open files lie under a worker's paths."""

    def __init__(self, source: ProcessSource = psutil_user_processes) -> None:
        self._source = source

    def active_processes(
        self, roots: tuple[Path, ...], *, started_after: datetime | None
    ) -> tuple[tuple[int, str], ...]:
        """Return ``(pid, name)`` per blocking process; skip vanished ones and fail closed on a failed scan."""
        containers = tuple(dict.fromkeys((*roots, *(root.resolve() for root in roots))))
        found: list[tuple[int, str]] = []
        try:
            for process in self._source():
                try:
                    if _blocks(process, containers):
                        found.append((process.pid, process.name))
                except ProcessVanishedError:
                    continue
                except ProcessObservationError:
                    if _may_be_worker_leftover(process, started_after):
                        found.append((process.pid, process.name))
        except WorktreeProcessScanError:
            raise
        except (OSError, RuntimeError) as exc:
            message = "process table could not be scanned"
            raise WorktreeProcessScanError(message) from exc
        return tuple(found)
