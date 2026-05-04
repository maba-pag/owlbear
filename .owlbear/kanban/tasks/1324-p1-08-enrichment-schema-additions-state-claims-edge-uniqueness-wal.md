---
id: 1324
title: 'P1-08: Enrichment schema additions (state, claims, edge uniqueness, WAL)'
status: research
priority: needed
created: 2026-05-04T05:48:50.076796+00:00
updated: 2026-05-04T05:50:51.051483+00:00
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

- [ ] enrichment_state column added to chunks: pending → claimed → enriched
- [ ] enrichment_state is a new column — consolidated column retains existing semantics
- [ ] claimed_at timestamp column on chunks for lease tracking
- [ ] reviewed_pairs table created: entity_name + source_a + source_b
- [ ] Edge UNIQUE constraint: UNIQUE(source_entity, target_entity, relation, document_id) (D17)
- [ ] WAL mode enabled on SQLite for concurrent writer support
- [ ] New chunks default to enrichment_state='pending'
- [ ] All #1323 tests pass green

## Scope

- **In scope:** Schema migrations/additions in knowledge graph store
- **Out of scope:** Worker claim logic (Layer 2 tools), consolidation tool behavior