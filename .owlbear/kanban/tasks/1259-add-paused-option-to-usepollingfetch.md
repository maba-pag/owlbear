---
id: 1259
title: Add paused option to usePollingFetch
status: in-progress
priority: nice-to-have
created: 2026-05-01T09:34:21.381409+00:00
updated: 2026-05-01T16:00:02.380724+00:00
tags:
- cockpit
- frontend
parent:
depends_on:
- 1235
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Add a `paused?: boolean` option to usePollingFetch. When true, skip interval ticks but keep refetch() callable. Default false for backward compatibility. See .owlbear/research/1235-eventsource-client-implementation.md §3.5
[[2026-05-01]]
## Research
- Research doc: .owlbear/research/1259-paused-option-usepollingfetch.md
- Sources: 5 studied, 3 high-relevance (Dan Abramov useInterval, TanStack Query enabled, existing codebase)
- Recommendation: Approach A — ref-based tick check (~5 LOC). Timer stays stable on pause/unpause, no unwanted immediate poll on resume, refetch() always callable. (confidence: 0.90)
- Follow-up tasks created: none needed — this task IS the implementation unit; downstream #1261 already depends on it
- Decision requests: none (T1 — backward-compatible option addition)

## Challenge Results
- Challenger: SKIP — trivial single-option-dominates change with clear prior art
- Key insight: Conditional interval (Dan Abramov pattern) actively harms the SSE use case because timer resets on resume cause unwanted immediate polls
[[2026-05-01]]

## Acceptance Criteria

- [ ] AC1: `UsePollingFetchOptions` adds `paused?: boolean` (default `false`) — `UsePollingFetchResult` unchanged (td:1)
- [ ] AC2: When `paused` is `true`, interval callback skips `poll()` (td:2)
- [ ] AC3: When `paused` is `true`, queued-repoll drain (`pendingPollRef` finalizer in `poll()`) also skips `poll()` (td:2)
- [ ] AC4: When `paused` is `true`, `refetch()` still triggers `poll()` (td:2)
- [ ] AC5: Initial mount `poll()` fires regardless of `paused` value (td:1)
- [ ] AC6: Toggling `paused` `true→false` resumes on next natural interval tick — no timer teardown/setup, no immediate burst (td:2)
- [ ] AC7: All existing `usePollingFetch_1227.test.ts` tests pass without modification (td:0)

## Architecture Review

**Verdict:** APPROVE

### AC Assessment

| AC | Assessment | Action |
|----|-----------|--------|
| AC1 | Clear interface addition, backward-compatible default | None |
| AC2 | Core pause behavior — ref-based guard in setInterval callback | None |
| AC3 | Challenger-identified gap: pendingPollRef finalizer must also honor pause | Added (was missing from research sketch) |
| AC4 | Explicit refetch-while-paused contract for SSE consumer (#1261) | None |
| AC5 | Mount fetch is initialization, not polling — fires unconditionally | None |
| AC6 | Timer stability: no effect dep change, no teardown/setup on toggle | None |
| AC7 | Regression gate — default false means no behavior change for existing consumers | None |

### Architecture Notes

- **Approach:** Ref-based tick check (Approach A from research). Add `pausedRef` synced to `options?.paused ?? false` on every render. Guard in `setInterval` callback AND in `pendingPollRef` finalizer. No effect dep change. ~6 LOC delta.
- **Consumers:** `useBoard.ts`, `usePendingDRs.ts`, `useScanPolling.ts` — none pass `paused` today; default `false` preserves behavior.
- **Pattern consistency:** Follows existing ref-heavy pattern (isMountedRef, inFlightRef, pendingPollRef, controllerRef). No new abstractions.
- **Local precedent:** `usePolling.ts` has a skip gate but uses different timer semantics (conditional interval). Approach A is preferred here because SSE fallback needs stable timer on resume.

### Dependency Analysis

- **#1235** (dependency): archived/done — satisfied.
- **#1261** (downstream consumer): in research, depends on this + #1260. Contract: `paused` option lets useBoard suppress interval polls during active SSE.

### Challenger Results

- Confidence: 0.58 → reconsider.
- Valid finding: queued-repoll path not covered by initial sketch. **Resolved:** added AC3 to explicitly require pause guard in pendingPollRef finalizer.
- Other findings (local precedent, proof plan): informational — addressed in architecture notes. Test-writer derives tests from AC lines.
- Post-resolution confidence: sufficient for approval.

[[2026-05-01]]
APPROVED #1259 → todo. Refined AC from prose into 7 verifiable lines with test-depth annotations. Challenger surfaced queued-repoll gap (pendingPollRef finalizer must also honor pause) — added as AC3. Approach A (ref-based tick check, ~6 LOC) approved.
[[2026-05-01]]
## Test-Writer Notes
- Test file: serve/cockpit/web/src/__tests__/usePollingFetch_1259.test.ts
- Classes: TestFromAC_PausedOption
- Tests per category: happy 5, edge 5, boundary 3
- Total: 13 tests, all FAIL (AssertionError — paused option not yet implemented)
- ruff: N/A (TypeScript); eslint: clean

### AC Coverage

| AC | Tests | Category |
|----|-------|----------|
| AC1 (td:1) | 1 | smoke (behavioral effect proof) |
| AC2 (td:2) | 3 | happy, edge, boundary |
| AC3 (td:2) | 2 | happy (via refetch), edge (via interval) |
| AC4 (td:2) | 3 | happy (combined w/ AC2), edge, boundary |
| AC5 (td:1) | 1 | smoke (combined w/ interval-skip to force fail) |
| AC6 (td:2) | 3 | happy, edge, boundary |
| AC7 (td:0) | 0 | skipped per skill |

### Notes for Builder
- AC3 tests: pause guard must be added to the `pendingPollRef` finalizer inside `poll()`, not just to the interval callback.
- AC4 boundary: `refetch()` while in-flight + paused → pendingPollRef queued → drain suppressed by pause (intersection with AC3).
- Approach A (ref-based): add `pausedRef = useRef(options?.paused ?? false)`, update on every render, guard in setInterval callback AND in pendingPollRef finalizer. No effect dep change — timer stays stable.