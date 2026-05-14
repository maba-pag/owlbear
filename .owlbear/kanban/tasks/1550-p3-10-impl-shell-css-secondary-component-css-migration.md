---
id: 1550
title: 'P3-10: impl — Shell.css + secondary component CSS migration'
status: in-progress
priority: important
created: 2026-05-13T18:43:23.937036+00:00
updated: 2026-05-14T05:56:50.762163+00:00
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
archival_reason:
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