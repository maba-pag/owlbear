---
id: 1492
title: 'Cockpit: Decompose DetailTab.tsx into 4 components'
status: research
priority: important
created: 2026-05-11T23:15:07.557623+00:00
updated: 2026-05-11T23:20:15.838029+00:00
tags:
- cockpit
- frontend
- refactor
parent:
depends_on:
- 1493
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective\nSplit 598-line DetailTab.tsx into focused components.\n\n## Acceptance Criteria\n- DetailTab.tsx → ~80 LOC container\n- TaskFieldsEditor.tsx (~200 LOC) — title, priority, body, deps, parent, block_reason editing\n- ConflictBanner.tsx + useConflictDraft.ts (~120 LOC) — OCC conflict detection, draft preservation, merge UI\n- TaskActions.tsx (~80 LOC) — claim/release/archive buttons\n- HistorySubtab.tsx stays as-is (already separated)\n\n## Source\nCockpit audit 2026-05-11, Finding F2