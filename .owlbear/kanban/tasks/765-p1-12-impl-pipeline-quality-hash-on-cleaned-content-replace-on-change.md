---
id: 765
title: 'P1-12: Impl — Pipeline quality: hash on cleaned content + replace-on-change'
status: backlog
priority: needed
created: '2026-04-10T10:55:57.388835+00:00'
updated: '2026-04-12T22:41:03.475162+00:00'
tags:
- phase-1
- scope:knowledge
parent: 751
depends_on: []
blocked: false
block_reason: null
claimed_by: green-dew
claimed_at: '2026-04-12T22:41:03.475162+00:00'
---
GREEN phase. Delta detection modified to hash cleaned text. Replace-on-change: cascade-delete old doc + entities + edges before re-ingestion.

All P1-11 tests pass.

Parent: #751

[[2026-04-12]]
## Research
- Research doc: .owlbear/research/765-pipeline-quality-hash-cleaned-content.md
- Sources: 7 studied, 5 high-relevance (.90+)
- Recommendation: `content_cleaner: Callable[[str], str] | None` param on `ingest()` (confidence: .88)
- Follow-up tasks created: none — implementation already delivered
- Decision requests: none

## Validation Pass (2026-04-12)
Existing research doc validated against current codebase. All claims confirmed:
- `content_cleaner` param exists on `ingest()` (ingest.py:144)
- `content_for_hash` computed before both hash operations (lines 177, 183, 250)
- Cascade-delete wired at line 193 via `delete_document_data()`
- All 12 RED-phase tests (#764) pass: 4 hash-cleaned, 3 cascade-delete, 2 skip-unchanged, 3 no-accumulation
- Tier: T1 — Autonomous (backward-compatible optional parameter)

## Challenge Results
- Challenger: FALLBACK — subagent not available
- Confidence in original: .88
- Self-challenge: chunker receives raw content (separate Phase 2 concern), ingest_text() excluded (no delta detection), clean() is sub-ms (no perf risk)
- Researcher response: accepted — no revisions needed