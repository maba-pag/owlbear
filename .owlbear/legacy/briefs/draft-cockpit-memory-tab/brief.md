# Brief — Cockpit Memory Tab

## Problem

The memory system stores agent institutional knowledge as markdown files with YAML frontmatter, managed through a pending → curated → approved → deleted state machine. The only interface is MCP tools (agent-driven). There is no human-readable surface for browsing, reviewing, or acting on memory entries. The user cannot see or curate what agents "remember" without invoking MCP tools.

## Target Outcome

A polished Memory tab in the cockpit providing full visibility and control over agent institutional memory. Plugs into the #1638 route config when that lands. Backend and engine extraction proceed independently of the frontend.

## Architecture

### Package Topology

```
serve/memory/           ← NEW shared engine package (transport-free)
  src/owlbear_memory/
    __init__.py         ← public exports
    engine.py           ← MemoryEngine with mutation methods
    models.py           ← MemoryEntry, MemoryCategory, MemoryState, errors
    storage.py          ← file I/O primitives (read/write/delete)

serve/mcp-memory/       ← EXISTING, rewired to depend on serve/memory/
  (tools.py becomes thin adapter calling engine methods)

serve/cockpit/          ← EXISTING, new dependency on serve/memory/
  src/owlbear_cockpit/
    routes/memory.py    ← NEW API routes
```

Both `serve/mcp-memory/` and `serve/cockpit/` depend on `owlbear-memory` as a workspace package. Neither imports the other.

### Scope Split

