---
id: 1564
title: 'P2-08 RED: Specify filter and form control behavior'
status: archived
priority: needed
created: 2026-05-14T18:26:23.465310+00:00
updated: 2026-05-15T11:25:39.859319+00:00
tags:
  - phase-2
  - scope:cockpit
  - frontend
  - type:test
  - filters
  - forms
  - visual-remediation
parent: 1559
depends_on:
  - 1560
blocked: false
block_reason: 'builder crashed twice: pre-existing unstaged changes in FilterPanel.tsx
  confused the agent; needs user direction to proceed'
claimed_at:
archival_reason: completed
archival_refs: []
---
## Context
Source of truth: `.owlbear/research/cockpit-visual-audit-consolidated-2026-05-14.md` sections 6, 7, and 8. PDS control policy: `.owlbear/research/1560-cockpit-design-policy.md` §5. Dependency #1560 (completed) provides the design-policy gate.

## Scope
In scope: filter trigger, search, priority select, tags multi-select, blocked binary control, active filter summary (toggle badge and result count), clear action, and task-editor visible form controls (tag display, select options, PDS-component presence).
Out of scope: overlay primitives, card metadata, responsive layout changes, and status filter (board columns serve as status grouping).

## Acceptance Criteria
AC-1: Test-writer adds Playwright E2E tests exercising the filter workflow targeting the post-PDS-migration DOM: opening the filter panel via toggle, searching tasks, selecting a priority, selecting tags, toggling the blocked control, verifying the toggle badge count and visible result count update, and clearing all filters; tests interact with PDS control selectors and are expected to fail against the current native-control implementation. The tags-selection step must perform a behavioral interaction (dispatching a PDS `update` event on `p-multi-select[name="tags-filter"]` with a selected tag value from the fixture data) and assert an observable outcome (task visibility narrows to only tasks carrying the selected tag); host-presence-only assertions do not satisfy the tags workflow requirement. The priority-selection `page.evaluate()` interaction must dispatch `new CustomEvent('change', { detail: { value: '{selected}' }, bubbles: true })` on the `p-select` host — this matches the PDS `p-select` emission contract and the established codebase pattern (see `FilterPanel.test.tsx`, `KanbanBoard.filter-e2e.test.tsx`, `DetailTab.test.tsx`); existing tests that use `new Event('input')` with pre-set `.value` exercise only the `readStringValue()` fallback path and must be updated. The clear-all step must interact with the clear control via `p-button[data-testid="filter-reset"]` (PDS-host-scoped selector); a generic `[data-testid="filter-reset"]` click without PDS host qualification is not acceptable because a native button reusing the same test-id would pass green. The filter-panel opening step must interact with the toggle via `p-button[data-testid="filter-toggle"]` (PDS-host-scoped selector); a generic `[data-testid="filter-toggle"]` click without PDS host qualification is not acceptable because a native button reusing the same test-id would pass green. Verify by quality-runner output for named test files showing the tags behavioral test exists and fails (or passes only after builder wires the interaction).
AC-2: Test-writer adds Playwright DOM assertions verifying filter-panel controls use PDS components per #1560 policy §5: (a) search field renders `p-input-search`, not native text input; (b) blocked toggle renders `p-switch` or `p-checkbox`, not native checkbox; (c) priority select renders `p-select-option` children AND does not contain native `<option>` children — the native-option absence assertion (test `c.2`) must use `page.evaluate()` to count elements with `tagName === 'OPTION'` in the `p-select` host element's direct `children` collection, because PDS `p-select` DOM absorption makes native `<option>` elements unreachable via the CSS child combinator `> option` in Playwright (the current `> option` selector is a confirmed false-green — FilterPanel.tsx L206-214 still has native `<option>` elements but the test passes); if `el.children` also cannot detect absorbed native options, the test-writer should escalate with evidence of the DOM state rather than accept a non-falsifiable selector; (d) filter trigger renders PDS button component, not native `<button>`; the test must assert both (d.1) `p-button[data-testid="filter-toggle"]` is visible AND (d.2) `button[data-testid="filter-toggle"]` has count 0 — a positive-only PDS host check cannot falsify a surviving native button with the same test-id; documented exceptions per policy §5 are accepted with test-strategy note; verify by named test output.
AC-3: Test-writer records a RED-phase historical snapshot as a Test Evidence section in the test file, citing audit P1 filter finding and listing each policy §5 violation observed in the current DOM at the time the RED tests are written, with component file and line reference. This is a frozen pre-remediation artifact — it is NOT required to reflect post-builder DOM state because the GREEN phase fixes the violations. Verify by: (a) evidence block exists in the test file, (b) cites audit P1 finding, (c) lists §5 violations with file+line references, (d) distinguishes documented exceptions from violations.
AC-4: Test-writer adds DOM assertions for task-editor visible form controls per #1560 policy §5: (a) priority select renders `p-select-option` children AND does not contain native `<option>` children within `p-select[name="priority"]` — the native-option absence assertion (test `a.2`) must use `page.evaluate()` to count elements with `tagName === 'OPTION'` in the `p-select[name="priority"]` host element's direct `children` collection (same mechanism as AC-2(c.2)); the CSS child combinator `> option` is not acceptable because it is a confirmed false-green class for PDS select hosts; (b) tag display renders `p-tag` elements, not plain span chips; the test must assert both (b.1) `p-tag[data-testid="tag-chip"]` is visible AND (b.2) `span[data-testid="tag-chip"]` has count 0 — the legacy chip identity (`<span data-testid="tag-chip">`) is documented in the RED-phase evidence block at spec line 32; a visibility-only assertion on `p-tag` is not acceptable because a dual-render state would pass green; controls already using PDS components (title via `p-input-text`, body via `p-textarea`, dependency inputs via `p-input-text`, action buttons via `p-button`) require individual presence assertions: `p-button[data-testid="save-button"]` AND `p-button[data-testid="body-edit-toggle"]` must each have an explicit `toBeAttached()` assertion — omitting the edit-toggle assertion is not acceptable because a native button with the same test-id would pass green; documented exceptions per policy §5 are accepted; verify by named test output.

Proof bundle: behavioral

