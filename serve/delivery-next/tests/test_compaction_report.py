"""Metrics' compaction report (C-03): per role, how often and how early its sessions compacted, from known logs."""

from __future__ import annotations

import gzip
import json
import logging
import re
import socket
import subprocess
import threading
import time
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from urllib.parse import quote

import pytest
import uvicorn
from fastapi import FastAPI
from fastapi.testclient import TestClient

from owlbear_delivery_next.change_contracts.models import Change, Step, StepKind
from owlbear_delivery_next.improvement import chatlogs
from owlbear_delivery_next.local_system import codebase, data_place
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.machine_host import app, project
from owlbear_delivery_next.machine_host.machine import Machine
from owlbear_delivery_next.project_host import metrics_routes
from owlbear_delivery_next.project_host.host import Host, HostRecord
from owlbear_delivery_next.runtimes import compaction_logs, spend_reconcile
from owlbear_delivery_next.settings import config
from owlbear_delivery_next.settings.config import Agent, GlobalLayer, Layer, MachineLayer
from owlbear_delivery_next.state_store import registry, spend_ledger
from owlbear_delivery_next.state_store.store import Store, update_layer

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from playwright.sync_api import Page

NOW = datetime.now(UTC).replace(microsecond=0) - timedelta(hours=1)
OLD = NOW - timedelta(days=40)
LAST_30 = f"from={(NOW - timedelta(days=30)).date()}&to={(NOW + timedelta(days=2)).date()}"
NONE = "\u2013"  # the en dash a cell without a value shows
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


