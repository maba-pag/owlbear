---
id: 1327
title: 'P2-11: Tests — Phase 1 enrichment tools (get_next_batch, store_enrichment)'
status: research
priority: needed
created: 2026-05-04T05:48:50.111772+00:00
updated: 2026-05-04T05:51:41.319112+00:00
tags:
- phase-2
- scope:mcp-knowledge
- knowledge
- test
parent: 1316
depends_on:
- 1324
- 1318
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1316 → `.owlbear/briefs/draft-knowledge-activation/brief.md` (§4.4)

## Acceptance Criteria

- [ ] Tests verify get_next_batch: atomic SELECT+UPDATE with IMMEDIATE transaction
- [ ] Tests verify get_next_batch returns chunk metadata (chunk_id, text, doc_title, section_path, source_name)
- [ ] Tests verify claimed chunks are not returned in subsequent get_next_batch calls
- [ ] Tests verify lease expiry: stale claims (>10 min) revert to pending
- [ ] Tests verify store_enrichment: UPSERT entities (INSERT OR REPLACE)
- [ ] Tests verify store_enrichment: INSERT OR IGNORE edges with UNIQUE constraint
- [ ] Tests verify store_enrichment updates enrichment_state to 'enriched'
- [ ] Tests verify WAL mode concurrent write safety

## Scope

- **In scope:** Phase 1 worker tool tests — get_next_batch, store_enrichment
- **Out of scope:** Phase 2 consolidation (P2-13/14), get_stats (P2-13/14)