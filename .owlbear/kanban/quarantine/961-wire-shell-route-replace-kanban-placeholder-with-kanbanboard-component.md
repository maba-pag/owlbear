---
id: 961
title: 'Wire Shell route: replace kanban placeholder with KanbanBoard component'
status: archived
priority: important
created: 2026-04-18T14:45:58.189018+00:00
updated: 2026-04-18T18:45:27.625200+00:00
tags:
- cockpit
- frontend
- phase-2
- type:build
parent:
depends_on:
- 933
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Objective

Replace the `<div>kanban</div>` placeholder in Shell.tsx route "/" with the KanbanBoard component. Verify Shell integration tests still pass.

## Acceptance Criteria

- [ ] Route "/" renders KanbanBoard instead of placeholder div
- [ ] Shell.test.tsx updated if needed (currently tests for "kanban" text)
- [ ] Build passes (npm run build)

## Files

- `serve/cockpit/web/src/Shell.tsx`
- `serve/cockpit/web/src/__tests__/Shell.test.tsx`
[[2026-04-18]]

## Research

- Research doc: N/A — trivial wiring task, findings in task body
- Sources: 0 external, codebase-only analysis
- Recommendation: Direct import + swap (confidence: .95)
- Follow-up tasks created: none
- Decision requests: none

### Gate Checklist (trivial path)

