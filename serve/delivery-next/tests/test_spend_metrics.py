"""Spend shares and the Metrics query (D-01M5XCDF6G60VG5GHTWF5QSSDE): exclusive, additive, never a made-up day."""

from __future__ import annotations

from datetime import date
from zoneinfo import ZoneInfo

import pytest

from owlbear_delivery_next.state_store import spend_metrics, spend_shares

UTC = ZoneInfo("UTC")
BERLIN = ZoneInfo("Europe/Berlin")


def usage(spent: float | None, model: str = "m1", tokens: int = 10, **agents: dict) -> dict:
    out: dict = {"credits": spent, "models": {model: {"credits": spent, "input": tokens, "output": 1}}}
    if agents:
        out["agents"] = agents
        out["models"] = {}
    return out


def agent(name: str, **models: float) -> dict:
    return {"agent": name, "models": {m: {"credits": c, "input": 1, "output": 1} for m, c in models.items()}}


def start(run: str, at: str, session: str = "s1", before: dict | None = None, **more) -> dict:
    return {"id": f"start:{run}", "type": "start", "run": run, "at": at, "session": session, "agent": "builder",
            "model": "m1", "before": before, "project": "p", "name": "P", "clone": "c1", "change": "ch",
            "step": "build", "job": ""} | more  # fmt: skip


def end(run: str, at: str, used: dict, session: str = "s1", **more) -> dict:
    return {"id": f"end:{run}", "type": "end", "run": run, "at": at, "session": session, "usage": used,
            "ending": "result", "limit": None, "stopped": "", "subagents": 0, "project": "p", "name": "P",
            "clone": "c1", "change": "ch", "step": "build", "job": ""} | more  # fmt: skip


def credits_of(pieces: list[dict], **match) -> float:
    return round(sum(p["credits"] or 0 for p in pieces if all(p[k] == v for k, v in match.items())), 6)


def test_a_resumed_session_crossing_a_month_counts_only_its_growth_in_each_month() -> None:
    lines = [
        start("r1", "2026-09-30T23:00:00+00:00", before={}),
        end("r1", "2026-09-30T23:30:00+00:00", usage(2.0)),
        start("r2", "2026-10-01T10:00:00+00:00", before=usage(2.0)),
        end("r2", "2026-10-01T10:30:00+00:00", usage(5.0)),
    ]
    pieces = spend_shares.derive(lines)
    assert [(p["run"], p["credits"], p["uncertain"]) for p in pieces] == [("r1", 2.0, []), ("r2", 3.0, [])]
    october = spend_metrics.query(pieces, tz=UTC, start=date(2026, 10, 1), end=date(2026, 11, 1))
    september = spend_metrics.query(pieces, tz=UTC, start=date(2026, 9, 1), end=date(2026, 10, 1))
    assert (october["totals"]["credits"], september["totals"]["credits"]) == (3.0, 2.0)
    assert october["undated"] is None


def test_lines_appended_out_of_order_and_repeated_never_count_twice() -> None:
    live = [start("r2", "2026-10-02T10:00:00+00:00", before=usage(2.0)), end("r2", "2026-10-02T11:00:00+00:00",
                                                                          usage(5.0))]  # fmt: skip
    imported = {"id": "event:x", "type": "event", "at": "2026-10-01T09:00:00+00:00", "session": "s1",
                "usage": usage(2.0), "agent": "builder", "project": "p", "change": "ch"}  # fmt: skip
    mark = {"id": "mark:x", "type": "mark", "session": "s1", "usage": usage(5.0), "agent": "", "project": "p"}
    pieces = spend_shares.derive([*live, imported, mark, imported])
    assert credits_of(pieces) == 5.0
    assert credits_of(pieces, run="event:x") == 2.0
    assert credits_of(pieces, run="r2") == 3.0


def test_a_missing_baseline_takes_the_growth_with_its_time_uncertain() -> None:
    lines = [end("r1", "2026-10-01T10:00:00+00:00", usage(2.0)), start("r2", "2026-10-02T10:00:00+00:00"),
             end("r2", "2026-10-02T11:00:00+00:00", usage(6.0))]  # fmt: skip
    pieces = spend_shares.derive(lines)
    said = [(p["run"], p["credits"], p["uncertain"]) for p in pieces]
    assert said == [("r1", 2.0, ["agent", "at"]), ("r2", 4.0, ["at"])]  # r1's start, naming its agent, was lost


