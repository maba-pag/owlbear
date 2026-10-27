"""The Spotter cases' job in the machine host (Improvement design §4, §6): paid replays, checks and publication.

One request at a time, each on a session slot of its own (``SLOT``), like memory curation: it waits while the machine
is paused or fenced, is admitted under the machine's stop barrier, and counts in what a stop when idle waits for. A
stop closes the running run's meter, so no further look starts and the run is kept as stopped; it is never resumed.

Requests come only from the owner's command (``owlbear cases``): a regression, a reserve comparison or a check of
candidates. Publication needs no request: once nothing is queued, the cases ``retro-review`` has not seen yet are
reviewed and published on their own (D-01M5XCE8ZFZE8Q1XCN1EE4B29S). Every run stops at its own credit limit: the
replay run limit for replays, the Retro run limit for checks and publication (D-01M5XCD49YHHR1NQKKY8TQD0C3); an unset
limit or role refuses the run, never a built-in value.
"""

from __future__ import annotations

import asyncio
import threading
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.change_contracts.profile_record import RoleModel
from owlbear_delivery_next.improvement import case_replay, case_review, cases, spotter
from owlbear_delivery_next.improvement.credit_meter import Meter
from owlbear_delivery_next.local_system import data_repo, local_home
from owlbear_delivery_next.runtimes import retro_review, spotter_look
from owlbear_delivery_next.settings.config import Layer, MachineLayer, SettingsUnset, resolve
from owlbear_delivery_next.state_store import machine_settings
from owlbear_delivery_next.state_store.store import MACHINE_SETTINGS, read_layer
from owlbear_delivery_next.workflow_steps import lookup

if TYPE_CHECKING:
    from collections.abc import Callable
    from contextlib import AbstractContextManager

    from owlbear_delivery_next.local_system.slots import Slots
    from owlbear_delivery_next.settings.config import Settings

SLOT = "improvement"  # the cases job's own share of the machine's slots
EVERY = 10.0  # seconds between looks at the queue
PUBLISH_EVERY = 300.0  # seconds between publication syncs that found work


def _settings() -> Settings:
    """This machine's settings outside any project."""
    shared = data_repo.locate()
    if shared is not None:
        return lookup.machine(shared)
    return resolve(None, Layer(), read_layer(local_home.root() / MACHINE_SETTINGS, MachineLayer))


def limits() -> dict[str, float | None]:
    """The run and look credit limits in force; None where unset.

    STAND-IN until feat/run-credit-limits merges: it adds ``replay_run_credit_limit`` and ``retro_run_credit_limit``
    to the machine values and ``look_credit_limit`` to the Spotter's settings; read here by name until then.
    """
    values = machine_settings.current()
    try:
        look = getattr(_settings().spotter, "look_credit_limit", None)
    except OSError, ValueError, SettingsUnset:
        look = None
    return {
        "replay": getattr(values, "replay_run_credit_limit", None),
        "retro": getattr(values, "retro_run_credit_limit", None),
        "look": look,
    }


def role(name: str) -> RoleModel:
    """The model a session of role *name* runs with.

    Raises:
        SettingsUnset: The role is unset.
    """
    agent = _settings().agent(name)
    return RoleModel(model=agent.model, effort=agent.effort, context=agent.context)


