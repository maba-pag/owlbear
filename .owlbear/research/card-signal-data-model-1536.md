# Card Signal Data Model — Test Design Research

> **Owning task:** #1536 — P1-03: test — card signal data model
> **Date:** 2026-05-13 **Status:** Complete

## 1. Context and Question

Task #1536 requires Vitest tests for a `computeSignal()` pure function that maps task operational state + pending DR cross-reference into a single display signal. The signal drives left-border color on board cards (brief D10, D14).

**Research questions:**
1. What input data is available and what type extensions are needed?
2. What function signature best fits the AC and codebase patterns?
3. Where should the function and tests live?
4. What edge cases exist beyond the AC?

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| S1 | `serve/cockpit/web/src/hooks/useBoard.ts` L18-28 | Codebase | 1.0 — current `Task` type (no `dep_status`) |
| S2 | `serve/cockpit/web/src/api/tasks.ts` L4-20 | Codebase | 0.9 — `TaskDetail` has `dep_status` |
| S3 | `serve/kanban/src/owlbear_kanban/models.py` L497-527 | Codebase | 1.0 — `TaskSummary` serves `dep_status` to API |
| S4 | `serve/cockpit/web/src/hooks/usePendingDRs.ts` | Codebase | 1.0 — DR hook returns `PendingDR[]` with `task_id` |
| S5 | `serve/cockpit/web/src/__tests__/filterTasks.test.ts` | Codebase | 0.9 — pure-function test pattern (fixture factory) |
| S6 | `serve/cockpit/web/src/utils/filterTasks.ts` | Codebase | 0.8 — existing utils module pattern |
| S7 | `.owlbear/briefs/draft-board-visual-design/brief.md` | Brief | 1.0 — signal precedence table (D10, D14) |

## 3. Analysis

### 3.1 Type Gap

The board-level `Task` interface (S1) lacks `dep_status`. The backend `TaskSummary` (S3) already serves it via `ListTasksResponse`. The frontend `TaskDetail` (S2) has it. The board `Task` type needs `dep_status: string | null` added — this is a sibling implementation task (#1544) concern, but the test must import a type that includes it.

**Test approach:** The test file defines a local `SignalInput` type (or extends `Task` with `dep_status`) so tests are self-contained and don't depend on the type extension happening first. Builder for #1544 adds `dep_status` to `Task` and aligns the import.

### 3.2 Function Signature

From AC-1: `computeSignal(task, pendingDRIds)`.

| Parameter | Type | Rationale |
|-----------|------|-----------|
| `task` | `{ id: number; blocked: boolean; claimed: boolean; dep_status: string \| null }` | Minimal fields needed for signal computation |
| `pendingDRIds` | `Set<number>` | O(1) lookup; `usePendingDRs` returns `PendingDR[]` — caller converts to Set |

| Return | Type | Values |
|--------|------|--------|
| signal | `CardSignal` (string union) | `"dr-pending"` \| `"blocked"` \| `"claimed"` \| `"deps-unmet"` \| `"ready"` |

### 3.3 Precedence Chain (D14)

```
dr-pending (1) > blocked (2) > claimed (3) > deps-unmet (4) > ready (5)
```

Higher-precedence conditions shadow lower ones. A task that is both blocked AND has a pending DR shows `"dr-pending"`.

### 3.4 File Placement

| Artifact | Path | Pattern source |
|----------|------|----------------|
| Function | `src/utils/computeSignal.ts` | Follows `filterTasks.ts` (S6) |
| Test | `src/__tests__/computeSignal.test.ts` | Follows `filterTasks.test.ts` (S5) |
| Type export | `src/utils/computeSignal.ts` | `CardSignal` union type co-located |

### 3.5 Edge Cases Beyond AC

| Case | Input | Expected | AC |
|------|-------|----------|-----|
| All flags true + DR pending | blocked=T, claimed=T, dep_status="blocked", in DR set | `dr-pending` | AC-2 |
| Blocked + claimed (no DR) | blocked=T, claimed=T | `blocked` | AC-2 |
| Only claimed | claimed=T | `claimed` | AC-2 |
| dep_status=null (no deps) | dep_status=null | `ready` | AC-3 |
| dep_status="ready" | dep_status="ready" | `ready` | AC-3 |
| Empty DR set | empty Set | `ready` (if no other flags) | AC-1 |

### 3.6 Test Structure

Following the `filterTasks.test.ts` pattern (S5):

```
describe('TestFromAC_ComputeSignal')
  describe('AC-1: DR pending signal')
    - returns dr-pending when task ID in pendingDRIds
    - returns ready when task ID not in pendingDRIds (no other flags)
  describe('AC-2: precedence chain')
    - dr-pending beats blocked
    - blocked beats claimed
    - claimed beats deps-unmet
    - deps-unmet beats ready
    - all flags active → dr-pending (highest wins)
  describe('AC-3: dep_status consumption')
    - dep_status "blocked" → deps-unmet
    - dep_status null → ready
    - dep_status "ready" → ready
```

Estimated test count: 10-12 cases. Pure function, no mocks needed.

## 4. Recommendation

**Confidence: 0.90** — Straightforward pure-function test design. Well-established patterns in codebase (filterTasks). No architectural risk.

Recommended approach:
1. Test file at `src/__tests__/computeSignal.test.ts`
2. Fixture factory `makeTask()` returning minimal signal-relevant fields
3. `CardSignal` type and `computeSignal` function stub in `src/utils/computeSignal.ts`
4. Tests import from `../utils/computeSignal`

**Challenge: SKIP** — Trivial pure-function test design. No competing options, no architecture trade-offs. Confidence threshold (.85+) exceeded.

## 5. Follow-up Tasks

No additional follow-up tasks needed. The existing decomposition (#1536 test → #1544 impl) is correctly structured. The builder for #1536 writes the test file; the builder for #1544 writes the implementation and extends the `Task` type.

**Test-writer note for builder:** The test must include a stub file (`src/utils/computeSignal.ts`) exporting the `computeSignal` function and `CardSignal` type with minimal signatures so imports resolve. The stub returns a placeholder to produce RED (assertion-failure) test results.
