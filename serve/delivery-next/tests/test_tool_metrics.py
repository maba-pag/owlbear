"""Tool use across Changes (C-28): measured runs only, weighted success, every Metrics filter, never a made-up run."""

from __future__ import annotations

from datetime import date
from zoneinfo import ZoneInfo

from fastapi import FastAPI
from fastapi.testclient import TestClient

from owlbear_delivery_next.project_host import metrics_routes
from owlbear_delivery_next.runtimes import spend_reconcile
from owlbear_delivery_next.state_store import spend_ledger, spend_shares, tool_metrics

UTC = ZoneInfo("UTC")
BERLIN = ZoneInfo("Europe/Berlin")
USED = {"credits": 1.0, "models": {"m1": {"credits": 1.0, "input": 10, "output": 1}}}


def start(run: str, at: str, **more: object) -> dict:
    return {"id": f"start:{run}", "type": "start", "run": run, "at": at, "session": f"s-{run}", "agent": "builder",
            "model": "m1", "before": {}, "project": "p", "name": "P", "clone": "", "change": "ch", "step": "build",
            "job": ""} | more  # fmt: skip


def end(run: str, at: str, tools: dict | None = None, wrong: dict | None = None, **more: object) -> dict:
    line = {"id": f"end:{run}", "type": "end", "run": run, "at": at, "session": f"s-{run}", "usage": USED,
            "ending": "result", "limit": None, "stopped": "", "subagents": 0, "project": "p", "name": "P", "clone": "",
            "change": "ch", "step": "build", "job": ""} | more  # fmt: skip
    return line | ({"tools": tools, "wrong": wrong} if tools is not None and wrong is not None else {})


def ran(run: str, at: str, tools: dict, wrong: dict | None = None, **more: object) -> list[dict]:
    place = {k: v for k, v in more.items() if k in {"agent", "model", "project", "change"}}
    return [start(run, at, **place), end(run, at, tools, wrong or {}, **more)]


def used(lines: list[dict], **filters: object) -> dict:
    return tool_metrics.query(spend_shares.runs(lines), tz=filters.pop("tz", UTC), **filters)  # type: ignore[arg-type]


def test_success_is_weighted_by_calls_and_refusals_keep_their_split() -> None:
    lines = [
        *ran("r1", "2026-10-01T10:00:00+00:00", {"submit_result": {"calls": 1}}),
        *ran("r2", "2026-10-01T11:00:00+00:00", {"submit_result": {"calls": 9, "rejected": 7, "invalid": 3,
             "checks": 2, "order": 1, "lint": 1, "late": 1, "retries": 6}}, {"denied": 2, "no_result": 1}),
    ]  # fmt: skip
    found = used(lines)
    [row] = found["tools"]
    assert (row["calls"], row["accepted"], row["success"]) == (10, 1, 10)  # 1/1 and 0/9: 10 %, never 50 %
    assert (row["invalid"], row["checks"], row["order"], row["unsplit"], row["lint"], row["late"]) == (3, 2, 1, 1, 1, 1)
    assert found["totals"]["success"] == 10
    assert found["wrong"] == {"order": 1, "denied": 2, "no_result": 1, "missing_pointless": 0}
    assert (found["runs"], found["since"]) == (2, "2026-10-01T10:00:00+00:00")


def test_only_measured_runs_count_and_sparse_or_repeated_lines_add_none() -> None:
    log_end = {"id": "log:r1", "type": "end", "run": "r1", "at": "2026-10-01T10:05:00+00:00", "session": "s-r1",
               "usage": {"credits": 2.0, "models": {}}, "source": "import:runtime-log"}  # fmt: skip
    event = {"id": "event:e", "type": "event", "at": "2026-10-01T10:30:00+00:00", "session": "s-r1",
             "usage": {"credits": 2.0, "models": {}}, "agent": "builder", "project": "p", "change": "ch",
             "source": "import:activity"}  # fmt: skip
    lines = [
        *ran("r1", "2026-10-01T10:00:00+00:00", {"bash": {"calls": 3}}), log_end, event,
        *ran("empty", "2026-10-01T12:00:00+00:00", {}),  # measured, though nothing was called
        start("open", "2026-10-01T13:00:00+00:00"),  # a run that never ended
        start("old", "2026-09-01T10:00:00+00:00"), end("old", "2026-09-01T10:00:00+00:00"),  # before this release
    ]  # fmt: skip
    for stopped in (False, True):
        found = used(lines, stopped=stopped)
        assert (found["runs"], found["totals"]["calls"]) == ((2, 3) if not stopped else (0, 0))
    assert used(lines)["since"] == "2026-10-01T10:00:00+00:00"  # the log's correction kept the run's tools