def seed(*, b1_unread: bool = False, shop: dict = SHOP, mill: dict = MILL) -> None:
    """The plan's fixture: shop's and mill's builder sessions, shop's reviewer and the machine's retro."""
    b1r = used(1.0)
    spend_ledger.append([
        *ran("b1r", OLD, shop, usage=b1r, session="s-b1", before={}),
        *ran("b1", NOW, shop, usage=used(3.0, x1=("explore", 0.5), x2=("explore", 0.5)), session="s-b1",
             before=None if b1_unread else b1r),
        *ran("b2", NOW, shop, usage=used(1.0, "m2"), before={}),
        *ran("b6", NOW, shop, usage=used(1.0), before={}),
        *ran("rv", NOW, shop | {"agent": "reviewer", "change": "c1"}, usage=used(0.5), stopped="reached", before={}),
        *ran("b3", NOW, mill, usage=used(1.0), before={}),
        *ran("b4", NOW, mill, usage=used(1.0), before={}),
        *ran("b7", NOW, mill, usage=used(1.0), before={}),
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


def context(path, model: type[Layer], role: str, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    update_layer(path, model, lambda layer: layer.model_copy(update={"agents": {role: Agent(context=value)}}))


def unset_reviewer(monkeypatch) -> None:
    """The reviewer's context is set on no layer, the tests' base layer included."""
    base = config.BASE
    assert base is not None
    agents = base.agents | {"reviewer": base.agents["reviewer"].model_copy(update={"context": None})}
    monkeypatch.setattr(config, "BASE", base.model_copy(update={"agents": agents}))


@pytest.fixture
def served(tmp_path, monkeypatch) -> list[tuple[str, Store]]:
    """Shop and mill on a shared location: builder long on Global, default on mill; retro long on this machine."""
    unset_reviewer(monkeypatch)
    shared = DataRepo(tmp_path / "data")
    stores = [(name, Store(tmp_path / "projects" / name, shared, name)) for name in ("shop", "mill")]
    context(shared.global_path, GlobalLayer, "builder", "long")
    context(stores[1][1].config_path, Layer, "builder", "default")
    context(stores[0][1].machine_path, MachineLayer, "retro", "long")
    return stores


@pytest.fixture
def get(monkeypatch, request):
    monkeypatch.setattr(spend_reconcile, "due", lambda *_a: False)  # the ledger holds only the fixture's lines
    stores = request.getfixturevalue("served") if "served" in request.fixturenames else []
    app = FastAPI()
    app.include_router(metrics_routes.router(list, lambda: stores), prefix="/api/next")
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


def links(answer: dict) -> dict[tuple, list]:
    return {(r["agent"], r["subagent"], r["project"]): r["settings"] for r in answer["rows"]}


def at(project: str, layer: str, **more: object) -> dict:
    return {"project": project, "name": project, "clone": project, "layer": layer} | more


@pytest.mark.usefixtures("served")
def test_each_row_links_its_roles_context_setting_on_the_layer_that_sets_it(get) -> None:
    seed()
    found = get(LAST_30).json()["compaction"]
    assert links(found) == {
        ("builder", "", None): [at("mill", "project"), at("shop", "global")],
        ("builder", "", "mill"): [at("mill", "project")],
        ("builder", "", "shop"): [at("shop", "global")],
        ("builder", "explore", "shop"): [],
        ("retro", "", ""): [{"project": "", "name": "This machine", "clone": "shop", "layer": "machine"}],
        ("reviewer", "", "shop"): [at("shop", "global", unset=True)],
    }
    assert found["settings_errors"] == []


def test_a_project_whose_settings_do_not_read_says_so_and_the_others_still_link(served, get, caplog) -> None:
    seed()
    mill = served[1][1].config_path
    mill.write_bytes(b"\xff\xfe not utf-8")
    found = get(LAST_30).json()["compaction"]
    said = links(found)
    assert said["builder", "", "mill"] == [{"project": "mill", "name": "mill", "why": "settings unreadable"}]
    assert said["builder", "", "shop"] == [at("shop", "global")]
    [error] = found["settings_errors"]
    assert (error["project"], error["file"]) == ("mill", str(mill))
    assert "UnicodeDecodeError" in error["error"]
    assert "settings of mill unreadable" in caplog.text


def test_a_row_of_a_project_this_machine_does_not_serve_says_so(get) -> None:
    seed()
    said = links(get(LAST_30).json()["compaction"])
    assert said["builder", "", "shop"] == [{"project": "shop", "name": "shop", "why": "not served"}]
    assert said["retro", "", ""] == [{"project": "", "name": "This machine", "why": "no project served"}]


def clone(path: Path) -> Path:
    for args in (["init", "-q", str(path)], ["-C", str(path), "commit", "-q", "--allow-empty", "-m", "i"]):
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], check=True)  # noqa: S603, S607
    store = Store.open(path)
    with store.lock(f"{path.name}-1") as lock:
        store.write(lock, Change(slug=f"{path.name}-1", step=Step(kind=StepKind.BUILD)))
    return path.resolve()


@contextmanager
def hosted(tmp_path: Path, monkeypatch, pds, shared: Path) -> Iterator[tuple[Page, str, str, str, list[str]]]:
    """The fixture's sessions and settings on registered clones shop and mill, a machine host serving them and a
    Chromium page reaching only it; the page, the host's address, shop's and mill's ids and the page's errors."""
    from playwright.sync_api import Error, sync_playwright  # noqa: PLC0415 - the optional browser runtime

    monkeypatch.setenv(data_place.VIEW, str(shared))
    monkeypatch.setattr(spend_reconcile, "due", lambda *_a: False)  # the ledger holds only the fixture's lines
    monkeypatch.setattr(project.readiness, "ready", lambda _store, _repo, **_kwargs: [])
    monkeypatch.setattr(Host, "_launch", lambda _self, _slug: False)
    unset_reviewer(monkeypatch)
    shop, mill = (registry.register(clone(tmp_path / name)) for name in ("shop", "mill"))
    stores = [Store.open(tmp_path / name) for name in ("shop", "mill")]
    assert [s.name for s in stores] == ["shop", "mill"]
    context(stores[0].global_path, GlobalLayer, "builder", "long")
    context(stores[1].config_path, Layer, "builder", "default")
    context(stores[0].machine_path, MachineLayer, "retro", "long")
    seed(shop=SHOP | {"clone": shop.id}, mill=MILL | {"clone": mill.id})
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    base = f"http://127.0.0.1:{sock.getsockname()[1]}"
    record = HostRecord(url=f"{base}/", token="t", pid=1, started_at=datetime.now(UTC), code=codebase.CURRENT)  # noqa: S106
    machine = Machine(record)
    machine.load_all()
    server = uvicorn.Server(uvicorn.Config(app.create(machine), log_level="warning", timeout_keep_alive=60))
    threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True).start()
    while not server.started:
        time.sleep(0.05)
    try:
        with sync_playwright() as pw:
            try:
                browser = pw.chromium.launch()
            except Error as exc:
                pytest.skip(f"no Playwright Chromium: {exc}")
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            pds.only(page, base)
            errors: list[str] = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
            page.goto(f"{base}/metrics#token=t")
            yield page, base, shop.id, mill.id, errors
            browser.close()
    finally:
        server.should_exit = True
        machine.stop_all()


