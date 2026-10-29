"""The six recorded plan refusals of a check written with its package directory: words, never a new form."""

from pathlib import Path

import pytest

from owlbear_delivery_next.change_contracts import tool_schema, tools
from owlbear_delivery_next.change_contracts.models import Brief, Change, Step, StepKind
from owlbear_delivery_next.change_contracts.permissions import Policy
from owlbear_delivery_next.change_contracts.profile_record import Profile, ProfileEntry
from owlbear_delivery_next.change_contracts.tools import PlanResult, Worktree
from owlbear_delivery_next.runtimes import sdk_adapter, step_input
from owlbear_delivery_next.runtimes.results import Gate
from owlbear_delivery_next.runtimes.session_result import Run

APP = (("packages/app", "npm test"),)  # the sandbox profile of the recorded refusals
HINT = 'write the command alone: "npm test"; the Builder runs it from that package\'s directory'
PROFILE = 'use one of "npm test"'


def errors(check: str, packages=APP) -> tuple[list[str], list[str]]:
    plan, _ = tool_schema.parse(
        PlanResult, {"tasks": [{"title": "t", "goal": "AC-1", "scope": ["packages/app"], "checks": [check]}]}
    )
    found = tools.check_plan(plan, Worktree("a", "a"), ["npm test"], (), packages)
    return plan.tasks[0].checks, found


@pytest.mark.parametrize(
    ("check", "said"),
    [
        ("cd packages/app && npm test", HINT),  # four recorded refusals
        ("cd ./packages/app/ && npm test", HINT),
        ("cd 'packages/app' &&npm test", HINT),
        ("npm --prefix packages/app test", PROFILE),  # two recorded refusals: today's error
        ("cd packages/other && npm test", PROFILE),
        ("cd packages && npm test", PROFILE),
        ("cd packages/app && npm run test", PROFILE),
        ("cd packages/app && npm test && rm -rf x", PROFILE),
        ("cd packages/app; npm test", PROFILE),
        ("cd packages/frontend-components-library; npm test", PROFILE),  # answered at once, however long
    ],
)
def test_a_check_with_its_package_directory_is_refused_with_what_to_write(check, said):
    assert errors(check) == ([check], [f'tasks[0].checks: "{check}" is not a check of the project profile - {said}'])


def test_the_hint_needs_the_profile_s_packages():
    assert errors("cd packages/app && npm test", ())[1][0].endswith(PROFILE)
    assert errors("npm test") == (["npm test"], [])


def test_the_hint_names_the_profile_s_command_as_written():
    task = {"title": "t", "goal": "AC-1", "scope": ["packages/app"], "checks": ["cd packages/app && npm test"]}
    plan, _ = tool_schema.parse(PlanResult, {"tasks": [task]})
    spaced = (("packages/app", "npm  test"),)
    found = tools.check_plan(plan, Worktree("a", "a"), ["npm  test"], (), spaced)
    assert found[0].endswith('write the command alone: "npm  test"; the Builder runs it from that package\'s directory')
    plan.tasks[0].checks = ["npm  test"]  # the hint's command is admitted as written
    assert tools.check_plan(plan, Worktree("a", "a"), ["npm  test"], (), spaced) == []


def test_the_plan_step_says_how_a_task_names_its_checks_and_carries_the_packages():
    entries = {
        "check:.": ProfileEntry(state="known", value="make check"),
        "check:packages/app": ProfileEntry(state="known", value="npm test"),
    }
    c = Change(slug="c1", brief=Brief(version=1), step=Step(kind=StepKind.PLAN))
    parts = step_input.session(c, Profile(entries=entries), Path("/w"), {})
    assert parts.packages == ((".", "make check"), ("packages/app", "npm test"))
    assert parts.checks == ("make check", "npm test")
    assert (
        "A task's `checks` are these check commands exactly as listed. The Builder runs each from its package's "
        "directory, so a check never starts with `cd`: write `npm test`, not `cd packages/app && npm test`."
    ) in parts.message
    bare = step_input.plan(c, Profile(), Path("/w"), {})
    assert "so a check never starts with `cd`." in bare  # no package check listed: no example naming one
    assert "write `" not in bare


def test_the_plan_step_s_gate_gives_the_hint():
    cfg = sdk_adapter.Session(
        StepKind.PLAN,
        Path("/w"),
        "s1",
        "m",
        resume=False,
        policy=Policy(Path("/w")),
        observe=lambda: Worktree("a", "a"),
        checks=("npm test",),
        packages=APP,
        submit=tools.PLAN,
    )
    gate = Gate(cfg, Run("s1"), lambda **_e: None, lambda: None)
    task = {"title": "t", "goal": "AC-1", "scope": ["packages/app"], "checks": ["cd packages/app && npm test"]}
    text, ok = gate.call(tools.PLAN, {"tasks": [task]})
    assert not ok
    assert HINT in text
