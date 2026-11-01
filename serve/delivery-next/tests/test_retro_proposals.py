"""What the Improvement page (#716) writes to Retro's proposals: decisions, outcomes and redrafts."""

import pytest

from owlbear_delivery_next.improvement import retro_proposals as props
from owlbear_delivery_next.improvement import retro_store as store

CASE = {"kind": "case"}


def _waiting(provenance="real", kind="spotter-case", about="r1"):
    pid = props.file(
        props.open_key(provenance, kind, about),
        ["g-1"],
        kind=kind,
        provenance=provenance,
        bar="b",
        record="r1",
        call="none",
    )
    props.reviewed(pid, props.folded()[pid]["evidence"], {"verdict": "survive", "why": "holds", "publishable": {}})
    return pid


@pytest.mark.parametrize(
    "change",
    ["re-review", "destination", "publishable", "review-only"],
)
def test_the_token_changes_with_anything_the_owner_saw(change):
    pid = _waiting()
    seen = props.token(props.folded()[pid], CASE)
    destination = CASE
    if change == "destination":
        destination = {"kind": "issue", "where": "o/r"}
    elif change == "review-only":  # a new sample, the same evidence digest: reviewed again, the text unchanged
        props.file(props.open_key("real", "spotter-case", "r1"), ["g-1"], {"count": 0, "sample": ["r9"]})
        answer = {"verdict": "survive", "why": "holds less", "risks": ["r9 says otherwise"], "publishable": {}}
        props.reviewed(pid, props.folded()[pid]["evidence"], answer)
        assert (props.folded()[pid]["state"], props.folded()[pid]["why"]) == ("waiting", "holds less")
    else:
        props.file(props.open_key("real", "spotter-case", "r1"), ["g-1", "g-2"])
        text = {"title": "t2"} if change == "publishable" else {}
        props.reviewed(pid, props.folded()[pid]["evidence"], {"verdict": "survive", "why": "x", "publishable": text})

    assert props.token(props.folded()[pid], destination) != seen


def test_a_refused_check_writes_nothing_and_an_accept_keeps_its_snapshot():
    pid = _waiting()
    before = store.lines(props.FILE)

    def stale(_snap):
        msg = "the page is stale"
        raise store.RetroError(msg)

    with pytest.raises(store.RetroError, match="stale"):
        props.transition(pid, "accepted", "owner", check=stale)
    assert store.lines(props.FILE) == before

    snap = props.transition(pid, "accepted", "owner", snapshot={"destination": CASE, "token": "t"})
    assert (snap["state"], snap["accepted"]["destination"], snap["apply_state"]) == ("accepted", CASE, "pending")


def test_apply_states_follow_the_steps_and_a_replayed_artefact_adds_nothing():
    pid = _waiting()
    props.transition(pid, "accepted", "owner", snapshot={"destination": CASE})
    case = {"kind": "case", "where": "cases", "ref": "c-1"}
    props.outcome(pid, "applied", step="created", artefact=case)
    props.outcome(pid, "applied", step="created", artefact=case)
    assert (props.folded()[pid]["apply_state"], len(props.folded()[pid]["applied"])) == ("partly", 1)

    props.outcome(pid, "failed", step="done", error="token ghp_" + "a" * 36 + " refused")
    snap = props.folded()[pid]
    assert snap["apply_state"] == "failed"
    assert "ghp_" not in snap["failures"][0]["error"]

    props.outcome(pid, "applied", step="done", artefact=case)
    assert props.folded()[pid]["apply_state"] == "done"


@pytest.mark.parametrize(("given", "kept"), [("irreversible-harm", "irreversible-harm"), ("maybe", "none")])
def test_a_redirect_is_redrafted_once_keeping_the_prior_evidence_and_kind(given, kept):
    pid = _waiting()
    props.transition(pid, "redirected", "owner", direction="ask for a case about tests")
    answer = {"cause": "c", "target": "look:tests", "mechanism": "m", "call": given}

    new = props.redrafted(pid, answer, "ask for a case about tests")

    assert props.redrafted(pid, answer, "ask for a case about tests") == new
    snaps = props.folded()
    assert snaps[pid]["redraft"] == new
    got = snaps[new]
    assert (got["kind"], got["bar"], got["findings"], got["record"]) == ("spotter-case", "b", ["g-1"], "r1")
    assert (got["call"], got["target"], got["redraft_of"], got["state"]) == (kept, "look:tests", pid, "drafted")
    assert [p["id"] for p in props.due_reviews()] == [new]


def test_a_proposal_not_redirected_is_not_redrafted():
    pid = _waiting()
    with pytest.raises(store.RetroError, match="not redirected"):
        props.redrafted(pid, {}, "x")


def test_the_reset_list_names_each_synthetic_artefact_once():
    real, fake = _waiting(), _waiting("synthetic")
    issue = {"kind": "issue", "where": "o/r", "ref": "7"}
    for pid in (real, fake):
        props.transition(pid, "accepted", "owner", snapshot={"destination": {"kind": "issue", "synthetic": True}})
        props.outcome(pid, "applied", step="created", artefact=issue)
    props.outcome(fake, "applied", step="closed", artefact=issue)

    assert props.synthetic_artefacts() == [issue]
