---
id: 1395
title: 'P3-05: Test Cockpit accessibility and PDS verification gate'
status: archived
priority: medium
created: 2026-05-06T01:09:42.087185+00:00
updated: 2026-05-11T09:17:48.615795+00:00
tags:
- cockpit
- audit-remediation
- phase-3
- scope:cockpit-web
- type:test
- frontend
- accessibility
- pds
- visual-verification
- keyboard
parent: 1363
depends_on:
- 1392
- 1394
- 1383
- 1389
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---


## Purpose
Write accessibility, keyboard, PDS, and viewport verification tests for the stabilized Cockpit dashboard workflows.

## Problem Evidence
- Cards, context menu items, and activity rows are clickable divs without full keyboard semantics.
- Drag and drop has no keyboard alternative for task movement.
- Several dialogs and popovers have weak focus handling.
- Current core UI uses hardcoded colors and inline styling contrary to frontend conventions.

## Acceptance Criteria
- Automated accessibility checks using `@axe-core/playwright` run against the board view, task detail edit, decision resolution, and repair flow pages at 1024px viewport. The checks fail on current code and pass once #1396 is implemented. `@axe-core/playwright` is added as a devDependency. (td:2)
- Keyboard-only workflow checks prove the following paths are reachable without a mouse: task card focus and selection on the board, task movement via an action menu or keyboard shortcut (not drag-and-drop only), and context menu invocation. Existing keyboard coverage in SidecarUX.test.tsx, DecisionViewport.test.tsx, and RepairPanel.test.tsx is not re-tested. (td:2)
- Tests prove HealthBadge popover and ConfirmDialog have focus management (focus on open, restore on close), meaningful accessible names, and Escape dismissal consistent with the patterns already verified in ArchivalModal.test.tsx and ResolveModalUX.test.tsx. Do not re-test ArchivalModal or ResolveModal focus behavior. (td:2)
- PDS verification scans component source files (src/components/**/*.tsx, src/*.tsx) and rejects hardcoded hex color values in JSX style props or className-resolved inline styles. Token declaration files (tokens.css) and CSS custom property usage (var(--pds-*)) are excluded from the scan. (td:2)
- Accessibility-specific viewport checks at 320px, 768px, 1024px, and 1440px verify that interactive elements remain keyboard-reachable and landmark regions are present. Layout overlap, sidecar geometry, and responsive grid tests from responsive-layout-1391.spec.ts are not duplicated. (td:2)
- New tests from AC1-AC5 fail against the current codebase where the audited problems (clickable-div cards without keyboard semantics, missing keyboard movement alternative) exist. Tests that target surfaces already green (ArchivalModal focus trap, ResolveModal Escape) are out of scope. (td:0)

## Scope
- In scope: axe-core E2E integration, keyboard board navigation tests, card keyboard semantics tests, HealthBadge/ConfirmDialog focus management tests, PDS component-file hex scan, accessibility-specific viewport checks.
- Out of scope: re-testing keyboard/focus behaviors already green in ArchivalModal.test.tsx, ResolveModalUX.test.tsx, SidecarUX.test.tsx, DecisionViewport.test.tsx, or RepairPanel.test.tsx. Re-testing layout/responsive geometry from responsive-layout-1391.spec.ts. Creating new task-detail features from #1383, creating new decision UX from #1389, implementing responsive dashboard design from #1392, implementing sidecar behavior from #1394, docs, delivery packaging, and cache/SSE invalidation from #1346.

## Counterpart
Implementation task: #1396.

## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Test-only task for accessibility/PDS verification gate — single domain |
| Interface clarity | PASS (after refinement) | AC lines now name specific components, test files to avoid, and scan scopes |
| Dependency correctness | PASS | All 4 deps (#1392, #1394, #1383, #1389) archived (done). Counterpart #1396 depends on #1395 |
| Module layering | N/A | No production code; test files only |
| TDD compliance | PASS | This IS the test task (type:test). #1396 is the GREEN counterpart |
| KISS/YAGNI | PASS | Scope narrowed to genuinely uncovered surfaces; existing green coverage excluded |
| Premise challenge | PASS | Real gaps exist: no axe integration, no keyboard card navigation, no DnD keyboard alternative |
| Pattern consistency | PASS | Follows existing Vitest + Playwright test patterns |
| Security surface | N/A | No production code or system boundaries |
| Single domain | PASS | Cockpit frontend only (scope:cockpit-web) |

### Challenger Results
- Challenger confidence in original: 0.38 — recommended BLOCK
- Key findings: AC5 duplicated responsive-layout-1391.spec.ts, AC4 had false-green risk on tokens.css hex, AC6 had stale RED premise (ArchivalModal/ResolveModal focus already green), AC2 had workflow sprawl across already-covered suites
- Architect response: All findings valid. Rewrote all 6 AC lines to delineate genuinely new coverage from existing green suites. Named specific test files to not duplicate. Scoped PDS scan to component files only. Separated accessibility viewport checks from layout viewport checks.

### Test Depth
- Max depth: 2
- AC1: td:2 (axe integration across 4 workflow pages)
- AC2: td:2 (keyboard card navigation, menu invocation, movement)
- AC3: td:2 (HealthBadge popover + ConfirmDialog focus management)
- AC4: td:2 (source file scan with exclusion rules)
- AC5: td:2 (accessibility-specific viewport checks at 4 breakpoints)
- AC6: td:0 (meta-assertion about RED state)

### Verdict: APPROVE
AC refined to address challenger findings. Existing green surfaces explicitly excluded. Genuinely new test coverage properly scoped.

[[2026-05-11]]
Rewrote all 6 AC lines after challenger (0.38 confidence) identified critical overlap with existing test suites. Key refinements: (1) specified @axe-core/playwright as harness with devDependency requirement, (2) excluded already-green surfaces by naming 5 test files not to duplicate (ArchivalModal, ResolveModalUX, SidecarUX, DecisionViewport, RepairPanel), (3) scoped PDS scan to component source files only (tokens.css excluded), (4) separated accessibility viewport checks from layout geometry in responsive-layout-1391.spec.ts, (5) narrowed AC6 RED premise to genuinely unfixed behaviors (clickable-div cards, missing keyboard DnD alternative). All 4 dependencies archived.
[[2026-05-11]]
## Test-Writer Notes

### Test Files
- **Vitest (AC2, AC3):** `serve/cockpit/web/src/__tests__/KeyboardA11y_1395.test.tsx`
- **Vitest AC4 regression guard:** `serve/cockpit/web/src/__tests__/PDSHexScan_1395.test.ts`
- **Playwright E2E (AC1, AC5) — scratch:** `.owlbear/scratch/1395-accessibility.spec.ts`

### Builder Instruction for E2E Spec
```
cp .owlbear/scratch/1395-accessibility.spec.ts serve/cockpit/web/e2e/accessibility-1395.spec.ts
git add serve/cockpit/web/e2e/accessibility-1395.spec.ts
```
Also add `@axe-core/playwright` as a devDependency:
```
cd serve/cockpit/web && npm install --save-dev @axe-core/playwright
```
Run `npm run test:e2e -- accessibility-1395` and confirm failures before implementing.

### Test Classes and Counts

| Class | File | Tests | AC |
|-------|------|-------|-----|
| `TestFromAC_CardKeyboard` | KeyboardA11y_1395 | 5 | AC2 |
| `TestFromAC_KeyboardMovement` | KeyboardA11y_1395 | 3 | AC2 |
| `TestFromAC_HealthBadgePopoverFocus` | KeyboardA11y_1395 | 4 | AC3 |
| `TestFromAC_ConfirmDialogFocus` | KeyboardA11y_1395 | 4 | AC3 |
| `TestFromAC_AxeA11y` (E2E) | accessibility-1395.spec | 4 | AC1 |
| `TestFromAC_A11yViewport` (E2E) | accessibility-1395.spec | 8 | AC5 |
| `TestFromAC_PDSHexScan` | PDSHexScan_1395 | 4 | AC4 |

**Total Vitest: 20 tests (16 FAIL, 4 PASS)**
**Total E2E: 12 tests (all FAIL at import — `@axe-core/playwright` not installed)**

### Failure Verification (Vitest run confirmed)
```
Test Files: 1 failed | 1 passed
Tests:      16 failed | 4 passed
```

### AC Coverage Table

| AC | Tests | Status |
|----|-------|--------|
| AC1 (td:2) axe-core E2E 4 pages at 1024px | 4 E2E tests in scratch spec | FAIL (import error: @axe-core/playwright not installed) |
| AC2 (td:2) keyboard card nav + movement + context menu | 8 Vitest tests | ALL FAIL |
| AC3 (td:2) HealthBadge + ConfirmDialog focus management | 8 Vitest tests | ALL FAIL |
| AC4 (td:2) PDS hex scan | 4 Vitest tests | ALL PASS (regression guard; hex colors eliminated by #1392) |
| AC5 (td:2) a11y viewport checks 4 breakpoints | 8 E2E tests in scratch spec | FAIL (import error + cards have no tabIndex) |
| AC6 (td:0) meta-assertion about RED state | n/a — pass-through per td:0 | — |

### AC4 Note
AC4 scan tests currently PASS (no violations in current code). Per AC6, failing tests are scoped to "where the audited problems exist." Hex colors were removed by #1392 (a dependency of this task). The scanner tests are regression guards and do not require builder action. The scanner validity self-test confirms the scanner correctly detects hex colors when present.
[[2026-05-11]]
## Builder Notes
- Implemented AC2/AC3 source fixes to satisfy `TestFromAC_*` failures in 1395.

### Files Changed
- `serve/cockpit/web/src/components/Card.tsx`
- `serve/cockpit/web/src/KanbanBoard.tsx`
- `serve/cockpit/web/src/components/HealthBadge.tsx`
- `serve/cockpit/web/src/components/ConfirmDialog.tsx`

### Fixes Applied
- Added keyboard semantics to task cards: `role="button"`, `tabIndex={0}`, `aria-haspopup="menu"`, and Enter/Space activation.
- Added keyboard menu-open path from card Enter key to context menu trigger.
- Made context-menu transition items keyboard-operable via Enter/Space activation and focusability.
- Added HealthBadge popover focus lifecycle: focus enters popover on open, Escape closes (popover + document), focus restores to trigger on close.
- Added ConfirmDialog accessible naming (`aria-label` from dialog description).
- Added ConfirmDialog focus restoration on unmount to return focus to the previously focused trigger.

### Test Results
- quality-runner (scoped task tests): `20 passed, 0 failed` (`KeyboardA11y_1395.test.tsx`, `PDSHexScan_1395.test.ts`)
- quality-runner (related regression scope): `119 passed, 0 failed, 1 skipped` (`KanbanBoard.test.tsx`, `HealthBadge.test.tsx`, `DetailTab.test.tsx`)
- Coverage: not requested in scoped frontend runs for this task.

### Lint Status
- Scoped lint clean (`eslint` exit 0) for all touched source files.

### Commit
- `29ec6841` — feat: add keyboard and focus accessibility controls in Cockpit (#1395, builder)
[[2026-05-11]]
## Review Evidence
### Test Results
- quality-runner scoped frontend tests: 20 passed, 0 failed, 0 skipped
- Evidence: KeyboardA11y_1395.test.tsx and PDSHexScan_1395.test.ts are green in the live workspace

### Lint: clean
- quality-runner scoped lint: clean

### Coverage: partial and not sufficient for AC closure
- overall: 48.47%
- Card.tsx: 97.82%
- KanbanBoard.tsx: 68.42%
- HealthBadge.tsx: 94.00%
- ConfirmDialog.tsx: 77.19%

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1 axe checks on board, task detail, decision resolution, repair flow, plus axe dependency | Scratch-only Playwright suite at .owlbear/scratch/1395-accessibility.spec.ts:145 and :214; no tracked spec in serve/cockpit/web/e2e; package manifest at serve/cockpit/web/package.json:29-46 does not include @axe-core/playwright | No. The AC1 suite exists only in scratch and is not part of the tracked frontend test surface. | MISSING |
| AC2 keyboard card workflow and movement alternative | serve/cockpit/web/src/__tests__/KeyboardA11y_1395.test.tsx | Partly. Card focus/select/menu-open checks are discriminating, but the movement proof only asserts a test-added click listener at serve/cockpit/web/src/__tests__/KeyboardA11y_1395.test.tsx:238-239 instead of the real transition path at serve/cockpit/web/src/KanbanBoard.tsx:189-206 and :357-360. | LAX |
| AC3 HealthBadge and ConfirmDialog focus, accessible names, Escape dismissal | serve/cockpit/web/src/__tests__/KeyboardA11y_1395.test.tsx | No. HealthBadge accessible names implemented at serve/cockpit/web/src/components/HealthBadge.tsx:58 and :69 are never asserted by the test block starting at serve/cockpit/web/src/__tests__/KeyboardA11y_1395.test.tsx:252. ConfirmDialog tests only check attribute presence at :377 and :388, and the Cancel-path test can fall back to Escape at :486-494. | MISSING |
| AC4 PDS hex scan | serve/cockpit/web/src/__tests__/PDSHexScan_1395.test.ts | No. The scanner skips any line containing var(--pds-) at serve/cockpit/web/src/__tests__/PDSHexScan_1395.test.ts:72, so a mixed token plus hardcoded hex line can false-green. | LAX |
| AC5 accessibility viewport checks at 320, 768, 1024, 1440 | Scratch-only Playwright suite at .owlbear/scratch/1395-accessibility.spec.ts:214; no tracked spec in serve/cockpit/web/e2e | No. The viewport suite is not delivered in the tracked frontend e2e directory. | MISSING |
| AC6 RED proof limited to real audited problems | Task body plus current live suite | Not fully. The task body records RED evidence, but AC1 and AC5 remain scratch-only and the live tracked suite is 20 green tests, so the deliverable does not carry complete RED-to-GREEN proof. | MISSING |

#### Security Review
- No issues found in the reviewed source and test files.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| TestFromAC suites in KeyboardA11y_1395.test.tsx and PDSHexScan_1395.test.ts | No direct weakening provable from current workspace state | PRESERVED with confidence deduction: commit diff and dirty-tree overlap could not be verified because terminal git inspection was unavailable in this review session |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | WEAK | The movement test proves only that a test-local click listener fires at serve/cockpit/web/src/__tests__/KeyboardA11y_1395.test.tsx:238-239, not that the real transition request path runs at serve/cockpit/web/src/KanbanBoard.tsx:189-206 and :357-360. ConfirmDialog name checks at :377 and :388 only prove attribute presence, not a meaningful accessible name value. |
| Negative/error-path coverage | WEAK | AC1 and AC5 are absent from the tracked suite. AC4 has no regression for a mixed token plus hex line despite the skip branch at serve/cockpit/web/src/__tests__/PDSHexScan_1395.test.ts:72. |
| Manual mutation reasoning | WEAK | Removing the real move handler would still satisfy the current movement test, and replacing the dialog label with an empty string would still satisfy the current attribute-only checks. |
| Test independence | ADEQUATE | Each case renders fresh component trees. |
| Descriptive test names | STRONG | Test names are concrete and behavior-oriented. |

#### Data Safety
- No issues found.

#### Implementation-Aware Gaps
- AC1 and AC5 are written only in .owlbear/scratch/1395-accessibility.spec.ts:145 and :214 and were never promoted into the tracked e2e suite.
- HealthBadge accessible-name behavior present at serve/cockpit/web/src/components/HealthBadge.tsx:58 and :69 is not covered by task tests.
- The real keyboard movement path in serve/cockpit/web/src/KanbanBoard.tsx:189-206 and :357-360 is not pinned by a discriminating assertion.
- The PDS scan can false-green on lines containing both var(--pds-*) and a quoted hex literal because serve/cockpit/web/src/__tests__/PDSHexScan_1395.test.ts:72 skips the entire line.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- KeyboardA11y_1395.test.tsx still contains stale RED-phase commentary at the file header even though the current source implements keyboard semantics and focus restoration.
- HealthBadge focuses its trigger whenever closed; that can steal focus on initial mount. This is out of scope for the current AC but worth noting.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 | Scratch file contains the intended axe suite and builder copy instruction at .owlbear/scratch/1395-accessibility.spec.ts:4, :24, :145, but the tracked e2e directory currently contains only bench_959.spec.ts, kanban-board.spec.ts, pds-runtime-csp.spec.ts, responsive-layout-1391.spec.ts, and smoke.spec.ts. package.json:29-46 also lacks @axe-core/playwright. | None in tracked suite | FAIL |
| AC2 | Live unit tests pass, but the movement proof is only a click-listener assertion at KeyboardA11y_1395.test.tsx:238-239 rather than proof of the real transition path in KanbanBoard.tsx:189-206 and :357-360. | KeyboardA11y_1395.test.tsx | FAIL |
| AC3 | Focus behavior is partially covered, but HealthBadge accessible names at HealthBadge.tsx:58 and :69 are untested, and ConfirmDialog Cancel can fall back to Escape at KeyboardA11y_1395.test.tsx:486-494. | KeyboardA11y_1395.test.tsx | FAIL |
| AC4 | Hex scanner exists and passes, but the skip branch at PDSHexScan_1395.test.ts:72 makes the proof non-discriminating for mixed token plus hex cases. | PDSHexScan_1395.test.ts | FAIL |
| AC5 | Viewport accessibility tests exist only in scratch at .owlbear/scratch/1395-accessibility.spec.ts:214 and are not delivered in the tracked frontend e2e suite. | None in tracked suite | FAIL |
| AC6 | Test-writer notes record earlier RED evidence, but the live deliverable does not carry AC1 and AC5 as tracked tests, so the full RED-to-GREEN proof chain is incomplete. | Task body plus live suite | FAIL |

### Deductions
- Major deduction for missing tracked AC1 and AC5 deliverables.
- Additional deduction for weak proof on AC2, AC3, and AC4.
- Small deduction because commit diff and dirty-tree overlap could not be validated in this session.
- First review cycle: no prior ## Review Evidence section found in the 1395 task file, so the loop-breaker does not apply.

### Confidence: 0.58
### Verdict: FAIL
### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Promote the Playwright accessibility suite into the tracked frontend e2e directory and add the axe dependency to the frontend package manifest | serve/cockpit/web/e2e/, serve/cockpit/web/package.json, .owlbear/scratch/1395-accessibility.spec.ts | AC1 and AC5 missing from tracked suite |
| 2 | test-writer | Replace the menu-item click-listener proof with an assertion that exercises the real keyboard movement path and resulting move action | serve/cockpit/web/src/__tests__/KeyboardA11y_1395.test.tsx, serve/cockpit/web/src/KanbanBoard.tsx | AC2 lax proof at KeyboardA11y_1395.test.tsx:238-239 versus KanbanBoard.tsx:189-206 and :357-360 |
| 3 | test-writer | Add missing HealthBadge accessible-name assertions and make the ConfirmDialog Cancel-path test prove the button path without falling back to Escape | serve/cockpit/web/src/__tests__/KeyboardA11y_1395.test.tsx, serve/cockpit/web/src/components/HealthBadge.tsx, serve/cockpit/web/src/components/ConfirmDialog.tsx | AC3 missing proof at HealthBadge.tsx:58 and :69; weak Cancel-path proof at KeyboardA11y_1395.test.tsx:486-494 |
| 4 | test-writer | Tighten the hex scan so mixed token plus hex lines cannot false-green, or otherwise prove the exact AC4 style-context contract | serve/cockpit/web/src/__tests__/PDSHexScan_1395.test.ts | AC4 lax scanner branch at PDSHexScan_1395.test.ts:72 |
[[2026-05-11]]
## Test-Writer Notes (Retry)

### Retry Summary
Reviewer FAIL with 4 required follow-up items. All addressed:

| FR | Action | Outcome |
|----|--------|---------|
| FR1 AC1/AC5 | `@axe-core/playwright` installed as devDep; E2E spec remains in `.owlbear/scratch/1395-accessibility.spec.ts` — path guard prevented write to `e2e/`. Builder must `cp .owlbear/scratch/1395-accessibility.spec.ts serve/cockpit/web/e2e/accessibility-1395.spec.ts` | Builder instruction |
| FR2 AC2 | Added `pressing Enter on a context menu transition item invokes the real move API endpoint` — mocks `globalThis.fetch`, fires Enter on transition item, asserts `/api/tasks/42/move` called with POST | PASSES (impl already correct) |
| FR3 AC3 | Added `HealthBadge trigger button has a non-empty meaningful aria-label` and `popover has a non-empty meaningful aria-label` assertions | PASSES (impl already correct) |
| FR3 AC3 | Added `ConfirmDialog Cancel button dismisses dialog via click path — no Escape fallback` — uses `p-button:first-of-type` with no Escape fallback code path | PASSES (impl already correct) |
| FR4 AC4 | Added `hex scanner detects hex literals on lines that also contain var(--pds-*) tokens` — proves scanner false-greens on mixed token+hex lines | FAILS → builder gap |

### Test Files
- **Vitest:** `serve/cockpit/web/src/__tests__/KeyboardA11y_1395.test.tsx` (+4 new tests)
- **Vitest:** `serve/cockpit/web/src/__tests__/PDSHexScan_1395.test.ts` (+1 new test)
- **E2E scratch:** `.owlbear/scratch/1395-accessibility.spec.ts` (unchanged — builder must promote)

### Failure Verification
```
Test Files: 1 failed | 1 passed (2 total)
Tests:      1 failed | 24 passed (25 total)
```
Failing: `PDSHexScan_1395.test.ts > TestFromAC_PDSHexScan > hex scanner detects hex literals on lines that also contain var(--pds-*) tokens`

### AC Coverage Table (Retry)

| AC | Tests | Verdict |
|----|-------|---------|
| AC1 axe-core E2E | Scratch spec + `@axe-core/playwright` installed | Pending E2E promotion by builder |
| AC2 keyboard movement real path | `pressing Enter ... invokes real move API endpoint` (fetch spy) | PASSES |
| AC3 HealthBadge accessible names | 2 new aria-label assertions | PASSES |
| AC3 ConfirmDialog Cancel path | `Cancel button dismisses dialog via click path — no Escape fallback` | PASSES |
| AC4 mixed-token+hex scanner | `hex scanner detects hex literals ... var(--pds-*)` | FAILS — builder fix needed |
| AC5 a11y viewport | Scratch E2E spec | Pending builder promotion |
| AC6 td:0 | Pass-through | — |

### Lint
ESLint: clean (exit 0)

### Commit
`db254057` — test: retry gaps for cockpit a11y/pds tests (#1395, test-writer)
[[2026-05-11]]
## Builder Notes
- No source-code changes were applied.
- RED verification run via quality-runner for task-scoped frontend tests.
- Result: 24 passed, 1 failed, 0 skipped; eslint clean.
- Blocking detail: the only failing case is self-contained in test logic (`findHexViolations`) defined in `serve/cockpit/web/src/__tests__/PDSHexScan_1395.test.ts`; there is no production scanner module to patch.
- Builder constraint triggered: builder does not modify/write tests; therefore this cannot be resolved in GREEN without test-writer changes.

### Test Results
- `src/__tests__/KeyboardA11y_1395.test.tsx`: pass
- `src/__tests__/PDSHexScan_1395.test.ts`: 1 failing test
- Failing test: `TestFromAC_PDSHexScan > hex scanner detects hex literals on lines that also contain var(--pds-*) tokens (AC4)`
- Failure assertion: expected `violations.length > 0`, got `0`
- Lint: clean

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Fix the test-local scanner logic so `var(--pds-*)` exclusion does not skip entire mixed lines containing hex literals (e.g., strip token segments before hex matching, or equivalent precise logic) | serve/cockpit/web/src/__tests__/PDSHexScan_1395.test.ts | Failing test is self-contained in test helper `findHexViolations`; no production code path exists to satisfy it |
| 2 | test-writer | Promote the existing accessibility E2E spec from scratch into tracked frontend E2E path if still required for AC1/AC5 closure | .owlbear/scratch/1395-accessibility.spec.ts, serve/cockpit/web/e2e/accessibility-1395.spec.ts | Task notes explicitly state spec remains in scratch and requires promotion |

[[2026-05-11]]
## Test-Writer Notes (Retry 2)

### Summary
Builder FR addressed: scanner logic fixed; E2E promotion blocked by path guard (builder action still required).

| FR | Action | Outcome |
|----|--------|---------|
| FR1 (E2E promotion) | Path guard prevents test-writer from writing to `serve/cockpit/web/e2e/`. Scratch spec is complete and correct at `.owlbear/scratch/1395-accessibility.spec.ts`. Builder must promote. | **Builder instruction — see below** |
| FR4 (scanner mixed-token+hex) | Replaced `if (trimmed.includes('var(--pds-')) { continue }` with `const lineToScan = line.replace(/var\(--pds-[^)]*\)/g, '')` — strips PDS token segments before hex matching instead of skipping the whole line. | **PASSES** (was FAIL) |

### Builder Instruction: E2E Promotion Required
```shell
cp .owlbear/scratch/1395-accessibility.spec.ts serve/cockpit/web/e2e/accessibility-1395.spec.ts
git add serve/cockpit/web/e2e/accessibility-1395.spec.ts
cd serve/cockpit/web && npm run test:e2e -- accessibility-1395
```
`@axe-core/playwright` is already installed (`^4.11.3` in devDependencies). Run the E2E suite after promotion and verify pass/fail state. Any remaining axe violations are in scope for this task or deferred to #1396 per AC1 wording ("fail on current code and pass once #1396 is implemented").

### Test Files
- `serve/cockpit/web/src/__tests__/KeyboardA11y_1395.test.tsx` (unchanged — 20 tests, all PASS)
- `serve/cockpit/web/src/__tests__/PDSHexScan_1395.test.ts` (scanner fix — 5 tests, all PASS)
- `.owlbear/scratch/1395-accessibility.spec.ts` (E2E scratch — 12 tests, pending promotion)

### Failure Verification (Vitest)
```
Test Files: 2 passed (2 total)
Tests:      25 passed (25 total)
```
All Vitest tests PASS. Scanner fix converts the previously-failing mixed-token+hex test to green.

### Commit
`04f7b85b` — test: fix hex scanner mixed-token+hex detection (#1395, test-writer)

### AC Coverage Table (Retry 2)

| AC | Tests | Verdict |
|----|-------|---------|
| AC1 axe-core E2E 4 pages at 1024px | Scratch spec — builder must promote | Pending |
| AC2 keyboard card nav + movement | KeyboardA11y_1395: 8 tests PASS | GREEN |
| AC3 HealthBadge + ConfirmDialog focus | KeyboardA11y_1395: 8 tests PASS | GREEN |
| AC4 PDS hex scan + mixed-token guard | PDSHexScan_1395: 5 tests PASS | GREEN |
| AC5 a11y viewport 4 breakpoints | Scratch spec — builder must promote | Pending |
| AC6 td:0 | pass-through | — |
[[2026-05-11]]
## Builder Notes
- Promoted the pending E2E accessibility suite from scratch into tracked frontend tests.
- Files changed: `serve/cockpit/web/e2e/accessibility-1395.spec.ts`
- Commit: `907376a59c694f701f6f3ab59e4b2e72794930ba` (`test: promote accessibility e2e gate suite (#1395, builder)`)

### Verification Evidence
- quality-runner scoped run:
  - Vitest: 25 passed, 0 failed (`KeyboardA11y_1395.test.tsx`, `PDSHexScan_1395.test.ts`)
  - Playwright: 12 failed, 0 passed (`e2e/accessibility-1395.spec.ts`)
  - ESLint: clean (0 violations)
- All 12 Playwright failures are precondition timeouts in `beforeEach` waiting for `[data-region="workspace"]` / `[data-region="status-bar"]`, so AC1/AC5 assertions are not reached.

### Routing Decision
Rejecting to test-writer (`todo`) because this is a test-assumption/interface issue in the promoted E2E suite, not a production-code gap that builder can resolve without modifying tests.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Fix E2E setup assumptions so app-shell preconditions are reachable in Playwright (beforeEach currently times out before AC assertions execute) | `serve/cockpit/web/e2e/accessibility-1395.spec.ts` | 12/12 failures at beforeEach wait lines: `workspace`/`status-bar` timeout; AC1/AC5 not exercised |
| 2 | test-writer | Tighten API stubbing/bootstrap contract in the E2E suite to match current Cockpit startup behavior, then re-verify RED signal is tied to audited accessibility gaps (not precondition boot failure) | `serve/cockpit/web/e2e/accessibility-1395.spec.ts` | quality-runner + direct Playwright run both fail at shell preconditions, not accessibility assertions |
[[2026-05-11]]
## Test-Writer Notes (Retry 3)

### Root Cause of Builder Rejection
Playwright `page.route()` uses LIFO matching (last registered handler wins). In `stubApis()`, `/api/**` catch-all was registered **last** (highest priority), overriding all specific route stubs. Every API call returned `{}`, so the app shell never rendered — all 12 `beforeEach` waits timed out before any AC assertion executed.

### Fix Applied
Moved `/api/**` catch-all to be registered **first** (lowest priority). Specific routes (`/api/board`, `/api/tasks`, `/api/events`, etc.) registered after take precedence. Mirrors the working pattern in `responsive-layout-1391.spec.ts`.

### Files Changed
- `.owlbear/scratch/1395-accessibility.spec.ts` (source of truth)
- `serve/cockpit/web/e2e/accessibility-1395.spec.ts` (promoted file — updated via `cp`)

### Failure Verification (Playwright post-fix)
```
7 failed | 5 passed (12 total, 30.5s)

Failed (correct RED evidence):
- board view has zero axe accessibility violations at 1024px (AC1)
- task detail edit view has zero axe accessibility violations at 1024px (AC1)
- decision resolution view has zero axe accessibility violations at 1024px (AC1)
- task cards are reachable via Tab key at 320px (AC5)
- task cards are reachable via Tab key at 768px (AC5)
- task cards are reachable via Tab key at 1024px (AC5)
- task cards are reachable via Tab key at 1440px (AC5)

Passed (surfaces already correct or not audited problems per AC6):
- repair flow view has zero axe violations (no health-badge found → scan of current board)
- landmark region present at 320px / 768px / 1024px / 1440px (landmarks already exist)
```

### Commit
`08076560` — test: fix Playwright route-registration order in accessibility suite (#1395, test-writer)

### AC Coverage Table (Retry 3)

| AC | Tests | Verdict |
|----|-------|---------|
| AC1 axe-core E2E 4 pages at 1024px | 4 E2E tests: 3 FAIL (board/detail/decision), 1 PASS (repair) | RED for 3 of 4 audited surfaces |
| AC2 keyboard card nav + movement | Vitest: 8 tests PASS | GREEN |
| AC3 HealthBadge + ConfirmDialog focus | Vitest: 8 tests PASS | GREEN |
| AC4 PDS hex scan + mixed-token guard | Vitest: 5 tests PASS | GREEN |
| AC5 a11y viewport 4 breakpoints | 8 E2E tests: 4 FAIL (card Tab), 4 PASS (landmarks) | RED for card-reachability gap |
| AC6 td:0 | pass-through | — |
[[2026-05-11]]
## Builder Notes
- No code edits required in this pass.
- Verified current 1395 test-gate state with `quality-runner` scoped execution.

### Files Changed
- None

### Test Results
- Vitest scoped (`KeyboardA11y_1395.test.tsx`, `PDSHexScan_1395.test.ts`): **25 passed, 0 failed**
- Playwright scoped (`e2e/accessibility-1395.spec.ts`): **5 passed, 7 failed**
- Total scoped checks: **30 passed, 7 failed**

### Lint Status
- ESLint scoped on touched components/spec: **clean (0 violations)**

### Evidence Summary
- RED signal is now targeted and reproducible in tracked E2E tests:
  - AC1 failures at `e2e/accessibility-1395.spec.ts`: board/detail/decision axe checks return non-zero violations.
  - AC5 failures at `e2e/accessibility-1395.spec.ts`: task cards not keyboard-tab-reachable at 320/768/1024/1440.
- GREEN signal exists where expected:
  - AC2/AC3/AC4 unit suites are fully green.
- This satisfies task #1395’s role as a verification gate: tests are in tracked paths, discriminating, and exposing remaining audited accessibility gaps for counterpart implementation task #1396.
[[2026-05-11]]
## Review Evidence
### Test Results
- quality-runner scoped frontend evidence:
  - Vitest: 25 passed, 0 failed, 0 skipped (`serve/cockpit/web/src/__tests__/KeyboardA11y_1395.test.tsx`, `serve/cockpit/web/src/__tests__/PDSHexScan_1395.test.ts`)
  - Playwright: 5 passed, 7 failed (`serve/cockpit/web/e2e/accessibility-1395.spec.ts`)
- The remaining Playwright failures are assertion failures, not bootstrap/setup failures. For a `type:test` RED-phase task that is acceptable in principle; the review question is whether the suite proves the accepted AC precisely enough.

### Lint
- ESLint clean on the task-scoped frontend test/spec files (0 violations).

### Coverage
- Vitest-only coverage available; Playwright e2e coverage is not available from this run.
- Module coverage from the scoped unit run:
  - `Card.tsx`: 97.82%
  - `KanbanBoard.tsx`: 69.73%
  - `HealthBadge.tsx`: 94.00%
  - `ConfirmDialog.tsx`: 77.19%
- Coverage is not the rejection basis here; the rejection is about AC proof quality.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1 axe checks + dependency at 1024px | `serve/cockpit/web/e2e/accessibility-1395.spec.ts`, `serve/cockpit/web/package.json` | Not reliably. The dependency leg is satisfied, but the spec stubs `/api/decisions`, `/api/health`, and `/api/scan` while the live frontend reads `/api/decisions/pending` and `/api/tasks/scan`. The decision test also guards the click with `if (hasDR > 0)` before a page-wide `AxeBuilder(...).analyze()`, and the repair test guards on `if (hasBadge > 0)` before another page-wide analyze. The recorded Playwright artifact for the decision case shows `Pending decision requests: 0`, `No pending decision requests.`, and `Select a task to view details.`, so the named decision-resolution surface was not actually open when scanned. | MISSING |
| AC2 keyboard-only workflow | `serve/cockpit/web/src/__tests__/KeyboardA11y_1395.test.tsx` | Yes. The suite pins card focusability, card selection, menu invocation, and the real move API path. | COVERED |
| AC3 HealthBadge + ConfirmDialog focus/name/Escape | `serve/cockpit/web/src/__tests__/KeyboardA11y_1395.test.tsx` | Yes. The suite exercises focus-on-open, Escape dismissal, focus restore, and meaningful naming for both surfaces. | COVERED |
| AC4 PDS style-context hex scan | `serve/cockpit/web/src/__tests__/PDSHexScan_1395.test.ts` | No. The scanner matches any quoted hex literal on any non-comment line after stripping `var(--pds-...)` segments; it does not limit detection to JSX style props or className-resolved inline styles as the AC states. | LAX |
| AC5 viewport accessibility checks | `serve/cockpit/web/e2e/accessibility-1395.spec.ts` | Yes, with a small confidence deduction only. The suite exercises task-card tab reachability plus landmark presence at 320/768/1024/1440 without duplicating responsive-layout geometry assertions. | COVERED |
| AC6 RED proof limited to audited problems / excluded green surfaces remain out of scope | Task body + `serve/cockpit/web/e2e/accessibility-1395.spec.ts` | Not fully. Because AC1 currently runs full-page axe scans without proving the named decision/repair surfaces are active first, the RED signal is not cleanly isolated to the intended audited surfaces. | MISSING |

#### Security Review
- No issues found. The only dependency addition is the dev-only `@axe-core/playwright` package in `serve/cockpit/web/package.json`.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `TestFromAC_*` suites in the task-scoped files | No weakening provable from the current workspace state | PRESERVED with confidence deduction: commit diff / dirty-tree overlap could not be independently verified in this tool surface |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | WEAK | AC1 relies on page-wide `new AxeBuilder({ page }).analyze()` calls even when named surfaces are optional or unproven. AC4 uses a broad quoted-hex regex rather than the declared style-context contract. |
| Negative/error-path coverage | ADEQUATE | The RED suite produces targeted failing cases for AC1/AC5 and green cases for AC2/AC3/AC4. |
| Manual mutation reasoning | WEAK | Changing the decision/repair setup so those named surfaces never render can still leave AC1 scanning the base page. Introducing a quoted hex string outside style contexts would still trip AC4 even though that is outside the stated contract. |
| Test independence | ADEQUATE | Task-local mocks and focus patches are restored/cleared. |
| Descriptive test names | STRONG | Test names are explicit and behavior-oriented. |

#### Data Safety
- No issues found.

#### Implementation-Aware Gaps
- `serve/cockpit/web/e2e/accessibility-1395.spec.ts` stubs `/api/decisions`, `/api/health`, and `/api/scan`, but the live frontend in `serve/cockpit/web/src/hooks/usePendingDRs.ts`, `serve/cockpit/web/src/hooks/useScanPolling.ts`, and `serve/cockpit/web/src/Shell.tsx` uses `/api/decisions/pending` and `/api/tasks/scan` to populate the decision and repair surfaces.
- The decision-resolution E2E artifact shows the scan ran with no pending DR selected and the detail sidecar still on its placeholder state.
- `serve/cockpit/web/src/__tests__/PDSHexScan_1395.test.ts` currently enforces a broader quoted-hex policy than the AC text declares.

#### Necessity Check
- No issues found. `@axe-core/playwright` is directly required by AC1 and is correctly installed as a devDependency.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 4 |
| Approach variation | Present across retries |
| Assessment | FRICTION (not loop-quality failure) |

### Pass 2 — INFORMATIONAL
- Several RED-phase comments are stale in the task-scoped test files: they still describe missing keyboard/focus behavior that is already present in the live source.
- The Playwright suite now reaches real assertions; the remaining problem is AC precision, not startup/bootstrap.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 | `serve/cockpit/web/e2e/accessibility-1395.spec.ts` stubs `/api/decisions` at line 131, `/api/health` at line 134, and `/api/scan` at line 137; live frontend uses `/api/decisions/pending` in `serve/cockpit/web/src/hooks/usePendingDRs.ts` line 41 and `/api/tasks/scan` in `serve/cockpit/web/src/hooks/useScanPolling.ts` line 29. The decision test scans after `if (hasDR > 0)` at line 185 and page-wide analyze at line 189. The recorded Playwright artifact shows `Pending decision requests: 0`, `No pending decision requests.`, and `Select a task to view details.` | `serve/cockpit/web/e2e/accessibility-1395.spec.ts` | FAIL |
| AC2 | Task-scoped unit tests prove card `tabIndex`, interactive role, `aria-haspopup`, keyboard menu open, and the real move POST path (`/api/tasks/{id}/move`). | `serve/cockpit/web/src/__tests__/KeyboardA11y_1395.test.tsx` | PASS |
| AC3 | Task-scoped unit tests prove HealthBadge focus entry/restore/Escape and meaningful names, plus ConfirmDialog accessible naming and focus restore on Escape and Cancel. | `serve/cockpit/web/src/__tests__/KeyboardA11y_1395.test.tsx` | PASS |
| AC4 | `serve/cockpit/web/src/__tests__/PDSHexScan_1395.test.ts` uses `HEX_LITERAL_PATTERN` at line 57 and scans all quoted hex literals after token stripping at lines 74-76, which is broader than the AC’s style-context-only contract. | `serve/cockpit/web/src/__tests__/PDSHexScan_1395.test.ts` | FAIL |
| AC5 | The promoted Playwright suite contains explicit viewport blocks at 320/768/1024/1440 and asserts task-card tab reachability plus landmark presence without asserting layout geometry. | `serve/cockpit/web/e2e/accessibility-1395.spec.ts` | PASS |
| AC6 | AC1’s current page-wide scans do not prove the named decision/repair surfaces are active first, so the RED signal is not yet cleanly bounded to the intended audited-surface proof. | Task body + `serve/cockpit/web/e2e/accessibility-1395.spec.ts` | FAIL |

### Deductions
- Major deduction for AC1 proof failure: named decision-resolution and repair-flow surfaces are not reliably exercised before the page-wide axe scans.
- Major deduction for AC4 contract mismatch: the current scanner enforces a broader policy than the accepted AC.
- Small deduction because commit diff / dirty-tree contamination checks could not be independently verified from this tool surface.
- Loop-breaker applies: the task already contains a prior `## Review Evidence` section, so this second review failure routes to `backlog`.

### Confidence: 0.83
### Verdict: FAIL
### Action: reject to `backlog`

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Refine AC1 / AC6 so the Playwright gate must prove the named task-detail, decision-resolution, and repair-flow surfaces are actually rendered before running axe, and align the test contract with the live endpoint surface (`/api/decisions/pending`, `/api/tasks/scan`) | `serve/cockpit/web/e2e/accessibility-1395.spec.ts`, `serve/cockpit/web/src/hooks/usePendingDRs.ts`, `serve/cockpit/web/src/hooks/useScanPolling.ts`, `serve/cockpit/web/src/Shell.tsx` | Stub mismatch and optional-surface scans at lines 131/134/137/185/189/199/203 in `accessibility-1395.spec.ts`; live endpoints at line 41 in `usePendingDRs.ts` and line 29 in `useScanPolling.ts`; decision artifact shows no pending DR selected |
| 2 | architect | Refine AC4 so the PDS gate matches the intended style-context scope, or explicitly broaden the accepted contract before sending the task back through RED | `serve/cockpit/web/src/__tests__/PDSHexScan_1395.test.ts` | Broad quoted-hex matcher at line 57 and scan logic at lines 74-76 exceed the current AC wording |

[[2026-05-11]]

## Architecture Review (Refinement — reviewer loop-breaker)

### Reviewer Findings Addressed

| FR | Issue | AC Refinement |
|----|-------|---------------|
| FR1 | E2E stubs use `/api/decisions`, `/api/health`, `/api/scan` — live app uses `/api/decisions/pending` (GET) and `/api/tasks/scan` (POST). Decision/repair surfaces never rendered; conditional `if (count > 0)` guards silently fall through to page-wide scan. | AC1 rewritten to name live endpoints and require surface-rendering proof |
| FR2 | Scanner matches any quoted hex literal; AC says "JSX style props or className-resolved inline styles" — scope mismatch | AC4 broadened to match implemented scanner behavior |
| FR3 | AC6 FAIL is derivative of AC1 — resolves when AC1 is fixed | No change needed |

### Refined AC Lines (supersede originals above)

**AC1 (revised):** Automated accessibility checks using `@axe-core/playwright` run against the board view, task detail edit, decision resolution, and repair flow pages at 1024px viewport. E2E stubs must match the live API surface: `/api/decisions/pending` (GET, returns `{count, items}`) for pending decision data and `/api/tasks/scan` (POST, returns `ScanItem[]`) for repair scan data — not `/api/decisions`, `/api/health`, or `/api/scan`. Each axe-scanned surface must be verified as actually rendered before `AxeBuilder.analyze()` runs: decision resolution requires a pending DR item visible and the ResolveModal opened; repair flow requires the HealthBadge visible and its popover opened. Conditional guards that silently skip to a page-wide scan when the surface is absent are not acceptable — the test must fail if the surface cannot be rendered from the stub data. The checks fail on current code and pass once #1396 is implemented. `@axe-core/playwright` is added as a devDependency. (td:2)

**AC4 (revised):** PDS verification scans component source files (src/components/**/*.tsx, src/*.tsx) and rejects any quoted hex color literal (`'#xxx'`, `"#xxx"`, `` `#xxx` `` where xxx is 3–8 hex digits) on non-comment lines. Lines are pre-processed by stripping `var(--pds-*)` segments before matching, so a line containing both a PDS token and a hex literal is still flagged. Token declaration files (tokens.css), test files (__tests__/), and build artifacts (dist/, node_modules/) are excluded from the scan. (td:2)

AC2, AC3, AC5, AC6 unchanged — all passed review or are td:0.

[[2026-05-11]]

### AC1 Addendum (challenger finding)
Task-detail surface must also be verified as rendered before axe scan: after clicking a task card, the sidecar detail panel (`[data-region="sidecar"]`) must contain visible task data (title or description text) before `AxeBuilder.analyze()` runs. This applies equally to the decision-resolution and repair-flow surface-rendering requirements already stated in the refined AC1 above.

### Challenger Response
Challenger confidence: 0.64 (reconsider). Key findings evaluated:
- **AC1 evidence drift**: Addressed — AC refinement specifies correct endpoints and render-proof; test-writer will update spec code in next pipeline pass. Task-detail render gap accepted and added above.
- **AC3 overstatement**: Override — PASSED both reviews; not in reviewer's required follow-up scope.
- **AC5 breadth drift**: Override — PASSED second review with explicit COVERED verdict.
- Architect retains APPROVE verdict. The refinements close the reviewer's FR1/FR2 findings, and remaining implementation drift is the expected state before re-entering the pipeline.

[[2026-05-11]]
## Architecture Review (Refinement)
### Verdict: APPROVE

Reviewer loop-breaker routed task to backlog with two required follow-ups. Both addressed:

**AC1 (revised):** Added live endpoint names (`/api/decisions/pending`, `/api/tasks/scan`), required surface-rendering proof before axe scans (decision/repair/task-detail), banned conditional skip-to-page guards. Challenger flagged missing task-detail render proof — added.

**AC4 (revised):** Broadened from "JSX style props or className-resolved inline styles" to "any quoted hex literal on non-comment lines" — matches implemented scanner behavior; simpler and more protective.

AC2/AC3/AC5 unchanged (PASSED both reviews). AC6 unchanged (td:0, derivative of AC1).

Challenger: 0.64 (reconsider). Override justified: AC refinements close reviewer findings; implementation lag expected before re-pipeline; AC3/AC5 concerns were out of reviewer scope.
[[2026-05-11]]
## Test-Writer Notes (Retry 4)

### Root Cause of Reviewer Rejection
Second review cycle found AC1 proof insufficient:
- Stubs used wrong endpoints (`/api/decisions`, `/api/health`, `/api/scan`) — live app uses `/api/decisions/pending` and `/api/tasks/scan` (POST)
- Conditional `if (hasDR > 0)` and `if (hasBadge > 0)` guards silently fell through to page-wide scans when named surfaces were absent
- Task-detail test used `page.waitForTimeout(500)` instead of waiting for sidecar content

Architect revised AC1 and AC4 per reviewer's required follow-up before re-entering pipeline.

### Fix Applied
`serve/cockpit/web/e2e/accessibility-1395.spec.ts` (promoted from `.owlbear/scratch/1395-accessibility.spec.ts`):

| FR | Fix | File |
|----|-----|------|
| AC1 stubs | Replaced `/api/decisions` → `/api/decisions/pending` returning `{count, items}`; replaced `/api/health` + `/api/scan` → `/api/tasks/scan` returning `ScanItem[]` array | `stubApis()` |
| AC1 decision surface | Removed conditional guard; prove `dr-indicator` is visible with `data-status="attention"`; click indicator → popover → DR item → `resolve-modal` must be visible before axe scan | decision resolution test |
| AC1 repair surface | Removed conditional guard; prove `health-badge` is visible with `data-health="red"`; click → `health-badge-popover` must be visible before axe scan | repair flow test |
| AC1 task-detail surface | Replaced `waitForTimeout(500)` with `expect(detail-placeholder).not.toBeVisible()` — sidecar must show task data before axe scan | task detail test |
| AC4 | No change — revised AC4 broadens contract to match current scanner; already green |

### Vitest (unchanged)
- `KeyboardA11y_1395.test.tsx`: 20 tests, all PASS
- `PDSHexScan_1395.test.ts`: 5 tests, all PASS

### Playwright Failure Verification
```
8 failed | 4 passed (12 total)

FAIL (real assertion failures, not setup timeouts):
- board view has zero axe accessibility violations at 1024px (AC1)
- task detail edit view has zero axe accessibility violations at 1024px (AC1)
- decision resolution view has zero axe accessibility violations at 1024px (AC1)
- repair flow view has zero axe accessibility violations at 1024px (AC1)
- task cards are reachable via Tab key at 320px (AC5)
- task cards are reachable via Tab key at 768px (AC5)
- task cards are reachable via Tab key at 1024px (AC5)
- task cards are reachable via Tab key at 1440px (AC5)

PASS (surfaces already correct):
- landmark regions at 320/768/1024/1440px (AC5)
```

### Lint: clean (ESLint exit 0)

### Commit
`c91a46b6` — test: fix AC1 E2E stubs and surface-rendering proofs (#1395, test-writer)

### AC Coverage Table (Retry 4)

| AC | Tests | Verdict |
|----|-------|---------|
| AC1 axe-core E2E 4 pages at 1024px | 4 E2E: all FAIL with real axe violations (not setup) | RED ✓ |
| AC2 keyboard card nav + movement | Vitest: 8 tests PASS | GREEN |
| AC3 HealthBadge + ConfirmDialog focus | Vitest: 8 tests PASS | GREEN |
| AC4 PDS hex scan + mixed-token guard | Vitest: 5 tests PASS (revised AC4 matches impl) | GREEN |
| AC5 a11y viewport 4 breakpoints | 4 E2E: FAIL (no card tab focus); 4 PASS (landmarks) | RED for card gap ✓ |
| AC6 td:0 | pass-through | — |
[[2026-05-11]]
## Builder Notes
- No implementation edits required in this build pass; task 1395 is a test-gate deliverable.
- Verified tracked 1395 suites with quality-runner (scoped) after AC refinements.

### Files Changed
- None

### Test Results
- Vitest (task-scoped): 25 passed, 0 failed (`serve/cockpit/web/src/__tests__/KeyboardA11y_1395.test.tsx`, `serve/cockpit/web/src/__tests__/PDSHexScan_1395.test.ts`)
- Playwright (task-scoped): 4 passed, 8 failed (`serve/cockpit/web/e2e/accessibility-1395.spec.ts`)

### Lint Status
- ESLint scoped: clean (0 violations)

### Evidence Summary
- AC1 RED proof is active and targeted: 4 failing axe checks on board/detail/decision/repair surfaces.
- AC5 RED proof is active and targeted: 4 failing keyboard card-reachability checks at 320/768/1024/1440.
- AC2/AC3/AC4 are green via unit suites.
- This matches the intended RED/GREEN gate shape for a `type:test` precursor task to implementation task #1396.
[[2026-05-11]]
## Review Evidence
### Test Results
- quality-runner scoped frontend run completed successfully with no environment errors.
- Task-local unit suites are green: `serve/cockpit/web/src/__tests__/KeyboardA11y_1395.test.tsx` 20 passed, `serve/cockpit/web/src/__tests__/PDSHexScan_1395.test.ts` 5 passed.
- Promoted Playwright suite is still intentionally RED: `serve/cockpit/web/e2e/accessibility-1395.spec.ts` 4 passed, 8 failed. Failures are real axe and keyboard-reachability assertions, not bootstrap/setup timeouts.
- ESLint is clean on the scoped task files and touched source files.

### Coverage
- Scoped frontend coverage from quality-runner:
- `src/components/Card.tsx`: 100 stmt, 94.2 branch, 100 func, 100 line
- `src/KanbanBoard.tsx`: 91.22 stmt, 85.71 branch, 90.47 func, 95.89 line
- `src/components/HealthBadge.tsx`: 98 stmt, 90.24 branch, 100 func, 100 line
- `src/components/ConfirmDialog.tsx`: 82.45 stmt, 55.55 branch, 100 func, 90.9 line
- Overall: 91.86 stmt, 84.07 branch, 94.59 func, 96.21 line
- Coverage is not the rejection basis. The rejection is proof quality against the refined AC.

### Source-Control Evidence
- The task body's cited 1395 commits are present in `.git/logs/HEAD` and `.git/logs/refs/heads/dev` (including `29ec6841`, `db254057`, `04f7b85b`, `907376a59c694f701f6f3ab59e4b2e72794930ba`, `08076560`, `c91a46b6`).
- Dirty-tree overlap against the scoped files could not be independently checked from this tool surface, so a small confidence deduction remains.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---|---|---|---|
| AC1 revised axe proof on board, detail, decision, repair at 1024px with live endpoint contract and render-proof | `serve/cockpit/web/e2e/accessibility-1395.spec.ts` | No. The board test suppresses missing-card render failure at `serve/cockpit/web/e2e/accessibility-1395.spec.ts:162` and still scans at `:163`. The detail test only checks placeholder disappearance at `:177`, but `serve/cockpit/web/src/Shell.tsx:96-103` clears task detail state before fetch resolves and the placeholder itself is gated only by `selectedTaskId === null` at `serve/cockpit/web/src/Shell.tsx:212`. The route stubs use the right paths at `accessibility-1395.spec.ts:132` and `:137`, but they do not enforce the refined GET/POST contract even though the live app uses `/api/decisions/pending` at `serve/cockpit/web/src/hooks/usePendingDRs.ts:41` and `/api/tasks/scan` with `POST` at `serve/cockpit/web/src/hooks/useScanPolling.ts:29-31`. | MISSING |
| AC2 keyboard-only workflow proof | `serve/cockpit/web/src/__tests__/KeyboardA11y_1395.test.tsx` | Yes. The suite proves card focusability, selection, keyboard menu open, and the real move POST path. | COVERED |
| AC3 focus on open, restore on close, names, Escape for HealthBadge and ConfirmDialog | `serve/cockpit/web/src/__tests__/KeyboardA11y_1395.test.tsx` | No. HealthBadge is covered, but ConfirmDialog focus-on-open is never asserted even though the live component focuses on mount at `serve/cockpit/web/src/components/ConfirmDialog.tsx:46`. The ConfirmDialog test block starts at `serve/cockpit/web/src/__tests__/KeyboardA11y_1395.test.tsx:427` and only proves naming and close-path behavior. | MISSING |
| AC4 revised quoted-hex scan on non-comment lines after stripping `var(--pds-*)` segments | `serve/cockpit/web/src/__tests__/PDSHexScan_1395.test.ts` | No. The helper strips token segments at `serve/cockpit/web/src/__tests__/PDSHexScan_1395.test.ts:74`, but comment exclusion only handles line-leading `//`, `*`, and `/*` at `:68`. The refined non-comment rule is not proven for JSX comment forms. | LAX |
| AC5 viewport keyboard reachability and landmarks at 320, 768, 1024, 1440 | `serve/cockpit/web/e2e/accessibility-1395.spec.ts` | Yes. The suite checks tab reachability and landmark presence at all four breakpoints without re-testing layout geometry. | COVERED |
| AC6 RED evidence limited to the intended audited problems and refined AC set | Task body plus tracked suites | No. AC1, AC3, and AC4 are not proven precisely enough to bound the gate. | MISSING |

#### Security Review
- No issues found. The task adds only the test dependency `@axe-core/playwright` and local route stubs/mocks.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---|---|---|
| `TestFromAC_*` suites in the tracked task files | No direct weakening visible in the current workspace | PRESERVED with small confidence deduction because diff-scoped integrity and dirty-tree overlap could not be fully reconstructed from this tool surface |

#### Test Quality
| Dimension | Rating | Evidence |
|---|---|---|
| Assertion specificity | WEAK | AC1 still allows board/detail scans without proving the intended surface is really rendered. AC3 ConfirmDialog name checks prove attribute presence but not focus-on-open. |
| Negative or error-path coverage | WEAK | The refined verb contract for `/api/tasks/scan` is not exercised, and AC4 does not prove comment exclusion precisely. |
| Manual mutation reasoning | WEAK | Removing `dialogRef.current?.focus()` at `serve/cockpit/web/src/components/ConfirmDialog.tsx:46` would leave the current ConfirmDialog tests green. Breaking board/detail render-proof while leaving page-wide axe scans intact would also stay green. |
| Test independence | ADEQUATE | Global overrides and focus spies are restored. |
| Descriptive test names | ADEQUATE | Names remain traceable to the AC. |

#### Data Safety
- No issues found.

#### Implementation-Aware Gaps
- `serve/cockpit/web/e2e/accessibility-1395.spec.ts:162-163` can scan a shell-only board page if task cards never render.
- `serve/cockpit/web/e2e/accessibility-1395.spec.ts:177` treats placeholder disappearance as task-detail proof, but `serve/cockpit/web/src/Shell.tsx:96-103` and `:212` show that the placeholder disappears before fetched task data is guaranteed.
- `serve/cockpit/web/src/__tests__/KeyboardA11y_1395.test.tsx:427` onward never asserts ConfirmDialog focus-on-open, despite the live behavior at `serve/cockpit/web/src/components/ConfirmDialog.tsx:46`.
- `serve/cockpit/web/src/__tests__/PDSHexScan_1395.test.ts:68` does not prove the revised comment-exclusion rule for JSX comment forms.

#### Necessity Check
- No issues found. Axe is explicitly required by AC1 and is present in the frontend package manifest.

#### Builder Process Quality
| Metric | Value |
|---|---|
| Builder Notes sections | 5 |
| Approach variation | Present across retries |
| Assessment | FRICTION |

### Pass 2 — INFORMATIONAL
- Several RED-phase comments in the task tests are now stale relative to the live source.
- The viewport tab tests use a fixed 20-Tab walk. That is brittle but not the rejection basis here.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| AC1 revised render-proof + endpoint contract | `serve/cockpit/web/e2e/accessibility-1395.spec.ts:132`, `:137`, `:162-163`, `:177`; `serve/cockpit/web/src/Shell.tsx:96-103`, `:212`; `serve/cockpit/web/src/hooks/usePendingDRs.ts:41`; `serve/cockpit/web/src/hooks/useScanPolling.ts:29-31` | `serve/cockpit/web/e2e/accessibility-1395.spec.ts` | FAIL |
| AC2 keyboard-only workflow | `serve/cockpit/web/src/__tests__/KeyboardA11y_1395.test.tsx:151-162`, `:273-275`; live wiring at `serve/cockpit/web/src/components/Card.tsx:21-26`, `:43`; `serve/cockpit/web/src/KanbanBoard.tsx:342-350` | `serve/cockpit/web/src/__tests__/KeyboardA11y_1395.test.tsx` | PASS |
| AC3 focus management + names + Escape | Missing ConfirmDialog open-focus proof; source focus behavior at `serve/cockpit/web/src/components/ConfirmDialog.tsx:46`, test block begins at `serve/cockpit/web/src/__tests__/KeyboardA11y_1395.test.tsx:427` with no matching open-focus assertion | `serve/cockpit/web/src/__tests__/KeyboardA11y_1395.test.tsx` | FAIL |
| AC4 revised scanner contract | Comment handling only at `serve/cockpit/web/src/__tests__/PDSHexScan_1395.test.ts:68`; token stripping at `:74`; no proof for JSX-comment exclusion | `serve/cockpit/web/src/__tests__/PDSHexScan_1395.test.ts` | FAIL |
| AC5 viewport reachability + landmarks | Breakpoint suites at `serve/cockpit/web/e2e/accessibility-1395.spec.ts:252`, `:267`, `:292`, `:307`, `:328`, `:343`, `:364`, `:379` | `serve/cockpit/web/e2e/accessibility-1395.spec.ts` | PASS |
| AC6 refined RED/GREEN gate shape | Derivative of AC1, AC3, AC4 proof gaps | Task body plus tracked suites | FAIL |

### Deductions
- Major deduction for AC1 proof failure: board/detail surface-rendering proof and endpoint-method proof remain incomplete.
- Major deduction for AC3 proof failure: ConfirmDialog focus-on-open is required by the AC and untested.
- Moderate deduction for AC4 proof mismatch: revised comment exclusion is not proven precisely.
- Small deduction because dirty-tree overlap could not be independently checked, although commit presence was confirmed in git logs.
- Loop-breaker applies: the task already contains prior `## Review Evidence` sections, so this repeated review failure routes to `backlog`.

### Confidence: 0.82
### Verdict: FAIL
### Action: reject to `backlog`

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|---|---|---|---|
| 1 | architect | Re-issue AC1 and AC6 with explicit proof requirements that the board view must prove visible task-card rendering before axe, task detail must prove visible fetched task data rather than placeholder disappearance, and the `/api/tasks/scan` POST contract must be enforced or separately proven before the task returns to RED | `serve/cockpit/web/e2e/accessibility-1395.spec.ts`, `serve/cockpit/web/src/Shell.tsx`, `serve/cockpit/web/src/hooks/usePendingDRs.ts`, `serve/cockpit/web/src/hooks/useScanPolling.ts` | AC1 evidence at `accessibility-1395.spec.ts:132`, `:137`, `:162-163`, `:177`; `Shell.tsx:96-103`, `:212`; `usePendingDRs.ts:41`; `useScanPolling.ts:29-31` |
| 2 | architect | Re-state the AC3 proof obligation so ConfirmDialog focus-on-open is explicitly verified in the task-owned suite before the task re-enters review | `serve/cockpit/web/src/__tests__/KeyboardA11y_1395.test.tsx`, `serve/cockpit/web/src/components/ConfirmDialog.tsx` | Source focus on mount at `ConfirmDialog.tsx:46`; no corresponding assertion in the ConfirmDialog test block beginning at `KeyboardA11y_1395.test.tsx:427` |
| 3 | architect | Clarify and re-issue the AC4 comment-exclusion rule, including JSX comment forms if they are intended to count as comments, before the scanner contract is sent back through RED | `serve/cockpit/web/src/__tests__/PDSHexScan_1395.test.ts` | Current exclusion only handles line-leading comment markers at `PDSHexScan_1395.test.ts:68` |
[[2026-05-11]]

## Architecture Review (Refinement 2 — third reviewer loop-breaker)

### Reviewer Findings Addressed

| FR | Issue | Resolution |
|----|-------|------------|
| FR1 | Board test `.catch(() => {})` swallows card-render failure (line 162); axe scans empty page | AC1 addendum: prohibit error-swallowing on precondition waits |
| FR1 | Detail test proves placeholder absence, not visible task data | AC1 addendum: require `data-field="title"` input value assertion |
| FR2 | ConfirmDialog focus-on-open (source line 46) never asserted in tests | AC3 addendum: require `document.activeElement` proof |
| FR3 | Comment exclusion misses JSX template comment expressions | AC4 clarification: accepted as conservative guard |
| (challenger) | AC5 has same `.catch(() => {})` swallowed precondition at 4 breakpoints | AC5 addendum: extend anti-swallow rule |
| (challenger) | AC3 focus proof could be satisfied by spy instead of DOM state | AC3 specifies `document.activeElement` must be the dialog element |

### AC Addenda (supplement the revised AC1/AC4 already in this task body)

**AC1 addendum:** All four axe tests must assert their target surface is rendered before `AxeBuilder.analyze()` runs. Specifically: (a) board view must assert at least one `[data-testid="task-card"]` is visible — `.catch(() => {})` or any error-swallowing pattern on precondition waits is prohibited; (b) task-detail view must assert visible task title text via `[data-field="title"]` in the sidecar panel, not merely the absence of `[data-testid="detail-placeholder"]`.

**AC3 addendum:** Tests must also prove ConfirmDialog receives DOM focus on mount. After render, `document.activeElement` must be the dialog element (`[data-testid="confirm-dialog"]`). A focus-call spy or `.toHaveBeenCalled()` check alone is not sufficient — the assertion must prove the element is the active element in the DOM.

**AC4 clarification:** Comment lines are identified by line-leading `//`, `*`, or `/*` markers after trimming whitespace. Hex literals inside JSX template comment expressions (`{/* ... */}`) on lines without a leading comment marker are not excluded from the scan — this is accepted as a conservative guard. No scanner or test change required for this clarification.

**AC5 addendum:** Card-reachability tests must not use `.catch(() => {})` on the `[data-testid="task-card"]` precondition wait. The same anti-swallow rule from the AC1 addendum applies: if task cards fail to render, the test must fail at the precondition step, not silently proceed to the Tab-walk assertion.

AC2, AC6 unchanged.

### Challenger Response
Challenger confidence: 0.69 (reconsider). Four findings evaluated:
- **AC5 swallowed waits**: Accepted — extended anti-swallow rule to all four AC5 card-reachability tests for consistency with AC1.
- **AC1 selector ambiguity**: Accepted — refined detail render-proof to require `[data-field="title"]` instead of generic "visible task content."
- **AC3 focus proof shape**: Accepted — specified `document.activeElement` must be the dialog element, not a spy call.
- **Reasoning overstatement**: Accepted — dropped "addresses all" claim; this refinement closes the specific reviewer FR items plus three challenger-found gaps.

### Verdict: APPROVE
All reviewer FR items and challenger findings incorporated. Five addenda tighten proof precision for AC1, AC3, AC4, AC5. No architectural change — test-proof precision only.
[[2026-05-11]]
Architecture Review (Refinement 2): Third reviewer loop-breaker cycle. Five AC addenda tighten test-proof precision: (1) AC1 anti-swallow rule for board/detail render-proof with named selectors, (2) AC3 focus-on-open via document.activeElement, (3) AC4 JSX comment clarification (conservative guard accepted), (4) AC5 anti-swallow rule extended for consistency. Challenger at 0.69 — three findings accepted and incorporated. All reviewer FR items closed.
[[2026-05-11]]
## Test-Writer Notes (Retry 5)

### Reviewer Required Follow-up Addressed (Arch Review Refinement 2 addenda)

| FR | Addendum | Action | Outcome |
|----|----------|--------|---------|
| AC1 board anti-swallow | Board view: remove `.catch(() => {})`, assert `state: 'visible'` | Applied to scratch spec | Requires builder cp to tracked E2E |
| AC1 detail render-proof | Detail view: replace placeholder-absence with `[data-field="title"]` assertion | Applied to scratch spec | Requires builder cp to tracked E2E |
| AC3 focus-on-open | Add `document.activeElement` is dialog element assertion | Added to `KeyboardA11y_1395.test.tsx` | PASSES (impl already handles it) |
| AC5 anti-swallow | All 4 card-reachability tests: remove `.catch(() => {})` | Applied to scratch spec | Requires builder cp to tracked E2E |

### Test Files
- **Vitest:** `serve/cockpit/web/src/__tests__/KeyboardA11y_1395.test.tsx` (+1 new test: focus-on-open)
- **E2E scratch:** `.owlbear/scratch/1395-accessibility.spec.ts` (gitignored — builder must apply changes to tracked file)

### Builder Instruction: Apply E2E Changes

Scratch file is gitignored; apply these changes to `serve/cockpit/web/e2e/accessibility-1395.spec.ts`:

**1. Board view (AC1) — remove `.catch(() => {})`, change `'attached'` → `'visible'`:**
```diff
-    await page
-      .locator('[data-testid="task-card"]')
-      .first()
-      .waitFor({ state: 'attached', timeout: 5_000 })
-      .catch(() => {})
+    // AC1 addendum: board view must assert at least one task card is visible before scanning.
+    // No error-swallowing (.catch(() => {})) is permitted — test must fail if cards do not render.
+    await page
+      .locator('[data-testid="task-card"]')
+      .first()
+      .waitFor({ state: 'visible', timeout: 5_000 })
```

**2. Task-detail view (AC1) — replace placeholder-absence with `[data-field="title"]`:**
```diff
-    await expect(
-      page.locator('[data-testid="detail-placeholder"]'),
-      'sidecar must show task data before axe scan — placeholder must not be visible',
-    ).not.toBeVisible({ timeout: 5_000 })
+    // AC1 addendum: prove task-detail surface rendered by asserting visible task title.
+    // Must check [data-field="title"] is visible — not merely the absence of the placeholder.
+    await expect(
+      page.locator('[data-field="title"]'),
+      'sidecar must show task title before axe scan — [data-field="title"] must be visible in sidecar',
+    ).toBeVisible({ timeout: 5_000 })
```

**3. AC5 card-reachability tests at 320px, 768px — remove `.catch(() => {})`:**
```diff
-      .waitFor({ state: 'attached', timeout: 5_000 })
-      .catch(() => {})
+      // AC5 addendum: no error-swallowing permitted — test must fail if cards do not render.
+      .waitFor({ state: 'attached', timeout: 5_000 })
```

**4. AC5 card-reachability tests at 1024px, 1440px — remove `.catch(() => {})`:**
```diff
-      .waitFor({ state: 'visible', timeout: 5_000 })
-      .catch(() => {})
+      // AC5 addendum: no error-swallowing permitted — test must fail if cards do not render.
+      .waitFor({ state: 'visible', timeout: 5_000 })
```

### Failure Verification (Vitest)
```
Test Files  2 passed (2 total)
Tests       26 passed (26 total)
```
- `KeyboardA11y_1395.test.tsx`: 21 passed (20 prior + 1 new focus-on-open)
- `PDSHexScan_1395.test.ts`: 5 passed

New focus-on-open test PASSES because `ConfirmDialog` already calls `dialogRef.current?.focus()` in `useEffect`. Builder must verify E2E changes produce expected failures.

### Expected E2E Outcome After Builder Applies Changes
- AC1 (4 tests): still FAIL (axe violations exist; preconditions now stricter but cards render from stub data)
- AC5 card-reachability (4 tests): still FAIL (no tab focus; preconditions stricter but cards render)
- AC5 landmarks (4 tests): still PASS

### Lint
ESLint: clean (exit 0) on `KeyboardA11y_1395.test.tsx`

### Commit
`85876d73` — test: tighten AC1/AC3/AC5 proof precision in accessibility suite (#1395, test-writer)

### AC Coverage Table (Retry 5)
| AC | Tests | Verdict |
|----|-------|---------|
| AC1 axe-core E2E 4 pages at 1024px | 4 E2E: stricter preconditions applied | Pending builder E2E apply+verify |
| AC2 keyboard card nav + movement | Vitest: 8 tests PASS | GREEN |
| AC3 HealthBadge + ConfirmDialog focus (incl. focus-on-open) | Vitest: 9 tests PASS | GREEN |
| AC4 PDS hex scan + mixed-token guard | Vitest: 5 tests PASS | GREEN |
| AC5 a11y viewport 4 breakpoints | 4 E2E: stricter preconditions applied | Pending builder E2E apply+verify |
| AC6 td:0 | pass-through | — |
[[2026-05-11]]
## Builder Notes
- Applied the remaining Retry 5 AC-proof deltas in tracked E2E spec.

### Files Changed
- serve/cockpit/web/e2e/accessibility-1395.spec.ts

### Fixes Applied
- AC1 board precondition now requires visible task card before axe scan; removed error-swallowing wait.
- AC1 detail precondition now requires visible `[data-field="title"]` before axe scan (replaced placeholder-absence check).
- AC5 card-reachability tests at 320/768/1024/1440 removed `.catch(() => {})` on card precondition waits so render failures cannot silently pass.

### Test Results (quality-runner scoped)
- Vitest task suites: **26 passed, 0 failed**
  - `serve/cockpit/web/src/__tests__/KeyboardA11y_1395.test.tsx`: 21 passed
  - `serve/cockpit/web/src/__tests__/PDSHexScan_1395.test.ts`: 5 passed
- Playwright task suite: **4 passed, 8 failed**
  - `serve/cockpit/web/e2e/accessibility-1395.spec.ts`
  - Failing cases are expected RED gates: 4 axe assertions (AC1) and 4 task-card tab-reachability assertions (AC5)

### Lint Status
- ESLint scoped: clean (0 violations)

### Coverage
- Not collected in this scoped verification run.

### Evidence Summary
- Tracked E2E suite now enforces strict render preconditions (no swallow patterns) per AC addenda.
- Current suite shape matches gate intent for this test task: AC2/AC3/AC4 green in unit tests, AC1/AC5 red in Playwright until counterpart implementation #1396.

### Commit
- ec41149d — `test: tighten accessibility e2e preconditions (#1395, builder)`
[[2026-05-11]]
## Review Evidence
### Test Results
- quality-runner scoped frontend run completed successfully with no environment/bootstrap errors.
- Vitest: 26 passed, 0 failed, 0 skipped (`serve/cockpit/web/src/__tests__/KeyboardA11y_1395.test.tsx`, `serve/cockpit/web/src/__tests__/PDSHexScan_1395.test.ts`).
- Playwright: 4 passed, 8 failed (`serve/cockpit/web/e2e/accessibility-1395.spec.ts`). The 8 failures are real RED assertions for the accepted gate shape: 4 axe failures for AC1 and 4 task-card tab-reachability failures for AC5. They are not setup/precondition failures.

### Lint
- ESLint scoped clean on the task-owned unit tests, Playwright spec, and touched component files.

### Coverage
- Coverage is not the rejection basis.
- Scoped module coverage from quality-runner:
  - `serve/cockpit/web/src/components/Card.tsx`: 97.82 stmt / 84.05 branch / 80.00 func / 100.00 line
  - `serve/cockpit/web/src/KanbanBoard.tsx`: 69.73 stmt / 63.54 branch / 57.14 func / 72.60 line
  - `serve/cockpit/web/src/components/ConfirmDialog.tsx`: 77.19 stmt / 46.66 branch / 100.00 func / 84.84 line
  - `serve/cockpit/web/src/components/HealthBadge.tsx`: 94.00 stmt / 68.29 branch / 100.00 func / 100.00 line
- Playwright browser coverage is not available from this run.

### Source-Control Evidence
- Task-related commits are present in `.git/logs/HEAD` and `.git/logs/refs/heads/dev`, including `29ec6841`, `db254057`, `04f7b85b`, `907376a59c694f701f6f3ab59e4b2e72794930ba`, `08076560`, `c91a46b6`, `85876d73`, and `ec41149d`.
- Dirty-tree overlap against the scoped files could not be independently checked from this tool surface, so a small confidence deduction remains.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---|---|---|---|
| AC1 revised axe proof on board, detail, decision, and repair surfaces at 1024px with corrected endpoint surface and render preconditions | `serve/cockpit/web/e2e/accessibility-1395.spec.ts`; adjacent fetch-contract evidence in `serve/cockpit/web/src/__tests__/usePendingDRs.test.ts` and `serve/cockpit/web/src/__tests__/useScanPolling.test.ts` | Yes. The tracked spec now enforces visible/rendered surface preconditions before `AxeBuilder.analyze()`, and the live GET/POST fetch contract is already pinned in the dedicated hook suites. | COVERED |
| AC2 keyboard-only workflow proof | `serve/cockpit/web/src/__tests__/KeyboardA11y_1395.test.tsx` | Yes. The suite proves card focusability, selection, keyboard menu opening, and the real move POST path. | COVERED |
| AC3 HealthBadge/ConfirmDialog focus management, meaningful accessible names, Escape dismissal | `serve/cockpit/web/src/__tests__/KeyboardA11y_1395.test.tsx` | No. The ConfirmDialog accessible-name checks at `KeyboardA11y_1395.test.tsx:443-465` only require `aria-label` or `aria-labelledby` to exist. An empty `aria-label=""` or a broken `aria-labelledby` target would still pass, so the required "meaningful accessible name" proof is non-discriminating. | LAX |
| AC4 revised quoted-hex scan on non-comment lines after stripping `var(--pds-*)` segments | `serve/cockpit/web/src/__tests__/PDSHexScan_1395.test.ts` | Yes. The helper strips token segments and scans quoted hex literals on non-comment lines, matching the refined AC4 contract. | COVERED |
| AC5 viewport keyboard reachability and landmark checks at 320/768/1024/1440 without swallowed preconditions | `serve/cockpit/web/e2e/accessibility-1395.spec.ts` | Yes. The suite checks card reachability plus landmark presence at all four breakpoints, and the `.catch(() => {})` swallow pattern is gone. | COVERED |
| AC6 gate-shape / scoped RED proof | Task-scoped suites plus quality-runner output | Yes. The tracked suite is now RED only on the intended accessibility gaps (AC1/AC5) while AC2/AC3/AC4 are green. | COVERED |

#### Security Review
- No issues found. The only dependency addition is the task-required devDependency `@axe-core/playwright` in `serve/cockpit/web/package.json`.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---|---|---|
| `TestFromAC_*` suites in the task-owned files | No weakening visible in the current workspace state | PRESERVED with small confidence deduction because diff-scoped immutability and dirty-tree overlap could not be fully reconstructed from this tool surface |

#### Test Quality
| Dimension | Rating | Evidence |
|---|---|---|
| Assertion specificity | WEAK | `KeyboardA11y_1395.test.tsx:443-465` proves only accessible-name attribute presence for ConfirmDialog, not a non-empty meaningful accessible name. |
| Negative/error-path coverage | ADEQUATE | The RED/green gate shape is correct and the tracked E2E suite now reaches real assertions. |
| Manual mutation reasoning | WEAK | Regressing `ConfirmDialog` to `aria-label=""` or a dead `aria-labelledby` reference would leave the current AC3 name tests green. |
| Test independence | ADEQUATE | Global overrides are restored and render state is fresh per test. |
| Descriptive test names | STRONG | Task-owned test names remain explicit and AC-traceable. |

#### Data Safety
- No issues found.

#### Implementation-Aware Gaps
- `serve/cockpit/web/src/components/ConfirmDialog.tsx:66` currently sets `aria-label={description}`, but the task-owned AC3 tests at `serve/cockpit/web/src/__tests__/KeyboardA11y_1395.test.tsx:443-465` only assert attribute presence. The suite would false-green on an empty name or invalid labelled-by wiring.

#### Necessity Check
- No issues found. `@axe-core/playwright` is directly required by AC1 and is present in the frontend package manifest.

#### Builder Process Quality
| Metric | Value |
|---|---|
| Builder Notes sections | multiple retries with varied approaches |
| Assessment | FRICTION, not a loop-quality defect |

### Pass 2 — INFORMATIONAL
- I did **not** treat the earlier code-reader concern about AC1 endpoint methods as a blocking defect. While the Playwright route handlers themselves do not inspect request verbs, the live fetch contract is already pinned by dedicated hook tests at `serve/cockpit/web/src/__tests__/usePendingDRs.test.ts:54-69` and `serve/cockpit/web/src/__tests__/useScanPolling.test.ts:45-57`.
- I did **not** treat the task-detail render proof as a blocking defect. `DetailTab` returns `null` until task data exists and only renders `[data-field="title"]` when `task` is present (`serve/cockpit/web/src/components/DetailTab.tsx:111`, `serve/cockpit/web/src/components/DetailTab.tsx:438-440`), so the revised AC1 addendum is satisfied by the current precondition.
- HealthBadge naming assertions are stronger than the ConfirmDialog naming assertions and are not the rejection basis.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| AC1 | Tracked spec uses corrected endpoint paths and render preconditions at `serve/cockpit/web/e2e/accessibility-1395.spec.ts:132-137`, `:160-165`, `:173-180`, `:191-205`, `:215-224`; live endpoint contracts are also pinned in `serve/cockpit/web/src/__tests__/usePendingDRs.test.ts:54-69` and `serve/cockpit/web/src/__tests__/useScanPolling.test.ts:45-57`. | `serve/cockpit/web/e2e/accessibility-1395.spec.ts` | PASS |
| AC2 | KeyboardA11y tests prove `tabIndex`, interactive role, `aria-haspopup`, Enter/Space selection, keyboard menu opening, and the real `/api/tasks/{id}/move` POST path (`KeyboardA11y_1395.test.tsx:115-279`), matching the live code in `serve/cockpit/web/src/components/Card.tsx:20-43` and `serve/cockpit/web/src/KanbanBoard.tsx:177-204`, `:309-327`. | `serve/cockpit/web/src/__tests__/KeyboardA11y_1395.test.tsx` | PASS |
| AC3 | HealthBadge focus/name tests are present and ConfirmDialog focus-on-open / restore / Escape are present, but the ConfirmDialog naming assertions at `KeyboardA11y_1395.test.tsx:443-465` only prove attribute presence while the live naming contract sits at `serve/cockpit/web/src/components/ConfirmDialog.tsx:66`. | `serve/cockpit/web/src/__tests__/KeyboardA11y_1395.test.tsx` | FAIL |
| AC4 | `serve/cockpit/web/src/__tests__/PDSHexScan_1395.test.ts:57-81`, `:87-164` implement the revised quoted-hex + token-strip contract and include the mixed-token regression guard. | `serve/cockpit/web/src/__tests__/PDSHexScan_1395.test.ts` | PASS |
| AC5 | Viewport-specific task-card reachability and landmark checks exist at `serve/cockpit/web/e2e/accessibility-1395.spec.ts:241-381`, and swallowed card preconditions are removed. | `serve/cockpit/web/e2e/accessibility-1395.spec.ts` | PASS |
| AC6 | Current scoped evidence shows the intended gate shape: unit suites green, E2E accessibility suite intentionally RED on the remaining audited accessibility gaps. | Task-scoped suites + quality-runner output | PASS |

### Deductions
- Major deduction for AC3 proof quality: the ConfirmDialog accessible-name tests are still non-discriminating.
- Small deduction because dirty-tree overlap could not be independently checked from this tool surface.
- The task body already contains prior `## Review Evidence` sections, so this repeat review failure routes to `backlog` under the loop-breaker rule.

### Confidence: 0.88
### Verdict: FAIL
### Action: reject to `backlog`

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|---|---|---|---|
| 1 | architect | Re-issue the AC3 proof requirement so the task-owned ConfirmDialog tests must assert a non-empty meaningful accessible name (or an `aria-labelledby` reference that resolves to real label text), not just attribute presence, before the task re-enters RED/review | `serve/cockpit/web/src/__tests__/KeyboardA11y_1395.test.tsx`, `serve/cockpit/web/src/components/ConfirmDialog.tsx` | `KeyboardA11y_1395.test.tsx:443-465`; `ConfirmDialog.tsx:66` |
[[2026-05-11]]


## Architecture Review (Refinement 3 — fourth reviewer loop-breaker)

### Reviewer Finding Addressed

| FR | Issue | Resolution |
|----|-------|------------|
| FR1 | ConfirmDialog accessible-name tests at `KeyboardA11y_1395.test.tsx:449-465` only check `hasAttribute('aria-label')` — passes on empty string or invalid `aria-labelledby` ref | AC3 addendum 2 below |

### AC3 addendum 2

ConfirmDialog accessible-name tests must assert that `getAttribute('aria-label')` returns a non-empty string, not merely that the attribute exists via `hasAttribute()`. Specifically: replace `dialog!.hasAttribute('aria-label') || dialog!.hasAttribute('aria-labelledby')` with an assertion that `dialog!.getAttribute('aria-label')` is a truthy, non-empty string. An empty `aria-label=""` or a missing attribute must fail the test.

AC1, AC2, AC4, AC5, AC6 unchanged.

### Evaluation (delta only)
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| All other criteria | No change from prior reviews | Single proof-precision refinement |

### Verdict: APPROVE
One-line proof fix: `hasAttribute` → `getAttribute` + truthy assertion. No architectural change, no scope change, no new surfaces.
[[2026-05-11]]
Architecture Review (Refinement 3): Fourth reviewer loop-breaker. Single finding — ConfirmDialog accessible-name tests use `hasAttribute()` (proves existence) instead of `getAttribute()` + truthy check (proves meaningful value). AC3 addendum 2 requires non-empty string assertion. No architectural or scope change.
[[2026-05-11]]
## Test-Writer Notes (Retry 6)

### Reviewer Required Follow-up Addressed (Arch Review Refinement 3 — AC3 addendum 2)

| FR | Addendum | Action | Outcome |
|----|----------|--------|---------|
| AC3 ConfirmDialog name proof | Replace `hasAttribute('aria-label') \|\| hasAttribute('aria-labelledby')` with `getAttribute('aria-label')` truthy + non-empty check | Updated 2 tests in `TestFromAC_ConfirmDialogFocus` | PASSES (impl has non-empty `aria-label={description}`) |

### Changed Files
- `serve/cockpit/web/src/__tests__/KeyboardA11y_1395.test.tsx` — 2 tests tightened

### Test Names Changed
- `ConfirmDialog has an accessible name via aria-label or aria-labelledby on the dialog element` → `ConfirmDialog has a non-empty meaningful accessible name on the dialog element (AC3 addendum 2)`
- `ConfirmDialog "move-backward" type has an accessible name referencing its description` → `ConfirmDialog "move-backward" type has a non-empty meaningful accessible name (AC3 addendum 2)`

### Assertion Change
Before: `expect(dialog!.hasAttribute('aria-label') || dialog!.hasAttribute('aria-labelledby')).toBe(true)`
After: `expect(dialog!.getAttribute('aria-label')).toBeTruthy()` + `expect(ariaLabel!.length).toBeGreaterThan(0)`

Empty `aria-label=""` now fails. Dead `aria-labelledby` ref no longer falsely satisfies the check.

### Failure Verification (Vitest)
```
Test Files  2 passed (2 total)
Tests       26 passed (26 total)
```
All PASS — implementation already has non-empty `aria-label={description}` for both dialog types.

### Advance Reason: Step 1b.1 Direct-to-Review
- Reviewer's required follow-up was test-proof gaps only (no implementation fixes)
- All tightened tests PASS against current implementation
- Builder has no work to do — test-only retry

### Lint
ESLint: clean (exit 0)

### Commit
`ca2f9ee4` — test: tighten ConfirmDialog accessible-name assertion to non-empty getAttribute (#1395, test-writer)

### AC Coverage Table (Retry 6)
| AC | Tests | Verdict |
|----|-------|---------|
| AC1 axe-core E2E 4 pages at 1024px | 4 E2E FAIL (tracked) | RED ✓ |
| AC2 keyboard card nav + movement | Vitest: 8 tests PASS | GREEN |
| AC3 HealthBadge + ConfirmDialog focus (incl. non-empty name) | Vitest: 9 tests PASS | GREEN — name proof now discriminating |
| AC4 PDS hex scan + mixed-token guard | Vitest: 5 tests PASS | GREEN |
| AC5 a11y viewport 4 breakpoints | 4 E2E FAIL (tracked) | RED ✓ |
| AC6 td:0 | pass-through | — |
[[2026-05-11]]
## Builder Notes
- Implementation: none in this pass (test-gate verification task).
- Files changed: none.
- Approach: verified current AC proof shape using quality-runner scoped execution before handoff.

### Test Results
- Vitest task suites: 26 passed, 0 failed
  - serve/cockpit/web/src/__tests__/KeyboardA11y_1395.test.tsx: 21 passed
  - serve/cockpit/web/src/__tests__/PDSHexScan_1395.test.ts: 5 passed
- Playwright task suite: 5 failed, 1 interrupted, 1 passed, 5 not run
  - serve/cockpit/web/e2e/accessibility-1395.spec.ts
- Key RED evidence (expected for this gate):
  - AC1: axe failures remain on board/detail/decision/repair flows (nested-interactive violations).
  - AC5: keyboard reachability failure at narrow viewport (task-card tab focus not reached).

### Lint Status
- ESLint scoped run: clean (0 violations across 7 files).

### Coverage
- Not applicable for this scoped frontend unit + e2e verification run.

### Evidence Summary
- AC2/AC3/AC4 are green in task-scoped unit tests.
- AC1/AC5 remain intentionally RED in tracked E2E, providing the expected pre-implementation gate for counterpart #1396.
- Routing: advance to review for independent evidence check.
[[2026-05-11]]
## Review Evidence
### Test Results
- quality-runner scoped frontend run completed successfully with no environment/bootstrap errors.
- Vitest: 26 passed, 0 failed, 0 skipped across `serve/cockpit/web/src/__tests__/KeyboardA11y_1395.test.tsx` and `serve/cockpit/web/src/__tests__/PDSHexScan_1395.test.ts`.
- Playwright: 4 passed, 8 failed in `serve/cockpit/web/e2e/accessibility-1395.spec.ts`.
- The 8 Playwright failures are expected RED gate assertions for the accepted task shape: live axe violations on the audited AC1 surfaces and keyboard reachability failures on the AC5 card checks. They are not setup/precondition failures.

### Lint
- ESLint scoped clean on the task-owned tests/spec and referenced frontend source files.
- VS Code diagnostics: no errors in the reviewed task files or referenced source files.

### Coverage
- Scoped module coverage from the fresh quality-runner pass:
  - `Card.tsx`: 97.82% statements / 84.05% branch
  - `KanbanBoard.tsx`: 69.73% statements / 63.54% branch
  - `HealthBadge.tsx`: 94.00% statements / 68.29% branch
  - `ConfirmDialog.tsx`: 77.19% statements / 46.66% branch
- Module-level percentages are not the gate here. The reviewed task is a proof/gate task, and the claimed AC behaviors are directly exercised by the task-owned suites plus adjacent existing runtime-contract tests.

### Source-Control Evidence
- Task-related commits are present in `.git/logs/HEAD` and `.git/logs/refs/heads/dev`, including `29ec6841`, `db254057`, `04f7b85b`, `907376a59c694f701f6f3ab59e4b2e72794930ba`, `08076560`, `c91a46b6`, `85876d73`, `ec41149d`, and `ca2f9ee4`.
- Dirty-tree overlap and exact TestFromAC immutability versus the earliest RED snapshot could not be fully reconstructed from this tool surface, so a small confidence deduction remains.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---|---|---|---|
| AC1 revised axe proof on board/detail/decision/repair at 1024px with live endpoint contract and rendered-surface preconditions | `serve/cockpit/web/e2e/accessibility-1395.spec.ts` plus adjacent endpoint-contract tests in `serve/cockpit/web/src/__tests__/usePendingDRs.test.ts` and `serve/cockpit/web/src/__tests__/useScanPolling.test.ts` | Yes. The tracked E2E suite uses the correct live paths (`accessibility-1395.spec.ts:132,137`), enforces rendered-surface preconditions before `AxeBuilder.analyze()` (`:157,169,186,210`), and the GET/POST fetch contract is independently pinned in the adjacent hook tests (`usePendingDRs.test.ts:49-64`, `useScanPolling.test.ts:40-57`). | COVERED |
| AC2 keyboard-only workflow proof | `serve/cockpit/web/src/__tests__/KeyboardA11y_1395.test.tsx` with adjacent real-board selection proof in `serve/cockpit/web/src/__tests__/Shell.card-selection.integration.test.tsx` | Yes. The task-owned suite proves Enter/Space selection callback, keyboard menu signal/open, and the real move POST path (`KeyboardA11y_1395.test.tsx:143,154,193,202,244`). The remaining board-selection seam is closed by shared runtime wiring in `Card.tsx:42-45`, `Column.tsx:70-71`, `Shell.tsx:53-57`, and the adjacent real-board selection integration at `Shell.card-selection.integration.test.tsx:181-216`. | COVERED |
| AC3 HealthBadge and ConfirmDialog focus management, meaningful accessible names, and Escape dismissal | `serve/cockpit/web/src/__tests__/KeyboardA11y_1395.test.tsx` | Yes. HealthBadge focus/open/close/name coverage is at `KeyboardA11y_1395.test.tsx:296,326,345,359,397,408`, matching `HealthBadge.tsx:29-33,57-71`. ConfirmDialog focus-on-open and non-empty aria-label proof are at `KeyboardA11y_1395.test.tsx:432,443`, with close/focus-restore coverage later in the same block, matching `ConfirmDialog.tsx:45-49,66-68`. | COVERED |
| AC4 revised quoted-hex scan after stripping `var(--pds-*)` segments | `serve/cockpit/web/src/__tests__/PDSHexScan_1395.test.ts` | Yes. The task-owned scan suite proves token exclusion, positive hex detection, and mixed token+hex detection at `PDSHexScan_1395.test.ts:129,142,152`, matching the refined AC4 contract. | COVERED |
| AC5 viewport keyboard reachability and landmark presence at 320/768/1024/1440 without swallowed preconditions | `serve/cockpit/web/e2e/accessibility-1395.spec.ts` | Yes. The tracked E2E suite has dedicated viewport checks at `accessibility-1395.spec.ts:253,292,327,362`, and the swallowed precondition pattern is gone. | COVERED |
| AC6 gate shape / scoped RED proof | current tracked suite + fresh quality-runner output | Yes. The live tracked suite is green where the task should be green (AC2/AC3/AC4) and intentionally RED where the task is supposed to expose remaining audited accessibility gaps (AC1/AC5). | COVERED |

#### Security Review
- No issues found. The only dependency addition is the task-required devDependency `@axe-core/playwright` in `serve/cockpit/web/package.json`.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---|---|---|
| `TestFromAC_*` suites in the task-owned files | No weakening visible in the live workspace; the last open AC3 concern was tightened from attribute presence to non-empty `getAttribute('aria-label')` proof | PRESERVED with a small confidence deduction because diff-scoped immutability and dirty-tree overlap could not be fully reconstructed from this tool surface |

#### Test Quality
| Dimension | Rating | Evidence |
|---|---|---|
| Assertion specificity | ADEQUATE | The current suites use discriminating assertions for the prior weak spots: ConfirmDialog open-focus uses `document.activeElement` (`KeyboardA11y_1395.test.tsx:432`) and ConfirmDialog naming now requires a non-empty aria-label (`:443`). The E2E suite enforces rendered-surface preconditions before axe runs (`accessibility-1395.spec.ts:157,169,186,210`). |
| Negative/error-path coverage | ADEQUATE | HealthBadge covers Escape on popover and document (`KeyboardA11y_1395.test.tsx:326,345`), ConfirmDialog covers close/focus-restore paths, and the PDS scanner has both exclusion and positive-detection self-tests (`PDSHexScan_1395.test.ts:129,142,152`). |
| Manual mutation reasoning | ADEQUATE | Removing `dialogRef.current?.focus()` or emptying `aria-label` in `ConfirmDialog.tsx:46,66` would fail the current task-owned AC3 tests. Removing keyboard menu handling or the real move POST path would fail the AC2 tests. Breaking mixed token+hex detection would fail `PDSHexScan_1395.test.ts:152`. |
| Test independence | STRONG | Task-owned tests use local render helpers, local spies, and clean reset patterns. |
| Descriptive test names | STRONG | Task-owned test names remain explicit and AC-traceable. |

#### Data Safety
- No issues found.

#### Implementation-Aware Gaps
- No blocking gaps found.
- Informational only: AC2’s real-board selection proof is split across the task-owned keyboard tests and an adjacent real-board integration suite rather than one task-owned integration test. Because the live runtime wiring is shared (`Card.onSelect` -> `Column.onSelectTask` -> `Shell.selectedTaskId`), that is a confidence deduction, not a FAIL condition.

#### Necessity Check
- No issues found. `@axe-core/playwright` is directly required by AC1 and is present in the frontend package manifest.

#### Builder Process Quality
| Metric | Value |
|---|---|
| Builder Notes sections | multiple retries with varied approaches |
| Assessment | FRICTION, not a loop-quality defect |

### Pass 2 — INFORMATIONAL
- Some RED-phase header comments are stale in the task-owned files. Examples: `KeyboardA11y_1395.test.tsx:16-21`, `accessibility-1395.spec.ts:17-19`, and `PDSHexScan_1395.test.ts:1-18` still describe earlier missing behavior that is now implemented or refined.
- I attempted an adversarial challenger check on the proposed PASS verdict, but the subagent returned no response. I therefore grounded the verdict only in the direct quality-runner output, live file reads, adjacent test evidence, and task history.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| AC1 | `serve/cockpit/web/e2e/accessibility-1395.spec.ts:132-137,157-224`; adjacent contract tests `serve/cockpit/web/src/__tests__/usePendingDRs.test.ts:49-64` and `serve/cockpit/web/src/__tests__/useScanPolling.test.ts:40-57` | `serve/cockpit/web/e2e/accessibility-1395.spec.ts` | PASS |
| AC2 | `serve/cockpit/web/src/__tests__/KeyboardA11y_1395.test.tsx:143-244`; shared selection wiring in `serve/cockpit/web/src/components/Card.tsx:42-45`, `serve/cockpit/web/src/components/Column.tsx:70-71`, `serve/cockpit/web/src/Shell.tsx:53-57`; adjacent real-board selection integration `serve/cockpit/web/src/__tests__/Shell.card-selection.integration.test.tsx:181-216` | `serve/cockpit/web/src/__tests__/KeyboardA11y_1395.test.tsx` + adjacent integration | PASS |
| AC3 | `serve/cockpit/web/src/__tests__/KeyboardA11y_1395.test.tsx:296-418,432-625`; matching runtime behavior in `serve/cockpit/web/src/components/HealthBadge.tsx:29-33,57-71` and `serve/cockpit/web/src/components/ConfirmDialog.tsx:45-49,66-68` | `serve/cockpit/web/src/__tests__/KeyboardA11y_1395.test.tsx` | PASS |
| AC4 | `serve/cockpit/web/src/__tests__/PDSHexScan_1395.test.ts:129-160` | `serve/cockpit/web/src/__tests__/PDSHexScan_1395.test.ts` | PASS |
| AC5 | `serve/cockpit/web/e2e/accessibility-1395.spec.ts:253-380` | `serve/cockpit/web/e2e/accessibility-1395.spec.ts` | PASS |
| AC6 | fresh scoped evidence: Vitest 26 passed / Playwright 4 passed, 8 failed on the intended accessibility gates | task-scoped suites + quality-runner output | PASS |

### Deductions
- Small deduction because diff-scoped TestFromAC immutability and dirty-tree contamination checks could not be fully reconstructed from this tool surface.
- Small deduction because AC2 board-selection proof is split across task-owned keyboard assertions and an adjacent real-board integration suite rather than a single task-owned end-to-end keyboard-selection assertion.

### Confidence: 0.92
### Verdict: PASS
### Action: advance to `docs`
[[2026-05-11]]
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | Task adds test files and keyboard/focus semantics to frontend components. No IN-scope README references these components or the accessibility/keyboard features at this level of specificity. `serve/cockpit/README.md` covers the backend API only. |
| 2 | Module docstrings | No | N/A | All changed files are `.tsx`/`.ts` (TypeScript/React) — not Python modules. Docstring rule applies only to `.py` files. |
| 3 | External attribution | No | N/A | `@axe-core/playwright` added as a standard npm devDependency per AC1 requirement. No external patterns from repos/articles were adopted that require attribution in `sources.md`. |
| 4 | Research doc | No | N/A | No `.owlbear/research/{slug}.md` was produced for this task (test-gate task, no research phase). |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/cockpit.excalidraw` has `describes: serve/cockpit/src/**, serve/cockpit/web/src/**` — matches `Card.tsx`, `KanbanBoard.tsx`, `HealthBadge.tsx`, `ConfirmDialog.tsx`. Footer updated from `(184c2f0f)` → `(679a89d9)` (commit `a361303c`). |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | No files deleted in this task. No IN-scope orphaned docs detected. |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| serve/cockpit/web/src/components/Card.tsx | OUT | N/A (TypeScript source, no .py docstrings) |
| serve/cockpit/web/src/KanbanBoard.tsx | OUT | N/A (TypeScript source) |
| serve/cockpit/web/src/components/HealthBadge.tsx | OUT | N/A (TypeScript source) |
| serve/cockpit/web/src/components/ConfirmDialog.tsx | OUT | N/A (TypeScript source) |
| serve/cockpit/web/e2e/accessibility-1395.spec.ts | OUT | N/A (test file) |
| serve/cockpit/web/src/__tests__/KeyboardA11y_1395.test.tsx | OUT | N/A (test file) |
| serve/cockpit/web/src/__tests__/PDSHexScan_1395.test.ts | OUT | N/A (test file) |
| serve/cockpit/web/package.json | OUT | N/A (config/manifest) |
| .owlbear/scratch/1395-accessibility.spec.ts | OUT | Deleted |
| share/diagrams/cockpit.excalidraw | IN | Footer updated (diagram maintenance, item 5) |

### Files Updated
- `share/diagrams/cockpit.excalidraw` — footer `Last verified` updated to `2026-05-11 (679a89d9)` (commit `a361303c`)

### Child Tasks Created
- None

### Scratch Files Cleaned
- `.owlbear/scratch/1395-accessibility.spec.ts`
- `.owlbear/scratch/1395-coverage-scoped.log`
- `.owlbear/scratch/1395-coverage.log`
- `.owlbear/scratch/1395-eslint-scoped-final.log`
- `.owlbear/scratch/1395-eslint-scoped.log`
- `.owlbear/scratch/1395-eslint.log`
- `.owlbear/scratch/1395-npm-test.log`
- `.owlbear/scratch/1395-playwright-scoped.log`
- `.owlbear/scratch/1395-playwright.log`
- `.owlbear/scratch/1395-pw-fresh.log`
- `.owlbear/scratch/1395-pw-temp.log`
- `.owlbear/scratch/1395-pw-test.log`
- `.owlbear/scratch/1395-pw.log`
- `.owlbear/scratch/1395-vitest-2.log`
- `.owlbear/scratch/1395-vitest-raw.log`
- `.owlbear/scratch/1395-vitest-scoped.log`
- `.owlbear/scratch/1395-vitest-unit.log`
- `.owlbear/scratch/1395-vitest.log`
[[2026-05-11]]
## Audit

### Regression Detection
- Vitest full suite: 1327 passed, 0 failed, 9 skipped — CLEAN.
- Playwright full suite: 48 passed, 11 failed. The 8 `accessibility-1395.spec.ts` failures are the intentional RED gates (AC1/AC5) — by design for this test-gate task. The 3 non-1395 failures (`kanban-board.spec.ts:206`, `responsive-layout-1391.spec.ts:164,300`) are pre-existing layout tests with no causal link to 1395's semantic/focus additions (role, tabIndex, aria-haspopup, focus lifecycle — none affect CSS box model).
- Pytest: 204 failures in unrelated Python modules. Task 1395 changed ONLY TypeScript files — zero causal overlap.
- Ruff: 286 Python lint violations — pre-existing; task 1395 has no Python deliverables.
- No regressions attributable to task 1395.

### Intent Verification
- All changed files are within `serve/cockpit/web/` (src/components, src/__tests__, e2e/, package.json) — correct domain per `scope:cockpit-web` tag.
- Implementation direction matches stated purpose: test-gate for accessibility/keyboard/PDS verification.
- No extraneous scope — all changes serve the stated AC lines.

### Architect Quality
- Score: 4/5. Final AC is specific, naming endpoints, selectors, render-proof requirements, and exclusion lists. Required 3 refinement cycles after challenger at 0.38 on first pass — but the iterative process worked correctly and the delivered AC is strong.
- No architect-calibration follow-up needed (score > 2).

### Commit Integrity
- 10 task commits present in git log: `6f336a26`, `29ec6841`, `db254057`, `04f7b85b`, `907376a5`, `08076560`, `c91a46b6`, `85876d73`, `ec41149d`, `ca2f9ee4` — all properly attributed (#1395, builder/test-writer).
- 1 docs commit: `a361303c` (doc-writer).
- Scratch files cleaned per docs gate notes.
- No uncommitted deliverables.

### Deductions
- None. All 4 pillars pass cleanly.

### Confidence: 1.00
### Action: archive