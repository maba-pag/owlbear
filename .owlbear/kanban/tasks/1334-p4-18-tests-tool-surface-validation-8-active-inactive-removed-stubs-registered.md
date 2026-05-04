---
id: 1334
title: 'P4-18: Tests — Tool surface validation (8 active, inactive removed, stubs
  registered)'
status: research
priority: important
created: 2026-05-04T05:48:50.188392+00:00
updated: 2026-05-04T05:51:41.361698+00:00
tags:
- phase-4
- scope:mcp-knowledge
- knowledge
- test
parent: 1316
depends_on:
- 1330
- 1332
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1316 → `.owlbear/briefs/draft-knowledge-activation/brief.md` (§4.9)

## Acceptance Criteria

- [ ] Tests verify exactly 8 tools registered in active MCP server (O7)
- [ ] Tests verify active tools: search_knowledge, list_sources, get_stats, ingest_document, refresh_source, get_next_batch, get_consolidation_candidates, store_enrichment
- [ ] Tests verify removed tools not registered: list_entities, bookmark_source, list_bookmarks, update_bookmark_tags, consolidate_knowledge
- [ ] Tests verify 4 scope stubs exist: import_scope, export_scope, sync_from_global, sync_to_global
- [ ] Tests verify scope stubs are not exposed to agents (registered internally but not in tool list)

## Scope

- **In scope:** Tool registration validation, tool count assertion, stub existence check
- **Out of scope:** Scope stub implementation (D12, D16 — deferred)