def test_an_unread_baseline_spreads_a_runs_share_over_the_window_since_the_last_report() -> None:
    """Sol's counterexample: 2 on Oct 1, then 6 on Oct 2 after an unread baseline put all 4 on Oct 2."""
    lines = [
        start("r1", "2026-10-01T09:00:00+00:00", before={}),
        end("r1", "2026-10-01T10:00:00+00:00", usage(2.0)),
        start("r2", "2026-10-02T10:00:00+00:00", before=None),
        end("r2", "2026-10-02T11:00:00+00:00", usage(6.0)),
    ]
    pieces = spend_shares.derive(lines)
    assert [(p["run"], p["credits"], p["lo"], p["hi"]) for p in pieces] == [
        ("r1", 2.0, "2026-10-01T10:00:00+00:00", "2026-10-01T10:00:00+00:00"),
        ("r2", 4.0, "2026-10-01T10:00:00+00:00", "2026-10-02T11:00:00+00:00"),
    ]
    days = spend_metrics.query(pieces, tz=UTC, by="day")
    assert [(r["key"], r["credits"]) for r in days["rows"]] == [("2026-10-01", 2.0), ("?", 4.0)]
    oct2 = spend_metrics.query(pieces, tz=UTC, start=date(2026, 10, 2), end=date(2026, 10, 3))
    assert (oct2["totals"]["credits"], oct2["undated"]["credits"]) == (0.0, 4.0)
    both = spend_metrics.query(pieces, tz=UTC, start=date(2026, 10, 1), end=date(2026, 10, 3))
    assert (both["totals"]["credits"], both["undated"]) == (6.0, None)


def test_re_splitting_earlier_credits_between_agents_never_creates_spend() -> None:
    """Sol's counterexample: an unsplit legacy total of 10, then the split cumulative total 11, made 13."""
    unsplit = usage(10.0)
    split = usage(11.0, main=agent("main", m1=8.0), x1=agent("explore", m1=3.0))
    lines = [
        start("r1", "2026-10-01T10:00:00+00:00", before={}),
        end("r1", "2026-10-01T10:30:00+00:00", unsplit),
        start("r2", "2026-10-02T10:00:00+00:00", before=unsplit),
        end("r2", "2026-10-02T10:30:00+00:00", split),
    ]
    pieces = spend_shares.derive(lines)
    assert credits_of(pieces) == 11.0
    assert credits_of(pieces, run="r2") == 1.0
    assert sum(p["input"] for p in pieces) == 10  # tokens too: never more than the session's highest total


def test_runs_that_spent_nothing_new_or_reported_no_credits_still_count_with_their_stop() -> None:
    """Sol's counterexamples: credits None with no models vanished; so did a resume stopped at a reached limit."""
    lines = [
        start("r1", "2026-10-01T10:00:00+00:00", session="a", before={}),
        end("r1", "2026-10-01T10:10:00+00:00", {"credits": None, "models": {}}, session="a"),
        start("r2", "2026-10-01T11:00:00+00:00", session="b", before={}),
        end("r2", "2026-10-01T11:10:00+00:00", usage(2.0), session="b"),
        start("r3", "2026-10-01T12:00:00+00:00", session="b", before=usage(2.0)),
        end("r3", "2026-10-01T12:00:05+00:00", usage(2.0), session="b", ending="credit-limit", stopped="reached",
            stopped_by="session", limit=2.0),
    ]  # fmt: skip
    pieces = spend_shares.derive(lines)
    assert [(p["run"], p["kind"], p["credits"]) for p in pieces] == [
        ("r1", "unknown", None), ("r2", "run", 2.0), ("r3", "run", 0.0)
    ]  # fmt: skip
    found = spend_metrics.query(pieces, tz=UTC)
    assert (found["totals"]["runs"], found["totals"]["unknown"], found["totals"]["stopped"]) == (3, 1, 1)
    r3 = next(r for r in found["runs"]["items"] if r["run"] == "r3")
    assert (r3["ending"], r3["stopped"], r3["stopped_by"], r3["credits"]) == ("credit-limit", "reached", "session", 0.0)


def test_a_stop_not_known_to_have_reached_its_limit_is_never_counted_as_reached() -> None:
    lines = []
    for n, stop in enumerate(("reached", "unknown", "")):
        at = f"2026-10-01T10:0{n}:00+00:00"
        lines += [
            start(f"r{n}", at, session=f"s{n}", before={}),
            end(f"r{n}", at, usage(1.0), session=f"s{n}", stopped=stop, stopped_by="look" if stop else ""),
        ]
    found = spend_metrics.query(spend_shares.derive(lines), tz=UTC)
    assert (found["totals"]["stopped"], found["totals"]["stopped_unknown"]) == (1, 1)
    only = spend_metrics.query(spend_shares.derive(lines), tz=UTC, stopped=True)
    assert [(r["run"], r["stopped"], r["stopped_by"]) for r in only["runs"]["items"]] == [("r0", "reached", "look")]


