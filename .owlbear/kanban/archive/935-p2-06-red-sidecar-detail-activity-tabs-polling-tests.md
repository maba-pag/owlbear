---
id: 935
title: 'P2-06: RED — Sidecar (Detail + Activity tabs) + polling tests'
status: research
priority: important
created: 2026-04-17T19:58:48.870731+00:00
updated: 2026-04-17T19:58:48.870731+00:00
tags:
- cockpit
- frontend
- phase-2
- type:test
parent: 920
depends_on:
- 933
- 934
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Brief: see parent #920

## Objective

Write failing tests for the sidecar Detail tab (task editing, conflict detection, history), Activity tab (sessions, filtering), polling infrastructure, and optimistic UI.

## Acceptance Criteria

- [ ] Test files for Detail tab, Activity tab, polling hook, and optimistic UI (Vitest + React Testing Library)
- [ ] Detail tab tests cover:
  - Renders allowlisted YAML fields as structured controls (title input, tag chips, priority dropdown, depends_on, parent, block_reason)
  - Read-only fields (id, created, claimed, status) shown as text with no edit affordance
  - Renders markdown body via react-markdown (sanitized output, no raw HTML injection)
  - Edit mode toggle for markdown body
  - Save sends `POST /api/tasks/{id}/edit` with `updated` snapshot
  - 409 response triggers refresh-or-overwrite modal (D9 conflict detection)
  - History subtab shows per-session breakdown (agent, duration, outcome)
  - "Oppose-the-flow" confirmations: backward move, unclaim, unblock require confirm dialog; unblock dialog surfaces existing block_reason
- [ ] Activity tab tests cover:
  - Default filter shows active sessions (running + stuck)
  - Filter switches: all / failed-or-rejected / released
  - Session row shows: agent name, task reference, state label, duration
  - Click row opens Detail tab for that task with History subtab active
- [ ] Polling tests cover:
  - Polls `GET /api/tasks` at ~3s interval using mtime for change detection
  - Skips 1 poll cycle after a local mutation
  - Connection health: green (poll OK within threshold), yellow (lagging), red (disconnected)
- [ ] Optimistic UI tests cover:
  - Mutation immediately updates local state
  - On API error, state rolls back to pre-mutation snapshot
- [ ] All tests fail (RED phase)

## Files

- `serve/cockpit/web/src/__tests__/DetailTab.test.tsx`
- `serve/cockpit/web/src/__tests__/ActivityTab.test.tsx`
- `serve/cockpit/web/src/__tests__/usePolling.test.ts`
- `serve/cockpit/web/src/__tests__/optimistic.test.ts`