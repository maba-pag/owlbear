---
id: 1278
title: Implement ActivityTab SSE live refetch
status: todo
priority: someday
created: 2026-05-02T12:10:47.689197+00:00
updated: 2026-05-03T16:33:07.276264+00:00
tags:
- cockpit
- frontend
parent: 1236
depends_on:
- 1276
- 1277
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Refactor ActivityTab from one-shot useEffect fetch to usePollingFetch (paused when SSE open, fallback interval 120s). Listen for activity-changed via useSSEEvent('activity-changed') and trigger refetch() on mtime change. Keep initial mount fetch behavior. See .owlbear/research/1264-activity-tab-sse-wiring.md
[[2026-05-03]]
## Research

Validation pass — existing research doc `.owlbear/research/1264-activity-tab-sse-wiring.md` fully covers analysis. Confirmed codebase state matches recommendations:

- **Dependencies met:** EventSourceProvider exists (`hooks/EventSourceProvider.tsx`), useBoard refactored to `useSSEEvent('tasks-changed')`, provider wrapped in `App.tsx`.
- **Implementation approach confirmed:** Mirror `useBoard` pattern — replace one-shot `useState`+`useEffect` with `usePollingFetch('/api/sessions?filter=all', { intervalMs: 120_000, paused: sseStatus === 'open', onSuccess: setSessions })` + `useSSEEvent('activity-changed')` trigger calling `refetch()` on mtime change.
- **Testing note:** Existing `ActivityTab.test.tsx` and `ActivityTab_1156.test.tsx` stub global `fetch` without `EventSourceProvider` context — after refactor, tests need provider wrapper or `useSSEEvent` mock.
- **Recommendation:** Direct implementation, ~20 LOC delta in ActivityTab. Confidence: 0.90.
- **Classification:** T1 — autonomous (applies established pattern, no new decisions).
- **Follow-up tasks:** None needed — task 1278 IS the implementation task.
- **Decision requests:** None.

## Challenge Results
- Challenger: SKIP — validation pass of complete existing research; no competing alternatives.
[[2026-05-03]]

## Acceptance Criteria

- [ ] AC1: ActivityTab wires `usePollingFetch<{ sessions: Session[] }>('/api/sessions?filter=all', { intervalMs: 120_000, paused: sseStatus === 'open', onSuccess: (data) => setSessions(data.sessions) })`; tests MUST prove three-state predicate discrimination: `open → paused: true`, `closed → paused: false`, `connecting → paused: false` (td:2)
- [ ] AC2: ActivityTab calls `useSSEEvent('activity-changed')` and destructures `{ status: sseStatus, mtime }` (td:1)
- [ ] AC3: A `useEffect` triggers `refetch()` when `mtime` changes AND `sseStatus === 'open'`, using a `lastObservedMtimeRef` guard to deduplicate — mirrors `useBoard.ts` lines 84-100 (td:2)
- [ ] AC4: When `sseStatus !== 'open'` or mtime is null, no SSE-triggered refetch fires (negative guard) (td:2)
- [ ] AC5: Initial mount fetch fires immediately, preserving current behavior (td:1)
- [ ] AC6: Existing ActivityTab test suites mock `useSSEEvent` via `vi.mock('../hooks/EventSourceProvider')` — jsdom lacks native EventSource (td:1)

## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: make ActivityTab SSE-aware via established pattern |
| Interface clarity | PASS | AC specifies hook calls, options, guard behavior, and negative case |
| Dependency correctness | PASS | Deps 1276/1277 archived (done); usePollingFetch, useSSEEvent, EventSourceProvider exist |
| Module layering | PASS | ActivityTab imports hooks from `../hooks/` — no upward imports |
| TDD compliance | PASS | Test-writer will process; 4 lines at td:2, 2 at td:1 |
| KISS/YAGNI | PASS | Mirrors useBoard pattern exactly; ~20 LOC production delta |
| Premise challenge | PASS | ActivityTab is currently one-shot; live updates don't exist yet |
| Pattern consistency | PASS | Identical to useBoard.ts: usePollingFetch + useSSEEvent + mtime guard effect |
| Security surface | PASS | No new system boundaries; same /api/sessions endpoint, same fetch |
| Single domain | PASS | Frontend/cockpit only |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| SSE disconnect | sseStatus !== 'open' | N/A | Yes — usePollingFetch resumes at 120s interval | Data refreshes slower, not stale |
| /api/sessions fetch error | Network or server error | onError callback | Yes — usePollingFetch retries on next interval | Temporary stale data, auto-recovers |
| mtime null on SSE reconnect | First event after reconnect has mtime | N/A | Yes — guard checks mtime !== null | No spurious refetch |

### Design Diverge
- Trigger: skipped — single established approach (mirror useBoard pattern), no competing alternatives

### Challenge Results
- Challenger: reconsider (0.67)
- Concerns: mtime guard under-specification, negative-case gap, test-path specificity
- Architect response: accepted — added AC3 mtime guard, AC4 negative case, AC6 mock specificity; all challenger gaps addressed in refined AC

### Test Depth
- Max depth: 2
- Test-writer: PROCEED

### Verdict: APPROVE
### Action Taken: Refined AC from description into 6 verifiable lines addressing challenger gaps; advanced to todo
[[2026-05-03]]

[[2026-05-03]]
## Test-Writer Notes (historical)
- Test file: serve/cockpit/web/src/__tests__/ActivityTab_1278.test.tsx
- Total: 14 tests, all PASS after builder implementation (commit `5a2a548a`)
- Legacy suites updated: ActivityTab.test.tsx (15 pass), ActivityTab_1156.test.tsx (49 pass)
- Coverage on ActivityTab.tsx: 98.73% statements, 100% branches, 93.75% functions, 100% lines

## Architecture Review (cycle 2)

### Context
Reviewer loop-breaker routed task back to backlog. Implementation commit `5a2a548a` is correct and stays intact. The blocker is proof quality: AC1 (td:2) requires the exact predicate `paused: sseStatus === 'open'` but the task suite only tests `open` and `closed`, leaving `connecting` untested. A mutation to `paused: sseStatus !== 'closed'` would pass all existing tests while violating AC1.

### AC Refinement
AC1 rewritten to explicitly require three-state proof:
- `open → paused: true`
- `closed → paused: false`
- `connecting → paused: false`

This matches the repo precedent in `useBoard_1277.test.ts` which already covers the same predicate discrimination for the identical hook.

### Evaluation (delta only — full evaluation passed in cycle 1)
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| TDD compliance | PASS | Adding `connecting` discriminator completes td:2 proof quality |
| Pattern consistency | PASS | Mirrors useBoard_1277 three-state coverage pattern |

### Challenge Results
- Challenger: SKIP — surgical proof-quality fix on established precedent; no design alternatives

### Test Depth
- Max depth: 2
- Test-writer: PROCEED (add connecting discriminator to AC1 test case in ActivityTab_1278.test.tsx)

### Verdict: APPROVE
### Action Taken: Refined AC1 to require explicit three-state (open/closed/connecting) paused-predicate proof; advanced to todo for test-writer to add connecting discriminator test case

[[2026-05-03]]
Architecture review cycle 2 complete. Refined AC1 to explicitly require three-state paused-predicate proof (open/closed/connecting), matching useBoard_1277 repo precedent. Implementation commit `5a2a548a` is intact — next cycle is test-writer only (add connecting discriminator).