"""Code ships no settings defaults (the owner, 2026-10-23): unset values, their errors and the one-time carry."""

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from owlbear_delivery_next.change_contracts.inbox import AnswerItem
from owlbear_delivery_next.change_contracts.models import Brief, Change, Criterion, Plan, Step, StepKind, Task
from owlbear_delivery_next.change_contracts.round_records import RoundLoop
from owlbear_delivery_next.change_flow import loop
from owlbear_delivery_next.commands import runner
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.local_system.slots import Slots
from owlbear_delivery_next.machine_host import curation
from owlbear_delivery_next.settings import carried, config, roles, rounds
from owlbear_delivery_next.settings.config import GlobalLayer, Layer, SettingsUnset, resolve
from owlbear_delivery_next.state_store import settings_carry
from owlbear_delivery_next.state_store.store import StoreError, read_layer
from owlbear_delivery_next.workflow_steps import decision_publication, decisions_gate, lookup, review, unset_settings


@pytest.fixture
def no_base(monkeypatch):
    monkeypatch.setattr(config, "BASE", None)


@pytest.mark.usefixtures("no_base")
def test_a_setting_no_layer_sets_is_unset_and_listed_never_filled_from_code():
    empty = resolve(None, Layer())
    assert (empty.agents, empty.sessions, empty.watcher, empty.final_review) == ({}, None, None, None)
    assert {"agents.builder.model", "agents.watcher.effort", "sessions", "watcher"} <= set(empty.missing)
    inactive = {"runtimes.sdk", "visible", "agents.builder.runtime", "agents.watcher.minutes"}
    inactive |= {"agents.picker.max_rounds"}
    assert not inactive & set(empty.missing)  # nothing reads them, and the page edits none of them
    assert empty.page()["agents"]["builder"]["model"] is None
    assert "sessions" not in empty.sources

    builder = carried.layer().agents["builder"]
    some = resolve(GlobalLayer(agents={"builder": builder}, sessions=3), Layer())
    assert (some.agent("builder").model, some.sessions, some.sources["sessions"]) == ("claude-opus-5.5", 3, "global")
    assert some.final_review is not None  # the final review inherits the builder's rounds
    with pytest.raises(SettingsUnset, match=r"agents\.reviewer\.model") as caught:
        roles.chosen(some, StepKind.REVIEW)
    assert all(k.startswith("agents.reviewer.") for k in caught.value.keys)
    with pytest.raises(SettingsUnset, match="pr_labels"):
        some.need("pr_marker", "pr_labels")
    assert "unset; fill it in" in roles.table(some)


def change(kind: StepKind) -> Change:
    return Change(
        slug="c1",
        brief=Brief(version=1, approved_version=1, challenged=1, criteria=[Criterion(id="AC-1", text="works")]),
        plan=Plan(tasks=[Task(id="t1", title="one", scope=["a"])]),
        step=Step(kind=kind, task="t1" if kind in {StepKind.BUILD, StepKind.REVIEW} else None),
    )


@pytest.mark.parametrize(("kind", "mode"), [(StepKind.REVIEW, None), (StepKind.SHAPE, "challenge")])
def test_a_step_that_needs_an_unset_setting_asks_the_owner_then_runs_the_same_step_again(kind, mode):
    asked = change(kind)
    asked.step.mode = mode
    written: list[Change] = []
    store = SimpleNamespace(read=lambda _slug: written[-1] if written else asked, write=lambda _l, c: written.append(c))
    unset_settings.asked(store, SimpleNamespace(slug="c1"), SettingsUnset(["agents.reviewer.model"]))
    (question,) = written[-1].questions
    assert question.cause == f"state:{kind}:settings-unset"
    assert "agents.reviewer.model" in question.text
    assert [o.id for o in question.options] == ["done", "pause"]

    done, _ = loop.schedule(written[-1], [AnswerItem(at=datetime.now(UTC), question=question.id, option="done")],
                            datetime.now(UTC))  # fmt: skip
    assert (done.step.kind, done.step.task, done.step.mode) == (kind, asked.step.task, mode)


def _git(root, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True).stdout.strip()  # noqa: S603, S607


