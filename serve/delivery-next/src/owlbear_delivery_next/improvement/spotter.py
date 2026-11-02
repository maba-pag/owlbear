"""The Spotter (design §4): it records what it would say and the action its finding's category is set to, and acts.

It looks at a Delivery step's plan, its hand-offs, its state changes and a sample of its actions; it delays the step
only where its finding could answer a hand-off (below). The step's plan is its agent's first reply after the step's
own message (or a resumed session's answer), looked at once as it arrives (``Spotter.seen``), so a finding can steer
the turn that follows it. The machine host's chats follower (``machine_host.chats``) gives an
enrolled chat's hand-offs, plans, state changes and samples to one ``Spotter`` per chat, whose ``room`` admits at most
one chat look at a time and none while paused. Each look keeps the settings in force when it was admitted, and its
record the turn (requester message) it belongs to.

A look runs as a task on the step's own event loop when the hand-off (the submit tool's call) or a sampled completion
happens, over a frozen snapshot of the step's intake: the same moment and inputs a live look will have. The loop only
freezes the snapshot; the card and every file write run in threads. A look is one tool-less SDK session on the spotter
role in an empty folder, with no SDK credit cap, noted in the chatlogs manifest so it is never taken for a chat. At most
``RUNNING`` looks run at once per step. A hand-off look always gets a slot: at full capacity it takes the slot of the
youngest sample look not yet answered, else of such a state-change look (an answered one keeps it: its finding may act),
which is recorded as skipped for having given it (``GAVE``); with none of them it waits for a slot, within ``LOOK``. In
the chats follower the same holds across every chat's Spotter (``peers``). Each look stops at its own credit limit
(D-01M5XCD49YHHR1NQKKY8TQD0C3): its meter (``improvement.credit_meter``) adds the spend the runtime reports and the look
is stopped once it reaches the limit, cooperatively, so it may pass it; there is no daily budget. Another look over
capacity, a look past ``LOOK``, or one still running ``DRAIN`` seconds after the step ends is recorded as skipped; its
teardown takes at most ``TEARDOWN`` per stage, then its runtime is forced to stop. Each record keeps its spend, whether
that is known, its limit and its stop (``credit_meter.Meter.report``). How Delivery answered each hand-off is kept
beside its look. Records, outcomes and cards stay on this machine in ``~/.owlbear/spotter/`` (owner-only), written by
``improvement.spotter_store`` on its threads; this module re-exports the store's names its callers use. A record that
names a state change is marked preliminary; the decision-conflict check's completed answer, kept on its act, lets Retro
count it (``retro_units``).

A record keeps its finding's ``category`` (one of ``CATEGORIES``; ``none`` when silent, ``insufficient-context`` when
the card lacked the facts, ``failed`` for an unusable answer, empty when skipped) and the ``action`` the settings gave
that category when the step started. Records written before the categories (2026-10-26) carry the earlier ``mode`` and
``verdict`` (silent, note, interrupt) instead; their lines are left as they are.

A context the owner of the work gave an actuator (``Context.act``) acts on each finding, by the rules in
``improvement.acts``: after the record, the act is decided from the act lines of the record's session and scope (so a
rebuilt Spotter keeps its counts), its line written, then, unless nothing is sent, the actuator awaited on the look's
own loop; one that raises leaves the act ``failed`` with its whole error. Its return is not delivery: the actuator
confirms that from the runtime's own log. A finding naming a state change then asks ``Context.conflicts`` on a thread
of its own, and its answer is added to the act. Without an actuator nothing acts and no act line is written.

In a Delivery step the actuator is the step's own (``runtimes.spotter_act``), bound once its session opens: it steers
the running turn, stops it and resumes with a note, or stops it to ask the owner. When a hand-off look could act
(``acts.could_act``), the submit waits for it (``handed_off(held=True)``): the note the actuator gives back
refuses the hand-off, and a look that ends without one lets Delivery answer as before; one that failed or timed out
writes an act saying so.

While the steered-versus-silent test runs (``state_store.spotter_test``), every look admitted, Delivery's and a chat's,
whenever its Spotter was built, gets the model, effort, context and prompt the test froze at its start, and its record
names the test; a look admitted before the start keeps its own, and its record names none.
"""

