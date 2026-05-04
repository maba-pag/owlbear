# Filter Accessibility Tests — Research

> **Owning task:** #1254 — P4-01: RED — Filter accessibility tests
> **Date:** 2026-05-03 **Status:** Complete

## 1. Context and Question

Task #1254 requires writing failing (RED) tests for the filter accessibility contract. The KanbanBoard toggle button and FilterPanel currently have zero ARIA attributes — no `aria-expanded`, `aria-controls`, `role`, `aria-label`, `aria-live`, or focus management.

Key questions: (a) What WAI-ARIA patterns apply? (b) Can all AC items be tested with existing infrastructure (Vitest + Testing Library + jsdom)? (c) How to test the "user-initiated only" and "debounce" requirements for aria-live?

## 2. Sources Studied

| Source | Relevance | Score |
|--------|-----------|-------|
| WAI-ARIA APG Disclosure (Show/Hide) pattern | Toggle + panel semantics | 0.95 |
| Existing test `usePollingFetch_1227.test.ts` | Fake timer pattern for debounce | 0.90 |
| Existing `FilterPanel.tsx` (L1-136) | Current state — no a11y attrs | 0.95 |
| Existing `KanbanBoard.tsx` (L220-250) | Toggle button — no aria-expanded | 0.95 |
| Existing `ArchivalModal.tsx` (L221) | Focus trap pattern (ref + autoFocus) | 0.80 |

## 3. Analysis

### Testability Matrix

| AC Item | Testing Mechanism | Feasibility |
|---------|-------------------|-------------|
| aria-expanded on toggle | `getAttribute('aria-expanded')` | Trivial |
| aria-controls on toggle | `getAttribute('aria-controls')` | Trivial |
| FilterPanel id/role/aria-label | `getAttribute()` queries | Trivial |
| aria-live="polite" on result count | `getAttribute('aria-live')` | Trivial |
| aria-live user-initiated only | Re-render with new tasks, assert region text unchanged | Medium |
| aria-live debounce 300ms | `vi.useFakeTimers()` + `advanceTimersByTime(299/300)` | Medium |
| Focus → first control on expand | `document.activeElement` check | Easy |
| Focus → toggle on collapse | `document.activeElement` check | Easy |
| Explicit accessible labels | `getByLabelText()` / aria-label assertions | Easy |

### Key Design Decisions for Tests

1. **User-initiated vs polling**: Test renders KanbanBoard with tasks prop. After filter change, aria-live region updates. Then re-render with different tasks (simulating polling) — region text must NOT change without a filter state change.

2. **Debounce**: Use fake timers. Type text → advance 299ms → region unchanged → advance 1ms → region updated.

3. **Focus management**: In jsdom, `element.focus()` works and `document.activeElement` tracks it. The test can check `document.activeElement === textInput` after expanding panel.

4. **Accessible labels**: FilterPanel text input has only `placeholder` (not a label). Priority select has no label. Tags control has no label. Tests should assert `getByLabelText()` or `aria-label` attribute existence.

## 4. Recommendation

**Proceed directly (T1 — autonomous).** Confidence: 0.92

All AC items are testable with existing infrastructure. No architectural decisions needed. The test file follows established patterns from `FilterPanel_1250.test.tsx` and `KanbanBoard_1252.test.tsx`.

Challenge: skipped — trivial RED-phase task with established ARIA patterns, no design alternatives to evaluate.

Recommended test file: `src/__tests__/FilterAccessibility_1254.test.tsx`

## 5. Follow-up Tasks

None required — #1254 itself is the follow-up from parent #1247. After RED tests pass review, the GREEN implementation task handles adding the accessibility attributes.
