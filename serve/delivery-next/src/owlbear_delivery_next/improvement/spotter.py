"""The Spotter (design §4): it records what it would say and the action its finding's category is set to, never acting.

It looks at a Delivery step's hand-offs and a sample of its actions, never delaying the step or changing its outcome.

A look runs as a task on the step's own event loop when the hand-off (the submit tool's call) or a sampled completion
happens, over a frozen snapshot of the step's intake: the same moment and inputs a live look will have. The loop only
freezes the snapshot; the card and every file write run in threads. A look is one tool-less SDK session on the spotter
role in an empty folder, with no SDK credit cap, noted in the chatlogs manifest so it is never taken for a chat. At most
``RUNNING`` looks run at once per step. Each look stops at its own credit limit (D-01M5XCD49YHHR1NQKKY8TQD0C3): its
meter (``improvement.credit_meter``) adds the spend the runtime reports and the look is stopped once it reaches the
limit, cooperatively, so it may pass it; there is no daily budget. A look over capacity, past ``LOOK``, or still running
``DRAIN`` seconds after the step ends is recorded as skipped; its teardown takes at most ``TEARDOWN`` per stage, then
its runtime is forced to stop. Each record keeps its spend, whether that is known, its limit and its stop
(``credit_meter.Meter.report``). How Delivery answered each hand-off is kept beside its look. Records, outcomes and
cards stay on this machine in ``~/.owlbear/spotter/`` (owner-only). A record that names a state change is marked
preliminary: the decision-conflict check comes with live delivery, so such records do not count toward going live.

A record keeps its finding's ``category`` (one of ``CATEGORIES``; ``none`` when silent, ``insufficient-context`` when
the card lacked the facts, ``failed`` for an unusable answer, empty when skipped) and the ``action`` the settings gave
that category when the step started; nothing acts on it yet. Records written before the categories (2026-10-26) carry
the earlier ``mode`` and ``verdict`` (silent, note, interrupt) instead; their lines are left as they are.
"""

from __future__ import annotations

import asyncio
import atexit
import contextlib
import dataclasses
import fcntl
import gzip
import json
import os
import queue
import random
import re
import threading
import time
import uuid
from concurrent.futures import Future
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.improvement import card, cases, credit_meter
from owlbear_delivery_next.improvement.events import Kept, as_dict, clip, kept_text
from owlbear_delivery_next.local_system import local_home
from owlbear_delivery_next.settings.improvement import CATEGORIES

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Iterable, Iterator, Mapping
    from pathlib import Path

PROMPT = cases.PROMPT  # the prompt file; what a look sends is ``Context.prompt``, frozen with its examples
RUNNING = 2  # looks at once per step
LOOK, TEARDOWN, DRAIN = 90.0, 5.0, 5.0  # seconds a look's answer, each teardown stage and the step's end may take
LOCK, GRACE = 5.0, 1.0  # seconds a file lock is waited for; and the Spotter's writes at the process's exit
ANSWERS = frozenset({*CATEGORIES, "none", "insufficient-context"})  # a finding's category, or why there is none


@dataclass(frozen=True)
class Context:
    """What the runner knows when the step starts: where, the Spotter's settings, the open work and the decisions."""

    project: str
    change: str
    step: str
    looks: tuple[str, ...]
    sample_rate: int  # percent of completed actions, when ``sample`` is a look
    verbose: bool
    model: str
    effort: str
    limit: float  # credits each look may spend: the Spotter's ``look_credit_limit``
    context: str = ""  # the role's context tier; "long" for the long one
    actions: Mapping[str, str] = field(default_factory=dict)  # each category's configured action
    open_work: tuple[str, ...] = ()
    decisions: tuple[str, ...] = ()
    gaps: tuple[str, ...] = ()  # what the runner could not give
    prompt: cases.Prompt | None = None  # frozen when the step starts (a chat: its turn); None: frozen by ``Spotter``


@dataclass
class Record:
    """One look, as stored."""

    id: str
    at: str
    project: str
    change: str
    step: str
    session: str
    look: str
    call: str  # the hand-off's or sampled action's call id
    cutoff: int  # the intake's events up to the moment
    probability: float
    category: str = ""
    action: str = ""  # the setting of the finding's category; recorded only, nothing acts yet
    note: str = ""
    evidence: list[str] = field(default_factory=list)
    state_change: str = ""
    rationale: str = ""
    preliminary: bool = False
    model: str = ""
    effort: str = ""
    prompt: str = ""  # the hash of exactly what the look sent before its card
    cases: int = 0  # the version of the Spotter cases its examples came from; 0: none
    sdk_sessions: list[str] = field(default_factory=list)  # the look's own SDK sessions; ``id`` joins them too
    credits: float = 0.0  # the known spend; see ``credit_meter.Meter.report`` for these six
    credits_known: bool = False  # a record without it predates measuring: its credits may be an estimate
    limit: float = 0.0
    stopped: str = ""
    stopped_by: str = ""
    seconds: float = 0.0
    skipped: str = ""


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


