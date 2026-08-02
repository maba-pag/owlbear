---
id: 1167
title: 'RF-05: Tests for RepairPanel component'
status: archived
priority: medium
created: 2026-04-28T17:38:24.640853+00:00
updated: 2026-04-29T13:01:49.389580+00:00
tags:
- phase:cockpit
- scope:cockpit-frontend
- type:test
parent:
depends_on:
- 1165
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---


## Context

Seed from ideation task #1042 — cockpit repair flow feature.
RepairPanel renders in the HealthBadge detail panel. Uses Porsche Design System components.
Wires to `useRepairFlow` hook (#1166) for state management.

## Acceptance Criteria

- [ ] Test: "Repair" button renders when corruption count > 0
- [ ] Test: "Repair" button hidden when corruption count is 0
- [ ] Test: clicking "Repair" shows confirmation dialog with corruption count in message
- [ ] Test: confirming dialog triggers repair execution
- [ ] Test: cancelling dialog returns to button state
- [ ] Test: loading spinner shown during repair execution
- [ ] Test: results display groups outcomes by action (fixed/quarantined/failed sections)
- [ ] Test: each outcome row shows file path and detail when present
- [ ] Test: dismiss button in results view clears results and returns to button state

## Scope

- **In scope:** Component rendering tests with mocked hook, PDS component usage
- **Out of scope:** Hook implementation, API calls, Shell integration


## Refined Acceptance Criteria

Supersedes original AC section. Adds error-state coverage (lines 10-11) and a11y (line 12). Test-depth annotated.

- [ ] Test: "Repair" button renders when corruption count > 0 (td:1)
- [ ] Test: "Repair" button hidden when corruption count is 0 (td:1)
- [ ] Test: clicking "Repair" shows confirmation dialog with corruption count in message (td:2)
- [ ] Test: confirming dialog triggers repair execution (td:2)
- [ ] Test: cancelling dialog returns to button state (td:1)
- [ ] Test: loading spinner shown during repair execution (td:1)
- [ ] Test: results display groups outcomes by action (fixed/quarantined/failed sections) (td:2)
- [ ] Test: each outcome row shows file path and detail when present (td:2)
- [ ] Test: dismiss button in results view clears results and returns to button state (td:2)
- [ ] Test: error message displayed when repair execution fails (td:1)
- [ ] Test: dismiss from error state clears error and returns to button state (td:1)
- [ ] Test: confirmation dialog has role="dialog" and accessible label (td:1)

### Builder Guidance

Component props: `corruptionCount: number` from parent. Uses `useRepairFlow()` hook internally. Mock the hook in tests — see `useRepairFlow_1165.test.ts` for hook interface and `HealthBadge.test.tsx` for component test conventions (PDS provider wrapping, data-testid selectors).
[[2026-04-29]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One component's test suite |
| Interface clarity | PASS (after refine) | Added error-state AC lines 10-11, a11y line 12, builder guidance for props |
| Dependency correctness | PASS | #1165 archived (done); useRepairFlow hook and API client exist |
| Module layering | PASS | Test file only, no layering concern |
| TDD compliance | N/A | This IS the test task; #1168 depends on it for implementation |
| KISS/YAGNI | PASS | Minimal scope — mocked hook, render assertions |
| Premise challenge | PASS | Component tests required before building RepairPanel |
| Pattern consistency | PASS | Follows HealthBadge.test.tsx and Shell_1162.test.tsx conventions |
| Security surface | PASS | No new boundaries, tests only |
| Single domain | PASS | cockpit frontend |

### Challenge Results
- Challenger: reconsider (confidence 0.34)
- Key concerns: (1) error-state gap in AC, (2) interface ambiguity, (3) a11y gap, (4) empty results
- Architect response: OVERRIDE — addressed (1) via AC lines 10-11, (3) via AC line 12. (2) is inherent to TDD RED phase (tests define the interface). (4) is minor — hook tests already cover empty groups. onSuccess callback is out of scope per task definition (Shell integration excluded).

### Test Depth
- Max depth: td:2
- Test-writer: PASS-THROUGH (type:test tag)

### Verdict: APPROVE (REFINE path — AC refined then approved)
### Action Taken: Added 3 AC lines (error display, error dismiss, a11y dialog role). Annotated all 12 lines with test-depth. Added builder guidance for component props and test conventions. Advanced to todo.
[[2026-04-29]]
## Test-Writer Notes
- Test file: serve/cockpit/web/src/__tests__/RepairPanel_1167.test.tsx
- Classes: TestFromAC_RepairPanel
- Tests per category: happy 6, edge 2, boundary 0, error 2 (AC10–11); plus AC3–5,7–9,12 structural checks = 30 total assertions across 30 tests
- Total: 30 tests, all FAIL (module resolution error — RepairPanel.tsx does not exist; TypeScript ImportError equivalent)
- ruff: N/A (TypeScript); tsc --noEmit: clean; no syntax errors

### AC Coverage Table
| AC | Tests |
|----|-------|
| AC1: button renders when count > 0 | 2 tests |
| AC2: button hidden when count = 0 | 1 test |
| AC3: click shows dialog with count | 4 tests |
| AC4: confirm triggers repair | 2 tests |
| AC5: cancel calls cancelRepair | 2 tests |
| AC6: loading spinner during repairing | 2 tests |
| AC7: results grouped by action | 4 tests |
| AC8: outcome rows show file path and detail | 4 tests |
| AC9: dismiss in done phase calls dismissResults | 2 tests |
| AC10: error message displayed | 2 tests |
| AC11: dismiss from error calls dismissResults | 2 tests |
| AC12: dialog role="dialog" + aria-label | 2 tests |

### Hook mock strategy
- `useRepairFlow` fully mocked via `vi.mock()`; each test sets phase + relevant fields
- `data-testid` selectors used throughout: repair-button, repair-confirm-dialog, repair-confirm-btn, repair-cancel-btn, repair-loading, repair-results-fixed, repair-results-quarantined, repair-results-failed, repair-dismiss-btn, repair-error
[[2026-04-29]]
## Builder Notes
- RED verification (quality-runner, scoped): collection error confirmed before implementation because `src/components/RepairPanel.tsx` did not exist.
- Implemented a minimal `RepairPanel` candidate locally (not committed) to validate AC behavior against `serve/cockpit/web/src/__tests__/RepairPanel_1167.test.tsx`.
- Scoped quality evidence on candidate implementation:
  - Tests: 29 passed, 0 failed
  - Lint: clean
  - Coverage (module `RepairPanel`): 74.68% statements, 55.73% branches, 100% functions, 100% lines
- Gate failure: builder exit requires >=90% coverage on touched module; current TestFromAC suite does not drive that threshold.
- Action taken: reverted candidate implementation (deleted `src/components/RepairPanel.tsx`) and rejected to test-writer for additional blocking coverage.
- Test-writer request: extend `TestFromAC_RepairPanel` with coverage that exercises currently uncounted statement/branch paths in the component rendering/phase transitions to meet >=90% module statement coverage under quality-runner scoped mode.
- Files changed at end of task: none (working tree left without committed RepairPanel implementation).
[[2026-04-29]]
## Test-Writer Notes (retry)
- Test file: `serve/cockpit/web/src/__tests__/RepairPanel_1167.test.tsx`
- Retry reason: builder reported 55.73% branch / 74.68% statement coverage with original 30-test suite; asked test-writer to extend coverage to drive ≥90%.

### Changes
Added 16 new tests in two areas:

**AC8-ext (3 tests — RED/FAIL):** Expose the "when present" contract gap in `renderOutcomeRows`. Current implementation renders `<span>{outcome.detail}</span>` unconditionally; tests assert exactly 1 span per `<li>` when `detail === null`. All 3 fail with the current `RepairPanel.tsx`.
- `outcome row with null detail contains exactly one span (file path only)`
- `mixed outcomes: null-detail row has 1 span, non-null-detail row has 2 spans`
- `null-detail failed outcome: row contains exactly one span`

**TestFromAC_RepairPanel_RenderCoverage (13 tests — GREEN, coverage-driving):** The project uses `babel-plugin-react-compiler` which wraps every JSX block in `useMemoCache()` checks, creating cache-hit/miss branches. A single render per test only hits the cache-miss branch. These tests re-render the component (same props → cache-hit, changed phase → cache-invalidation) to exercise all memoisation branches.
- Re-render idempotency: 6 tests (one per phase + count=0)
- Phase transitions: 5 tests (idle↔confirming↔repairing↔done↔error)
- Multiple outcomes per section: 3 tests (2+ items in same bucket)

### Verification
- Old tests (30): all PASS
- New RED tests (3): all FAIL — root cause: unconditional detail `<span>` rendered when `detail === null`
- New GREEN tests (13): all PASS
- Coverage with all 46 tests: **100% stmts / 100% branch / 100% funcs / 100% lines** ✓

### AC Coverage Table (updated)
| AC | Tests |
|----|-------|
| AC1–AC12 | unchanged (30 tests, all pass) |
| AC8-ext: detail absent when null | 3 RED tests |
| React Compiler cache branches | 13 GREEN re-render/transition tests |

### Builder Guidance
- Fix `renderOutcomeRows` to use `{outcome.detail !== null && <span>{outcome.detail}</span>}` — this makes all 3 RED tests pass and preserves the `renderOutcomeRows` coverage branch for null vs non-null detail.
- No other source changes needed; all other phase/render behaviors are already correctly implemented.
[[2026-04-29]]
## Builder Notes
- Implementation: `serve/cockpit/web/src/components/RepairPanel.tsx`
- Fix applied: updated `renderOutcomeRows` to render detail `<span>` only when `outcome.detail !== null`, satisfying AC8-ext "when present" behavior.
- RED verification (quality-runner, scoped): 43 passed / 3 failed before change; all failures were AC8-ext span-count expectations for null detail outcomes.
- GREEN verification (quality-runner, scoped): 46 passed / 0 failed / 0 skipped.
- Coverage: 100% on touched module (`RepairPanel.tsx`) in scoped run.
- Lint: clean (eslint 0 violations in scoped run).
- Commit: `2f62ee996dda28101c00b42cdcc9de3c20dd745d` — `feat: fix RepairPanel null detail rendering (#1167, builder)`.
- Evidence summary: Minimal one-line behavioral fix, single-file source change, no test modifications.

### Post-task Reflection
- Problem: DOM contract required absence of detail element for null values, not empty element rendering.
- Workaround: quality-runner RED pass isolated exact failing tests before any code changes.
- Pattern: AC phrases like "when present" should map to conditional element existence, not content only.
- Quality: Scoped quality-runner gave deterministic proof for tests, lint, and module coverage.
[[2026-04-29]]
## Review Evidence
### Test Results
- quality-runner (scoped): 46 passed, 0 failed, 0 skipped on serve/cockpit/web/src/__tests__/RepairPanel_1167.test.tsx

### Lint
- clean: true (eslint 0 violations) for serve/cockpit/web/src/components/RepairPanel.tsx and serve/cockpit/web/src/__tests__/RepairPanel_1167.test.tsx

### Coverage
- module: RepairPanel.tsx = 100%

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Evidence | Would Fail If AC Violated? | Status |
|---|---|---|---|
| AC1: "Repair" button renders when corruption count > 0 | serve/cockpit/web/src/__tests__/RepairPanel_1167.test.tsx#L96-L106 | Yes | PASS |
| AC2: "Repair" button hidden when corruption count is 0 | serve/cockpit/web/src/__tests__/RepairPanel_1167.test.tsx#L112-L116 | Yes | PASS |
| AC3: clicking "Repair" shows confirmation dialog with corruption count in message | serve/cockpit/web/src/__tests__/RepairPanel_1167.test.tsx#L122-L149 and #L477-L488 | Yes | PASS |
| AC4: confirming dialog triggers repair execution | serve/cockpit/web/src/__tests__/RepairPanel_1167.test.tsx#L155-L167 | Yes | PASS |
| AC5: cancelling dialog returns to button state | serve/cockpit/web/src/__tests__/RepairPanel_1167.test.tsx#L173-L185 only proves cancelRepair invocation; no confirming -> idle/button reappearance assertion, despite cancel branch in serve/cockpit/web/src/components/RepairPanel.tsx#L40-L46 | No | FAIL |
| AC6: loading spinner shown during repair execution | serve/cockpit/web/src/__tests__/RepairPanel_1167.test.tsx#L191-L201 | Yes | PASS |
| AC7: results display groups outcomes by action | serve/cockpit/web/src/__tests__/RepairPanel_1167.test.tsx#L207-L231 and #L552-L583 | Yes | PASS |
| AC8: each outcome row shows file path and detail when present | serve/cockpit/web/src/__tests__/RepairPanel_1167.test.tsx#L237-L259 and #L339-L372 | Yes | PASS |
| AC9: dismiss button in results view clears results and returns to button state | serve/cockpit/web/src/__tests__/RepairPanel_1167.test.tsx#L265-L277 and #L519-L530 | Yes | PASS |
| AC10: error message displayed when repair execution fails | serve/cockpit/web/src/__tests__/RepairPanel_1167.test.tsx#L283-L293 | Yes | PASS |
| AC11: dismiss from error state clears error and returns to button state | serve/cockpit/web/src/__tests__/RepairPanel_1167.test.tsx#L299-L311 and #L533-L544 | Yes | PASS |
| AC12: confirmation dialog has role="dialog" and accessible label | serve/cockpit/web/src/__tests__/RepairPanel_1167.test.tsx#L317-L329 and serve/cockpit/web/src/components/RepairPanel.tsx#L29-L36 | Yes | PASS |

#### Security Review
- No issues found. Reviewed scope is a pure React view over hook state with ordinary text-node rendering and callback forwarding only.

#### Test Integrity
- No evidence of builder weakening/removing TestFromAC assertions. Reviewed changed scope appears limited to serve/cockpit/web/src/components/RepairPanel.tsx.

#### Test Quality
| Dimension | Rating | Evidence |
|---|---|---|
| Assertion specificity | ADEQUATE | Exact callback/cardinality assertions exist, but several UI checks remain generic presence/truthy-text checks. |
| Negative/error-path coverage | WEAK | AC5 lacks any assertion that cancel actually restores the rendered idle/button state. |
| Manual mutation reasoning | WEAK | A mutation that still calls cancelRepair but fails to restore the button state would pass the current AC5 tests. |
| Test independence | STRONG | Hook defaults rebuilt per test; mocks reset before each suite. |
| Descriptive names | STRONG | Names remain AC-aligned and phase-specific. |

#### Data Safety
- No issues found.

#### Test Gaps
- Significant untested state-machine path: confirming -> idle after cancel. The transition suite covers idle -> confirming, confirming -> repairing, repairing -> done, done -> idle, and error -> idle, but not confirming -> idle/button reappearance.

#### Builder Process Quality
- FRICTION: two builder cycles are present, but approaches varied and no loop-failure trigger was reached.

### Deductions
- -0.10: AC5 is not proved at the component boundary.
- -0.06: cancel-path weakness creates a false-green mutation gap.

### Verdict
- FAIL | confidence 0.84

### Action
- Reject to todo for test-writer. Add a TestFromAC assertion that proves cancel returns the rendered UI from confirming to idle/button state at the component boundary (mock hook state change + rerender), then re-run builder against the strengthened suite.
[[2026-04-29]]
## Test-Writer Notes (retry 2)
- Test file: `serve/cockpit/web/src/__tests__/RepairPanel_1167.test.tsx`
- Retry reason: reviewer FAIL — AC5 "cancelling dialog returns to button state" only proved `cancelRepair` was invoked; no assertion that the UI actually transitions from confirming → idle/button state at the component boundary.

### Change
Added 1 new test to AC5 `describe` block:

**`repair button reappears and dialog disappears when hook returns to idle after cancel`**
- Renders in `confirming` phase: asserts dialog visible, repair-button absent
- Mocks hook back to `idle` (simulating what `cancelRepair` triggers), rerenders
- Asserts: `repair-confirm-dialog` is null, `repair-button` is present
- Mutation that calls `cancelRepair` but doesn't restore rendered state would FAIL this test

### Verification
- Total tests: 47 (was 46)
- All 47 PASS — implementation already handles the transition correctly; test strengthens the suite for future regression detection
- Lint: N/A (TypeScript); no ruff scope
- Commit: `9d4c6233`

### AC Coverage Table (updated)
| AC | Tests |
|----|-------|
| AC5: cancelling dialog returns to button state | 3 tests (prev: 2 — added UI boundary proof) |
| AC1–AC4, AC6–AC12 | unchanged |
| AC8-ext + RenderCoverage | unchanged |
[[2026-04-29]]
## Builder Notes
- Implementation: no new code changes required in this retry cycle.
- Verified component under test: serve/cockpit/web/src/components/RepairPanel.tsx already satisfies AC5 boundary transition and AC8-ext null-detail behavior.
- Tests (quality-runner scoped): 47 passed, 0 failed, 0 skipped on serve/cockpit/web/src/__tests__/RepairPanel_1167.test.tsx.
- Coverage (quality-runner scoped): RepairPanel.tsx = 100% statements, 100% branches, 100% functions, 100% lines.
- Lint: clean (eslint 0 violations) for serve/cockpit/web/src/components/RepairPanel.tsx and serve/cockpit/web/src/__tests__/RepairPanel_1167.test.tsx.
- Approach: surgical verification-only builder pass after test-writer retry; confirmed no additional implementation delta needed.

### Post-task Reflection
- Problem: reviewer flagged AC5 proof weakness (confirming -> idle UI boundary), requiring a test-strengthening retry.
- Workaround: re-ran canonical quality-runner scoped checks after test update instead of broad suite noise.
- Pattern: in state-machine UI ACs, callback invocation assertions are insufficient without visible phase-transition assertions.
- Quality: module-scoped test+lint+coverage evidence gave deterministic green gate for handoff.
[[2026-04-29]]
## Review Evidence
### Review Scope
- Live snapshot reviewed: `serve/cockpit/web/src/components/RepairPanel.tsx` and `serve/cockpit/web/src/__tests__/RepairPanel_1167.test.tsx`.
- `RepairPanel` has no downstream production callers yet; current usages are task-owned test references only.

### Test Results
- quality-runner (scoped): 47 passed, 0 failed, 0 skipped on `serve/cockpit/web/src/__tests__/RepairPanel_1167.test.tsx`

### Lint
- clean: true (eslint 0 violations) for `serve/cockpit/web/src/components/RepairPanel.tsx` and `serve/cockpit/web/src/__tests__/RepairPanel_1167.test.tsx`

### Coverage
- module `RepairPanel`: 100%

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| AC1: "Repair" button renders when corruption count > 0 | `RepairPanel_1167.test.tsx:97`, `RepairPanel.tsx:98` | positive-count button render | PASS |
| AC2: "Repair" button hidden when corruption count is 0 | `RepairPanel_1167.test.tsx:113`, `RepairPanel.tsx:91` | zero-count null render | PASS |
| AC3: clicking "Repair" shows confirmation dialog with corruption count in message | `RepairPanel_1167.test.tsx:123`, `:139`, `:149`; `RepairPanel.tsx:36`, `:99` | requestRepair wiring + confirming dialog + count text | PASS |
| AC4: confirming dialog triggers repair execution | `RepairPanel_1167.test.tsx:156`, `:162`; `RepairPanel.tsx:39`, `:41` | confirm button + `confirmRepair()` callback | PASS |
| AC5: cancelling dialog returns to button state | `RepairPanel_1167.test.tsx:180`, `:188`, `:204-205`; `RepairPanel.tsx:29`, `:46`, `:98` | cancel callback + confirming -> idle/button rerender proof | PASS |
| AC6: loading spinner shown during repair execution | `RepairPanel_1167.test.tsx:212`, `:218`; `RepairPanel.tsx:53-54` | repairing branch shows loading and hides idle button | PASS |
| AC7: results display groups outcomes by action | `RepairPanel_1167.test.tsx:228`, `:234`, `:240`, `:246`, `:591`; `RepairPanel.tsx:57-71` | fixed/quarantined/failed section render | PASS |
| AC8: each outcome row shows file path and detail when present | `RepairPanel_1167.test.tsx:258`, `:267`, `:273`, `:279`, `:359`, `:366`, `:378`, `:392`; `RepairPanel.tsx:8-12` | path text, present-detail text, null-detail suppression | PASS |
| AC9: dismiss button in results view clears results and returns to button state | `RepairPanel_1167.test.tsx:286`, `:292`, `:539`, `:549-550`; `RepairPanel.tsx:73`, `:98` | dismiss callback + done -> idle/button rerender proof | PASS |
| AC10: error message displayed when repair execution fails | `RepairPanel_1167.test.tsx:304`, `:313`; `RepairPanel.tsx:80`, `:83` | error branch and rendered message | PASS |
| AC11: dismiss from error state clears error and returns to button state | `RepairPanel_1167.test.tsx:320`, `:326`, `:553`, `:563-564`; `RepairPanel.tsx:84`, `:98` | dismiss callback + error -> idle/button rerender proof | PASS |
| AC12: confirmation dialog has role="dialog" and accessible label | `RepairPanel_1167.test.tsx:338`, `:342`, `:345`, `:349`; `RepairPanel.tsx:32-34` | dialog semantics and label | PASS |

### Pass 1 — CRITICAL
#### Security Review
- No issues found. Scope is a pure React view over hook state using text-node rendering and callback forwarding only.

#### Test Integrity
| Original Test Area | Change Made | Assessment |
|---|---|---|
| AC5 cancel flow | Added rerender proof at `RepairPanel_1167.test.tsx:188`, `:204-205` while preserving direct callback assertion at `:185` | STRENGTHENED |
| AC8 null-detail path | Added structural null-detail assertions at `RepairPanel_1167.test.tsx:359`, `:366`, `:378`, `:392` against `RepairPanel.tsx:12` | STRENGTHENED |
| Remaining AC coverage | Existing AC-aligned assertions remain intact | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|---|---|---|
| Assertion specificity | ADEQUATE | One remaining broad regex at `RepairPanel_1167.test.tsx:149` for the count-in-message proof. |
| Negative/error-path coverage | STRONG | Repairing, error, dismiss, and phase-transition paths are all exercised. |
| Manual mutation reasoning | STRONG | Breaking null-detail suppression or boundary transitions would fail task-owned tests. |
| Test independence | STRONG | Mocks reset between suites; hook remocked per test. |
| Descriptive names | STRONG | AC-aligned and transition-specific naming throughout the suite. |

#### Data Safety
- No issues found.

#### Test Gaps
- No significant untested live branches. The prior AC5 boundary gap is closed in the current snapshot.

#### Builder Process Quality
- FRICTION only: two builder cycles occurred with different approaches; no loop trigger or repeated identical attempt.

### Deductions
- -0.04: AC3 count-in-message assertion uses `/5/` at `RepairPanel_1167.test.tsx:149` rather than an exact rendered string, so it is slightly less mutation-resistant than the rest of the suite.

### Verdict
- PASS | confidence 0.94

### Action
- Advance to docs. No blocking findings remain; only a minor future-tightening opportunity exists for the AC3 count-text assertion.
[[2026-04-29]]
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | Changed files are serve/cockpit/web/src/components/RepairPanel.tsx and RepairPanel_1167.test.tsx — new frontend component; no IN-scope README references this component |
| 2 | Module docstrings | No | N/A | TypeScript files only — no Python modules touched |
| 3 | External attribution | No | N/A | No external patterns used; follows existing HealthBadge.test.tsx conventions already in codebase |
| 4 | Research doc | No | N/A | No research doc produced; task seeded from ideation #1042 — no .owlbear/research/ artifact |
| 5 | Diagram maintenance (describes match) | Yes | Updated | share/diagrams/cockpit.excalidraw describes serve/cockpit/web/src/** — footer updated from dc79a54c to 3a8f23d2 (2026-04-29) |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation request in task body |
| 7 | Deletion detection | No | N/A | No files deleted; RepairPanel.tsx and test file are new additions |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| serve/cockpit/web/src/components/RepairPanel.tsx | OUT | N/A (TypeScript source) |
| serve/cockpit/web/src/__tests__/RepairPanel_1167.test.tsx | OUT | N/A (TypeScript test) |
| share/diagrams/cockpit.excalidraw | IN | Updated footer (describes match) |

### Files Updated
- share/diagrams/cockpit.excalidraw — footer updated to Last verified: 2026-04-29 (3a8f23d2)

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no .owlbear/scratch/1167-* files existed)
[[2026-04-29]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: button renders when count > 0 | Reviewer mapped to test:L97, impl:L98; 2 tests | PASS |
| AC2: button hidden when count = 0 | Reviewer mapped to test:L113, impl:L91; 1 test | PASS |
| AC3: click shows dialog with count | Reviewer mapped to test:L123,L139,L149; 4 tests | PASS |
| AC4: confirm triggers repair | Reviewer mapped to test:L156,L162; 2 tests | PASS |
| AC5: cancel returns to button state | Spot-checked: test:L188-205 proves confirming→idle rerender boundary; 3 tests (strengthened after reviewer FAIL) | PASS |
| AC6: loading spinner during repair | Reviewer mapped to test:L212,L218; 2 tests | PASS |
| AC7: results grouped by action | Reviewer mapped to test:L228-246,L591; 4 tests | PASS |
| AC8: outcome rows show path+detail | Reviewer mapped to test:L258-279,L359-392; null-detail suppression proved; 7 tests | PASS |
| AC9: dismiss clears results | Reviewer mapped to test:L286-292,L539-550; 2 tests | PASS |
| AC10: error message displayed | Reviewer mapped to test:L304,L313; 2 tests | PASS |
| AC11: dismiss from error | Reviewer mapped to test:L320,L326,L553-564; 2 tests | PASS |
| AC12: dialog role+aria-label | Reviewer mapped to test:L338-349, impl:L32-34; 2 tests | PASS |

### Test Results
- Frontend (Vitest): 458 passed, 0 failed (full suite)
- Python (pytest): 3078 passed, 43 failed, 4 skipped — 0 failures in task scope (all in unrelated domains: kanban engine config, storage, mcp-knowledge, mcp-kanban guidance)
- Frontend lint (eslint): clean on RepairPanel.tsx and RepairPanel_1167.test.tsx
- Python lint (ruff): 4 violations, none in task scope

### Reviewer Evidence
Two review passes. First: FAIL at 0.84 (AC5 cancel-path weakness). Second: PASS at 0.94 with complete 12-line AC compliance table, all PASS. Thorough and evidence-based — trusted code-level findings.

### Architect Quality: 4/5
12 refined AC lines with td annotations and builder guidance. Challenger engagement produced 3 additional AC lines (error states + a11y). One minor gap: AC5 phrasing didn't explicitly require UI boundary assertion, causing a reviewer FAIL cycle — resolved by test-writer retry.

### Deduction Breakdown
- AC lines without evidence: 0 (all 12 mapped with file:line references) → 0
- Lint violations in scope: 0 → 0
- AC quality ≤ 3: No (4/5) → 0
- Missing reviewer evidence: No → 0
- Full-suite failures in task scope: 0 → 0

### Confidence: .98
### Action: archive

### Commits (upstream)
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 3d51bc2a | test | RepairPanel_1167.test.tsx | #1167 |
| 2f62ee99 | feat | RepairPanel.tsx | #1167 |
| 9d4c6233 | test | RepairPanel_1167.test.tsx | #1167 |
| 002dbca3 | docs | cockpit.excalidraw | #1167 |