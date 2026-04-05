# memory-mcp Server Architecture Design

> **Owning task:** #387 — Design per-agent institutional knowledge system via dedicated memory-mcp server
> **Date:** 2026-04-01 **Status:** Complete

## 1. Context and Question

OwlBear needs per-agent institutional knowledge that persists across sessions and projects. The current `/memories/repo/inbox/` system is unscoped, not git-tracked, not auto-loaded, and not cross-project. #387 designs a dedicated memory-mcp server separate from knowledge-mcp. Binding constraints from DR #428 (resolved): adopt patterns 1 (fact schema), 2 (confidence gating), 4 (soft-delete, customized), 6 (category taxonomy). Patterns 3 (dedup) and 5 (token-budgeted injection) were not mentioned in the DR and require separate approval.

## 2. Sources Studied

| # | Source | Path/URL | Relevance |
|---|--------|----------|-----------|
| S1 | #499 schema definitions | `docs/research/deer-flow-memory-patterns-schema-definitions.md` | .95 |
| S2 | DR #428 resolved | `docs/decisions/resolved/428-adopt-deer-flow-memory-patterns.md` | 1.0 |
| S3 | deer-flow deep dive | `docs/research/deer-flow-memory-subagent-deep-dive.md` | .85 |
| S4 | mcp-kanban server | `packages/mcp-kanban/src/owlbear_mcp_kanban/server.py` | .90 |
| S5 | mcp-knowledge server | `packages/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` | .90 |
| S6 | mcp-project server | `packages/mcp-project/src/owlbear_mcp_project/server.py` | .85 |
| S7 | Mem0 open-source | `github.com/mem0ai/mem0` (API, scoping via user_id/agent_id) | .75 |
| S8 | setup.py (MCP wiring) | `scripts/setup.py` | .85 |
| S9 | agent-common.instructions | `instructions/agent-common.instructions.md` L248 (inbox pattern) | .90 |
| S10 | copilot-instructions.md | `.github/copilot-instructions.md` (memory governance) | .85 |

## 3. Analysis

### 3A. Storage Backend

| Criterion | SQLite (rec) | JSON files | YAML files |
|-----------|-------------|------------|------------|
| Query support | SQL WHERE/ORDER BY | manual parse | manual parse |
| Concurrent access | WAL mode + busy_timeout | file locking | file locking |
| Consistency with project | mcp-knowledge uses SQLite (S5) | deer-flow uses JSON (S3) | no prior art |
| Dependencies | stdlib `sqlite3` | stdlib `json` | PyYAML |
| Portability | single .db file | directory of files | directory of files |
| Human-readable | no (binary) — mitigated by `list_entries` tool | yes | yes |

**Recommendation (.90):** SQLite via stdlib `sqlite3` + `asyncio.to_thread` (matching mcp-knowledge pattern, S5 L153-161). WAL mode for concurrent read/write from parallel agent sessions.

### 3B. Entry Schema (12 fields)

Based on #499 (S1) with DR-approved patterns. Two fields flagged as needing separate approval:

| Field | Type | DR basis | Notes |
|-------|------|----------|-------|
| `id` | UUID4 str | Pattern 1 | Primary key |
| `content` | str | Pattern 1 | The conclusion/learning |
| `category` | enum | Pattern 6 | preference/knowledge/context/behavior/goal |
| `confidence` | float 0.0-1.0 | Pattern 2 | Agent-assigned, threshold-gated at 0.7 |
| `created_at` | datetime UTC | Pattern 1 | Immutable |
| `updated_at` | datetime UTC | OwlBear ext | Last edit timestamp |
| `source` | str | Pattern 1 | Agent name + task ID (e.g. `builder:#480`) |
| `scope_agent` | str or NULL | OwlBear 4D | NULL = all agents |
| `scope_project` | str or NULL | OwlBear 4D | NULL = all projects |
| `approval_state` | enum | OwlBear ext | pending/approved/deleted |
| `deleted_at` | datetime or NULL | Pattern 4 (custom) | Soft-delete only; user-only permanent delete |
| `content_hash` | str | **Pattern 3 — NOT in DR** | Needs supplemental approval |

