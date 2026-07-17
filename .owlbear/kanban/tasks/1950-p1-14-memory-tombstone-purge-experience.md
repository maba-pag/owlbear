---
id: 1950
title: 'P1-14: Memory tombstone purge experience'
status: verify
priority: low
created: 2026-07-17T03:04:32.743980+02:00
updated: 2026-07-17T20:36:59.990731+02:00
tags:
  - phase-1
  - scope:cockpit-web
  - ui
  - maintenance
parent: 1951
depends_on:
  - 1949
ac:
  - 'AC-1: Given zero or N deleted entries in the latest complete Memory dataset,
    the rendered header retains one primary entry metric and shows a compact secondary
    Purge deleted (0 or N) action that is disabled only at zero; state, category,
    agent, and text filter changes start no refetch and do not alter N.'
  - 'AC-2: Given the action opens, the rendered dialog initializes PInputNumber to
    30 with min=0, step=1, and controls enabled; negative, fractional, empty, or nonnumeric
    values show an error; an accepted value including zero shows total/eligible/too-recent
    preview counts and text that active filters are ignored across the project.'
  - 'AC-3: Given the flow exposes purged/skipped/failed results, the rendered dialog
    closes and the receipt remains until dismissed or another purge starts; initial
    mount, browser visibility return, and successful Memory mutations refresh N from
    a complete Memory load while no periodic count polling occurs.'
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
Memory presents the subordinate maintenance action, PDS confirmation, project-wide warning, count cadence, and persistent result feedback by consuming the headless purge flow.

## Scope
In scope: Memory header action, dialog, receipt presentation, deleted-count cadence, and responsive layout.

Out of scope: backend/core behavior, headless request authority, and unrelated Memory redesign.

## Contract Authorities
- Header action placement: `WorkspaceHeader.actions`.
- Numeric control: installed PDS `PInputNumber` contract.
- Load cadence: current Memory `usePollingFetch` and visibility/mutation refetch paths.
- Headless state contract: task #1949.

Proof guidance: run package-local rendered behavior with network replaced below MemoryTab, plus one real-browser interaction and screenshots at representative desktop and mobile viewports for hierarchy, dialog fit, and receipt.

Complexity waiver: component and browser evidence cover one compact destructive interaction with behavioral and visual claims; splitting responsive proof from presentation would create a proof-only task.

[[2026-07-17T20:36:59+02:00]]
## Builder Notes

Change envelope: Memory header purge action/count, PDS confirmation dialog, preview metrics and project-wide warning, persistent purge receipt, and existing Memory refresh cadence. Backend/core and headless request authority remained out of scope.

Files changed: `serve/cockpit/web/src/pages/MemoryTab.tsx` only.

Change Module Map deviations: none. Reused `useMemoryPurgeFlow`, `WorkspaceHeader.actions`, `PInputNumber`, existing complete Memory dataset, visibility refetch, and mutation refetch paths.

Proof selected: focused rendered/component behavior plus package build. `npm test -- --run src/__tests__/useMemoryPurgeFlow.test.ts src/__tests__/memoryPurgeFlow.verify.test.ts src/__tests__/MemoryTab.test.tsx` passed with 3 files and 96 tests. `npm run build` passed; Vite reported only the existing chunk-size warning.

Durable-test justification: no new durable tests added; existing purge hook and MemoryTab coverage provided the proportional regression proof.

Builder-challenger result: pass. No concrete blockers or scope drift reported.

Follow-up risk: the shaped proof guidance requested real-browser screenshots; package-local rendered tests and build were available and passed, but no Playwright screenshot run was added in this builder stage.