from __future__ import annotations

import asyncio
import dataclasses
import functools
import json
import random
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.improvement import acts, card, cases, credit_meter
from owlbear_delivery_next.improvement.events import Kept, as_dict, clip, kept_text
from owlbear_delivery_next.improvement.spotter_store import (  # noqa: F401 - kept importable here
    GRACE,
    LOCK,
    WORK,
    _append,
    _today,
    place,
    root,
    store,
)
from owlbear_delivery_next.settings.improvement import CATEGORIES
from owlbear_delivery_next.state_store import spotter_test

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Iterable, Mapping

PROMPT = cases.PROMPT  # the prompt file; what a look sends is ``Context.prompt``, frozen with its examples
RUNNING = 2  # looks at once per step
LOOK, TEARDOWN, DRAIN = 90.0, 5.0, 5.0  # seconds a look's answer, each teardown stage and the step's end may take
SLOT = 0.05  # seconds between a waiting hand-off look's tries for a slot
GAVE = "gave its slot to a hand-off look"  # why a record-only look cancelled for a hand-off look is skipped
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
    arm: str | None = None  # the unit's arm of the steered-versus-silent test (``state_store.spotter_arms``)
    cap: int | None = None  # steering notes per step or chat turn: the Spotter's ``intervention_cap``
    act: Callable[[Record, acts.Act], Awaitable[None]] | None = None  # the actuator; None: nothing acts
    conflicts: Callable[[str], str] | None = None  # the decision-conflict check of a state change, its answer as text
    test: str = ""  # the running test whose frozen inputs a look admitted with (``frozen``); "": none


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
    turn: str = ""  # the requester message the moment belongs to: its event id
    category: str = ""
    action: str = ""  # the setting of the finding's category; what was done is its act (``improvement.acts``)
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
    test: str = ""  # the test whose frozen model and prompt the look used; "": none ran when it was admitted


