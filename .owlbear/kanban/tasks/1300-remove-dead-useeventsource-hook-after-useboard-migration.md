---
id: 1300
title: Remove dead useEventSource hook after useBoard migration
status: in-progress
priority: someday
created: 2026-05-02T19:48:32.676272+00:00
updated: 2026-05-03T13:53:37.679354+00:00
tags:
- cockpit
- frontend
parent:
depends_on:
- 1277
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

After #1277 refactors useBoard to use EventSourceProvider context, hooks/useEventSource.ts has zero production imports. Delete the hook file and its test files (useEventSource_1260.test.ts, useEventSource_1263.test.ts). Verify no other production code imports it first.
[[2026-05-03]]
## Research

**Verified:** `hooks/useEventSource.ts` has zero production imports. Only consumers are its own test files (`useEventSource_1260.test.ts`, `useEventSource_1263.test.ts`). `useBoard.ts` was migrated to `useSSEEvent` from `EventSourceProvider` (task #1277, archived). Task #1278 (pending ActivityTab work) also uses the new pattern.

**Files to delete (3):**
1. `serve/cockpit/web/src/hooks/useEventSource.ts`
2. `serve/cockpit/web/src/__tests__/useEventSource_1260.test.ts`
3. `serve/cockpit/web/src/__tests__/useEventSource_1263.test.ts`

**Risk:** None — zero production consumers confirmed via exhaustive grep.
**Confidence:** 0.95
**No follow-up tasks needed** — task is atomic and ready for implementation.
[[2026-05-03]]

## Acceptance Criteria

- [ ] `serve/cockpit/web/src/hooks/useEventSource.ts` deleted (td:0)
- [ ] `serve/cockpit/web/src/__tests__/useEventSource_1260.test.ts` deleted (td:0)
- [ ] `serve/cockpit/web/src/__tests__/useEventSource_1263.test.ts` deleted (td:0)
- [ ] Existing frontend test suite passes (`npm test`) with no broken imports (td:0)

## Architecture Review

**Verdict:** APPROVE

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Delete one dead hook + its tests |
| Interface clarity | PASS | 3 explicit file deletions + suite-pass gate |
| Dependency correctness | PASS | #1277 archived (completed); codebase shows migration done |
| Module layering | PASS | Deletion only, no new imports |
| TDD compliance | PASS | All td:0 — mechanical removal |
| KISS/YAGNI | PASS | Minimal scope, no extras |
| Premise challenge | PASS | Confirmed dead: grep shows zero production imports |
| Pattern consistency | PASS | Standard dead-code cleanup |
| Security surface | PASS | No new boundaries |
| Single domain | PASS | Frontend only |

### Challenge
Challenge: SKIP — all AC lines td:0.

### Test-writer: SKIP
All AC lines are td:0 (mechanical file deletion). No new tests required.
[[2026-05-03]]
Architecture review complete. All AC lines td:0 (mechanical deletion). Zero production imports confirmed via grep. Dependency #1277 archived. Test-writer: SKIP.
[[2026-05-03]]
## Test-Writer Notes
- All AC lines are (td:0) — test-writer skipped.
- Passing through to builder.