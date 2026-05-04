---
id: 1335
title: 'P4-19: Tool surface cleanup + scope stubs'
status: research
priority: important
created: 2026-05-04T05:48:50.199644+00:00
updated: 2026-05-04T05:51:41.367530+00:00
tags:
- phase-4
- scope:mcp-knowledge
- knowledge
parent: 1316
depends_on:
- 1334
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1316 → `.owlbear/briefs/draft-knowledge-activation/brief.md` (§4.9)

## Acceptance Criteria

- [ ] Only 8 active tools registered: search_knowledge, list_sources, get_stats, ingest_document, refresh_source, get_next_batch, get_consolidation_candidates, store_enrichment (O7)
- [ ] Removed from registration: list_entities, bookmark_source, list_bookmarks, update_bookmark_tags, consolidate_knowledge
- [ ] 4 scope stubs registered internally: import_scope, export_scope, sync_from_global, sync_to_global (D12, D16)
- [ ] Scope stubs not exposed to agents — registered but excluded from tool discovery
- [ ] All #1334 tests pass green

## Scope

- **In scope:** MCP tool registration cleanup, scope stub creation
- **Out of scope:** Scope stub implementation (D12, D16), delete_source tool (D19)