# Shell.css + Secondary Component CSS Implementation

> **Owning task:** #1550 — P3-10: impl — Shell.css + secondary component CSS migration
> **Date:** 2026-05-14 **Status:** Complete

## 1. Context and Question

Task #1550 implements CSS token migration across Shell.css, context menu, filter panel, DetailTab/ActivityTab, and the board container. Dependencies #1542 (tests) and #1543 (token architecture) are archived/completed. Question: what implementation work remains, and what was already completed by prior tasks?

## 2. Sources Studied

| Source | URL/Path | Relevance |
|--------|----------|-----------|
| Shell.css | `serve/cockpit/web/src/Shell.css` | 1.0 — target file for AC-1 |
| KanbanBoard.css | `serve/cockpit/web/src/KanbanBoard.css` | 1.0 — context menu CSS (AC-2) |
| KanbanBoard.tsx L295-312 | `serve/cockpit/web/src/KanbanBoard.tsx` | 1.0 — board container layout (AC-4) |
| FilterPanel.tsx | `serve/cockpit/web/src/components/FilterPanel.tsx` | 1.0 — filter panel structure (AC-2) |
| styles.ts | `serve/cockpit/web/src/utils/styles.ts` | 1.0 — deletion target (AC-3) |
| SessionRows.css | `serve/cockpit/web/src/components/SessionRows.css` | 0.9 — `[data-state]` replacement (AC-3) |
| DetailTab.tsx | `serve/cockpit/web/src/components/DetailTab.tsx` | 0.9 — AC-3 scope verification |
| ActivityTab.tsx | `serve/cockpit/web/src/components/ActivityTab.tsx` | 0.9 — AC-3 scope verification |
| ShellSecondaryCSS_1542 tests | `serve/cockpit/web/src/__tests__/ShellSecondaryCSS_1542.test.tsx` | 0.9 — test coverage baseline |
| #1552 task (grep gate) | `.owlbear/kanban/tasks/1552-*.md` | 0.8 — owns legacy-token cleanup in tests |
| #1542 research doc | `.owlbear/research/1542-shell-secondary-css-test-approach.md` | 0.8 — test patterns for this migration |
| Brief (parent #1534) | `.owlbear/briefs/draft-board-visual-design/brief.md` | 1.0 — specifications |

## 3. Analysis

### 3.1 AC Status Matrix

| AC | Requirement | Status | Evidence | Remaining Work |
|----|-------------|--------|----------|---------------|
| AC-1 | Shell.css agnostic tokens + breakpoints | **Done** | 19 `--pds-*` refs, 0 `--pds-theme-light-*`, 3 breakpoints intact | None |
| AC-2a | Context menu PDS tokens | **Done** | KanbanBoard.css `.kanban-context-menu` with `--pds-background-surface`, `--pds-shadow-md`, `--pds-radius-md` | None |
| AC-2b | Filter panel PDS tokens | **Open** | FilterPanel.tsx container `<div>` has no CSS class, no background/border/spacing tokens | Create FilterPanel.css, add className, import |
| AC-3a | `rowStyleForState()` removed | **Done** | `styles.ts` exports only `SESSION_ROW_STATE_ATTR`; no files import `rowStyleForState` | None |
| AC-3b | `[data-state]` CSS selectors | **Done** | SessionRows.css: `[data-state="blocked"]`, `[data-state="rejected"]`, `[data-state="stuck"]` | None |
| AC-3c | `styles.ts` file deleted | **Open** | File exists with unused `SESSION_ROW_STATE_ATTR` constant (0 importers) | Delete file |
| AC-3d | DetailTab agnostic tokens | **N/A** | DetailTab.tsx has zero styling — pure structural JSX delegating to HistorySubtab/TaskFieldsEditor. No tokens to migrate. | None (structural component) |
| AC-3e | ActivityTab agnostic tokens | **Done** | Imports `./SessionRows.css` (line 6); no legacy token refs | None |
| AC-4 | Board container gap + overflow | **Open** | KanbanBoard.tsx L307: `gap: '16px'` (hardcoded), L308: `overflowX: 'hidden'` | Change to `var(--pds-spacing-md)` and `auto` |

### 3.2 Implementation Approach

| Item | Files | Change | Risk |
|------|-------|--------|------|
| FilterPanel CSS (AC-2b) | New `FilterPanel.css` + FilterPanel.tsx | Add CSS class to container div with `background: var(--pds-background-surface)`, `border: 1px solid var(--pds-border-default)`, `padding: var(--pds-spacing-md)` | Low — PDS components style themselves; external container tokens won't conflict |
| styles.ts deletion (AC-3c) | Delete `utils/styles.ts` | `SESSION_ROW_STATE_ATTR` has 0 importers; safe to delete | Low — grep confirms no references |
| Board container (AC-4) | KanbanBoard.tsx | L307: `gap: 'var(--pds-spacing-md)'`, L308: `overflowX: 'auto'` | Low — token `--pds-spacing-md` defined in tokens.css (16px fallback) |

### 3.3 Ownership Boundaries

| Item | Owner | NOT #1550 |
|------|-------|-----------|
| ErrorBoundary.tsx `--pds-theme-light-contrast-medium` (L30) | #1552 grep gate | Legacy token in component outside AC scope |
| ResponsiveLayout_1391 stale AC-5 tests (L296-309) | #1552 grep gate | Stale test assertions for old tokens — #1542 archive explicitly routes to #1552 |
| styles.test.ts (deleted) | Already done | File already absent per ShellSecondaryCSS_1542 AC-3(e) test |

### 3.4 Test Coverage

Existing `ShellSecondaryCSS_1542.test.tsx` (8 tests, all passing) covers AC-1, AC-2 (context menu), AC-3. Gaps:

| Gap | Coverage Impact |
|-----|----------------|
| AC-2b filter panel tokens | No test asserts FilterPanel.css existence or PDS token usage |
| AC-4 board container | No test asserts `var(--pds-spacing-md)` gap or `overflow-x: auto` |

Builder should extend `ShellSecondaryCSS_1542.test.tsx` with 2–3 additional assertions for these gaps, following the established file-read + regex pattern.

## 4. Recommendation

**Proceed with implementation** (confidence: 0.80).

Three small, low-risk changes remain: FilterPanel.css creation, styles.ts deletion, and board container token migration. AC-1, AC-2a, AC-3a/b/e are already satisfied by prior task work.

Challenge: reconsider (original 0.58) — challenger correctly identified: (1) proof mismatch on AC-3 file deletion, (2) missing filter panel evidence, (3) AC-4 unproven, (4) ownership drift for ErrorBoundary/ResponsiveLayout cleanup. All accepted. Revised recommendation drops ErrorBoundary/ResponsiveLayout from scope (owned by #1552), explicitly separates done vs open items, and reduces confidence from 0.85 to 0.80 (remaining items are mechanical but need test coverage).

**Tier: T1 — Autonomous.** CSS token migration and file deletion. No architecture, capability, or security changes.

## 5. Follow-up Tasks

None needed. Remaining work is within #1550's scope — the builder implements AC-2b, AC-3c, AC-4, and extends test coverage. No new tasks required.

Builder guidance summary:
1. Create `FilterPanel.css` with PDS background/border/spacing tokens → import from FilterPanel.tsx
2. Delete `utils/styles.ts` (zero importers)
3. KanbanBoard.tsx board grid: `gap: 'var(--pds-spacing-md)'`, `overflowX: 'auto'`
4. Extend `ShellSecondaryCSS_1542.test.tsx` with AC-2b + AC-4 assertions
5. Do NOT touch ErrorBoundary.tsx or ResponsiveLayout_1391 tests — those belong to #1552
