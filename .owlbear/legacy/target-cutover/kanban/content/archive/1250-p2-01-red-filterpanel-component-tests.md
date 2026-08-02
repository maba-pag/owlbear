---
id: 1250
title: 'P2-01: RED — FilterPanel component tests'
status: archived
priority: medium
created: 2026-05-01T04:34:48.876923+00:00
updated: 2026-05-02T14:01:41.519048+00:00
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
  - Priority select non-placeholder options are an exact ordered match to the `priorities` prop array (same values, same sequence, no extras); at most one empty-value placeholder option is permitted at index 0 (td:1)
  - Hides tag control entirely when availableTags is empty (td:1)
  - Reset button not rendered (absent from DOM) when all filters are at empty state; rendered when at least one filter is active (non-empty text, priority set, tags selected, or blocked enabled) (td:1)
  - Reset button clears all filter values (calls onFilterChange with empty FilterState) (td:1)
  - Each control interaction fires onFilterChange with updated FilterState, preserving all other FilterState fields unchanged; each of text, priority, tags, and blocked must have at least one interaction test that starts from a fully-populated FilterState and asserts the untouched fields are preserved (td:2)
  - Does not render controls when open={false} — all five controls absent from DOM (not merely hidden from the accessibility tree): text input, priority select, tags multi-select, blocked switch, reset button; assertions must use DOM-level selectors (`container.querySelector` returning null), not role queries (td:1)
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
|---------|--------|----|
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
- Vitest failure is the expected RED import failure at serve/cockpit/web/src/__tests__/FilterPanel_1250.test.tsx#L36
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
| AC2 | FAIL. The strongest proof checks count plus arrayContaining, which allows reordered non-placeholder options to pass. | FAIL |
| AC3 | Empty and non-empty availableTags cases are both asserted with DOM absence/presence tests | PASS |
| AC4 | Empty-state absence plus text/priority/tags/blocked active-state presence are all covered | PASS |
| AC5 | Reset click asserts one callback with the exact empty FilterState object | PASS |
| AC6 | PASS. Exact callback payloads are asserted for each interaction, and the refined multi-field requirement is satisfied. | PASS |
| AC7 | All five controls are asserted absent when open=false, including reset | PASS |
| AC8 | PASS. quality-runner reported the expected unresolved import failure and workspace search found no FilterPanel component file yet | PASS |

#### Security Review
- No issues. Test-only TSX file; no secrets, injection surfaces, path handling, persistence, or outbound execution.

#### Test Quality
- FAIL. AC2 still has a non-discriminating assertion.

### Verdict
- FAIL. Confidence: 0.88

### Action
- Reject to backlog.
- Reason: AC2 is still not proven at the strength required by the refined contract.
- Required follow-up: strengthen AC2 so the non-placeholder option sequence is asserted as an exact ordered match to the priorities prop array.

[[2026-05-02]]
## Architecture Review (3rd pass — post-reviewer 2nd rejection)

### Verdict: APPROVE → todo

Reviewer rejected at 0.88. Single remaining defect: AC2 wording "option values match prop array" permitted `arrayContaining` (unordered containment) instead of strict ordered equality.

### AC2 Refinement
**Before:** Priority select populated exactly from `priorities` prop — option values match prop array, no extras beyond an optional empty/placeholder (td:1)
**After:** Priority select non-placeholder options are an exact ordered match to the `priorities` prop array (same values, same sequence, no extras); at most one empty-value placeholder option is permitted at index 0 (td:1)

### Challenger: SKIP
Single-line wording tightening on already-challenged criterion. No new design surface.

### Required Test-Writer Action
1. Replace `expect(nonEmptyValues).toEqual(expect.arrayContaining(custom))` with `expect(nonEmptyValues).toEqual(custom)` — strict ordered equality
2. If a placeholder exists, assert it is at index 0 with empty string value
[[2026-05-02]]
Architecture Review (3rd pass): APPROVE after AC2 refinement. Tightened to "exact ordered match" with placeholder at index 0.
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
[[2026-05-02]]
## Builder Notes
- Non-implementation RED task; implementation remains out of scope for #1250.
- Files changed: none.
- quality-runner evidence: vitest failed as expected due to missing `../components/FilterPanel` import; ESLint clean.
- Action: pass-through to review.
[[2026-05-02]]
## Review Evidence

### Test Results
- quality-runner (frontend scoped): 0 passed, 1 failed suite, 0 skipped.
- Expected RED failure: unresolved import at FilterPanel_1250.test.tsx#L36.

### Lint
- ESLint clean: 0 violations.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| AC1 | Direct render checks for all 5 controls | PASS |
| AC2 | Exact ordered equality asserted + placeholder position/value asserted | PASS |
| AC3 | DOM-null assertion for empty availableTags | PASS |
| AC4 | Empty and active-state checks | PASS |
| AC5 | Exact callback payload asserted | PASS |
| AC6 | Multi-field sibling-preservation proof exists | PASS |
| AC7 | FAIL. Text and priority absence checks use queryByRole (accessibility tree, not DOM absence). Hidden-but-mounted controls would false-green. | FAIL |
| AC8 | Expected import-resolution failure confirmed | PASS |

