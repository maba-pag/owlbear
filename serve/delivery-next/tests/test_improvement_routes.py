"""The Improvement page's machine routes (#716): reads of the Spotter, Retro, cases and proposals; the owner's acts."""

from __future__ import annotations

import json
import threading
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from owlbear_delivery_next.change_contracts import models as m
from owlbear_delivery_next.improvement import case_replay, cases, improvement_view, spotter
from owlbear_delivery_next.improvement import proposal_targets as targets
from owlbear_delivery_next.improvement import retro_proposals as props
from owlbear_delivery_next.improvement import retro_store as store
from owlbear_delivery_next.improvement.credit_meter import Meter
from owlbear_delivery_next.local_system import codebase
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.local_system.slots import Slots
from owlbear_delivery_next.machine_host import app, cases_job, improvement_routes
from owlbear_delivery_next.machine_host.machine import Machine
from owlbear_delivery_next.project_host.host import HostRecord
from owlbear_delivery_next.state_store import watch_reports
from owlbear_delivery_next.state_store.store import Lock, Store
from owlbear_delivery_next.state_store.watch_reports import Report

if TYPE_CHECKING:
    from pathlib import Path

API = "/api/next/improvement"
UNITS = {"f-1": "chg:p1:fix", "f-2": "chg:p1:fix"}
TEXT = {"title": "Check the export's week column", "body": "The builder said done before the week held ISO weeks."}


@pytest.fixture
def world(tmp_path, monkeypatch):
    monkeypatch.setattr(targets, "units_of", lambda: UNITS)
    projects: dict[str, tuple[Store, Path]] = {}
    for pid, name in (("p1", "alpha"), ("p2", "beta")):
        clone = tmp_path / name
        clone.mkdir()
        st = Store(tmp_path / f"{name}-store", name=f"{name}-folder")
        for slug in ("fix", "other"):
            done = datetime(2026, 10, 1, tzinfo=UTC) if slug == "fix" else None
            st.write(Lock(slug), m.Change(slug=slug, step=m.Step(kind=m.StepKind.BUILD), finished_at=done))
        projects[pid] = (st, clone)
    machine = SimpleNamespace(
        retro=SimpleNamespace(seams=SimpleNamespace(projects=lambda: projects)),
        projects=dict.fromkeys(projects),
        updating="",
        stopping=threading.Event(),
    )
    served = FastAPI()
    served.include_router(improvement_routes.router(machine, lambda: DataRepo(tmp_path / "shared")), prefix="/api/next")
    return SimpleNamespace(http=TestClient(served), projects=projects, shared=tmp_path / "shared")


def _records(*rows: dict[str, Any]) -> None:
    folder = spotter.root()
    with (folder / "records-2026-10-01.jsonl").open("a") as out:
        for r in rows:
            base = {"at": "2026-10-01T10:00:00+00:00", "step": "build", "session": "s", "look": "handoff", "call": "c"}
            out.write(json.dumps(base | r) + "\n")


def _waiting() -> str:
    store.add_findings([{"id": "f-1", "unit": "chg:p1:fix", "change": "p1:fix", "what": "done before the week held",
                         "cost": "a re-run", "mechanism": "m-1"}])  # fmt: skip
    key = props.open_key("real", "lesson", "agent:builder")
    pid = props.file(key, ["f-1"], kind="lesson", target="agent:builder", provenance="real")
    props.reviewed(pid, props.folded()[pid]["evidence"], {"verdict": "survive", "why": "holds", "publishable": TEXT})
    return pid


def test_the_routes_need_the_machine_token() -> None:
    record = HostRecord(url="http://127.0.0.1:9/", token="t", pid=1, started_at=datetime.now(UTC),  # noqa: S106
                        code=codebase.CURRENT)  # fmt: skip
    machine = Machine(record)
    try:
        http = TestClient(app.create(machine), base_url="http://127.0.0.1")
        assert http.get(API).status_code == 401
        assert http.post(f"{API}/followups", json={"finding": "f-1"}).status_code == 401
        said = http.get(API, headers={"authorization": "Bearer t"})
        assert said.status_code == 200, said.text
        assert set(said.json()) == {"spotter", "retro", "cases", "proposals"}
    finally:
        machine.stop_all()


