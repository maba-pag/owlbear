"""Where spend is recorded from and what OwlBear's other records add (D-01M5XCDF6G60VG5GHTWF5QSSDE)."""

from __future__ import annotations

import contextvars
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from owlbear_delivery_next.change_contracts.models import Change, Step, StepKind
from owlbear_delivery_next.change_contracts.spend import Spend
from owlbear_delivery_next.commands import runner
from owlbear_delivery_next.local_system import local_home
from owlbear_delivery_next.pack_runs import pack_job, pack_replay
from owlbear_delivery_next.project_host import metrics_routes
from owlbear_delivery_next.runtimes import chatlogs, spend_reconcile
from owlbear_delivery_next.state_store import spend_ledger, spend_metrics, spend_shares
from owlbear_delivery_next.state_store.spend_ledger import Where
from owlbear_delivery_next.state_store.store import Lock, Store

UTC_ZONE = ZoneInfo("UTC")


def used(spent: float, model: str = "m1") -> dict:
    return {"credits": spent, "models": {model: {"credits": spent, "input": 10, "output": 2}}}


def total() -> float:
    assert spend_ledger.WRITER.settled(5)
    return round(sum(p["credits"] or 0 for p in spend_shares.derive(spend_ledger.lines())), 6)


def test_a_runner_spends_for_its_project_change_and_step(change_repo, monkeypatch) -> None:
    store = Store.open(change_repo)
    with store.lock("c1") as lock:
        store.write(lock, Change(slug="c1", step=Step(kind=StepKind.BUILD)))
    seen = []
    monkeypatch.setattr(runner, "_step", lambda *_a: seen.append(spend_ledger.where()))
    contextvars.copy_context().run(runner.main, ["c1", "--repo", str(change_repo)])
    clone = store.root.name
    assert seen == [Where(project=clone, name=change_repo.name, clone=clone, change="c1", step="build")]


def test_design_pack_work_spends_for_the_project_that_started_it(tmp_path, monkeypatch) -> None:
    store, seen = Store(tmp_path / "abc", None, "shop"), []
    store.shared = SimpleNamespace()  # replay needs one; its work is replaced here
    monkeypatch.setattr(pack_replay, "_replay", lambda *_a: seen.append(spend_ledger.where()))
    pack_replay.replay(store)
    job = pack_job.Job(store)
    monkeypatch.setattr(job, "_steps", lambda _work: seen.append(spend_ledger.where()))
    monkeypatch.setattr(job, "_release", lambda: None)
    job._run(lambda: None)  # noqa: SLF001 - the job thread's own entry
    assert [(w.project, w.clone, w.job) for w in seen] == [
        ("shop", "abc", "design pack replay"), ("shop", "abc", "design pack update")
    ]  # fmt: skip


@pytest.fixture
def project(tmp_path) -> Store:
    """A project whose Change spent in three sessions: s1 with its event kept, s2 with its event dropped, and one
    report with no session."""
    store = Store(tmp_path / "projects" / "0123456789abcdef", None, "shop")
    spend = Spend().plus(used(3.0), "s1").plus(used(2.0, "m2"), "s2").plus({"credits": 0.5}, "")
    store.write(Lock("c1"), Change(slug="c1", spend=spend))
    store.log(Lock("c1"), "c1", {"event": "step", "at": "2026-10-20T10:00:00+00:00", "session": "s1", "kind": "build",
                                 "usage": used(3.0), "ending": "result"})  # fmt: skip
    return store


def test_earlier_spend_is_imported_once_as_a_union_never_twice(project) -> None:
    spend_ledger.started("live", "s1", agent="builder", job="", model="m1", before={})  # the race: live first
    spend_ledger.ended("live", "s1", usage=used(3.0), ending="result")
    assert spend_ledger.WRITER.settled(5)
    said = spend_reconcile.run([(project, None)])
    assert (said["state"], said["done"], said["sources"], said["imported"]["changes"]) == ("done", 3, 3, 3)
    assert total() == 5.5  # the Change's own total: s1 once, s2's mark and the residual
    kinds = {(line["type"], line.get("session")) for line in spend_ledger.lines() if line["type"] != "start"}
    assert kinds == {("end", "s1"), ("event", "s1"), ("mark", "s2"), ("residual", "residual:0123456789abcdef:c1")}
    again = spend_reconcile.run([(project, None)])
    assert again["imported"] == {"changes": 0, "spotter": 0, "logs": 0}
    pieces = spend_shares.derive(spend_ledger.lines())
    rest = next(p for p in pieces if p["kind"] == "run" and p["session"].startswith("residual:"))
    assert (rest["project"], rest["agent"], rest["lo"], rest["uncertain"]) == ("shop", "", None, ["agent", "at"])


