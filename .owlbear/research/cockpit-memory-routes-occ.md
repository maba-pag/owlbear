# Cockpit Backend API — Memory Routes with OCC

> **Owning task:** #1670 — P2-02: Cockpit backend API — memory routes with OCC
> **Date:** 2026-05-19 **Status:** Complete

## 1. Context and Question

How should the cockpit backend expose memory management endpoints (list, approve, edit, delete) using the MemoryEngine from `serve/memory/`, following existing cockpit patterns for DI, error handling, and caching?

Key sub-questions:
- How to handle memory errors (not KanbanError subclasses) in the global exception handler?
- How to wire MemoryEngine into the DI graph?
- What response models are needed?

## 2. Sources Studied

| Source | Location | Relevance |
|--------|----------|-----------|
| Cockpit routes pattern | `serve/cockpit/src/owlbear_cockpit/routes/mutation.py` | 1.0 — exact pattern to follow |
| DI implementation | `serve/cockpit/src/owlbear_cockpit/deps.py` | 1.0 — DI graph to extend |
| Error envelope | `serve/cockpit/src/owlbear_cockpit/main.py:42-72` | 1.0 — exception handler pattern |
| MemoryEngine API | `serve/memory/src/owlbear_memory/engine.py` | 1.0 — engine public interface |
| Memory errors | `serve/memory/src/owlbear_memory/errors.py` | 1.0 — exception hierarchy |
| Brief spec | `.owlbear/briefs/draft-cockpit-memory-tab/brief.md` | 0.9 — contract definition |
| Task #1668 (archived) | MemoryEngine implementation evidence | 0.8 — confirms API shape |

## 3. Analysis

### 3.1 Error Handling Strategy

Memory errors (`NotFoundError`, `ConcurrencyError`, `TransitionError`, `ValidationError`) are plain `Exception` subclasses — they do NOT inherit from `KanbanError`. The existing handler won't catch them.

| Option | Approach | Pro | Con | KISS Score |
|--------|----------|-----|-----|-----------|
| A: Base class + global handler | Add `MemoryError` base in `owlbear_memory.errors`, register `@app.exception_handler(MemoryError)` | Identical pattern to kanban | Requires modifying the memory package |
| B: Individual handlers | Register 4 separate handlers for each error type | No memory package changes | Verbose, 4 handlers in main.py |
| C: Route-level try/except | Catch in each endpoint, raise HTTPException | Self-contained in routes file | Deviates from established pattern, duplicated logic |
| **D: Import + dispatch** | Register handlers for each memory error type in main.py with a shared status mapper | No memory package changes, DRY | Slightly more imports in main.py |

**Recommendation: Option D** — Register individual exception handlers that use a shared `_memory_status()` mapper, mirroring the existing `_kanban_status()` pattern. This keeps the error envelope consistent without modifying the memory package. The memory errors lack `.code`/`.user_message` attributes, so the handler extracts from `str(exc)` with stable prefixed codes.

Error code mapping:

| Exception | HTTP Status | Code String |
|-----------|-------------|-------------|
| `NotFoundError` | 404 | `MEM_NOT_FOUND` |
| `ConcurrencyError` | 409 | `MEM_CONFLICT` |
| `TransitionError` | 422 | `MEM_INVALID_TRANSITION` |
| `ValidationError` | 422 | `MEM_VALIDATION_ERROR` |

### 3.2 DI Wiring

| Component | Pattern | Implementation |
|-----------|---------|---------------|
| `get_memory_engine()` | Same as `get_engine()` | Read from `app.state.memory_engine` |
| Engine init | Same as kanban engine in `run()` | `MEMORY_DIR` env var → `MemoryEngine(dir)` → `app.state.memory_engine` |
| Cache | Engine-internal | MemoryEngine already has `MtimeScanCache` internally; no separate cockpit cache needed |
| Test override | `app.dependency_overrides[get_memory_engine]` | Standard FastAPI DI pattern |

### 3.3 Response Models

```
MemoryEntryResponse — mirrors MemoryEntry fields (id, title, content, categories, confidence, state, scope_agents, source_agent, created_at, updated_at, approved_at)
MemoriesResponse — { entries: list[MemoryEntryResponse], parse_errors: int }
ApproveRequest — { expected_updated_at: str }
EditRequest — { expected_updated_at: str, title?, content?, categories?, confidence?, scope_agents? }
DeleteRequest — { expected_updated_at: str }
```

### 3.4 Package Dependency

The cockpit `pyproject.toml` needs `owlbear-memory` added as a workspace dependency:
- Add to `[project] dependencies`
- Add to `[tool.uv.sources]` as `{ workspace = true }`

### 3.5 File Placement

| File | Purpose |
|------|---------|
| `serve/cockpit/src/owlbear_cockpit/routes/memory.py` | 4 endpoints + request/response models |
| `serve/cockpit/src/owlbear_cockpit/deps.py` | Add `get_memory_engine()` |
| `serve/cockpit/src/owlbear_cockpit/main.py` | Add memory exception handlers, memory router include, memory engine init in `run()` |
| `serve/cockpit/pyproject.toml` | Add `owlbear-memory` dependency |

## 4. Recommendation

**Confidence: 0.90** — This is a direct composition of proven patterns. The cockpit already does exactly this for kanban; memory routes follow the same structure with the only design decision being the error handler strategy (Option D recommended).

**Tier: T1** — No new capability, architecture change, or security boundary. It's a route file addition following the established pattern.

Challenge: SKIPPED — single clear approach (composition of existing cockpit + engine patterns), no competing architectural designs.

## 5. Follow-up Tasks

No additional research tasks needed. The existing task #1670 has sufficient scope and AC for direct implementation. Implementation is straightforward composition:
1. Add workspace dep to cockpit pyproject.toml
2. Add `get_memory_engine()` to deps.py
3. Add `routes/memory.py` with 4 endpoints
4. Register router + exception handlers in main.py
5. Init memory engine in `run()`
