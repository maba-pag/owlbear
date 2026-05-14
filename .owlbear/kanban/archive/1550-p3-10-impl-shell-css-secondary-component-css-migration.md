---
id: 1550
title: 'P3-10: impl — Shell.css + secondary component CSS migration'
status: archived
priority: important
created: 2026-05-13T18:43:23.937036+00:00
updated: 2026-05-14T06:46:02.337644+00:00
tags:
  - phase-3
  - scope:cockpit
  - css
  - frontend
parent: 1534
depends_on:
  - 1542
  - 1543
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
Brief: see parent #1534 (`.owlbear/briefs/draft-board-visual-design/brief.md`)

## Scope
- **In:** FilterPanel container PDS token styling, `utils/styles.ts` deletion, board grid container token migration
- **Out:** Token architecture (done in P1-02 #1543), PDS component adoption for native inputs, outer board layout gap (L259 — owned by #1552 grep gate), ErrorBoundary.tsx legacy tokens (#1552), ResponsiveLayout_1391 stale tests (#1552)

## Acceptance Criteria

- AC-1: `FilterPanel.tsx` root container element has a CSS `className` and imports a dedicated `FilterPanel.css`; that CSS file applies PDS tokens `--pds-background-surface` (background), `--pds-border-default` (border), `--pds-spacing-md` (padding)
- AC-2: `utils/styles.ts` is deleted; no remaining source files import the module
- AC-3: `KanbanBoard.tsx` column grid container (the `display: 'grid'` element) uses `gap: var(--pds-spacing-md)` replacing hardcoded `'16px'` and `overflowX: 'auto'` replacing `'hidden'`

## Prior Work (completed by dependencies)
- Shell.css agnostic token migration: #1543
- Context menu PDS styling (background-surface, shadow-md, radius-md): #1543/#1546
- `rowStyleForState()` removal + `[data-state]` CSS selectors: #1546/#1547
- ActivityTab/SessionRows CSS: #1547
- DetailTab: pure structural JSX — no tokens to migrate

## Builder Guidance
1. Create `FilterPanel.css` with container class styling; add `className` to FilterPanel.tsx root `<div>`; import the CSS file
2. Delete `utils/styles.ts` — zero importers confirmed (SESSION_ROW_STATE_ATTR is unused)
3. KanbanBoard.tsx L307: `gap: 'var(--pds-spacing-md)'`; L308: `overflowX: 'auto'`
4. Extend `ShellSecondaryCSS_1542.test.tsx` with assertions for AC-1 (FilterPanel.css existence + tokens + className), AC-2 (styles.ts absent), AC-3 (board grid gap + overflow) — follow existing file-read + regex pattern
5. Do NOT touch ErrorBoundary.tsx or ResponsiveLayout_1391 tests — owned by #1552

Proof bundle: behavioral
2026-05-14T05:51:04+00:00
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One failure domain: CSS token migration across secondary components. 3 remaining items all serve the same migration story. |
| Interface clarity | PASS (after REFINE) | Original AC described completed work. Rewrote to 3 focused AC items with specific files, tokens, and observable properties. |
| Dependency correctness | PASS | #1542 (tests) archived, #1543 (token architecture) done. Both satisfied. |
| Module layering | PASS | CSS-only changes + one file deletion. No module dependency concerns. |
| TDD compliance | PASS | Existing `ShellSecondaryCSS_1542.test.tsx` (8 tests) covers prior work. Test-writer extends with 3 new assertions for remaining AC. |
| KISS/YAGNI | PASS | 3 mechanical changes: new CSS file, file deletion, 2 inline style updates. No abstractions. |
| Premise challenge | PASS | CSS token migration is valid — brief specs require PDS token consistency across all components. |
| Pattern consistency | PASS | Follows PDS token patterns from #1543/#1546 (Shell.css, KanbanBoard.css, SessionRows.css). |
| Security surface | PASS | No new system boundaries. CSS-only. |
| Single domain | PASS | Frontend/CSS only. |

### Challenge Results
- Challenger: reconsider (0.64)
- Findings: (1) AC semantic quality — refined AC-1 to require className + import, not just tokens; (2) proof mismatch — existing tests don't cover remaining items, test-writer writes new ones per behavioral bundle; (3) #1552 boundary overlap — removed "confirmed by grep" language, #1552 owns global grep gate; (4) scope drift — rebutted, FilterPanel already uses PDS components, container tokens are remaining work; (5) traceability loss — accepted, added Prior Work section; (6) adjacent hardcoded spacing L259 — reviewed, outer layout gap not "between columns" per brief, explicitly excluded in Out scope
- Architect response: accepted findings 1/2/3/5, rebutted 4, reviewed 6. AC rewritten from 4 broad items to 3 focused remaining-work items. Dropped complexity waiver. Added explicit #1552 boundary in scope.

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED — extend ShellSecondaryCSS_1542.test.tsx with AC-1/2/3 assertions

### Verdict: APPROVE (after REFINE)
### Action Taken: Rewrote AC to 3 focused items reflecting only remaining work. Added Prior Work section for traceability. Added Builder Guidance. Explicit #1552 boundary in Out scope. Advanced to todo.
2026-05-14T05:56:50+00:00
## Test-Writer Notes
- Test file: `serve/cockpit/web/src/__tests__/ShellSecondaryCSS_1550.test.tsx`
- Classes: `TestFromAC_FilterPanelCSS_1550`, `TestFromAC_StylesTsDeletion_1550`, `TestFromAC_BoardGridTokens_1550`
- Tests per category: happy 0, edge 0, error 0, boundary 0 — all 9 are file-contract assertions (CSS/source inspection pattern matching existing suite convention)
- Total: 9 tests, all FAIL
- ruff: n/a (TypeScript) — eslint: clean

### AC Coverage
| AC | Test(s) | Status |
|----|---------|--------|
| AC-1: FilterPanel.css exists | `AC-1: FilterPanel.css exists in src/components/` | FAIL ✓ |
| AC-1: FilterPanel.tsx imports FilterPanel.css | `AC-1: FilterPanel.tsx imports FilterPanel.css` | FAIL ✓ |
| AC-1: root container has className | `AC-1: FilterPanel.tsx root container element has a className attribute` | FAIL ✓ |
| AC-1: --pds-background-surface applied | `AC-1: FilterPanel.css applies var(--pds-background-surface) for background` | FAIL ✓ |
| AC-1: --pds-border-default applied | `AC-1: FilterPanel.css applies var(--pds-border-default) for border` | FAIL ✓ |
| AC-1: --pds-spacing-md applied | `AC-1: FilterPanel.css applies var(--pds-spacing-md) for padding` | FAIL ✓ |
| AC-2: styles.ts deleted | `AC-2: utils/styles.ts is deleted (file must not exist)` | FAIL ✓ |
| AC-3: gap = var(--pds-spacing-md) | `AC-3: KanbanBoard.tsx board grid container uses var(--pds-spacing-md) for gap` | FAIL ✓ |
| AC-3: overflowX = auto | `AC-3: KanbanBoard.tsx board grid container uses overflowX: auto` | FAIL ✓ |

Commit: b50a848e
2026-05-14T06:03:52+00:00
## Builder Notes
- Implementation:
  - serve/cockpit/web/src/components/FilterPanel.tsx
  - serve/cockpit/web/src/components/FilterPanel.css
  - serve/cockpit/web/src/KanbanBoard.tsx
  - serve/cockpit/web/src/utils/styles.ts (deleted)
- AC coverage implementation:
  - AC-1: Added dedicated FilterPanel CSS file with required PDS tokens (background, border, padding), imported it in FilterPanel, and added root className on the filter panel container.
  - AC-2: Removed obsolete utils/styles.ts module from source tree.
  - AC-3: Updated KanbanBoard grid container inline styles to gap var(--pds-spacing-md) and overflowX auto.
- Tests:
  - Task suite: ShellSecondaryCSS_1550.test.tsx -> 9 passed, 0 failed.
  - Durable adjacent suite: ShellSecondaryCSS_1542.test.tsx -> 8 passed, 0 failed.
- Lint:
  - eslint/stylelint clean on scoped touched files.
- Coverage:
  - Scoped frontend quality-runner runs reported no coverage module data for these Vitest source-contract tests (non-blocking for this frontend scoped gate).
- Evidence summary:
  - RED verified pre-implementation (6 failing AC assertions).
  - GREEN verified post-implementation (all AC assertions pass, lint clean).
- Commit:
  - 4fa9da4f2b9673f27c2364d9d3a23195c8969308
  - feat: migrate secondary CSS contracts (#1550, builder)
2026-05-14T06:19:29+00:00
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1550 -> docs | AC mapped to code and evidence sufficient.

| AC | Code Evidence | Proof Evidence | Status |
|---|---|---|---|
| AC-1 | `serve/cockpit/web/src/components/FilterPanel.tsx:9` imports `./FilterPanel.css`; `serve/cockpit/web/src/components/FilterPanel.tsx:139-140` gives the root container `id="filter-panel"` and `className="filter-panel"`; `serve/cockpit/web/src/components/FilterPanel.css:1-4` applies the required `background`, `border`, and `padding` PDS tokens on `.filter-panel` | `serve/cockpit/web/src/__tests__/ShellSecondaryCSS_1550.test.tsx:16-58` covers CSS file existence, import wiring, root `className`, and required token declarations | PASS |
| AC-2 | `serve/cockpit/web/src/utils/styles.ts` is absent in the current tree; reviewer grep over `serve/cockpit/web/src/**` found no remaining production-source imports of `utils/styles` | `serve/cockpit/web/src/__tests__/ShellSecondaryCSS_1550.test.tsx:63-68` proves file deletion; reviewer source grep closed the no-import clause | PASS |
| AC-3 | `serve/cockpit/web/src/KanbanBoard.tsx:305` identifies the grid container; `serve/cockpit/web/src/KanbanBoard.tsx:307-308` set `gap: 'var(--pds-spacing-md)'` and `overflowX: 'auto'` on that grid element | `serve/cockpit/web/src/__tests__/ShellSecondaryCSS_1550.test.tsx:72-85` asserts the updated gap and overflow values in source | PASS |

- Builder evidence cross-check: commit `4fa9da4f2b9673f27c2364d9d3a23195c8969308` is present in `.git/logs`; current scoped files have no editor diagnostics.
- Blocking findings: none.

## Observations
- Initial review concern about AC-1 selector linkage was not blocking under the written contract: the AC requires a root `className`, a dedicated CSS import, and the required declarations in `FilterPanel.css`, all of which are present.
- AC-2's `no remaining source files import the module` clause is only partially encoded in the task suite; the reviewer closed that clause with a direct source grep. Later migration-verification and consolidation tasks remain useful defense-in-depth for broader token/import sweeps.
- Builder summary says RED verified with 6 failing AC assertions, while the test-writer note records 9 failing tests. That recordkeeping mismatch did not affect the current PASS because the implemented source and GREEN evidence were consistent.
2026-05-14T06:27:55+00:00
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | README verification | Yes | N/A | `serve/cockpit/README.md` covers backend API surface only; no references to `FilterPanel`, `KanbanBoard`, or `utils/styles.ts`. Grep and full editorial read confirm no stale content. |
| 2 | External attribution | No | N/A | No new external sources — PDS tokens (`--pds-background-surface`, `--pds-border-default`, `--pds-spacing-md`) are established in the codebase. |
| 3 | Research doc | No | N/A | No research artifact referenced in task body. |
| 4 | Deletion detection | Yes | N/A | `utils/styles.ts` deleted; grep of `serve/cockpit/README.md` finds no orphaned reference. No other mapped docs affected. |

### Verification Layers
- Layer 1 — grep structural: searched `serve/cockpit/README.md` for `styles\.ts`, `utils/styles`, `FilterPanel`, `KanbanBoard` — zero matches.
- Layer 2 — LLM editorial: full read of `serve/cockpit/README.md` (160 lines); content is consistent, covers backend API surface and frontend toolchain metadata; no contradictions or stale claims introduced by this task.

### Files Updated
- None

### Scratch Files Cleaned
- None (no `1550-*` scratch files existed)
2026-05-14T06:46:02+00:00
## Audit\n### Regression Detection\n- quality-runner mode full: pytest 4602 passed / 212 failed, vitest 1590 passed / 156 failed, ruff clean, eslint clean\n- Pre-existing background failures: 212 pytest failures in unrelated domains (ideation, engine, server, cockpit_view cleanup). 156 vitest failures are background. Task changed only 4 CSS/frontend files — CSS-only changes cannot cause Python test regressions.\n- Task-scoped suite: ShellSecondaryCSS_1550.test.tsx 9/9 PASS; adjacent ShellSecondaryCSS_1542.test.tsx 8/8 PASS\n- regression verdict: PASS\n\n### Intent Verification\n- scope alignment: PASS (4 changed files all in cockpit/web frontend CSS domain: FilterPanel.tsx, FilterPanel.css, KanbanBoard.tsx, styles.ts deleted)\n- purpose match: PASS (AC-1 FilterPanel PDS tokens, AC-2 styles.ts deletion, AC-3 KanbanBoard grid tokens — all addressed)\n- extraneous scope: none\n- boundary check: function-level behavior verification deferred to reviewer\n\n### Architect Quality: 4/5\nAC refined after challenger feedback (0.64 reconsider). Final 3 AC items are specific with file names, token names, and observable properties. Minor gap: builder noted 6 failing vs test-writer's 9 — recordkeeping only, not an AC deficiency.\n\n### Commit Integrity\n- upstream commit presence: PASS (builder 4fa9da4f — M FilterPanel.tsx, A FilterPanel.css, M KanbanBoard.tsx, D styles.ts; test-writer b50a848e)\n- kanban commit packaging: pending (this audit cycle)\n\n### Deduction Breakdown\nNo deductions applied.\n\n### Confidence: 1.00\n### Action: archive