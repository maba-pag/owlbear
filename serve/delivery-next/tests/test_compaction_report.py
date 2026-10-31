"""Metrics' compaction report (C-03): per role, how often and how early its sessions compacted, from known logs."""

from __future__ import annotations

import gzip
import json
import logging
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from owlbear_delivery_next.improvement import chatlogs
from owlbear_delivery_next.project_host import metrics_routes
from owlbear_delivery_next.runtimes import compaction_logs, spend_reconcile
from owlbear_delivery_next.state_store import spend_ledger

NOW = datetime.now(UTC).replace(microsecond=0) - timedelta(hours=1)
OLD = NOW - timedelta(days=40)
LAST_30 = f"from={(NOW - timedelta(days=30)).date()}&to={(NOW + timedelta(days=2)).date()}"
COUNTS = ("sessions", "logs", "missing", "unreadable", "compacted", "compactions", "median", "earliest")


def used(total: float, model: str = "m1", **agents: tuple[str, float]) -> dict:
    if not agents:
        return {"credits": total, "models": {model: {"credits": total, "input": 10, "output": 1}}}
    split = {"main": {"agent": "main", "models": {model: {"credits": total - sum(c for _, c in agents.values())}}}}
    split |= {key: {"agent": name, "models": {model: {"credits": spent}}} for key, (name, spent) in agents.items()}
    return {"credits": total, "models": {}, "agents": split}


def ran(  # noqa: PLR0913 - the run, its time, place, usage, baseline and session
    run: str, at: datetime, place: dict, *, usage: dict, before: dict | None, session: str = "", **end: object
) -> list[dict]:
    """A run's start and end lines at the same time; *before* is its session's usage so far, None unread."""
    when = at.isoformat(timespec="seconds")
    common = {"run": run, "session": session or f"s-{run}", "step": "build", "job": ""} | place
    model = next(iter(usage["models"]), "m1") if usage["models"] else "m1"
    return [
        common | {"id": f"start:{run}", "type": "start", "at": when, "model": model,
                  "before": before},
        common | {"id": f"end:{run}", "type": "end", "at": when, "usage": usage, "ending": "result", "limit": None,
                  "stopped": "", "subagents": 0} | end,
    ]  # fmt: skip


def event(kind: str, agent: str = "", **data: object) -> str:
    return json.dumps({"type": kind, "data": data, "id": "e", "timestamp": "2026-10-28T14:40:17.428Z"}
                      | ({"agentId": agent} if agent else {})) + "\n"  # fmt: skip


def calls(n: int, agent: str = "", parent: str = "") -> list[str]:
    return [event("assistant.turn_start", agent, **({"parentToolCallId": parent} if parent else {}))] * n


def start(attempt: str, agent: str = "") -> str:
    return event("session.compaction_start", agent, compactionAttemptId=attempt, trigger="threshold")


def done(attempt: str, **how: object) -> str:
    return event("session.compaction_complete", compactionAttemptId=attempt, **({"success": True, "outcome": "applied"}
                                                                               | how))  # fmt: skip


def applied(attempt: str) -> list[str]:
    return [start(attempt), done(attempt)]


def live(session: str, lines: list[str]) -> None:
    path = chatlogs.state() / session / "events.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(lines))


def copied(session: str, data: bytes) -> None:
    path = chatlogs.root() / "chatlogs" / session / "log.jsonl.gz"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


SHOP = {"project": "shop", "name": "shop", "clone": "shop", "agent": "builder", "change": "c2"}
MILL = {"project": "mill", "name": "mill", "clone": "mill", "agent": "builder", "change": "c3"}


def seed(*, b1_unread: bool = False) -> None:
    """The plan's fixture: shop's and mill's builder sessions, shop's reviewer and the machine's retro."""
    b1r = used(1.0)
    spend_ledger.append([
        *ran("b1r", OLD, SHOP, usage=b1r, session="s-b1", before={}),
        *ran("b1", NOW, SHOP, usage=used(3.0, x1=("explore", 0.5), x2=("explore", 0.5)), session="s-b1",
             before=None if b1_unread else b1r),
        *ran("b2", NOW, SHOP, usage=used(1.0, "m2"), before={}),
        *ran("b6", NOW, SHOP, usage=used(1.0), before={}),
        *ran("rv", NOW, SHOP | {"agent": "reviewer", "change": "c1"}, usage=used(0.5), stopped="reached", before={}),
        *ran("b3", NOW, MILL, usage=used(1.0), before={}),
        *ran("b4", NOW, MILL, usage=used(1.0), before={}),
        *ran("b7", NOW, MILL, usage=used(1.0), before={}),
        *ran("rt", NOW, {"project": "", "name": "", "clone": "", "agent": "retro", "change": ""}, usage=used(0.5),
             before={}),
    ])  # fmt: skip
    live("s-b1", [
        *calls(1), start("a"), *calls(1), done("a"), *calls(2), event("session.resume"), *calls(1),
        event("subagent.started", "c1", toolCallId="t1", agentName="explore"), *calls(2, "c1", "t1"), start("x", "c1"),
        *calls(1), done("x"), *calls(3, "c1", "t1"), *calls(2),
        event("subagent.started", "c2", toolCallId="t2", agentName="explore"), *calls(3, "c2", "t2"), *calls(2),
    ])  # fmt: skip
    live("s-b2", [*calls(4), event("session.compaction_start", compactionAttemptId="a"),
                  event("session.compaction_complete", compactionAttemptId="a", success=True),
                  *calls(3), *applied("b"), *calls(3)])  # fmt: skip
    live("s-rv", [event("session.start")])
    live("s-b3", [*calls(3), start("a"), done("a", success=False, outcome="failed"), *calls(6), *applied("b"),
                  *calls(1)])  # fmt: skip
    live("s-b4", [*calls(2), start("a"), done("a", outcome="cancelled"), *calls(2), start("b"), *calls(2),
                  done("z"), *calls(2)])  # fmt: skip
    copied("s-b7", b"not a gzip file")
    copied("s-rt", gzip.compress("".join([*calls(1), *applied("a"), *calls(4)]).encode()))


