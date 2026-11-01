"""The Spotter cases' job in the machine host (Improvement design §4, §6): paid replays, checks and publication.

One request at a time, each on a session slot of its own (``SLOT``), like memory curation: it waits while the machine
is paused or fenced, is admitted under the machine's stop barrier, and counts in what a stop when idle waits for. A
stop closes the running run's meter, so no further look starts and the run is kept as stopped; it is never resumed.

Requests come only from the owner's command (``owlbear cases``): a regression, a reserve comparison or a check of
candidates. Publication needs no request: once nothing is queued, the cases ``retro-review`` has not seen yet are
reviewed and published on their own (D-01M5XCE8ZFZE8Q1XCN1EE4B29S). Every run stops at its own credit limit: the
replay run limit for replays, the Retro run limit for checks and publication (D-01M5XCD49YHHR1NQKKY8TQD0C3); an unset
limit or role refuses the run, never a built-in value.

Each admitted run holds a maintenance lease (``local_system.maintenance``) from before its first session to the
confirmed end of its last runtime: a runtime whose end teardown could not confirm keeps the lease, and with it the
slot, held until the owner recovers it after a reboot, so nothing else of the job starts meanwhile and a stop when idle
or an update waits for it. When the host ends, ``drain`` cancels the running session, whose teardown and spend are
bounded, and waits for the run's result to be kept.
"""

from __future__ import annotations

import asyncio
import contextlib
import threading
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.change_contracts.profile_record import RoleModel
from owlbear_delivery_next.improvement import case_replay, case_review, cases, spotter
from owlbear_delivery_next.improvement.credit_meter import Meter
from owlbear_delivery_next.local_system import data_repo, local_home, maintenance, processes
from owlbear_delivery_next.runtimes import retro_review, spotter_look
from owlbear_delivery_next.settings.config import Layer, MachineLayer, SettingsUnset, resolve
from owlbear_delivery_next.state_store import machine_settings
from owlbear_delivery_next.state_store.store import MACHINE_SETTINGS, read_layer
from owlbear_delivery_next.workflow_steps import lookup

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from contextlib import AbstractContextManager

    from owlbear_delivery_next.local_system.slots import Slots
    from owlbear_delivery_next.settings.config import Settings

SLOT = "improvement"  # the cases job's own share of the machine's slots
EVERY = 10.0  # seconds between looks at the queue
PUBLISH_EVERY = 300.0  # seconds between publication syncs that found work
DRAIN = 30.0  # seconds the host's end waits for a cancelled run: its sessions' bounded teardown, then its result
KIND = "replay"  # the Spotter's lane of the maintenance ledger; chat looks hold theirs under their own project
LINGERING = "Spotter cases: a session's runtime may still run (its end was not confirmed); see Maintenance"


@dataclass(frozen=True)
class _Ended:
    """What a run's sessions left, as the maintenance ledger reads it; their runtimes record no PIDs."""

    termination: processes.Termination
    pids: processes.Pids = field(default_factory=dict)
    runtime_pid: int | None = None


def settings() -> Settings:
    """This machine's settings outside any project."""
    shared = data_repo.locate()
    if shared is not None:
        return lookup.machine(shared)
    return resolve(None, Layer(), read_layer(local_home.root() / MACHINE_SETTINGS, MachineLayer))


def limits() -> dict[str, float | None]:
    """The run and look credit limits in force (D-01M5XCD49YHHR1NQKKY8TQD0C3); None where unset.

    The replay and Retro run limits are this machine's values; a replayed look's is the Spotter's ``look_credit_limit``.
    """
    values = machine_settings.current()
    try:
        look = settings().spotter.look_credit_limit
    except OSError, ValueError, SettingsUnset:
        look = None
    return {"replay": values.replay_run_credit_limit, "retro": values.retro_run_credit_limit, "look": look}


def role(name: str) -> RoleModel:
    """The model a session of role *name* runs with.

    Raises:
        SettingsUnset: The role is unset.
    """
    agent = settings().agent(name)
    return RoleModel(model=agent.model, effort=agent.effort, context=agent.context)


async def look(the_card: dict[str, Any], prompt: cases.Prompt, meter: Meter, spot: RoleModel) -> dict[str, Any]:
    """One replayed look: the frozen card under the frozen prompt, on its own look *meter* inside the run's.

    ``spotter_look.judged`` charges the look's billed calls to *meter* as they are reported and stops the turn once
    it closes; an empty answer (the meter closed before one) parses as failed, never as silence.
    """
    ctx = spotter.Context(project="", change="", step="replay", looks=(), sample_rate=0, verbose=False,
                          model=spot.model or "", effort=spot.effort or "", limit=meter.limit,
                          context=spot.context or "", prompt=prompt)  # fmt: skip
    return spotter.parse(await spotter_look.judged(the_card, ctx, meter))


