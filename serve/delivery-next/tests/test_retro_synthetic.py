"""Retro's fixture units and the retirement of synthetic runs."""

import json
from types import SimpleNamespace

import pytest
from tests import retro_fixture as syn

from owlbear_delivery_next.commands import cli
from owlbear_delivery_next.improvement import assumptions, retro_evidence, retro_judge, retro_store
from owlbear_delivery_next.improvement import proposal_targets as targets
from owlbear_delivery_next.improvement import retro_proposals as props
from owlbear_delivery_next.improvement import retro_units as units
from owlbear_delivery_next.improvement.retro_calls import Paid
from owlbear_delivery_next.improvement.retro_segments import REF
from owlbear_delivery_next.state_store import registry
from owlbear_delivery_next.state_store.database import StoreError
from owlbear_delivery_next.state_store.store import Store

CANNED = {  # a quote in a synthetic unit -> the finding's cause and target
    "All tests pass.": ("skipped-verification", "agent:builder"),
    "the export tests pass": ("skipped-verification", "agent:builder"),
    "edit api/schema.json and run the tests": ("instruction-gap", "skill:w-build"),
    "Document every new command in docs/cli.md": ("instruction-gap", "skill:w-build"),
    "the full test run passed": ("skipped-verification", "agent:builder"),
    "the edit was never written": ("tool-defect", "tool:edit"),
    "List every function the repository defines": ("instruction-gap", "agent:scout"),
}
WRONG = {"syn-edit-lost-2": "none"}  # a record the Spotter got wrong -> what it should have said


SHOWN = {"title": "a proposal", "body": "what it proposes"}


def _evidence(message):
    return json.loads(message.split("```json\n")[-1].rsplit("\n```", 1)[0])


def _judged(ev):
    found = [
        {
            "refs": [REF.findall(p["text"][: p["text"].index(quote)])[-1]],
            "quotes": [quote],
            "what": "it said done before checking",
            "mechanism": "it trusted what it was told",
            "cost": "a rework round",
            "recovered": True,
            "catchable": True,
            "cause": cause,
            "target": target,
            "steps": "edit app/report.py, then git diff --stat" if cause == "tool-defect" else "",
            "rests_on_gap": quote == "the full test run passed",
        }
        for p in ev["parts"]
        for quote, (cause, target) in CANNED.items()
        if quote in p["text"]
    ]
    grades = [
        {"record": r["id"], "grade": "wrong", "call": WRONG[r["id"]], "reason": "the tests ran and passed"}
        if r["id"] in WRONG
        else {"record": r["id"], "grade": "worth-it"}
        for r in ev["records"]
    ]
    return {"findings": found, "grades": grades}


def ask(_key, message, agent):
    ev = _evidence(message)
    if agent == "retro-review":
        said = {"verdict": "survive", "why": "shared in two families", "risks": [], "publishable": SHOWN}
    elif "mechanisms" in ev:
        known = [m["id"] for m in ev["mechanisms"]]
        said = {"assign": {f["id"]: known[0] if known else "new:a" for f in ev["findings"]}, "new": {"a": "one reason"}}
    else:
        said = _judged(ev)
    return Paid(json.dumps(said), 1.0, 1.0)


def _real_fixture(spec, run, project="p1"):
    """Use fixture evidence as separate real Change units, rather than running synthetic Retro."""
    rev = syn.install(spec)
    old, uid = syn.unit_id(spec), f"chg:{project}:{spec['name']}"
    work = syn.work(spec, rev, run, ask)

    def move(table):
        unit = table["units"].pop(old)
        unit.update(provenance="real", assumptions=[], family=uid)
        table["units"][uid] = unit

    retro_store.update(move)
    work.uid, work.unit, work.provenance = uid, retro_store.known()[uid], "real"
    for record in work.records:
        record.update(project=project, change=spec["name"], step="build", provenance="real")
    return work