def test_legacy_spotter_looks_are_measured_only_when_reported_and_named_by_their_project(project) -> None:
    folder = local_home.root() / "spotter"
    folder.mkdir()
    rec = {"project": project.root.name, "change": "c1", "step": "build", "model": "m1", "look": "hand-off"}
    looks = [
        rec | {"id": "a", "at": "2026-10-20T10:00:00+00:00", "credits": 0.5},  # the estimate: unknown
        rec | {"id": "b", "at": "2026-10-20T10:01:00+00:00", "credits": 0.07},
        rec | {"id": "c", "at": "2026-10-20T10:02:00+00:00", "credits": 0.0},  # skipped: no look ran
        rec | {"id": "d", "at": "2026-10-20T10:03:00+00:00", "credits": 0.3, "credits_known": False},
        rec | {"id": "e", "at": "2026-10-20T10:04:00+00:00", "credits": 0.2, "credits_known": True, "limit": 1.0,
               "stopped": "reached", "stopped_by": "look"},
    ]  # fmt: skip
    (folder / "records-2026-10-20.jsonl").write_text("".join(json.dumps(x) + "\n" for x in looks))
    spend_reconcile.run([(project, None)])
    found = {p["run"]: p for p in spend_shares.derive(spend_ledger.lines()) if p["session"].startswith("look:")}
    assert {k: (p["kind"], p["credits"]) for k, p in found.items()} == {
        "look:a": ("unknown", None), "look:b": ("run", 0.07), "look:d": ("unknown", None), "look:e": ("run", 0.2),
    }  # fmt: skip
    assert {(p["project"], p["name"], p["agent"], p["job"]) for p in found.values()} == {
        ("shop", "shop", "spotter", "hand-off look")
    }
    assert (found["look:e"]["stopped"], found["look:e"]["stopped_by"], found["look:e"]["limit"]) == (
        "reached",
        "look",
        1.0,
    )


def checkpoint(at: str, nano: float) -> str:
    snap = {"totalNanoAiu": nano, "modelMetrics": {"m1": {"totalNanoAiu": nano, "usage": {"inputTokens": 7,
            "outputTokens": 3}}}, "agentMetrics": {"main": {"totalNanoAiu": nano, "modelMetrics": {"m1": {
            "totalNanoAiu": nano, "usage": {"inputTokens": 7, "outputTokens": 3}}}}}}  # fmt: skip
    return json.dumps({"type": "session.usage_checkpoint", "timestamp": at, "data": {"accountingSnapshot": snap}})


def runtime_log(sid: str, *events: str) -> None:
    folder = Path.home() / ".copilot" / "session-state" / sid
    folder.mkdir(parents=True)
    (folder / "events.jsonl").write_text("".join(f"{e}\n" for e in ('{"type": "session.start"}', *events)))


def test_a_killed_run_and_sessions_the_ledger_never_saw_are_read_from_the_runtimes_log(project) -> None:
    long_ago = (datetime.now(UTC) - timedelta(hours=4)).isoformat(timespec="seconds")
    spend_ledger.append([{"id": "start:k", "type": "start", "run": "k", "at": long_ago, "session": "killed",
                          "agent": "builder", "before": {}, "project": "shop", "change": "c1"}])  # fmt: skip
    runtime_log("killed", checkpoint("2026-10-27T01:00:00.123Z", 1.5e9))
    curator = "memory-curation-shop-1a2b3c4d"
    runtime_log(curator, checkpoint("2026-10-26T09:00:00Z", 0.5e9), checkpoint("2026-10-26T09:05:00Z", 0.8e9))
    chatlogs.root().mkdir(parents=True)
    owner = {
        "event": "started",
        "session": curator,
        "kind": "review",
        "role": "curator",
        "job": "memory-curation",
        "worktree": "/var/folders/x/owlbear-curation-x",  # a recorded path, never opened
    }
    (chatlogs.root() / "manifest.jsonl").write_text(json.dumps(owner) + "\n")
    said = spend_reconcile.run([(project, None)])
    assert said["imported"]["logs"] == 2
    pieces = {p["run"]: p for p in spend_shares.derive(spend_ledger.lines()) if p["session"] in {"killed", curator}}
    killed = pieces["k"]
    assert (killed["kind"], killed["credits"], killed["ending"], killed["lo"], killed["source"]) == (
        "run", 1.5, "unconfirmed", "2026-10-27T01:00:00+00:00", "import:runtime-log"
    )  # fmt: skip
    [(rid, cur)] = [(k, p) for k, p in pieces.items() if k != "k"]
    assert (cur["project"], cur["agent"], cur["job"], cur["credits"], cur["lo"]) == (
        "shop", "curator", "memory-curation", 0.8, "2026-10-26T09:05:00+00:00"
    )  # fmt: skip
    assert spend_reconcile.run([(project, None)])["imported"]["logs"] == 0  # unchanged logs are not read again
    assert rid.startswith("log:")


