---
id: 1254
title: 'P4-01: RED — Filter accessibility tests'
status: archived
priority: medium
created: 2026-05-01T04:35:01.084199+00:00
updated: 2026-05-03T19:57:37.870586+00:00
tags:
- phase-4
- scope:cockpit-web
- tdd:red
parent: 1247
depends_on:
- 1253
blocked: false
block_reason:
claimed_at:
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
[[2026-05-03]]
## Review Evidence

### Test Results
- quality-runner frontend scoped pass in `serve/cockpit/web`: 22 passed, 0 failed
  - `serve/cockpit/web/src/__tests__/FilterAccessibility_1254.test.tsx`
  - `serve/cockpit/web/src/__tests__/FilterAccessibilityPanel_1254.test.tsx`
- Adjacent regression pass: 75 passed, 0 failed
  - `serve/cockpit/web/src/__tests__/KanbanBoard.test.tsx`
  - `serve/cockpit/web/src/__tests__/FilterPanel_1250.test.tsx`
- VS Code diagnostics: no errors in touched source or task test files

### Lint
- ESLint clean on `serve/cockpit/web/src/KanbanBoard.tsx` and `serve/cockpit/web/src/components/FilterPanel.tsx`

### Coverage
- Scoped frontend coverage metric was unavailable from the quality-runner/vitest configuration in this workspace. This is not the fail reason, but it costs confidence.

### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| `.owlbear/kanban/tasks/1254-p4-01-red-filter-accessibility-tests.md:25` aria-expanded reflects panelOpen | `serve/cockpit/web/src/KanbanBoard.tsx:251`; `serve/cockpit/web/src/__tests__/FilterAccessibility_1254.test.tsx:130,136,145` | PASS |
| `.owlbear/kanban/tasks/1254-p4-01-red-filter-accessibility-tests.md:26` aria-controls=`filter-panel` | `serve/cockpit/web/src/KanbanBoard.tsx:252`; `serve/cockpit/web/src/__tests__/FilterAccessibility_1254.test.tsx:160-163` | PASS |
| `.owlbear/kanban/tasks/1254-p4-01-red-filter-accessibility-tests.md:27` panel id/role/aria-label | Implemented at `serve/cockpit/web/src/components/FilterPanel.tsx:134-136`, but tests split proof across `#filter-panel` at `serve/cockpit/web/src/__tests__/FilterAccessibilityPanel_1254.test.tsx:61` and separate `[role="region"]` queries at `:66` and `:72`, so the same-element contract is under-proved | LAX |
| `.owlbear/kanban/tasks/1254-p4-01-red-filter-accessibility-tests.md:28` aria-live=`polite` present | `serve/cockpit/web/src/KanbanBoard.tsx:258`; `serve/cockpit/web/src/__tests__/FilterAccessibility_1254.test.tsx:170,184` | PASS |
| `.owlbear/kanban/tasks/1254-p4-01-red-filter-accessibility-tests.md:29` user-initiated-only aria-live | Source branches text vs non-text at `serve/cockpit/web/src/KanbanBoard.tsx:226-229`, but every synthetic change in `serve/cockpit/web/src/__tests__/FilterAccessibility_1254.test.tsx:176,201,267,291,309,333,337` is text-only; positive assertions are only non-empty / regex at `:206` and `:271` | FAIL |
| `.owlbear/kanban/tasks/1254-p4-01-red-filter-accessibility-tests.md:30` 300ms debounce | Timeout is set at `serve/cockpit/web/src/KanbanBoard.tsx:227`; negative 299ms proof exists at `serve/cockpit/web/src/__tests__/FilterAccessibility_1254.test.tsx:279`, but the positive proofs after 300ms and rapid input only require non-empty or changed text at `:317` and `:347` | FAIL |
| `.owlbear/kanban/tasks/1254-p4-01-red-filter-accessibility-tests.md:31` focus moves to first panel control | Implementation focuses the text input at `serve/cockpit/web/src/components/FilterPanel.tsx:98`; the test named at `serve/cockpit/web/src/__tests__/FilterAccessibilityPanel_1254.test.tsx:80` only proves focus is somewhere inside the panel via `:114` and `:119` | FAIL |
| `.owlbear/kanban/tasks/1254-p4-01-red-filter-accessibility-tests.md:32` programmatic focus return on collapse | The rerender-close path is covered at `serve/cockpit/web/src/__tests__/FilterAccessibilityPanel_1254.test.tsx:208` and `:244`, but the Escape-path proof is incomplete: the test creates `onClose = vi.fn()` at `:163`, fires Escape at `:185`, forces a closed rerender at `:189`, and the file contains no `expect(onClose...)` assertion while runtime wiring lives at `serve/cockpit/web/src/components/FilterPanel.tsx:139` and `serve/cockpit/web/src/KanbanBoard.tsx:275-276` | FAIL |
| `.owlbear/kanban/tasks/1254-p4-01-red-filter-accessibility-tests.md:33` explicit labels on controls | `serve/cockpit/web/src/components/FilterPanel.tsx:146,154-155,170-171`; `serve/cockpit/web/src/__tests__/FilterAccessibilityPanel_1254.test.tsx:255,269,278` | PASS |
| `.owlbear/kanban/tasks/1254-p4-01-red-filter-accessibility-tests.md:34` RED-only pre-implementation condition | Historical RED-phase requirement; not scored against the current GREEN snapshot | N/A |

### Pass 1 — Critical
#### Test-Writer AC Coverage
- MISSING: none.
- LAX / false-green risk:
  - AC27 same-element semantics.
  - AC29 announcement content and branch proof.
  - AC30 exact debounce-announcement proof.
  - AC31 first-control focus proof.
  - AC32 Escape close wiring proof.

#### Security Review
- No issues in `serve/cockpit/web/src/KanbanBoard.tsx:213-229,251-276` or `serve/cockpit/web/src/components/FilterPanel.tsx:45-171`. No secrets, injection surface, unsafe deserialization, or new dependency risk.

#### Test Integrity
- Builder commit `3b1c83e0` changes only `serve/cockpit/web/src/KanbanBoard.tsx` and `serve/cockpit/web/src/components/FilterPanel.tsx`.
- No builder modification to the `TestFromAC_*` files was found in the builder commit object.
- Small confidence deduction remains because the broader commit range from test-writer commit `506d4da3` crosses unrelated history; immutability proof relies on the builder commit object itself.

#### Test Quality
- WEAK.
- The suite still allows false green on core td:2 contracts:
  - `serve/cockpit/web/src/__tests__/FilterAccessibility_1254.test.tsx:206` and `:317` accept any non-empty announcement text.
  - `serve/cockpit/web/src/__tests__/FilterAccessibility_1254.test.tsx:271` accepts any text containing `1`.
  - `serve/cockpit/web/src/__tests__/FilterAccessibility_1254.test.tsx:347` accepts any changed text, even stale or duplicate content.
  - `serve/cockpit/web/src/__tests__/FilterAccessibilityPanel_1254.test.tsx:119` accepts focus on any descendant instead of the first control.