async def look(the_card: dict[str, Any], prompt: cases.Prompt, meter: Meter, spot: RoleModel) -> dict[str, Any]:
    """One replayed look: the frozen card under the frozen prompt, its answer parsed.

    STAND-IN until feat/run-credit-limits merges: there ``spotter_look.judged(card, ctx, meter) -> str`` meters the
    look itself through ``runtimes.credit_limit.Limit`` and ``Context.limit`` replaces ``budget``; here the look's
    reported spend is charged to its meter once it ends.
    """
    if not meter.admit():
        return {
            "category": "failed",
            "note": f"the {meter.report()['stopped_by']} spend is {meter.report()['stopped']}",
        }
    ctx = spotter.Context(
        project="",
        change="",
        step="replay",
        looks=(),
        sample_rate=0,
        verbose=False,
        model=spot.model or "",
        effort=spot.effort or "",
        budget=0,
        context=spot.context or "",
        prompt=prompt,
    )
    text, spent = await spotter_look.judged(the_card, ctx)
    share = meter.part()
    share.call(spent)
    share.ended(spent, confirmed=True)
    return spotter.parse(text)


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
    ) -> None:
        self.slots, self.fenced, self.paused, self.say = slots, fenced, paused, say
        self.admission = admission or threading.Lock
        self.looked, self.asked, self.shared = looked, asked, shared
        self.running, self.halting, self.meter, self.lock = "", "", None, threading.Lock()
        self.published_at, self.checked = -PUBLISH_EVERY, False

    def working(self) -> list[str]:
        """What a stop when idle and an update wait for: the running replay, check or publication."""
        return [f"Spotter cases: {self.running}"] if self.running else []

    def stop(self) -> None:
        """OwlBear stops: no further look or review of the running run starts; it is kept as stopped."""
        self.halting = "OwlBear is stopping"

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
        """One pass: each queued request in turn, then a publication sync when due; nothing while paused or fenced."""
        if self.paused() or self.fenced():
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
        key = f"cases:{what}"
        turn = threading.Event()
        while not self.slots.take(SLOT, key, 1, 1, wake=turn.set):
            if self._held():
                self.slots.cancel(SLOT, key)
                return False
            turn.wait(5)
            turn.clear()
        try:
            with self.admission():
                if self._held():
                    return False
                self.running = what
            work()
            return True
        finally:
            self.running = ""
            self.slots.give(SLOT, key)

    def _metered(self, limit: float, scope: str) -> Meter:
        with self.lock:
            self.meter = Meter(limit, scope)
            return self.meter

    def _ended(self, request: dict[str, Any], why: str, meter: Meter | None = None) -> None:
        """Keep *request*'s result as *why*, with what it spent, unless a result of it is kept already."""
        with cases.locked():
            if any(r.get("id") == request["id"] and "result" in r for r in case_replay.results()):
                return
            line = {"id": request["id"], "kind": request.get("kind"), "by": request.get("by", ""),
                    "asked": request.get("at"), "result": why, "ended": cases.now()}  # fmt: skip
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
        lim, kind, meter = limits(), request.get("kind"), None
        try:
            if kind in {"regression", "compare"}:
                if lim["replay"] is None or lim["look"] is None:
                    self._ended(request, "refused: the replay run's or a look's credit limit is unset")
                    return
                spot = role("spotter")
                meter = self._metered(lim["replay"], "replay-run")
                looked = lambda c, p, m: self.looked(c, p, m, spot)  # noqa: E731 - the role bound once
                asyncio.run(case_replay.run(request, looked, meter, lim["look"], self.halt))
            elif kind == "check":
                if lim["retro"] is None:
                    self._ended(request, "refused: the Retro run credit limit is unset")
                    return
                reviewer = role("retro-review")
                meter = self._metered(lim["retro"], "retro-run")
                asked = lambda text, m: self.asked(text, m, reviewer)  # noqa: E731 - the role bound once
                asyncio.run(case_review.check(request, asked, meter, self.halt))
            else:
                self._ended(request, f"refused: unknown request {kind!r}")
        except (SettingsUnset, cases.CaseError) as exc:
            self._ended(request, f"refused: {exc}", meter)
        except Exception as exc:  # noqa: BLE001 - a failed run is kept as failed with its spend, never rerun
            self._ended(request, f"failed: {type(exc).__name__}: {exc}"[:300], meter)
        finally:
            with self.lock:
                self.meter = None

    def _publish(self) -> None:
        lim = limits()
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
            done = asyncio.run(case_review.sync(self.shared(), asked, meter, self.halt))
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
