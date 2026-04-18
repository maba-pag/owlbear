# RED: Context Menu Transition-Click → POST /move Tests

> **Owning task:** #958 — RED: Context menu transition-click triggers POST /move and refetches board
> **Date:** 2026-04-18 **Status:** Complete

## 1. Context and Question

Task #933 implemented a display-only context menu on kanban cards — right-click shows valid transitions, but items have no click handler. This task writes RED tests exposing the gap: clicking a transition item should POST to `/api/tasks/{id}/move`, refetch the board, show errors on failure, and close the menu.

**Key question:** What test patterns are needed, and do the existing conventions support them?

## 2. Sources Studied

| # | Source | Relevance | What was taken |
|---|--------|-----------|---------------|
| 1 | `serve/cockpit/web/src/KanbanBoard.tsx` (lines 155–207) | 1.0 | Context menu renders `transition-item` divs with no onClick — confirms RED gap |
| 2 | `serve/cockpit/web/src/__tests__/KanbanBoard.test.tsx` | 1.0 | Established stub pattern: `vi.stubGlobal('fetch', ...)`, `fireEvent.contextMenu()`, `waitFor()` |
| 3 | `serve/cockpit/src/owlbear_cockpit/routes/mutation.py` (lines 78–92) | 0.9 | POST `/tasks/{id}/move` accepts `{status}`, validates transitions, returns 422/404 |
| 4 | `serve/cockpit/web/src/__tests__/KanbanBoard_933.test.tsx` | 0.8 | Additional fetch stub patterns (error stubs, multi-task stubs) |

## 3. Analysis

### Current Component Gap

The transition items in `KanbanBoard.tsx` line 201–203 are:
```tsx
<div key={target} data-testid="transition-item" data-status={target}>
  → {target}
</div>
```
No `onClick`, no task ID tracked in context menu state, no refetch mechanism in `useBoard()`.

### Test Strategy Matrix

| AC | Test approach | Stub modification | Expected RED failure reason |
|----|--------------|-------------------|---------------------------|
| AC1: POST /move called | Click transition-item, assert fetch called with POST + correct body | Add POST handler to stub | No onClick handler exists |
| AC2: Board refetch | After successful move, assert fresh GET calls and updated DOM | Return different data on 2nd GET | No refetch mechanism exists |
| AC3: Error on failure | Stub POST to return 422, assert error element appears | Add failing POST handler | No error handling for moves |
| AC4: Menu closes | After click, assert context-menu element is gone | Standard success stub | No click handler to close menu |

### Conventions to Follow

- Extend existing `KanbanBoard.test.tsx` (per task AC "extend existing")
- New `describe('move via context menu', ...)` block inside `TestFromAC_KanbanBoard`
- Track task ID in context menu interaction: right-click card → get task ID from `data-id`, click transition → assert POST with that ID
- The fetch stub needs to intercept POST method — current stubs only check URL path

## 4. Recommendation

Proceed with standard RED tests in the existing test file. No new dependencies, patterns, or architectural changes needed. Confidence: **.92**

Challenge: FALLBACK — subagent unavailable for trivial test research.

## 5. Follow-up Tasks

None — #958 itself is the actionable task and is ready to advance to backlog for test-writer pickup.
