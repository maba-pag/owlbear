# Research Notes — Cockpit Memory Tab

## Verified Findings

### Memory File Format
- Files at `.owlbear/memory/{slug}-{6-char-suffix}.md`
- YAML frontmatter: `id` (UUIDv4), `title`, `categories` (list of MemoryCategory enum), `confidence` (0.7–1.0), `state` (pending|curated|approved|deleted), `scope_agents` (list[str]), `source_agent`, `created_at`, `updated_at`, `approved_at` (nullable)
- Markdown body after `---` delimiter, stripped on load, max 1024 chars
- 103 entries: 56 curated, 30 approved, 15 deleted, 2 pending

### Memory Categories (MemoryCategory StrEnum)
`domain-knowledge`, `behaviour`, `pitfall`, `process`, `tool-usage`, `goal`, `personality`, `preference`, `env-context`

### State Machine Transitions
- pending → curated: auto-promotes when `scope_agents` provided during curate
- approved → curated: auto-downgrades on re-curate
- curated → approved: explicit `approve_memory()` call, sets `approved_at` timestamp
- pending → hard-delete: file removed from disk
- curated/approved → deleted: soft-delete, file retained with `state: deleted`
- deleted → nowhere (locked)

### Cockpit File Reading Patterns
- Uses `ruamel.yaml` for YAML parsing (preserves formatting on rewrites)
- Split-on-`---` delimiter pattern, same as kanban/decisions
- `MtimeScanCache` in `cache.py`: Blake2b hash of (filename + mtime_ns), skips re-parse when signature unchanged
- DI pattern: `Annotated[Type, Depends(get_engine)]` for dependency injection
- Route pattern: `APIRouter()`, `ConfigDict(extra="forbid")` for strict request validation, catch `YAMLError`/`ValueError`/`TypeError`, return `dict[str, object]`

### Tab Infrastructure (#1638)
- Route config array: declarative entries (path, label, icon, component). Adding a tab = adding an entry.
- Nav-rail with `useNavigate()` handlers, `aria-current="page"` on active
- React Router `<Routes>` in Shell, lazy loading via `React.lazy()` + Suspense
- Route-conditional sidecar (kanban-only)
- All tasks still in research status, parent #1638 depends on consolidation #1649

### PDS Components Available for Memory Tab
- `PMultiSelect`/`PMultiSelectOption`: filter dropdowns (state, categories, agent)
- `PInputSearch`: text search
- `PTag`: category badges
- `PButton`: action buttons (approve, edit, delete)
- `PAccordion`: expandable detail sections
- `PText`: text formatting
- CSS modules (`.css` next to `.tsx`)

### Cockpit Dependencies
- Already depends on `owlbear-kanban` as workspace package (engine + models)
- Can add workspace dependencies via `[tool.uv.sources]`

## Candidate Implications

### Engine Extraction Tension
The kanban engine lives in a separate package (`serve/kanban/`) that both the cockpit and `serve/mcp-kanban/` depend on. The memory engine lives **inside** the MCP server package (`serve/mcp-memory/`). No separate `serve/memory/` package exists.

Options for the cockpit to access memory data:
1. **Read files directly** — cockpit reimplements YAML frontmatter parsing for memory files (same `ruamel.yaml` split-on-`---` pattern used everywhere). Simple for reads, duplication risk for mutations (state machine logic).
2. **Extract memory engine** — create `serve/memory/` as a standalone package (like kanban), move engine + models there. Both cockpit and mcp-memory depend on it. Eliminates duplication but adds a package extraction task.
3. **Import from MCP package** — add `owlbear-mcp-memory` as a cockpit dependency. Fastest path but may violate architecture intent (MCP servers shouldn't be importable libraries).

### Client-Side Filtering
At ≤500 entries with ≤1KB each, entire dataset is <500KB. Single `GET /api/memories` returning all entries, filtered in React. Eliminates backend query parameters, pagination, and server-side filter logic. Backend becomes trivially simple: one read-all endpoint + mutation endpoints.

### State Machine Duplication Scope
If cockpit does full mutations (approve + edit + delete), it must implement:
- Approve guard: only curated → approved
- Edit downgrade: approved → curated on field change
- Delete: pending → hard-delete, curated/approved → soft-delete
- Content validation: ≤1024 chars, ≥1 category, confidence range
- Auto-promote: pending → curated when scope_agents provided

With engine extraction (option 2), all this lives in one place. Without it, the cockpit reimplements ~100 lines of transition logic.

## Open Research Questions

1. **Architecture ruling on memory engine location**: should memory follow the kanban pattern (separate engine package) or stay inside the MCP server? This affects cockpit's import strategy and duplication risk.
2. **Detail view pattern**: inline expand (PAccordion) vs separate route. At 1024 chars max, inline is viable. Mediation should decide based on the overall tab UX feel.
3. **SSE integration**: should the memory tab use SSE events for live updates (like kanban does for `activity-changed`), or is poll-on-focus sufficient for memory data?
4. **Deleted entries visibility**: should the tab show deleted entries? They're soft-deleted and retained on disk. The input document suggests "read-only archive view, if shown at all."
5. **Nav-rail badge**: should the memory tab show a pending count badge (like decisions tab), or is that premature with typically ≤2 pending entries?
