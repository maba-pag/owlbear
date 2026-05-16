# Research: Formatting Utility Tests

> **Owning task:** #1598 — P1-04: Tests — formatting utilities
> **Date:** 2026-05-16 **Status:** Complete

## 1. Context and Question

Task #1598 is the TDD RED phase for formatting utilities (`utils/format.ts`). The brief (parent #1590, data stance) specifies null-safe formatters with a strict canonical/display partition (C8). This research determines: what functions to test, their signatures, and how to verify AC2 (no formatter output in mutation paths).

**Task scope:** relative time, priority label, status label, signal description.
**Out of scope:** implementation (#1604), `formatDuration` (session-specific), `formatSessionState`.

## 2. Sources Studied

| Source | Relevance | What was taken |
|--------|-----------|----------------|
| Brief data stance (`stances/data.md`) | 0.95 | Function signatures, C8 partition rule, null-safety requirements |
| Brief synthesis (`synthesis.md`) | 0.90 | C7 (config-driven enums), C8 (canonical/display partition) constraints |
| `computeSignal.ts` + test | 0.85 | Test structure pattern, existing signal types |
| Card.tsx, Column.tsx, DecisionViewport.tsx | 0.80 | Existing inline formatters to consolidate |
| `api/tasks.ts` — MoveRequest, EditRequest, ReleaseRequest | 0.90 | Mutation payloads (canonical fields) |
| `tasks_1501.test.ts`, `decisions_1502.test.ts` | 0.75 | Existing payload-level assertions |
| Mutation components: KanbanBoard, ArchivalModal, ResolveModal, DetailTab, TaskFieldsEditor | 0.85 | Full mutation call graph for AC2 |

## 3. Analysis

### 3.1 Formatter Scope — What to Test

| Function | Signature | Null/undefined fallback | Notes |
|----------|-----------|------------------------|-------|
| `formatRelativeTime` | `(iso: string \| null \| undefined) → string` | `"—"` | Replaces inline `formatUpdatedAge`, `formatAge` in 3 files |
| `formatPriority` | `(p: string \| null \| undefined) → string` | `"—"` | Title-case display; config-driven — unknown values render raw |
| `formatStatus` | `(status: string \| null \| undefined) → string` | `"—"` | Replaces inline `toDisplayStatus` in Column.tsx; dash→space, title-case |
| `formatSignalDescription` | `(signal: CardSignal \| null \| undefined) → string` | `"Unknown"` | Maps signal enum to human label |

### 3.2 AC2 — Canonical/Display Partition Testing

**Challenger pushback (confidence in original: 0.24):** The initially proposed static import-scan of API files + hooks was insufficient. Mutation payloads are assembled in components (DetailTab, TaskFieldsEditor, KanbanBoard, ArchivalModal, ResolveModal), not just API modules. Import scanning ≠ data-flow isolation; the codebase already has inline formatters that wouldn't be caught.

**Revised approach — two-tier:**

| Tier | Method | Catches | Misses |
|------|--------|---------|--------|
| **T1: Import ban** | Read every file in the mutation call graph; assert none import from `utils/format` | Direct import of formatter module | Inline re-implementation; pass-through of formatted values |
| **T2: Existing payload assertions** | Existing tests (tasks_1501, decisions_1502, ArchivalModal, KanbanBoard.dragstart) already assert exact serialized request bodies with canonical values | Formatted values reaching the wire | Only covers tested paths |

The full mutation call graph for T1 scanning:
- `api/tasks.ts`, `api/decisions.ts`, `api/cleanup.ts`, `api/repair.ts`
- `hooks/useTaskMutation.ts`, `hooks/useCleanupFlow.ts`, `hooks/useRepairFlow.ts`
- `KanbanBoard.tsx` (handleDrop, handleTransitionClick)
- `components/ArchivalModal.tsx`, `components/ResolveModal.tsx`
- `components/DetailTab.tsx`, `components/TaskFieldsEditor.tsx`, `components/TaskActions.tsx`

**T1 is a guardrail, not a proof.** T2 (existing tests) provides the behavioral evidence. Together they satisfy AC2 at the RED phase — the builder can strengthen either tier during implementation.

### 3.3 Test File Structure

Follow existing `computeSignal.test.ts` pattern:
- `src/__tests__/format_1598.test.ts` — unit tests for all 4 formatters (AC1)
- `src/__tests__/formatPartition_1598.test.ts` — import ban + mutation path analysis (AC2)

Alternatively, combine into one file since the total test count is moderate (~25 tests).

## 4. Recommendation

**Write a single test file** `src/__tests__/format_1598.test.ts` covering both ACs:

- **AC1 block:** ~16 tests — 4 formatters × 4 inputs (null, undefined, valid, edge case)
- **AC2 block:** ~1 test — import-ban scan across the 13 mutation-graph files, using `fs.readFileSync` + regex for `from.*utils/format`

**Confidence: 0.80** — function signatures are well-specified by the brief. The import-ban test is a pragmatic guardrail acknowledged as incomplete; existing payload-level tests in the suite provide the behavioral evidence layer. The real proof strengthens at implementation (#1604) when formatters exist.

Challenge: proceed — confidence in original revised from 0.24 (import-only) to 0.80 (two-tier with acknowledged limitations).

## 5. Follow-up Tasks

No new tasks needed — #1604 (P1-05: Formatting utilities) already exists as the implementation task depending on #1598.
