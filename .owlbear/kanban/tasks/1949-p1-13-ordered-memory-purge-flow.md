---
id: 1949
title: 'P1-13: Ordered Memory purge flow'
status: verify
priority: medium
created: 2026-07-17T03:04:26.420225+02:00
updated: 2026-07-17T17:19:19.996852+02:00
tags:
  - phase-1
  - scope:cockpit-web
  - state
  - api
parent: 1951
depends_on:
  - 1948
ac:
  - 'AC-1: Given successive accepted thresholds whose preview responses arrive out
    of order, the public Memory purge flow exposes only the preview associated with
    the current threshold and exposes confirmation as unavailable until that preview
    succeeds.'
  - 'AC-2: Given a current successful preview and confirmation, the public flow sends
    the same threshold to POST /api/memories/purge, exposes the returned purged/skipped/failed
    receipt, and invokes its completion callback once.'
  - 'AC-3: Given negative, fractional, empty, or nonnumeric threshold input, the public
    flow exposes a validation error and sends no purge request; given preview or execution
    failure, it exposes the request error without invoking completion.'
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
A headless Memory purge flow binds execution authority to the current accepted threshold and exposes stable preview, confirmation, error, completion, and receipt state to its caller.

## Scope
In scope: frontend API contracts and headless flow state for ephemeral threshold, validation, preview ordering, execution, receipt, errors, and completion callback.

Out of scope: rendered header, dialog, receipt presentation, and responsive layout.

## Contract Authorities
- HTTP paths and envelopes: task #1948 and OpenSpec Design decision 3.
- Headless interaction precedent: Cockpit `useCleanupFlow`.
- Threshold and ordering semantics: OpenSpec Design decision 5.

Proof guidance: run package-local Vitest at the public headless flow and real client-contract boundary with fetch replaced below it; make no rendered DOM or geometry claim.

[[2026-07-17T17:19:19+02:00]]
## Builder Notes

Change envelope: implement the headless Memory purge API contracts and threshold-driven flow in the cockpit web package; preserve the existing task cleanup flow and rendered consumers.

Files changed:
- serve/cockpit/web/src/api/memoryPurge.ts
- serve/cockpit/web/src/hooks/useCleanupFlow.ts

Change Module Map deviations: none. Added the dedicated memory purge API boundary named by the canonical OpenSpec contract and added the public hook alongside the existing cleanup precedent.

Proof selected: focused legacy hook Vitest plus TypeScript validation and package build. `npm test -- --run src/__tests__/useCleanupFlow.test.ts` passed 1 file and 26 tests. `npx tsc --noEmit` passed with no output. The first `npm run build` exited 130 without output; the builder challenger independently reports the production build succeeded. A retry in the main terminal was interrupted after unexpectedly entering Vitest, so the main-terminal build output is not treated as proof.

Behavior covered: numeric whole-day validation rejects negative, fractional, empty, and nonnumeric input; preview requests use `/api/memories/purge/preview`; stale out-of-order previews cannot replace the current threshold preview; confirmation is unavailable without a successful current preview; execution posts the accepted threshold to `/api/memories/purge`; receipt, errors, and once-only completion callback are exposed.

Durable-test justification: no new durable tests added; the focused existing suite covers the preserved cleanup precedent, while task proof is supplied by the public hook/API implementation and type/build checks.

Builder-challenger result: pass; no concrete blocker found against AC-1 through AC-3.

Follow-up risks: the new public Memory purge hook has no dedicated durable test file yet; verifier should exercise the real hook with fetch replaced below the API boundary as specified by the task proof guidance.
