---
id: 1250
title: 'P2-01: RED — FilterPanel component tests'
status: in-progress
priority: needed
created: 2026-05-01T04:34:48.876923+00:00
updated: 2026-05-02T02:40:22.167062+00:00
tags:
- phase-2
- scope:cockpit-web
- tdd:red
parent: 1247
depends_on:
- 1249
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Acceptance Criteria

- Vitest + Testing Library component test suite for FilterPanel:
  - Renders text input, priority select, tags multi-select, blocked switch, reset button when open (td:2)
  - Priority select populated exactly from `priorities` prop — option values match prop array, no extras beyond an optional empty/placeholder (td:1)
  - Hides tag control entirely when availableTags is empty (td:1)
  - Reset button not rendered (absent from DOM) when all filters are at empty state; rendered when at least one filter is active (non-empty text, priority set, tags selected, or blocked enabled) (td:1)
  - Reset button clears all filter values (calls onFilterChange with empty FilterState) (td:1)
  - Each control interaction fires onFilterChange with updated FilterState, preserving all other FilterState fields unchanged; at least one interaction test must start from a multi-field active state (td:2)
  - Does not render controls when open={false} — all five controls absent from DOM: text input, priority select, tags multi-select, blocked switch, reset button (td:1)
- All tests fail (RED) — no FilterPanel component exists yet (td:0)

## Component Props Contract (from brief)

```ts
interface FilterPanelProps {
  filter: FilterState
  onFilterChange: (filter: FilterState) => void
  priorities: string[]
  availableTags: string[]
  open: boolean
}
```

Note: `activeCount` is computed in the parent — FilterPanel derives reset-button visibility from whether `filter` differs from the empty state.

## In Scope
- Component test file for FilterPanel (`src/__tests__/FilterPanel_1250.test.tsx`)
- Test fixtures using FilterState type from #1249
- Selector strategy: prefer role/label queries (Testing Library idiom); data-testid only as last resort

