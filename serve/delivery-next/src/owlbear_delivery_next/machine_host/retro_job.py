"""Retro's job in the machine host (#715, Improvement design §5): one unit revision per run, one paid call at a time.

Each paid call is admitted on its own: it takes a slot of the job's share (``SLOT``), re-reads the fence, a stop, the
run's switch, pause and idle time and the unit's eligibility under the machine's stop barrier, and holds a
maintenance lease from before its session to the confirmed end of its runtime; nothing is held between calls. A call
refused between calls leaves the run waiting at its cursor (its kept answers), taken up again once admitted. A
runtime whose end is not confirmed keeps its lease, and with it the slot, held: the run ends at its next call and no
Retro call starts until Maintenance recovers it.

On start, an open run resumes on the rest of its allowance only when no call of it is unsettled and its spend is
known; otherwise it ends ``stopped: unknown spend after an interruption`` and its unit waits for the button. Per
pass: the button's requests (they bypass both switches and pause, never the fence, eligibility or a held lease), then
a waiting run, then Changes due when ``retro_after_change`` allows, then enrolled chats due when OwlBear is idle and
``retro_when_idle`` allows, and once a day the pruning of judged chat captures no finding, case or open proposal pins.
An unset limit or role, or a retired assumption the run needs, refuses the run, recorded. While a setting of the
unit's project is unset (``retro_block``), the button's run is refused, recorded, and the automatic ones wait.
"""

from __future__ import annotations

import asyncio
import contextlib
import functools
import logging
import threading
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.improvement import retro_judge
from owlbear_delivery_next.improvement import retro_store as store
from owlbear_delivery_next.improvement import retro_synthetic as syn
from owlbear_delivery_next.improvement import retro_units as units
from owlbear_delivery_next.improvement.credit_meter import Meter
from owlbear_delivery_next.improvement.retro_calls import Paid, StoppedError, WaitingError, Work
from owlbear_delivery_next.improvement.retro_evidence import evidence
from owlbear_delivery_next.local_system import maintenance, processes
from owlbear_delivery_next.machine_host import cases_job, retro_block
from owlbear_delivery_next.machine_host.auto_update import IDLE_FOR
from owlbear_delivery_next.machine_host.retro_inputs import (
    Running,
    enrolled,
    failed_grading,
    prune,
    session,
    settle_open,
    unfinished,
    where,
)
from owlbear_delivery_next.runtimes import retro_review, spotter_look
from owlbear_delivery_next.runtimes.session_result import Run
from owlbear_delivery_next.settings.config import SettingsUnset
from owlbear_delivery_next.state_store import machine_settings, registry, spend_ledger

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from contextlib import AbstractContextManager

    from owlbear_delivery_next.local_system.slots import Slots
    from owlbear_delivery_next.machine_host.machine import Machine

LOG = logging.getLogger(__name__)
SLOT = KIND = "retro"  # the job's share of the machine's slots, and its lane of the maintenance ledger
EVERY = 30.0  # seconds between passes
DRAIN = 30.0  # seconds the host's end waits for a cancelled call: its session's bounded teardown, then the result
PRUNE_EVERY = 86_400.0  # seconds between prunings of judged captures
LINGERING = "Retro: a session's runtime may still run (its end was not confirmed); see Maintenance"
SWITCH = {"change": "retro_after_change", "idle": "retro_when_idle"}  # an automatic run's machine setting


@dataclass(frozen=True)
class Seams:
    """What the job reads of the machine: its fence, pause, stop barrier, idle time, loaded projects and blocks."""

    fenced: Callable[[], str] = str
    paused: Callable[[], bool] = bool
    admission: Callable[[], AbstractContextManager[object]] = threading.Lock
    say: Callable[[str], None] = lambda _t: None
    asked: Callable[..., Any] = retro_review.asked
    idle: Callable[[], bool] = bool
    projects: Callable[[], units.Projects] = dict
    blocked: Callable[[str], str] = lambda _uid: ""  # why a unit may not start; ``attach`` reads ``retro_block``


