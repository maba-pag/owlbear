"""Plan checks select the complete directory-qualified commands offered by the project profile."""

from pathlib import Path

import pytest

from owlbear_delivery_next.change_contracts import check_hint, tool_schema, tools
from owlbear_delivery_next.change_contracts.models import Brief, Change, Step, StepKind
from owlbear_delivery_next.change_contracts.permissions import Policy
from owlbear_delivery_next.change_contracts.profile_record import Profile, ProfileEntry
from owlbear_delivery_next.change_contracts.tools import PlanResult, Worktree
from owlbear_delivery_next.runtimes import sdk_adapter, step_input
from owlbear_delivery_next.runtimes.results import Gate
from owlbear_delivery_next.runtimes.session_result import Run

APP = (("packages/app", "npm test"),)
CHOICE = "cd ./packages/app && {\nnpm test\n}"
PROFILE = f'use one of "{CHOICE}"'


def errors(check: str, packages=APP) -> tuple[list[str], list[str]]:
    plan, _ = tool_schema.parse(
        PlanResult, {"tasks": [{"title": "t", "goal": "AC-1", "scope": ["packages/app"], "checks": [check]}]}
    )
    found = tools.check_plan(plan, Worktree("a", "a"), [CHOICE], (), packages)
    return plan.tasks[0].checks, found


@pytest.mark.parametrize(
    ("check", "said"),
    [
        ("npm test", PROFILE),
        ("cd ./packages/app/ && npm test", PROFILE),
        ("cd 'packages/app' &&npm test", PROFILE),
        ("npm --prefix packages/app test", PROFILE),
        ("cd packages/other && npm test", PROFILE),
        ("cd packages && npm test", PROFILE),
        ("cd packages/app && npm run test", PROFILE),
        ("cd packages/app && npm test && rm -rf x", PROFILE),
        ("cd packages/app; npm test", PROFILE),
        ("cd packages/frontend-components-library; npm test", PROFILE),  # answered at once, however long
    ],
)
def test_a_check_not_offered_by_the_profile_is_refused_with_the_choice(check, said):
    assert errors(check) == ([check], [f'tasks[0].checks: "{check}" is not a check of the project profile - {said}'])


def test_the_hint_needs_the_profile_s_packages():
    assert errors("npm test", ())[1][0].endswith(PROFILE)
    assert errors(CHOICE) == ([CHOICE], [])
    target = "cd ./packages/app && {\nnpm test -- tests/metrics.test.js\n}"
    assert errors(target) == ([target], [])
    root = check_hint.qualified(".", "uv run test --changed")
    target = check_hint.qualified(".", "uv run test --changed -- serve/tools/tests/test_todo.py")
    plan, _ = tool_schema.parse(
        PlanResult, {"tasks": [{"title": "t", "goal": "AC-1", "scope": ["serve/tools"], "checks": [target]}]}
    )
    assert tools.check_plan(plan, Worktree("a", "a"), [root], (), ((".", "uv run test --changed"),)) == []
    frozen = check_hint.freeze(plan.tasks[0].checks[0], ["before..after"])
    assert check_hint.task_command(frozen, "base", "target") == check_hint.qualified(
        ".",
        "uv run test --changed serve/tools/tests/test_todo.py --task-base base --target target"
        " --keep-span before..after",
    )


def test_the_hint_names_the_profile_s_command_as_written():
    task = {"title": "t", "goal": "AC-1", "scope": ["packages/app"], "checks": [CHOICE]}
    plan, _ = tool_schema.parse(PlanResult, {"tasks": [task]})
    spaced = (("packages/app", "npm  test"),)
    offered = "cd ./packages/app && {\nnpm  test\n}"
    found = tools.check_plan(plan, Worktree("a", "a"), [offered], (), spaced)
    assert found[0].endswith(f'use one of "{offered}"')
    plan.tasks[0].checks = [offered]
    assert tools.check_plan(plan, Worktree("a", "a"), [offered], (), spaced) == []


def test_the_plan_step_says_how_a_task_names_its_checks_and_carries_the_packages():
    entries = {
        "check:.": ProfileEntry(state="known", value="make check"),
        "check:packages/app": ProfileEntry(state="known", value="npm test"),
    }
    c = Change(slug="c1", brief=Brief(version=1), step=Step(kind=StepKind.PLAN))
    parts = step_input.session(c, Profile(entries=entries), Path("/w"), {})
    assert parts.packages == ((".", "make check"), ("packages/app", "npm test"))
    assert parts.checks == ("cd . && {\nmake check\n}", CHOICE)
    assert all(f"check `{command}`" in parts.message for command in parts.checks)
    bare = step_input.session(c, Profile(), Path("/w"), {})
    assert (bare.checks, bare.packages) == ((), ())


def test_the_plan_step_s_gate_gives_the_hint():
    cfg = sdk_adapter.Session(
        StepKind.PLAN,
        Path("/w"),
        "s1",
        "m",
        resume=False,
        policy=Policy(Path("/w")),
        observe=lambda: Worktree("a", "a"),
        checks=(CHOICE,),
        packages=APP,
        submit=tools.PLAN,
    )
    gate = Gate(cfg, Run("s1"), lambda **_e: None, lambda: None)
    task = {"title": "t", "goal": "AC-1", "scope": ["packages/app"], "checks": ["npm test"]}
    text, ok = gate.call(tools.PLAN, {"tasks": [task]})
    assert not ok
    assert PROFILE in text
    task["checks"] = [CHOICE]
    assert gate.call(tools.PLAN, {"tasks": [task]})[1]