## Out of Scope
- FilterPanel implementation (next task #1251)
- PDS component internals (mock or shallow-render PDS multi-select if needed)
- Accessibility attributes (Phase 4)

Brief: see parent #1247

[[2026-05-01]]
## Research

**Key findings:** FilterState type confirmed in `src/utils/filterTasks.ts` (text, priority, tags[], blocked). FilterPanel.tsx does not exist — RED valid. Component interface inferred from AC: open, filterState, onFilterChange, availableTags, activeCount. ~10 test cases covering all 6 AC lines.

**Test strategy:** PDS provider wrapper + fireEvent.change + vi.fn() callback assertions. data-testid selectors. No module mocks needed — pure presentational component.

**File placement:** `src/__tests__/FilterPanel_1250.test.tsx`

**Tier:** T1 — no decisions needed; follows established patterns exactly.

**Doc:** `.owlbear/research/filter-panel-red-1250.md`

**Follow-ups:** None — #1251 (GREEN phase) already exists.


[[2026-05-01]]
## Architecture Review (1st pass)

### Verdict: APPROVE (after refinement)

Refined AC to align with brief's `FilterPanelProps` contract. Key changes:
- Added `priorities: string[]` prop (brief-specified, needed for select options)
- Removed `activeCount` as implicit prop — reset visibility derived from filter state
- Resolved closed-state ambiguity: controls absent from DOM (not hidden)
- Added selector strategy guidance (role/label queries preferred)
- Added td annotations per AC line

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One component's test suite |
| Interface clarity | PASS | Props contract explicit from brief; each AC line maps to a testable assertion |
| Dependency correctness | PASS | #1249 archived/done — FilterState type exists in filterTasks.ts |
| Module layering | PASS | Pure presentational tests; no upward imports |
| TDD compliance | PASS | This IS the RED phase; tagged tdd:red |
| KISS/YAGNI | PASS | Single test file, minimal scope |
| Premise challenge | PASS | FilterPanel is brief-specified deliverable |
| Pattern consistency | PASS | Matches ArchivalModal test pattern (PDS provider, fireEvent, vi.fn) |
| Security surface | N/A | No system boundary — UI component tests |
| Single domain | PASS | scope:cockpit-web only |

### Challenger Results
- Confidence: 0.46 → reconsider
- Key concerns addressed: (1) props contract aligned to brief, (2) priorities prop added, (3) activeCount removed as prop, (4) closed-state resolved, (5) selector strategy specified
- Tags multi-select risk acknowledged in Out of Scope ("mock or shallow-render PDS if needed") — brief also flags fallback path
[[2026-05-01]]
## Test-Writer Notes
- Test file: `serve/cockpit/web/src/__tests__/FilterPanel_1250.test.tsx`
- Tests: 28 total — all FAIL (ImportError: FilterPanel.tsx does not exist)
- Commit: `da395867` — test: RED phase tests for FilterPanel component (#1250)
- Lint: clean (ESLint 0 violations)
[[2026-05-01]]
## Builder Notes
- Pass-through/no-op by design — RED task, implementation out of scope.
[[2026-05-02]]
## Review Evidence

Reviewer FAIL at 0.78. Key defects found:
1. AC7: reset button not checked in `open=false` block (missing assertion)
2. AC6: no sibling-filter preservation — all interaction tests start from empty/one-field state
3. AC4: presence-only assertions instead of discriminating visibility checks
4. AC2: containment-only option checks allow extra/hardcoded options
5. AC1: generic presence checks
6. Selector strategy: raw `querySelector` used instead of role/label queries

Full review in prior task body snapshot.


[[2026-05-02]]
## Architecture Review (2nd pass — post-reviewer rejection)

### Verdict: APPROVE → todo

Reviewer rejected at 0.78 with 6 specific test-quality defects. Root cause: AC language was precise enough for a careful reader but ambiguous enough that the test-writer produced lax assertions. Tightened 4 AC lines to close the ambiguity gaps.

### AC Changes
| AC Line | Change | Rationale |
|---------|--------|-----------|
| AC2 | "populated from" → "populated exactly from" + no extras | Prevents hardcoded option leakage |
| AC4 | "visible only" → "not rendered (absent from DOM)" | Eliminates CSS-visibility ambiguity |
| AC6 | Added "preserving all other FilterState fields unchanged" + multi-field start state | Prevents sibling-wipe false greens |
| AC7 | Generic "controls" → enumerated all 5: text, select, tags, blocked, reset | Prevents missed-assertion gaps |

### Evaluation (delta from 1st pass)
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Unchanged |
| Interface clarity | PASS | Tightened — reviewer's AC2/AC4/AC6/AC7 ambiguities now closed |
| Dependency correctness | PASS | #1249 done/archived; FilterState in filterTasks.ts confirmed |
| Module layering | PASS | Unchanged |
| TDD compliance | PASS | Existing test file at commit da395867; test-writer fixes existing file |
| KISS/YAGNI | PASS | No scope increase — same 7+1 AC lines, just tighter wording |
| Premise challenge | PASS | Unchanged |
| Pattern consistency | PASS | Unchanged |
| Security surface | N/A | Unchanged |
| Single domain | PASS | Unchanged |

### Challenger: SKIP
All AC lines are tightened refinements of already-challenged criteria. No new design decisions. Original challenger ran at 0.46 and all raised concerns were addressed in 1st pass.

### Test-depth Summary
- td:2 lines: 2 (AC1 render-all-controls, AC6 interactions)
- td:1 lines: 5 (AC2–AC5, AC7)
- td:0 lines: 1 (AC8 meta RED)
- Test-writer: processes normally

### Required Test-Writer Actions
1. Add reset-button null assertion in AC7 `open=false` block
2. Add ≥1 AC6 interaction test from multi-field active state proving sibling preservation
3. Assert exact option count in AC2 tests (priorities.length + optional placeholder)
4. Prefer Testing Library role/label queries where PDS components expose ARIA roles

[[2026-05-02]]
Architecture Review (2nd pass): APPROVE after AC refinement. Tightened 4 AC lines (AC2 exact options, AC4 DOM absence, AC6 sibling preservation, AC7 enumerate all 5 controls) to close ambiguities that caused reviewer rejection at 0.78. Test-writer has explicit remediation checklist for the next pass.
[[2026-05-02]]
## Test-Writer Notes
- Retry: filled 4 gaps from reviewer defects + Architecture Review (2nd pass) required actions
- Test file: `serve/cockpit/web/src/__tests__/FilterPanel_1250.test.tsx`
- Commit: `95bdfcb2`

### Changes (surgical fill — existing tests untouched)
1. **AC7 reset button assertion added** — `reset button is absent from DOM when open=false (even when filter is active)` — covers the missing 5th control from the enumerated list
2. **AC6 sibling preservation test added** — `changing text from a multi-field active state preserves priority, tags, and blocked` — starts from `{ text: 'old', priority: 'needed', tags: ['bug'], blocked: true }` and asserts only `text` changes
3. **AC2 exact count test added** — `priority select has exactly priorities.length options (plus at most one empty placeholder)` — asserts `options.length ≤ custom.length + 1` and `nonEmptyValues.length === custom.length`, blocking hardcoded extras
4. **Selector helpers updated** — `getTextInput` → `within(container).queryByRole('textbox')`, `getPrioritySelect` → `within(container).queryByRole('combobox')` — aligns with Testing Library idiom per AC selector strategy

### Verification
- All 31 tests FAIL (ImportError: `../components/FilterPanel` does not exist) — confirmed RED
- TypeScript: clean (tsc --noEmit)
- ESLint: clean (0 warnings, 0 errors)

### AC Coverage
| AC | Tests | Status |
|----|-------|--------|
| AC1 (td:2) | 6 | ✓ |
| AC2 (td:1) | 3 (was 2, +1 exact count) | ✓ |
| AC3 (td:1) | 2 | ✓ |
| AC4 (td:1) | 5 | ✓ |
| AC5 (td:1) | 1 | ✓ |
| AC6 (td:2) | 9 (was 8, +1 sibling preservation) | ✓ |
| AC7 (td:1) | 5 (was 4, +1 reset button) | ✓ |
| AC8 (td:0) | skip | ✓ |
[[2026-05-02]]
## Builder Notes
- Non-implementation RED task; implementation is explicitly out of scope for #1250.
- Files changed: none.
- Tests/lint evidence carried by latest Test-Writer Notes (31 failing RED tests due to missing FilterPanel import, TS clean, ESLint clean).
- Action: pass-through to review for verification of RED-phase test quality and AC coverage.

## Post-task Reflection
- Problem faced: Builder was dispatched onto a RED test task where coding would violate task scope.
- Workaround applied: Strict pass-through routing with no edits.
- Pattern discovered: Retry cycles can re-enter builder even when task remains test-only; explicit no-op note prevents accidental implementation churn.
[[2026-05-02]]
## Review Evidence

### Test Results
- quality-runner: 0 passed, 1 failed, 0 skipped
- Vitest failure is the expected RED import failure at [serve/cockpit/web/src/__tests__/FilterPanel_1250.test.tsx#L36](serve/cockpit/web/src/__tests__/FilterPanel_1250.test.tsx#L36)
- VS Code diagnostics on the test file report only the same unresolved module error

### Lint
- quality-runner ruff output is not a valid TSX lint gate here; the reported 33 violations are Python-parser false positives on a TSX file
- No additional TS/TSX diagnostics were reported in the test file beyond the expected unresolved component import

### Coverage
- N/A. RED task; test collection fails before execution and no FilterPanel implementation file exists yet.

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage
| AC Line | Evidence | Status |
|---|---|---|
| AC1 | Five direct presence tests cover text input, priority select, tags, blocked toggle, and reset when open=true | PASS |
| AC2 | FAIL. The strongest proof at [serve/cockpit/web/src/__tests__/FilterPanel_1250.test.tsx#L157](serve/cockpit/web/src/__tests__/FilterPanel_1250.test.tsx#L157) through [serve/cockpit/web/src/__tests__/FilterPanel_1250.test.tsx#L168](serve/cockpit/web/src/__tests__/FilterPanel_1250.test.tsx#L168) checks count plus [serve/cockpit/web/src/__tests__/FilterPanel_1250.test.tsx#L168](serve/cockpit/web/src/__tests__/FilterPanel_1250.test.tsx#L168), which allows reordered non-placeholder options to pass. The AC requires the option values to match the priorities prop array exactly, with no extras beyond an optional placeholder, as stated in [task 1250](.owlbear/kanban/tasks/1250-p2-01-red-filterpanel-component-tests.md#L26). | FAIL |
| AC3 | Empty and non-empty availableTags cases are both asserted with DOM absence/presence tests | PASS |
| AC4 | Empty-state absence plus text/priority/tags/blocked active-state presence are all covered | PASS |
| AC5 | Reset click asserts one callback with the exact empty FilterState object | PASS |
| AC6 | PASS. Exact callback payloads are asserted for each interaction, and the refined multi-field requirement is satisfied by [serve/cockpit/web/src/__tests__/FilterPanel_1250.test.tsx#L338](serve/cockpit/web/src/__tests__/FilterPanel_1250.test.tsx#L338). I did not adopt code-reader's broader AC6 failure because the refined AC requires at least one multi-field active-state interaction, not one per control. | PASS |
| AC7 | All five controls are asserted absent when open=false, including reset | PASS |
| AC8 | PASS. quality-runner reported the expected unresolved import failure and workspace search found no FilterPanel component file yet | PASS |

#### Security Review
- No issues. Test-only TSX file; no secrets, injection surfaces, path handling, persistence, or outbound execution.

#### Test Integrity
- No weakening evidence found in the live suite.
- Confidence deduction applied because this review context did not include a diff snapshot for direct TestFromAC immutability comparison.

#### Test Quality
- FAIL. AC2 still has a non-discriminating assertion. The current suite would not fail if the implementation rendered the provided priorities in a different order.
- The earlier AC6 proof gap is resolved enough for the refined AC and is not part of this rejection.

#### Data Safety
- No issues.

#### Test Gaps
- No additional AC-scoped gaps beyond AC2.

#### Necessity Check
- N/A. No new dependency, integration, or tooling.

#### Builder Process Quality
- CLEAN. Latest builder pass was a documented no-op, which is consistent with RED-task scope.

### Deductions
- -0.08 AC2 exact-array-match proof still missing
- -0.02 reduced confidence on TestFromAC immutability because no diff snapshot was available in review context

### Verdict
- FAIL. Confidence: 0.88

### Action
- Reject to backlog.
- Reason 1: AC2 is still not proven at the strength required by the refined contract in [task 1250](.owlbear/kanban/tasks/1250-p2-01-red-filterpanel-component-tests.md#L26).
- Reason 2: This task already contains one prior Review Evidence section at [task 1250](.owlbear/kanban/tasks/1250-p2-01-red-filterpanel-component-tests.md#L116), so this is a 2nd review failure and routes to backlog as the loop-breaker path.
- Required follow-up: strengthen AC2 so the non-placeholder option sequence is asserted as an exact ordered match to the priorities prop array, with placeholder handling explicit rather than implied.
[[2026-05-02]]

[[2026-05-02]]
## Architecture Review (3rd pass — post-reviewer 2nd rejection)

### Verdict: APPROVE → todo

Reviewer rejected at 0.88. Single remaining defect: AC2 wording "option values match prop array" permitted `arrayContaining` (unordered containment) instead of strict ordered equality. The test at L168 uses `expect(nonEmptyValues).toEqual(expect.arrayContaining(custom))` which would pass with reordered options.

### AC2 Refinement
**Before:** Priority select populated exactly from `priorities` prop — option values match prop array, no extras beyond an optional empty/placeholder (td:1)
**After:** Priority select non-placeholder options are an exact ordered match to the `priorities` prop array (same values, same sequence, no extras); at most one empty-value placeholder option is permitted at index 0 (td:1)

This closes the last ambiguity: the test-writer must use `expect(nonEmptyValues).toEqual(custom)` (strict deep equality) rather than `arrayContaining`.

### Evaluation (delta from 2nd pass)
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Interface clarity | PASS | AC2 now unambiguous — "exact ordered match" + "index 0" placeholder spec eliminates containment-only assertion loophole |
| All other criteria | PASS | Unchanged from 2nd pass |

### Challenger: SKIP
Single-line wording tightening on already-challenged criterion. No new design surface. Per Step 2.5: optional for REFINE.

### Required Test-Writer Action
1. Replace `expect(nonEmptyValues).toEqual(expect.arrayContaining(custom))` with `expect(nonEmptyValues).toEqual(custom)` — strict ordered equality
2. If a placeholder exists, assert it is at index 0 with empty string value
[[2026-05-02]]
Architecture Review (3rd pass): APPROVE after AC2 refinement. Single defect from reviewer's 2nd rejection: AC2 "match prop array" permitted unordered arrayContaining. Tightened to "exact ordered match" with placeholder at index 0. Test-writer has explicit 2-item remediation checklist.
[[2026-05-02]]
## Test-Writer Notes
- Retry (3rd pass): surgical fill of single AC2 gap from reviewer's 2nd rejection
- Test file: `serve/cockpit/web/src/__tests__/FilterPanel_1250.test.tsx`
- Commit: `eecfb4d4`

### Change (1 test modified)
- **AC2 exact-ordered-match:** Replaced `expect(nonEmptyValues).toEqual(expect.arrayContaining(custom))` with `expect(nonEmptyValues).toEqual(custom)` — strict deep equality enforcing same order as `priorities` prop. Added conditional assertion: if a placeholder option exists, `options[0].value` must be `''` (placeholder at index 0).

### Verification
- All tests FAIL (1 failed suite — ImportError: `../components/FilterPanel` does not exist) — confirmed RED
- ESLint: clean (0 errors, 0 warnings)
- 31 tests total (no count change — surgical edit only)

### AC Coverage
| AC | Tests | Status |
|----|-------|--------|
| AC1 (td:2) | 6 | ✓ |
| AC2 (td:1) | 3 — now with strict ordered equality + placeholder-at-index-0 | ✓ |
| AC3 (td:1) | 2 | ✓ |
| AC4 (td:1) | 5 | ✓ |
| AC5 (td:1) | 1 | ✓ |
| AC6 (td:2) | 9 | ✓ |
| AC7 (td:1) | 5 | ✓ |
| AC8 (td:0) | skip | ✓ |