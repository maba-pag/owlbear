---
id: 1332
title: 'P3-16: Search result provenance contract'
status: research
priority: important
created: 2026-05-04T05:48:50.166605+00:00
updated: 2026-05-04T05:51:41.351472+00:00
tags:
- phase-3
- scope:mcp-knowledge
- knowledge
parent: 1316
depends_on:
- 1331
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1316 → `.owlbear/briefs/draft-knowledge-activation/brief.md` (§4.8)

## Acceptance Criteria

- [ ] search_knowledge results include: score, source (name + URL), retrieval_path, entities, related_sources (O5)
- [ ] retrieval_path indicates: "vector", "graph", or "vector+graph"
- [ ] entities array contains extracted entity references (name, type)
- [ ] related_sources array contains cross-source relationships (name, relationship, entity)
- [ ] When enrichment not run, entities and related_sources are empty arrays
- [ ] Response shape deterministic regardless of enrichment state
- [ ] All #1331 tests pass green

## Scope

- **In scope:** search_knowledge response schema extension, provenance field population
- **Out of scope:** Graph query optimization, hybrid sparse vector activation