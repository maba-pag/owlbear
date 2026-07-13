---
id: 1571
title: 'P2-09 GREEN: Recompose Cockpit filters and visible form controls'
status: archived
priority: medium
created: 2026-05-14T18:26:50.109551+00:00
updated: 2026-05-15T14:30:16.614928+00:00
tags:
  - phase-2
  - scope:cockpit
  - frontend
  - type:build
  - filters
  - forms
  - visual-remediation
parent: 1559
depends_on:
  - 1564
  - 1569
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Context
Verifies PDS control compliance from #1564 after #1560 records the PDS control policy and #1569 provides the overlay primitive strategy. Source audit: `.owlbear/research/cockpit-visual-audit-consolidated-2026-05-14.md` sections 6, 7, and 8.

Note: PDS control migration was substantially completed during the #1564 lifecycle (34/34 tests GREEN at archival). This GREEN task verifies the existing implementation against the #1564 proof spec; the builder may find no source changes are needed.

## Scope
In scope: filter workflow controls, active filter summary, clear action, and task-editor visible form-control PDS compliance.
Out of scope: overlay primitive behavior, card metadata, mobile/tablet layout contract, filter-panel layout/reflow behavior (inline panel is the current design — reflow remediation, if needed, is a separate concern), and task-editor priority selection functionality (single-option limitation is a pre-existing concern outside PDS migration scope).

## Acceptance Criteria
AC-1: Given filter trigger opens via `p-button[data-testid="filter-toggle"]`, Cockpit filter panel presents search (`p-input-search[name="search-filter"]`), priority select (`p-select[name="priority-filter"]` with `p-select-option` children), tags multi-select (`p-multi-select[name="tags-filter"]`), blocked toggle (`p-checkbox[name="blocked-filter"]`), active filter badge count in the toggle button, result-count display (`[data-testid="filter-result-count"]`), and clear action (`p-button[data-testid="filter-reset"]`); verify with `serve/cockpit/web/e2e/filter-controls-1564.spec.ts` "AC-1 | Filter workflow via PDS control selectors" test group (16 tests).

AC-2: Given a filter value changes via PDS control interaction (search input, priority `CustomEvent('change', { detail: { value } })`, tags `CustomEvent('update', { detail: { value: [...] } })`, or blocked toggle click), board task-card visibility filters to the matching set and the result-count text reflects the correct ratio; verify with the surviving-set and result-count assertions in `serve/cockpit/web/e2e/filter-controls-1564.spec.ts` AC-1 test group.

AC-3: Filter-panel controls and task-editor visible form controls use mapped PDS components per `1560-cockpit-design-policy.md` §5, with `PMultiSelect` as the documented exception for tags; verify with `serve/cockpit/web/e2e/filter-controls-1564.spec.ts` "AC-2 | FilterPanel PDS compliance assertions" (8 tests including dual-render falsifiability checks) plus policy diff inspection.

AC-4: Task-editor renders PDS controls for priority (`p-select` with `p-select-option`), tag display (`p-tag[data-testid="tag-chip"]`), text fields (`p-input-text` for title/depends_on/parent, `p-textarea` for body), and action buttons (`p-button[data-testid="save-button"]`, `p-button[data-testid="body-edit-toggle"]`); verify with `serve/cockpit/web/e2e/filter-controls-1564.spec.ts` "AC-4 | Task-editor PDS compliance assertions" (10 tests including dual-render falsifiability checks for priority options and legacy tag chips).

Proof bundle: existing
Existing proof scope: `serve/cockpit/web/e2e/filter-controls-1564.spec.ts` (34 tests)

