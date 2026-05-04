---
id: 1320
title: 'P0-04: Qdrant filesystem persistence + source identity fix'
status: backlog
priority: critical
created: 2026-05-04T05:48:37.771717+00:00
updated: 2026-05-04T12:12:46.135113+00:00
tags:
- phase-0
- scope:knowledge
- knowledge
parent: 1316
depends_on:
- 1319
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1316 → `.owlbear/briefs/draft-knowledge-activation/brief.md` (§4.3)

## Acceptance Criteria

- [ ] Qdrant uses filesystem persistence — vectors survive server restart (O6)
- [ ] SQLite DB on disk — data survives server restart (O6)
- [ ] Both Qdrant and SQLite storage paths are gitignored
- [ ] ingest_document registers/resolves source record before storing chunks
- [ ] Source record: name, URL/path, fetch_method (http/browser/local), enrich flag (true/false), timestamps
- [ ] Source identity resolved by URL (web) or file path (local)
- [ ] All #1319 tests pass green

## Scope

- **In scope:** Qdrant config, SQLite persistence, source record table/model, ingest_document source registration
- **Out of scope:** Enrichment schema (Layer 1), browser detection flow (Layer 1)
[[2026-05-04]]
## Research
- Research doc: .owlbear/research/1320-qdrant-persistence-source-identity-impl.md
- Sources: 10 studied, 6 high-relevance (1.0)
- Recommendation: 4-change wiring task (~20 LOC across server.py + .gitignore) (confidence: 0.92)
- Follow-up tasks created: none — this IS the implementation task
- Decision requests: none

## Key Findings

All library code already works — 34/34 #1319 tests pass GREEN. Gaps are MCP server wiring only:

1. `QdrantVectorStore()` in lifespan defaults to `:memory:` — needs `location=".owlbear/knowledge/vectors"`
2. `IngestPipeline()` missing `source_store=source_store` kwarg (created but not passed)
3. MCP `ingest_document` tool lacks `source_url`/`source_id` params (pipeline supports them)
4. `.gitignore` missing Qdrant directory entry

## Challenge Results
Challenge: proceed — confidence 0.92. Trivial wiring, no design ambiguity.