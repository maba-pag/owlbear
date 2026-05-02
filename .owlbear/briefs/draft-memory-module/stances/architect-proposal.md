# Architect Proposal — Memory Module Restructure

## Design Summary

Replace `serve/mcp-memory/` SQLite storage with per-entry markdown files using YAML frontmatter, mirroring the kanban module's proven storage pattern. Storage location moves from `store/memory/memory.db` to `.owlbear/memory/entries/`. The MCP server thins to a file-backed CRUD layer with in-memory indexing. All 5 tools are preserved with compatible semantics.

The design prioritises: git-native storage, minimal module complexity, direct reuse of `storage_io.atomic_write`, and a data model that maps 1:1 from current SQLite fields to frontmatter keys.

---

## 1. File Layout

```
.owlbear/memory/
├── entries/           # one .md per memory entry
│   ├── a1b2c3d4-scope-filtering-pitfall.md
│   ├── e5f6g7h8-always-run-lint-before-commit.md
│   └── ...
└── config.yml         # minimal config (optional, future-proofing)
```

### Naming Convention

`{uuid-short}-{slug}.md`

- `uuid-short`: first 8 chars of the UUID (sufficient uniqueness at <200 scale; full UUID lives in frontmatter)
- `slug`: first 60 chars of content, slugified (`[^a-z0-9]+ → -`, strip leading/trailing `-`)
- Rationale: human-scannable filenames in `git log --stat` and directory listings

### Why not numeric IDs?

Kanban uses auto-incrementing integers because task ordering matters and humans reference tasks by number. Memory entries have no natural ordering and are never referenced by ID in conversation — UUIDs avoid collision on independent creation (e.g., two agents recording simultaneously).

---

## 2. Data Model

### Frontmatter Fields

```yaml
---
id: "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
category: knowledge          # preference | knowledge | context | behavior | goal
confidence: 0.85             # 0.7–1.0 (validated)
approval_state: approved     # pending | approved | deleted
source: builder              # agent_id that created the entry
scope_agent: builder         # nullable — scope filter for retrieval
scope_project: owlbear-dev   # nullable — scope filter for retrieval
created: "2026-04-15T10:30:00+00:00"
updated: "2026-04-20T14:22:00+00:00"
deleted_at: null             # ISO timestamp when soft-deleted, else null
---
```

### Body

Free-form markdown — the `content` field from the current model. No structural requirements beyond valid UTF-8 markdown.

```markdown
When reviewing engine tests, always check that `write_task_if_unchanged` is
tested with a stale timestamp — this catches OCC regressions that otherwise
slip through.
```

### Pydantic Model

```python
class MemoryEntry(BaseModel):
    id: str                    # full UUID
    category: Literal["preference", "knowledge", "context", "behavior", "goal"]
    confidence: float          # Field(ge=0.7, le=1.0)
    approval_state: Literal["pending", "approved", "deleted"] = "pending"
    source: str                # agent_id that recorded
    scope_agent: str | None = None
    scope_project: str | None = None
    created: str               # ISO 8601 UTC
    updated: str               # ISO 8601 UTC
    deleted_at: str | None = None
    body: str = ""             # content, not in frontmatter
```

Field naming aligns with kanban (`created`/`updated` not `created_at`/`updated_at`) for pattern consistency. The `source` field replaces the overloaded `agent_id` write parameter from the current tool API — it records who created the entry.

---

## 3. Engine Architecture

### Module: `engine.py`

Single class `MemoryEngine` — the only component that touches disk.

```python
class MemoryEngine:
    def __init__(self, memory_dir: Path) -> None:
        self._entries_dir = memory_dir / "entries"
        self._entries_dir.mkdir(parents=True, exist_ok=True)
        self._entries: list[MemoryEntry] = []
        self._index: dict[str, MemoryEntry] = {}  # id → entry
        self._reload()

    def _reload(self) -> None:
        """Full scan — parse all .md files, validate, populate index."""

    def get(self, entry_id: str) -> MemoryEntry | None: ...
    def query(self, *, agent_id: str, ...) -> list[MemoryEntry]: ...
    def create(self, entry: MemoryEntry) -> Path: ...
    def update(self, entry: MemoryEntry) -> Path: ...
```