def test_a_decision_names_what_the_page_read_and_a_stale_one_is_refused_with_nothing_written(world) -> None:
    pid = _waiting()
    (shown,) = world.http.get(API).json()["proposals"]
    assert (shown["id"], shown["state"], shown["destination"]["kind"]) == (pid, "waiting", "memory")
    seen = {
        "id": "f-1",
        "change": "p1:fix",
        "unit": "chg:p1:fix",
        "what": "done before the week held",
        "cost": "a re-run",
    }
    assert shown["seen"] == [seen]
    props.file(props.open_key("real", "lesson", "agent:builder"), ["f-1", "f-2"])  # it grows and is re-reviewed
    props.reviewed(pid, props.folded()[pid]["evidence"], {"verdict": "survive", "why": "again", "publishable": TEXT})
    before = store.lines(props.FILE)

    stale = world.http.post(f"{API}/proposals/{pid}/decide", json={"state": "accepted", "token": shown["token"]})

    assert (stale.status_code, store.lines(props.FILE)) == (409, before)
    assert "changed since it was shown" in stale.json()["detail"]
    bad = world.http.post(f"{API}/proposals/{pid}/decide", json={"state": "merged", "token": shown["token"]})
    assert bad.status_code == 422
    assert world.http.post(f"{API}/proposals/{pid}/apply").status_code == 409  # not accepted


def test_an_accepted_proposal_is_applied_from_the_page(world) -> None:
    pid = _waiting()
    (shown,) = world.http.get(API).json()["proposals"]

    after = world.http.post(f"{API}/proposals/{pid}/decide", json={"state": "accepted", "token": shown["token"]})
    applied = world.http.post(f"{API}/proposals/{pid}/apply")

    assert (after.status_code, after.json()["state"]) == (200, "accepted")
    assert (applied.status_code, applied.json()["apply_state"]) == (200, "done"), applied.text
    redraft = world.http.post(f"{API}/proposals/{pid}/redraft")
    assert (redraft.status_code, store.queued()) == (409, [])


def test_a_closed_proposal_with_work_left_stays_shown_past_the_newest_closed(world, monkeypatch) -> None:
    ticks = iter(range(1000))
    start = datetime(2026, 10, 1, tzinfo=UTC)
    monkeypatch.setattr(store, "now", lambda: (start + timedelta(minutes=next(ticks))).isoformat(timespec="seconds"))
    pids = []
    for i in range(improvement_view.CLOSED + 1):
        store.add_findings([{"id": f"f-{i}", "unit": "chg:p1:fix", "change": "p1:fix", "what": "w", "cost": "c",
                             "mechanism": f"m-{i}"}])  # fmt: skip
        pid = props.file(props.open_key("real", "lesson", f"agent:{i}"), [f"f-{i}"], kind="lesson",
                         target="agent:builder", provenance="real")  # fmt: skip
        answer = {"verdict": "survive", "why": "holds", "publishable": TEXT}
        props.reviewed(pid, props.folded()[pid]["evidence"], answer)
        pids.append(pid)
    (first,) = [p for p in world.http.get(API).json()["proposals"] if p["id"] == pids[0]]
    accepted = world.http.post(f"{API}/proposals/{pids[0]}/decide", json={"state": "accepted", "token": first["token"]})
    assert accepted.json()["apply_state"] == "pending"  # the oldest closed one, never made
    for pid in pids[1:]:
        props.transition(pid, "rejected", "owner")

    shown = [p["id"] for p in world.http.get(API).json()["proposals"]]

    assert (len(shown), shown[-1]) == (improvement_view.CLOSED + 1, pids[0])
    assert world.http.post(f"{API}/proposals/{pids[0]}/apply").json()["apply_state"] == "done"
    assert pids[0] not in [p["id"] for p in world.http.get(API).json()["proposals"]]  # the cap holds again


