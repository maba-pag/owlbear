# Research Notes — Memory Module

## Verified Findings

### 1. Knowledge MCP and Memory MCP are fundamentally different systems

| Dimension | mcp-knowledge | mcp-memory |
|-----------|---------------|------------|
| Purpose | External KB (docs, URLs, entities) | Agent introspection (learnings, preferences) |
| Query model | Semantic search (vector + graph hybrid) | Scope-based retrieval (agent/project filter) |
| Storage | Qdrant vectors + SQLite graph | Single SQLite table |
| Complexity | LLM-heavy (extraction, synthesis, embedding) | Trivial (validation + CRUD) |
| Tools | 14 | 5 |
| Lifecycle | Continuous ingestion, periodic refresh | One-shot write, read-on-demand |

**Conclusion:** Merge is architecturally wrong. No functional overlap. Different query semantics, lifecycles, and operational models.

### 2. The "0 tools discovered" bug — probable root cause

The server starts and processes `ListToolsRequest` but returns 0 tools. Two hypotheses:

1. **`MEMORY_TOOLS_EXCLUDE` env var is set** (excludes tools by name) — if set to all 5 tool names, result is 0. Check with `echo $MEMORY_TOOLS_EXCLUDE`.
2. **Module-level `_apply_tool_exclusions(mcp)` runs before tools are registered** — if import order causes the exclusion function to fire before decorators attach, tools are removed before they exist.

The knowledge server calls `_apply_tool_exclusions` inside `app_lifespan()` (after startup). The memory server calls it at module import time. This timing difference may be the bug.

### 3. The kanban pattern (markdown + YAML frontmatter) is a proven storage model

The kanban module stores tasks as individual `.md` files with YAML frontmatter (id, title, status, priority, tags, etc.). Key properties:
- Atomic writes via temp file + rename
- Frontmatter = Pydantic model (round-trip safe)
- Git-native (diffable, mergeable, human-readable)
- Concurrency via OCC (optimistic concurrency control)

This pattern is directly applicable to memory entries: each entry as a `.md` file with confidence, category, agent-scope, approval-state in frontmatter, content in body.

### 4. Current `/memories/repo/` files are unstructured but functional

11 curated topic files, ~25KB total. Agents read them at startup. Curation runs every ~2hr. Current state is the result of a 150→11 reduction audit. The system works but has no metadata layer — no confidence, no category, no agent-scope filtering.

## Candidate Implications

### Option A: Fix + Keep (as-is)

Fix the transport bug (likely env var or import timing). Module becomes operational immediately.
- **Pro:** Fastest path to operational; all infrastructure already built
- **Con:** Keeps SQLite (not diffable, not human-readable); coexistence complexity with VS Code memory
- **Risk:** Still unclear if the module delivers measurable value over file-based approach

### Option B: Restructure to markdown+frontmatter (kanban pattern)

Replace SQLite with per-entry `.md` files. Keep MCP tools but back them with file-based storage.
- **Pro:** Git-native, diffable, human-readable; proven pattern from kanban module; tools still provide filtered retrieval
- **Con:** More implementation work; need to decide file layout; query performance different from SQLite
- **Risk:** At scale (1000+ entries) file-based may be slower than SQLite for filtered queries

### Option C: Cut module + enhance `/memories/repo/`

Drop `mcp-memory`. Add YAML frontmatter to existing repo memory files for metadata.
- **Pro:** Simplest; no MCP server to maintain; zero coexistence complexity
- **Con:** Loses queryable retrieval (agents load everything or parse frontmatter); loses approval workflow; curation stays manual
- **Risk:** May not scale; agents get no read-time filtering

### Option D: Restructure + merge into existing `/memories/repo/` directory

Apply the kanban pattern to the `/memories/repo/` directory itself. Keep MCP tools but they now read/write to the same directory agents already load from.
- **Pro:** Single source of truth; no "promotion" step; git-native; filtered retrieval via MCP tools; agents can also read raw files directly
- **Con:** Need to manage the interaction between MCP writes and VS Code memory tool expectations
- **Risk:** VS Code may not like structured frontmatter in its repo memory directory

## Open Research Questions

1. ~~Does VS Code's memory tool interact with `/memories/repo/` at all?~~ **Answered:** No — VS Code uses hidden workspace-storage, these are separate systems.
2. ~~What is the actual failure mode when `ListToolsRequest` returns 0?~~ **Hypothesis:** Check `MEMORY_TOOLS_EXCLUDE` env var; or module-level `_apply_tool_exclusions()` timing issue vs. knowledge server's lifespan-scoped approach.
3. At what scale does file-based memory become slower than SQLite for filtered queries? Kanban handles ~100-200 tasks; memory might need 500+.
4. What storage layout works best for markdown+frontmatter entries? Per-entry files (like kanban tasks/) vs. grouped topic files with frontmatter per section?
5. How should the restructured module interact with the existing curator agent workflow?

## Additional Finding: GitHub copilotMemory.enabled

Per workspace research from March 2026 (`copilot-memory.md`):
- `github.copilot.chat.copilotMemory.enabled` is **GitHub cloud storage**, NOT in-repo files
- 28-day auto-expiry
- No instruction-based boundary control (toggle only)
- Cross-surface (VS Code, github.com, CLI) but not committable
- Recommended disabled for privacy and local-first architecture

**Implication:** "Wait for GitHub to ship committable memory" (Option E) is based on a false premise. The feature provides cross-surface cloud persistence, not in-repo committable storage. Custom module remains the only path to committable, quality-gated agent memory.
