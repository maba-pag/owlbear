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
from owlbear_delivery_next.improvement.credits import Meter
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

    STAND-IN until feat/run-credit-limits: there ``spotter_look.judged(card, ctx, meter)`` meters the look itself and
    ``Context.limit`` replaces ``budget``; here its spend is charged after it ends.
    """
    if not meter.open():
        raise RuntimeError(meter.report()["stopped"] or "no credits left for this look")
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
    meter.charge(spent)
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
        self.running, self.meter, self.lock = "", None, threading.Lock()
        self.published_at, self.checked = -PUBLISH_EVERY, False

    def working(self) -> list[str]:
        """What a stop when idle and an update wait for: the running replay, check or publication."""
        return [f"Spotter cases: {self.running}"] if self.running else []

    def stop(self) -> None:
        """Close the running run's meter: no further look or review starts; it is kept as stopped."""
        with self.lock:
            if self.meter is not None:
                self.meter.refuse("OwlBear is stopping")

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
            if self.paused() or self.fenced():
                return
            self._admitted(request["id"], lambda r=request: self._taken(r))
        if now - self.published_at >= PUBLISH_EVERY and any(case_review.due()):
            self.published_at = now
            self._admitted("publication", self._publish)

    def _admitted(self, what: str, work: Callable[[], None]) -> None:
        """Run *work* on one slot, admitted under the stop barrier."""
        key = f"cases:{what}"
        turn = threading.Event()
        while not self.slots.take(SLOT, key, 1, 1, wake=turn.set):
            if self.fenced():
                self.slots.cancel(SLOT, key)
                return
            turn.wait(5)
            turn.clear()
        try:
            with self.admission():
                if self.fenced():
                    return
                self.running = what
            work()
        finally:
            self.running = ""
            self.slots.give(SLOT, key)

    def _metered(self, limit: float) -> Meter:
        with self.lock:
            self.meter = Meter(limit)
            return self.meter

    def _refused(self, request: dict[str, Any], why: str) -> None:
        with cases.locked():
            cases.append(
                "runs.jsonl",
                {
                    "id": request["id"],
                    "kind": request["kind"],
                    "by": request.get("by", ""),
                    "asked": request.get("at"),
                    "result": f"refused: {why}",
                    "ended": cases.now(),
                },
            )

    def _taken(self, request: dict[str, Any]) -> None:
        """Run *request* once: off the queue before it starts, so a crash never runs it again."""
        if case_replay.take(request["id"]):
            try:
                self._request(request)
            finally:
                case_replay.done(request["id"])

    def _request(self, request: dict[str, Any]) -> None:
        lim = limits()
        kind = request.get("kind")
        try:
            if kind in {"regression", "compare"}:
                if lim["replay"] is None or lim["look"] is None:
                    self._refused(request, "the replay run's or a look's credit limit is unset")
                    return
                spot = role("spotter")
                meter = self._metered(lim["replay"])
                asyncio.run(case_replay.run(request, lambda c, p, m: self.looked(c, p, m, spot), meter, lim["look"]))
            elif kind == "check":
                if lim["retro"] is None:
                    self._refused(request, "the Retro run credit limit is unset")
                    return
                reviewer = role("retro-review")
                meter = self._metered(lim["retro"])
                asyncio.run(case_review.check(request, lambda text, m: self.asked(text, m, reviewer), meter))
            else:
                self._refused(request, f"unknown request {kind!r}")
        except (SettingsUnset, cases.CaseError) as exc:
            self._refused(request, str(exc))
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
        meter = self._metered(lim["retro"])
        try:
            done = asyncio.run(case_review.sync(self.shared(), lambda text, m: self.asked(text, m, reviewer), meter))
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