def shown(page: Page) -> list[list[str]]:
    """The compaction table's rows as shown, but for their links: agent, project, sessions to earliest."""
    return page.locator("#compaction-table p-table-row").evaluate_all(
        "rows => rows.map(r => [...r.querySelectorAll('p-table-cell')].slice(0, 7)"
        ".map(c => c.textContent.replace(/\\s+/g, ' ').trim()))"
    )


def returned(page: Page, pds, left: str) -> None:
    """Back on Metrics at the address *left* with the compaction section focused and every filter as it was."""
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    expect(page).to_have_url(f"{left}#compaction")
    expect(page.locator("#compaction-title")).to_be_focused()
    query = {"period": "30", "by": "agent"} | dict(p.split("=", 1) for p in left.split("?", 1)[1].split("&"))
    filters = page.get_by_role("group", name="Show only")
    for label, key in (("Period", "period"), ("Project", "in"), ("Agent", "agent"), ("Model", "model"),
                       ("Change", "change"), ("Split by", "by")):  # fmt: skip
        expect(pds.select(filters, label)).to_have_js_property("value", query.get(key, "").replace("%2F", "/"))
    if "from" in query:
        expect(page.locator("#from")).to_have_js_property("value", query["from"])
        expect(page.locator("#to")).to_have_js_property("value", query["to"])
    expect(page.locator("#stopped")).to_have_js_property("checked", query.get("stopped") == "1")


def setting_link(page: Page, row: str):
    return page.locator(f"#set-agents-{row}").get_by_role("link", name="Compaction on Metrics")