- These are fail-worthy because the architect explicitly refined the task to avoid accidental aria-live and focus false-greens at `.owlbear/kanban/tasks/1254-p4-01-red-filter-accessibility-tests.md:48-49`.

#### Data Safety
- No issues. Timer cleanup and focus bookkeeping are bounded in `serve/cockpit/web/src/KanbanBoard.tsx:109,218,227` and `serve/cockpit/web/src/components/FilterPanel.tsx:77-82,111`.

#### Test Gaps
- Immediate announcement for non-text filter changes is untested even though the source has a separate branch at `serve/cockpit/web/src/KanbanBoard.tsx:226-229`.
- Escape-to-close wiring is untested end-to-end; the current panel test proves only forced rerender focus restoration, not that Escape actually invokes `onClose` and closes the real board path.

#### Necessity Check
- N/A. No new dependency or integration surface.

#### Builder Process Quality
- FRICTION only, not a loop: two `## Builder Notes` sections at `.owlbear/kanban/tasks/1254-p4-01-red-filter-accessibility-tests.md:127` and `:175`, with an approach change after the test-writer split.
- No prior `## Review Evidence` section exists in the task file, so this is the first review-cycle failure.

### Deductions
- `-0.12` weak/lax AC proof on td:2 contracts
- `-0.02` frontend coverage metric unavailable
- `-0.02` TestFromAC immutability reconstructed from the commit object rather than a clean linear range diff

### Verdict
- FAIL, confidence `0.84`

### Action
- Reject to `backlog`. This is not a source-implementation miss; it is a test-quality / AC-proof failure.
- Required follow-up:
  - strengthen AC29/30 assertions to exact announcement text/count, not non-empty/regex/different-text checks;
  - add non-text filter-change coverage for the priority/tags/blocked immediate-announcement branch;
  - assert the first control specifically for AC31;
  - assert that Escape triggers `onClose` and, ideally, cover the real `KanbanBoard` close wiring for AC32;
  - tighten AC27 so one panel-root element is required to carry `id`, `role`, and `aria-label` together.
[[2026-05-03]]

## Review Rejection — Test Strengthening Required

Reviewer rejected at confidence 0.84 due to test-quality gaps, NOT implementation issues. The 22 tests pass but allow false-green on td:2 contracts. Test-writer must fix the following:

### 1. AC3 same-element semantics (FilterAccessibilityPanel_1254)
Current: three separate queries (`#filter-panel`, `[role="region"]`, `aria-label`). Fix: query ONE element and assert all three attributes on that single element, e.g. `const panel = container.querySelector('#filter-panel'); expect(panel).toHaveAttribute('role', 'region'); expect(panel).toHaveAttribute('aria-label', 'Task filters')`.

### 2. AC5/AC6 exact announcement text (FilterAccessibility_1254)
Current: assertions accept any non-empty / changed text. Fix: assert exact announcement content matching the visible count format (e.g. `"Showing 1 of 2 tasks"` or whatever the implementation produces). Concrete string, not regex/non-empty.

### 3. AC5 non-text filter coverage (FilterAccessibility_1254)
Current: only text-input filter changes tested. Fix: add test that priority/tags/blocked filter changes trigger immediate (non-debounced) aria-live update with correct count text.

### 4. AC7 first-control specificity (FilterAccessibilityPanel_1254)
Current: asserts focus is "inside the panel". Fix: assert `document.activeElement` is specifically the text input (the first focusable control), not just any descendant.

### 5. AC8 Escape triggers onClose (FilterAccessibilityPanel_1254)
Current: fires Escape, rerenders closed, checks focus — but never asserts `expect(onClose).toHaveBeenCalled()`. Fix: add `expect(onClose).toHaveBeenCalledTimes(1)` between the keydown and the rerender.

[[2026-05-03]]
## Architecture Review (cycle 2)

### Verdict: APPROVE → todo

### Context
Reviewer rejected at confidence 0.84 — test-quality / assertion-strength failure, not implementation. All 22 tests pass but assertions are too weak to prevent false-green on td:2 contracts.

### AC Assessment (unchanged)
AC lines remain verifiable as-is. The weakness is in test assertion strength, not AC precision.

| AC Line | Assessment | Action |
|---------|-----------|--------|
| AC1 aria-expanded (td:2) | Tests adequate | None |
| AC2 aria-controls (td:1) | Tests adequate | None |
| AC3 id/role/aria-label (td:1) | Tests query separately — same-element not proved | Guidance added |
| AC4 aria-live present (td:1) | Tests adequate | None |
| AC5 user-initiated only (td:2) | Weak assertions (non-empty); missing non-text coverage | Guidance added |
| AC6 debounce 300ms (td:2) | Weak assertion (non-empty/changed) | Guidance added |
| AC7 focus to first control (td:2) | Asserts "inside panel" not "first control" | Guidance added |
| AC8 focus return on collapse (td:2) | Missing onClose assertion on Escape | Guidance added |
| AC9 explicit labels (td:2) | Tests adequate | None |

### Architecture Notes
- Implementation is sound (reviewer confirmed PASS on source)
- No structural changes needed — only test assertion tightening
- Test-writer has explicit 5-point strengthening guide in task body

### Dependency Analysis
- #1253 (dependency): archived/done — no issue
- Parent #1247: archived — context only

### Challenge: SKIP
Reviewer evidence is concrete and code-referenced. No architectural ambiguity to challenge — this is mechanical test-quality work.
[[2026-05-03]]
## Test-Writer Notes
- Retry: strengthened 5 weak assertion areas per reviewer Required Follow-up
- Files: `serve/cockpit/web/src/__tests__/FilterAccessibility_1254.test.tsx`, `serve/cockpit/web/src/__tests__/FilterAccessibilityPanel_1254.test.tsx`
- Commit: `d8911678`

### Changes made (all in `TestFromAC_` classes — no tests removed)

1. **AC3 same-element** (`FilterAccessibilityPanel_1254`): consolidated 3 separate queries into 1 test that queries `#filter-panel` and asserts `role="region"` + `aria-label="Task filters"` on the single element. (-2 tests, +1 test)
2. **AC5 exact announcement text** (`FilterAccessibility_1254`): changed `not.toBe('')` → `toBe('1 / 2 tasks')` (test 1) and `toMatch(/1/)` → `toBe('1 / 2 tasks')` (test 3)
3. **AC5 non-text filter coverage** (`FilterAccessibility_1254`): added new test asserting priority filter change triggers **immediate** (non-debounced) announcement with exact count `'1 / 2 tasks'`. (+1 test)
4. **AC6 exact announcement text** (`FilterAccessibility_1254`): changed `not.toBe('')` → `toBe('1 / 2 tasks')` (test 2) and `not.toBe(textBefore)` → `toBe('1 / 2 tasks')` (test 3)
5. **AC7 first-control specificity** (`FilterAccessibilityPanel_1254`): changed `panelRegion?.contains(activeEl)` → `document.activeElement === textInput` (the text input explicitly)
6. **AC8 Escape→onClose** (`FilterAccessibilityPanel_1254`): added `expect(onClose).toHaveBeenCalledTimes(1)` after `fireEvent.keyDown(Escape)`