def test_a_failed_final_read_is_unknown_until_the_next_run_recovers_it_in_its_window() -> None:
    lines = [
        start("r1", "2026-10-01T10:00:00+00:00", before={}),
        end("r1", "2026-10-01T10:40:00+00:00", {"error": "TimeoutError"}),
        start("r2", "2026-10-01T12:00:00+00:00", before=usage(4.0)),
        end("r2", "2026-10-01T12:30:00+00:00", usage(6.0)),
    ]
    pieces = spend_shares.derive(lines)
    kinds = [(p["run"], p["kind"], p["credits"], p["lo"], p["hi"]) for p in pieces]
    assert kinds == [
        ("r1", "recovered", 4.0, "2026-10-01T10:00:00+00:00", "2026-10-01T12:00:00+00:00"),
        ("r2", "run", 2.0, "2026-10-01T12:30:00+00:00", "2026-10-01T12:30:00+00:00"),
    ]
    day = spend_metrics.query(pieces, tz=UTC, start=date(2026, 10, 1), end=date(2026, 10, 2), by="day")
    assert [(r["key"], r["credits"]) for r in day["rows"]] == [("2026-10-01", 6.0)]  # its window is in one day


def test_a_killed_run_stays_open_and_unknown_until_reconciled() -> None:
    pieces = spend_shares.derive([start("r1", "2026-10-01T10:00:00+00:00", before={})])
    assert [(p["kind"], p["credits"]) for p in pieces] == [("open", None)]
    found = spend_metrics.query(pieces, tz=UTC)
    assert (found["totals"]["unknown"], found["totals"]["open"], found["coverage"]["open"]) == (1, 1, 1)
    assert found["runs"]["items"][0]["open"] is True


def test_pre_ledger_history_of_a_resumed_session_is_a_gap_with_no_day() -> None:
    lines = [start("r1", "2026-10-01T10:00:00+00:00", before=usage(3.0)), end("r1", "2026-10-01T10:30:00+00:00",
                                                                              usage(4.0))]  # fmt: skip
    pieces = spend_shares.derive(lines)
    assert [(p["kind"], p["credits"], p["lo"]) for p in pieces] == [("gap", 3.0, None), ("run", 1.0,
                                                                      "2026-10-01T10:30:00+00:00")]  # fmt: skip
    day = spend_metrics.query(pieces, tz=UTC, by="day")
    assert [(r["key"], r["credits"]) for r in day["rows"]] == [("2026-10-01", 1.0), ("?", 3.0)]
    ranged = spend_metrics.query(pieces, tz=UTC, start=date(2026, 10, 1), end=date(2026, 10, 2))
    assert (ranged["totals"]["credits"], ranged["undated"]["credits"]) == (1.0, 3.0)


def test_subagents_get_exclusive_shares_and_the_unsplit_rest_is_unallocated() -> None:
    first = usage(4.5, main=agent("main", m1=3.0), a1=agent("explore", m2=1.0))
    again = usage(9.5, main=agent("main", m1=5.0), a1=agent("explore", m2=1.0), a2=agent("explore", m2=3.0))
    lines = [
        start("r1", "2026-10-01T10:00:00+00:00", before={}),
        end("r1", "2026-10-01T10:30:00+00:00", first),
        start("r2", "2026-10-02T10:00:00+00:00", before=first),
        end("r2", "2026-10-02T10:30:00+00:00", again),
    ]
    pieces = spend_shares.derive(lines)
    assert credits_of(pieces) == 9.5
    assert {(p["run"], p["agent"], p["under"], p["model"], p["credits"]) for p in pieces} == {
        ("r1", "builder", "", "m1", 3.0),
        ("r1", "explore", "builder", "m2", 1.0),
        ("r1", "", "builder", "", 0.5),
        ("r2", "builder", "", "m1", 2.0),
        ("r2", "explore", "builder", "m2", 3.0),
    }  # fmt: skip  (the unsplit rest is cumulative too: it did not grow in r2)
    explore = spend_metrics.query(pieces, tz=UTC, agent="explore", by="model")
    assert [(r["key"], r["credits"]) for r in explore["rows"]] == [("m2", 4.0)]
    agents = spend_metrics.query(pieces, tz=UTC, by="agent")
    assert [(r["label"], r["credits"]) for r in agents["rows"]] == [
        ("builder", 5.0),
        ("explore (subagent)", 4.0),
        ("Agent unknown", 0.5),
    ]
    assert agents["totals"]["uncertain_agent"] == 0.5


