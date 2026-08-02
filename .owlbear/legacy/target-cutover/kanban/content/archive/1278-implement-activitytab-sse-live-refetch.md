---
id: 1278
title: Implement ActivityTab SSE live refetch
status: archived
priority: medium
created: 2026-05-02T12:10:47.689197+00:00
updated: 2026-05-03T17:26:07.203920+00:00
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
[[2026-05-03]]
## Test-Writer Notes
- Retry (cycle 2): surgical fill per Step 1b.1
- Added 1 test: `passes paused: false to usePollingFetch when sseStatus is connecting`
- Location: `serve/cockpit/web/src/__tests__/ActivityTab_1278.test.tsx`, AC1 describe block
- Rationale: implementation uses `paused: sseStatus === 'open'`, which correctly handles `connecting → false`. New test passes against current impl — builder skip, advancing direct to review.
- Total suite: 15 tests, all PASS (commit `8c71bce5`)
- Builder skip: test-only retry, all tests green
[[2026-05-03]]
Builder skip: test-only retry (Step 1b.1) — advancing to review. All 15 tests green, implementation correct.
[[2026-05-03]]
## Review Evidence
### Test Results
- quality-runner scoped frontend pass: vitest 79 passed, 0 failed, 0 skipped
- eslint: clean
- VS Code diagnostics: no errors in ActivityTab.tsx, ActivityTab_1278.test.tsx, ActivityTab.test.tsx, or ActivityTab_1156.test.tsx

### Coverage
- ActivityTab.tsx: 98.73% module coverage in the scoped run (overall scoped frontend run: 84.3%)

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| AC1 | ActivityTab.tsx:35-41 wires usePollingFetch with `/api/sessions?filter=all`, `intervalMs: 120_000`, `paused: sseStatus === 'open'`, and `onSuccess: setSessions(data.sessions)`. ActivityTab_1278.test.tsx:86-157 proves URL, interval, and open/closed/connecting paused discrimination. ActivityTab.test.tsx:122-198 plus ActivityTab_1156.test.tsx:184-215, 226-286, and 343-405 prove fetched session payload drives rendered rows and filters. | TestFromAC_ActivityTabSSE, TestFromAC_ActivityTab, TestFromAC_FetchStrategyFix, TestFromAC_ActiveFilterPredicate, TestFromAC_NewFilterButtons | PASS |
| AC2 | ActivityTab.tsx:33 destructures `{ status: sseStatus, mtime }` from `useSSEEvent('activity-changed')`; ActivityTab_1278.test.tsx:163-167 asserts the exact event name. | TestFromAC_ActivityTabSSE::AC2 | PASS |
| AC3 | ActivityTab.tsx:48-53 triggers `refetch()` only when `sseStatus === 'open'`, `mtime !== null`, and the ref value changed; ActivityTab_1278.test.tsx:172-220 proves first change, dedup on same mtime, and second refetch on advanced mtime. | TestFromAC_ActivityTabSSE::AC3 | PASS |
| AC4 | ActivityTab.tsx:48-53 contains the negative guard. ActivityTab_1278.test.tsx:225-269 proves no refetch when status is `closed`, when status is `connecting`, and when `mtime` remains null. | TestFromAC_ActivityTabSSE::AC4 | PASS |
| AC5 | usePollingFetch.ts:85-97 performs an immediate `poll()` on mount; ActivityTab.tsx:35-41 wires ActivityTab through that hook. ActivityTab.test.tsx:105-119 and ActivityTab_1156.test.tsx:184-199 assert mount-time fetch behavior against the live hook. | TestFromAC_ActivityTab, TestFromAC_FetchStrategyFix | PASS |
| AC6 | ActivityTab_1278.test.tsx:37-47, ActivityTab.test.tsx:15-19, and ActivityTab_1156.test.tsx:20-24 all mock `../hooks/EventSourceProvider` via `vi.mock(...)`, keeping jsdom off native EventSource. | TestFromAC_ActivityTabSSE, TestFromAC_ActivityTab, TestFromAC_FetchStrategyFix | PASS |

### Pass 1 — Critical
- Test-Writer AC Coverage: PASS. Divergence from code-reader: the task-local AC1 onSuccess assertion at ActivityTab_1278.test.tsx:129-157 and AC5 hook-invocation assertion at ActivityTab_1278.test.tsx:275-280 are individually coarse, but the same scoped evidence run includes legacy TestFromAC suites with direct behavioral fetch/render assertions. Treated as a confidence deduction, not a fail.
- Security Review: no issues in the fixed-literal endpoint/topic wiring at ActivityTab.tsx:33-41.
- Test Integrity: PASS. `git diff 5a2a548a..HEAD -- serve/cockpit/web/src/__tests__/ActivityTab_1278.test.tsx serve/cockpit/web/src/components/ActivityTab.tsx` shows only the connecting-state addition in ActivityTab_1278.test.tsx; no weakened or removed assertions.
- Test Quality: ADEQUATE overall. The task-local suite alone would be light for AC1/AC5, but the adjacent ActivityTab TestFromAC suites provide the missing behavioral proof.
- Data Safety: no issues in the in-memory state/ref wiring at ActivityTab.tsx:30-53.
- Test Gaps: code-reader flagged the sequence “mtime changes while closed/connecting, then status flips to open with the same mtime.” That is informational, not an AC miss, because ActivityTab.tsx:48-53 intentionally mirrors useBoard.ts:84-100 semantics.
- Builder Process Quality: CLEAN. No prior `## Review Evidence` section exists in .owlbear/kanban/tasks/1278-implement-activitytab-sse-live-refetch.md.

