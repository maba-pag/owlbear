"""The picked set at work (TD-452, TD-456, TD-457): every role gets it, challengers the complete list.

A brief is shaped, picked and approved through the host API (`picking`); the Change then runs its next steps, where a
decision new since the pick goes to the picker.
"""

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from owlbear_decisions import Decision, Link, LinkType, Origin, Scope, State, new_id, write
from owlbear_delivery_next.change_contracts import pick_tools, tools
from owlbear_delivery_next.change_contracts.decision_records import Pick
from owlbear_delivery_next.change_contracts.dispute_tools import ReconsiderResult
from owlbear_delivery_next.change_contracts.failures import cause_key
from owlbear_delivery_next.change_contracts.inbox import AnswerItem
from owlbear_delivery_next.change_contracts.models import Change, ErrorKind, Exit, Plan, Step, StepKind, Task
from owlbear_delivery_next.change_contracts.profile_record import Profile
from owlbear_delivery_next.change_flow import brief_rounds, loop
from owlbear_delivery_next.commands import runner
from owlbear_delivery_next.local_system.processes import Termination
from owlbear_delivery_next.project_host import session_slots
from owlbear_delivery_next.runtimes import step_decisions, step_input
from owlbear_delivery_next.runtimes.session_result import Run
from owlbear_delivery_next.state_store.store import Lock
from owlbear_delivery_next.workflow_steps import decisions_gate, pick, plan_round, reconsider, sessions

AT = datetime(2026, 10, 21, 9, tzinfo=UTC)
PROJECT = "shop-site"


def make(**changes) -> Decision:
    fields = {
        "id": new_id(), "title": "Pages are plain HTML", "statement": "The pages are plain HTML with no build step.",
        "scope": Scope.PROJECT, "project": PROJECT, "origin": Origin.APPROVED, "actor": "shaper",
        "state": State.IN_FORCE, "created_at": AT, "topic": "pages",
    }  # fmt: skip
    return Decision(**{**fields, **changes})


def picked(*ids: str) -> pick_tools.PickResult:
    return pick_tools.PickResult(picked=[{"id": i, "note": "it governs the work"} for i in ids])


def line(d: Decision) -> str:
    return step_decisions.entry(d)


def prepared(picking, monkeypatch, *chosen: Decision, between: Callable[[], object] | None = None):
    """Run the actual pick; its unrelated clean challenge uses the domain producer, not another SDK journey."""
    picking.save()
    assert picking.ask(1).status_code == 200
    picking.picks.append(picked(*(d.id for d in chosen)))
    c = pick.run(picking.store, Lock(picking.slug), picking.change())
    brief_rounds.counted(c, [], {}, AT)
    picking.store.write(Lock(picking.slug), c)
    if between is not None:
        between()
    assert picking.approve(1).status_code == 200
    return recording(picking, monkeypatch)


def recording(picking, monkeypatch):
    c = picking.approved()
    c.plan = Plan(tasks=[Task(id="t1", title="Add farewell", scope=["packages/app"], checks=["true"])])
    c.step = Step(kind=StepKind.BUILD, task="t1")
    picking.store.write(Lock(picking.slug), c)
    held: list[tuple[list[str], list[str]]] = []

    def record(*_a) -> None:
        held.append((step_decisions.held(), step_decisions.held(complete=True)))

    monkeypatch.setattr(runner, "_agent", record)
    monkeypatch.setattr(runner, "_engine", record)
    return held


def advance(picking, at: datetime | None = None):
    c = picking.change()
    runner._step(picking.store, Lock(picking.slug), c, loop.next_step(c, at or AT), picking.repo)  # noqa: SLF001
    return picking.change()


