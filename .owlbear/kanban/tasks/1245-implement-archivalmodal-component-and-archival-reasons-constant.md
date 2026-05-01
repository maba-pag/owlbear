---
id: 1245
title: 'Implement: ArchivalModal component and ARCHIVAL_REASONS constant'
status: todo
priority: needed
created: 2026-05-01T03:08:07.623554+00:00
updated: 2026-05-01T22:06:11.311360+00:00
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

- `ARCHIVAL_REASONS` constant defined with order: `completed → dropped → wontfix → deprecated → duplicate` (td:0)
- `ArchivalModal` component created at `components/ArchivalModal.tsx` (td:0)
- Zero TypeScript compile errors in `ArchivalModal.tsx` — resolve PDS type incompatibilities: `readControlValue` event param, `PSelect` `onInput`, `PInputText` missing `name`, `PButton` variant (td:1)
- All state, rendering, a11y, submission, and error-handling behaviours specified in brief F2 are implemented: (td:2)
  - `role="dialog"`, `aria-modal="true"`, `aria-labelledby` pointing to visible title
  - Focus on reason dropdown at open; focus trap for Tab/Shift+Tab; Escape closes without move
  - `completed` option hidden when `taskStatus !== "done"`
  - Refs field visible only for `deprecated` and `duplicate`; refs state cleared on reason change
  - Submit disabled when no reason, when refs required and empty, or when `isSubmitting`
  - Hint text displayed below refs field when visible: "Required — enter at least one task ID" (em-dash `—`, not hyphen) per brief F2 line 130
  - Placeholder `e.g., 1230, 1229` on refs input when visible
  - Client-side NaN guard before firing POST; inline error shown on validation failure
  - 422: stays open, renders `error.detail` verbatim; 409: stays open, stale error; success: close and refresh
- Test selectors in `ArchivalModal_1241.test.tsx` and `ArchivalModal_1245.test.tsx` reconciled with PDS component contract: query `p-select`/`p-input-text` (or their rendered shadow DOM) instead of raw `select`/`input[type="text"]`; query `p-heading` instead of raw `h3` (td:1)
- All tests in `ArchivalModal_1241.test.tsx` and `ArchivalModal_1245.test.tsx` pass (td:0)
- `PdsMigration_1230.test.tsx` ArchivalModal assertions continue to pass (regression gate) (td:0)

## In Scope

- `serve/cockpit/web/src/components/ArchivalModal.tsx` (fix TS errors, hint text em-dash)
- `serve/cockpit/web/src/__tests__/ArchivalModal_1241.test.tsx` (selector reconciliation with PDS contract)
- `serve/cockpit/web/src/__tests__/ArchivalModal_1245.test.tsx` (selector reconciliation with PDS contract)

## Out of Scope

- `handleTransitionClick` intercept (F3 task #1246)
- Backend changes
- PdsMigration_1230.test.tsx itself (already passing — regression gate only)

## Brief reference

Brief: `.owlbear/briefs/draft-archival-ux/brief.md` — Frontend Changes F1, F2

## Builder Guidance

This task has been through 3+ review cycles. The implementation is largely correct but has three defect categories:

1. **TS compile errors (6 active):** PDS wrapper types are stricter than the `readControlValue` helper expects. Fix the event parameter type to accept `CustomEvent<unknown>` or use explicit casts. `PInputText` requires a `name` prop. `PButton` no longer accepts `variant="tertiary"` — check current PDS API for the cancel button variant.

2. **Hint text mismatch:** Line 266 renders `"Required - enter at least one task ID"` (hyphen). Brief F2 requires em-dash `—`. Single character fix.

3. **Test selector reconciliation:** Both test files use `querySelector('select')` and `querySelector('input[type="text"]')` which return null because the component renders PDS custom elements (`<p-select>`, `<p-input-text>`). Update test helpers to query PDS elements. Reference `PdsMigration_1230.test.tsx` lines 308-519 for the expected selector patterns.

**Prior cycle evidence (preserved below) documents the full history.**
[[2026-05-01]]
## Architecture Review

### Verdict: APPROVE (after REFINE)

### AC Assessment
| AC Line | Assessment | Action |
|---------|-----------|--------|
| ARCHIVAL_REASONS order | Verified in source at line 10-16 | Retained, downgraded to td:0 (already proven) |
| Component file exists | Verified | Retained td:0 |
| F2 behavior bundle | Source correct but 6 TS compile errors prevent clean build | Added explicit "zero TS errors" AC line (td:1); made hint text em-dash requirement explicit |
| Placeholder | Present at line 255, tests exist | Made explicit AC sub-bullet |
| Tests pass (old AC) | 38/49 FAIL due to stale raw-DOM selectors post-PDS migration | Expanded: added selector reconciliation AC (td:1), added PdsMigration_1230 regression gate |

### Architecture Notes
- Component is fully PDS-migrated (PSelect, PInputText, PButton, PHeading) — correct pattern
- Tests written pre-migration still use `querySelector('select')`, `querySelector('input[type="text"]')` which return null
- PdsMigration_1230.test.tsx explicitly asserts no raw elements in ArchivalModal — authoritative contract
- TS errors are PDS wrapper type strictness: event param typing, missing `name` prop, removed `tertiary` variant

### Scope Expansion Rationale
Added both test files to In Scope. Without reconciling selectors, the task literally cannot pass its own regression gate. This is the minimum scope needed to break the 3-cycle review loop.

### Challenger Results
- Confidence: 0.22, recommendation: block
- Override: challenger treated this as needing research, but the diagnosis is complete. All defects are enumerated, mechanical to fix, and well-scoped. No ambiguity remains.
- Addressed: (1) TS errors acknowledged as defects not "functional correctness"; (2) em-dash made explicit; (3) scope expansion is intentional to break the loop; (4) PdsMigration_1230 added as regression gate per challenger's blind spot #4.

### Dependency Check
- #1241 (test task): archived/done — selector reconciliation inherits this work
- Parent #1238: archival UX feature — this is F1+F2 implementation slice

### Test-Depth Summary
- td:0 lines: 4 (file exists, constant, suite gates)
- td:1 lines: 2 (TS errors, selector reconciliation)
- td:2 lines: 1 (F2 behavior bundle)
- Test-writer: process normally — existing tests need selector updates, not new test logic