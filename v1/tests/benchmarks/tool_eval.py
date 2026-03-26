"""Tool-trajectory evaluation harness.

Evaluates agent tool-selection behavior by comparing expected tool calls
against actual tool calls extracted from PydanticAI message traces.

Inspired by GCP generative-ai evaluation pattern (trajectory_single_tool_use).

Task: #719
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic_ai.messages import ModelResponse, ToolCallPart

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from pydantic_ai.messages import ModelMessage


@dataclass
class EvalCase:
    """A single evaluation case specifying expected tool usage."""

    case_id: str
    prompt: str
    agent_name: str
    expected_tools: list[str]


@dataclass
class EvalResult:
    """Result of running a single evaluation case."""

    case: EvalCase
    actual_tools: list[str]
    passed: bool
    error: str | None


def extract_tool_calls(messages: list[ModelMessage]) -> list[str]:
    """Extract tool names from ToolCallPart in a PydanticAI message list.

    Preserves call order across messages.
    """
    tool_names: list[str] = []
    for msg in messages:
        if isinstance(msg, ModelResponse):
            tool_names.extend(
                part.tool_name for part in msg.parts if isinstance(part, ToolCallPart)
            )
    return tool_names


def match_tools(expected: list[str], actual: list[str]) -> bool:
    """Return True when set(expected) is a subset of set(actual).

    Order-insensitive containment check.
    """
    return set(expected) <= set(actual)


async def run_eval(
    cases: list[EvalCase],
    run_fn: Callable[[EvalCase], Awaitable[list[ModelMessage]]],
) -> list[EvalResult]:
    """Evaluate each case using the injected runner function.

    The harness does NOT own agent construction — callers inject the runner.
    Exceptions from the runner are captured in :pyattr:`EvalResult.error`.
    """
    results: list[EvalResult] = []
    for case in cases:
        try:
            messages = await run_fn(case)
            actual = extract_tool_calls(messages)
            passed = match_tools(case.expected_tools, actual)
            results.append(EvalResult(case=case, actual_tools=actual, passed=passed, error=None))
        except Exception as exc:  # noqa: BLE001
            results.append(EvalResult(case=case, actual_tools=[], passed=False, error=str(exc)))
    return results


def compute_accuracy(results: list[EvalResult]) -> dict[str, float]:
    """Compute per-agent accuracy: ``{agent_name: passed_count / total_count}``.

    Returns an empty dict when *results* is empty. Agents with zero cases
    simply won't appear in the returned dict.
    """
    totals: dict[str, int] = defaultdict(int)
    passed: dict[str, int] = defaultdict(int)
    for r in results:
        agent = r.case.agent_name
        totals[agent] += 1
        if r.passed:
            passed[agent] += 1
    return {agent: passed[agent] / totals[agent] for agent in totals}


def format_eval_report(
    results: list[EvalResult],
    accuracy: dict[str, float],
) -> str:
    """Produce a markdown report with per-case table and accuracy summary."""
    lines: list[str] = []

    # Per-case table
    lines.append("## Per-Case Results")
    lines.append("")
    lines.append("| Case ID | Agent | Expected | Actual | Result |")
    lines.append("|---------|-------|----------|--------|--------|")
    for r in results:
        expected = ", ".join(r.case.expected_tools)
        actual = ", ".join(r.actual_tools)
        status = "PASS" if r.passed else "FAIL"
        lines.append(
            f"| {r.case.case_id} | {r.case.agent_name} | {expected} | {actual} | {status} |"
        )

    lines.append("")

    # Accuracy summary table
    lines.append("## Accuracy Summary")
    lines.append("")
    lines.append("| Agent | Accuracy |")
    lines.append("|-------|----------|")
    for agent, acc in sorted(accuracy.items()):
        lines.append(f"| {agent} | {acc:.2f} |")

    return "\n".join(lines)
