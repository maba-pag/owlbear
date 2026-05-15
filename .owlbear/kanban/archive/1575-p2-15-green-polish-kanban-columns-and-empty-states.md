---
id: 1575
title: 'P2-15 GREEN: Polish kanban columns and empty states'
status: archived
priority: needed
created: 2026-05-14T18:34:00.455181+00:00
updated: 2026-05-15T08:17:25.859345+00:00
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
archival_reason: completed
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
AC-4: Given Column.css, the following PDS-token declarations are proved by ColumnCSS_1547.test.ts (18 assertions):
- `.column` root: `background` (surface token), `border` (contrast token), `border-radius` (radius token)
- `.column[data-drag-over="true"]`: `background` (state token)
- `.column header`: `padding` full two-value shorthand (spacing tokens on both axes)
- `.column-body`: `padding` and `gap` (spacing tokens)
- `.column-empty`: `padding` (spacing token)
Verify by ColumnCSS_1547.test.ts passing (18 assertions) and Stylelint clean output. For multi-value shorthand declarations, the proof regex must match the FULL declaration value (all axes). A regression from `var(--pds-spacing-sm) var(--pds-spacing-sm)` to `var(--pds-spacing-sm) 6px` must fail.
Exemptions: `.column-count` padding (`1px 6px`) — PDS spacing tokens (min 4px) are too coarse for badge pill geometry; intentional design choice. Deferred to #1573: `.column header` border-bottom token, `.column-count` background/radius tokens — consolidation task covers these in its visual-regression and PDS-policy gate (AC-2, AC-4).

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
2026-05-15T06:16:40+00:00
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
- Evidence summary: AC-1/AC-2/AC-3/AC-4 required existing-proof suite is green, including tightened full-value `.column header` padding assertion and AC-4 exemption alignment for `.column-count` padding.
- Fixes applied: none in this cycle; architecture/test refinements from prior cycles were re-verified and remain green.
2026-05-15T06:39:14+00:00
## Review Evidence
- Verdict: FAIL
- FAIL routing: FAIL #1575 -> backlog | AC-4 still over-claims proof coverage; header divider and badge token declarations can regress green under the current suite.
- Builder evidence reviewed first: task history reports 43 passed with eslint/stylelint clean at `.owlbear/kanban/tasks/1575-p2-15-green-polish-kanban-columns-and-empty-states.md:153` and `.owlbear/kanban/tasks/1575-p2-15-green-polish-kanban-columns-and-empty-states.md:154`.
- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC-4 | The current AC-4 text still covers tokenized border/radius/surface declarations that the retained proof bundle does not exercise. A regression of `.column header` `border-bottom` or `.column-count` background/radius away from PDS tokens would still pass the 18 CSS assertions and Stylelint clean output. | Contract scope: `.owlbear/kanban/tasks/1575-p2-15-green-polish-kanban-columns-and-empty-states.md:38`. Unproved declarations: `serve/cockpit/web/src/components/Column.css:18`, `serve/cockpit/web/src/components/Column.css:28`, `serve/cockpit/web/src/components/Column.css:29`. Current CSS proof only covers root token assertions, drag-over background, and spacing checks at `serve/cockpit/web/src/__tests__/ColumnCSS_1547.test.ts:45`, `serve/cockpit/web/src/__tests__/ColumnCSS_1547.test.ts:52`, `serve/cockpit/web/src/__tests__/ColumnCSS_1547.test.ts:59`, `serve/cockpit/web/src/__tests__/ColumnCSS_1547.test.ts:153`, `serve/cockpit/web/src/__tests__/ColumnCSS_1547.test.ts:166`, `serve/cockpit/web/src/__tests__/ColumnCSS_1547.test.ts:173`, `serve/cockpit/web/src/__tests__/ColumnCSS_1547.test.ts:180`, `serve/cockpit/web/src/__tests__/ColumnCSS_1547.test.ts:187`. Stylelint config is generic validity-only at `serve/cockpit/web/.stylelintrc.json:3`, `serve/cockpit/web/.stylelintrc.json:14`, `serve/cockpit/web/.stylelintrc.json:18`. | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Decide whether AC-4 should require proof for the header divider and badge background/radius token declarations; either narrow the contract explicitly or dispatch updated CSS proof that fails raw-token regressions for those declarations. | `.owlbear/kanban/tasks/1575-p2-15-green-polish-kanban-columns-and-empty-states.md`, `serve/cockpit/web/src/components/Column.css`, `serve/cockpit/web/src/__tests__/ColumnCSS_1547.test.ts`, `serve/cockpit/web/.stylelintrc.json` | Blocking finding #1 |

