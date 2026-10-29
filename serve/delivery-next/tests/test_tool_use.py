"""C-28 T8: each Delivery tool's calls of a step, counted by its gate and kept on the Change."""

from pathlib import Path
from types import SimpleNamespace

from owlbear_delivery_next.change_contracts import permissions, tools
from owlbear_delivery_next.change_contracts.models import StepKind
from owlbear_delivery_next.change_contracts.permissions import Policy
from owlbear_delivery_next.change_contracts.tool_use import ToolTally, ToolUse
from owlbear_delivery_next.change_contracts.tools import Worktree
from owlbear_delivery_next.design_packs import design_tools
from owlbear_delivery_next.runtimes import sdk_adapter, sdk_spend
from owlbear_delivery_next.runtimes.results import ACCEPTED, ENDED, Gate
from owlbear_delivery_next.runtimes.session_result import Run

HEAD, BASE = "a" * 40, "b" * 40
GOOD = {"summary": "Added greet().", "checks": []}
SUBMIT = tools.SUBMIT.name


def session(base: str = BASE, **fields: object) -> sdk_adapter.Session:
    fields.setdefault("observe", lambda: Worktree(HEAD, base, changed=("src/greet.ts",)))
    return sdk_adapter.Session(
        StepKind.BUILD,
        Path(),
        "s1",
        "m",
        resume=False,
        policy=Policy(Path(), write=False),
        checks=(),
        journal=sdk_adapter.Journal(event=lambda _e: None),
        **fields,
    )


def gate(base: str = BASE, **fields: object) -> Gate:
    return Gate(session(base, **fields), Run("s1"), lambda **_e: None, lambda: None)


def shell(text: str) -> SimpleNamespace:
    """One SDK shell permission request for *text*."""
    command = SimpleNamespace(identifier=text.split(maxsplit=1)[0])
    segment = SimpleNamespace(full_command_text=text)
    return SimpleNamespace(kind="shell", commands=[command], command_segments=[segment], full_command_text=text,
                           possible_paths=(), possible_urls=())  # fmt: skip


def step() -> sdk_adapter._Step:
    return sdk_adapter._Step(session(), SimpleNamespace(call_soon_threadsafe=lambda *_: None))  # noqa: SLF001


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
    assert g.run.tool_calls == {SUBMIT: {"calls": 2, "rejected": 1, "invalid": 1, "retries": 1}}
    assert g.call(tools.SUBMIT, GOOD) == (ENDED, False)
    assert g.run.tool_calls == {SUBMIT: {"calls": 3, "rejected": 1, "invalid": 1, "retries": 1, "late": 1}}


def test_a_lint_only_refusal_counts_as_lint_not_as_rejected() -> None:
    g = gate()
    g.lint.check = lambda *_a: ["lint: ruff check found problems in src/greet.ts"]
    assert g.call(tools.SUBMIT, GOOD)[1] is False
    assert (g.run.tool_calls, g.run.invalid) == ({SUBMIT: {"calls": 1, "lint": 1}}, 0)


def test_a_refusal_counts_invalid_arguments_or_failed_checks_inside_its_rejections() -> None:
    g = gate(base=HEAD)  # nothing committed since the base: the content check fails
    assert g.call(tools.SUBMIT, GOOD)[1] is False
    assert g.call(tools.SUBMIT, {"summary": 1})[1] is False
    assert g.run.tool_calls == {SUBMIT: {"calls": 2, "rejected": 2, "checks": 1, "invalid": 1, "retries": 1}}
    assert g.run.invalid == 2  # the limit of invalid calls still counts both


def test_a_helpers_schema_error_counts_as_invalid_arguments() -> None:
    g = gate(helpers=((tools.MISSING, lambda _a: "ok"),))
    assert g.call(tools.MISSING, {"tool": "docker"})[1] is False
    assert g.call(tools.MISSING, {"tool": "docker", "need": "tests", "error": "absent"}) == ("ok", True)
    assert g.run.tool_calls == {tools.MISSING.name: {"calls": 2, "rejected": 1, "invalid": 1, "retries": 1}}


def test_a_verdict_before_the_first_look_or_a_second_look_is_the_wrong_moment() -> None:
    images = ("home-1280-A.png", "home-1280-B.png")
    g = gate(role="design-judge", submit=design_tools.FINAL, first_look=design_tools.FIRST,
             observe=lambda: Worktree("h", "h", changed=images))  # fmt: skip
    look = {"verdict": "pass", "preferences": [{"pair": "home-1280", "better": "equal", "why": "Same"}],
            "covered_paths": list(images)}  # fmt: skip
    assert g.call(design_tools.FINAL, look | {"verdict": "fail"})[1] is False  # also no findings: the order wins
    assert g.call(design_tools.FIRST, look)[1] is True
    assert g.call(design_tools.FIRST, look)[1] is False
    assert g.run.tool_calls[design_tools.FINAL.name] == {"calls": 1, "rejected": 1, "order": 1}
    assert g.run.tool_calls[design_tools.FIRST.name] == {"calls": 2, "rejected": 1, "order": 1}


def test_a_runs_wrong_choices_add_to_the_changes_and_old_refusals_stay_unsplit() -> None:
    old = ToolUse.model_validate({"tools": {"a": {"calls": 2, "rejected": 2}}})  # kept before the split
    use = old.plus({"a": {"calls": 1, "rejected": 1, "invalid": 1}}, {"denied": 2})
    use = use.plus({}, {"denied": 1, "no_result": 1})
    assert use.tools["a"] == ToolTally(calls=3, rejected=3, invalid=1)  # 2 of its refusals are unsplit
    assert use.wrong == {"denied": 3, "no_result": 1}
    assert ToolUse.model_validate_json(use.model_dump_json()) == use


def test_a_guard_denial_is_a_wrong_choice_unless_it_refused_a_bypass() -> None:
    st = step()
    st.permission(shell("docker compose up > log"), None)  # writes in a read-only step
    st.permission(shell("git commit --no-verify -m x"), None)
    st.permission(shell("docker ps"), None)
    assert permissions.bypass(st.run.denials[-1])
    assert not permissions.bypass(st.run.denials[0])
    assert (st.run.wrong, len(st.run.denials), st.run.denied) == ({"denied": 1}, 2, {"git": st.run.denials[-1]})


def test_a_missing_tool_report_is_pointless_while_the_guard_denies_it_or_only_a_window_has_it() -> None:
    def reported(tool: str, *requests: str, after: tuple[str, ...] = ()) -> dict[str, int]:
        st = step()
        for text in requests:
            st.permission(shell(text), None)
        assert st.gate.call(tools.MISSING, {"tool": tool, "need": "tests", "error": "not found"})[1] is True
        for text in after:  # the turn may go on until the session is torn down
            st.permission(shell(text), None)
        sdk_spend.pointless(st.run)
        return {k: n for k, n in st.run.wrong.items() if k != "denied"}

    assert reported("docker", "docker compose up > log") == {"missing_pointless": 1}
    assert reported("docker", "docker compose up > log", "docker ps") == {}  # it ran: maybe really absent
    assert reported("docker", "docker compose up > log", after=("docker ps",)) == {}  # as Delivery classifies it
    assert reported("browser") == {"missing_pointless": 1}  # only a VS Code window has one
    assert reported("docker") == {}
