# Fix Inter-Doc Prompt Integration with Corporate Type Guidance

> **Owning task:** #862 — P3-01: Fix inter-doc prompt integration with corporate type guidance
> **Date:** 2026-04-13 **Status:** Complete

## 1. Context and Question

`INTER_DOC_PROMPT` in `inter_doc_graph_builder.py` is dead code — defined at L31 but never referenced. The `_build_inter_prompt()` function at L60 sends only bare entity names (`({a.name}, {b.name})`) with no types, descriptions, or corporate relationship guidance. The LLM therefore lacks context to infer GOVERNS or SUPERSEDES_VERSION edges.

**Research question:** What is the cleanest way to activate the prompt, enrich entity context, and add corporate guidance — without changing the `StructuredExtractor` protocol?

## 2. Sources Studied

| Source | Relevance | What |
|--------|-----------|------|
| `inter_doc_graph_builder.py` (codebase) | .95 | Dead `INTER_DOC_PROMPT`, bare `_build_inter_prompt` |
| `llm_extractor.py` (codebase) | .95 | `LLMExtractor` hardcodes `system_prompt=LLM_EXTRACTION_PROMPT` |
| `protocol.py` (codebase) | .90 | `StructuredExtractor.extract(prompt: str)` — single-arg protocol |
| `models.py` (codebase) | .85 | Entity: name, entity_type, description; RelationType: GOVERNS, SUPERSEDES_VERSION |
| `.owlbear/research/772-interdocgraphbuilder-corporate-types.md` | .90 | Parent research: gaps G1, G2, G7 map to this task |
| `test_inter_doc_graph_builder.py` (codebase) | .85 | 20+ tests — none verify prompt content or corporate guidance |

## 3. Analysis

### 3.1 Core Problem

The `StructuredExtractor` protocol is `extract(prompt: str)` — one arg. System prompt is baked into `LLMExtractor.__init__` at construction time via `pydantic_ai.Agent(model, system_prompt=...)`. Currently `LLMExtractor` hardcodes `LLM_EXTRACTION_PROMPT` (intra-doc extraction). InterDocGraphBuilder needs a DIFFERENT system prompt (inter-doc relationship inference).

### 3.2 Approach Comparison

| Criterion | A: Configurable LLMExtractor (.85) | B: Combined prompt in user text (.60) | C: Dedicated InterDocExtractor (.70) |
|-----------|-------------------------------------|----------------------------------------|--------------------------------------|
| Protocol change needed | No | No | No |
| Files changed (prod) | `llm_extractor.py` (+2 LOC), `inter_doc_graph_builder.py` (~20 LOC) | `inter_doc_graph_builder.py` only (~25 LOC) | New file (~40 LOC) + `inter_doc_graph_builder.py` (~20 LOC) |
| System/user prompt separation | Clean — system prompt at Agent level | Mixed — system semantics in user text | Clean |
| DI pattern | Preserved — caller picks system prompt via constructor arg | Preserved but prompt semantics degraded | Preserved |
| Conflicts with intra-doc prompt | None — separate extractor instance | Yes if InterDocGraphBuilder reuses same LLMExtractor instance | None |
| Code duplication | None | None | Duplicates LLMExtractor except system prompt |
| KISS score | High | Medium | Low |

### 3.3 Recommended Change Set (Approach A)

**`llm_extractor.py`** — make system prompt configurable:
```python
def __init__(self, model: str, system_prompt: str = LLM_EXTRACTION_PROMPT) -> None:
    self._agent = pydantic_ai.Agent(model, output_type=ExtractionResult, system_prompt=system_prompt)
```

**`inter_doc_graph_builder.py`** — two changes:

1. Update `INTER_DOC_PROMPT` to include corporate relationship guidance:
   - Add GOVERNS guidance: policy/standard → procedure/requirement
   - Add SUPERSEDES_VERSION guidance: same entity across document versions
   - Format `{relation_types}` dynamically from `RelationType` enum (as intra-doc prompt does)

2. Enrich `_build_inter_prompt()` to include entity types and descriptions:
   ```
   - Data Classification Framework [policy]: Org-wide data handling rules
     ↔ Data Handling Procedure [procedure]: Step-by-step data processing
   ```

**Wiring** (out of scope — covered by G6/separate task): caller creates `LLMExtractor(model, system_prompt=INTER_DOC_PROMPT.format(...))` and passes to InterDocGraphBuilder.

### 3.4 Testing Strategy

New tests needed (the existing 20+ tests don't verify prompt content):
- `_build_inter_prompt` includes `entity_type` for each entity
- `_build_inter_prompt` includes `description` for each entity
- `INTER_DOC_PROMPT` contains "governs" guidance text
- `INTER_DOC_PROMPT` contains "supersedes_version" guidance text
- `INTER_DOC_PROMPT` references `{relation_types}` placeholder
- Existing tests pass unchanged (behavioral contract preserved)

## 4. Recommendation (confidence: .85)

**Approach A: Configurable `system_prompt` in LLMExtractor.** 2-line change to `llm_extractor.py`, ~20 LOC in `inter_doc_graph_builder.py`, plus 4–6 new tests. No protocol change. Follows established DI pattern. Callers (future G6 task) provide the right extractor at construction time.

**Risk:** Low. The `system_prompt` parameter defaults to `LLM_EXTRACTION_PROMPT`, so all existing call sites work unchanged. The `_build_inter_prompt` enrichment only adds information the LLM already ignores (since current prompt is bare names).

Challenge: FALLBACK — challenger subagent not available in agent list.

## 5. Follow-up Tasks

No decomposition needed — #862's AC already covers the full scope. Task is ready for implementation (backlog).