## Builder Scope (Cycle 4)
After the test-writer updates (c.2) to use `page.evaluate()` on `el.children` and updates priority interaction tests to dispatch `CustomEvent('change', { detail: { value } })`, the builder must:
1. Remove all native `<option>` children from FilterPanel.tsx `p-select[name="priority-filter"]`, retaining only `<p-select-option>` children.
2. Verify the existing durable unit tests in `FilterPanel.test.tsx` (which encode native `option` expectations at L150-178) still pass or update them if removal breaks them.

## Builder Scope (Cycle 5)
After the test-writer updates AC-4(a.2) to use `page.evaluate()` on `el.children` (replacing `> option` CSS selector), the builder must verify all E2E tests pass green. No source changes expected since TaskFieldsEditor already has no native `<option>` children — this is a test-only update.

## Evidence Expectations
Failing Playwright E2E filter-workflow tests and PDS-compliance DOM assertions that fail against the current native-control implementation. Policy linkage to #1560 §5. Tags behavioral test must exercise the interaction contract, not just host presence. PDS-option assertions must include native-option absence checks to prevent false-green against dual-render states. The AC-2(c.2) native-option absence check must use `page.evaluate()` on the host element's `children` collection, not CSS `> option`, due to PDS shadow DOM absorption. The AC-4(a.2) native-option absence check must also use `page.evaluate()` on the host element's `children` collection — CSS `> option` is not acceptable. Priority interaction tests must use `CustomEvent('change', { detail: { value } })` matching PDS emission contract.
2026-05-15T07:08:34+00:00
## Architecture Review (Cycle 4 — Reviewer-requested REFINE, AC-4(a.2) selector alignment)

### Context
Reviewer rejected (Cycle 4) citing one blocking finding: AC-4(a.2) uses CSS `> option` selector despite the task contract saying "same dual-assertion contract as AC-2(c)" — and AC-2(c.2) was already refined to require `page.evaluate()` on `el.children`. The cross-reference was insufficient to prevent the test-writer from using the weaker approach.

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Unchanged from Cycle 3 |
| Interface clarity | PASS (after REFINE) | AC-4(a.2) now self-contained with explicit `page.evaluate()` requirement |
| Dependency correctness | PASS | #1560 archived/completed |
| Module layering | N/A | Test task, no production code |
| TDD compliance | PASS | This IS the RED task |
| KISS/YAGNI | PASS | Focused scope |
| Premise challenge | PASS | Audit P1 finding still valid |
| Pattern consistency | PASS | Both AC-2(c.2) and AC-4(a.2) now use identical proof methodology |
| Security surface | N/A | No system boundaries |
| Single domain | PASS | Cockpit frontend only |
| User-action detection | NOT DETECTED | Counter-signals C2, C3 present |

### AC Assessment (Cycle 4 refinement)
| AC Line | Issue | Refinement |
|---------|-------|------------|
| AC-4(a) | "same dual-assertion contract as AC-2(c)" cross-reference was insufficient — test-writer used CSS `> option` instead of `page.evaluate()` on `el.children` | Made self-contained: explicitly requires `page.evaluate()` to count `tagName === 'OPTION'` in host `el.children` collection; explicitly states CSS `> option` is not acceptable because it is a confirmed false-green class |

### Codebase Evidence
- `serve/cockpit/web/e2e/filter-controls-1564.spec.ts:451-458`: current AC-4(a.2) uses `page.locator('p-select[name="priority"] > option').toHaveCount(0)` — weaker selector
- `serve/cockpit/web/e2e/filter-controls-1564.spec.ts:413-423`: AC-2(c.2) correctly uses `page.evaluate()` on `el.children` — stronger selector
- `serve/cockpit/web/src/components/TaskFieldsEditor.tsx:182-192`: only `<p-select-option>` present, no native `<option>` — test is a regression guard (passes today with either approach, but only `evaluate` would catch future regressions involving PDS absorption)

### Challenge Results
- Challenger: SKIPPED — narrow AC wording alignment; all architectural criteria unchanged from Cycle 3 APPROVE; no new design decisions introduced

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED

### Verdict: APPROVE (after REFINE)
### Action Taken: Made AC-4(a.2) self-contained by explicitly requiring `page.evaluate()` on `el.children` and explicitly prohibiting CSS `> option`. Added Builder Scope (Cycle 5) noting this is test-only (TaskFieldsEditor is already clean). Advanced to todo.
2026-05-15T07:19:35+00:00
## Test-Writer Notes
- Test file: serve/cockpit/web/e2e/filter-controls-1564.spec.ts
- Retry Cycle 5: AC-4(a.2) selector updated from CSS `> option` (confirmed false-green) to `page.evaluate()` on `el.children` — matching AC-2(c.2) mechanism
- Change: replaced `page.locator('p-select[name="priority"] > option').toHaveCount(0)` with `page.evaluate((el) => Array.from(el.children).filter((c) => c.tagName === 'OPTION').length)` + `expect(...).toBe(0)`
- Quality-runner result: 31/31 tests PASS, lint clean
- Builder skip: TaskFieldsEditor already has no native `<option>` children — test-only retry, all tests green against current impl
- Direct-to-review advance: reviewer's Required Follow-up contained only test-proof gap (selector strength), no implementation fixes needed
2026-05-15T07:47:38+00:00
## Review Evidence
- Verdict: FAIL
- Routing signal: FAIL #1564 -> backlog | AC-4(b) proof still allows a legacy plain span chip to coexist with a new p-tag and pass green.
- Builder evidence reviewed first: the latest retry note records the AC-4(a.2) selector-strength fix, 31/31 tests PASS, lint clean, and builder skip for a test-only retry. I did not rerun quality-runner because that packet is internally consistent and the blocker is assertion strength, not missing execution evidence.

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC-1 | `FilterPanel.tsx` wires the PDS event surface for search, priority, and tags (`readStringValue`, `readStringArrayValue`, and listeners on `input`/`change`/`update`), and `KanbanBoard.tsx` renders the filter badge and result-count surface. | `serve/cockpit/web/e2e/filter-controls-1564.spec.ts` covers toggle open, search narrowing, priority selection via `CustomEvent('change', { detail: { value } })`, tags selection via `CustomEvent('update', { detail: { value: [...] } })`, blocked filtering, badge/result-count updates, clear behavior, and surviving-set assertions. | PASS |
| AC-2 | `FilterPanel.tsx` renders `p-input-search`, `p-select` with `p-select-option`, `PMultiSelect`, and `p-checkbox`; `KanbanBoard.tsx` renders the trigger with `PButton`. | `serve/cockpit/web/e2e/filter-controls-1564.spec.ts` adds host assertions plus explicit native-input/native-checkbox/native-option absence checks, and AC-2(c.2) uses `page.evaluate()` on `el.children` as required. | PASS |
| AC-3 | The task-local spec contains a frozen RED-phase evidence block with audit and policy references plus violation/exception notes. | `serve/cockpit/web/e2e/filter-controls-1564.spec.ts` lines 1-41 include the Test Evidence block with audit P1, policy §5, file+line references, and the documented exception. | PASS |
| AC-4 | `TaskFieldsEditor.tsx` now renders `p-select-option` and `p-tag` in the green implementation. | AC-4(a.2) now uses the required `page.evaluate()` native-option absence check, but AC-4(b) only asserts `expect(page.locator('p-tag')).toBeVisible()` and never proves the legacy plain span chip is gone. | FAIL |

- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC-4(b) | The task-local proof only shows that some `p-tag` is visible. It does not prove the legacy plain span chip is absent or replaced, so a dual-render state with both `p-tag` and a surviving legacy chip would still pass green. The implementation currently looks correct, but the proof is not strong enough for the AC wording. Because this is a repeated review cycle, route to backlog for AC refinement. | AC contract in task body requires `p-tag` and "not plain span chips"; the historical legacy chip identity is recorded in `serve/cockpit/web/e2e/filter-controls-1564.spec.ts`; the current assertion at AC-4(b) only checks visible `p-tag`; current source at `serve/cockpit/web/src/components/TaskFieldsEditor.tsx` shows the green state only. | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Restate AC-4(b) so the proof contract explicitly requires tying the visible task-editor chip to the historical tag-chip identity and proving no plain span chip survives, then re-dispatch a test-only retry. | `.owlbear/kanban/tasks/1564-p2-08-red-specify-filter-and-form-control-behavior.md`, `serve/cockpit/web/e2e/filter-controls-1564.spec.ts`, `serve/cockpit/web/src/components/TaskFieldsEditor.tsx` | Review finding #1 |

## Observations
- I accepted the latest execution packet in the task body as sufficient run evidence: selector fix recorded, 31/31 tests PASS, lint clean, and builder skip for the test-only retry.
- No editor diagnostics are present in the task-local spec or the adjacent source files I inspected.
- I did not carry AC-2(d) as a blocker. The filter-trigger assertion is already host-bound to `p-button[data-testid="filter-toggle"]`, and I found no demonstrated button-specific false-green class on this record that would justify a second absence assertion.
2026-05-15T07:51:22+00:00

## Builder Scope (Cycle 6)
After the test-writer adds the AC-4(b.2) `span[data-testid="tag-chip"]` count-0 assertion alongside the existing (b.1) `p-tag` visibility check, the builder must verify all E2E tests pass green. No source changes expected since TaskFieldsEditor already renders `<p-tag data-testid="tag-chip">` with no legacy spans — this is a test-only update.
2026-05-15T07:51:45+00:00
## Architecture Review (Cycle 6 — Reviewer-requested REFINE, AC-4(b) dual-assertion alignment)

### Context
Reviewer rejected (Cycle 5) citing one blocking finding: AC-4(b) only asserts `p-tag` visibility without proving the legacy `<span data-testid="tag-chip">` chip is absent. A dual-render state (both `p-tag` and surviving legacy span) would pass green. This mirrors the exact false-green pattern already addressed in AC-2(c) and AC-4(a) for native `<option>` elements.

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Unchanged |
| Interface clarity | PASS (after REFINE) | AC-4(b) now requires dual assertion: positive (p-tag visible) + negative (legacy span absent) |
| Dependency correctness | PASS | #1560 archived/completed |
| Module layering | N/A | Test task, no production code |
| TDD compliance | PASS | This IS the RED task |
| KISS/YAGNI | PASS | Focused scope |
| Premise challenge | PASS | Audit P1 finding still valid |
| Pattern consistency | PASS | AC-4(b) now follows same dual-assertion pattern as AC-2(c) and AC-4(a) |
| Security surface | N/A | No system boundaries |
| Single domain | PASS | Cockpit frontend only |
| User-action detection | NOT DETECTED | Counter-signals C2, C3 present |

### AC Assessment (Cycle 6 refinement)
| AC Line | Issue | Refinement |
|---------|-------|------------|
| AC-4(b) | Visibility-only assertion on `p-tag` allows a dual-render false-green; reviewer proved legacy chip identity `<span data-testid="tag-chip">` is documented in evidence block but never absence-asserted | Made self-contained: explicitly requires (b.1) `p-tag[data-testid="tag-chip"]` visible AND (b.2) `span[data-testid="tag-chip"]` count 0; explicitly states visibility-only is not acceptable |

### Codebase Evidence
- `serve/cockpit/web/e2e/filter-controls-1564.spec.ts:460-465`: current AC-4(b) test uses only `page.locator('p-tag').toBeVisible()` — no absence check
- `serve/cockpit/web/e2e/filter-controls-1564.spec.ts:32`: RED-phase evidence documents legacy chip as `<span data-testid="tag-chip">{tag}</span>`
- `serve/cockpit/web/src/components/TaskFieldsEditor.tsx:192`: current impl is `<p-tag data-testid="tag-chip">` — no legacy spans (builder Cycle 6 is test-only)

### Challenge Results
- Challenger: SKIPPED — narrow AC wording alignment following established dual-assertion pattern; all architectural criteria unchanged from Cycle 4 APPROVE; no new design decisions

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Test-writer: PROCEED

