---
id: 1254
title: 'P4-01: RED — Filter accessibility tests'
status: review
priority: important
created: 2026-05-01T04:35:01.084199+00:00
updated: 2026-05-03T16:34:19.325807+00:00
tags:
- phase-4
- scope:cockpit-web
- tdd:red
parent: 1247
depends_on:
- 1253
blocked: false
block_reason:
claimed_at: 2026-05-03T16:34:19.325807+00:00
archival_reason:
archival_refs: []
---

## Acceptance Criteria

- Test suite covering filter accessibility contract:
  - Toggle button has aria-expanded reflecting panelOpen state (td:2)
  - Toggle button has aria-controls="filter-panel" (td:1)
  - FilterPanel has id="filter-panel", role="region", aria-label="Task filters" (td:1)
  - Result count region has aria-live="polite" (td:1)
  - aria-live region announces count only on user-initiated filter changes; polling-driven task updates that change visible count must NOT trigger a new aria-live announcement (td:2)
  - aria-live debounced: announcement fires 300ms after last text input keystroke (td:2)
  - Focus moves to first panel control on expand (td:2)
  - Focus returns to toggle button on collapse — test must verify programmatic focus restoration when focus was inside the panel (e.g. via Escape key or re-render with open=false), not merely via toggle button click which naturally lands focus on the clicked element (td:2)
  - All filter controls have explicit accessible labels — text input, priority select, and tags multi-select currently lack labels; blocked switch is already labeled (td:2)
- All tests fail (RED) — accessibility attributes not yet implemented (td:0)

## In Scope
- Accessibility test cases for FilterPanel and KanbanBoard filter UI
- Focus management behavior tests
- aria-live timing/debounce tests

## Out of Scope
- Accessibility implementation (next task)
- Screen reader integration testing (manual QA)

## Notes for Test-Writer
- The blocked control (`role="switch"` inside `<label>`) already has accessibility semantics — test the other 3 controls for missing labels
- KanbanBoard_1252.test.tsx mocks FilterPanel; these a11y tests need real FilterPanel rendering for panel-level assertions
- For focus-return: cannot rely on toggle click collapse (accidental pass); use re-render with `open={false}` or keyboard trigger while focus is inside panel
- For aria-live user-initiated-only: aria-live region is conceptually separate from the visible result count span; test that re-rendering with changed tasks (simulating polling) does NOT update aria-live textContent when filter state is unchanged

Brief: see parent #1247
[[2026-05-03]]
## Research

**Key findings:** All 10 AC items are testable with existing Vitest + Testing Library + jsdom infrastructure. Zero accessibility attributes currently exist on FilterPanel or the toggle button — all RED tests will fail as required. Testing patterns: attribute assertions for ARIA, `document.activeElement` for focus management, `vi.useFakeTimers()` + `advanceTimersByTime()` for debounce, re-render with new tasks prop to verify user-initiated-only constraint.

**Outcome:** T1 autonomous — standard WAI-ARIA Disclosure pattern + aria-live regions. No architectural decisions needed.

**Doc:** `.owlbear/research/filter-accessibility-tests-1254.md`