@pytest.mark.browser
def test_metrics_shows_each_roles_compaction_and_its_setting_leads_back_with_the_filters(
    tmp_path: Path, monkeypatch, pds, shared_repo
) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    with hosted(tmp_path, monkeypatch, pds, shared_repo[0]) as (page, base, shop, mill, errors):
        page.goto(f"{base}/metrics?period=30&in=")
        expect(page.locator("#compaction-table p-table-row")).to_have_count(6)
        assert shown(page) == [
            ["builder", "All projects", "6 · 1 without a log · 1 unreadable", "3 of 4 (75%)", "4",
             "40% of its model calls", "20%"],
            ["builder", "mill", "3 · 1 unreadable", "1 of 2 (50%)", "1", "90% of its model calls", "90%"],
            ["builder", "shop", "3 · 1 without a log", "2 of 2 (100%)", "3", "30% of its model calls", "20%"],
            ["explore (subagent of builder)", "shop", "2", "1 of 2 (50%)", "1", "40% of its model calls", "40%"],
            ["retro", "This machine", "1", "1 of 1 (100%)", "1", "20% of its model calls", "20%"],
            ["reviewer", "shop", "1", "0 of 1 (0%)", "0", NONE, NONE],
        ]  # fmt: skip
        table = page.locator("#compaction-table")
        expect(table.locator("p-table-row").nth(3).locator("p-table-cell").last).to_have_text(NONE)
        retro = table.get_by_role("link", name="This machine, retro's context setting")
        assert f"project={shop}&layer=machine" in (retro.get_attribute("href") or "")
        expect(page.locator("#compaction-errors")).to_contain_text("Could not read the log of session s-b7 (mill)")

        page.goto(f"{base}/metrics?period=custom&from={(NOW - timedelta(days=3)).date()}"
                  f"&to={(NOW + timedelta(days=2)).date()}&in=shop&agent=reviewer&model=m1&change=shop%2Fc1"
                  "&stopped=1&by=day")  # fmt: skip
        expect(page.locator("#compaction-table p-table-row")).to_have_count(1)
        left = page.url
        table.get_by_role("link", name="shop: Global (unset), reviewer's context setting").click()
        expect(page.locator("#set-agents-reviewer :focus")).not_to_have_count(0)  # its first control
        assert page.url.startswith(f"{base}/config?project={shop}&layer=global&back=")
        expect(pds.select(page, "Layer")).to_have_js_property("value", "global")
        pds.pick(page, "Layer", "machine")
        setting_link(page, "reviewer").click()
        returned(page, pds, left)

        page.goto(f"{base}/metrics?in=&agent=builder")
        expect(page.locator("#compaction-table p-table-row")).to_have_count(3)  # explore is an agent of its own
        left = page.url
        table.get_by_role("link", name="mill: project layer, builder's context setting").last.click()
        expect(page.locator("#set-agents-builder :focus")).not_to_have_count(0)  # its first control
        expect(pds.select(page, "Layer")).to_have_js_property("value", "project")
        expect(pds.select(page, "Layer").locator('p-select-option[value="project"]')).to_have_text("Project mill")
        setting_link(page, "builder").click()
        returned(page, pds, left)
        table.locator("p-table-row").first.get_by_role("link", name="shop: Global, builder's context setting").click()
        expect(pds.select(page, "Layer")).to_have_js_property("value", "global")
        assert f"project={shop}&" in page.url
        setting_link(page, "builder").click()
        returned(page, pds, left)
        page.locator("#split").get_by_role("button", name="Show only builder").click()  # the drill still filters
        expect(page).to_have_url(re.compile(r"agent=builder"))
        expect(page.locator("#compaction-table p-table-row")).to_have_count(3)  # explore is an agent of its own

        page.goto(f"{base}/config?project={mill}#agents")
        expect(setting_link(page, "builder")).to_have_attribute(
            "href", f"/metrics?project={mill}&in=mill&agent=builder#compaction"
        )
        pds.pick(page, "Layer", "machine")
        expect(setting_link(page, "builder")).to_have_attribute(
            "href", f"/metrics?project={mill}&agent=builder&in=#compaction"
        )
        assert errors == []

        page.route("**/api/next/metrics?*", lambda route: route.abort())
        setting_link(page, "builder").click()
        expect(page.locator("#error")).to_be_visible()
        expect(page).to_have_url(f"{base}/metrics?project={mill}&agent=builder&in=#compaction")


@pytest.mark.browser
def test_settings_keep_unsaved_edits_and_go_back_only_to_this_hosts_metrics(
    tmp_path: Path, monkeypatch, pds, shared_repo
) -> None:
    from playwright.sync_api import expect  # noqa: PLC0415 - the optional browser runtime

    with hosted(tmp_path, monkeypatch, pds, shared_repo[0]) as (page, base, shop, _mill, errors):
        fallback = f"/metrics?project={shop}&in=shop&agent=builder#compaction"
        for away in ("https://evil.example/metrics", "/config", "https://["):
            page.goto(f"{base}/config?project={shop}&back={quote(away, safe='')}#agents")
            expect(setting_link(page, "builder")).to_have_attribute("href", fallback)
        page.goto(f"{base}/config?project={shop}&back={quote('/metrics?in=&agent=builder#compaction', safe='')}#runs")
        page.get_by_label("Rounds at most, builder").fill("4")
        pds.group(page, "agents")
        setting_link(page, "builder").click()
        expect(page.locator("#machine > [role=alert]")).to_have_text(
            "Save or discard your edits before you leave this page."
        )
        assert page.url.startswith(f"{base}/config?")
        expect(setting_link(page, "builder")).to_have_attribute("href", "/metrics?in=&agent=builder#compaction")
        assert errors == []