def test_every_role_gets_exactly_the_picked_set_and_the_changes_own_and_challengers_the_complete_list(
    picking, monkeypatch
):
    rule, general = picking.put(make()), picking.put(make(scope=Scope.GLOBAL, project="", title="Ask one question"))
    other = picking.put(make(title="Invoices are PDF", topic="billing", statement="Invoices are sent as PDF."))
    picking.save()
    assert picking.ask(1).status_code == 200
    picking.picks.append(picked(rule.id, general.id))
    picking.verdicts.append(tools.ReviewResult(verdict="pass"))
    picking.step()
    assert picking.approve(1).status_code == 200
    held = recording(picking, monkeypatch)
    _, judge = picking.told
    said = judge.message  # the brief challenger: the pick, then the complete list (TD-452)
    assert said.index(line(rule)) < said.index(step_decisions.COMPLETE) < said.index(line(other))
    own = make(scope=Scope.CHANGE, change=f"{picking.change().brief.approved_at:%Y%m%d-%H%M%S}-{picking.slug}",
               title="Farewell is short", statement="The farewell is one word.")  # fmt: skip
    write(own, picking.shared.root / PROJECT / "changes" / own.change)

    assert advance(picking).outcome is None

    [(worker, challenger)] = held
    entries = [x for x in worker if x.startswith("- D-")]
    assert sorted(entries) == sorted([line(rule), line(general), line(own)])  # its own attach without a pick
    assert line(other) not in worker
    assert challenger[: len(worker)] == worker
    assert challenger[len(worker) :] == ["", step_decisions.COMPLETE, line(other)]
    assert len(picking.pickers()) == 1  # its own decision needed no picker
    c = picking.change()
    assert (c.decisions_baseline.picked, set(c.decisions_baseline.said)) == (True, {rule.id, general.id, own.id})
    with step_decisions.using(worker, challenger[len(worker) :]):
        planned = Plan(tasks=[Task(id="t1", title="Add", scope=["packages/app"], checks=["true"])])
        plan = step_input.plan_challenge(c, planned, Profile(), Path(), {})
        tree = SimpleNamespace(base="a" * 40, head="b" * 40, changed=())
        review = step_input.review(c, None, Path(), tree)
        build = step_input.build(c, c.plan.tasks[0], Path(), [])
    assert all(line(other) in m and step_decisions.COMPLETE in m for m in (plan, review))
    assert line(rule) in build
    assert line(other) not in build  # the worker reads the picked set only


def test_a_decision_activated_elsewhere_is_picked_at_the_next_boundary_and_an_unchanged_one_calls_no_picker(
    picking, monkeypatch
):
    rule = picking.put(make())
    held = prepared(picking, monkeypatch, rule)
    assert advance(picking).outcome is None
    assert len(picking.pickers()) == 1  # an unchanged boundary picks nothing
    governs = picking.put(make(title="Farewells are polite", statement="Farewells say thank you."))
    unrelated = picking.put(make(title="Invoices are PDF", topic="billing", statement="Invoices are sent as PDF."))
    picking.picks.append(picked(governs.id))

    c = advance(picking)

    assert (c.outcome, loop.open_question(c)) == (None, None)  # no owner question
    later = picking.pickers()[-1]
    assert (len(picking.pickers()), later.model, later.effort) == (2, "gpt-6.1-sol", "medium")
    assert later.message.startswith(pick.LATER)
    rows = later.message.split("## Decisions")[1]
    assert (governs.id in rows, unrelated.id in rows, rule.id in rows) == (True, True, False)  # only the new ones
    pin = c.decisions_baseline
    assert set(pin.said) == {rule.id, governs.id}
    assert pin.revisions[unrelated.id] == unrelated.rule_revision  # considered, not picked
    assert pin.session == ""
    assert c.spend.credits == 12.0  # the shaping pick and this one
    worker, _ = held[-1]
    assert (line(governs) in worker, line(unrelated) in worker) == (True, False)

    assert advance(picking).outcome is None
    assert len(picking.pickers()) == 2  # nothing new since: no picker call


def test_a_replaced_pinned_decision_asks_the_owner_and_its_successor_goes_to_the_picker(picking, monkeypatch):
    rule = picking.put(make())
    prepared(picking, monkeypatch, rule)
    successor = picking.put(make(statement="The pages are plain HTML and CSS.",
                                 links=(Link(type=LinkType.REPLACES, target=rule.id),)))  # fmt: skip
    write(rule.model_copy(update={"state": State.REPLACED}), picking.shared.root / PROJECT, rule.revision)

    c = advance(picking)

    q = loop.open_question(c)
    assert q.cause.startswith("decisions:build:")
    assert f"no longer in force: {rule.id}" in q.text
    assert len(picking.pickers()) == 1
    c, _ = loop.schedule(c, [AnswerItem(at=AT, question=q.id, option="continue")], AT)
    picking.store.write(Lock(picking.slug), c)
    picking.picks.append(picked(successor.id))
    assert advance(picking).outcome is None
    assert set(picking.change().decisions_baseline.said) == {successor.id}