### Load Strategy

Full in-memory load on startup (all files parsed, validated, indexed). At <200 files this is <50ms — no lazy loading, no caching complexity.

### Query Strategy

Pure Python filtering on the in-memory list. The `query()` method applies:
1. Exclude `approval_state == "deleted"` (unless `include_deleted=True`)
2. Scope matching: entries where `scope_agent` is None OR matches `agent_id`; same for `scope_project`
3. Optional category filter
4. Optional min_confidence filter
5. Sort by scope-specificity tier → approval_state (approved first) → confidence DESC
6. Limit

This replicates the current SQL query logic without SQL. At <200 entries, linear scan with sort is negligible.

### Write Strategy

Reuse `storage_io.atomic_write` from the kanban module (import directly — it's a pure utility with no kanban coupling). Sequence:
1. Validate entry via Pydantic
2. Render frontmatter (ordered fields) + `---\n` + body
3. `atomic_write(path, content)`
4. Update in-memory index

### Concurrency

Not needed at this scale. Memory entries are written by one agent at a time (MCP is single-session). No OCC, no file locking. If multi-session becomes real, add `write_if_unchanged` later (kanban pattern exists to copy).

---

## 4. Tool API Mapping

### `get_knowledge(agent_id, limit, categories, min_confidence)`

Maps to `engine.query(agent_id=agent_id, limit=limit, categories=categories, min_confidence=min_confidence)`. Returns list of dicts (entry model dumps). No signature change needed.

### `record_learning(agent_id, content, category, confidence, scope_agent, scope_project)`

1. Validate confidence ≥ 0.7, category valid
2. Generate UUID, timestamp
3. Build `MemoryEntry(id=uuid, source=agent_id, body=content, ...)`
4. `engine.create(entry)` → atomic write to file
5. Return entry ID string

Signature unchanged. `agent_id` parameter becomes `source` internally.

### `list_entries(agent_id, category, status, include_deleted)`

Maps to `engine.query(...)` with relaxed scope (no scope-tier sorting, just direct field matching). Returns list of dicts or `"[]"` string for empty (preserving FastMCP compatibility).

### `set_approval_state(entry_id, new_state)`

1. `engine.get(entry_id)` — raise ToolError if None
2. Validate transition against `_VALID_TRANSITIONS`
3. Mutate `approval_state`, set `updated`, set `deleted_at` if `new_state == "deleted"`
4. `engine.update(entry)` → atomic rewrite of file
5. Return success message

### `mark_for_deletion(entry_id)`

1. `engine.get(entry_id)` — raise ToolError if None
2. If already deleted → return no-op message
3. Set `approval_state = "deleted"`, `deleted_at = now`, `updated = now`
4. `engine.update(entry)` → atomic rewrite
5. Return success message

---

## 5. Migration Path

### One-shot script: `migrate.py` (already exists as a file — repurpose)

```
uv run python -m owlbear_mcp_memory.migrate
```

1. Open SQLite `store/memory/memory.db`
2. Read all rows from `memory_entries`
3. For each row: build `MemoryEntry`, generate slug from content, write to `.owlbear/memory/entries/`
4. Print summary (N entries migrated, any validation failures)
5. Do NOT delete the SQLite file — leave for manual cleanup after verification

### Rollback

SQLite file remains untouched. If migration fails or new module is broken, revert code and data is still there.

### Empty-state handling

If no SQLite file exists (fresh install), engine starts with empty `entries/` directory. No migration needed.

---

## 6. Package Structure

```
serve/mcp-memory/
├── pyproject.toml
├── README.md
├── src/
│   └── owlbear_mcp_memory/
│       ├── __init__.py        # package marker
│       ├── __main__.py        # entry point (unchanged)
│       ├── models.py          # MemoryEntry Pydantic model
│       ├── engine.py          # MemoryEngine (load, query, create, update)
│       ├── storage_io.py      # RE-EXPORT from owlbear_kanban OR inline copy
│       ├── server.py          # FastMCP app, lifespan, AppContext
│       ├── tools.py           # 5 MCP tool functions
│       └── migrate.py         # SQLite → files one-shot migration
└── tests/
    └── ...
```

### `storage_io.py` — Import vs. Copy

**Position: inline copy.** The kanban `atomic_write` is 40 lines with zero dependencies beyond stdlib. Importing from `owlbear_kanban` creates a cross-package dependency that doesn't exist today and shouldn't. Copy the function, attribute the source in a comment. If a third package needs it later, extract to a shared `owlbear-storage-utils` micro-package then.

### Removed Files

- `approve.py` — its logic folds into `set_approval_state` tool (already does)
- SQLite connection management — gone entirely
- `asyncio.to_thread` wrappers — gone (file I/O at this scale is fast enough synchronous; tools can stay async with trivial `await asyncio.to_thread(engine.create, entry)` if needed for MCP contract)

---

## 7. Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `MEMORY_DIR` | `.owlbear/memory` | Root directory for memory storage |
| `MEMORY_TOOLS_EXCLUDE` | `""` | Comma-separated tool names to hide (existing pattern) |
| `OWLBEAR_PROJECT` | basename of cwd | Project name for `scope_project` default |

### Resolution in lifespan

```python
@asynccontextmanager
async def app_lifespan(_server: FastMCP):
    memory_dir = Path(os.environ.get("MEMORY_DIR", ".owlbear/memory"))
    project_name = os.environ.get("OWLBEAR_PROJECT", Path.cwd().name)
    _apply_tool_exclusions(_server)
    engine = MemoryEngine(memory_dir)
    yield AppContext(engine=engine, project_name=project_name)
```

No config file needed at this scale. `config.yml` in the directory is reserved for future use (e.g., custom categories, retention policies) but not implemented now.

---

## Key Structural Choices

| Choice | Rationale |
|--------|-----------|
| Full in-memory load, no cache invalidation | <200 entries, <50ms parse, single-session MCP — complexity not justified |
| UUID-based filenames (not sequential int) | No natural ordering; concurrent creation by different agents; no ID coordination needed |
| Inline `atomic_write` copy | Avoids cross-package dependency for 40 lines of stdlib code |
| No OCC/locking | Single MCP session, one writer at a time; add later if needed |
| `entries/` subdirectory | Keeps root clean for future `config.yml`, index files, migration markers |
| Sync file I/O wrapped in `asyncio.to_thread` | MCP tools are async; file ops are <1ms at this scale but contract requires async |
| Slug from content, not title | Memory entries have no title field; first 60 chars of body slugified |

---

## Trade-offs

| Trade-off | Accepted cost | Gained benefit |
|-----------|---------------|----------------|
| No SQL query optimisation | Linear scan on every query | Zero external dependencies, human-readable storage |
| File-per-entry at scale | Directory with 200 `.md` files | Git-diffable, individually editable, mergeable |
| No schema migration framework | Manual script for one-shot migration | No runtime migration complexity |
| Duplicated `atomic_write` | 40 lines of code duplication | Package independence |

---

## Domain Rationale

This design follows the kanban module exactly where the patterns apply (atomic writes, frontmatter validation, in-memory load) and diverges only where the domain differs:

- **UUIDs not ints** — memory entries are created independently, never referenced by number
- **No OCC** — single-session writer, no concurrent mutation risk
- **No corruption detection** — entries are simpler (no cross-references, no status FSM beyond approval_state)
- **No archive directory** — soft-delete via `approval_state` is sufficient; physical deletion is a future curator concern

The result is a module that is ~60% thinner than the kanban engine while maintaining the same structural guarantees (atomic writes, Pydantic validation, git-native storage).

---

## Confidence

**0.88** — High confidence in the structural design. The kanban pattern is proven at this scale. Minor uncertainty on slug generation from content (might produce poor slugs for short entries) and on whether `asyncio.to_thread` wrapping is necessary for <1ms file ops (MCP contract says yes, performance says irrelevant).
