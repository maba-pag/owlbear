---
id: 1277
title: Refactor useBoard to consume EventSourceProvider context
status: archived
priority: medium
created: 2026-05-02T12:10:47.678864+00:00
updated: 2026-05-03T13:19:57.982007+00:00
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

## Acceptance Criteria (addendum — auditor regression fix)

9. Test files that render Shell without mocking `useBoard` must provide EventSourceProvider context (mock or wrapper). Currently affected: `Shell.test.tsx`, `Shell_1162.test.tsx`, `Shell_1192.test.tsx`, `Shell_1194.test.tsx`, `Shell_1228.test.tsx`, `PdsMigration_1230.test.tsx` (td:0)
10. Scoped regression gate: all `useBoard*`, `usePollingFetch_1227`, and the six AC9 Shell-rendering test suites pass with 0 failures (td:0)


### Auditor regression context
- Runtime dependency chain: `Shell.tsx:20` → `useBoard()` → `useSSEEvent('tasks-changed')` at `useBoard.ts:58` → throws without provider (`EventSourceProvider.tsx:178`)
- 10 Shell-rendering test files exist; 4 already mock `useBoard` (Shell_966, Shell_1227, Shell_1228_integration, Shell_1263) — safe. 6 do not — listed in AC9.
- Auditor also flagged `KanbanBoard_1252.test.tsx` and `ActivityTab_1156.test.tsx`. These are false positives: `KanbanBoard.tsx:4` is `import { type Board, type Task }` — type-only, zero runtime useSSEEvent call; `ActivityTab.tsx` has zero dependency on useSSEEvent/useBoard/EventSourceProvider. AC10 (scoped regression gate) catches any unexpected failures.

[[2026-05-03]]

## Architecture Review (original)

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
- No security findings in scope.

#### Test Integrity
- No live evidence of weakened or removed `TestFromAC_*` assertions in the current workspace.

#### Test Quality
- WEAK: AC4 does not yet have a discriminating proof that polling still runs while `status === 'connecting'`.
- WEAK: AC5 only simulates task-mtime changes after status is already open.

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

[[2026-05-02]]
## Test-Writer Notes
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
Current `useEffect` dep array: `[lastTasksMtime, sseStatus]`. When status transitions `connecting → open` with an existing non-null mtime (e.g. 500), the effect fires and calls `refetchTasksRef.current()` — an extra unintended fetch. Fix: guard on an actual mtime value change (track previous mtime in a ref), or restructure deps so sseStatus alone cannot trigger the SSE refetch path.

[[2026-05-02]]
## Builder Notes
- Implementation: updated serve/cockpit/web/src/hooks/useBoard.ts to ensure SSE-driven task refetch only runs when tasks-changed mtime value actually changes.
- Tests: quality-runner scoped task suite passed 10/10 in useBoard_1277.test.ts.
- Regression tests: quality-runner AC8 scoped suite passed 69/69.
- Coverage: useBoard.ts statements 96.15%, lines 96.15%, functions 100%, branches 70.37%.
- Lint: ESLint clean.
- Commit: a0eab0cf

[[2026-05-02]]
## Review Evidence (second pass)
### Test Results
- quality-runner scoped frontend run: 69 passed, 0 failed, 0 skipped.

### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 | PASS | AC2 | PASS | AC3 | PASS | AC4 | PASS | AC5 | PASS | AC6 | PASS | AC7 | PASS | AC8 | PASS |

### Verdict
- PASS -> docs | confidence 0.95

[[2026-05-02]]
## Docs Gate
### Checklist
| # | Check | Status |
|---|-------|--------|
| 1 | Descriptive prose docs | N/A |
| 2 | Module docstrings | N/A |
| 3 | External attribution | N/A |
| 4 | Research doc | Verified |
| 5 | Diagram maintenance | Updated |
| 6 | Explicit diagram creation | N/A |
| 7 | Deletion detection | N/A |

[[2026-05-02]]
## Audit
### AC Verification — all 8 lines PASS
### Cross-Task Regression
80 vitest tests FAIL across 8 test files — all caused by missing EventSourceProvider context in Shell-rendering tests. AC7 only enumerated direct `renderHook(useBoard)` callers. Auditor added AC9/AC10 addendum. Rejected to backlog.

### Architect Quality: 3/5

