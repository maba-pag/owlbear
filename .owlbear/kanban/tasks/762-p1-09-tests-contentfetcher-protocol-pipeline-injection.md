---
id: 762
title: 'P1-09: Tests — ContentFetcher protocol + pipeline injection'
status: research
priority: needed
created: '2026-04-10T10:55:57.297626+00:00'
updated: '2026-04-10T10:55:57.297626+00:00'
tags:
- phase-1
- type:test
- scope:knowledge
parent: 751
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
RED phase. Tests for ContentFetcher protocol:
1. ContentFetcher Protocol definition (async fetch → cleaned text + metadata)
2. BrowserContentFetcher delegates to CDP manager + extractor
3. Default HttpxContentFetcher unchanged for unauthenticated sources
4. Pipeline accepts ContentFetcher via protocol injection

Mock-based. All tests fail (RED).

Parent: #751