### 3C. Multi-Dimensional Scoping Model

Two nullable scope fields create 4 dimensions orthogonally (S1 §3A):

| scope_agent | scope_project | Effective scope | Example |
|-------------|---------------|-----------------|---------|
| NULL | NULL | General | "uv run python -m pytest is more reliable" |
| NULL | "myproject" | Project-specific | "this project uses Protocol-based DI" |
| "builder" | NULL | Agent-specific | "always verify tests FAIL before implementing" |
| "builder" | "myproject" | Agent+project | "packages/knowledge uses bare --cov only" |

**Query resolution:** `get_knowledge` returns the union of all matching scopes for the given agent+project, sorted by specificity (agent+project first, general last), then by confidence desc within each tier.

**Agent identity:** Agents pass `agent_id` explicitly (their own name). The MCP server resolves project identity from `owlbear-project.json` at startup (same as mcp-project, S6 L65-72). Agents know their name but don't control scoping logic.

**Project identity:** `AppContext.project_name` populated from `owlbear-project.json` during lifespan startup. Falls back to `OWLBEAR_MEMORY_PROJECT` env var, then to `None` (no project scoping).

### 3D. Storage Location Configuration

| Mode | Config | Use case |
|------|--------|----------|
| Central (default) | `OWLBEAR_MEMORY_DB_PATH` unset: `../owlbear/data/memory/memory.db` | Knowledge accumulates across projects |
| In-repo | `OWLBEAR_MEMORY_DB_PATH=data/memory/memory.db` | Self-contained project, git-trackable |

**Single database path** — not dual-path. Cross-project aggregation happens naturally with the central default (all projects share one DB, differentiated by `scope_project`). In-repo mode sacrifices cross-project for portability. YAGNI on dual-path hybrid.

`setup.py` (S8) adds a 4th MCP server entry with optional `env` block for `OWLBEAR_MEMORY_DB_PATH`.

### 3E. MCP Tool Interface (4 tools)

| Tool | Params | Returns | Annotations |
|------|--------|---------|-------------|
| `get_knowledge` | `agent_id` (str), `categories?` (str), `min_confidence?` (float), `limit?` (int) | List of entries sorted by scope-specificity then confidence | readOnly, idempotent |
| `record_learning` | `content` (str), `category` (str), `confidence` (float), `agent_id` (str), `scope_project?` (str), `scope_agent?` (str) | Created entry ID or validation error | not readOnly |
| `list_entries` | `agent_id?` (str), `category?` (str), `status?` (str), `include_deleted?` (bool) | Full entry list with metadata (for curation) | readOnly, idempotent |
| `mark_for_deletion` | `entry_id` (str) | Success/error | not readOnly |

**Approval mechanism:** No agent-facing `promote_entry` tool. Approval is a privileged operation: the curator agent writes recommendations to its curation report, and the user approves via CLI tool or direct DB edit. This matches #387 AC: "who can approve (user via CLI, curator agent, or both)." A `promote_entry` tool would be added to the curator agent's toolset only if needed — not exposed to all agents.

**Token budgeting:** `get_knowledge` accepts `limit` (entry count) rather than `max_tokens`. Token counting requires a tokenizer dependency that OwlBear doesn't have. Entry count is simpler, and the agent can adjust based on prompt budget. If pattern 5 is approved later, token-based limiting can be added as a parameter alongside `limit`.

### 3F. Approval Workflow

```
Agent writes → pending
Curator reviews → recommends promote/delete
User approves → approved (or user soft-deletes → deleted)
```