class RetroJob:
    """The machine's Retro: runs from the button, after Changes and over idle chats, each paid call admitted."""

    def __init__(self, slots: Slots, seams: Seams | None = None, owner: maintenance.Maintenance | None = None) -> None:
        self.slots, self.seams = slots, seams or Seams()
        self.maintenance = owner or maintenance.Maintenance(slots)
        self.running, self.halting, self.lock = "", "", threading.Lock()
        self.task: tuple[asyncio.AbstractEventLoop, asyncio.Task[Any] | None] | None = None
        self.unended: list[str] = []  # the running call's sessions whose runtime's end was not confirmed
        self.thread: threading.Thread | None = None
        self.waiting: list[Running] = []
        self.checked, self.pruned_at = False, -PRUNE_EVERY
        self.skips = retro_block.Skips(self.seams.say, self.seams.blocked)

    @classmethod
    def attach(cls, m: Machine, fenced: Callable[[], str]) -> RetroJob:
        """The job of machine *m*: its slots, *fenced*, pause, stop barrier, idle time and loaded projects."""

        def idle() -> bool:
            if m.auto.mono() - m.auto.last_use < IDLE_FOR or m.updating or m.ending:
                return False
            mine = set(job.working())
            return not [w for w in m.busy() if w not in mine]

        def projects() -> units.Projects:
            loaded = [(pid, p) for pid, p in list(m.projects.items()) if p.store and p.state == "loaded"]
            return {pid: (p.store, Path(p.entry.path)) for pid, p in loaded}

        blocked = functools.partial(retro_block.block, projects=m.projects)  # reads them at each call
        seams = Seams(fenced, lambda: m.paused, lambda: m.lock, m.say, retro_review.asked, idle, projects, blocked)
        job = cls(m.slots, seams, m.maintenance)
        return job

    def working(self) -> list[str]:
        """What a stop when idle and an update wait for: the running run, or a runtime that may still run."""
        if self.running:
            return [f"Retro: {self.running}"]
        return [LINGERING] if self.lingering() else []

    def lingering(self) -> bool:
        """Whether a call's lease is held: a runtime of it may still run, so no Retro call starts."""
        return SLOT in self.maintenance.holding(KIND)

    def stop(self) -> None:
        """OwlBear stops: no further call starts; the running run waits, kept."""
        self.halting = "OwlBear is stopping"

    def start(self, stopping: threading.Event, clock: Callable[[], float]) -> None:
        """Run ``loop`` on the job's own thread, which ``drain`` waits for."""
        self.thread = threading.Thread(target=self.loop, args=(stopping, clock), daemon=True, name="retro")
        self.thread.start()

    def drain(self, timeout: float = DRAIN) -> bool:
        """The host ends: stop, cancel the running session and wait up to *timeout* for the job's thread; ended?"""
        self.stop()
        with self.lock:
            running = self.task
        if running is not None and running[1] is not None:
            with contextlib.suppress(RuntimeError):  # its loop closed meanwhile: the call ended
                running[0].call_soon_threadsafe(running[1].cancel)
        thread = self.thread
        if thread is None or thread is threading.current_thread():
            return True
        thread.join(timeout)
        return not thread.is_alive()

    def loop(self, stopping: threading.Event, clock: Callable[[], float]) -> None:
        """Thread: a pass every ``EVERY`` seconds."""
        while not stopping.wait(EVERY):
            try:
                self.tick(clock())
            except Exception as exc:
                LOG.exception("a Retro pass failed")
                self.seams.say(f"Retro failed: {type(exc).__name__}: {exc}")

    def tick(self, now: float) -> None:
        """One pass: restore once, then the button's requests, a waiting run, Changes, chats and the pruning."""
        if not self.checked:
            self._restore()
            self.checked = True
        store.add_grades(units.gap_grades(units.records(), store.known(), store.graded()))  # no call needed
        for request in store.queued():
            if self._closed():
                return
            if store.take(request["id"]):
                self._button(request)
        for ctx in list(self.waiting):
            if self._closed():
                return
            self._go(ctx)
        if self.waiting or self._closed():
            return
        self._changes()
        self._chats()
        if now - self.pruned_at >= PRUNE_EVERY and not self.waiting:
            self.pruned_at = now
            prune(self.seams.say)

    def _closed(self) -> bool:
        return bool(self.seams.fenced() or self.halting or self.lingering())

    # Starting and ending runs

    def _restore(self) -> None:
        """Take up the runs this host's predecessor left open; end those whose spend is not known."""
        live = set()
        for snap in store.run_states().values():
            if snap["state"] == "ended":
                continue
            ctx = Running.of(snap)
            if snap["unsettled"] or not snap["known"]:
                self._ended(ctx, "stopped: unknown spend after an interruption")
            elif ctx.limit - ctx.spent <= 0:
                self._ended(ctx, "stopped: its credit limit is spent")
            else:
                ctx.why = "OwlBear restarted"
                store.run_event(ctx.id, "waiting", why=ctx.why)
                self.waiting.append(ctx)
                live.add((ctx.uid, ctx.rev))
        settle_open(live)

    def _button(self, request: dict[str, Any]) -> None:
        by = request.get("by", "")
        if named := request.get("synthetic"):
            spec = syn.specs(named)[0]
            if not self._took(uid := syn.unit_id(spec), by):
                why = f"refused: {why}" if (why := self.seams.blocked(uid)) else ""
                self._start(Running(uid, "button", by, provenance="synthetic", spec=spec["name"]), why)
            return
        change, chat = request.get("change"), request.get("chat", "")
        uid = units.change_id(*change.split(":", 1)) if change else units.chat_id(chat)
        if self._took(uid, by):
            return
        if why := self.seams.blocked(uid):  # before the grade-only runs, so a refusal is a plain run of its own
            self._start(Running(uid, "button", by), f"refused: {why}")
            return
        late = [i for i in units.late(units.records(), store.known(), store.graded()) if i["unit"] == uid]
        late += unfinished(uid)  # with records written after a judged revision, grade-only runs that stopped
        for i in late:
            self._start(Running(uid, "button", by, rev=i["rev"], mode="grade-only", records=i["records"]))
            if self.waiting:
                return
        try:
            item = self._due(uid, request)
        except (store.RetroError, OSError) as exc:
            self._start(Running(uid, "button", by), f"refused: {exc}")
            return
        if item is None or item["rev"] in {i["rev"] for i in late}:  # that judged revision is graded now
            if not late:
                self._start(Running(uid, "button", by), "refused: it is not due (not finished, quiet or enrolled)")
            return
        self._start(Running(uid, "button", by, rev=item["rev"]))

    def _took(self, uid: str, by: str) -> bool:
        """The button takes over *uid*'s waiting run, its cursor and spend kept; was there one?"""
        if (same := next((c for c in self.waiting if c.uid == uid), None)) is None:
            return False
        same.trigger, same.by, same.why = "button", by, ""
        store.run_event(same.id, "resumed", by=by, trigger="button")
        self._go(same)
        return True

    def _due(self, uid: str, request: dict[str, Any]) -> dict[str, Any] | None:
        if request.get("change"):
            found = units.due_changes(self.seams.projects(), change=request["change"])
        else:
            found = units.due_chats(enrolled(), datetime.now(UTC), chat=request["chat"])
        return next((i for i in found if i["unit"] == uid), None)

    def _start(self, ctx: Running, refused: str = "") -> None:
        """Open *ctx*, recorded, and run it; refused when its limit, a role or an assumption it needs is missing."""
        why, limit = refused, None
        if not why:
            try:
                limit = cases_job.limits()["retro"]
                for agent in ("retro", "retro-review"):
                    session(agent)
            except (SettingsUnset, registry.RegistryError, OSError, ValueError) as exc:
                why = f"refused: {type(exc).__name__}: {exc}"[:300]
        if not why and limit is None:
            why = "refused: the Retro run credit limit is unset"
        why = why or ctx.retired()
        ctx.limit, ctx.new = limit or 0.0, True
        keep = {"trigger": ctx.trigger, "by": ctx.by, "rev": ctx.rev, "mode": ctx.mode, "records": ctx.records}
        store.run_event(ctx.id, "opened", unit=ctx.uid, provenance=ctx.provenance, spec=ctx.spec, limit=ctx.limit,
                        assumptions=list(ctx.needs), **keep)  # fmt: skip
        if why:
            self._ended(ctx, why)
        else:
            self._go(ctx)

    def _go(self, ctx: Running) -> None:
        """Run *ctx* from its cursor: kept answers replayed, the rest asked; it ends, or waits when refused a call."""
        self.running, out = ctx.uid, None
        try:
            if ctx.meter is None:
                ctx.meter = Meter(ctx.limit - ctx.spent, "retro-run")
            work = self._admitted(ctx, "open", lambda _key: self._work(ctx))
            out = retro_judge.run(work)
            result = "stopped: runtime end unconfirmed" if ctx.unended else "judged"  # its last call's end too
        except WaitingError as exc:
            if exc.why != ctx.why:
                store.run_event(ctx.id, "waiting", why=exc.why)
            ctx.why = exc.why
            if ctx not in self.waiting:
                self.waiting.append(ctx)
            return
        except StoppedError as exc:
            result, out = exc.result, {"held": True} if exc.held else None
        except asyncio.CancelledError:
            result = "stopped: OwlBear stopped"
        except Exception as exc:
            LOG.exception("a Retro run failed")
            result = f"failed: {type(exc).__name__}: {exc}"[:300]
        finally:
            self.running = ""
        self._ended(ctx, result, out)

    def _ended(self, ctx: Running, result: str, out: dict[str, Any] | None = None) -> None:
        """Keep how *ctx* ended, with its spend, and settle its revision, unless grade-only or held before any work."""
        report = ctx.meter.report() if ctx.meter else None
        spent = ctx.spent + (report["credits"] if report else 0.0)
        known = ctx.known and (report["credits_known"] if report else True)
        store.run_event(ctx.id, "ended", result=result, credits=report, spent=spent, known=known, **(out or {}))
        if ctx.rev and ctx.mode != "grade-only" and not (out or {}).get("held"):  # a held run never took it
            units.settle(ctx.uid, ctx.rev, result.split(":", 1)[0], run=ctx.id, result=result)
        if ctx in self.waiting:
            self.waiting.remove(ctx)

    def _work(self, ctx: Running) -> Work:
        """*ctx*'s revision, taken now when it is not yet, with its records and evidence; read only once admitted."""

        def ask(batch: str, message: str, agent: str) -> Paid:
            return self._paid(ctx, batch, message, agent)

        projects = self.seams.projects()
        if ctx.rev and ctx.mode != "grade-only" and self._revision(ctx).get("run") != ctx.id:
            units.settle(ctx.uid, ctx.rev, "open", run=ctx.id)  # a retry owns the revision it takes again until it ends
        if ctx.provenance == "synthetic":
            spec = syn.specs(ctx.spec)[0]
            if not ctx.rev:
                self._frozen(ctx, syn.install(spec)["rev"])
            return syn.work(spec, self._revision(ctx), ctx.id, ask)
        if not ctx.rev:
            self._frozen(ctx, units.freeze({"unit": ctx.uid, "rev": ""}, projects, units.records())["rev"])
        unit, rev = store.known()[ctx.uid], self._revision(ctx)
        found = {r["id"]: r for r in units.records()}
        held = [found[i] for i in (ctx.records if ctx.mode == "grade-only" else rev.get("records") or ()) if i in found]
        prepared = evidence(ctx.uid, unit, rev, projects)
        return Work(ctx.id, ctx.uid, rev, unit, held, prepared, ask, grade_only=ctx.mode == "grade-only")

    def _frozen(self, ctx: Running, rev: str) -> None:
        ctx.rev = rev
        store.run_event(ctx.id, "frozen", rev=rev)
        units.settle(ctx.uid, rev, "open", run=ctx.id)

    def _revision(self, ctx: Running) -> dict[str, Any]:
        return next(r for r in store.known()[ctx.uid]["revisions"] if r["rev"] == ctx.rev)

    # Admission and one paid call

    def _allowed(self, switch: str) -> bool:
        """Curation's rule: an automatic run's switch on, and while paused set so."""
        try:
            said = getattr(machine_settings.current(), switch)
        except registry.RegistryError:
            return False
        return said == "paused" or (said == "on" and not self.seams.paused())

    def _refusal(self, ctx: Running) -> str:
        """Why no call of *ctx* may start now (it waits); "" when one may."""
        if why := self.seams.fenced() or self.halting:
            return why
        if ctx.trigger == "button":
            return ""
        if not self._allowed(SWITCH[ctx.trigger]):
            return "OwlBear is paused" if self.seams.paused() else f"{SWITCH[ctx.trigger]} is not on"
        if ctx.trigger == "idle" and not self.seams.idle():
            return "OwlBear is not idle"
        return ""

    def _admitted[T](self, ctx: Running, what: str, work: Callable[[str], T], *, lease: bool = False) -> T:
        """Run *work* on one slot once admitted under the stop barrier, with a lease when it starts a session.

        Raises:
            WaitingError: The fence, a stop, pause, a switch, idle time or a held lease refuses it now.
            StoppedError: The unit may no longer be read, or an assumption the run rests on is retired; it ends refused.
        """
        key, turn = f"retro:{what}:{uuid.uuid4().hex[:8]}", threading.Event()
        while not self.slots.take(SLOT, key, 1, 1, wake=turn.set):
            if why := self._refusal(ctx) or (LINGERING if self.lingering() else ""):
                self.slots.cancel(SLOT, key)
                raise WaitingError(why)
            turn.wait(5)
            turn.clear()
        begun = ""
        try:
            with self.seams.admission():
                if why := self._refusal(ctx):
                    raise WaitingError(why)
                real, fresh = ctx.provenance == "real", not ctx.rev  # a chat's new revision only when it is quiet
                why = real and units.eligible(ctx.uid, enrolled(), self.seams.projects(), fresh=fresh)
                if why := ctx.retired() or (f"refused: {why}" if why else ""):
                    raise StoppedError(why)
                if ctx.new and (why := self.seams.blocked(ctx.uid)):  # set when it opened, unset since? (#808)
                    raise StoppedError.unset(why)
                ctx.new = False  # rechecked once, by the first admission that gets this far
                if lease:
                    begun = self.maintenance.begin(SLOT, key, KIND, "")  # durable before the session starts
            if ctx.why:
                store.run_event(ctx.id, "resumed")
                ctx.why = ""
            self.unended = []
            return work(key)
        finally:
            if begun:
                ctx.unended = self._released(begun) or ctx.unended
            if not begun or not self.maintenance.held(SLOT, key):
                self.slots.give(SLOT, key)

    def _paid(self, ctx: Running, batch: str, message: str, agent: str) -> Paid:
        """One paid call of *ctx*: admitted, leased, ``inflight`` written, asked; its answer and spend.

        Raises:
            StoppedError: An earlier session's end was not confirmed, the run's allowance is spent or a role is unset.
        """
        meter = ctx.meter or Meter(0, "retro-run")
        if ctx.unended:
            msg = "stopped: runtime end unconfirmed"
            raise StoppedError(msg)
        if not meter.admit():
            msg = "stopped: the run's credit limit is reached"
            raise StoppedError(msg)
        try:
            role, seconds = session(agent)
        except SettingsUnset as exc:
            msg = f"refused: {exc}"
            raise StoppedError(msg) from exc

        def call(_key: str) -> Paid:
            store.run_event(ctx.id, "inflight", batch=batch)
            before = meter.report()["credits"]
            try:
                with spend_ledger.at(where(ctx.uid, self.seams.projects())):
                    text = self._run(self.seams.asked(message, meter, role, agent=agent, seconds=seconds))
            except RuntimeError:  # the meter closed before the session started
                text = ""
            report = meter.report()
            known = ctx.known and report["credits_known"]
            spent = report["credits"]
            return Paid(text, spent - before, ctx.spent + spent, known, cut=not meter.admit())

        return self._admitted(ctx, "call", call, lease=True)

    def _released(self, lease: str) -> bool:
        """End a call's lease: released when its runtime's end was confirmed, else held with its slot; held?"""
        left = list(self.unended)
        problems = (f"the end of Retro sessions was not confirmed: {', '.join(left)}"[:300],) if left else ()
        self.maintenance.finished(lease, Run(lease, termination=processes.Termination(not left, problems=problems)))
        if left:
            self.seams.say(f"Retro: {problems[0]}; no Retro call starts until Maintenance recovers it")
        return bool(left)

    def _run[T](self, work: Coroutine[Any, Any, T]) -> T:
        """Run *work*'s session on a loop of its own, cancellable by ``drain``; its unconfirmed end noted."""

        async def main() -> T:
            with self.lock:
                self.task = (asyncio.get_running_loop(), asyncio.current_task())
            try:
                return await work
            finally:
                with self.lock:
                    self.task = None

        token = spotter_look.UNENDED.set(self.unended)
        try:
            return asyncio.run(main())
        finally:
            spotter_look.UNENDED.reset(token)

    # Automatic runs and pruning

    def _changes(self) -> None:
        if not self._allowed(SWITCH["change"]):
            return
        for item in units.due_changes(self.seams.projects()):
            if self.skips.blocked(item["unit"]):
                continue
            self._start(Running(item["unit"], "change", rev=item["rev"]))
            if self.waiting:
                return
        self._late("chg:", "change")

    def _chats(self) -> None:
        if not self._allowed(SWITCH["idle"]) or not self.seams.idle():
            return
        for item in units.due_chats(enrolled(), datetime.now(UTC)):
            if self.skips.blocked(item["unit"]):
                continue
            self._start(Running(item["unit"], "idle", rev=item["rev"]))
            if self.waiting:
                return
        self._late("chat:", "idle")

    def _late(self, prefix: str, trigger: str) -> None:
        """Grade-only runs of judged revisions with records written after them; one that did not end judged waits."""
        failed = failed_grading()
        for item in units.late(units.records(), store.known(), store.graded()):
            unit = item["unit"]
            if unit.startswith(prefix) and (unit, item["rev"]) not in failed and not self.skips.blocked(unit):
                self._start(Running(item["unit"], trigger, rev=item["rev"], mode="grade-only", records=item["records"]))
                if self.waiting:
                    return
