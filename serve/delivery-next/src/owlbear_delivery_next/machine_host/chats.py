"""The chats follower (Improvement design §4, "Where: Chats"): the Spotter's looks at enrolled chats, recording only.

One follower runs in the machine host, on its own thread with its own event loop, and holds
``~/.owlbear/spotter/chats.lock`` from before its first read until its thread ends, after its looks drained and its
records were written. A second follower (the next version's host after a handover, while this one still ends) reads
and admits nothing until it holds the lock, and says that it waits: at most one follows the chats.

Every ``POLL`` seconds, one pass:

1. The Spotter's settings, Global's under this machine's (``chat_settings``), and the enrolled chats. Off, unset
   or unreadable: no chat is read, and what was followed is dropped.
2. The manifest of OwlBear's own sessions; unreadable, no chat is read this pass (provenance fails closed).
3. The chats: each session folder of the runtime the manifest does not name whose ``workspace.yaml`` (the only file
   read before enrolment is checked; read again whenever it or its metadata changes, never kept when unreadable) names
   a folder in an enrolled one and outside OwlBear's own. Only then is its ``events.jsonl`` opened.
4. Each chat's new bytes, at most ``PASS`` fetched a pass in all and ``CHUNK`` (``HISTORY`` for context) a read, the
   chats' order turning each pass. Each byte is fetched once: an event not yet complete is kept and continued at the
   next read; one over ``LINE`` bytes is left out and said in the chat's cards from then on.

Where a chat starts: one whose folder existed when the follower started following (at its start, when switched on and
when the enrolled folders change: the baseline, by folder names alone) starts at its end then; one found later starts
at its beginning. What came before the start is read as context once the chat grows, never looked at; so is a
replaced log, and so is a chat followed before and found again (its metadata was missing meanwhile): it starts at
its end then. A restart records each chat's bytes written while OwlBear was not following them as a gap
(D-01M5XCE8ZA4FGYYY45YP44M8RD), from the offsets the last run left in ``chats.json``. A chat without a new event for a
day goes dormant: its intake is dropped and its offset kept until it grows.

Admission (``room``): one chat look at a time across all chats, a draining one counted; none while the machine is
paused (D-01M5XCE8ZC030KT2FZ7D6SZCJN), once the follower closes, or while a look's runtime may still run (its lease
held, ``chat_looks``); the chats are read all the same. The state-change moment of a completed call is looked at
instead of a sample of it. Before any moment is settled or admitted, a chat's Spotter gets the settings in force (its
``look_credit_limit`` among them) and every gap known by then; its prompt and cases' snapshot
(``cases.snapshot``) is taken when a turn starts (a turn begun before following, at its first live event) and serves
every look of that turn. An admitted look keeps both, whatever changes before it runs, and its record keeps the turn,
the case version and prompt hash, and its meter's spend and stop.
"""

from __future__ import annotations

import asyncio
import dataclasses
import fcntl
import functools
import json
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.improvement import cases, spotter
from owlbear_delivery_next.machine_host import chat_looks, chat_offsets
from owlbear_delivery_next.machine_host.chat_settings import Plan, settings_now
from owlbear_delivery_next.runtimes import chatlogs, spotter_look
from owlbear_delivery_next.runtimes.chat_moments import Moments

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_delivery_next.local_system import maintenance

POLL = 5.0  # seconds between passes
CHUNK, HISTORY, PASS, LINE = 1 << 20, 8 << 20, 16 << 20, 8 << 20  # bytes: a live read, a context read, a pass, an event
LOOKS = 1  # chat looks at once on this machine
QUIET = chatlogs.QUIET.total_seconds()  # a chat without a new event this long goes dormant
CLOSE = spotter.DRAIN + 3 * spotter.TEARDOWN + 5.0  # seconds the machine's stop waits for the follower to end
LOCK = "chats.lock"


@dataclass
class Chat:
    """One chat as followed: where its log is read to, and its intake while it is not dormant."""

    id: str
    workspace: str
    offset: int = 0  # bytes read
    history: int = 0  # bytes before this are context, never looked at
    file: tuple[int, int] = (0, 0)  # the log's device and inode
    grew: float = 0.0  # when it last grew (wall clock)
    skipping: bool = False  # inside an event over ``LINE`` bytes
    partial: bytes = b""  # the bytes after *offset* already read: an event not yet complete
    spot: spotter.Spotter | None = None
    moments: Moments | None = None
    gaps: list[str] = field(default_factory=list)
    base: spotter.Context | None = None  # the settings of the latest pass
    turn: str = ""  # the turn *prompt* was taken for
    prompt: cases.Prompt | None = None  # the prompt and cases' snapshot taken at that turn's start
    verbose: bool = False  # the verbose setting it was taken with


