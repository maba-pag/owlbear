# Brief — Memory Module Restructure

## Problem

The mcp-memory module exists with full SQLite implementation but was never used in production. Agent lessons-learned accumulate in VS Code's `/memories/repo/` (not in-repo, not queryable, not quality-gated). The curator workflow writes to a separate thematic file layer. Result: no single source of truth, no confidence scoring, no state-based quality ladder, no filtered retrieval.

## Outcome

Restructure `serve/mcp-memory/` from unused SQLite storage to a markdown+frontmatter file engine in `.owlbear/memory/`, with quality-gated MCP tools for storage, retrieval, and curation. Internal architecture mirrors the kanban module: data engine (file I/O + parsing) → business logic (state transitions, validation, queries) → MCP tool layer (tool definitions, access control).

## Scope

- Restructure `serve/mcp-memory/` internals (SQLite → file engine, preserving the 3-layer split: engine / logic / MCP tools)
- 5 MCP tools with restricted mutation access
- State machine: `pending` → `curated` → `approved` → `deleted`
- Retire `/memories/repo/` thematic files (MCP entries become canonical)
- Update `h-mcp-memory`, `h-memory-structure`, `w-mem-curation`, `r-pipeline-protocol` skills/docs

## Data Model

### File: `.owlbear/memory/{slug}-{id6}.md`

```yaml
---
id: <UUIDv4>
title: <required, human-readable summary>
categories: [knowledge, behaviour]  # multi-value from 9-value enum
confidence: 0.85  # float [0.7, 1.0] — agent's certainty this is correct and reproducible
state: pending  # pending | curated | approved | deleted
scope_agents: [builder]  # optional list — which agents this applies to
created_at: 2026-05-02T10:00:00Z
updated_at: 2026-05-02T10:00:00Z
---

Markdown body with the actual learning content.
```

### Confidence

Single value: "creating agent's certainty that this observation is correct and reproducible."

- Range [0.7, 1.0] — entries below 0.7 too uncertain to store
- The state machine provides the rest: curator confirms correctness (curated), user confirms value (approved)
- Curator may adjust confidence during curation

### Category Enum (9 values)

`knowledge`, `behaviour`, `pitfall`, `process`, `tool`, `goal`, `personality`, `preference`, `context`

### Filename

- Slug derived from `title` field, kebab-cased, truncated
- 6-char random alphanumeric suffix
- Frozen at creation (never renamed)
- Example: `ruff-import-sorting-pitfall-a3f7c8.md`

## State Machine

```
pending ──(curator promotes)──→ curated ──(user approves)──→ approved
    │                              │                            │
    └──(curator deletes)───────────┴────────────────────────────┴──→ deleted ──(user purges)──→ removed
```

- **pending**: agent-created, unreviewed, excluded from default queries
- **curated**: curator-approved, visible to all agents in queries
- **approved**: user-approved, highest trust, visible to all agents
- **deleted**: marked for purge, excluded from all queries, grace period until user manually purges

## Tool API

| Tool | Access | Purpose |
|------|--------|---------|
| `store_learning` | Any agent | Create entry (state=pending). Requires: title, content, categories, confidence. Optional: scope_agents. |
| `query_memory` | Any agent | Filter/retrieve entries. Default: curated+approved only. Params: categories, scope_agents, min_confidence, limit. Sort: approved first, then curated, by confidence desc. |
| `update_entry` | Curator only | Edit content, categories, confidence. Promote state (pending→curated). |
| `delete_entry` | Curator only | Set state=deleted. |
| `approve_entry` | User only (via curator prompt) | Promote curated→approved. Curator presents candidates, user confirms. |

## Architecture

- **Engine**: `MemoryEngine` class — load all `.md` from `.owlbear/memory/`, parse YAML frontmatter + body, hold in-memory list of `MemoryEntry` Pydantic models
- **Cache**: `MtimeScanCache` — skip re-parse when directory mtime unchanged (kanban pattern)
- **Write**: atomic `mkstemp` → `fsync` → `rename` into `.owlbear/memory/`
- **Validation**: Pydantic model with enum constraints, confidence range, required fields
- **YAML**: `yaml.safe_load` / `yaml.safe_dump` only
- **Dedup**: none at engine level (curator responsibility)
- **Concurrency**: no OCC needed (single-user, sequential agents; mtime cache handles manual edits)

## Mutation Rules

- Any agent can create (pending)
- Only curator can promote pending→curated, edit content, or mark deleted
- Only user can promote curated→approved (via curator-presented approval flow)
- No agent can modify approved entries except to mark deleted (curator only)
- Enforcement: `allowed_agents` tool-level config in MCP server

## Migration

- No SQLite migration (server never used)
- No auto-migration of `/memories/repo/` entries
- User manually promotes VS Code memory entries during curation runs
- Thematic files in `/memories/repo/` retired after manual curation complete

## Deliverables

1. **Engine** — `serve/mcp-memory/src/owlbear_mcp_memory/engine.py` (new file-based engine)
2. **Models** — `serve/mcp-memory/src/owlbear_mcp_memory/models.py` (Pydantic entry model)
3. **Tools** — `serve/mcp-memory/src/owlbear_mcp_memory/tools.py` (5 MCP tools)
4. **Cache** — mtime-based scan cache
5. **Tests** — unit tests for engine, tools, validation, state transitions
6. **Skill updates** — `h-mcp-memory`, `h-memory-structure`, `w-mem-curation`, `r-pipeline-protocol`
7. **Config** — `allowed_agents` mutation restrictions
8. **Cleanup** — remove SQLite code, db file, alembic/migration artifacts if any

## Constraints

- Python 3.12+, `uv` package manager
- No external dependencies beyond stdlib + pydantic + pyyaml (already in workspace)
- `.owlbear/memory/` directory created on first write
- Maximum ~500 entries (in-memory load acceptable)
- No backwards compatibility with unused SQLite schema

## Risks

| Risk | Mitigation |
|------|-----------|
| Slug gets stale after aggregation | Acceptable — frozen slug doesn't corrupt data, git log still shows creation context |
| Purge breaks audit references | Git history preserves; grace period gives recovery window |
| 500+ entries slow startup | MtimeScanCache ensures re-parse only on change; scale unlikely near-term |
| Category sprawl (9 values) | Multi-value means each entry can be precise; curator consolidates overlapping entries |
