# Architectural Stance — Cockpit Memory Tab

## Position: Extract `serve/memory/` as prerequisite; cockpit consumes the shared engine

The memory tab's structural foundation must be a standalone `serve/memory/` package — following the kanban extraction pattern. This is a repo-topology refactor that precedes the tab feature itself.

## Structural Reasoning

### Package Topology

The cockpit's architecture constraint is clear: it cannot import MCP server packages. Today the memory engine, models, enums, and all business logic live inside `serve/mcp-memory/`. The cockpit needs to read memory files AND mutate state (approve, edit, delete). Two paths exist:

1. **Reimplement in cockpit** — duplicate parsing, validation, state machine, visibility logic (~200+ lines). Guaranteed drift.
2. **Extract to `serve/memory/`** — shared package consumed by both `serve/mcp-memory/` and `serve/cockpit/`. Single source of truth.

I take position (2) unconditionally. The kanban package proves this works at this scale. The alternative creates a category of bug (logic drift between two state machine implementations) that no amount of testing can fully prevent.

### Extraction Scope — Larger Than "Engine + Transitions"

The extraction must include:

| Component | Current Location | Notes |
|-----------|-----------------|-------|
| MemoryEngine class | `mcp-memory/engine.py` | File I/O, scan, parse YAML+body |
| MemoryEntry model | `mcp-memory/models.py` | Pydantic model with all fields |
| Enums (Category, State) | `mcp-memory/models.py` | StrEnum types |
| State machine transitions | `mcp-memory/tools.py` | Must move INTO engine class |
| Validation rules | `mcp-memory/tools.py` | Content length, confidence range, category count |
| Visibility filtering | `mcp-memory/tools.py` | State-aware list (exclude deleted by default), configurable |
| Metadata-only list | `mcp-memory/tools.py` | Return entries without body for list surfaces |

Explicitly **excluded** from extraction:
- Git commit lifecycle — design question (see below)
- MCP-specific teaching validation messages — transport-layer concern
- Curator-only access policy — caller-layer enforcement

### State Machine Ownership

All transitions move into MemoryEngine methods:
- `approve(id)` — guards: curated only → approved, sets `approved_at`
- `edit(id, fields)` — validates, auto-downgrades approved → curated
- `delete(id)` — pending = hard delete, curated/approved = soft delete
- `curate(id, scope_agents)` — pending → curated, approved → curated (downgrade)

Engine methods raise typed domain exceptions (`InvalidTransition`, `EntryNotFound`, `ValidationError`). Callers map to their transport format (MCP error messages, HTTP error envelopes).

### Cockpit Integration Pattern

- **DI:** `get_memory_engine()` factory returning an **app-scoped singleton** MemoryEngine instance. Cached via the same WeakKeyDictionary pattern used for KanbanEngine.
- **Cache:** New `MtimeScanCache` instance keyed on memory engine identity. Same blake2b(filename + mtime_ns) hashing as kanban, applied to all files in memory directory.
- **Routes:** `APIRouter()` prefix `/api/memories`, strict Pydantic response models.
- **Concurrency:** Optimistic concurrency via `updated_at` token. This is a **new** contract for memory (MCP tools don't need it; cockpit does because the user may view stale data). Mutation requests carry `expected_updated_at`; engine rejects on mismatch with 409. MCP tools bypass this (single-writer assumption for agent callers).

### API Surface

```
GET  /api/memories                    → all entries, all states, metadata + body
POST /api/memories/{id}/approve       → {expected_updated_at}
POST /api/memories/{id}/edit          → {expected_updated_at, title?, content?, ...}
DELETE /api/memories/{id}             → {expected_updated_at}
```

### SSE: Bounded but Non-Trivial

Adding memory to the event stream requires:
1. Backend: expand watch root to include memory directory (currently only kanban_dir)
2. Backend: add event classification branch (`memories-changed` type)
3. Frontend: extend EventSourceProvider to handle new event type
4. Frontend: new `useMemories()` hook subscribes to events, triggers refetch

Each step is well-defined but touches existing contracts (event type literals, provider typing, test assertions). Not a one-liner; bounded at ~4 integration points.

### Frontend Structure

Without #1638, adding the memory tab requires modifying Shell.tsx — adding a route and nav entry into the currently hardcoded kanban-only layout. The shell is tightly coupled to kanban state at top level.

Recommendation: structure the memory page as `pages/Memory/index.tsx` (lazy-loadable), with its own data hook. When #1638 lands, it migrates to a config entry. But the pre-#1638 shell modification is real work, not a trivial wire-up.

## Key Trade-offs

| Decision | Cost | Benefit |
|----------|------|---------|
| Extract `serve/memory/` first | Sequencing cost — prerequisite task before tab work | Single source of truth, no logic drift, shared models |
| OCC as new contract | Frontend complexity (conflict handling), engine must track tokens | Prevents stale-write bugs in multi-tab or slow-network scenarios |
| SSE for memory | ~4 integration points across backend + frontend | Real-time updates, consistent with kanban UX |
| App-scoped engine singleton | Must handle directory changes gracefully | Cache efficiency, no per-request re-parse |

## Open Design Questions (Not Settled Here)

1. **Git commit lifecycle:** Current git batching is a standalone helper called at MCP session boundaries, not per-mutation. For cockpit, per-mutation commits are more natural (user action → commit). This needs fresh design during extraction — it is NOT inherited behavior.

2. **Deleted entry visibility:** Whether the admin surface shows deleted entries is an open product question (research notes flag this explicitly). My recommendation: show them with clear state badging, since they exist on disk. But this needs a user decision.

3. **Caller context / policy boundary:** The engine should accept a visibility configuration (e.g., "include deleted" flag on list methods) rather than hardcoding admin vs agent behavior. Policy enforcement (curator-only restrictions, admin override) belongs in the caller layer, not the engine.

## Warnings

- **Do not build the tab before the extraction.** If the cockpit reimplements memory parsing/mutations directly, you create a second state machine that will diverge. The extraction is cheap (most code moves, little is rewritten) and pays for itself immediately.
- **The storage root must be pinned.** Current verified default is `.owlbear/memory/`. Both consumers must agree on this path. Make it configurable via the engine constructor.
- **OCC divergence between callers is acceptable.** MCP tools (single-agent, no concurrent writes) can skip the concurrency token. Cockpit requires it. The engine supports both modes: pass `expected_updated_at=None` to bypass the check.

## Confidence

0.78

The core structural choice (extract → share) is well-supported by precedent and eliminates the primary risk (logic drift). Reduced from higher because git lifecycle and deleted-visibility are genuine open questions that affect implementation scope. The direction is firm; the details need resolution during task decomposition.
