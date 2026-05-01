---
id: 1250
title: 'P2-01: RED — FilterPanel component tests'
status: todo
priority: needed
created: 2026-05-01T04:34:48.876923+00:00
updated: 2026-05-01T21:24:50.288463+00:00
tags:
- phase-2
- scope:cockpit-web
- tdd:red
parent: 1247
depends_on:
- 1249
blocked: false
block_reason:
claimed_at: 2026-05-01T21:24:50.288463+00:00
archival_reason:
archival_refs: []
---

## Acceptance Criteria

- Vitest + Testing Library component test suite for FilterPanel:
  - Renders text input, priority select, tags multi-select, blocked switch, reset button when open (td:2)
  - Priority select populated from `priorities` prop (td:1)
  - Hides tag control entirely when availableTags is empty (td:1)
  - Reset button visible only when at least one filter is active (non-empty text, priority set, tags selected, or blocked enabled) (td:1)
  - Reset button clears all filter values (calls onFilterChange with empty FilterState) (td:1)
  - Each control interaction fires onFilterChange with updated FilterState (td:2)
  - Does not render controls when open={false} — controls absent from DOM (td:1)
- All tests fail (RED) — no FilterPanel component exists yet (td:0)

## Component Props Contract (from brief)

```ts
interface FilterPanelProps {
  filter: FilterState
  onFilterChange: (filter: FilterState) => void
  priorities: string[]
  availableTags: string[]
  open: boolean
}
```

Note: `activeCount` is computed in the parent — FilterPanel derives reset-button visibility from whether `filter` differs from the empty state.

## In Scope
- Component test file for FilterPanel (`src/__tests__/FilterPanel_1250.test.tsx`)
- Test fixtures using FilterState type from #1249
- Selector strategy: prefer role/label queries (Testing Library idiom); data-testid only as last resort

## Out of Scope
- FilterPanel implementation (next task #1251)
- PDS component internals (mock or shallow-render PDS multi-select if needed)
- Accessibility attributes (Phase 4)

Brief: see parent #1247
[[2026-05-01]]
## Research

**Key findings:** FilterState type confirmed in `src/utils/filterTasks.ts` (text, priority, tags[], blocked). FilterPanel.tsx does not exist — RED valid. Component interface inferred from AC: open, filterState, onFilterChange, availableTags, activeCount. ~10 test cases covering all 6 AC lines.

**Test strategy:** PDS provider wrapper + fireEvent.change + vi.fn() callback assertions. data-testid selectors. No module mocks needed — pure presentational component.

**File placement:** `src/__tests__/FilterPanel_1250.test.tsx`

**Tier:** T1 — no decisions needed; follows established patterns exactly.

**Doc:** `.owlbear/research/filter-panel-red-1250.md`

**Follow-ups:** None — #1251 (GREEN phase) already exists.
[[2026-05-01]]
## Architecture Review

### Verdict: APPROVE (after refinement)

Refined AC to align with brief's `FilterPanelProps` contract. Key changes:
- Added `priorities: string[]` prop (brief-specified, needed for select options)
- Removed `activeCount` as implicit prop — reset visibility derived from filter state
- Resolved closed-state ambiguity: controls absent from DOM (not hidden)
- Added selector strategy guidance (role/label queries preferred)
- Added td annotations per AC line

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One component's test suite |
| Interface clarity | PASS | Props contract explicit from brief; each AC line maps to a testable assertion |
| Dependency correctness | PASS | #1249 archived/done — FilterState type exists in filterTasks.ts |
| Module layering | PASS | Pure presentational tests; no upward imports |
| TDD compliance | PASS | This IS the RED phase; tagged tdd:red |
| KISS/YAGNI | PASS | Single test file, minimal scope |
| Premise challenge | PASS | FilterPanel is brief-specified deliverable |
| Pattern consistency | PASS | Matches ArchivalModal test pattern (PDS provider, fireEvent, vi.fn) |
| Security surface | N/A | No system boundary — UI component tests |
| Single domain | PASS | scope:cockpit-web only |

### Challenger Results
- Confidence: 0.46 → reconsider
- Key concerns addressed: (1) props contract aligned to brief, (2) priorities prop added, (3) activeCount removed as prop, (4) closed-state resolved, (5) selector strategy specified
- Tags multi-select risk acknowledged in Out of Scope ("mock or shallow-render PDS if needed") — brief also flags fallback path

### Test-depth Summary
- td:2 lines: 2 (render-all-controls, control-interactions)
- td:1 lines: 5
- td:0 lines: 1 (meta RED requirement)
- Test-writer: processes normally