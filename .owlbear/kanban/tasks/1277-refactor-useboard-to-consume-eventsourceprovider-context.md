---
id: 1277
title: Refactor useBoard to consume EventSourceProvider context
status: in-progress
priority: someday
created: 2026-05-02T12:10:47.678864+00:00
updated: 2026-05-03T00:33:48.376202+00:00
tags:
- cockpit
- frontend
parent: 1236
depends_on:
- 1276
blocked: false
block_reason:
claimed_at: 2026-05-03T00:33:48.376202+00:00
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
[[2026-05-02]]
## Builder Notes
- Implementation: updated serve/cockpit/web/src/hooks/useBoard.ts to ensure SSE-driven task refetch only runs when tasks-changed mtime value actually changes, preventing status-only (connecting -> open) transitions from triggering an extra fetch.
- Files changed: serve/cockpit/web/src/hooks/useBoard.ts
- Tests: quality-runner scoped task suite passed 10/10 in serve/cockpit/web/src/__tests__/useBoard_1277.test.ts.
- Regression tests: quality-runner AC8 scoped suite passed 69/69 across useBoard_1277, useBoard, useBoard_967, useBoard_1261, useBoard_1263, and usePollingFetch_1227 tests.
- Coverage: useBoard.ts statements 96.15%, lines 96.15%, functions 100%, branches 70.37%.
- Lint: ESLint clean on useBoard.ts and all 6 scoped regression test files.
- Commit: a0eab0cf
- Approach: retained existing status gate (open) and added previous-mtime tracking so refetch is tied to mtime deltas rather than effect re-runs from status-only changes.

### Post-task Reflection
- The regression was a classic dependency-array trap where adding status as a dependency broadened the trigger semantics beyond AC5.
- Keeping the fix in the production hook (not tests) preserved the stronger retry tests as durable proof.
- Re-running the full AC8 suite was necessary to ensure no behavior regression in legacy useBoard variants while tightening the refetch trigger.

[[2026-05-02]]
## Review Evidence
### Test Results
- quality-runner scoped frontend run: 69 passed, 0 failed, 0 skipped across `useBoard_1277.test.ts` (10), `useBoard.test.ts` (14), `useBoard_967.test.ts` (19), `useBoard_1261.test.ts` (8), `useBoard_1263.test.ts` (5), and `usePollingFetch_1227.test.ts` (13).
- VS Code diagnostics: no errors in `serve/cockpit/web/src/hooks/useBoard.ts` or the 6 scoped frontend test files.

### Lint
- Scoped lint clean on `serve/cockpit/web/src/hooks/useBoard.ts` plus all 6 scoped task/regression suites.
- Informational only: the coverage-retry run used broader default lint scope and surfaced one unrelated pre-existing ESLint config issue in `src/hooks/usePolling.ts:49` (`react-hooks/exhaustive-deps` rule missing). That file is outside the task diff and outside the scoped lint gate for #1277.

### Coverage
- quality-runner retry with coverage: overall 97.88%.
- `serve/cockpit/web/src/hooks/useBoard.ts`: 96.15% coverage.
- Changed SSE wiring is directly exercised at `useBoard.ts:58-64` and `useBoard.ts:90-99`; uncovered lines reported by quality-runner (`110`, `119`) are outside the retry fix path.

### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 | `useBoard.ts:58-59`; `useBoard_1277.test.ts` tests at lines 125 and 136; `useBoard_1263.test.ts` line 78 | PASS |
| AC2 | `useBoard.ts:44,59,147`; `useBoard_1277.test.ts` line 148; `useBoard_1263.test.ts` line 96 | PASS |
| AC3 | `useBoard.ts:135-136`; `useBoard_1277.test.ts` line 162; `useBoard_1261.test.ts` lines 161, 171, 181; `usePollingFetch_1227.test.ts` closed-state health assertions | PASS |
| AC4 | `useBoard.ts:64`; `useBoard_1277.test.ts` lines 177 and 271; `useBoard_1261.test.ts` lines 85 and 101 | PASS |
| AC5 | `useBoard.ts:90-99`; `useBoard_1277.test.ts` lines 199, 220, 241, and 294; `useBoard_1261.test.ts` line 126; `useBoard_1263.test.ts` lines 109 and 124 | PASS |
| AC6 | `useBoard.ts:1-4,58-59` contains `useSSEEvent` import/use and no `useEventSource` import | PASS |
| AC7 | module-level `vi.mock('../hooks/EventSourceProvider', ...)` present at `useBoard.test.ts:13`, `useBoard_967.test.ts:16`, `useBoard_1261.test.ts:11`, `useBoard_1263.test.ts:12`, `usePollingFetch_1227.test.ts:14` | PASS |
| AC8 | quality-runner run verified all pre-existing `useBoard*` and `usePollingFetch_1227` suites green (69/69) | PASS |