def test_a_run_with_subagents_but_no_split_is_uncertain_in_agent() -> None:
    lines = [start("r1", "2026-10-01T10:00:00+00:00", before={}),
             end("r1", "2026-10-01T10:30:00+00:00", usage(2.0), subagents=2)]  # fmt: skip
    pieces = spend_shares.derive(lines)
    assert [(p["agent"], p["under"], p["role"], p["uncertain"]) for p in pieces] == [
        ("", "builder", "builder", ["agent"])
    ]
    by_agent = spend_metrics.query(pieces, tz=UTC, by="agent")["rows"]
    assert [(r["label"], r["credits"]) for r in by_agent] == [("Agent unknown", 2.0)]  # never all the builder's
    assert spend_metrics.query(pieces, tz=UTC, agent="builder")["totals"]["credits"] == 0


@pytest.mark.parametrize(
    ("day", "inside", "outside"),
    [
        (date(2026, 10, 25), ["2026-10-24T22:30:00+00:00", "2026-10-25T22:30:00+00:00"], ["2026-10-25T23:30:00+00:00"]),
        (date(2026, 3, 29), ["2026-03-28T23:30:00+00:00", "2026-03-29T21:30:00+00:00"], ["2026-03-29T22:30:00+00:00"]),
    ],
)
def test_a_day_is_local_midnight_to_midnight_on_25_and_23_hour_days(day, inside, outside) -> None:
    lines = []
    for n, at in enumerate(inside + outside):
        lines += [start(f"r{n}", at, session=f"s{n}", before={}), end(f"r{n}", at, usage(1.0), session=f"s{n}")]
    after = date.fromordinal(day.toordinal() + 1)
    found = spend_metrics.query(spend_shares.derive(lines), tz=BERLIN, start=day, end=after, by="day")
    assert [(r["key"], r["credits"]) for r in found["rows"]] == [(day.isoformat(), float(len(inside)))]


def test_filters_splits_limit_stops_and_a_paged_run_list() -> None:
    lines = []
    for n in range(60):
        at = f"2026-10-01T10:{n:02d}:00+00:00"
        stop = {"stopped": "reached", "stopped_by": "session", "limit": 2.0} if n % 20 == 0 else {}
        project = {"project": "q", "name": "Q", "clone": "c2"} if n % 2 else {}
        lines += [
            start(f"r{n}", at, session=f"s{n}", before={}, **project),
            end(f"r{n}", at, usage(1.0, model="m2" if n % 3 else "m1"), session=f"s{n}", **stop, **project),
        ]
    pieces = spend_shares.derive(lines)
    found = spend_metrics.query(pieces, tz=UTC, by="project")
    assert [(r["label"], r["credits"], r["stopped"]) for r in found["rows"]] == [("P", 30.0, 3), ("Q", 30.0, 0)]
    assert (found["runs"]["total"], len(found["runs"]["items"]), found["runs"]["next"]) == (60, 50, 50)
    assert found["runs"]["items"][0]["run"] == "r59"
    rest = spend_metrics.query(pieces, tz=UTC, cursor=50)["runs"]
    assert (len(rest["items"]), rest["next"]) == (10, None)
    stopped = spend_metrics.query(pieces, tz=UTC, stopped=True, project="p")
    assert (stopped["totals"]["runs"], stopped["totals"]["stopped"]) == (3, 3)
    one = spend_metrics.query(pieces, tz=UTC, stopped=True, project="p", model="m1")
    assert [r["run"] for r in one["runs"]["items"]] == ["r0"]
    assert found["choices"]["clones"] == {"c1": "p", "c2": "q"}
    assert found["choices"]["changes"] == ["p/ch", "q/ch"]


def test_imported_marks_and_residuals_say_what_is_uncertain() -> None:
    lines = [
        {"id": "residual:x", "type": "residual", "session": "residual:c1:ch", "usage": {"credits": 1.5},
         "project": "p", "change": "ch", "source": "import:change"},
        {"id": "look:1", "type": "look", "at": "2026-10-01T10:00:00+00:00", "session": "look:1",
         "usage": {"error": "estimate"}, "agent": "spotter", "project": "p", "source": "import:spotter"},
    ]  # fmt: skip
    pieces = spend_shares.derive(lines)
    assert [(p["kind"], p["credits"], p["agent"], p["uncertain"]) for p in pieces] == [
        ("run", 1.5, "", ["agent", "at"]),
        ("unknown", None, "spotter", []),
    ]
    found = spend_metrics.query(pieces, tz=UTC)
    assert (found["totals"]["credits"], found["totals"]["unknown"]) == (1.5, 1)
    assert found["coverage"]["sources"] == {"import:change": 1.5, "import:spotter": 0.0}