@pytest.mark.parametrize("governs", [False, True], ids=["unrelated", "governing"])
def test_decisions_the_pick_did_not_read_pass_approval_and_go_to_the_next_steps_picker(picking, monkeypatch, governs):
    rule = picking.put(make())
    other = picking.put(make(title="Invoices are PDF", topic="billing", statement="Invoices are sent as PDF."))
    new = (
        make(title="Farewells are polite", statement="Farewells say thank you.")
        if governs
        else make(title="Receipts are numbered", topic="billing", statement="Receipts carry a running number.")
    )
    renamed = other.model_copy(update={"title": "Invoices are PDF files"})

    def between() -> None:
        picking.put(new)
        write(renamed, picking.shared.root / PROJECT, other.revision)

    held = prepared(picking, monkeypatch, rule, between=between)
    pin = picking.change().decisions_baseline
    assert (pin.picked, set(pin.said)) == (True, {rule.id})
    assert pin.revisions == {rule.id: rule.rule_revision, other.id: other.rule_revision}  # what the pick read
    picking.picks.append(picked(new.id) if governs else picked())

    c = advance(picking)

    assert c.outcome is None
    context, rows = picking.pickers()[-1].message.split("## Decisions")
    assert (len(picking.pickers()), new.id in rows, other.id in rows, rule.id in rows) == (2, True, True, False)
    assert (
        context.split("## The work's rules so far (context, not to judge)\n")[1].strip()
        == f"{rule.id} | {rule.statement}"
    )
    pin = c.decisions_baseline
    assert pin.revisions[other.id] == renamed.rule_revision  # considered at its new revision
    assert (new.id in pin.said, pin.revisions[new.id]) == (governs, new.rule_revision)
    [(worker, _)] = held
    assert (line(new) in worker, line(rule) in worker) == (governs, True)
    (event,) = [e for e in picking.store.events(picking.slug) if e.get("reassessed")]
    assert sorted(event["reassessed"]) == sorted([new.id, other.id])
    assert picking.approve(1).status_code == 200  # a retried approval keeps what was judged since
    again = picking.change().decisions_baseline
    assert (again.said, again.revisions) == (pin.said, pin.revisions)


def test_a_pick_approved_while_the_decisions_did_not_load_offers_its_rule_as_it_stands_and_pins_that(
    picking, monkeypatch, tmp_path
):
    rule, data, away = picking.put(make()), picking.shared.root / PROJECT, tmp_path / "away"
    prepared(picking, monkeypatch, rule, between=lambda: data.rename(away))
    assert picking.change().decisions_unpinned_at is not None
    away.rename(data)
    renamed = rule.model_copy(update={"title": "Pages are plain HTML files"})
    write(renamed, data, rule.revision)

    q = loop.open_question(advance(picking))

    assert f"{rule.id} Pages are plain HTML files:" in q.text
    c, _ = loop.schedule(picking.change(), [AnswerItem(at=AT, question=q.id, option="continue")], AT)
    picking.store.write(Lock(picking.slug), c)
    assert advance(picking).outcome is None  # no second question
    assert picking.change().decisions_baseline.revisions[rule.id] == renamed.rule_revision


@pytest.mark.parametrize("fate", ["changed", "withdrawn"])
def test_a_picked_decision_changed_or_withdrawn_before_approval_asks_the_owner_at_the_next_step(
    picking, monkeypatch, fate
):
    rule = picking.put(make())
    update = {"title": "Pages are plain HTML files"} if fate == "changed" else {"state": State.WITHDRAWN}

    def between() -> None:
        write(rule.model_copy(update=update), picking.shared.root / PROJECT, rule.revision)

    held = prepared(picking, monkeypatch, rule, between=between)

    c = advance(picking)

    q = loop.open_question(c)
    assert q.cause.startswith("decisions:build:")
    gone = f"no longer in force: {rule.id}"
    assert (f"changed: {rule.id} Pages are plain HTML files: was" if fate == "changed" else gone) in q.text
    assert rule.statement in q.text  # the wording the pick read
    assert (held, len(picking.pickers())) == ([], 1)
    assert picking.approve(1).status_code == 200  # a retried approval keeps the question's offer
    c, _ = loop.schedule(picking.change(), [AnswerItem(at=AT, question=q.id, option="continue")], AT)
    picking.store.write(Lock(picking.slug), c)
    assert advance(picking).outcome is None  # Continue took the change in: not asked again


