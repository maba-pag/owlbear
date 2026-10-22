"""The picked set at work (TD-452, TD-456, TD-457): every role gets it, challengers the complete list.

A brief is shaped, picked and approved through the host API (`picking`); the Change then runs its next steps, where a
decision new since the pick goes to the picker.
"""

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from owlbear_decisions import Decision, Link, LinkType, Origin, Scope, State, new_id, write
from owlbear_delivery_next.change_contracts import pick_tools, tools
from owlbear_delivery_next.change_contracts.dispute_tools import ReconsiderResult
from owlbear_delivery_next.change_contracts.inbox import AnswerItem
from owlbear_delivery_next.change_contracts.models import Change, ErrorKind, Exit, Plan, Step, StepKind, Task
from owlbear_delivery_next.change_contracts.profile_record import Profile
from owlbear_delivery_next.change_flow import loop
from owlbear_delivery_next.commands import runner
from owlbear_delivery_next.project_host import session_slots
from owlbear_delivery_next.runtimes import step_decisions, step_input
from owlbear_delivery_next.state_store.store import Lock
from owlbear_delivery_next.workflow_steps import pick, plan_round, reconsider, sessions

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


class Running:
    """A Change approved on a pick, then at its build step; each step records the sections it held."""

    def __init__(self, picking, monkeypatch, *chosen: Decision) -> None:
        self.p = picking
        picking.save()
        assert picking.ask(1).status_code == 200
        picking.picks.append(picked(*(d.id for d in chosen)))
        picking.verdicts.append(tools.ReviewResult(verdict="pass"))
        picking.step()
        assert picking.approve(1).status_code == 200
        c = picking.approved()
        c.plan = Plan(tasks=[Task(id="t1", title="Add farewell", scope=["packages/app"], checks=["true"])])
        c.step = Step(kind=StepKind.BUILD, task="t1")
        picking.store.write(Lock(picking.slug), c)
        self.held: list[tuple[list[str], list[str]]] = []

        def record(*_a) -> None:
            self.held.append((step_decisions.held(), step_decisions.held(complete=True)))

        monkeypatch.setattr(runner, "_agent", record)
        monkeypatch.setattr(runner, "_engine", record)

    def step(self, at: datetime | None = None):
        c = self.p.change()
        runner._step(self.p.store, Lock(self.p.slug), c, loop.next_step(c, at or AT), self.p.repo)  # noqa: SLF001
        return self.p.change()


def test_every_role_gets_exactly_the_picked_set_and_the_changes_own_and_challengers_the_complete_list(
    picking, monkeypatch
):
    rule, general = picking.put(make()), picking.put(make(scope=Scope.GLOBAL, project="", title="Ask one question"))
    other = picking.put(make(title="Invoices are PDF", topic="billing", statement="Invoices are sent as PDF."))
    run = Running(picking, monkeypatch, rule, general)
    _, judge = picking.told
    said = judge.message  # the brief challenger: the pick, then the complete list (TD-452)
    assert said.index(line(rule)) < said.index(step_decisions.COMPLETE) < said.index(line(other))
    own = make(scope=Scope.CHANGE, change=f"{run.p.change().brief.approved_at:%Y%m%d-%H%M%S}-{run.p.slug}",
               title="Farewell is short", statement="The farewell is one word.")  # fmt: skip
    write(own, picking.shared.root / PROJECT / "changes" / own.change)

    assert run.step().outcome is None

    [(worker, challenger)] = run.held
    entries = [x for x in worker if x.startswith("- D-")]
    assert sorted(entries) == sorted([line(rule), line(general), line(own)])  # its own attach without a pick
    assert line(other) not in worker
    assert challenger[: len(worker)] == worker
    assert challenger[len(worker) :] == ["", step_decisions.COMPLETE, line(other)]
    assert len(picking.pickers()) == 1  # its own decision needed no picker
    c = run.p.change()
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
    run = Running(picking, monkeypatch, rule)
    assert run.step().outcome is None
    assert len(picking.pickers()) == 1  # an unchanged boundary picks nothing
    governs = picking.put(make(title="Farewells are polite", statement="Farewells say thank you."))
    unrelated = picking.put(make(title="Invoices are PDF", topic="billing", statement="Invoices are sent as PDF."))
    picking.picks.append(picked(governs.id))

    c = run.step()

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
    worker, _ = run.held[-1]
    assert (line(governs) in worker, line(unrelated) in worker) == (True, False)

    assert run.step().outcome is None
    assert len(picking.pickers()) == 2  # nothing new since: no picker call


