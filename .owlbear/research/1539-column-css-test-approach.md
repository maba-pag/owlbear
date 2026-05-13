# Column Component CSS Test Approach

> **Owning task:** #1539 — P3-03: test — column component CSS: fixed header, scroll body, empty text fallback
> **Date:** 2026-05-13 **Status:** Complete

## 1. Context and Question

Task #1539 writes Vitest tests (RED phase) for column CSS behaviors defined in the board visual design brief (#1534). Three ACs: header/body separation, overflow scrolling, empty state text. Question: what test approach works in jsdom for CSS layout assertions?

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| SO: vitest CSS styling test | stackoverflow.com/questions/76571158 | 0.9 — confirms jsdom CSS cascade not implemented |
| jsdom/jsdom#2690 | github.com/jsdom/jsdom/pull/2690 | 0.8 — CSS cascade implementation status |
| Codebase: Column.tsx | serve/cockpit/web/src/components/Column.tsx | 1.0 — current component structure |
| Codebase: ResponsiveLayout_1391.test.tsx | serve/cockpit/web/src/__tests__/ | 0.9 — file-based CSS testing pattern |
| Codebase: KanbanBoard.test.tsx | serve/cockpit/web/src/__tests__/ | 0.8 — existing column DOM tests |
| Brief: board visual design | .owlbear/briefs/draft-board-visual-design/brief.md | 1.0 — column spec |
| Vitest environment docs | vitest.dev/guide/environment | 0.7 — jsdom test env config |

## 3. Analysis

### 3.1 Current Column.tsx State vs Brief Target

| Aspect | Current | Brief Target |
|--------|---------|-------------|
| Header/body | Single `<div>` wraps all | Separate header + scrollable body |
| Overflow | Inline `overflowY` on root div (conditional) | Body container with `overflow-y: auto` |
| Empty text | "No tasks" (generic) | "No {status} tasks" (parameterized) |
| Centering | None | Centered empty state |
| CSS file | None (inline styles only) | Column.css expected |

### 3.2 jsdom CSS Limitation

jsdom does NOT implement the CSS cascade ([jsdom#2690](https://github.com/jsdom/jsdom/pull/2690)). `getComputedStyle()` returns empty strings for class-based CSS properties. Confirmed by SO #76571158 and Vitest docs.

**Impact by AC:**
- AC-1 (header/body separation): No impact — DOM structure is fully testable
- AC-2 (overflow-y): Cannot verify via `getComputedStyle`; need alternative
- AC-3 (centered layout): Cannot verify centering geometry; need proxy proof

### 3.3 Test Approach per AC

| AC | Strategy | Proof Type | False-Green Risk |
|----|----------|-----------|-----------------|
| AC-1 | Render → verify `<header>` and body are sibling children of column root | DOM structure | Low |
| AC-2 | **Dual-proof:** (a) render → verify body element has CSS class, (b) read Column.css → verify class has `overflow-y: auto` | Class wiring + source contract | Low |
| AC-3 | (a) Render → verify "No {status} tasks" text, (b) read Column.css → verify centering declarations | Content + source contract | Medium (centering) |

### 3.4 Dual-Proof Rationale

The challenger (0.57 confidence in original) correctly identified that file-based CSS parsing alone doesn't prove CSS-to-DOM wiring, and DOM-only checks don't prove CSS property values. The dual-proof closes both gaps:

1. **Rendered element** → proves the CSS class is wired to the DOM node
2. **CSS file parse** → proves the class defines the expected property

Neither alone is sufficient; together they provide source-contract proof.

### 3.5 Existing Test Overlap

KanbanBoard.test.tsx already covers column count badge presence and empty-state non-blank text. New tests must be **discriminating** — testing scroll semantics and status-parameterized text, not duplicating existence checks.

### 3.6 Centering Limitation

AC-3 "centered layout" is a layout geometry claim. jsdom cannot verify centering. The test provides CSS source-contract proof (file contains centering declarations on the empty-state class). True geometric proof requires Playwright E2E.

## 4. Recommendation

**Proceed with dual-proof approach** (confidence: 0.75, revised from 0.57 after addressing challenger concerns).

Test structure per AC:
- **AC-1**: Render Column → query column root → verify it has a `<header>` child AND a separate body child (using `data-testid="column-body"` or similar) → verify they are siblings, not nested
- **AC-2**: (a) Render Column with tasks → query body container → verify CSS class presence via `classList.contains()` or `className`; (b) Read Column.css as string → regex for body class + `overflow-y: auto`
- **AC-3**: (a) Render Column with status="research" and empty tasks → verify text "No research tasks" appears; (b) Read Column.css → verify empty-state class has centering (`text-align: center` or flex centering)

Challenge: reconsider → revised to dual-proof — confidence in original: 0.57. After revision: 0.75.

**Tier: T1 — Autonomous.** Test scaffolding guidance, no architecture changes.

## 5. Follow-up Tasks

None needed — #1539 is correctly scoped. Notes for test-writer:
- Use `data-testid="column-body"` as the expected test hook for the scrollable body (or document what the impl task should provide)
- Existing KanbanBoard tests cover count-badge presence — don't re-test that
- The dual-proof pattern (rendered class + CSS file regex) should be the standard for all component CSS test tasks in this brief
