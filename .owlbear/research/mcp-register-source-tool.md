# MCP Knowledge: register_source Tool Wiring

> **Owning task:** #1890 — Knowledge: MCP add register_source tool
> **Date:** 2026-05-27 **Status:** Complete

## 1. Context and Question

Task 1890 asks to create a new `knowledge_register_source` MCP tool in `serve/mcp-knowledge/`. All downstream components exist (SqliteSourceStore, SourceRegistration model, SourceConfig discriminated union). The question: exact wiring strategy and Pydantic strict-mode handling at the MCP boundary.

## 2. Sources Studied

| Source | Type | Relevance |
|--------|------|-----------|
| `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` | Codebase — AppContext + lifespan | 0.95 |
| `serve/knowledge/src/owlbear_knowledge/protocols/sources.py` | Codebase — SourceRegistration, SourceConfig, SourceRecord | 0.95 |
| `serve/knowledge/src/owlbear_knowledge/stores/sources.py` | Codebase — SqliteSourceStore.register_source() | 0.90 |
| `serve/knowledge/src/owlbear_knowledge/protocols/common.py` | Codebase — BoundaryModel (frozen, strict, extra=forbid) | 0.85 |

## 3. Analysis

### 3.1 Component Readiness

| Component | Status | Notes |
|-----------|--------|-------|
| `AppContext.source_store_v2` | ✓ Ready | `SqliteSourceStore` instance in lifespan |
| `SqliteSourceStore.register_source()` | ✓ Ready | Accepts `SourceRegistration`, returns `SourceRecord` |
| `SourceRegistration` model | ✓ Ready | Fields: name, kind, fetch_method, config, scope, enrich, refreshable, priority, metadata |
| `SourceConfig` discriminated union | ✓ Ready | 4 variants keyed on `kind` field |
| `ensure_tables()` call in lifespan | ✓ Ready | Already called during app startup |

### 3.2 Key Design Consideration: Strict Mode Boundary

`BoundaryModel` uses `ConfigDict(frozen=True, strict=True, extra="forbid")`. MCP parameters arrive as JSON primitives (plain strings, not StrEnum instances). Direct construction `SourceRegistration(kind="inline")` fails in strict mode.

| Approach | Pros | Cons | Confidence |
|----------|------|------|------------|
| `model_validate(data, strict=False)` | Clean one-liner, handles all coercion, idiomatic boundary crossing | Slight strictness relaxation at entry point | .85 |
| Manual enum construction before model init | Preserves strict semantics | Verbose, duplicates validation logic | .70 |
| TypeAdapter with explicit lax mode | Flexible | Over-engineering for single usage | .60 |

**Recommendation:** Use `SourceRegistration.model_validate(payload, strict=False)` — explicit boundary relaxation at the MCP edge. Wrap in `try/except ValidationError → ToolError`.

### 3.3 Implementation Pattern

```python
@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False))
async def knowledge_register_source(ctx, name, kind, fetch_method, config, ...):
    # 1. Get store from AppContext
    # 2. model_validate({...}, strict=False) → SourceRegistration
    # 3. Catch ValidationError → raise ToolError with detail
    # 4. Call store.register_source(registration) in thread
    # 5. Serialize SourceRecord → {id, name, state, kind, scope}
```

### 3.4 Return Shape

AC specifies: "Returns serialized SourceRecord (id, name, state, kind, scope)". `register_source()` always returns a `ConfiguredSourceRecord` (ACTIVE state). Serialize to a TypedDict with these 5 fields.

## 4. Recommendation

Straightforward wiring (confidence: .88). All components exist and are tested. Single new function in `server.py` (~25 LOC), one new TypedDict in `_types.py`, registration in `__all__`.

Challenge: FALLBACK — T1 greenfield wiring with zero ambiguity; challenge unnecessary.

## 5. Follow-up Tasks

No additional follow-up tasks needed — task 1890 itself is the implementation unit at `research` status, ready for architect → builder flow.