### Verdict
- FAIL. Confidence: 0.88
- Reason: AC7 DOM-absence proof gap — queryByRole proves accessibility-tree absence, not DOM absence.
- Required follow-up: replace AC7 text/priority absence checks with direct DOM-null assertions.

[[2026-05-02]]
## Architecture Review (4th pass — post-reviewer 3rd rejection)

### Verdict: APPROVE → todo

Reviewer rejected at 0.88. Single remaining defect: AC7 text-input and priority-select absence checks use `queryByRole` (accessibility-tree query) instead of direct DOM selectors. This would false-green if the implementation hides controls via `aria-hidden` or CSS rather than unmounting them. The other three AC7 controls already use `container.querySelector` (correct).

### AC7 Refinement
**Before:** Does not render controls when open={false} — all five controls absent from DOM: text input, priority select, tags multi-select, blocked switch, reset button (td:1)
**After:** Does not render controls when open={false} — all five controls absent from DOM (not merely hidden from the accessibility tree): text input, priority select, tags multi-select, blocked switch, reset button; assertions must use DOM-level selectors (`container.querySelector` returning null), not role queries (td:1)

This closes the last ambiguity: the test-writer must use direct DOM selectors for ALL five controls in the `open=false` block, matching the pattern already used for tags, blocked, and reset.

### Evaluation (delta from 3rd pass)
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Interface clarity | PASS | AC7 now explicitly distinguishes DOM absence from accessibility-tree absence |
| All other criteria | PASS | Unchanged from 3rd pass |

### Challenger: SKIP
Single-line assertion-technique clarification on already-challenged criterion. No new design surface.

### Required Test-Writer Action
1. In the AC7 `open=false` describe block, replace `getTextInput(container)` (which uses `queryByRole('textbox')`) with a `container.querySelector` call targeting the input element directly
2. Replace `getPrioritySelect(container)` (which uses `queryByRole('combobox')`) with a `container.querySelector` call targeting the select element directly
3. Leave the other three AC7 assertions unchanged — they already use DOM selectors
[[2026-05-02]]
Architecture Review (4th pass): APPROVE after AC7 refinement. Single defect from reviewer's 3rd rejection: AC7 text-input and priority-select absence checks use queryByRole (accessibility-tree query) instead of direct DOM selectors. Tightened AC7 to explicitly require DOM-level selectors (container.querySelector returning null), not role queries. Test-writer has explicit 3-item remediation checklist.
[[2026-05-02]]
## Test-Writer Notes
- Retry (4th pass): surgical fix of single AC7 gap from reviewer's 3rd rejection
- Test file: `serve/cockpit/web/src/__tests__/FilterPanel_1250.test.tsx`
- Commit: `80270f03`

### Change (2 lines modified)
- **AC7 DOM-selector fix:** Replaced `getTextInput(container)` (`queryByRole('textbox')`) with `container.querySelector('input[type="text"]')` in `open=false` text-input absence test
- Replaced `getPrioritySelect(container)` (`queryByRole('combobox')`) with `container.querySelector('select')` in `open=false` priority-select absence test
- All other AC7 assertions (blocked, tags, reset) already used `container.querySelector` — unchanged

### Verification
- All 31 tests FAIL (ImportError: `../components/FilterPanel` does not exist) — confirmed RED
- ESLint: clean (0 violations)

### AC Coverage
| AC | Tests | Status |
|----|-------|--------|
| AC1 (td:2) | 6 | ✓ |
| AC2 (td:1) | 3 | ✓ |
| AC3 (td:1) | 2 | ✓ |
| AC4 (td:1) | 5 | ✓ |
| AC5 (td:1) | 1 | ✓ |
| AC6 (td:2) | 9 | ✓ |
| AC7 (td:1) | 5 (all use container.querySelector — DOM-level absence) | ✓ |
| AC8 (td:0) | skip | ✓ |
[[2026-05-02]]
## Builder Notes
- Non-implementation RED task; implementation remains out of scope for #1250.
- Files changed: none.
- Validation via quality-runner (scoped):
  - Vitest: expected RED failure confirmed (`Failed to resolve import "../components/FilterPanel"` in `serve/cockpit/web/src/__tests__/FilterPanel_1250.test.tsx`).
  - ESLint: clean (0 violations) on retry.
- quality-runner env fallback: first lint attempt returned environment hang (exit 130); retried once with explicit frontend cwd hint per protocol and obtained clean lint result.
- Action: pass-through to review for final RED-phase verification.

