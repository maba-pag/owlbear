"""Credit limits per look and run (D-01M5XCD49YHHR1NQKKY8TQD0C3): cooperative stopping on reported spend, no SDK cap.

A meter adds what the runtime reports; it closes at its limit or once a spend is unknown, and stays closed. Each session
reconciles only its own share, so retries add up; a look inside a run charges both at once. The runtime side stops a
turn once its meter closes, every wait bounded, and keeps an answer that completed first.
"""

from __future__ import annotations

import asyncio
import math
import threading
import uuid
from types import SimpleNamespace
from typing import Any

import pytest
from copilot.generated.session_events import SessionEvent

from owlbear_delivery_next.improvement import credit_meter, spotter
from owlbear_delivery_next.improvement.credit_meter import Meter
from owlbear_delivery_next.runtimes import credit_limit, spotter_look

REAL_LOOK = spotter_look.judged  # taken before the suite's fixture replaces it
REPORT = ("credits", "credits_known", "limit", "stopped", "stopped_by")


def ctx() -> spotter.Context:
    return spotter.Context(project="p", change="c1", step="build", looks=("hand-off",), sample_rate=0, verbose=False,
                           model="gpt-6-luna", effort="medium", limit=0.75)  # fmt: skip


def event(kind: str, data: dict[str, Any]) -> SessionEvent:
    raw = {"id": str(uuid.uuid4()), "timestamp": "2026-10-27T10:00:00.000Z", "type": kind, "data": data}
    return SessionEvent.from_dict(raw)


def usage(credits_: float | None) -> SessionEvent:
    data: dict[str, Any] = {"model": "gpt-6-luna"}
    if credits_ is not None:
        data["copilotUsage"] = {"totalNanoAiu": credits_ * 1e9, "tokenDetails": []}
    return event("assistant.usage", data)


def said(text: str) -> SessionEvent:
    return event("assistant.message", {"messageId": str(uuid.uuid4()), "content": text})


def test_the_schema_the_other_slices_read_is_frozen() -> None:
    assert tuple(Meter(0.75).report()) == REPORT
    assert Meter(0.75).report() == {"credits": 0.0, "credits_known": True, "limit": 0.75, "stopped": "",
                                    "stopped_by": ""}  # fmt: skip
    fields = {f.name: f.default for f in spotter.Record.__dataclass_fields__.values()}
    assert {k: fields[k] for k in REPORT} == {"credits": 0.0, "credits_known": False, "limit": 0.0, "stopped": "",
                                              "stopped_by": ""}  # fmt: skip  # unmeasured unless measured


@pytest.mark.parametrize("bad", [0, -1, math.inf, math.nan, True, "0.5", None])
def test_a_limit_is_a_finite_amount_above_zero(bad: object) -> None:
    with pytest.raises(ValueError, match="finite number above zero"):
        Meter(bad)  # type: ignore[arg-type]


@pytest.mark.parametrize(("value", "got"), [(0.2, 0.2), (0, 0.0), (3, 3.0), (math.nan, None), (math.inf, None),
                                            (-0.1, None), (True, None), ("0.2", None), (None, None)])  # fmt: skip
def test_a_billed_amount_that_is_not_finite_or_is_negative_is_unknown(value: object, got: float | None) -> None:
    assert credit_meter.amount(value) == got


def test_sessions_of_a_look_add_up_and_each_reconciles_only_its_own_share_idempotently() -> None:
    look = Meter(1.0)
    first = look.part()
    first.call(0.15)
    first.ended(0.2, confirmed=True)  # the session's total corrects its calls' sum
    first.ended(0.2, confirmed=True)  # twice: no change
    second = look.part()  # a retry, in a session of its own
    second.call(0.1)
    second.ended(0.1, confirmed=True)
    assert look.report()["credits"] == pytest.approx(0.3)
    assert (look.report()["credits_known"], look.admit()) == (True, True)


def test_a_look_in_a_run_charges_both_and_a_closed_run_stops_its_looks() -> None:
    run = Meter(1.0, "replay-run")
    one = Meter(0.75, "look", parent=run)
    part = one.part()
    assert part.call(0.5)
    part.ended(0.5, confirmed=True)
    two = Meter(0.75, "look", parent=run)
    assert not two.part().call(0.6)  # within its own 0.75, but the run's 1.0 is reached
    assert (run.report()["credits"], run.report()["stopped"], run.report()["stopped_by"]) == (1.1, "reached",
                                                                                              "replay-run")  # fmt: skip
    assert (two.report()["stopped"], two.report()["stopped_by"]) == ("reached", "replay-run")
    three = Meter(0.75, "look", parent=run)
    assert not three.admit()  # the run closed: no next look starts
    assert (three.report()["stopped_by"], three.report()["credits"]) == ("replay-run", 0.0)
    assert (one.report()["stopped"], one.left()) == ("", 0.0)  # the first look ended within its limit


