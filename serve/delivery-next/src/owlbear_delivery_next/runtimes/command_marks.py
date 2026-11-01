"""The marks a runner's step leaves for its host, so the host finds what the step's commands left behind (#752).

Each shell command of the step's sessions writes its process group and start to ``commands`` through the session's
init script; each remote Git command's leader is journaled as a ``pids`` event. The host reads both itself, so the
marks outlive a runner that dies.
"""

from __future__ import annotations

import contextlib
import shlex
import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import psutil
from copilot.rpc import SessionUpdateOptionsParams, ShellInitScript, ShellInitScriptShell, ShellOptions

from owlbear_delivery_next.git import remote_git
from owlbear_delivery_next.local_system import processes
from owlbear_delivery_next.runtimes.instruction_scope import applied
from owlbear_delivery_next.runtimes.sdk_teardown import call as _call
from owlbear_delivery_next.state_store import step_pids

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from pathlib import Path

    from owlbear_delivery_next.change_contracts.user_config import UserConfig
    from owlbear_delivery_next.state_store.store import Lock, Store

FILE = "commands"
SCRIPT = "commands.sh"
LSTART = "%a %b %d %H:%M:%S %Y"
_active: list[Path] = []  # the folder of the Change whose runner marks its commands; empty elsewhere


def folder(store: Store, slug: str) -> Path:
    """Where a Change's marks live."""
    return store.root / "changes" / slug


@contextlib.contextmanager
def marking(store: Store, lock: Lock, slug: str) -> Iterator[None]:
    """While a runner's step runs: its sessions mark their commands and its remote Git leaders are journaled.

    The marks file and the recorded processes start afresh, since the host starts a runner only once the last step's
    processes are gone.
    """
    where = folder(store, slug)
    (where / SCRIPT).write_text(f"LC_ALL=C /bin/ps -o pgid=,lstart= -p $$ >> {shlex.quote(str(where / FILE))}\n")
    (where / FILE).write_bytes(b"")
    (where / step_pids.FILE).write_bytes(b"")

    def launched(pid: int) -> None:
        started: float | None = None
        with contextlib.suppress(psutil.Error, OSError):
            started = processes.started(pid)
        event = {"event": "pids", "at": datetime.now(UTC).isoformat(), "pids": {str(pid): started}}
        store.log(lock, slug, event)

    _active[:] = [where]
    remote_git.launched = launched
    try:
        yield
    finally:
        _active.clear()
        remote_git.launched = None


async def opened(session: Any, worktree: Path, user: UserConfig, log: Callable[..., None]) -> None:  # noqa: ANN401
    """The session's options before its first message: its instruction scope, and in a runner its command marks.

    Raises:
        RuntimeError: The runtime refused either; the step ends before any message.
    """
    await applied(session, worktree, user, log)
    if not _active:
        return
    script = ShellInitScript(path=str(_active[0] / SCRIPT), shell=ShellInitScriptShell.BASH)
    update = session.rpc.options.update(SessionUpdateOptionsParams(shell=ShellOptions(init_scripts=[script])))
    if not (await _call(update, "command marks")).success:
        msg = "the runtime refused the shell init script that marks the step's commands"
        raise RuntimeError(msg)


def read(where: Path, since: datetime) -> dict[int, float]:
    """Each marked command's group since *since*, with the latest its shell can have started (``lstart`` is whole s).

    Raises:
        OSError: The marks file could not be read.
        ValueError: A line is not what the init script writes.
    """
    path = where / FILE
    try:
        text = path.read_text()
    except FileNotFoundError:
        return {}
    marks: dict[int, float] = {}
    for n, line in enumerate(text.splitlines(), 1):
        try:
            pgid, when = line.split(maxsplit=1)
            bound = time.mktime(time.strptime(when.strip(), LSTART)) + 1
            marks |= {int(pgid): bound} if bound >= since.timestamp() - 1 else {}
        except ValueError as exc:
            msg = f"{path} line {n}: {line!r}"
            raise ValueError(msg) from exc
    return marks