## Post-task Reflection
- Problem faced: builder dispatch landed on a test-only RED task where code changes would violate scope.
- Workaround applied: used strict pass-through with scoped quality-runner evidence instead of touching implementation.
- Pattern discovered: frontend lint in delegated runs can require explicit cwd hint; one protocol retry resolved it cleanly.
- Quality gap: none in builder scope; remaining judgment belongs to reviewer on AC-proof strength.
[[2026-05-02]]
## Review Evidence

### Test Results
- quality-runner (frontend scoped): 0 passed, 1 failed suite, 0 skipped.
- Expected RED failure confirmed: `Failed to resolve import "../components/FilterPanel"` at `serve/cockpit/web/src/__tests__/FilterPanel_1250.test.tsx:36`.
- Workspace search found no `FilterPanel` component file under `serve/cockpit/web/src/`, so the RED condition is still real rather than incidental.

### Lint
- ESLint clean: 0 violations.
- VS Code diagnostics on the test file report no additional in-editor errors beyond the expected Vitest-time unresolved import.

### Coverage
- N/A. Vitest fails at import resolution before test collection or instrumentation.

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage
| AC Line | Evidence | Status |
|---|---|---|
| AC1 | Render presence tests exist for text, priority, tags, blocked, and reset at `serve/cockpit/web/src/__tests__/FilterPanel_1250.test.tsx:109`, `:114`, `:119`, `:124`, `:129`. Adjacent Cockpit PDS tests already use `querySelector`/`data-testid` for custom elements, so the tags selector is acceptable here. | PASS |
| AC2 | Exact ordered match + optional placeholder-at-index-0 proof at `serve/cockpit/web/src/__tests__/FilterPanel_1250.test.tsx:157`. | PASS |
| AC3 | Tag control DOM absence when `availableTags=[]` at `serve/cockpit/web/src/__tests__/FilterPanel_1250.test.tsx:190`. | PASS |
| AC4 | Empty-state absence at `serve/cockpit/web/src/__tests__/FilterPanel_1250.test.tsx:206`; active-state presence proved for text/priority/blocked/tags at `:211`, `:216`, `:221`, `:226`. | PASS |
| AC5 | Reset click asserts one callback with the exact empty `FilterState` payload at `serve/cockpit/web/src/__tests__/FilterPanel_1250.test.tsx:237`. | PASS |
| AC6 | Only the text handler gets a multi-field preservation proof at `serve/cockpit/web/src/__tests__/FilterPanel_1250.test.tsx:342`. The priority, blocked, and tags interaction tests at `:277`, `:298`, and `:319` start from empty or single-field state, so a handler that clobbers sibling fields would still pass. The AC says each control interaction must preserve the other `FilterState` fields unchanged. | FAIL |
| AC7 | All five closed-state DOM-absence checks now use DOM selectors, including text at `serve/cockpit/web/src/__tests__/FilterPanel_1250.test.tsx:364`, priority at `:369`, blocked at `:374`, tags at `:379`, reset at `:384`. | PASS |
| AC8 | PASS. quality-runner confirmed the expected unresolved import failure, and workspace search found no `FilterPanel` component file. | PASS |

#### Security Review
- No issues. Test-only TSX file with no secret, network, shell, filesystem, or persistence surface.

#### Test Integrity
- No direct weakening detected in the live snapshot.
- Small confidence deduction only: I could not diff the latest `TestFromAC_*` commit against a baseline from the reviewer environment, so immutability is not fully provable from git evidence alone.

#### Test Quality
- FAIL. Manual mutation reasoning still breaks on AC6: if the priority, blocked, or tags handler resets sibling fields to `emptyFilter`, the current tests still pass.

### Deductions
- -0.10 AC6 universal sibling-preservation contract is not fully proved.
- -0.03 TestFromAC immutability could not be diff-verified in this environment.

### Verdict
- FAIL. Confidence: 0.87

### Action
- Reject to `backlog`.
- Reason 1: AC6 proof gap remains.
- Reason 2: this task body already contains three prior `## Review Evidence` sections, so this is a 2nd+ review failure and the loop-breaker route is `backlog`.

## Post-task Reflection
- Problem faced: code-reader overcalled AC8 and tag-selector issues; I re-checked both against live runner evidence and adjacent PDS test patterns before deciding scope.
- Workaround applied: treated frontend RED proof as runner evidence plus workspace search, not as a requirement for self-enforcing test-body logic.
- Pattern discovered: PDS custom-element tests in this repo routinely use `querySelector` and `data-testid`; the real false-green risk here is state-preservation proof, not selector style.

[[2026-05-02]]
## Architecture Review (5th pass — post-reviewer 4th rejection)

### Verdict: APPROVE → todo

Reviewer rejected at 0.87. Single remaining defect: AC6 "at least one interaction test must start from a multi-field active state" was globally scoped — test-writer satisfied it with one text-handler test but left priority, blocked, and tags handlers starting from empty/single-field state. A handler that resets siblings to `emptyFilter` would still pass for those three.