def frozen(ctx: Context) -> Context:
    """*ctx* with the running test's frozen model, effort, context and prompt; *ctx* itself while none runs."""
    if (test := spotter_test.active()) is None:
        return ctx
    f = test["frozen"]
    prompt = cases.Prompt(f["prompt"], f["cases"], f["prompt_hash"])
    return dataclasses.replace(
        ctx, model=f["model"], effort=f["effort"], context=f["context"], prompt=prompt, test=test["id"]
    )


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

    def __init__(  # noqa: PLR0913 - a step's seams, and the chats follower's admission
        self,
        ctx: Context,
        session: Callable[[], str],
        judge: Judge,
        rng: random.Random | None = None,
        *,
        room: Callable[[], str] | None = None,
        left: Callable[[], None] | None = None,
        peers: Callable[[], Iterable[Spotter]] | None = None,
    ) -> None:
        """*room* admits a look ("") or says why none may start now, beyond this session's own capacity.

        *left* is told once when a look *room* admitted ends. *peers* are the Spotters sharing *room*'s slots, this one
        among them: a hand-off look may take the slot of a look of any of them.
        """
        if ctx.prompt is None:
            ctx = dataclasses.replace(ctx, prompt=cases.snapshot(verbose=ctx.verbose))
        self.ctx, self.session, self.kept, self.judge = ctx, session, Kept(), judge
        self.room, self.left = room or str, left
        self.peers = peers or (lambda: (self,))
        self.folder = place()  # where every write of this session goes, whatever changes later; made when written
        self.rng = rng or random.Random()  # noqa: S311 - sampling, not secrecy
        self.tasks: set[asyncio.Future[Any]] = set()
        self.running = 0  # looks admitted and not ended
        self.yielding: dict[asyncio.Future[Any], str] = {}  # running record-only looks not yet answered, by kind
        self.gave: set[asyncio.Future[Any]] = set()  # looks cancelled to give their slot to a hand-off look
        self.crowded: dict[str, int] = {}  # sampled looks skipped, by why, recorded once at the end
        self.closing = False  # the step ended: no look starts any more
        self.deciding = asyncio.Lock()  # one act decided and written at a time: each reads the lines of the last
        self.hand_offs: dict[str, asyncio.Future[str | None]] = {}  # a waiting submit's call id: the look's note
        self.planned = False  # the step's plan was seen live: ``seen`` looks at it once

    def seen(self, ev: Any) -> None:  # noqa: ANN401 - an SDK event, on the step's loop
        """Take one event in: its own agent's completed action may be sampled, its first reply is its plan."""
        d = as_dict(ev)
        unanswered = self.kept.first_reply is None
        if self.take(d):
            self.sample(d)
        elif unanswered and self.kept.first_reply and self.kept.turn and not self.planned:
            self.planned = True
            if "plan" in self.ctx.looks:  # the card shows the reply as the plan
                moment = {"at": d.get("timestamp"), "kind": "the agent's first reply after the requester's message",
                          "call": str(d.get("id") or "")}  # fmt: skip
                self._look("plan", 1.0, moment)

    def take(self, ev: Any) -> bool:  # noqa: ANN401 - an SDK event or a logged one
        """Take one event in without a look; whether it completed a call of the session's own agent."""
        return self.kept.add(ev)

    def sample(self, d: dict[str, Any]) -> None:
        """Maybe sample the completed call *d* for a look, at the configured rate."""
        if "sample" in self.ctx.looks and self.rng.random() * 100 < self.ctx.sample_rate:
            moment = {"at": d.get("timestamp"), "kind": "a completed action", "call": d["data"].get("toolCallId")}
            self._look("sample", self.ctx.sample_rate / 100, moment)

    def look(self, look: str, probability: float, moment: dict[str, Any]) -> None:
        """A look of kind *look* at *moment*, admitted now with the settings in force now, or recorded as skipped."""
        self._look(look, probability, moment)

    def skip(self, look: str, probability: float, moment: dict[str, Any], why: str) -> None:
        """No look of kind *look* at *moment*, for *why*: recorded as skipped, with the intake's turn and count now."""
        moment = {"turn": self.kept.turn, "cutoff": self.kept.n, **moment}  # a waited hand-off's own, frozen
        skipped = self._record(look, probability, moment, skipped=why)
        self._track(offload(store, self.folder, skipped, None))

    def history(self, events: Iterable[Any]) -> None:
        """A resumed session's transcript, taken in without looks: the task, plan and evidence the agent has."""
        for ev in events:
            self.kept.add(ev)

    def handed_off(
        self,
        call_id: str,
        arguments: Any,  # noqa: ANN401 - the submit tool's JSON arguments
        *,
        held: bool = False,
    ) -> asyncio.Future[str | None] | None:
        """A look at the step's hand-off (its submit call, before Delivery accepts it), if hand-offs are looked at.

        *held*: the submit waits for the look; the future gives the note it answers with, None once the look ended
        without one (or none started).
        """
        if "hand-off" not in self.ctx.looks:
            return None
        at = datetime.now(UTC).isoformat(timespec="seconds")
        moment = {"at": at, "kind": "hand-off", "call": call_id, "result": kept_text(arguments, 3000)}
        task = self._look("hand-off", 1.0, moment)
        if not held:
            return None
        waiter: asyncio.Future[str | None] = asyncio.get_running_loop().create_future()
        self.hand_offs[call_id] = waiter
        if task is None:
            waiter.set_result(None)
        else:
            task.add_done_callback(lambda _t: waiter.done() or waiter.set_result(None))
        return waiter

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

    def _record(self, look: str, probability: float, moment: dict[str, Any], ctx: Context | None = None,
                **fields: Any) -> Record:  # noqa: ANN401 # fmt: skip
        ctx = ctx or self.ctx
        return Record(id=uuid.uuid4().hex[:12], at=datetime.now(UTC).isoformat(timespec="seconds"),
                      project=ctx.project, change=ctx.change, step=ctx.step, session=self.session(), look=look,
                      call=str(moment.get("call") or ""), cutoff=int(moment.get("cutoff") or 0),
                      probability=probability, turn=str(moment.get("turn") or ""), model=ctx.model,
                      effort=ctx.effort, test=ctx.test, **fields)  # fmt: skip

    def _look(self, look: str, probability: float, moment: dict[str, Any]) -> asyncio.Future[Any] | None:
        """Freeze the intake and the settings now (a running test's own inputs among them); the rest runs in a task."""
        if self.closing:
            return None
        ctx = frozen(self.ctx)  # the test's inputs, while it runs; read before admission, so a raise leaks none
        if why := self._admitted():
            if look == "hand-off" and why.startswith("capacity"):  # it judges this moment, whatever comes in meanwhile
                return self._track(asyncio.ensure_future(self._waited(probability, *self._frozen(moment), ctx)))
            if look == "sample":  # a burst of samples is one count, not a write each
                self.crowded[why] = self.crowded.get(why, 0) + 1
            else:
                self.skip(look, probability, moment, why)
            return None
        return self._start(look, probability, *self._frozen(moment), ctx)

    def _frozen(self, moment: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        """The intake's snapshot now, and *moment* with its turn and cutoff."""
        snapshot = self.kept.snapshot()
        return snapshot, {"turn": snapshot["turn"], **moment, "cutoff": snapshot["n"]}

    def _admitted(self) -> str:
        """Admit one look now (""), or say why none may start."""
        return "capacity: looks already running" if self.running >= RUNNING else self.room()

    def _start(
        self, look: str, probability: float, snapshot: dict[str, Any], moment: dict[str, Any], ctx: Context
    ) -> asyncio.Future[Any]:
        self.running += 1
        task = self._run(look, probability, snapshot, moment, ctx)
        looked = self._track(asyncio.ensure_future(task))
        looked.add_done_callback(self._ended)
        if look in acts.RECORD_ONLY:
            self.yielding[looked] = look
        return looked

    async def _waited(self, probability: float, snapshot: dict[str, Any], moment: dict[str, Any], ctx: Context) -> None:
        """A hand-off look at full capacity, on its intake frozen then: it takes a slot or waits, within LOOK."""
        deadline, why = time.monotonic() + LOOK, "capacity: looks already running"
        while not self.closing and time.monotonic() < deadline:
            self._give()
            await asyncio.sleep(SLOT)
            if self.closing:
                break
            if not (why := self._admitted()):
                await self._start("hand-off", probability, snapshot, moment, ctx)
                return
            if not why.startswith("capacity"):
                break
        if self.closing:
            why = "capacity: looks still running when the step ended"
        self.skip("hand-off", probability, moment, why)

    def _give(self) -> None:
        """Free a slot for a waiting hand-off look: cancel the youngest sample look not yet answered, else state change.

        Every Spotter sharing the admission (``peers``) is asked; one already giving its slot frees it.
        """
        spots = list(self.peers())
        if any(s.gave for s in spots):
            return
        for kind in ("sample", "state-change"):
            for s in spots:
                if young := [t for t, k in s.yielding.items() if k == kind]:
                    task = young[-1]
                    del s.yielding[task]
                    s.gave.add(task)
                    task.cancel()
                    return

    def _ended(self, task: asyncio.Future[Any]) -> None:
        self.running -= 1
        self.yielding.pop(task, None)
        self.gave.discard(task)
        if self.left is not None:
            self.left()

    async def _run(
        self, look: str, probability: float, snapshot: dict[str, Any], moment: dict[str, Any], ctx: Context
    ) -> None:
        started, the_card = time.monotonic(), None
        record = self._record(look, probability, moment, ctx, skipped="the step ended before the look began")
        meter: credit_meter.Meter | None = None
        acting = False
        try:
            meter = credit_meter.Meter(ctx.limit, "look", ident=record.id)  # one identity: the record and its sessions
            gaps = [*ctx.gaps, *([ctx.prompt.gap] if ctx.prompt and ctx.prompt.gap else [])]
            context = {"step": ctx.step, "open_work": list(ctx.open_work), "decisions": list(ctx.decisions),
                       "gaps": gaps}  # fmt: skip
            the_card = await offload(card.build, snapshot, moment, context)
            record.skipped = "the step ended while the look ran"
            text = await asyncio.wait_for(self.judge(the_card, ctx, meter), LOOK)
            self.yielding.pop(asyncio.current_task(), None)  # answered: its finding may act, so it keeps its slot
            if not text and meter.stopped:
                record.skipped = f"credit limit: {meter.stopped} ({meter.stopped_by}) before an answer"
            else:
                said = parse(text)
                record.skipped, record.category = "", said["category"]
                record.action = ctx.actions.get(record.category, "")
                record.note = clip(said.get("note") or "", 1200)
                record.evidence = [clip(e, 300) for e in said.get("evidence") or [] if isinstance(e, str)][:8]
                record.state_change = clip(said.get("state_change") or "", 400)
                record.rationale = clip(said.get("rationale") or "", 1500)
                record.preliminary = bool(record.state_change)
                acting = ctx.act is not None and record.category in CATEGORIES
        except TimeoutError:
            record.skipped = f"time: the look took over {LOOK:.0f} seconds"
        except Exception as exc:  # noqa: BLE001 - a look never reaches the step
            record.category, record.skipped = "failed", f"{type(exc).__name__}: {exc}"
        finally:
            if asyncio.current_task() in self.gave:
                record.skipped = GAVE
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
        if acting:
            await self._act(record, ctx)
        elif look == "hand-off" and record.call in self.hand_offs and (record.skipped or record.category == "failed"):
            why = f"the hand-off was accepted: {record.skipped or 'the look gave an unusable answer'}"
            await offload(acts.write, self.folder, acts.held_back(record, ctx, why))

    async def _act(self, record: Record, ctx: Context) -> None:
        """Decide *record*'s act, write it and dispatch it unless nothing is sent; then check its state change."""
        async with self.deciding:
            sent, unresolved = await offload(acts.counts, self.folder, record.session, acts.scope(record, ctx))
            act = acts.decide(record, record.look, ctx, sent, unresolved)
            await offload(acts.write, self.folder, act)
        if act.act not in acts.UNSENT and ctx.act is not None:
            try:
                await ctx.act(record, act)
            except Exception as exc:  # noqa: BLE001 - kept on the act, whole; a look never reaches the step
                error = f"{type(exc).__name__}: {exc}"
                await offload(functools.partial(acts.update, self.folder, record.id, delivery="failed", error=error))
        if record.state_change:
            checking = acts.CHECKS.submit(acts.checked, self.folder, record.id, ctx.conflicts, record.state_change)
            await asyncio.shield(asyncio.wrap_future(checking))  # a stopped wait leaves the check to end on its thread

    async def drain(self) -> None:
        """At the step's end: no look starts any more; wait briefly for running ones, then stop the rest; bounded."""
        self.closing = True
        for why, n in self.crowded.items():
            said = f"capacity: {n} sampled looks skipped, looks already running" if why.startswith("capacity") else (
                f"{why}: {n} sampled looks skipped")  # fmt: skip
            skipped = self._record("sample", self.ctx.sample_rate / 100, {"kind": "samples"}, skipped=said)
            self._track(offload(store, self.folder, skipped, None))
        self.crowded = {}
        if not self.tasks:
            return
        _, pending = await asyncio.wait(set(self.tasks), timeout=DRAIN)
        for task in pending:
            task.cancel()
        if pending:
            await asyncio.wait(pending, timeout=4 * TEARDOWN)  # its spend's read, two teardown stages, its record
