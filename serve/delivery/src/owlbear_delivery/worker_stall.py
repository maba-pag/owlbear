"""Claim-issuer window identity and leftover-worker evidence; never a proof of worker death."""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

try:
    import psutil
except ImportError:  # pragma: no cover - psutil is a declared dependency; absence fails closed.
    psutil = None

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Iterator

CLAIM_ISSUERS_DIRECTORY = "claim-issuers"
DEFAULT_WORKER_QUIET_PERIOD = timedelta(seconds=30)
LAUNCHER_PROCESS_NAMES = frozenset({"uv", "uvx", "sh", "bash", "zsh", "fish", "env"})
SHELL_PROCESS_NAMES = frozenset({"sh", "bash", "zsh", "fish"})
_MAX_ANCESTRY = 32
# Same pid within this many seconds of its recorded start is the same process; errs toward "alive".
_CREATE_TIME_TOLERANCE_SECONDS = 1.0
_MAX_REPORTED_NAMES = 5
_MAX_REPORTED_NAME_LENGTH = 32
_ATTEMPT_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_CHANGE_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_logger = logging.getLogger(__name__)

type WindowHostState = Literal["alive", "gone", "unknown"]


class ProcessObservationError(RuntimeError):
    """One live process could not be observed; callers treat it as unknown."""


class ProcessVanishedError(ProcessObservationError):
    """The process exited or became a zombie while it was observed."""


class WorktreeProcessScanError(RuntimeError):
    """The process table as a whole could not be scanned; callers must treat the worker as active."""


@dataclass(frozen=True)
class ObservedProcess:
    """One process-table row used to identify and re-check a claim-issuing window."""

    pid: int
    parent_pid: int | None
    create_time: float
    name: str


type ProcessLookup = Callable[[int], ObservedProcess | None]


def psutil_process(pid: int) -> ObservedProcess | None:
    """Return one live process, ``None`` when it no longer exists, or raise when it cannot be observed."""
    if psutil is None:
        message = "process table is unavailable"
        raise ProcessObservationError(message)
    try:
        process = psutil.Process(pid)
        with process.oneshot():
            return ObservedProcess(
                pid=pid, parent_pid=process.ppid(), create_time=process.create_time(), name=process.name()
            )
    except psutil.NoSuchProcess:  # Includes zombies: an exited window is gone.
        return None
    except (psutil.Error, OSError) as exc:
        message = "process is not observable"
        raise ProcessObservationError(message) from exc


def _is_launcher(name: str) -> bool:
    normalized = name.lower().removesuffix(".exe").lstrip("-")
    return normalized in LAUNCHER_PROCESS_NAMES or normalized.startswith("python")


class WindowHostIdentity(BaseModel):
    """The exact VS Code window process whose agents receive claims issued by this Delivery process."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    pid: int = Field(gt=1)
    create_time: float = Field(ge=0, allow_inf_nan=False)
    name: str = Field(min_length=1, max_length=256)

    @classmethod
    def capture(cls, lookup: ProcessLookup = psutil_process, *, pid: int | None = None) -> WindowHostIdentity | None:
        """Return the nearest ancestor that is not this process or a launcher wrapper, if one is identifiable."""
        try:
            current = lookup(os.getpid() if pid is None else pid)
            for _ in range(_MAX_ANCESTRY):
                if current is None or current.parent_pid is None or current.parent_pid <= 1:
                    break
                current = lookup(current.parent_pid)
                if current is not None and not _is_launcher(current.name):
                    return cls(pid=current.pid, create_time=current.create_time, name=current.name[:256])
        except (ProcessObservationError, ValueError):
            pass
        _logger.warning("Delivery issuer window is unidentifiable; stale claims need user-confirmed release.")
        return None


class WindowLivenessProbe(Protocol):
    """Engine dependency answering whether one recorded claim-issuing window still exists."""

    def window_state(self, window: WindowHostIdentity) -> WindowHostState:
        """Return ``gone`` only when that exact process (pid and start time) no longer exists."""
        ...


class ProcessWindowLivenessProbe:
    """Check one recorded window against the live process table without signalling it."""

    def __init__(self, lookup: ProcessLookup = psutil_process) -> None:
        self._lookup = lookup

    def window_state(self, window: WindowHostIdentity) -> WindowHostState:
        """A missing pid or a reused pid with another start time is gone; unobservable stays unknown."""
        try:
            current = self._lookup(window.pid)
        except ProcessObservationError:
            return "unknown"
        if current is None or abs(current.create_time - window.create_time) >= _CREATE_TIME_TOLERANCE_SECONDS:
            return "gone"
        return "alive"


class ProcessView(Protocol):
    """Lazy view of one same-user process.

    Methods raise ``ProcessVanishedError`` when it exits and ``ProcessObservationError`` when it is unreadable.
    """

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


class WorktreeProcessProbe(Protocol):
    """Engine dependency naming live processes that may still be doing a stopped worker's work."""

    def active_processes(self, roots: tuple[Path, ...], *, issued_after: datetime | None) -> tuple[str, ...]:
        """Return one name per blocking process; raise ``WorktreeProcessScanError`` when the scan cannot run.

        ``issued_after`` is the claim's issue time; ``None`` means unknown, so every unreadable process blocks.
        """
        ...


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
    def name(self) -> str:
        return self._name

    @property
    def create_time(self) -> float | None:
        return self._create_time

    def _require_owner(self) -> None:
        if not self._owner_known:
            message = "process owner is unknown"
            raise ProcessObservationError(message)

    def cwd(self) -> Path | None:
        self._require_owner()
        try:
            cwd = self._process.cwd()
        except (psutil.Error, OSError) as exc:
            raise _observation_error(exc) from exc
        return Path(cwd) if cwd else None

    def open_files(self) -> tuple[Path, ...]:
        self._require_owner()
        try:
            return tuple(Path(item.path) for item in self._process.open_files())
        except (psutil.Error, OSError) as exc:
            raise _observation_error(exc) from exc

    def has_terminal(self) -> bool:
        try:
            return self._process.terminal() is not None
        except (psutil.Error, OSError) as exc:
            raise _observation_error(exc) from exc

    def cmdline(self) -> tuple[str, ...]:
        self._require_owner()
        try:
            return tuple(self._process.cmdline())
        except (psutil.Error, OSError) as exc:
            raise _observation_error(exc) from exc

    def has_live_children(self) -> bool:
        try:
            children = self._process.children()
        except (psutil.Error, OSError) as exc:
            raise _observation_error(exc) from exc
        for child in children:
            try:
                if child.status() != psutil.STATUS_ZOMBIE:
                    return True
            except psutil.NoSuchProcess:
                continue
            except (psutil.Error, OSError):
                return True
        return False