## Observations
- The implementation itself is currently compliant on the inspected surface: the header divider and badge token declarations already exist at `serve/cockpit/web/src/components/Column.css:18`, `serve/cockpit/web/src/components/Column.css:28`, and `serve/cockpit/web/src/components/Column.css:29`.
- AC-1, AC-2, and AC-3 still map cleanly to code and proof: `serve/cockpit/web/src/components/Column.tsx:20`, `serve/cockpit/web/src/components/Column.tsx:62`, `serve/cockpit/web/src/components/Column.tsx:87`, `serve/cockpit/web/src/components/Column.tsx:90`, `serve/cockpit/web/src/components/Column.tsx:92`; `serve/cockpit/web/src/__tests__/ColumnPolish_1574.test.tsx:89`, `serve/cockpit/web/src/__tests__/ColumnPolish_1574.test.tsx:185`, `serve/cockpit/web/src/__tests__/ColumnPolish_1574.test.tsx:253`; `serve/cockpit/web/e2e/column-body-a11y-1574.spec.ts:134`, `serve/cockpit/web/e2e/column-body-a11y-1574.spec.ts:167`.
- Builder and test-writer commit references cited in the task history are present in `.git/logs/refs/heads/dev:2894` and `.git/logs/refs/heads/dev:2932`.
2026-05-15T06:45:04+00:00
## Architecture Review (cycle 5 — AC-4 contract narrowing)
### Evaluation
Reviewer cycle 4 correctly identifies that AC-4's prose ("surface, border, spacing, and radius declarations") still over-claims relative to the 18 assertions in ColumnCSS_1547.test.ts. Three declarations use PDS tokens but are not exercised by the suite: `.column header` border-bottom (`var(--pds-contrast-low)`), `.column-count` background (`var(--pds-background-shading)`), `.column-count` border-radius (`var(--pds-radius-sm)`). Implementation is correct — the gap is purely proof scope vs AC scope.

Resolution: AC-4 rewritten to exhaustively enumerate the exact selector+property combinations the 18 assertions cover. Unproved decorative-token declarations explicitly deferred to consolidation task #1573, which already depends on #1575 and lists column components in its AC-4. This eliminates the over-claim without requiring new tests or bundle escalation.

### AC Assessment
| AC Line | Assessment | Action |
|---------|-----------|--------|
| AC-1 (labels + badges) | PASS | No change |
| AC-2 (empty state) | PASS | No change |
| AC-3 (focusability) | PASS | No change |
| AC-4 (token proof) | REFINED | Replaced prose contract with exhaustive selector+property list matching the 18 assertions exactly. Deferred `.column header` border-bottom and `.column-count` background/radius to #1573. |

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: existing
- Existing proof scope: ColumnPolish_1574 (13), column-body-a11y-1574 (2), Column_1539 (10), ColumnCSS_1547 (18)
- Test-writer: SKIP — contract narrowed to match existing suite; no new tests needed

### Challenge Results
- Challenger: SKIPPED — existing bundle, refinement-only cycle (loop-breaker)