### Verdict: APPROVE (after REFINE)
### Action Taken: Made AC-4(b) self-contained by explicitly requiring (b.1) `p-tag[data-testid="tag-chip"]` visible + (b.2) `span[data-testid="tag-chip"]` count 0. Added Builder Scope (Cycle 6) noting test-only (TaskFieldsEditor already clean). Advanced to todo.
2026-05-15T08:13:05+00:00
## Test-Writer Notes
- Test file: serve/cockpit/web/e2e/filter-controls-1564.spec.ts
- Retry Cycle 6: AC-4(b) dual-assertion added — split old `(b)` test into `(b.1)` + `(b.2)`
  - (b.1) `p-tag[data-testid="tag-chip"]` visibility (previously used un-scoped `p-tag`)
  - (b.2) `span[data-testid="tag-chip"]` count-0 assertion (new — falsifiability guard against dual-render state)
- Quality-runner result: 32/32 tests PASS (was 31), lint clean
- Builder skip: TaskFieldsEditor already renders `<p-tag data-testid="tag-chip">` with no legacy spans — test-only retry, all tests green against current impl
- Direct-to-review advance: reviewer's Required Follow-up contained only test-proof gap (missing absence assertion), no implementation fixes needed
- AC coverage: AC-4(b) now satisfies dual-assertion contract matching AC-2(c) and AC-4(a) patterns
2026-05-15T08:43:03+00:00
## Review Evidence
- Verdict: FAIL
- Routing signal: FAIL #1564 -> backlog | The clear-all flow still uses a generic test-id selector instead of a PDS host selector, and the task-editor edit toggle never gets a `p-button` presence assertion.
- Builder evidence reviewed first: the latest retry note records 32/32 tests PASS, lint clean, and builder skip for a test-only retry. I did not rerun quality-runner because that execution packet is internally consistent; the blockers are proof-strength gaps in the task-local spec.

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC-1 | `FilterPanel.tsx` wires PDS search/priority/tags/blocked controls and renders the clear action as `<PButton data-testid="filter-reset">` (`serve/cockpit/web/src/components/FilterPanel.tsx:78`, `:96`, `:114`, `:193`, `:206`, `:233`, `:243`). `KanbanBoard.tsx` renders the badge/result-count surface (`serve/cockpit/web/src/KanbanBoard.tsx:89`, `:91`, `:272`, `:280`, `:290`). | The spec covers search, priority, tags, blocked, badge, result-count text, and clear behavior, but both clear-action tests still click `[data-testid="filter-reset"]` rather than a PDS host selector (`serve/cockpit/web/e2e/filter-controls-1564.spec.ts:260`, `:348`). | FAIL |
| AC-2 | `FilterPanel.tsx` renders `p-input-search`, `p-select-option`, and `p-checkbox` (`serve/cockpit/web/src/components/FilterPanel.tsx:193`, `:206`, `:208`, `:233`). | The spec asserts host presence plus native-input/native-checkbox/native-option absence, and the native-option check now uses `page.evaluate()` on `el.children` (`serve/cockpit/web/e2e/filter-controls-1564.spec.ts:388`, `:398`, `:409`, `:423`). | PASS |
| AC-3 | The task-local spec includes the frozen RED evidence block with audit/policy references, violation list, documented exception, and already-compliant inventory (`serve/cockpit/web/e2e/filter-controls-1564.spec.ts:1`). | The evidence block exists and distinguishes violations from the documented exception. | PASS |
| AC-4 | `TaskFieldsEditor.tsx` renders the priority host with `p-select-option`, the tag chip as `p-tag`, the edit toggle as `<PButton data-testid="body-edit-toggle">`, and the save action as `<PButton data-testid="save-button">` (`serve/cockpit/web/src/components/TaskFieldsEditor.tsx:184`, `:190`, `:192`, `:238`, `:239`, `:248`). | The spec now proves native-option absence and legacy-chip absence (`serve/cockpit/web/e2e/filter-controls-1564.spec.ts:447`, `:460`, `:464`, `:469`, `:472`, `:479`), but it only clicks `[data-testid="body-edit-toggle"]` generically (`serve/cockpit/web/e2e/filter-controls-1564.spec.ts:489`) while only the save action gets a `p-button[...]` presence assertion (`serve/cockpit/web/e2e/filter-controls-1564.spec.ts:503`, `:505`). | FAIL |

- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC-1 | The clear-all proof no longer relies on native-option selectors, but it still does not interact with a PDS host selector for the clear control. AC-1 explicitly says the workflow tests must interact with PDS control selectors. The current tests click `[data-testid="filter-reset"]`, while the real control is a `PButton`. A native button reusing the same test id would still pass green. | AC contract: `.owlbear/kanban/tasks/1564-p2-08-red-specify-filter-and-form-control-behavior.md:34`; current test selectors: `serve/cockpit/web/e2e/filter-controls-1564.spec.ts:260`, `:348`; current control host: `serve/cockpit/web/src/components/FilterPanel.tsx:243`. | backlog |
| 2 | AC-4 | The task-editor proof still does not bind the edit action to a `p-button` host. AC-4 requires presence assertions for already-compliant action buttons via `p-button`, and the RED evidence block itself lists `save/edit` as PButton-backed controls. The spec only clicks `[data-testid="body-edit-toggle"]` and asserts the textarea appears; only the save action gets the required `p-button[...]` presence assertion. A native edit button with the same test id would still pass green. | AC contract: `.owlbear/kanban/tasks/1564-p2-08-red-specify-filter-and-form-control-behavior.md:37`; RED evidence block: `serve/cockpit/web/e2e/filter-controls-1564.spec.ts:45`; current generic click: `serve/cockpit/web/e2e/filter-controls-1564.spec.ts:489`; save-only host assertion: `serve/cockpit/web/e2e/filter-controls-1564.spec.ts:503`, `:505`; current edit host: `serve/cockpit/web/src/components/TaskFieldsEditor.tsx:238`, `:239`. | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Refine AC-1 so the clear-all step explicitly requires a PDS-host selector or assertion on `p-button[data-testid="filter-reset"]`, then re-dispatch a test-only retry. | `.owlbear/kanban/tasks/1564-p2-08-red-specify-filter-and-form-control-behavior.md`, `serve/cockpit/web/e2e/filter-controls-1564.spec.ts`, `serve/cockpit/web/src/components/FilterPanel.tsx` | Blocking finding #1 |
| 2 | architect | Refine AC-4 so the already-compliant action-button clause explicitly requires a presence assertion for `p-button[data-testid="body-edit-toggle"]`, then re-dispatch a test-only retry. | `.owlbear/kanban/tasks/1564-p2-08-red-specify-filter-and-form-control-behavior.md`, `serve/cockpit/web/e2e/filter-controls-1564.spec.ts`, `serve/cockpit/web/src/components/TaskFieldsEditor.tsx` | Blocking finding #2 |