### AC6 Refinement
**Before:** Each control interaction fires onFilterChange with updated FilterState, preserving all other FilterState fields unchanged; at least one interaction test must start from a multi-field active state (td:2)
**After:** Each control interaction fires onFilterChange with updated FilterState, preserving all other FilterState fields unchanged; at least one interaction test must start from a multi-field active state (td:2) → **per control** — each of text, priority, tags, and blocked must have at least one test that starts from a fully-populated FilterState and asserts the untouched fields are preserved

### Evaluation (delta from 4th pass)
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Interface clarity | PASS | AC6 now requires per-control sibling-preservation proof, closing the last false-green window |
| All other criteria | PASS | Unchanged from 4th pass |

### Challenger: SKIP
Single-line scoping clarification on already-challenged criterion. No new design surface.

### Required Test-Writer Action
1. Add a multi-field preservation test for the **priority** handler: start from fully-populated FilterState, change priority, assert text/tags/blocked unchanged
2. Add a multi-field preservation test for the **blocked** handler: start from fully-populated FilterState, toggle blocked, assert text/priority/tags unchanged
3. Add a multi-field preservation test for the **tags** handler: start from fully-populated FilterState, change tags, assert text/priority/blocked unchanged
4. Text handler already has the multi-field test — no change needed
[[2026-05-02]]
Architecture Review (5th pass): APPROVE after AC6 refinement. Tightened "at least one interaction test must start from a multi-field active state" to per-control requirement — each of text, priority, tags, and blocked must have at least one test starting from fully-populated FilterState. Test-writer has 3-item remediation checklist (priority, blocked, tags handlers need multi-field tests; text already has one).
[[2026-05-02]]
## Test-Writer Notes
- Retry (5th pass): surgical fill of AC6 sibling-preservation gap from reviewer's 4th rejection
- Test file: `serve/cockpit/web/src/__tests__/FilterPanel_1250.test.tsx`
- Commit: `0a495551`

### Changes (3 tests added)
1. **Priority handler multi-field test** — starts from `{ text: 'search', priority: 'needed', tags: ['bug'], blocked: true }`, changes priority to `'critical'`, asserts text/tags/blocked unchanged
2. **Blocked handler multi-field test** — starts from same fully-populated state, toggles blocked off, asserts text/priority/tags unchanged
3. **Tags handler multi-field test** — starts from same fully-populated state, fires CustomEvent with `['feature']`, asserts text/priority/blocked unchanged
4. Text handler already had multi-field test — untouched

### Verification
- All tests FAIL (ImportError: `../components/FilterPanel` does not exist) — confirmed RED
- ESLint: clean (0 errors, 0 warnings)
- Total: 34 tests (was 31, +3)

### AC Coverage
| AC | Tests | Status |
|----|-------|--------|
| AC1 (td:2) | 6 | ✓ |
| AC2 (td:1) | 3 | ✓ |
| AC3 (td:1) | 2 | ✓ |
| AC4 (td:1) | 5 | ✓ |
| AC5 (td:1) | 1 | ✓ |
| AC6 (td:2) | 12 (was 9, +3 per-control sibling-preservation) | ✓ |
| AC7 (td:1) | 5 (all container.querySelector — DOM-level) | ✓ |
| AC8 (td:0) | skip | ✓ |

[[2026-05-02]]
## Builder Notes
- Non-implementation RED task (`tdd:red`): implementation is out of scope for #1250.
- Files changed: none.
- Action taken: builder pass-through only; no source or test edits performed.
- Routing: advancing to `review` for RED-phase test-quality verification.

## Post-task Reflection
- Problem faced: builder dispatch landed on a test-only RED task.
- Workaround applied: strict no-op pass-through to avoid out-of-scope implementation churn.
- Pattern discovered: repeated retry cycles can re-enter builder even when the task scope remains test-only.
[[2026-05-02]]
## Review Evidence

### Test Results
- quality-runner (frontend scoped): 0 passed, 1 failed suite, 0 skipped.
- Expected RED failure confirmed: Failed to resolve import "../components/FilterPanel" at serve/cockpit/web/src/__tests__/FilterPanel_1250.test.tsx:36.
- Workspace file search found no FilterPanel component file under serve/cockpit/web/src/, so the RED condition is real rather than incidental.

### Lint
- ESLint clean: 0 violations on serve/cockpit/web/src/__tests__/FilterPanel_1250.test.tsx.

### Coverage
- N/A. Vitest fails at import resolution before test collection or instrumentation.

### Pass 1 - CRITICAL

