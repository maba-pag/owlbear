---
id: 1322
title: 'P0-06: Content injection guard wiring at ingest pipeline'
status: research
priority: critical
created: 2026-05-04T05:48:37.792577+00:00
updated: 2026-05-04T05:50:51.042407+00:00
tags:
- phase-0
- scope:knowledge
- knowledge
parent: 1316
depends_on:
- 1321
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1316 → `.owlbear/briefs/draft-knowledge-activation/brief.md` (§4.6)

## Acceptance Criteria

- [ ] ContentInjectionGuard wired into ingest_document tool path (O9)
- [ ] All web content passes through guard before being stored as chunks
- [ ] Guard rejects or sanitizes content containing injection markers
- [ ] Pre-guard legacy chunks are not retroactively scanned (D20 — one-time edge case)
- [ ] All #1321 tests pass green

## Scope

- **In scope:** Wire existing ContentInjectionGuard into MCP ingest_document path
- **Out of scope:** Guard at enrichment time (D20), modifying guard implementation itself