**Follow-ups:** None — task is ready for test-writer at backlog.
[[2026-05-03]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Solely RED accessibility tests for filter UI |
| Interface clarity | PASS | Each AC line specifies exact attribute, element, and value |
| Dependency correctness | PASS | #1253 archived/done; component structure exists |
| Module layering | PASS | Test file imports components only, no upward deps |
| TDD compliance | PASS | This IS the RED task; GREEN #1255 depends on it |
| KISS/YAGNI | PASS | Minimal scope — assertions only, no implementation |
| Premise challenge | PASS | No existing a11y test coverage for these components |
| Pattern consistency | PASS | Follows FilterPanel_1250.test.tsx naming/patterns |
| Security surface | N/A | Test-only, no new system boundaries |
| Single domain | PASS | Frontend accessibility testing only |

### Challenge Results
- Challenger: reconsider (0.58)
- Key concerns: (1) aria-live proof mismatch — visible count vs announcement channel, (2) focus-return accidental pass via toggle click, (3) blocked control already labeled
- Architect response: ACCEPTED — refined AC to clarify aria-live separation from visible count, specified programmatic focus restoration requirement, noted existing blocked control label. Added Notes for Test-Writer section with explicit guidance on all three concerns.

### Test Depth
- Max depth: td:2
- Test-writer: PROCEED

### Verdict: APPROVE (after REFINE)
### Action Taken: Refined 3 AC lines to address challenger concerns (aria-live observable separation, focus-return mechanism, existing label acknowledgment). Added "Notes for Test-Writer" section with implementation guidance. Advanced to todo.
[[2026-05-03]]
## Test-Writer Notes
- Test file: serve/cockpit/web/src/__tests__/FilterAccessibility_1254.test.tsx
- Classes: TestFromAC_FilterA11y
- Tests per category:
  - AC1 (aria-expanded): happy x1, edge x2 = 3
  - AC2 (aria-controls): smoke x1 = 1
  - AC3 (id/role/aria-label): smoke x3 = 3
  - AC4 (aria-live present): smoke x2 = 2
  - AC5 (user-initiated only): happy x1, edge x2 = 3
  - AC6 (debounce 300ms): boundary x2, edge x1 = 3
  - AC7 (focus on expand): happy x1, edge x1 = 2
  - AC8 (focus on collapse): happy x1, edge x1 = 2
  - AC9 (accessible labels): happy x4 = 4
- Total: 23 tests, all FAIL
- ESLint: clean
- Commit: a6a878a6

### AC Coverage Table
| AC Line | Tests | Coverage |
|---------|-------|---------|
| Toggle button aria-expanded reflects panelOpen (td:2) | 3 | ✅ |
| Toggle button aria-controls="filter-panel" (td:1) | 1 | ✅ |
| FilterPanel id/role/aria-label (td:1) | 3 | ✅ |
| Result count aria-live="polite" (td:1) | 2 | ✅ |
| aria-live user-initiated only, not polling (td:2) | 3 | ✅ |
| aria-live debounced 300ms (td:2) | 3 | ✅ |
| Focus to first control on expand (td:2) | 2 | ✅ |
| Focus to toggle on collapse/programmatic (td:2) | 2 | ✅ |
| Explicit labels on text input, priority select, tags multi-select (td:2) | 4 | ✅ |

### Strategy Notes
- AC1/AC2/AC4/AC5/AC6: KanbanBoard + mocked FilterPanel (capturedOnFilterChange pattern from KanbanBoard_1252.test.tsx)
- AC3/AC7/AC8/AC9: real FilterPanel imported directly (bypasses vi.mock hoisting)
- AC8 focus-return: tested via Escape-key dispatch + re-render with open=false (avoids accidental pass from toggle click)
- AC5 polling test: rerender with additional task, assert aria-live region text unchanged
[[2026-05-03]]
## Builder Notes
- Files changed: none (local exploratory edits reverted; no commit)
- Scoped verification: `FilterAccessibility_1254.test.tsx` remains RED with 23 failing tests pre-implementation.
- Attempted GREEN implementation was not gateable due test-contract infeasibility in current RED file.

### Rejection Reason (test assumption mismatch)
`FilterAccessibility_1254.test.tsx` globally mocks `../components/FilterPanel` via `vi.mock(...)` near the top of the file, then AC3/AC7/AC8/AC9 tests later attempt to import/render the “real” `FilterPanel` using `await import('../components/FilterPanel')`.

In Vitest, this dynamic import resolves to the mocked module under the active mock, so tests asserting real DOM semantics (panel `id`/`role`/`aria-label`, focus movement within real controls, explicit labels on real controls) are unreachable from source implementation changes alone.

### Evidence Summary
- Lint clean.
- Related durable tests (`KanbanBoard_1252`, `FilterPanel_1250`) pass in scoped run.
- Failures concentrated in AC3/AC7/AC8/AC9 checks that require unmocked `FilterPanel` behavior while the file-level mock is active.

### Test-Writer: what to fix
- Split tests into mocked-vs-real suites OR unmock before “real FilterPanel” assertions (`vi.unmock`/`vi.doUnmock` + isolated import module pattern), so AC3/AC7/AC8/AC9 execute against real component markup and focus behavior.
- Keep AC1/AC2/AC4/AC5/AC6 on mocked KanbanBoard path if desired; run panel-structure/focus/label assertions on an unmocked path.

[[2026-05-03]]
## Test-Writer Notes
- Retry: fixed vi.mock hoisting issue per builder rejection
- Split into two files:
  - `serve/cockpit/web/src/__tests__/FilterAccessibility_1254.test.tsx` — 12 tests (mocked KB path: AC1/AC2/AC4/AC5/AC6)
  - `serve/cockpit/web/src/__tests__/FilterAccessibilityPanel_1254.test.tsx` — 10 tests (real FilterPanel, no vi.mock: AC3/AC7/AC8/AC9)
- Total: 22 tests, all FAIL (removed blocked-switch regression guard that passed before split — it's existing behavior per AC, not new implementation)
- ESLint: clean
- Commit: 506d4da3

### Root cause of original rejection
`vi.mock('../components/FilterPanel')` is hoisted to file top by Vitest. Dynamic `await import('../components/FilterPanel')` inside test bodies in the same file always resolves to the mock — so AC3/AC7/AC8/AC9 could never see real FilterPanel attributes or focus behavior regardless of implementation.

### Fix
Moved AC3/AC7/AC8/AC9 to a new file with no `vi.mock('../components/FilterPanel')`, using static import. Builder can now implement a11y attributes and make those tests pass.

### AC Coverage Table
| AC Line | Tests | File | Status |
|---------|-------|------|--------|
| Toggle button aria-expanded reflects panelOpen (td:2) | 3 | FilterAccessibility_1254 | ✅ all FAIL |
| Toggle button aria-controls="filter-panel" (td:1) | 1 | FilterAccessibility_1254 | ✅ FAIL |
| FilterPanel id/role/aria-label (td:1) | 3 | FilterAccessibilityPanel_1254 | ✅ all FAIL |
| Result count aria-live="polite" (td:1) | 2 | FilterAccessibility_1254 | ✅ all FAIL |
| aria-live user-initiated only (td:2) | 3 | FilterAccessibility_1254 | ✅ all FAIL |
| aria-live debounced 300ms (td:2) | 3 | FilterAccessibility_1254 | ✅ all FAIL |
| Focus to first control on expand (td:2) | 2 | FilterAccessibilityPanel_1254 | ✅ all FAIL |
| Focus to toggle on collapse/Escape (td:2) | 2 | FilterAccessibilityPanel_1254 | ✅ all FAIL |
| Explicit labels: text input, priority select, tags (td:2) | 3 | FilterAccessibilityPanel_1254 | ✅ all FAIL |
[[2026-05-03]]
## Builder Notes
- Implementation: `serve/cockpit/web/src/KanbanBoard.tsx`, `serve/cockpit/web/src/components/FilterPanel.tsx`
- Commit: `3b1c83e0` (`feat: implement filter accessibility behavior (#1254, builder)`)
- Tests (task-scoped): 22 passed, 0 failed
  - `serve/cockpit/web/src/__tests__/FilterAccessibility_1254.test.tsx`
  - `serve/cockpit/web/src/__tests__/FilterAccessibilityPanel_1254.test.tsx`
- Regression tests: 75 passed, 0 failed
  - `serve/cockpit/web/src/__tests__/KanbanBoard.test.tsx`
  - `serve/cockpit/web/src/__tests__/FilterPanel_1250.test.tsx`
- Lint: clean (scoped lint on touched source + task tests)
- Coverage: scoped frontend run reported N/A (not requested/instrumented in this quality-runner mode)

### Evidence Summary
- Added `aria-expanded` + `aria-controls` on filter toggle in KanbanBoard.
- Added always-rendered `aria-live="polite"` region and user-initiated announcement updates.
- Implemented 300ms debounce for text-input-driven announcement updates (with timer reset on rapid input).
- Added FilterPanel semantics: `id="filter-panel"`, `role="region"`, `aria-label="Task filters"`.
- Added explicit labels on controls: text input `aria-label`, `PSelect` label + `aria-label`, `PMultiSelect` label + `aria-label`.
- Implemented focus behavior:
  - on open, focus moves to first panel control unless focus already inside panel;
  - on close, focus returns to filter toggle when prior focus was inside panel;
  - Escape key triggers close callback when provided.

### Post-task Reflection
- Problems faced: initial RED evidence was inconsistent due an incorrect quality-runner test-path invocation format.
- Workaround applied: reran quality-runner with explicit frontend cwd and canonical test paths to establish reliable baseline.
- Pattern discovered: PDS `label` prop is not always reflected as a test-visible DOM attribute; explicit `aria-label` is safer for assertion stability.
- Time sink: reconciling stale historical AC text claiming "all fail" vs live RED baseline.
- Quality gap: frontend scoped quality-runner did not produce module-level coverage instrumentation for touched files in this run mode.