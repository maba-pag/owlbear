---
id: 862
title: 'P3-01: Fix inter-doc prompt integration with corporate type guidance'
status: todo
priority: nice-to-have
created: '2026-04-13T19:16:55.084666+00:00'
updated: '2026-04-15T13:34:47.597165+00:00'
tags:
- phase-3
- scope:knowledge
- deferred
parent: 772
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Context

InterDocGraphBuilder's `INTER_DOC_PROMPT` is defined but never used (dead code). The `_build_inter_prompt()` function sends only entity names — no types, descriptions, or corporate-type relationship guidance. The LLM lacks context to infer GOVERNS or SUPERSEDES_VERSION relationships.

See: .owlbear/research/772-interdocgraphbuilder-corporate-types.md (Gaps G1, G2, G7)

## Acceptance Criteria

- [ ] `INTER_DOC_PROMPT` is used as system prompt for inter-doc extraction (or replaced with a dedicated extractor)
- [ ] `_build_inter_prompt()` includes entity types and descriptions alongside names
- [ ] Corporate-type relationship guidance added to inter-doc prompt (GOVERNS: policy/standard → procedure; SUPERSEDES_VERSION: same entity across versions)
- [ ] Existing inter-doc tests still pass; new tests cover corporate type guidance in prompt

## Affected Files

- `serve/knowledge/src/owlbear_knowledge/inter_doc_graph_builder.py`

## Dependency

Deferred until Phase 1 entity model is proven via real corporate ingestion.

[[2026-04-13]]
## Research
- Research doc: .owlbear/research/862-inter-doc-prompt-integration.md
- Sources: 6 studied (all codebase-internal), 4 high-relevance
- Recommendation: Approach A — configurable `system_prompt` param in LLMExtractor (confidence: .85). 2-line change to `llm_extractor.py`, ~20 LOC in `inter_doc_graph_builder.py`, 4–6 new tests. No protocol change. DI pattern preserved.
- Follow-up tasks created: none — #862 AC already covers the full scope
- Decision requests: none (T1 — correctness fix for dead code + impoverished prompt)

[[2026-04-14]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: fix dead prompt + enrich context for inter-doc extraction |
| Interface clarity | PASS/FLAG | AC1 says "INTER_DOC_PROMPT is used as system prompt" — ambiguous in DI context. Builder receives extractor via DI, doesn't control system prompt. See builder guidance below for how to interpret AC1 as testable. |
| Dependency correctness | PASS | No deps needed; self-contained within owlbear_knowledge |
| Module layering | PASS | Changes within owlbear_knowledge package only. No cross-package violations. |
| TDD compliance | PASS | Will go through RED/GREEN pipeline |
| KISS/YAGNI | PASS | ~2 LOC in llm_extractor.py + ~20 LOC in inter_doc_graph_builder.py + 4-6 tests |
| Premise challenge | PASS | Verified: INTER_DOC_PROMPT defined at L31 but never referenced. _build_inter_prompt at L60 sends only bare names. Both are real defects. |
| Pattern consistency | PASS | Follows existing DI pattern. LLMExtractor already uses system_prompt internally; making it a constructor param is natural. Same {relation_types} format pattern as LLM_EXTRACTION_PROMPT. |
| Security surface | PASS | No new system boundaries. Prompt changes are internal to the knowledge package. |
| Single domain | PASS | scope:knowledge only |

### Affected Files Correction

Task body lists only `inter_doc_graph_builder.py`. Research doc explicitly identifies a 2-line change to `llm_extractor.py` (adding optional `system_prompt` parameter). Builder must also touch:

- `serve/knowledge/src/owlbear_knowledge/llm_extractor.py` — add `system_prompt: str = LLM_EXTRACTION_PROMPT` constructor parameter

### Builder Guidance for AC1

AC1 says: "INTER_DOC_PROMPT is used as system prompt for inter-doc extraction (or replaced with a dedicated extractor)"

In the DI context, this means:
1. `LLMExtractor.__init__` accepts `system_prompt: str = LLM_EXTRACTION_PROMPT` — backward-compatible, single production call site in `server.py:194` uses default
2. `INTER_DOC_PROMPT` content is updated to be ready for use (corporate guidance, {relation_types} placeholder)
3. Test verifies: `LLMExtractor(model="test", system_prompt=INTER_DOC_PROMPT.format(relation_types=...))` creates a working extractor

The actual wiring (caller creates LLMExtractor with INTER_DOC_PROMPT and passes to InterDocGraphBuilder) is #864's scope. This task enables it.

### Codebase Evidence

- `INTER_DOC_PROMPT`: `inter_doc_graph_builder.py:31-52` — defined, never imported/called
- `_build_inter_prompt()`: `inter_doc_graph_builder.py:60-62` — `f"({a.name}, {b.name})"` only
- `LLMExtractor.__init__`: `llm_extractor.py:82-86` — hardcodes `system_prompt=LLM_EXTRACTION_PROMPT`
- `Entity` model: `models.py:88-97` — has `entity_type` (EntityType) and `description` (str, default="")
- Production LLMExtractor calls: only `server.py:194` — backward-compatible with optional param
- Production InterDocGraphBuilder calls: none — no call site exists yet (#864 wiring)
- Existing tests: 20+ in test_inter_doc_graph_builder.py, none verify prompt content

### Challenge Results
- Challenger: FALLBACK — no challenger agent in available roster
- Architect response: Proceeded; high confidence from codebase evidence. Backward-compatible change, no protocol violation, follows established DI pattern.

### Verdict: APPROVE
### Action Taken: Advanced #862 to todo. Flagged missing affected file (llm_extractor.py) and clarified AC1 interpretation for builder.

[[2026-04-14]]
## Premise Invalidated
pydantic-ai dependency and LLMExtractor class removed from the project (2026-04-14). Research recommendation (configurable `system_prompt` in LLMExtractor) is no longer viable. When Phase 3 is picked up, this task needs re-scoping — either wire INTER_DOC_PROMPT directly into EntityExtractor, or implement a new lightweight extraction callable without pydantic-ai. Architecture review and research notes above are stale.