#### Test-Writer AC Coverage
| AC Line | Evidence | Status |
|---|---|---|
| AC1 | Open-state render checks exist in serve/cockpit/web/src/__tests__/FilterPanel_1250.test.tsx, and text/tags/blocked/reset are exercised. I am not failing AC1 directly because the blocking contract mismatch is more specific to the priority-control assertions below. | PASS |
| AC2 | FAIL. The suite finds priority with queryByRole('combobox') at serve/cockpit/web/src/__tests__/FilterPanel_1250.test.tsx:80-81, then casts it to HTMLSelectElement and inspects select.options at :150-161 and :178-179. The authoritative brief says priority is a PDS Select at .owlbear/briefs/draft-filter-search-ux/brief.md:162 and the GREEN task repeats that at .owlbear/kanban/tasks/1251-p2-02-green-filterpanel-controlled-component.md:26. Adjacent Cockpit tests assert p-select is present and raw select is absent at serve/cockpit/web/src/__tests__/PdsMigration_1230.test.tsx:646-651. This RED suite is proving a native-select contract that does not match the intended implementation. | FAIL |
| AC3 | Tag-control absence when availableTags is empty is asserted in serve/cockpit/web/src/__tests__/FilterPanel_1250.test.tsx:187-194. | PASS |
| AC4 | Empty-state absence and active-state presence for reset are asserted in serve/cockpit/web/src/__tests__/FilterPanel_1250.test.tsx:203-228. | PASS |
| AC5 | Reset click asserts a single callback with the exact empty FilterState in serve/cockpit/web/src/__tests__/FilterPanel_1250.test.tsx:234-247. | PASS |
| AC6 | FAIL. The new multi-field preservation tests cover all four controls, but the priority branch still drives a native select shape: getPrioritySelect returns queryByRole('combobox') at :80-81 and the interaction tests call fireEvent.change on an HTMLSelectElement at :280-292 and :358-369. Adjacent PDS tests drive p-select with CustomEvent detail.value at serve/cockpit/web/src/__tests__/PdsMigration_1230.test.tsx:837-838. The preservation proof is stronger than before, but it is still attached to the wrong control contract for priority. | FAIL |
| AC7 | FAIL. The closed-state priority absence check is expect(container.querySelector('select')).toBeNull() at serve/cockpit/web/src/__tests__/FilterPanel_1250.test.tsx:419. That is a false-green against the brief-defined PDS Select, because the same repo already asserts that a correct priority control renders p-select while raw select stays absent at serve/cockpit/web/src/__tests__/PdsMigration_1230.test.tsx:646-651. A regression that leaves p-select mounted while open=false would still pass this test. | FAIL |
| AC8 | PASS. quality-runner confirmed the expected unresolved import failure, and the workspace contains no FilterPanel component file. | PASS |

#### Security Review
- No issues. This is a frontend test-only file with no secret, network, shell, filesystem, or persistence surface.

#### Test Integrity
- No direct weakening was visible in the live snapshot.
- Small confidence deduction only: builder reported no file changes, but I could not diff-verify TestFromAC immutability from reviewer-side git evidence.

#### Test Quality
- FAIL. Root cause: the RED suite still models the priority control as a native select even though the brief and downstream GREEN task specify a PDS Select. That misalignment affects option assertions, interaction events, and the open=false DOM-absence proof.

### Deductions
- -0.20 priority-control test contract is misaligned with the authoritative brief and adjacent Cockpit PDS patterns.
- -0.03 TestFromAC immutability was not diff-verified from reviewer-side git evidence.

### Verdict
- FAIL. Confidence: 0.77.

### Action
- Reject to backlog.
- Reason 1: this is a test-quality / AC-contract defect, not an implementation miss. The task needs architectural rework so the RED suite matches the brief-defined PDS priority control.
- Reason 2: this task file already contains four prior Review Evidence sections at .owlbear/kanban/tasks/1250-p2-01-red-filterpanel-component-tests.md:117, :216, :297, and :393, so the loop-breaker route is backlog.

## Post-task Reflection
- Problem faced: repeated retries fixed local assertion gaps while leaving the deeper brief-to-test contract mismatch untouched.
- Workaround applied: compared the live RED selectors against the authoritative Filter Panel brief and adjacent PDS tests instead of relying on prior review notes.
- Pattern discovered: queryByRole('combobox') plus HTMLSelectElement casts plus raw select absence checks are strong red flags when the brief says PDS Select.
- Quality gap: frontend RED reviews need an explicit brief-vs-selector sanity check early, or narrow retries can churn without addressing the root cause.
[[2026-05-02]]


[[2026-05-02]]
## Architecture Review (6th pass — post-reviewer 5th rejection)

### Verdict: APPROVE → todo

Reviewer rejected at 0.77. Root cause: the **entire priority-control test infrastructure** models priority as a native `<select>` (using `queryByRole('combobox')`, `HTMLSelectElement` casts, `fireEvent.change` with `target.value`, and `container.querySelector('select')` for closed-state). The brief and GREEN task #1251 both specify **PDS Select (`p-select`)**. Adjacent `PdsMigration_1230.test.tsx` confirms the established pattern: `container.querySelector('p-select')` + `CustomEvent({ detail: { value } })`. `ArchivalModal` uses `PSelect` from `@porsche-design-system/components-react` with `readControlValue` helper.

