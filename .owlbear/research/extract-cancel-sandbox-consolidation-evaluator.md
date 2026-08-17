# Extract CancelSignal, sandbox_path, Consolidation & Evaluator

> **Owning task:** #135 — Extract CancelSignal, sandbox_path, consolidation, and evaluator into knowledge package
> **Date:** 2026-03-29 **Status:** Complete

## 1. Context and Question

Task #135 extracts four v1 modules (Group A from #130 research) that have no IngestPipeline
dependency into `packages/knowledge/`. Key questions: (a) can v1 code be extracted as-is or
does it need adaptation, (b) what is the correct LLM injection pattern for v2, (c) what
schema/infrastructure already exists.

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| v1 cancellation.py | Local `v1/src/owlbear/memory/knowledge/cancellation.py` (29 LOC) | 1.0 |
| v1 paths.py | Local `v1/src/owlbear/paths.py` (36 LOC) | 1.0 |
| v1 consolidation.py | Local `v1/src/owlbear/memory/knowledge/consolidation.py` (114 LOC) | 1.0 |
| v1 evaluator.py | Local `v1/src/owlbear/memory/knowledge/evaluator.py` (167 LOC) | 1.0 |
| v2 knowledge package | Local `packages/knowledge/src/owlbear_knowledge/` | 1.0 |
| Cooperative cancellation research | `docs/research/cooperative-cancellation.md` | .85 |
| #130 parent research | `docs/research/extract-knowledge-secondary-features.md` §3 | .90 |
| Python `typing.Callable` docs | <https://docs.python.org/3/library/typing.html#typing.Callable> | .80 |
| .NET CancellationToken docs | <https://learn.microsoft.com/en-us/dotnet/standard/threading/cancellation-in-managed-threads> | .75 |

## 3. Analysis

### 3.1 Module Readiness Assessment

| Module | v1 LOC | v2 schema ready? | PydanticAI dep? | Adaptation needed |
|--------|--------|-------------------|-----------------|-------------------|
| CancelSignal + LinkedCancelSignal | 29 | N/A (no DB) | No | Minimal — v1 `LinkedCancelSignal` takes `CancelSignal` (Protocol) args; cooper-cancel research shows `asyncio.Event` variant. v2 should keep Protocol-only (KISS). |
| sandbox_path | 14 | N/A (no DB) | No | None — pure function, zero deps, copy as-is to `_paths.py` |
| ConsolidationService | 114 | Yes — `consolidations` table + `chunks.consolidated` column exist | Yes — `Agent(model, system_prompt=...)` | Replace `Agent` with `TextCompletionFn` callable; remove `_agent` field |
| SourceEvaluator + EvaluationResult | 167 | N/A (no DB) | Yes — `Agent(model, output_type=EvaluationResult)` | Replace `Agent` with `EvaluateFn` callable; drop UsageTracker import |

### 3.2 LLM Injection Pattern

The existing v2 pattern (`extractor.py`) uses a no-op stub class. The #130 research
recommends async callable injection instead — more flexible and testable (.85 confidence):

```python
from collections.abc import Awaitable, Callable

TextCompletionFn = Callable[[str], Awaitable[str]]
EvaluateFn = Callable[[str], Awaitable[EvaluationResult]]
```

This aligns with KISS — no ABC, no Protocol class, just typed callables. Tests inject
`AsyncMock` or simple lambdas. Application layer injects real PydanticAI calls.

**Placement:** Define type aliases in each module that uses them (consolidation, evaluator).
No shared `_types.py` needed — YAGNI until a third consumer appears.

### 3.3 CancelSignal Design Decision

Two variants exist in research:

| Variant | From | Takes | v2 fit |
|---------|------|-------|--------|
| Protocol-args | v1 `cancellation.py` | `*sources: CancelSignal` | Clean — any Protocol-satisfying object works |
| asyncio.Event-args | `cooperative-cancellation.md` §3.3 | `*events: asyncio.Event \| None` | Tied to asyncio primitives |

**Recommendation (.90 confidence):** Use the v1 Protocol-args variant. It's more general,
already implemented, and matches the Protocol-first style in v2 (`VectorStoreProtocol`,
`EmbeddingProvider`). The asyncio.Event is one implementation detail — callers wrap events
in Protocol-satisfying objects.

### 3.4 Infrastructure Verification

| Prerequisite | Status | Location |
|--------------|--------|----------|
| `consolidations` table DDL | Exists | `schema.py` L133-141 |
| `chunks.consolidated` column | Exists | `schema.py` L83 (v8 migration) |
| `init_db` creates both | Verified | `schema.py` L269 |
| `GraphStore` import available | Yes | `owlbear_knowledge.graph_store` |
| `__init__.py` export pattern | Standard | add new public names to `__all__` |

### 3.5 Testing Strategy

| Module | Test approach | Key assertions |
|--------|---------------|----------------|
| CancelSignal | `is_set()` returns False initially, True after set | Protocol conformance, LinkedCancelSignal composition |
| sandbox_path | Parametrized: valid paths resolve, traversal paths raise `PermissionError` | Null-byte rejection, `..` traversal, absolute-outside-root |
| ConsolidationService | In-memory SQLite + `AsyncMock` for LLM fn | Returns 0 on empty, 1 on success, marks chunks consolidated, handles LLM failure |
| SourceEvaluator | `AsyncMock` returning `EvaluationResult` | Empty content returns score 0, no project context returns default, LLM failure returns neutral |

## 4. Recommendation (.90 confidence)

Extract all four modules with these specific adaptations:

1. **CancelSignal** — copy v1 Protocol-args variant verbatim to `cancellation.py`
2. **sandbox_path** — copy to `_paths.py` (private, not in `__init__.__all__`)
3. **ConsolidationService** — replace `Agent` with `TextCompletionFn` constructor param; keep `consolidate()` and `schedule_periodic()` public API; drop `_agent` field
4. **SourceEvaluator** — replace `Agent` with `EvaluateFn` constructor param; drop UsageTracker, `record_agent_usage`, and provider; keep `EvaluationResult`, `_default_result`, `_build_prompt` helpers

Risk: The callable approach means the application layer must construct the right lambda/closure.
This is a feature (explicit wiring) not a bug — matches v2's composition-over-framework pattern.

## 5. Follow-up Tasks

Task #135 itself is the implementation task — it already has concrete AC. No additional
follow-up tasks needed. The research validates the AC and provides implementation guidance.