- **Backend (proceeds now):** Engine extraction + cockpit API routes. No dependency on #1638.
- **Frontend (blocks on #1638):** React component, filtering UI, accordion detail, action buttons. Starts when tab infrastructure defines the component mounting contract.

## Engine Package (`serve/memory/`)

### Public API

```python
class MemoryEngine:
    def __init__(self, memory_dir: Path | str) -> None: ...
    def load(self) -> None: ...
    def get_entries(self) -> list[MemoryEntry]: ...
    def get_entry(self, entry_id: str) -> MemoryEntry: ...
    def approve(self, entry_id: str, expected_updated_at: str) -> MemoryEntry: ...
    def edit(self, entry_id: str, fields: EditPayload, expected_updated_at: str) -> MemoryEntry: ...
    def delete(self, entry_id: str, expected_updated_at: str) -> None: ...
    def save(self, entry: MemoryEntry) -> MemoryEntry: ...  # create new pending entry
```

### State Machine (enforced in engine methods)

| From | To | Trigger | Side effects |
|------|-----|---------|-------------|
| pending | curated | `edit()` with `scope_agents` provided | `updated_at` set |
| curated | approved | `approve()` | `approved_at` set, `updated_at` set |
| approved | curated | `edit()` (any field change) | `approved_at` cleared, `updated_at` set |
| pending | *(hard delete)* | `delete()` | File removed from disk |
| curated | deleted | `delete()` | `state` set to deleted, `updated_at` set |
| approved | deleted | `delete()` | `state` set to deleted, `updated_at` set |
| deleted | *(nowhere)* | — | Terminal state, no transitions out |

### Models

```python
class MemoryCategory(StrEnum):
    DOMAIN_KNOWLEDGE = "domain-knowledge"
    BEHAVIOUR = "behaviour"
    PITFALL = "pitfall"
    PROCESS = "process"
    TOOL_USAGE = "tool-usage"
    GOAL = "goal"
    PERSONALITY = "personality"
    PREFERENCE = "preference"
    ENV_CONTEXT = "env-context"

class MemoryState(StrEnum):
    PENDING = "pending"
    CURATED = "curated"
    APPROVED = "approved"
    DELETED = "deleted"

class MemoryEntry(BaseModel):
    id: str                          # UUIDv4
    title: str                       # non-empty
    categories: list[MemoryCategory] # ≥1
    confidence: float                # 0.7–1.0
    state: MemoryState
    content: str                     # ≤1024 chars
    scope_agents: list[str]
    source_agent: str                # non-empty
    created_at: datetime
    updated_at: datetime
    approved_at: datetime | None
```

### Validation Rules

- **Lenient on read:** Parse existing files accepting minor invariant violations (e.g., stale `approved_at` on deleted entries, missing optional fields). Entries that pass YAML parse and have a valid `id` are returned.
- **Strict on write:** All mutations enforce the full Pydantic model. Content ≤1024 chars, ≥1 category, confidence in range, non-empty title/source_agent, valid state transition.
- **Unparseable files:** Skip entirely. Report count as `parse_errors` in engine metadata.
- **Duplicate UUIDs:** Keep the entry with the later `updated_at`. Log a warning. Surface count in metadata.

### File I/O Requirements

- YAML parsing via `ruamel.yaml` (safe load only)
- Split-on-`---` delimiter pattern (frontmatter + markdown body)
- Atomic writes: temp file + rename
- Path containment: `resolved_path.is_relative_to(memory_dir)` assertion on every file operation
- Reject symlinks: check `Path.is_symlink()` before read/write/delete
- File size bound: skip files >8KB
- `MtimeScanCache` pattern for skip-reparsing when directory mtime unchanged

### OCC (Optimistic Concurrency Control)

Mutation methods accept `expected_updated_at`. If the on-disk `updated_at` differs, raise `ConcurrencyError`. MCP tools may bypass OCC (they operate in agent-driven serial contexts).

### Error Types

```python
class NotFoundError(Exception): ...      # entry ID not on disk
class ConcurrencyError(Exception): ...   # expected_updated_at mismatch
class ValidationError(Exception): ...    # field validation failure
class TransitionError(Exception): ...    # invalid state transition
```

## Cockpit Backend API

### Routes (`routes/memory.py`)

| Method | Path | Purpose | Response |
|--------|------|---------|----------|
| GET | `/api/memories` | Return all entries (including deleted) + metadata | `{ entries: [...], parse_errors: int }` |
| POST | `/api/memories/{id}/approve` | Approve entry | `{ entry: {...} }` |
| POST | `/api/memories/{id}/edit` | Edit entry fields | `{ entry: {...} }` |
| POST | `/api/memories/{id}/delete` | Delete entry (state-dependent) | `{ success: true }` |

### Request/Response Shapes

```python
# GET /api/memories response
class MemoriesResponse(BaseModel):
    entries: list[MemoryEntryResponse]
    parse_errors: int

# POST /api/memories/{id}/approve request
class ApproveRequest(BaseModel):
    expected_updated_at: str  # ISO 8601

# POST /api/memories/{id}/edit request
class EditRequest(BaseModel):
    expected_updated_at: str
    title: str | None = None
    categories: list[MemoryCategory] | None = None
    confidence: float | None = None
    scope_agents: list[str] | None = None
    content: str | None = None

# POST /api/memories/{id}/delete request
class DeleteRequest(BaseModel):
    expected_updated_at: str
```

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 404 | Entry not found (or unparseable) |
| 409 | OCC conflict (`expected_updated_at` mismatch) |
| 422 | Validation error (invalid field values or state transition) |

### Integration Patterns

- DI: `Depends(get_memory_engine)` providing `MemoryEngine` instance
- Caching: `MtimeScanCache` keyed on memory directory mtime
- Error handling: catch engine exceptions → map to HTTP status codes via existing error envelope pattern
- No git auto-commit on mutations
- Config: `MEMORY_DIR` env var (default `.owlbear/memory/`)

## Cockpit Frontend

### Component: MemoryTab

Top-level route component (plugs into #1638 route config entry when available).

### List View

- Display all non-deleted entries by default (client-side filter)
- Each row: title, categories (PTag chips), confidence, state badge (color-coded), scope_agents
- Sort: state priority (pending → curated → approved → deleted), then `created_at` ascending within group
- Filter controls:
  - State: multi-select (PMultiSelect), defaults to pending + curated + approved
  - Category: multi-select (PMultiSelect)
  - Scoped agent: dropdown
  - Text search: PInputSearch across title and content

### Detail (Inline Accordion)

- PAccordion expand on row click
- Shows: full content (sanitized markdown), all metadata (id, source_agent, scope_agents, categories, confidence, state, created_at, updated_at, approved_at)
- Action buttons displayed within the expanded accordion based on entry state

### Actions (State-Dependent)

| Action | Visible when | Confirmation | Effect |
|--------|-------------|-------------|--------|
| Approve | state = curated | None (natural deliberation via accordion expand) | curated → approved |
| Edit | state = pending \| curated \| approved | Inline warning for approved entries ("will require re-approval") | Opens edit form; approved → curated on save |
| Delete | state = pending \| curated \| approved | Confirmation dialog (both hard and soft delete) | pending = hard delete; curated/approved = soft delete |

### Edit Form

- Inline within the accordion (no modal/drawer)
- Editable fields: title, categories, confidence, scope_agents, content
- Immutable (display only): id, source_agent, created_at, updated_at, approved_at, state
- Content textarea with character counter (max 1024)
- Save sends `POST /api/memories/{id}/edit` with `expected_updated_at`

### Data Freshness

- Refetch after every mutation (immediate UI update from response)
- Refetch on tab focus (catches agent-driven background changes)
- No SSE in V1

### Markdown Rendering

- Render entry content as markdown in the detail view
- Use rehype-sanitize (or equivalent allowlist sanitizer)
- Strip all HTML tags except safe inline formatting (strong, em, code, a with href validation)
- No `dangerouslySetInnerHTML`
- No remote image loading (strip `img` tags or restrict to data: URIs)

### Nav-Rail Integration (when #1638 lands)

- Route config entry: path `/memories`, label "Memory", appropriate icon
- Badge: pending entry count (only visible when count > 0)
- Lazy loaded via `React.lazy()` + Suspense

## Dependencies

- **Blocks on:** #1638 (frontend component mounting only)
- **Backend independent:** Engine extraction + API routes have no frontend dependency

## Deferred (Post-V1)

- SSE live-updates for memory events
- Approval provenance (`approved_by` field)
- Remote image blocking (beyond tag stripping)
- Bulk approve/delete
- Memory diff view
- Memory creation from cockpit
- Link memories to tasks
- Memory statistics dashboard