class CasesJob:
    """The machine's Spotter cases job: one request at a time, then publication."""

    def __init__(  # noqa: PLR0913 - the machine's seams: the slots, its fence, pause, stop barrier and the sessions
        self,
        slots: Slots,
        *,
        fenced: Callable[[], str] = str,
        paused: Callable[[], bool] = lambda: False,
        admission: Callable[[], AbstractContextManager[object]] | None = None,
        say: Callable[[str], None] = lambda _t: None,
        looked: Callable[..., Any] = look,
        asked: Callable[..., Any] = retro_review.asked,
        shared: Callable[[], data_repo.DataRepo | None] = data_repo.locate,
        ownership: maintenance.Maintenance | None = None,
    ) -> None:
        self.slots, self.fenced, self.paused, self.say = slots, fenced, paused, say
        self.admission = admission or threading.Lock
        self.looked, self.asked, self.shared = looked, asked, shared
        self.maintenance = ownership or maintenance.Maintenance(slots)
        self.running, self.halting, self.meter, self.lock = "", "", None, threading.Lock()
        self.published_at, self.checked = -PUBLISH_EVERY, False
        self.task: tuple[asyncio.AbstractEventLoop, asyncio.Task[Any] | None] | None = None  # the running sessions
        self.unended: list[str] = []  # the running run's sessions whose runtime's end was not confirmed
        self.thread: threading.Thread | None = None

    def working(self) -> list[str]:
        """What a stop when idle and an update wait for: the running run, or a runtime that may still run."""
        if self.running:
            return [f"Spotter cases: {self.running}"]
        return [LINGERING] if self.lingering() else []

    def lingering(self) -> bool:
        """Whether a run's lease is held: a runtime of it may still run, so nothing else of the job starts."""
        return SLOT in self.maintenance.holding(KIND)

    def stop(self) -> None:
        """OwlBear stops: no further look or review of the running run starts; it is kept as stopped."""
        self.halting = "OwlBear is stopping"

    def start(self, stopping: threading.Event, clock: Callable[[], float]) -> None:
        """Run ``loop`` on the job's own thread, which ``drain`` waits for."""
        self.thread = threading.Thread(target=self.loop, args=(stopping, clock), daemon=True, name="spotter-cases")
        self.thread.start()

    def drain(self, timeout: float = DRAIN) -> bool:
        """The host ends: stop, cancel the running session and wait up to *timeout* for the job's thread; ended?

        A cancelled session still reads its spend and tears its runtime down, each bounded, and the run keeps its
        result as stopped; a runtime whose end is not confirmed keeps the run's lease held. The caller has set the
        loop's *stopping*.
        """
        self.stop()
        with self.lock:
            running = self.task
        if running is not None and running[1] is not None:
            with contextlib.suppress(RuntimeError):  # its loop closed meanwhile: the run ended
                running[0].call_soon_threadsafe(running[1].cancel)
        thread = self.thread
        if thread is None or thread is threading.current_thread():
            return True
        thread.join(timeout)
        return not thread.is_alive()

    def halt(self) -> str:
        """Why no further look or review may start now, else nothing."""
        return self.halting

    def loop(self, stopping: threading.Event, clock: Callable[[], float]) -> None:
        """Thread: every ``EVERY`` seconds, run what is queued, then publish what is due."""
        while not stopping.wait(EVERY):
            try:
                self.tick(clock())
            except Exception as exc:  # noqa: BLE001 - the loop outlives one failed pass
                self.say(f"the Spotter cases job failed: {type(exc).__name__}: {exc}")

    def tick(self, now: float) -> None:
        """One pass: each queued request in turn, then a publication sync when due; none if paused, fenced or held."""
        if self.paused() or self.fenced() or self.lingering():
            return
        if not self.checked:
            case_replay.interrupted()
            self.checked = True
        for request in case_replay.queued():
            if not self._admitted(request["id"], lambda r=request: self._taken(r)):
                return  # paused, fenced or stopping: it stays queued
        if now - self.published_at >= PUBLISH_EVERY and any(case_review.due()):
            self.published_at = now
            self._admitted("publication", self._publish)

    def _held(self) -> str:
        return self.fenced() or self.halting or ("paused" if self.paused() else "")

    def _admitted(self, what: str, work: Callable[[], None]) -> bool:
        """Run *work* on one slot, admitted under the stop barrier; whether it ran.

        Pause, the fence and a stop are read again once the slot is granted, under the barrier: then the slot is
        given back and nothing starts, so a queued request stays queued.
        """
        key = f"cases:{what}:{uuid.uuid4().hex[:8]}"  # one admission: its lease's slot
        turn = threading.Event()
        while not self.slots.take(SLOT, key, 1, 1, wake=turn.set):
            if self._held() or self.lingering():  # a held lease keeps the job's one slot
                self.slots.cancel(SLOT, key)
                return False
            turn.wait(5)
            turn.clear()
        lease = ""
        try:
            with self.admission():
                if self._held():
                    return False
                self.running = what
            lease = self.maintenance.begin(SLOT, key, KIND, "")  # durable before any session starts
            self.unended = []
            work()
            return True
        finally:
            self.running = ""
            if lease:
                self._released(lease)
            if not lease or not self.maintenance.held(SLOT, key):
                self.slots.give(SLOT, key)

    def _released(self, lease: str) -> None:
        """End the run's lease: released when every runtime's end was confirmed, else held with its slot."""
        left = list(self.unended)
        problems = (f"the end of Spotter cases sessions was not confirmed: {', '.join(left)}"[:300],) if left else ()
        self.maintenance.finished(lease, _Ended(processes.Termination(not left, problems=problems)))
        if left:
            self.say(f"Spotter cases: {problems[0]}; the job waits until Maintenance recovers it")

    def _run[T](self, work: Coroutine[Any, Any, T]) -> T:
        """Run *work*'s sessions on a loop of their own, cancellable by ``drain``; their unconfirmed ends noted."""

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

    def _metered(self, limit: float, scope: str) -> Meter:
        with self.lock:
            self.meter = Meter(limit, scope)
            return self.meter

    def _ended(self, request: dict[str, Any], why: str, meter: Meter | None = None) -> None:
        """Keep *request*'s result as *why*, with what it spent and the cases it named, unless a result is kept."""
        with cases.locked():
            if any(r.get("id") == request["id"] and "result" in r for r in case_replay.results()):
                return
            line = {"id": request["id"], "kind": request.get("kind"), "by": request.get("by", ""),
                    "asked": request.get("at"), **({"ids": request["ids"]} if "ids" in request else {}),
                    "result": why, "ended": cases.now()}  # fmt: skip
            if meter is not None:
                line["credits"] = meter.report()
            cases.append("runs.jsonl", line)

    def _taken(self, request: dict[str, Any]) -> None:
        """Run *request* once: off the queue before it starts, so a crash never runs it again."""
        if case_replay.take(request["id"]):
            try:
                self._request(request)
            finally:
                case_replay.done(request["id"])

    def _request(self, request: dict[str, Any]) -> None:
        """Run one taken request; whatever happens, its result and spend are kept, and nothing reruns it."""
        kind, meter = request.get("kind"), None
        try:
            lim = limits()
            if kind in {"regression", "compare"}:
                if lim["replay"] is None or lim["look"] is None:
                    self._ended(request, "refused: the replay run's or a look's credit limit is unset")
                    return
                spot = role("spotter")
                meter = self._metered(lim["replay"], "replay-run")
                looked = lambda c, p, m: self.looked(c, p, m, spot)  # noqa: E731 - the role bound once
                self._run(case_replay.run(request, looked, meter, lim["look"], self.halt))
            elif kind == "check":
                if lim["retro"] is None:
                    self._ended(request, "refused: the Retro run credit limit is unset")
                    return
                reviewer = role("retro-review")
                meter = self._metered(lim["retro"], "retro-run")
                asked = lambda text, m: self.asked(text, m, reviewer)  # noqa: E731 - the role bound once
                self._run(case_review.check(request, asked, meter, self.halt))
            else:
                self._ended(request, f"refused: unknown request {kind!r}")
        except (SettingsUnset, cases.CaseError) as exc:
            self._ended(request, f"refused: {exc}", meter)
        except asyncio.CancelledError:  # the host ended before the run kept its own result
            self._ended(request, "stopped: OwlBear stopped", meter)
        except Exception as exc:  # noqa: BLE001 - a failed run is kept as failed with its spend, never rerun
            self._ended(request, f"failed: {type(exc).__name__}: {exc}"[:300], meter)
        finally:
            with self.lock:
                self.meter = None

    def _publish(self) -> None:
        try:
            lim = limits()
        except Exception as exc:  # noqa: BLE001 - said; the next sync tries again
            self.say(f"the Spotter cases are not published: the credit limits cannot be read: {exc}")
            return
        if lim["retro"] is None:
            self.say("the Spotter cases are not published: the Retro run credit limit is unset")
            return
        try:
            reviewer = role("retro-review")
        except SettingsUnset:
            self.say("the Spotter cases are not published: the retro-review role is unset")
            return
        meter = self._metered(lim["retro"], "retro-run")
        asked = lambda text, m: self.asked(text, m, reviewer)  # noqa: E731 - the role bound once
        try:
            done = self._run(case_review.sync(self.shared(), asked, meter, self.halt))
        except asyncio.CancelledError:  # the host ended before the sync said what it did
            done = {"result": "stopped: OwlBear stopped"}
        except Exception as exc:  # noqa: BLE001 - kept as failed with its spend; the next sync takes what is due
            done = {"result": f"failed: {type(exc).__name__}: {exc}"[:300]}
        finally:
            with self.lock:
                self.meter = None
        with cases.locked():
            cases.append(
                "runs.jsonl",
                {
                    "id": f"p-{cases.now()}",
                    "kind": "publication",
                    **done,
                    "credits": meter.report(),
                    "ended": cases.now(),
                },
            )
