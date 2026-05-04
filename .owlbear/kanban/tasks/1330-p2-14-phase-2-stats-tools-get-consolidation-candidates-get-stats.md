---
id: 1330
title: 'P2-14: Phase 2 + stats tools (get_consolidation_candidates, get_stats)'
status: research
priority: needed
created: 2026-05-04T05:48:50.144282+00:00
updated: 2026-05-04T05:51:41.339901+00:00
tags:
- phase-2
- scope:mcp-knowledge
- knowledge
parent: 1316
depends_on:
- 1329
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1316 → `.owlbear/briefs/draft-knowledge-activation/brief.md` (§4.4)

## Acceptance Criteria

- [ ] get_consolidation_candidates(limit=N): deterministic SQL, entity names in 2+ sources, excludes reviewed_pairs and existing cross-source edges (O4)
- [ ] Returns: entity_name + relevant chunks from both sources inline
- [ ] store_enrichment with consolidation: writes cross-source edges
- [ ] store_enrichment with empty edges: marks pair in reviewed_pairs (dismissal, D14)
- [ ] New sources generate new candidate pairs; old dismissals preserved
- [ ] get_stats: total sources, total chunks, chunks enriched/total, consolidation candidates remaining (D18)
- [ ] All #1329 tests pass green

## Scope

- **In scope:** MCP tool implementations for get_consolidation_candidates, get_stats
- **Out of scope:** Per-source health breakdown in get_stats (D18 — deferred)