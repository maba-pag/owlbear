# Full Board Filter Integration Tests — Research

> **Owning task:** #1256 — P5-01: Integration tests — full board filter flow
> **Date:** 2026-05-03 **Status:** Complete

## 1. Context and Question

Task #1256 requires end-to-end Vitest integration tests for the complete filter feature. Existing tests either mock FilterPanel (#1252, #1254) or test components in isolation (#1248, #1249, #1250). The question: what test strategy exercises the real KanbanBoard + FilterPanel + filterTasks chain, and what are the jsdom interaction patterns needed?

## 2. Sources Studied

| Source | Relevance | Notes |
|--------|-----------|-------|
| `KanbanBoard_1252.test.tsx` | 1.0 | Mocked FilterPanel — proves AC scenarios but not real DOM interactions |
| `FilterPanel_1250.test.tsx` | 1.0 | Proves PDS event patterns: `CustomEvent('change')` for PSelect, `CustomEvent('update')` for PMultiSelect, `fireEvent.click()` for checkbox |
| `FilterAccessibilityPanel_1254.test.tsx` | 0.9 | Uses REAL FilterPanel without vi.mock — proves the unmocked render pattern works |
| `Column.tsx` | 0.8 | `data-column`, `data-testid="empty-column"`, `data-testid="column-count"` selectors |
| `Card.tsx` | 0.8 | `data-testid="task-card"`, `data-id={task.id}` selectors |
| `KanbanBoard.tsx` | 1.0 | `handleFilterChange` dismisses context menu and cancels drag; `availableTags` from full task set |

## 3. Analysis

### Integration vs. Unit Test Gap

| Scenario | Covered by #1252 (mocked) | Integration adds |
|----------|---------------------------|------------------|
| Filter → correct columns | ✓ via `capturedOnFilterChange` | Real user typing in text input |
| Empty column placeholder | ✗ (not tested) | Column shows "No tasks" after filtering |
| Result count | ✓ | Real FilterPanel trigger |
| Toggle badge count | ✓ | Real panel interaction cycle |
| Context menu dismissal | ✓ via callback | Real filter control change |
| Drag cancellation | ✓ via callback | Real filter control change |
| Tag filter → 0-result state | ✗ | Tags in filter persist after no tasks match |
| Reset clears all | ✗ (partial) | Click real "Clear all" button |
| Accessibility attributes | ✓ separate file | Combined tree verification |

### PDS Interaction Patterns (proven in existing tests)

| Control | Event | Pattern |
|---------|-------|---------|
| Text input | `onChange` | `fireEvent.change(input, { target: { value: 'x' } })` |
| PSelect | `onChange/onInput` | `fireEvent(el, new CustomEvent('change', { detail: { value: 'needed' }, bubbles: true }))` |
| PMultiSelect | `update` listener | `fireEvent(el, new CustomEvent('update', { bubbles: true, detail: { value: ['tag'] } }))` |
| Checkbox (blocked) | click | `fireEvent.click(checkbox)` |
| Reset button | click | `fireEvent.click(button)` |

### "Tag persisting after vanishing from task set" — Clarified

`availableTags` is derived from the full `tasks` prop, not `filteredTasks`. The 0-result state occurs when:
1. User selects tag X + another dimension (e.g., text filter) that excludes all tasks with tag X, OR
2. Tasks prop changes (simulated via rerender) removing all tasks that had tag X — filter state `{ tags: ['X'] }` persists in local state → 0 matching tasks.

Both paths should be tested. Path 2 is the stronger integration test.

### Test File Structure

- File: `src/__tests__/KanbanBoard_1256.test.tsx`
- NO `vi.mock('../components/FilterPanel')` — use real component
- NO `vi.mock('../components/ArchivalModal')` — not needed if no archival flow tested
- Render: `<PorscheDesignSystemProvider><MemoryRouter><KanbanBoard .../></MemoryRouter></PorscheDesignSystemProvider>`
- Interaction helpers: query real filter controls inside `#filter-panel`

### Risk Assessment

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| PMultiSelect jsdom limitations | Medium | Use proven `CustomEvent('update')` pattern from #1250 |
| PSelect custom events not firing `onChange` in jsdom | Low | Both `onChange` and `onInput` handlers read from `event.detail.value` — CustomEvent works |
| Controlled component re-render timing | Low | Use `waitFor()` around assertions |
| Text input debounce (300ms for aria-live) | Low | Use `vi.useFakeTimers()` + `vi.advanceTimersByTime(300)` for announcement tests |

## 4. Recommendation

**Confidence: 0.85** — Straightforward integration test using proven patterns. All PDS interaction techniques are validated in existing test files. No architectural changes needed.

**Approach:** Single test file, ~9 test cases mapping 1:1 to AC bullets. Use real FilterPanel, real filterTasks. Interaction via proven DOM event patterns.

Challenge: SKIP — trivial T1 task (standard test file creation), no architectural risk.

## 5. Follow-up Tasks

Task #1256 is already correctly positioned as a `type:test` task in `todo` pipeline stage. The builder needs:
1. The test file (RED phase) — write failing integration tests
2. Verify tests pass against existing implementation (should be GREEN immediately since all components already exist)

Since the implementation is already complete (KanbanBoard.tsx has all filter logic), this is a **GREEN-on-write** integration test — tests should pass immediately after creation. The test-writer should write them as passing tests verifying integrated behavior.

No additional follow-up tasks needed — this is the terminal task in the Phase 5 decomposition.
