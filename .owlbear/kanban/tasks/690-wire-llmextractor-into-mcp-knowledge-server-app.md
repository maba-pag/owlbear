---
id: 690
title: Wire LLMExtractor into MCP knowledge server app_lifespan
status: todo
priority: needed
created: 2026-04-08T21:06:20.2270499+02:00
updated: 2026-04-09T05:30:31.4919357+02:00
tags:
    - scope:mcp-knowledge
    - ' type:feature'
    - ' source:research'
parent: 676
depends_on:
    - 699
    - 689
class: standard
---

## Context

Research for #676. The MCP server's `app_lifespan()` creates `EntityExtractor(model)` without injecting a `StructuredExtractor`. After LLMExtractor exists (sibling task), wire it in.

## Acceptance Criteria

- [ ] AC1: `app_lifespan()` creates `LLMExtractor(model)` and passes it as `EntityExtractor(extractor=llm_extractor)`
- [ ] AC2: `owlbear-mcp-knowledge` declares dependency on `owlbear-knowledge[llm]` (optional extras)
- [ ] AC3: Ingest a test document and verify `get_stats` shows entity_count > 0 and edge_count > 0
- [ ] AC4a: `app_lifespan()` creates `GraphAugmentedRetriever(vs, gs, emb)` and passes it as `KnowledgeQueryService(retriever=...)`
- [ ] AC4b: `search_knowledge` response dicts include `entity_type` field (already in `StructuredSearchResult`, currently dropped by the list comprehension)
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

[[2026-04-09]] Thu 05:30
## Architecture Review

### Metadata Fixes Applied
- `depends_on`: [676] → [699, 689] — #689 creates LLMExtractor, #699 is TDD RED
- `parent`: null → 676
- `tags`: scope:knowledge → scope:mcp-knowledge

### AC Refinement
- AC4 split into AC4a (wire GraphAugmentedRetriever) and AC4b (include entity_type in search response) — original "graph expansion context" was ambiguous per research finding #2

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | All changes are "activate graph features in MCP server" — one logical unit |
| Interface clarity | PASS (after refine) | AC4 was vague; split into AC4a/AC4b with specific wiring targets |
| Dependency correctness | PASS (after fix) | Fixed depends_on to [699, 689]; #689=LLMExtractor impl, #699=TDD RED tests |
| Module layering | PASS | MCP server → knowledge package (correct direction) |
| TDD compliance | PASS | #699 is TDD RED predecessor |
| KISS/YAGNI | PASS | Wiring existing DI slots; no new abstractions |
| Premise challenge | PASS | EntityExtractor is currently a no-op stub; this task activates it |
| Pattern consistency | PASS | Follows existing app_lifespan DI pattern, try/except graceful degradation |
| Security surface | PASS | No new system boundaries; LLM calls go through existing model infrastructure |
| Single domain | PASS | scope:mcp-knowledge only |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|-------------|-----------|----------|-------------|
| LLMExtractor import | pydantic-ai not installed | ImportError | Yes (AC5 try/except → extractor=None) | Vector-only mode |
| LLMExtractor(model) | construction failure | Exception | Yes (AC5 same try block) | Vector-only mode |
| GraphAugmentedRetriever.retrieve | vector store error | Exception | Yes (KnowledgeQueryService wraps in try/except) | Empty results |

### Codebase Evidence
- EntityExtractor DI slot: `serve/knowledge/src/owlbear_knowledge/extractor.py` L66-73 (`extractor: StructuredExtractor | None = None`)
- KnowledgeQueryService retriever slot: `serve/knowledge/src/owlbear_knowledge/query_service.py` L57 (`retriever: GraphAugmentedRetriever | None = None`)
- search_knowledge drops entity_type: `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` L227 (dict comprehension only includes title/score/snippet)
- GraphAugmentedRetriever: `serve/knowledge/src/owlbear_knowledge/retrieval.py` L36-43 (constructor matches available components vs/gs/emb)

### Challenge Results
- Challenger: FALLBACK — challenger agent not available
- Architect response: Proceeded with high confidence (0.90) — all DI slots pre-built, wiring is mechanical, research corroborates

### Verdict: APPROVE (with refinements applied)
### Action Taken: Fixed metadata defects (depends_on, parent, tags), refined AC4 into AC4a/AC4b with specific wiring targets, advanced to todo
