# Memory Engine — State Machine, OCC, and Caching

> **Owning task:** #1668 — P1-02: Memory engine — MemoryEngine with state machine, OCC, and caching
> **Date:** 2026-05-19 **Status:** Complete

## 1. Context and Question

Task #1668 implements `MemoryEngine` in `serve/memory/src/owlbear_memory/engine.py` — the orchestration layer over P1-01 storage primitives. Questions: (a) which MtimeScanCache pattern to use, (b) how to encode the state machine, (c) OCC implementation details, (d) EditPayload design, (e) duplicate UUID dedup strategy.

## 2. Sources Studied

| Source | Type | Relevance |
|--------|------|-----------|
| `serve/mcp-memory/src/owlbear_mcp_memory/engine.py` | Codebase | 1.0 — extraction source, MtimeScanCache pattern |
| `serve/cockpit/src/owlbear_cockpit/cache.py` | Codebase | 0.7 — alternative blake2b digest cache |
| `serve/kanban/src/owlbear_kanban/storage.py` L435–475 | Codebase | 0.9 — OCC via `write_task_if_unchanged` |
| `.owlbear/briefs/draft-cockpit-memory-tab/brief.md` | Project doc | 1.0 — authoritative spec |
| `serve/memory/src/owlbear_memory/storage.py` | Codebase | 1.0 — P1-01 primitives (read/write/delete) |
| `serve/kanban/src/owlbear_kanban/engine.py` L741 | Codebase | 0.6 — duplicate ID handling (raises) |

## 3. Analysis

### 3.1 MtimeScanCache Pattern

| Pattern | Source | Pros | Cons |
|---------|--------|------|------|
| Simple `st_mtime_ns` on dir | mcp-memory engine | Fast, single syscall, brief specifies this | May miss rapid sub-second edits |
| Blake2b of filenames+mtimes | cockpit cache | Detects per-file changes | More complex, multi-syscall scan |

**Decision:** Use simple `st_mtime_ns` on directory — matches brief wording ("directory mtime unchanged") and the memory directory changes infrequently (agent writes, not concurrent user edits).

### 3.2 State Machine Encoding

Brief specifies a constrained table (not open transitions like kanban). Best encoding: frozen dict keyed by `(from_state, action)` → `to_state | HARD_DELETE` sentinel.

```python
_TRANSITIONS: dict[tuple[MemoryState, str], MemoryState | None] = {
    (PENDING, "edit"):    CURATED,   # only when scope_agents provided
    (CURATED, "approve"): APPROVED,
    (APPROVED, "edit"):   CURATED,
    (PENDING, "delete"):  None,      # None = hard delete
    (CURATED, "delete"):  DELETED,
    (APPROVED, "delete"): DELETED,
}
```

Raise `TransitionError` for any `(state, action)` pair not in the table.

### 3.3 OCC Implementation

Follows kanban pattern: compare `expected_updated_at` (string) against `entry.updated_at` before mutation. String comparison is sufficient since timestamps are ISO-8601 with timezone and the engine controls all writes.

```python
if entry.updated_at != expected_updated_at:
    raise ConcurrencyError(f"expected {expected_updated_at}, found {entry.updated_at}")
```

### 3.4 EditPayload Type

No existing `EditPayload` in the package. Options:

| Option | Pros | Cons |
|--------|------|------|
| TypedDict with all-optional fields | Type-safe, IDE support | Requires `total=False` |
| Plain `dict[str, Any]` | Simple | No type safety at call site |
| Pydantic model | Validation built-in | Over-engineering for internal API |

**Decision:** `TypedDict` with `total=False` — matches the package's internal-API nature, gives IDE support without adding a Pydantic model for an internal parameter.

Editable fields: `title`, `categories`, `confidence`, `scope_agents`, `content`. State transitions are implicit (not user-settable).

### 3.5 Duplicate UUID Handling

| Approach | Source | Brief specifies |
|----------|--------|-----------------|
| Raise error | kanban | No |
| Keep later `updated_at` | brief § Engine Package | **Yes** |

Keep the entry with the later `updated_at`. Log warning. Return dedup count in load metadata.

### 3.6 Lenient Read

`storage.read_entry()` already returns `None` for malformed files. Engine counts `None` returns as `parse_errors`. The `get_entries()` return type is `list[MemoryEntry]` but engine tracks `parse_errors` as instance state for API consumers.

## 4. Recommendation

**Confidence: 0.88** — All patterns have direct codebase precedent. The only novel element is the constrained state machine table, which is straightforward.

Implementation path:
1. Add `MtimeScanCache` class (copy from mcp-memory, already proven)
2. Add `EditFields` TypedDict
3. Add `MemoryEngine` class with `_TRANSITIONS` table
4. Wire mutations through OCC check → transition validation → field update → `write_entry()`
5. Export `MemoryEngine` and `MtimeScanCache` from `__init__.py`

Challenge: FALLBACK — extraction+composition of proven patterns with full spec; challenger not invoked.

## 5. Follow-up Tasks

None needed — #1668 has well-defined AC (5 lines) and clear implementation path. Downstream tasks (#1669 P2-01 MCP wiring, #1670 P2-02 cockpit API) are already planned.
