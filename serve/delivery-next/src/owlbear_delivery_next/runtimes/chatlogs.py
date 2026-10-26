"""Retro chatlogs (Improvement design §5): the evidence Retro reads, kept on this machine so it survives.

``~/.owlbear/retro/`` (owner-only) holds an append-only ``manifest.jsonl`` (each SDK session OwlBear runs: ``started``
with its owner, ``ended`` with its ending) and one snapshot folder per session, ``chatlogs/<session>/``: the runtime's
own ``~/.copilot/session-state/<session>/events.jsonl`` as ``log.jsonl.gz``, a ``sidecar.json`` saying when and from
which size and time it was copied, whether the copy is provisional (its session's end was not confirmed, or it may
resume), and in ``outputs/`` the large outputs the agent saw only as a saved file: copied when they are the runtime's
own output files in the temp folder, still there and within the bounds; listed as missing or refused otherwise. A
capture is a whole snapshot switched in for the last one: taking it again refreshes it when the log grew. Nothing here
reads a chat outside the enrolled folders, or judges anything; Retro does (design §5).
"""

from __future__ import annotations

import asyncio
import errno
import fcntl
import gzip
import json
import os
import re
import shutil
import stat
import sys
import tempfile
import threading
import time
from contextlib import contextmanager, suppress
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any, BinaryIO

import yaml

from owlbear_delivery_next.local_system import local_home

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Iterable, Iterator

    from owlbear_delivery_next.runtimes.session_result import Run

SAVED = re.compile(r"Saved to: (\S+copilot-tool-output-[\w.-]+)")
OUTPUTS, OUTPUT_BYTES = 50, 50 * 2**20  # at most this many saved outputs per session, and this many bytes in all
QUIET = timedelta(days=1)  # a chat with no event for this long counts as finished
KEPT = timedelta(days=30)  # a judged session's logs go this long after its judgement, unless something refers to them
CAPTURE = 120.0  # seconds a capture may take after its step; then it stops, and a later capture takes it again
LOCK = 10.0  # seconds a lock is waited for
CHUNK = 1 << 20


class Stopped(Exception):  # noqa: N818 - says what happened
    """A capture ran past its time, or its step was cancelled: the copy so far is dropped."""


def root() -> Path:
    """Where Retro's evidence is kept on this machine."""
    return local_home.root() / "retro"


def state() -> Path:
    """The runtime's own session records, read at call time (a test replaces HOME)."""
    return Path.home() / ".copilot" / "session-state"


def _private(folder: Path) -> Path:
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    folder.chmod(0o700)
    return folder


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


@contextmanager
def _locked(path: Path) -> Iterator[None]:
    """An exclusive lock on *path* across processes, waited for at most ``LOCK`` seconds."""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT, 0o600)
    try:
        until = time.monotonic() + LOCK
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() > until:
                    raise TimeoutError(f"{path.name} stayed locked") from None  # noqa: TRY003, EM102
                time.sleep(0.05)
        yield
    finally:
        os.close(fd)


