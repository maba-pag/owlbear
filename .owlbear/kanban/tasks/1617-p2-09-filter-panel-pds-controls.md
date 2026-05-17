---
id: 1617
title: 'P2-09: Filter panel PDS controls'
status: todo
priority: important
created: 2026-05-16T03:37:02.279043+00:00
updated: 2026-05-16T20:31:17.206975+00:00
tags:
  - frontend
  - pds
  - phase-2
parent: 1590
depends_on: []
ac:
  - Blocked checkbox uses `PCheckbox` React wrapper with `checked` prop and 
    `onChange` handler (replaces raw `<p-checkbox>` web component with 
    `onClick`)
  - Priority `PSelect` uses `PSelectOption` children (replaces native `<option>`
    elements)
  - 'Filter panel `.filter-panel` uses flex layout: `display: flex; flex-wrap: wrap;
    gap: var(--pds-spacing-sm); align-items: flex-end`'
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1590.

Scope: Filter panel PDS controls only.
Out of scope: Simple swaps, cards, sidecar IA, modals.

2026-05-16T15:23:07+00:00
## Research Findings

**AC naming correction:** `PCheckboxWrapper` and `PTextFieldWrapper` are deprecated (🚫) in PDS v4. Correct components: `PCheckbox` and `PInputSearch`. The existing code already uses `PInputSearch`, `PSelect`, `PMultiSelect` — only the blocked checkbox needs migration from raw `<p-checkbox>` web component to `PCheckbox` React wrapper.

**Implementation scope:**
1. Import `PCheckbox` from `@porsche-design-system/components-react`
2. Replace `<p-checkbox>` with `<PCheckbox name="blocked-filter" label="Show only blocked tasks" checked={filter.blocked} onChange={...} />`
3. Use `onChange` (not `onClick`) — gets `CheckboxChangeEventDetail` with typed event
4. Add flex layout to `.filter-panel`: `display:flex; flex-wrap:wrap; gap:var(--p-spacing-sm); align-items:flex-end`

**Research doc:** `.owlbear/research/filter-panel-pds-controls.md`

[[2026-05-16T17:23:24+02:00]]
## Research
- Research doc: .owlbear/research/filter-panel-pds-controls.md
- Sources: 7 studied, 5 high-relevance (PDS docs, GitHub examples, codebase)
- Recommendation: Migrate `<p-checkbox>` → `PCheckbox` React wrapper + add flex layout (confidence: 0.85)
- Follow-up tasks created: none needed — #1617 is the implementation task itself
- Decision requests: none (T1 autonomous — component migration + layout fix)

## Challenge Results
- Challenger: FALLBACK — trivial migration scope (1 component + layout CSS); challenger not cost-justified
- Confidence in original: 0.85

## Key findings
1. FilterPanel is ~80% PDS-compliant already; only blocked checkbox needs migration
2. AC names `PCheckboxWrapper`/`PTextFieldWrapper` are deprecated in PDS v4; correct components are `PCheckbox` and `PInputSearch` (already used)
3. `PCheckbox` uses `onChange` with `CheckboxChangeEventDetail` (not `onClick`)
4. Horizontal flex bar is the right layout for 4 controls (KISS)

[[2026-05-16T18:06:11+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Migrate filter panel controls to PDS-compliant wrappers + add flex layout |
| Interface clarity | PASS (after refine) | AC now names exact components, props, and CSS properties |
| Dependency correctness | PASS | No dependencies; test task #1612 archived — existing e2e suite `filter-controls-1564.spec.ts` covers RED phase |
| Module layering | PASS | Single component file + CSS, no cross-domain imports |
| TDD compliance | PASS | Existing e2e tests from #1564 already assert: `p-checkbox[name]` visibility, `p-select-option` children, no native `<option>` |
| KISS/YAGNI | PASS | 2 component swaps + 1 CSS rule — minimal scope |
| Premise challenge | PASS | Raw `<p-checkbox>` and native `<option>` are genuine PDS v4 violations per design policy §5 |
| Pattern consistency | PASS | Other controls in same file already use React wrappers (PInputSearch, PMultiSelect) |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | Frontend only |

### AC Refinement Applied
Original AC referenced deprecated `PCheckboxWrapper`/`PTextFieldWrapper` and vague layout options. Challenger identified PSelectOption as in-scope (existing e2e tests already assert it). Refined to 3 precise, testable AC lines.

### Challenge Results
- Challenger: reconsider (confidence 0.49)
- Key finding accepted: PSelectOption migration IS in-scope — e2e test `filter-controls-1564.spec.ts` L412-432 already asserts `p-select-option` children and fails on native `<option>`
- Key finding rebutted: "task-contract drift" — addressed by persisting refined AC via edit_task
- Architect response: accepted scope expansion (PSelectOption), rebutted contract-drift (now persisted)

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: `serve/cockpit/web/e2e/filter-controls-1564.spec.ts` (e2e RED tests), `serve/cockpit/web/src/__tests__/FilterPanel.test.tsx` (unit tests)
- Test-writer: PROCEED (existing e2e covers RED; unit test updates needed for onChange path)

### Verdict: APPROVE
### Action Taken: Refined AC (deprecated names → correct PDS v4 components, added PSelectOption migration, specified exact flex layout tokens), advanced to todo

[[2026-05-16T18:50:25+02:00]]
## Test-Writer Notes

**Test file:** `serve/cockpit/web/src/__tests__/FilterPanel_PDS_1617.test.tsx`

**Classes:**
- `TestFromAC_PCheckboxWrapper` — AC1 (5 tests)
- `TestFromAC_PSelectOption` — AC2 (4 tests)
- `TestFromAC_FilterPanelFlexLayout` — AC3 (4 tests)

**Tests per category:**
- Happy path: 3 (checked DOM property true, change→blocked:true, change→blocked:false)
- Edge / sibling preservation: 1 (onChange preserves text/priority/tags)
- Falsifiability guards: 3 (aria-checked absent, no native option, no native option dual-render)
- Boundary / count: 1 (p-select-option count ≥ priorities.length)
- CSS source contract: 4 (display:flex, flex-wrap:wrap, gap token, align-items:flex-end)

**Total: 13 tests, all FAIL** (verified via quality-runner)

**AC coverage:**
| AC | Tests |
|----|-------|
| AC1: PCheckbox wrapper with checked + onChange | 5 |
| AC2: PSelectOption children (not native option) | 4 |
| AC3: .filter-panel flex layout CSS | 4 |

**Failure evidence:**
- AC1: `el.checked === undefined` (not true); onFilterChange called 0 times on change event; `aria-checked="true"` still present
- AC2: no `p-select-option` found; 6 native OPTION children found; values array empty
- AC3: 4 CSS assertions fail — no flex declarations in current `.filter-panel {}` block

**Lint:** ESLint clean (exit 0)
**Commit:** `ebd9224` — test: FilterPanel PDS controls — PCheckbox, PSelectOption, flex layout (#1617, test-writer)

**Note on jsdom selector quirk:** PDS custom element `name` attributes are not reflected as queryable DOM attributes in jsdom (unlike Playwright). Tests use `querySelector('p-checkbox')` and `querySelector('p-select')` rather than attribute-scoped selectors, consistent with existing `FilterPanel.test.tsx` patterns (`getPrioritySelect`, `getBlockedControl` helpers).

[[2026-05-16T19:43:38+02:00]]
## Builder Notes
- Implementation attempt (not committed): migrated `FilterPanel` to `PCheckbox` + `PSelectOption`, switched blocked handler to `onChange(detail.checked)`, added flex layout declarations in `FilterPanel.css`.
- RED verification before implementation (quality-runner): `serve/cockpit/web/src/__tests__/FilterPanel_PDS_1617.test.tsx` -> 13 failed / 0 passed, lint clean.
- GREEN verification during implementation (quality-runner): same file -> 13 passed / 0 failed, eslint/stylelint clean.
- Regression visibility check (quality-runner durable test file): `serve/cockpit/web/src/__tests__/FilterPanel.test.tsx` -> 33 passed / 7 failed.
- Root cause: durable tests encode pre-migration interface assumptions that conflict with current AC for #1617.
  - AC2 conflict: durable helper reads native `option` children (`querySelectorAll('option')`) while #1617 AC requires `PSelectOption` children and forbids native options.
  - AC6/controlled conflict: durable tests simulate blocked toggle via `click` and assert `aria-checked`; #1617 AC requires `PCheckbox` with `checked` prop + `change` event detail.
- Action taken: reverted local code/CSS changes and rejected to test-writer for durable-test contract alignment before builder implementation can land safely.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Update durable priority-option assertions to `p-select-option` contract (not native `option`) and remove assumptions that require native option children. | serve/cockpit/web/src/__tests__/FilterPanel.test.tsx | quality-runner durable run: 3 AC2 failures (`optionValues` empty / option count 0 under `PSelectOption` implementation) |
| 2 | test-writer | Align blocked-control interaction tests with `PCheckbox` wrapper contract (`change` with `detail.checked`) instead of click-toggle assumptions. | serve/cockpit/web/src/__tests__/FilterPanel.test.tsx | quality-runner durable run: 3 AC6 failures (`onFilterChange` not called on click in PCheckbox change-path implementation) |
| 3 | test-writer | Replace controlled-state checked assertions that read `aria-checked` with checks against `checked` DOM property on `p-checkbox`. | serve/cockpit/web/src/__tests__/FilterPanel.test.tsx | quality-runner durable run: 1 controlled-state failure (`blocked true` expected from aria-checked, incompatible with wrapper checked-prop path) |
