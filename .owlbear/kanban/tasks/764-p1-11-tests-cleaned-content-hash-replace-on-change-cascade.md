---
id: 764
title: 'P1-11: Tests — Cleaned-content hash + replace-on-change cascade'
status: research
priority: needed
created: '2026-04-10T10:55:57.357680+00:00'
updated: '2026-04-10T10:55:57.357680+00:00'
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
RED phase. Tests for pipeline quality fixes:
1. Delta detection hashes cleaned markdown, not raw HTML
2. Changed content → old doc + entities + edges cascade-deleted before re-ingestion
3. Unchanged content hash → skip
4. No entity accumulation on refresh

All tests fail (RED). Depends on schema (#757).

Parent: #751
