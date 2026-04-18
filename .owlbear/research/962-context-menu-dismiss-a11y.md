# RED: Context Menu Dismiss Behavior + Accessibility Basics

> **Owning task:** #962 — RED: Context menu dismiss behavior + accessibility basics
> **Date:** 2026-04-18 **Status:** Complete

## 1. Context and Question

The #931 RED tests cover menu opening and transition rendering. The #958 RED tests cover transition-click → POST. Neither covers **dismiss behavior** (click-outside, Escape, re-right-click) or **baseline ARIA roles** (`role="menu"`, `role="menuitem"`). A menu that opens but cannot be dismissed is broken UX; missing ARIA roles violate PDS accessibility requirements.

**Key question:** Can all five dismiss/a11y ACs be tested with the existing vitest+jsdom+RTL stack, and what patterns are needed?

## 2. Sources Studied

| # | Source | Relevance | What was taken |
|---|--------|-----------|---------------|
| 1 | WAI-ARIA APG Menu Pattern ([w3.org](https://www.w3.org/WAI/ARIA/apg/patterns/menu/)) | 1.0 | Menu container: `role="menu"`. Items: `role="menuitem"`. Escape closes menu and returns focus. |
| 2 | RTL fireEvent docs ([testing-library.com](https://testing-library.com/docs/dom-testing-library/api-events)) | 0.9 | `fireEvent.keyDown(node, {key: 'Escape'})`, `fireEvent.mouseDown(node)`, `fireEvent.contextMenu(node)` patterns |
| 3 | `serve/cockpit/web/src/KanbanBoard.tsx` (lines 155–207) | 1.0 | No click-outside listener, no keydown listener, no ARIA roles on menu div or items |
| 4 | `serve/cockpit/web/src/__tests__/KanbanBoard.test.tsx` | 1.0 | Established patterns: `vi.stubGlobal`, `fireEvent.contextMenu()`, `waitFor()`, `data-testid` queries |
| 5 | `serve/cockpit/web/vitest.setup.ts` | 0.8 | jsdom env confirmed, PDS polyfill, no event-related limitations |

## 3. Analysis

### Current Component Gaps

```
KanbanBoard.tsx context menu (lines 195–207):
- ❌ No document mousedown/click listener → click-outside won't dismiss
- ❌ No document keydown listener → Escape won't dismiss
- ✅ setContextMenu() replaces state → re-right-click already works implicitly
- ❌ No role="menu" on container div
- ❌ No role="menuitem" on transition-item divs
- ❌ No done-status task in mock → need mock extension for done-card test
```

### Test Pattern Matrix

| AC | Event Sequence | Assertion | jsdom | Mock Change |
|----|---------------|-----------|-------|-------------|
| Click-outside dismiss | `contextMenu(card)` → `mouseDown(document.body)` | `[data-testid="context-menu"]` absent | ✅ | None |
| Escape dismiss | `contextMenu(card)` → `keyDown(document, {key:'Escape'})` | `[data-testid="context-menu"]` absent | ✅ | None |
| Re-right-click | `contextMenu(cardA)` → verify A transitions → `contextMenu(cardB)` | Menu shows B transitions, not A | ✅ | None |
| ARIA roles | `contextMenu(card)` | `role="menu"` on container, `role="menuitem"` on items | ✅ | None |
| Done card | `contextMenu(doneCard)` | No menu OR menu with 0 transition-items | ✅ | Add `{status:'done'}` task |

### jsdom Event Behavior (verified)

- `mouseDown` on `document.body` bubbles correctly in jsdom — standard click-outside detection works.
- `keyDown` on `document` with `{key: 'Escape'}` — jsdom dispatches the KeyboardEvent properly.
- `contextMenu` on a second card — React re-render replaces `contextMenu` state; verified by existing tests.

### Done-Card Mock Extension

Current TASKS fixture has no `status: 'done'` task. Add:
```ts
{ id: 5, title: 'Completed task', status: 'done', priority: 'nice-to-have',
  tags: [], blocked: false, block_reason: null, claimed: false }
```
This is additive and won't break existing tests since `done` column currently shows empty state.

### Risk Assessment

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| mouseDown vs click for click-outside | Low | Both work in jsdom; mouseDown is the standard pattern (fires before click, prevents edge cases) |
| Done card: "no menu" vs "empty menu" ambiguity | Low | AC says "shows no menu or an empty menu" — test can assert either; recommend testing for absent menu (stricter UX) |

## 4. Recommendation

Proceed with five RED tests in a new `describe('dismiss and accessibility', ...)` block inside the existing `TestFromAC_KanbanBoard` suite. Standard fireEvent patterns, no new dependencies. Add one mock task for done-card AC.

**Confidence: .92** — All patterns are well-established; existing test infrastructure fully supports them.

Challenge: skipped — pattern-confirmation research, no alternative trade-offs to challenge.

## 5. Follow-up Tasks

No new follow-up tasks needed — #962 itself is the actionable RED test task and is ready to advance to backlog.
