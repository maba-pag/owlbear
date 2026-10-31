"""Where an accepted proposal lands (#716): the destination table, row by row."""

import pytest

from owlbear_delivery_next.improvement import proposal_targets as targets
from owlbear_delivery_next.improvement import retro_store as store

UNITS = {"f-1": "chg:p1:fix", "f-2": "chg:p1:fix", "f-3": "chg:p2:fix", "f-4": "chat:s1"}


@pytest.fixture
def places(tmp_path):
    found = {}
    for pid, name in (("p1", "alpha"), ("p2", "beta")):
        clone = tmp_path / name
        (clone / ".github" / "agents").mkdir(parents=True)
        found[pid] = targets.Place(folder=f"{name}-folder", clone=clone)
    (found["p2"].clone / ".github" / "agents" / "scout.agent.md").write_text("Use the skill `map-code` to map.")
    (found["p2"].clone / ".github" / "skills" / "map-code").mkdir(parents=True)
    return found


def _snap(kind, target, findings, provenance="real", body="a body"):
    return {
        "kind": kind,
        "target": target,
        "findings": findings,
        "provenance": provenance,
        "publishable": {"title": "t", "body": body},
    }


def _resolve(snap, places, tmp_path):
    return targets.resolve(snap, places, tmp_path / "shared", UNITS)


@pytest.mark.parametrize(
    ("snap", "want"),
    [
        (
            _snap("lesson", "agent:builder", ["f-1", "f-2"]),
            {"kind": "memory", "project": "p1", "roles": ["builder"], "recommended": "project"},
        ),
        (
            _snap("lesson", "skill:map-code", ["f-3"]),
            {"kind": "memory", "project": "p2", "roles": ["scout"], "recommended": "project"},
        ),
        (
            _snap("lesson", "agent:builder", ["f-1", "f-3"]),
            {"kind": "memory", "project": "", "roles": ["builder"], "recommended": "global"},
        ),
        (_snap("delivery-change", "tool:edit", ["f-1"]), {"kind": "issue", "synthetic": False}),
        (_snap("agent-change", "agent:owlbear-builder", ["f-3"]), {"kind": "issue", "synthetic": False}),
        (_snap("agent-change", "agent:scout", ["f-3"]), {"kind": "backlog", "project": "p2", "folder": "beta-folder"}),
        (_snap("agent-change", "agent:scout", ["f-1"]), {"kind": "backlog", "project": "", "folder": ""}),
        (_snap("agent-change", "agent:scout", ["f-4"]), {"kind": "backlog", "project": ""}),
        (_snap("look-reconsider", "spotter:looks", ["f-4"]), {"kind": "issue", "repository": "maba-pag/owlbear"}),
    ],
)
def test_each_kind_and_target_resolves_to_its_row_the_project_read_from_the_unit_not_the_slug(
    snap, want, places, tmp_path
):
    got = _resolve(snap, places, tmp_path)
    assert {k: got[k] for k in want} == want
    if got["kind"] == "memory":
        folder = places[got["project"]].folder if got["project"] else targets.OWLBEAR
        assert got["folder"] == str(tmp_path / "shared" / folder / "memory")


def test_a_spotter_case_becomes_a_case_and_a_lesson_too_long_for_a_memory_is_refused(places, tmp_path):
    case = {"kind": "spotter-case", "record": "r1", "call": "none", "findings": ["g-1"], "provenance": "real"}
    assert _resolve(case, places, tmp_path) == {"kind": "case", "record": "r1", "call": "none", "synthetic": False}
    with pytest.raises(store.RetroError, match="too long for a memory"):
        _resolve(_snap("lesson", "agent:builder", ["f-1"], body="x" * 1025), places, tmp_path)


def test_synthetic_proposals_publish_only_to_the_sandbox(places, tmp_path):
    with pytest.raises(store.RetroError, match="only to the sandbox"):
        _resolve(_snap("agent-change", "agent:scout", ["f-3"], "synthetic"), places, tmp_path)

    sandbox = tmp_path / targets.SANDBOX
    sandbox.mkdir()
    places = {**places, "p9": targets.Place(folder="sandbox-folder", clone=sandbox)}
    got = _resolve(_snap("agent-change", "agent:scout", ["f-3"], "synthetic"), places, tmp_path)
    assert (got["kind"], got["project"]) == ("backlog", "p9")
    lesson = _resolve(_snap("lesson", "agent:scout", ["f-1"], "synthetic"), places, tmp_path)
    assert lesson["folder"] == str(tmp_path / "shared" / "sandbox-folder" / "memory")
    issue = _resolve(_snap("delivery-change", "tool:edit", ["f-1"], "synthetic"), places, tmp_path)
    assert (issue["kind"], issue["synthetic"]) == ("issue", True)
