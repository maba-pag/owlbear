# Wire StructuredExtractor to Activate Knowledge Graph Layer

> **Owning task:** #676 — Wire StructuredExtractor to activate knowledge graph layer
> **Date:** 2026-04-08 **Status:** Complete

## 1. Context and Question

The knowledge graph layer is a no-op in production. `EntityExtractor(model)` is created in
`app_lifespan()` without an injected `StructuredExtractor`, so `extract()` returns empty
results. Question: *What is the minimal, KISS-aligned approach to implement and wire a
concrete `StructuredExtractor` that activates entity/edge extraction?*

Key design tension discovered: `StructuredExtractor.extract()` is **sync** but real LLM
calls are async. `EntityExtractor.extract()` is async but calls the sync protocol without
`await`. This must be resolved before any concrete implementation can work in production.

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| 1 | `serve/knowledge/src/owlbear_knowledge/protocol.py` L87-98 | Codebase | 1.0 |
| 2 | `serve/knowledge/src/owlbear_knowledge/extractor.py` L55-100 | Codebase | 1.0 |
| 3 | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` L113-162 | Codebase | 1.0 |
| 4 | `v1/src/owlbear/memory/knowledge/extractor.py` — PydanticAI pattern | Codebase | 0.9 |
| 5 | `serve/knowledge/src/owlbear_knowledge/evaluator.py` — EvaluateFn DI | Codebase | 0.8 |
| 6 | `.owlbear/research/extract-entity-extraction-graph-builders.md` | Research | 0.7 |
| 7 | PydanticAI docs — `run_sync()` event loop behavior | External | 0.9 |

## 3. Analysis

### 3.1 Sync/Async Resolution

| Approach | Mechanism | Risk | KISS |
|----------|-----------|------|------|
| **A: Make protocol async** | `async def extract(...)` + `await` in EntityExtractor | Low — only test mocks break | High |
| B: `to_thread` + `asyncio.run` | Sync protocol; EntityExtractor wraps call | Medium — event loop per call | Medium |
| C: Raw httpx sync | No PydanticAI; manual JSON parsing | High — fragile, more code | Low |

**Finding:** `PydanticAI.run_sync()` calls `loop.run_until_complete()` — fails inside
an async context (RuntimeError). Option B requires `asyncio.run()` inside `to_thread()`
which creates+destroys an event loop per extraction call. Option A is cleanest:
`EntityExtractor.extract()` is already async, so `await self._extractor.extract(prompt)`
is a one-line change. `@runtime_checkable` checks attribute existence, not signature,
so isinstance() works regardless of sync/async.

### 3.2 LLM SDK Choice

| Option | Deps added | Structured output | LOC | KISS |
|--------|-----------|-------------------|-----|------|
| **PydanticAI** | 1 (+ transitive) | Native `result_type=ExtractionResult` | ~30 | High |
| openai SDK | 1 (+ transitive) | JSON schema → manual parse | ~60 | Medium |
| httpx raw | 0 (already optional) | Manual prompt + parse | ~100 | Low |

**Finding:** v1 used PydanticAI for this exact purpose — `Agent(model, output_type=ExtractionResult,
system_prompt=EXTRACTION_PROMPT)` → `await agent.run(prompt)` → `result.output`. The pattern
is proven. PydanticAI handles validation, retries, and structured output natively with
Pydantic v2 models. The `ExtractionResult` model is already defined.

### 3.3 Placement

AC6 mandates the implementation lives in `owlbear-knowledge`, not the MCP server.
Add `pydantic-ai` as an optional dependency (`llm` extras group). The MCP server
constructs and injects it in `app_lifespan()`.

### 3.4 System Prompt

v1's `EXTRACTION_PROMPT` covers all `EntityType` and `RelationType` enum values and
instructs the LLM to output JSON matching `ExtractionResult`. It can be reused directly.

### 3.5 Related Issue — SourceEvaluator

`SourceEvaluator(model)` passes a model name string where `EvaluateFn` (async callable)
is expected. Same wiring gap. Out of scope for #676 but should be tracked separately.

## 4. Recommendation

**Make protocol async + PydanticAI adapter in knowledge engine** (confidence: 0.82)

1. Change `StructuredExtractor.extract()` to `async def`
2. Add `await` in `EntityExtractor.extract()` delegation
3. Create `LLMExtractor` class in `owlbear-knowledge` (~30 LOC) using PydanticAI
4. Add `pydantic-ai` as optional dep (`llm` extras)
5. Wire in MCP server: `LLMExtractor(model)` → `EntityExtractor(extractor=...)`

Challenge: FALLBACK — challenger agent not available in this session.

Risks:
- PydanticAI adds transitive deps (~5) — mitigated by optional extras group
- Protocol change breaks test mocks — low impact, ~10 test files need `AsyncMock`

## 5. Follow-up Tasks

See task IDs created below. Task #676 needs decomposition into implementation sub-tasks.
