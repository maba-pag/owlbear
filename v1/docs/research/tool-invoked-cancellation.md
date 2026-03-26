# Expose Daemon Shutdown to Tool-Invoked Knowledge Cancellation

> **Owning task:** #877 — Expose daemon shutdown to tool-invoked knowledge cancellation
> **Date:** 2026-03-25 **Status:** Complete

## 1. Context and Question

Task #870 threaded cooperative cancellation through knowledge pipelines (`RefreshOrchestrator`, `IngestPipeline`, `BookmarkPipeline`, `crawl_and_ingest()`). However, the cancel signal was only composed in the daemon-owned `RetrospectiveHook` path. Three agent-facing toolsets invoke the same pipelines during turns but never pass `cancel=`:

| Toolset | Tool method | Pipeline call | Cancel today? |
|---------|------------|---------------|---------------|
| `KnowledgeToolset` | `_ingest_document()` | `pipeline.ingest()` / `ingest_text()` | No |
| `KnowledgeSourceToolset` | `_refresh_source()` | `orchestrator.refresh()` | No |
| `BookmarkToolset` | `_bookmark_source()` | `pipeline.process()` | No |

The structural problem: toolsets are constructed during `bootstrap()`, but `shutdown_event` is created later in `run_daemon()`. No late-binding mechanism exists to bridge this gap.

## 2. Sources Studied

| Source | URL | Relevance | What it established |
|--------|-----|-----------|---------------------|
| .NET CancellationTokenSource/Token | <https://learn.microsoft.com/en-us/dotnet/standard/threading/cancellation-in-managed-threads> | .95 | Token source (write-side) vs token (read-side) separation; `CreateLinkedTokenSource` for composing parent/child signals; one token per cancelable operation |
| PydanticAI FunctionToolset tools | <https://ai.pydantic.dev/tools/> | .90 | FunctionToolset tools are bound methods accessing `self`, not RunContext; changing signatures to accept RunContext requires explicit refactoring per tool |
| OwlBear cancellation.py | local: `src/owlbear/memory/knowledge/cancellation.py` | .95 | `CancelSignal` protocol (`is_set() -> bool`) and `LinkedCancelSignal` adapter already exist; `asyncio.Event` satisfies the protocol transparently |
| OwlBear bootstrap/toolsets.py | local: `src/owlbear/bootstrap/toolsets.py` | .90 | Toolsets are built in `build_toolsets()` during `bootstrap()`, then wrapped in `HookedToolset`/`ApprovalGateToolset`; `shutdown_event` does not exist at construction time |
| OwlBear daemon.py | local: `src/owlbear/daemon.py` | .90 | `run_daemon()` creates `shutdown_event`, wires signal handlers and passes it to `channel_loop`/`poll_loop`; `BootstrapResult` does not currently expose a cancel surface |

## 3. Analysis

### 3.1 Approach comparison

| Approach | Description | KISS | Coupling | Non-daemon impact | Verdict |
|----------|-------------|------|----------|-------------------|---------|
| **A: CancelSlot** | Mutable container satisfying `CancelSignal`; `set_source()` for late binding | High (~10 LOC) | Zero — toolsets see `CancelSignal`, daemon sees `set_source()` | None — `is_set()` returns `False` until linked | Recommend |
| **B: RunContext deps** | Add cancel to `OwlBearDeps`, tools read `ctx.deps.cancel` | Low — requires all 6+ tool methods to accept `RunContext` | Medium — changes tool function signatures | Signature changes required | Reject |
| **C: Create event early** | Create `shutdown_event` in BearClaw command before `bootstrap()` | Medium | High — CLI code manages asyncio lifecycle | Minor | Possible but couples CLI to internals |
| **D: Setter per toolset** | `set_cancel()` method on each toolset, called after wrapping | Medium | Medium — caller must unwrap `HookedToolset` | None | Fragile — relies on wrapper internals |

### 3.2 CancelSlot design (.85 confidence)

Maps directly to the .NET CancellationTokenSource/Token split:

