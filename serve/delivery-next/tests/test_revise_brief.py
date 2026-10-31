"""A saved brief opens a new shaping chat to revise it, the Change left as it is; a refusing state says why."""

from __future__ import annotations

import threading
import time
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from owlbear_delivery_next.change_contracts import models as m
from owlbear_delivery_next.change_contracts.round_records import RoundFinding, RoundLoop, RoundPolicy
from owlbear_delivery_next.change_flow.status import Activity
from owlbear_delivery_next.local_system.codebase import CURRENT
from owlbear_delivery_next.project_host import api
from owlbear_delivery_next.project_host.host import HostRecord
from owlbear_delivery_next.state_store import briefs
from owlbear_delivery_next.state_store.store import Lock, Store

NOW = datetime(2026, 10, 16, 2, tzinfo=UTC)
DRAFT = {
    "change": "c1",
    "title": "Flip the hero",
    "outcome": "Visitors flip the hero image with one button.",
    "criteria": ["A second press returns the hero"],
    "scope": ["web"],
}


class Host:
    maintenance = None
    wake = SimpleNamespace(set=lambda: None)
    draining = staticmethod(lambda: False)
    closed = staticmethod(lambda: False)
    updating = staticmethod(lambda: "")
    launching = threading.Lock()
    record = HostRecord(url="http://127.0.0.1:9/", token="tok", pid=1, started_at=NOW, code=CURRENT)  # noqa: S106 - test token

    def activity(self, _slug):
        return Activity(host_up=True)


def change(**update) -> m.Change:
    brief = m.Brief(version=2, title="Flip the hero", outcome="Visitors flip the hero image with one button.")
    c = m.Change(slug="flip", handle="c1", brief=brief, step=m.Step(kind=m.StepKind.SHAPE))
    return c.model_copy(update=update)


def project(tmp_path, c: m.Change):
    store, calls = Store(tmp_path), []
    store.write(Lock("flip"), c)
    host = Host()
    host.repo = store.root
    launch = lambda *a: calls.append(a) or {"state": "open"}  # noqa: E731
    app = api.create_app(store, "t", host, launch=launch, which=lambda _n: "/bin/code")
    return store, calls, TestClient(app, base_url="http://127.0.0.1", headers={"authorization": "Bearer t"})


def kept(store: Store) -> tuple:
    with store.db.read() as db:
        inbox = db.execute("SELECT item FROM inbox WHERE slug = 'flip'").fetchall()
    return store.read("flip").model_dump(), store.rev("flip"), store.events("flip"), inbox


def test_a_saved_brief_opens_a_new_shaping_chat_in_its_project_and_leaves_the_change_as_it_is(tmp_path):
    paused = m.Intent(paused_at=NOW, pause_reason="lunch")  # a pause holds Delivery's work, not the owner's chat
    store, calls, http = project(tmp_path, change(intent=paused))
    before = kept(store)
    assert http.get("/api/next/changes/flip").json()["brief"]["unrevisable"] == ""
    out = http.post("/api/next/changes/flip/revise-brief").json()
    assert (out["started"], set(out)) == (True, {"started", "launch"})
    end = time.monotonic() + 5
    while not calls and time.monotonic() < end:
        time.sleep(0.01)
    [(repo, _role, prompt)] = calls
    assert repo == store.root
    assert prompt.startswith('Continue Delivery Change c1 ("Flip the hero") in this project: use the owlbear-change')
    assert kept(store) == before


def finding(**f) -> dict:
    loop = RoundLoop(subject="brief", policy=RoundPolicy(), findings=[RoundFinding(id="F1", text="t", raised=1, **f)])
    return {"loops": {"brief": loop}}


@pytest.mark.parametrize(
    ("update", "reason"),
    [
        ({"step": m.Step(kind=m.StepKind.PLAN)}, "c1 is approved; ask for changes in the Changes page"),
        ({"finished_at": NOW}, "c1 is approved; ask for changes in the Changes page"),
        ({"step": m.Step(kind=m.StepKind.SHAPE, mode="challenge")}, "its challenge runs; save the revision after it"),
        (finding(reconsider="due"), "a finding of its challenge waits for the owner's decision in the Changes page"),
    ],
)
def test_a_state_that_refuses_a_revision_says_why_and_opens_no_chat(tmp_path, update, reason):
    store, calls, http = project(tmp_path, change(**update))
    assert http.get("/api/next/changes/flip").json()["brief"]["unrevisable"] == reason
    refused = http.post("/api/next/changes/flip/revise-brief")
    assert (refused.status_code, refused.json()["detail"], calls) == (409, reason, [])
    assert briefs.save_brief(store, DRAFT) == (409, {"errors": [f"change: {reason}"]})
