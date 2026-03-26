# CancelSlot and Tool-Invoked Cancellation — Research Validation

> **Owning task:** #1001 — Add CancelSlot and wire tool-invoked cancellation to daemon shutdown
> **Date:** 2026-03-25 **Status:** Complete

## 1. Context and Question

Task #1001 was created by #877 research ([docs/research/tool-invoked-cancellation.md](../research/tool-invoked-cancellation.md)). This validation confirms the original findings remain accurate against current HEAD and the task is ready for architect review.

Key question: Is the CancelSlot approach still viable after #870 was completed and merged?

## 2. Sources Studied

| Source | URL | Relevance | What it established |
|--------|-----|-----------|---------------------|
| .NET CancellationTokenSource/Token | <https://learn.microsoft.com/en-us/dotnet/standard/threading/cancellation-in-managed-threads> | .95 | Write-side (`CancellationTokenSource.Cancel`) / read-side (`CancellationToken.IsCancellationRequested`) split; `CreateLinkedTokenSource` for composition; token passed to operations at construction |
| AnyIO cancel scopes | <https://anyio.readthedocs.io/en/stable/cancellation.html> | .75 | Cooperative cancellation via scoped context managers; level-based cancellation in Python async; confirms polling `is_set()` is idiomatic for async-native code |
| OwlBear cancellation.py (local) | src/owlbear/memory/knowledge/cancellation.py | .95 | `CancelSignal` protocol + `LinkedCancelSignal` adapter exist and are stable post-#870 |
| OwlBear bootstrap/knowledge.py (local) | src/owlbear/bootstrap/knowledge.py | .90 | `_build_*_toolset` helpers construct toolsets without cancel; confirms wiring surface |
| OwlBear pipeline methods (local) | src/owlbear/memory/knowledge/*.py | .90 | `ingest()`, `ingest_text()`, `refresh()`, `process()` all accept `cancel=` — no pipeline changes needed |

## 3. Analysis

### 3.1 Dependency validation

| Check | Result |
|-------|--------|
| #870 (cancel signal infrastructure) archived? | Yes — archived 2026-03-25 |
| `CancelSignal` protocol exists in cancellation.py? | Yes — `is_set() -> bool`, runtime-checkable |
| `LinkedCancelSignal` exists in cancellation.py? | Yes — composes `*sources`, `any()` delegation |
| Pipeline methods accept `cancel=`? | Yes — `ingest()`, `ingest_text()`, `refresh()`, `process()` all have it |
| Toolset methods pass `cancel=` to pipelines? | No — this is the gap #1001 fills |

### 3.2 CancelSlot feasibility (.90 confidence)

The CancelSlot pattern maps cleanly to .NET's CancellationTokenSource/Token:

| .NET | OwlBear | LOC |
|------|---------|-----|
| `CancellationTokenSource` | `CancelSlot.set_source()` | ~3 |
| `CancellationToken.IsCancellationRequested` | `CancelSlot.is_set()` | ~2 |
| `CreateLinkedTokenSource` | `LinkedCancelSignal` (exists) | 0 |

Total new code: ~10 LOC in cancellation.py. Satisfies `CancelSignal` protocol — toolsets receive it as their existing type.

### 3.3 Wiring validation

Current constructor signatures (no cancel param):

- `KnowledgeToolset(workspace_root, vector_store, graph_store, embedding_provider, ingest_pipeline, project_scope)`
- `BookmarkToolset(pipeline, store)`
- `KnowledgeSourceToolset(store, orchestrator, workspace_root)`

Adding `cancel: CancelSignal | None = None` to each is backward-compatible. The `_build_*_toolset` helpers in `bootstrap/knowledge.py` need one extra kwarg each.

`BootstrapResult` is a non-frozen dataclass — adding `cancel_slot: CancelSlot | None = None` is safe.

### 3.4 Risk assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Mutable shared state across concurrent tools | Low | `is_set()` is read-only; single-threaded event loop; `set_source()` called once |
| Late-binding race (tool called before `set_source`) | None | `is_set()` returns `False` when unlinked — safe no-op |
| Non-daemon callers (CLI, tests) | None | CancelSlot never linked; `is_set()` always returns `False` |

## 4. Recommendation (.90 confidence)

Original #877 research recommendation remains valid. CancelSlot approach is the simplest option (KISS), requires no signature changes beyond adding an optional param, and has zero impact on non-daemon callers (YAGNI).

No changes to the AC are needed. Task is ready for architect gate.

## 5. Follow-up Tasks

No new tasks needed — #1001 AC is complete and actionable as written. The companion RED test task (#1002) should also exist from #877 research.
