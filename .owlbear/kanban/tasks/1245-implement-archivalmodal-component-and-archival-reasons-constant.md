---
id: 1245
title: 'Implement: ArchivalModal component and ARCHIVAL_REASONS constant'
status: review
priority: needed
created: 2026-05-01T03:08:07.623554+00:00
updated: 2026-05-01T15:49:05.132411+00:00
tags:
- scope:frontend
parent: 1238
depends_on:
- 1241
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Acceptance Criteria

- `ARCHIVAL_REASONS` constant defined with order: `completed → dropped → wontfix → deprecated → duplicate`
- `ArchivalModal` component created at `components/ArchivalModal.tsx`
- All state, rendering, a11y, submission, and error-handling behaviours specified in brief F2 are implemented:
  - `role="dialog"`, `aria-modal="true"`, `aria-labelledby` pointing to visible title
  - Focus on reason dropdown at open; focus trap for Tab/Shift+Tab; Escape closes without move
  - `completed` option hidden when `taskStatus !== "done"`
  - Refs field visible only for `deprecated` and `duplicate`; refs state cleared on reason change
  - Submit disabled when no reason, when refs required and empty, or when `isSubmitting`
  - Hint text displayed below refs field when visible: "Required — enter at least one task ID"
  - Client-side NaN guard before firing POST; inline error shown on validation failure
  - 422: stays open, renders `error.detail` verbatim; 409: stays open, stale error; success: close and refresh
- All tests from #1241 pass

## In Scope

- `components/ArchivalModal.tsx` (new file)
- `ARCHIVAL_REASONS` constant (in `KanbanBoard.tsx` or a shared constants file)

## Out of Scope

- `handleTransitionClick` intercept (F3 task #1246)
- Backend changes

## Brief reference

Brief: `.owlbear/briefs/draft-archival-ux/brief.md` — Frontend Changes F1, F2
[[2026-05-01]]
## Test-Writer Notes
- Test file: serve/cockpit/web/src/__tests__/ArchivalModal_1245.test.tsx
- Classes: TestFromAC_ArchivalModal_RefsPlaceholder
- Tests per category: happy 2, edge 0, error 0, boundary 1
- Total: 3 tests, all FAIL
- lint (eslint): clean

**Coverage gap addressed:**
`ArchivalModal_1241.test.tsx` (46 tests, all green) covers every AC sub-bullet already, since the component was pre-built. The only gap from brief F2 not in 1241: the refs `<input>` must have `placeholder="e.g., 1230, 1229"`. The current component omits this attribute entirely. All 3 new tests confirm RED via `expected null to be 'e.g., 1230, 1229'`.

**AC coverage:**
| AC line | Covered by |
|---|---|
| ARCHIVAL_REASONS constant order | ArchivalModal_1241 |
| Component created at components/ArchivalModal.tsx | ArchivalModal_1241 (import) |
| role/aria-modal/aria-labelledby | ArchivalModal_1241 AC2 |
| Focus on open / focus trap / Escape | ArchivalModal_1241 AC3/15/16 |
| completed hidden / refs visibility / refs clear | ArchivalModal_1241 AC4/5/6 |
| Submit disabled states (3 conditions) | ArchivalModal_1241 AC7/8/9 |
| Hint text / NaN guard / 422/409/success | ArchivalModal_1241 AC10/11/12/13/14 |
| refs input placeholder "e.g., 1230, 1229" | **ArchivalModal_1245.test.tsx** (new, RED) |

Commit: 0c375f91

[[2026-05-01]]
## Builder Notes
- Files changed: `serve/cockpit/web/src/components/ArchivalModal.tsx`
- Fix applied: added `placeholder="e.g., 1230, 1229"` to the refs `<input>` shown for `deprecated`/`duplicate` reasons.
- Scope discipline: single-line surgical fix for the known AC gap from #1241/#1245; no unrelated edits.

### Test Results
- Targeted frontend tests (Vitest): 49 passed, 0 failed
  - `serve/cockpit/web/src/__tests__/ArchivalModal_1245.test.tsx` (3 tests)
  - `serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx` (46 tests)
- Evidence: prior RED reproduced (`expected null/'' to be 'e.g., 1230, 1229'`), then GREEN after fix.

### Lint Status
- ESLint (scoped to changed files): clean, 0 violations.
- Ruff: not applicable for this TypeScript frontend change.

### Coverage
- Frontend coverage not measured in quality-runner scoped TS flow for this task; correctness gate satisfied via full relevant Vitest suite pass.

### Evidence Summary
- AC gap closed: refs input now includes exact placeholder string required by brief F2 and enforced by #1245 tests.
- Regression safety: #1241 archival modal test suite remains green after change.