@pytest.fixture
def get(monkeypatch):
    monkeypatch.setattr(spend_reconcile, "due", lambda *_a: False)  # the ledger holds only the fixture's lines
    app = FastAPI()
    app.include_router(metrics_routes.router(list), prefix="/api/next")
    client = TestClient(app, raise_server_exceptions=False)
    return lambda query="": client.get(f"/api/next/metrics?{query}")


def rows(answer: dict) -> dict[tuple, tuple]:
    return {(r["agent"], r["subagent"], r["project"]): tuple(r[k] for k in COUNTS) for r in answer["rows"]}


BUILDER_SHOP = {("builder", "", "shop"): (3, 2, 1, 0, 2, 3, 0.3, 0.2)}
BUILDER_MILL = {("builder", "", "mill"): (3, 2, 0, 1, 1, 1, 0.9, 0.9)}
EXPLORE = {("builder", "explore", "shop"): (2, 2, 0, 0, 1, 1, 0.4, 0.4)}
RETRO = {("retro", "", ""): (1, 1, 0, 0, 1, 1, 0.2, 0.2)}
REVIEWER = {("reviewer", "", "shop"): (1, 1, 0, 0, 0, 0, None, None)}
EVERY = {("builder", "", None): (6, 4, 1, 1, 3, 4, 0.4, 0.2)} | BUILDER_SHOP | BUILDER_MILL | EXPLORE | RETRO | REVIEWER


def test_each_role_shows_how_often_and_how_early_its_sessions_compacted(get, caplog) -> None:
    seed()
    caplog.set_level(logging.WARNING, compaction_logs.__name__)
    found = get(f"{LAST_30}&tz=UTC").json()["compaction"]
    assert rows(found) == EVERY
    assert [r["project"] for r in found["rows"]][:3] == [None, "mill", "shop"]  # the aggregate first, then by name
    [error] = found["errors"]
    assert (error["session"], error["project"], error["role"]) == ("s-b7", "mill", "builder")
    assert str(chatlogs.root() / "chatlogs" / "s-b7" / "log.jsonl.gz") in error["error"]
    assert "BadGzipFile" in error["error"]
    assert "BadGzipFile" in caplog.text
    assert get(f"{LAST_30}&by=day&cursor=50").json()["compaction"] == found


def test_a_resumed_session_counts_once_with_its_whole_log(get, monkeypatch) -> None:
    seed()
    read = []
    real = compaction_logs.read
    monkeypatch.setattr(compaction_logs, "read", lambda s: read.append(s) or real(s))
    assert rows(get().json()["compaction"]) == EVERY  # all time: b1r and b1 both inside
    assert read.count("s-b1") == 1
    old = f"from={(OLD - timedelta(days=5)).date()}&to={(OLD + timedelta(days=1)).date()}"  # b1r's piece only
    assert rows(get(old).json()["compaction"]) == {("builder", "", "shop"): (1, 1, 0, 0, 1, 1, 0.2, 0.2)} | EXPLORE


def test_each_filter_picks_its_sessions_and_an_agent_its_own_rows(get) -> None:
    seed()
    assert rows(get(f"{LAST_30}&project=mill").json()["compaction"]) == BUILDER_MILL
    assert rows(get(f"{LAST_30}&agent=reviewer").json()["compaction"]) == REVIEWER
    assert rows(get(f"{LAST_30}&agent=explore").json()["compaction"]) == EXPLORE
    assert rows(get(f"{LAST_30}&model=m2").json()["compaction"]) == {
        ("builder", "", "shop"): (1, 1, 0, 0, 1, 2, 0.4, 0.4)}  # fmt: skip
    assert rows(get(f"{LAST_30}&change=shop/c1").json()["compaction"]) == REVIEWER
    assert rows(get(f"{LAST_30}&stopped=true").json()["compaction"]) == REVIEWER


def test_a_session_whose_spend_crosses_the_periods_start_is_left_out(get) -> None:
    seed(b1_unread=True)
    assert rows(get(LAST_30).json()["compaction"]) == {
        ("builder", "", None): (5, 3, 1, 1, 2, 3, 0.65, 0.4), ("builder", "", "shop"): (2, 1, 1, 0, 1, 2, 0.4, 0.4),
    } | BUILDER_MILL | RETRO | REVIEWER  # fmt: skip


def test_a_log_that_grew_is_read_again(get) -> None:
    seed()
    get(LAST_30)
    path = chatlogs.state() / "s-b4" / "events.jsonl"
    path.write_text(path.read_text() + "".join([*applied("c"), *calls(2)]))
    found = rows(get(LAST_30).json()["compaction"])
    assert found["builder", "", "mill"] == (3, 2, 0, 1, 2, 2, 0.85, 0.8)
    assert found["builder", "", None] == (6, 4, 1, 1, 4, 5, 0.6, 0.2)


def test_a_failed_report_says_why(get, monkeypatch, caplog) -> None:
    seed()

    def broken(_session: str) -> None:
        msg = "x"
        raise RuntimeError(msg)

    monkeypatch.setattr(compaction_logs, "read", broken)
    answer = get(LAST_30)
    assert answer.status_code == 500
    assert answer.json()["detail"] == "compaction report: RuntimeError: x"
    assert "RuntimeError: x" in caplog.text
