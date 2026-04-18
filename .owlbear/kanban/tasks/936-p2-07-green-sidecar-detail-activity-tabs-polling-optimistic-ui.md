---
id: 936
title: 'P2-07: GREEN — Sidecar (Detail + Activity tabs) + polling + optimistic UI'
status: research
priority: important
created: 2026-04-17T19:59:03.599720+00:00
updated: 2026-04-17T19:59:03.599720+00:00
tags:
- cockpit
- frontend
- phase-2
- type:build
parent: 920
depends_on:
- 935
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Brief: see parent #920

## Objective

Implement sidecar tabs, polling infrastructure, and optimistic UI to pass RED tests from #935.

## Acceptance Criteria

- [ ] Detail tab: allowlisted YAML fields as structured controls (PDS or Radix inputs, dropdowns, tag chips); markdown body rendered with react-markdown + remark-gfm + rehypeSanitize; toggle edit mode for body
- [ ] Save-time `updated` comparison (D9): on 409, show refresh-or-overwrite modal with current vs. server values
- [ ] History subtab: per-session breakdown from `GET /api/sessions?task_id={id}` (agent, duration, outcome)
- [ ] Activity tab: sessions from `GET /api/sessions?filter=`; default filter = active; switchable filters (all / failed-or-rejected / released)
- [ ] Click session row selects task in Detail tab + activates History subtab
- [ ] Polling: mtime-aware ~3s interval (TanStack Query refetchInterval or custom hook); skip 1 cycle after local mutation
- [ ] Connection health traffic light in status bar: green (poll within threshold) / yellow (lagging) / red (disconnected)
- [ ] Optimistic UI: snapshot state before mutation; immediate local update; rollback on API error
- [ ] Confirmation dialogs: backward moves, unclaim, unblock (surfaces block_reason before clearing)
- [ ] XSS hardening: strict CSP meta tag; no `dangerouslySetInnerHTML`; rehypeSanitize on all task-derived markdown
- [ ] Designed empty, loading, and error states for both tabs (no white-screen paths)
- [ ] All RED tests from #935 pass

## Files

- `serve/cockpit/web/src/components/DetailTab.tsx`
- `serve/cockpit/web/src/components/ActivityTab.tsx`
- `serve/cockpit/web/src/components/HistorySubtab.tsx`
- `serve/cockpit/web/src/components/ConfirmDialog.tsx`
- `serve/cockpit/web/src/hooks/usePolling.ts`
- `serve/cockpit/web/src/hooks/useOptimistic.ts`
- `serve/cockpit/web/src/hooks/useConnectionHealth.ts`