def test_todays_built_in_values_are_carried_into_global_once_keeping_what_it_sets(shared_repo):
    shared = DataRepo(shared_repo[0])
    shared.global_path.write_text(json.dumps({"format": 2, "agents": {"builder": {"model": "gpt-6-luna"}},
                                              "runtimes": {}, "widths": [1440]}))  # fmt: skip
    _git(shared.root, "add", "-A")
    _git(shared.root, "commit", "-qm", "an old global layer")
    assert settings_carry.due(shared)

    settings_carry.carry(shared)

    glob = read_layer(shared.global_path, GlobalLayer)
    assert (glob.agents["builder"].model, glob.agents["builder"].effort, glob.widths) == (
        "gpt-6-luna",
        "medium",
        [1440],
    )
    assert (glob.agents["watcher"].model, glob.sessions, glob.pr_marker, glob.curator_threshold) == (
        "gpt-6-luna", 2, True, 95)  # fmt: skip
    assert json.loads(shared.global_path.read_text())["format"] == config.CONFIG_FORMAT >= config.CARRIED_FORMAT
    assert _git(shared.root, "log", "-1", "--format=%s") == "settings: today's built-in values carried into Global"
    assert _git(shared.root, "status", "--porcelain") == ""
    head = _git(shared.root, "rev-parse", "HEAD")
    assert (settings_carry.due(shared), settings_carry.carry(shared)) == (False, "")
    assert _git(shared.root, "rev-parse", "HEAD") == head  # once: nothing more


@pytest.mark.usefixtures("no_base")
def test_a_carried_global_resolves_every_setting(shared_repo):
    shared = DataRepo(shared_repo[0])
    settings_carry.carry(shared)  # no Global file yet: today's values in full
    assert resolve(read_layer(shared.global_path, GlobalLayer), Layer()).missing == []


@pytest.mark.usefixtures("no_base")
def test_a_role_needs_only_the_fields_its_work_reads():
    fields = ("model", "effort", "context")
    watcher = carried.layer().agents["watcher"].model_dump(include=set(fields))
    shaper = carried.layer().agents["shaper"].model_dump(include={*fields, *config.RoundPolicy.model_fields})
    agents = {"watcher": config.Agent.model_validate(watcher), "shaper": config.Agent.model_validate(shaper)}
    some = resolve(GlobalLayer(agents=agents), Layer())
    assert (some.agent("watcher").model, some.agent("watcher").minutes) == (carried.MODELS["watcher"].model, None)
    assert some.agent("shaper").max_rounds is not None
    assert not [k for k in some.missing if k.startswith(("agents.watcher.", "agents.shaper."))]
    picker = carried.layer().agents["picker"].model_dump(include=set(fields))
    with pytest.raises(SettingsUnset, match=r"agents\.picker\.minutes"):  # a picker session has a time limit
        resolve(GlobalLayer(agents={"picker": config.Agent.model_validate(picker)}), Layer()).agent("picker")
    assert set(config.used("builder")) == set(config.Effective.model_fields) - {"runtime", "visible", "categories"}


def test_the_decision_gate_asking_for_an_unset_setting_asks_the_owner(monkeypatch):
    asked: list[SettingsUnset] = []
    c = change(StepKind.BUILD)
    store = SimpleNamespace(settings=lambda: None)
    monkeypatch.setattr(decision_publication, "resume", lambda *_a: c)
    monkeypatch.setattr(runner.clarification, "checked", lambda _s, _l, c: c)
    monkeypatch.setattr(unset_settings, "asked", lambda _s, _l, exc: asked.append(exc))

    def gated(*_a):
        raise SettingsUnset(["agents.picker.model"])

    monkeypatch.setattr(decisions_gate, "gated", gated)
    runner._step(store, SimpleNamespace(slug="c1"), c, c.step, None)  # noqa: SLF001
    assert [e.keys for e in asked] == [["agents.picker.model"]]


@pytest.mark.usefixtures("no_base")
def test_curation_never_starts_with_its_threshold_or_role_unset(shared_repo):
    shared = DataRepo(shared_repo[0])
    settings_carry.carry(shared)
    assert curation._unset(lookup.machine(shared)) == ""  # noqa: SLF001
    glob = read_layer(shared.global_path, GlobalLayer)
    shared.global_path.write_text(glob.model_copy(update={"curator_threshold": None}).model_dump_json())
    assert "curator_threshold" in curation._unset(lookup.machine(shared))  # noqa: SLF001
    job = curation.Curation(Slots(lambda: 1), shared=lambda: shared, run=lambda _cfg: pytest.fail("never started"))
    ran = job._session(shared, "shop", datetime.now(UTC), "curate:shop")  # noqa: SLF001 - cleared while it waited
    assert (ran.state, "curator_threshold" in ran.reason, ran.seen) == ("failed", True, {})
    agents = {r: a for r, a in glob.agents.items() if r != "curator"}
    shared.global_path.write_text(glob.model_copy(update={"agents": agents}).model_dump_json())
    assert "agents.curator.model" in curation._unset(lookup.machine(shared))  # noqa: SLF001