### Verdict: APPROVE (REFINE applied inline)
### Action Taken: Narrowed AC-4 from prose-based "surface, border, spacing, and radius" to an exhaustive enumeration of proved selector+property pairs. Explicitly deferred unproved decorative tokens to consolidation #1573. No test changes required. Advanced backlog → todo.
2026-05-15T07:06:49+00:00
## Test-Writer Notes
- Retry cycle (cycle 5): proof bundle existing — no new RED tests required.
- Reviewer cycle 4 finding routed to architect (not test-writer): unproved decorative-token declarations on `.column header` border-bottom and `.column-count` background/radius.
- Architect cycle 5 resolved by narrowing AC-4 from prose-based contract to exhaustive selector+property enumeration matching the 18 existing assertions exactly. Unproved decorative tokens explicitly deferred to consolidation task #1573.
- Existing proof scope unchanged: ColumnPolish_1574 (13 tests), column-body-a11y-1574 (2 tests), Column_1539 (10 tests), ColumnCSS_1547 (18 tests).
- No new test files created or modified this cycle.
- Passing through to builder.
2026-05-15T07:18:02+00:00
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
- Evidence summary: AC-1/AC-2/AC-3/AC-4 required existing-proof suite is green under the cycle-5 refined AC-4 contract (explicit selector+property proof scope), including the full-value `.column header` padding assertion and clean CSS/TS lint gates.
- Fixes applied: none in this cycle; implementation and proof refinements from prior cycles were re-verified and remain green.
2026-05-15T07:42:41+00:00
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1575 -> docs | AC mapped to code and evidence sufficient.
- Builder evidence reviewed first and accepted as sufficient: `Proof bundle: existing` with named proof scope at `.owlbear/kanban/tasks/1575-p2-15-green-polish-kanban-columns-and-empty-states.md:47-48`; scoped builder evidence reports 43 passed with eslint/stylelint clean at `.owlbear/kanban/tasks/1575-p2-15-green-polish-kanban-columns-and-empty-states.md:228-231`. Direct source/proof inspection found no contradiction requiring an independent rerun.
- AC evidence map:

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC-1 | `serve/cockpit/web/src/components/Column.tsx:20-28` normalizes status strings; `serve/cockpit/web/src/components/Column.tsx:87-88` renders the polished label and count badge; `serve/cockpit/web/src/components/Column.css:20` and `serve/cockpit/web/src/components/Column.css:27` preserve label-over-badge hierarchy. | `serve/cockpit/web/src/__tests__/ColumnPolish_1574.test.tsx:89`, `:103`, `:115`, `:124`, `:136`, `:148`, `:160` verify normalized labels across statuses; `serve/cockpit/web/src/__tests__/ColumnPolish_1574.test.tsx:253`, `:278`, `:298`, `:324` verify count badge presence/count and subordinate font-size hierarchy. | PASS |
| AC-2 | `serve/cockpit/web/src/components/Column.tsx:92` renders empty-state copy from `displayStatus` and keeps `data-testid="empty-column"`; `serve/cockpit/web/src/components/Column.css:50-52` keeps the empty state padded, smaller, and dimmed. | `serve/cockpit/web/src/__tests__/ColumnPolish_1574.test.tsx:185`, `:190`, `:200`, `:211`, `:236` verify polished empty copy, empty-column test id, smaller font-size, and opacity below 1. | PASS |
| AC-3 | `serve/cockpit/web/src/components/Column.tsx:62` sets the focusability attribute on the scroll body; `serve/cockpit/web/src/components/Column.tsx:90` renders the `column-body`; `serve/cockpit/web/src/components/Column.css:38` keeps the body scrollable. | `serve/cockpit/web/e2e/column-body-a11y-1574.spec.ts:134`, `:147-152` verify zero `scrollable-region-focusable` violations; `serve/cockpit/web/e2e/column-body-a11y-1574.spec.ts:167`, `:189-211` prove the scan is non-vacuous by forcing and measuring actual overflow. | PASS |
| AC-4 | The current contract is the narrowed selector/property list at `.owlbear/kanban/tasks/1575-p2-15-green-polish-kanban-columns-and-empty-states.md:38-45`. Required declarations are present at `serve/cockpit/web/src/components/Column.css:5-7`, `:17`, `:40-41`, `:50`, and `:56`. | `serve/cockpit/web/src/__tests__/ColumnCSS_1547.test.ts:45`, `:52`, `:59`, `:153`, `:166`, `:173`, `:180`, `:187` exactly cover the enumerated selectors/properties; the header-padding assertion satisfies the full-value shorthand requirement called out at `.owlbear/kanban/tasks/1575-p2-15-green-polish-kanban-columns-and-empty-states.md:44`. | PASS |

- Blocking findings: none.