def _still_delivery_descendant(pid: int, create_time: float | None, own_pid: int) -> bool | None:
    """Return ``None`` when the process vanished; any other doubt means it is scanned like every process."""
    try:
        current = psutil.Process(pid)
        if create_time is None or current.create_time() != create_time:
            return False
        return any(parent.pid == own_pid for parent in current.parents())
    except psutil.NoSuchProcess:
        return None
    except (psutil.Error, OSError):
        return False


def psutil_user_processes() -> Iterator[ProcessView]:
    """Yield every process owned, or possibly owned, by the current user except Delivery and its descendants."""
    if psutil is None:
        message = "process table is unavailable"
        raise WorktreeProcessScanError(message)
    own_pid, own_uid = os.getpid(), os.getuid()
    try:
        processes = tuple(psutil.process_iter(("pid", "name", "uids", "create_time")))
        # Delivery's own Git subprocesses run inside worktrees; they are never a stopped worker's leftovers.
        own_pids = {child.pid for child in psutil.Process(own_pid).children(recursive=True)}
    except (psutil.Error, OSError) as exc:
        message = "process table could not be scanned"
        raise WorktreeProcessScanError(message) from exc
    for process in processes:
        info = process.info
        pid, uids = info.get("pid"), info.get("uids")
        if pid == own_pid or (uids is not None and uids.real != own_uid):
            continue
        # A descendant orphaned since the snapshot is no longer Delivery's own work.
        if pid in own_pids and _still_delivery_descendant(pid, info.get("create_time"), own_pid) is not False:
            continue
        yield _PsutilProcessView(process, info.get("name") or "", info.get("create_time"), owner_known=uids is not None)


def _may_be_worker_leftover(process: ProcessView, issued_after: datetime | None) -> bool:
    """A worker's leftover started after its claim was issued; unknown times cannot rule that out."""
    created = process.create_time
    # A naive time depends on the host's local zone, so it cannot rule out a leftover either.
    if issued_after is None or issued_after.tzinfo is None or created is None:
        return True
    try:
        threshold = issued_after.timestamp() - _CREATE_TIME_TOLERANCE_SECONDS
    except (OverflowError, OSError, ValueError):
        return True
    return created >= threshold


