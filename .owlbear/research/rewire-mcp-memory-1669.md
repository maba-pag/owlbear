# Rewire mcp-memory to owlbear-memory Engine Package

> **Owning task:** #1669 — P2-01: Rewire mcp-memory to import from owlbear-memory engine package
> **Date:** 2026-05-19 **Status:** Complete

## 1. Context and Question

Task #1669 requires rewiring `serve/mcp-memory/` to depend on the new `owlbear-memory` engine package (#1667/#1668) instead of its own `engine.py` and `models.py`. The question: what approach minimizes risk while satisfying all AC?

## 2. Sources Studied

| Source | Location | Relevance |
|--------|----------|-----------|
| mcp-memory tools.py | `serve/mcp-memory/src/owlbear_mcp_memory/tools.py` | 1.0 — primary file to rewire |
| mcp-memory engine.py | `serve/mcp-memory/src/owlbear_mcp_memory/engine.py` | 1.0 — file to remove |
| mcp-memory models.py | `serve/mcp-memory/src/owlbear_mcp_memory/models.py` | 1.0 — file to remove |
| owlbear-memory engine | `serve/memory/src/owlbear_memory/engine.py` | 1.0 — replacement engine |
| owlbear-memory models | `serve/memory/src/owlbear_memory/models.py` | 1.0 — replacement models |
| mcp-knowledge pattern | `serve/mcp-knowledge/pyproject.toml` | 0.9 — proven workspace dep pattern |
| mcp-kanban pattern | `serve/mcp-kanban/pyproject.toml` | 0.9 — proven workspace dep pattern |
| Existing tests | `tests/test_mutation_tools.py`, `test_recall_memory.py`, `test_memory_engine.py` | 0.8 — tests that import old modules |

## 3. Analysis

### API Surface Comparison

| Method | Old engine (`owlbear_mcp_memory.engine`) | New engine (`owlbear_memory`) |
|--------|------------------------------------------|-------------------------------|
| Load all | `load()` → `list[MemoryEntry]` | `load()` → `list[MemoryEntry]` |
| Cached read | `get_entries()` → `list[MemoryEntry]` | `get_entries()` → `list[MemoryEntry]` |
| Read one | `get_entry(id)` raises `KeyError` | `get_entry(id)` raises `NotFoundError` |
| Write raw | `write(entry)` → `Path` | **Not public** (`_write_updated_entry`) |
| Create | *n/a (tools construct + write)* | `save(title, content, ...)` → `MemoryEntry` |
| Update | *n/a (tools construct + write)* | `edit(id, fields, expected_updated_at)` → `MemoryEntry` |
| Approve | *n/a (tools construct + write)* | `approve(id, expected_updated_at)` → `MemoryEntry` |
| Delete | `delete(id)` (hard only) | `delete(id, expected_updated_at)` (hard/soft) |

### Key Gap: No Public `write()`

The old engine exposes `write(entry: MemoryEntry) → Path` which tools.py calls 12+ times. The new engine internalizes writes behind higher-level methods with OCC enforcement.

### Approach Comparison

| Criterion | A: Delegate to engine methods | B: Add public `write()` to new engine | C: Use `storage.write_entry()` directly |
|-----------|-------------------------------|---------------------------------------|----------------------------------------|
| AC compliance | Full (AC3: "delegating to MemoryEngine methods") | Partial (exposes bypass) | Violates AC3 |
| Behavioral parity | High — state machines match with care | Exact — no logic change | Exact |
| OCC enforcement | Automatic (free — entry loaded before mutate) | None (bypass) | None |
| Test impact | Import paths change; logic unchanged | Import paths only | Import paths only |
| Refactoring scope | Medium (~50 LOC rewrite in tools.py) | Minimal (~10 LOC in new engine) | Minimal |
| Future safety | Best — tools can't circumvent state machine | Risky — raw write bypasses guarantees | Risky |

### State Machine Compatibility

Both tools.py and the new engine implement the same transitions:
- `pending` + scope_agents → `curated` (promotion)
- `approved` + edit → `curated` (downgrade, clears approved_at)
- `curated` + edit → `curated` (no change)
- `curated` → `approved` (approve)
- `pending` → hard-delete; `curated`/`approved` → soft-delete

The key subtlety: tools.py resolves inherited scope_agents before checking promotion. If the builder always passes the resolved scope_agents in the `EditPayload`, `fields.get("scope_agents")` is truthy when non-empty — matching tools.py behavior exactly.

### Error Mapping

| New engine error | tools.py mapping |
|------------------|------------------|
| `NotFoundError` | `ToolError("entry not found: {id}")` |
| `TransitionError` | `ToolError(msg)` (with existing pre-checks) |
| `ConcurrencyError` | Should not occur in single-session MCP; map to ToolError if it does |

### Test Files Requiring Import Updates

| File | Current import | New import |
|------|---------------|------------|
| `tests/test_memory_engine.py` | `owlbear_mcp_memory.engine/models` | Delete or migrate (covered by `test_memory_engine_1668.py`) |
| `tests/test_recall_memory.py` | `owlbear_mcp_memory.engine/models` | `owlbear_memory` |
| `tests/test_mutation_tools.py` | `owlbear_mcp_memory.engine/models` | `owlbear_memory` |

### Dependency Change

```toml
# serve/mcp-memory/pyproject.toml
dependencies = ["mcp[cli]>=1.27.1", "owlbear-memory", "pydantic>=2.13.4", "pyyaml>=6.0.3"]

[tool.uv.sources]
owlbear-memory = { workspace = true }
```

Note: `pyyaml` stays because `git.py` uses it independently of the engine.

## 4. Recommendation

**Approach A: Delegate to new engine's public methods** — confidence 0.85

Refactor tools.py to call `engine.save()`, `engine.edit()`, `engine.approve()`, `engine.delete()` with proper error mapping. This is the cleanest architecture and matches the AC wording ("thin MCP adapters delegating to MemoryEngine methods").

Challenge: FALLBACK — trivial T1 refactoring with strong prior art (mcp-knowledge, mcp-kanban), challenger unnecessary.

### Risks and Mitigations

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Subtle state machine difference causes test failure | Low | Both engines implement identical transitions; resolve scope_agents before edit() |
| OCC parameter threading is error-prone | Low | Every mutation already loads entry first; `current.updated_at` is always available |
| `test_memory_engine.py` breaks | Certain | Either delete (redundant with 1668 tests) or update imports |

## 5. Follow-up Tasks

The task itself (#1669) is ready for development. No additional research tasks needed — the scope is clear and the approach is validated by prior art. The task can proceed directly to `todo` status for architecture review.
