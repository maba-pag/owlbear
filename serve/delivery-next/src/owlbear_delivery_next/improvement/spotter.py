"""The Spotter in learning mode (design §4): it records what it would say, never sending anything.

It looks at a Delivery step's hand-offs and a sample of its actions, never delaying the step or changing its outcome.

A look runs as a task on the step's own event loop when the hand-off (the submit tool's call) or a sampled completion
happens, over a frozen snapshot of the step's intake: the same moment and inputs a live look will have. The loop only
freezes the snapshot; the reservation, the card and every file write run in threads. A look is one tool-less SDK
session on the spotter role in an empty folder, its credits capped at ``ESTIMATE``, noted in the chatlogs manifest so
it is never taken for a chat. At most ``RUNNING`` looks run at once per step; each reserves ``ESTIMATE`` against the
day's Spotter budget in a locked ledger before it starts and settles its spend after (the estimate when unknown). A look
over capacity, over budget, past ``LOOK``, or still running ``DRAIN`` seconds after the step ends is recorded as
skipped; its teardown takes at most ``TEARDOWN`` per stage, then its runtime is forced to stop. How Delivery answered
each hand-off is kept beside its look. Records, outcomes and cards stay on this machine in ``~/.owlbear/spotter/``
(owner-only). A record that names a state change is marked preliminary: the decision-conflict check comes with live
delivery, so such records do not count toward going live.
"""

from __future__ import annotations

import asyncio
import atexit
import contextlib
import fcntl
import gzip
import hashlib
import json
import os
import queue
import random
import re
import tempfile
import threading
import time
import uuid
from concurrent.futures import Future
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.improvement import card
from owlbear_delivery_next.improvement.events import Kept, as_dict, clip, kept_text
from owlbear_delivery_next.local_system import local_home

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Iterable, Iterator

PROMPT = Path(__file__).with_name("spotter_prompt.md")
RUNNING, ESTIMATE = 2, 0.5  # looks at once per step; credits a look reserves, and its SDK credit limit
LOOK, TEARDOWN, DRAIN = 90.0, 5.0, 5.0  # seconds a look's answer, each teardown stage and the step's end may take
LOCK, GRACE = 5.0, 1.0  # seconds a file lock is waited for; and the Spotter's writes at the process's exit
VERDICTS = frozenset({"silent", "note", "interrupt", "insufficient-context"})


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
    budget: int  # credits a day for every look on this machine
    context: str = ""  # the role's context tier; "long" for the long one
    mode: str = "learning"
    open_work: tuple[str, ...] = ()
    decisions: tuple[str, ...] = ()
    gaps: tuple[str, ...] = ()  # what the runner could not give


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
    mode: str
    verdict: str = ""
    note: str = ""
    evidence: list[str] = field(default_factory=list)
    state_change: str = ""
    rationale: str = ""
    preliminary: bool = False
    model: str = ""
    effort: str = ""
    prompt: str = ""
    credits: float = 0.0
    seconds: float = 0.0
    skipped: str = ""