### Test outcome
- Total: 21 tests (FilterAccessibility: 13, FilterAccessibilityPanel: 8)
- All 21 PASS against current implementation — implementation already handles all strengthened contracts
- ESLint: clean

### Step 1b.1 — Direct-to-Review Advance
Reviewer's Required Follow-up contained ONLY test-proof gaps; all new/strengthened tests pass. Builder skip — advancing to review.
[[2026-05-03]]
## Builder Notes
- Implementation: no additional code changes required in this cycle; existing implementation in serve/cockpit/web/src/KanbanBoard.tsx and serve/cockpit/web/src/components/FilterPanel.tsx already satisfies strengthened tests.
- Tests: 21 TestFromAC passed (0 failed)
  - serve/cockpit/web/src/__tests__/FilterAccessibility_1254.test.tsx
  - serve/cockpit/web/src/__tests__/FilterAccessibilityPanel_1254.test.tsx
- Lint: clean
  - npx eslint src/KanbanBoard.tsx src/components/FilterPanel.tsx src/__tests__/FilterAccessibility_1254.test.tsx src/__tests__/FilterAccessibilityPanel_1254.test.tsx
- Coverage (scoped, task tests only):
  - Statements: 70.14% (235/335)
  - Branches: 68.91% (204/296)
  - Functions: 40.00% (16/40)
  - Lines: 70.69% (152/215)
- Coverage note: broader combined coverage run for adjacent durable tests was interrupted in this terminal environment (exit 130), so only stable scoped module coverage metrics are recorded in this cycle.
- Evidence summary: all reviewer-requested test-strengthening points are now present and passing; builder performed verification-only rerun and no new implementation changes were necessary.

### Post-task Reflection
- Problem faced: quality-runner and some coverage invocations returned inconsistent/interrupt-driven results in this session.
- Workaround applied: used direct local vitest binary for stable scoped coverage capture.
- Pattern discovered: for frontend coverage in this workspace, `./node_modules/.bin/vitest` is more reliable than `npx vitest` under tool orchestration.
- Quality gap: could not capture broader coverage aggregation due repeated run interruption (exit 130).
[[2026-05-03]]
## Review Evidence

### Test Results
- quality-runner scoped frontend run in `serve/cockpit/web`: 96 passed, 0 failed
  - task suites: `serve/cockpit/web/src/__tests__/FilterAccessibility_1254.test.tsx` (13) and `serve/cockpit/web/src/__tests__/FilterAccessibilityPanel_1254.test.tsx` (8)
  - adjacent regression suites: `serve/cockpit/web/src/__tests__/KanbanBoard.test.tsx` (35) and `serve/cockpit/web/src/__tests__/FilterPanel_1250.test.tsx` (40)
- VS Code diagnostics: no errors in `serve/cockpit/web/src/KanbanBoard.tsx`, `serve/cockpit/web/src/components/FilterPanel.tsx`, or the two task test files

### Lint
- ESLint clean on `serve/cockpit/web/src/KanbanBoard.tsx`, `serve/cockpit/web/src/components/FilterPanel.tsx`, `serve/cockpit/web/src/__tests__/FilterAccessibility_1254.test.tsx`, and `serve/cockpit/web/src/__tests__/FilterAccessibilityPanel_1254.test.tsx`

### Coverage
- Scoped frontend coverage is unavailable in this session. quality-runner reproduced a vitest v8 instrumentation hang / exit 130 on scoped coverage attempts. This is not the fail reason.

### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| `.owlbear/kanban/tasks/1254-p4-01-red-filter-accessibility-tests.md:25` aria-expanded reflects `panelOpen` | `serve/cockpit/web/src/KanbanBoard.tsx:251`; `serve/cockpit/web/src/__tests__/FilterAccessibility_1254.test.tsx:130` | PASS |
| `.owlbear/kanban/tasks/1254-p4-01-red-filter-accessibility-tests.md:26` toggle has `aria-controls="filter-panel"` | `serve/cockpit/web/src/KanbanBoard.tsx:252`; `serve/cockpit/web/src/__tests__/FilterAccessibility_1254.test.tsx:160` | PASS |
| `.owlbear/kanban/tasks/1254-p4-01-red-filter-accessibility-tests.md:27` panel root carries `id` / `role` / `aria-label` together | `serve/cockpit/web/src/components/FilterPanel.tsx:134-136`; `serve/cockpit/web/src/__tests__/FilterAccessibilityPanel_1254.test.tsx:59` | PASS |
| `.owlbear/kanban/tasks/1254-p4-01-red-filter-accessibility-tests.md:28` result-count live region has `aria-live="polite"` | `serve/cockpit/web/src/KanbanBoard.tsx:258`; `serve/cockpit/web/src/__tests__/FilterAccessibility_1254.test.tsx:170` | PASS |
| `.owlbear/kanban/tasks/1254-p4-01-red-filter-accessibility-tests.md:29` polling-driven task updates that change visible count must not create a new announcement | positive user-change proof exists at `serve/cockpit/web/src/__tests__/FilterAccessibility_1254.test.tsx:196`; source only writes announcements inside `handleFilterChange` at `serve/cockpit/web/src/KanbanBoard.tsx:213-230`; but the negative polling test at `serve/cockpit/web/src/__tests__/FilterAccessibility_1254.test.tsx:210-243` explicitly keeps filters inactive (`:212`), so it does not exercise the AC's named active-filter / visible-count-change permutation | FAIL |
| `.owlbear/kanban/tasks/1254-p4-01-red-filter-accessibility-tests.md:30` announcement fires 300ms after the last text keystroke | single-input boundaries are covered at `serve/cockpit/web/src/__tests__/FilterAccessibility_1254.test.tsx:294-333`; however the rapid-keystroke proof at `:336-363` never inspects the stale-first-timer boundary. `serve/cockpit/web/src/utils/filterTasks.ts:14-20` makes `"A"` match 2 tasks and `"Al"` match 1, so a bug that fails to clear the first timer at `serve/cockpit/web/src/KanbanBoard.tsx:217-227` can still announce early and be overwritten before the only final assertion at `:363` | FAIL |
| `.owlbear/kanban/tasks/1254-p4-01-red-filter-accessibility-tests.md:31` focus moves to the first panel control on expand | `serve/cockpit/web/src/components/FilterPanel.tsx:98`; `serve/cockpit/web/src/__tests__/FilterAccessibilityPanel_1254.test.tsx:71` | PASS |
| `.owlbear/kanban/tasks/1254-p4-01-red-filter-accessibility-tests.md:32` programmatic focus return on collapse | `serve/cockpit/web/src/components/FilterPanel.tsx:79,139`; `serve/cockpit/web/src/__tests__/FilterAccessibilityPanel_1254.test.tsx:151,198` | PASS |
| `.owlbear/kanban/tasks/1254-p4-01-red-filter-accessibility-tests.md:33` explicit labels on text input / priority / tags | `serve/cockpit/web/src/components/FilterPanel.tsx:146,154-155,170-171`; `serve/cockpit/web/src/__tests__/FilterAccessibilityPanel_1254.test.tsx:245,259,268` | PASS |
| `.owlbear/kanban/tasks/1254-p4-01-red-filter-accessibility-tests.md:34` all tests fail in RED | historical td:0 line; not a GREEN gate in the current snapshot | N/A |

