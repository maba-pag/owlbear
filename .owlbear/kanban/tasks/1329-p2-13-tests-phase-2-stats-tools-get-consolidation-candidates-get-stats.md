---
id: 1329
title: 'P2-13: Tests — Phase 2 + stats tools (get_consolidation_candidates, get_stats)'
status: research
priority: needed
created: 2026-05-04T05:48:50.133593+00:00
updated: 2026-05-04T05:51:41.334704+00:00
tags:
- phase-2
- scope:mcp-knowledge
- knowledge
- test
parent: 1316
depends_on:
- 1328
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1316 → `.owlbear/briefs/draft-knowledge-activation/brief.md` (§4.4)

## Acceptance Criteria

- [ ] Tests verify get_consolidation_candidates: deterministic SQL finding entity names in 2+ sources
- [ ] Tests verify candidates exclude entries with existing cross-source edges or reviewed_pairs
- [ ] Tests verify candidates return entity_name + relevant chunks from both sources inline
- [ ] Tests verify store_enrichment with consolidation: writes cross-source edges
- [ ] Tests verify store_enrichment with empty edges marks pair in reviewed_pairs (dismissal)
- [ ] Tests verify new sources generate new candidate pairs; old dismissals preserved
- [ ] Tests verify get_stats: total sources, total chunks, chunks enriched/total, consolidation candidates remaining

## Scope

- **In scope:** Phase 2 consolidation tool tests, get_stats tests
- **Out of scope:** Phase 1 tools (P2-11/12), agent enricher loop