---
id: 1949
title: 'P1-13: Ordered Memory purge flow'
status: verify
priority: medium
created: 2026-07-17T03:04:26.420225+02:00
updated: 2026-07-17T20:15:51.035858+02:00
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

[[2026-07-17T17:21:47+02:00]]
## Verify Notes

Verdict: REJECT.

Evidence reviewed:
- Contract authorities checked: OpenSpec `purge-deleted-memories` Design decisions 3 and 5; dependency #1948's archived assembled FastAPI verification; and the `useCleanupFlow` headless-interaction precedent.
- Decision 5 requires mount-local input initialized to 30, current-value preview gating, exact previewed threshold execution, and invalid-input feedback without mutation.
- Change Module Map checked: implementation remains within the mapped web API boundary (`serve/cockpit/web/src/api/memoryPurge.ts`) and headless flow owner (`serve/cockpit/web/src/hooks/useCleanupFlow.ts`); no module-map deviation.

Normal-path boundary exercised:
- Temporary public-hook probe using `renderHook(() => useMemoryPurgeFlow())` verified the required initial threshold after the local patch, then was removed rather than retained as a verification-only durable test.
- Existing `useCleanupFlow` suite remains regression evidence for the preserved precedent; it is not accepted as evidence for the new Memory purge public-flow contract.

Checks run:
- `npm test -- --run src/__tests__/memoryPurgeFlow.verify.test.ts` passed: 1 file, 1 test (temporary probe; removed afterward).
- `npm test -- --run src/__tests__/useCleanupFlow.test.ts` passed: 1 file, 26 tests.
- `npm run build` passed (`tsc -b` and Vite production build); only the existing chunk-size warning was emitted.
- `git diff --check` passed.

Patch applied:
- `serve/cockpit/web/src/hooks/useCleanupFlow.ts`: initialized `useMemoryPurgeFlow` threshold to `'30'`, the explicit Design decision 5 default.

Findings:
1. AC-1 is not satisfied: after a successful preview, `setThreshold()` accepts a new value without clearing `preview` or invalidating the accepted threshold. `confirmPurge()` can therefore execute the old accepted threshold while the current threshold differs, leaving confirmation available for a stale preview.
2. AC-2 is not satisfied: `confirmPurge()` has no in-flight or completion guard. Repeated calls before state propagation can invoke `purgeMemories()` and `onSuccess` more than once.
3. The shaped public-flow proof is absent. The existing test exercises only `useCleanupFlow`; the Memory purge hook needs a focused Vitest public-hook test with the API/fetch replaced below that boundary.

Patches applied beyond the default correction: none. The remaining issues require coordinated behavior and durable proof, exceeding verifier patch-pass scope.

Verifier-challenger result: not requested because this is a REJECT, not a PASS.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Invalidate the accepted preview and confirmation availability whenever the threshold changes; ensure only a successful preview for the current value can execute. | `serve/cockpit/web/src/hooks/useCleanupFlow.ts` | AC-1 finding above; Design decision 5. |
| 2 | builder | Guard purge execution and completion so a single confirmation results in exactly one request and one completion callback. | `serve/cockpit/web/src/hooks/useCleanupFlow.ts` | AC-2 finding above. |
| 3 | builder | Add focused public-hook Vitest coverage using the real Memory-purge API boundary with fetch replaced below it: out-of-order previews, current-threshold gating, exact execution threshold and receipt, callback once, invalid input/no request, and preview/execution errors/no callback. | `serve/cockpit/web/src/__tests__/useMemoryPurgeFlow.test.ts` | Task proof guidance and AC-1 through AC-3. |

Final route: REJECT -> build.

[[2026-07-17T17:32:10+02:00]]
## Builder Notes

Change envelope: repair the headless Memory purge flow in the mapped web hook and add the shaped public-flow regression proof; preserve the existing cleanup flow and API boundary.

Files changed:
- serve/cockpit/web/src/hooks/useCleanupFlow.ts
- serve/cockpit/web/src/__tests__/useMemoryPurgeFlow.test.ts

Change Module Map deviations: none. Threshold setter now invalidates accepted preview/receipt state and stale preview requests; purge execution uses a ref lock to prevent duplicate requests and completion callbacks.

Proof selected: focused existing cleanup-hook suite plus focused public Memory purge hook tests at the real hook/API boundary with fetch replaced below the API client. Existing suite passed 1 file and 26 tests. Builder challenger independently verified the new suite passed 3 tests and TypeScript completed successfully. The package test and direct Vitest commands in the main terminal exited 130 before output; root npm run build emitted unrelated backend health-check output and did not provide frontend build evidence. No frontend build claim is made.

Behavior covered: threshold changes invalidate confirmation; out-of-order previews cannot replace the current threshold preview; exact current threshold is posted for execution; repeated confirmation submits once and invokes onSuccess once; invalid thresholds produce validation errors with no request; preview failure exposes error without completion.

Durable-test justification: the new test protects a concrete observed verifier regression in a shared public hook contract and exercises state ordering, duplicate submission, validation, and failure boundaries.

Builder-challenger result: pass. It independently reported the focused suite 3/3 and direct TypeScript check TSC_OK, with no concrete blocker.

Follow-up risks: production frontend build evidence was unavailable in the main terminal because the invoked build path was interrupted or routed through unrelated repository checks; verifier should rerun package-local build if needed.
