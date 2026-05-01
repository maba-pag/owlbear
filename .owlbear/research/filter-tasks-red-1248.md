# filterTasks RED Phase — Test Strategy

> **Owning task:** #1248 — P1-01: RED — filterTasks unit tests
> **Date:** 2026-05-01 **Status:** Complete

## 1. Context and Question

Task #1248 requires writing failing Vitest tests for a `filterTasks` pure function and exporting a `FilterState` type. Research question: What test structure, file placement, and type shape best fit the existing cockpit frontend patterns?

## 2. Sources Studied

| Source | Relevance | Notes |
|--------|-----------|-------|
| `src/hooks/useBoard.ts` (Task interface) | 1.0 | Defines all fields referenced in AC (title, priority, tags, blocked) |
| `src/__tests__/optimistic.test.ts` | 0.9 | Pure-function test pattern — no rendering, globals enabled |
| `vite.config.ts` (test block) | 0.8 | Confirms `globals: true`, jsdom, include pattern |
| `src/__tests__/` directory listing | 0.7 | Naming conventions: `{feature}.test.ts`, `{feature}_{taskId}.test.ts` |

## 3. Analysis

### FilterState Type Shape (derived from AC)

```typescript
interface FilterState {
  text: string        // case-insensitive substring match on title; '' = pass all
  priority: string    // exact match on task.priority; '' = pass all
  tags: string[]      // AND semantics — task must have ALL; [] = pass all
  blocked: boolean    // true = only blocked pass; false = all pass
}
```

### File Placement

| Option | Path | Rationale |
|--------|------|-----------|
| A (recommended) | `src/__tests__/filterTasks_1248.test.ts` | Follows `{feature}_{taskId}` convention seen in codebase |
| B | `src/__tests__/filterTasks.test.ts` | Simpler; may conflict with GREEN phase additions |

Recommendation: **Option A** (confidence: 0.85). Task-ID suffix is established pattern for task-owned test files.

### Implementation module path

The test will import from `../utils/filterTasks`. This path doesn't exist yet (RED phase), which is correct — tests must fail on import.

### Test Structure (from AC)

| Dimension | Test Count | Approach |
|-----------|-----------|----------|
| Text (case-insensitive substring) | 3 | Match, no-match, empty-string pass-all |
| Priority (exact match) | 3 | Match, no-match, empty-string pass-all |
| Tags (AND semantics) | 4 | All present, subset missing, empty-filter pass-all, empty-task-tags |
| Blocked (boolean gate) | 2 | true=only-blocked, false=all-pass |
| AND combination | 2 | Multiple active dimensions; all-pass = no filters |
| Edge cases | 2 | undefined fields, empty tags array |

Total: ~16 test cases.

## 4. Recommendation

Proceed with implementation (confidence: 0.85). The pattern is well-established in this codebase. No architectural decisions required.

Challenge: FALLBACK — trivial T1 task, no competing options to challenge.

## 5. Follow-up Tasks

No additional research tasks needed. Task #1249 (GREEN phase) already exists as the natural successor.