def test_a_case_shows_the_grade_it_rests_on_and_a_lost_redraft_is_asked_for_again(world) -> None:
    grade = {"id": "rg-r1", "record": "r1", "grade": "wrong", "reason": "it missed the column", "unit": "chg:p1:fix",
             "look": "handoff", "provenance": "real"}  # fmt: skip
    store.add_grades([grade])
    pid = props.file(props.open_key("real", "spotter-case", "r1"), ["rg-r1"], kind="spotter-case",
                     target="look:handoff", record="r1", call="hand-off-fitness", provenance="real")  # fmt: skip
    props.reviewed(pid, props.folded()[pid]["evidence"], {"verdict": "survive", "why": "holds", "publishable": TEXT})
    (shown,) = world.http.get(API).json()["proposals"]
    what = "the handoff look was graded wrong: it missed the column"
    assert shown["seen"] == [{"id": "rg-r1", "change": "p1:fix", "unit": "chg:p1:fix", "what": what, "cost": ""}]

    body = {"state": "redirected", "token": shown["token"], "direction": "Ask for the columns first"}
    assert world.http.post(f"{API}/proposals/{pid}/decide", json=body).status_code == 200
    (asked,) = store.queued()
    assert world.http.get(API).json()["proposals"][0]["redraft_run"] == {"state": "queued"}
    assert store.take(asked["id"])  # the host that took it stopped before its run opened

    assert world.http.get(API).json()["proposals"][0]["redraft_run"] == {}
    again = world.http.post(f"{API}/proposals/{pid}/redraft")
    assert (again.status_code, [q.get("redraft") for q in store.queued()]) == (200, [pid])

    (asked,) = store.queued()
    assert store.take(asked["id"])  # this run filed the redraft, then stopped before reviewing it
    child = props.redrafted(pid, {"cause": "review", "target": "look:handoff", "mechanism": "ask first"}, "x")
    shown = world.http.get(API).json()["proposals"]
    assert [(p["id"], p["redraft"], p["redraft_state"]) for p in shown if p["id"] == pid] == [(pid, child, "drafted")]
    review = world.http.post(f"{API}/proposals/{pid}/redraft")
    assert (review.status_code, [q.get("redraft") for q in store.queued()]) == (200, [pid])


def test_only_an_irreversible_stop_marks_a_stopped_step_and_looks_filter_by_project_id(world) -> None:
    _records(
        {"id": "r-credit", "project": "p1", "change": "fix", "category": "", "stopped": "reached",
         "stopped_by": "look"},
        {"id": "r-harm", "project": "p1", "change": "fix", "category": "irreversible-harm", "acted": "stopped",
         "at": "2026-10-01T11:00:00+00:00"},
        {"id": "r-other", "project": "p2", "change": "fix", "category": "irreversible-harm"},
    )  # fmt: skip

    said = world.http.get(f"{API}/looks", params={"project": "p1"}).json()

    assert [(r["id"], r["stopped_step"], r["credit_stop"]) for r in said["looks"]] == [
        ("r-harm", True, ""),
        ("r-credit", False, "reached"),
    ]
    assert said["looks"][0]["followup"] == {"state": ""}
    assert world.http.get(f"{API}/looks", params={"project": "nope"}).status_code == 404
    detail = world.http.get(f"{API}/change", params={"project": "p2", "slug": "fix"}).json()
    assert ([r["id"] for r in detail["looks"]], detail["findings"]) == (["r-other"], [])
    assert world.http.get(f"{API}/change", params={"project": "p2", "slug": "gone"}).status_code == 404


def test_a_look_whose_spend_was_not_reported_counts_as_unknown_and_one_never_begun_counts_apart() -> None:
    at = "2026-10-01T10:00:00+00:00"
    records = [
        {"id": "r-1", "at": at, "project": "p1", "credits": 0.2, "credits_known": True, "stopped": "reached"},
        {"id": "r-2", "at": at, "project": "p1", "credits": 0.1, "credits_known": False, "stopped": "unknown"},
        {"id": "r-3", "at": at, "project": "p1", "skipped": "capacity: looks already running"},
        {"id": "r-4", "at": at, "project": "p1", "skipped": "time: the look ran over", "sdk_sessions": ["s-4"]},
    ]

    said = improvement_view.spotter({}, records, datetime(2026, 10, 2, tzinfo=UTC))

    spent = {"looks": 3, "credits": pytest.approx(0.3), "unknown": 2, "stopped": 1, "skipped": 1}
    assert said["spend"]["p1"] == spent
    stops = [r["credit_stop"] for r in improvement_view.looks({}, records, [])["looks"]]
    assert stops == ["reached", "unknown", "", ""]


def test_the_outside_writes_of_every_change_of_every_project_are_listed_together_each_tagged(world) -> None:
    for (pid, slug), at in zip((("p1", "fix"), ("p2", "other")), ("01", "02"), strict=True):
        st = world.projects[pid][0]
        with st.db.write() as connection:
            row = Report("s", f"c-{pid}", f"2026-10-01T10:00:{at}.000+00:00", "build", "main", "bash", "cp a /x",
                         ("/x",), "outside write (not judged yet)", "", "start")  # fmt: skip
            watch_reports.put(slug, row)(connection)
            inside = Report("s", f"i-{pid}", "2026-10-01T10:00:03.000+00:00", "build", "main", "bash", "ls", (),
                            "inside", "", "start")  # fmt: skip
            watch_reports.put(slug, inside)(connection)

    said = world.http.get(f"{API}/looks").json()

    assert [(r["project"], r["change"], r["call_id"]) for r in said["outside"]] == [
        ("p2", "other", "c-p2"),
        ("p1", "fix", "c-p1"),
    ]


