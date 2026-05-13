# Shell.css + Secondary Component CSS Test Approach

> **Owning task:** #1542 — P3-09: test — Shell.css + secondary component CSS migration
> **Date:** 2026-05-13 **Status:** Complete

## 1. Context and Question

Task #1542 writes Vitest tests (RED phase) for Shell.css token migration, context menu styling, and `styles.ts` removal. Three ACs covering: agnostic token rename in Shell.css, context menu PDS token usage, and `rowStyleForState()` deletion with `[data-state]` CSS replacement. Question: what test patterns suit each AC given jsdom's CSS limitations?

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| Codebase: Shell.css | `serve/cockpit/web/src/Shell.css` | 1.0 — 12+ `--pds-theme-light-*` refs to be renamed |
| Codebase: styles.ts | `serve/cockpit/web/src/utils/styles.ts` | 1.0 — `rowStyleForState()` export to be removed |
| Codebase: HistorySubtab.tsx | `serve/cockpit/web/src/components/HistorySubtab.tsx` | 0.9 — already has `data-state={s.state}` on rows |
| Codebase: ActivityTab.tsx | `serve/cockpit/web/src/components/ActivityTab.tsx` | 0.9 — imports `rowStyleForState`, renders inline styles |
| Codebase: ResponsiveLayout_1391.test.tsx | `serve/cockpit/web/src/__tests__/` | 0.9 — file-based CSS test pattern (fs.readFileSync) |
| Codebase: #1539 research | `.owlbear/research/1539-column-css-test-approach.md` | 0.9 — dual-proof model for CSS tests |
| Codebase: #1535 research | `.owlbear/research/1535-token-architecture-test-approach.md` | 0.8 — file-based token verification |
| Vitest #1689 | `github.com/vitest-dev/vitest/issues/1689` | 0.8 — confirms jsdom CSS cascade not implemented |
| Brief: board visual design | `.owlbear/briefs/draft-board-visual-design/brief.md` | 1.0 — component specs and migration targets |

## 3. Analysis

### 3.1 Current State vs Brief Target

| Component | Current | Brief Target |
|-----------|---------|-------------|
| Shell.css tokens | 12+ `--pds-theme-light-*` refs (background-base, surface, contrast-low, primary) | All agnostic `--pds-*` names |
| Context menu CSS | Zero CSS — inline `position:fixed` only, no background/shadow/radius | PDS `background-surface`, `shadow-md`, `radius-md` |
| styles.ts | Exports `rowStyleForState()` with 3 branches, used by HistorySubtab + ActivityTab | **Deleted** — styles absorbed into `[data-state]` CSS selectors |
| HistorySubtab `data-state` | ✅ Already has `data-state={s.state}` on rows | Kept — CSS targets this attribute |
| ActivityTab `data-state` | Uses `rowStyleForState()` inline + `data-state` via HistorySubtab | CSS-only via `[data-state]` selectors |

### 3.2 Test Approach per AC

| AC | Strategy | Proof Type | False-Green Risk |
|----|----------|-----------|-----------------|
| AC-1 | Read Shell.css → regex assert zero `--pds-theme-light-` matches + ≥5 `--pds-` tokens present | Source contract | Low |
| AC-2 | Triple-proof: (a) render menu → verify CSS class; (b) read CSS file → exact tokens `--pds-background-surface`, `--pds-shadow-md`, `--pds-radius-md`; (c) read KanbanBoard.tsx → verify CSS import | Class wiring + source contract + import proof | Low |
| AC-3 | Triple-proof: (a) verify `rowStyleForState` export absent; (b) read CSS → verify `[data-state="blocked"]` and `[data-state="stuck"]` selectors; (c) read component source → verify CSS file imported by component that renders `data-state` rows | Source contract + import wiring | Low |

### 3.3 AC-1: Shell.css Token Scan

Shell.css currently has 12+ occurrences of `--pds-theme-light-*`:
- `--pds-theme-light-background-base`, `--pds-theme-light-background-surface`
- `--pds-theme-light-contrast-low`, `--pds-theme-light-primary`

Test reads Shell.css via `fs.readFileSync`, uses regex `/--pds-theme-light-/g` and asserts zero matches. Positive check: verify at least 5 `--pds-` token references exist (guards against empty file). Pattern established in #1535 research.

### 3.4 AC-2: Context Menu — Concrete Target and Exact Tokens

Context menu is rendered inside `KanbanBoard.tsx` (line ~346). No dedicated CSS file exists today.