def root() -> Path:
    """Where the Spotter's records, cards and ledger are kept on this machine."""
    folder = local_home.root() / "spotter"
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    (folder / "cards").mkdir(exist_ok=True, mode=0o700)
    return folder


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
    with contextlib.suppress(OSError, TimeoutError), _locked(folder / "records.lock"):
        fd = os.open(folder / f"{name}-{_today()}.jsonl", os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        with os.fdopen(fd, "a") as out:
            out.write(json.dumps(line) + "\n")


def store(folder: Path, record: Record, card_: dict[str, Any] | None) -> None:
    """Keep *record*'s card and append the record to the day's records in *folder*; a failure never reaches the step."""
    with contextlib.suppress(OSError):
        if card_ is not None:
            fd = os.open(folder / "cards" / f"{record.id}.json.gz", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "wb") as raw, gzip.open(raw, "wt") as out:
                json.dump(card_, out)
    _append(folder, "records", asdict(record))


class LedgerError(Exception):
    """The day's budget ledger cannot be read or written."""

    def __init__(self, why: object) -> None:
        super().__init__(f"the ledger failed: {why}")


type Token = tuple[str, str]  # the day a reservation was made on, and its id


def _ledger(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"reserved": {}, "spent": 0.0}
    try:
        ledger = json.loads(path.read_text())
        float(ledger["spent"]), sum(float(v) for v in ledger["reserved"].values())
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        raise LedgerError(exc) from exc
    return ledger


def _put(path: Path, ledger: dict[str, Any]) -> None:
    """Write *ledger* whole or not at all: a killed writer leaves the previous one."""
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".ledger-")
    try:
        with os.fdopen(fd, "w") as out:
            json.dump(ledger, out)
        Path(tmp).replace(path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def reserve(folder: Path, budget: int, estimate: float = ESTIMATE) -> Token | None:
    """Reserve *estimate* credits of today's Spotter budget across processes; None when it would pass the budget.

    A reservation its process never settles (it was killed) stays counted for its day: the budget errs on the safe side.

    Raises:
        LedgerError: The day's ledger cannot be read or written.
    """
    day, rid = _today(), uuid.uuid4().hex[:12]
    try:
        with _locked(folder / "ledger.lock"):
            path = folder / f"ledger-{day}.json"
            ledger = _ledger(path)
            if sum(ledger["reserved"].values()) + ledger["spent"] + estimate > budget:
                return None
            ledger["reserved"][rid] = estimate
            _put(path, ledger)
    except (OSError, TimeoutError) as exc:
        raise LedgerError(repr(exc)) from exc
    return day, rid


def settle(folder: Path, token: Token, actual: float) -> None:
    """End the reservation *token* on its own day's ledger in *folder* and book what the look cost; never raises."""
    day, rid = token
    with contextlib.suppress(OSError, TimeoutError, LedgerError), _locked(folder / "ledger.lock"):
        path = folder / f"ledger-{day}.json"
        ledger = _ledger(path)
        if ledger["reserved"].pop(rid, None) is not None:
            ledger["spent"] += actual
            _put(path, ledger)


def prompt_version() -> str:
    """The prompt's version: the start of its content's hash."""
    return hashlib.sha256(PROMPT.read_bytes()).hexdigest()[:12]


def parse(text: str) -> dict[str, Any]:
    """The look's JSON verdict; a verdict it did not give is "failed", never silence."""
    hit = re.search(r"\{.*\}", text or "", re.DOTALL)
    try:
        said = json.loads(hit.group(0)) if hit else {}
    except json.JSONDecodeError:
        said = {}
    if not isinstance(said, dict) or said.get("verdict") not in VERDICTS:
        return {"verdict": "failed", "note": clip(text or "", 300)}
    return said


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
    """Run *work* on the Spotter's own threads: a step's loop never waits for it when it ends."""
    return asyncio.wrap_future(WORK.submit(work, *args))


type Judge = Callable[[dict[str, Any], Context], Awaitable[tuple[str, float]]]


class Spotter:
    """One step session's Spotter: its intake and its looks; nothing it does blocks the step's loop.

    *judge* runs one look (``runtimes.spotter_look``); a test gives its own.
    """

    def __init__(self, ctx: Context, session: Callable[[], str], judge: Judge,
                 rng: random.Random | None = None) -> None:  # fmt: skip
        self.ctx, self.session, self.kept, self.judge = ctx, session, Kept(), judge
        self.folder = root()  # where every write of this session goes, whatever changes later
        self.rng = rng or random.Random()  # noqa: S311 - sampling, not secrecy
        self.tasks: set[asyncio.Future[Any]] = set()
        self.running = 0  # looks admitted and not ended
        self.crowded = 0  # sampled looks skipped for capacity, recorded once at the end

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
        """How Delivery answered the hand-off *call_id* (accepted, rejected or failed), kept beside its look."""
        line = {"at": datetime.now(UTC).isoformat(timespec="seconds"), "session": self.session(), "call": call_id,
                "outcome": outcome, "change": self.ctx.change, "step": self.ctx.step}  # fmt: skip
        self._track(offload(_append, self.folder, "outcomes", line))

    def _track(self, task: asyncio.Future[Any]) -> asyncio.Future[Any]:
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)
        return task

    def _record(self, look: str, probability: float, moment: dict[str, Any], **fields: Any) -> Record:  # noqa: ANN401
        ctx = self.ctx
        return Record(id=uuid.uuid4().hex[:12], at=datetime.now(UTC).isoformat(timespec="seconds"),
                      project=ctx.project, change=ctx.change, step=ctx.step, session=self.session(), look=look,
                      call=str(moment.get("call") or ""), cutoff=int(moment.get("cutoff") or 0),
                      probability=probability, mode=ctx.mode, model=ctx.model, effort=ctx.effort, **fields)  # fmt: skip

    def _look(self, look: str, probability: float, moment: dict[str, Any]) -> None:
        """Freeze the intake now; everything else runs in a task, its file work on the Spotter's own threads."""
        if self.running >= RUNNING:
            if look == "sample":  # a burst of samples is one count, not a write each
                self.crowded += 1
            else:
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
        ctx, started, the_card, spent = self.ctx, time.monotonic(), None, 0.0
        record = self._record(look, probability, moment, skipped="the step ended before the look began")
        reserving = WORK.submit(reserve, self.folder, ctx.budget)  # owned from here: its end starts ``_finished``
        try:
            if await asyncio.shield(asyncio.wrap_future(reserving)) is None:
                record.skipped = "budget: today's Spotter budget is spent"
                return
            context = {"step": ctx.step, "open_work": list(ctx.open_work), "decisions": list(ctx.decisions),
                       "gaps": list(ctx.gaps)}  # fmt: skip
            the_card = await offload(card.build, snapshot, moment, context)
            record.skipped, spent = "the step ended while the look ran", ESTIMATE  # unknown until it answers
            text, spent = await asyncio.wait_for(self.judge(the_card, ctx), LOOK)
            said = parse(text)
            record.skipped, record.verdict = "", said["verdict"]
            record.note = clip(said.get("note") or "", 1200)
            record.evidence = [clip(e, 300) for e in said.get("evidence") or [] if isinstance(e, str)][:8]
            record.state_change = clip(said.get("state_change") or "", 400)
            record.rationale = clip(said.get("rationale") or "", 1500)
            record.preliminary = bool(record.state_change)
        except TimeoutError:
            record.skipped = f"time: the look took over {LOOK:.0f} seconds"
        except LedgerError as exc:
            record.skipped = f"budget: {exc}"[:300]
        except Exception as exc:  # noqa: BLE001 - a look never reaches the step
            record.verdict, record.skipped = "failed", f"{type(exc).__name__}: {exc}"[:300]
        finally:
            record.prompt, record.seconds = prompt_version(), round(time.monotonic() - started, 1)
            finishing: Future[None] = Future()
            reserving.add_done_callback(
                lambda r: WORK.submit(_finished, self.folder, r, record, the_card, spent).add_done_callback(
                    lambda _: finishing.set_result(None)
                )
            )  # once the reservation ends, never before: what it reserved is always settled, even if the step stops
            await asyncio.wait({asyncio.wrap_future(finishing)})

    async def drain(self) -> None:
        """At the step's end: wait briefly for running looks, then stop the rest; bounded, recorded either way."""
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
            await asyncio.wait(pending, timeout=3 * TEARDOWN)  # its two teardown stages, then its record


def _finished(
    folder: Path, reserving: Future[Token | None], record: Record, the_card: dict[str, Any] | None, spent: float
) -> None:
    """On the Spotter's threads, once *reserving* ended: adopt what it reserved, store the record, settle once."""
    token = reserving.result() if not reserving.cancelled() and reserving.exception() is None else None
    if token is None and record.skipped.startswith("the step ended before"):
        record.skipped = "the step ended before the look began; nothing was reserved"
    record.credits = spent if token else 0.0
    store(folder, record, the_card)
    if token is not None:
        settle(folder, token, spent)  # an unknown spend counts as the estimate, the look's credit limit


class Worker:
    """The Spotter's own daemon threads, first in, first out: the process waits at most ``GRACE`` for them at exit.

    What a killed write loses errs on the safe side: a ledger is replaced whole, and an unsettled reservation stays
    counted for its day.
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