def test_the_route_answers_the_page_validates_its_filters_and_reconciles_in_the_background(project) -> None:
    app = FastAPI()
    app.include_router(metrics_routes.router(lambda: [(project, None)]), prefix="/api/next")
    http = TestClient(app)
    for bad in ("tz=Mars/Base", "from=yesterday", "from=2026-10-02&to=2026-10-01", "by=colour", "cursor=-1"):
        assert http.get(f"/api/next/metrics?{bad}").status_code == 422, bad
    first = http.get("/api/next/metrics?tz=Europe/Berlin&by=project").json()
    assert first["coverage"]["reconcile"]["state"] in {"never", "running", "done"}
    assert spend_reconcile.settled(10)
    assert spend_ledger.WRITER.settled(5)
    done = http.get("/api/next/metrics?tz=Europe/Berlin&by=project").json()
    assert done["coverage"]["reconcile"]["state"] == "done"
    assert [(r["label"], r["credits"]) for r in done["rows"]] == [("shop", 5.5)]
    assert spend_reconcile.settled(10)
    assert done["choices"]["clones"] == {"0123456789abcdef": "shop"}
    assert spend_metrics.query([], tz=UTC_ZONE)["totals"]["credits"] == 0


def test_a_live_look_and_its_spotter_record_are_counted_once_whatever_their_times(project) -> None:
    """Sol's counterexample: the record is made before its look's runtime starts, so a time cutoff counted 0.2 twice."""
    folder = local_home.root() / "spotter"
    folder.mkdir()
    rec = {"id": "x", "at": "2026-10-27T10:00:00+00:00", "credits": 0.2, "project": project.root.name, "model": "m1"}
    (folder / "records-2026-10-27.jsonl").write_text(json.dumps(rec) + "\n")
    place = Where(project="shop", name="shop")
    spend_ledger.started("L", "look-sdk-1", agent="spotter", job="look", model="m1", before={}, place=place, look="x")
    spend_ledger.ended("L", "look-sdk-1", usage=used(0.2), ending="finished", place=place, look="x")
    assert spend_ledger.WRITER.settled(5)
    assert spend_reconcile.run([(project, None)])["imported"]["spotter"] == 0
    looks = [p for p in spend_shares.derive(spend_ledger.lines()) if p["role"] == "spotter"]
    assert [(p["run"], p["credits"]) for p in looks] == [("L", 0.2)]


def test_a_runtime_log_whose_lines_could_not_be_written_is_read_again(project, monkeypatch) -> None:
    """Sol's counterexample: the log's fingerprint was kept although its line was not, so no pass appended it."""
    long_ago = (datetime.now(UTC) - timedelta(hours=4)).isoformat(timespec="seconds")
    spend_ledger.append([{"id": "start:k", "type": "start", "run": "k", "at": long_ago, "session": "killed",
                          "agent": "builder", "before": {}, "project": "shop"}])  # fmt: skip
    runtime_log("killed", checkpoint("2026-10-27T01:00:00Z", 1.5e9))
    real = spend_ledger.append

    def failing(lines: list[dict]) -> list[dict]:
        return lines if any(x.get("source") == "import:runtime-log" for x in lines) else real(lines)

    monkeypatch.setattr(spend_ledger, "append", failing)
    first = spend_reconcile.run([(project, None)])
    assert (first["imported"].get("logs", 0), first["errors"]) == (0, ["logs: 1 line(s) not written"])
    monkeypatch.setattr(spend_ledger, "append", real)
    assert spend_reconcile.run([(project, None)])["imported"]["logs"] == 1
    assert [p["credits"] for p in spend_shares.derive(spend_ledger.lines()) if p["run"] == "k"] == [1.5]