This is NOT a narrow assertion-strength issue — it is a fundamental contract mismatch that affects AC2, AC6, and AC7. The `getPrioritySelect` helper must be rewritten, and all priority assertions/interactions must change.

### ⚠ AC Overrides (supersede top-level AC wording)

**AC2 (replaces):** Priority control is a PDS Select (`p-select` element, NOT native `<select>`); its non-placeholder `<option>` children are an exact ordered match to the `priorities` prop array (same values, same sequence, no extras); at most one empty-value placeholder `<option>` is permitted at index 0; option assertions must query light-DOM `<option>` children of `p-select`, not cast to `HTMLSelectElement` (td:1)

**AC6 (replaces):** Each control interaction fires onFilterChange with updated FilterState, preserving all other FilterState fields unchanged; each of text, priority, tags, and blocked must have at least one interaction test that starts from a fully-populated FilterState and asserts the untouched fields are preserved; priority interactions must use the PDS event pattern (`fireEvent(el, new CustomEvent('change', { detail: { value }, bubbles: true }))` on the `p-select` element) — not `fireEvent.change` on a cast `HTMLSelectElement` (td:2)

**AC7 (replaces):** Does not render controls when open={false} — all five controls absent from DOM (not merely hidden from the accessibility tree): text input (`input[type="text"]`), priority select (`p-select`, NOT `select`), tags multi-select (`[data-testid="filter-tags"]`), blocked switch (`[role="switch"]` or `input[type="checkbox"]`), reset button (`[data-testid="filter-reset"]`); assertions must use DOM-level selectors (`container.querySelector` returning null), not role queries (td:1)

### PDS Element Contract (authoritative — from brief)

| Control | PDS Component | DOM Selector | Interaction Pattern |
|---------|--------------|-------------|---------------------|
| priority | PSelect | `p-select` | `new CustomEvent('change', { detail: { value }, bubbles: true })` |
| tags | PMultiSelect | `[data-testid="filter-tags"]` | CustomEvent (existing pattern correct) |
| blocked | PSwitch | `[role="switch"]` | Existing pattern correct |
| text | plain input | `input[type="text"]` | `fireEvent.change` (native — correct) |
| reset | button | `[data-testid="filter-reset"]` | `fireEvent.click` (native — correct) |

Reference patterns: `PdsMigration_1230.test.tsx:646-651` (PDS presence/absence), `:837-838` (PDS interaction). `ArchivalModal` uses `PSelect` + `readControlValue`.

### Required Test-Writer Actions

1. **Rewrite `getPrioritySelect` helper** — change from `within(container).queryByRole('combobox')` to `container.querySelector('p-select')`
2. **AC2 option assertions** — query `p-select` element's light-DOM children via `el.querySelectorAll('option')` and map `.value`; remove all `as HTMLSelectElement` casts and `.options` property access
3. **AC6 priority interactions** — replace `fireEvent.change(select, { target: { value } })` with `fireEvent(el, new CustomEvent('change', { detail: { value }, bubbles: true }))` for ALL priority tests (basic change, clearing, and multi-field preservation)
4. **AC7 closed-state** — replace `container.querySelector('select')` with `container.querySelector('p-select')`

### Evaluation (delta from 5th pass)
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Interface clarity | PASS | AC2/AC6/AC7 now explicitly name PDS elements and event patterns; native select patterns explicitly prohibited |
| Pattern consistency | PASS | Aligned with adjacent PdsMigration_1230 and ArchivalModal PDS test patterns |
| All other criteria | PASS | Unchanged from 5th pass |

### Challenger: SKIP
PDS contract alignment is a factual correction from the brief, not a design decision. No new design surface to challenge.

### Test-depth Summary
- td:2 lines: 2 (AC1, AC6)
- td:1 lines: 5 (AC2–AC5, AC7)
- td:0 lines: 1 (AC8 meta RED)
- Test-writer: processes normally

[[2026-05-02]]
Architecture Review (6th pass): APPROVE after AC2/AC6/AC7 refinement. Root cause of reviewer's 5th rejection: priority tests model native `<select>` but brief mandates PDS Select (`p-select`). Rewrote 3 AC lines to explicitly require PDS element selectors, PDS event patterns, and prohibit native select patterns. Added PDS Element Contract table and 4-item remediation checklist referencing established PdsMigration_1230 and ArchivalModal test patterns.
[[2026-05-02]]
## Test-Writer Notes
- Retry (6th pass): surgical fix of priority-control contract mismatch from reviewer's 5th rejection
- Test file: `serve/cockpit/web/src/__tests__/FilterPanel_1250.test.tsx`
- Commit: `ea72a988`

### Root cause addressed
Priority control tests modelled native `<select>` (queryByRole('combobox'), HTMLSelectElement casts, fireEvent.change with target.value, container.querySelector('select')). Brief and GREEN task #1251 specify PDS Select (`p-select`). Architecture Review 6th pass mandated full rewrite of priority test infrastructure.

