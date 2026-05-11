---
id: 1493
title: 'Cockpit: Centralize API client (tasks + decisions)'
status: research
priority: needed
created: 2026-05-11T23:15:20.997863+00:00
updated: 2026-05-11T23:15:31.279703+00:00
tags:
- cockpit
- frontend
parent:
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective\nCreate api/tasks.ts and api/decisions.ts to replace raw fetch() across 5+ components.\n\n## Acceptance Criteria\n- api/tasks.ts: moveTask(), editTask(), releaseTask(), getTask() with consistent error envelope parsing\n- api/decisions.ts: resolveDR() with consistent error handling\n- KanbanBoard, DetailTab, ArchivalModal, ResolveModal use these instead of raw fetch\n- All response types properly typed\n- Error parsing centralized (getResponseErrorMessage already exists, integrate)\n\n## Source\nCockpit audit 2026-05-11, Finding F4