def test_an_unknown_spend_closes_its_meter_and_its_run_and_stays_latched_once_known() -> None:
    run = Meter(10.0, "retro-run")
    look = Meter(0.75, "look", parent=run)
    part = look.part()
    assert not part.call(math.nan)  # no usable cost: stop
    assert (look.report()["credits_known"], run.report()["credits_known"]) == (False, False)
    assert (look.report()["stopped"], look.report()["stopped_by"]) == ("unknown", "look")
    assert (run.report()["stopped"], run.report()["stopped_by"]) == ("unknown", "retro-run")  # its own spend, too
    part.ended(0.1, confirmed=True)  # its total, read once the turn's end was confirmed
    known = (look.report()["credits_known"], run.report()["credits_known"], run.report()["credits"])
    assert known == (True, True, 0.1)
    assert (look.admit(), run.admit(), look.report()["stopped"]) == (False, False, "unknown")  # still stopped


def test_an_unknown_share_counts_only_until_its_own_session_resolves() -> None:
    run = Meter(10.0, "replay-run")
    known, unsure = run.part(), run.part()
    known.call(0.1)
    unsure.call(None)
    known.ended(0.1, confirmed=True)  # one known child never erases another's unknown
    assert run.report()["credits_known"] is False
    unsure.ended(0.2, confirmed=True)
    assert run.report()["credits_known"] is True


def test_a_downward_correction_never_reopens_a_reached_meter() -> None:
    look = Meter(0.75)
    part = look.part()
    assert not part.call(0.8)
    part.ended(0.5, confirmed=True)  # the session's total says less
    assert (look.report()["credits"], look.report()["stopped"], look.admit()) == (0.5, "reached", False)


def test_an_unconfirmed_end_is_provisional_and_unknown() -> None:
    look = Meter(0.75)
    part = look.part()
    part.call(0.1)
    part.ended(0.3, confirmed=False)  # read before the turn's end was seen: a call may still be billed
    assert (look.report()["credits"], look.report()["credits_known"]) == (0.3, False)
    part.ended(0.2, confirmed=False)  # never below what was already seen
    assert look.report()["credits"] == 0.3


def test_charges_from_many_threads_add_up_exactly_once() -> None:
    run = Meter(1e6, "replay-run")
    looks = [Meter(1e6, "look", parent=run) for _ in range(8)]

    def charge(meter: Meter) -> None:
        part = meter.part()
        for _ in range(1000):
            part.call(0.001)

    threads = [threading.Thread(target=charge, args=(m,)) for m in looks]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert run.report()["credits"] == pytest.approx(8.0)
    assert run.calls == 8000


class Session:
    """A fake SDK session: its turn plays *script* (events to emit, then how it ends), its RPCs as configured."""

    def __init__(self, made: dict[str, Any], script: list[Any], *, abort: str = "ends", metrics: Any = 0.0) -> None:
        self.made, self.script, self.abort_mode, self.metrics = made, script, abort, metrics
        self.session_id, self.aborted = "look-x", asyncio.Event()
        self.rpc = SimpleNamespace(usage=SimpleNamespace(get_metrics=self._metrics))

    async def send_and_wait(self, *_a: Any, **_kw: Any) -> None:
        for step in self.script:
            if step == "wait-abort":
                await self.aborted.wait()
                return
            if step == "hang":
                await asyncio.sleep(30)
            self.made["on_event"](step)

    async def abort(self) -> None:
        self.made["aborted"] = self.made.get("aborted", 0) + 1
        if self.abort_mode == "stalls":
            await asyncio.sleep(30)
        self.aborted.set()

    async def _metrics(self) -> Any:
        if self.metrics == "stalls":
            await asyncio.sleep(30)
        return SimpleNamespace(total_nano_aiu=None if self.metrics is None else self.metrics * 1e9)

    async def disconnect(self) -> None:
        self.made["disconnected"] = True


def run_look(monkeypatch, session: Session, meter: Meter, made: dict[str, Any]) -> tuple[str, float]:
    class Client:
        def __init__(self, **_kw: Any) -> None:
            made["clients"] = made.get("clients", 0) + 1

        async def start(self) -> None:
            pass

        async def create_session(self, **kw: Any) -> Session:
            made.update(kw)
            return session

        async def stop(self) -> None:
            pass

    monkeypatch.setattr(spotter_look, "CopilotClient", Client)
    monkeypatch.setattr(spotter_look, "cli_path", lambda: "/bin/false")
    monkeypatch.setattr(spotter, "TEARDOWN", 0.1)

    async def main() -> tuple[str, float]:
        loop = asyncio.get_running_loop()
        began = loop.time()
        text = await REAL_LOOK({}, ctx(), meter)
        return text, loop.time() - began

    return asyncio.run(main())


