"""Where spend is recorded from and what OwlBear's other records add (D-01M5XCDF6G60VG5GHTWF5QSSDE)."""

from __future__ import annotations

import contextvars
import json
import threading
from datetime import UTC, date, datetime, timedelta
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
from owlbear_delivery_next.runtimes import chatlogs, sdk_spend, spend_reconcile, subagents
from owlbear_delivery_next.runtimes.session_result import Run
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
        rec | {"id": "f", "at": "2026-10-20T10:05:00+00:00", "credits": 0.0, "credits_known": True,
               "sdk_sessions": ["s-f"]},  # a session that cost nothing is still a run
        rec | {"id": "g", "at": "2026-10-20T10:06:00+00:00", "credits": 0.0, "credits_known": True,
               "stopped": "reached", "stopped_by": "retro-run"},  # refused by its run's limit: no session
    ]  # fmt: skip
    (folder / "records-2026-10-20.jsonl").write_text("".join(json.dumps(x) + "\n" for x in looks))
    spend_reconcile.run([(project, None)])
    found = {p["run"]: p for p in spend_shares.derive(spend_ledger.lines()) if p["session"].startswith("look:")}
    assert {k: (p["kind"], p["credits"]) for k, p in found.items()} == {
        "look:a": ("unknown", None), "look:b": ("run", 0.07), "look:d": ("unknown", None), "look:e": ("run", 0.2),
        "look:f": ("run", 0.0),
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


def shutdown(at: str, nano: float) -> str:
    snap = json.loads(checkpoint(at, nano))["data"]["accountingSnapshot"]
    return json.dumps({"type": "session.shutdown", "timestamp": at, "data": {"accountingSnapshot": snap,
                       "totalNanoAiu": nano, "shutdownType": "routine"}})  # fmt: skip


def runtime_log(sid: str, *events: str) -> None:
    folder = Path.home() / ".copilot" / "session-state" / sid
    folder.mkdir(parents=True)
    (folder / "events.jsonl").write_text("".join(f"{e}\n" for e in ('{"type": "session.start"}', *events)))


def logged(sid: str, *events: str) -> None:
    """More of the runtime's log of *sid*, as it writes on."""
    with (Path.home() / ".copilot" / "session-state" / sid / "events.jsonl").open("a") as f:
        f.write("".join(f"{e}\n" for e in events))


def run_piece(rid: str) -> tuple[float | None, bool, str]:
    """A run's credits over its pieces, whether any is a lower bound, and its first piece's kind."""
    assert spend_ledger.WRITER.settled(5)
    pieces = [p for p in spend_shares.derive(spend_ledger.lines()) if p["run"] == rid]
    spent = None if any(p["credits"] is None for p in pieces) else round(sum(p["credits"] for p in pieces), 6)
    return spent, any(p["incomplete"] for p in pieces), pieces[0]["kind"]


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


def step(usage: dict, *, billed: dict | None = None, ending: str = "result", limit: float | None = None):
    """A step's state as its teardown finds it: the usage Delivery's model check proved, and how it ended."""
    said: list[str] = []
    run = Run("s1", ending=ending, usage=usage, model_check="verified")

    def wrong(detail: str) -> None:
        said.append(detail)
        run.model_check, run.ending = "mismatch", "error"

    cfg = SimpleNamespace(model="m1", credit_limit=limit)
    st = SimpleNamespace(run=run, billed=billed if billed is not None else {}, cfg=cfg, spent={},
                         watch=subagents.Watch(allowed=True), gate=SimpleNamespace(wrong_model=wrong))  # fmt: skip
    return st, said


def tokens(**models: int) -> dict:
    return {"credits": float(sum(models.values())) / 10,
            "models": {m: {"credits": n / 10, "tokens": n} for m, n in models.items()}}  # fmt: skip


def test_a_final_read_where_another_model_grew_is_a_wrong_model_even_if_it_billed_before() -> None:
    """Sol's counterexample: a historical foreign model growing only in the final read stayed verified."""
    st, said = step(tokens(m1=10, other=5), billed=tokens(m1=2, other=5))
    sdk_spend.final(st, tokens(m1=12, other=7))
    assert (st.run.model_check, st.run.ending, said) == (
        "mismatch",
        "error",
        ["the usage names other, the step needs m1"],
    )
    assert st.spent == tokens(m1=12, other=7)  # the ledger still records every credit


def test_a_limit_reached_only_by_the_final_read_is_the_runs_stop() -> None:
    """Sol's counterexample: earlier 1 of a limit of 2, ending no-result; the final 2 was adopted without a stop."""
    st, _ = step(tokens(m1=10), ending="no-result", limit=2.0)
    sdk_spend.final(st, tokens(m1=20))
    assert (st.run.ending, st.run.usage["credits"], st.run.model_check) == ("credit-limit", 2.0, "verified")


def test_a_failed_final_read_keeps_the_proof_and_marks_the_ledgers_sample_incomplete(project) -> None:
    """Sol's counterexample: the earlier sample stood in as fully known; now it is a lower bound, completed later."""
    st, _ = step(tokens(m1=10))
    sdk_spend.final(st, {"error": "TimeoutError"})
    assert (st.run.usage, st.spent) == (tokens(m1=10), tokens(m1=10) | {"incomplete": "TimeoutError"})
    spend_ledger.started("r", "partial", agent="builder", job="", model="m1", before={})
    spend_ledger.ended("r", "partial", usage=st.spent, ending="result")
    assert spend_ledger.WRITER.settled(5)
    [piece] = [p for p in spend_shares.derive(spend_ledger.lines()) if p["run"] == "r"]
    assert (piece["credits"], piece["incomplete"]) == (1.0, True)
    runtime_log("partial", checkpoint("2026-10-27T01:00:00Z", 1.5e9))
    assert spend_reconcile.run([(project, None)])["imported"]["logs"] == 1
    [piece] = [p for p in spend_shares.derive(spend_ledger.lines()) if p["run"] == "r"]
    assert (piece["credits"], piece["incomplete"], piece["source"]) == (1.5, True, "import:runtime-log")


def test_a_look_finishing_while_a_pass_scans_is_counted_once(project, monkeypatch) -> None:
    """Sol's counterexample: the pass checked look ids against its first snapshot only, so a look ending meanwhile
    was imported from its Spotter record too."""
    folder = local_home.root() / "spotter"
    folder.mkdir()
    rec = {
        "id": "x",
        "at": "2026-10-27T10:00:00+00:00",
        "credits": 0.2,
        "credits_known": True,
        "limit": 1.0,
        "stopped": "",
        "stopped_by": "",
        "sdk_sessions": ["look-sdk"],
        "project": project.root.name,
        "model": "m1",
    }
    (folder / "records-2026-10-27.jsonl").write_text(json.dumps(rec) + "\n")
    real = spend_ledger.lines

    def snapshot_then_look_ends() -> list[dict]:
        seen = real()
        place = Where(project="shop", name="shop")
        spend_ledger.started("L", "look-sdk", agent="spotter", job="look", model="m1", before={}, place=place, look="x")
        spend_ledger.ended("L", "look-sdk", usage=used(0.2), ending="finished", place=place, look="x")
        assert spend_ledger.WRITER.settled(5)
        return seen

    monkeypatch.setattr(spend_reconcile.spend_ledger, "lines", snapshot_then_look_ends)
    assert spend_reconcile.run([(project, None)])["imported"]["spotter"] == 1  # it could not know yet
    monkeypatch.setattr(spend_reconcile.spend_ledger, "lines", real)
    looks = [p for p in spend_shares.derive(spend_ledger.lines()) if p["role"] == "spotter"]
    assert [(p["run"], p["credits"]) for p in looks] == [("L", 0.2)]


def test_two_passes_at_once_import_each_line_once(project, monkeypatch) -> None:
    """Reconciliation running concurrently: a second pass while one runs does nothing, and the totals stay right."""
    real, entered, release = spend_reconcile._changes, threading.Event(), threading.Event()  # noqa: SLF001

    def slow(*args: object) -> list[dict]:
        entered.set()
        release.wait(5)
        return real(*args)

    monkeypatch.setattr(spend_reconcile, "_changes", slow)
    results: list[dict] = []
    first = threading.Thread(target=lambda: results.append(spend_reconcile.run([(project, None)])))
    first.start()
    assert entered.wait(5)
    second = spend_reconcile.run([(project, None)])  # the first holds the machine's pass lock
    assert second["state"] == "running"
    release.set()
    first.join(10)
    assert results[0]["imported"]["changes"] == 3
    assert spend_reconcile.run([(project, None)])["imported"] == {"changes": 0, "spotter": 0, "logs": 0}
    assert total() == 5.5


def test_a_pass_during_a_looks_retry_counts_each_session_once_and_the_look_once(project, monkeypatch) -> None:
    """A pass reads the ledger while a look's retry is live: its first session's lines are in, its second's arrive
    while the pass reads the Spotter records, whose record already names both. The record is imported, yet the look
    counts as its two sessions, once each, never again as its record."""
    place = Where(project="shop", name="shop")
    spend_ledger.started("A", "look-a", agent="spotter", job="look", model="m1", before={}, place=place, look="x")
    spend_ledger.ended("A", "look-a", usage=used(0.1), ending="finished", place=place, look="x")
    assert spend_ledger.WRITER.settled(5)
    folder = local_home.root() / "spotter"
    folder.mkdir()
    rec = {"id": "x", "at": "2026-10-27T10:00:00+00:00", "credits": 0.4, "credits_known": True, "limit": 1.0,
           "stopped": "", "stopped_by": "", "sdk_sessions": ["look-a", "look-b"], "project": project.root.name,
           "model": "m1"}  # fmt: skip
    (folder / "records-2026-10-27.jsonl").write_text(json.dumps(rec) + "\n")
    real = spend_ledger.lines

    def snapshot_then_retry_ends() -> list[dict]:
        seen = real()
        spend_ledger.started("B", "look-b", agent="spotter", job="look", model="m1", before={}, place=place, look="x")
        spend_ledger.ended("B", "look-b", usage=used(0.3), ending="finished", place=place, look="x")
        assert spend_ledger.WRITER.settled(5)
        return seen

    monkeypatch.setattr(spend_reconcile.spend_ledger, "lines", snapshot_then_retry_ends)
    assert spend_reconcile.run([(project, None)])["imported"]["spotter"] == 1  # look-b's lines came after its read
    monkeypatch.setattr(spend_reconcile.spend_ledger, "lines", real)
    assert spend_reconcile.run([(project, None)])["imported"]["spotter"] == 0
    looks = [p for p in spend_shares.derive(spend_ledger.lines()) if p["role"] == "spotter"]
    assert sorted((p["run"], p["session"], p["credits"]) for p in looks) == [("A", "look-a", 0.1), ("B", "look-b", 0.3)]
    assert total() == 5.5 + 0.4  # the project's Change and the look


def test_a_look_still_running_during_a_pass_is_never_imported_from_a_record(project) -> None:
    """A live look has no record yet, and its finished first session's lines cover nothing the pass could import."""
    place = Where(project="shop", name="shop")
    spend_ledger.started("A", "look-a", agent="spotter", job="look", model="m1", before={}, place=place, look="x")
    spend_ledger.ended("A", "look-a", usage=used(0.1), ending="finished", place=place, look="x")
    spend_ledger.started("B", "look-b", agent="spotter", job="look", model="m1", before={}, place=place, look="x")
    assert spend_ledger.WRITER.settled(5)
    assert spend_reconcile.run([(project, None)])["imported"]["spotter"] == 0
    spend_ledger.ended("B", "look-b", usage=used(0.3), ending="finished", place=place, look="x")
    folder = local_home.root() / "spotter"
    folder.mkdir()
    rec = {"id": "x", "at": "2026-10-27T10:00:00+00:00", "credits": 0.4, "credits_known": True,
           "sdk_sessions": ["look-a", "look-b"], "project": project.root.name, "model": "m1"}  # fmt: skip
    (folder / "records-2026-10-27.jsonl").write_text(json.dumps(rec) + "\n")
    assert spend_ledger.WRITER.settled(5)
    assert spend_reconcile.run([(project, None)])["imported"]["spotter"] == 0
    looks = [p for p in spend_shares.derive(spend_ledger.lines()) if p["role"] == "spotter"]
    assert sorted((p["run"], p["credits"]) for p in looks) == [("A", 0.1), ("B", 0.3)]


def test_a_run_whose_initial_and_final_reads_failed_is_recovered_from_its_runtimes_log(project) -> None:
    """Sol's counterexample: only usage marked incomplete was recovered, so an unread end stayed unknown for good."""
    spend_ledger.started("r", "unread", agent="builder", job="", model="m1", before=None)
    spend_ledger.ended("r", "unread", usage={"error": "TimeoutError"}, ending="result")
    assert run_piece("r") == (None, False, "unknown")
    chatlogs.root().mkdir(parents=True)  # Retro's manifest names the session too: it is left to its run
    (chatlogs.root() / "manifest.jsonl").write_text(json.dumps({"event": "started", "session": "unread",
                                                                 "kind": "build", "job": ""}) + "\n")  # fmt: skip
    runtime_log("unread", checkpoint("2026-10-27T01:00:00Z", 2e9))
    assert spend_reconcile.run([(project, None)])["imported"]["logs"] == 1
    assert run_piece("r") == (2.0, True, "run")  # its run, provisional: the session never said it shut down
    assert total() == 5.5 + 2.0


def test_later_checkpoints_raise_a_correction_until_the_session_shuts_down(project) -> None:
    """Sol's counterexample: every correction had one id, so checkpoints of 2 then 3 left 2, marked complete."""
    spend_ledger.started("r", "growing", agent="builder", job="", model="m1", before={})
    spend_ledger.ended("r", "growing", usage=used(1.0) | {"incomplete": "TimeoutError"}, ending="result")
    runtime_log("growing", checkpoint("2026-10-27T01:00:00Z", 2e9))
    assert spend_reconcile.run([(project, None)])["imported"]["logs"] == 1
    assert run_piece("r") == (2.0, True, "run")
    logged("growing", checkpoint("2026-10-27T01:01:00Z", 3e9))  # the runtime was still stopping
    assert spend_reconcile.run([(project, None)])["imported"]["logs"] == 1
    assert run_piece("r") == (3.0, True, "run")
    assert spend_reconcile.run([(project, None)])["imported"]["logs"] == 0  # unchanged: not read again
    logged("growing", shutdown("2026-10-27T01:02:00Z", 3e9))
    assert spend_reconcile.run([(project, None)])["imported"]["logs"] == 1
    assert run_piece("r") == (3.0, False, "run")  # final now
    logged("growing", checkpoint("2026-10-27T01:03:00Z", 3e9))
    assert spend_reconcile.run([(project, None)])["imported"]["logs"] == 0  # a final run is not revisited
    assert run_piece("r") == (3.0, False, "run")


def test_a_correction_never_lowers_a_run_and_a_final_tie_beats_a_provisional_one() -> None:
    def end(usage: dict, n: int) -> dict:
        return {"id": f"end:r:{n}", "type": "end", "run": "r", "session": "s", "usage": usage}

    start = {"id": "start:r", "type": "start", "run": "r", "session": "s", "at": "2026-10-27T01:00:00+00:00"}
    lines = [start, end(used(3.0) | {"incomplete": "checkpoint"}, 1), end(used(2.0), 2), end({"error": "x"}, 3)]
    [run] = spend_shares.runs(lines)
    assert run["usage"] == used(3.0) | {"incomplete": "checkpoint"}
    [run] = spend_shares.runs([*lines, end(used(3.0), 4), end(used(3.0) | {"incomplete": "checkpoint"}, 5)])
    assert run["usage"] == used(3.0)


def test_a_recorded_end_after_log_checkpoints_dates_the_run_alone() -> None:
    def end(n: int, spent: float, at: str, **more: object) -> dict:
        return {"id": f"end:r:{n}", "type": "end", "run": "r", "session": "s", "at": at, "usage": used(spent)} | more

    start = {"id": "start:r", "type": "start", "run": "r", "session": "s", "at": "2026-10-01T20:00:00+00:00",
             "before": {}}  # fmt: skip
    log = {"source": "import:runtime-log", "ending": "unconfirmed"}
    first = end(1, 1.0, "2026-10-01T23:00:00+00:00", **log) | {"usage": used(1.0) | {"incomplete": "checkpoint"}}
    second = end(2, 2.0, "2026-10-02T01:00:00+00:00", **log) | {"usage": used(2.0) | {"incomplete": "checkpoint"}}
    assert len(spend_shares.runs([start, first, second])) == 2  # the run and its later checkpoint's continuation
    [run] = spend_shares.runs([start, first, second, end(3, 2.5, "2026-10-02T02:00:00+00:00", ending="result")])
    assert (run["at"], run["usage"], run["ending"]) == ("2026-10-02T02:00:00+00:00", used(2.5), "result")
    [piece] = spend_shares.derive([start, first, second, end(3, 1.5, "2026-10-02T02:00:00+00:00", ending="result")])
    assert (piece["credits"], piece["incomplete"], piece["lo"]) == (2.0, True, "2026-10-02T02:00:00+00:00")


def test_a_killed_run_and_a_logged_session_are_read_again_when_their_logs_grow(project) -> None:
    long_ago = (datetime.now(UTC) - timedelta(hours=4)).isoformat(timespec="seconds")
    spend_ledger.append([{"id": "start:k", "type": "start", "run": "k", "at": long_ago, "session": "killed",
                          "agent": "builder", "before": {}, "project": "shop"}])  # fmt: skip
    runtime_log("killed", checkpoint("2026-10-27T01:00:00Z", 1e9))
    runtime_log("solo", checkpoint("2026-10-27T01:00:00Z", 0.5e9))
    chatlogs.root().mkdir(parents=True)
    solo = {"event": "started", "session": "solo", "kind": "review", "role": "curator"}
    (chatlogs.root() / "manifest.jsonl").write_text(json.dumps(solo) + "\n")
    assert spend_reconcile.run([(project, None)])["imported"]["logs"] == 2
    assert (run_piece("k"), run_piece("log:solo")) == ((1.0, True, "run"), (0.5, True, "run"))
    logged("killed", shutdown("2026-10-27T01:05:00Z", 1.2e9))
    logged("solo", checkpoint("2026-10-27T01:05:00Z", 0.9e9))
    assert spend_reconcile.run([(project, None)])["imported"]["logs"] == 2
    assert (run_piece("k"), run_piece("log:solo")) == ((1.2, False, "run"), (0.9, True, "run"))
    assert total() == 7.6  # the project's Change, the killed run and the logged session


def test_a_pass_during_a_looks_teardown_stays_provisional_until_its_runtime_stops(project) -> None:
    """The look's end line is queued before its runtime stops: a pass meanwhile reads a checkpoint, not the end."""
    place = Where(project="shop", name="shop")
    spend_ledger.started("L", "look-t", agent="spotter", job="look", model="m1", before={}, place=place, look="x")
    spend_ledger.ended("L", "look-t", usage=used(0.1) | {"incomplete": "unconfirmed"}, ending="unconfirmed",
                       place=place, look="x")  # fmt: skip
    runtime_log("look-t", checkpoint("2026-10-27T01:00:00Z", 0.2e9))
    assert spend_reconcile.run([(project, None)])["imported"]["logs"] == 1
    assert run_piece("L") == (0.2, True, "run")
    logged("look-t", shutdown("2026-10-27T01:00:05Z", 0.25e9))
    assert spend_reconcile.run([(project, None)])["imported"]["logs"] == 1
    assert run_piece("L") == (0.25, False, "run")
    looks = [p for p in spend_shares.derive(spend_ledger.lines()) if p["role"] == "spotter"]
    assert [(p["run"], p["credits"]) for p in looks] == [("L", 0.25)]


def test_a_pass_whose_worker_starts_late_is_said_running_and_its_imports_follow(project, monkeypatch) -> None:
    """Sol's counterexample: the answer said the last pass's "done" while the new one had not begun, so the page
    never read again and showed what was there before the pass."""
    spend_ledger.folder().mkdir(parents=True, exist_ok=True)
    long_ago = (datetime.now(UTC) - timedelta(hours=1)).isoformat(timespec="seconds")
    spend_reconcile.state_path().write_text(json.dumps({"state": "done", "finished": long_ago}))
    real, began, go = spend_reconcile.run, threading.Event(), threading.Event()

    def late(projects: list) -> dict:
        began.set()
        go.wait(5)  # the worker thread is slow to begin its pass
        return real(projects)

    monkeypatch.setattr(spend_reconcile, "run", late)
    app = FastAPI()
    app.include_router(metrics_routes.router(lambda: [(project, None)]), prefix="/api/next")
    http = TestClient(app)
    first = http.get("/api/next/metrics?by=project").json()
    assert (first["coverage"]["reconcile"]["state"], first["rows"]) == ("running", [])
    assert began.wait(5)
    assert http.get("/api/next/metrics?by=project").json()["coverage"]["reconcile"]["state"] == "running"
    go.set()
    assert spend_reconcile.settled(10)
    after = http.get("/api/next/metrics?by=project").json()
    assert after["coverage"]["reconcile"]["state"] == "done"
    assert [(r["label"], r["credits"]) for r in after["rows"]] == [("shop", 5.5)]


def test_a_logged_sessions_growth_across_midnight_is_dated_between_its_checkpoints(project) -> None:
    """Sol's counterexample: a later checkpoint took the first one's time, so 1 credit on Oct 1 and 3 by Oct 2 counted
    3 on Oct 1 and 0 on Oct 2, complete. Each checkpoint keeps its time; the growth lies between the two."""
    runtime_log("solo", checkpoint("2026-10-01T22:00:00Z", 1e9))
    chatlogs.root().mkdir(parents=True)
    solo = {"event": "started", "session": "solo", "kind": "review", "role": "curator"}
    (chatlogs.root() / "manifest.jsonl").write_text(json.dumps(solo) + "\n")
    assert spend_reconcile.run([(project, None)])["imported"]["logs"] == 1
    logged("solo", shutdown("2026-10-02T09:00:00Z", 3e9))
    assert spend_reconcile.run([(project, None)])["imported"]["logs"] == 1
    assert run_piece("log:solo") == (3.0, False, "run")  # final: no piece of it is a lower bound any more
    pieces = sorted((p["lo"], p["hi"], p["credits"], p["uncertain"]) for p in spend_shares.derive(spend_ledger.lines())
                    if p["run"] == "log:solo")  # fmt: skip
    assert pieces == [
        ("2026-10-01T22:00:00+00:00", "2026-10-01T22:00:00+00:00", 1.0, []),
        ("2026-10-01T22:00:00+00:00", "2026-10-02T09:00:00+00:00", 2.0, ["at"]),
    ]  # fmt: skip
    found = spend_metrics.pieces()

    def on(start: str, end: str) -> dict:
        totals = spend_metrics.query(found, tz=UTC_ZONE, start=date.fromisoformat(start), end=date.fromisoformat(end),
                                     agent="curator")["totals"]  # fmt: skip
        return {k: totals[k] for k in ("credits", "runs", "incomplete")}

    everything = spend_metrics.query(found, tz=UTC_ZONE, agent="curator")
    assert (everything["totals"]["credits"], everything["totals"]["runs"]) == (3.0, 1)
    assert everything["totals"]["uncertain_time"] == 2.0
    assert on("2026-10-01", "2026-10-02") == {"credits": 1.0, "runs": 1, "incomplete": 0}  # its first checkpoint
    assert on("2026-10-02", "2026-10-03")["credits"] == 0  # the growth may lie on Oct 1: never pinned to Oct 2
    assert on("2026-10-01", "2026-10-03")["credits"] == 3.0  # both days: all of it


def test_a_recorded_ending_keeps_its_time_whatever_the_logs_checkpoint_says(project) -> None:
    spend_ledger.started("r", "kept", agent="builder", job="", model="m1", before={})
    spend_ledger.ended("r", "kept", usage={"error": "TimeoutError"}, ending="result")
    assert spend_ledger.WRITER.settled(5)
    [end] = [x for x in spend_ledger.lines() if x["type"] == "end"]
    runtime_log("kept", checkpoint("2026-10-01T22:00:00Z", 2e9))
    assert spend_reconcile.run([(project, None)])["imported"]["logs"] == 1
    [piece] = [p for p in spend_shares.derive(spend_ledger.lines()) if p["run"] == "r"]
    assert (piece["lo"], piece["hi"], piece["credits"]) == (end["at"], end["at"], 2.0)
