# Wire PydanticAI Evaluate Callable for SourceEvaluator

> **Owning task:** #701 — Wire PydanticAI evaluate callable for SourceEvaluator in MCP server
> **Date:** 2026-04-09 **Status:** Complete

## 1. Context and Question

After #688/#700 fixed the SourceEvaluator crash, the evaluator runs as a no-op stub
via `make_evaluate_fn()` in `server.py` — all evaluations return neutral defaults
(score 0.5, worth_ingesting=True). Task #701 replaces this stub with a real
PydanticAI-backed `EvaluateFn` callable to produce actual LLM relevance scores.

**Questions:**
1. Where should the PydanticAI factory live? (knowledge engine vs. MCP server)
2. What's the correct PydanticAI API for structured `EvaluationResult` output?
3. How to handle graceful degradation when `pydantic-ai` is not installed?
4. Dependency coordination with #689 (LLMExtractor, same optional dep)?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| 1 | `evaluator.py` — EvaluateFn, SourceEvaluator, EVALUATION_PROMPT | Codebase | 1.0 |
| 2 | `server.py` — make_evaluate_fn placeholder, app_lifespan wiring | Codebase | 1.0 |
| 3 | v1 `evaluator.py:103-165` — PydanticAI Agent SourceEvaluator | Codebase | 0.95 |
| 4 | `consolidation.py` — TextCompletionFn callable injection pattern | Codebase | 0.85 |
| 5 | `extractor.py` — EntityExtractor DI, StructuredExtractor protocol | Codebase | 0.85 |
| 6 | PydanticAI docs — Agent, output_type, run() API | External | 1.0 |
| 7 | `.owlbear/research/fix-sourceevaluator-wiring.md` — Option B analysis | Research | 0.90 |
| 8 | `.owlbear/research/llmextractor-pydanticai-implementation.md` — dep strategy | Research | 0.85 |
| 9 | `test_sourceevaluator_wiring_688.py` — existing tests gated on #701 | Codebase | 0.90 |
| 10 | `serve/knowledge/pyproject.toml` — current optional deps | Codebase | 0.80 |

## 3. Analysis

### 3.1 PydanticAI API Surface (Confirmed)

Current PydanticAI API uses `output_type` for structured output:

```python
from pydantic_ai import Agent

agent = Agent(model, output_type=EvaluationResult, system_prompt=EVALUATION_PROMPT)
result = await agent.run(prompt)
evaluation = result.output  # typed as EvaluationResult
```

v1 used identical pattern successfully. `agent.run()` is async, matching
`EvaluateFn = Callable[[str], Awaitable[EvaluationResult]]`.

### 3.2 Factory Placement

| Option | Location | AC1? | KISS | Separation |
|--------|----------|------|------|------------|
| **A: evaluator.py** | Knowledge engine | ✓ | High | Evaluation logic co-located |
| B: llm_evaluator.py | Knowledge engine (new file) | ✓ | Medium | New file for ~15 LOC |
| C: server.py | MCP server | ✗ | Low | Violates AC1 |

**Option A** places the factory alongside `EvaluateFn`, `EVALUATION_PROMPT`, and
`SourceEvaluator` — all evaluation concerns in one module. No new file needed.

### 3.3 Implementation Shape

**Factory in evaluator.py** (~15 LOC):
```python
def make_pydantic_evaluate_fn(model: str) -> EvaluateFn:
    from pydantic_ai import Agent  # deferred import — optional dep

    agent: Agent[None, EvaluationResult] = Agent(
        model,
        output_type=EvaluationResult,
        system_prompt=EVALUATION_PROMPT,
    )

    async def _evaluate(prompt: str) -> EvaluationResult:
        result = await agent.run(prompt)
        return result.output

    return _evaluate
```

**Server.py make_evaluate_fn update** (~8 LOC change):
```python
def make_evaluate_fn(model: str) -> EvaluateFn:
    try:
        from owlbear_knowledge.evaluator import make_pydantic_evaluate_fn
        return make_pydantic_evaluate_fn(model)
    except ImportError:
        async def _noop(_prompt: str) -> EvaluationResult:
            return EvaluationResult(relevance_score=0.5, ...)
        return _noop
```

Key design decisions:
- PydanticAI import is **deferred** inside factory (not module-level) — evaluator.py
  remains importable even without pydantic-ai
- ImportError caught in server.py → no-op fallback (AC4)
- Agent created once at factory call time, reused across evaluations (stateless)
- Closure pattern matches ConsolidationService's `TextCompletionFn`

### 3.4 Graceful Degradation (AC4)

| Layer | Failure mode | Behavior |
|-------|-------------|----------|
| pydantic-ai not installed | `ImportError` at factory call | server.py catches → no-op fn |
| LLM call fails at runtime | `Exception` in agent.run() | SourceEvaluator catches → neutral result |
| Empty content | — | SourceEvaluator returns score 0.0 |
| No project context | — | SourceEvaluator returns _default_result() |

Two-layer degradation: install-time (ImportError → no-op) and runtime (LLM error →
neutral score). Both already covered by existing SourceEvaluator exception handling
and the proposed server.py guard.

### 3.5 Dependency Strategy

#689 (LLMExtractor) plans `llm = ["pydantic-ai>=0.1"]` extras group. Shared with #701.
Whichever lands first creates the group. `full` extras should include `llm`.

Current `pyproject.toml` has: `qdrant`, `embedding`, `intake`, `full`.
Add: `llm = ["pydantic-ai>=0.1"]`, update `full` to include `pydantic-ai>=0.1`.

### 3.6 Existing Test Coverage

`test_sourceevaluator_wiring_688.py` contains 7 tests. After #700 (backward-compat fix),
5 pass. Two remain gated on `make_evaluate_fn` existing — both already pass since
#700 added the placeholder. Tests verify:
- Server doesn't pass model string positionally (✓ passing)
- Factory exists and returns callable (✓ passing)
- Graceful degradation on LLM exception (✓ passing)

Missing coverage for #701:
- Factory produces a callable that calls PydanticAI Agent (not just returns neutral)
- ImportError fallback path when pydantic-ai not installed
- Integration: full pipeline with real (or test-model) evaluation

### 3.7 Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| pydantic-ai API breaking change | Low | Medium | Pin `>=0.1`, covers current API |
| Transitive dep bloat (~5 deps) | Low | Low | Optional extras group isolates |
| EVALUATION_PROMPT quality | Low | Medium | Reuse proven v1 prompt already in module |
| Agent overhead per call | Low | Low | Agent constructed once (factory closure) |

## 4. Recommendation

**Option A: Factory function in evaluator.py** (confidence: 0.85)

Add `make_pydantic_evaluate_fn(model)` to `evaluator.py` with deferred PydanticAI
import. Update `server.py:make_evaluate_fn()` to delegate with ImportError fallback.
Add `pydantic-ai` as optional `llm` extras in `pyproject.toml`.

This is the simplest change (~20 LOC total), follows the established
callable-injection pattern, reuses the existing `EVALUATION_PROMPT`, and provides
two-layer graceful degradation.

Challenge: FALLBACK — challenger agent not available in this session.
Confidence in original: 0.85.

**Tier:** T1 — Autonomous (implements planned feature from #688 research, proven v1
pattern, no new capability or arch change).

## 5. Follow-up Tasks

No new tasks needed — #701 itself is the implementation task. ACs are concrete with
clear affected files. Existing tests provide partial coverage; additional tests for
the PydanticAI integration path should be created as part of the TDD cycle.
