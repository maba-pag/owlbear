---
id: 1326
title: 'P1-10: Browser fetcher wiring + RefreshOrchestrator fix'
status: research
priority: needed
created: 2026-05-04T05:48:50.100105+00:00
updated: 2026-05-04T05:50:51.062779+00:00
tags:
- phase-1
- scope:knowledge
- knowledge
parent: 1316
depends_on:
- 1325
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1316 → `.owlbear/briefs/draft-knowledge-activation/brief.md` (§4.5, §4.7)

## Acceptance Criteria

- [ ] ContentFetcher injected into RefreshOrchestrator (HTTP or browser based on source fetch_method)
- [ ] GraphStore injected for entity/edge cleanup on re-ingest
- [ ] inter_doc_builder skipped — enrichment handled by agent workers
- [ ] refresh_source uses saved fetch_method from source manifest (O2)
- [ ] Browser fetcher selected when fetch_method='browser' in source record (O3)
- [ ] All #1325 tests pass green

## Scope

- **In scope:** RefreshOrchestrator wiring, ContentFetcher injection, fetch_method routing
- **Out of scope:** HTTP-first detection UX (agent-side), Playwright browser module changes