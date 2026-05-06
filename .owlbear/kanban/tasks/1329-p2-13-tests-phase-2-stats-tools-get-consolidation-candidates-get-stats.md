---
id: 1329
title: 'P2-13: Tests — Phase 2 + stats tools (get_consolidation_candidates, get_stats)'
status: todo
priority: needed
created: 2026-05-04T05:48:50.133593+00:00
updated: 2026-05-06T00:14:15.338478+00:00
tags:
- phase-2
- scope:mcp-knowledge
- knowledge
- test
parent: 1316
depends_on:
- 1328
blocked: true
block_reason: 'Double crash: test-writer agent returned no response twice (cycle 39).
  Likely transient infrastructure issue.'
claimed_at: 2026-05-06T00:13:09.623195+00:00
archival_reason:
archival_refs: []
---

Brief: see parent #1316 → `.owlbear/briefs/draft-knowledge-activation/brief.md` (§4.4)

## Acceptance Criteria

- [ ] Tests verify get_consolidation_candidates(ctx, limit=20): deterministic SQL (ORDER BY entity_name) finding entity names in 2+ sources (td:2)
- [ ] Tests verify candidates exclude entries with existing cross-source edges or reviewed_pairs rows (td:2)
- [ ] Tests verify candidates return list of dicts with entity_name + relevant chunks from both sources inline (td:1)
- [ ] Tests verify store_enrichment Phase 2 mode (ctx, candidate_id, edges=[...]): writes cross-source edges when edges non-empty (td:1)
- [ ] Tests verify store_enrichment Phase 2 mode with empty edges=[] marks pair in reviewed_pairs (dismissal) (td:1)
- [ ] Tests verify new sources generate new candidate pairs; old dismissals in reviewed_pairs preserved (td:2)
- [ ] Tests verify get_stats returns additive result: preserves existing {documents, entities, edges} AND adds total_sources, total_chunks, chunks_enriched_ratio, consolidation_candidates_remaining (td:2)

## Scope

- **In scope:** Phase 2 consolidation tool tests, get_stats expansion tests
- **Out of scope:** Phase 1 tools (P2-11/12), agent enricher loop, existing get_stats durable suite compatibility (existing package-local tests cover legacy fields)

## Notes for builder

- Import `get_consolidation_candidates` from `owlbear_mcp_knowledge.server` (ImportError RED until #1330)
- Phase 2 `store_enrichment` has different signature than Phase 1 per Brief §4.4 line 97: `store_enrichment(candidate_id, edges=[...])` — test the Phase 2 entry point separately
- `get_stats` expansion: current impl uses `graph_store.get_counts()` for legacy fields; new fields (sources, chunks, enrichment ratio, candidates) are SQL-based via `conn`. Tests must mock/provide both
- Follow fixture patterns from `tests/test_mcp_knowledge_enrichment_tools_1327.py` (in-memory SQLite + init_db + MagicMock MCP ctx)
- `reviewed_pairs` table PK: `(entity_name, source_a, source_b)` — already in schema.py

[[2026-05-05]]
## Research
- Research doc: .owlbear/research/phase2-consolidation-tests-1329.md
- Sources: 6 studied, 4 high-relevance (all internal codebase)
- Recommendation: Single test file following #1327 patterns — import get_consolidation_candidates (ImportError RED), test expanded get_stats fields, test store_enrichment Phase 2 dismissal mode (confidence: 0.88)
- Follow-up tasks created: none needed — #1330 is the builder task
- Decision requests: none

## Challenge Results
- Challenger: FALLBACK — trivial test-structure research with no design trade-offs
- Confidence in original: 0.88
- Key findings: schema ready (reviewed_pairs, enrichment_state exist), get_stats needs expansion from 3 fields to include sources/chunks/enrichment-ratio/candidates-remaining, get_consolidation_candidates has no implementation yet (clean RED)
[[2026-05-06]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Tests only for Phase 2 consolidation + stats expansion |
| Interface clarity | PASS (after refine) | Refined AC to pin Phase 2 store_enrichment signature, get_stats additive contract, deterministic ORDER BY |
| Dependency correctness | PASS | #1328 archived (Phase 1 tools complete); reviewed_pairs schema exists |
| Module layering | PASS | Tests import from owlbear_mcp_knowledge.server; no upward imports |
| TDD compliance | PASS | This IS the test task; #1330 builder depends on it |
| KISS/YAGNI | PASS | Scoped to Brief §4.4 spec; no extras |
| Premise challenge | PASS | get_consolidation_candidates doesn't exist (clean RED); get_stats expansion is brief-mandated |
| Pattern consistency | PASS | Follows #1327 test patterns: in-memory SQLite, init_db, MagicMock MCP ctx |
| Security surface | PASS | Test-only task; no new system boundaries |
| Single domain | PASS | All in knowledge/mcp-knowledge domain |

### Challenge Results
- Challenger: reconsider (confidence 0.67)
- Concerns: (1) Phase 2 store_enrichment signature ambiguity, (2) get_stats additive vs. replacement unclear, (3) dual data source for get_stats not noted
- Architect response: ACCEPTED — refined all 3 concerns into AC. AC4/5 now pin `(candidate_id, edges=[...])` signature. AC7 now explicitly states additive semantics. Builder notes explain dual data source (graph_store + conn).

### Test Depth
- Max depth: td:2
- Test-writer: SKIP (task tagged `test` — pass-through)

### Verdict: APPROVE (with AC refinement)
### Action Taken: Refined AC to resolve challenger concerns (signature, additive semantics, dual data source). Added builder notes section. Advanced to todo.