def test_real_fixture_units_yield_every_proposal_kind_reviewed_and_reset_hides_retired_findings():
    for n, spec in enumerate(syn.specs()):
        work = _real_fixture(spec, f"run-{n}")
        retro_judge.run(work)
        units.settle(work.uid, work.rev["rev"], "judged", run=f"run-{n}")

    shown = {p["kind"]: p for p in props.proposals()}
    assert set(shown) == {"lesson", "agent-change", "delivery-change", "spotter-case", "look-reconsider"}
    assert all(p["verdict"] == "survive" and p["state"] == "waiting" for p in shown.values())
    assert all(assumptions.RETRO_SYNTHETIC not in p["assumptions"] for p in shown.values())
    assert shown["agent-change"]["target"] == "skill:w-build"
    assert shown["delivery-change"]["target"] == "tool:edit"
    assert shown["spotter-case"]["record"] == "syn-edit-lost-2"
    gap = retro_store.findings(unit="chg:p1:gap")
    assert [f["status"] for f in gap] == ["unknown"]
    assert len(retro_store.grades()) == sum(len(s["records"]) for s in syn.specs())

    assumptions.reset()

    assert props.proposals() == []
    assert retro_store.findings() == []
    assert retro_store.grades() == []


def test_two_real_scout_changes_make_one_agent_change_in_their_projects_backlog(tmp_path):
    for n, name in enumerate(("scout-a", "scout-b")):
        spec = syn.specs(name)[0]
        work = _real_fixture(spec, f"run-{n}", project="p2")
        retro_judge.run(work)
        units.settle(work.uid, work.rev["rev"], "judged", run=f"run-{n}")

    (change,) = [p for p in props.proposals() if p["kind"] == "agent-change"]
    assert (change["target"], change["state"]) == ("agent:scout", "waiting")
    agents = tmp_path / "example" / ".github" / "agents"
    agents.mkdir(parents=True)
    (agents / "scout.agent.md").write_text("Scout")
    places = {
        "p1": targets.Place(folder="work", clone=tmp_path / "work"),
        "p2": targets.Place(folder="example", clone=tmp_path / "example"),
    }
    assert targets.projects(change, places, targets.units_of()) == ["p2", "p2"]
    got = targets.resolve(change, places, tmp_path / "shared")
    assert (got["kind"], got["project"]) == ("backlog", "p2")


def test_the_large_unit_needs_two_judging_batches_and_an_unchanged_unit_keeps_its_revision():
    spec = syn.specs("large")[0]
    rev = syn.install(spec)
    w = syn.work(spec, rev, "run-1", ask)

    assert len(retro_judge.batches(w, w.records)) >= 2
    assert syn.install(spec)["rev"] == rev["rev"]
    assert units.folder(syn.session(spec)).is_relative_to(retro_store.place())


def test_the_command_refuses_synthetic_runs_and_plans_without_queueing(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["improvement", "retro", "run", "--synthetic", "large"])
    assert exc.value.code != 0
    assert cli.main(["improvement", "retro", "run", "--change", "nowhere/x"]) == 1
    capsys.readouterr()

    assert cli.main(["improvement", "retro", "status", "--plan", "syn:large"]) == 1
    assert "synthetic Retro is retired" in capsys.readouterr().out
    assert retro_store.queued() == []


def test_a_change_named_by_its_folder_is_planned_under_its_projects_id_and_a_bad_name_is_refused(
    monkeypatch, tmp_path, capsys
):
    project = SimpleNamespace(id="p1", path=str(tmp_path / "work"))
    monkeypatch.setattr(registry, "load", lambda: SimpleNamespace(projects=[project]))
    monkeypatch.setattr(Store, "open", lambda _path: "store")
    monkeypatch.setattr(retro_evidence, "plan", lambda uid, projects: {"uid": uid, "projects": sorted(projects)})
    for named in ("chg:work:fix-it", "work/fix-it", "chg:p1:fix-it"):
        assert cli.main(["improvement", "retro", "status", "--plan", named]) == 0
        assert json.loads(capsys.readouterr().out) == {"uid": "chg:p1:fix-it", "projects": ["p1"]}

    def unreadable(_path):
        msg = "the store is unreadable"
        raise StoreError(msg)

    monkeypatch.setattr(Store, "open", unreadable)
    for named in ("chg:p1", "chg:p1:fix-it"):
        assert cli.main(["improvement", "retro", "status", "--plan", named]) == 1
    assert capsys.readouterr().out.count("refused: ") == 2
