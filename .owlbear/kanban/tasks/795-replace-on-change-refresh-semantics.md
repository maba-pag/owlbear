---
id: 795
title: Replace-on-change refresh semantics
status: backlog
priority: important
created: '2026-04-10T12:31:51.917663+00:00'
updated: '2026-04-10T12:31:51.917663+00:00'
tags:
- phase-1
- scope:knowledge
parent: 775
depends_on:
- 791
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- `ingest.py` changed branch calls `delete_document_data(conn, existing_id)` before inserting the new document
- Ghost document bug (F1) fixed — `existing_id` now used in the content-changed path
- All #791 tests pass; existing ingest tests still pass
- File: `serve/knowledge/src/owlbear_knowledge/ingest.py`

## Context
- WS-D: Pipeline Integration
- Scope item 10 from #775
- See research F1: ghost document bug — delete_document_data() already exists for cascade
