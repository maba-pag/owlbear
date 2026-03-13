---
id: 719
title: Implement tool-trajectory evaluation harness
status: todo
priority: nice-to-have
created: 2026-03-10T17:10:55.7758069+01:00
updated: 2026-03-11T17:16:42.0246949+01:00
tags:
    - scope:core
    - test
    - evaluation
claimed_by: test-writer
claimed_at: 2026-03-11T17:16:42.0246949+01:00
class: standard
---

Adapt the GCP generative-ai evaluation pattern for OwlBear. Build a lightweight tool-trajectory eval harness in tests/benchmarks/ that evaluates agent tool selection behavior.

Inspired by GCP evaluating_adk_agent.ipynb trajectory_single_tool_use metric. See docs/research/gcp-generative-ai-audit-research.md section 4.3-4.4.

## Acceptance Criteria

- [ ] `tests/benchmarks/tool_eval.py` defines `EvalCase` dataclass: `case_id: str`, `prompt: str`, `agent_name: str`, `expected_tools: list[str]`
- [ ] `tests/benchmarks/tool_eval.py` defines `EvalResult` dataclass: `case: EvalCase`, `actual_tools: list[str]`, `passed: bool`, `error: str | None`
- [ ] `extract_tool_calls(messages: list[ModelMessage]) -> list[str]` extracts `ToolCallPart.tool_name` from PydanticAI message list (preserves call order)
- [ ] `match_tools(expected: list[str], actual: list[str]) -> bool` returns True when `set(expected) <= set(actual)` (order-insensitive containment)
- [ ] `run_eval(cases, run_fn) -> list[EvalResult]` takes `Callable[[EvalCase], Awaitable[list[ModelMessage]]]` and evaluates each case. The harness does NOT own agent construction - callers inject the runner
- [ ] `compute_accuracy(results: list[EvalResult]) -> dict[str, float]` returns `{agent_name: passed_count / total_count}` (0.0 if no cases for agent)
- [ ] `format_eval_report(results, accuracy) -> str` produces markdown with per-case table (case_id, agent, expected, actual, pass/fail) and summary accuracy table
- [ ] `tests/test_benchmark_tool_eval.py` tests all harness functions with synthetic EvalCase fixtures (no LLM calls). >= 90% coverage of tool_eval.py
- [ ] ruff clean on both files

## Architecture Notes

Follow existing `tests/benchmarks/` pattern (harness.py, evaluate.py): pure functions on typed data, no heavy deps. Runner injection pattern enables both FunctionModel (CI) and @pytest.mark.api (future real LLM). TDD: combined RED+GREEN since this IS test infrastructure.

[[2026-03-11]] Wed 16:29
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| EvalCase dataclass with 4 fields | Precise: all fields typed, matches GCP pattern | Kept |
| EvalResult dataclass with 4 fields | Precise: references EvalCase, typed | Kept |
| extract_tool_calls(messages) -> list[str] | Correct PydanticAI types (ModelMessage, ToolCallPart.tool_name in ModelResponse.parts) | Kept |
| match_tools set containment | Precise: algorithm specified (order-insensitive) | Kept |
| run_eval with injected runner Callable | Precise: async signature, caller-owned agent construction, good separation of concerns | Kept |
| compute_accuracy returns dict[str, float] | Precise: formula specified, edge case (0 cases) handled | Kept |
| format_eval_report -> markdown string | Precise: output format described (per-case table + summary) | Kept |
| test_benchmark_tool_eval.py >= 90% coverage | Precise: file location, coverage target, synthetic fixtures (no LLM) | Kept |
| ruff clean | Standard gate | Kept |

### Architecture Notes
- **Pattern consistency:** Follows existing tests/benchmarks/ pattern (harness.py pure functions, evaluate.py formatting, bench_*.py runners). tool_eval.py fits naturally alongside.
- **PydanticAI types verified:** ModelMessage = ModelRequest |} ModelResponse. ToolCallPart lives in ModelResponse.parts with .tool_name attribute. Confirmed in condenser.py, test_pydantic_messages.py, test_intent_routing.py.
- **Runner injection:** Correct design  `Callable[[EvalCase], Awaitable[list[ModelMessage]]]` enables FunctionModel (CI) and real LLM (@pytest.mark.api) without harness changes. Matches existing search.py pattern (embed provider injected).
- **TDD exception valid:** Combined RED+GREEN is appropriate  this IS test infrastructure. The task includes its own tests (test_benchmark_tool_eval.py with 90% coverage gate).
- **Module layering:** All code in tests/benchmarks/  no src/ layering concerns.
- **Security surface:** None  pure test infrastructure, no system boundaries.

### Dependencies
- Verified: No depends_on in frontmatter. No blocking prerequisites needed.
- Note: #720 (eval dataset) depends implicitly on this harness for EvalCase types  currently in-progress. No conflict since #720 can define data independently and integrate later.

### Changes Made
- Moving #719 to todo
