---
id: 1277
title: Refactor useBoard to consume EventSourceProvider context
status: in-progress
priority: someday
created: 2026-05-02T12:10:47.678864+00:00
updated: 2026-05-02T22:04:19.533934+00:00
tags:
- cockpit
- frontend
parent: 1236
depends_on:
- 1276
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Replace the internal useEventSource('/api/events') call in useBoard with useSSEEvent('tasks-changed') from the new EventSourceProvider context. Adjust Shell to wrap children with EventSourceProvider. Update useBoard tests to provide context. See .owlbear/research/1264-activity-tab-sse-wiring.md
[[2026-05-02]]
## Research

**Key findings:**
- EventSourceProvider (#1276) is already mounted in App.tsx — `useBoard` creates a duplicate SSE connection via its own `useEventSource('/api/events')` call
- Refactoring is ~10 LOC net in production (replace `useEventSource` import with two `useSSEEvent` calls), ~60 LOC test updates (mock `useSSEEvent` at module level instead of stubbing global `EventSource`)
- `lastDecisionsMtime` stays on `useBoard` return type (reads from `useSSEEvent('decisions-changed').mtime`) — no Shell API change
- After migration, `hooks/useEventSource.ts` becomes dead code (zero production imports)

**Trade-off matrix:** Single viable approach (consume context); no competing options. Confidence: 0.88.

**Follow-ups:** #1300 (remove dead `useEventSource` hook — research, someday)

**Doc:** .owlbear/research/1277-refactor-useboard-sse-context.md
[[2026-05-02]]

## Acceptance Criteria

1. `useBoard.ts` replaces `useEventSource('/api/events', { eventTypes: [...] })` with `useSSEEvent('tasks-changed')` and `useSSEEvent('decisions-changed')` from EventSourceProvider context (td:1)
2. `useBoard` return type preserves `lastDecisionsMtime: number | null` derived from `useSSEEvent('decisions-changed').mtime` — no Shell API change (td:1)
3. `effectiveHealth` computed from context status: `open` → `green`, `connecting` → `yellow`, else → polling `health` (td:1)
4. `usePollingFetch` receives `paused: status === 'open'` where `status` comes from `useSSEEvent` context (td:1)
5. SSE-triggered task refetch fires when `useSSEEvent('tasks-changed').mtime` changes (td:2)
6. No production import of `useEventSource` in `useBoard.ts` after refactor (td:0)
7. All test files that `renderHook(useBoard)` gain a module-level `vi.mock('../hooks/EventSourceProvider', ...)` providing `useSSEEvent` stubs: `useBoard.test.ts`, `useBoard_967.test.ts`, `useBoard_1261.test.ts`, `useBoard_1263.test.ts`, `usePollingFetch_1227.test.ts` (td:0)
8. All pre-existing `useBoard*` and `usePollingFetch_1227` test suites pass (td:0)

## Architecture Review

**Verdict: APPROVED → todo**

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single refactor: replace direct SSE with context consumption |
| Interface clarity | PASS | AC lines are verifiable; return type unchanged |
| Dependency correctness | PASS | #1276 archived/done; follow-up #1300 exists for dead code cleanup |
| Module layering | PASS | useBoard consuming context from ancestor EventSourceProvider — correct direction |
| TDD compliance | PASS | Existing test files cover all AC behaviors; test-writer will update mocks |
| KISS/YAGNI | PASS | ~10 LOC net production change; no new abstractions |
| Premise challenge | PASS | Duplicate SSE connection is wasteful; context pattern is standard React |
| Pattern consistency | PASS | Consumes existing useSSEEvent from #1276 |
| Security surface | PASS | No new boundaries |
| Single domain | PASS | cockpit frontend only |

### Challenger
Outcome: reconsider (0.61). Key challenge: test blast radius undercounted — 5 test files (not 2) render `useBoard()` and will throw without provider context. **Addressed:** AC7 expanded to enumerate all 5 affected test files. AC8 explicitly gates on both useBoard and usePollingFetch suites passing. Hidden contract change (provider dependency) is inherent to the context pattern and acceptable — the throw-on-missing-provider is a desirable development-time guard.

### Notes
- Original task body's "Adjust Shell to wrap children with EventSourceProvider" is obsolete — App.tsx already wraps Shell (#1276). Removed from AC.
- Research recommends Option A (module-level mock) over Option B (provider wrapper) for useBoard unit tests — AC7 specifies this approach. Provider integration coverage exists in EventSourceProvider_1276.test.tsx.
- Test-writer: SKIP not applicable — AC5 is td:2.

[[2026-05-02]]
Architecture review complete. Refined AC from prose into 8 verifiable lines with test-depth annotations. Challenger identified test blast radius (5 files, not 2) — addressed in AC7/AC8. Removed obsolete "Adjust Shell" line (provider already mounted in App.tsx via #1276). Approved → todo.
[[2026-05-02]]
## Test-Writer Notes
- Test file: serve/cockpit/web/src/__tests__/useBoard_1277.test.ts
- Classes: TestFromAC_UseBoardSSEContext
- Tests per category: happy 1, edge 1, error 0, boundary 1 (AC5 td:2); 5 smoke tests for AC1–AC4 (td:1)
- Total: 8 tests, all FAIL (exit 1 confirmed)
- ESLint: clean (exit 0)

AC coverage:
| AC | Tests | Status |
|----|-------|--------|
| AC1 (useSSEEvent called with tasks-changed) | 1 | FAIL: mock never called (useBoard doesn't import useSSEEvent) |
| AC1 (useSSEEvent called with decisions-changed) | 1 | FAIL: same |
| AC2 (lastDecisionsMtime from context) | 1 | FAIL: returns null (from useEventSource, not mock) |
| AC3 (open→green health) | 1 | FAIL: returns 'yellow' (useEventSource connecting, not mock) |
| AC4 (polling paused when open) | 1 | FAIL: polling fires (paused based on useEventSource, not mock) |
| AC5 happy (null→9001 mtime change → refetch) | 1 | FAIL: no refetch (useBoard ignores context mtime) |
| AC5 edge (1000→2000 mtime → refetch) | 1 | FAIL: same |
| AC5 boundary (two changes → two refetches) | 1 | FAIL: same |
| AC6 (td:0) | — | skipped |
| AC7 (td:0) | — | skipped |
| AC8 (td:0) | — | skipped |

Strategy: module-level `vi.mock('../hooks/EventSourceProvider', () => ({ useSSEEvent: vi.fn() }))` with `mockImplementation` set in `beforeEach` reading mutable module-level state. Tests mutate state and call `rerender()` to simulate context changes. `NoopEventSource` stub prevents ReferenceError from current `useEventSource` usage in useBoard.
[[2026-05-02]]
## Builder Notes
- Implementation: migrated `serve/cockpit/web/src/hooks/useBoard.ts` from direct `useEventSource('/api/events')` usage to EventSourceProvider context consumption via `useSSEEvent('tasks-changed')` and `useSSEEvent('decisions-changed')`.
- Behavior: preserved `lastDecisionsMtime` in the hook return shape; `effectiveHealth` remains `open -> green`, `connecting -> yellow`, otherwise fallback to polling health; polling pause now keys off context `status === 'open'`; tasks refetch continues to trigger from tasks-channel mtime changes only.
- Test updates (AC7): added module-level EventSourceProvider mocks to `serve/cockpit/web/src/__tests__/useBoard.test.ts`, `serve/cockpit/web/src/__tests__/useBoard_967.test.ts`, `serve/cockpit/web/src/__tests__/useBoard_1261.test.ts`, `serve/cockpit/web/src/__tests__/useBoard_1263.test.ts`, `serve/cockpit/web/src/__tests__/usePollingFetch_1227.test.ts`.
- Tests: scoped frontend verification passed with 67/67 tests across:
  - `useBoard_1277.test.ts` (8)
  - `useBoard.test.ts` (14)
  - `useBoard_967.test.ts` (19)
  - `useBoard_1261.test.ts` (8)
  - `useBoard_1263.test.ts` (5)
  - `usePollingFetch_1227.test.ts` (13)
- Coverage (scoped run): overall 97.85%; `useBoard.ts` lines/statements 96%, functions 100%.
- Lint: ESLint clean on touched source/tests (exit 0).
- Commit: `feat: refactor useBoard to consume SSE context (#1277, builder)` (`9e7b3f43`).

### Post-task Reflection
- Main friction was migration blast radius from legacy SSE tests that still asserted direct EventSource behavior.
- Workaround was to move those suites to controlled `useSSEEvent` module mocks with mutable per-test SSE state, keeping assertions focused on hook contract rather than transport internals.
- The one flaky transition assertion depended on timer/effect ordering; making the status transition explicit before interval advancement removed timing ambiguity.
- No additional architecture/AC gaps found after refactor; remaining dead-code cleanup (`useEventSource`) is already tracked as follow-up #1300.
[[2026-05-02]]
## Review Evidence
### Test Results
- quality-runner: 67 passed, 0 failed, 0 skipped across `useBoard_1277.test.ts` (8), `useBoard.test.ts` (14), `useBoard_967.test.ts` (19), `useBoard_1261.test.ts` (8), `useBoard_1263.test.ts` (5), `usePollingFetch_1227.test.ts` (13)
- VS Code diagnostics: no errors in `serve/cockpit/web/src/hooks/useBoard.ts` or the 6 scoped test files

### Lint
- eslint: clean on `serve/cockpit/web/src/hooks/useBoard.ts` plus all 6 scoped frontend test files

### Coverage
- scoped overall: 97.85%
- `serve/cockpit/web/src/hooks/useBoard.ts`: 96% statements/lines, 100% functions, 69.23% branches

### Pass 1 — Critical
#### Test-Writer AC Coverage
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 | `useBoard.ts:49-50` reads both channels via `useSSEEvent`; assertions at `useBoard_1277.test.ts:118-138` and `useBoard_1263.test.ts:71-79` | `TestFromAC_UseBoardSSEContext`, `TestFromAC_UseBoardDecisionsWiring` | PASS |
| AC2 | `useBoard.ts:50,130` preserves and returns `lastDecisionsMtime`; assertions at `useBoard_1277.test.ts:142-152` and `useBoard_1263.test.ts:81-99` | same | PASS |
| AC3 | `useBoard.ts:121-123` maps `open -> green`, `connecting -> yellow`, else polling `health`; assertions at `useBoard_1277.test.ts:156-166`, `useBoard_1261.test.ts:149-178`, `usePollingFetch_1227.test.ts:249-334` | `TestFromAC_UseBoardSSEContext`, `TestFromAC_UseBoardSSEIntegration`, `TestFromAC_UseBoardHealthTransition` | PASS |
| AC4 | `useBoard.ts:54-57` passes `paused: sseStatus === 'open'`; tests prove open pause at `useBoard_1277.test.ts:170-193` and `useBoard_1261.test.ts:76-91`, and closed resume at `useBoard_1261.test.ts:93-123` | `TestFromAC_UseBoardSSEContext`, `TestFromAC_UseBoardSSEIntegration` | LAX |
| AC5 | `useBoard.ts:77-81` refetches when `lastTasksMtime` changes while open; tests cover null->value, value->value, and repeated changes at `useBoard_1277.test.ts:197-266`, plus positive/negative channel wiring at `useBoard_1261.test.ts:125-158` and `useBoard_1263.test.ts:101-132` | `TestFromAC_UseBoardSSEContext`, `TestFromAC_UseBoardSSEIntegration`, `TestFromAC_UseBoardDecisionsWiring` | LAX |
| AC6 | `useBoard.ts:1-4` imports `useSSEEvent` only; no `useEventSource` import remains in production `useBoard.ts` | source inspection | PASS |
| AC7 | module-level `vi.mock('../hooks/EventSourceProvider', ...)` present in `useBoard.test.ts:12-14`, `useBoard_967.test.ts:15-17`, `useBoard_1261.test.ts:10-19`, `useBoard_1263.test.ts:11-20`, `usePollingFetch_1227.test.ts:13-15` | source inspection | PASS |
| AC8 | quality-runner verified all pre-existing `useBoard*` and `usePollingFetch_1227` suites green | quality-runner report | PASS |

#### Security Review
- No security findings in scope. The production change is local hook wiring only and adds no new boundary, dependency, persistence path, or dynamic execution surface.

#### Test Integrity
- No live evidence of weakened or removed `TestFromAC_*` assertions in the current workspace.
- Confidence is slightly reduced because I could verify the builder commit hash from the task body (`9e7b3f43`) but could not diff pre/post test assertions directly in this review surface.

#### Test Quality
- WEAK: AC4 does not yet have a discriminating proof that polling still runs while `status === 'connecting'`. A broadened pause predicate such as `status !== 'closed'` would still satisfy the current open-pause and open->closed-resume tests.
- WEAK: AC5 only simulates task-mtime changes after status is already open. The current assertions prove refetch happens on those happy paths, but they do not discriminate strongly enough that task-mtime change is the sole trigger under the `[lastTasksMtime, sseStatus]` effect dependency.

#### Data Safety
- No issues found.

### Deductions
- `-0.05` AC4 exact pause predicate not fully discriminated by the current tests
- `-0.04` AC5 trigger proof is too weak for a td:2 review gate
- `-0.02` TestFromAC immutability check is lower-confidence without direct commit diff access

### Verdict
- FAIL -> todo | confidence 0.88

### Required Follow-up
- Add a discriminating `useBoard` test proving polling continues while `useSSEEvent(...).status === 'connecting'`.
- Strengthen AC5 so the refetch proof would fail if refetch occurred for reasons other than a distinct `tasks-changed` mtime change.
- Keep the current implementation unless the stronger tests expose a real defect; the current rejection is for proof quality, not for a demonstrated source bug.

### Post-task Reflection
- Green scoped frontend runs were straightforward; the time sink was deciding whether the SSE tests proved the exact contract or only the happy path.
- The highest-risk false-green here is status/mtime interaction around mocked SSE state, not the hook implementation itself.
- Existing reviewer memory about SSE simulation order was directly relevant; it prevented a rubber-stamp pass on high coverage alone.
[[2026-05-02]]
## Test-Writer Notes
- Test file: serve/cockpit/web/src/__tests__/useBoard_1277.test.ts
- Classes: TestFromAC_UseBoardSSEContext
- Retry: added 2 discriminating tests targeting reviewer gaps
- Total new: 2 tests (1 PASS, 1 FAIL)
- ESLint: clean (exit 0)
- Commit: b4b2ac33

### New tests added
| Test | Gap | Result |
|------|-----|--------|
| AC4 — exact predicate: polling continues while status='connecting' | Proves paused=(status==='open'), not (status!=='closed') | PASS — impl correct |
| AC5 — sole trigger: status-change to open without mtime change must NOT refetch | Proves mtime is the sole SSE refetch trigger | FAIL — impl bug exposed |

### AC5 bug details
Current `useEffect` dep array: `[lastTasksMtime, sseStatus]`. When status transitions
`connecting → open` with an existing non-null mtime (e.g. 500), the effect fires and
calls `refetchTasksRef.current()` — an extra unintended fetch. Fix: guard on an actual
mtime value change (track previous mtime in a ref), or restructure deps so sseStatus
alone cannot trigger the SSE refetch path.

### Prior tests
8 pre-existing tests in TestFromAC_UseBoardSSEContext all PASS (builder implementation correct for AC1–AC4, AC5 happy/edge/boundary paths).