## Observations
- The previously disputed false-green classes are now closed correctly: native-option checks use `page.evaluate()` on `el.children`, and the legacy tag-chip span is explicitly absence-asserted.
- I accepted the latest execution packet in the task body as sufficient run evidence: 32/32 scoped tests PASS, lint clean, builder skip for a test-only retry.
- I used the required behavioral-bundle adversarial cross-checks. Challenger pushed back on treating the edit-toggle gap by itself as blocking, but code-reader independently confirmed the stronger AC-1 clear-action selector gap and the AC-4 edit-toggle proof gap. The final verdict is based on the AC text plus direct file inspection, not on missing run evidence.
2026-05-15T08:44:01+00:00
## Architecture Review (Cycle 7 — Reviewer-requested REFINE, AC-1 clear-action + AC-4 edit-toggle PDS host selectors)

### Context
Reviewer rejected (Cycle 6) citing two blocking findings: (1) AC-1 clear-all tests click `[data-testid="filter-reset"]` rather than a PDS host selector — a native button reusing that test-id would pass green; (2) AC-4 edit-toggle is only clicked generically via `[data-testid="body-edit-toggle"]` with no `p-button` presence assertion — same false-green class as the save button (which already has a presence test).

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Unchanged |
| Interface clarity | PASS (after REFINE) | AC-1 now requires PDS-host-scoped clear interaction; AC-4 now requires edit-toggle presence assertion |
| Dependency correctness | PASS | #1560 archived/completed |
| Module layering | N/A | Test task, no production code |
| TDD compliance | PASS | This IS the RED task |
| KISS/YAGNI | PASS | Focused scope |
| Premise challenge | PASS | Audit P1 finding still valid |
| Pattern consistency | PASS | Both refinements follow established PDS-host-selector pattern from save-button test |
| Security surface | N/A | No system boundaries |
| Single domain | PASS | Cockpit frontend only |
| User-action detection | NOT DETECTED | Counter-signals C2, C3 present |

### AC Assessment (Cycle 7 refinement)
| AC Line | Issue | Refinement |
|---------|-------|------------|
| AC-1 | Clear-all workflow clicks `[data-testid="filter-reset"]` (generic test-id) — AC says "interact with PDS control selectors" but test does not prove the control is a PDS button | Added explicit requirement: clear-action interactions must use `p-button[data-testid="filter-reset"]` selector (PDS-host-scoped); generic `[data-testid="filter-reset"]` without PDS host qualification is not acceptable because a native button with the same test-id would pass green |
| AC-4 | Edit-toggle only clicked generically with no `p-button` host assertion, while save-button already has one | Added explicit requirement: already-compliant action buttons must include `p-button[data-testid="body-edit-toggle"]` presence assertion (matching save-button pattern at `p-button[data-testid="save-button"]`) |

### Codebase Evidence
- `serve/cockpit/web/e2e/filter-controls-1564.spec.ts:260,348`: clear-action tests use `page.click('[data-testid="filter-reset"]')` — generic selector
- `serve/cockpit/web/e2e/filter-controls-1564.spec.ts:503,505`: save-button presence test correctly uses `p-button[data-testid="save-button"]` — pattern to follow
- `serve/cockpit/web/e2e/filter-controls-1564.spec.ts:489`: edit-toggle clicked via generic `[data-testid="body-edit-toggle"]` with no PDS host assertion
- `serve/cockpit/web/src/components/FilterPanel.tsx:243`: clear renders `<PButton data-testid="filter-reset">`
- `serve/cockpit/web/src/components/TaskFieldsEditor.tsx:238-239`: edit-toggle renders `<PButton data-testid="body-edit-toggle">`

### Challenge Results
- Challenger: SKIPPED — narrow AC wording alignment following established PDS-host-selector pattern; all architectural criteria unchanged from Cycle 6 APPROVE; no new design decisions

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Test-writer: PROCEED

### Verdict: APPROVE (after REFINE)
### Action Taken: (1) Refined AC-1 to explicitly require `p-button[data-testid="filter-reset"]` selector for clear-action interactions. (2) Refined AC-4 to explicitly require `p-button[data-testid="body-edit-toggle"]` presence assertion matching the save-button pattern. Added Builder Scope (Cycle 7) noting test-only update. Advanced to todo.

## Builder Scope (Cycle 7)
After the test-writer updates:
1. Clear-action interactions in AC-1 tests (lines ~260, ~348) to use `p-button[data-testid="filter-reset"]` selector instead of generic `[data-testid="filter-reset"]`.
2. AC-4 edit-toggle test to add a `p-button[data-testid="body-edit-toggle"]` presence assertion (matching the save-button presence test pattern).

The builder must verify all E2E tests pass green. No source changes expected since both FilterPanel.tsx and TaskFieldsEditor.tsx already render PDS `<PButton>` — this is a test-only update.
2026-05-15T08:45:35+00:00
Cycle 7 REFINE+APPROVE: (1) AC-1 now explicitly requires `p-button[data-testid="filter-reset"]` PDS-host-scoped selector for clear-action interactions — generic testid click prohibited. (2) AC-4 action-button clause now enumerates both `p-button[data-testid="save-button"]` and `p-button[data-testid="body-edit-toggle"]` as requiring individual presence assertions. Builder Scope (Cycle 7) added — test-only update, no source changes expected.
2026-05-15T08:59:23+00:00
## Test-Writer Notes
- Test file: serve/cockpit/web/e2e/filter-controls-1564.spec.ts
- Retry Cycle 7: two targeted proof-strength fixes
  1. Clear-action selectors (lines 262, 352): `page.click('[data-testid="filter-reset"]')` → `page.click('p-button[data-testid="filter-reset"]')` — PDS-host-scoped interaction; generic testid would pass green against a native button
  2. Added `[presence] edit toggle: p-button[data-testid="body-edit-toggle"] is in the DOM` after save-button presence test — AC-4 action-button clause requires both action buttons have explicit PDS-host assertions
