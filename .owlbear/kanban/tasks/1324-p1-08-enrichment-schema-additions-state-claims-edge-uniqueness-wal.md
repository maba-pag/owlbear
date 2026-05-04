---
id: 1324
title: 'P1-08: Enrichment schema additions (state, claims, edge uniqueness, WAL)'
status: todo
priority: needed
created: 2026-05-04T05:48:50.076796+00:00
updated: 2026-05-04T15:11:09.267077+00:00
tags:
- phase-1
- scope:knowledge
- knowledge
parent: 1316
depends_on:
- 1323
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1316 → `.owlbear/briefs/draft-knowledge-activation/brief.md` (§4.4)

## Acceptance Criteria

- [ ] enrichment_state column added to chunks: pending → claimed → enriched (td:2)
- [ ] enrichment_state is a new column — consolidated column retains existing semantics (td:1)
- [ ] claimed_at timestamp column on chunks for lease tracking (td:1)
- [ ] reviewed_pairs table created: entity_name + source_a + source_b (td:2)
- [ ] Edge UNIQUE constraint: UNIQUE(source_id, target_id, relation, document_id) (D17) (td:2)
- [ ] WAL mode enabled on SQLite for concurrent writer support (td:0)
- [ ] New chunks default to enrichment_state='pending' (td:1)
- [ ] All #1323 tests pass green (td:0)

## Scope

- **In scope:** Schema migrations/additions in knowledge graph store
- **Out of scope:** Worker claim logic (Layer 2 tools), consolidation tool behavior
[[2026-05-04]]
## Research
- Research doc: .owlbear/research/1324-enrichment-schema-additions.md
- Sources: 5 studied, 3 high-relevance (schema.py, brief §4.4, test file)
- Recommendation: Single migration v10→v11 in schema.py following existing pattern (confidence: 0.95)
- Follow-up tasks created: none (task IS the implementation follow-up)
- Decision requests: none

## Challenge Results
- Challenger: SKIPPED — trivial implementation with no design choices; all specs locked by brief + RED tests
- Key findings: ALTER TABLE ADD COLUMN for chunks (2 cols) and edges (1 col), new reviewed_pairs table, UNIQUE index on edges, WAL PRAGMA. Single-file change (schema.py). NULL document_id on existing edges is safe (SQLite treats NULLs as distinct in UNIQUE indexes). WAL on :memory: is no-op but harmless.
[[2026-05-04]]
## Architecture Review

### AC Refinement
- AC5: Fixed column names from `source_entity, target_entity` → `source_id, target_id` to match actual edges DDL in `serve/knowledge/src/owlbear_knowledge/schema.py`

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single-file schema migration (schema.py only) |
| Interface clarity | PASS | AC specifies exact columns, types, defaults, constraints |
| Dependency correctness | PASS | #1323 (RED tests) archived/done; test file exists with 21 tests |
| Module layering | PASS | Changes isolated to `serve/knowledge/src/owlbear_knowledge/schema.py` |
| TDD compliance | PASS | 21 failing tests in `tests/test_enrichment_schema_1323.py` |
| KISS/YAGNI | PASS | Minimal DDL: 2 cols on chunks, 1 col on edges, 1 table, 1 index, 1 PRAGMA |
| Premise challenge | PASS | Enrichment subsystem requires schema foundation per Brief §4.4 |
| Pattern consistency | PASS | Follows exact v9→v10 migration pattern (ALTER TABLE + contextlib.suppress + DDL constant) |
| Security surface | PASS | Schema DDL only — no system boundary changes |
| Single domain | PASS | Knowledge domain only |

### Challenge Results
- Challenger: SKIPPED — mechanical schema migration with zero design choices. All specs locked by Brief §4.4 + 21 RED tests. Implementation pattern identical to v9→v10.
- Architect response: accepted (skip justified)

### Test Depth
- Max depth: td:2
- Test-writer: SKIP (tests already written in #1323, this is the GREEN pair)

### Verdict: APPROVE
### Action Taken: AC5 column names corrected. Test-depth annotations added. Advanced to todo.