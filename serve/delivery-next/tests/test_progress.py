from dataclasses import asdict
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from owlbear_delivery_next.change_contracts.failures import cause_key
from owlbear_delivery_next.change_contracts.models import (
    VISUAL,
    Brief,
    Change,
    ErrorKind,
    Exit,
    Intent,
    Plan,
    Step,
    StepKind,
    Task,
    VisualState,
)
from owlbear_delivery_next.change_contracts.visual_records import VisualRound
from owlbear_delivery_next.change_flow import budgets
from owlbear_delivery_next.change_flow.loop import StepResult
from owlbear_delivery_next.change_flow.progress import progress
from owlbear_delivery_next.change_flow.status import Activity
from owlbear_delivery_next.project_host import api
from owlbear_delivery_next.state_store.store import Lock, Store
from owlbear_delivery_next.workflow_steps import decision

NOW = datetime(2026, 10, 15, 12, tzinfo=UTC)
FOUR = [Task(id=f"t{i}", title=f"part {i}", scope=[f"src/{i}"], done=i == 1) for i in range(1, 5)]


def states(c: Change) -> dict[str, str]:
    return {s.key: s.state for s in progress(c).stages}


def reviewing(fix_rounds: int) -> Change:
    """Task 2 of 4 after *fix_rounds* review verdicts sent it back to fixing, each fix repairing the last."""
    fixes = [
        Task(id=f"t{5 + i}", title="Fix 1 review finding(s)", scope=["src/2"], origin="review", fixes=f"t{4 + i}")
        for i in range(fix_rounds)
    ]
    fixes[0] = fixes[0].model_copy(update={"fixes": "t2"})
    c = Change(slug="c1", plan=Plan(tasks=FOUR + fixes), step=Step(kind=StepKind.REVIEW, task=fixes[-1].id))
    c.budgets.loops[budgets.round_key(c)] = fix_rounds
    return c


def test_a_new_change_is_shaping_with_no_round():
    p = progress(Change(slug="c1"))

    assert (p.current, p.line, p.round, p.task) == ("shape", "Shape", 1, None)
    assert states(Change(slug="c1")) == {
        "shape": "current",
        "plan": "upcoming",
        "build": "upcoming",
        "final": "upcoming",
        "publish": "upcoming",
        "visual": "skipped",
        "checks": "skipped",
        "merge": "upcoming",
    }


def test_one_plan_challenge_makes_planning_round_two():
    c = Change(slug="c1", step=Step(kind=StepKind.PLAN))
    budgets.retry(c, StepResult(exit=Exit.RETRY, reason="plan challenge: task 3 has no check"), NOW)

    p = progress(c)

    assert p.line == "Plan · Re-planning after the plan challenge · round 2"
    assert [(s.key, s.state, s.rounds) for s in p.stages[:3]] == [
        ("shape", "done", 1),
        ("plan", "current", 2),
        ("build", "upcoming", 1),
    ]


def test_build_task_two_of_four_in_its_fourth_review_round():
    c = reviewing(3)
    p = progress(c)

    assert p.line == "Build · Task 2 of 4 · Task review · round 4"
    assert (p.task, p.tasks, p.sub, p.round) == (2, 4, "Task review", 4)
    assert next(s for s in p.stages if s.key == "build").rounds == 4
    c.step = Step(kind=StepKind.BUILD, task="t7")
    assert progress(c).line == "Build · Task 2 of 4 · Fixing review findings · round 4"


def test_a_first_build_names_only_its_task():
    c = Change(slug="c1", plan=Plan(tasks=FOUR), step=Step(kind=StepKind.BUILD, task="t2"))
    assert progress(c).line == "Build · Task 2 of 4"


def test_an_integration_inside_a_loop_shows_that_loops_round():
    c = reviewing(3)
    c.step = Step(kind=StepKind.INTEGRATE, mode=StepKind.REVIEW, task=c.step.task)
    p = progress(c)

    assert (p.line, p.round) == ("Build · Task 2 of 4 · Updating with the target · round 4", 4)
    c.budgets.loops["final"] = 2
    c.step = Step(kind=StepKind.INTEGRATE, mode=StepKind.REVIEW)  # the final review's third round
    assert progress(c).line == "Final review · Updating with the target · round 3"