### Pass 1 — Critical
#### Test-Writer AC Coverage
- FAIL: AC5 still lacks a TestFromAC proof for the exact regression named by the AC: active filters already applied, polling changes the visible count, aria-live text stays unchanged.
- FAIL: AC6 still lacks a discriminating rapid-keystroke assertion at the stale-first-timer boundary; the current final-state-only check can false-green if the first timer fires early and the second timer overwrites it.
- PASS: AC1, AC2, AC3, AC4, AC7, AC8, and AC9 are adequately covered for the current AC wording.

#### Security Review
- No issues in `serve/cockpit/web/src/KanbanBoard.tsx`, `serve/cockpit/web/src/components/FilterPanel.tsx`, or the task tests. No secrets, injection paths, unsafe deserialization, path handling, or new dependency surface.

#### Test Integrity
- Builder commit `3b1c83e0` touches only `serve/cockpit/web/src/KanbanBoard.tsx` and `serve/cockpit/web/src/components/FilterPanel.tsx`.
- Retry test-writer commit `d8911678` touches only `serve/cockpit/web/src/__tests__/FilterAccessibility_1254.test.tsx` and `serve/cockpit/web/src/__tests__/FilterAccessibilityPanel_1254.test.tsx`.
- No builder weakening of `TestFromAC_*` assertions was found.

#### Test Quality
- WEAK overall, due specifically to the remaining td:2 proof gaps in AC5 and AC6.
- This is a proof-quality failure, not an implementation failure. Current source behavior appears consistent with the intended contract; the issue is that the test suite still does not prove both contracts strongly enough.

#### Data Safety
- No issues. Timeout cleanup is bounded at `serve/cockpit/web/src/KanbanBoard.tsx:109,217` and focus bookkeeping is local to `serve/cockpit/web/src/components/FilterPanel.tsx:49-98`.

#### Test Gaps
- AC5: add a polling rerender that starts from an already-active filter, changes the visible count, and proves the live-region text remains the pre-poll value.
- AC6: tighten the rapid-keystroke test so the intermediate stale-timer boundary is observed directly.

#### Necessity Check
- N/A. No new dependency or integration surface.

#### Builder Process Quality
- CLEAN. No builder loop problem was found.
- This task already contains one prior `## Review Evidence` section at `.owlbear/kanban/tasks/1254-p4-01-red-filter-accessibility-tests.md:205`, so this rejection is the second review-cycle fail and routes to backlog per the reviewer loop-breaker rule.

### Deductions
- `-0.08` AC5 active-filter polling permutation not proved by TestFromAC
- `-0.08` AC6 last-keystroke / stale-timer boundary still under-proved
- `-0.02` scoped frontend coverage unavailable in this session

### Verdict
- FAIL, confidence `0.82`

### Action
- Reject to `backlog`.
- Required follow-up:
  - AC5: start from an active filter, capture the live-region text, rerender tasks so the visible count changes, and assert the visible count updates while the aria-live text does not.
  - AC6: use successive text inputs that produce different counts (`A` => `2 / 2 tasks`, `Al` => `1 / 2 tasks` with current fixtures), assert no announcement at the stale-first-timer boundary, then assert the exact final text only after 300ms from the second keystroke.
  - Keep this with the test-writer / architect path. Builder source changes are not the blocker.

### Post-task Reflection
- Source inspection narrowed AC5 from a likely implementation concern to a proof-only gap; static code helped, but it did not replace missing TestFromAC coverage.
- Rapid debounce tests need an intermediate boundary assertion, not just a before-window check and a final-state check.
- Choosing successive inputs with different filtered counts makes timer-reset regressions observable instead of silently overwritten.
[[2026-05-03]]
## Architecture Review (cycle 3)

### Verdict: APPROVE → todo

### Context
Second reviewer rejection at confidence 0.82. Two remaining proof gaps in test assertions — NOT implementation or AC issues. Both gaps are precisely identified with line-level source/test evidence.

### AC Assessment (unchanged from cycle 2)
AC lines remain correctly scoped. Only test assertion tightening is needed.

| AC Line | Assessment | Action |
|---------|-----------|--------|
| AC1–AC4, AC7–AC9 | Reviewer PASS on both cycles | None |
| AC5 user-initiated only (td:2) | Proof gap: polling test uses inactive filters — doesn't exercise "active filter + visible count changes" permutation | Guidance below |
| AC6 debounce 300ms (td:2) | Proof gap: rapid-keystroke test has no assertion at first-timer boundary (t=300 from first keystroke) | Guidance below |

### Architecture Notes
- Implementation is confirmed sound by both reviewer cycles
- Source at `KanbanBoard.tsx:213-230` only announces inside `handleFilterChange` — inherently user-initiated-only. But the TestFromAC must prove this contract survives future refactoring (e.g. a useEffect that recalculates on task changes)
- Timer cancel at `KanbanBoard.tsx:217-219` correctly clears the previous timer, but the rapid-keystroke test must prove it at the boundary

### Dependency Analysis
- #1253: done — no issue
- Parent #1247: context only

### Challenge: SKIP
Reviewer evidence is concrete, code-referenced, and unambiguous. No architectural ambiguity — purely mechanical test-assertion work.

### Test Depth
- Max depth: td:2
- Test-writer: PROCEED

### Guidance for Test-Writer (2 fixes only)

**Fix 1 — AC5 active-filter polling permutation:**
In `FilterAccessibility_1254.test.tsx`, add a test (or modify the existing polling test):
1. Render board, open panel, apply filter `{ text: 'A', ... }` via `capturedOnFilterChange`
2. Advance timer 300ms so announcement fires ('2 / 2 tasks')
3. Capture `liveRegion.textContent` 
4. Rerender with an additional task that ALSO matches 'A' (e.g. title: 'Another task')
5. Assert `liveRegion.textContent` is STILL '2 / 2 tasks' — NOT updated to '3 / 3 tasks'
This proves polling-driven visible-count changes don't trigger re-announcement.

