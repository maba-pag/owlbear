---
id: 1547
title: 'P3-04: impl — column component CSS: fixed header, scroll body, empty text
  fallback'
status: archived
priority: important
created: 2026-05-13T18:43:23.829051+00:00
updated: 2026-05-14T03:36:41.300798+00:00
tags:
  - phase-3
  - scope:cockpit
  - css
  - frontend
parent: 1534
depends_on:
  - 1539
  - 1543
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
Brief: see parent #1534 (`.owlbear/briefs/draft-board-visual-design/brief.md`)

## Scope
- **In:** Column CSS: PDS surface background, border-radius, fixed header with name + count badge, scrollable body, empty state text fallback, minimum width 200px
- **Out:** Empty state illustrations (user-supplied), card CSS, DnD column highlighting beyond minimal `[data-drag-over]` rule

## Acceptance Criteria

- AC-1: `.column` selector has `background: var(--pds-background-surface)`, `border-radius: var(--pds-radius-md)`, `border: 1px solid var(--pds-contrast-low)`, and `min-width: 200px`
- AC-2: `.column` is `display: flex; flex-direction: column`; `header` has `flex-shrink: 0`; `.column-body` has `flex: 1; min-height: 0; overflow-y: auto` (scroll activates when board layout constrains column height — integration verified by #1554)
- AC-3: Empty columns display "No {status} tasks" text in `.column-empty` (centering already implemented by #1539; verified as preserved)
- AC-4: `.column[data-drag-over="true"]` has `background: var(--pds-state-hover)` for drop-target highlight

Proof bundle: behavioral

## Research
- Research doc: .owlbear/research/1547-column-css-impl.md
- Sources: 8 studied, 6 high-relevance
- Recommendation: CSS-only Column.css expansion using agnostic PDS tokens (confidence: 0.75)
- Challenge: reconsider (0.67) — accepted as advisory: layout coupling with #1550, proof gaps for AC-1/AC-4, AC ambiguity. None block the CSS approach.
- Key findings: (1) Fixed-header scroll pattern requires flex-direction:column + min-height:0 on body (SO #21515042). (2) All needed tokens exist in tokens.css from #1543. (3) No JSX changes needed — HTML structure complete from #1539. (4) Cross-task dependency on #1550 for board-level height constraints that activate column body scroll.
- Follow-up tasks: none needed (task correctly scoped)
- Commit: f7febab2
2026-05-14T02:42:01+00:00
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | CSS-only changes to Column.css; no JSX modifications |
| Interface clarity | PASS | All 4 AC lines name exact selectors, properties, and token values |
| Dependency correctness | PASS | #1539 (test) and #1543 (tokens) both archived; #1550 is cross-task coupling for scroll activation, documented in AC-2 parenthetical |
| Module layering | PASS | CSS file only; no import concerns |
| TDD compliance | PASS | Test task #1539 archived; CSS token assertion pattern exists in Card.css.test.ts |
| KISS/YAGNI | PASS | Minimal CSS additions using existing tokens and HTML structure |
| Premise challenge | PASS | Column needs visual treatment; HTML structure ready from #1539, tokens ready from #1543 |
| Pattern consistency | PASS | Follows Card.css peer pattern; uses established PDS token convention |
| Security surface | N/A | CSS only, no system boundaries |
| Single domain | PASS | Frontend/cockpit CSS domain only |

### AC Refinements Applied
| AC | Original issue | Refined to |
|----|---------------|------------|
| AC-1 | "subtle border" was vague | Specified `1px solid var(--pds-contrast-low)` |
| AC-2 | Omitted parent selector and flex details | Named `.column` as flex parent, specified `flex-shrink: 0` on header, `flex: 1; min-height: 0` on body |
| AC-3 | "image placeholder infrastructure ready" was unverifiable | Simplified to contract verification of existing centering from #1539 |
| AC-4 | "border color or background shift" was subjective | Specified `background: var(--pds-state-hover)` |
| Scope-Out | "DnD column highlighting (minimal)" contradicted AC-4 | Clarified: "beyond minimal `[data-drag-over]` rule" |

### Challenge Results
- Challenger: reconsider (0.62)
- Architect response: accepted as advisory, rebutted as non-blocking
  - Evidence drift: resolved by writing refined AC to task body
  - Proof gap: `behavioral` bundle routes test-writer to write CSS assertions following Card.css.test.ts pattern
  - Cross-task coupling: AC-2 parenthetical documents #1550 dependency; CSS properties are testable in isolation; integration verification belongs to #1554
  - AC quality: addressed via refinements above
  - #1539 overlap: #1539 built skeleton (structure + centering); this task adds visual treatment (tokens, border, radius, flex layout)

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED (CSS token assertions following Card.css.test.ts pattern)

### Verdict: APPROVE
### Action Taken: Refined all 4 AC lines for selector-level specificity and token precision, clarified scope-out wording, advanced backlog → todo
2026-05-14T02:49:58+00:00
## Test-Writer Notes
- Test file: serve/cockpit/web/src/__tests__/ColumnCSS_1547.test.ts
- Classes: TestFromAC_ColumnBaseStyling, TestFromAC_ColumnFlexLayout, TestFromAC_ColumnEmptyState, TestFromAC_ColumnDragOver
- Tests per category: happy 11 (property-present assertions), regression-guard 3 (AC-3 centering preserved from #1539)
- Total: 14 tests; 11 FAIL (AC-1 × 4, AC-2 × 6, AC-4 × 1) — all new-behavior tests fail RED ✓
- AC-3 exception: 3 regression guards PASS — centering pre-exists from #1539; guards against builder removal during Column.css expansion (expected per w-tdd-red regression-guard rule)
- ruff: N/A (TypeScript); eslint: clean
- Commit: fbdac935

### AC Coverage
| AC | Tests | Status |
|----|-------|--------|
| AC-1: .column base styling (background, border-radius, border, min-width 200px) | 4 | FAIL ✓ |
| AC-2: flex layout (.column display/flex-dir, header flex-shrink, .column-body flex/min-height/overflow) | 6 | FAIL ✓ |
| AC-3: .column-empty centering preserved | 3 | PASS (regression guard, pre-existing from #1539) |
| AC-4: .column[data-drag-over="true"] background: var(--pds-state-hover) | 1 | FAIL ✓ |

### Pattern
File-based CSS parsing following Card.css.test.ts — readFileSync + getCSSBlock helper + regex assertions against PDS token values.
2026-05-14T02:59:10+00:00
## Builder Notes
- Implementation: updated serve/cockpit/web/src/components/Column.css
- AC mapping:
  - AC-1: `.column` now includes `background: var(--pds-background-surface)`, `border-radius: var(--pds-radius-md)`, `border: 1px solid var(--pds-contrast-low)`, `min-width: 200px`
  - AC-2: `.column` now uses `display: flex; flex-direction: column`; `.column header` has `flex-shrink: 0`; `.column-body` has `flex: 1; min-height: 0; overflow-y: auto`
  - AC-3: `.column-empty` centering declarations preserved unchanged
  - AC-4: added `.column[data-drag-over="true"] { background: var(--pds-state-hover); }`
- Tests (quality-runner):
  - RED verification pre-implementation: `serve/cockpit/web/src/__tests__/ColumnCSS_1547.test.ts` -> 3 passed, 11 failed (expected)
  - GREEN verification post-implementation: `serve/cockpit/web/src/__tests__/ColumnCSS_1547.test.ts` -> 14 passed, 0 failed
  - Durable module baseline: `serve/cockpit/web/src/__tests__/Column_1539.test.tsx` -> 10 passed, 0 failed (pre and post)
- Coverage: N/A for CSS file (quality-runner reports no module coverage for this run)
- Lint: clean (eslint/stylelint clean in scoped run)
- Evidence summary: all task AC assertions now passing in TestFromAC classes with no test changes.
- Commit: 7ae33a07
2026-05-14T03:10:32+00:00
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1547 -> docs | AC mapped to code and evidence sufficient.
- Builder evidence reviewed first: scoped task test `serve/cockpit/web/src/__tests__/ColumnCSS_1547.test.ts` GREEN 14/14, durable baseline `serve/cockpit/web/src/__tests__/Column_1539.test.tsx` GREEN 10/10, scoped lint clean; independent rerun not required because the evidence packet was internally consistent.
- Challenger cross-check: `reconsider` on AC-2 wording / split-proof presentation; reconciled against the existing Architecture Review note that integration verification belongs to #1554, so no blocking finding remained.

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC-1 | `serve/cockpit/web/src/components/Column.css:1` `.column` block includes `background`, `border-radius`, `border`, `min-width`; `serve/cockpit/web/src/components/Column.tsx:41` wires the `.column` root | `serve/cockpit/web/src/__tests__/ColumnCSS_1547.test.ts:44` exact `.column` block assertions | PASS |
| AC-2 | `serve/cockpit/web/src/components/Column.css:1` `.column` sets `display:flex` / `flex-direction:column`; `serve/cockpit/web/src/components/Column.css:10` sets `.column header { flex-shrink: 0; }`; `serve/cockpit/web/src/components/Column.css:14` sets `.column-body { flex: 1; min-height: 0; overflow-y: auto; }`; `serve/cockpit/web/src/components/Column.tsx:64` wires `.column-body` | `serve/cockpit/web/src/__tests__/ColumnCSS_1547.test.ts:76` proves `.column` / `.column-body` declarations; `serve/cockpit/web/src/__tests__/Column_1539.test.tsx:63` keeps header and body structurally separated | PASS |
| AC-3 | `serve/cockpit/web/src/components/Column.tsx:66` renders `No ${status} tasks` in `.column-empty`; `serve/cockpit/web/src/components/Column.css:21` preserves `.column-empty` centering | `serve/cockpit/web/src/__tests__/Column_1539.test.tsx:169` / `:181` / `:190` prove parameterized empty text; `serve/cockpit/web/src/__tests__/Column_1539.test.tsx:200` and `serve/cockpit/web/src/__tests__/ColumnCSS_1547.test.ts:124` prove centering is present and preserved | PASS |
| AC-4 | `serve/cockpit/web/src/components/Column.css:28` adds `.column[data-drag-over="true"] { background: var(--pds-state-hover); }`; `serve/cockpit/web/src/components/Column.tsx:42` wires `data-drag-over` state | `serve/cockpit/web/src/__tests__/ColumnCSS_1547.test.ts:152` exact selector assertion | PASS |
- Safety/security: N/A for this CSS-only change; no input handling, auth, storage, or dependency surface changed.
- Blocking findings: none.

## Observations
- AC-2's parenthetical (`integration verified by #1554`) is better understood as downstream consolidation scope than as a gate for this CSS-only task; the task record already documents that interpretation in Architecture Review.
- AC-3 proof is intentionally split: task-local tests guard CSS expansion regressions, while the durable component suite still carries the empty-text fallback proof. That split is acceptable here, but it should stay explicit in later audits.
- The task-local header assertion in `serve/cockpit/web/src/__tests__/ColumnCSS_1547.test.ts:91` is broader than the implementation selector at `serve/cockpit/web/src/components/Column.css:10`. Current source satisfies the AC, so this is non-blocking, but tightening the assertion later would reduce false-green risk.
2026-05-14T03:19:24+00:00
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | README verification | No | N/A | `serve/cockpit/README.md` documents backend API routes, launch commands, and frontend stack metadata only — no column CSS selectors, PDS token values, or component-level details are documented; CSS-only internal change has no README impact |
| 2 | External attribution | Yes | N/A (pre-updated) | `sources/overview.md` line 4653: "Column CSS Implementation Research (Task #1547)" section already present with 6 high-relevance sources including SO #21515042 and PDS v4 SCSS Introduction; researcher committed this in f7febab2 |
| 3 | Research doc | Yes | N/A (pre-linked) | `.owlbear/research/1547-column-css-impl.md` exists; task body references it explicitly under "Research" section |
| 4 | Deletion detection | No | N/A | No files deleted; only `serve/cockpit/web/src/components/Column.css` modified |

### Verification Layers
- Layer 1 — grep: no references to `Column.css`, `.column` selectors, `pds-background-surface`, or `column-body` in `serve/cockpit/README.md`; sources/overview.md contains Task #1547 section confirmed at line 4653; research file confirmed present via `file_search`
- Layer 2 — editorial: README covers backend Python API and frontend stack versions only; zero overlap with CSS token or selector-level implementation; no contradictions or stale claims introduced by this task

### Scratch Cleanup
No `.owlbear/scratch/1547-*` files found.
2026-05-14T03:36:41+00:00
## Audit\n### Regression Detection\n- quality-runner mode full: 6287 passed (4599 Python + 1688 Frontend), vitest exit 0, pytest exit 1 (pre-existing failures unrelated to CSS task). ESLint clean, Stylelint clean, Ruff clean. HTMLHint false positives on .tsx files (not applicable).\n- regression verdict: PASS\n\n### Intent Verification\n- scope alignment: PASS (builder commit 7ae33a07 touched only serve/cockpit/web/src/components/Column.css +16 lines; test-writer commit fbdac935 created ColumnCSS_1547.test.ts +159 lines; both within cockpit frontend CSS domain)\n- purpose match: PASS (CSS properties match AC: PDS surface background, border-radius, flex layout with fixed header + scroll body, empty state centering preserved, drag-over highlight)\n- extraneous scope: none\n- boundary check: function-level behavior verification deferred to reviewer\n\n### Architect Quality: 5/5\nAC lines refined from vague descriptions to exact selectors, properties, and PDS token values. All 4 AC lines are directly verifiable. Scope-out clarified. Challenge results addressed with rebuttals.\n\n### Commit Integrity\n- upstream commit presence: PASS (researcher f7febab2, test-writer fbdac935, builder 7ae33a07; all properly formatted)\n- kanban commit packaging: pending (will commit after end_work)\n\n### Deduction Breakdown\nNo deductions applied.\n\n### Confidence: 1.00\n### Action: archive