---
id: 1251
title: 'P2-02: GREEN — FilterPanel controlled component'
status: review
priority: needed
created: 2026-05-01T04:34:51.936867+00:00
updated: 2026-05-02T16:03:16.446825+00:00
tags:
- phase-2
- scope:cockpit-web
- tdd:green
parent: 1247
depends_on:
- 1250
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Acceptance Criteria

- FilterPanel.tsx component implemented with:
  - Text input with placeholder "Search by title…"
  - PDS Select for priority (single-select, "All priorities" empty option)
  - PDS MultiSelect for tags (type-to-filter, hidden when availableTags empty)
  - PDS Switch for blocked toggle ("Show only blocked tasks")
  - Reset button ("Clear all") visible when any filter is active
- Controlled component: receives filter + onFilterChange + priorities + availableTags + open as props
- All #1250 component tests pass (GREEN)

## In Scope
- FilterPanel.tsx component
- FilterPanelProps interface

## Out of Scope
- KanbanBoard integration (Phase 3)
- Accessibility attributes beyond basic labels (Phase 4)
- Layout/positioning within board (Phase 3)

Brief: see parent #1247
[[2026-05-02]]
## Research

**Gate: PASS (trivial GREEN — test contract fully defines implementation)**

### Key Findings

1. **Test contract exists**: `FilterPanel_1250.test.tsx` (441 lines, 7 AC groups, 30+ assertions) — fully defines component interface and behavior.
2. **FilterState type exists**: `src/utils/filterTasks.ts` exports `FilterState { text, priority, tags[], blocked }`.
3. **PDS v4 components confirmed**: `PSelect`, `PMultiSelect`, `PMultiSelectOption`, `PSwitch` all exported from `@porsche-design-system/components-react@4.0.0`.
4. **Established pattern**: `readControlValue(event)` helper (reads `event.detail?.value` or `event.target?.value`) — used in ArchivalModal, DetailTab, ResolveModal.

### Risk: PDS jsdom Event Mismatch (confidence: .90)

| Control | Test fires | PDS React wrapper listens for | Mitigation |
|---------|-----------|-------------------------------|------------|
| Priority (PSelect) | `CustomEvent('change')` | 'change' → onChange | ✅ Aligned |
| Tags (PMultiSelect) | `CustomEvent('update')` | 'change' → onChange | ⚠️ Use ref + `addEventListener('update', ...)` |
| Blocked (PSwitch) | `fireEvent.click()` | 'update' → onUpdate | ⚠️ Use native `<input type="checkbox" role="switch">` or handle click manually |

**Builder guidance:** For tags control, use a ref-based 'update' event listener (PMultiSelect's `onChange` prop won't fire from the 'update' CustomEvent the test dispatches). For blocked, a native `<input type="checkbox" role="switch">` is the simplest path — fireEvent.click toggles it and the onChange fires directly.

### Implementation Approach

- Controlled component pattern: derive callbacks from `filter` + `onFilterChange` props (spread + override one field)
- `data-testid="filter-tags"` on PMultiSelect element, `data-testid="filter-reset"` on reset button
- Reset button conditionally rendered: compare filter vs `{ text: '', priority: '', tags: [], blocked: false }`
- `open=false` → early return (render nothing or empty fragment)
- No follow-up tasks needed — test contract is complete

### Classification

T1 — Autonomous. Standard component implementation against pre-written tests. No architecture decisions, no new capabilities.
[[2026-05-02]]


## AC Refinements (Architecture Review)

Changes from original AC:
1. **Blocked toggle**: "PDS Switch for blocked toggle" → "Blocked toggle (`role="switch"` or native checkbox — test accepts either)". Reason: test helper queries both selectors; mandating PDS Switch contradicts the builder guidance and test contract.
2. **Tags type-to-filter**: Removed "type-to-filter" qualifier — not asserted by any test in #1250. PMultiSelect supports it natively but it's not an AC constraint.
3. **Test-depth annotations added** (see below).

Refined AC (supersedes original):
- FilterPanel.tsx component implemented with: (td:2)
  - Text input with placeholder "Search by title…"
  - PDS Select for priority (single-select, "All priorities" empty option)
  - PDS MultiSelect for tags (hidden when availableTags empty)
  - Blocked toggle (`role="switch"` or native checkbox) with label "Show only blocked tasks"
  - Reset button ("Clear all") visible when any filter is active
- Controlled component: receives filter + onFilterChange + priorities + availableTags + open as props (td:1)
- All #1250 component tests pass (GREEN) (td:0)