**Fix 2 — AC6 stale-first-timer boundary assertion:**
In the rapid-keystroke test, after the second keystroke at t=100, add an assertion at the stale-first-timer boundary:
1. After second keystroke, advance to t=300 (200ms more from current t=100 position) — this is where the FIRST timer would fire if not cancelled
2. Assert `liveRegion.textContent === textBefore` (no announcement — first timer was cancelled)
3. Then advance remaining 100ms to t=400 (300ms after second keystroke)
4. Assert final announcement '1 / 2 tasks'

Current test jumps from t=200→t=400 with a single `advanceTimersByTime(200)`. Split that into `advanceTimersByTime(100)` + assert + `advanceTimersByTime(100)` + assert.

### Action Taken
Approved to todo with precise 2-fix guidance. No AC changes needed — implementation is correct, only test proofs need tightening.
[[2026-05-03]]
## Test-Writer Notes
- Retry (cycle 3): added 2 assertions / 1 new test for reviewer gaps — builder skip, direct-to-review advance
- Files modified: `serve/cockpit/web/src/__tests__/FilterAccessibility_1254.test.tsx`
- Commit: `bdba1436`
- Tests: 22 passed, 0 failed (14 in FilterAccessibility_1254, 8 in FilterAccessibilityPanel_1254)
- ESLint: clean

### Changes made (surgical fill — no existing tests removed)

**Fix 1 — AC5 active-filter polling permutation** (new test added):
- Test: `'aria-live does not update when polling changes visible count while active filter is already applied'`
- Scenario: apply text filter 'A' → advance 300ms → announcement fires ('2 / 2 tasks') → rerender with TASK_ANOTHER (also matches 'A') → assert aria-live text unchanged
- Proves the active-filter + visible-count-change polling permutation that the prior test missed (prior test used inactive filters)

**Fix 2 — AC6 stale-first-timer boundary assertion** (rapid-keystroke test modified):
- Split the final `advanceTimersByTime(200)` into `advanceTimersByTime(100)` + assert + `advanceTimersByTime(100)` + assert
- At t=300 (stale first-timer boundary): assert `liveRegion.textContent === textBefore` — proves first timer was cancelled
- At t=400 (300ms after second keystroke): assert `'1 / 2 tasks'` — proves second timer fired correctly

### Step 1b.1 — Direct-to-Review Advance
- Reviewer's Required Follow-up contained ONLY test-proof gaps; no implementation fixes needed
- All new/modified tests PASS against current implementation (source already handles both contracts)
- Builder has no work to do → advancing directly to review
[[2026-05-03]]
## Builder Notes
- Implementation: no new source edits in this cycle.
- Verification scope: `serve/cockpit/web/src/__tests__/FilterAccessibility_1254.test.tsx`, `serve/cockpit/web/src/__tests__/FilterAccessibilityPanel_1254.test.tsx`, `serve/cockpit/web/src/KanbanBoard.tsx`, `serve/cockpit/web/src/components/FilterPanel.tsx`.
- Tests: 22 passed, 0 failed, 0 skipped (scoped Vitest run).
- Lint: clean (scoped ESLint run).
- Coverage (scoped statements): overall 73.06%; `src/KanbanBoard.tsx` 67.9%; `src/components/FilterPanel.tsx` 74.16%.
- Approach: verification-only builder pass, since latest test-writer retry already strengthened AC5/AC6 proofs and all task-scoped checks pass against existing implementation.

### Evidence Summary
- No builder test modifications.
- No builder source modifications.
- Current implementation already satisfies the strengthened task contracts in the latest `TestFromAC_*` assertions.

### Post-task Reflection
- Problem faced: historical task thread contains multiple prior rejection cycles, so stale evidence can mislead if not re-verified.
- Workaround applied: ran fresh scoped quality-runner evidence against the current test and source snapshot.
- Pattern discovered: this cycle is a pure proof-verification pass; forcing additional source edits would add risk without increasing AC confidence.
[[2026-05-03]]
## Review Evidence

### Test Results
- quality-runner scoped frontend pass: 97 passed, 0 failed
  - task suites: serve/cockpit/web/src/__tests__/FilterAccessibility_1254.test.tsx (14) and serve/cockpit/web/src/__tests__/FilterAccessibilityPanel_1254.test.tsx (8)
  - adjacent regression suites: serve/cockpit/web/src/__tests__/KanbanBoard.test.tsx (35) and serve/cockpit/web/src/__tests__/FilterPanel_1250.test.tsx (40)
- VS Code diagnostics: no errors in serve/cockpit/web/src/KanbanBoard.tsx, serve/cockpit/web/src/components/FilterPanel.tsx, or the two task test files

### Lint
- ESLint clean on serve/cockpit/web/src/KanbanBoard.tsx, serve/cockpit/web/src/components/FilterPanel.tsx, serve/cockpit/web/src/__tests__/FilterAccessibility_1254.test.tsx, and serve/cockpit/web/src/__tests__/FilterAccessibilityPanel_1254.test.tsx

### Coverage
- Scoped frontend coverage was unavailable from quality-runner in this session. This is not the fail reason, but it reduces confidence.

### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 aria-expanded reflects panelOpen | serve/cockpit/web/src/KanbanBoard.tsx:251; serve/cockpit/web/src/__tests__/FilterAccessibility_1254.test.tsx:130,136,145 | PASS |
| AC2 aria-controls="filter-panel" | serve/cockpit/web/src/KanbanBoard.tsx:252; serve/cockpit/web/src/__tests__/FilterAccessibility_1254.test.tsx:160 | PASS |
| AC3 panel root carries id, role, and aria-label together | serve/cockpit/web/src/components/FilterPanel.tsx:134-136; serve/cockpit/web/src/__tests__/FilterAccessibilityPanel_1254.test.tsx:59 | PASS |
| AC4 result count live region has aria-live="polite" | serve/cockpit/web/src/KanbanBoard.tsx:258; serve/cockpit/web/src/__tests__/FilterAccessibility_1254.test.tsx:170,184 | PASS |
| AC5 only user-initiated filter changes announce; polling does not create a new announcement | serve/cockpit/web/src/KanbanBoard.tsx:213-230; serve/cockpit/web/src/__tests__/FilterAccessibility_1254.test.tsx:206,290 | PASS |
| AC6 announcement fires 300ms after last text keystroke | serve/cockpit/web/src/KanbanBoard.tsx:227; serve/cockpit/web/src/__tests__/FilterAccessibility_1254.test.tsx:383-417 | PASS |
| AC7 focus moves to the first panel control on expand | serve/cockpit/web/src/components/FilterPanel.tsx:98; serve/cockpit/web/src/__tests__/FilterAccessibilityPanel_1254.test.tsx:71 | PASS |
| AC8 focus returns to the toggle on programmatic collapse | serve/cockpit/web/src/components/FilterPanel.tsx:79,139; serve/cockpit/web/src/KanbanBoard.tsx:274; serve/cockpit/web/src/__tests__/FilterAccessibilityPanel_1254.test.tsx:151,198 | PASS |
| AC9 filter controls have explicit accessible labels | Source labels exist at serve/cockpit/web/src/components/FilterPanel.tsx:146,154-155,170-171, but the proof in serve/cockpit/web/src/__tests__/FilterAccessibilityPanel_1254.test.tsx:250-251,264,273 only checks attribute presence. Empty aria-label or label values would still pass. | FAIL |
| AC10 RED-only condition | Historical td:0 requirement; not a GREEN gate in the current snapshot | N/A |

