---
id: 1226
title: Frontend — dedup rowStyleForState + delete scratch files
status: backlog
priority: nice-to-have
created: '2026-04-30 16:31:18.617727+00:00'
updated: '2026-04-30 16:33:23.428939+00:00'
tags:
- cockpit
- frontend
- cleanup
parent:
depends_on:
- 1225
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective
Remove duplicated utility function and orphaned scratch artifacts.

## Acceptance Criteria
- [ ] `rowStyleForState` extracted to shared utility (e.g. `src/utils/styles.ts`)
- [ ] `ActivityTab.tsx` and `HistorySubtab.tsx` import from shared utility
- [ ] All 9 `.owlbear*` scratch files deleted from `serve/cockpit/web/`
- [ ] Tests pass

## Files
- `serve/cockpit/web/src/components/ActivityTab.tsx`
- `serve/cockpit/web/src/components/HistorySubtab.tsx`