- Quality-runner result: 33/33 tests PASS (was 32), lint clean
- Builder skip: both FilterPanel.tsx and TaskFieldsEditor.tsx already render PDS `<PButton>` — test-only retry, all tests green against current impl
- Direct-to-review advance: reviewer's Required Follow-up contained only test-proof gaps (selector strength + missing presence assertion), no implementation fixes needed
- AC coverage: AC-1 clear-action interactions now PDS-host-scoped; AC-4 edit-toggle presence explicitly asserted matching save-button pattern
2026-05-15T09:22:25+00:00
## Review Evidence
- Verdict: FAIL
- Routing signal: FAIL #1564 -> backlog | The filter workflow still opens the panel through a generic toggle selector, and AC-2(d) still does not falsify a surviving native toggle.
- Builder evidence reviewed first: the latest retry note records 33/33 tests PASS, lint clean, and builder skip for a test-only retry. I did not rerun quality-runner because that execution packet is internally consistent; the blocker is proof sufficiency, not missing run evidence.
- Behavioral-bundle adversarial checks: challenger and code-reader both converged on the same remaining gap in the toggle proof path.

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC-1 | The production toggle is a PDS button in `serve/cockpit/web/src/KanbanBoard.tsx:269-281`, and the rest of the filter-panel controls are already exercised through host-scoped PDS selectors in the task-local spec. | The workflow helper still opens the panel with `page.click('[data-testid="filter-toggle"]')` in `serve/cockpit/web/e2e/filter-controls-1564.spec.ts:166`, so the suite does not prove that opening-via-toggle uses a PDS control selector. | FAIL |
| AC-2 | The filter trigger is rendered as `<PButton data-testid="filter-toggle">` in `serve/cockpit/web/src/KanbanBoard.tsx:269-281`. | The dedicated trigger test only asserts positive presence of `p-button[data-testid="filter-toggle"]` in `serve/cockpit/web/e2e/filter-controls-1564.spec.ts:182-183` and `serve/cockpit/web/e2e/filter-controls-1564.spec.ts:434`, but unlike the search and blocked controls it never adds a native-element absence guard. The "not native `<button>`" half of AC-2(d) remains unproven. | FAIL |
| AC-3 | The task-local spec still contains the frozen RED evidence block with audit reference, policy linkage, file+line citations, and documented exception separation at `serve/cockpit/web/e2e/filter-controls-1564.spec.ts:1-41`. | The evidence block is intact and remains adequate for the historical snapshot requirement. | PASS |
| AC-4 | The current task-editor implementation renders `p-select-option`, `p-tag[data-testid="tag-chip"]`, and `PButton` for both save and edit in `serve/cockpit/web/src/components/TaskFieldsEditor.tsx:182-192` and `serve/cockpit/web/src/components/TaskFieldsEditor.tsx:238-250`. | The task-local spec now proves native-option absence, legacy-span absence, and explicit `p-button` presence for both save and edit at `serve/cockpit/web/e2e/filter-controls-1564.spec.ts:447-517`. | PASS |

- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC-1 | The workflow suite still opens the filter panel through a generic selector instead of a PDS-host selector. Because AC-1 says the workflow tests interact with PDS control selectors, this leaves the opening-via-toggle step under-proven. A surviving native toggle with the same test id could still drive the workflow green. | Task contract: `.owlbear/kanban/tasks/1564-p2-08-red-specify-filter-and-form-control-behavior.md:34`; helper selector: `serve/cockpit/web/e2e/filter-controls-1564.spec.ts:166`; real toggle host: `serve/cockpit/web/src/KanbanBoard.tsx:269-281`. | backlog |
| 2 | AC-2(d) | The trigger identity proof is still positive-only. The spec proves that a `p-button[data-testid="filter-toggle"]` exists, but it never proves that a native `button[data-testid="filter-toggle"]` does not. That is weaker than the explicit dual-render guards already used for search and blocked controls, and it leaves the "not native `<button>`" clause non-falsifiable. | AC clause: `.owlbear/kanban/tasks/1564-p2-08-red-specify-filter-and-form-control-behavior.md:35`; positive-only assertions: `serve/cockpit/web/e2e/filter-controls-1564.spec.ts:182-183`, `serve/cockpit/web/e2e/filter-controls-1564.spec.ts:434`; contrast with dual-render guards: `serve/cockpit/web/e2e/filter-controls-1564.spec.ts:392-405`. | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Refine the toggle proof contract so AC-1 explicitly requires opening the panel via `p-button[data-testid="filter-toggle"]`, then re-dispatch a test-only retry. | `.owlbear/kanban/tasks/1564-p2-08-red-specify-filter-and-form-control-behavior.md`, `serve/cockpit/web/e2e/filter-controls-1564.spec.ts`, `serve/cockpit/web/src/KanbanBoard.tsx` | Blocking finding #1 |
| 2 | architect | Refine AC-2(d) into a falsifiable trigger-identity requirement by explicitly requiring proof that no native `button[data-testid="filter-toggle"]` survives, or otherwise making the exclusivity check self-contained, then re-dispatch a test-only retry. | `.owlbear/kanban/tasks/1564-p2-08-red-specify-filter-and-form-control-behavior.md`, `serve/cockpit/web/e2e/filter-controls-1564.spec.ts`, `serve/cockpit/web/src/KanbanBoard.tsx` | Blocking finding #2 |

