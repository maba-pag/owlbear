"""Retro's judged state (#715): saved answers, findings, grades and the proposals' event log."""

from owlbear_delivery_next.improvement import assumptions
from owlbear_delivery_next.improvement import retro_proposals as props
from owlbear_delivery_next.improvement import retro_store as store


def _finding(fid, provenance="real", **more):
    return {"id": fid, "unit": "chat:s1", "provenance": provenance, "assumptions": ["retro-causes-1"], **more}


def test_a_saved_batch_is_replayed_and_an_unusable_answer_only_kept_as_an_attempt():
    store.keep("b-1", "run-1", None, 3.0, attempt="empty answer")
    assert store.saved("b-1") is None
    assert [a["attempt"] for a in store.attempts("b-1")] == ["empty answer"]
    store.keep("b-1", "run-2", {"findings": [1]}, 4.0)
    store.keep("b-1", "run-3", {"findings": [2]}, 5.0)
    assert store.saved("b-1")["answer"] == {"findings": [1]}
    assert store.add_findings([_finding("rf-b-1-0")]) == ["rf-b-1-0"]
    assert store.add_findings([_finding("rf-b-1-0")]) == []
    assert [f["id"] for f in store.findings()] == ["rf-b-1-0"]


def test_growth_goes_to_the_open_proposal_and_makes_its_review_stale():
    key = props.open_key("real", "lesson", "skipped-verification", "w-build", "m1")
    pid = props.file(key, ["rf-1", "rf-2"], kind="lesson", provenance="real")
    snap = props.folded()[pid]
    props.reviewed(pid, snap["evidence"], {"verdict": "survive", "why": "holds"})
    assert props.folded()[pid]["state"] == "waiting"
    assert props.file(key, ["rf-2", "rf-3"]) == pid
    grown = props.folded()[pid]
    assert (grown["findings"], grown["state"]) == (["rf-1", "rf-2", "rf-3"], "drafted")
    assert grown["review_digest"] != grown["evidence"]
    assert [p["id"] for p in props.due_reviews()] == [pid]


def test_counterexamples_that_return_to_an_earlier_count_are_kept_as_they_are_now():
    key = props.open_key("real", "lesson", "skipped-verification", "w-build", "m1")
    pid = props.file(key, ["rf-1"], {"count": 3, "sample": ["a"]}, kind="lesson", provenance="real")
    for count in (4, 3, 4):
        props.file(key, ["rf-1"], {"count": count, "sample": ["a"]})
    assert props.folded()[pid]["counterexamples"]["count"] == 4


def test_a_verdict_and_the_state_it_moves_to_are_kept_in_one_write_so_a_failing_disk_never_strands_it(monkeypatch):
    pid = props.file(props.open_key("real", "spotter-case", "r1"), ["g-1"], kind="spotter-case", provenance="real")
    writes, real = [], store.append

    def append(name, *rows):
        if name == props.FILE:
            if writes:
                msg = "the disk is full"
                raise OSError(msg)
            writes.append(rows)
        real(name, *rows)

    monkeypatch.setattr(store, "append", append)
    props.reviewed(pid, props.folded()[pid]["evidence"], {"verdict": "survive", "why": "holds"})

    assert props.folded()[pid]["state"] == "waiting"


def test_real_and_synthetic_keys_stay_apart_and_synthetic_ones_are_hidden_unless_asked():
    real = props.file(props.open_key("real", "delivery-change", "tool-defect", "x"), ["rf-1"], provenance="real")
    fake = props.file(
        props.open_key("synthetic", "delivery-change", "tool-defect", "x"), ["rf-1"], provenance="synthetic"
    )
    assert real != fake
    assert [p["id"] for p in props.proposals()] == [real]
    assert {p["id"] for p in props.proposals(synthetic=True)} == {real, fake}


def test_a_recurrence_after_rejection_opens_a_new_proposal_naming_the_prior_one():
    key = props.open_key("real", "agent-change", "instruction-gap", "w-plan", "m2")
    first = props.file(key, ["rf-1", "rf-2"], provenance="real")
    props.transition(first, "rejected", "owner")
    assert props.file(key, ["rf-1"]) is None
    again = props.file(key, ["rf-1", "rf-9"], provenance="real")
    assert again != first
    assert props.folded()[again]["prior"] == first


def test_what_rests_on_a_retired_assumption_is_hidden():
    assumptions.ensure("retro-causes-1")
    store.add_findings([_finding("rf-1")])
    assumptions.reset()
    assert store.findings() == []
    assert len(store.all_findings()) == 1


def test_a_reader_sees_only_real_units_on_live_assumptions_and_synthetic_ones_when_asked():
    assumptions.ensure("retro-synthetic-1")
    units = {
        "chat:s1": {"provenance": "real"},
        "syn:a": {"provenance": "synthetic", "assumptions": ["retro-synthetic-1"]},
    }
    store.update(lambda t: t["units"].update(units))
    assert (list(store.units()), list(store.units(synthetic=True))) == (["chat:s1"], ["chat:s1", "syn:a"])
    assumptions.reset()
    assert (list(store.units(synthetic=True)), list(store.known())) == (["chat:s1"], ["chat:s1", "syn:a"])


def test_replaying_every_file_twice_changes_no_snapshot():
    store.request("owner", chat="s1")
    store.run_event("run-1", "opened", unit="chat:s1", rev="r1")
    store.run_event("run-1", "inflight", batch="b-1")
    store.keep("b-1", "run-1", {"x": 1}, 2.0)
    store.run_event("run-1", "settled", batch="b-1", spent=2.0, known=True)
    store.add_findings([_finding("rf-1")])
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
