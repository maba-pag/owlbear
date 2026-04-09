# LLMExtractor Implementation via PydanticAI

> **Owning task:** #689 — Implement LLMExtractor concrete StructuredExtractor using PydanticAI
> **Date:** 2026-04-09 **Status:** Complete

## 1. Context and Question

Task #689 requires a concrete `LLMExtractor` class satisfying the `StructuredExtractor`
protocol, using PydanticAI for structured output. The v2 knowledge graph is inert without
this — `EntityExtractor` returns empty results when no `StructuredExtractor` is injected.
Question: *What is the correct PydanticAI API surface, implementation pattern, system
prompt design, dependency strategy, and testing approach for LLMExtractor?*

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| 1 | `serve/knowledge/src/owlbear_knowledge/protocol.py` L87-98 | Codebase | 1.0 |
| 2 | `serve/knowledge/src/owlbear_knowledge/extractor.py` L22-49, L55-100 | Codebase | 1.0 |
| 3 | `serve/knowledge/src/owlbear_knowledge/models.py` L14-35 | Codebase | 1.0 |
| 4 | `serve/knowledge/pyproject.toml` | Codebase | 0.9 |
| 5 | PydanticAI docs — Agent, output_type, run() | External | 1.0 |
| 6 | PydanticAI docs — Testing (TestModel, FunctionModel, override) | External | 0.9 |
| 7 | `.owlbear/research/wire-structuredextractor-knowledge-graph.md` | Research | 0.9 |
| 8 | v1 extractor pattern (documented in #676 research + multiple research docs) | Codebase | 0.9 |

## 3. Analysis

### 3.1 PydanticAI API Confirmation

Current PydanticAI API uses `output_type` (not `result_type`):

```python
agent = Agent(model, output_type=ExtractionResult, system_prompt=EXTRACTION_PROMPT)
result = await agent.run(prompt)
extraction = result.output  # typed as ExtractionResult
```

This matches the v1 pattern exactly. `agent.run()` is async; `run_sync()` uses
`loop.run_until_complete()` — requires async `StructuredExtractor.extract()` (#687).

### 3.2 System Prompt Gap

Existing `EXTRACTION_PROMPT` in `extractor.py` lists 6 relation types but the `RelationType`
enum has 7 — `governed_by` is missing. AC3 requires all enum values covered.

| EntityType values (6) | In EXTRACTION_PROMPT? |
|----------------------|----------------------|
| file, function, class_, decision, pattern, concept | All 6 present ✓ |

| RelationType values (7) | In EXTRACTION_PROMPT? |
|--------------------------|----------------------|
| defines, imports, depends_on, related_to, implements, documents | 6 present ✓ |
| **governed_by** | **Missing ✗** |

**Recommendation:** LLMExtractor should define its own system prompt constant (or
extend `EXTRACTION_PROMPT`) to include `governed_by`. Reusing the existing prompt
as-is violates AC3.

### 3.3 Implementation Shape (~30 LOC)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Agent construction | At `__init__` time | Agent is reusable, stateless between runs |
| System prompt | Static string covering all enum values | AC3 compliance |
| Error handling | `try/except Exception` → empty `ExtractionResult()` | AC5 graceful degradation |
| Logging | `logger.warning` on LLM failure | Observability without exception propagation |
| Type hint | `Agent[None, ExtractionResult]` | No deps needed |

### 3.4 Optional Dependency Strategy

| Approach | KISS | Isolation |
|----------|------|-----------|
| **`llm` extras group** | High | High — consumers opt in |
| Add to core deps | Low — forces pydantic-ai on all users | Low |
| Inline in MCP server | Medium | Low — violates AC6 |

**Recommendation:** Add `llm = ["pydantic-ai>=0.1"]` to `[project.optional-dependencies]`
and update `full` to include it. AC4 is explicit about this pattern.

### 3.5 Testing Strategy

| Approach | Pros | Cons | Fit |
|----------|------|------|-----|
| **PydanticAI TestModel + agent.override()** | Official pattern, validates output schema, tests integration | Requires pydantic-ai in test deps | Best |
| AsyncMock on agent.run() | Simpler, no pydantic-ai internals | Doesn't validate schema handling | Acceptable |
| FunctionModel | Custom response control | More setup code | Good for edge cases |

**Recommendation (confidence .85):** Primary tests use `TestModel` via `agent.override()`
with `models.ALLOW_MODEL_REQUESTS = False` safety guard. Error path tests mock
`agent.run()` to raise exceptions. This matches PydanticAI's documented testing pattern.

### 3.6 Dependency Chain

| Predecessor | Status | Required for |
|-------------|--------|-------------|
| #687 (async protocol) | research (claimed) | Protocol must be async before `extract()` can `await agent.run()` |
| #698 (TDD RED) | backlog | Tests must exist before implementation (TDD) |

**Metadata defect:** #689 currently has `depends_on: [676]`. Should be `[698, 687]`.
This was flagged by reviewer and architect on #676 but remains unapplied.

## 4. Recommendation

**Implement LLMExtractor as thin PydanticAI Agent wrapper** (confidence: 0.88)

The pattern is proven (v1), the API is confirmed (PydanticAI docs), the protocol interface
is defined (`StructuredExtractor`), and the testing approach is documented. Implementation
is straightforward once dependencies (#687, #698) are satisfied.

Key implementation notes for builder:
1. Define complete system prompt covering all 7 `RelationType` values (include `governed_by`)
2. Use `Agent[None, ExtractionResult]` with `output_type=ExtractionResult`
3. `async def extract(self, prompt: str) -> ExtractionResult` wraps `await self._agent.run(prompt)`
4. Catch `Exception` broadly → return `ExtractionResult()` + log warning
5. Add `llm = ["pydantic-ai>=0.1"]` extras group to pyproject.toml

Challenge: FALLBACK — challenger agent not available.

## 5. Follow-up Tasks

No new tasks needed. #689's ACs are complete and concrete. Predecessor tasks (#687, #698)
already exist. Metadata correction (depends_on) is an orchestrator action documented in #676.