**Target CSS file:** `KanbanBoard.css` — co-located with the rendering component. The context menu is not a standalone component (it's a conditional `<div>` inside KanbanBoard), so a separate `ContextMenu.css` would be orphaned from its owner. KanbanBoard.css is the natural home.

**Exact tokens to assert (from brief §Context Menu):**
- `--pds-background-surface` (agnostic name, post-migration)
- `--pds-shadow-md` (shadow scale)
- `--pds-radius-md` (border-radius scale)

**Triple-proof chain:**
1. **Source contract:** Read `KanbanBoard.css` → regex for `.context-menu` (or `[data-testid="context-menu"]`) class containing exact tokens `--pds-background-surface`, `--pds-shadow-md`, `--pds-radius-md`
2. **Import wiring:** Read `KanbanBoard.tsx` → verify `import './KanbanBoard.css'`
3. **DOM wiring:** Render context menu → verify element has the expected CSS class via `classList.contains()`

This closes the gap the challenger identified: proving the class exists, proving the file is imported, proving the DOM element uses the class.

### 3.5 AC-3: styles.ts Removal — Ownership Clarification

The challenger correctly identified that `DetailTab.tsx` does NOT render session rows directly — it delegates to `HistorySubtab.tsx`. The actual `rowStyleForState()` consumers are:
- `HistorySubtab.tsx` (line 58: `style={rowStyleForState(s.state)}`)
- `ActivityTab.tsx` (line 155: `style={rowStyleForState(s.state)}`)

Both already render `data-state={s.state}` on rows. The implementation removes the inline `style=` binding and adds CSS `[data-state]` selectors to a CSS file imported by these components.

**Triple-proof chain:**
1. **Export removal:** `fs.existsSync(stylesPath)` returns false OR file content lacks `export function rowStyleForState` (handles both deletion and refactoring)
2. **CSS replacement:** Read CSS file (likely `HistorySubtab.css` or `ActivityTab.css`) → verify selectors `[data-state="blocked"]`, `[data-state="stuck"]` with `border-left` and `background-color` declarations
3. **Import wiring:** Read `HistorySubtab.tsx` source → verify CSS file import; read `ActivityTab.tsx` source → verify CSS file import OR verify it delegates to HistorySubtab which imports the CSS

**Note for test-writer:** `data-state` DOM attribute is already present — no DOM render assertion needed for that (it's already covered by existing ActivityTab tests). The new proof is the CSS file + import chain.

### 3.6 Existing Test Impact

| Test File | Impact | Owner |
|-----------|--------|-------|
| `styles.test.ts` | Tests `rowStyleForState()` directly — obsolete after removal | Builder (#1550) deletes |
| `ActivityTab.fetch-filter.test.tsx` L519 | Checks `style.cursor === 'pointer'` — needs migration to CSS-based check | Builder (#1550) updates |
| `KanbanBoard.both-or-nothing.test.tsx` | Checks `card.style.borderLeft` — separate card task, not this scope | Out of scope |

## 4. Recommendation

**Proceed with triple-proof approach** (confidence: 0.75, revised from 0.80 after challenger).

Test structure:
- **AC-1:** Read Shell.css → negative regex for `--pds-theme-light-` (zero matches) + positive regex for `--pds-` (≥5 matches)
- **AC-2:** (a) Read KanbanBoard.css → regex for `.context-menu` class with exact tokens `--pds-background-surface`, `--pds-shadow-md`, `--pds-radius-md`; (b) Read KanbanBoard.tsx → verify CSS import; (c) Render context menu → verify CSS class on element
- **AC-3:** (a) `styles.ts` absent or `rowStyleForState` export gone; (b) CSS file has `[data-state="blocked"]` + `[data-state="stuck"]` selectors; (c) Component source imports that CSS file

**Tier: T1 — Autonomous.** Test scaffolding guidance, no architecture changes.

## Challenge Results

- Challenger: reconsider (original 0.58)
- Key challenges accepted:
  - **CSS-to-DOM wiring gap (critical):** Added import-wiring proof leg to AC-2 and AC-3. Without it, CSS file + DOM class don't prove the selector reaches the element.
  - **Token contract drift (moderate):** Tightened to exact token names: `--pds-background-surface`, `--pds-shadow-md`, `--pds-radius-md`.
  - **Non-concrete AC-2 target (moderate):** Specified `KanbanBoard.css` as target file, `.context-menu` as expected class.
  - **DetailTab ownership (blind spot):** Clarified DetailTab delegates to HistorySubtab; the real consumers are HistorySubtab + ActivityTab.
- Rejected: block recommendation — concerns are valid but addressable by tightening proof chains, not blocking the task.
- Confidence in revised: 0.75

## 5. Follow-up Tasks

None needed — #1542 is correctly scoped for test-writing. Notes for test-writer:
- Use triple-proof pattern: source contract (CSS file) + import wiring (component imports CSS) + DOM structure (element has class/attribute)
- Shell.css negative scan is straightforward file-based analysis (single-proof adequate)
- Target `KanbanBoard.css` for context menu styles; use filename constant so builder can match
- Target `HistorySubtab.css` or `ActivityTab.css` for `[data-state]` selectors; verify import chain
- Existing `styles.test.ts` becomes obsolete — NOT in scope for #1542 (builder handles)
- `data-state` DOM attribute already exists on HistorySubtab rows — no need to re-test presence