@pytest.mark.parametrize(
    "cause",
    [
        cause_key(ErrorKind.LIVENESS, StepKind.REVIEW, "session-ended"),  # a crash
        cause_key(ErrorKind.TOOLING, StepKind.REVIEW, "sdk"),  # a Delivery defect
        cause_key(ErrorKind.NETWORK, StepKind.REVIEW, "sdk"),  # a network wait
    ],
)
def test_a_retry_after_a_crash_or_a_network_wait_is_not_a_round(cause):
    c = reviewing(1)
    before = progress(c)

    budgets.retry(c, StepResult(exit=Exit.RETRY, cause=cause, reason="session ended"), NOW)

    assert c.budgets.causes  # the retry was counted, as a retry
    assert progress(c) == before
    assert before.line == "Build · Task 2 of 4 · Task review · round 2"


def test_a_failed_visual_check_loops_back_through_the_build_and_counts_its_round():
    brief = Brief(visual=[VisualState(name="home", path="/", expect="a greeting")])
    c = Change(slug="c1", brief=brief, plan=Plan(tasks=[t.model_copy(update={"done": True}) for t in FOUR]))
    fix = decision.repair(c, "Fix: the visual check of abc1234 failed: the greeting is cut off", ["cut off"]).fix_task
    c.plan.tasks.append(fix)
    c.visual_rounds.append(VisualRound(number=1, head="a" * 40, tree="b" * 40, outcome="back", at=NOW))
    c.step = Step(kind=StepKind.BUILD, task=fix.id)

    fixing = progress(c)

    assert fixing.line == "Build · Fixing visual findings · round 2"
    assert {s.key: (s.state, s.rounds) for s in fixing.stages}["visual"] == ("upcoming", 2)
    c.plan.tasks[-1].done, c.step = True, Step(kind=StepKind.CHECK, task=VISUAL)
    again = progress(c)
    assert again.line == "Visual check · Visual review · round 2"
    assert [s.state for s in again.stages] == ["done"] * 5 + ["current", "skipped", "upcoming"]


def test_a_final_review_repair_counts_the_final_reviews_round():
    fix = Task(id="t5", title="Fix 2 review finding(s) of the final review", origin="review")
    c = Change(slug="c1", plan=Plan(tasks=[*FOUR, fix]), step=Step(kind=StepKind.BUILD, task="t5"))
    c.budgets.loops["final"] = 1

    assert progress(c).line == "Build · Fixing final review findings · round 2"
    c.step = Step(kind=StepKind.REVIEW, mode="final")
    assert progress(c).line == "Final review · round 2"


def test_a_merged_change_has_every_needed_stage_done_and_an_abandoned_one_none():
    done = Change(slug="c1", step=Step(kind=StepKind.CLEANUP), finished_at=NOW)
    gone = done.model_copy(
        update={"intent": Intent(abandoned_at=NOW), "step": Step(kind=StepKind.CLEANUP, mode="abandon")}
    )

    assert set(states(done).values()) == {"done", "skipped"}
    assert states(done)["merge"] == "done"
    assert set(states(gone).values()) == {"skipped"}
    assert progress(done).line is progress(gone).line is None


class Host:
    maintenance = None
    wake = SimpleNamespace(set=lambda: None)
    record = None

    def activity(self, _slug):
        return Activity(host_up=True)


def test_the_change_list_and_detail_carry_the_progress(tmp_path):
    store = Store(tmp_path)
    c = reviewing(3)
    store.write(Lock("c1"), c)
    http = TestClient(
        api.create_app(store, "t", Host()), base_url="http://127.0.0.1", headers={"authorization": "Bearer t"}
    )

    listed = http.get("/api/next/changes").json()[0]["progress"]
    detail = http.get("/api/next/changes/c1").json()["progress"]

    assert listed == detail == asdict(progress(c))
    assert detail["line"] == "Build · Task 2 of 4 · Task review · round 4"
    assert detail["stages"][2] == {"key": "build", "label": "Build", "state": "current", "rounds": 4}


def test_the_shown_round_never_drops_and_a_passed_review_keeps_its_badge():
    c = reviewing(3)
    key = budgets.round_key(c)
    c.budgets.rounds[key] = 0  # the review budget restarted after progress; the loops it counted stay
    assert progress(c).round == 4
    c.budgets.rounds.pop(key, None)  # the review passed: its budget entry is dropped
    c.step = Step(kind=StepKind.REVIEW)  # on to the final review
    assert next(s for s in progress(c).stages if s.key == "build").rounds == 4