def test_a_pick_saved_before_it_recorded_what_it_read_counts_only_its_picks_as_read(picking, monkeypatch):
    rule = picking.put(make())
    other = picking.put(make(title="Invoices are PDF", topic="billing", statement="Invoices are sent as PDF."))
    new = make(title="Farewells are polite", statement="Farewells say thank you.")

    def between() -> None:
        c = picking.change()
        c.brief.picked = Pick.model_validate(c.brief.picked.model_dump(exclude={"read"}))  # as older releases saved
        picking.store.write(Lock(picking.slug), c)
        picking.put(new)

    prepared(picking, monkeypatch, rule, between=between)
    assert picking.change().decisions_baseline.revisions == {rule.id: rule.rule_revision}
    picking.picks.append(picked())

    c = advance(picking)

    assert c.outcome is None
    rows = picking.pickers()[-1].message.split("## Decisions")[1]
    assert (new.id in rows, other.id in rows, rule.id in rows) == (True, True, False)  # every other one, once
    assert set(c.decisions_baseline.revisions) == {rule.id, other.id, new.id}
    assert advance(picking).outcome is None
    assert len(picking.pickers()) == 2


def test_a_failed_pick_at_a_boundary_waits_and_tries_again_never_taking_it_for_none_apply(picking, monkeypatch):
    rule = picking.put(make())
    held = prepared(picking, monkeypatch, rule)
    new = picking.put(make(title="Farewells are polite", statement="Farewells say thank you."))
    picking.picks.append("error")

    c = advance(picking)

    assert held == []  # no step ran on a set that misses it
    assert (c.stop, c.outcome.exit, c.outcome.cause) == (None, Exit.PENDING, f"{ErrorKind.NETWORK}:build:{pick.LABEL}")
    assert "could not be put to the picker" in c.outcome.reason
    assert loop.next_step(c, c.outcome.at) is None  # it waits
    assert new.id not in c.decisions_baseline.revisions  # not recorded as considered
    assert c.decisions_baseline.session == ""
    picking.picks.append(picked())

    c = advance(picking, c.outcome.wake_at)

    assert len(held) == 1  # the step ran once the pick succeeded
    assert (len(picking.pickers()), new.id in c.decisions_baseline.said) == (3, False)
    assert c.decisions_baseline.revisions[new.id] == new.rule_revision


@pytest.mark.parametrize("pinned", [True, False])
def test_a_change_approved_without_a_pick_keeps_every_decision_in_force(picking, monkeypatch, pinned):
    rule = picking.put(make())
    held = prepared(picking, monkeypatch, rule)
    c = picking.change()
    c.brief.picked = None  # approved before picking
    c.decisions_baseline = None if not pinned else c.decisions_baseline.model_copy(update={"picked": False})
    picking.store.write(Lock(picking.slug), c)
    other = picking.put(make(title="Invoices are PDF", topic="billing", statement="Invoices are sent as PDF."))

    c = advance(picking)

    if pinned:  # a new decision asks the owner, as before picking existed
        assert f"new: {other.id}" in loop.open_question(c).text
        return
    worker, _ = held[-1]
    assert (line(rule) in worker, line(other) in worker, len(picking.pickers())) == (True, True, 1)


@pytest.mark.parametrize("kind", [StepKind.PUBLISH, StepKind.MERGE])
def test_a_decision_new_at_a_step_without_an_agent_waits_for_a_session_then_is_picked(picking, monkeypatch, kind):
    rule = picking.put(make())
    held = prepared(picking, monkeypatch, rule)
    c = picking.change()
    c.step = Step(kind=kind)
    picking.store.write(Lock(picking.slug), c)
    new = picking.put(make(title="Farewells are polite", statement="Farewells say thank you."))
    monkeypatch.setattr(sessions, "GRANT", session_slots.wanted(c, c.step))  # what the host grants it: none

    c = advance(picking)  # no SessionGrantError escapes: the host would record a runner gone, again and again

    assert (sessions.GRANT, held, len(picking.pickers()), c.stop) == (0, [], 1, None)
    assert (c.outcome.exit, c.outcome.cause) == (Exit.PENDING, f"{ErrorKind.NETWORK}:{kind}:{pick.LABEL}")
    step = loop.next_step(c, c.outcome.wake_at)
    assert (step.kind, session_slots.wanted(c, step)) == (kind, 1)  # the host grants its pick a session
    monkeypatch.setattr(sessions, "GRANT", 1)
    picking.picks.append(picked(new.id))

    c = advance(picking, c.outcome.wake_at)

    assert (len(held), len(picking.pickers()), new.id in c.decisions_baseline.said) == (1, 2, True)