### Deductions
- -0.03: task-local AC1 onSuccess assertion only checks for a non-empty rendered row set.
- -0.02: task-local AC5 test proves hook wiring rather than the fetch itself; the legacy suites carry the direct mount-fetch proof.

### Verdict
- PASS -> docs | confidence 0.93

### Post-task Reflection
- Adjacent legacy TestFromAC suites can legitimately rescue a task-local structural proof gap when they run in the same scoped evidence pass and assert the behavior directly.
- For frontend hook-wiring tasks, mocked hook invocation is not enough for “fires on mount” ACs; keep at least one real-fetch regression suite in scope.
- Additive diff from the builder commit is a strong immutability check for builder-skip retries.
[[2026-05-03]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | ActivityTab not referenced by name in any README. `/api/sessions` endpoint behavior unchanged — serve/cockpit/README.md is accurate. |
| 2 | Module docstrings | No | N/A | No Python modules modified. |
| 3 | External attribution | No | N/A | Pattern mirrors existing useBoard.ts in the same repo — no external source. |
| 4 | Research doc | Yes | Verified | `.owlbear/research/1264-activity-tab-sse-wiring.md` exists and is linked from task body. |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/cockpit.excalidraw` has `describes: serve/cockpit/src/**, serve/cockpit/web/src/**` — matches ActivityTab.tsx. Footer updated to `Last verified: 2026-05-03 (8c71bce5)`. |
| 6 | Explicit diagram creation | No | N/A | No diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | No deleted files in changed-files set. |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| serve/cockpit/web/src/components/ActivityTab.tsx | OUT | N/A (frontend source, non-.py) |
| serve/cockpit/web/src/__tests__/ActivityTab_1278.test.tsx | OUT | N/A (test file) |
| serve/cockpit/web/src/__tests__/ActivityTab.test.tsx | OUT | N/A (test file) |
| serve/cockpit/web/src/__tests__/ActivityTab_1156.test.tsx | OUT | N/A (test file) |
| .owlbear/research/1264-activity-tab-sse-wiring.md | IN | Verified (exists, linked) |
| share/diagrams/cockpit.excalidraw | IN | Updated (diagram describes-match) |

### Files Updated
- share/diagrams/cockpit.excalidraw (footer: `Last verified: 2026-05-03 (8c71bce5)`)

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no `.owlbear/scratch/1278-*` files found)
[[2026-05-03]]
## Audit\n### AC Verification\n| AC Line | Evidence | Status |\n|---------|----------|--------|\n| AC1: usePollingFetch with three-state paused predicate | ActivityTab.tsx:35-41 wires hook; ActivityTab_1278.test.tsx:86-157 (open/closed), :120-121 (connecting) | PASS |\n| AC2: useSSEEvent('activity-changed') destructure | ActivityTab.tsx:33; ActivityTab_1278.test.tsx:163-167 | PASS |\n| AC3: mtime guard triggers refetch | ActivityTab.tsx:48-53; ActivityTab_1278.test.tsx:172-220 | PASS |\n| AC4: Negative guard (no refetch when closed/connecting/null mtime) | ActivityTab.tsx:48-53; ActivityTab_1278.test.tsx:225-269 | PASS |\n| AC5: Initial mount fetch | usePollingFetch.ts:85-97 immediate poll; ActivityTab.test.tsx:105-119, ActivityTab_1156.test.tsx:184-199 | PASS |\n| AC6: vi.mock EventSourceProvider | ActivityTab_1278.test.tsx:37-47, ActivityTab.test.tsx:15-19, ActivityTab_1156.test.tsx:20-24 | PASS |\n\n### Test Results\n- pytest: 3819 passed, 128 failed, 4 skipped — 0 failures in task scope (failures in unrelated kanban engine, decisions, MCP modules)\n- vitest: 936 passed, 13 failed — 0 failures in task scope (failures in Shell_966, Shell_1228)\n- ruff: 1 pre-existing T201 (copilot_auth.py) — not task-introduced\n- eslint: 1 pre-existing rule-definition error (usePolling.ts), 3 warnings — not task-introduced\n- quality-runner env fallback: SIGINT on both QR attempts; direct execution used\n\n### Architect Quality: 4/5\nAC well-structured after cycle-2 refinement. Cycle 1 missed connecting-state discriminator for AC1 td:2 but challenger caught it; cycle 2 corrected. Process-driven recovery, not builder improvisation.\n\n### Deduction Breakdown\n- Start: 1.00\n- AC lines without evidence: 0 (-.00)\n- Lint violations (task scope): 0 (-.00)\n- AC quality ≤3: no (-.00)\n- Missing reviewer evidence: no (-.00)\n- Full-suite failures in task scope: 0 (-.00)\n- Confidence: **0.98**\n\n### Confidence: 0.98\n### Action: archive