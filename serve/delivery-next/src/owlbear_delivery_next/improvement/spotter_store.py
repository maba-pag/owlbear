"""Where and how the Spotter (``improvement.spotter``) keeps its files on this machine, and the threads that write them.

Records, outcomes and cards stay in ``~/.owlbear/spotter/`` (owner-only). Each line is appended to its day's file under
the folder's lock; a failed write never reaches the step. Writes run on ``WORK``, the Spotter's own daemon threads, so a
step's end never waits for them; the process waits at most ``GRACE`` for them at exit. ``spotter`` re-exports these
names for its callers.
"""

from __future__ import annotations

import atexit
import contextlib
import fcntl
import gzip
import json
import os
import queue
import threading
import time
from concurrent.futures import Future
from dataclasses import asdict
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.local_system import local_home

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from pathlib import Path

    from owlbear_delivery_next.improvement.spotter import Record

LOCK, GRACE = 5.0, 1.0  # seconds a file lock is waited for; and the Spotter's writes at the process's exit


def place() -> Path:
    """Where the Spotter's records and cards are kept on this machine; nothing is created."""
    return local_home.root() / "spotter"


def ready(folder: Path) -> Path:
    """*folder*, created owner-only with its cards' folder if needed."""
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    (folder / "cards").mkdir(exist_ok=True, mode=0o700)
    return folder


def root() -> Path:
    """The Spotter's folder, created if needed."""
    return ready(place())


def _today() -> str:
    return datetime.now(UTC).date().isoformat()


@contextlib.contextmanager
def _locked(path: Path, seconds: float = LOCK) -> Iterator[None]:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT, 0o600)
    try:
        until = time.monotonic() + seconds
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() > until:
                    raise TimeoutError(path.name) from None
                time.sleep(0.02)
        yield
    finally:
        os.close(fd)


def _append(folder: Path, name: str, line: dict[str, Any]) -> None:
    """One line appended to the day's file *name* in *folder* under its lock; a failure never reaches the step."""
    with contextlib.suppress(OSError, TimeoutError), _locked(ready(folder) / "records.lock"):
        fd = os.open(folder / f"{name}-{_today()}.jsonl", os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        with os.fdopen(fd, "a") as out:
            out.write(json.dumps(line) + "\n")


def store(folder: Path, record: Record, card_: dict[str, Any] | None) -> None:
    """Keep *record*'s card and append the record to the day's records in *folder*; a failure never reaches the step."""
    with contextlib.suppress(OSError):
        if card_ is not None:
            fd = os.open(ready(folder) / "cards" / f"{record.id}.json.gz", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "wb") as raw, gzip.open(raw, "wt") as out:
                json.dump(card_, out)
    _append(folder, "records", asdict(record))


class Worker:
    """The Spotter's own daemon threads, first in, first out: the process waits at most ``GRACE`` for them at exit.

    A killed write loses at most the line it was writing.
    """

    def __init__(self, threads: int) -> None:
        self.jobs: queue.Queue[tuple[Future[Any], Callable[..., Any], tuple[Any, ...]]] = queue.Queue()
        self.threads, self.started, self.lock = threads, False, threading.Lock()

    def submit[T](self, work: Callable[..., T], *args: Any) -> Future[T]:  # noqa: ANN401 - the work's arguments
        """Queue *work*; its future."""
        with self.lock:
            if not self.started:
                for i in range(self.threads):
                    threading.Thread(target=self._serve, name=f"spotter-{i}", daemon=True).start()
                self.started = True
        done: Future[T] = Future()
        self.jobs.put((done, work, args))
        return done

    def _serve(self) -> None:
        while True:
            done, work, args = self.jobs.get()
            try:
                if done.set_running_or_notify_cancel():
                    try:
                        done.set_result(work(*args))
                    except BaseException as exc:  # noqa: BLE001 - the future carries it
                        done.set_exception(exc)
            finally:
                self.jobs.task_done()

    def settled(self, seconds: float) -> bool:
        """Wait at most *seconds* until every queued job ended; whether they did."""
        until = time.monotonic() + seconds
        while self.jobs.unfinished_tasks and time.monotonic() < until:
            time.sleep(0.01)
        return not self.jobs.unfinished_tasks


WORK = Worker(2)
atexit.register(WORK.settled, GRACE)