[[2026-05-03]]
## Architecture Review (re-review after auditor rejection)
**Verdict: APPROVED → todo**
AC9/AC10 addendum added. All td:0. Test-writer: SKIP.

[[2026-05-03]]
## Test-Writer Notes (pass-through)
- All new AC lines are td:0. Passing through to builder.

[[2026-05-03]]
## Builder Notes (AC10 reject)
- AC9 already satisfied — all 6 files have EventSourceProvider mocks.
- AC10 infeasible — full vitest suite blocked by unrelated RED suites (KanbanBoard_1252, ActivityTab_1156).
- Scoped AC9 files: 147 passed, 0 failed.
- Rejected to backlog requesting AC10 scope refinement.

[[2026-05-03]]
[[2026-05-03]]
AC10 refined from full-suite gate to scoped regression gate (11 files: 5 useBoard hook + 6 Shell-rendering). Builder confirmed AC9 already satisfied and unrelated RED suites (KanbanBoard_1252, ActivityTab_1156) are the sole blockers. Verified: all 6 AC9 files have EventSourceProvider mocks; both failing suites have zero EventSourceProvider/useBoard imports. Challenger skipped (all remaining work is td:0). Approved → todo.
[[2026-05-03]]
## Test-Writer Notes
- Retry (AC10 refinement): all new/changed AC lines remain td:0 — no tests needed.
- AC9 (td:0): enumerated Shell files — builder concern, not testable.
- AC10 (td:0): scoped regression gate (11 files) — builder execution concern, not testable.
- Passing through to builder.
[[2026-05-03]]
## Builder Notes
- Files changed: none (verification-only pass; implementation and AC9 wiring were already present in workspace).
- Test results: scoped AC10 regression gate passed **216/216** across 12 suites:
  - `useBoard_1277.test.ts` (10)
  - `useBoard.test.ts` (14)
  - `useBoard_967.test.ts` (19)
  - `useBoard_1261.test.ts` (8)
  - `useBoard_1263.test.ts` (5)
  - `usePollingFetch_1227.test.ts` (13)
  - `Shell.test.tsx` (18)
  - `Shell_1162.test.tsx` (21)
  - `Shell_1192.test.tsx` (11)
  - `Shell_1194.test.tsx` (3)
  - `Shell_1228.test.tsx` (13)
  - `PdsMigration_1230.test.tsx` (81)
- Lint status: scoped eslint run returned exit 0 (no errors). Two non-blocking warnings in `Shell_1228.test.tsx` (`@typescript-eslint/no-unused-vars` on `DetailTab` and `ActivityTab`).
- Coverage: not required for AC10 td:0 scoped gate; not run in this verification pass.
- Evidence summary: AC10 refined requirement (scoped regression gate on useBoard/usePollingFetch + six Shell-rendering suites) is satisfied in current workspace state; task ready for review.
[[2026-05-03]]
## Review Evidence
### Test Results
- quality-runner scoped frontend run: 216 passed, 0 failed, 0 skipped across the AC10 suite set (`useBoard_1277`, `useBoard`, `useBoard_967`, `useBoard_1261`, `useBoard_1263`, `usePollingFetch_1227`, `Shell`, `Shell_1162`, `Shell_1192`, `Shell_1194`, `Shell_1228`, `PdsMigration_1230`)
- adjacent regression check: `App_1276.test.tsx` 1 passed, 0 failed
- VS Code diagnostics: no errors in `serve/cockpit/web/src/hooks/useBoard.ts`, `serve/cockpit/web/src/App.tsx`, `serve/cockpit/web/src/Shell.tsx`, or the scoped suites

### Lint
- eslint: clean on `serve/cockpit/web/src/hooks/useBoard.ts` and all scoped suites
- adjacent `serve/cockpit/web/src/App.tsx` / `serve/cockpit/web/src/__tests__/App_1276.test.tsx`: clean

### Coverage
- `serve/cockpit/web/src/hooks/useBoard.ts`: 96.15% lines/statements, 100% functions, 70.37% branches; uncovered lines 110 and 119 are outside the AC-critical refactor path