### Pass 1 — Critical
#### Test-Writer AC Coverage
- COVERED. The retry tests now discriminate the previously weak cases: `useBoard_1277.test.ts:271` proves polling continues while SSE status is `connecting`, and `useBoard_1277.test.ts:294` proves a status-only transition to `open` does not trigger an SSE refetch.

#### Security Review
- No issues found. This refactor only rewires internal hook consumption and adds no new boundary, dependency, persistence, or dynamic execution surface.

#### Test Integrity
- No weakened or removed `TestFromAC_*` assertions are visible in the current workspace snapshot.
- Lower-confidence note only: I verified builder/test-writer commit presence from `.git/logs/*` (`9e7b3f43`, `b4b2ac33`, `a0eab0cf`) but did not have a direct pre/post diff for immutable assertion comparison.

#### Test Quality
- STRONG. Assertions are exact and discriminating for the prior false-green risks: open vs connecting pause behavior, task-mtime vs decision-mtime triggers, and status-only transition non-triggering.

#### Data Safety
- No issues found.

#### Implementation-Aware Gap Analysis
- No significant untested path remains in the changed SSE wiring. Positive and negative coverage exist for task mtime changes, decisions-only changes, status-only changes, and pause-state transitions.

#### Necessity Check
- Not applicable. No new dependency, integration, or speculative capability was introduced.

#### Builder Process Quality
- CLEAN. The task file contains one prior `## Review Evidence` section at `.owlbear/kanban/tasks/1277-refactor-useboard-to-consume-eventsourceprovider-context.md:123`, followed by one targeted test-writer retry and one targeted builder retry that changed approach and resolved the reported proof gap.

### Deductions
- `-0.02` TestFromAC immutability verification is lower-confidence without direct commit diff access.
- `-0.01` Coverage required a retry because frontend instrumentation did not initialize on the first quality-runner pass.

### Verdict
- PASS -> docs | confidence 0.95

### Action
- Advance to `docs`.

### Post-task Reflection
- The prior FAIL was valid; the retry added the exact negative controls that were missing for AC4 and AC5.
- Independent reruns matter on frontend tasks: the first quality pass hid coverage behind a tooling hiccup, but the retry produced the needed module evidence.
- The broad ESLint retry surfaced unrelated frontend lint debt; scoped lint on the changed task files is the correct gate for this review.
[[2026-05-02]]
## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | Task is a frontend hook internal refactor (useBoard SSE wiring). No README or setup guide references useBoard SSE internals. |
| 2 | Module docstrings | No | N/A | TypeScript-only task; no Python modules created or modified. |
| 3 | External attribution | No | N/A | No external repos, articles, or docs cited; standard React context pattern. |
| 4 | Research doc | Yes | Verified | `.owlbear/research/1277-refactor-useboard-sse-context.md` exists and is linked in task body. Follow-up #1300 created for dead-code cleanup. |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/cockpit.excalidraw` describes `serve/cockpit/web/src/**` — matches `useBoard.ts`. Footer updated: `Last verified: 2026-05-03 (0ae82a7b)`. Commit: `5a7f802e`. |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | No files deleted; `useEventSource` dead code tracked via follow-up #1300. |

### Scope Classification
- **IN-scope changed files:** `serve/cockpit/web/src/hooks/useBoard.ts` (docstrings — TypeScript, N/A), `.owlbear/research/1277-refactor-useboard-sse-context.md` (research doc, verified)
- **OUT-scope:** all test files, application source