def note(event: dict[str, Any]) -> None:
    """Append one line to the manifest under its lock; a failure is told on stderr and never raised."""
    try:
        folder = _private(root())
        with _locked(folder / "manifest.lock"):
            fd = os.open(folder / "manifest.jsonl", os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
            with os.fdopen(fd, "a") as out:
                out.write(json.dumps(event | {"at": _now()}) + "\n")
    except (OSError, TimeoutError) as exc:
        sys.stderr.write(f"retro chatlogs: manifest not written ({exc})\n")


def owner(kind: str, role: str, job: str, worktree: Path) -> dict[str, str]:
    """Whose session it is: its kind, role and job, and the folder it ran in (a worktree names project and Change)."""
    return {"kind": kind, "role": role, "job": job, "worktree": str(worktree)}


def sessions() -> set[str]:
    """Every session id the manifest names: OwlBear's own sessions, never taken for a chat."""
    try:
        lines = (root() / "manifest.jsonl").read_text().splitlines()
    except OSError:
        return set()
    found = set()
    for line in lines:
        with suppress(ValueError, AttributeError, KeyError, TypeError):
            found.add(str(json.loads(line)["session"]))
    return found


def _copy(src: BinaryIO, target: Path, limit: int | None, stop: threading.Event, until: float) -> int:
    """Stream *src* gzipped into *target*, atomically and owner-only; at most *limit* bytes; the bytes copied."""
    fd, tmp = tempfile.mkstemp(dir=target.parent, prefix=f".{target.name}.")
    copied = 0
    try:
        with os.fdopen(fd, "wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb") as out:
            while chunk := src.read(CHUNK if limit is None else min(CHUNK, limit - copied + 1)):
                _go_on(stop, until, over=limit is not None and copied + len(chunk) > limit)
                out.write(chunk)
                copied += len(chunk)
        Path(tmp).chmod(0o600)
        Path(tmp).replace(target)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
    return copied


def _go_on(stop: threading.Event, until: float, *, over: bool) -> None:
    """Raise ``Stopped`` when the capture was stopped, ran past its time, or a copy would pass its bound."""
    if over or stop.is_set() or time.monotonic() > until:
        raise Stopped


def _named(log: Path, stop: threading.Event, until: float) -> list[str]:
    """The first ``OUTPUTS`` saved-output paths the log's tool results name; stops with the capture.

    A message or a call's arguments quoting such a path never count.
    """
    seen: dict[str, None] = {}
    with log.open(errors="replace") as lines:
        for n, line in enumerate(lines):
            if n % 1000 == 0:
                _go_on(stop, until, over=False)
            if "Saved to:" in line:
                seen |= dict.fromkeys(p for text in _results(line) for p in SAVED.findall(text))
            if len(seen) >= OUTPUTS:
                break
    return list(seen)[:OUTPUTS]


def _results(line: str) -> list[str]:
    """A completed tool call's result texts, from one log line; nothing for any other event."""
    try:
        event = json.loads(line)
    except ValueError:
        return []
    if not isinstance(event, dict) or event.get("type") != "tool.execution_complete":
        return []
    result = (event.get("data") or {}).get("result") if isinstance(event.get("data"), dict) else None
    if isinstance(result, str):
        return [result]
    if isinstance(result, dict):
        return [v for k in ("content", "detailedContent") if isinstance(v := result.get(k), str)]
    return []


def _output(path: str, target: Path, room: int, stop: threading.Event, until: float) -> tuple[str, int]:
    """Copy one named output if it is the runtime's own regular file directly in the temp folder; else why not.

    The file is opened once, without following a link, and copied within *room* bytes.
    """
    temp, p = Path(tempfile.gettempdir()).resolve(), Path(path)
    try:
        if p.parent.resolve() != temp or not SAVED.fullmatch(f"Saved to: {p}"):
            return "refused", 0
        dfd = os.open(temp, os.O_RDONLY | os.O_DIRECTORY)
        try:
            fd = os.open(p.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=dfd)  # a FIFO never blocks
        finally:
            os.close(dfd)
    except FileNotFoundError:
        return "missing", 0
    except OSError as exc:
        return ("refused" if exc.errno == errno.ELOOP else "missing"), 0
    with os.fdopen(fd, "rb") as src:
        if not stat.S_ISREG(os.fstat(src.fileno()).st_mode):
            return "refused", 0
        try:
            return "kept", _copy(src, target, room, stop, until)
        except Stopped:
            if stop.is_set() or time.monotonic() > until:
                raise  # the whole capture stops: nothing is published, a later capture takes it again
            return "over the bound", 0


def capture(
    session: str,
    *,
    provisional: bool,
    records: Path | None = None,
    stop: threading.Event | None = None,
    seconds: float = CAPTURE,
) -> dict[str, Any]:
    """Copy *session*'s log and saved outputs as one snapshot folder under the session's lock; the sidecar's contents.

    A final, unchanged copy is kept as it is; a provisional one, or one asked for as provisional, is taken again. A new
    snapshot is staged whole and switched in for the old one, which stays if anything fails; an output whose temporary
    file is gone is carried over from the old snapshot.
    """
    folder, log = _private(root() / "chatlogs"), (records or state()) / session / "events.jsonl"
    live, stop, until = folder / session, stop or threading.Event(), time.monotonic() + seconds
    with _locked(folder / f".{session}.lock"):
        _recover(folder, session)
        before: dict[str, Any] = {}
        with suppress(OSError, ValueError):
            before = json.loads((live / "sidecar.json").read_text())
        try:
            st = log.stat()
        except OSError:
            said = {"session": session, "copied_at": _now(), "missing": True, "provisional": provisional,
                    "outputs": []}  # fmt: skip
            if not before:
                _switch(folder, session, said, None)
            return before or said
        final = (before.get("size"), before.get("mtime"), before.get("provisional")) == (st.st_size, st.st_mtime, False)
        if final and not provisional:
            return before
        stage = Path(tempfile.mkdtemp(dir=folder, prefix=f".stage-{session}-"))
        try:
            with log.open("rb") as src:
                size = _copy(src, stage / "log.jsonl.gz", None, stop, until)
            outputs = _outputs(log, stage, live, before, stop, until)
            _go_on(stop, until, over=False)
            said = {"session": session, "copied_at": _now(), "size": size, "mtime": st.st_mtime,
                    "provisional": provisional or size != st.st_size, "outputs": outputs}  # fmt: skip
            _switch(folder, session, said, stage)
            return said
        finally:
            shutil.rmtree(stage, ignore_errors=True)


def _outputs(  # noqa: PLR0913, PLR0917 - the log, both snapshots and the capture's bounds
    log: Path, stage: Path, live: Path, before: dict[str, Any], stop: threading.Event, until: float
) -> list[dict[str, Any]]:
    """Each named output copied into *stage*, or carried over from the live snapshot when its file is gone.

    Every kept output's bytes, carried ones included, count against the budget.
    """
    sizes = {o.get("path"): o.get("bytes") for o in before.get("outputs", []) if isinstance(o, dict)}
    used, outputs = 0, []
    for path in _named(log, stop, until):
        name = f"{Path(path).name}.gz"
        _private(stage / "outputs")
        verdict, n = _output(path, stage / "outputs" / name, OUTPUT_BYTES - used, stop, until)
        kept = live / "outputs" / name
        if verdict == "missing" and kept.is_file() and isinstance(sizes.get(path), int):  # the only copy left
            n = sizes[path]
            verdict = "kept" if used + n <= OUTPUT_BYTES else "over the bound"
            if verdict == "kept":
                shutil.copy2(kept, stage / "outputs" / name)
            else:
                n = 0
        used += n
        outputs.append({"path": path, "state": verdict, "bytes": n})
    return outputs


def _recover(folder: Path, session: str) -> None:
    """Finish a switch an exit interrupted: the old snapshot comes back if no new one took its place."""
    live, old = folder / session, folder / f".old-{session}"
    if old.exists() and not live.exists():
        old.rename(live)
    shutil.rmtree(old, ignore_errors=True)


def _switch(folder: Path, session: str, said: dict[str, Any], stage: Path | None) -> None:
    """Put a complete snapshot, its sidecar written into it first, in place of the old one.

    The old one comes back if the switch fails; the caller holds the session's lock.
    """
    stage = stage or Path(tempfile.mkdtemp(dir=folder, prefix=f".stage-{session}-"))
    _write(stage / "sidecar.json", said)
    live, old = folder / session, folder / f".old-{session}"
    shutil.rmtree(old, ignore_errors=True)
    if live.exists():
        live.rename(old)
    try:
        stage.rename(live)
        live.chmod(0o700)
    except BaseException:
        if old.exists() and not live.exists():
            old.rename(live)
        raise
    shutil.rmtree(old, ignore_errors=True)


def _write(path: Path, data: dict[str, Any]) -> None:
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    with os.fdopen(fd, "w") as out:
        json.dump(data, out)
    Path(tmp).chmod(0o600)
    Path(tmp).replace(path)


def kept(session: str, ending: str, *, provisional: bool, stop: threading.Event | None = None) -> None:
    """A session's end: its manifest line, then its capture; a failure is told on stderr and never raised."""
    note({"event": "ended", "session": session, "ending": ending, "provisional": provisional})
    try:
        capture(session, provisional=provisional, stop=stop)
    except Exception as exc:  # noqa: BLE001 - evidence is best effort: a step never fails for it
        sys.stderr.write(f"retro chatlogs: {session} not captured ({type(exc).__name__}: {exc})\n")


async def around(cfg: Any, step: Awaitable[Run], current: Callable[[], str] | None = None) -> Run:  # noqa: ANN401
    """Run *cfg*'s *step* between its manifest lines, then capture it; an interruption of the step: its line only.

    The capture runs in an owned daemon thread that stops at its deadline or when this is cancelled.
    """
    session, who = cfg.session_id, owner(cfg.kind.value, cfg.role, cfg.job, cfg.worktree)
    note({"event": "started", "session": session, **who})
    try:
        done = await step
    except BaseException:
        active = (current() if current else "") or session
        if active != session:  # a replacement was under way: its owner line too
            note({"event": "started", "session": active, "replaces": session, **who})
        note({"event": "ended", "session": active, "ending": "interrupted", "provisional": True})
        raise
    actual = done.session_id or session
    if actual != session:  # a replacement session: its own owner line, naming the one it replaces
        note({"event": "started", "session": actual, "replaces": session, **who})
    confirmed = done.termination is not None and done.termination.confirmed
    loop, stop = asyncio.get_running_loop(), threading.Event()
    finished = loop.create_future()

    def work() -> None:
        try:
            kept(actual, done.ending, provisional=not confirmed, stop=stop)
        finally:
            with suppress(RuntimeError):  # the loop closed meanwhile
                loop.call_soon_threadsafe(lambda: finished.done() or finished.set_result(None))

    threading.Thread(target=work, name=f"chatlog-{actual}", daemon=True).start()
    try:
        await asyncio.wait_for(asyncio.shield(finished), CAPTURE + LOCK + 5)
    except TimeoutError:
        stop.set()  # the copy stops at its next chunk; a later capture takes the session again
        sys.stderr.write(f"retro chatlogs: {actual} capture stopped at its deadline\n")
    except asyncio.CancelledError:
        stop.set()
        raise
    return done


def enrolled(cwd: str, folders: Iterable[str]) -> bool:
    """Whether a chat in *cwd* may be read: an absolute folder that is an enrolled one or inside one."""
    if not cwd or not Path(cwd).is_absolute():
        return False  # unknown or unreadable metadata never enrols a chat
    try:
        here = Path(cwd).resolve()
    except OSError, ValueError:
        return False
    return any(here.is_relative_to(Path(f).resolve()) for f in folders if f)


def _cwd(folder: Path) -> str:
    """A session's workspace folder, from ``workspace.yaml``: the only file read before enrolment is checked."""
    with suppress(OSError, ValueError, yaml.YAMLError):  # unreadable or invalid metadata: no folder, never enrolled
        data = yaml.safe_load((folder / "workspace.yaml").read_text())
        if isinstance(data, dict) and isinstance(cwd := data.get("cwd"), str):
            return cwd
    return ""


def finished_chats(folders: list[str], now: datetime, records: Path | None = None) -> Iterator[str]:
    """Enrolled chats with no event for a day, never one of OwlBear's own sessions; a day-old log is final enough.

    OwlBear's own sessions are those the manifest names (every SDK session runs through ``around``; a later session
    kind that does not, such as a Spotter look, notes itself there too) and any in its own folder (worktrees).
    """
    records = records or state()
    if not folders or not records.is_dir():
        return
    own, outside = sessions(), (local_home.root().resolve(),)
    for folder in sorted(p for p in records.iterdir() if p.is_dir()):
        cwd = _cwd(folder)
        if folder.name in own or not enrolled(cwd, folders) or any(Path(cwd).resolve().is_relative_to(o)
                                                                  for o in outside):  # fmt: skip
            continue
        with suppress(OSError):
            if now - datetime.fromtimestamp((folder / "events.jsonl").stat().st_mtime, UTC) >= QUIET:
                yield folder.name


def prune(now: datetime, judged: dict[str, datetime], pinned: set[str]) -> list[str]:
    """Remove each judged session's copies a month after its judgement, unless a finding, case or proposal pins it."""
    folder, gone = _private(root() / "chatlogs"), []
    for session, at in judged.items():
        if session in pinned or now - at < KEPT:
            continue
        with _locked(folder / f".{session}.lock"):  # never under a capture of the same session
            shutil.rmtree(folder / session, ignore_errors=True)
        gone.append(session)
    return gone