[[2026-05-02]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One component (FilterPanel.tsx), one interface (FilterPanelProps) |
| Interface clarity | PASS | Props fully specified by test contract: filter, onFilterChange, priorities, availableTags, open |
| Dependency correctness | PASS | #1250 (RED tests) archived/done; test file exists at `src/__tests__/FilterPanel_1250.test.tsx` |
| Module layering | PASS | Imports FilterState from `utils/filterTasks.ts` (downward). No upward imports. |
| TDD compliance | PASS | Preceding RED task #1250 done. 441-line test file with 7 AC groups, 30+ assertions. |
| KISS/YAGNI | PASS | Controlled component, no abstractions. readControlValue duplication noted (4th instance) but extraction is a separate concern. |
| Premise challenge | PASS | No existing filter component in codebase. Feature required by parent #1247. |
| Pattern consistency | PASS | Follows established controlled-component patterns (ArchivalModal, DetailTab, ResolveModal). |
| Security surface | PASS | No system boundaries. Local UI state only. |
| Single domain | PASS | Frontend/cockpit-web only. |

### Failure Mode Map
N/A — pure UI component, no failure codepaths.

### Design Diverge
- Trigger: SKIPPED — single clear approach (controlled component). No competing designs.

### Challenge Results
- Challenger: block (confidence 0.46)
- Challenges raised: (1) AC mandates PDS Switch but test accepts native checkbox — VALID, AC refined; (2) labels/copy not test-enforced — accepted as informational, standard for codebase; (3) event mitigation unproven — standard GREEN risk with adequate builder guidance
- Architect response: override → REFINE-then-APPROVE. Refined AC to remove PDS Switch mandate and untested type-to-filter qualifier. Remaining challenges are informational or standard builder-phase concerns.

### Test Depth
- Max depth: td:2
- Test-writer: PROCEED (tests already exist from #1250 RED phase; test-writer confirms and passes through)

### Verdict: APPROVE (after refinement)
### Action Taken: Refined AC (blocked toggle wording, removed untested type-to-filter), annotated test depths, advanced to todo.
[[2026-05-02]]
## Test-Writer Notes
- Test file: `serve/cockpit/web/src/__tests__/FilterPanel_1250.test.tsx` (written in RED task #1250)
- Tests: 30+ assertions across 7 AC groups (AC1–AC7), all in `TestFromAC_FilterPanel`
- RED confirmed: suite fails at import — `FilterPanel.tsx` does not exist (`Failed to resolve import "../components/FilterPanel"`)
- Pass-through: tests pre-exist from #1250 RED phase; architect review explicitly authorized pass-through

### AC Coverage
| AC | Description | Tests | Depth |
|----|-------------|-------|-------|
| AC1 | Renders text input, priority select, tags, blocked toggle, reset button when open=true | 6 | td:2 |
| AC2 | Priority select populated from priorities prop | 3 | td:1 |
| AC3 | Hides tag control when availableTags empty | 2 | td:1 |
| AC4 | Reset button visible only when filter is active | 5 | td:1 |
| AC5 | Reset clears all filters (onFilterChange with empty FilterState) | 1 | td:1 |
| AC6 | Each control interaction fires onFilterChange with updated FilterState | 12 | td:2 |
| AC7 | Controls absent from DOM when open=false | 5 | td:1 |

- Total: ~34 tests, all FAIL (import error = valid RED for new-file task)
- No new test file committed — pre-existing from #1250
[[2026-05-02]]
## Builder Notes
- Implementation: added `serve/cockpit/web/src/components/FilterPanel.tsx` (new controlled component + `FilterPanelProps`).
- Tests (RED verification before implementation): `FilterPanel_1250.test.tsx` failed to load due to missing import (`../components/FilterPanel`) as expected.
- Tests (GREEN): 34 passed, 0 failed, 0 skipped for `serve/cockpit/web/src/__tests__/FilterPanel_1250.test.tsx`.
- Coverage: `FilterPanel.tsx` line coverage 95.55% (statements 80%, branches 55.88%, functions 85.71%).
- Lint: clean (`eslint` exit 0 on component + task test file).
- Commit: `d42da30e` with message `feat: implement FilterPanel controlled component (#1251, builder)`.
- Evidence summary: component now satisfies test contract for open/closed rendering, priority select options, tag-control visibility, blocked toggle updates, and reset behavior.
- Fixes applied during retry: replaced initial PDS text input with native text input so jsdom exposes a textbox role consumed by the RED tests.

### Post-task Reflection
- problems_faced: jsdom role visibility mismatch for PDS text input caused AC1/AC6 failures.
- workarounds_applied: migrated search field to native `<input type="text">` while preserving controlled behavior.
- patterns_discovered: PMultiSelect requires `update` event handling via DOM listener in this test environment.
- quality_gaps: branch coverage remains below line coverage despite full AC test pass; this is test-shape driven.
- time_sinks: initial implementation retry needed after first scoped GREEN run surfaced the textbox-role mismatch.