### Files Updated
- `share/diagrams/cockpit.excalidraw` — footer date/hash updated (commit `5a7f802e`)

### Scratch Files
- No `.owlbear/scratch/1277-*` files found.

### Child Tasks
- None created.
[[2026-05-02]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 | `useBoard.ts:4,58-59` imports and calls `useSSEEvent` for both channels | PASS |
| AC2 | `useBoard.ts:44,59,147` returns `lastDecisionsMtime` from context | PASS |
| AC3 | `useBoard.ts:135-136` maps open→green, connecting→yellow, else polling health | PASS |
| AC4 | `useBoard.ts:64` passes `paused: sseStatus === 'open'` | PASS |
| AC5 | `useBoard.ts:90-99` refetches on mtime delta only (prevMtimeRef guards status-only transitions) | PASS |
| AC6 | `useBoard.ts:1-4` — no `useEventSource` import in production | PASS |
| AC7 | 5 enumerated files have `vi.mock('../hooks/EventSourceProvider', ...)` | PASS |
| AC8 | useBoard* and usePollingFetch_1227 suites all green (69/69 scoped) | PASS |

### Cross-Task Regression (auditor unique finding)
**80 vitest tests FAIL across 8 test files** — all caused by this task's changes:
- `Shell.test.tsx` (18 tests)
- `Shell_1162.test.tsx`
- `Shell_1192.test.tsx`
- `Shell_1194.test.tsx`
- `Shell_1228.test.tsx`
- `KanbanBoard_1252.test.tsx`
- `ActivityTab_1156.test.tsx`
- `PdsMigration_1230.test.tsx`

All fail with: `useSSEEvent must be used within an EventSourceProvider`. These are component-level tests that render Shell (which calls useBoard → useSSEEvent) but were not updated with EventSourceProvider mocks.

AC7 only enumerated `renderHook(useBoard)` callers. Shell/component tests that transitively depend on useBoard were missed. The challenger noted "5 test files, not 2" but still only counted direct hook consumers, not component renderers.

### Test Results
- pytest: 128 failed, 3717 passed — all Python failures are pre-existing/unrelated to this frontend task (kanban engine, MCP, guidance tests)
- vitest: 80 failed, 878 passed — 80 failures are directly caused by #1277 (confirmed via error message)
- ruff: 1 violation in `serve/knowledge/copilot_auth.py:106` (unrelated T201)
- eslint: 1 error in `usePolling.ts:49` (pre-existing, unrelated)

quality-runner env fallback: SIGINT (exit 130) on two consecutive runs; direct execution used.

### Architect Quality: 3/5
AC7's test blast radius was undercounted even after challenger intervention. The challenger correctly flagged the blast radius issue but only counted `renderHook(useBoard)` callers (5 files), missing component-level renders that transitively use useBoard through Shell (8 additional files). This gap resulted in a 80-test regression that was invisible to scoped reviewer runs but caught by the full-suite auditor gate.

### Deduction Breakdown
- -0.10: 80 vitest failures across 8 test files directly caused by task changes (cross-task regression)

### Confidence: 0.90
### Action: reject-to-backlog

### Required Fix
Add `vi.mock('../hooks/EventSourceProvider', ...)` (or equivalent provider wrapper) to all 8 failing test files that render Shell or components using useBoard transitively. Re-run full vitest suite to confirm 0 failures.
[[2026-05-03]]

## Acceptance Criteria (addendum — auditor regression fix)

9. Test files that render Shell without mocking `useBoard` must provide EventSourceProvider context (mock or wrapper). Currently affected: `Shell.test.tsx`, `Shell_1162.test.tsx`, `Shell_1192.test.tsx`, `Shell_1194.test.tsx`, `Shell_1228.test.tsx`, `PdsMigration_1230.test.tsx` (td:0)
10. Full vitest suite (`npm test` in `serve/cockpit/web/`) passes with 0 failures (td:0)

### Auditor regression context
- Runtime dependency chain: `Shell.tsx:20` → `useBoard()` → `useSSEEvent('tasks-changed')` at `useBoard.ts:58` → throws without provider (`EventSourceProvider.tsx:178`)
- 10 Shell-rendering test files exist; 4 already mock `useBoard` (Shell_966, Shell_1227, Shell_1228_integration, Shell_1263) — safe. 6 do not — listed in AC9.
- Auditor also flagged `KanbanBoard_1252.test.tsx` and `ActivityTab_1156.test.tsx`. These are false positives: `KanbanBoard.tsx:4` has type-only import (`import { type Board, type Task }`); `ActivityTab.tsx` has zero dependency on useSSEEvent/useBoard/EventSourceProvider. AC10 (full suite gate) will catch any unexpected failures.

[[2026-05-03]]
## Architecture Review (re-review after auditor rejection)

**Verdict: APPROVED → todo**

### Reason for re-review
Auditor rejected to backlog: 80 vitest failures across component-level test files rendering Shell without EventSourceProvider context. AC7 only enumerated direct `renderHook(useBoard)` callers (5 files), missing Shell-rendering component tests.

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Fix is scoped to test harness mocks only — no production change |
| Interface clarity | PASS | AC9 states behavioral requirement + enumerates affected files; AC10 is binary gate |
| Dependency correctness | PASS | No new deps. #1276 done. Follow-up #1300 tracks dead useEventSource |
| Module layering | PASS | Mock at provider boundary — correct layer |
| TDD compliance | PASS | AC9/AC10 are td:0; existing AC1-AC8 already implemented and verified |
| KISS/YAGNI | PASS | Minimal fix: 6 test files need provider mock |
| Premise challenge | PASS | Regression is real — Shell renders useBoard which calls useSSEEvent |
| Pattern consistency | PASS | Same vi.mock pattern as AC7 |
| Security surface | PASS | Test-only change |
| Single domain | PASS | cockpit frontend only |

### Blast radius analysis (10 Shell-rendering test files)
| File | Mocks useBoard? | Needs fix? |
|------|----------------|-----------|
| Shell.test.tsx | No | YES |
| Shell_966.test.tsx | Yes (line 19) | No — safe |
| Shell_1162.test.tsx | No | YES |
| Shell_1192.test.tsx | No | YES |
| Shell_1194.test.tsx | No | YES |
| Shell_1227.test.tsx | Yes (line 20) | No — safe |
| Shell_1228.test.tsx | No | YES |
| Shell_1228_integration.test.tsx | Yes (line 21) | No — safe |
| Shell_1263.test.tsx | Yes (line 22) | No — safe |
| PdsMigration_1230.test.tsx | No | YES |

### Auditor false-positive analysis
- `KanbanBoard_1252.test.tsx`: KanbanBoard.tsx:4 is `import { type Board, type Task }` — type-only, zero runtime useSSEEvent call
- `ActivityTab_1156.test.tsx`: ActivityTab.tsx has no import of useSSEEvent, useBoard, or EventSourceProvider
- AC10 (full suite gate) catches any unexpected failures

### Challenger
Outcome: reconsider (0.78). Addressed: (1) documented all 10 Shell-rendering test files with safety analysis; (2) included runtime import graph evidence for auditor override; (3) reworded AC9 as behavioral requirement rather than technique prescription; (4) simplified AC10 to binary gate. Confidence after addressing: 0.90.

### Notes
- AC1-AC8 are fully implemented and pipeline-verified. Only AC9/AC10 are new work.
- Test-writer: SKIP — all new AC lines are td:0. Existing test file `useBoard_1277.test.ts` (10 tests) is unaffected.
- Builder: add EventSourceProvider mock or useBoard mock to each AC9 file. The choice of mock strategy is left to the builder (consistent with existing file patterns).
[[2026-05-03]]
## Test-Writer Notes
- Retry: all new AC lines are td:0 — no new failing tests required.
  - AC9 (td:0): add EventSourceProvider mock/wrapper to 6 Shell-rendering test files
  - AC10 (td:0): full vitest suite passes with 0 failures (binary gate)
- Architecture review explicitly states "Test-writer: SKIP — all new AC lines are td:0."
- Existing 10 tests in `serve/cockpit/web/src/__tests__/useBoard_1277.test.ts` are unaffected and remain as-is.
- Passing through to builder for Shell-rendering test file fixes (AC9/AC10).