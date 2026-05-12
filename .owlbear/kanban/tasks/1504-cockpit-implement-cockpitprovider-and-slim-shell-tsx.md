---
id: 1504
title: 'Cockpit: Implement CockpitProvider and slim Shell.tsx'
status: backlog
priority: important
created: 2026-05-12T02:59:59.210772+00:00
updated: 2026-05-12T10:47:41.434551+00:00
tags:
  - cockpit
  - frontend
  - refactor
parent: 1491
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective
Extract all state management from Shell.tsx into a CockpitProvider context component.

## Acceptance Criteria
- CockpitProvider.tsx (~150 LOC) created in `src/hooks/` alongside EventSourceProvider
- Provider calls useBoard, usePendingDRs, useScanPolling internally
- Three consumer hooks exported: useBoardState(), useTaskSelection(), useDRState()
- Task fetch effect (with AbortController) moved into provider or internal useTaskFetch hook
- Cross-domain effect: lastDecisionsMtime → refetchPendingDRs lives inside provider (F10)
- useConnectionHealth remains inside useBoard (F11 — no change needed, already co-located)
- Provider placed in App.tsx inside EventSourceProvider, wrapping ErrorBoundary + Shell
- Shell.tsx reduced to ~75 LOC: CSS grid layout, view-local refs (tabsRef, detailRef, activityRef), tab-change accessibility effect, component composition via consumer hooks
- No prop drilling through Shell — children consume context hooks directly
- All existing Vitest suites pass (npm test)
- Callback identities stable — rely on React Compiler; add explicit useCallback only if churn observed

## Source
Research: .owlbear/research/1491-cockpit-provider-extraction.md
2026-05-12T10:47:41+00:00
Advanced from research to backlog. Research phase complete — full AC present from researcher. Ready for independent architecture review.