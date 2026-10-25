"""A value over a field's limit is refused with its path, its length, the limit and what to cut (C-28)."""

import pytest

from owlbear_delivery_next.change_contracts import tool_schema, tools

GOAL = "name each criterion by its id and how the Builder knows it is met; leave out how to build it, or split the task"


def goal(length: int) -> str:
    text = "".join(f"- AC-{i}: the page shows item {i} once the build has finished.\n" for i in range(200))
    return text[:length]


def plan(length: int) -> dict:
    return {"tasks": [{"title": "t", "goal": goal(length), "scope": ["packages/app"], "checks": ["npm test"]}]}


# The six oversized fields Delivery refused in the sandbox projects, recovered from their sessions' calls: each was
# tasks[0].goal of a plan; the goal's limit was 1000 until it became 3000.
RECORDED = [
    ("add-a-flip-direction-button-with-a-plan-all-d19de6d0", 4444, 3000),
    ("add-a-flip-direction-button-with-a-plan-all-d19de6d0", 3137, 3000),
    ("add-a-flip-direction-button-with-a-plan-all-a15be2d0", 3813, 3000),
    ("add-a-notes-textarea-with-an-800-charact-plan-all-2b9aa2d6", 1233, 1000),
    ("add-a-theme-toggle-to-the-preview-page-plan-all-417d3068", 1386, 1000),
    ("add-a-theme-toggle-to-the-preview-page-plan-all-22106d75", 1767, 1000),
]


@pytest.mark.parametrize(("session", "length", "then"), RECORDED, ids=[f"{s[-8:]}-{n}" for s, n, _ in RECORDED])
def test_each_recorded_oversized_goal_now_passes_or_says_what_to_cut(session, length, then):
    assert session.endswith(("d19de6d0", "a15be2d0", "2b9aa2d6", "417d3068", "22106d75"))
    result, errors = tool_schema.parse(tools.PlanResult, plan(length))
    if length <= 3000:
        assert (errors, len(result.tasks[0].goal)) == ([], length)
        assert then == 1000
    else:
        assert result is None
        assert errors == [f"tasks[0].goal: {length} characters, at most 3000 - {GOAL}"]


@pytest.mark.parametrize(
    ("model", "args", "error"),
    [
        (
            tools.BuildResult,
            {"summary": "s" * 2412, "checks": []},
            (
                "summary: 2412 characters, at most 2000 - say what changed and why in a few sentences; the "
                "commit shows the rest"
            ),
        ),
        (
            tools.BuildResult,
            {"summary": "s", "checks": [{"command": "npm test", "exit_code": 0}] * 21},
            "checks: 21 items, at most 20 - report each task check once, as it last ran",
        ),
        (
            tools.BuildResult,
            {"summary": "s", "checks": [{"command": "x" * 301, "exit_code": 0}]},
            "checks[0].command: 301 characters, at most 300 - shorten it",
        ),
        (
            tools.BuildResult,
            {"summary": "s", "checks": [], "response": {"how": "answered", "text": "y" * 3001}},
            "response.text: 3001 characters, at most 3000 - shorten it",
        ),
        (
            tools.PlanResult,
            {"tasks": [{"title": "t", "goal": "g", "scope": ["a"], "checks": ["npm test"]}] * 9},
            "tasks: 9 items, at most 8 - merge small tasks into larger ones; every criterion stays covered",
        ),
        (
            tools.PlanResult,
            {"tasks": [{"title": "t", "goal": "g", "scope": ["a"] * 21, "checks": ["npm test"]}]},
            "tasks[0].scope: 21 items, at most 20 - name the directories that hold the files instead of each file",
        ),
        (
            tools.VisualReviewResult,
            {"verdict": "fix", "findings": [{"place": "p", "problem": "x", "fix": "f"}] * 21},
            "findings: 21 items, at most 20 - merge findings with the same fix; leave out none that must be fixed",
        ),
        (
            tools.ReviewResult,
            {"verdict": "fix", "findings": [{"place": "p", "problem": "x", "fix": "f"}, {"place": "p" * 301}]},
            "findings[1].place: 301 characters, at most 300 - shorten it",
        ),
        (
            tools.WrongPremise,
            {"stage": "plan", "reason": "r", "evidence": ["e"] * 11},
            "evidence: 11 items, at most 10 - combine related items; leave out none the result needs",
        ),
    ],
)
def test_a_limit_error_names_the_path_the_length_the_limit_and_what_to_cut(model, args, error):
    result, errors = tool_schema.parse(model, args)
    assert result is None  # refused whole: nothing is cut to fit
    assert error in errors


def test_other_errors_give_the_nested_field_s_own_example():
    _, errors = tool_schema.parse(tools.PlanResult, {"tasks": [{"title": "t", "goal": "g", "scope": ["a"]}]})
    assert errors == ['tasks[0].checks: Field required - e.g. ["npm test"]']
    _, errors = tool_schema.parse(tools.BuildResult, {"summary": "s", "checks": [{"command": "npm test"}]})
    assert errors == ["checks[0].exit_code: Field required - e.g. 0"]
    _, errors = tool_schema.parse(tools.PlanResult, {"tasks": "[]"})  # the recorded wrong type
    assert errors == [
        (
            'tasks: Input should be a valid list - e.g. [{"title": "Add farewell", "goal": "AC-1", "scope": '
            '["packages/app"], "checks": ["npm test"]}]'
        )
    ]
    _, errors = tool_schema.parse(tools.PlanResult, {"tasks": ["t1"]})
    assert errors[0].startswith('tasks[0]: Input should be a valid dictionary or instance of PlanTask - e.g. {"title"')


def test_a_visual_reviews_covered_paths_over_the_limit_keep_every_screenshot():
    from owlbear_delivery_next.change_contracts import tool_schema, tools  # noqa: PLC0415

    paths = [f"shots/{n}.png" for n in range(500)]
    _, errors = tool_schema.parse(tools.VisualReviewResult, {"verdict": "pass", "covered_paths": paths})
    told = next(e for e in errors if e.startswith("covered_paths"))
    assert told.endswith("list each required screenshot once, by its exact file name")
    _, errors = tool_schema.parse(tools.ReviewResult, {"verdict": "pass", "covered_paths": paths})
    assert next(e for e in errors if e.startswith("covered_paths")).endswith(
        "name the directories you read instead of each file"
    )
