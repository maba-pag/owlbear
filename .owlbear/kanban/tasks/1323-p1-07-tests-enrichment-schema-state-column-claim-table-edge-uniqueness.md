---
id: 1323
title: 'P1-07: Tests — Enrichment schema (state column, claim table, edge uniqueness)'
status: research
priority: needed
created: 2026-05-04T05:48:50.064935+00:00
updated: 2026-05-04T05:50:51.046749+00:00
tags:
- phase-1
- scope:knowledge
- knowledge
- test
parent: 1316
depends_on:
- 1320
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1316 → `.owlbear/briefs/draft-knowledge-activation/brief.md` (§4.4)

## Acceptance Criteria

- [ ] Tests verify enrichment_state column on chunks table (values: pending, claimed, enriched)
- [ ] Tests verify enrichment_state does NOT reuse the existing consolidated column
- [ ] Tests verify claimed_at timestamp column for lease tracking
- [ ] Tests verify reviewed_pairs table: entity_name + source_a + source_b
- [ ] Tests verify edge UNIQUE constraint: UNIQUE(source_entity, target_entity, relation, document_id) (D17)
- [ ] Tests verify new chunks default to enrichment_state='pending'

## Scope

- **In scope:** Schema addition tests — columns, tables, constraints, defaults
- **Out of scope:** Worker claim logic (Layer 2), enrichment tool behavior (Layer 2)