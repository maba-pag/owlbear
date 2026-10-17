"""TD-208 step 5, TD-217: the Change page's round markers, finding details, unreviewed repairs, standing rejections."""

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from owlbear_delivery_next.change_contracts.models import Brief, Change, Plan, Task
from owlbear_delivery_next.change_contracts.round_records import FINAL, RoundFinding, RoundLoop, RoundPolicy
from owlbear_delivery_next.change_flow import round_marks
from owlbear_delivery_next.change_flow.status import Activity
from owlbear_delivery_next.project_host import api
from owlbear_delivery_next.state_store.store import Lock, Store

NOW = datetime(2026, 10, 17, 6, tzinfo=UTC)


def found(n: int, raised: int, state: str = "open", **kw: object) -> RoundFinding:
    return RoundFinding(id=f"F{n}", text=f"a.txt:{n}: p - fix: f", raised=raised, state=state, **kw)


def test_a_finding_is_open_unverified_or_settled():
    lp = RoundLoop(subject="t1", policy=RoundPolicy(), round=2, unreviewed=["t4"], reviewed=["t3"])
    kinds = {
        "open": found(1, 1),
        "owner-fix": found(2, 1, "owner-fix"),
        "escalated": found(3, 1, "escalated"),
        "fixed in a later round's review": found(4, 1, "fixed", repair="t3"),
        "fixed, its repair unreviewed": found(5, 1, "fixed", repair="t4"),
        "fixed after the latest round": found(6, 1, "fixed", repair="t5"),  # the owner's Fix after a verdict
        "rejected": found(7, 1, "rejected"),
        "standing": found(8, 1, "standing"),
        "owner-drop": found(9, 1, "owner-drop"),
        "withdrawn": found(10, 1, "withdrawn"),
    }
    assert {name: round_marks.kind(lp, f) for name, f in kinds.items()} == {
        "open": "open",
        "owner-fix": "open",
        "escalated": "open",
        "fixed in a later round's review": "settled",
        "fixed, its repair unreviewed": "unverified",
        "fixed after the latest round": "unverified",
        "rejected": "unverified",
        "standing": "settled",
        "owner-drop": "settled",
        "withdrawn": "settled",
    }


def test_a_rounds_marker_takes_its_most_urgent_kind_with_a_count_and_the_latest_is_marked():
    lp = RoundLoop(subject="t1", policy=RoundPolicy(), round=3, unreviewed=["t6"], reviewed=["t3"])
    lp.findings = [
        found(1, 1, "fixed", repair="t3"),
        found(2, 1, "standing", reason="r", judgement="j"),
        found(3, 3, "fixed", repair="t6"),
        found(4, 3, "rejected", reason="not so"),
        found(5, 3, "escalated"),
        found(6, 3, "escalated"),
    ]
    marks = round_marks.rounds(lp, lp.findings)
    assert [(m["round"], m["last"], m["kind"], m["count"]) for m in marks] == [
        (1, False, "settled", 2),
        (3, True, "open", 2),
    ]
    assert marks[1]["said"] == (
        "Round 3 (latest): 1 fix reported, not re-reviewed; 1 rejection not reviewed; "
        "2 rejections the reviewer did not accept"
    )
    assert marks[0]["findings"][1] == {
        "id": "F2",
        "text": "a.txt:2: p - fix: f",
        "kind": "settled",
        "state": "rejection the reviewer accepted",
        "tasks": [],
        "reason": "r",
        "judgement": "j",
        "note": "",
    }


def test_the_page_gets_each_tasks_markers_apart_and_what_is_left(tmp_path):
    tasks = [
        Task(id="t1", title="one", done=True),
        Task(id="t2", title="two", done=True),
        Task(id="t3", title="Fix 1 finding of task t1", origin="review", fixes="t1", done=True),
        Task(id="t4", title="Fix 2 findings of the final review", origin="review", fixes=FINAL, done=True),
    ]
    own = RoundLoop(subject="t1", policy=RoundPolicy(), round=1, ended="count", unreviewed=["t3"])
    own.findings = [found(1, 1, "rejected", reason="it is right")]
    final = RoundLoop(subject=FINAL, attempt=2, policy=RoundPolicy(), round=1, unreviewed=["t4"])
    final.findings = [found(1, 1, "fixed", tasks=["t1", "t2"], repair="t4"), found(2, 1, "standing", tasks=["t2"])]
    final.findings.append(found(3, 1, tasks=["t2"]))
    c = Change(slug="c1", brief=Brief(version=1), plan=Plan(tasks=tasks), loops={"t1": own, FINAL: final})
    shown = round_marks.shown(c)
    brief = {
        t: {k: [(m["round"], m["kind"], m["count"]) for m in v] for k, v in r.items()}
        for t, r in shown["tasks"].items()
    }
    assert brief == {
        "t1": {"task": [(1, "unverified", 1)], "final": [(1, "unverified", 1)]},
        "t2": {"task": [], "final": [(1, "open", 1)]},
    }
    assert [(m["round"], m["kind"], m["count"]) for m in shown["final"]] == [(1, "open", 1)]
    assert (shown["attempt"], shown["unreviewed"]) == (
        2,
        [
            {"id": "t3", "title": "Fix 1 finding of task t1", "loop": "t1"},
            {"id": "t4", "title": "Fix 2 findings of the final review", "loop": FINAL},
        ],
    )
    assert [(f["loop"], f["id"], f["state"]) for f in shown["standing"]] == [
        ("t1", "F1", "rejection not reviewed"),
        (FINAL, "F2", "rejection the reviewer accepted"),
    ]
    store = Store(tmp_path / "store")
    store.write(Lock("c1"), c)
    host = type("H", (), {"wake": None, "record": None, "activity": lambda _s, _slug: Activity(host_up=True)})()
    client = TestClient(
        api.create_app(store, "t", host), base_url="http://127.0.0.1", headers={"authorization": "Bearer t"}
    )
    assert client.get("/api/next/changes/c1").json()["rounds"] == round_marks.shown(store.read("c1"))
