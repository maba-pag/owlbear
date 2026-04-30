---
id: 1227
title: 'Frontend — polling refactor: remove /health redundancy + shared utility'
status: backlog
priority: needed
created: '2026-04-30 16:31:18.626374+00:00'
updated: '2026-04-30 16:33:23.434922+00:00'
tags:
- cockpit
- frontend
- refactor
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
Remove redundant /health polling and extract shared polling pattern.

## Acceptance Criteria
- [ ] `/health` polling removed — connection health derived from tasks poll response (success = green, fail = degrade)
- [ ] Shared `usePollingFetch` or similar utility extracted with inFlight/coalesce/cleanup pattern
- [ ] `useBoard`, `useScanPolling`, `usePendingDRs` use the shared utility
- [ ] Traffic light in Shell still shows green/yellow/red based on connection health
- [ ] All frontend tests pass

## Files
- `serve/cockpit/web/src/hooks/usePolling.ts` (remove or repurpose)
- `serve/cockpit/web/src/hooks/useBoard.ts`
- `serve/cockpit/web/src/hooks/useScanPolling.ts`
- `serve/cockpit/web/src/hooks/usePendingDRs.ts`
- `serve/cockpit/web/src/hooks/useConnectionHealth.ts`
