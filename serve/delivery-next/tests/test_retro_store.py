"""Retro's judged state (#715): saved answers, findings, grades and the proposals' event log."""

import json

import pytest

from owlbear_delivery_next.improvement import assumptions
from owlbear_delivery_next.improvement import retro_proposals as props
from owlbear_delivery_next.improvement import retro_store as store


def _finding(fid, provenance="real", **more):
    return {"id": fid, "unit": "chat:s1", "provenance": provenance, "assumptions": ["retro-causes-1"], **more}


@pytest.mark.parametrize("review_between", [True, False])
def test_proposal_growth_journey(review_between):
    key = props.open_key("real", "lesson", "skipped-verification", "w-build", "m1")
    pid = props.file(key, ["rf-1", "rf-2"], {"count": 3, "sample": ["a"]}, kind="lesson", provenance="real")
    snap = props.folded()[pid]
    props.reviewed(pid, snap["evidence"], {"verdict": "survive", "why": "holds"})
    assert props.folded()[pid]["state"] == "waiting"
    props.transition(pid, "shown", "owner")
    assert props.file(key, ["rf-2", "rf-3"]) == pid
    grown = props.folded()[pid]
    assert (grown["findings"], grown["state"]) == (["rf-1", "rf-2", "rf-3"], "drafted")
    assert grown["review_digest"] != grown["evidence"]
    assert [p["id"] for p in props.due_reviews()] == [pid]
    before = store.lines(props.FILE)
    with pytest.raises(store.RetroError, match="waits for its review"):
        props.transition(pid, "accepted", "owner")
    assert store.lines(props.FILE) == before

    props.reviewed(pid, grown["evidence"], {"verdict": "survive", "why": "holds"})
    reviewed_digest = props.folded()[pid]["evidence"]
    props.file(key, ["rf-1"], {"count": 4, "sample": ["a"]})
    assert props.folded()[pid]["state"] == "drafted"
    if review_between:
        props.reviewed(pid, props.folded()[pid]["evidence"], {"verdict": "survive", "why": "holds"})
    props.file(key, ["rf-1"], {"count": 3, "sample": ["a"]})
    assert props.folded()[pid]["evidence"] == reviewed_digest
    assert (props.folded()[pid]["state"], [p["id"] for p in props.due_reviews()]) == ("drafted", [pid])
    props.file(key, ["rf-1"], {"count": 4, "sample": ["a"]})
    assert props.folded()[pid]["counterexamples"]["count"] == 4
    assert (props.folded()[pid]["state"], [p["id"] for p in props.due_reviews()]) == ("drafted", [pid])
    props.reviewed(pid, props.folded()[pid]["evidence"], {"verdict": "survive", "why": "still holds"})
    assert (props.folded()[pid]["state"], props.due_reviews()) == ("waiting", [])
    props.transition(pid, "accepted", "owner")
    assert props.folded()[pid]["state"] == "accepted"


def test_review_and_state_are_kept_whole(monkeypatch):
    pid = props.file(props.open_key("real", "spotter-case", "r1"), ["g-1"], kind="spotter-case", provenance="real")
    writes, real = [], store.append

    def append(name, *rows):
        if name == props.FILE:
            writes.append(rows)
        real(name, *rows)
        if name == props.FILE:
            raise KeyboardInterrupt

    monkeypatch.setattr(store, "append", append)
    with pytest.raises(KeyboardInterrupt):
        props.reviewed(pid, props.folded()[pid]["evidence"], {"verdict": "survive", "why": "holds"})
    assert len(writes[0]) == 2
    assert props.folded()[pid]["state"] == "waiting"


