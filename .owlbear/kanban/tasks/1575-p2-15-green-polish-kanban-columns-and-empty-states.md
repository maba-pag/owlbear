---
id: 1575
title: 'P2-15 GREEN: Polish kanban columns and empty states'
status: in-progress
priority: needed
created: 2026-05-14T18:34:00.455181+00:00
updated: 2026-05-15T05:56:53.908906+00:00
tags:
  - phase-2
  - scope:cockpit
  - frontend
  - type:build
  - columns
  - empty-states
  - visual-remediation
parent: 1559
depends_on:
  - 1574
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Context
Implements the failing proof from #1574. Source audit: `.owlbear/research/cockpit-visual-audit-consolidated-2026-05-14.md` sections 6 and 8.

**Implementation status:** All code changes were already committed during #1574's pipeline cycle (builder commit `dd4b6669`). The `toDisplayStatus()` function in Column.tsx, polished empty-state text, `tabIndex` attribute on `.column-body`, and `.column-empty` font-size fix in Column.css are already in place and verified by #1574's test suite.

## Scope
In scope: column display labels, empty-state styling/copy, column-body focusability, count badge polish, and spacing consistency between columns and cards.
Out of scope: card metadata, filter controls, sidecar layout, and broad responsive shell changes.

## Acceptance Criteria
AC-1: Given the board renders all statuses, column headers use intentional display labels and count badges with consistent hierarchy; verify with the named tests from #1574.
AC-2: Given a column has no tasks, it shows a quiet, designed empty state that does not dominate the board and does not leak raw internal status strings; verify with the visual/DOM tests from #1574.
AC-3: Given a column body is scrollable, keyboard and axe checks pass for scrollable-region focusability; verify with the accessibility proof from #1574.
AC-4: Given Column.css, the column surface, border, spacing, and radius declarations reference PDS design tokens; verify by ColumnCSS_1547.test.ts passing (18 assertions) and Stylelint clean output. For multi-value shorthand declarations (e.g. `.column header` padding), the proof regex must match the FULL declaration value (all axes), not just the first token. A regression from `var(--pds-spacing-sm) var(--pds-spacing-sm)` to `var(--pds-spacing-sm) 6px` must fail. Exception: `.column-count` padding (`1px 6px`) is exempt from tokenization — PDS spacing tokens (min 4px) are too coarse for badge pill geometry; this is an intentional design choice, not proof debt. Cross-viewport/cross-theme visual coherence deferred to consolidation task #1573.

Proof bundle: existing
Existing proof scope: `serve/cockpit/web/src/__tests__/ColumnPolish_1574.test.tsx` (13 tests: AC-1 ×7, AC-2 ×3, AC-4 ×3), `serve/cockpit/web/e2e/column-body-a11y-1574.spec.ts` (2 tests: AC-3), `serve/cockpit/web/src/__tests__/Column_1539.test.tsx` (10 tests: durable regression), `serve/cockpit/web/src/__tests__/ColumnCSS_1547.test.ts` (18 tests: CSS structural + spacing tokens, AC-4)

## Evidence Expectations
Passing #1574 tests (ColumnPolish_1574 ×13, column-body-a11y-1574 ×2, Column_1539 ×10, ColumnCSS_1547 ×18), axe/focusability evidence, and Stylelint clean output.

## Proof Refinement Note (cycle 3)
Reviewer finding: `.column header` padding is a two-value shorthand (`var(--pds-spacing-sm) var(--pds-spacing-sm)`). The test regex `/padding\s*:\s*var\(--pds-spacing-sm\)/` is prefix-only — it matches even if the second axis regresses to a raw value. Fix: change the regex to match the full declaration, e.g. `/padding\s*:\s*var\(--pds-spacing-sm\)\s+var\(--pds-spacing-sm\)/` or equivalent full-value assertion. Only the `.column header` padding test at `ColumnCSS_1547.test.ts` line ~170 needs updating; the other three spacing assertions are single-value and already sufficient.
2026-05-15T04:46:11+00:00
## Architecture Review (cycle 3 — refinement pass)
### Evaluation
Criteria unchanged from initial review — all PASS. This cycle addresses only the AC-4 proof precision finding from reviewer cycle 2.

### AC Assessment (post-refinement)
| AC Line | Assessment | Action |
|---------|-----------|--------|
| AC-1 (labels + badges) | PASS | No change |
| AC-2 (empty state) | PASS | No change |
| AC-3 (focusability) | PASS | No change |
| AC-4 (spacing tokens) | REFINED | Added explicit full-declaration-match requirement for multi-value shorthand padding. AC now names the exact regression vector (`var(--pds-spacing-sm) 6px`) that must fail. Updated test count 14→18. |

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: existing
- Existing proof scope: ColumnPolish_1574 (13), column-body-a11y-1574 (2), Column_1539 (10), ColumnCSS_1547 (18)
- Test-writer: SKIP for new RED tests; one existing test regex fix needed per Proof Refinement Note

### Challenge Results
- Challenger: SKIPPED — existing bundle, refinement-only cycle