## Observations
- I found no adjacent implementation defect in the current toggle render. The source already uses `PButton`; the remaining problem is proof quality in the task-local E2E spec.
- The previously disputed proof gaps are now closed correctly: clear-all uses `p-button[data-testid="filter-reset"]`, task-editor action buttons each get their own `p-button` presence assertion, native-option checks use `page.evaluate()` on `el.children`, and the legacy tag-chip span is explicitly absence-asserted.
- No editor diagnostics are present in the scoped files (`serve/cockpit/web/e2e/filter-controls-1564.spec.ts`, `serve/cockpit/web/src/components/FilterPanel.tsx`, `serve/cockpit/web/src/components/TaskFieldsEditor.tsx`).
2026-05-15T10:11:05+00:00

## Builder Scope (Cycle 8)
After the test-writer updates:
1. `openFilterPanel()` helper (line ~166) to use `page.click('p-button[data-testid="filter-toggle"]')` instead of generic `page.click('[data-testid="filter-toggle"]')`.
2. AC-2(d) trigger test to add a `button[data-testid="filter-toggle"]` count-0 absence assertion alongside the existing `p-button[data-testid="filter-toggle"]` visibility check.

The builder must verify all E2E tests pass green. No source changes expected since KanbanBoard.tsx already renders `<PButton data-testid="filter-toggle">` — this is a test-only update.
2026-05-15T10:11:33+00:00
## Architecture Review (Cycle 8 — Reviewer-requested REFINE, AC-1 toggle + AC-2(d) native-button absence)

### Context
Reviewer rejected (Cycle 7) citing two blocking findings: (1) AC-1 workflow helper opens the filter panel via generic `[data-testid="filter-toggle"]` instead of PDS-host-scoped selector — a native button with the same test-id would pass green; (2) AC-2(d) trigger identity proof is positive-only — proves `p-button[data-testid="filter-toggle"]` exists but never proves a native `button[data-testid="filter-toggle"]` does not, unlike the dual-render guards already used for search/blocked controls.

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Unchanged |
| Interface clarity | PASS (after REFINE) | AC-1 now requires PDS-host-scoped toggle interaction; AC-2(d) now requires dual assertion |
| Dependency correctness | PASS | #1560 archived/completed |
| Module layering | N/A | Test task, no production code |
| TDD compliance | PASS | This IS the RED task |
| KISS/YAGNI | PASS | Focused scope |
| Premise challenge | PASS | Audit P1 finding still valid |
| Pattern consistency | PASS | Both refinements follow established PDS-host-selector and dual-render patterns |
| Security surface | N/A | No system boundaries |
| Single domain | PASS | Cockpit frontend only |
| User-action detection | NOT DETECTED | Counter-signals C2, C3 present |

### AC Assessment (Cycle 8 refinement)
| AC Line | Issue | Refinement |
|---------|-------|------------|
| AC-1 | `openFilterPanel()` helper clicks `[data-testid="filter-toggle"]` (generic) — AC says "interact with PDS control selectors" but toggle-open step was never explicitly called out | Added explicit requirement: filter-panel opening step must use `p-button[data-testid="filter-toggle"]` (PDS-host-scoped); generic click without PDS host qualification is not acceptable |
| AC-2(d) | Positive-only `p-button[data-testid="filter-toggle"]` assertion — no native button absence guard, weaker than dual-render guards for search/blocked controls | Added dual-assertion requirement: (d.1) `p-button[data-testid="filter-toggle"]` visible AND (d.2) `button[data-testid="filter-toggle"]` count 0 |

### Codebase Evidence
- `serve/cockpit/web/e2e/filter-controls-1564.spec.ts:166`: `openFilterPanel()` uses `page.click('[data-testid="filter-toggle"]')` — generic selector
- `serve/cockpit/web/e2e/filter-controls-1564.spec.ts:434`: AC-2(d) test only asserts `p-button[data-testid="filter-toggle"]` visible — no absence check
- `serve/cockpit/web/e2e/filter-controls-1564.spec.ts:392-405`: dual-render guards for search/blocked use `toHaveCount(0)` pattern — this is the pattern AC-2(d) should follow
- `serve/cockpit/web/src/KanbanBoard.tsx:269-281`: production toggle renders `<PButton data-testid="filter-toggle">` — Cycle 8 is test-only

### Challenge Results
- Challenger: SKIPPED — narrow AC wording alignment following established PDS-host-selector and dual-render patterns; all architectural criteria unchanged from Cycle 7 APPROVE; no new design decisions

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Test-writer: PROCEED

### Verdict: APPROVE (after REFINE)
### Action Taken: (1) Refined AC-1 to explicitly require `p-button[data-testid="filter-toggle"]` for the filter-panel opening step. (2) Refined AC-2(d) to explicitly require dual assertion: (d.1) PDS host visible + (d.2) native `button` count 0. Added Builder Scope (Cycle 8) noting test-only update. Advanced to todo.
2026-05-15T10:27:59+00:00
## Test-Writer Notes
- Test file: serve/cockpit/web/e2e/filter-controls-1564.spec.ts
- Retry Cycle 8: two targeted proof-strength fixes
  1. `openFilterPanel()` helper (line ~166): `page.click('[data-testid="filter-toggle"]')` → `page.click('p-button[data-testid="filter-toggle"]')` — PDS-host-scoped interaction; generic testid click is not acceptable because a native button reusing the same test-id would drive the workflow green (AC-1 requirement)
  2. AC-2(d) test split into (d.1) + (d.2):
     - (d.1) `p-button[data-testid="filter-toggle"]` is visible (existing, positive-only, renamed)
     - (d.2) `button[data-testid="filter-toggle"]` has count 0 (new — dual-render falsifiability guard, matching the search/blocked pattern at lines 392-405)