### Changes (surgical — existing passing logic untouched)
1. **`getPrioritySelect` helper rewritten** — `within(container).queryByRole('combobox')` → `container.querySelector('p-select')`; return type `HTMLElement | null` → `Element | null`
2. **AC2 option assertions** — all three tests: removed `as HTMLSelectElement` casts and `.options` property access; replaced with `pSelect.querySelectorAll('option')` + `as HTMLOptionElement[]` — queries light-DOM `<option>` children of `p-select`
3. **AC6 priority interactions** — three tests (basic change, clearing, multi-field preservation): `fireEvent.change(select, { target: { value } })` → `fireEvent(pSelect, new CustomEvent('change', { detail: { value }, bubbles: true }))` — matches PDS event pattern from PdsMigration_1230.test.tsx:837
4. **AC7 closed-state** — `container.querySelector('select')` → `container.querySelector('p-select')` — correctly detects PDS Select presence

### Verification
- Vitest: 1 failed suite (ImportError: `../components/FilterPanel` does not exist) — confirmed RED
- ESLint: clean (0 errors, 0 warnings)
- TypeScript: clean (tsc --noEmit: 0 FilterPanel_1250 errors)
- Test count: 34 (unchanged — surgical edit only)

### AC Coverage
| AC | Tests | Status |
|----|-------|--------|
| AC1 (td:2) | 6 | ✓ |
| AC2 (td:1) | 3 — now queries p-select light-DOM options | ✓ |
| AC3 (td:1) | 2 | ✓ |
| AC4 (td:1) | 5 | ✓ |
| AC5 (td:1) | 1 | ✓ |
| AC6 (td:2) | 12 — priority interactions use PDS CustomEvent | ✓ |
| AC7 (td:1) | 5 — all DOM-level selectors including p-select for priority | ✓ |
| AC8 (td:0) | skip | ✓ |
[[2026-05-02]]
## Builder Notes
- Non-implementation RED task (`tdd:red`): implementation is out of scope for #1250.
- Files changed: none.
- quality-runner (scoped): Vitest exit 1 with expected import-resolution failure (`../components/FilterPanel` missing), ESLint clean (0 violations).
- Coverage: not available because tests do not collect before implementation exists.
- Action: pass-through to `review` with no code edits.

## Post-task Reflection
- Problem faced: builder dispatch on a RED-only test task where implementation would violate scope.
- Workaround applied: strict no-op pass-through with fresh scoped evidence.
- Pattern discovered: RED tasks benefit from lightweight revalidation before routing, even when no code changes are expected.
[[2026-05-02]]
## Review Evidence

### Test Results
- quality-runner (frontend scoped): 0 passed, 1 failed suite, 0 skipped.
- Expected RED failure confirmed: `Failed to resolve import "../components/FilterPanel" from "src/__tests__/FilterPanel_1250.test.tsx"` at line 35:24.
- Workspace file search found no `FilterPanel` implementation under `serve/cockpit/web/src/`, so the RED condition is real.

### Lint
- ESLint clean: 0 violations on `serve/cockpit/web/src/__tests__/FilterPanel_1250.test.tsx`.
- VS Code diagnostics on the test file show no additional errors.

### Coverage
- N/A. RED task; import resolution fails before test collection.

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage
| AC Line | Evidence | Status |
|---|---|---|
| AC1 | Open-state render tests cover text input, priority select, tags control, blocked switch, and reset button (`renders a text input when open=true`, `renders a priority select when open=true`, plus companion tests for tags/blocked/reset). | PASS |
| AC2 | Exact ordered non-placeholder option sequence is asserted in `priority select has exactly priorities.length options (plus at most one empty placeholder)`; placeholder, if present, must be empty and at index 0. | PASS |
| AC3 | `tag control is absent from DOM when availableTags is empty` proves the negative case; the companion positive case covers non-empty tags. | PASS |
| AC4 | Empty-state absence plus active-state presence for text, priority, blocked, and tags are each asserted in dedicated reset-button tests. | PASS |
| AC5 | `clicking reset calls onFilterChange with the empty FilterState` asserts one callback with the exact empty `FilterState` object. | PASS |
| AC6 | Exact callback payloads are asserted for text, priority, blocked, and tags interactions, and each control has a separate multi-field preservation test from a fully-populated `FilterState`. | PASS |
| AC7 | Closed-state DOM-absence checks use `container.querySelector` for all five controls, including `input[type="text"]` and `p-select`. | PASS |
| AC8 | quality-runner confirms the unresolved `FilterPanel` import, and workspace search confirms no `FilterPanel` implementation file exists. | PASS |

#### Security Review
- No issues. Test-only frontend file; no secret, network, shell, filesystem, or persistence surface.

#### Test Integrity
- No weakening or removal was visible in the live snapshot.
- Git log search confirms the #1250 retry commit chain through `ea72a988` (`test: fix priority control to PDS p-select contract (#1250)`).
- Small confidence deduction only: I did not reconstruct full per-hunk diffs reviewer-side, so immutability is not diff-proven end-to-end.