### Pass 1 - Critical
#### Test-Writer AC Coverage
- FAIL: AC9 is only covered by attribute-existence checks.
- The current assertions use hasAttribute('aria-label'), hasAttribute('aria-labelledby'), and hasAttribute('label') at serve/cockpit/web/src/__tests__/FilterAccessibilityPanel_1254.test.tsx:250-251,264,273.
- That does not prove a usable accessible name. A regression to aria-label="" or label="" would stay green.
- PASS: AC1 through AC8 are adequately covered for the current task wording.

#### Security Review
- No issues in serve/cockpit/web/src/KanbanBoard.tsx or serve/cockpit/web/src/components/FilterPanel.tsx. No secrets, injection sinks, unsafe deserialization, path handling, or new dependency surface in scope.

#### Test Integrity
- git show confirms builder commit 3b1c83e0 touched only serve/cockpit/web/src/KanbanBoard.tsx and serve/cockpit/web/src/components/FilterPanel.tsx.
- git show confirms later test-writer commits d8911678 and bdba1436 touched only the task test files.
- No builder weakening or removal of TestFromAC assertions was found.

#### Test Quality
- WEAK, due to AC9.
- The source sets explicit non-empty label values at serve/cockpit/web/src/components/FilterPanel.tsx:146,154-155,170-171, but the current tests do not prove those values remain usable.
- Divergence from code-reader: code-reader also flagged a pending-debounce polling interaction as a possible gap. I am treating that as informational rather than fail-worthy because the current AC and architect guidance do not define a separate mid-debounce polling freshness contract. AC5 and AC6 as written are otherwise proved.

#### Data Safety
- No issues. Timeout cleanup and local focus bookkeeping are bounded in serve/cockpit/web/src/KanbanBoard.tsx and serve/cockpit/web/src/components/FilterPanel.tsx.

#### Test Gaps
- Fail-worthy gap: AC9 accessible-name proof is not discriminating enough.
- Informational only: if architecture later widens the announcement contract, consider adding a polling-during-pending-debounce test.

#### Necessity Check
- N/A. No dependency or integration expansion in scope.

#### Builder Process Quality
- No builder loop issue found.
- This task already contains two prior Review Evidence sections at .owlbear/kanban/tasks/1254-p4-01-red-filter-accessibility-tests.md:205 and :392, so this rejection is a third review-cycle failure and routes to backlog under the loop-breaker rule.

### Deductions
- -0.09 AC9 proof is weak because it checks only attribute existence, not a usable accessible name
- -0.02 scoped frontend coverage unavailable in this session

### Verdict
- FAIL, confidence 0.89

### Action
- Reject to backlog.
- Required follow-up:
  - strengthen AC9 to assert non-empty accessible names, not bare attribute presence
  - for the text input, assert the actual accessible name or exact aria-label value
  - for the priority and tags controls, assert the actual accessible name or exact aria-label value
  - keep the rest of the task intact; the remaining blocker is test proof quality, not implementation behavior

### Post-task Reflection
- Green task and regression suites can still hide a false green when a td:2 accessibility contract is checked with attribute-presence assertions.
- Commit-surface reconstruction was clean here: the builder commit is source-only, and the later task commits are test-only.
- When a subagent finds a broader robustness concern, keep the gate tied to the written AC unless the task artifact explicitly broadens the contract.
[[2026-05-03]]
## Architecture Review (cycle 4)

### Verdict: APPROVE → todo

### Context
Third reviewer rejection at confidence 0.89 — single remaining gap: AC9 accessible-label tests check attribute *presence* (`hasAttribute`) rather than asserting non-empty, usable accessible names. Implementation is confirmed sound across all three review cycles.

### AC Assessment (unchanged)
AC lines remain correctly scoped. Only AC9 test assertion needs final tightening.

| AC Line | Assessment | Action |
|---------|-----------|--------|
| AC1–AC8 | Reviewer PASS on all three cycles | None |
| AC9 explicit labels (td:2) | Tests use `hasAttribute('aria-label')` / `hasAttribute('label')` — empty string `""` would pass | Guidance below |

### Architecture Notes
- Implementation sets concrete values at `FilterPanel.tsx:148` (`aria-label="Search tasks"`), `:154-155` (`label="Priority"`, `aria-label="Priority"`), `:170-171` (`label="Tags"`, `aria-label="Tags"`)
- Test assertions at `FilterAccessibilityPanel_1254.test.tsx:250-251,264,273` only call `hasAttribute()` — a regression to empty-string labels would stay green
- No structural or AC changes needed

### Dependency Analysis
- #1253: done — no issue
- Parent #1247: context only

### Challenge: SKIP
Reviewer evidence is concrete and code-referenced. This is a single-line assertion-strength fix with no architectural ambiguity.

### Test Depth
- Max depth: td:2
- Test-writer: PROCEED

### Guidance for Test-Writer (1 fix, 3 assertions)

In `FilterAccessibilityPanel_1254.test.tsx`, strengthen the AC9 assertions to verify non-empty accessible names:

**Text input** (line ~250-251): Replace `hasAttribute('aria-label')` check with:
```ts
expect(textInput.getAttribute('aria-label')).toBe('Search tasks')
```

**Priority select** (line ~264): Replace `hasAttribute('label') || hasAttribute('aria-label')` with:
```ts
expect(pSelect!.getAttribute('aria-label')).toBe('Priority')
```

**Tags multi-select** (line ~273): Replace `hasAttribute('label') || hasAttribute('aria-label')` with:
```ts
expect(pMultiSelect!.getAttribute('aria-label')).toBe('Tags')
```

These match the concrete values already in `FilterPanel.tsx`. Any regression to empty or removed labels will now fail.