- `pending`: visible in `get_knowledge` results (sorted after `approved` entries)
- `approved`: full visibility, highest sort priority
- `deleted`: hidden from `get_knowledge`, visible via `list_entries(include_deleted=True)` for user review
- **Only users** may permanently DELETE rows from the database (DR #428 custom: "only user may actually delete")

### 3G. Auto-Loading Mechanism

**Recommendation:** Agent-common instruction adds Step 0 to every agent workflow:

```
Before starting work, call `get_knowledge` with your agent name to load institutional knowledge.
```

This is the simplest approach (S9, S10). Alternatives considered:
- MCP prompt injection via system prompt: requires VS Code extension changes, not feasible
- Per-skill step 0: too many files to update, agent-common is the single point of change

### 3H. Write Mechanism

Agents call `record_learning` at task end (replacing the current `memory create /memories/repo/inbox/` step in agent-common L248, S9). During migration, agents write to BOTH systems. After verification, the inbox pattern is removed from agent-common.

### 3I. Curation Interface

Curator agent uses `list_entries` to review pending entries. Curation actions:
- **Promote:** Curator writes recommendation to curation report; user sets `approval_state=approved` via CLI
- **Soft-delete:** Curator calls `mark_for_deletion` for noise entries
- **Cross-pollinate:** Curator calls `record_learning` with broader scope (e.g., copy agent-specific insight to general scope)

### 3J. Cross-Project Aggregation

With central storage (default), all projects share one SQLite database. The `scope_project` field differentiates entries. `get_knowledge` returns: general entries + entries matching the current project + entries matching the agent + entries matching agent+project. Cross-project knowledge (scope_project=NULL) is automatically available everywhere.

### 3K. Deer-Flow Pattern Assessment

| Pattern | DR Status | Design Action |
|---------|-----------|---------------|
| 1: Fact schema | Approved unchanged | Adopted in §3B |
| 2: Confidence gating | Approved unchanged | Adopted: 0.7 threshold, write-time rejection |
| 3: Content dedup | **Not in DR** | Flagged in DR for this task |
| 4: Max-capacity pruning | Approved (custom) | Soft-delete only (§3F) |
| 5: Token-budgeted injection | **Not in DR** | Flagged in DR for this task; `limit` param as interim |
| 6: Category taxonomy | Approved unchanged | Adopted: 5 categories (§3B) |

### 3L. Migration Path

| Phase | Action | Risk |
|-------|--------|------|
| 1: Build | Create mcp-memory package alongside existing `/memories/repo/` | None — parallel systems |
| 2: Dual-write | Agent-common instructs agents to write to both inbox AND `record_learning` | Low — redundant data |
| 3: Bulk import | CLI tool converts existing `/memories/repo/` files to memory.db entries | Medium — category mapping needed |
| 4: Cut over | Remove inbox pattern from agent-common; `get_knowledge` replaces manual memory reads | Medium — verify all agents migrated |
| 5: Cleanup | Archive `/memories/repo/inbox/`; update memory governance in copilot-instructions.md | Low |

**`/memories/` coexistence:** The built-in memory tool (`/memories/`, `/memories/session/`) remains for user-facing notes and session context. The MCP server replaces ONLY `/memories/repo/inbox/` (agent institutional knowledge). Copilot-instructions.md memory governance must be updated to clarify this boundary.

**Category mapping:** Current inbox uses informal labels (problems_faced, workarounds_applied, patterns_discovered, time_sinks, quality_gaps). These map to the DR-approved taxonomy: problems_faced→knowledge, workarounds_applied→knowledge, patterns_discovered→behavior, time_sinks→context, quality_gaps→context.

## 4. Recommendation (.78 confidence)

SQLite-backed memory-mcp server with 4 MCP tools, 4D scoping via nullable agent/project fields, single-path configurable storage, approval workflow (pending/approved/deleted with user-only permanent deletion), auto-loading via agent-common Step 0. Follows existing MCP server patterns (AppContext, lifespan, `sqlite3` + `asyncio.to_thread`, ToolAnnotations).

**Open questions requiring user decision:** Patterns 3 (content dedup) and 5 (token-budgeted injection) from deer-flow were not addressed in DR #428. Both are recommended — dedup prevents duplicates, token budgeting ensures usable response sizes — but they need explicit approval. See decision request.

Challenge: reconsider — confidence in original: .62. Challenger surfaced valid gaps in agent identity mechanism (addressed: explicit `agent_id` param), DR compliance for patterns 3/5 (addressed: flagged in DR), promote_entry tool (addressed: removed, approval is privileged), and dual-path YAGNI (addressed: single-path). Revised confidence .78 after integrating challenge feedback.

## 5. Follow-up Tasks

T3 classification — new capability (memory-mcp server), new package, modifies agent instructions. Blocking decision request created at `docs/decisions/pending/387-memory-mcp-architecture.md`.

```
kanban\kanban-md.exe create "Scaffold mcp-memory package" --priority needed --status ideation --tags "scope:agents,phase-2" --body "Create packages/mcp-memory/ following existing MCP server patterns (mcp-kanban, mcp-knowledge). Package: owlbear-mcp-memory. Module: owlbear_mcp_memory. Entry point: __main__.py. See docs/research/memory-mcp-server-design.md. AC: - [ ] Package scaffolded with pyproject.toml, __init__.py, __main__.py, server.py, models.py - [ ] SQLite schema for memory_entries table (12 fields per design) - [ ] AppContext + lifespan pattern with WAL mode - [ ] setup.py updated to include 4th MCP server entry - [ ] pyproject.toml workspace member added - [ ] test_package_boundary.py ALLOWED_IMPORTS updated"
kanban\kanban-md.exe create "Implement memory-mcp tools" --priority needed --status ideation --tags "scope:agents,phase-2" --body "Implement 4 MCP tools per docs/research/memory-mcp-server-design.md sec 3E: get_knowledge, record_learning, list_entries, mark_for_deletion. AC: - [ ] get_knowledge returns entries sorted by scope-specificity then confidence - [ ] record_learning validates confidence >= 0.7, valid category, stores entry as pending - [ ] list_entries supports filtering by agent/category/status/include_deleted - [ ] mark_for_deletion sets approval_state=deleted and deleted_at - [ ] All tools have correct ToolAnnotations (readOnly, idempotent hints) - [ ] Project identity resolved from owlbear-project.json in AppContext"
kanban\kanban-md.exe create "Update agent-common for memory-mcp integration" --priority needed --status ideation --tags "scope:agents,phase-2" --body "Update agent instructions for memory-mcp auto-loading and write mechanism per docs/research/memory-mcp-server-design.md sec 3G-3H. AC: - [ ] agent-common.instructions.md adds Step 0: call get_knowledge with agent name - [ ] agent-common.instructions.md post-task reflection updated to call record_learning (dual-write with inbox during migration) - [ ] mcp-memory skill created for agent tool reference - [ ] copilot-instructions.md memory governance updated to clarify /memories/ vs mcp-memory boundary"
kanban\kanban-md.exe create "Build memory migration CLI tool" --priority important --status ideation --tags "scope:agents,phase-2" --body "CLI tool to bulk-import existing /memories/repo/ files into memory.db. Per docs/research/memory-mcp-server-design.md sec 3L. AC: - [ ] Script reads /memories/repo/inbox/*.md and established repo memory files - [ ] Category mapping: problems_faced/workarounds_applied to knowledge, patterns_discovered to behavior, time_sinks/quality_gaps to context - [ ] Entries created with approval_state=pending, confidence=0.7 (default) - [ ] Source field set to 'migration:filename' for traceability - [ ] Dry-run mode shows what would be imported without writing"
kanban\kanban-md.exe create "Design curator workflow for memory-mcp" --priority important --status ideation --tags "scope:agents,phase-2" --body "Update curator agent and curation-workflow skill for memory-mcp integration per docs/research/memory-mcp-server-design.md sec 3I. AC: - [ ] Curator agent updated to use list_entries for reviewing pending entries - [ ] Curator can call mark_for_deletion for noise entries - [ ] Curator can call record_learning to cross-pollinate insights to broader scopes - [ ] Curation report includes recommendations for user approval (promote to approved) - [ ] CLI or admin tool for user to batch-approve curator recommendations"
```
