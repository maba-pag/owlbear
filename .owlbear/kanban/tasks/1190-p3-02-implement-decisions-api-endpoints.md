---
id: 1190
title: 'P3-02: Implement decisions API endpoints'
status: research
priority: needed
created: 2026-04-30T00:52:13.248574+00:00
updated: 2026-04-30T00:53:48.706494+00:00
tags:
- phase-3
- scope:cockpit
- type:impl
parent: 1179
depends_on:
- 1181
- 1189
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---

## Acceptance Criteria

- `GET /api/decisions/pending` endpoint registered in Cockpit routes
- Reads pending/*.md files, parses frontmatter, returns structured JSON
- Response shape: `{count: int, items: [{id, task_id, agent, request_type, created, title, body_preview}]}`
- body_preview truncated to ~200 chars
- Returns `{count: 0, items: []}` when pending/ is empty or missing
- `POST /api/decisions/{id}/resolve` endpoint registered
- Accepts `{response: enum, notes?: string}`, validates response enum
- Updates file: sets response field in frontmatter, appends ## Response with notes
- Returns 404 for non-existent DR id
- Uses existing DI pattern (get_engine) for engine access
- All tests from #1189 pass

## Scope

- IN: two Cockpit API endpoints (route module + registration)
- OUT: frontend components, decisions.py changes

Brief: see parent #1179