def test_history_survives_reset():
    assumptions.ensure("retro-causes-1")
    assumptions.ensure("retro-synthetic-1")
    store.add_findings([_finding("rf-1")])
    units = {
        "chat:s1": {"provenance": "real"},
        "syn:a": {"provenance": "synthetic", "assumptions": ["retro-synthetic-1"]},
    }
    store.update(lambda t: t["units"].update(units))
    real = props.file(props.open_key("real", "delivery-change", "tool-defect", "x"), ["rf-1"], provenance="real")
    fake = props.file(
        props.open_key("synthetic", "delivery-change", "tool-defect", "x"), ["rf-1"], provenance="synthetic"
    )
    assert real != fake
    assert [p["id"] for p in props.proposals()] == [real]
    assert {p["id"] for p in props.proposals(synthetic=True)} == {real, fake}
    assert [p["id"] for p in props.due_reviews()] == [real]
    assert fake in props.folded()
    assert (list(store.units()), list(store.units(synthetic=True))) == (["chat:s1"], ["chat:s1", "syn:a"])
    issue = {"kind": "issue", "where": "o/r", "ref": "7"}
    for pid in (real, fake):
        props.reviewed(pid, props.folded()[pid]["evidence"], {"verdict": "survive", "why": "holds"})
        props.transition(pid, "accepted", "owner", snapshot={"destination": {"kind": "issue", "synthetic": True}})
        props.outcome(pid, "applied", step="created", artefact=issue)
    props.outcome(fake, "applied", step="closed", artefact=issue)
    assert props.synthetic_artefacts() == [issue]
    history = store.lines(props.FILE)
    assumptions.reset()
    assert store.findings() == []
    assert [f["id"] for f in store.all_findings()] == ["rf-1"]
    assert (list(store.units(synthetic=True)), list(store.known())) == (["chat:s1"], ["chat:s1", "syn:a"])
    assert props.synthetic_artefacts() == [issue]
    assert store.lines(props.FILE) == history


def test_a_recurrence_after_rejection_opens_a_new_proposal_naming_the_prior_one():
    key = props.open_key("real", "agent-change", "instruction-gap", "w-plan", "m2")
    first = props.file(key, ["rf-1", "rf-2"], provenance="real")
    props.reviewed(first, props.folded()[first]["evidence"], {"verdict": "survive", "why": "holds"})
    props.transition(first, "rejected", "owner")
    assert props.file(key, ["rf-1"]) is None
    again = props.file(key, ["rf-1", "rf-9"], provenance="real")
    assert again != first
    assert props.folded()[again]["prior"] == first


def test_a_page_left_open_across_a_reset_cannot_move_a_proposal_resting_on_the_retired_assumption():
    assumptions.ensure("retro-causes-1")
    pid = props.file("real|lesson|k1", ["rf-1"], provenance="real", assumptions=["retro-causes-1"])
    props.reviewed(pid, props.folded()[pid]["evidence"], {"verdict": "survive", "why": "holds"})
    assumptions.reset()
    with pytest.raises(store.RetroError, match="hidden"):
        props.transition(pid, "accepted", "owner")
    assert props.folded()[pid]["state"] == "waiting"


def test_what_rests_on_an_unreadable_assumption_entry_is_hidden_and_the_rest_shown():
    assumptions.ensure("retro-causes-1")
    assumptions.ensure("retro-grades-1")
    marks = assumptions.listed() | {"retro-grades-1": {}}
    assumptions.path().write_text(json.dumps(marks))
    store.add_findings([_finding("rf-1"), _finding("rf-2", assumptions=["retro-grades-1"])])
    assert [f["id"] for f in store.findings()] == ["rf-1"]


def test_replay_journey():
    store.request("owner", chat="s1")
    store.run_event("run-1", "opened", unit="chat:s1", rev="r1")
    store.run_event("run-1", "inflight", batch="b-1")
    store.keep("b-1", "run-0", None, 3.0, attempt="empty answer")
    assert store.saved("b-1") is None
    assert [a["attempt"] for a in store.attempts("b-1")] == ["empty answer"]
    store.keep("b-1", "run-1", {"x": 1}, 2.0)
    store.keep("b-1", "run-2", {"x": 2}, 5.0)
    assert store.saved("b-1")["answer"] == {"x": 1}
    store.run_event("run-1", "settled", batch="b-1", spent=2.0, known=True)
    assert store.add_findings([_finding("rf-1")]) == ["rf-1"]
    assert store.add_findings([_finding("rf-1")]) == []
    assert [f["id"] for f in store.findings()] == ["rf-1"]
    store.add_grades([{"id": "rg-r1", "record": "r1", "grade": "wrong", "look": "a", "category": "c"}])
    pid = props.file(props.open_key("real", "lesson", "c", "t", "m"), ["rf-1"], provenance="real")
    props.reviewed(pid, props.folded()[pid]["evidence"], {"verdict": "reject", "why": "thin"})

    def seen():
        return (
            store.run_states(),
            props.folded(),
            store.all_findings(),
            store.grades(),
            store.queued(),
            store.class_grades(),
            store.saved("b-1"),
        )

    before = seen()
    for name in ("runs.jsonl", "batches.jsonl", "findings.jsonl", "grades.jsonl", "proposals.jsonl", "requests.jsonl"):
        path = store.place() / name
        path.write_text(path.read_text() * 2)
    assert seen() == before
    assert before[0]["run-1"]["calls"] == 1
    assert before[1][pid]["state"] == "rejected"