def both(models: dict[str, float], **agents: dict) -> dict:
    """A usage as the runtime reports it: per model and, when given, per agent instance."""
    out: dict = {"credits": sum(models.values()), "models": {m: {"credits": c} for m, c in models.items()}}
    return out | ({"agents": agents} if agents else {})


def test_agents_named_later_never_move_credits_between_models() -> None:
    """Sol's counterexample: m1=7, m2=3, then main/m1=8 and explore/m2=3 reported m1=7.25, m2=3.75, not 8 and 3."""
    first = both({"m1": 7.0, "m2": 3.0})
    later = both({"m1": 8.0, "m2": 3.0}, main=agent("main", m1=8.0), x1=agent("explore", m2=3.0))
    lines = [
        start("r1", "2026-10-01T10:00:00+00:00", before={}),
        end("r1", "2026-10-01T10:30:00+00:00", first),
        start("r2", "2026-10-02T10:00:00+00:00", before=first),
        end("r2", "2026-10-02T10:30:00+00:00", later),
    ]
    pieces = spend_shares.derive(lines)
    assert (credits_of(pieces, model="m1"), credits_of(pieces, model="m2")) == (8.0, 3.0)
    assert [(p["run"], p["agent"], p["model"], p["credits"]) for p in pieces if p["run"] == "r2"] == [
        ("r2", "builder", "m1", 1.0)
    ]


def test_a_model_whose_agents_re_split_earlier_spend_leaves_the_agent_unknown_not_invented() -> None:
    first = both({"m1": 10.0})
    later = both({"m1": 11.0}, main=agent("main", m1=8.0), x1=agent("explore", m1=3.0))
    lines = [
        start("r1", "2026-10-01T10:00:00+00:00", before={}),
        end("r1", "2026-10-01T10:30:00+00:00", first),
        start("r2", "2026-10-02T10:00:00+00:00", before=first),
        end("r2", "2026-10-02T10:30:00+00:00", later),
    ]
    r2 = [p for p in spend_shares.derive(lines) if p["run"] == "r2"]
    assert [(p["agent"], p["under"], p["model"], p["credits"], p["uncertain"]) for p in r2] == [
        ("", "builder", "m1", 1.0, ["agent"])
    ]


@pytest.mark.parametrize("live_first", [True, False])
def test_a_look_seen_by_its_own_lines_and_its_spotter_record_counts_once(live_first) -> None:
    """Sol's counterexample: a look finishing while a pass scanned was imported too (0.2 counted as 0.4)."""
    live = [
        start("L", "2026-10-27T10:00:01+00:00", session="look-sdk", before={}, agent="spotter", look="x"),
        end("L", "2026-10-27T10:00:09+00:00", usage(0.2), session="look-sdk", look="x"),
    ]
    imported = {"id": "look:x", "type": "look", "at": "2026-10-27T10:00:00+00:00", "session": "look:x",
                "usage": usage(0.2), "agent": "spotter", "look": "x", "source": "import:spotter"}  # fmt: skip
    pieces = spend_shares.derive([*live, imported] if live_first else [imported, *live])
    assert [(p["run"], p["credits"]) for p in pieces] == [("L", 0.2)]


@pytest.mark.parametrize("event_at", ["2026-10-01T10:29:59+00:00", "2026-10-01T10:30:01+00:00"])
def test_an_imported_checkpoint_repeating_a_runs_totals_adds_no_run(event_at) -> None:
    """Sol's counterexample: an invocation and its activity event with the same totals made an extra zero run."""
    event = {"id": "event:e", "type": "event", "at": event_at, "session": "s1", "usage": usage(3.0),
             "agent": "builder", "project": "p", "change": "ch", "source": "import:activity"}  # fmt: skip
    lines = [start("r1", "2026-10-01T10:00:00+00:00", before={}), end("r1", "2026-10-01T10:30:00+00:00", usage(3.0)),
             event]  # fmt: skip
    found = spend_metrics.query(spend_shares.derive(lines), tz=UTC)
    assert (found["totals"]["runs"], found["totals"]["credits"], found["runs"]["items"][0]["run"]) == (1, 3.0, "r1")