class Follower:
    """The machine's chats follower; ``start`` it once, ``close`` and ``join`` it at the machine's stop."""

    def __init__(  # noqa: PLR0913 - the machine's seams, and a test's
        self,
        paused: Callable[[], bool],
        say: Callable[[str], None],
        *,
        read: Callable[[], Plan | str] = settings_now,
        judge: spotter.Judge | None = None,
        poll: float = POLL,
        sessions: Path | None = None,
        ownership: maintenance.Maintenance | None = None,
    ) -> None:
        """Nothing is read or written until it runs; *sessions* is the runtime's session folder (its own by default).

        With *ownership* (the machine's maintenance ledger) each look holds a lease (``chat_looks``).
        """
        self.paused, self.say, self.read, self.judge, self.poll = paused, say, read, judge, poll
        self.owned = chat_looks.Owned(ownership, say) if ownership is not None else None
        self.sessions = sessions
        self.closed, self.ended = threading.Event(), threading.Event()
        self.thread: threading.Thread | None = None
        self.chats: dict[str, Chat] = {}
        self.leaving: list[spotter.Spotter] = []  # the Spotters of chats no longer followed, while their looks end
        self.tasks: set[asyncio.Future[Any]] = set()  # their drains
        self.baseline: set[str] | None = None  # the session folders when following began; None while not following
        self.folders: tuple[str, ...] = ()
        self.last: dict[str, Any] = {}  # the last run's offsets, until its chats were found again
        self.restarted = True  # the first time following begins compares with the last run's offsets
        self.metadata: dict[str, tuple[tuple[int, ...], str]] = {}  # a session's workspace.yaml: its stamp, folder
        self.turns = 0
        self.said = ""
        self.saved: dict[str, Any] = {}

    def start(self) -> None:
        """Run on the follower's own daemon thread."""
        self.thread = threading.Thread(target=self.run, name="spotter-chats", daemon=True)
        self.thread.start()

    def close(self) -> None:
        """No look is admitted from now on; the follower drains its looks, keeps its offsets and ends."""
        self.closed.set()

    def join(self, seconds: float) -> bool:
        """Wait at most *seconds* for the follower to end; whether it ended (it keeps its lock until it does)."""
        if self.thread is not None:
            self.thread.join(seconds)
        return self.thread is None or not self.thread.is_alive()

    def room(self) -> str:
        """Why no chat look may start now, else ""; read on the follower's loop when a look is admitted."""
        if self.closed.is_set():
            return "stopping: OwlBear's chats follower is ending"
        if self.paused():
            return "paused: the machine is paused"
        self.leaving = [s for s in self.leaving if s.running]
        running = sum(c.spot.running for c in self.chats.values() if c.spot) + sum(s.running for s in self.leaving)
        if running >= LOOKS:
            return "capacity: a chat look is already running"
        if self.owned is not None and self.owned.lingering():
            return "held: a chat look's runtime may still run; no chat look starts until Maintenance recovers it"
        return ""

    def working(self) -> list[str]:
        """What a stop when idle and an update wait for: a chat look's runtime that may still run."""
        return [chat_looks.LINGERING] if self.owned is not None and self.owned.lingering() else []

    def run(self) -> None:
        """The thread: take the lock, follow until closed, drain and write, then let the lock go."""
        try:
            fd = os.open(spotter.root() / LOCK, os.O_WRONLY | os.O_CREAT, 0o600)
        except OSError as exc:
            self.say(f"chats follower: its lock cannot be opened ({exc}); no chat is followed")
            self.ended.set()
            return
        try:
            if not self._owned(fd):
                return
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(self._main())
            finally:
                if left := asyncio.all_tasks(loop):
                    for task in left:
                        task.cancel()
                    loop.run_until_complete(asyncio.wait(left, timeout=spotter.TEARDOWN))
                loop.close()
                spotter.WORK.settled(spotter.GRACE)  # its records are written before another follower may begin
        finally:
            os.close(fd)
            self.ended.set()

    def _owned(self, fd: int) -> bool:
        waited = False
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                if not waited:
                    self.say("chats follower: waiting for the previous one to end; no chat is read meanwhile")
                    waited = True
                if self.closed.wait(self.poll):
                    return False
            else:
                return True

    async def _main(self) -> None:
        while not self.closed.is_set():
            try:
                await self._pass()
            except Exception as exc:  # noqa: BLE001 - the follower outlives one failed pass
                self._tell(f"chats follower: a pass failed: {type(exc).__name__}: {exc}"[:300])
            await self._nap()
        await self._quit()

    async def _nap(self) -> None:
        until = time.monotonic() + self.poll
        while not self.closed.is_set() and time.monotonic() < until:  # noqa: ASYNC110 - another thread closes it
            await asyncio.sleep(min(0.05, self.poll))

    async def _quit(self) -> None:
        """Drain every chat's looks at once within one bound, then keep the offsets."""
        spots = [c.spot for c in self.chats.values() if c.spot] + self.leaving
        if spots:
            await asyncio.wait({asyncio.ensure_future(s.drain()) for s in spots}, timeout=CLOSE - spotter.GRACE - 2)
        self._save()

    def _tell(self, text: str) -> None:
        if text and text != self.said:
            self.say(text)
        self.said = text

    def _root(self) -> Path:
        return self.sessions or chatlogs.state()

    async def _pass(self) -> None:
        plan = self.read()
        if isinstance(plan, str):
            self._off(f"chats follower: {plan}; no chat is read")
            return
        if self.baseline is None or plan.folders != self.folders:
            self._begin(plan.folders)
        # The folders first, then the manifest: OwlBear notes a session before its folder exists, so every folder
        # listed here that is OwlBear's own is named in the manifest read after it.
        try:
            listed = sorted(p for p in self._root().iterdir() if p.is_dir())
        except OSError:
            listed = []
        ours = chatlogs.own()
        if ours is None:
            self._tell("chats follower: the manifest of OwlBear's own sessions cannot be read; no chat is read")
            return
        self._tell("")
        found = self._found(listed, ours, plan.folders)
        ids = sorted(found)
        self.turns += 1
        ids = ids[self.turns % len(ids) :] + ids[: self.turns % len(ids)] if ids else []
        left = PASS
        for cid in ids:
            if self.closed.is_set() or left <= 0:
                break
            left -= await self._tail(cid, found[cid], plan.ctx, left)
        self.last = {}  # what the last run left counts only for the chats found when following began
        self._save()

    def _off(self, why: str) -> None:
        self._tell(why)
        for cid in list(self.chats):
            self._forget(cid)
        self.baseline = None

    def _begin(self, folders: tuple[str, ...]) -> None:
        """Following begins, or the enrolled folders changed: the session folders now are the baseline."""
        if self.restarted:
            self.last, self.restarted = chat_offsets.load(), False
        self.folders = folders
        try:
            self.baseline = {p.name for p in self._root().iterdir() if p.is_dir()}
        except OSError:
            self.baseline = set()

    def _found(self, listed: list[Path], ours: set[str], folders: tuple[str, ...]) -> dict[str, str]:
        """Each chat of *listed* that may be read now, with its workspace; a chat followed that may not be is dropped.

        Only folders listed before *ours* was read: a session OwlBear starts later is listed at the next pass, by when
        the manifest names it.
        """
        found = {}
        for folder in listed:
            if cwd := chatlogs.chat(folder, folders, ours, self._workspace):
                found[folder.name] = cwd
        for cid in list(self.chats):
            if cid not in found:
                self._forget(cid)
        return found

    def _workspace(self, folder: Path) -> str:
        """``chatlogs.workspace``, read again whenever the file or its metadata changes; never kept when unreadable."""
        try:
            st = (folder / "workspace.yaml").stat()
        except OSError:
            self.metadata.pop(folder.name, None)
            return ""
        stamp = (st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns)  # ctime: its permissions changed too
        if (kept := self.metadata.get(folder.name)) is not None and kept[0] == stamp:
            return kept[1]
        if cwd := chatlogs.workspace(folder):
            self.metadata[folder.name] = (stamp, cwd)
        else:
            self.metadata.pop(folder.name, None)
        return cwd

    def _forget(self, cid: str) -> None:
        """Stop following *cid*; found again, it starts at its end then, what it held before being context only."""
        self._dormant(self.chats.pop(cid))
        if self.baseline is not None:
            self.baseline.add(cid)

    def _new(self, cid: str, cwd: str, size: int, file: tuple[int, int]) -> Chat:
        start = size if self.baseline is not None and cid in self.baseline else 0
        c = Chat(cid, cwd, offset=start, history=start, file=file, grew=time.time())
        if (old := self.last.get(cid)) is not None:
            was = (int(old.get("offset") or 0), tuple(old.get("file") or (0, 0)))
            if was[1] != file:
                chat_offsets.gap(
                    cid, "the chat's log was replaced while OwlBear was not following it; read as context only"
                )
            elif was[0] < start:
                missed = f"bytes {was[0]}..{start} of the chat's log were read as context, never looked at"
                chat_offsets.gap(cid, f"OwlBear was not following: {missed}")
        return c

    def _intake(self, c: Chat, ctx: spotter.Context) -> None:
        """The chat grew: its Spotter and moments, rebuilt from its beginning, what came before its start as context."""
        judge = self.judge or spotter_look.judged
        if self.owned is not None:
            judge = functools.partial(self.owned.judged, judge)
        c.spot = spotter.Spotter(self._ctx(c, ctx), lambda cid=c.id: cid, judge, room=self.room)
        c.moments = Moments(c.workspace, Path.home(), Path(os.environ["TMPDIR"]) if os.environ.get("TMPDIR") else None)
        c.history, c.offset, c.skipping, c.partial = max(c.history, c.offset), 0, False, b""

    async def _tail(self, cid: str, cwd: str, ctx: spotter.Context, left: int) -> int:
        """Read the chat's new complete lines, at most *left* bytes; the bytes read."""
        try:
            fd = os.open(self._root() / cid / "events.jsonl", os.O_RDONLY)
        except OSError:
            return 0
        try:
            st = os.fstat(fd)
            file = (st.st_dev, st.st_ino)
            if (c := self.chats.get(cid)) is None:
                c = self.chats[cid] = self._new(cid, cwd, st.st_size, file)
            if c.workspace != cwd or c.file != file or st.st_size < max(c.offset + len(c.partial), c.history):
                if c.file != file or st.st_size < max(c.offset + len(c.partial), c.history):
                    c.gaps.append("the chat's log was replaced; what it held then is context only")
                    c.offset = c.history = st.st_size
                self._dormant(c)
                c.workspace, c.file = cwd, file
            if c.spot is not None:  # what this pass admits uses today's settings; admitted looks keep theirs
                c.spot.ctx = self._ctx(c, ctx)
            if st.st_size == max(c.offset + len(c.partial), c.history) and (c.spot is None or c.offset >= c.history):
                self._still(c)
                return 0
            if c.spot is None:
                self._intake(c, ctx)
            c.grew = time.time()
            return await self._read(c, fd, st.st_size, left)
        finally:
            os.close(fd)

    def _ctx(self, c: Chat, ctx: spotter.Context) -> spotter.Context:
        """*ctx* (this pass's settings) for chat *c*: its gaps, and its turn's prompt snapshot once taken."""
        c.base = ctx
        made = dataclasses.replace(ctx, gaps=(*ctx.gaps, *c.gaps, *self._forgotten(c)))
        return dataclasses.replace(made, prompt=c.prompt, verbose=c.verbose) if c.prompt is not None else made

    def _snapped(self, c: Chat) -> None:
        """The prompt and cases' snapshot for the chat's turn, taken when the turn starts; a look admitted keeps it.

        A turn that began before OwlBear followed it takes its snapshot at its first live event or moment.
        """
        if c.spot is None or c.base is None or (c.prompt is not None and c.turn == c.spot.kept.turn):
            return
        c.turn, c.verbose = c.spot.kept.turn, c.base.verbose
        c.prompt = cases.snapshot(verbose=c.verbose)
        c.spot.ctx = self._ctx(c, c.base)

    def _fresh(self, c: Chat) -> None:
        """Before a look is admitted: its turn's snapshot, and this pass's settings with every gap known by now."""
        self._snapped(c)
        if c.spot is not None and c.base is not None:
            c.spot.ctx = self._ctx(c, c.base)

    def _forgotten(self, c: Chat) -> tuple[str, ...]:
        n = c.moments.forgotten if c.moments else 0
        return (f"{n} of the agent's calls were open too long to be judged when they completed",) if n else ()

    def _dormant(self, c: Chat) -> None:
        if c.spot is not None:  # its looks end on their own; they count until they have
            self.leaving.append(c.spot)
            task = asyncio.ensure_future(c.spot.drain())
            self.tasks.add(task)
            task.add_done_callback(self.tasks.discard)
        c.spot, c.moments = None, None
        c.history = max(c.history, c.offset)  # an event not yet complete is read again, as context
        c.offset, c.partial = c.history, b""

    def _still(self, c: Chat) -> None:
        """No new byte: settle its turn; a day without one makes it dormant."""
        if c.moments is not None and c.spot is not None and not c.skipping:
            for m in c.moments.settle(frontier=True, now=time.monotonic()):
                self._admit(c, m)
        if c.spot is not None and not c.spot.running and time.time() - c.grew >= QUIET:
            self._dormant(c)

    async def _read(self, c: Chat, fd: int, size: int, left: int) -> int:
        """Read *c*'s log up to *size*, fetching at most *left* bytes; the bytes fetched.

        Every byte is fetched once: an event not yet complete stays in ``Chat.partial`` (at most ``LINE`` bytes) and
        the next read, in this pass or a later one, goes on after it.
        """
        fetched = 0
        while (at := c.offset + len(c.partial)) < size and fetched < left and not self.closed.is_set():
            data = os.pread(fd, min(HISTORY if c.offset < c.history else CHUNK, size - at, left - fetched), at)
            if not data:  # the log shrank since it was measured: the next pass finds it replaced
                break
            fetched += len(data)
            if c.skipping:
                nl = data.find(b"\n")
                step = len(data) if nl < 0 else nl + 1
                c.offset, c.skipping, data = c.offset + step, nl < 0, data[step:]
            self._lines(c, c.partial + data)
            await asyncio.sleep(0)  # the looks' tasks run between reads
        if c.moments is not None and not c.skipping:
            for m in c.moments.settle(frontier=c.offset >= size, now=time.monotonic()):
                self._admit(c, m)
        return fetched

    def _lines(self, c: Chat, data: bytes) -> None:
        """Take in *data*'s complete events, read from ``Chat.offset``; keep the rest; skip an event over ``LINE``."""
        nl = data.rfind(b"\n")
        start = c.offset
        for line in data[: nl + 1].splitlines(keepends=True):
            if len(line) > LINE + 1:
                self._left_out(c)
            else:
                self._event(c, line, live=start >= c.history)
            start += len(line)
        c.offset, c.partial = start, data[nl + 1 :]
        if len(c.partial) > LINE:
            c.offset, c.partial, c.skipping = c.offset + len(c.partial), b"", True
            self._left_out(c)

    def _left_out(self, c: Chat) -> None:
        c.gaps.append(f"an event over {LINE >> 20} MiB was left out")
        if c.spot is not None and c.base is not None:  # the next look of this read says so
            c.spot.ctx = self._ctx(c, c.base)

    def _event(self, c: Chat, line: bytes, *, live: bool) -> None:
        try:
            d = json.loads(line)
        except ValueError:
            return
        if not isinstance(d, dict) or c.spot is None or c.moments is None:
            return
        before, after = c.moments.feed(d, live=live, now=time.monotonic())
        for m in before:  # a turn the event closes is looked at before the event enters the card
            self._admit(c, m)
        completed = c.spot.take(d)
        if not live:
            return
        self._snapped(c)  # a requester message starts a turn: its snapshot, before any look of it
        changed = False
        for m in after:
            changed = self._admit(c, m) or changed
        if completed and not changed:
            self._fresh(c)
            c.spot.sample(d)

    def _admit(self, c: Chat, moment: dict[str, Any]) -> bool:
        """Look at *moment* if its kind is a look; whether it is a state change looked at (or skipped as one)."""
        look = moment.pop("look")
        if c.spot is None or look not in c.spot.ctx.looks:
            return False
        self._fresh(c)
        c.spot.look(look, 1.0, moment)
        return look == "state-change"

    def _save(self) -> None:
        """Keep each followed chat's offset for the next run's gap record (``chat_offsets``)."""
        now = {c.id: {"offset": max(c.offset, c.history), "file": list(c.file)} for c in self.chats.values()}
        if now != self.saved and chat_offsets.save(now):
            self.saved = now
