---
id: 1325
title: 'P1-09: Tests — Browser fetcher wiring + RefreshOrchestrator fix'
status: research
priority: needed
created: 2026-05-04T05:48:50.088181+00:00
updated: 2026-05-04T05:50:51.057041+00:00
tags:
- phase-1
- scope:knowledge
- knowledge
- test
parent: 1316
depends_on:
- 1320
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1316 → `.owlbear/briefs/draft-knowledge-activation/brief.md` (§4.5, §4.7)

## Acceptance Criteria

- [ ] Tests verify ContentFetcher injection into RefreshOrchestrator (HTTP and browser modes)
- [ ] Tests verify GraphStore injection for entity/edge cleanup on re-ingest
- [ ] Tests verify fetch_method from source manifest determines fetcher type (http vs browser)
- [ ] Tests verify RefreshOrchestrator works without inter_doc_builder (skipped — agent workers handle enrichment)
- [ ] Tests verify refresh_source uses saved fetch_method from source record

## Scope

- **In scope:** RefreshOrchestrator dependency injection, browser fetcher selection logic
- **Out of scope:** Browser detection UX flow (agent-side, §4.5), Playwright integration testing