### Verdict: APPROVE (REFINE applied inline)
### Action Taken: Tightened AC-4 proof contract to require full-value regex match on multi-value padding shorthand. Added Proof Refinement Note with exact fix location (ColumnCSS_1547.test.ts line ~170) and example regex. Advanced to todo.
2026-05-15T04:59:22+00:00
## Test-Writer Notes
- Proof bundle: existing — no new RED tests required.
- Existing proof scope: ColumnPolish_1574 (13 tests), column-body-a11y-1574 (2 tests), Column_1539 (10 tests), ColumnCSS_1547 (18 tests).
- Regex fix applied per Proof Refinement Note (cycle 3): `.column header` padding assertion in `ColumnCSS_1547.test.ts` tightened from prefix-only `/padding\s*:\s*var\(--pds-spacing-sm\)/` to full two-value match `/padding\s*:\s*var\(--pds-spacing-sm\)\s+var\(--pds-spacing-sm\)/`. A regression from `var(--pds-spacing-sm) var(--pds-spacing-sm)` to `var(--pds-spacing-sm) 6px` will now fail.
- All 18 ColumnCSS_1547 tests pass with tightened regex (CSS implementation already compliant).
- Commit: 053985bf
- ruff: n/a (TypeScript); eslint: clean
2026-05-15T05:23:09+00:00
## Builder Notes
- Change type: proof-bundle existing pass-through (no source edits required in this cycle).
- Files changed by builder: none.
- Verified required existing proof via quality-runner (scoped):
  - `serve/cockpit/web/src/__tests__/ColumnPolish_1574.test.tsx` (13)
  - `serve/cockpit/web/e2e/column-body-a11y-1574.spec.ts` (2)
  - `serve/cockpit/web/src/__tests__/Column_1539.test.tsx` (10)
  - `serve/cockpit/web/src/__tests__/ColumnCSS_1547.test.ts` (18)
- Test results: 43 passed, 0 failed, 0 skipped.
- Lint status: clean (eslint exit 0, stylelint exit 0).
- Coverage: not required for this `Proof bundle: existing` route; no new implementation introduced.
- Evidence summary: AC-1/AC-2/AC-3/AC-4 proof suite is green, including tightened full-value `.column header` padding assertion in `ColumnCSS_1547.test.ts` and stylelint-clean tokenized CSS contract checks.
2026-05-15T05:38:45+00:00
## Review Evidence
- Verdict: FAIL
- Route: backlog (repeated review cycle loop-breaker; task body already records cycle 3 refinement context)
- AC-1 to AC-3: code and cited proof remain sufficient.
- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC-4 | `Column.css` still contains a raw spacing declaration on the count badge (`.column-count { padding: 1px 6px; }`), so the stylesheet does not fully satisfy the task's PDS-token spacing contract. The existing proof bundle false-greens because it only asserts tokenized spacing for `.column header`, `.column-body`, and `.column-empty`, while the badge proof checks only count content and font-size hierarchy. | `serve/cockpit/web/src/components/Column.css:25-30`; `serve/cockpit/web/src/__tests__/ColumnCSS_1547.test.ts:163-191`; `serve/cockpit/web/src/__tests__/ColumnPolish_1574.test.tsx:241-324` | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Re-scope the remaining AC-4 count-badge spacing contract and dispatch follow-on work so `.column-count` padding is either explicitly exempted from tokenization or converted to PDS spacing tokens with proof that fails raw pixel regressions. | serve/cockpit/web/src/components/Column.css; serve/cockpit/web/src/__tests__/ColumnCSS_1547.test.ts; serve/cockpit/web/src/__tests__/ColumnPolish_1574.test.tsx | Blocking finding #1 |

## Observations
- Builder evidence was internally consistent for the cited proof surface: the task body reports the four scoped suites green (43 passed) with eslint/stylelint clean, and workspace diagnostics show no editor errors in the cited files.
- The blocker is proof completeness against the refined AC, not a contradiction inside the builder packet.
2026-05-15T05:55:16+00:00
## Architecture Review (cycle 4 — AC-4 exemption scoping)
### Evaluation
Reviewer cycle 3 identified `.column-count { padding: 1px 6px; }` as raw-pixel spacing violating AC-4's blanket PDS-token contract. Codebase check confirms PDS spacing tokens (`tokens.css`) start at `--pds-spacing-xs: 4px` — no token maps to 1px or 6px. Forcing tokenization would produce a visually oversized badge pill (minimum 4px×4px vs intentional 1px×6px). This is an intentional design choice for micro-UI geometry, not proof debt.

### AC Assessment
| AC Line | Assessment | Action |
|---------|-----------|--------|
| AC-1 (labels + badges) | PASS | No change |
| AC-2 (empty state) | PASS | No change |
| AC-3 (focusability) | PASS | No change |
| AC-4 (spacing tokens) | REFINED | Added explicit exemption clause: `.column-count` padding (`1px 6px`) is exempt from tokenization — PDS tokens (min 4px) are too coarse for badge pill geometry. Existing proof scope now fully covers the scoped contract. |

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: existing
- Existing proof scope: ColumnPolish_1574 (13), column-body-a11y-1574 (2), Column_1539 (10), ColumnCSS_1547 (18)
- Test-writer: SKIP — no new tests needed; exemption narrows AC-4 scope to match what existing suite already covers

### Challenge Results
- Challenger: SKIPPED — existing bundle, refinement-only cycle addressing reviewer loop-breaker

### Verdict: APPROVE (REFINE applied inline)
### Action Taken: Refined AC-4 to add explicit `.column-count` padding exemption with design rationale. No new proof needed — exemption aligns AC scope with existing test coverage. Advanced backlog → todo.
2026-05-15T05:56:53+00:00
## Test-Writer Notes
- Retry cycle (cycle 4): proof bundle existing — no new RED tests required.
- Reviewer finding (cycle 3) was routed to architect, not test-writer. Architect cycle 4 refined AC-4 to add explicit `.column-count` padding exemption (1px 6px is intentionally below PDS token granularity). Existing proof scope already covers the narrowed AC contract.
- Existing proof scope unchanged: ColumnPolish_1574 (13 tests), column-body-a11y-1574 (2 tests), Column_1539 (10 tests), ColumnCSS_1547 (18 tests).
- Regex fix from cycle 3 (commit 053985bf) retained — full two-value `.column header` padding assertion still in place.
- No new test files created or modified this cycle.
- Passing through to builder.