# Fix SourceEvaluator Wiring — Model String Passed Where Callable Expected

> **Owning task:** #688 — Fix SourceEvaluator wiring — model string passed where EvaluateFn callable expected
> **Date:** 2026-04-08 **Status:** Complete

## 1. Context and Question

`server.py:149` constructs `SourceEvaluator(model)` passing the string `"gpt-4o-mini"`.
The constructor signature is `__init__(self, llm_fn: EvaluateFn)` where
`EvaluateFn = Callable[[str], Awaitable[EvaluationResult]]`. The string is stored as
`_llm_fn`. When `evaluate()` reaches `await self._llm_fn(prompt)` with non-empty
content and non-None project_context, it crashes: `TypeError: 'str' object is not callable`.

**Questions:**
1. What is the correct fix pattern? (backward-compat stub vs. real LLM wiring vs. both)
2. How does this relate to the EntityExtractor fix from #676?
3. What dependencies are needed for real LLM evaluation?

## 2. Sources Studied

| Source | Location | Relevance |
|--------|----------|-----------|
| v2 evaluator.py | `serve/knowledge/src/owlbear_knowledge/evaluator.py` | 1.0 |
| v2 server.py (wiring) | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py:131-170` | 1.0 |
| v2 extractor.py (EntityExtractor pattern) | `serve/knowledge/src/owlbear_knowledge/extractor.py:55-100` | 0.95 |
| v2 bookmark_pipeline.py (consumer) | `serve/knowledge/src/owlbear_knowledge/bookmark_pipeline.py` | 0.90 |
| v2 consolidation.py (sibling pattern) | `serve/knowledge/src/owlbear_knowledge/consolidation.py` | 0.85 |
| v1 evaluator.py (PydanticAI original) | `v1/src/owlbear/memory/knowledge/evaluator.py:83-160` | 0.80 |
| #676 research — StructuredExtractor wiring | `.owlbear/research/wire-structuredextractor-knowledge-graph.md` | 0.85 |
| #135 research — LLM injection pattern | `.owlbear/research/extract-cancel-sandbox-consolidation-evaluator.md` §3.2 | 0.80 |
| test_evaluator.py (correct usage) | `tests/test_evaluator.py` | 0.85 |

## 3. Analysis

### 3.1 Runtime Impact

The crash path: `app_lifespan` → `SourceEvaluator("gpt-4o-mini")` → `_llm_fn = "gpt-4o-mini"` →
`bookmark_pipeline.process(url, project_context={...})` → `evaluator.evaluate(content, project_context)` →
`await self._llm_fn(prompt)` → **TypeError**.

Partial mitigation: when `project_context is None`, `evaluate()` returns `_default_result()` without
calling `_llm_fn`. But any call with project_context crashes.

### 3.2 Fix Options

| Option | Description | Crash fix | Real scores | Deps added | LOC | KISS |
|--------|-------------|-----------|-------------|------------|-----|------|
| **A** | Backward-compat constructor (no-op stub) | Yes | No — neutral defaults | 0 | ~10 | High |
| **B** | PydanticAI adapter in knowledge engine | Yes | Yes | pydantic-ai (optional) | ~40 | Medium |
| **C** | Factory function in MCP server layer | Yes | Yes | pydantic-ai in MCP | ~30 | Medium |
| **D** | A then B (two tasks) | Yes | Yes (when wired) | pydantic-ai (optional) | ~45 | High |

### 3.3 Option Detail

**Option A — Backward-compatible constructor:**
Mirror EntityExtractor pattern. Accept positional `model` arg, add keyword-only `llm_fn`.
When `llm_fn` is None, return `_default_result()` without LLM call. ~10 LOC change.
```python
def __init__(self, model: str | object | None = None, *, llm_fn: EvaluateFn | None = None) -> None:
    self._model = model
    self._llm_fn = llm_fn
```
Then in `evaluate()`, if `self._llm_fn is None` → return `_default_result()`.

**Option B — PydanticAI adapter:**
Create `LLMEvaluator` class or factory in `owlbear_knowledge` using PydanticAI
`Agent(model, output_type=EvaluationResult, system_prompt=EVALUATION_PROMPT)`.
Requires `pydantic-ai` as optional dep — same dep #676 needs for `LLMExtractor`.

**Option C — Factory in MCP server:**
Inline `_make_evaluate_fn(model)` in server.py. Couples server to PydanticAI directly.
Violates separation: knowledge engine owns evaluation logic, not the MCP server.

**Option D — Combined A + B:**
Task 1 fixes the crash immediately (A). Task 2 adds real evaluation (B) once
pydantic-ai dep lands via #676. Follows EntityExtractor precedent exactly.

### 3.4 EntityExtractor Precedent

EntityExtractor (#676) solved the identical problem with this pattern:
- Constructor accepts `model` string for backward compat (no-op stub)
- `StructuredExtractor` injected via keyword-only `extractor=` param
- Server wires the real adapter when available

For SourceEvaluator, the same pattern: `model` positional for compat, `llm_fn`
keyword for real callable. Simpler than EntityExtractor since `EvaluateFn` is
already a type alias — no Protocol class needed.

## 4. Recommendation

**Option D: Two-step fix** (confidence: 0.80)

1. **Immediate:** Backward-compatible constructor (Option A) — fixes crash, 0 new deps
2. **Follow-on:** PydanticAI adapter (Option B) — delivers real scores, shares dep with #676

Rationale: crash fix shouldn't be blocked by LLM integration. The two-step approach
follows the proven EntityExtractor pattern, maintains KISS, and lets the real-evaluation
task coordinate with #676's pydantic-ai dep addition.

**Risk:** Between steps 1 and 2, evaluation returns neutral defaults (score 0.5,
worth_ingesting=True). Bookmarks still get stored but without meaningful relevance
filtering. Acceptable for a transitional state.

Challenge: FALLBACK — challenger agent not available in this session.
Confidence in original: 0.80.

**Tier:** T1 — Autonomous (bug fix, no new capability, no arch change).

## 5. Follow-up Tasks

1. **Backward-compat constructor fix** — make SourceEvaluator accept model string without crashing
2. **PydanticAI evaluate adapter** — create LLM callable + wire in server.py (depends on pydantic-ai dep from #676)