def test_a_replaced_pinned_decision_asks_the_owner_and_its_successor_goes_to_the_picker(picking, monkeypatch):
    rule = picking.put(make())
    run = Running(picking, monkeypatch, rule)
    successor = picking.put(make(statement="The pages are plain HTML and CSS.",
                                 links=(Link(type=LinkType.REPLACES, target=rule.id),)))  # fmt: skip
    write(rule.model_copy(update={"state": State.REPLACED}), picking.shared.root / PROJECT, rule.revision)

    c = run.step()

    q = loop.open_question(c)
    assert q.cause.startswith("decisions:build:")
    assert f"no longer in force: {rule.id}" in q.text
    assert len(picking.pickers()) == 1
    c, _ = loop.schedule(c, [AnswerItem(at=AT, question=q.id, option="continue")], AT)
    picking.store.write(Lock(picking.slug), c)
    picking.picks.append(picked(successor.id))
    assert run.step().outcome is None
    assert set(run.p.change().decisions_baseline.said) == {successor.id}


def test_a_failed_pick_at_a_boundary_waits_and_tries_again_never_taking_it_for_none_apply(picking, monkeypatch):
    rule = picking.put(make())
    run = Running(picking, monkeypatch, rule)
    new = picking.put(make(title="Farewells are polite", statement="Farewells say thank you."))
    picking.picks.append("error")

    c = run.step()

    assert run.held == []  # no step ran on a set that misses it
    assert (c.stop, c.outcome.exit, c.outcome.cause) == (None, Exit.PENDING, f"{ErrorKind.NETWORK}:build:{pick.LABEL}")
    assert "could not be put to the picker" in c.outcome.reason
    assert loop.next_step(c, c.outcome.at) is None  # it waits
    assert new.id not in c.decisions_baseline.revisions  # not recorded as considered
    assert c.decisions_baseline.session == ""
    picking.picks.append(picked())

    c = run.step(c.outcome.wake_at)

    assert len(run.held) == 1  # the step ran once the pick succeeded
    assert (len(picking.pickers()), new.id in c.decisions_baseline.said) == (3, False)
    assert c.decisions_baseline.revisions[new.id] == new.rule_revision


@pytest.mark.parametrize("pinned", [True, False])
def test_a_change_approved_without_a_pick_keeps_every_decision_in_force(picking, monkeypatch, pinned):
    rule = picking.put(make())
    run = Running(picking, monkeypatch, rule)
    c = run.p.change()
    c.brief.picked = None  # approved before picking
    c.decisions_baseline = None if not pinned else c.decisions_baseline.model_copy(update={"picked": False})
    picking.store.write(Lock(picking.slug), c)
    other = picking.put(make(title="Invoices are PDF", topic="billing", statement="Invoices are sent as PDF."))

    c = run.step()

    if pinned:  # a new decision asks the owner, as before picking existed
        assert f"new: {other.id}" in loop.open_question(c).text
        return
    worker, _ = run.held[-1]
    assert (line(rule) in worker, line(other) in worker, len(picking.pickers())) == (True, True, 1)


@pytest.mark.parametrize("kind", [StepKind.PUBLISH, StepKind.MERGE])
def test_a_decision_new_at_a_step_without_an_agent_waits_for_a_session_then_is_picked(picking, monkeypatch, kind):
    rule = picking.put(make())
    run = Running(picking, monkeypatch, rule)
    c = run.p.change()
    c.step = Step(kind=kind)
    picking.store.write(Lock(picking.slug), c)
    new = picking.put(make(title="Farewells are polite", statement="Farewells say thank you."))
    monkeypatch.setattr(sessions, "GRANT", session_slots.wanted(c, c.step))  # what the host grants it: none

    c = run.step()  # no SessionGrantError escapes: the host would record a runner gone, again and again

    assert (sessions.GRANT, run.held, len(picking.pickers()), c.stop) == (0, [], 1, None)
    assert (c.outcome.exit, c.outcome.cause) == (Exit.PENDING, f"{ErrorKind.NETWORK}:{kind}:{pick.LABEL}")
    step = loop.next_step(c, c.outcome.wake_at)
    assert (step.kind, session_slots.wanted(c, step)) == (kind, 1)  # the host grants its pick a session
    monkeypatch.setattr(sessions, "GRANT", 1)
    picking.picks.append(picked(new.id))

    c = run.step(c.outcome.wake_at)

    assert (len(run.held), len(picking.pickers()), new.id in c.decisions_baseline.said) == (1, 2, True)


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
