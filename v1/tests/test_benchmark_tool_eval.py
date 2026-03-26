"""Tests for tests/benchmarks/tool_eval — tool-trajectory evaluation harness.

TDD RED phase: tests define the contract for the tool-eval harness functions
before implementation. All imports from tool_eval will fail with ImportError
since the module does not exist yet.

Task: #719
"""

from __future__ import annotations

import asyncio

from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)

from tests.benchmarks.tool_eval import (
    EvalCase,
    EvalResult,
    compute_accuracy,
    extract_tool_calls,
    format_eval_report,
    match_tools,
    run_eval,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _case(
    case_id: str = "c1",
    prompt: str = "test prompt",
    agent_name: str = "agent-a",
    expected_tools: list[str] | None = None,
) -> EvalCase:
    """Build an EvalCase with sensible defaults."""
    return EvalCase(
        case_id=case_id,
        prompt=prompt,
        agent_name=agent_name,
        expected_tools=expected_tools or ["tool_a"],
    )


def _result(
    case: EvalCase | None = None,
    actual_tools: list[str] | None = None,
    *,
    passed: bool = True,
    error: str | None = None,
) -> EvalResult:
    """Build an EvalResult with sensible defaults."""
    return EvalResult(
        case=case or _case(),
        actual_tools=actual_tools or ["tool_a"],
        passed=passed,
        error=error,
    )


# ---------------------------------------------------------------------------
# TestFromAC_EvalCase — AC: EvalCase dataclass
# ---------------------------------------------------------------------------


class TestFromAC_EvalCase:  # noqa: N801
    """EvalCase dataclass has case_id, prompt, agent_name, expected_tools."""

    def test_has_case_id_field(self) -> None:
        ec = _case(case_id="abc")
        assert ec.case_id == "abc"

    def test_has_prompt_field(self) -> None:
        ec = _case(prompt="Do something")
        assert ec.prompt == "Do something"

    def test_has_agent_name_field(self) -> None:
        ec = _case(agent_name="owl")
        assert ec.agent_name == "owl"

    def test_has_expected_tools_field(self) -> None:
        ec = _case(expected_tools=["read_file", "search"])
        assert ec.expected_tools == ["read_file", "search"]

    def test_expected_tools_is_list_of_str(self) -> None:
        ec = _case(expected_tools=["a", "b", "c"])
        assert isinstance(ec.expected_tools, list)
        assert all(isinstance(t, str) for t in ec.expected_tools)


# ---------------------------------------------------------------------------
# TestFromAC_EvalResult — AC: EvalResult dataclass
# ---------------------------------------------------------------------------


class TestFromAC_EvalResult:  # noqa: N801
    """EvalResult dataclass has case, actual_tools, passed, error."""

    def test_has_case_field(self) -> None:
        c = _case()
        er = _result(case=c)
        assert er.case is c

    def test_has_actual_tools_field(self) -> None:
        er = _result(actual_tools=["tool_x", "tool_y"])
        assert er.actual_tools == ["tool_x", "tool_y"]

    def test_has_passed_field(self) -> None:
        er = _result(passed=False)
        assert er.passed is False

    def test_has_error_field_none(self) -> None:
        er = _result(error=None)
        assert er.error is None

    def test_has_error_field_str(self) -> None:
        er = _result(error="something broke")
        assert er.error == "something broke"


# ---------------------------------------------------------------------------
# TestFromAC_ExtractToolCalls — AC: extract_tool_calls
# ---------------------------------------------------------------------------


class TestFromAC_ExtractToolCalls:  # noqa: N801
    """extract_tool_calls extracts ToolCallPart.tool_name from ModelMessage list."""

    def test_extracts_single_tool_call(self) -> None:
        messages = [
            ModelResponse(parts=[ToolCallPart(tool_name="read_file", args={}, tool_call_id="c1")]),
        ]
        result = extract_tool_calls(messages)
        assert result == ["read_file"]

    def test_extracts_multiple_tool_calls_in_order(self) -> None:
        messages = [
            ModelResponse(
                parts=[
                    ToolCallPart(tool_name="search", args={}, tool_call_id="c1"),
                    ToolCallPart(tool_name="read_file", args={}, tool_call_id="c2"),
                ]
            ),
        ]
        result = extract_tool_calls(messages)
        assert result == ["search", "read_file"]

    def test_extracts_across_multiple_responses(self) -> None:
        messages = [
            ModelRequest(parts=[UserPromptPart(content="hello")]),
            ModelResponse(parts=[ToolCallPart(tool_name="tool_a", args={}, tool_call_id="c1")]),
            ModelRequest(
                parts=[ToolReturnPart(tool_name="tool_a", content="ok", tool_call_id="c1")]
            ),
            ModelResponse(parts=[ToolCallPart(tool_name="tool_b", args={}, tool_call_id="c2")]),
        ]
        result = extract_tool_calls(messages)
        assert result == ["tool_a", "tool_b"]

    def test_empty_messages_returns_empty_list(self) -> None:
        result = extract_tool_calls([])
        assert result == []

    def test_no_tool_calls_returns_empty_list(self) -> None:
        messages = [
            ModelRequest(parts=[UserPromptPart(content="hello")]),
            ModelResponse(parts=[TextPart(content="Hi there")]),
        ]
        result = extract_tool_calls(messages)
        assert result == []

    def test_ignores_text_parts_in_response(self) -> None:
        messages = [
            ModelResponse(
                parts=[
                    TextPart(content="Let me search"),
                    ToolCallPart(tool_name="search", args={}, tool_call_id="c1"),
                ]
            ),
        ]
        result = extract_tool_calls(messages)
        assert result == ["search"]

    def test_preserves_call_order_across_messages(self) -> None:
        messages = [
            ModelResponse(parts=[ToolCallPart(tool_name="first", args={}, tool_call_id="c1")]),
            ModelRequest(
                parts=[ToolReturnPart(tool_name="first", content="ok", tool_call_id="c1")]
            ),
            ModelResponse(parts=[ToolCallPart(tool_name="second", args={}, tool_call_id="c2")]),
            ModelRequest(
                parts=[ToolReturnPart(tool_name="second", content="ok", tool_call_id="c2")]
            ),
            ModelResponse(parts=[ToolCallPart(tool_name="third", args={}, tool_call_id="c3")]),
        ]
        result = extract_tool_calls(messages)
        assert result == ["first", "second", "third"]


# ---------------------------------------------------------------------------
# TestFromAC_MatchTools — AC: match_tools
# ---------------------------------------------------------------------------


class TestFromAC_MatchTools:  # noqa: N801
    """match_tools returns True when set(expected) <= set(actual)."""

    def test_exact_match(self) -> None:
        assert match_tools(["a", "b"], ["a", "b"]) is True

    def test_subset_match(self) -> None:
        assert match_tools(["a"], ["a", "b", "c"]) is True

    def test_superset_fails(self) -> None:
        assert match_tools(["a", "b", "c"], ["a"]) is False

    def test_empty_expected_always_matches(self) -> None:
        assert match_tools([], ["a", "b"]) is True

    def test_empty_expected_empty_actual(self) -> None:
        assert match_tools([], []) is True

    def test_nonempty_expected_empty_actual_fails(self) -> None:
        assert match_tools(["a"], []) is False

    def test_order_insensitive(self) -> None:
        assert match_tools(["b", "a"], ["a", "b"]) is True

    def test_duplicates_in_expected_still_subset(self) -> None:
        # set(["a", "a"]) == {"a"} which is <= {"a", "b"}
        assert match_tools(["a", "a"], ["a", "b"]) is True


# ---------------------------------------------------------------------------
# TestFromAC_RunEval — AC: run_eval
# ---------------------------------------------------------------------------


class TestFromAC_RunEval:  # noqa: N801
    """run_eval takes cases + run_fn callable and evaluates each case."""

    def test_evaluates_single_case(self) -> None:
        case = _case(expected_tools=["tool_a"])

        async def runner(_c: EvalCase) -> list[object]:
            return [
                ModelResponse(parts=[ToolCallPart(tool_name="tool_a", args={}, tool_call_id="c1")])
            ]

        results = asyncio.run(run_eval([case], runner))
        assert len(results) == 1
        assert results[0].passed is True
        assert results[0].actual_tools == ["tool_a"]

    def test_evaluates_multiple_cases(self) -> None:
        cases = [
            _case(case_id="c1", expected_tools=["tool_a"]),
            _case(case_id="c2", expected_tools=["tool_b"]),
        ]

        async def runner(c: EvalCase) -> list[object]:
            tool_name = c.expected_tools[0]
            return [
                ModelResponse(parts=[ToolCallPart(tool_name=tool_name, args={}, tool_call_id="x")])
            ]

        results = asyncio.run(run_eval(cases, runner))
        assert len(results) == 2
        assert all(r.passed for r in results)

    def test_failing_case_has_passed_false(self) -> None:
        case = _case(expected_tools=["tool_a"])

        async def runner(_c: EvalCase) -> list[object]:
            return [
                ModelResponse(
                    parts=[ToolCallPart(tool_name="wrong_tool", args={}, tool_call_id="c1")]
                )
            ]

        results = asyncio.run(run_eval([case], runner))
        assert results[0].passed is False

    def test_empty_cases_returns_empty(self) -> None:
        async def runner(_c: EvalCase) -> list[object]:
            return []

        results = asyncio.run(run_eval([], runner))
        assert results == []

    def test_runner_exception_captured_in_error(self) -> None:
        case = _case()

        async def runner(_c: EvalCase) -> list[object]:
            msg = "LLM timeout"
            raise RuntimeError(msg)

        results = asyncio.run(run_eval([case], runner))
        assert len(results) == 1
        assert results[0].passed is False
        assert results[0].error is not None
        assert "LLM timeout" in results[0].error

    def test_result_case_references_original(self) -> None:
        case = _case(case_id="ref-test")

        async def runner(_c: EvalCase) -> list[object]:
            return [
                ModelResponse(parts=[ToolCallPart(tool_name="tool_a", args={}, tool_call_id="c1")])
            ]

        results = asyncio.run(run_eval([case], runner))
        assert results[0].case is case


# ---------------------------------------------------------------------------
# TestFromAC_ComputeAccuracy — AC: compute_accuracy
# ---------------------------------------------------------------------------


class TestFromAC_ComputeAccuracy:  # noqa: N801
    """compute_accuracy returns {agent_name: passed_count / total_count}."""

    def test_all_pass(self) -> None:
        results = [
            _result(case=_case(agent_name="owl"), passed=True),
            _result(case=_case(agent_name="owl"), passed=True),
        ]
        acc = compute_accuracy(results)
        assert acc == {"owl": 1.0}

    def test_all_fail(self) -> None:
        results = [
            _result(case=_case(agent_name="owl"), passed=False),
            _result(case=_case(agent_name="owl"), passed=False),
        ]
        acc = compute_accuracy(results)
        assert acc == {"owl": 0.0}

    def test_mixed_results(self) -> None:
        results = [
            _result(case=_case(agent_name="owl"), passed=True),
            _result(case=_case(agent_name="owl"), passed=False),
        ]
        acc = compute_accuracy(results)
        assert acc == {"owl": 0.5}

    def test_multiple_agents(self) -> None:
        results = [
            _result(case=_case(agent_name="owl"), passed=True),
            _result(case=_case(agent_name="owl"), passed=True),
            _result(case=_case(agent_name="bear"), passed=True),
            _result(case=_case(agent_name="bear"), passed=False),
        ]
        acc = compute_accuracy(results)
        assert acc["owl"] == 1.0
        assert acc["bear"] == 0.5

    def test_empty_results(self) -> None:
        acc = compute_accuracy([])
        assert acc == {}

    def test_zero_cases_for_agent_returns_zero(self) -> None:
        # AC: "0.0 if no cases for agent" — this is edge: all results
        # belong to other agents, ask about a missing one
        results = [
            _result(case=_case(agent_name="owl"), passed=True),
        ]
        acc = compute_accuracy(results)
        # Agent "bear" not present → not in dict (no division by zero)
        assert "bear" not in acc


# ---------------------------------------------------------------------------
# TestFromAC_FormatEvalReport — AC: format_eval_report
# ---------------------------------------------------------------------------


class TestFromAC_FormatEvalReport:  # noqa: N801
    """format_eval_report produces markdown with per-case table and summary."""

    def test_returns_string(self) -> None:
        results = [_result(case=_case(case_id="c1"), actual_tools=["tool_a"], passed=True)]
        accuracy = {"agent-a": 1.0}
        report = format_eval_report(results, accuracy)
        assert isinstance(report, str)

    def test_contains_per_case_table_headers(self) -> None:
        results = [_result(case=_case(case_id="c1"), actual_tools=["tool_a"], passed=True)]
        accuracy = {"agent-a": 1.0}
        report = format_eval_report(results, accuracy)
        # Should have markdown table columns for case_id, agent, expected, actual, pass/fail
        assert "case_id" in report.lower() or "case" in report.lower()
        assert "agent" in report.lower()

    def test_contains_case_data(self) -> None:
        results = [
            _result(
                case=_case(case_id="eval-1", agent_name="owl", expected_tools=["search"]),
                actual_tools=["search", "read_file"],
                passed=True,
            )
        ]
        accuracy = {"owl": 1.0}
        report = format_eval_report(results, accuracy)
        assert "eval-1" in report
        assert "owl" in report

    def test_contains_accuracy_summary(self) -> None:
        results = [_result(case=_case(agent_name="owl"), passed=True)]
        accuracy = {"owl": 1.0}
        report = format_eval_report(results, accuracy)
        assert "1.0" in report or "100" in report

    def test_contains_pass_fail_indicator(self) -> None:
        results = [
            _result(case=_case(case_id="pass-case"), passed=True),
            _result(case=_case(case_id="fail-case"), passed=False),
        ]
        accuracy = {"agent-a": 0.5}
        report = format_eval_report(results, accuracy)
        # Report should distinguish pass from fail
        lower = report.lower()
        assert "pass" in lower or "✓" in report or "✅" in report
        assert "fail" in lower or "✗" in report or "❌" in report

    def test_multiple_agents_in_summary(self) -> None:
        results = [
            _result(case=_case(agent_name="owl"), passed=True),
            _result(case=_case(agent_name="bear"), passed=False),
        ]
        accuracy = {"owl": 1.0, "bear": 0.0}
        report = format_eval_report(results, accuracy)
        assert "owl" in report
        assert "bear" in report

    def test_markdown_table_pipe_chars(self) -> None:
        """Report should contain markdown table pipes."""
        results = [_result()]
        accuracy = {"agent-a": 1.0}
        report = format_eval_report(results, accuracy)
        assert "|" in report