def parse(text: str) -> dict[str, Any]:
    """The look's JSON answer; one without a known ``category`` (an old ``verdict`` too) is "failed", never silence."""
    hit = re.search(r"\{.*\}", text or "", re.DOTALL)
    try:
        said = json.loads(hit.group(0)) if hit else {}
    except json.JSONDecodeError:
        said = {}
    if not isinstance(said, dict) or said.get("category") not in ANSWERS or not _well_formed(said):
        return {"category": "failed", "note": clip(text or "", 300)}
    return said


def _well_formed(said: dict[str, Any]) -> bool:
    """Whether every field the answer gives has its type: texts, or a list of texts for the evidence."""
    texts = all(said.get(k) is None or isinstance(said[k], str) for k in ("note", "state_change", "rationale"))
    evidence = said.get("evidence")
    noted = said["category"] not in CATEGORIES or bool(str(said.get("note") or "").strip())  # a finding is said
    listed = evidence is None or (isinstance(evidence, list) and all(isinstance(e, str) for e in evidence))
    return texts and noted and listed


async def through(task: asyncio.Future[Any]) -> None:
    """Await *task* (bounded) to its end, whatever cancels the caller meanwhile; then pass the caller's cancellation on.

    ``asyncio.wait`` raises only the caller's own cancellation, never the task's outcome, so the two are told apart.
    """
    cancelled = False
    while not task.done():
        try:
            await asyncio.wait({task})
        except asyncio.CancelledError:
            cancelled = True
    if cancelled:
        raise asyncio.CancelledError


def offload[T](work: Callable[..., T], *args: Any) -> asyncio.Future[T]:  # noqa: ANN401 - the work's arguments
    """Run *work* on the Spotter's own threads: a step's end never waits for it, and a stopped wait never drops it."""
    return asyncio.shield(asyncio.wrap_future(WORK.submit(work, *args)))


type Judge = Callable[[dict[str, Any], Context, credit_meter.Meter], Awaitable[str]]  # the answer; spend: the meter