def test_a_continued_runs_later_checkpoints_are_not_counted_again() -> None:
    checkpoint = {"id": "log:k", "type": "end", "run": "k", "at": "2026-10-01T10:00:00+00:00", "session": "s-k",
                  "usage": {"credits": 1.0, "models": {}}, "source": "import:runtime-log"}  # fmt: skip
    later = {"id": "log:k2", "at": "2026-10-01T11:00:00+00:00", "usage": {"credits": 2.0, "models": {}}}
    lines = [start("k", "2026-10-01T09:00:00+00:00"), checkpoint | {"tools": {"bash": {"calls": 2}}, "wrong": {}},
             checkpoint | later]  # fmt: skip
    entries = spend_shares.runs(lines)
    assert any(e.get("continued") for e in entries)
    assert (used(lines)["runs"], used(lines)["totals"]["calls"]) == (1, 2)


def test_each_filter_picks_the_runs_main_agent_model_place_stop_and_local_period() -> None:
    lines = [
        *ran("a", "2026-10-01T21:30:00+00:00", {"bash": {"calls": 1}}, agent="builder", model="m1", project="p"),
        *ran("b", "2026-10-01T22:30:00+00:00", {"bash": {"calls": 2}}, agent="reviewer", model="m2", project="q",
             change="other", stopped="reached"),
        *ran("c", "2026-10-02T10:00:00+00:00", {"bash": {"calls": 4}}, agent="", model="", project=""),
    ]  # fmt: skip

    def calls(**filters: object) -> int:
        return used(lines, **filters)["totals"]["calls"]

    assert calls() == 7
    assert (calls(project="p"), calls(project="q"), calls(project="?")) == (1, 2, 4)
    assert (calls(agent="reviewer"), calls(agent="?"), calls(agent="explore")) == (2, 4, 0)  # a subagent has none
    assert (calls(model="m2"), calls(change="q/other"), calls(stopped=True)) == (2, 2, 2)
    day = {"start": date(2026, 10, 2), "end": date(2026, 10, 3)}
    assert (calls(**day), calls(tz=BERLIN, **day)) == (4, 6)  # 22:30 UTC is already 2 October in Berlin
    assert used(lines, project="p")["choices"] == {"agents": ["?", "builder", "reviewer"], "models": ["?", "m1", "m2"]}


def test_the_route_answers_tool_use_and_offers_a_main_agent_seen_only_as_an_unsplit_subagent() -> None:
    split = {"credits": 2.0, "models": {}, "agents": {"x": {"agent": "explore", "models": {"m1": {"credits": 2.0}}}}}
    spend_ledger.append([
        start("r", "2026-10-01T10:00:00+00:00", agent="designer"),
        end("r", "2026-10-01T10:00:00+00:00", {"submit_result": {"calls": 2, "rejected": 1, "invalid": 1}},
            {"missing_pointless": 1}, usage=split),
    ])  # fmt: skip
    assert spend_ledger.WRITER.settled(5)
    app = FastAPI()
    app.include_router(metrics_routes.router(list), prefix="/api/next")
    found = TestClient(app).get("/api/next/metrics?from=2026-10-01&to=2026-10-02&by=day&cursor=0").json()
    assert spend_reconcile.settled(10)
    assert "designer" in found["choices"]["agents"]
    use = found["tool_use"]
    assert (use["runs"], use["tools"][0]["tool"], use["tools"][0]["success"]) == (1, "submit_result", 50)
    assert use["wrong"]["missing_pointless"] == 1
