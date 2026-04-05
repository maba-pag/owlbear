# Task #143 TDD RED Scope Validation

> **Owning task:** #143 — Test: Extract CancelSignal, sandbox_path, consolidation, and evaluator
> **Date:** 2026-03-29 **Status:** Complete

## 1. Context and Question

Task #143 was created by the architect during #135 review to split tests from implementation
(TDD discipline). It covers TDD RED tests for 4 modules: CancelSignal, sandbox_path,
ConsolidationService, and SourceEvaluator. Key questions: (a) are the AC items accurate
against v1 source, (b) is the testing approach feasible, (c) does #143 overlap with the
existing #138 test task?

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| v1 cancellation.py | `v1/src/owlbear/memory/knowledge/cancellation.py` (29 LOC) | 1.0 |
| v1 paths.py | `v1/src/owlbear/paths.py` (36 LOC) | 1.0 |
| v1 consolidation.py | `v1/src/owlbear/memory/knowledge/consolidation.py` (114 LOC) | 1.0 |
| v1 evaluator.py | `v1/src/owlbear/memory/knowledge/evaluator.py` (167 LOC) | 1.0 |
| #138 task + tests | `tests/test_consolidation.py`, `tests/test_evaluator.py` | 1.0 |
| #135 task AC | `kanban/tasks/135-*.md` (#143's parent impl task) | 1.0 |
| #139 task AC | `kanban/tasks/139-*.md` (stub impl matching #138's tests) | 1.0 |
| v2 test patterns | `tests/test_knowledge_foundation.py` (500+ LOC) | .90 |
| extract research doc | `docs/research/extract-cancel-sandbox-consolidation-evaluator.md` | .95 |

## 3. Analysis

### 3.1 CancelSignal + sandbox_path — Valid and Unique

These modules have **no existing tests** and no overlap with #138.

| AC item | v1 source match | Feasible |
|---------|-----------------|----------|
| CancelSignal is runtime_checkable Protocol | v1 L8: `@runtime_checkable` — exact | Yes |
| LinkedCancelSignal.is_set() False when no source set | v1 L27: `any(...)` on empty tuple → False | Yes |
| LinkedCancelSignal.is_set() True when any source set | v1 L28: `any(source.is_set() ...)` | Yes |
| sandbox_path valid relative resolves | v1 L28: `(root / candidate).resolve()` | Yes |
| sandbox_path null byte raises PermissionError | v1 L21: explicit `\x00` check | Yes |
| sandbox_path `..` traversal raises PermissionError | v1 L30: `is_relative_to` guard | Yes |
| sandbox_path absolute inside root resolves | v1 L28: `candidate.is_absolute()` branch | Yes |
| sandbox_path absolute outside root raises | v1 L30: `is_relative_to` guard | Yes |

All AC items are accurate and directly verifiable against v1 source. No issues.

### 3.2 Consolidation + Evaluator — Scope Overlap with #138/#139

**Critical finding:** #143 and #138 both test `ConsolidationService` and `SourceEvaluator`
but against **incompatible constructor interfaces**.

| Aspect | #138/#139 (stub) | #143/#135 (LLM-injectable) |
|--------|------------------|---------------------------|
| ConsolidationService init | `(conn, graph_store=None, model=None)` | `(conn, llm_fn: TextCompletionFn)` |
| SourceEvaluator init | `(model=None)` | `(llm_fn: EvaluateFn)` |
| consolidate() behavior | Returns 0 (no-op) | Calls llm_fn, stores insight, marks chunks |
| evaluate() behavior | Returns stub neutral | Calls llm_fn, returns real result |
| Status | #138 in-progress (tests written) | #143 at ideation |

When #135 implements the LLM-injectable interface, **#138's stub tests will break** because
the constructor signatures change. Two test files testing the same module with different
APIs creates a collision.

### 3.3 Task Chain Conflict

```
Chain A: #138 (RED, done) → #139 (GREEN, todo) — stub extraction
Chain B: #143 (RED, ideation) → #135 (GREEN, backlog) — full extraction
```

#135 supersedes #139 for consolidation + evaluator. Either #139's stubs get replaced by
#135's full implementation (breaking #138's tests), or both coexist with conflicting APIs.

### 3.4 Recommendation (.90 confidence)

**Refine #143 scope to CancelSignal + sandbox_path only.** Remove the consolidation and
evaluator test AC items, which are already covered by #138 (albeit with the stub interface).

When #135 is implemented, it should update **#138's existing tests** to match the new
LLM-injectable constructor signatures rather than creating a parallel test file.

| Option | Pros | Cons | KISS |
|--------|------|------|------|
| A: Refine #143 to cancel+sandbox only | No overlap, clean scope | #135 must update #138 tests | High |
| B: Keep #143 as-is, delete #138 overlap | One test file per chain | Wastes #138 work already done | Low |
| C: Make #143 additive (import+extend) | Tests both interfaces | Over-engineered, two test shapes | Low |

**Recommendation: Option A** — refine #143 to only cover CancelSignal and sandbox_path.
Add a note to #135 AC: "Update test_consolidation.py + test_evaluator.py constructors to
use TextCompletionFn/EvaluateFn when replacing stubs."

## 4. Research Checklist

1. **Theoretical validity** — TDD RED for CancelSignal/sandbox_path is sound and needed.
2. **Prior art** — v1 source verified, v2 test patterns established (test_knowledge_foundation.py).
3. **Technical feasibility** — All test approaches (Protocol isinstance, path resolution, AsyncMock)
   are standard pytest/Python patterns. No blockers.
4. **Architecture fit** — Follows existing v2 test naming (`TestFromAC_*`), in-memory SQLite,
   `pytest-asyncio`. Consolidation/evaluator overlap needs resolution per §3.2.
5. **Implementation approach** — Single test file, import from `owlbear_knowledge` packages.
6. **Testing strategy** — Covered by the task itself (it IS the test task).
7. **Findings documented** — This document.

## 5. Follow-up Tasks

Refine existing tasks rather than creating new ones:

1. **Refine #143** — Remove consolidation + evaluator AC items. Rename to
   "Test: Extract CancelSignal and sandbox_path". Keep CancelSignal (4 tests) +
   sandbox_path (5 tests) AC. Update test filename to
   `tests/test_knowledge_cancel_sandbox.py`.

2. **Add note to #135** — AC should include: "Update existing test_consolidation.py and
   test_evaluator.py constructor signatures to match TextCompletionFn/EvaluateFn interface
   (replacing stub model param)."

Both refinements are for the **architect** to action — researcher does not modify task AC.