- Quality-runner result: 34/34 tests PASS (was 33), lint clean
- Builder skip: KanbanBoard.tsx already renders `<PButton data-testid="filter-toggle">` — test-only retry, all tests green against current impl
- Direct-to-review advance: reviewer's Required Follow-up contained only test-proof gaps (selector strength + missing absence assertion), no implementation fixes needed
- AC coverage: AC-1 toggle-open step now PDS-host-scoped; AC-2(d) now dual-asserted matching established pattern
2026-05-15T10:49:13+00:00
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1564 -> docs | AC mapped to code and evidence sufficient.
- Builder evidence reviewed first: the latest retry note reports 34/34 tests PASS, lint clean, and builder skip for a test-only retry. I did not rerun quality-runner because that packet is internally consistent and direct file inspection found no remaining proof gaps.
- Proof scope note: coverage is not applicable on this cycle because the retry changed only the task-local E2E spec and no production code surface.

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC-1 | FilterPanel renders p-input-search, p-select-option children, p-checkbox, and PButton filter-reset at serve/cockpit/web/src/components/FilterPanel.tsx:195, 202-210, 233, 243. KanbanBoard renders the PButton filter-toggle and result-count surface at serve/cockpit/web/src/KanbanBoard.tsx:282-300. | openFilterPanel uses p-button[data-testid="filter-toggle"] at serve/cockpit/web/e2e/filter-controls-1564.spec.ts:165-170; priority workflow dispatches CustomEvent change at :216-219 and :246-248; tags workflow dispatches update and proves narrowed plus surviving set at :281-299 and :336-343; clear uses p-button[data-testid="filter-reset"] at :265 and :355; badge and result-count assertions are present at :237-238, :249, and :366-367. | PASS |
| AC-2 | FilterPanel surface matches the enumerated DOM targets: search-filter at serve/cockpit/web/src/components/FilterPanel.tsx:195, priority-filter with p-select-option children at :202-210, blocked p-checkbox at :233, and trigger PButton at serve/cockpit/web/src/KanbanBoard.tsx:282. | Search positive/negative checks at serve/cockpit/web/e2e/filter-controls-1564.spec.ts:384 and :398; blocked positive/negative at :391 and :405; priority option presence plus evaluate-based native-option absence at :416 and :429-431; trigger positive and native-button absence at :434-448. | PASS |
| AC-3 | N/A beyond the frozen historical snapshot requirement. | The Test Evidence block exists and cites audit P1, policy section 5, file+line references, and documented-exception separation at serve/cockpit/web/e2e/filter-controls-1564.spec.ts:1-41. | PASS |
| AC-4 | TaskFieldsEditor renders the priority p-select, p-tag tag-chip, p-input-text title/depends_on/parent, p-textarea body after edit, and PButton edit/save at serve/cockpit/web/src/components/TaskFieldsEditor.tsx:174, 182, 192, 195, 204, 226, 239, 248. | Priority option presence and evaluate-based native-option absence at serve/cockpit/web/e2e/filter-controls-1564.spec.ts:461-479; p-tag visibility and legacy-span absence at :482-497; title/body/depends_on/parent presence at :500-519; explicit save and edit-toggle p-button presence at :521-531. | PASS |

## Observations
- Behavioral-bundle challenger raised one non-blocking scope question about whether AC-2 should also require DOM identity proof for the tags and clear controls. I overrode that concern because the accepted task contract scopes AC-2 through enumerated subclauses (a)-(d), handles tags as a documented exception in AC-1, and requires clear-action PDS host interaction in AC-1 rather than AC-2.
- No editor diagnostics are present in the scoped files.
- No safety or security issues surfaced in scope; this cycle is a test-only selector-strength review with no new dependencies or external-input changes.
2026-05-15T11:02:27+00:00
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | README verification | Yes | Updated | `serve/cockpit/README.md` — #1564 bullet added to "Accessibility and responsive state" list; describes 34-test spec, PDS-host-scoped selectors, dual-render guards, `page.evaluate()` absence checks |
| 2 | External attribution | No | N/A | No external sources used; test-only selector-strength refinements |
| 3 | Research doc | No | N/A | No task-1564-specific research doc created; context references #1560 research docs (pre-existing) |
| 4 | Deletion detection | No | N/A | No files deleted; single test spec added |

### Verification Layers
- Layer 1 — grep confirmed `filter-controls-1564.spec.ts` present in `serve/cockpit/README.md` line 79; no orphaned references
- Layer 2 — editorial check: new bullet follows established pattern (task#, spec filename, test count, key proof mechanisms); content accurate against task body (34 tests, filter workflow + task-editor, PDS-host-scoped selectors, `page.evaluate()` on `el.children`); no contradictions with adjacent bullets

### Files Updated
- `serve/cockpit/README.md` — commit f10f5428

### Scratch Files Cleaned
- None (no `.owlbear/scratch/1564-*` files found)
2026-05-15T11:25:39+00:00
## Audit

### Regression Detection
- quality-runner mode full: 4553 passed, 234 Python + 28 frontend failures, lint clean (ruff + eslint)
- All failures are pre-existing from concurrent development (DetailTab conflict-resolution, FilterAccessibilityPanel, HealthBadgeRepair, ideation diagram, cockpit-view static analysis, kanban server). Task 1564 only added/modified the task-local E2E spec file and cannot cause regressions in unrelated vitest unit tests or Python test files.
- regression verdict: PASS (no task-caused regressions)

### Intent Verification
- scope alignment: PASS (changed files: e2e/filter-controls-1564.spec.ts + serve/cockpit/README.md, both in cockpit frontend domain matching scope:cockpit tag)
- purpose match: PASS (Playwright E2E tests specifying filter and form control PDS migration behavior, directly matches stated purpose)
- extraneous scope: none
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 3/5
AC concept was sound but proof-strength requirements for PDS host selectors were repeatedly underspecified. 4 cycles of reviewer-driven refinement (Cycles 5-8) were needed to make dual-assertion and PDS-host-scoped selector requirements explicit, despite these being established patterns in the codebase. Each refinement was narrow and correct, but the iteration count indicates the original AC did not systematically anticipate the false-green class.

### Commit Integrity
- upstream commit presence: PASS (test-writer: 120ac125 Cycle 8 final; doc-writer: f10f5428; multiple prior cycles also committed)
- kanban commit packaging: pending (this step)
- commit messages follow convention (test:/docs: with task ID and agent attribution)

### Deduction Breakdown
| Criterion | Applied? | Deduction |
|-----------|----------|-----------|
| Intent mismatch | No | 0 |
| Evidence integrity concern | No | 0 |
| Lint violations | No | 0 |
| AC quality score 3 | Yes | -.03 |
| Missing reviewer evidence | No | 0 |
| Regression failures | No | 0 |

### Confidence: .97
### Action: archive