### Pass 1 — Critical
#### Test-Writer AC Coverage
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 | `useBoard.ts:50-51` reads `useSSEEvent('tasks-changed')` and `useSSEEvent('decisions-changed')`; exact call assertions in `useBoard_1277.test.ts:125-143` and `useBoard_1263.test.ts:78-84` | PASS |
| AC2 | `useBoard.ts:51,130` preserves and returns `lastDecisionsMtime`; direct equality assertions in `useBoard_1277.test.ts:148-157` and `useBoard_1263.test.ts:96-106`; `Shell.tsx:20,74-77` still consumes the same field | PASS |
| AC3 | `useBoard.ts:121-123` maps `open -> green`, `connecting -> yellow`, else polling health; covered by `useBoard_1277.test.ts:162-169` and `useBoard_1261.test.ts:161-181` | PASS |
| AC4 | `useBoard.ts:54-57` passes `paused: sseStatus === 'open'`; discriminating proofs in `useBoard_1277.test.ts:177-194` and `useBoard_1277.test.ts:271-289`, plus open/closed regression checks in `useBoard_1261.test.ts:85-123` | PASS |
| AC5 | `useBoard.ts:90-99` only refetches on a distinct tasks-channel mtime while open; positive and negative proofs in `useBoard_1277.test.ts:199-315`, `useBoard_1261.test.ts:126-158`, and `useBoard_1263.test.ts:124-142` | PASS |
| AC6 | `useBoard.ts:1-4` imports `useSSEEvent` only; scoped search of `useBoard.ts` found no `useEventSource` reference | PASS |
| AC7 | module-level `vi.mock('../hooks/EventSourceProvider', ...)` present in `useBoard.test.ts:13`, `useBoard_967.test.ts:16`, `useBoard_1261.test.ts:11`, `useBoard_1263.test.ts:12`, and `usePollingFetch_1227.test.ts:14` | PASS |
| AC8 | quality-runner scoped frontend run passed all pre-existing `useBoard*` and `usePollingFetch_1227` suites with 0 failures | PASS |
| AC9 | module-level provider mocks present in `Shell.test.tsx:7`, `Shell_1162.test.tsx:27`, `Shell_1192.test.tsx:30`, `Shell_1194.test.tsx:30`, `Shell_1228.test.tsx:37`, and `PdsMigration_1230.test.tsx:28` | PASS |
| AC10 | quality-runner scoped frontend run passed the full 12-suite regression gate with 0 failures | PASS |

#### Security Review
- No security issues found in scope. The refactor reuses existing SSE/provider infrastructure and adds no new secrets, sinks, or dependencies.

#### Test Integrity
- Reconstructed builder diff scope: commit `9e7b3f43` touched `useBoard.ts` plus the five AC7 hook suites; commit `a0eab0cf` touched `useBoard.ts` only.
- No live evidence of weakened or removed `TestFromAC_*` assertions. Provider mocks preserve prior regression assertions and the task-specific AC tests remain discriminating.

#### Test Quality
- Assertion specificity: ADEQUATE/STRONG. Task-specific proofs are discriminating, especially the exact channel-call assertions and the AC5 status-only negative.
- Negative/error-path coverage: STRONG.
- Manual mutation reasoning: STRONG. Wrong channel names, a broadened pause predicate, or status-only refetch logic would fail current tests.
- Test independence: STRONG.
- Descriptive names: STRONG.

#### Data Safety
- No issues found.

#### Test Gaps
- No FAIL-level AC gap remains in the current task scope.
- Code-reader raised one out-of-scope integration concern: the scoped task suite does not itself prove the pre-existing App provider wrapper. I verified the dedicated adjacent regression `App_1276.test.tsx`, which passed and directly proves `App.tsx` still wraps `Shell` in `EventSourceProvider` with `url='/api/events'`. This concern does not justify failing task #1277.

#### Necessity Check
- No issues found. This is a refactor onto existing workspace infrastructure, not a new dependency or speculative feature.

### Deductions
- `-0.02` TestFromAC immutability check is snapshot-based rather than a full line-by-line commit diff comparison
- `-0.02` `useBoard_1277.test.ts` still contains stale RED-phase comments, which slightly lowers review clarity but not executable proof quality

### Verdict
- PASS -> docs | confidence 0.94

