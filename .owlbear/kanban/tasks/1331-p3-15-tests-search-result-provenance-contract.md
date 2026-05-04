---
id: 1331
title: 'P3-15: Tests — Search result provenance contract'
status: research
priority: important
created: 2026-05-04T05:48:50.155044+00:00
updated: 2026-05-04T05:51:41.345513+00:00
tags:
- phase-3
- scope:mcp-knowledge
- knowledge
- test
parent: 1316
depends_on:
- 1324
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1316 → `.owlbear/briefs/draft-knowledge-activation/brief.md` (§4.8)

## Acceptance Criteria

- [ ] Tests verify search results include retrieval_path field (vector/graph/vector+graph)
- [ ] Tests verify search results include entities array (extracted entity references)
- [ ] Tests verify search results include related_sources array (cross-source relationships)
- [ ] Tests verify provenance fields are empty arrays when enrichment has not been run
- [ ] Tests verify response shape is deterministic regardless of enrichment state
- [ ] Tests verify source field includes name and URL

## Scope

- **In scope:** search_knowledge response contract tests, provenance field shape
- **Out of scope:** Graph query optimization, ranking algorithm changes