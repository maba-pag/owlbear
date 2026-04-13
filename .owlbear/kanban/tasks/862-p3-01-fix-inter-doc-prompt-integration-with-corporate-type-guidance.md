---
id: 862
title: 'P3-01: Fix inter-doc prompt integration with corporate type guidance'
status: backlog
priority: nice-to-have
created: '2026-04-13T19:16:55.084666+00:00'
updated: '2026-04-13T20:50:44.186317+00:00'
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