| .NET concept | OwlBear equivalent | Role |
|-------------|-------------------|------|
| `CancellationTokenSource` | `CancelSlot.set_source()` | Write-side (daemon) |
| `CancellationToken.IsCancellationRequested` | `CancelSlot.is_set()` | Read-side (toolsets) |
| `CreateLinkedTokenSource` | `LinkedCancelSignal` | Compose parent + per-op signals |

The slot satisfies `CancelSignal` itself, so toolsets receive it as their existing protocol type. Non-daemon callers never call `set_source()`, leaving `is_set()` permanently `False`.

### 3.3 Wiring flow

```
bootstrap() ──────────────────────────────────────────────
  │ creates CancelSlot ─┬─> KnowledgeToolset(cancel=slot)
  │                     ├─> BookmarkToolset(cancel=slot)  [via _build_*]
  │                     └─> KnowledgeSourceToolset(cancel=slot)
  │ stores slot on BootstrapResult
  └────────────────────────────────────────────────────────

run_daemon() ─────────────────────────────────────────────
  │ creates shutdown_event
  │ slot.set_source(LinkedCancelSignal(shutdown_event))
  │ ← from here, toolset.is_set() reflects daemon shutdown
  └────────────────────────────────────────────────────────
```

### 3.4 Scope boundaries

| In scope | Out of scope |
|----------|-------------|
| `CancelSlot` class in `cancellation.py` | Per-operation child cancel (user-initiated cancel of a single ingest) |
| Constructor param on 3 toolsets | Changing tool signatures to accept `RunContext` |
| Pipeline `cancel=` passthrough in tool methods | `GraphEnricher` cancellation (#871) |
| `BootstrapResult` field for cancel slot | CLI / non-daemon shutdown workflows |
| `run_daemon()` wiring | Agent-level turn cancellation |

## 4. Recommendation (.85 confidence)

Use a `CancelSlot` adapter in `cancellation.py`:

- ~10 LOC; satisfies existing `CancelSignal` protocol
- Injected into 3 toolsets at construction; stored on `BootstrapResult`
- Daemon calls `set_source(LinkedCancelSignal(shutdown_event))` in `run_daemon()`
- Non-daemon callers unchanged; no daemon imports in memory modules

Risk: mutable shared state across concurrent tool calls. Mitigated because `is_set()` is read-only and thread-safe for `asyncio.Event` (single-threaded event loop).

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Add CancelSlot and wire tool-invoked cancellation to daemon shutdown" --priority nice-to-have --status ideation --tags scope:core,type:build --depends-on 870 --body "**Source:** #877 research (docs/research/tool-invoked-cancellation.md)\n\n**AC:**\n1. Add CancelSlot class to cancellation.py satisfying CancelSignal with set_source() for late binding.\n2. KnowledgeToolset, KnowledgeSourceToolset, and BookmarkToolset accept optional cancel: CancelSignal and pass it to pipeline calls in _ingest_document, _refresh_source, _bookmark_source.\n3. bootstrap build_toolsets creates a CancelSlot, injects into all 3 toolsets, and stores on BootstrapResult.\n4. run_daemon calls slot.set_source(LinkedCancelSignal(shutdown_event)) after creating shutdown_event.\n5. Non-daemon callers remain unchanged (CancelSlot.is_set returns False when unlinked).\n6. Focused tests for shutdown-driven early exit in tool-invoked ingest, refresh, and bookmark paths."
```

```
kanban\kanban-md.exe create "RED tests for tool-invoked cancellation wiring" --priority nice-to-have --status ideation --tags scope:core,type:test --depends-on 877 --body "**Source:** #877 research (docs/research/tool-invoked-cancellation.md)\n\n**AC:**\n1. CancelSlot unit tests: is_set returns False when unlinked, True when linked source is set.\n2. KnowledgeToolset._ingest_document passes cancel to pipeline.ingest/ingest_text.\n3. KnowledgeSourceToolset._refresh_source passes cancel to orchestrator.refresh.\n4. BookmarkToolset._bookmark_source passes cancel to pipeline.process.\n5. Integration: BootstrapResult exposes cancel slot; run_daemon wires it to shutdown_event.\n6. All tests fail before implementation (RED phase)."
```
