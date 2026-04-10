---
id: 765
title: 'P1-12: Impl — Pipeline quality: hash on cleaned content + replace-on-change'
status: research
priority: needed
created: '2026-04-10T10:55:57.388835+00:00'
updated: '2026-04-10T10:55:57.388835+00:00'
tags:
- phase-1
- scope:knowledge
parent: 751
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
GREEN phase. Delta detection modified to hash cleaned text. Replace-on-change: cascade-delete old doc + entities + edges before re-ingestion.

All P1-11 tests pass.

Parent: #751
