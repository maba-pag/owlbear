"""C-28 T8: each Delivery tool's calls of a step, counted by its gate and kept on the Change."""

from pathlib import Path

from owlbear_delivery_next.change_contracts import tools
from owlbear_delivery_next.change_contracts.models import StepKind
from owlbear_delivery_next.change_contracts.permissions import Policy
from owlbear_delivery_next.change_contracts.tool_use import ToolTally, ToolUse
from owlbear_delivery_next.change_contracts.tools import Worktree
from owlbear_delivery_next.runtimes import sdk_adapter
from owlbear_delivery_next.runtimes.results import ACCEPTED, ENDED, Gate
from owlbear_delivery_next.runtimes.session_result import Run

HEAD, BASE = "a" * 40, "b" * 40
GOOD = {"summary": "Added greet().", "changed_paths": ["src/greet.ts"], "checks": []}
SUBMIT = tools.SUBMIT.name


def gate() -> Gate:
    cfg = sdk_adapter.Session(
        StepKind.BUILD,
        Path(),
        "s1",
        "m",
        resume=False,
        policy=Policy(Path()),
        observe=lambda: Worktree(HEAD, BASE, changed=("src/greet.ts",)),
        checks=(),
    )
    return Gate(cfg, Run("s1"), lambda **_e: None, lambda: None)


def test_a_runs_counts_add_to_each_tools_total() -> None:
    use = ToolUse().plus({"a": {"calls": 2, "rejected": 1, "retries": 1}})
    use = use.plus({"a": {"calls": 1, "late": 1}, "b": {"calls": 3, "lint": 2}})
    assert use.tools == {
        "a": ToolTally(calls=3, rejected=1, late=1, retries=1),
        "b": ToolTally(calls=3, lint=2),
    }
    assert ToolUse.model_validate_json(use.model_dump_json()) == use


def test_a_refused_submit_then_an_accepted_one_counts_a_rejection_and_a_retry_and_a_late_call_counts_late() -> None:
    g = gate()
    assert g.call(tools.SUBMIT, {"summary": "x"})[1] is False
    assert g.call(tools.SUBMIT, GOOD) == (ACCEPTED, True)
    assert g.run.tool_calls == {SUBMIT: {"calls": 2, "rejected": 1, "retries": 1}}
    assert g.call(tools.SUBMIT, GOOD) == (ENDED, False)
    assert g.run.tool_calls == {SUBMIT: {"calls": 3, "rejected": 1, "retries": 1, "late": 1}}


def test_a_lint_only_refusal_counts_as_lint_not_as_rejected() -> None:
    g = gate()
    g.lint.check = lambda *_a: ["lint: ruff check found problems in src/greet.ts"]
    assert g.call(tools.SUBMIT, GOOD)[1] is False
    assert (g.run.tool_calls, g.run.invalid) == ({SUBMIT: {"calls": 1, "lint": 1}}, 0)
