---
id: 791
title: Tests — Replace-on-change refresh semantics
status: backlog
priority: needed
created: '2026-04-10T12:31:33.717159+00:00'
updated: '2026-04-10T12:31:33.717159+00:00'
tags:
- phase-1
- scope:knowledge
- type:test
parent: 775
depends_on:
- 785
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- Tests verify: when content changes for an existing document, the old document is deleted via `delete_document_data(existing_id)` before new insertion
- Tests verify: no ghost documents remain after content-change re-ingest (F1 regression test)
- Tests verify: unchanged content still skips (no delete, no re-ingest)
- File: `tests/test_replace_on_change_775.py`

## Context
- WS-D: Pipeline Integration
- Scope item 10 from #775
- See research F1: ghost document bug — existing_id unused in changed branch