### Action Taken
Approved to todo with single-fix guidance. No AC changes needed — implementation is correct, only 3 attribute-existence assertions need exact-value assertions.
[[2026-05-03]]
## Test-Writer Notes (cycle 4)
- Retry: tightened AC9 label assertions per architect cycle-4 guidance — builder skip, direct-to-review advance
- File modified: `serve/cockpit/web/src/__tests__/FilterAccessibilityPanel_1254.test.tsx`
- Commit: `235c4020`
- Tests: 22 passed, 0 failed (FilterAccessibility_1254: 13, FilterAccessibilityPanel_1254: 9)
- ESLint: clean

### Single change made (3 assertions, AC9 only)
Replaced bare `hasAttribute()` presence checks with exact-value assertions:
1. **Text input**: `textInput.getAttribute('aria-label')` → `toBe('Search tasks')`
2. **Priority select**: `pSelect!.getAttribute('aria-label')` → `toBe('Priority')`
3. **Tags multi-select**: `pMultiSelect!.getAttribute('aria-label')` → `toBe('Tags')`

Any regression to empty-string or removed labels now fails the suite.

### AC Coverage (unchanged from cycle 3)
| AC Line | Tests | Status |
|---------|-------|--------|
| AC1 aria-expanded | 3 | ✅ |
| AC2 aria-controls | 1 | ✅ |
| AC3 id/role/aria-label (same element) | 1 | ✅ |
| AC4 aria-live present | 2 | ✅ |
| AC5 user-initiated only + non-text branch | 3 | ✅ |
| AC6 debounce 300ms + stale-timer boundary | 3 | ✅ |
| AC7 focus to first control | 2 | ✅ |
| AC8 focus return on collapse/Escape | 2 | ✅ |
| AC9 explicit accessible labels (exact values) | 3 | ✅ |

### Step 1b.1 — Direct-to-Review Advance
Reviewer's cycle 4 Required Follow-up was a single assertion-strength fix. All tests pass against current implementation. Builder has no work → advancing to review.
[[2026-05-03]]
## Builder Notes
- Implementation: no source changes required in this builder pass.
- Files changed: none.
- Tests: 97 passed, 0 failed (scoped frontend run).
  - task suites: `serve/cockpit/web/src/__tests__/FilterAccessibility_1254.test.tsx` (14), `serve/cockpit/web/src/__tests__/FilterAccessibilityPanel_1254.test.tsx` (8)
  - adjacent regression suites: `serve/cockpit/web/src/__tests__/KanbanBoard.test.tsx` (35), `serve/cockpit/web/src/__tests__/FilterPanel_1250.test.tsx` (40)
- Lint: clean.
  - `serve/cockpit/web/src/KanbanBoard.tsx`
  - `serve/cockpit/web/src/components/FilterPanel.tsx`
  - `serve/cockpit/web/src/__tests__/FilterAccessibility_1254.test.tsx`
  - `serve/cockpit/web/src/__tests__/FilterAccessibilityPanel_1254.test.tsx`
- Coverage: not requested in this scoped quality-runner invocation.

### Evidence Summary
- Current implementation already satisfies latest strengthened `TestFromAC_*` assertions.
- No additional builder code edits were necessary; verification-only builder pass completed with clean test and lint results.

### Fixes Applied
- None in this cycle (verification-only pass).
[[2026-05-03]]
## Review Evidence

### Test Results
- quality-runner scoped frontend run in serve/cockpit/web: 97 passed, 0 failed, 0 skipped
  - task suites: serve/cockpit/web/src/__tests__/FilterAccessibility_1254.test.tsx (14) and serve/cockpit/web/src/__tests__/FilterAccessibilityPanel_1254.test.tsx (8)
  - adjacent regression suites: serve/cockpit/web/src/__tests__/KanbanBoard.test.tsx (35) and serve/cockpit/web/src/__tests__/FilterPanel_1250.test.tsx (40)
- VS Code diagnostics: no errors in serve/cockpit/web/src/KanbanBoard.tsx, serve/cockpit/web/src/components/FilterPanel.tsx, or the two task test files

### Lint
- ESLint clean on serve/cockpit/web/src/KanbanBoard.tsx, serve/cockpit/web/src/components/FilterPanel.tsx, serve/cockpit/web/src/__tests__/FilterAccessibility_1254.test.tsx, and serve/cockpit/web/src/__tests__/FilterAccessibilityPanel_1254.test.tsx

### Coverage
- Frontend coverage artifact generated at serve/cockpit/web/coverage/
- KanbanBoard.tsx: 84.65% statements, 81.02% branches, 76.19% functions, 85.29% lines
- FilterPanel.tsx: 85.00% statements, 72.27% branches, 84.21% functions, 92.40% lines
- The gate here is diff-scoped, not whole-file scoped. The builder-owned accessibility lines in both files are directly exercised by the task suites and adjacent regressions.

### Pass 1 - Critical
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Evidence | Status |
|---------|-------------|----------|--------|
| AC1 aria-expanded reflects panelOpen | FilterAccessibility_1254.test.tsx:130 | KanbanBoard.tsx:251; exact false/true/false assertions in the AC1 block | PASS |
| AC2 aria-controls="filter-panel" | FilterAccessibility_1254.test.tsx:160 | KanbanBoard.tsx:252 | PASS |
| AC3 panel root carries id, role, and aria-label together | FilterAccessibilityPanel_1254.test.tsx:59 | FilterPanel.tsx:134-136 | PASS |
| AC4 result-count live region has aria-live="polite" | FilterAccessibility_1254.test.tsx:170 | KanbanBoard.tsx:258 | PASS |
| AC5 only user-initiated filter changes announce; polling does not re-announce | FilterAccessibility_1254.test.tsx:196,246,290 | KanbanBoard.tsx:223,227,258; exact `1 / 2 tasks` and `2 / 2 tasks` assertions plus active-filter polling no-update proof | PASS |
| AC6 announcement fires 300ms after last text keystroke | FilterAccessibility_1254.test.tsx:362,383 | KanbanBoard.tsx:223,227; exact 300ms text and stale-first-timer boundary proof | PASS |
| AC7 focus moves to first panel control on expand | FilterAccessibilityPanel_1254.test.tsx:71 | FilterPanel.tsx:98; exact activeElement equals text input at FilterAccessibilityPanel_1254.test.tsx:108 | PASS |
| AC8 programmatic focus return on collapse | FilterAccessibilityPanel_1254.test.tsx:151 | FilterPanel.tsx:79,139; KanbanBoard.tsx:276; Escape path asserts onClose at FilterAccessibilityPanel_1254.test.tsx:175 | PASS |
| AC9 explicit accessible labels on text input, priority, tags | FilterAccessibilityPanel_1254.test.tsx:245,252,259 | FilterPanel.tsx:146,154-155,170-171; exact aria-label value assertions at FilterAccessibilityPanel_1254.test.tsx:249,256,263 | PASS |
| RED-only meta line | historical td:0 line | Not a GREEN gate in the current snapshot | N/A |