1–4: N/A — trivial change: KanbanBoard component exists (`src/KanbanBoard.tsx`), fully tested (#933 archived/done), just needs import in Shell.tsx and route element swap.

### Implementation Notes for Builder

1. **Shell.tsx**: Add `import KanbanBoard from './KanbanBoard'`, replace `<div>kanban</div>` with `<KanbanBoard />` on Route "/".
2. **Shell.test.tsx**: Line ~85 checks `workspace?.textContent?.toLowerCase()).toContain('kanban')` — will break because KanbanBoard renders `"Loading…"` initially (async fetch). Update test to check for `data-testid="loading-indicator"` instead (verifies KanbanBoard is wired without coupling to its data-fetching behavior; data-fetching is already covered in KanbanBoard_933.test.tsx).
3. Build verification: `npm run build` to confirm no TS errors.
[[2026-04-18]]

## Architecture Review

### Refined Acceptance Criteria (supersedes original AC)

- [ ] Route "/" renders `<KanbanBoard />` instead of placeholder `<div>kanban</div>` (add import + swap element in Shell.tsx)
- [ ] Shell.test.tsx adds file-level fetch stub (`vi.stubGlobal('fetch', ...)` in `beforeEach`/`afterEach`) so all 15 default-route tests that now mount KanbanBoard don't fire real network requests or cause React act() warnings — follow the pattern in `KanbanBoard_933.test.tsx` (minimal stub returning 200 with empty board/tasks data)
- [ ] Shell.test.tsx route "/" assertion updated: replace `textContent.toContain('kanban')` with check for `data-testid="loading-indicator"` in workspace region (verifies KanbanBoard is wired without coupling to its data-fetching behavior)
- [ ] `npm test` passes (no act() warnings, no unhandled promise rejections)
- [ ] `npm run build` passes (no TS errors)

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One thing: swap placeholder for real component + update tests |
| Interface clarity | PASS (after refinement) | Original AC2 was vague ("if needed"). Refined to explicit fetch stub + assertion change |
| Dependency correctness | PASS | #933 archived/done. KanbanBoard.tsx exists with default export |
| Module layering | PASS | Sibling component import, no layer violation |
| TDD compliance | PASS | Test-writer will process at `todo` |
| KISS/YAGNI | PASS | Minimal scope — import + element swap + test stub |
| Premise challenge | PASS | Placeholder exists at Shell.tsx:37, component exists, wiring is necessary |
| Pattern consistency | PASS | Standard React import + route element pattern |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | Frontend/cockpit only |

### Failure Mode Map

N/A — no new failure codepaths. KanbanBoard already handles loading/error states.

### Challenge Results

- Challenger: **block** (confidence 0.40)
- Key concerns: (C1) 15 Shell tests mount KanbanBoard at "/" without fetch mock; (C2) React act() warnings from unguarded async effects; (C3) AC didn't require fetch stub
- Architect response: **accepted** — all concerns valid. Refined AC to require file-level fetch stub in Shell.test.tsx following KanbanBoard_933.test.tsx pattern. Added explicit `npm test` requirement. Concerns fully addressed in refined AC.

### Implementation Notes for Builder (updated)

1. **Shell.tsx**: `import KanbanBoard from './KanbanBoard'`, replace `<div>kanban</div>` with `<KanbanBoard />` on Route "/".
2. **Shell.test.tsx**: Add `beforeEach`/`afterEach` with `vi.stubGlobal('fetch', ...)` returning minimal valid responses (empty board/tasks). Follow `KanbanBoard_933.test.tsx` stub pattern. Update route "/" assertion to check for `data-testid="loading-indicator"`.
3. Verify: `npm test` clean (no warnings), `npm run build` clean.

### Verdict: APPROVE (after AC refinement)

### Action Taken: Refined AC to address challenger concerns (fetch stub requirement, explicit npm test gate), advanced to todo

[[2026-04-18]]

## Test-Writer Notes

- **Test file:** `serve/cockpit/web/src/__tests__/Shell.test.tsx`
- **Test class:** `TestFromAC_AppShell` (existing class, modified 1 test)
- **Infrastructure added:** file-level `beforeEach`/`afterEach` fetch stub (`vi.stubGlobal`) returning empty board/tasks — follows `KanbanBoard_933.test.tsx` pattern; prevents real network requests and React act() warnings once KanbanBoard is wired to route "/"

### Tests by category

| Category | Count | Notes |
|----------|-------|-------|
| Happy path | 1 FAIL | Route "/" renders loading-indicator in workspace |
| Infrastructure | — | Fetch stub (not a test, but required AC) |

- **Total new/modified tests:** 1
- **Fail confirmation:** `× route "/" renders KanbanBoard (loading indicator visible) in workspace region` — confirmed FAIL via `npm test`
- **Existing tests:** 14 pass unchanged

### AC Coverage

| AC | Test |
|----|------|
| Route "/" renders KanbanBoard instead of placeholder div | `route "/" renders KanbanBoard (loading indicator visible) in workspace region` → checks `data-testid="loading-indicator"` in workspace region — FAILS (placeholder has no such element) |
| Shell.test.tsx adds file-level fetch stub | `beforeEach`/`afterEach` with `vi.stubGlobal('fetch', ...)` added at file scope |
| Route "/" assertion updated (no more text 'kanban' check) | Old assertion replaced — new assertion checks loading-indicator |
| npm test passes (after build) | N/A — builder gate |
| npm run build passes | N/A — builder gate |
[[2026-04-18]]

## Builder Notes

### Files changed

- `serve/cockpit/web/src/Shell.tsx` — added `import KanbanBoard from './KanbanBoard'`, swapped `<div>kanban</div>` for `<KanbanBoard />` on route "/"
- `serve/cockpit/web/src/__tests__/Shell.test.tsx` — simplified file-level fetch stub from resolving-data pattern to `new Promise<never>(() => {})` (never-resolving), eliminating act() warnings; pattern follows KanbanBoard_963.test.tsx line 150

### Test results

- 18 passed, 0 failed, 0 warnings
- `npm run build` clean (135 modules, no TS errors)

### Lint

- ruff N/A (frontend-only task)

### Evidence

- Failing test before: `route "/" renders KanbanBoard (loading indicator visible) in workspace region` — FAIL (placeholder div had no loading-indicator)
- After: all 18 tests pass, zero act() warnings
- Commit: 5773862d
[[2026-04-18]]

## Review Evidence

### Test Results

- Command: `npm test -- --run` in `serve/cockpit/web`
- **79 passed, 0 failed** (5 test files)
- Shell.test.tsx: **18/18 passed, 0 act() warnings, 0 unhandled rejections**
- Pre-existing (not caused by #961): 8 act() warnings in App.test.tsx, 1 unhandled TypeError in KanbanBoard.test.tsx (`pressing Escape key dismisses context menu` → PDS jsdom-polyfill null ownerDocument); both files unchanged by builder

### Build Results

- Command: `npm run build`
- **PASS** — 135 modules, 0 TS errors

### Lint

- N/A (frontend-only task, ruff not applicable)

### AC Compliance

| AC Line | Evidence | Status |
|---------|----------|--------|
| Route "/" renders `<KanbanBoard />` instead of `<div>kanban</div>` | Shell.tsx:L2 import; Shell.tsx:L37 `<Route path="/" element={<KanbanBoard />} />` | PASS |
| File-level fetch stub (beforeEach/afterEach) | Shell.test.tsx:L12-15: `vi.stubGlobal('fetch', vi.fn(() => new Promise<never>(() => {})))` + `vi.unstubAllGlobals()` | PASS |
| Route "/" assertion → `data-testid="loading-indicator"` | Shell.test.tsx:L90: `expect(workspace?.querySelector('[data-testid="loading-indicator"]')).not.toBeNull()` | PASS |
| `npm test` passes (no act() warnings from KanbanBoard mount in Shell tests) | Shell.test.tsx 18/18 clean; fetch stub keeps KanbanBoard in loading state, no state updates post-assertion | PASS |
| `npm run build` passes | 135 modules, 0 TS errors | PASS |

### TestFromAC_AppShell Integrity

| Test | Change | Assessment |
|------|--------|------------|
| CSS Grid regions (5 tests) | None | PRESERVED |
| Nav rail (2 tests) | None | PRESERVED |
| Status bar (2 tests) | None | PRESERVED |
| route "/" renders KanbanBoard | Old `textContent.toContain('kanban')` → `data-testid="loading-indicator"` in workspace | STRENGTHENED |
| route "/hello" tests (2 tests) | None | PRESERVED |
| Sidecar tabs (5 tests) | None | PRESERVED |
| TestBuilderDiscovered (1 test) | None | PRESERVED |

### Builder Process Quality

CLEAN — 1 Builder Notes section, single attempt, no retries.

### Notable: Fetch Stub Pattern Deviation

Architect AC specified following `KanbanBoard_933.test.tsx` (resolving-data pattern). Builder instead used never-resolving `new Promise<never>(() => {})` citing `KanbanBoard_963.test.tsx:L149`. This is a valid improvement: the never-resolving pattern prevents state updates after assertions, eliminating act() warnings more reliably than the resolving-data approach. `data-testid="loading-indicator"` exists in KanbanBoard.tsx:L221, confirming the assertion is valid. No weakening.

### Deductions

- Pre-existing act() warnings in App.test.tsx (not caused by #961): –0
- Pre-existing unhandled error in KanbanBoard.test.tsx (not caused by #961): –0
- Fetch stub pattern deviation (improvement, not weakening): –0

### Verdict

Confidence: .97 → **PASS**
[[2026-04-18]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Route "/" wired to KanbanBoard — internal frontend routing only; copilot-instructions.md has no routing table and tech stack/build commands are unchanged |
| 2 | Module docstrings | No | N/A | TypeScript-only change (Shell.tsx, Shell.test.tsx); no Python modules created or modified |
| 3 | External attribution | No | N/A | Task states "Sources: 0 external, codebase-only analysis" |
| 4 | CLI changes | No | N/A | No CLI commands added or modified |
| 5 | Research doc | No | N/A | Task states "Research doc: N/A — trivial wiring task" |

### Files Updated

- None

### Scratch Files Cleaned

- None (no `.owlbear/scratch/961-*` files found)
[[2026-04-18]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| Route "/" renders `<KanbanBoard />` instead of placeholder | Shell.tsx:L3 import, L37 `<Route path="/" element={<KanbanBoard />} />` | PASS |
| File-level fetch stub (beforeEach/afterEach) | Shell.test.tsx:L12-15 `vi.stubGlobal('fetch', vi.fn(() => new Promise<never>(() => {})))` + L17 `vi.unstubAllGlobals()` | PASS |
| Route "/" assertion updated to `data-testid="loading-indicator"` | Shell.test.tsx:L90 checks `workspace?.querySelector('[data-testid="loading-indicator"]')` — target confirmed at KanbanBoard.tsx:L221 | PASS |
| `npm test` passes | Reviewer confirmed 79/0 (5 test files), Shell.test.tsx 18/18 clean, 0 act() warnings | PASS |
| `npm run build` passes | Reviewer confirmed 135 modules, 0 TS errors | PASS |

### Test Results

- pytest (full Python suite): 594 passed, 16 failed — all failures pre-existing in unrelated domains (knowledge MCP output schema, cockpit claimed fields). None in #961 scope.
- ruff: clean
- npm test: 79 passed, 0 failed (per reviewer evidence)

### Architect Quality: 4/5

Initial AC vague on test changes ("updated if needed"). Architect refined after challenger raised valid concerns (fetch stub, act() warnings). Well-structured refinement with explicit AC lines. Minor gap: original AC required improvement, but architect self-corrected effectively.

### Deduction Breakdown

- AC lines without evidence: 0 (all 5 PASS)
- Lint violations: 0
- AC quality (4/5 > 3): 0
- Missing reviewer section: 0
- In-scope test failures: 0

### Confidence: .98

### Action: archive