class ProcessTableWorktreeProbe:
    """Find same-user processes whose working directory or open files lie under a worker's paths."""

    def __init__(self, source: ProcessSource = psutil_user_processes) -> None:
        self._source = source

    def active_processes(self, roots: tuple[Path, ...], *, issued_after: datetime | None) -> tuple[str, ...]:
        """Skip vanished processes and unreadable ones older than the claim; fail closed on a failed scan."""
        containers = tuple(dict.fromkeys((*roots, *(root.resolve() for root in roots))))
        names: list[str] = []
        try:
            for process in self._source():
                try:
                    if _blocks(process, containers):
                        names.append(process.name)
                except ProcessVanishedError:
                    continue
                except ProcessObservationError:
                    if _may_be_worker_leftover(process, issued_after):
                        names.append(process.name)
        except WorktreeProcessScanError:
            raise
        except (OSError, RuntimeError) as exc:
            message = "process table could not be scanned"
            raise WorktreeProcessScanError(message) from exc
        return tuple(names)


def _reported_name(name: str) -> str:
    base = name.rsplit("/", 1)[-1]
    printable = "".join(character for character in base if character.isprintable())
    return " ".join(printable.split())[:_MAX_REPORTED_NAME_LENGTH] or "unnamed"


def describe_active_processes(names: tuple[str, ...]) -> str:
    """Summarize blocking processes as a count and a few bounded names, never paths or command lines."""
    distinct = sorted({_reported_name(name) for name in names})
    shown = ", ".join(distinct[:_MAX_REPORTED_NAMES])
    if len(distinct) > _MAX_REPORTED_NAMES:
        shown += f" and {len(distinct) - _MAX_REPORTED_NAMES} more"
    noun = "process" if len(names) == 1 else "processes"
    return f"{len(names)} {noun} ({shown})"


class DeliveryWorkerActiveError(RuntimeError):
    """A stuck-worker release found possible leftover worker activity and changed nothing."""

    code = "ERR_DELIVERY_WORKER_ACTIVE"

    def __init__(self, retry_after: datetime | None, active_processes: tuple[str, ...] = ()) -> None:
        self.active_processes = active_processes
        self.retry_after = None if active_processes else retry_after
        if active_processes:
            verb = "is" if len(active_processes) == 1 else "are"
            reason = (
                f"{describe_active_processes(active_processes)} {verb} still active in the worker's worktree, so "
                "the worker may still be running. Retry after they exit."
            )
        elif retry_after is not None:
            reason = (
                "The worker's worktree changed recently, so the worker may still be active. Retry at or after "
                f"{retry_after.isoformat().replace('+00:00', 'Z')}."
            )
        else:
            reason = (
                "The worker's worktree or its processes could not be observed safely, so the worker may still be "
                "active. Retry after they can be observed safely and the worktree stays unchanged for the quiet "
                "period."
            )
        super().__init__(f"Custody, files and retry accounting are unchanged. {reason}")


class DeliveryClaimIssuer(BaseModel):
    """Immutable binding of one issued claim to the VS Code window, if any, whose agents received it."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal[1] = 1
    change_id: str = Field(pattern=_CHANGE_ID_PATTERN.pattern)
    outcome_id: str | None = Field(default=None, pattern=r"^OUT-[0-9]{3}$")
    attempt_id: str = Field(pattern=_ATTEMPT_ID_PATTERN.pattern)
    claim_id: str = Field(min_length=1, max_length=256)
    role: Literal["planner", "builder", "finalizer"]
    window: WindowHostIdentity | None
    issued_at: str = Field(min_length=1, max_length=64)


def is_issuable_attempt_id(attempt_id: str) -> bool:
    """Return whether an attempt identity can name a contained issuer record."""
    return _ATTEMPT_ID_PATTERN.fullmatch(attempt_id) is not None


def claim_issuer_path(change_id: str, attempt_id: str) -> Path:
    """Locate one issuer record relative to the runtime root."""
    if _CHANGE_ID_PATTERN.fullmatch(change_id) is None or not is_issuable_attempt_id(attempt_id):
        message = "claim issuer identity is not a contained record name"
        raise ValueError(message)
    return Path("changes") / change_id / CLAIM_ISSUERS_DIRECTORY / f"{attempt_id}.json"


__all__ = [
    "CLAIM_ISSUERS_DIRECTORY",
    "DEFAULT_WORKER_QUIET_PERIOD",
    "LAUNCHER_PROCESS_NAMES",
    "SHELL_PROCESS_NAMES",
    "DeliveryClaimIssuer",
    "DeliveryWorkerActiveError",
    "ObservedProcess",
    "ProcessLookup",
    "ProcessObservationError",
    "ProcessSource",
    "ProcessTableWorktreeProbe",
    "ProcessVanishedError",
    "ProcessView",
    "ProcessWindowLivenessProbe",
    "WindowHostIdentity",
    "WindowHostState",
    "WindowLivenessProbe",
    "WorktreeProcessProbe",
    "WorktreeProcessScanError",
    "claim_issuer_path",
    "describe_active_processes",
    "is_issuable_attempt_id",
    "psutil_process",
    "psutil_user_processes",
]