## Evidence Expectations
Passing `serve/cockpit/web/e2e/filter-controls-1564.spec.ts` (34 tests) and policy exception documentation when used.
2026-05-15T13:18:10+00:00
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | PDS control compliance verification for filter panel + task editor — one domain (Cockpit PDS migration) |
| Interface clarity | PASS (after REFINE) | All 4 AC lines now name concrete PDS selectors, test group names, test counts, and PDS event contracts |
| Dependency correctness | PASS | #1564 archived/completed, #1569 archived/completed, #1560 archived/completed |
| Module layering | PASS | Component-level in serve/cockpit/web/src/components/ and serve/cockpit/web/src/; no upward imports |
| TDD compliance | PASS | #1564 is the RED task with 34 E2E tests; proof bundle changed to `existing` (tests already written and pass) |
| KISS/YAGNI | PASS | Scoped to existing PDS control verification; no hypothetical requirements |
| Premise challenge | PASS | Audit sections 6-8 document PDS control violations; #1564 proved remediation requirements |
| Pattern consistency | PASS | Uses established PDS component patterns from @porsche-design-system/components-react |
| Security surface | N/A | No new system boundaries |
| Single domain | PASS | Cockpit frontend only |
| User-action detection | NOT DETECTED | Counter-signals C1 (component signatures), C2 (expected test outcomes), C3 (tagged type:build) |

### AC Assessment (post-REFINE)
| AC Line | Original Issue | Refinement |
|---------|---------------|------------|
| AC-1 | "status or priority select" and "count or chips" — disjunctive wording broader than proof | Replaced with explicit PDS selectors: `p-select[name="priority-filter"]`, badge count, `[data-testid="filter-result-count"]`; mapped to named test group (16 tests) |
| AC-2 | "without shell/status-bar reflow" — no layout-stability test in #1564 spec; filter panel renders inline at KanbanBoard.tsx:306 | Removed reflow claim; AC-2 now scopes to task-card visibility and result-count ratio only; reflow remediation explicitly out of scope |
| AC-3 | Reasonable but needed explicit test group reference | Added test group name "AC-2 | FilterPanel PDS compliance assertions" (8 tests) |
| AC-4 | "grouped, labeled, keyboard-reachable" — no test coverage (h-ac-quality B2 violation); "status/priority controls" — status is read-only text in DetailTab.tsx:163, not a control; "confirm/destructive actions" — ConfirmDialog/TaskActions not tested by #1564 | Removed untestable qualifiers; narrowed to what #1564 tests actually verify: priority, tag display, text fields, save and edit-toggle buttons; mapped to named test group (10 tests) |
| Content Audit Amendment | "screenshot evidence" not pipeline-verifiable; duplicated AC-4 scope | Superseded by refined AC-4; removed |
| Proof bundle | "behavioral" implies failing tests exist; all 34 tests pass | Changed to "existing" with explicit scope |

### Codebase Evidence
- FilterPanel.tsx: p-input-search (L195), p-select with p-select-option (L202-L210), PMultiSelect (L216-L225), p-checkbox (L233), PButton clear (L243) — fully PDS-compliant
- TaskFieldsEditor.tsx: PInputText title/depends_on/parent (L181/L197/L203), p-select with p-select-option priority (L188-L191), p-tag (L193), PTextarea body (L223), PButton save/edit (L248/L239) — PDS-compliant
- KanbanBoard.tsx: PButton filter toggle (L282) — PDS-compliant
- All 34 #1564 E2E tests pass (confirmed by #1564 archival at confidence 0.97)
- TaskFieldsEditor priority select renders one option (current value only, L190-L191) — noted as pre-existing functional limitation, explicitly out of scope for PDS migration

### Dependency Analysis
- #1564 (RED tests): archived/completed — 34 E2E tests in filter-controls-1564.spec.ts
- #1569 (overlays): archived/completed — overlay patterns ready
- #1560 (PDS policy): archived/completed — policy §5 decided
- #1572 depends on #1571 — will unblock after completion
- #1573 (consolidation test) depends on #1571 — will unblock after completion