def test_a_carry_whose_commit_failed_is_committed_at_the_next_start_never_filled_again(shared_repo, monkeypatch):
    shared = DataRepo(shared_repo[0])
    with monkeypatch.context() as m:
        m.setattr(DataRepo, "publish", lambda *_a: "the commit failed")
        assert settings_carry.carry(shared) == "the commit failed"
    assert _git(shared.root, "status", "--porcelain")  # filled, left uncommitted
    cleared = read_layer(shared.global_path, GlobalLayer).model_copy(update={"sessions": None}).model_dump_json()

    head = _git(shared.root, "rev-parse", "HEAD")
    shared.global_path.write_text("{ not json")  # an invalid layer is never published
    with pytest.raises(StoreError):
        settings_carry.carry(shared)
    assert (_git(shared.root, "rev-parse", "HEAD"), shared.global_path.read_text()) == (head, "{ not json")

    shared.global_path.write_text(cleared)  # the owner cleared a carried value before the retry
    assert settings_carry.due(shared)
    settings_carry.carry(shared)
    assert _git(shared.root, "status", "--porcelain") == ""
    assert _git(shared.root, "log", "-1", "--format=%s") == "settings: today's built-in values carried into Global"
    assert read_layer(shared.global_path, GlobalLayer).sessions is None

    shared.global_path.write_text(read_layer(shared.global_path, GlobalLayer).model_copy(
        update={"sessions": 7}).model_dump_json())  # fmt: skip
    head = _git(shared.root, "rev-parse", "HEAD")
    assert (settings_carry.due(shared), settings_carry.carry(shared)) == (False, "")  # a later edit: a save's to share
    assert _git(shared.root, "rev-parse", "HEAD") == head
    shared.global_path.unlink()  # deleted after the carry committed: never carried again
    assert (settings_carry.due(shared), settings_carry.carry(shared), shared.global_path.exists()) == (False, "", False)
    _git(shared.root, "add", "-A")
    _git(shared.root, "commit", "-qm", "the owner deletes Global")  # a committed deletion too
    assert (settings_carry.due(shared), settings_carry.carry(shared), shared.global_path.exists()) == (False, "", False)


@pytest.mark.usefixtures("no_base")
def test_a_loop_reads_only_round_values_and_a_pinned_loop_never_reads_them_again():
    rounds_only = config.Agent.model_validate(carried.layer().agents["planner"].model_dump(
        include=set(config.RoundPolicy.model_fields)))  # fmt: skip
    settings = resolve(GlobalLayer(agents={"planner": rounds_only}), Layer())
    assert rounds.policy(settings, "plan", "planner").max_rounds == rounds_only.max_rounds  # the model may be unset

    c = change(StepKind.PLAN)
    pinned = rounds.pinned(c, "plan", settings, "planner")
    c.loops["plan"] = RoundLoop(subject="plan", policy=pinned)
    cleared = resolve(None, Layer())  # the owner cleared the planner's rounds since the loop started
    assert rounds.pinned(c, "plan", cleared, "planner") == pinned
    assert rounds.loop(c, "plan", cleared, "planner").policy == pinned
    with pytest.raises(SettingsUnset, match=r"agents\.planner\.max_rounds"):
        rounds.pinned(change(StepKind.PLAN), "plan", cleared, "planner")


@pytest.mark.usefixtures("no_base")
def test_round_values_that_do_not_hold_together_are_refused_while_the_role_is_incomplete():
    bad = config.Agent(max_rounds=3, max_findings=10, last_round_at=8, ask_owner_at=7)  # its model unset
    with pytest.raises(ValidationError, match="must be below"):
        resolve(GlobalLayer(agents={"shaper": bad}), Layer())


@pytest.mark.usefixtures("no_base")
def test_a_worker_that_may_propose_wording_needs_the_challenger_before_it_starts():
    base = carried.layer()
    no_challenger = resolve(base.model_copy(update={"agents": {r: a for r, a in base.agents.items()
                                                                if r != "challenger"}}), Layer())  # fmt: skip
    c = change(StepKind.BUILD)  # AC-1 is generated: the builder may propose its wording
    with pytest.raises(SettingsUnset, match=r"agents\.challenger\."):
        review.started(c, c.plan.tasks[0], Path(), no_challenger)
    assert c.plan.tasks[0].spans == []  # raised before anything changed
    c.brief.specified = ["AC-1"]  # nothing left to propose
    review.started(c, None, Path(), no_challenger)


@pytest.mark.usefixtures("no_base")
def test_the_page_shows_final_review_values_set_while_others_are_unset():
    some = resolve(GlobalLayer(final_review=config.FinalReview(max_rounds=5)), Layer())
    assert some.final_review is None  # a loop needs all four
    assert some.page()["final_review"] == {"max_rounds": 5, "max_findings": None, "last_round_at": None,
                                           "ask_owner_at": None}  # fmt: skip
