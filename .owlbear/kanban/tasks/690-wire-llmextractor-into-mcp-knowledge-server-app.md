---
id: 690
title: Wire LLMExtractor into MCP knowledge server app_lifespan
status: backlog
priority: needed
created: 2026-04-08T21:06:20.2270499+02:00
updated: 2026-04-09T05:09:36.5361634+02:00
tags:
    - scope:knowledge
    - ' type:feature'
    - ' source:research'
depends_on:
    - 676
class: standard
---

## Context

Research for #676. The MCP server's `app_lifespan()` creates `EntityExtractor(model)` without injecting a `StructuredExtractor`. After LLMExtractor exists (sibling task), wire it in.

## Acceptance Criteria

- [ ] AC1: `app_lifespan()` creates `LLMExtractor(model)` and passes it as `EntityExtractor(extractor=llm_extractor)`
- [ ] AC2: `owlbear-mcp-knowledge` declares dependency on `owlbear-knowledge[llm]` (optional extras)
- [ ] AC3: Ingest a test document and verify `get_stats` shows entity_count > 0 and edge_count > 0
- [ ] AC4: `search_knowledge` returns graph expansion context (not just vector chunks)
- [ ] AC5: Graceful degradation — if OWLBEAR_MODEL is unset or LLM unavailable, ingestion succeeds (vector-only fallback)

## Affected Files

- `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py`
- `serve/mcp-knowledge/pyproject.toml`
- `serve/mcp-knowledge/tests/test_ingest_graph_tools.py`

[[2026-04-09]] Thu 05:09
## Research
- Research doc: .owlbear/research/wire-llmextractor-mcp-knowledge.md
- Sources: 7 studied, 5 high-relevance (all codebase)
- Recommendation: Wire LLMExtractor + GraphAugmentedRetriever in app_lifespan, try/except for graceful degradation (confidence: 0.85)
- Key findings:
  1. Wiring is ~15 LOC across 2 files (server.py + pyproject.toml); DI slot is pre-built
  2. AC4 has scope ambiguity: "graph expansion context" needs GraphAugmentedRetriever wiring + entity_type in SearchResult (Option A+B); full expansion text output (Option C) is a separate enhancement
  3. Graceful degradation via try/except around LLMExtractor import handles missing-dep and construction-failure cases; runtime failures handled by LLMExtractor itself (#689 AC5)
  4. METADATA DEFECTS: depends_on should be [699, 689], parent should be 676, tag should be scope:mcp-knowledge — orchestrator must fix before dispatch
- Follow-up tasks created: none (decomposition from #676 covers all work)
- Decision requests: none — T1 autonomous
- Challenge: FALLBACK — challenger agent not available