def test_a_turn_that_reaches_its_limit_is_aborted_and_its_total_settles_it(monkeypatch) -> None:
    made: dict[str, Any] = {}
    look = Meter(0.75)
    session = Session(made, [usage(0.5), usage(0.4), "wait-abort"], metrics=0.95)
    text, _ = run_look(monkeypatch, session, look, made)
    assert (text, made["aborted"], made["disconnected"]) == ("", 1, True)
    assert {k: look.report()[k] for k in REPORT} == {"credits": 0.95, "credits_known": True, "limit": 0.75,
                                                     "stopped": "reached", "stopped_by": "look"}  # fmt: skip


def test_an_answer_completed_as_the_limit_is_reached_is_kept(monkeypatch) -> None:
    made: dict[str, Any] = {}
    look = Meter(0.75)
    session = Session(made, [said('{"category": "none"}'), usage(0.9)], metrics=0.9)  # the turn ends at once
    text, _ = run_look(monkeypatch, session, look, made)
    assert text == '{"category": "none"}'
    assert (look.report()["stopped"], look.report()["credits"], look.report()["credits_known"]) == ("reached", 0.9,
                                                                                                    True)  # fmt: skip


def test_a_stalled_abort_leaves_the_turn_unconfirmed_and_every_wait_bounded(monkeypatch) -> None:
    made: dict[str, Any] = {}
    look = Meter(0.75)
    session = Session(made, [usage(0.8), "hang"], abort="stalls", metrics=0.8)
    text, took = run_look(monkeypatch, session, look, made)
    assert text == ""
    assert took < 1.5  # abort, the turn's end and the total each at most TEARDOWN, then the teardown
    report = look.report()
    assert (report["credits"], report["credits_known"], report["stopped"]) == (0.8, False, "reached")


def test_a_stalled_usage_read_keeps_the_calls_reported_within_its_bound(monkeypatch) -> None:
    made: dict[str, Any] = {}
    look = Meter(0.75)
    session = Session(made, [usage(0.1), said('{"category": "none"}')], metrics="stalls")
    text, took = run_look(monkeypatch, session, look, made)
    assert (text, look.report()["credits"], look.report()["credits_known"]) == ('{"category": "none"}', 0.1, True)
    assert took < 1.5


def test_a_cost_the_runtime_reports_as_not_finite_stops_the_turn_as_unknown(monkeypatch) -> None:
    made: dict[str, Any] = {}
    look = Meter(0.75)
    session = Session(made, [usage(math.inf), "wait-abort"], metrics=None)
    text, _ = run_look(monkeypatch, session, look, made)
    assert (text, made["aborted"]) == ("", 1)
    assert (look.report()["stopped"], look.report()["credits_known"]) == ("unknown", False)


def test_a_retry_or_extension_on_a_closed_meter_starts_no_session(monkeypatch) -> None:
    made: dict[str, Any] = {}
    look = Meter(0.75)
    first = Session(made, [usage(0.8), "wait-abort"], metrics=0.8)
    run_look(monkeypatch, first, look, made)
    assert made["clients"] == 1
    again = Session(made, [said('{"category": "none"}')])
    assert run_look(monkeypatch, again, look, made)[0] == ""  # the same look's meter: nothing left
    assert made["clients"] == 1  # no runtime was started for it
    assert look.report()["credits"] == 0.8


def test_a_cancelled_turn_reads_its_total_as_provisional(monkeypatch) -> None:
    made: dict[str, Any] = {}
    look = Meter(0.75)
    session = Session(made, [usage(0.1), "hang"], metrics=0.3)

    class Client:
        def __init__(self, **_kw: Any) -> None:
            pass

        async def start(self) -> None:
            pass

        async def create_session(self, **kw: Any) -> Session:
            made.update(kw)
            return session

        async def stop(self) -> None:
            pass

    monkeypatch.setattr(spotter_look, "CopilotClient", Client)
    monkeypatch.setattr(spotter_look, "cli_path", lambda: "/bin/false")
    monkeypatch.setattr(spotter, "TEARDOWN", 0.1)

    async def main() -> None:
        task = asyncio.ensure_future(REAL_LOOK({}, ctx(), look))
        await asyncio.sleep(0.05)
        task.cancel()  # the step ends while the look runs
        await asyncio.wait({task})

    asyncio.run(main())
    assert spotter.WORK.settled(5)
    assert (look.report()["credits"], look.report()["credits_known"], made["disconnected"]) == (0.3, False, True)


def test_the_limit_ignores_other_events_and_a_bounded_wait_cancels_what_stalls() -> None:
    async def main() -> tuple[bool, Any, bool, Any]:
        limit = credit_limit.Limit(Meter(0.75))
        limit.heard(said("hello"))
        limit.heard(SimpleNamespace(type="assistant.usage", data=None))  # no cost: unknown

        async def stall() -> None:
            await asyncio.sleep(30)

        async def fail() -> None:
            raise RuntimeError

        return (*await credit_limit.bounded(stall, 0.01), *await credit_limit.bounded(fail, 0.1))

    assert asyncio.run(main()) == (False, None, False, None)