### Challenge Results
- Challenger: block (0.38)
- Architect response: accepted 5/5 findings; revised AC and proof bundle:
  1. Routing/scope contradiction: ACCEPTED — reclassified as inherited-proof verification task; context updated; proof bundle changed to "existing"
  2. AC-4 overclaims: ACCEPTED — removed "grouped, labeled, keyboard-reachable", "status/", and "confirm/destructive actions"; narrowed to concrete PDS controls verified by #1564 tests
  3. AC-2 reflow claim: ACCEPTED — removed "without shell/status-bar reflow"; reflow remediation explicitly out of scope
  4. Priority select gap: ACCEPTED — documented as pre-existing concern, explicitly out of scope for PDS migration
  5. Proof bundle downgrade: ACCEPTED — fixed AC overclaims first, then changed bundle from "behavioral" to "existing" with scope

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: existing (downgraded — tests already exist and pass from #1564 lifecycle)
- Existing proof scope: `serve/cockpit/web/e2e/filter-controls-1564.spec.ts` (34 tests)
- Test-writer: SKIP

### Non-impl tagging
- Tagged `type:build` — builder processes and verifies; `existing` proof bundle routes test-writer to SKIP

### Consolidation test
- #1573 exists as consolidation-test sibling depending on #1571 — no gap

### Verdict: APPROVE (after REFINE)
### Action Taken: Rewrote all 4 AC lines to match #1564 proof surface (explicit PDS selectors, test group names, test counts). Removed 5 overclaims (reflow, grouped/labeled/keyboard-reachable, status controls, confirm/destructive actions, screenshot evidence). Changed proof bundle from behavioral to existing. Updated context to note inherited-proof verification task. Advanced backlog → todo.
2026-05-15T13:19:01+00:00
## Test-Writer Notes
- Proof bundle: existing — no new test writing required.
- Existing proof scope: `serve/cockpit/web/e2e/filter-controls-1564.spec.ts` (34 tests, all pass per #1564 archival).
- Passing through to builder.
2026-05-15T13:27:10+00:00
## Builder Notes
- Files changed: none (verification-only task under `Proof bundle: existing`).
- Implementation action: no source edits required; existing Cockpit filter/form PDS implementation already satisfies AC-1 through AC-4.
- Required proof executed: `serve/cockpit/web/e2e/filter-controls-1564.spec.ts`.
- Quality-runner results: 34 passed, 0 failed, 0 skipped.
- Lint status: clean (`eslint` violations: none).
- Coverage: not required for `existing` proof bundle; quality-runner reported none.
- Evidence summary: Existing proof bundle satisfied exactly as specified in task body (`Existing proof scope: serve/cockpit/web/e2e/filter-controls-1564.spec.ts (34 tests)`).
- Regression check: working tree shows no changes under `serve/cockpit/web` for this task.
2026-05-15T13:46:46+00:00
## Review Evidence
- Verdict: FAIL
- Routing: FAIL #1571 to todo | AC-1 proof never verifies the required blocked-toggle selector.
- Blocking findings:
| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC-1 | The existing proof never asserts or clicks the required `p-checkbox[name="blocked-filter"]`; it uses the broader `p-switch, p-checkbox` locator, so a switch or renamed checkbox could still pass green while violating the contract. | AC contract: `.owlbear/kanban/tasks/1571-p2-09-green-recompose-cockpit-filters-and-visible-form-controls.md:36`; implementation: `serve/cockpit/web/src/components/FilterPanel.tsx:233-237`; weak proof: `serve/cockpit/web/e2e/filter-controls-1564.spec.ts:228,237,326,391` | todo |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Tighten the blocked-toggle proof to the exact `p-checkbox[name="blocked-filter"]` selector for both presence and interaction paths so the suite fails if the control type or name drifts from AC-1. | `serve/cockpit/web/e2e/filter-controls-1564.spec.ts` | AC-1 at `.owlbear/kanban/tasks/1571-p2-09-green-recompose-cockpit-filters-and-visible-form-controls.md:36`; broad locator at `serve/cockpit/web/e2e/filter-controls-1564.spec.ts:228,237,326,391` |

## Observations
- Current implementation matches the contract for the blocked control and the rest of the scoped PDS controls: `serve/cockpit/web/src/components/FilterPanel.tsx:193-243`, `serve/cockpit/web/src/components/TaskFieldsEditor.tsx:172-248`, and `serve/cockpit/web/src/KanbanBoard.tsx:282-306`.
- AC-3's PMultiSelect exception is adequately documented because the policy allows task-note exceptions (`.owlbear/research/1560-cockpit-design-policy.md:54`) and task 1571 names this one at `.owlbear/kanban/tasks/1571-p2-09-green-recompose-cockpit-filters-and-visible-form-controls.md:40`.
- Builder evidence is otherwise coherent for an `existing` proof bundle: 34 Playwright tests passed and lint was clean, but that packet is insufficient against the AC-1 selector gap.
2026-05-15T13:51:57+00:00
## Test-Writer Notes
- Retry: tightened 4 broad `p-switch, p-checkbox` locators to exact `p-checkbox[name="blocked-filter"]` in `serve/cockpit/web/e2e/filter-controls-1564.spec.ts`.
- Locations changed: lines ~228 (presence+click), ~237 (badge count interaction), ~326 (surviving-set interaction), ~391 (PDS compliance assertion).
- AC coverage: AC-1 blocked-toggle presence and interaction paths now fail if control type drifts to `p-switch` or name attribute changes.
- Proof: 34/34 Playwright tests PASS, lint clean (ESLint exit 0).
- Builder skip: test-only retry — implementation already uses exact `p-checkbox[name="blocked-filter"]` (FilterPanel.tsx:233); no source changes needed.
- Commit: 76c3b1e8
2026-05-15T13:58:43+00:00
## Review Evidence
- Verdict: PASS
- PASS confirmation (one line): PASS #1571 -> docs | AC mapped to code and evidence sufficient.
- Builder/test-writer evidence reviewed first: the `existing` proof packet is coherent after the retry note (`34/34` Playwright tests PASS, ESLint clean). Builder skip is valid because the prior FAIL named only a test-proof gap.

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC-1 | `serve/cockpit/web/src/KanbanBoard.tsx:279-300` renders `p-button[data-testid="filter-toggle"]` and `[data-testid="filter-result-count"]`; `serve/cockpit/web/src/components/FilterPanel.tsx:193-243` renders `p-input-search[name="search-filter"]`, `p-select[name="priority-filter"]` with `p-select-option` children, `PMultiSelect` `name="tags-filter"`, `p-checkbox[name="blocked-filter"]`, and `PButton` clear action. | `serve/cockpit/web/e2e/filter-controls-1564.spec.ts:180-281` covers trigger, search, priority, exact blocked-toggle selector, badge count, result-count display, clear action, and tags host/interaction. | PASS |
| AC-2 | `serve/cockpit/web/src/KanbanBoard.tsx:285-300` computes active-filter badge and exact result-count text; `serve/cockpit/web/src/components/FilterPanel.tsx:233-243` toggles blocked state and clear action. | `serve/cockpit/web/e2e/filter-controls-1564.spec.ts:297-361` proves the surviving sets for search, priority, blocked, and tags filters, proves clear restores hidden cards, and proves the ratio text is exact (`1 / 3 tasks`). | PASS |
| AC-3 | Policy ` .owlbear/research/1560-cockpit-design-policy.md:54,59,63-66` requires PDS-first visible controls, `PButton`, `PInputSearch`, `PCheckbox`/`PSwitch`, `PSelect + PSelectOption`, and `PTag`. `serve/cockpit/web/src/components/FilterPanel.tsx:193-243` and `serve/cockpit/web/src/components/TaskFieldsEditor.tsx:172-248` match those mappings, with the task-documented `PMultiSelect` tags exception implemented at `serve/cockpit/web/src/components/FilterPanel.tsx:215-228`. | `serve/cockpit/web/e2e/filter-controls-1564.spec.ts:375-450` verifies filter-panel PDS host types plus dual-render falsifiability for blocked/native checkbox, priority/native option, and toggle/native button. `serve/cockpit/web/e2e/filter-controls-1564.spec.ts:455-527` verifies the task-editor controls against the same policy surface. | PASS |
| AC-4 | `serve/cockpit/web/src/components/TaskFieldsEditor.tsx:172-248` renders `p-select` with `p-select-option`, `p-tag[data-testid="tag-chip"]`, `p-input-text` title/depends_on/parent fields, `p-textarea[name="body"]`, and `p-button[data-testid="save-button"]` / `p-button[data-testid="body-edit-toggle"]`. | `serve/cockpit/web/e2e/filter-controls-1564.spec.ts:455-527` verifies task-editor priority PDS options, no native option children, `p-tag` with no legacy span chips, the visible text fields, body textarea after Edit, and both action buttons. | PASS |

- Blocking findings: none.

## Observations
- The prior false-green gap is resolved: blocked-toggle proof now uses the exact selector in interaction and compliance assertions at `serve/cockpit/web/e2e/filter-controls-1564.spec.ts:223-237`, `serve/cockpit/web/e2e/filter-controls-1564.spec.ts:321-327`, and `serve/cockpit/web/e2e/filter-controls-1564.spec.ts:388-393`, matching `serve/cockpit/web/src/components/FilterPanel.tsx:233-237`.
- No independent quality-runner rerun was necessary because the retry proof packet is internally consistent for an `existing` bundle and the inspected file state matches the reported surface.
2026-05-15T14:15:03+00:00
## Docs Gate

### Checklist

| Item | Status | Evidence |
|------|--------|----------|
| 1. README Verification | PASS (pre-existing TODO added) | Changed file: `serve/cockpit/web/e2e/filter-controls-1564.spec.ts` (locator tightening only) → maps to `serve/cockpit/README.md`. #1564 section (lines 80–90) accurately describes the filter-controls spec and PDS compliance surface; no update required for #1571's test-implementation-only change. Pre-existing stale entry at line 149: `view.cleanup()` row claims `pruned_lock_paths` and "prunes orphan lock files" — both removed by flock-infrastructure removal (different task). `CleanupResult` in `serve/kanban/src/owlbear_kanban/models.py` confirms actual fields: `released_claim_ids`, `archived_task_ids`, `duplicate_removed_ids`, `skipped_items`. TODO marker added inline. |
| 2. External Attribution | N/A | No external sources used; verification-only task with existing proof bundle. |
| 3. Research Doc | N/A | Task body already references `.owlbear/research/cockpit-visual-audit-consolidated-2026-05-14.md` §§6-8. |
| 4. Deletion Detection | N/A | No source files deleted. |

### Files Updated

- `serve/cockpit/README.md` — inserted `> **TODO:** stale — view.cleanup() row claims pruned_lock_paths...` marker after the stale table row (commit `423803c0`).

### Scratch Cleanup

No `.owlbear/scratch/1571-*` files found — nothing to delete.

### Layer 1 (grep)

- Confirmed `pruned_lock_paths` absent from all `serve/` source files (only README match).
- Confirmed `> **TODO:**` marker present in README at the stale row.
- No symbols from #1571 changes removed from README.

### Layer 2 (editorial)

README #1564 section is coherent and accurate for the delivered PDS compliance surface. The locator tightening (`p-switch, p-checkbox` → `p-checkbox[name="blocked-filter"]`) is an internal test implementation detail with no user-visible behavioral change requiring documentation. The TODO marker is visible and greppable.
2026-05-15T14:30:16+00:00
## Audit

### Regression Detection
- quality-runner mode full: pytest 4562 passed / 226 failed (pre-existing in unrelated modules: test_cockpit_view, test_server, test_engine_accessor_migration, test_ideation_diagram); ruff clean; Playwright filter-controls-1564 34/34 PASS; Vitest 1822 passed / 22 failed (pre-existing, unrelated files)
- Pre-existing evidence: terminal history shows pytest Exit Code: 1 on runs prior to #1571 commits; failing tests are in modules unrelated to cockpit E2E locator changes
- Regression verdict: PASS (no new failures introduced by #1571)

### Intent Verification
- Scope alignment: PASS (changed files: serve/cockpit/web/e2e/filter-controls-1564.spec.ts + serve/cockpit/README.md, both within cockpit frontend domain)
- Purpose match: PASS (PDS control compliance verification; locator tightening matches reviewer FAIL remediation)
- Extraneous scope: none
- Boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 4/5
Initial AC had 5 overclaims (reflow, grouped/labeled/keyboard-reachable, status controls, confirm/destructive actions, screenshot evidence) caught by challenger. After refinement cycle: specific PDS selectors, exact test counts, mapped to named test groups. Final AC is well-targeted and precisely scoped. One challenge cycle needed but outcome is solid.

### Commit Integrity
- Upstream commit presence: PASS (76c3b1e8 test-writer, 423803c0 doc-writer; builder had no source changes for verification-only task)
- Kanban commit packaging: pending (this step)

### Deduction Breakdown
No deductions applied:
- No intent mismatch
- No evidence integrity concerns
- Lint clean
- AC quality 4/5 (above deduction threshold)
- Reviewer evidence section present and detailed (PASS with full AC mapping table)
- No regressions from this task

### Confidence: 1.00
### Action: archive