#### Security Review
- No issues. The changed code is local UI state, focus management, and aria-live behavior only; no new secrets, injection sinks, path handling, deserialization, or dependency surface.

#### Test Integrity
- Builder commit 3b1c83e0 touched only serve/cockpit/web/src/KanbanBoard.tsx and serve/cockpit/web/src/components/FilterPanel.tsx.
- Test-writer commits 506d4da3, d8911678, bdba1436, and 235c4020 touched only the task test files.
- No builder weakening or removal of TestFromAC assertions was found.

#### Test Quality
- PASS.
- Current td:2 assertions are discriminating: exact announcement text, exact stale-first-timer boundary, exact activeElement, exact aria-label values.
- Adjacent durable proof at serve/cockpit/web/src/__tests__/FilterPanel_1250.test.tsx:256 covers real text-input forwarding to onFilterChange, so the mocked board-level tests do not leave the current keystroke path unguarded.
- Informational only: code-reader and challenger both surfaced a mid-debounce polling freshness edge in KanbanBoard.tsx:221-227. The current AC and architect guidance do not define that interleave as a gate condition, so I am not scoring it as a fail in this review.

#### Data Safety
- No fail-worthy issue in the builder-owned task scope.

#### Test Gaps
- None fail-worthy for the written AC.
- Informational only: if product scope later requires announcement freshness when polling lands during a pending debounce window, add a dedicated interleaving test.

#### Necessity Check
- N/A.

#### Builder Process Quality
- CLEAN.
- Three prior Review Evidence sections exist in the task file. The current snapshot resolves the prior proof-quality failures without any new builder weakening.

### Deductions
- -0.04 module-level coverage on the touched files remains below 90 in some dimensions, even though the diff-scoped accessibility lines are directly exercised
- -0.03 one broader robustness edge remains informational rather than AC-gated

### Verdict
- PASS, confidence 0.91

### Action
- Advance to docs.

### Post-task Reflection
- Multiple stale review sections in the task body made it necessary to re-anchor on the live files and commit surfaces rather than prior notes.
- On frontend tasks that intentionally mock a child component, adjacent durable suites can close a proof gap without widening the AC.
- Diff-scoped coverage reasoning is more useful than raw whole-file percentages on narrow UI changes.
- A real robustness edge can exist without being a valid fail reason when the written AC does not define that interleave.
[[2026-05-03]]
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | No IN-scope prose docs reference filter accessibility UI; serve/cockpit/README.md has no mention of ARIA attributes or FilterPanel a11y |
| 2 | Module docstrings | No | N/A | No Python modules modified |
| 3 | External attribution | Yes | Updated | WAI-ARIA APG Disclosure (Show/Hide) pattern cited in research doc — added row to `.owlbear/sources/overview.md`; precedent from task #962 (Menu Pattern) |
| 4 | Research doc | Yes | Verified | `.owlbear/research/filter-accessibility-tests-1254.md` exists, linked from task body, follow-ups noted as none required |
| 5 | Diagram maintenance (describes match) | No | N/A | No diagram in doc-index has a `describes` glob matching any changed file |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation request in task body |
| 7 | Deletion detection | No | N/A | No files deleted |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| serve/cockpit/web/src/KanbanBoard.tsx | OUT | N/A |
| serve/cockpit/web/src/components/FilterPanel.tsx | OUT | N/A |
| serve/cockpit/web/src/__tests__/FilterAccessibility_1254.test.tsx | OUT | N/A |
| serve/cockpit/web/src/__tests__/FilterAccessibilityPanel_1254.test.tsx | OUT | N/A |
| .owlbear/research/filter-accessibility-tests-1254.md | IN | Verified (research doc exists, linked) |
| .owlbear/sources/overview.md | IN | Updated (attribution row added) |

### Files Updated
- `.owlbear/sources/overview.md` — added WAI-ARIA APG Disclosure attribution row under new "Filter Accessibility Tests (Task #1254)" section

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no `.owlbear/scratch/1254-*` files found)
[[2026-05-03]]
## Audit

### AC Verification (spot-check, reviewer cycle 4 PASS trusted)
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 aria-expanded | KanbanBoard.tsx:251; FilterAccessibility_1254.test.tsx:130 | PASS |
| AC2 aria-controls | KanbanBoard.tsx:252; FilterAccessibility_1254.test.tsx:160 | PASS |
| AC3 id/role/aria-label same element | FilterPanel.tsx:134-136; FilterAccessibilityPanel_1254.test.tsx:59 | PASS |
| AC4 aria-live polite | KanbanBoard.tsx:258; FilterAccessibility_1254.test.tsx:170 | PASS |
| AC5 user-initiated only (incl. active-filter polling) | KanbanBoard.tsx:213-230; FilterAccessibility_1254.test.tsx:196,290 | PASS |
| AC6 debounce 300ms (incl. stale-timer boundary) | KanbanBoard.tsx:227; FilterAccessibility_1254.test.tsx:362,383 | PASS |
| AC7 focus to first control | FilterPanel.tsx:98; FilterAccessibilityPanel_1254.test.tsx:71 | PASS |
| AC8 focus return on collapse | FilterPanel.tsx:79,139; FilterAccessibilityPanel_1254.test.tsx:151,198 | PASS |
| AC9 explicit labels (exact values) | FilterPanel.tsx:146,154-155,170-171; FilterAccessibilityPanel_1254.test.tsx:249,256,263 | PASS |

### Test Results
- Task-scoped frontend: 97 passed, 0 failed (22 task + 75 regression)
- Full Python suite: 128 failures (all unrelated: events_1234 import, engine_init_1067 ConfigError, Shell_966 context)
- Full frontend suite: 13 failures (all unrelated: Shell_966, Shell_1228 polyfill)
- No cross-task regressions from #1254 deliverables (confirmed via grep)
- ESLint: clean on all 4 task files
- Ruff: 1 violation in copilot_auth.py (unrelated)

### Commit Integrity
- Builder 3b1c83e0: KanbanBoard.tsx, FilterPanel.tsx only
- Test-writer 235c4020: FilterAccessibilityPanel_1254.test.tsx only
- Test-writer bdba1436: FilterAccessibility_1254.test.tsx only
- Docs commit: sources/overview.md attribution added
- No builder weakening of TestFromAC assertions

### Architect Quality: 4/5
AC lines were specific and testable. Required iterative refinement on td:2 edge cases (focus-return mechanism, aria-live separation, existing label). Challenger-driven refinement worked correctly. Minor gap: original AC did not pre-specify assertion strength expectations, leading to 4 review cycles.

### Deduction Breakdown
- Frontend coverage metric unavailable from quality-runner: -0.02
- No other deductions (all AC evidenced, lint clean in scope, AC quality > 3, reviewer evidence present and detailed)

### Confidence: 0.98
### Action: archive