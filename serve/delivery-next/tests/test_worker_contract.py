from datetime import UTC, datetime
from pathlib import Path

from owlbear_delivery_next import tools
from owlbear_delivery_next.models import Exit, StepKind
from owlbear_delivery_next.sdk_adapter import Policy, Request, Run, Termination, decide, to_result, verdict
from owlbear_delivery_next.tools import AskQuestion, BuildResult, Worktree

NOW = datetime(2026, 10, 10, 12, tzinfo=UTC)
HEAD, BASE = "a" * 40, "b" * 40
GOOD = {
    "summary": "Added greet().",
    "changed_paths": ["packages/app/src/greet.ts"],
    "commit": HEAD[:7],
    "checks": [{"command": "npm test", "exit_code": 0}],
}


def build(**changes) -> BuildResult:
    result, errors = tools.parse(BuildResult, {**GOOD, **changes})
    assert errors == []
    return result


def test_schema_errors_name_the_field_and_give_an_example() -> None:
    result, errors = tools.parse(BuildResult, {**GOOD, "commit": "HEAD", "checks": [{"command": "npm test"}], "x": 1})
    assert result is None
    assert any(e.startswith("commit:") and '"3f2c1ab"' in e for e in errors)
    assert any(e.startswith("checks[0].exit_code:") for e in errors)
    assert any(e.startswith("x:") for e in errors)
    assert tools.parse(AskQuestion, "not json")[1] == ["arguments: not a JSON object - send the fields as one object"]


def test_uncommitted_work_is_rejected_on_the_commit_field() -> None:
    tree = Worktree(head=BASE, base=BASE, dirty=("packages/app/src/greet.ts",))
    errors = tools.check_build(build(commit=BASE[:7]), tree, ["npm test"])
    assert errors[0] == (
        f"commit: HEAD of the worktree is {BASE[:12]}, the task's base; commit your changes, then submit again"
    )
    assert errors[1].startswith("commit: the worktree has uncommitted changes (packages/app/src/greet.ts)")


def test_a_committed_result_must_name_head_paths_and_every_passing_check() -> None:
    tree = Worktree(head=HEAD, base=BASE, changed=("packages/app/src/greet.ts", "packages/app/test/greet.test.ts"))
    assert tools.check_build(build(), Worktree(HEAD, BASE, changed=("packages/app/src/greet.ts",)), ["npm test"]) == []
    errors = tools.check_build(
        build(commit="c" * 7, checks=[{"command": "npm test", "exit_code": 1}]), tree, ["npm test", "npm run lint"]
    )
    assert errors[0].startswith(f"commit: HEAD of the worktree is {HEAD[:12]}, not ccccccc")
    assert errors[1] == "changed_paths: missing packages/app/test/greet.test.ts - list every path your commit changes"
    assert errors[2].startswith("checks[0].exit_code: 1")
    assert errors[3].startswith('checks: "npm run lint" missing')


def test_question_options_must_differ() -> None:
    q, _ = tools.parse(AskQuestion, {"question": "q", "why": "w", "options": [{"label": "A", "effect": "x"}] * 2})
    assert tools.check_question(q) == ["options: labels repeat - give each option a distinct answer"]


def test_permission_allows_listed_commands_and_worktree_paths_only(tmp_path: Path) -> None:
    policy = Policy(tmp_path, ("git add", "git commit", "npm test", "cd"))
    assert decide(policy, Request("shell", (("cd packages/app", False), ("npm test -- --x", False)))) is None
    assert decide(policy, Request("shell", (("git push origin x", False),))) == "`git push origin x` is denied"
    assert decide(policy, Request("shell", (("npm test", False), ("rm -rf /", False)))) == (
        "`rm -rf /` is not in this step's allow list"
    )
    assert decide(policy, Request("shell", (("ls", True),), paths=("src",))) is None
    assert decide(policy, Request("shell", (("cat", True),), paths=("/etc/passwd",))) is not None
    assert decide(policy, Request("shell", (("npm test", False),), urls=True)) is not None
    assert decide(policy, Request("write", paths=(str(tmp_path / "a.ts"),))) is None
    assert decide(policy, Request("write", paths=("../escape.ts",))) == "write outside the worktree: ../escape.ts"
    assert decide(Policy(tmp_path, (), write=False), Request("write", paths=("a.ts",))) is not None
    assert decide(policy, Request("url")) == "url requests are not allowed in this step"
    assert decide(policy, Request("custom-tool", tool="submit_result")) is None


def test_termination_is_confirmed_only_when_every_recorded_pid_is_observed_gone() -> None:
    states = {1: False, 2: False}
    assert verdict({1: 10.0, 2: None}, lambda pid, _: states[pid]).confirmed
    t = verdict({1: 10.0, 2: None, 3: 5.0}, lambda pid, _: {1: False, 2: True, 3: None}[pid])
    assert (t.confirmed, t.survivors, t.unknown) == (False, (2,), (3,))
    assert not verdict({1: 10.0}, lambda *_: False, ["tasks.list failed (RuntimeError)"]).confirmed


def test_a_valid_result_still_stops_while_a_step_process_survives() -> None:
    run = Run("s1", ending="result", payload=build(), termination=Termination(confirmed=True))
    assert to_result(run, StepKind.BUILD, NOW).exit == Exit.DONE
    stopped = to_result(run, StepKind.BUILD, NOW, scanned=[(17494, "sh")])
    assert (stopped.exit, stopped.stop.action) == (Exit.STOP, "End processes 17494")
    run.termination = Termination(confirmed=False, unknown=(9,), problems=("disconnect failed (OSError)",))
    assert to_result(run, StepKind.BUILD, NOW).stop.reason == (
        "termination unverified: processes 9 still present; disconnect failed (OSError)"
    )