def verdict(*places: str, upheld: dict[str, bool] | None = None) -> tools.ReviewResult:
    judged = [{"finding": k, "upheld": u, "reason": "see AC-1"} for k, u in (upheld or {}).items()]
    found = [{"place": p, "problem": "untestable", "fix": "name the output"} for p in places]
    return tools.ReviewResult(verdict="fix" if places else "pass", findings=found, rechecked=judged)


def test_a_brief_reconsideration_reads_the_pick_beside_the_complete_list(picking):
    rule = picking.put(make())
    other = picking.put(make(title="Invoices are PDF", topic="billing", statement="Invoices are sent as PDF."))
    picking.save()
    picking.ask(1)
    clarified = [{"finding": "F1", "verdict": "clarified", "text": "AC-1: name the exact text", "reason": "r"}]
    picking.picks.append(picked(rule.id))
    picking.verdicts += [verdict("AC-1"), verdict(upheld={"F1": True}), ReconsiderResult(reconsidered=clarified)]
    picking.step()
    picking.ask(1, {"F1": "no"})
    q = loop.open_question(picking.step())
    picking.store.put_inbox(picking.slug, AnswerItem(at=AT, question=q.id, option="reconsider", text="narrow it"))
    picking.approved()  # folds the answer

    picking.step()

    said = picking.told[-1].message
    assert said.startswith("You reconsider brief challenge findings")
    assert said.index(line(rule)) < said.index(step_decisions.COMPLETE) < said.index(line(other))


@pytest.mark.parametrize("which", ["plan", "code"])
def test_plan_and_code_reconsiderations_read_the_complete_list(which):
    rule, other = make(), make(title="Invoices are PDF", topic="billing", statement="Invoices are sent as PDF.")
    task = Task(id="t1", title="Add farewell")
    c = Change(slug="c1", plan=Plan(tasks=[task]))

    with step_decisions.using(step_decisions.section([rule]), step_decisions.complete([other])):  # the runner's gate
        said = plan_round.prompt(c, Path()) if which == "plan" else reconsider.prompt(c, task, Path())

    assert said.index(line(rule)) < said.index(step_decisions.COMPLETE) < said.index(line(other))


# trigger words in a note leave the gate's cause as it was (#971)
NOTE = "while reading the corrections log; the request timed out over quota"


def _session_said(ending: str, payload: pick_tools.PickResult | None = None, **fields):
    async def run(cfg):
        return Run(cfg.session_id, ending, payload, termination=Termination(confirmed=True), **fields)

    return run


@pytest.mark.parametrize(
    ("said", "why"),
    [
        ("corrections", "OSError: {e}\n" + NOTE),
        ("detail", "its session ended error: {e}"),
        ("usage_unread", "its pick cannot be trusted: {e}"),
    ],
    ids=["corrections", "detail", "usage_unread"],
)
def test_a_failed_pick_at_a_boundary_keeps_its_whole_reason(picking, monkeypatch, whole_error, said, why):
    prepared(picking, monkeypatch, picking.put(make()))
    picking.put(make(title="Farewells are polite", statement="Farewells say thank you."))
    if said == "corrections":
        unreadable = OSError(whole_error)
        unreadable.add_note(NOTE)
        monkeypatch.setattr(pick, "corrections", lambda *_a: (_ for _ in ()).throw(unreadable))
    elif said == "detail":
        monkeypatch.setattr(runner.sdk_adapter, "run", _session_said("error", detail=whole_error))
    else:
        monkeypatch.setattr(runner.sdk_adapter, "run", _session_said("result", picked(), usage_unread=whole_error))

    c = advance(picking)

    reason = f"{decisions_gate.REPICK}: {why.format(e=whole_error)}"
    assert (c.outcome.reason, c.outcome.cause) == (reason, cause_key(ErrorKind.NETWORK, StepKind.BUILD, pick.LABEL))
    (event,) = [e for e in picking.store.events(picking.slug) if e.get("kind") == StepKind.BUILD]
    assert event["reason"] == reason