def test_retro_runs_only_on_a_finished_change_and_an_unknown_follow_up_is_not_found(world) -> None:
    assert world.http.post(f"{API}/retro", json={"change": "p1:other"}).status_code == 409
    queued = world.http.post(f"{API}/retro", json={"change": "p1:fix"})
    assert (queued.status_code, [r["change"] for r in store.queued()]) == (200, ["p1:fix"])
    finished = world.http.get(API).json()["retro"]["finished"]
    assert sorted(f["change"] for f in finished) == ["p1:fix", "p2:fix"]
    assert world.http.post(f"{API}/followups", json={"finding": "nope"}).status_code == 404


def _checked() -> str:
    for call in ("none", "none", "hand-off-fitness"):
        cid = cases.freeze({"intent": {"task": f"t {call}"}, "recent": [{"tool": "bash", "args": "make"}]},
                           {"source": "pilot", "family": "f"})  # fmt: skip
        entry = {"stage": "candidate", "call": call, "why": "why", "example": "", "review": None}
        cases.commit(cases.current()["n"], {cid: entry}, "t", "add")
        cases.commit(cases.current()["n"], {cid: cases.edited(cid, entry, stage="test", reviewed_by="sol")}, "t", "r")
    return cid


def _job(monkeypatch) -> cases_job.CasesJob:
    monkeypatch.setattr(cases_job, "limits", lambda: {"replay": 10.0, "retro": 5.0, "look": 1.0})
    monkeypatch.setattr(cases_job, "role", lambda _name: cases_job.RoleModel(model="m", effort="medium"))
    slots = Slots(lambda: 1)
    slots.open()

    def spent(meter: Meter) -> None:
        share = meter.part()
        share.call(0.1)
        share.ended(0.1, confirmed=True)

    async def looked(_card, _prompt, meter: Meter, _spot) -> dict[str, Any]:
        spent(meter)
        return {"category": "none", "note": ""}

    async def asked(_message, meter: Meter, _role) -> str:
        spent(meter)
        return '{"situation": "An agent stopped with half the task done.", "call": "hand-off-fitness", "why": "x"}'

    return cases_job.CasesJob(slots, paused=lambda: False, looked=looked, asked=asked, shared=lambda: None)


def test_a_case_run_the_job_has_taken_still_holds_the_moves(world) -> None:
    chosen, n = _checked(), cases.current()["n"]
    rid = world.http.post(f"{API}/cases/{chosen}/move", json={"stage": "example", "parent": n, "example": "x"})
    assert case_replay.take(rid.json()["queued"])  # the job runs it now

    queued = world.http.get(API).json()["cases"]["queued"]

    assert [(q["id"], q.get("running")) for q in queued] == [(rid.json()["queued"], True)]


def test_a_checked_case_moves_into_the_examples_only_with_its_text_and_commits_once_its_regression_passes(
    world, monkeypatch
) -> None:
    chosen = _checked()
    n = cases.current()["n"]
    listed = {c["id"]: c for c in world.http.get(API).json()["cases"]["cases"]}
    assert (listed[chosen]["example"], listed[chosen]["prefill"]) == ("", "t hand-off-fitness\n\nbash make")

    empty = world.http.post(f"{API}/cases/{chosen}/move", json={"stage": "example", "parent": n, "example": " "})
    assert (empty.status_code, cases.current()["n"], case_replay.queued()) == (422, n, [])

    said = world.http.post(f"{API}/cases/{chosen}/move", json={"stage": "example", "parent": n, "example": "a moment"})
    assert said.status_code == 200, said.text
    _job(monkeypatch).tick(0)

    result = next(r for r in case_replay.results() if r["id"] == said.json()["queued"])["result"]
    assert result == "passed"
    assert (cases.current()["cases"][chosen]["stage"], cases.current()["cases"][chosen]["example"]) == (
        "example",
        "a moment",
    )
    stale = world.http.post(f"{API}/cases/{chosen}/move", json={"stage": "test", "parent": n})
    assert stale.status_code == 409
