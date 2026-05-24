---
id: 1821
title: Repair kanban board split root tests
status: done
priority: important
created: 2026-05-24T09:23:21+02:00
updated: 2026-05-24T10:10:20+02:00
tags:
  - scope:cockpit-web
  - scope:kanban-engine
  - test-failure
  - discussion
parent: 1814
depends_on:
  - 1814
ac:
  - The two `tests/test_kanban_board_split.py` failures are checked against the current frontend file layout.
  - Static source assertions are updated only if they still protect current architecture.
  - Any frontend-adjacent change has the appropriate Cockpit verification path.
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Observation
The #1814 root glob has two failures in `tests/test_kanban_board_split.py`, covering `Card.tsx` priority colors and `Column.tsx` memo wrapper assertions.

## Boundary
Do not change Cockpit frontend structure from this root-glob triage task without explicit approval.

## Decision
User approved inspecting UI/context before repairing #1821. A 1024px Cockpit board screenshot showed the board rendering correctly; the failing assertions did not map to a visible board break.

The static tests were stale:
- Newer card-signal work intentionally removed `PRIORITY_COLORS`; Card now keeps priority available through `data-priority`, ARIA text, and rail classes.
- `Column.tsx` uses `useCallback` for scroll-cue/event/effect coordination, not as a render memo wrapper. The static test now forbids `React.memo` and `useMemo` render wrappers while allowing behavior-motivated callbacks.

Created follow-up #1822 for the observed 1024px horizontal-overflow usability question. No Cockpit product code was changed in #1821.

## Verification
- `uv run ruff check tests/test_kanban_board_split.py` — passed.
- `uv run pytest tests/test_kanban_board_split.py -q --tb=short` — 8 passed.
- `npm test -- --run src/__tests__/Column.test.tsx src/__tests__/Card.visual-treatment.test.tsx src/__tests__/CardSignalModel.test.tsx src/__tests__/KanbanBoard.test.tsx` — 4 files passed, 102 tests passed.
- `uv run pytest tests/test_engine_*.py tests/test_kanban_*.py -q --tb=no` — 540 passed.

## Remaining
The root engine/Kanban glob is green after #1821.