class Spotter:
    """One step session's Spotter: its intake and its looks; nothing it does blocks the step's loop.

    *judge* runs one look (``runtimes.spotter_look``); a test gives its own.
    """

    def __init__(self, ctx: Context, session: Callable[[], str], judge: Judge,
                 rng: random.Random | None = None) -> None:  # fmt: skip
        if ctx.prompt is None:
            ctx = dataclasses.replace(ctx, prompt=cases.snapshot(verbose=ctx.verbose))
        self.ctx, self.session, self.kept, self.judge = ctx, session, Kept(), judge
        self.folder = place()  # where every write of this session goes, whatever changes later; made when written
        self.rng = rng or random.Random()  # noqa: S311 - sampling, not secrecy
        self.tasks: set[asyncio.Future[Any]] = set()
        self.running = 0  # looks admitted and not ended
        self.crowded = 0  # sampled looks skipped for capacity, recorded once at the end
        self.closing = False  # the step ended: no look starts any more

    def seen(self, ev: Any) -> None:  # noqa: ANN401 - an SDK event, on the step's loop
        """Take one event in; a completed action of the session's own agent may be sampled for a look."""
        d = as_dict(ev)
        if (self.kept.add(d) and "sample" in self.ctx.looks
                and self.rng.random() * 100 < self.ctx.sample_rate):  # fmt: skip
            moment = {"at": d.get("timestamp"), "kind": "a completed action", "call": d["data"].get("toolCallId")}
            self._look("sample", self.ctx.sample_rate / 100, moment)

    def history(self, events: Iterable[Any]) -> None:
        """A resumed session's transcript, taken in without looks: the task, plan and evidence the agent has."""
        for ev in events:
            self.kept.add(ev)

    def handed_off(self, call_id: str, arguments: Any) -> None:  # noqa: ANN401 - the submit tool's JSON arguments
        """A look at the step's hand-off (its submit call, before Delivery accepts it), if hand-offs are looked at."""
        if "hand-off" in self.ctx.looks:
            at = datetime.now(UTC).isoformat(timespec="seconds")
            self._look(
                "hand-off", 1.0, {"at": at, "kind": "hand-off", "call": call_id, "result": kept_text(arguments, 3000)}
            )

    def answered(self, call_id: str, outcome: str) -> None:
        """How Delivery answered the hand-off *call_id* (accepted, rejected or failed), kept beside its look.

        Called from the thread that handled it; the write goes to the Spotter's threads, so nothing cancels it.
        """
        line = {"at": datetime.now(UTC).isoformat(timespec="seconds"), "session": self.session(), "call": call_id,
                "outcome": outcome, "change": self.ctx.change, "step": self.ctx.step}  # fmt: skip
        WORK.submit(_append, self.folder, "outcomes", line)

    def _track(self, task: asyncio.Future[Any]) -> asyncio.Future[Any]:
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)
        return task

    def _record(self, look: str, probability: float, moment: dict[str, Any], **fields: Any) -> Record:  # noqa: ANN401
        ctx = self.ctx
        return Record(id=uuid.uuid4().hex[:12], at=datetime.now(UTC).isoformat(timespec="seconds"),
                      project=ctx.project, change=ctx.change, step=ctx.step, session=self.session(), look=look,
                      call=str(moment.get("call") or ""), cutoff=int(moment.get("cutoff") or 0),
                      probability=probability, model=ctx.model, effort=ctx.effort, **fields)  # fmt: skip

    def _look(self, look: str, probability: float, moment: dict[str, Any]) -> None:
        """Freeze the intake now; everything else runs in a task, its file work on the Spotter's own threads."""
        if self.closing:
            return
        if self.running >= RUNNING:
            if look == "sample":  # a burst of samples is one count, not a write each
                self.crowded += 1
            else:
                moment = {**moment, "cutoff": self.kept.n}
                skipped = self._record(look, probability, moment, skipped="capacity: looks already running")
                self._track(offload(store, self.folder, skipped, None))
            return
        snapshot = self.kept.snapshot()
        moment = {**moment, "cutoff": snapshot["n"]}
        self.running += 1
        self._track(asyncio.ensure_future(self._run(look, probability, snapshot, moment))).add_done_callback(
            self._ended
        )

    def _ended(self, _task: asyncio.Future[Any]) -> None:
        self.running -= 1

    async def _run(self, look: str, probability: float, snapshot: dict[str, Any], moment: dict[str, Any]) -> None:
        ctx, started, the_card = self.ctx, time.monotonic(), None
        record = self._record(look, probability, moment, skipped="the step ended before the look began")
        meter: credit_meter.Meter | None = None
        try:
            meter = credit_meter.Meter(ctx.limit, "look", ident=record.id)  # one identity: the record and its sessions
            gaps = [*ctx.gaps, *([ctx.prompt.gap] if ctx.prompt and ctx.prompt.gap else [])]
            context = {"step": ctx.step, "open_work": list(ctx.open_work), "decisions": list(ctx.decisions),
                       "gaps": gaps}  # fmt: skip
            the_card = await offload(card.build, snapshot, moment, context)
            record.skipped = "the step ended while the look ran"
            text = await asyncio.wait_for(self.judge(the_card, ctx, meter), LOOK)
            if not text and meter.stopped:
                record.skipped = f"credit limit: {meter.stopped} ({meter.stopped_by}) before an answer"
                return
            said = parse(text)
            record.skipped, record.category = "", said["category"]
            record.action = ctx.actions.get(record.category, "")
            record.note = clip(said.get("note") or "", 1200)
            record.evidence = [clip(e, 300) for e in said.get("evidence") or [] if isinstance(e, str)][:8]
            record.state_change = clip(said.get("state_change") or "", 400)
            record.rationale = clip(said.get("rationale") or "", 1500)
            record.preliminary = bool(record.state_change)
        except TimeoutError:
            record.skipped = f"time: the look took over {LOOK:.0f} seconds"
        except Exception as exc:  # noqa: BLE001 - a look never reaches the step
            record.category, record.skipped = "failed", f"{type(exc).__name__}: {exc}"[:300]
        finally:
            record.prompt, record.cases = ctx.prompt.hash if ctx.prompt else "", ctx.prompt.cases if ctx.prompt else 0
            record.seconds = round(time.monotonic() - started, 1)
            if meter is not None:  # without one (a limit it refused) nothing ran: the record still says why
                spend = meter.report()
                record.credits, record.credits_known, record.limit = (
                    spend["credits"],
                    spend["credits_known"],
                    spend["limit"],
                )
                record.stopped, record.stopped_by = spend["stopped"], spend["stopped_by"]
                record.sdk_sessions = spend["sdk_sessions"]
            writing = asyncio.wrap_future(WORK.submit(store, self.folder, record, the_card))  # never cancelled
            await asyncio.wait({writing}, timeout=2 * LOCK)  # it goes on if this wait ends

    async def drain(self) -> None:
        """At the step's end: no look starts any more; wait briefly for running ones, then stop the rest; bounded."""
        self.closing = True
        if self.crowded:
            why = f"capacity: {self.crowded} sampled looks skipped, looks already running"
            skipped = self._record("sample", self.ctx.sample_rate / 100, {"kind": "samples"}, skipped=why)
            self.crowded = 0
            self._track(offload(store, self.folder, skipped, None))
        if not self.tasks:
            return
        _, pending = await asyncio.wait(set(self.tasks), timeout=DRAIN)
        for task in pending:
            task.cancel()
        if pending:
            await asyncio.wait(pending, timeout=4 * TEARDOWN)  # its spend's read, two teardown stages, its record


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
