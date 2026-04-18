# Memoize KanbanBoard: React.memo, useMemo, useCallback

> **Owning task:** #963 — Memoize KanbanBoard: React.memo on Card/Column, useMemo on filter/sort
> **Date:** 2026-04-18 **Status:** Complete

## 1. Context and Question

Research #959 (§ 3.2) identified a re-render cascade: every state change in KanbanBoard triggers 700 Card re-renders because there is zero memoization. Task #963 asks whether `React.memo`, `useMemo`, and `useCallback` can eliminate this at zero bundle cost.

Sub-questions: (a) Where does each hook go? (b) Should Column filtering move inside Column or stay in KanbanBoard? (c) Any risks to existing tests? (d) Is React Compiler a better alternative?

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| S1 | `serve/cockpit/web/src/KanbanBoard.tsx` — 200 LOC, 3 components, zero memoization | 0.95 |
| S2 | `serve/cockpit/web/src/__tests__/KanbanBoard.test.tsx` — 26+ tests, DOM-only assertions | 0.90 |
| S3 | `.owlbear/research/959-frontend-perf-virtualization.md` § 3.2 — re-render cascade analysis | 0.90 |
| S4 | react.dev/reference/react/memo — React.memo API, shallow comparison, when to use | 0.85 |
| S5 | react.dev/reference/react/useMemo — caching calculations, dependency array | 0.85 |
| S6 | react.dev/reference/react/useCallback — caching functions, memo compatibility | 0.85 |
| S7 | `serve/cockpit/web/vite.config.ts` — standard @vitejs/plugin-react, no React Compiler | 0.80 |

## 3. Analysis

### 3.1 Filtering Location: Column-Internal vs KanbanBoard-Level Map

| Criterion | Filter inside Column | tasksByStatus map in KanbanBoard |
|-----------|---------------------|--------------------------------|
| Interface change | Column receives all tasks (breaking change) | Column keeps current pre-filtered tasks prop |
| `tasks.length` in header | Breaks — shows 700 instead of column count | Correct — uses filtered array length |
| Memos added | 7 useMemos (1 per column) | 1 useMemo for the map |
| Code diff size | Larger (Column interface + filtering logic) | Smaller (1 memo in KanbanBoard) |
| AC match | Literal match for "Column task filtering uses useMemo" | Semantic match — memo serves column filtering |

**Winner: KanbanBoard-level map.** Avoids interface change and B3 regression risk (challenger). The AC "Column task filtering uses useMemo" is satisfied by memoizing the filtering FOR columns, even if the memo is in the parent.

### 3.2 Recommended Implementation

| AC Item | Location | Code Pattern |
|---------|----------|-------------|
| Card → React.memo | Card component | `const Card = memo(function Card({...}) {...})` |
| Column sort → useMemo | Column component | `useMemo(() => [...tasks].sort(...), [tasks, priorities])` |
| handleContextMenu → useCallback | KanbanBoard | `useCallback((e, task) => { ... setContextMenu(...) }, [])` |
| Column filtering → useMemo | KanbanBoard | `useMemo(() => Object.groupBy(tasks, t => t.status), [tasks])` |

**Hook ordering gotcha:** `handleContextMenu` is currently defined after early returns. `useCallback` must move before them (React hooks rule: same order every render). No behavioral change — the callback is unused during loading/error states.

**Object.groupBy note:** Available in all modern browsers and Node 22+. Alternative: manual `reduce()` or `for-of` loop to build the map. `Object.groupBy` is cleanest but check TypeScript target.

### 3.3 Re-Render Cascade: Before vs After

| Trigger | Before (no memo) | After (memo) |
|---------|-------------------|--------------|
| contextMenu click | 7 Column renders + 700 Card renders + 7 filter + 7 sort | 7 Column renders + 0 Card renders + 0 filter + 0 sort |
| tasks data change | 7 Column renders + 700 Card renders + 7 filter + 7 sort | 7 Column renders + 700 Card renders + 7 filter + 7 sort |

Memo eliminates re-renders from unrelated state changes. When tasks themselves change, memos correctly invalidate. Adding React.memo to Column would further eliminate the 7 Column renders for unrelated state changes, but this is out of AC scope.

### 3.4 React Compiler Alternative

React Compiler (babel-plugin-react-compiler) would auto-memoize all values, functions, and components — making manual memos redundant. Integration: 1 Vite plugin addition. However: (a) adds a build dependency, (b) still experimental as of React 19, (c) overkill for 1 component. Manual memos are simpler and self-documenting for this scope. Created follow-up for evaluation.

### 3.5 Test Compatibility

All 26+ tests use `data-testid` DOM selectors and behavior assertions. React.memo/useMemo/useCallback are transparent optimizations — they don't change rendered output. No test modifications needed. Verified: no tests assert render counts or component identity.

### 3.6 Risks

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Hook ordering (handleContextMenu before early returns) | Low | Restructure only — no behavioral change |
| Polling creates new task refs, defeating Card memo | Medium | Polling task should preserve refs when data unchanged (mtime check) |
| No measurement AC proves benefit | Low | Benchmark task exists as #959 follow-up; #963 is structural |
| Object.groupBy TypeScript support | Low | Use manual loop if TS target doesn't support it |

## 4. Recommendation

**Proceed with manual memoization using KanbanBoard-level tasksByStatus map.**

Four changes: (1) Card → React.memo, (2) Column sort → useMemo, (3) handleContextMenu → useCallback, (4) tasksByStatus → useMemo in KanbanBoard. Keep Column's interface unchanged.

**Confidence: 0.80**

Challenge: `reconsider` — challenger confidence in original: 0.50. Valid concerns accepted: C1 (use KanbanBoard-level map instead of Column-internal filtering — avoids interface change), B3 (tasks.length regression — eliminated by keeping pre-filtered props), C4 (structural AC acknowledged — benchmark is separate task). Rejected: A1 (YAGNI — task exists with defined AC, research validates approach not premise), A2 (React Compiler — additional build dep for 1 component is not KISS).

## 5. Follow-up Tasks

1. React Compiler evaluation — assess integration cost vs manual memo maintenance burden