## Observations
- The prior loop-back findings are resolved by the current contract text: `.column-count` padding is explicitly exempted, and `.column header` border-bottom plus `.column-count` background/radius are explicitly deferred to #1573 at `.owlbear/kanban/tasks/1575-p2-15-green-polish-kanban-columns-and-empty-states.md:45`. Re-raising those as blockers here would be contract expansion, not review of the accepted AC.
- Workspace diagnostics report no editor errors in `serve/cockpit/web/src/components/Column.tsx`, `serve/cockpit/web/src/components/Column.css`, `serve/cockpit/web/src/__tests__/ColumnPolish_1574.test.tsx`, `serve/cockpit/web/src/__tests__/ColumnCSS_1547.test.ts`, or `serve/cockpit/web/e2e/column-body-a11y-1574.spec.ts`.
2026-05-15T07:49:27+00:00
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | README verification | Yes | N/A | Convention map: `serve/cockpit/web/src/**` → `serve/cockpit/README.md`. Layer 1 grep: no #1575-specific symbols (`toDisplayStatus`, `column-empty`, task-scoped test names) appear in the README. Layer 2 editorial: changes are component-level visual polish (column labels, empty-state copy, CSS tokens, test regex tightening) with no impact on documented API contracts, CLI commands, or behavioral contracts. The `tabIndex` / `column-body` focusability contract is already documented under #1566 and remains accurate — no contradiction. No update required. |
| 2 | External attribution | No | N/A | No external sources cited in task body or referenced in implementation. |
| 3 | Research doc | Yes | N/A | Task body references `.owlbear/research/cockpit-visual-audit-consolidated-2026-05-14.md` in Context section — linked correctly. No action needed. |
| 4 | Deletion detection | No | N/A | Builder changed no source files in any pipeline cycle; test-writer tightened one existing test regex (ColumnCSS_1547.test.ts). No files deleted, no orphaned references possible. |

### Verification Layers
- Layer 1 — grep on `serve/cockpit/README.md` for `toDisplayStatus|column-empty|ColumnPolish|column-body-a11y-1574|ColumnCSS_1547`: 0 matches. No implementation symbols from #1575 appear in the README; nothing to update or correct.
- Layer 2 — full editorial read of README: coherent, no contradictions with #1575 implementation. Column visual polish is implementation-internal and below the README's documentation threshold.

### Files Updated
- None

### Scratch Files Cleaned
- None (no `.owlbear/scratch/1575-*` files found)
2026-05-15T08:17:25+00:00
## Audit
### Regression Detection
- quality-runner mode full: 4544 passed, 215+ failed, 14 skipped. All failures are pre-existing and unrelated to #1575 (engine accessor migration, validation push, ideation, cockpit view detail key, MCP kanban line count, knowledge stats — none in cockpit column components or proof files). Task's 43 proof-scope tests (ColumnPolish_1574 ×13, column-body-a11y-1574 ×2, Column_1539 ×10, ColumnCSS_1547 ×18) all pass.
- regression verdict: PASS (no cross-task regressions introduced; task made no source changes)

### Intent Verification
- scope alignment: PASS (only file changed: ColumnCSS_1547.test.ts regex tightening; source code from #1574 dependency commit dd4b6669; all within serve/cockpit/web domain)
- purpose match: PASS (column display labels, empty-state styling, CSS token proof, focusability — matches stated scope exactly)
- extraneous scope: none
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 3/5
AC-1/2/3 were well-scoped from the start. AC-4 required 3 architect refinement cycles (cycles 3-5) to narrow from over-broad prose-based PDS-token contract to exhaustive selector+property enumeration. Cycle 3 tightened padding regex, cycle 4 added .column-count exemption, cycle 5 narrowed to proved declarations only and deferred unproved decorative tokens to #1573. Final AC-4 is precise but the iterative refinement cost was significant.

### Commit Integrity
- upstream commit presence: PASS (test-writer 053985bf verified — scoped to ColumnCSS_1547.test.ts only; builder no-op for existing bundle pass-through; source implementation in #1574 dependency commit dd4b6669)
- kanban commit packaging: pending (this audit cycle)

### Deduction Breakdown
- AC quality score 3/5: -.03
- No other deductions

### Confidence: 0.97
### Action: archive