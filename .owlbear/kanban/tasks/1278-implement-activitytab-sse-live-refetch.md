---
id: 1278
title: Implement ActivityTab SSE live refetch
status: in-progress
priority: someday
created: 2026-05-02T12:10:47.689197+00:00
updated: 2026-05-03T14:01:04.817843+00:00
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

- [ ] AC1: ActivityTab replaces one-shot `useState`+`useEffect` fetch with `usePollingFetch<{ sessions: Session[] }>('/api/sessions?filter=all', { intervalMs: 120_000, paused: sseStatus === 'open', onSuccess: (data) => setSessions(data.sessions) })` (td:2)
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
Architecture review complete. Refined AC from narrative description into 6 verifiable lines with test-depth annotations. Challenger reconsider (0.67) addressed: added mtime guard AC (AC3), negative-case AC (AC4), and test-mock specificity (AC6). All 10 criteria PASS. Pattern mirrors useBoard.ts exactly — usePollingFetch + useSSEEvent + mtime guard effect. Max td:2, test-writer PROCEED.
[[2026-05-03]]
## Test-Writer Notes
- Test file: serve/cockpit/web/src/__tests__/ActivityTab_1278.test.tsx
- Classes: TestFromAC_ActivityTabSSE
- Tests per category: happy 8 (AC1 url/intervalMs/paused-open/paused-closed/onSuccess, AC2 event type, AC3 new-mtime/mtime-advance), edge 3 (AC3 dedup guard, AC4 null mtime with open, AC5 mount), error 0, boundary 3 (AC4 closed/connecting guards, AC6 jsdom mock smoke)
- Total: 14 tests, all FAIL
- ruff: n/a (TypeScript); eslint: clean (exit 0)

AC coverage:
| AC | Tests |
|----|-------|
| AC1 — usePollingFetch URL, intervalMs, paused flag, onSuccess | 5 |
| AC2 — useSSEEvent('activity-changed') | 1 |
| AC3 — mtime guard triggers refetch (new mtime, dedup, advance) | 3 |
| AC4 — no refetch when closed/connecting/null-mtime | 3 |
| AC5 — initial mount fetch (usePollingFetch called on mount) | 1 |
| AC6 — EventSourceProvider mock pattern (jsdom compat) | 1 |

Mock strategy: vi.hoisted mutable sseState + pollingCapture; vi.mock on usePollingFetch and useSSEEvent so no native EventSource needed in jsdom.