### Post-task Reflection
- The only substantive challenge was an App-wiring proof that sat outside the written AC; the right way to resolve it was an adjacent dedicated regression suite, not widening the current task after the fact.
- The latest task authority is the refined AC plus the current workspace snapshot; the builder's verification-only final cycle was acceptable because the live files already satisfied AC9/AC10.
- Snapshot-only immutability checks remain a small confidence deduction when direct commit-diff comparison is unavailable.
[[2026-05-03]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | All changed files are `.ts`/`.tsx` frontend source/test files — no IN-scope prose docs reference useBoard internals |
| 2 | Module docstrings | No | N/A | No `.py` files changed |
| 3 | External attribution | No | N/A | Task body and research doc cite no external repos/articles requiring attribution |
| 4 | Research doc | Yes | Verified | `.owlbear/research/1277-refactor-useboard-sse-context.md` exists and is linked from task body |
| 5 | Diagram maintenance | Yes | Updated | `share/diagrams/cockpit.excalidraw` describes `serve/cockpit/web/src/**` — footer updated from `2026-05-03 (bb63990c)` → `2026-05-03 (489578a3)` |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation requested |
| 7 | Deletion detection | No | N/A | No files deleted; `useEventSource` dead-code removal is tracked as follow-up #1300 |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| serve/cockpit/web/src/hooks/useBoard.ts | OUT | N/A (TypeScript source, not a .py docstring) |
| serve/cockpit/web/src/__tests__/useBoard*.test.ts | OUT | N/A (test files) |
| serve/cockpit/web/src/__tests__/Shell*.test.tsx | OUT | N/A (test files) |
| serve/cockpit/web/src/__tests__/PdsMigration_1230.test.tsx | OUT | N/A (test file) |
| share/diagrams/cockpit.excalidraw | IN | Footer updated (commit bc1cd508) |

### Files Updated
- share/diagrams/cockpit.excalidraw (footer: Last verified: 2026-05-03 (489578a3))

### Child Tasks Created
- None

### Scratch Files Cleaned
- None found
[[2026-05-03]]
## Audit (second pass)
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 | `useBoard.ts:4,50-51` imports and calls `useSSEEvent('tasks-changed')` and `useSSEEvent('decisions-changed')` | PASS |
| AC2 | `useBoard.ts:51,130` preserves `lastDecisionsMtime` from context in return type | PASS |
| AC3 | `useBoard.ts:121-123` maps `open → green`, `connecting → yellow`, else polling health | PASS |
| AC4 | `useBoard.ts:54` passes `paused: sseStatus === 'open'` to `usePollingFetch` | PASS |
| AC5 | `useBoard.ts:90-99` refetches only on distinct tasks-changed mtime while open (guarded by `lastObservedTasksMtimeRef`) | PASS |
| AC6 | `grep useEventSource useBoard.ts` → 0 matches; only `useSSEEvent` imported | PASS |
| AC7 | Reviewer verified all 5 test files; trusted | PASS |
| AC8 | quality-runner full vitest: 957/958 passed; all useBoard/usePollingFetch suites green | PASS |
| AC9 | Spot-checked Shell.test.tsx:7, Shell_1162.test.tsx:27, PdsMigration_1230.test.tsx:28 — all have `vi.mock('../hooks/EventSourceProvider')` | PASS |
| AC10 | quality-runner full vitest: 957/958 passed; 1 failure is ActivityTab_1156 (explicitly out of scope per AC addendum) | PASS |

### Test Results
- vitest: 957 passed, 1 failed (ActivityTab_1156 — out of scope, zero useSSEEvent/useBoard dependency)
- pytest: 3793 passed, 132 failed (all Python backend — kanban engine, MCP, knowledge — unrelated to frontend hook refactor)
- eslint: clean on useBoard.ts
- ruff: 1 error in copilot_auth.py (out of scope)

### Architect Quality: 3/5
Original 8 AC lines were specific and verifiable but missed Shell-rendering test blast radius (transitive `useBoard` → `useSSEEvent` → provider dependency). Challenger partially caught it (expanded AC7 from 2→5 files) but didn't enumerate Shell tests. Required auditor rejection + AC9/AC10 addendum. Recovery was clean. Score carried from first audit.

### Deduction Breakdown
- AC lines with no evidence: 0 × −0.02 = 0.00
- Lint violations in task scope: none → 0.00
- AC quality ≤ 3: −0.03
- Missing reviewer evidence: no → 0.00
- Full-suite test failures in task scope: 0 → 0.00

### Confidence: 0.97
### Action: archive