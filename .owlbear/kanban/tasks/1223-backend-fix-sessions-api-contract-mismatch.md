---
id: 1223
title: Backend — fix sessions API contract mismatch
status: backlog
priority: needed
created: '2026-04-30 16:31:18.589039+00:00'
updated: '2026-04-30 21:37:32.990854+00:00'
tags:
- cockpit
- bug
parent:
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective
Fix contract mismatch between GET /api/sessions response shape and frontend expectations.

## Acceptance Criteria
- [ ] Backend `GET /api/sessions` returns `{"sessions": [...]}` envelope (matching frontend ActivityTab.tsx expectation of `data.sessions`)
- [ ] Or: frontend is updated to expect `list` directly — whichever is the cleaner contract
- [ ] Existing backend tests updated to match chosen contract
- [ ] Frontend ActivityTab correctly parses the response

## Context
Backend returns `list[SessionRecord]` at top level. Frontend `ActivityTab.tsx` line ~63 does `data.sessions` expecting an envelope. This will fail at runtime when the tab is wired in.

## Files
- `serve/cockpit/src/owlbear_cockpit/routes/read.py`
- `serve/cockpit/web/src/components/ActivityTab.tsx`