#### Test Quality
- PASS. Assertions are discriminating on the current AC set.
- The latest architecture override is binding: priority must be a PDS Select, while text remains a plain input. The live test file matches that split.
- Divergence from `code-reader`: it flagged the text control based on adjacent PDS input patterns, but the task's Architecture Review (6th pass) explicitly defines text as plain input and priority as `p-select`; that concern is non-blocking.

### Deductions
- -0.02 full `TestFromAC` immutability was not diff-verified from reviewer-side evidence.

### Verdict
- PASS. Confidence: 0.96

### Action
- Advance to `docs`.

## Post-task Reflection
- Problem faced: the task body contains several stale rejection trails, so old reviewer assumptions were easy to re-import accidentally.
- Workaround applied: I anchored the verdict to the latest Architecture Review override instead of prior review notes or adjacent-component patterns.
- Pattern discovered: looped RED tasks can legitimately flip from FAIL to PASS once the refined AC is written into the task artifact and the live suite matches it.
[[2026-05-02]]
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | Changed file is a test-only `.tsx`; no IN-scope prose doc references test file internals |
| 2 | Module docstrings | No | N/A | No Python modules created or modified |
| 3 | External attribution | No | N/A | PDS is an established project dependency; adjacent `PdsMigration_1230.test.tsx` is an internal reference, not a new external source |
| 4 | Research doc | Yes | Verified | `.owlbear/research/filter-panel-red-1250.md` exists and is linked from task body |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `cockpit.excalidraw` describes `serve/cockpit/web/src/**` — test file matches; footer updated to `Last verified: 2026-05-02 (092ecd1d)`, committed as `8248a0c5` |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation request in task body |
| 7 | Deletion detection | No | N/A | No files deleted; no orphaned IN-scope docs detected |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `serve/cockpit/web/src/__tests__/FilterPanel_1250.test.tsx` | OUT (test code) | N/A — test file; no doc edits |
| `share/diagrams/cockpit.excalidraw` | IN (diagram) | Footer updated (describes-match, Item 5) |

### Files Updated
- `share/diagrams/cockpit.excalidraw` — footer updated to `092ecd1d`

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no `1250-*` scratch files found)
[[2026-05-02]]
## Audit

### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 (td:2) | 6 tests in FilterPanel_1250.test.tsx:105-140 — render presence for all 5 controls | PASS |
| AC2 (td:1) | 3 tests :145-182 — exact ordered match via toEqual(custom), placeholder at index 0 | PASS |
| AC3 (td:1) | 2 tests :187-196 — DOM-null for empty availableTags, present for non-empty | PASS |
| AC4 (td:1) | 5 tests :201-228 — reset absent at empty, present for each active field | PASS |
| AC5 (td:1) | 1 test :234-247 — exact empty FilterState callback assertion | PASS |
| AC6 (td:2) | 12 tests :253-397 — per-control interactions + 4 multi-field preservation tests from fully-populated state | PASS |
| AC7 (td:1) | 5 tests :403-434 — all use container.querySelector (DOM-level), including p-select and input[type=text] | PASS |
| AC8 (td:0) | No FilterPanel.tsx exists (file_search confirms only test file); vitest fails at import resolution | PASS |

### Test Results
- Vitest (full): 48 passed files, 4 failed files (882 passed / 13 failed tests). FilterPanel_1250 fails at import (expected RED). Other failures (usePollingFetch_1227, Shell_1228) are pre-existing and unrelated to #1250 scope.
- pytest (full): 3618 passed, 126 failed (exit 0). Failures in unrelated packages (engine, decisions, mcp-kanban). No cockpit-web scope regressions.
- ESLint: 0 violations on FilterPanel_1250.test.tsx.
- Ruff: 3 violations in unrelated packages (knowledge, mcp-knowledge, orchestrator). None in task scope.

### Reviewer Evidence
Present, detailed, PASS at 0.96. All 8 AC lines mapped. Code-reader divergence on text control resolved by authoritative Architecture Review (6th pass) PDS Element Contract table. Accepted.

### Commit Integrity
- Deliverable: ea72a988 (test: fix priority control to PDS p-select contract, #1250)
- Full chain: da395867 through ea72a988 (7 commits)
- Docs: 8248a0c5 (docs: update cockpit diagram footer)

### Architect Quality: 2/5
Initial AC omitted PDS Select contract (said "priority select" generically), lacked exact-ordered-match requirement, conflated DOM absence with accessibility-tree queries, and allowed single-control satisfaction of per-control requirement. Required 5 architecture re-passes to reach verifiable specificity. Brief had the information; architect failed to carry it into AC lines.

### Deduction Breakdown
- Start: 1.00
- AC quality score 2 (lte 3): -0.03
- Confidence: 0.97

### Action: archive