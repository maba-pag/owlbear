---
id: 1617
title: 'P2-09: Filter panel PDS controls'
status: archived
priority: medium
created: 2026-05-16T03:37:02.279043+00:00
updated: 2026-05-17T15:26:05.824165+02:00
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
    gap: var(--p-spacing-static-sm); align-items: flex-end`'
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason: completed
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

[[2026-05-17T05:57:09+02:00]]
## Test-Writer Notes (retry)

**Retry cycle**: All 3 Required Follow-up items (builder notes) already addressed by prior commits (`986810ef`, `bf09a1a7`, `f5746938`) — design-token refactor and PDS-wrapper migration work updated the durable file contracts before this retry ran.

**Verification — RED state confirmed:**

| File | Passed | Failed |
|------|--------|--------|
| `serve/cockpit/web/src/__tests__/FilterPanel_PDS_1617.test.tsx` | 0 | 13 |
| `serve/cockpit/web/src/__tests__/FilterPanel.test.tsx` (durable) | 33 | 7 |
| **Total** | **33** | **20** |

**Durable failures (7) per Required Follow-up:**
- AC2 ×3: `getPriorityOptions` uses `p-select-option` selector → returns empty against current `<option>` impl
- AC6 ×3: blocked control uses `change` + `detail.checked` → not fired by current `onClick` handler
- Controlled ×1: `blocked.checked === true` assertion → returns `undefined` with current `aria-checked` impl

**Task-scoped failures (13):**
- `TestFromAC_PCheckboxWrapper` (5): `PCheckbox` checked-prop + onChange contract — unimplemented
- `TestFromAC_PSelectOption` (4): `PSelectOption` children, no native `<option>` — unimplemented
- `TestFromAC_FilterPanelFlexLayout` (4): CSS flex declarations — absent from `.filter-panel {}`

**AC coverage:**
| AC | Tests |
|----|-------|
| AC1: PCheckbox + checked + onChange | 5 task-scoped + 3 durable |
| AC2: PSelectOption (no native option) | 4 task-scoped + 3 durable |
| AC3: .filter-panel flex layout | 4 task-scoped |

**Lint:** ESLint clean (exit 0)
**No new commit needed** — all required changes were already committed.

[[2026-05-17T07:33:16+02:00]]
## Builder Notes
- Implementation: migrated filter panel controls to PDS wrappers in serve/cockpit/web/src/components/FilterPanel.tsx and added flex layout rules in serve/cockpit/web/src/components/FilterPanel.css.
- AC1 fix: replaced raw `<p-checkbox>` + `onClick` toggle with controlled `PCheckbox` (`checked={filter.blocked}`) and `onChange` using `detail.checked`.
- AC2 fix: replaced native `<option>` children with `PSelectOption` children under `PSelect`.
- AC3 fix: `.filter-panel` now declares `display:flex`, `flex-wrap:wrap`, `gap:var(--p-spacing-static-sm)`, and `align-items:flex-end`.
- Durable contract alignment: added `role="textbox"` to `PInputSearch` host to preserve existing durable text-input queries and interaction tests.

- Tests (quality-runner):
  - RED baseline before code changes: `src/__tests__/FilterPanel_PDS_1617.test.tsx` showed failing AC assertions (12 failed / 1 passed).
  - GREEN scoped: `src/__tests__/FilterPanel_PDS_1617.test.tsx` -> 13 passed / 0 failed.
  - Durable check via quality-runner retry initially showed 5 remaining failures (text-input query/interaction path), resolved by `role="textbox"` host fix.
  - Post-fix durable verification (direct env fallback, targeted previously failing tests): 5/5 passed:
    1) renders a text input when open=true
    2) text input change fires onFilterChange with updated text
    3) clearing text input fires onFilterChange with text: ""
    4) changing text from a multi-field active state preserves priority, tags, and blocked
    5) text input value reflects filter.text

- Lint:
  - `eslint` clean for `src/components/FilterPanel.tsx`, `src/__tests__/FilterPanel_PDS_1617.test.tsx`, `src/__tests__/FilterPanel.test.tsx`.
  - `stylelint` clean for `src/components/FilterPanel.css`.

- Coverage:
  - Scoped coverage (task test only) for `src/components/FilterPanel.tsx`: statements 62.77%, branches 45.45%, functions 52.63%, lines 71.27%.
  - quality-runner env fallback: repeated environment/interruption issues when executing the full durable file together with coverage (`vitest` exit 130/SIGINT after first file), so full combined coverage report could not be captured in one run.

- Evidence summary:
  - AC behaviors implemented and validated by task-scoped GREEN tests.
  - Durable regressions introduced by this migration were identified and fixed.
  - Commit created with task-scoped files only.

- Commit: 281883df (`feat: migrate filter panel PDS controls (#1617, builder)`).

[[2026-05-17T08:25:44+02:00]]
## Review Evidence
- Verdict: FAIL
- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC3: Filter panel `.filter-panel` uses flex layout with `gap: var(--pds-spacing-sm)` | The authoritative AC, task research, implementation, and task-scoped proof disagree on the required spacing token, so the current GREEN packet does not prove the contract. Frontmatter requires `var(--pds-spacing-sm)`, task research recommends `var(--p-spacing-sm)`, and both implementation and task test assert `var(--p-spacing-static-sm)`. This is a contract/proof-quality split, not a clean builder-only miss. | `.owlbear/kanban/tasks/1617-p2-09-filter-panel-pds-controls.md:20-21`; `.owlbear/kanban/tasks/1617-p2-09-filter-panel-pds-controls.md:43`; `.owlbear/research/filter-panel-pds-controls.md:75`; `serve/cockpit/web/src/components/FilterPanel.css:6`; `serve/cockpit/web/src/__tests__/FilterPanel_PDS_1617.test.tsx:226-232`; token-migration baseline: `.owlbear/kanban/tasks/1603-p1-03-atomic-token-migration-delete-tokens-css-migrate-references.md:100`, `.owlbear/kanban/tasks/1603-p1-03-atomic-token-migration-delete-tokens-css-migrate-references.md:128-130` | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Reconcile AC3 to one authoritative spacing token that matches the current Cockpit token baseline, and persist that decision in the task contract/body before re-dispatch. | `.owlbear/kanban/tasks/1617-p2-09-filter-panel-pds-controls.md`; `.owlbear/research/filter-panel-pds-controls.md` | Review finding #1 |
| 2 | architect | Realign the task-scoped proof to the reconciled AC3 token so a future GREEN run cannot false-green a contract mismatch. | `serve/cockpit/web/src/__tests__/FilterPanel_PDS_1617.test.tsx` | Review finding #1 |

## Observations
- AC1 maps cleanly in implementation: `PCheckbox` is rendered with `checked={filter.blocked}` and `onChange` reading `detail.checked` in `serve/cockpit/web/src/components/FilterPanel.tsx:226-233`. Task-scoped proof covers checked-state reflection, change true/false, and removal of the old `aria-checked` pattern in `serve/cockpit/web/src/__tests__/FilterPanel_PDS_1617.test.tsx:73-127`.
- AC2 maps cleanly in implementation: `PSelect` renders `PSelectOption` children in `serve/cockpit/web/src/components/FilterPanel.tsx:192-205`, and task-scoped proof includes both positive and falsifiability checks for `p-select-option` presence and absence of native `<option>` in `serve/cockpit/web/src/__tests__/FilterPanel_PDS_1617.test.tsx:151-199`.
- No editor diagnostics were reported for the reviewed source and test files. No scoped dirty-tree overlap was observed on the builder commit surface.

[[2026-05-17T09:16:03+02:00]]
## Architecture Review (re-review)

### Context
Re-review after reviewer FAIL verdict. Single blocking finding: AC3 referenced deprecated `--pds-spacing-sm` while implementation and tests correctly used `--p-spacing-static-sm` per completed token migration #1603.

### Token Reconciliation
**Decision:** AC3 updated from `var(--pds-spacing-sm)` to `var(--p-spacing-static-sm)`.
**Evidence:** Task #1603 provenance map explicitly maps `--pds-spacing-sm` → `--p-spacing-static-sm`. All Cockpit CSS files (FilterPanel.css, Card.css, Column.css, Shell.tsx) use this token. Implementation commit `281883df` and task-scoped test (L226-232) both assert `--p-spacing-static-sm`.
**Body note:** Research findings section (line ~43) references `var(--p-spacing-sm)` — this is the research recommendation written before #1603 migration completed. The authoritative AC (frontmatter) now reads `var(--p-spacing-static-sm)`. Research doc `.owlbear/research/filter-panel-pds-controls.md` is historical record, not live contract.

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Migrate filter panel controls to PDS-compliant wrappers + add flex layout |
| Interface clarity | PASS | AC names exact components, props, CSS properties, and token values |
| Dependency correctness | PASS | No task dependencies; #1603 token migration already completed |
| Module layering | PASS | Single component file + CSS, no cross-domain imports |
| TDD compliance | PASS | Task-scoped tests exist (13 tests), durable suite aligned |
| KISS/YAGNI | PASS | 2 component swaps + 1 CSS rule — minimal scope |
| Premise challenge | PASS | Raw `<p-checkbox>` and native `<option>` are genuine PDS v4 violations |
| Pattern consistency | PASS | Other controls in same file already use React wrappers |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | Frontend only |

### Challenge Results
- Challenger: reconsider (confidence 0.59)
- Key findings evaluated:
  - evidence-integrity: Accepted partially — no single-run full durable report in record; evidence shows 33 pre-passing + 5 individually verified fixes
  - contract-completion: Accepted — annotated stale body reference above; research doc is historical, frontmatter AC is authoritative
  - proof-sufficiency: Rebutted — environmental interruption (vitest SIGINT); task-scoped 13/13 GREEN covers behavioral changes; reviewer will run full suite
  - ac-quality (minor): Rebutted — migration AC is inherently implementation-shaped; specifying target component IS the acceptance criterion
- Architect response: accepted token reconciliation concern, rebutted remaining as non-blocking for approval

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: `serve/cockpit/web/src/__tests__/FilterPanel_PDS_1617.test.tsx` (task-scoped), `serve/cockpit/web/src/__tests__/FilterPanel.test.tsx` (durable)
- Test-writer: PROCEED (existing tests aligned to reconciled AC)

### Verdict: APPROVE
### Action Taken: Reconciled AC3 token (--pds-spacing-sm → --p-spacing-static-sm per #1603 migration baseline), annotated body provenance, advanced to todo

[[2026-05-17T09:16:08+02:00]]
Re-review complete. Reconciled AC3 token from deprecated --pds-spacing-sm to --p-spacing-static-sm (per #1603 migration baseline). Implementation and task-scoped tests already aligned to correct token. Challenger reconsider (0.59) — accepted contract-completion concern (annotated body provenance), rebutted proof-sufficiency and ac-quality as non-blocking. Advanced to todo.

[[2026-05-17T14:00:04+02:00]]
## Test-Writer Notes (retry 2 — direct-to-review)

**Retry cycle**: Reviewer Required Follow-up was architect-scope only (AC3 token reconciliation: `--pds-spacing-sm` → `--p-spacing-static-sm`). Architect resolved both items in re-review — AC3 updated in frontmatter, confirmed task-scoped tests already assert `--p-spacing-static-sm` (correct reconciled token).

**Verification — GREEN state (Step 1b.1):**

| File | Passed | Failed |
|------|--------|--------|
| `serve/cockpit/web/src/__tests__/FilterPanel_PDS_1617.test.tsx` | 13 | 0 |

**Why GREEN is correct here:** Builder commit `281883df` already implemented AC1 (PCheckbox + onChange), AC2 (PSelectOption children), and AC3 (flex layout with `--p-spacing-static-sm`). The implementation matches the reconciled AC exactly. Tests were written RED in the prior cycle and are now GREEN because the builder's implementation is complete.

**Builder skip:** No builder work remains. Test-only retry — advancing directly to review.

**Lint:** ESLint clean (exit 0)

[[2026-05-17T14:42:12+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation (one line): PASS #1617 -> docs | AC mapped to code and evidence sufficient.
- Builder evidence review: the builder packet was close but not fully auditable because the task history preserved a RED-count inconsistency and only a targeted durable rerun. Independent verification was therefore cost-justified.
- Independent verification: quality-runner reran `serve/cockpit/web/src/__tests__/FilterPanel_PDS_1617.test.tsx` and `serve/cockpit/web/src/__tests__/FilterPanel.test.tsx` -> 53 passed, 0 failed, 0 skipped; eslint/stylelint clean; coverage for `src/components/FilterPanel.tsx` = 78.1% statements, 56.36% branches, 89.47% functions, 86.17% lines; Errors: none.
- AC evidence map:

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC1 | `serve/cockpit/web/src/components/FilterPanel.tsx:226-232` renders `PCheckbox`, sets `checked={filter.blocked}`, and reads `event.detail.checked` | `serve/cockpit/web/src/__tests__/FilterPanel_PDS_1617.test.tsx:73,84,113`; `serve/cockpit/web/src/__tests__/FilterPanel.test.tsx:310,486` | PASS |
| AC2 | `serve/cockpit/web/src/components/FilterPanel.tsx:199-200` renders `PSelectOption` children under `PSelect` | `serve/cockpit/web/src/__tests__/FilterPanel_PDS_1617.test.tsx:151,175,187`; `serve/cockpit/web/src/__tests__/FilterPanel.test.tsx:163,171` | PASS |
| AC3 | `serve/cockpit/web/src/components/FilterPanel.css:4-7` declares `display:flex`, `flex-wrap:wrap`, `gap:var(--p-spacing-static-sm)`, and `align-items:flex-end`; live AC reconciled at `.owlbear/kanban/tasks/1617-p2-09-filter-panel-pds-controls.md:21` with authority note at `.owlbear/kanban/tasks/1617-p2-09-filter-panel-pds-controls.md:249` | `serve/cockpit/web/src/__tests__/FilterPanel_PDS_1617.test.tsx:207,216,226,236` | PASS |
- Challenger: proceed (confidence 0.81). No blocking contradiction between the live AC, implementation, and proof.

## Observations
- Supporting artifacts still carry stale pre-reconciliation spacing-token text at `.owlbear/kanban/tasks/1617-p2-09-filter-panel-pds-controls.md:43` and `.owlbear/research/filter-panel-pds-controls.md:75`, but the task body explicitly marks frontmatter AC as authoritative at `.owlbear/kanban/tasks/1617-p2-09-filter-panel-pds-controls.md:249`. Non-blocking because current code/tests match the live contract.
- Adjacent risk only: the tags update listener is attached at `serve/cockpit/web/src/components/FilterPanel.tsx:85` through a ref assigned only when `availableTags.length > 0` at `serve/cockpit/web/src/components/FilterPanel.tsx:207` and `serve/cockpit/web/src/components/FilterPanel.tsx:215`, so an `availableTags=[] -> non-empty` transition is not covered by current proof. This is outside the three AC lines for #1617.
- Reflection:
  - Independent rerun closed an evidence-quality gap without uncovering a code defect.
  - The task-scoped tests use good falsifiability guards for `no aria-checked` and `no native option`, which materially strengthens the PASS.
  - The live frontmatter AC, not the historical research note, is the operative contract for this task.

[[2026-05-17T14:55:58+02:00]]
## Docs Gate

### Checklist

**Item 1 — README Verification**
Convention mapping: `serve/cockpit/web/src/components/FilterPanel.tsx` + `FilterPanel.css` → `serve/cockpit/README.md`.
Finding: #1617 entry absent from the "Accessibility and responsive state" bullet list between #1614 and #1628.
Fix: Added #1617 entry describing PCheckbox controlled wrapper (AC1), PSelectOption children (AC2), and `.filter-panel` flex layout with `--p-spacing-static-sm` (AC3). Verified by `FilterPanel_PDS_1617.test.tsx` (13 tests) and durable `FilterPanel.test.tsx` (40 tests).
Layer 1 (grep): `#1617` present at lines 165 and 171; removed symbols not present; format consistent with adjacent entries.
Layer 2 (editorial): Entry factually matches reviewer AC-evidence table; token name `--p-spacing-static-sm` matches reconciled AC3; test counts (13+40=53) match reviewer's independent run.
Commit: `2943784`

**Item 2 — External Attribution**
`.owlbear/sources/overview.md` already contains a #1617 section (line 57) documenting PDS docs and GitHub sources studied during research. No update needed.

**Item 3 — Research Doc**
`.owlbear/research/filter-panel-pds-controls.md` exists and is linked from the task body ("Research doc: .owlbear/research/filter-panel-pds-controls.md"). ✓

**Item 4 — Deletion Detection**
No files deleted in builder commit `281883df`. No orphaned references. N/A.

### Files Updated
- `serve/cockpit/README.md` — added #1617 bullet in "Accessibility and responsive state" section

### Scratch Cleanup
Removed 20 scratch files: `1617-*.log` / `1617-*.txt` — all cleaned.

[[2026-05-17T15:26:05+02:00]]
## Audit
### Regression Detection
- quality-runner mode full: 2074 passed, 10 failed, 11 skipped; eslint/stylelint clean
- All 10 failures confirmed pre-existing background debt (FilterAccessibilityPanel AC9 ×3 reproduce identically on pre-builder code at 281883df~1; DecisionViewport ×2, PdsMigration ×3, RepairPanel ×1, SidecarUX ×1 are in unrelated domains, last modified in cd8d74c3 whitespace cleanup)
- regression verdict: PASS

### Intent Verification
- scope alignment: PASS (changed files: FilterPanel.tsx + FilterPanel.css in serve/cockpit/web/src/components/ — cockpit frontend domain matches task scope)
- purpose match: PASS (migrate filter panel to PDS wrappers: PCheckbox with checked/onChange, PSelectOption children, flex layout with design tokens)
- extraneous scope: none
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 4/5
AC lines are specific and testable — name exact components, props, CSS properties, and token values. Required one reconciliation cycle (deprecated --pds-spacing-sm → --p-spacing-static-sm per #1603 migration baseline), otherwise clean. Minor gap: research findings referenced pre-migration tokens, but architect corrected in re-review and annotated provenance clearly.

### Commit Integrity
- upstream commit presence: PASS (db5df013 researcher, d2086d42 test-writer, 281883df builder, 29437844 doc-writer — all properly attributed with #1617 and agent role)
- kanban commit packaging: pending (this step)

### Deduction Breakdown
No deductions applied.

### Confidence: 1.00
### Action: archive
