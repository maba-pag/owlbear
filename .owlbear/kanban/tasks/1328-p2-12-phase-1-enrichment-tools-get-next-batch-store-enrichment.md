---
id: 1328
title: 'P2-12: Phase 1 enrichment tools (get_next_batch, store_enrichment)'
status: research
priority: needed
created: 2026-05-04T05:48:50.122372+00:00
updated: 2026-05-04T05:51:41.329220+00:00
tags:
- phase-2
- scope:mcp-knowledge
- knowledge
parent: 1316
depends_on:
- 1327
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1316 → `.owlbear/briefs/draft-knowledge-activation/brief.md` (§4.4)

## Acceptance Criteria

- [ ] get_next_batch(limit=N): SELECT pending chunks, IMMEDIATE transaction, UPDATE to claimed + set claimed_at
- [ ] Returns: chunk_id, text, doc_title, section_path, source_name
- [ ] Claimed chunks excluded from subsequent get_next_batch calls
- [ ] Lease expiry: on-demand during get_next_batch, resets stale claims (>10 min) to pending
- [ ] store_enrichment(chunk_id, entities, edges): UPSERT entities, INSERT OR IGNORE edges with UNIQUE(src, tgt, rel, doc_id)
- [ ] store_enrichment updates chunk enrichment_state to 'enriched' (O4)
- [ ] Per-source enrich flag respected: chunks from enrich=false sources not queued (O8)
- [ ] All #1327 tests pass green

## Scope

- **In scope:** MCP tool implementations for get_next_batch, store_enrichment
- **Out of scope:** Phase 2 consolidation tools, agent worker loop